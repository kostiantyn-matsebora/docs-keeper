"""
docs-keeper core engine — drift detection (platform-neutral).

Pure functions only: index/children computation, registry checks, the
revise/index/registry-sync command queue, and the neutral commit-time
maintenance evaluation. NO host-specific payload field names, hook
decision verbs, or plugin-root references live here — adapters translate
their host's payload into the calls below.

Collaborators (`dir_lister`, `file_reader`, git output) are injected as
plain callables / strings so the whole module is testable with fakes.
"""

import hashlib
import json
import re

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

EXCLUDE_DIRS_DEFAULT = frozenset(
    {"node_modules", "dist", "build", "bin", "obj", "vendor", "out", ".next", ".nuxt", "coverage", "target"}
)

# Default watch/index scope: every Markdown file at any depth. Overridable via
# the `paths` glob list in .docs-keeper/config.json (config.get_index_globs).
INDEX_GLOBS_DEFAULT = ("**/*.md",)

# Neutral binding-gates reference. Adapters may override with a host-specific
# path (e.g. the installed plugin's agent file) via format_block_message.
BINDING_GATES_REF = "Binding gates: docs-keeper role spec sections Non-overwrite policy + Hard rules."


# ---------------------------------------------------------------------------
# Payload helpers (host-neutral: plain JSON + a generic session id)
# ---------------------------------------------------------------------------


def read_hook_payload(json_str: str) -> dict | None:
    """Parse a JSON payload string; return None on empty/invalid."""
    if not json_str or not json_str.strip():
        return None
    try:
        return json.loads(json_str)
    except (ValueError, TypeError):
        return None


def get_session_id_from_payload(payload: dict | None) -> str:
    """Extract session_id from a parsed payload; return '' when absent."""
    if payload and isinstance(payload, dict) and payload.get("session_id"):
        return str(payload["session_id"])
    return ""


def get_safe_session_id(session_id: str) -> str:
    """
    Sanitize a session id for use in a filename: keep [A-Za-z0-9._-],
    collapse anything else to '_'. Empty / whitespace -> ''.
    """
    if not session_id or not session_id.strip():
        return ""
    return re.sub(r"[^A-Za-z0-9._-]", "_", session_id)


# ---------------------------------------------------------------------------
# Git parsing
# ---------------------------------------------------------------------------


def is_git_commit(command: str) -> bool:
    """
    Return True when command contains `git ... commit` (word boundary match).

    Accepts flags between `git` and `commit` (e.g. git -C /repo commit).
    Must be preceded by start-of-string, whitespace, &, ; or |.
    The word 'commit' must be followed by end-of-string, whitespace, or flags
    — prevents matching `git commit-tree` / `git commit-graph`.
    """
    if not command or not command.strip():
        return False
    return bool(re.search(r"(^|[\s;&|])git(\s+-[A-Za-z]+(\s+\S+)?)*\s+commit($|[\s])", command))


def convert_git_name_status(name_status: str) -> list[dict]:
    """
    Parse `git diff --name-status -M` output into a list of change dicts.

    Each dict has keys: status, path, old_path (may be None).
    """
    if not name_status or not name_status.strip():
        return []
    changes = []
    for line in re.split(r"\r?\n", name_status):
        if not line.strip():
            continue
        parts = line.split("\t")
        raw_status = parts[0]
        if re.match(r"^[RC]\d*$", raw_status) and len(parts) >= 3:
            changes.append({"status": raw_status[0], "old_path": parts[1], "path": parts[2]})
        elif len(parts) >= 2:
            changes.append({"status": raw_status, "path": parts[1], "old_path": None})
    return changes


def is_markdown_path(path: str | None) -> bool:
    """Return True when path ends with .md (case-sensitive)."""
    if not path:
        return False
    return path.endswith(".md")


def _glob_to_regex(pattern: str) -> str:
    """
    Translate a path glob into an anchored regex string (POSIX `/` separators).

    Supports `**/` (zero or more path segments), `**` (anything), `*` (anything
    within a segment), and `?` (one non-separator char). Everything else is a
    literal.
    """
    i, n, out = 0, len(pattern), []
    while i < n:
        if pattern[i] == "*":
            if pattern[i:i + 2] == "**":
                if pattern[i:i + 3] == "**/":
                    out.append("(?:[^/]+/)*")  # zero or more whole path segments
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")  # within a single path segment
                i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return "(?s:" + "".join(out) + r")\Z"


def path_matches_globs(path: str | None, index_globs: tuple | list | None = None) -> bool:
    """
    Return True when path matches any of index_globs (default INDEX_GLOBS_DEFAULT).

    This is the single watch/index membership test: a repo-relative path is
    "indexed content" iff it matches a configured glob. A leading `./` is ignored.
    """
    if not path:
        return False
    globs = index_globs or INDEX_GLOBS_DEFAULT
    candidate = path[2:] if path.startswith("./") else path
    return any(re.match(_glob_to_regex(p), candidate) for p in globs)


def touches_indexed_content(changes: list[dict], index_globs: tuple | list | None = None) -> bool:
    """Return True when any change record involves a watched/indexed file."""
    for change in changes:
        for p in (change.get("path"), change.get("old_path")):
            if path_matches_globs(p, index_globs):
                return True
    return False


# ---------------------------------------------------------------------------
# Discovery + drift
# ---------------------------------------------------------------------------


def is_hidden_name(name: str) -> bool:
    """Return True for dot- or underscore-prefixed names."""
    return name.startswith(".") or name.startswith("_")


def find_host_root_prompt_file(file_reader) -> str:
    """
    Return the first non-empty candidate host prompt file path.

    Candidates in order: CLAUDE.md, AGENTS.md, .agent/INDEX.md.
    """
    for candidate in ("CLAUDE.md", "AGENTS.md", ".agent/INDEX.md"):
        content = file_reader(candidate)
        if content and content.strip():
            return candidate
    return ""


def _index_entry_slug(name: str) -> str:
    """Drop the final extension for the index child slug (foo.md -> foo)."""
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def get_expected_children(
    dir_path: str, dir_lister, prefix: str = "", index_globs: tuple | list | None = None
) -> list[str]:
    """
    Compute the expected children entries for a docs-keeper index directory.

    Only files matching index_globs (default INDEX_GLOBS_DEFAULT, i.e. *.md) are
    indexed; non-matching files are ignored.

    Rules:
    - Hidden/underscore entries are skipped.
    - Sub-directory WITH index.md -> single boundary entry "/<prefix><name>".
    - Sub-directory WITHOUT index.md -> recurse, prefixing names.
    - index.md file itself -> skipped.
    - Matching files -> "/<prefix><basename>" (extension stripped).
    - Non-matching files -> skipped.

    Entries are returned in a deterministic lexical order (sorted by Unicode code
    point) so the emitted index is identical across platforms regardless of the
    underlying filesystem's directory-iteration order.
    """
    entries = []
    for entry in dir_lister(dir_path):
        name = entry["name"]
        if is_hidden_name(name):
            continue
        if entry["is_dir"]:
            child_dir = name if dir_path == "." else f"{dir_path}/{name}"
            child_listing = dir_lister(child_dir)
            has_index = any(e["name"] == "index.md" for e in child_listing)
            if has_index:
                entries.append(f"/{prefix}{name}")
            else:
                entries.extend(get_expected_children(child_dir, dir_lister, f"{prefix}{name}/", index_globs))
        else:
            if name == "index.md":
                continue
            file_path = name if dir_path == "." else f"{dir_path}/{name}"
            if path_matches_globs(file_path, index_globs):
                entries.append(f"/{prefix}{_index_entry_slug(name)}")
            # Non-matching files are not indexed.
    return sorted(entries)


def get_declared_children(content: str) -> list[str]:
    """
    Parse the YAML front-matter children: block list from an index.md.

    Returns items exactly as declared (order preserved, set comparison later).
    """
    if not content or not content.strip():
        return []
    children = []
    fm_delimiters = 0
    in_children = False
    for line in re.split(r"\r?\n", content):
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


def sets_equal(a: list, b: list) -> bool:
    """Return True when a and b contain the same elements (order-insensitive)."""
    return set(a) == set(b)


def get_index_dirs(dir_path: str, dir_lister, exclude_dirs: frozenset | set = EXCLUDE_DIRS_DEFAULT) -> list[str]:
    """
    Recursively find all directories that contain an index.md.

    Hidden directories and those in exclude_dirs are skipped.
    """
    result = []
    listing = dir_lister(dir_path)
    if any(e["name"] == "index.md" for e in listing):
        result.append(dir_path)
    for entry in listing:
        if not entry["is_dir"]:
            continue
        name = entry["name"]
        if is_hidden_name(name):
            continue
        if name in exclude_dirs:
            continue
        child_path = name if dir_path == "." else f"{dir_path}/{name}"
        result.extend(get_index_dirs(child_path, dir_lister, exclude_dirs))
    return result


def get_root_index_dirs(index_dirs: list[str]) -> list[str]:
    """
    Return the subset of index_dirs whose parent directory is NOT itself an index dir.

    These are the ROOT index directories for registry checking.
    """
    dir_set = set(index_dirs)
    roots = []
    for d in index_dirs:
        m = re.match(r"^(.*)/[^/]+$", d)
        parent = m.group(1) if m else ""
        if parent not in dir_set:
            roots.append(d)
    return roots


def registry_needle(dir_path: str) -> str:
    """
    The substring that identifies an index dir's entry in the registry section.

    Sub-dir indexes are referenced by their directory path (`docs/`); the
    repo-root index (dir `.` / '') has no `./`-style path in a natural bullet —
    its registry entry links the root index file, so match `index.md`.
    """
    if dir_path in ("", "."):
        return "index.md"
    return dir_path if dir_path.endswith("/") else f"{dir_path}/"


def check_registry_has_entry(content: str, dir_path: str) -> bool:
    """
    Return True when dir_path's entry appears in the "Sources of truth" section.

    Named check_ (not test_) so pytest does not collect it as a fixture.
    """
    if not content or not content.strip():
        return False
    needle = registry_needle(dir_path)
    in_section = False
    for line in re.split(r"\r?\n", content):
        if re.match(r"^#{1,6}\s", line):
            in_section = bool(re.search(r"(?i)sources?\s+of\s+truth|authoritative", line))
            continue
        if in_section and needle in line:
            return True
    return False


def check_registry_role_in_sync(content: str, dir_path: str, intro: str) -> bool:
    """
    Return True when the registry line for dir_path also contains intro.

    If intro is empty, returns True (nothing to verify).
    Named check_ (not test_) so pytest does not collect it as a fixture.
    """
    if not intro:
        return True
    if not content or not content.strip():
        return False
    needle = registry_needle(dir_path)
    in_section = False
    for line in re.split(r"\r?\n", content):
        if re.match(r"^#{1,6}\s", line):
            in_section = bool(re.search(r"(?i)sources?\s+of\s+truth|authoritative", line))
            continue
        if in_section and needle in line:
            return intro in line
    return False


# ---------------------------------------------------------------------------
# Mode B (revise) helpers
# ---------------------------------------------------------------------------


def get_content_sha(content: str | None) -> str:
    """Return the SHA-256 hex digest of content (UTF-8 encoded)."""
    if content is None:
        content = ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_intro_from_front_matter(content: str) -> str:
    """
    Extract the `intro:` value from YAML front-matter.

    Strips surrounding single or double quotes; returns '' when absent.
    """
    if not content or not content.strip():
        return ""
    fm_delimiters = 0
    for line in re.split(r"\r?\n", content):
        if re.match(r"^---\s*$", line):
            fm_delimiters += 1
            if fm_delimiters >= 2:
                break
            continue
        if fm_delimiters != 1:
            continue
        m = re.match(r"^intro:\s*(.+?)\s*$", line)
        if m:
            val = m.group(1)
            if re.match(r"^'(.*)'$", val):
                return re.match(r"^'(.*)'$", val).group(1)
            if re.match(r'^"(.*)"$', val):
                return re.match(r'^"(.*)"$', val).group(1)
            return val
    return ""


def resolve_revise_queue(paths: list[str]) -> list[dict]:
    """
    Return a single `revise` queue entry for all sorted paths, or an empty
    list when paths is empty.

    Command tokens are bare (no leading slash, no host namespace); adapters
    prepend their own prefix via format_block_message(command_prefix=...).
    """
    if not paths:
        return []
    sorted_paths = sorted(paths)
    return [{"command": "revise", "args": " ".join(sorted_paths)}]


def resolve_enforcement_mode(env_value: str) -> str:
    """Return 'warn' only for 'warn' (case-insensitive); else 'block'."""
    if env_value and env_value.strip().lower() == "warn":
        return "warn"
    return "block"


def expand_host_content(content: str, file_reader) -> str:
    """
    Expand @<path> import lines in content (non-recursive, one level only).

    Lines matching `^@<path>$` cause the referenced file's content to be
    appended. Lines with @ in the middle are ignored.
    """
    expanded = content
    for line in re.split(r"\r?\n", content):
        m = re.match(r"^@(\S+)\s*$", line)
        if m:
            import_path = m.group(1)
            imported = file_reader(import_path)
            if imported and imported.strip():
                expanded = expanded + "\n" + imported
    return expanded


# ---------------------------------------------------------------------------
# Queue assembly
# ---------------------------------------------------------------------------


def resolve_command_queue(drifted_index_dirs: list[str], registry_drift: bool) -> list[dict]:
    """
    Build the ordered command queue from drift results.

    `index` entries come first (sorted by dir), then `registry-sync`. Command
    tokens are bare; adapters namespace them via format_block_message.
    """
    queue = []
    for d in sorted(drifted_index_dirs):
        args = d if d.endswith("/") else f"{d}/"
        queue.append({"command": "index", "args": args})
    if registry_drift:
        queue.append({"command": "registry-sync", "args": ""})
    return queue


def format_block_message(
    queue: list[dict],
    standalone: bool = False,
    mode: str = "block",
    binding_gates_ref: str = BINDING_GATES_REF,
    command_prefix: str = "/",
) -> str:
    """
    Format a human-readable block/warn message from the command queue.

    Returns '' for empty/None queues. `binding_gates_ref` is the footer line
    and `command_prefix` is prepended to each bare command token; adapters may
    pass host-specific values (e.g. command_prefix="/docs-keeper:").
    """
    if not queue:
        return ""
    if mode == "warn":
        header = "Documentation maintenance suggested (non-blocking)."
        follow_up = "Recommended commands, in order:"
    else:
        header = "Documentation drift detected in the working tree."
        if standalone:
            follow_up = "Run the following commands to fix:"
        else:
            follow_up = "Run the following commands in order, re-stage modified files, then re-commit:"

    lines = [header, follow_up, ""]
    for i, item in enumerate(queue, start=1):
        name = f"{command_prefix}{item['command']}"
        cmd = f"{name} {item['args']}" if item.get("args") else name
        lines.append(f"  {i}. {cmd}")
    lines.append("")
    lines.append(binding_gates_ref)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestration (platform-neutral)
# ---------------------------------------------------------------------------


def get_docs_drift_queue(
    dir_lister,
    file_reader,
    docs_root: str = ".",
    exclude_dirs: frozenset | set = EXCLUDE_DIRS_DEFAULT,
    index_globs: tuple | list | None = None,
) -> list[dict]:
    """
    Compute the full drift queue (index + registry) for the docs tree.

    Returns an ordered command queue (may be empty when no drift).
    """
    index_dirs = get_index_dirs(docs_root, dir_lister, exclude_dirs)
    if not index_dirs:
        return []

    drifted = []
    for d in index_dirs:
        expected = get_expected_children(d, dir_lister, index_globs=index_globs)
        index_path = "index.md" if d == "." else f"{d}/index.md"
        declared = get_declared_children(file_reader(index_path))
        if not sets_equal(expected, declared):
            drifted.append(d)

    roots = get_root_index_dirs(index_dirs)
    host_file = find_host_root_prompt_file(file_reader)
    host_content = file_reader(host_file) if host_file else ""
    host_content = expand_host_content(host_content, file_reader)

    registry_drift = False
    for root in roots:
        if not check_registry_has_entry(host_content, root):
            registry_drift = True
            continue
        root_index_path = "index.md" if root == "." else f"{root}/index.md"
        intro = get_intro_from_front_matter(file_reader(root_index_path))
        if not check_registry_role_in_sync(host_content, root, intro):
            registry_drift = True

    return resolve_command_queue(drifted, registry_drift)


def evaluate_commit_maintenance(
    command: str,
    name_status: str,
    session_tracked_md: dict,
    dir_lister,
    file_reader,
    enforcement_mode: str = "",
    binding_gates_ref: str = BINDING_GATES_REF,
    command_prefix: str = "/",
    index_globs: tuple | list | None = None,
) -> dict:
    """
    Platform-neutral commit-time maintenance evaluation.

    Inputs are already extracted by the adapter:
      - command           : the bash command string the host is about to run.
      - name_status       : `git diff --cached --name-status -M` output.
      - session_tracked_md: {path: {"revised": bool}} merged tracker state.

    Returns {exit_code, message, reason, queue, mode}.
    """
    mode = resolve_enforcement_mode(enforcement_mode)

    if not is_git_commit(command):
        return {"exit_code": 0, "message": "", "reason": "not-git-commit", "queue": [], "mode": mode}

    changes = convert_git_name_status(name_status)
    if not touches_indexed_content(changes, index_globs):
        return {"exit_code": 0, "message": "", "reason": "no-docs-change", "queue": [], "mode": mode}

    staged = []
    seen = set()
    for change in changes:
        p = change.get("path")
        if path_matches_globs(p, index_globs) and p not in seen:
            staged.append(p)
            seen.add(p)

    tracked_md = session_tracked_md or {}
    revise_md = [p for p in staged if not tracked_md.get(p, {}).get("revised", False)]

    drift_queue = get_docs_drift_queue(dir_lister, file_reader, index_globs=index_globs)
    queue = resolve_revise_queue(revise_md) + drift_queue

    if not queue:
        return {"exit_code": 0, "message": "", "reason": "no-docs-drift", "queue": [], "mode": mode}

    exit_code = 0 if mode == "warn" else 2
    reason = "docs-action-suggested" if mode == "warn" else "docs-drift-detected"
    msg = format_block_message(
        queue, standalone=False, mode=mode, binding_gates_ref=binding_gates_ref, command_prefix=command_prefix
    )
    return {"exit_code": exit_code, "message": msg, "reason": reason, "queue": queue, "mode": mode}
