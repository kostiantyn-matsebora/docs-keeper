# setup — procedure

One-time **bootstrap**: take a repo with no docs-keeper state to a green baseline —
**create** the config file (`.docs-keeper/config.json`), create the host root prompt if
absent, build `index.md` indexes across the docs, and **create** the "Sources of truth"
registry section. Afterwards the `config` / `index` / `revise` / `registry-sync` commands
(and the commit-time gate) maintain everything. Mode E.

> Platform-neutral procedure. The Claude Code adapter exposes it as `/docs-keeper:setup [doc-root ...]`.

## Pre-flight (binding)

Inherited from [`../role.md`](../role.md):

1. **Non-overwrite policy** § — `Write` only creates absent files; edits to an existing
   host root prompt are surgical/additive (never clobber, never reorder unrelated lines).
2. **Host authoring rules** § — load and honor; never inject rules into the host.
3. **YAML front-matter quoting** § — single-quote `intro`; quote anchor-bearing `title`.
4. **README classification** § — content-bearing vs legacy-navigation.

## When to use

Right after installing docs-keeper in a repo that has **no `index.md` files** and/or **no
"Sources of truth" registry**. `registry-sync` deliberately refuses to create the section
from nothing (it halts and asks) — `setup` is the command that performs that cold start.
Idempotent: re-running on an already-green repo makes no changes.

## Scope

`setup [doc-root ...]` — optional path args limit indexing to those roots; with no args,
the scope is the whole repo from its root. The **set of files indexed** is governed by the
config `paths` globs (default `["**/*.md"]`, established in step 1); `[doc-root ...]` further
narrows *which directories* this run touches. Files outside `paths` are ignored.

## Steps

1. **Establish config (cold start).** Reuse the **`config`** procedure
   ([`config.md`](config.md)): show the current settings (`--get`). If
   `.docs-keeper/config.json` is **absent**, initialize it through the config entrypoint with
   the defaults — `enforcement` and `paths: ["**/*.md"]` — so the repo's settings are explicit
   and committable. If it already **exists**, do not overwrite; read it. The resulting `paths`
   globs determine which files steps 3-4 index. When the file was created cold (defaults
   applied), the report MUST surface those defaults and how to change them — see step 7's
   *Defaults notice*.
2. **Locate or create the host root prompt.** Probe `CLAUDE.md` → `AGENTS.md` →
   `.agent/INDEX.md`. If none exists, **create `CLAUDE.md`** with a minimal skeleton: an
   H1 title and an empty `## Sources of truth` section. Record the create in the report.
3. **Index the docs.** For each scope root, run the **`index`** procedure
   ([`index.md`](index.md)) — recursive-descent `children:` + ancestor walk-up — writing
   each `index.md`, honoring the configured `paths` globs from step 1. Skip a root that
   already has an up-to-date `index.md` (idempotent). Take the `children:` set from the engine
   (`cli.py --emit-children <dir>`, per index.md § *Deterministic `children:`*) — do NOT
   free-hand it, and do NOT introduce sub-indexes here (a single index per scope root; splitting
   is a later, explicit `index <sub>/` operation). This keeps the baseline reproducible.
4. **Seed the registry (cold start).** Build the coverage map and identify ROOT indexes +
   uncovered unique docs per **`registry-sync`** § *Registry membership rule*. If the
   "Sources of truth" section is **absent**, create it and populate the bullet list. If it
   already **exists**, do not recreate — hand off to `registry-sync` to reconcile.
5. **Authoring rules — report only.** Per role.md § *Host authoring rules*, report whether
   host rules were found. If none, note that the bundled fallback
   ([`../conventions/index-authoring.md`](../conventions/index-authoring.md)) applies. Do
   NOT add authoring rules to the host.
6. **Verify green (binding).** Setup's contract is a green baseline. Run the drift gate
   (`cli.py --drift-only`); if it reports any `index <dir>/` or `registry-sync` drift, apply the
   named fix (re-emit that dir's `children:`, reconcile the registry) and re-run the gate. Repeat
   until it exits clean. Setup MUST NOT report success while the gate still reports drift.
7. **Report.** List the config file (created vs already present), created `index.md` files,
   the registry section (created vs already present), the host prompt (created vs existing),
   the authoring-rules status, and the final drift-gate result (must be clean). When the
   config was created cold, also emit the *Defaults notice* (below).

## Chaining

- Step 1 reuses `config` (create-mode for a missing file, read-mode otherwise); step 3
  reuses `index`; step 4 reuses `registry-sync` (create-mode for a missing section,
  reconcile-mode otherwise).
- After `setup`, ongoing maintenance is the commit-time drift gate plus
  `config` / `index` / `revise` / `sweep` / `registry-sync`.

## Report (binding)

Use the **Documentation Report** ([`../templates/_output-template.md`](../templates/_output-template.md)),
Mode = E. Slots: config file (created / existing) + effective `paths`, created `index.md`
files (with walk-up trace), registry section (created / synced), host root prompt
(created / existing), authoring-rules status.

### Defaults notice (cold start only — binding)

Emit ONLY when step 1 created `.docs-keeper/config.json` from defaults (skip when the file
already existed). Echo the **actual values written** (read them back via the config `--get`),
do not hard-code them. Tell the user, plainly:

- **Applied defaults.** `enforcement: <value>` · `paths: <globs>`.
- **How to change.** Either run the config command (preferred — it validates and canonicalizes
  the file):
  - `/docs-keeper:config enforcement <warn|block>`
  - `/docs-keeper:config paths <glob> [<glob> ...]` — pass the FULL list; the array is replaced.

  …or hand-edit `.docs-keeper/config.json` directly (keep it valid JSON; same keys/values —
  `enforcement` ∈ {`warn`,`block`}, `paths` an array of globs). The command path is recommended
  because it rejects invalid values.
- **Then reindex.** After changing `paths`, re-run `/docs-keeper:index` (or `/docs-keeper:setup`)
  so the indexes reflect the new scope. An `enforcement`-only change needs no reindex.
