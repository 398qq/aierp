"""Tests for CORS origin parsing extracted from main.py."""


from app.main import _parse_cors_origins


class TestParseCorsOrigins:
    def test_multiple_origins_comma_separated(self):
        result = _parse_cors_origins("http://localhost:3002,https://erp.example.com")
        assert result == ["http://localhost:3002", "https://erp.example.com"]

    def test_single_origin_no_comma(self):
        result = _parse_cors_origins("https://myapp.com")
        assert result == ["https://myapp.com"]

    def test_empty_string_returns_empty_list(self):
        result = _parse_cors_origins("")
        assert result == []

    def test_whitespace_stripped(self):
        result = _parse_cors_origins(" http://a.com ,  https://b.com ")
        assert result == ["http://a.com", "https://b.com"]

    def test_trailing_comma_ignored(self):
        result = _parse_cors_origins("http://a.com,")
        assert result == ["http://a.com"]

    def test_leading_comma_ignored(self):
        result = _parse_cors_origins(",http://a.com")
        assert result == ["http://a.com"]

    def test_only_commas_returns_empty_list(self):
        result = _parse_cors_origins(",,,")
        assert result == []

    def test_wildcard_origin_preserved(self):
        result = _parse_cors_origins("*")
        assert result == ["*"]
