# docs-keeper — e2e test-case catalog

A living catalog of end-to-end test cases for continuous improvement. Each case is black-box:
it drives docs-keeper as an installed plugin (or its hook entrypoints by path) and asserts an
**observable outcome** on a host repo. Grow coverage by moving `⬜ planned` cases to `✅
automated` and wiring them into [`e2e.yml`](../.github/workflows/e2e.yml) + the
[`assert_e2e.py`](assert_e2e.py) harness.

## Legend

| Status | Meaning |
|---|---|
| ✅ | Automated in `e2e.yml` today |
| 🟡 | Partially automated (happy path only, or asserted indirectly) |
| ⬜ | Planned — not yet automated |

**Tier.** `D` = deterministic (no API key; runs in `engine-e2e`). `A` = agentic (real headless
Claude session; runs in `agentic-e2e`).

Each case lists **Pre** (preconditions), **Do** (action), **Expect** (assertion). Authors:
keep one observable assertion per case; prefer drift-gate exit codes and structural file checks
over transcript scraping.

---

## 1. Install — plugin assets in place

| ID | Tier | Status | Title |
|---|---|---|---|
| INST-01 | D | ✅ | Plugin manifest valid + names `docs-keeper` |
| INST-02 | D | ✅ | `hooks.json` wires SessionStart / PreToolUse / Stop |
| INST-03 | D | ✅ | Agent + all 7 `/docs-keeper:*` commands ship |
| INST-04 | D | ✅ | Vendored `_engine` + `spec` trees present in plugin root |
| INST-05 | A | 🟡 | `claude plugin install` succeeds; `plugin list` shows it enabled |
| INST-06 | A | ⬜ | SessionStart hook fires on session start (snapshot written under `.docs-keeper/`) |
| INST-07 | D | ⬜ | `claude plugin validate --strict adapters/claude-code` passes |
| INST-08 | A | ⬜ | Uninstall removes hooks; a later commit is no longer gated |

- **INST-05.** *Pre:* CLI installed, local marketplace added. *Do:* `claude plugin install
  docs-keeper@docs-keeper`. *Expect:* `claude plugin list` contains `docs-keeper`; exit 0.
- **INST-06.** *Pre:* plugin enabled. *Do:* start a headless session. *Expect:* a session
  snapshot file appears under the host repo's `.docs-keeper/` runtime state.

## 2. Setup — cold start to a green baseline

| ID | Tier | Status | Title |
|---|---|---|---|
| SETUP-01 | A | ✅ | `config.json` created + valid (`enforcement`, `paths`) |
| SETUP-02 | A | ✅ | At least one `index.md` built across the docs |
| SETUP-03 | A | ✅ | Host prompt gains a "Sources of truth" section |
| SETUP-04 | A | ✅ | Post-setup drift gate is clean (exit 0) |
| SETUP-05 | A | ⬜ | Idempotent — a second `setup` on a green repo writes no changes (`git diff` empty) |
| SETUP-06 | A | ⬜ | No host prompt present → `setup` creates a minimal `CLAUDE.md` skeleton |
| SETUP-07 | A | ⬜ | `setup docs/` scopes indexing to one root; siblings untouched |
| SETUP-08 | A | ⬜ | Existing hand-authored `index.md` is not clobbered (proposed diff, not overwrite) |
| SETUP-09 | A | ⬜ | Pre-existing `config.json` is read, not overwritten |

- **SETUP-05.** *Pre:* `setup` already run, tree clean. *Do:* run `setup` again. *Expect:*
  `git status --porcelain` empty.
- **SETUP-06.** *Pre:* host repo with no `CLAUDE.md`/`AGENTS.md`. *Do:* `setup`. *Expect:*
  `CLAUDE.md` created with an H1 + empty `## Sources of truth`.

## 3. Drift on code change — hook works, docs synchronized

| ID | Tier | Status | Title |
|---|---|---|---|
| CODE-01 | A | ✅ | Code edit + new doc → agent syncs indexes/registry → drift clean |
| CODE-02 | A | ✅ | New doc is declared in its `index.md` `children:` after sync |
| CODE-03 | D | ✅ | PreToolUse commit gate blocks a drifting `git commit` (exit 2, message names commands) |
| CODE-04 | A | 🟡 | Agent commits after syncing; the gate no longer blocks |
| CODE-05 | A | ⬜ | `enforcement: warn` → gate exits 0 but emits a `systemMessage` advisory |
| CODE-06 | A | ⬜ | Code-only change (no markdown) → gate is silent (exit 0, `no-docs-change`) |
| CODE-07 | A | ⬜ | Doc edited + marked revised this session → no `revise` re-suggested on commit |

- **CODE-03.** *Pre:* git repo, indexed dir declaring no children, a new staged `.md`. *Do:*
  pipe a `git commit` payload to `cc_maintenance.py` with `enforcement=block`. *Expect:* exit 2,
  stderr contains the drift queue (`/docs-keeper:revise`, `/docs-keeper:index`).
- **CODE-06.** *Pre:* green repo, `paths: ["**/*.md"]`. *Do:* stage a source-only change and
  commit. *Expect:* gate exit 0, reason `no-docs-change`.

## 4. Drift on documentation change — hook works, docs synchronized

| ID | Tier | Status | Title |
|---|---|---|---|
| DOC-01 | A | ✅ | New unindexed doc → drift gate detects it (exit 2) |
| DOC-02 | A | ✅ | `/docs-keeper:index <dir>` resolves the drift → gate clean (exit 0) |
| DOC-03 | A | ✅ | Resolved index declares the new doc as a child |
| DOC-04 | D | ✅ | Neutral CLI gate: clean tree exits 0, drifting tree exits 2 |
| DOC-05 | A | ⬜ | Deleted doc → walk-up removes its `children:` entry; gate clean |
| DOC-06 | A | ⬜ | Renamed doc → old slug dropped, new slug added in one pass |
| DOC-07 | A | ⬜ | New sub-dir with its own `index.md` folds into parent as one boundary entry |
| DOC-08 | A | ⬜ | Config `paths` narrowed → files outside the globs are not indexed and don't drift |

## 5. Other commands (coverage backlog)

| ID | Tier | Status | Title |
|---|---|---|---|
| REV-01 | A | ⬜ | `/docs-keeper:revise <doc>` tightens prose without inventing decisions |
| REG-01 | A | ⬜ | `/docs-keeper:registry-sync` reconciles a stale registry line |
| REG-02 | A | ⬜ | `registry-sync` on a repo with no section halts and asks (no cold-create) |
| SWEEP-01 | A | ⬜ | `/docs-keeper:sweep` reports orphans + broken links |
| SWEEP-02 | A | ⬜ | `sweep` flags a legacy-navigation README as a deprecation candidate |
| CFG-01 | A | ⬜ | `/docs-keeper:config enforcement block` persists + validates |
| CFG-02 | A | ⬜ | `config paths docs/**/*.md` replaces the watch globs |
| CFG-03 | D | ⬜ | `config` rejects an invalid enforcement value with a clear error |
| CAP-01 | A | ⬜ | PostCompact capture records a doc-worthy decision from a summary |

## 6. Session + lifecycle hooks

| ID | Tier | Status | Title |
|---|---|---|---|
| SESS-01 | A | ⬜ | Stop hook tracks edited docs into session state |
| SESS-02 | A | ⬜ | PostToolUse(Skill) marks a revised doc so the commit gate stops re-suggesting it |
| SESS-03 | A | ⬜ | SessionEnd GCs stale per-session tracker files |

## 7. Edge cases + robustness

| ID | Tier | Status | Title |
|---|---|---|---|
| EDGE-01 | D | ⬜ | Empty repo (no docs) → setup + gate are no-ops, exit 0 |
| EDGE-02 | D | ⬜ | `AGENTS.md` host (no `CLAUDE.md`) → registry section detected there |
| EDGE-03 | D | ⬜ | Excluded dirs (`node_modules`, `build`) never indexed |
| EDGE-04 | D | ⬜ | `git commit-tree` / `commit-graph` do NOT trigger the gate (word-boundary) |
| EDGE-05 | D | ⬜ | Non-`.md` files under a matching glob ignored as children |
| EDGE-06 | A | ⬜ | Large tree → growth-by-splitting introduces a sub-index; parent shrinks |
| EDGE-07 | D | ⬜ | Windows/CRLF index.md parsed identically to LF |

---

## How to add a case

1. Pick the next ID in its section; write **Pre / Do / Expect** with a single observable
   assertion.
2. Prefer a **deterministic (`D`)** realization when the outcome doesn't require the LLM — wire
   it into `engine-e2e` against a `tmp`/fixture repo so it runs without an API key.
3. For **agentic (`A`)** cases, add a phase step in `agentic-e2e` and an assertion in
   `assert_e2e.py` (with a sibling unit test), then flip the status to ✅.
4. Keep assertions on drift-gate exit codes + structural file checks; treat session transcripts
   as debug artifacts, not assertions (they vary run to run).
