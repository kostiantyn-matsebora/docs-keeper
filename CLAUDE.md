# docs-keeper

A **stack-, domain-, product-agnostic** documentation steward: documentation writer +
hierarchical indexer + sources-of-truth registrar. Platform-neutral **core**, thin
per-platform **adapters** (Claude Code first; Copilot reserved). This repo doubles as its
own single-plugin marketplace.

User-facing overview + install: [`README.md`](README.md). This file is the agent root
prompt — how to work *in* this repo.

## Core / adapter separation (the central invariant)

- **`core/engine/`** — platform-neutral Python engine (pure drift / session / capture +
  git/fs collaborator factories) + a neutral `cli.py --drift-only`.
- **`core/spec/`** — platform-neutral spec: `role.md`, `conventions/`, the 5 command
  procedures (`commands/`), companion templates (`templates/`).
- **`adapters/<platform>/`** — per-platform glue ONLY: manifest, hook-config, thin
  entrypoints translating that platform's hook payload/response into `core/engine` calls,
  native agent/command wrappers. The Claude Code adapter (`adapters/claude-code/`) is the
  reference; `adapters/copilot/` is a reserved contract stub.
- **`build/assemble.py`** vendors `core/` into the adapter (`hooks/_engine/` + `spec/`) so
  the plugin is self-contained — Claude Code plugins cannot reference files outside their
  own root.

**Binding rule — keep `core/` platform-clean.** No host-specific payload field names, hook
decision verbs, or plugin-root references in `core/` (CI greps for `CLAUDE_PLUGIN_ROOT`,
`tool_input`, `"decision"`, `docs-keeper:`). Translate platform shapes at the adapter edge.

## Where things live

| Need | Path |
|---|---|
| Drift detection / children / registry / commit gate | `core/engine/drift.py` |
| Session tracker lifecycle (snapshot/track/mark-revised/GC) | `core/engine/session.py` |
| Doc-capture model + I/O | `core/engine/capture.py` |
| Per-repo config reader (`.docs-keeper/config.json`: `enforcement`, `paths` globs) | `core/engine/config.py` |
| git / dir-lister / file-reader factories | `core/engine/gitio.py` |
| Neutral CI drift gate | `core/engine/cli.py` |
| Role definition + index/authoring conventions + command procedures | `core/spec/` |
| Claude Code plugin manifest / hooks | `adapters/claude-code/.claude-plugin/plugin.json` · `adapters/claude-code/hooks/hooks.json` |
| Thin CC entrypoints (payload ↔ engine) | `adapters/claude-code/hooks/cc_*.py` |
| Vendoring (core → adapter) + drift guard | `build/assemble.py` |

**Generated — never hand-edit:** `adapters/claude-code/hooks/_engine/` and
`adapters/claude-code/spec/`. They are vendored from `core/` by `build/assemble.py` and
guarded by `assemble --check` (ruff excludes `_engine`).

## Change workflow (binding)

1. **Edit the source, not the vendored copy.** Logic → `core/engine/`; procedures/spec →
   `core/spec/`; platform glue → `adapters/<platform>/`.
2. **Re-assemble** after any `core/` change: `python3 build/assemble.py`.
3. **Test + lint + sync-check** before committing:
   ```
   python3 -m pytest          # core + adapter + build (no mocks)
   python3 -m ruff check .
   python3 build/assemble.py --check
   ```
4. **Tests are mandatory and mock-free.** Every module has a sibling `*_test.py`
   (`drift.py` → `drift_test.py`) in the same directory — no mirror tree. Inject
   collaborators as plain callables; real filesystem via `tmp_path`.

## Scripts convention

Python 3.11+, stdlib-only at runtime (so entrypoints stay invocable by path). Side-effecting
logic lives in `main()` guarded by `if __name__ == "__main__": main()`, so tests import and
exercise pure functions directly. ruff config + pytest discovery: [`pyproject.toml`](pyproject.toml).

## Authoring rules (this repo eats its own dog food)

- Concise + LLM-optimized; cut filler/preamble.
- Structure over prose: steps → numbered lists, mappings → tables, "X means Y" →
  `**X.** Y` on its own line.
- Preserve normative content (`MUST`/`SHOULD`/numbered constraints) under compression.
- The canonical statement of these rules is the product itself: [`core/spec/role.md`](core/spec/role.md)
  and [`core/spec/conventions/index-authoring.md`](core/spec/conventions/index-authoring.md).

## Adding a new platform adapter

Mirror `adapters/claude-code`: native manifest + hook-config, thin entrypoints that call
the `core/engine` API (see `adapters/copilot/README.md` for the binding table), native
agent/command wrappers pointing at the bundled `spec/`, and — if the platform also forbids
out-of-root references — a `build/assemble.py` vendoring job guarded by `--check`. Keep
`core/` untouched and platform-clean.
