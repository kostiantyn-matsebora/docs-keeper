"""
docs-keeper end-to-end assertions (platform-neutral, stdlib-only).

Black-box checks the `.github/workflows/e2e.yml` job runs against a *host*
repository after each phase of the e2e: plugin install, `setup`, and the
drift-sync cycle. Kept separate from the engine's own pytest suites — those
test the engine in isolation; this asserts observable outcomes on a real repo
the agent has operated on (config file written, indexes built, host registry
section present, a doc declared in its index).

Pure helpers (parsing / discovery) are importable and unit-tested by the
sibling `assert_e2e_test.py`; `main()` wires them to a real path and exits
0 (pass) / 1 (fail) with a human-readable PASS/FAIL line per check, so a
failing phase fails the workflow step.
"""

import argparse
import json
import os
import re
import sys

# Commands the installed Claude Code plugin must expose (bare names).
EXPECTED_COMMANDS = ("capture", "config", "index", "registry-sync", "revise", "setup", "sweep")
# Hook events the adapter wires up; a subset asserted as "installed correctly".
EXPECTED_HOOK_EVENTS = ("SessionStart", "PreToolUse", "Stop")
# Host root-prompt candidates, in the engine's probe order.
HOST_PROMPT_CANDIDATES = ("CLAUDE.md", "AGENTS.md", ".agent/INDEX.md")
# Directories never descended when discovering index.md files.
EXCLUDE_DIRS = frozenset(
    {"node_modules", "dist", "build", "bin", "obj", "vendor", "out", ".next", ".nuxt", "coverage", "target", ".git"}
)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------


def read_text(path: str) -> str:
    """Return file contents, or '' when the file is absent/unreadable."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def validate_config(raw: str) -> list[str]:
    """
    Validate a `.docs-keeper/config.json` body. Returns a list of error strings
    (empty == valid): must parse to an object, `enforcement` in {warn, block},
    `paths` a non-empty list of non-blank strings.
    """
    errors: list[str] = []
    if not raw or not raw.strip():
        return ["config.json missing or empty"]
    try:
        cfg = json.loads(raw)
    except (ValueError, TypeError):
        return ["config.json is not valid JSON"]
    if not isinstance(cfg, dict):
        return ["config.json is not a JSON object"]
    enforcement = cfg.get("enforcement")
    if enforcement not in ("warn", "block"):
        errors.append(f"enforcement must be 'warn' or 'block', got {enforcement!r}")
    paths = cfg.get("paths")
    if not isinstance(paths, list) or not [p for p in paths if isinstance(p, str) and p.strip()]:
        errors.append("paths must be a non-empty list of glob strings")
    return errors


def has_registry_section(text: str) -> bool:
    """
    Return True when text contains a "Sources of truth" (or "authoritative")
    heading — the host registry section `setup` seeds. Mirrors the engine's
    heading match so the assertion tracks the product.
    """
    if not text or not text.strip():
        return False
    for line in re.split(r"\r?\n", text):
        if re.match(r"^#{1,6}\s", line) and re.search(r"(?i)sources?\s+of\s+truth|authoritative", line):
            return True
    return False


def find_index_files(root: str) -> list[str]:
    """Return absolute paths of every index.md under root (excluding hidden/build dirs)."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in EXCLUDE_DIRS]
        if "index.md" in filenames:
            found.append(os.path.join(dirpath, "index.md"))
    return sorted(found)


def parse_declared_children(index_text: str) -> list[str]:
    """Parse the `children:` YAML front-matter list from an index.md body."""
    if not index_text or not index_text.strip():
        return []
    children: list[str] = []
    fm_delimiters = 0
    in_children = False
    for line in re.split(r"\r?\n", index_text):
        if re.match(r"^---\s*$", line):
            fm_delimiters += 1
            if fm_delimiters >= 2:
                break
            continue
        if fm_delimiters != 1:
            continue
        if re.match(r"^children:\s*$", line):
            in_children = True
            continue
        if in_children:
            m = re.match(r"^\s+-\s+(\S+)\s*$", line)
            if m:
                children.append(m.group(1))
            elif re.match(r"^\S", line):
                in_children = False
    return children


def find_host_prompt(repo: str) -> str:
    """Return the path of the first present host root-prompt candidate, else ''."""
    for candidate in HOST_PROMPT_CANDIDATES:
        path = os.path.join(repo, candidate)
        if read_text(path).strip():
            return path
    return ""


# ---------------------------------------------------------------------------
# Phase checks (return list of (ok, message) tuples)
# ---------------------------------------------------------------------------


def check_install(plugin_root: str) -> list[tuple]:
    """Assert the assembled Claude Code plugin ships every expected asset."""
    results: list[tuple] = []

    manifest_path = os.path.join(plugin_root, ".claude-plugin", "plugin.json")
    manifest_raw = read_text(manifest_path)
    manifest = {}
    try:
        manifest = json.loads(manifest_raw) if manifest_raw else {}
    except (ValueError, TypeError):
        manifest = {}
    results.append((manifest.get("name") == "docs-keeper", f"plugin.json name == docs-keeper ({manifest_path})"))
    results.append((bool(manifest.get("hooks")), "plugin.json declares a hooks entry"))

    hooks_raw = read_text(os.path.join(plugin_root, "hooks", "hooks.json"))
    hooks_doc = {}
    try:
        hooks_doc = json.loads(hooks_raw) if hooks_raw else {}
    except (ValueError, TypeError):
        hooks_doc = {}
    # Claude Code requires the event map wrapped under a top-level "hooks" key;
    # a bare event map fails to load (see TEST_CASES.md § Findings F1).
    has_wrapper = isinstance(hooks_doc, dict) and isinstance(hooks_doc.get("hooks"), dict)
    results.append((has_wrapper, 'hooks.json wraps events under a top-level "hooks" key'))
    events = hooks_doc.get("hooks") if has_wrapper else {}
    for event in EXPECTED_HOOK_EVENTS:
        results.append((event in events, f"hooks.json wires {event}"))

    results.append(
        (bool(read_text(os.path.join(plugin_root, "agents", "docs-keeper.md")).strip()), "agents/docs-keeper.md present")
    )
    for cmd in EXPECTED_COMMANDS:
        path = os.path.join(plugin_root, "commands", f"{cmd}.md")
        results.append((bool(read_text(path).strip()), f"commands/{cmd}.md present"))

    # Vendored engine + spec must have been assembled into the plugin root.
    results.append(
        (os.path.isfile(os.path.join(plugin_root, "hooks", "_engine", "drift.py")), "vendored hooks/_engine/drift.py present")
    )
    results.append((os.path.isfile(os.path.join(plugin_root, "spec", "role.md")), "vendored spec/role.md present"))
    return results


def check_setup(repo: str) -> list[tuple]:
    """Assert `setup` reached a green baseline: config + indexes + host registry."""
    results: list[tuple] = []

    config_errors = validate_config(read_text(os.path.join(repo, ".docs-keeper", "config.json")))
    results.append((not config_errors, ".docs-keeper/config.json created and valid" + (f" — {config_errors}" if config_errors else "")))

    indexes = find_index_files(repo)
    results.append((len(indexes) >= 1, f"at least one index.md built ({len(indexes)} found)"))

    host = find_host_prompt(repo)
    results.append((bool(host), f"host root prompt present ({os.path.basename(host) if host else 'none'})"))
    results.append((has_registry_section(read_text(host)) if host else False, "host has a 'Sources of truth' section"))
    return results


def check_index_declares(index_path: str, child: str) -> list[tuple]:
    """Assert a specific child slug is declared in an index.md's front-matter."""
    declared = parse_declared_children(read_text(index_path))
    return [(child in declared, f"{index_path} declares child {child!r} (declared: {declared})")]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def report(phase: str, results: list[tuple]) -> int:
    """Print PASS/FAIL per check; return 0 when all passed, else 1."""
    failed = 0
    print(f"== e2e assert: {phase} ==")
    for ok, message in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {message}")
        if not ok:
            failed += 1
    print(f"-- {len(results) - failed}/{len(results)} checks passed --")
    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="docs-keeper end-to-end phase assertions.")
    sub = parser.add_subparsers(dest="phase", required=True)

    p_install = sub.add_parser("install", help="Assert the assembled plugin ships every asset.")
    p_install.add_argument("--plugin-root", required=True, help="Path to the Claude Code adapter root.")

    p_setup = sub.add_parser("setup", help="Assert setup reached a green baseline.")
    p_setup.add_argument("--repo", required=True, help="Path to the host repo setup ran against.")

    p_decl = sub.add_parser("index-declares", help="Assert an index.md declares a child slug.")
    p_decl.add_argument("--index", required=True, help="Path to the index.md to inspect.")
    p_decl.add_argument("--child", required=True, help="Child slug expected in children: (e.g. /payments).")

    args = parser.parse_args()

    if args.phase == "install":
        sys.exit(report("install", check_install(args.plugin_root)))
    if args.phase == "setup":
        sys.exit(report("setup", check_setup(args.repo)))
    if args.phase == "index-declares":
        sys.exit(report("index-declares", check_index_declares(args.index, args.child)))


if __name__ == "__main__":
    main()
