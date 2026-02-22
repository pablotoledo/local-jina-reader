"""URL normalization utilities."""
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl


def normalize_url(url: str) -> str:
    """Normalize URL: lowercase scheme+host, sort query params, strip trailing slash."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") if parsed.path not in ("/", "") else "/"
    # Sort query params for stable cache keys
    query = urlencode(sorted(parse_qsl(parsed.query)))
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))
