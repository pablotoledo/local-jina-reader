"""SSE helpers (stub for Phase 1, full impl in Phase 2)."""
from typing import AsyncIterator


async def sse_stream(content: str) -> AsyncIterator[str]:
    """Yield SSE events for a given content string."""
    yield f"event: phase\ndata: {{\"phase\":\"rendered\"}}\n\n"
    yield f"event: final\ndata: {{\"content\":{content!r}}}\n\n"
