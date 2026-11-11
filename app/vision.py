"""Photo check for listings without a shared code: does the listing photo show the same product and
colourway as the Amazon photo? Returns SAME / DIFFERENT / UNSURE; UNSURE without ANTHROPIC_API_KEY."""
from __future__ import annotations

import base64
import json
import os
import re

import httpx

from app.models import Candidate, SourceProduct

MODEL = "claude-sonnet-5-5"


async def _img(client: httpx.AsyncClient, url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    try:
        r = await client.get(url)
    except httpx.HTTPError:
        return None
    ct = r.headers.get("content-type", "").split(";")[0]
    return (ct, base64.b64encode(r.content).decode()) if r.status_code == 200 and ct.startswith("image/") else None


async def same_product(src: SourceProduct, cand: Candidate) -> str:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "UNSURE"
    try:
        import anthropic
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as hc:
            a, b = await _img(hc, src.image), await _img(hc, cand.image)
        if not a or not b:
            return "UNSURE"
        async with anthropic.AsyncAnthropic() as ac:
            msg = await ac.messages.create(model=MODEL, max_tokens=150, messages=[{"role": "user", "content": [
                {"type": "text", "text": f"Listing A: {src.title} (colour {src.canon.colour})"},
                {"type": "image", "source": {"type": "base64", "media_type": a[0], "data": a[1]}},
                {"type": "text", "text": f"Listing B: {cand.title} (colour {cand.canon.colour})"},
                {"type": "image", "source": {"type": "base64", "media_type": b[0], "data": b[1]}},
                {"type": "text", "text": "Are A and B the exact same product: same design AND same colourway "
                 "(size ignored)? Compare logo, print, panels and colour. Reply only JSON "
                 '{"verdict":"SAME"|"DIFFERENT"|"UNSURE"}.'}]}])
        m = re.search(r"\{.*\}", msg.content[0].text, re.S)
        v = json.loads(m.group(0)).get("verdict") if m else None
        return v if v in ("SAME", "DIFFERENT", "UNSURE") else "UNSURE"
    except Exception:
        return "UNSURE"
