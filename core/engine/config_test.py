"""
pytest suite for the repo configuration reader (config.py).

Mock-free: file_reader is a plain dict-backed callable; no host coupling.
"""

import json

from core.engine.config import (
    CONFIG_REL_PATH,
    apply_setting,
    get_enforcement_setting,
    get_index_globs,
    load_config,
    normalize_setting,
    serialize_config,
    set_config_value,
    write_config,
)


def new_file_reader(files: dict):
    """Return a file_reader(rel_path) -> str backed by an in-memory dict."""
    return lambda rel_path: files.get(rel_path, "")


class DescribeLoadConfig:
    def test_returns_empty_dict_when_file_absent(self):
        assert load_config(new_file_reader({})) == {}

    def test_returns_empty_dict_when_file_blank(self):
        assert load_config(new_file_reader({CONFIG_REL_PATH: "   \n"})) == {}

    def test_returns_empty_dict_on_invalid_json(self):
        assert load_config(new_file_reader({CONFIG_REL_PATH: "{not json"})) == {}

    def test_returns_empty_dict_when_top_level_is_not_an_object(self):
        assert load_config(new_file_reader({CONFIG_REL_PATH: "[1, 2, 3]"})) == {}

    def test_parses_settings_object(self):
        files = {CONFIG_REL_PATH: json.dumps({"enforcement": "warn"})}
        assert load_config(new_file_reader(files)) == {"enforcement": "warn"}


class DescribeGetEnforcementSetting:
    def test_returns_empty_when_unset(self):
        assert get_enforcement_setting({}) == ""

    def test_returns_empty_when_config_not_a_dict(self):
        assert get_enforcement_setting(None) == ""

    def test_returns_the_raw_value(self):
        assert get_enforcement_setting({"enforcement": "block"}) == "block"

    def test_coerces_non_string_values_to_str(self):
        assert get_enforcement_setting({"enforcement": 0}) == "0"


class DescribeGetIndexGlobs:
    def test_returns_empty_when_unset(self):
        assert get_index_globs({}) == []

    def test_returns_empty_when_not_a_list(self):
        assert get_index_globs({"paths": "**/*.md"}) == []

    def test_returns_the_configured_globs(self):
        assert get_index_globs({"paths": ["**/*.md"]}) == ["**/*.md"]

    def test_supports_multiple_globs(self):
        cfg = {"paths": ["docs/**/*.md", "**/*.mdx", "adr/**/*.md"]}
        assert get_index_globs(cfg) == ["docs/**/*.md", "**/*.mdx", "adr/**/*.md"]

    def test_drops_blank_and_non_string_entries(self):
        assert get_index_globs({"paths": ["**/*.md", "", 7, "  ", "docs/*.md"]}) == ["**/*.md", "docs/*.md"]


class DescribeNormalizeSetting:
    def test_accepts_valid_enforcement(self):
        assert normalize_setting("enforcement", ["warn"]) == ("warn", "")
        assert normalize_setting("enforcement", ["block"]) == ("block", "")

    def test_rejects_invalid_enforcement(self):
        value, error = normalize_setting("enforcement", ["loud"])
        assert value is None
        assert "enforcement must be one of" in error

    def test_rejects_enforcement_with_extra_values(self):
        value, error = normalize_setting("enforcement", ["warn", "block"])
        assert value is None and error

    def test_accepts_one_or_more_path_globs(self):
        assert normalize_setting("paths", ["**/*.md", "adr/*.md"]) == (["**/*.md", "adr/*.md"], "")

    def test_rejects_blank_only_paths(self):
        value, error = normalize_setting("paths", ["  "])
        assert value is None
        assert "at least one glob" in error

    def test_rejects_unknown_key(self):
        value, error = normalize_setting("bogus", ["x"])
        assert value is None
        assert "unknown setting" in error


class DescribeApplyAndSetConfigValue:
    def test_set_config_value_does_not_mutate_input(self):
        original = {"enforcement": "warn"}
        updated = set_config_value(original, "paths", ["**/*.md"])
        assert original == {"enforcement": "warn"}
        assert updated == {"enforcement": "warn", "paths": ["**/*.md"]}

    def test_apply_setting_validates_then_sets(self):
        new_config, error = apply_setting({"enforcement": "warn"}, "enforcement", ["block"])
        assert error == ""
        assert new_config == {"enforcement": "block"}

    def test_apply_setting_returns_error_and_no_config_on_invalid(self):
        new_config, error = apply_setting({}, "paths", [])
        assert new_config is None
        assert error


class DescribeSerializeAndWriteConfig:
    def test_serialize_is_sorted_and_newline_terminated(self):
        out = serialize_config({"paths": ["**/*.md"], "enforcement": "warn"})
        assert out.endswith("\n")
        # sorted keys: enforcement before paths
        assert out.index('"enforcement"') < out.index('"paths"')

    def test_write_config_round_trips_via_load(self, tmp_path):
        write_config(str(tmp_path), {"enforcement": "block", "paths": ["docs/**/*.md"]})
        written = (tmp_path / ".docs-keeper" / "config.json").read_text()
        reloaded = load_config(new_file_reader({CONFIG_REL_PATH: written}))
        assert reloaded == {"enforcement": "block", "paths": ["docs/**/*.md"]}
