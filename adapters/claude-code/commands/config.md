---
description: View or change docs-keeper's per-repo settings in .docs-keeper/config.json — enforcement (warn|block) and the paths globs docs-keeper watches and indexes.
argument-hint: "[get | enforcement <warn|block> | paths <glob ...>]"
---

# /docs-keeper:config

View or change docs-keeper settings (`.docs-keeper/config.json`). Requested change = `$ARGUMENTS`
(empty → just show the current config).

Read and follow the bundled procedure **in full**:
[`spec/commands/config.md`](${CLAUDE_PLUGIN_ROOT}/spec/commands/config.md).

Always show the current config first, then apply changes via the bundled config entrypoint
(never hand-edit the JSON):

```
# view
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/cc_config.py" --get

# set enforcement
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/cc_config.py" --set enforcement warn

# set the watch/index globs (replaces the whole array)
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/cc_config.py" --set paths "docs/**/*.md" "adr/**/*.md"
```

Invalid values exit non-zero with the reason on stderr; surface it and leave the file unchanged.
