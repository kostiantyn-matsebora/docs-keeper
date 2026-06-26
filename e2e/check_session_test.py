"""
pytest suite for e2e/check_session.py — surfacing headless session errors.
"""

from e2e.check_session import session_error


class DescribeSessionError:
    def test_reports_auth_error_with_status(self):
        raw = '{"is_error": true, "api_error_status": 401, "result": "Invalid API key"}'
        assert session_error(raw) == "Invalid API key (HTTP 401)"

    def test_reports_error_without_status(self):
        raw = '{"is_error": true, "result": "boom"}'
        assert session_error(raw) == "boom"

    def test_empty_on_success(self):
        raw = '{"is_error": false, "result": "all good"}'
        assert session_error(raw) == ""

    def test_empty_on_non_json(self):
        assert session_error("not json at all") == ""

    def test_empty_on_blank(self):
        assert session_error("") == ""
