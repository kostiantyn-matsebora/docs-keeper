---
title: docs-keeper
description: "A platform-agnostic documentation steward — keeps code and docs consistent both ways, and gives LLMs a hierarchical index to find the right doc fast, no MCP required."
permalink: /
---

# docs-keeper

[![Release](https://img.shields.io/github/v/release/kostiantyn-matsebora/docs-keeper?label=release&color=0f7a45)](https://github.com/kostiantyn-matsebora/docs-keeper/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/kostiantyn-matsebora/docs-keeper/ci.yml?branch=master&label=CI)](https://github.com/kostiantyn-matsebora/docs-keeper/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-0f7a45)](https://github.com/kostiantyn-matsebora/docs-keeper/blob/master/LICENSE)

**Documentation that can't drift from the code.**

Docs are written once and left behind. The code moves on; the docs don't. By the time someone
reads one, it may already be wrong — and no one can tell which line went stale.

docs-keeper makes docs a maintained system.

---

## Why docs-keeper

<ul class="features">
  <li>🔁 <strong>Both-way sync</strong> — Change the code or the docs; docs-keeper pulls the other side back into step. Neither silently drifts.</li>
  <li>🛡️ <strong>Commit-time gate</strong> — Drift can't sneak in. The commit blocks (or warns) the moment docs fall behind, and names exactly what to fix.</li>
  <li>🗂️ <strong>Hierarchical index</strong> — An LLM finds the right doc in seconds — a map at every level it walks top-down. No grep, no whole-repo dump.</li>
  <li>🔌 <strong>No MCP, no server</strong> — The index is plain <code>index.md</code> in your repo. Nothing to host or keep alive — unlike servers like <code>mcp-server-markdown</code>.</li>
  <li>📒 <strong>Sources-of-truth registry</strong> — Your host prompt's canonical references stay current on their own.</li>
  <li>🎯 <strong>Deterministic</strong> — Same tree, same index, every time. Computed by the engine — no LLM guesswork.</li>
  <li>♻️ <strong>Incremental</strong> — Only what changed gets reindexed. Never a full rebuild.</li>
  <li>🌐 <strong>Platform-agnostic</strong> — Stack-, domain-, and host-neutral core. Claude Code today; adapters stay thin.</li>
</ul>

## Install

docs-keeper installs **per repository**, not per user — so the whole team (and CI) picks it up
from one committed config. Run these in the repo you want to steward:

```
claude plugin marketplace add kostiantyn-matsebora/docs-keeper
claude plugin install docs-keeper@docs-keeper --scope project
```

`--scope project` writes the enablement into the repo's `.claude/settings.json` — commit that
file and every collaborator gets docs-keeper automatically. A plain `/plugin install` inside a
session enables it for **you** only; use project scope so it travels with the repo.

> The repo is **private** — `marketplace add` works for anyone with GitHub access to it (Claude
> Code uses your git credentials). Request access first if you don't have it.

Installing registers the agent, the `/docs-keeper:*` commands, and the commit/session hooks. It
doesn't touch your repo yet.

## Set up (once)

Run once in the repo you want to steward:

```
/docs-keeper:setup            # whole repo
/docs-keeper:setup docs/      # or scope to specific doc roots
```

`setup` reaches a green baseline: it creates `.docs-keeper/config.json`, finds or creates your
host prompt (`CLAUDE.md`), builds the `index.md` indexes, seeds the "Sources of truth" section,
and verifies there's no drift. It's **idempotent** — re-running on a green repo changes nothing.

## Everyday use

After setup, maintenance is automatic at commit time:

1. Edit docs (or code + docs) and run `git commit`.
2. In strict mode the **drift gate blocks** the commit and prints the exact fix queue.
3. The agent runs the queued maintenance (incremental — only what changed).
4. Re-stage and re-commit — the gate is clean and the commit lands.

Set `warn` mode if you'd rather be advised without blocking. The agent never commits for you —
you own the commit.

## Commands

| Command | Use it when |
|---|---|
| `/docs-keeper:setup [roots...]` | First run — bootstrap config + indexes + registry |
| `/docs-keeper:index <dir>` | A directory's docs changed, or you want to (re)build / split an index |
| `/docs-keeper:revise [doc] [-- brief]` | Tighten an existing doc or author a new one |
| `/docs-keeper:registry-sync` | The "Sources of truth" registry drifted |
| `/docs-keeper:sweep [scope]` | Consistency check — orphans, broken links, legacy READMEs |
| `/docs-keeper:capture` | Record a doc-worthy decision for later |
| `/docs-keeper:config` | View or change settings |

## Configuration

Settings live in `.docs-keeper/config.json` — a small, committed, per-repo file:

```json
{
  "enforcement": "warn",
  "paths": ["**/*.md"]
}
```

- **`enforcement`** — `warn` advises without blocking; `block` fails the commit (exit 2) on drift.
- **`paths`** — globs docs-keeper watches and indexes (default: every Markdown file). Narrow it
  (`["docs/**/*.md"]`) or add more (`["docs/**/*.md", "adr/**/*.md"]`).

Edit it directly, or use the command:

```
/docs-keeper:config                                 # show current settings
/docs-keeper:config enforcement block               # switch enforcement
/docs-keeper:config paths docs/**/*.md adr/**/*.md  # replace the watch globs
```

The rest of `.docs-keeper/` is per-machine runtime state and stays gitignored — only
`config.json` is committed.

## Use it in CI (no plugin needed)

The engine ships a host-neutral drift gate (stdlib-only Python 3.11+) — no Claude Code, no
plugin. Check docs-keeper out alongside **your** repo and point the gate at your repo root:

```yaml
# .github/workflows/docs-drift.yml — in YOUR repo
- uses: actions/checkout@v4                        # your repo, into the workspace
- name: Fetch the docs-keeper engine (private repo — needs a token)
  run: |
    git clone --depth 1 \
      "https://x-access-token:${{ secrets.DK_TOKEN }}@github.com/kostiantyn-matsebora/docs-keeper" \
      /tmp/docs-keeper
- name: Drift gate
  run: python3 /tmp/docs-keeper/core/engine/cli.py --drift-only --repo-root . --enforce block
```

`--repo-root` is the repo to check (`.` = your checkout); `--enforce warn|block` mirrors your
`.docs-keeper/config.json`. Exit `0` (clean) or `2` (drift; message on stderr).

## Troubleshooting

- **The commit gate didn't fire.** It only runs when Claude Code runs `git commit` (a PreToolUse
  hook), and only when staged files match your `paths` globs. A code-only change with the default
  `["**/*.md"]` won't trip it.
- **`setup` left drift.** Re-run `/docs-keeper:setup` — it converges to green and is idempotent.
- **Plugin shows "failed to load".** Re-install: `/plugin install docs-keeper@docs-keeper`. Hooks
  load from the plugin's standard `hooks/hooks.json`.
- **Want a stricter repo.** `/docs-keeper:config enforcement block` makes commits fail on drift.

---

Questions or issues? See the [repository](https://github.com/kostiantyn-matsebora/docs-keeper).
