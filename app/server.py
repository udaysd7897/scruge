from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from app.pipeline import check

INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"
GENERIC_ERROR = "Something went wrong. Please try again."

log = logging.getLogger(__name__)
app = FastAPI()


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _stream(url: str) -> AsyncIterator[str]:
    if not url or not url.strip():
        yield _sse({"type": "error", "message": "Please paste an Amazon.in product link."})
        yield _sse({"type": "done"})
        return
    yield _sse({"type": "progress", "platform": None, "message": "Reading the Amazon listing…"})
    try:
        async for event in check(url.strip()):
            yield _sse(event)
    except Exception as exc:
        log.warning("check failed: %s", type(exc).__name__)
        yield _sse({"type": "error", "message": GENERIC_ERROR})
        yield _sse({"type": "done"})


@app.get("/")
async def index():
    return FileResponse(INDEX, media_type="text/html")


@app.get("/api/check")
async def api_check(url: str = ""):
    return StreamingResponse(
        _stream(url),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
