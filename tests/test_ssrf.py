"""Unit tests for SSRF protection."""
import pytest
from fastapi import HTTPException
from app.services.url_guard import check_url


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/anything",
    "http://localhost/anything",
    "http://10.0.0.1/anything",
    "http://172.16.0.1/anything",
    "http://192.168.1.1/anything",
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata
    "ftp://example.com/file",
    "file:///etc/passwd",
    "gopher://evil.com",
])
def test_ssrf_blocked(url):
    with pytest.raises(HTTPException) as exc_info:
        check_url(url)
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize("url", [
    "https://example.com",
    "http://example.com/path?q=1",
])
def test_allowed_urls(url):
    # Patch DNS resolution so the test works without network access
    from unittest.mock import patch
    fake_infos = [(None, None, None, None, ("93.184.216.34", 0))]
    with patch("socket.getaddrinfo", return_value=fake_infos):
        check_url(url)  # Should not raise
