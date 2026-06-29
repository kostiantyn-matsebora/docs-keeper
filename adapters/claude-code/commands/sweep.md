---
description: Cross-doc consistency sweep — verify every sources-of-truth entry, walk every index.md children list, flag orphans + broken links + legacy-navigation READMEs, hand off drift. Mode C of docs-keeper.
argument-hint: "[optional-scope-path]"
---

# /docs-keeper:sweep

Cross-doc consistency sweep over `$ARGUMENTS` (defaults to repo root). Read-only.

Read and follow the bundled procedure **in full**:
[`spec/commands/sweep.md`](${CLAUDE_PLUGIN_ROOT}/spec/commands/sweep.md).
Report via the bundled Documentation Report template, Mode C.

First resolve the effective `paths` globs (default applied) — they define which files are
indexed and which extensions children resolve against:

```
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_engine/cli.py" --emit-globs --repo-root "${CLAUDE_PROJECT_DIR}"
```
