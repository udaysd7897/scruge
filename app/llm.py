from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import asdict

from app.models import Candidate, SourceProduct

MODEL = "claude-sonnet-5-5"
TIMEOUT = 20


def _fields(canon) -> dict:
    return {k: v for k, v in asdict(canon).items() if v is not None and k != "title"}


def build_prompt(src: SourceProduct, survivors: list[Candidate]) -> str:
    source = {"title": src.title, **_fields(src.canon)}
    cands = [{"number": i, "title": c.title, **_fields(c.canon)} for i, c in enumerate(survivors, 1)]
    return (
        "You are matching an Amazon.in product to listings on another store. A listing matches only if "
        "it is the identical product (same model, variant and colour where known).\n\n"
        f"Source product:\n{json.dumps(source, ensure_ascii=False)}\n\n"
        f"Candidate listings:\n{json.dumps(cands, ensure_ascii=False, indent=1)}\n\n"
        "Return ONLY the number of the candidate that is the identical product, or the word none "
        "if no candidate is clearly identical. No other text."
    )


async def _ask(prompt: str) -> str:
    import anthropic

    async with anthropic.AsyncAnthropic(timeout=TIMEOUT) as client:
        msg = await client.messages.create(
            model=MODEL, max_tokens=50, messages=[{"role": "user", "content": prompt}]
        )
    return "".join(getattr(b, "text", "") for b in msg.content)


async def llm_tiebreak(src: SourceProduct, survivors: list[Candidate]) -> Candidate | None:
    """Optional Claude tie-break (§6.6). None when no key, on any error, or on 'none'/unparsable."""
    if not os.environ.get("ANTHROPIC_API_KEY") or not survivors:
        return None
    try:
        text = await asyncio.wait_for(_ask(build_prompt(src, survivors)), TIMEOUT)
    except Exception:
        return None
    m = re.fullmatch(r"\s*(\d+)\s*\.?\s*", text or "")
    if not m:
        return None
    i = int(m.group(1))
    return survivors[i - 1] if 1 <= i <= len(survivors) else None
