from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from app.models.schemas import ReadRequest
from app.services.reader_service import read_url

router = APIRouter()


@router.get("/r/{url:path}")
async def read_get(
    url: str,
    accept: str = Header(default="text/markdown"),
    x_no_cache: bool = Header(default=False, alias="x-no-cache"),
):
    as_json = "application/json" in accept
    data = await read_url(url, as_json=as_json, no_cache=x_no_cache)
    if as_json:
        return JSONResponse(content=data)
    return PlainTextResponse(
        f"Title: {data['title']}\n\n{data['content']}\n\nSource: {data['url']}"
    )


@router.post("/r")
async def read_post(body: ReadRequest):
    as_json = body.accept == "application/json"
    data = await read_url(body.url, as_json=as_json, no_cache=body.no_cache)
    if as_json:
        return JSONResponse(content=data)
    return PlainTextResponse(
        f"Title: {data['title']}\n\n{data['content']}\n\nSource: {data['url']}"
    )
