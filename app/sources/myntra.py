from __future__ import annotations

import json
import re
from urllib.parse import quote_plus

import httpx

from app.extract import from_myntra_search
from app.models import Candidate, FetchStatus
from app.sources.http import fetch


def _slug(q: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")


# Myntra answers a search in ~1 s but stalls on and off (ReadTimeout, 2026-11-13): short attempts and
# more of them beat one long wait. Worst case per query: 4 tries x 8 s + 1+2+4 s ≈ 39 s; the pipeline stops
# the query ladder after a query that fails outright, so a stalled Myntra can't eat the 90 s budget.
ATTEMPT_TIMEOUT = 8.0
BACKOFF = (1.0, 2.0, 4.0)


async def myntra_fetch(client: httpx.AsyncClient, url: str) -> tuple[FetchStatus, str]:
    return await fetch(client, url, timeout=ATTEMPT_TIMEOUT, backoff=BACKOFF)


async def myntra_candidates(client: httpx.AsyncClient, q: str) -> tuple[FetchStatus, list[Candidate]]:
    url = f"https://www.myntra.com/{_slug(q)}?rawQuery={quote_plus(q)}"
    status, html = await myntra_fetch(client, url)
    if status != FetchStatus.OK:
        return status, []
    marker = "window.__myx = "
    i = html.find(marker)
    if i < 0:
        return FetchStatus.ERROR, []
    try:
        data, _ = json.JSONDecoder().raw_decode(html[i + len(marker):])
        prods = data["searchData"]["results"]["products"]
        if not isinstance(prods, list):
            raise TypeError
        cands = from_myntra_search(html)
    except Exception:
        return FetchStatus.ERROR, []
    return (FetchStatus.OK, cands) if cands else (FetchStatus.EMPTY, [])
