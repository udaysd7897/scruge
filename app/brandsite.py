"""Style code → the brand's own product name (the name Myntra lists). Only brands whose site answers a
plain request are supported; others return None and the app falls back to Amazon's title."""
from __future__ import annotations

import re

import httpx

from app.models import FetchStatus
from app.sources.http import fetch

_CACHE: dict[tuple[str, str], str | None] = {}


def puma_name(html: str, style: str) -> str | None:
    m = re.search(rf"/in/en/pd/([a-z0-9-]+)/{re.escape(style[:6])}", html)
    return m.group(1).replace("-", " ") if m else None


async def official_name(client: httpx.AsyncClient, brand: str | None, style: str | None) -> str | None:
    if brand != "puma" or not style or not re.fullmatch(r"\d{6}[-_]?\d{0,2}", style):
        return None
    key = (brand, style[:6])
    if key not in _CACHE:
        st, html = await fetch(client, f"https://in.puma.com/in/en/search?q={style[:6]}")
        _CACHE[key] = puma_name(html, style) if st == FetchStatus.OK else None
    return _CACHE[key]
