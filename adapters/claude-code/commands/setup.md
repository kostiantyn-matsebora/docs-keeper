---
description: Bootstrap docs-keeper in this repo — create the host root prompt if absent, build index.md indexes across the docs, and create the Sources-of-truth registry. One-time cold start. Mode E of docs-keeper.
argument-hint: "[doc-root ...]"
---

# /docs-keeper:setup

Bring this repo to a green docs-keeper baseline. Scope = `$ARGUMENTS` (optional doc roots;
default = the whole repo from its root).

Read and follow the bundled procedure **in full**:
[`spec/commands/setup.md`](${CLAUDE_PLUGIN_ROOT}/spec/commands/setup.md).
Honor the pre-flight gates in [`spec/role.md`](${CLAUDE_PLUGIN_ROOT}/spec/role.md)
(Non-overwrite policy · Host authoring rules · YAML quoting · README classification).
Report via the bundled Documentation Report template, Mode E.
