---
title: docs-keeper
description: "A documentation steward for Claude Code — builds your indexes, keeps a sources-of-truth registry, and catches doc drift at commit time."
permalink: /
---

# docs-keeper

[![Release](https://img.shields.io/github/v/release/kostiantyn-matsebora/docs-keeper?label=release&color=0f7a45)](https://github.com/kostiantyn-matsebora/docs-keeper/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/kostiantyn-matsebora/docs-keeper/ci.yml?branch=master&label=CI)](https://github.com/kostiantyn-matsebora/docs-keeper/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-0f7a45)](https://github.com/kostiantyn-matsebora/docs-keeper/blob/master/LICENSE)

A **documentation steward** for Claude Code. docs-keeper builds your per-directory indexes, keeps
a "sources of truth" registry in sync, and **catches documentation drift at commit time** — so
your docs never silently fall out of step with the code. It installs as a Claude Code plugin (an
agent + `/docs-keeper:*` commands + hooks).

<ul class="features">
  <li>🗂️ <strong>Indexes</strong> — per-directory <code>index.md</code> files, built and kept current incrementally (never a full rebuild).</li>
  <li>🛡️ <strong>Drift gate</strong> — blocks (or warns on) a <code>git commit</code> when docs drift; tells you exactly what to fix.</li>
  <li>📒 <strong>Registry</strong> — keeps the host prompt's "Sources of truth" section in sync.</li>
  <li>🎯 <strong>Deterministic</strong> — indexes are computed by the engine, so the same tree always yields the same result.</li>
</ul>

---

## Install

docs-keeper is distributed from its GitHub repo as a single-plugin marketplace. In Claude Code:

```
/plugin marketplace add kostiantyn-matsebora/docs-keeper
/plugin install docs-keeper@docs-keeper
```

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

The engine ships a host-neutral drift gate you can run in any CI:

```
python3 core/engine/cli.py --drift-only [--repo-root <path>] [--enforce warn|block]
```

Exit `0` (clean) or `2` (drift; message on stderr).

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
