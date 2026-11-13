from __future__ import annotations

import logging
import os
import re
from urllib.parse import urlparse

import httpx

from app.extract import from_amazon
from app.models import FetchStatus, SourceProduct
from app.sources import apify
from app.sources.amazon_page import looks_like_product, parse_amazon_page
from app.sources.apify import run_actor
from app.sources.http import fetch

ACTOR = "junglee~amazon-crawler"
_MSG = "Please paste an Amazon.in product link"
_ASIN = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", re.I)
_SHORT_HOSTS = {"amzn.in", "www.amzn.in", "amzn.to", "www.amzn.to", "a.co", "www.a.co"}


log = logging.getLogger(__name__)


def _summary(sp) -> str:
    c = sp.canon
    keys = ("brand", "family", "model_code", "ram_gb", "storage_gb", "screen_in", "colour", "style_code", "gender", "mrp")
    return f"asin={sp.asin} cat={sp.category.value} missing={sp.missing_required} " + \
        " ".join(f"{k}={getattr(c, k)!r}" for k in keys if getattr(c, k) not in (None, ""))


class SourceError(Exception):
    pass


def _with_scheme(url: str) -> str:
    # "amazon.in/dp/…" or "www.amazon.in/…" pasted without https://
    url = url.strip()
    return url if re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I) else "https://" + url


def _is_amazon_in(host: str) -> bool:
    return host == "amazon.in" or host.endswith(".amazon.in")


def amazon_dp_url(url: str) -> str | None:
    p = urlparse(_with_scheme(url))
    if not _is_amazon_in((p.hostname or "").lower()):
        return None
    m = _ASIN.search(p.path)
    return f"https://www.amazon.in/dp/{m.group(1).upper()}" if m else None


async def resolve_amazon_url(client: httpx.AsyncClient, url: str) -> str:
    url = _with_scheme(url)
    host = (urlparse(url).hostname or "").lower()
    if host in _SHORT_HOSTS:
        try:
            r = await client.get(url, follow_redirects=True)
            final = str(r.url)
        except httpx.HTTPError:
            raise ValueError(_MSG) from None
        out = amazon_dp_url(final)
    else:
        out = amazon_dp_url(url)
    if not out:
        raise ValueError(_MSG)
    return out


async def get_source(client: httpx.AsyncClient, url: str) -> SourceProduct:
    dp = await resolve_amazon_url(client, url)
    payload = {"categoryOrProductUrls": [{"url": dp}], "maxItemsPerStartUrl": 1, "scrapeProductDetails": True}
    # 0. an Apify answer already paid for (richer than the page parser); 1. the product page (free);
    # 2. Apify live (paid) when the page is blocked or unreadable
    cached = apify._read_cache(ACTOR, payload)
    if cached:
        try:
            sp = from_amazon(cached[0])
            log.info("amazon source via Apify cache: %s", _summary(sp))
            return sp
        except Exception:
            log.exception("amazon cached item unreadable")
    st, html = await fetch(client, dp)
    log.info("amazon page %s %s (%dB)", dp, st.value, len(html))
    if st == FetchStatus.OK:
        item = parse_amazon_page(html, dp)
        if looks_like_product(item):
            try:
                sp = from_amazon(item)
                log.info("amazon source via page: %s", _summary(sp))
                return sp
            except Exception:
                log.exception("amazon page parse failed")
        else:
            log.info("amazon page not readable as a product (no title/asin)")
    log.info("amazon falling back to Apify")
    status, items = await run_actor(
        client,
        ACTOR,
        {"categoryOrProductUrls": [{"url": dp}], "maxItemsPerStartUrl": 1, "scrapeProductDetails": True},
    )
    if status != FetchStatus.OK and not os.environ.get("APIFY_KEY") and not apify.OFFLINE:
        # not cached and no key: say so instead of a generic "try again"
        raise SourceError("APIFY_KEY is not set — see README")
    log.info("amazon Apify %s items=%d", status.value, len(items or []))
    if status != FetchStatus.OK or not items:
        raise SourceError("Couldn't read this Amazon product right now. Please try again in a bit.")
    try:
        return from_amazon(items[0])
    except Exception:
        raise SourceError("Couldn't read this Amazon product right now.") from None
