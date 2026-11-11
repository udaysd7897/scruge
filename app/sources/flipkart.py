from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus

import httpx

from app.extract import from_flipkart_page
from app.models import Candidate, FetchStatus
from app.sources.http import fetch

_LINK = re.compile(r"/[^\"'\s]+/p/itm[a-z0-9]+\?pid=[A-Z0-9]+")
_PID = re.compile(r"pid=([A-Z0-9]+)")


async def _search_html(client, q):
    return await fetch(client, f"https://www.flipkart.com/search?q={quote_plus(q)}")


def _links(html: str, q: str = "") -> list[str]:
    seen, out = set(), []
    for m in _LINK.finditer(html.replace("&amp;", "&")):
        link = m.group(0)
        pid = _PID.search(link).group(1)
        if pid in seen:
            continue
        seen.add(pid)
        out.append(link.split("&")[0])
    # Search pages interleave sponsored/unrelated tiles: links whose slug contains every query
    # token come first (stable), then the rest; keep 10.
    toks = [t for t in re.split(r"[^a-z0-9]+", q.lower()) if t]
    out.sort(key=lambda u: not all(t in u.split("/p/")[0].lower() for t in toks))
    return ["https://www.flipkart.com" + u for u in out[:10]]


async def flipkart_search(client: httpx.AsyncClient, q: str) -> tuple[FetchStatus, list[str]]:
    status, html = await _search_html(client, q)
    if status != FetchStatus.OK:
        return status, []
    urls = _links(html, q)
    return (FetchStatus.OK, urls) if urls else (FetchStatus.EMPTY, [])


async def flipkart_candidates(client: httpx.AsyncClient, q: str) -> tuple[FetchStatus, list[Candidate]]:
    status, urls = await flipkart_search(client, q)
    if status != FetchStatus.OK:
        return status, []
    sem = asyncio.Semaphore(3)

    async def one(u):
        async with sem:
            return u, *(await fetch(client, u))

    results = await asyncio.gather(*(one(u) for u in urls))
    cands: list[Candidate] = []
    failures: list[FetchStatus] = []
    for u, st, html in results:
        if st != FetchStatus.OK:
            failures.append(st)
            continue
        try:
            cands.extend(from_flipkart_page(html, u))
        except Exception:
            failures.append(FetchStatus.ERROR)
    if not cands:
        if failures and len(failures) * 2 >= len(results):
            return (FetchStatus.BLOCKED if FetchStatus.BLOCKED in failures else FetchStatus.ERROR), []
        return FetchStatus.EMPTY, []
    return FetchStatus.OK, cands
