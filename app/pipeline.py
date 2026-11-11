from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import asdict
from enum import Enum

from app.llm import llm_tiebreak
from app.matcher import decide, resolve_tie, to_result
from app.models import Candidate, Category, Decision, FetchStatus, Outcome, Platform, PlatformResult, SourceProduct
from app.queries import ladder
from app.sources.amazon import SourceError, get_source
from app.sources.croma import croma_candidates
from app.sources.flipkart import flipkart_candidates
from app.sources.http import make_client
from app.sources.myntra import myntra_candidates

PLATFORMS: dict[Category, list[Platform]] = {
    Category.PHONE: [Platform.FLIPKART, Platform.CROMA],
    Category.TV: [Platform.FLIPKART, Platform.CROMA],
    Category.SNEAKER: [Platform.FLIPKART, Platform.MYNTRA],
    Category.APPAREL: [Platform.FLIPKART, Platform.MYNTRA],
}
ADAPTERS = {
    Platform.FLIPKART: flipkart_candidates,
    Platform.CROMA: croma_candidates,
    Platform.MYNTRA: myntra_candidates,
}
TIMEOUTS: dict[Platform, float] = {Platform.CROMA: 90, Platform.FLIPKART: 20, Platform.MYNTRA: 20}
UNSUPPORTED = "This product isn't a phone, TV, sneaker or T-shirt/polo/jersey."


def _name(p: Platform) -> str:
    return p.value.capitalize()


def _plain(obj) -> dict:
    def conv(v):
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v

    return conv(asdict(obj))


async def _walk(client, src: SourceProduct, platform: Platform) -> PlatformResult:
    adapter = ADAPTERS[platform]
    statuses: list[FetchStatus] = []
    pool: list[Candidate] = []
    seen: set[str] = set()
    m = decide(src, [])
    for q in ladder(src, platform):
        status, cands = await adapter(client, q)
        statuses.append(status)
        for c in cands:
            if c.url not in seen:
                seen.add(c.url)
                pool.append(c)
        m = decide(src, pool)
        if m.decision in (Decision.MATCH, Decision.AMBIGUOUS):
            break
    if m.decision == Decision.AMBIGUOUS and m.reason == "tie":
        chosen = await llm_tiebreak(src, m.survivors)
        m = resolve_tie(m, chosen)
    return to_result(platform, m, statuses, src.canon.colour)


async def run_platform(client, src: SourceProduct, platform: Platform) -> PlatformResult:
    try:
        return await asyncio.wait_for(_walk(client, src, platform), TIMEOUTS[platform])
    except (asyncio.TimeoutError, TimeoutError):
        return PlatformResult(platform, Outcome.COULDNT_CHECK, None, f"Couldn't check {_name(platform)}: timed out")
    except Exception:
        return PlatformResult(platform, Outcome.COULDNT_CHECK, None,
                              f"Couldn't check {_name(platform)}: something went wrong")


async def check(url: str) -> AsyncIterator[dict]:
    async with make_client() as client:
        try:
            src = await get_source(client, url)
        except (ValueError, SourceError) as e:
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}
            return
        yield {"type": "source", "data": _plain(src)}
        platforms = PLATFORMS.get(src.category)
        if not platforms:
            yield {"type": "error", "message": UNSUPPORTED}
            yield {"type": "done"}
            return
        for p in platforms:
            yield {"type": "progress", "platform": p.value, "message": f"Searching {_name(p)}…"}
        for fut in asyncio.as_completed([run_platform(client, src, p) for p in platforms]):
            res = await fut
            yield {"type": "result", "data": _plain(res)}
        yield {"type": "done"}
