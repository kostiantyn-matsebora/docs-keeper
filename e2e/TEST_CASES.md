# docs-keeper — e2e test-case catalog

A living catalog of end-to-end test cases for continuous improvement. Each case is black-box:
it drives docs-keeper as an installed plugin (or its hook entrypoints by path) and asserts an
**observable outcome** on a host repo. Grow coverage by moving `⬜ planned` cases to `✅
automated` and wiring them into [`e2e.yml`](../.github/workflows/e2e.yml) + the
[`assert_e2e.py`](assert_e2e.py) harness.

## How docs-keeper synchronizes (the model the cases assert)

docs-keeper is **not** a re-index-from-scratch tool. Its steady-state contract:

1. **Bootstrap once** — `/docs-keeper:setup` brings a fresh repo to a green baseline (config +
   per-dir `index.md` + the host "Sources of truth" registry).
2. **Then auto-maintain at commit time** — the **integrator** edits docs (or code+docs) and runs
   `git commit`. The **PreToolUse commit gate** auto-detects drift on the staged Markdown and,
   in **strict (`block`) mode**, blocks the commit with the *minimal incremental* maintenance
   queue (`revise <files>` · `index <dir>/` · `registry-sync`). In **`warn` mode** it emits a
   non-blocking advisory instead.
3. **The agent runs only the queued maintenance** — `index` is a recursive-descent + **walk-UP**
   that touches only affected ancestors (idempotent), never a full rebuild. The agent **never
   commits** (`role.md` § *Hand back* — "the integrator owns it"); the integrator re-stages and
   re-commits, and the gate clears.

**Cases therefore assert the gate→sync→commit loop, not explicit re-indexing.** A change-phase
case stages an edit, asks the session only to *commit*, and asserts (a) the gate first blocks
(drift present), (b) after auto-sync the tree is clean again **incrementally**, and (c) the
initially-blocked commit eventually lands.

## Legend

| Status | Meaning |
|---|---|
| ✅ | Automated in `e2e.yml` today |
| 🟡 | Partially automated (happy path only, or asserted indirectly) |
| ⬜ | Planned — not yet automated |
| 🐞 | Automated **and currently failing — surfaced a real product issue** (see § Findings) |

**Tier.** `D` = deterministic (no API key; runs in `engine-e2e`). `A` = agentic (real headless
Claude session; runs in `agentic-e2e`).

Each case lists **Pre** (preconditions), **Do** (action), **Expect** (assertion). Keep one
observable assertion per case; prefer drift-gate exit codes and structural file checks over
transcript scraping.

---

## 1. Install — plugin assets + activation

| ID | Tier | Status | Title |
|---|---|---|---|
| INST-01 | D | ✅ | Plugin manifest valid + names `docs-keeper` |
| INST-02 | D | ✅ | `hooks.json` wires SessionStart / PreToolUse / Stop |
| INST-03 | D | ✅ | Agent + all 7 `/docs-keeper:*` commands ship |
| INST-04 | D | ✅ | Vendored `_engine` + `spec` trees present in plugin root |
| INST-05 | A | 🟡 | `claude plugin install` succeeds and the plugin is listed |
| INST-06 | D | ✅ | `hooks.json` wraps events under a top-level `"hooks"` key (load-format guard, F1) |
| INST-07 | A | 🟡 | **Installed plugin's hooks LOAD** (`Status: loaded`) — F1 fixed; pending agentic re-run |
| INST-08 | A | ⬜ | SessionStart hook fires (snapshot written under `.docs-keeper/` runtime state) |
| INST-09 | D | ⬜ | `claude plugin validate --strict adapters/claude-code` passes |

- **INST-06.** *Do:* `assert_e2e.py install`. *Expect:* the wrapper check passes. This is the
  deterministic regression guard for F1 — a bare event map (no top-level `"hooks"`) fails to load.
- **INST-07.** *Pre:* plugin installed. *Do:* `claude plugin list`. *Expect:* docs-keeper
  `Status: loaded` (no `Hook load failed`). Load-bearing for the commit-gate auto-sync (§3, §4).

## 2. Setup — cold start to a green baseline

| ID | Tier | Status | Title |
|---|---|---|---|
| SETUP-01 | A | ✅ | `config.json` created + valid (`enforcement`, `paths`) |
| SETUP-02 | A | ✅ | Per-directory `index.md` files built across the docs |
| SETUP-03 | A | ✅ | Host prompt gains a "Sources of truth" section |
| SETUP-04 | A | 🟡 | **Post-setup drift gate is CLEAN (exit 0)** — F2 fixed; pending agentic re-run |
| SETUP-05 | A | ⬜ | Idempotent — a second `setup` on a green repo writes no changes (`git diff` empty) |
| SETUP-06 | A | ⬜ | No host prompt present → `setup` creates a minimal `CLAUDE.md` skeleton |
| SETUP-07 | A | ⬜ | `setup docs/` scopes indexing to one root; siblings untouched |
| SETUP-08 | A | ⬜ | Existing hand-authored `index.md` is not clobbered (proposed diff, not overwrite) |
| SETUP-09 | A | ⬜ | Pre-existing `config.json` is read, not overwritten |
| SETUP-10 | D | ✅ | `cli.py --emit-children <dir>` is deterministic + matches the gate's expected set (F3) |
| SETUP-11 | A | 🟡 | Setup reaches green deterministically across repeated runs (F3 fix) — pending agentic re-run |

- **SETUP-04.** *Pre:* `setup` ran. *Do:* `cli.py --drift-only --enforce block`. *Expect:* exit 0.
  F2 (repo-root index never satisfied the registry check) is fixed in the engine; the assertion is
  unchanged and now passes deterministically (EDGE-07) — pending the agentic re-run for the
  full-stack confirmation.

## 3. Code change → auto-synchronized by the commit gate

| ID | Tier | Status | Title |
|---|---|---|---|
| CODE-01 | D | ✅ | PreToolUse gate blocks a drifting `git commit` (exit 2; queue names the commands) |
| CODE-02 | A | 🟡 | Strict mode: code+doc change → commit → gate auto-syncs → **commit lands**, tree clean |
| CODE-03 | A | 🟡 | New doc declared in its `index.md` after the auto-sync (incremental walk-up) |
| CODE-04 | A | ⬜ | `warn` mode: commit is NOT blocked; advisory `systemMessage` emitted; commit lands as-is |
| CODE-05 | A | ⬜ | Code-only change (no Markdown staged) → gate is silent (exit 0, `no-docs-change`) |
| CODE-06 | A | ⬜ | Edited (not new) doc, unrevised this session → gate queues `revise`, not `index` |
| CODE-07 | A | ⬜ | Agent must NOT bypass the gate (`--no-verify` is disallowed and not used) |

- **CODE-02/03 depend on INST-07** (hooks loading). With F1 fixed the in-session commit is gated,
  so the agent must sync before the commit lands — pending the agentic re-run to confirm green.

## 4. Documentation change → auto-synchronized by the commit gate

| ID | Tier | Status | Title |
|---|---|---|---|
| DOC-01 | D | ✅ | Neutral CLI gate: clean tree exits 0, drifting tree exits 2 |
| DOC-02 | A | 🟡 | Strict mode: new doc → commit → gate auto-syncs index/registry → commit lands, tree clean |
| DOC-03 | A | 🟡 | Resolved index declares the new doc as a child (incremental, no full rebuild) |
| DOC-04 | A | ⬜ | Deleted doc → walk-up removes its `children:` entry on the next commit; gate clean |
| DOC-05 | A | ⬜ | Renamed doc → old slug dropped, new slug added in one incremental pass |
| DOC-06 | A | ⬜ | New sub-dir with its own `index.md` folds into the parent as one boundary entry |
| DOC-07 | A | ⬜ | `index.md` `title`/`intro` change → gate queues `registry-sync`; registry line refreshed |
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

## 6. Session + lifecycle hooks (all depend on INST-06)

| ID | Tier | Status | Title |
|---|---|---|---|
| SESS-01 | A | ⬜ | Stop hook tracks edited docs into session state |
| SESS-02 | A | ⬜ | PostToolUse(Skill) marks a revised doc so the commit gate stops re-suggesting `revise` |
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
| EDGE-07 | D | ✅ | Repo-root indexed tree (`./index.md`) registry membership resolves (regression for F2) |
| EDGE-08 | D | ⬜ | Windows/CRLF index.md parsed identically to LF |

---

## Findings — surfaced by e2e runs (both now FIXED)

Real product issues the agentic e2e caught. Both are fixed in the engine/adapter and guarded by
new deterministic regression tests; the agentic cases that depended on them (INST-07, SETUP-04,
CODE-02/03, DOC-02/03) move 🐞→🟡 and confirm green on the next agentic run. Assertions were never
weakened to go green.

### F1 — installed plugin hooks failed to load (blocked all hook-driven auto-sync) — **FIXED**

`claude plugin install docs-keeper@docs-keeper` then `claude plugin list` reports:

```
docs-keeper@docs-keeper  Status: ✘ failed to load
  Error: Hook load failed: expected record, received undefined at path ["hooks"]
```

Commands + agent load fine (so `setup` works), but **no hooks activate** — the PreToolUse commit
gate never fires in a real session. This nullifies the strict-mode auto-sync that is docs-keeper's
core "guard" feature.

**Root cause (confirmed vs the current Claude Code plugin spec).** A plugin hooks file must wrap
the event map under a top-level `"hooks"` key; `adapters/claude-code/hooks/hooks.json` put the
event names at the top level.

**Fix (landed).** Wrapped the event map: `{ "hooks": { "SessionStart": [...], ... } }`. Guarded
by `assert_e2e.check_install` (INST-06) — both the real adapter and a unit test asserting a bare
event map is rejected. Verified: `Status: loaded` on the next agentic run (INST-07).

### F2 — setup left residual drift for a repo-root indexed tree — **FIXED**

After a successful `setup` on a host whose indexed-tree root is the repo root (a `./index.md`),
`cli.py --drift-only --enforce block` still reported drift (`/registry-sync`). The root index's
registry bullet was written as `[index.md](index.md)`, but the engine's registry-membership check
for the root dir `.` looked for the literal `./` substring (`drift.check_registry_has_entry`),
which the bullet never contains — so a repo-root index could never satisfy the registry check.

**Fix (landed).** `drift.registry_needle(dir_path)` maps the root dir `.`/`''` to the `index.md`
file reference (sub-dirs keep `<dir>/`), used by both `check_registry_has_entry` and
`check_registry_role_in_sync`. Guarded by new `drift_test.py` cases + the EDGE-07 integration
check; `setup` now reaches a green baseline on a root-level tree (SETUP-04).

### F3 — `setup` was non-deterministic; didn't reliably reach a green baseline — **FIXED**

The drift algorithm (`drift.get_expected_children`) is pure and byte-stable, but `setup`/`index`
relied on the **agent** to hand-author the `children:` set from the spec. So the LLM's structure
choice varied run-to-run: one run built 5 per-dir sub-indexes (gate-clean), another built a single
flat root `index.md` whose `children:` didn't match the engine's recursive descent → residual
`/index ./` drift, so the green baseline wasn't reached.

**Fix (landed).** The engine now *emits* the authoritative set: `cli.py --emit-children <dir>`
prints the exact descent the gate checks (deterministic, reproducible). `index.md` § *Deterministic
`children:`* and `setup.md` step 3 make the procedure source `children:` from that emitter instead
of free-handing it (and setup creates a single index per scope root — no ad-hoc sub-indexes).
`setup.md` step 6 adds a binding **verify-green** loop: run the gate and converge until clean
before reporting success. Guarded by SETUP-10 (deterministic emitter); the full-stack
reproducibility confirms on the next agentic run (SETUP-11).

---

## How to add a case

1. Pick the next ID in its section; write **Pre / Do / Expect** with a single observable
   assertion.
2. Prefer a **deterministic (`D`)** realization when the outcome doesn't require the LLM — wire it
   into `engine-e2e` against a `tmp`/fixture repo so it runs without an API key.
3. For **agentic (`A`)** cases, add a phase step in `agentic-e2e` and an assertion in
   `assert_e2e.py` (with a sibling unit test), then flip the status to ✅.
4. Assert the **gate→sync→commit loop** (drift-gate exit codes + structural file checks + "the
   commit landed"); treat session transcripts as debug artifacts, not assertions.
5. When a case surfaces a product bug, mark it 🐞 and document it under § Findings — never relax
   the assertion to go green.
