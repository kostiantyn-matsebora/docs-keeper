# setup — procedure

One-time **bootstrap**: take a repo with no docs-keeper state to a green baseline —
create the host root prompt if absent, build `index.md` indexes across the docs, and
**create** the "Sources of truth" registry section. Afterwards the `index` / `revise` /
`registry-sync` commands (and the commit-time gate) maintain everything. Mode E.

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
the scope is the whole repo from its root. Only Markdown (`.md`) files are indexed
(role.md § *Index convention*); non-Markdown is ignored.

## Steps

1. **Locate or create the host root prompt.** Probe `CLAUDE.md` → `AGENTS.md` →
   `.agent/INDEX.md`. If none exists, **create `CLAUDE.md`** with a minimal skeleton: an
   H1 title and an empty `## Sources of truth` section. Record the create in the report.
2. **Index the docs.** For each scope root, run the **`index`** procedure
   ([`index.md`](index.md)) — recursive-descent `children:` + ancestor walk-up — writing
   each `index.md`. Skip a root that already has an up-to-date `index.md` (idempotent).
3. **Seed the registry (cold start).** Build the coverage map and identify ROOT indexes +
   uncovered unique docs per **`registry-sync`** § *Registry membership rule*. If the
   "Sources of truth" section is **absent**, create it and populate the bullet list. If it
   already **exists**, do not recreate — hand off to `registry-sync` to reconcile.
4. **Authoring rules — report only.** Per role.md § *Host authoring rules*, report whether
   host rules were found. If none, note that the bundled fallback
   ([`../conventions/index-authoring.md`](../conventions/index-authoring.md)) applies. Do
   NOT add authoring rules to the host.
5. **Report.** List created `index.md` files, the registry section (created vs already
   present), the host prompt (created vs existing), and the authoring-rules status.

## Chaining

- Step 2 reuses `index`; step 3 reuses `registry-sync` (in create-mode for a missing
  section, reconcile-mode otherwise).
- After `setup`, ongoing maintenance is the commit-time drift gate plus
  `index` / `revise` / `sweep` / `registry-sync`.

## Report (binding)

Use the **Documentation Report** ([`../templates/_output-template.md`](../templates/_output-template.md)),
Mode = E. Slots: created `index.md` files (with walk-up trace), registry section
(created / synced), host root prompt (created / existing), authoring-rules status.
