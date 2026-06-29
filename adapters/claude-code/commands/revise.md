---
description: Revise an existing doc or author a new one against host authoring rules. Extract over compact for files >200 lines. Mode B of docs-keeper. Without a path, targets all uncommitted doc files.
argument-hint: "[doc-path] [-- brief]"
---

# /docs-keeper:revise

Revise or author the resolved target doc(s) (`$ARGUMENTS`; empty → all uncommitted doc files
matching the config `paths` globs).

Read and follow the bundled procedure **in full**:
[`spec/commands/revise.md`](${CLAUDE_PLUGIN_ROOT}/spec/commands/revise.md).
Honor the pre-flight gates in [`spec/role.md`](${CLAUDE_PLUGIN_ROOT}/spec/role.md).

When resolving targets with no path argument, get the effective `paths` globs (default applied)
and filter the uncommitted file set to them:

```
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/_engine/cli.py" --emit-globs --repo-root "${CLAUDE_PROJECT_DIR}"
```
