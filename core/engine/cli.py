"""
docs-keeper core engine — neutral CLI.

Platform-independent drift gate for CI on any repo / agent platform. Computes
index + registry drift and exits 0 (clean) or 2 (drift; message on stderr).
No hook payload, no platform host required.

    python3 core/engine/cli.py --drift-only [--repo-root <path>] [--enforce warn|block]

Runnable as a module (`python3 -m core.engine.cli`) or by path; import works
either way via the fallback below.
"""

import argparse
import os
import sys

try:  # package context (python3 -m core.engine.cli, or the vendored _engine package)
    from .config import get_enforcement_setting, get_index_globs, load_config
    from .drift import format_block_message, get_docs_drift_queue, get_expected_children, resolve_enforcement_mode
    from .gitio import make_dir_lister, make_file_reader, resolve_repo_root_from_git
except ImportError:  # script context (python3 <…>/cli.py) — flat sibling import, location-independent
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import get_enforcement_setting, get_index_globs, load_config
    from drift import format_block_message, get_docs_drift_queue, get_expected_children, resolve_enforcement_mode
    from gitio import make_dir_lister, make_file_reader, resolve_repo_root_from_git


def run_drift_only(repo_root: str, enforcement_mode: str, index_globs=None) -> int:
    """Compute drift and return the exit code; prints the message to stderr."""
    dir_lister = make_dir_lister(repo_root)
    file_reader = make_file_reader(repo_root)
    queue = get_docs_drift_queue(dir_lister, file_reader, index_globs=index_globs)
    if not queue:
        return 0
    mode = resolve_enforcement_mode(enforcement_mode)
    msg = format_block_message(queue, standalone=True, mode=mode)
    print(msg, file=sys.stderr)
    return 0 if mode == "warn" else 2


def run_emit_children(repo_root: str, target_dir: str, index_globs=None) -> int:
    """
    Print the authoritative `children:` entries for target_dir's index.md, one
    per line — the SAME deterministic recursive descent the drift gate checks.

    Lets the index/setup procedures build a `children:` set that matches the gate
    by construction (no hand-enumeration), so the result is reproducible.
    """
    normalized = (target_dir or ".").rstrip("/") or "."
    dir_lister = make_dir_lister(repo_root)
    for entry in get_expected_children(normalized, dir_lister, index_globs=index_globs):
        print(entry)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="docs-keeper neutral drift gate.")
    parser.add_argument("--drift-only", action="store_true", help="Index + registry drift check only.")
    parser.add_argument(
        "--emit-children",
        metavar="DIR",
        default="",
        help="Print the deterministic children entries for DIR's index.md (one per line) and exit.",
    )
    parser.add_argument("--repo-root", default="", help="Repo working tree (default: git root / cwd).")
    parser.add_argument(
        "--enforce",
        default="",
        help="Enforcement: 'warn' (exit 0) or 'block' (exit 2 on drift). "
        "Defaults to the 'enforcement' setting in .docs-keeper/config.json, else 'block'.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root or resolve_repo_root_from_git() or os.getcwd()
    config = load_config(make_file_reader(repo_root))
    enforcement_mode = args.enforce or get_enforcement_setting(config)
    index_globs = get_index_globs(config)

    if args.emit_children:
        sys.exit(run_emit_children(repo_root, args.emit_children, index_globs))

    if args.drift_only:
        sys.exit(run_drift_only(repo_root, enforcement_mode, index_globs))

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
