from pydantic import BaseModel, HttpUrl


class ReadPostBody(BaseModel):
    url: str
    headers: dict[str, str] | None = None
