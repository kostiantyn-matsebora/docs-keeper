"""
Deterministic black-box e2e — drives the installed entrypoints BY PATH against
real tmp fixtures (no mocks, no API key, no LLM). Where the per-module pytest
suites test engine functions in isolation, this exercises the actual CLI / hook
contracts a host invokes:

  * core/engine/cli.py            — `--drift-only`, `--emit-children`
  * adapters/.../cc_maintenance.py — the PreToolUse commit gate
  * adapters/.../cc_config.py      — the config command

These realize the deterministic (`D`) rows of TEST_CASES.md so they run in CI
without spending tokens. Agentic (`A`) rows live in .github/workflows/e2e.yml.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "core" / "engine" / "cli.py"
HOOKS_DIR = REPO_ROOT / "adapters" / "claude-code" / "hooks"
CC_MAINTENANCE = HOOKS_DIR / "cc_maintenance.py"
CC_CONFIG = HOOKS_DIR / "cc_config.py"


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------


def write(root, rel, content):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def init_repo(root):
    git(root, "init", "-q")
    git(root, "config", "user.email", "bb@docs-keeper.test")
    git(root, "config", "user.name", "bb")


def set_config(root, enforcement=None, paths=None):
    obj = {}
    if enforcement is not None:
        obj["enforcement"] = enforcement
    if paths is not None:
        obj["paths"] = paths
    import json

    write(root, ".docs-keeper/config.json", json.dumps(obj))


def run_drift(root, enforce=""):
    """Run the neutral CI drift gate; return (exit_code, stderr)."""
    argv = [sys.executable, str(CLI), "--drift-only", "--repo-root", str(root)]
    if enforce:
        argv += ["--enforce", enforce]
    r = subprocess.run(argv, capture_output=True, text=True)
    return r.returncode, r.stderr


def emit_children(root, target="."):
    """Run the deterministic children emitter; return the list of entries."""
    r = subprocess.run(
        [sys.executable, str(CLI), "--emit-children", target, "--repo-root", str(root)],
        capture_output=True,
        text=True,
    )
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def run_commit_gate(root, command="git commit -m wip"):
    """Invoke the PreToolUse commit gate by path; return (exit_code, stdout, stderr)."""
    import json

    payload = json.dumps({"tool_input": {"command": command}, "session_id": "bb"})
    r = subprocess.run(
        [sys.executable, str(CC_MAINTENANCE)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(HOOKS_DIR),
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": _path()},
    )
    return r.returncode, r.stdout, r.stderr


def run_config_set(root, *args):
    r = subprocess.run(
        [sys.executable, str(CC_CONFIG), "--repo-root", str(root), "--set", *args],
        capture_output=True,
        text=True,
        cwd=str(HOOKS_DIR),
    )
    return r.returncode, r.stdout, r.stderr


def _path():
    import os

    return os.environ.get("PATH", "")


def make_green(root):
    """A drift-clean repo-root index: declares its two markdown siblings + registry."""
    write(root, "index.md", "---\ntitle: Docs\nintro: 'Acme docs.'\nchildren:\n  - /CLAUDE\n  - /a\n---\n")
    write(root, "a.md", "# A\n")
    write(root, "CLAUDE.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md) — Acme docs.\n")


# ---------------------------------------------------------------------------
# CODE — commit-gate behavior (by path)
# ---------------------------------------------------------------------------


class DescribeCommitGate:
    def test_code04_warn_mode_advises_without_blocking(self, tmp_path):
        init_repo(tmp_path)
        make_green(tmp_path)
        set_config(tmp_path, enforcement="warn")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-qm", "baseline")
        write(tmp_path, "b.md", "# B\n")  # new doc the index does not declare -> drift
        git(tmp_path, "add", "b.md")
        code, out, _ = run_commit_gate(tmp_path)
        assert code == 0  # warn never blocks
        assert "systemMessage" in out

    def test_code05_code_only_change_is_silent(self, tmp_path):
        init_repo(tmp_path)
        make_green(tmp_path)
        set_config(tmp_path, enforcement="block")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-qm", "baseline")
        write(tmp_path, "src/app.cs", "// code\n")
        git(tmp_path, "add", "src/app.cs")
        code, out, err = run_commit_gate(tmp_path)
        assert code == 0  # no markdown staged -> no-docs-change
        assert out.strip() == ""

    def test_code06_edited_doc_queues_revise(self, tmp_path):
        init_repo(tmp_path)
        make_green(tmp_path)
        set_config(tmp_path, enforcement="block")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-qm", "baseline")
        write(tmp_path, "a.md", "# A\n\nedited body.\n")  # structural set unchanged
        git(tmp_path, "add", "a.md")
        code, _, err = run_commit_gate(tmp_path)
        assert code == 2
        assert "revise" in err

    def test_edge04_commit_tree_is_not_gated(self, tmp_path):
        init_repo(tmp_path)
        make_green(tmp_path)
        write(tmp_path, "b.md", "# B\n")  # drift present, but the command is not a commit
        git(tmp_path, "add", "-A")
        code, out, err = run_commit_gate(tmp_path, command="git commit-tree HEAD^{tree}")
        assert code == 0
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# DOC / EDGE — drift + emitter (by path)
# ---------------------------------------------------------------------------


class DescribeDriftGate:
    def test_doc04_deleted_doc_drifts_then_clears(self, tmp_path):
        make_green(tmp_path)
        assert run_drift(tmp_path, "block")[0] == 0
        (tmp_path / "a.md").unlink()  # index still declares /a
        assert run_drift(tmp_path, "block")[0] == 2
        assert emit_children(tmp_path) == ["/CLAUDE"]
        write(tmp_path, "index.md", "---\ntitle: Docs\nintro: 'Acme docs.'\nchildren:\n  - /CLAUDE\n---\n")
        assert run_drift(tmp_path, "block")[0] == 0

    def test_doc05_renamed_doc_swaps_slug(self, tmp_path):
        make_green(tmp_path)
        (tmp_path / "a.md").rename(tmp_path / "b.md")
        assert run_drift(tmp_path, "block")[0] == 2
        assert emit_children(tmp_path) == ["/CLAUDE", "/b"]

    def test_doc06_subdir_with_index_folds_to_boundary(self, tmp_path):
        write(tmp_path, "CLAUDE.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md) — Acme docs.\n")
        write(tmp_path, "a.md", "# A\n")
        write(tmp_path, "sub/index.md", "---\ntitle: Sub\nintro: 'Sub.'\nchildren:\n  - /x\n---\n")
        write(tmp_path, "sub/x.md", "# X\n")
        entries = emit_children(tmp_path)
        assert "/sub" in entries  # boundary, not enumerated
        assert "/sub/x" not in entries

    def test_doc07_intro_change_queues_registry_sync(self, tmp_path):
        make_green(tmp_path)
        # Change the root index intro; leave the registry line stale.
        write(tmp_path, "index.md", "---\ntitle: Docs\nintro: 'New intro.'\nchildren:\n  - /CLAUDE\n  - /a\n---\n")
        code, err = run_drift(tmp_path, "block")
        assert code == 2
        assert "registry-sync" in err

    def test_doc08_paths_narrowing_changes_indexed_set(self, tmp_path):
        write(tmp_path, "index.md", "---\ntitle: Docs\nintro: 'Acme docs.'\nchildren:\n  - /a\n---\n")
        write(tmp_path, "a.md", "# A\n")
        write(tmp_path, "draft.md", "# Draft\n")
        write(tmp_path, "CLAUDE.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md) — Acme docs.\n")
        set_config(tmp_path, paths=["**/*.md"])
        assert run_drift(tmp_path)[0] == 2  # draft.md + CLAUDE undeclared
        set_config(tmp_path, paths=["a.md"])
        assert emit_children(tmp_path) == ["/a"]
        assert run_drift(tmp_path)[0] == 0

    def test_edge01_repo_without_indexes_is_clean(self, tmp_path):
        write(tmp_path, "README.md", "# readme\n")  # no index.md anywhere
        assert run_drift(tmp_path, "block")[0] == 0

    def test_edge02_agents_md_host_registry_is_detected(self, tmp_path):
        # Host prompt is AGENTS.md (no CLAUDE.md); registry lives there. AGENTS.md is a
        # root .md so it is itself an expected child of the root index.
        write(tmp_path, "index.md", "---\ntitle: Docs\nintro: 'Acme docs.'\nchildren:\n  - /AGENTS\n  - /a\n---\n")
        write(tmp_path, "a.md", "# A\n")
        write(tmp_path, "AGENTS.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md) — Acme docs.\n")
        assert run_drift(tmp_path, "block")[0] == 0
        write(tmp_path, "AGENTS.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md)\n\n(registry intro removed)\n")
        assert run_drift(tmp_path, "block")[0] == 2

    def test_edge03_excluded_dirs_are_not_indexed(self, tmp_path):
        # An inconsistent index inside node_modules must not be treated as an index root.
        write(tmp_path, "node_modules/index.md", "---\ntitle: NM\nchildren:\n  - /ghost\n---\n")
        write(tmp_path, "node_modules/real.md", "# real\n")
        assert run_drift(tmp_path, "block")[0] == 0

    def test_edge05_non_markdown_is_not_a_child(self, tmp_path):
        write(tmp_path, "index.md", "---\ntitle: Docs\nintro: 'Acme docs.'\nchildren:\n  - /a\n---\n")
        write(tmp_path, "a.md", "# A\n")
        write(tmp_path, "notes.txt", "not markdown\n")
        write(tmp_path, "CLAUDE.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md) — Acme docs.\n")
        entries = emit_children(tmp_path)
        assert "/a" in entries
        assert not any("notes" in e for e in entries)

    def test_edge08_crlf_index_parses_like_lf(self, tmp_path):
        crlf = "---\r\ntitle: Docs\r\nintro: 'Acme docs.'\r\nchildren:\r\n  - /CLAUDE\r\n  - /a\r\n---\r\n"
        (tmp_path / "index.md").write_bytes(crlf.encode("utf-8"))
        write(tmp_path, "a.md", "# A\n")
        write(tmp_path, "CLAUDE.md", "# Host\n\n## Sources of truth\n\n- [`index.md`](index.md) — Acme docs.\n")
        assert run_drift(tmp_path, "block")[0] == 0


# ---------------------------------------------------------------------------
# CFG — config command (by path)
# ---------------------------------------------------------------------------


class DescribeConfigCommand:
    def test_cfg03_rejects_invalid_enforcement(self, tmp_path):
        code, _, err = run_config_set(tmp_path, "enforcement", "loud")
        assert code == 1
        assert "enforcement" in err

    def test_cfg_accepts_valid_enforcement(self, tmp_path):
        code, out, _ = run_config_set(tmp_path, "enforcement", "block")
        assert code == 0
        assert (tmp_path / ".docs-keeper" / "config.json").exists()
