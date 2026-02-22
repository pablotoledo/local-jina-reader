"""Cache key hashing utilities."""
import hashlib


def make_cache_key(
    url: str,
    target_selector: str | None = None,
    wait_for_selector: str | None = None,
    respond_with: str | None = None,
    accept: str | None = None,
    extractor_version: str = "1",
) -> str:
    """
    Build a stable cache key from URL + request parameters.
    Hash: normalized_url + x-target-selector + x-wait-for-selector + x-respond-with + Accept + extractor_version
    """
    parts = [
        url or "",
        target_selector or "",
        wait_for_selector or "",
        respond_with or "",
        accept or "",
        extractor_version,
    ]
    raw = "|".join(parts)
    return "reader:" + hashlib.sha256(raw.encode()).hexdigest()
