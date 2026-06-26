"""
Surface a headless Claude Code session error from its `--output-format json`
result so a workflow step fails fast (with the real message) instead of letting
a masked `claude` failure show up only as a downstream assertion.

A `claude -p ... --output-format json` run prints one JSON object whose
`is_error` flag and `result`/`api_error_status` fields describe auth failures
(401), permission denials, etc. `session_error` extracts a human message;
`main()` exits 1 with a `::error::` annotation when one is present, else 0.
"""

import json
import sys


def session_error(raw: str) -> str:
    """Return a human-readable error string for a failed session, else ''."""
    if not raw or not raw.strip():
        return ""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return ""  # non-JSON output (e.g. CLI start failure) — let asserts catch it
    if not isinstance(data, dict) or not data.get("is_error"):
        return ""
    message = str(data.get("result") or "session error")
    status = data.get("api_error_status")
    return f"{message} (HTTP {status})" if status else message


def main() -> None:
    raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    err = session_error(raw)
    if err:
        print(f"::error::headless claude session failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
