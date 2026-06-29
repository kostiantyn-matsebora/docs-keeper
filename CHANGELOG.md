# Changelog

All notable changes to docs-keeper are recorded here. This project adheres to
[Semantic Versioning](https://semver.org/).

## 0.3.0 — config-aware sweep & revise, public release

### Added

- **`cli.py --emit-globs`** — prints the effective index globs (config `paths`, else the engine
  default), one per line. The deterministic source path-aware procedures and adapters use to
  surface the indexed glob set instead of assuming `.md`.

### Changed

- **`sweep` and `revise` now honor the config `paths` globs** instead of hard-coding `.md`. With a
  custom `paths` (e.g. `["**/*.md", "**/*.mdx"]`), `sweep` resolves `children:` entries and detects
  orphans against the configured extensions, and `revise`'s no-arg target resolution filters
  uncommitted files to `paths`. The default `["**/*.md"]` preserves existing behavior. This closes
  the gap where `index` / `setup` / the drift gate already respected `paths` but these two did not.

### Project

- **First public release.** Added `SECURITY.md`, GitHub issue / pull-request templates, and
  `CODEOWNERS`; flipped the install docs from private to public; ignored Jekyll build artifacts
  (`docs/_site/`, `docs/.sass-cache/`). Renamed the default branch `master` → `main`.

## 0.2.0 — runtime sessions split, docs site, deterministic indexing

### Added

- **Adopter documentation site** (GitHub Pages) — landing page with install/CI guidance and an
  "Alternatives & comparison" section ([`docs/`](docs/)).
- **`setup` defaults notice** — on a cold start, `setup` now reports the seeded config defaults
  (`enforcement`, `paths`) and how to change them (the `config` command, or hand-editing
  `.docs-keeper/config.json`), plus a reminder to reindex after a `paths` change.

### Changed

- **Runtime state relocated to `.docs-keeper/sessions/`** — all per-session runtime files
  (session / capture / attempts) now live under `.docs-keeper/sessions/`, leaving only the
  committed `config.json` at the `.docs-keeper/` root for a clean config-vs-runtime split.
- **`config` guidance relaxed** — hand-editing `.docs-keeper/config.json` is now explicitly
  allowed (the `config` command is still preferred because it validates and canonicalizes).
- **README aligned with the docs site** — per-repo `claude plugin install … --scope project`
  install flow and a full 7-command table.

### Fixed

- **Deterministic children emission across platforms** — `get_expected_children` now returns
  sorted entries, so `index` / `setup` build identical `children:` lists regardless of the
  filesystem's directory-iteration order (previously diverged on Windows NTFS).

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
