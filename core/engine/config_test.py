"""
pytest suite for the repo configuration reader (config.py).

Mock-free: file_reader is a plain dict-backed callable; no host coupling.
"""

import json

from core.engine.config import (
    CONFIG_REL_PATH,
    get_enforcement_setting,
    get_index_globs,
    load_config,
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
