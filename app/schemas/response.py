from pydantic import BaseModel
from typing import Any


class ReaderMeta(BaseModel):
    from_cache: bool = False
    elapsed_ms: int = 0
    engine: str = "httpx+readability"
    accept: str = "text/markdown"
    respond_with: str = "markdown"


class ReaderResponse(BaseModel):
    url: str
    title: str
    content: str
    meta: ReaderMeta
