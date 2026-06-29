# docs-keeper

A **stack-, domain-, product-agnostic** documentation steward: a documentation writer +
hierarchical indexer + sources-of-truth registrar. The capability is **platform-neutral
at its core**, with **thin per-platform adapters**. The Claude Code adapter (a plugin) is
the first; this repo doubles as its own single-plugin marketplace.

## What it does

- **Index.** Build / refresh per-directory `index.md` files (github/docs-style
  recursive-descent `children:` lists with sub-index boundaries) and walk up the tree.
- **Revise.** Tighten or author docs against the host project's authoring rules
  (extract-over-compact, structure-over-prose), never inventing product decisions.
- **Register.** Keep the host's "sources of truth" registry in minimum-footprint sync.
- **Sweep.** Cross-doc consistency: orphans, broken links, ambiguous resolutions, legacy
  READMEs.
- **Guard.** A commit-time drift gate (block / warn), session tracking of edited docs, and
  capture of doc-worthy decisions — all backed by the same neutral engine.

## Layout

```
core/
  engine/      Platform-neutral Python engine (pure drift/session/capture + git/fs
               collaborators) + a neutral `cli.py --drift-only` for CI on any platform.
  spec/        Platform-neutral spec: role.md, conventions/, the 7 command procedures,
               and companion templates (Documentation Report, anchor slugs).
adapters/
  claude-code/ The Claude Code plugin: .claude-plugin/plugin.json, thin hooks/cc_*.py
               entrypoints (CC payload <-> engine), hooks.json, agents/ + commands/
               wrappers, and the vendored core (hooks/_engine/ + spec/, generated).
  copilot/     Reserved contract stub referencing the same core/engine API.
build/
  assemble.py  Vendors core/ into the adapter so the plugin is self-contained
               (Claude Code plugins cannot reference files outside their root);
               `assemble.py --check` guards core <-> adapter sync in CI.
.claude-plugin/marketplace.json   This repo as a single-plugin marketplace.
```

**Core / adapter separation (invariant).** No host-specific payload field names, hook
decision verbs, or plugin-root references live in `core/` — adapters translate their
platform's hook payload into engine calls at the edge. CI enforces this.

## Install (Claude Code)

docs-keeper is distributed from this repository as a single-plugin marketplace and installs
**per repository**, not per user — so the whole team (and CI) picks it up from one committed
config. Run these in the repo you want to steward:

```
claude plugin marketplace add kostiantyn-matsebora/docs-keeper
claude plugin install docs-keeper@docs-keeper --scope project
```

`--scope project` writes the enablement into the repo's `.claude/settings.json` — commit that
file and every collaborator gets docs-keeper automatically. A plain `/plugin install` inside a
session enables it for **you** only; use project scope so it travels with the repo.

> The repo is **private** — `marketplace add` works for anyone with GitHub access to it (Claude
> Code uses your git credentials), so request access first if you don't have it.

This registers the `docs-keeper` agent, the seven `/docs-keeper:*` commands (see
[Commands](#commands)), and the SessionStart / PreToolUse / PostToolUse / PostCompact / Stop /
SessionEnd hooks.

Configure docs-keeper via `.docs-keeper/config.json`, a per-repo settings file you commit
alongside your docs:

```json
{
  "enforcement": "warn",
  "paths": ["**/*.md"]
}
```

- **`enforcement`** — `warn` surfaces the drift queue without blocking; `block` fails the
  commit (exit 2) on drift. Defaults to `block` when the file or setting is absent.
- **`paths`** — array of glob patterns docs-keeper watches and indexes. Defaults to
  `["**/*.md"]` (every Markdown file in the repo). Narrow it (`["docs/**/*.md"]`) or add
  more globs (`["docs/**/*.md", "adr/**/*.md", "**/*.mdx"]`) to change scope. Globs support
  `**/` (any depth), `*` (within a path segment), and `?`.

Edit the file directly, or use the `/docs-keeper:config` command to view and change settings
with validation:

```
/docs-keeper:config                                 # show current config
/docs-keeper:config enforcement block               # switch enforcement
/docs-keeper:config paths docs/**/*.md adr/**/*.md  # replace the watch/index globs
```

Per-machine runtime state (session / capture files) lives under `.docs-keeper/sessions/` and
stays gitignored — only `config.json` is committed.

### First run (bootstrap)

Install registers the agent/commands/hooks but does not touch your repo. To reach a green
baseline — index your docs and create the "sources of truth" registry — run once:

```
/docs-keeper:setup            # whole repo
/docs-keeper:setup docs/      # or scope to specific doc roots
```

After that, the commit-time gate and `/docs-keeper:index` · `revise` · `sweep` ·
`registry-sync` keep things in sync.

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

## Use without a platform (neutral CI gate)

```
python3 core/engine/cli.py --drift-only [--repo-root <path>] [--enforce warn|block]
```

Exit 0 (clean) or 2 (drift; message on stderr). No hook host required.

## Alternatives & comparison

docs-keeper occupies a niche no single tool covers: **agent-native, in-repo, structural
documentation stewardship**. Adjacent tools each cover one slice; none unify
**INDEX + REVISE + REGISTER + DRIFT GATE + CAPTURE + SWEEP**.

| Competitor | Overlaps | docs-keeper does better |
|---|---|---|
| **Swimm** | Drift gate | Gates inside coding-agent hooks (not just PR-check time); watches all Markdown + indexes + registry, not only code-coupled snippets; no full-history requirement. |
| **Doc Detective** | Consistency sweep | Static index/registry/link analysis with a fix queue, vs runtime tests against a live product. |
| **lychee / markdown-link-check** | Broken links | Adds orphans, ambiguous resolutions, registry sync, and indexing — not links alone. |
| **Mintlify `llms.txt`** | Indexing | Recursive per-directory `index.md` with ancestor walk-up, vs one flat hosted index (100K-char cap). |
| **Docusaurus / MkDocs / Sphinx / Antora** | Nav + link check | Automatic code-to-docs drift detection and walk-up indexing, vs manual nav and release-snapshot versioning. |
| **adr-log / Log4brains / Backstage** | Registry | Whole-repo sources-of-truth sync + drift gating, not ADR-scoped manual nav edits. |

**Where docs-keeper wins:**

- Commit-time drift gating wired into coding-agent hooks.
- Hierarchical `index.md` generation with ancestor walk-up.
- Agent-native decision capture during coding sessions.
- Platform-neutral core + thin adapters.

**Where established tools still lead:** hosting, versioning, ecosystem breadth, and
non-Markdown/API docs.

## Example host repo (pair-repo)

`docs-keeper-example` is a standalone sample host project — the **Acme Stack** app (frontend +
backend + infrastructure + testing + docs) — used to exercise docs-keeper end-to-end and as a
runnable example. It ships a clean docs baseline and a pairing test that runs this engine against
itself. Keep it checked out next to this repo to run the pairing suite.

## Develop

```
python3 -m pytest          # core + adapter + build suites (no mocks)
python3 -m ruff check .     # lint
python3 build/assemble.py           # regenerate the vendored plugin
python3 build/assemble.py --check   # CI: fail if core <-> adapter drifted
```

After editing anything under `core/`, re-run `build/assemble.py` so the vendored copies
inside `adapters/claude-code/` stay in sync (CI's `assemble --check` enforces it).

## License

MIT — see [`LICENSE`](LICENSE).
