from app.core.config import settings


def verify_api_key(token: str) -> bool:
    """Return True if token is in the configured API key list."""
    return token in settings.API_KEYS
