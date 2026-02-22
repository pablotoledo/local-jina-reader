from pydantic import BaseModel, HttpUrl


class ReadRequest(BaseModel):
    url: str
    accept: str = "text/markdown"
    no_cache: bool = False


class ReadResponse(BaseModel):
    url: str
    title: str
    content: str
    usage: dict
    cached: bool
    fetched_at: str
