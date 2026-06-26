"""
docs-keeper core engine — repo configuration file (platform-neutral).

Reads `.docs-keeper/config.json`, the per-repo settings file. Unlike the rest
of `.docs-keeper/` — per-machine runtime state that is gitignored — config.json
is *source*: committed and shared across the team.

Pure: I/O is delegated to an injected `file_reader(rel_path) -> str` ('' when
absent), the same collaborator the drift engine consumes. The first setting is
`enforcement` (`warn` | `block`); resolve it through
`drift.resolve_enforcement_mode(get_enforcement_setting(config))`.
"""

import json

# Repo-relative path; config.json sits beside the runtime state but is committed.
CONFIG_REL_PATH = ".docs-keeper/config.json"


def load_config(file_reader) -> dict:
    """
    Parse `.docs-keeper/config.json` via file_reader. Returns the settings dict,
    or {} when the file is missing, empty, or not a valid JSON object.
    """
    raw = file_reader(CONFIG_REL_PATH)
    if not raw or not raw.strip():
        return {}
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def get_enforcement_setting(config: dict) -> str:
    """Return the raw `enforcement` string from config ('' when unset)."""
    value = config.get("enforcement") if isinstance(config, dict) else None
    return str(value) if value is not None else ""
