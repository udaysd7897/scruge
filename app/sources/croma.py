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
    return FetchStatus.OK, [from_croma(i) for i in items]
