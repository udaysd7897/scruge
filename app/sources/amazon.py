from __future__ import annotations

import os
import re
from urllib.parse import urlparse

import httpx

from app.extract import from_amazon
from app.models import FetchStatus, SourceProduct
from app.sources import apify
from app.sources.apify import run_actor

ACTOR = "junglee~amazon-crawler"
_MSG = "Please paste an Amazon.in product link"
_ASIN = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", re.I)
_SHORT_HOSTS = {"amzn.in", "www.amzn.in", "amzn.to", "www.amzn.to", "a.co", "www.a.co"}


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
    status, items = await run_actor(
        client,
        ACTOR,
        {"categoryOrProductUrls": [{"url": dp}], "maxItemsPerStartUrl": 1, "scrapeProductDetails": True},
    )
    if status != FetchStatus.OK and not os.environ.get("APIFY_KEY") and not apify.OFFLINE:
        # not cached and no key: say so instead of a generic "try again"
        raise SourceError("APIFY_KEY is not set — see README")
    if status != FetchStatus.OK or not items:
        raise SourceError("Couldn't read this Amazon product right now. Please try again in a bit.")
    try:
        return from_amazon(items[0])
    except Exception:
        raise SourceError("Couldn't read this Amazon product right now.") from None
