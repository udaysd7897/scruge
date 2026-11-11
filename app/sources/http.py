from __future__ import annotations

import re

import httpx

from app.models import FetchStatus

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"}
# Real product pages embed words like "captcha"/"Access Denied" in their JS bundles, so the
# soft markers only count on small (challenge-sized) bodies; bm-verify counts anywhere.
_SOFT_MARKERS = ("access denied", "robot check", "captcha")
_SOFT_MAX_BYTES = 20_000
_META_REFRESH = re.compile(r"<meta[^>]+http-equiv=[\"']?refresh", re.I)


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20)


def classify(status_code: int, body: str) -> FetchStatus:
    if status_code in (403, 429, 503, 529):
        return FetchStatus.BLOCKED
    low = body.lower()
    size = len(body.encode("utf-8", "ignore"))
    if "bm-verify" in low or (size < _SOFT_MAX_BYTES and any(m in low for m in _SOFT_MARKERS)):
        return FetchStatus.BLOCKED
    if size < 3000 and _META_REFRESH.search(body):
        return FetchStatus.BLOCKED
    if not 200 <= status_code < 300:
        return FetchStatus.ERROR
    return FetchStatus.OK


async def fetch(client: httpx.AsyncClient, url: str) -> tuple[FetchStatus, str]:
    try:
        r = await client.get(url)
    except httpx.HTTPError:
        return FetchStatus.ERROR, ""
    return classify(r.status_code, r.text), r.text
