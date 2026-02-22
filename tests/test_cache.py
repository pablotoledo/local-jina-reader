"""Unit tests for cache key hashing."""
from app.utils.hashing import make_cache_key
from app.utils.url import normalize_url


def test_cache_key_stable():
    key1 = make_cache_key("https://example.com/", None, None, None, None)
    key2 = make_cache_key("https://example.com/", None, None, None, None)
    assert key1 == key2


def test_cache_key_differs_by_selector():
    key1 = make_cache_key("https://example.com/", "article", None, None, None)
    key2 = make_cache_key("https://example.com/", "main", None, None, None)
    assert key1 != key2


def test_cache_key_differs_by_accept():
    key1 = make_cache_key("https://example.com/", None, None, None, "text/markdown")
    key2 = make_cache_key("https://example.com/", None, None, None, "application/json")
    assert key1 != key2


def test_cache_key_prefix():
    key = make_cache_key("https://example.com/")
    assert key.startswith("reader:")


def test_normalize_url_lowercase():
    assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"


def test_normalize_url_trailing_slash():
    assert normalize_url("https://example.com/path/") == "https://example.com/path"


def test_normalize_url_sorts_query():
    url = normalize_url("https://example.com/?b=2&a=1")
    assert url == "https://example.com/?a=1&b=2"
