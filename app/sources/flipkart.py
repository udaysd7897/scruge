from __future__ import annotations

import asyncio
import re
from urllib.parse import quote, quote_plus

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


SIBLING_FROM = 3   # expand the variant lists of the top 3 search hits
SIBLING_MAX = 12   # at most this many extra product pages


def sibling_links(html: str, url: str) -> list[str]:
    """Other variants (storage/colour) of the same product: links on the page sharing its itm id."""
    m = re.search(r"/p/(itm[a-z0-9]+)", url)
    if not m:
        return []
    own = _PID.search(url)
    out = []
    for link in re.findall(rf"/[a-z0-9-]+/p/{m.group(1)}\?pid=[A-Z0-9]+", html.replace("&amp;", "&")):
        u = "https://www.flipkart.com" + link
        if (not own or own.group(1) not in link) and u not in out:
            out.append(u)
    return out


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

    results = list(await asyncio.gather(*(one(u) for u in urls)))
    # the exact variant is often not among the search hits: walk the top hits' variant lists
    seen = set(urls)
    sibs = []
    for u, st, html in results[:SIBLING_FROM]:
        if "/p/itm" in u and "pid=TSH" in u:
            continue  # clothing siblings are sizes of the same item: nothing to gain, many fetches
        if st == FetchStatus.OK:
            sibs += [x for x in sibling_links(html, u) if x not in seen and not seen.add(x)]
    if sibs:
        results += await asyncio.gather(*(one(u) for u in sibs[:SIBLING_MAX]))
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
    if failures:
        # an unread product page may have been the match: report the failure together with what did
        # parse, so a match among those still wins but "no match" becomes "Couldn't check"
        return (FetchStatus.BLOCKED if FetchStatus.BLOCKED in failures else FetchStatus.ERROR), cands
    return (FetchStatus.OK, cands) if cands else (FetchStatus.EMPTY, [])


CODE_PAGES = 2   # brand(+colour)-filtered result pages scanned for the style code
CODE_OPEN = 6    # at most this many product pages opened
_CARD_LINK = re.compile(r"/[^\"\s]+/p/itm[a-z0-9]+\?pid=[A-Z0-9]{16}")
_CARD_IMG = re.compile(r"/image/\d+/\d+/[^\"\s]*?/([a-z0-9-]+)\.(?:jpeg|jpg|webp)")


def _code_groups(code: str) -> list[str]:
    return [g for g in re.findall(r"\d{4,}", code or "")]


def code_card_links(html: str, code: str) -> list[str]:
    """Product links of search cards whose image file name carries the style code's digit groups
    ("m-auskb-04065-ausk-original-....jpeg" for AUSK-04065-L). Each card's image sits right after its link."""
    groups = _code_groups(code)
    if not groups:
        return []
    h = html.replace("&amp;", "&")
    links = [(m.start(), m.group(0)) for m in _CARD_LINK.finditer(h)]
    out: list[str] = []
    for m in _CARD_IMG.finditer(h):
        name = m.group(1)
        if all(re.search(rf"(?<!\d){g}(?!\d)", name) for g in groups):
            prev = [lk for pos, lk in links if pos < m.start()]
            if prev:
                u = "https://www.flipkart.com" + prev[-1].split("&")[0]
                if u not in out:
                    out.append(u)
    return out


async def flipkart_code_candidates(client: httpx.AsyncClient, brand: str | None, colour: str | None,
                                   code: str | None, noun: str = "t-shirt") -> tuple[FetchStatus, list[Candidate]]:
    """Find listings by brand style code. Flipkart's text search doesn't index codes and ranks small
    brands low (AUSK on page 2); a brand(+colour)-filtered listing does, and card image names carry codes."""
    if not (brand and code and _code_groups(code)):
        return FetchStatus.EMPTY, []
    base = (f"https://www.flipkart.com/search?q={quote_plus(brand + ' ' + noun)}"
            f"&p%5B%5D={quote('facets.brand[]=' + brand.upper())}")
    if colour:
        base += f"&p%5B%5D={quote('facets.color[]=' + colour.title())}"
    urls: list[str] = []
    statuses: list[FetchStatus] = []
    for page in range(1, CODE_PAGES + 1):
        st, html = await fetch(client, base + f"&page={page}")
        statuses.append(st)
        if st == FetchStatus.OK:
            urls += [u for u in code_card_links(html, code) if u not in urls]
    if not urls:
        bad = [x for x in statuses if x != FetchStatus.OK]
        return (bad[0] if bad else FetchStatus.EMPTY), []
    cands: list[Candidate] = []
    for u in urls[:CODE_OPEN]:
        st, html = await fetch(client, u)
        if st == FetchStatus.OK:
            try:
                cands += from_flipkart_page(html, u)
            except Exception:
                continue
    return (FetchStatus.OK, cands) if cands else (FetchStatus.ERROR, [])
