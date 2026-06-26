# Changelog

All notable changes to docs-keeper are recorded here. This project adheres to
[Semantic Versioning](https://semver.org/).

## 0.1.0 — first release

First published release of the docs-keeper Claude Code plugin (platform-neutral core + the
Claude Code adapter), distributed from this repo as a single-plugin marketplace.

### Features

- **Documentation steward** — writer + hierarchical indexer + sources-of-truth registrar,
  stack-/domain-/product-agnostic.
- **Agent + commands** — the `docs-keeper` agent and `/docs-keeper:*` commands: `setup` ·
  `index` · `revise` · `sweep` · `registry-sync` · `capture` · `config`.
- **Commit-time drift gate** — a PreToolUse hook auto-detects index/registry drift on staged
  Markdown and, in strict (`block`) mode, blocks the commit with the minimal incremental
  maintenance queue; `warn` mode advises without blocking.
- **Session + capture hooks** — SessionStart/Stop/SessionEnd tracking of edited docs and
  PostCompact capture of doc-worthy decisions.
- **Per-repo config** — `.docs-keeper/config.json` (`enforcement`, `paths`).
- **Deterministic indexing** — `cli.py --emit-children` exposes the engine's exact recursive
  descent so `index`/`setup` build `children:` reproducibly (no free-handing).

### Fixes (hardened via the end-to-end suite)

- **Plugin hooks now load** — wrap the hook event map under a top-level `"hooks"` key and drop
  the redundant `plugin.json` `hooks` reference (the standard `hooks/hooks.json` auto-loads).
- **Setup reaches a green baseline** — repo-root index registry membership resolves, and setup
  converges deterministically (verify-green loop).
- **Valid command frontmatter** — `revise.md` `argument-hint` is quoted (previously invalid
  YAML, which dropped the command's metadata at load).

### Testing

- A tiered end-to-end workflow ([`.github/workflows/e2e.yml`](.github/workflows/e2e.yml)): a
  deterministic engine/hook job plus a real headless Claude Code session that installs the
  plugin, runs `setup`, and exercises the commit-gate auto-sync against a host repo.
- ~330 mock-free unit + black-box tests; see [`e2e/TEST_CASES.md`](e2e/TEST_CASES.md).
