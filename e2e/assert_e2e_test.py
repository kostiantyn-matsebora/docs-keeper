"""
pytest suite for e2e/assert_e2e.py — the end-to-end phase assertions.

Real filesystem against synthetic repos under tmp_path; no mocks. Exercises the
pure helpers and the phase checks (install / setup / index-declares) so the
black-box assertions the workflow depends on are themselves trustworthy.
"""

from e2e.assert_e2e import (
    check_index_declares,
    check_install,
    check_setup,
    find_host_prompt,
    find_index_files,
    frontmatter_unquoted_flow_keys,
    has_registry_section,
    parse_declared_children,
    validate_config,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _make_plugin(root, *, complete=True):
    """Lay down an assembled-plugin tree; drop one command when complete=False."""
    (root / ".claude-plugin").mkdir(parents=True)
    # No `hooks` field: the standard hooks/hooks.json is auto-loaded; referencing
    # it from the manifest triggers "Duplicate hooks file detected" (F1).
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "docs-keeper"}', encoding="utf-8")
    (root / "hooks").mkdir()
    (root / "hooks" / "hooks.json").write_text(
        '{"hooks": {"SessionStart": [], "PreToolUse": [], "PostToolUse": [], "Stop": [], "SessionEnd": []}}',
        encoding="utf-8",
    )
    (root / "hooks" / "_engine").mkdir()
    (root / "hooks" / "_engine" / "drift.py").write_text("X = 1\n", encoding="utf-8")
    (root / "agents").mkdir()
    (root / "agents" / "docs-keeper.md").write_text("# agent\n", encoding="utf-8")
    (root / "commands").mkdir()
    commands = ["capture", "config", "index", "registry-sync", "revise", "setup", "sweep"]
    if not complete:
        commands.remove("sweep")
    for cmd in commands:
        (root / "commands" / f"{cmd}.md").write_text(f"# {cmd}\n", encoding="utf-8")
    (root / "spec").mkdir()
    (root / "spec" / "role.md").write_text("# role\n", encoding="utf-8")


def _make_setup_repo(root, *, config=True, index=True, registry=True):
    """Lay down a host repo as it looks after a successful `setup`."""
    if config:
        (root / ".docs-keeper").mkdir()
        (root / ".docs-keeper" / "config.json").write_text(
            '{"enforcement": "warn", "paths": ["**/*.md"]}', encoding="utf-8"
        )
    docs = root / "docs"
    docs.mkdir()
    (docs / "overview.md").write_text("# Overview\n", encoding="utf-8")
    if index:
        (docs / "index.md").write_text(
            "---\ntitle: Docs\nintro: 'Docs.'\nchildren:\n  - /overview\n---\n", encoding="utf-8"
        )
    registry_md = "## Sources of truth\n\n- `docs/` — docs\n" if registry else ""
    (root / "CLAUDE.md").write_text(f"# Host\n\n{registry_md}", encoding="utf-8")


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------


class DescribeValidateConfig:
    def test_accepts_valid(self):
        assert validate_config('{"enforcement": "warn", "paths": ["**/*.md"]}') == []

    def test_accepts_block(self):
        assert validate_config('{"enforcement": "block", "paths": ["docs/**/*.md"]}') == []

    def test_rejects_missing(self):
        assert validate_config("") == ["config.json missing or empty"]

    def test_rejects_bad_json(self):
        assert validate_config("{not json") == ["config.json is not valid JSON"]

    def test_rejects_bad_enforcement(self):
        errors = validate_config('{"enforcement": "loud", "paths": ["**/*.md"]}')
        assert any("enforcement" in e for e in errors)

    def test_rejects_empty_paths(self):
        errors = validate_config('{"enforcement": "warn", "paths": []}')
        assert any("paths" in e for e in errors)


class DescribeHasRegistrySection:
    def test_detects_sources_of_truth(self):
        assert has_registry_section("# H\n\n## Sources of truth\n\n- x\n") is True

    def test_detects_authoritative_heading(self):
        assert has_registry_section("### Authoritative references\n") is True

    def test_false_when_only_in_body(self):
        assert has_registry_section("Some sources of truth live here.\n") is False

    def test_false_when_empty(self):
        assert has_registry_section("") is False


class DescribeParseDeclaredChildren:
    def test_parses_list(self):
        text = "---\ntitle: T\nchildren:\n  - /a\n  - /b/c\n---\nbody\n"
        assert parse_declared_children(text) == ["/a", "/b/c"]

    def test_empty_when_no_front_matter(self):
        assert parse_declared_children("# just a doc\n") == []

    def test_stops_at_next_key(self):
        text = "---\nchildren:\n  - /a\nintro: 'x'\n---\n"
        assert parse_declared_children(text) == ["/a"]


class DescribeFindIndexFiles:
    def test_finds_nested(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("x", encoding="utf-8")
        (tmp_path / "docs" / "sub").mkdir()
        (tmp_path / "docs" / "sub" / "index.md").write_text("x", encoding="utf-8")
        found = find_index_files(str(tmp_path))
        assert len(found) == 2

    def test_skips_excluded_dirs(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "index.md").write_text("x", encoding="utf-8")
        assert find_index_files(str(tmp_path)) == []


class DescribeFindHostPrompt:
    def test_prefers_claude_md(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# c\n", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        assert find_host_prompt(str(tmp_path)).endswith("CLAUDE.md")

    def test_empty_when_none(self, tmp_path):
        assert find_host_prompt(str(tmp_path)) == ""


# ---------------------------------------------------------------------------
# phase checks
# ---------------------------------------------------------------------------


class DescribeCheckInstall:
    def test_all_pass_for_complete_plugin(self, tmp_path):
        _make_plugin(tmp_path)
        assert all(ok for ok, _ in check_install(str(tmp_path)))

    def test_flags_missing_command(self, tmp_path):
        _make_plugin(tmp_path, complete=False)
        results = check_install(str(tmp_path))
        assert any(not ok and "sweep" in msg for ok, msg in results)

    def test_flags_unwrapped_hooks(self, tmp_path):
        # The bare-event-map format (no top-level "hooks" key) fails to load (F1).
        _make_plugin(tmp_path)
        (tmp_path / "hooks" / "hooks.json").write_text('{"SessionStart": []}', encoding="utf-8")
        results = check_install(str(tmp_path))
        assert any(not ok and "wraps events" in msg for ok, msg in results)

    def test_flags_manifest_referencing_standard_hooks(self, tmp_path):
        # plugin.json pointing at the auto-loaded hooks/hooks.json => duplicate (F1).
        _make_plugin(tmp_path)
        (tmp_path / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "docs-keeper", "hooks": "./hooks/hooks.json"}', encoding="utf-8"
        )
        results = check_install(str(tmp_path))
        assert any(not ok and "redundantly reference" in msg for ok, msg in results)


class DescribeCheckSetup:
    def test_all_pass_for_green_repo(self, tmp_path):
        _make_setup_repo(tmp_path)
        assert all(ok for ok, _ in check_setup(str(tmp_path)))

    def test_flags_missing_config(self, tmp_path):
        _make_setup_repo(tmp_path, config=False)
        results = check_setup(str(tmp_path))
        assert any(not ok and "config" in msg for ok, msg in results)

    def test_flags_missing_registry(self, tmp_path):
        _make_setup_repo(tmp_path, registry=False)
        results = check_setup(str(tmp_path))
        assert any(not ok and "Sources of truth" in msg for ok, msg in results)


class DescribeFrontmatterUnquotedFlowKeys:
    def test_flags_unquoted_double_bracket(self):
        text = "---\ndescription: x\nargument-hint: [doc-path] [-- brief]\n---\nbody\n"
        assert frontmatter_unquoted_flow_keys(text) == ["argument-hint"]

    def test_ok_when_quoted(self):
        text = '---\nargument-hint: "[doc-path] [-- brief]"\n---\n'
        assert frontmatter_unquoted_flow_keys(text) == []

    def test_ok_plain_scalar(self):
        text = "---\ndescription: A plain description.\n---\n"
        assert frontmatter_unquoted_flow_keys(text) == []


class DescribeCheckIndexDeclares:
    def test_passes_when_declared(self, tmp_path):
        idx = tmp_path / "index.md"
        idx.write_text("---\nchildren:\n  - /payments\n---\n", encoding="utf-8")
        assert check_index_declares(str(idx), "/payments")[0][0] is True

    def test_fails_when_absent(self, tmp_path):
        idx = tmp_path / "index.md"
        idx.write_text("---\nchildren:\n  - /other\n---\n", encoding="utf-8")
        assert check_index_declares(str(idx), "/payments")[0][0] is False
