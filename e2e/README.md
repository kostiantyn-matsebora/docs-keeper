# e2e — end-to-end test of docs-keeper as an installed plugin

Driven by [`.github/workflows/e2e.yml`](../.github/workflows/e2e.yml). Where the per-module
pytest suites test the engine in isolation, this harness asserts **observable outcomes on a
real host repo** after each phase a user would go through: install → setup → code change →
doc change.

## Two tiers

| Job | Needs secrets? | What it proves |
|---|---|---|
| `engine-e2e` | no | Plugin assembles + ships every asset; the **PreToolUse commit gate** and the **neutral CI drift gate** block on drift (exit 2) and pass when clean (exit 0) — run by path against a throwaway git fixture. |
| `agentic-e2e` | yes | A real headless Claude Code session imitates a user: installs the plugin, runs `/docs-keeper:setup`, makes a code change + a doc change, and the drift hooks keep the docs synchronized. |

`agentic-e2e` is gated by a `preflight` job: when the secrets are absent it is **skipped with
a warning**, so the deterministic tier still runs on every trigger.

## Required secrets (agentic tier)

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` **or** `CLAUDE_CODE_OAUTH_TOKEN` | Authenticates the headless `claude` CLI. Use an Anthropic Console API key (`sk-ant-…`) **or** a Claude subscription token from `claude setup-token` — the workflow accepts either. |
| `EXAMPLE_REPO_TOKEN` | PAT that can clone the **private** `kostiantyn-matsebora/docs-keeper-example` host repo (the default `GITHUB_TOKEN` is scoped to this repo only). |

## Triggers

`workflow_dispatch` (manual) + weekly `schedule`. The agentic tier clones an external repo and
spends API tokens, so it is deliberately not on every push.

## Phases asserted

1. **Install** — `assert_e2e.py install` checks `plugin.json`, `hooks.json` events, the agent,
   all seven `/docs-keeper:*` commands, and the vendored `_engine` + `spec` trees.
2. **Setup** — `assert_e2e.py setup` checks `.docs-keeper/config.json` is created + valid, the
   per-directory `index.md` files were built, and the host prompt gained a "Sources of truth"
   section; then the drift gate must be clean (green baseline).
3. **Code change → auto-synced on commit** — a source edit + a new doc are staged; the session is
   asked only to *commit*. In strict (`block`) mode the PreToolUse gate auto-detects drift, blocks,
   and the agent runs the queued incremental maintenance (walk-up index + registry-sync) before
   the integrator's commit can land. Asserts: gate first blocks (exit 2) → tree clean again → the
   new doc is declared → the initially-blocked commit landed. **No explicit re-index.**
4. **Doc change → auto-synced on commit** — same gate→sync→commit loop driven by a direct doc edit.

> The change phases assert docs-keeper's real contract — the commit gate auto-drives *incremental*
> synchronization; the agent never re-indexes from scratch and never commits (the integrator does).
> See [`TEST_CASES.md`](TEST_CASES.md) for the full catalog and the open Findings (F1: installed
> hooks fail to load; F2: setup leaves registry drift for a repo-root index).

## The assertion harness

[`assert_e2e.py`](assert_e2e.py) — stdlib-only, pure helpers + an argparse CLI with one
sub-command per phase (`install` / `setup` / `index-declares`). Each prints `PASS`/`FAIL` per
check and exits non-zero on any failure. Unit-tested by the sibling
[`assert_e2e_test.py`](assert_e2e_test.py) (real filesystem under `tmp_path`, no mocks), and
collected by the standard `pytest` run.

```
python3 e2e/assert_e2e.py install --plugin-root adapters/claude-code
python3 e2e/assert_e2e.py setup   --repo /path/to/host-repo
python3 e2e/assert_e2e.py index-declares --index <dir>/index.md --child /payments
```
