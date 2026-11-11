from __future__ import annotations

import httpx

from app.extract import from_croma
from app.models import Candidate, FetchStatus
from app.sources.apify import run_actor

ACTOR = "sian.agency~croma-product-scraper"


async def croma_candidates(client: httpx.AsyncClient, q: str) -> tuple[FetchStatus, list[Candidate]]:
    status, items = await run_actor(
        client, ACTOR, {"keywords": [q], "scrapeMode": "detail", "sort": "relevance", "maxResults": 10}
    )
    if status != FetchStatus.OK:
        return status, []
    cands: list[Candidate] = []
    for i in items:
        if not isinstance(i, dict):
            continue
        try:
            c = from_croma(i)
            if c.title:
                cands.append(c)
        except Exception:
            continue
    return (FetchStatus.OK, cands) if cands else (FetchStatus.ERROR, [])
