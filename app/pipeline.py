from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import asdict
from enum import Enum

from app.brandsite import official_name
from app.llm import llm_tiebreak
from app.confirm import confirm
from app.matcher import NEEDS_CONFIRM, Match, decide, resolve_tie, to_result, veto
from app.models import Candidate, Category, Decision, FetchStatus, Outcome, Platform, PlatformResult, SourceProduct
from app.queries import ladder
from app.sources.amazon import SourceError, get_source
from app.sources.croma import croma_candidates
from app.sources.flipkart import flipkart_candidates, flipkart_code_candidates
from app.sources.http import make_client
from app.sources.myntra import myntra_candidates

PLATFORMS: dict[Category, list[Platform]] = {
    Category.PHONE: [Platform.FLIPKART, Platform.CROMA],
    Category.TV: [Platform.FLIPKART, Platform.CROMA],
    Category.SNEAKER: [Platform.FLIPKART, Platform.MYNTRA],
    Category.APPAREL: [Platform.FLIPKART, Platform.MYNTRA],
}
log = logging.getLogger(__name__)
CODE_RUNG = "<style code search>"

ADAPTERS = {
    Platform.FLIPKART: flipkart_candidates,
    Platform.CROMA: croma_candidates,
    Platform.MYNTRA: myntra_candidates,
}
TIMEOUTS: dict[Platform, float] = {Platform.CROMA: 90, Platform.FLIPKART: 90, Platform.MYNTRA: 90}
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


async def _walk(client, src: SourceProduct, platform: Platform) -> tuple[Match, list[FetchStatus]]:
    adapter = ADAPTERS[platform]
    statuses: list[FetchStatus] = []
    pool: list[Candidate] = []
    seen: set[str] = set()
    m = decide(src, [])
    rungs: list[str] = list(ladder(src, platform))
    c = src.canon
    if platform == Platform.FLIPKART and src.category in (Category.APPAREL, Category.SNEAKER) and c.style_code:
        rungs.insert(0, CODE_RUNG)  # brand-filtered search matched on the code in card images
    for q in rungs:
        t = time.monotonic()
        if q == CODE_RUNG:
            status, cands = await flipkart_code_candidates(
                client, c.brand, c.base_colour, c.style_code,
                "shoes" if src.category == Category.SNEAKER else "t-shirt")
        else:
            status, cands = await adapter(client, q)
        statuses.append(status)
        reasons = Counter(veto(src.canon, c, src.category) or "PASS" for c in cands)
        log.info("%s q=%r status=%s candidates=%d %.1fs reasons=%s", platform.value, q, status.value,
                 len(cands), time.monotonic() - t, dict(reasons.most_common(6)))
        for c in cands:
            if c.url not in seen:
                seen.add(c.url)
                pool.append(c)
        m = decide(src, pool)
        log.info("%s decision=%s reason=%r pick=%s", platform.value, m.decision.value, m.reason,
                 m.candidate.url if m.candidate else None)
        # a code-search hit that isn't proven stays open: the text rungs may still find the exact code
        if m.decision == Decision.MATCH or (m.decision == Decision.AMBIGUOUS and q != CODE_RUNG):
            break
    return m, statuses


async def run_platform(client, src: SourceProduct, platform: Platform) -> PlatformResult:
    try:
        m, statuses = await asyncio.wait_for(_walk(client, src, platform), TIMEOUTS[platform])
    except (asyncio.TimeoutError, TimeoutError):
        log.warning("%s timed out after %ss", platform.value, TIMEOUTS[platform])
        return PlatformResult(platform, Outcome.COULDNT_CHECK, None, f"Couldn't check {_name(platform)}: timed out")
    except Exception:
        log.exception("%s failed", platform.value)
        return _went_wrong(platform)
    try:
        # The tie-break runs outside the platform budget: llm_tiebreak has its own 20 s cap and
        # returns None on timeout/error, so a slow LLM leaves the result at "Possible match".
        if m.decision == Decision.AMBIGUOUS and m.reason == "tie":
            chosen = await llm_tiebreak(src, m.survivors)
            m = resolve_tie(m, chosen)
        if m.decision == Decision.AMBIGUOUS and m.reason == NEEDS_CONFIRM:
            # no shared style code: MRP + manufacturer + photo may confirm it; on timeout it stays Possible
            try:
                m = await asyncio.wait_for(confirm(client, src, m), 45)
            except (asyncio.TimeoutError, TimeoutError):
                pass
        r = to_result(platform, m, statuses, src.canon.colour)
        log.info("%s RESULT %s | %s | %s", platform.value, r.outcome.value, r.reason, r.url)
        return r
    except Exception:
        log.exception("%s failed", platform.value)
        return _went_wrong(platform)


def _went_wrong(platform: Platform) -> PlatformResult:
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
        if src.category == Category.APPAREL and src.canon.style_code:
            try:
                src.canon.official_name = await asyncio.wait_for(
                    official_name(client, src.canon.brand, src.canon.style_code), 10)
            except Exception:
                pass  # no official name: the ladder falls back to Amazon's title
        yield {"type": "source", "data": _plain(src)}
        platforms = PLATFORMS.get(src.category)
        if not platforms:
            yield {"type": "error", "message": UNSUPPORTED}
            yield {"type": "done"}
            return
        for p in platforms:
            yield {"type": "progress", "platform": p.value, "message": f"Searching {_name(p)}…"}
        tasks = [asyncio.create_task(run_platform(client, src, p), name=f"run_platform:{p.value}")
                 for p in platforms]
        try:
            for fut in asyncio.as_completed(tasks):
                res = await fut
                yield {"type": "result", "data": _plain(res)}
            yield {"type": "done"}
        finally:
            # consumer may close the stream early: don't leave platform calls running
            pending = [t for t in tasks if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
