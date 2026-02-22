from fastapi import Header, HTTPException, status
from app.core.security import verify_api_key
from app.core.config import settings


async def require_api_key(authorization: str | None = Header(default=None)) -> str | None:
    """Optional API key check. If API_KEYS is empty, auth is disabled."""
    if not settings.API_KEYS:
        return None
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or not verify_api_key(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return token
