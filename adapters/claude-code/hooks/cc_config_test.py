"""
pytest suite for the Claude Code config adapter (cc_config.py).

End-to-end: run the real entrypoint as a subprocess against a tmp repo and
assert the config file it writes + the JSON it prints. No mocks; real filesystem.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = str(Path(__file__).with_name("cc_config.py"))


def _run(args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
    )


def _config_file(tmp_path):
    return tmp_path / ".docs-keeper" / "config.json"


class DescribeGet:
    def test_prints_empty_object_when_unconfigured(self, tmp_path):
        result = _run(["--get", "--repo-root", str(tmp_path)])
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_reflects_persisted_values(self, tmp_path):
        _run(["--set", "enforcement", "block", "--repo-root", str(tmp_path)])
        result = _run(["--get", "--repo-root", str(tmp_path)])
        assert json.loads(result.stdout) == {"enforcement": "block"}


class DescribeSetEnforcement:
    def test_writes_a_valid_value(self, tmp_path):
        result = _run(["--set", "enforcement", "warn", "--repo-root", str(tmp_path)])
        assert result.returncode == 0
        assert json.loads(_config_file(tmp_path).read_text()) == {"enforcement": "warn"}

    def test_rejects_an_invalid_value(self, tmp_path):
        result = _run(["--set", "enforcement", "loud", "--repo-root", str(tmp_path)])
        assert result.returncode == 1
        assert "enforcement must be one of" in result.stderr
        assert not _config_file(tmp_path).exists()


class DescribeSetPaths:
    def test_replaces_the_glob_array(self, tmp_path):
        result = _run(["--set", "paths", "docs/**/*.md", "adr/**/*.md", "--repo-root", str(tmp_path)])
        assert result.returncode == 0
        assert json.loads(_config_file(tmp_path).read_text())["paths"] == ["docs/**/*.md", "adr/**/*.md"]

    def test_requires_at_least_one_glob(self, tmp_path):
        # argparse needs >=1 value for --set; a single blank glob is rejected by validation.
        result = _run(["--set", "paths", "   ", "--repo-root", str(tmp_path)])
        assert result.returncode == 1
        assert "at least one glob" in result.stderr


class DescribeSetGeneral:
    def test_rejects_an_unknown_key(self, tmp_path):
        result = _run(["--set", "bogus", "x", "--repo-root", str(tmp_path)])
        assert result.returncode == 1
        assert "unknown setting" in result.stderr

    def test_preserves_other_keys_across_sets(self, tmp_path):
        _run(["--set", "enforcement", "block", "--repo-root", str(tmp_path)])
        _run(["--set", "paths", "**/*.md", "--repo-root", str(tmp_path)])
        data = json.loads(_config_file(tmp_path).read_text())
        assert data == {"enforcement": "block", "paths": ["**/*.md"]}
