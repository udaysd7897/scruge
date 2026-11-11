from __future__ import annotations

import re
from urllib.parse import quote_plus

import httpx

from app.extract import from_myntra_search
from app.models import Candidate, FetchStatus
from app.sources.http import fetch


def _slug(q: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")


async def myntra_candidates(client: httpx.AsyncClient, q: str) -> tuple[FetchStatus, list[Candidate]]:
    url = f"https://www.myntra.com/{_slug(q)}?rawQuery={quote_plus(q)}"
    status, html = await fetch(client, url)
    if status != FetchStatus.OK:
        return status, []
    if "window.__myx" not in html:
        return FetchStatus.ERROR, []
    cands = from_myntra_search(html)
    return (FetchStatus.OK, cands) if cands else (FetchStatus.EMPTY, [])
