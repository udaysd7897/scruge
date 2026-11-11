"""Confirm a no-code apparel match (Myntra shows no brand style code). A survivor is confirmed only when
its MRP equals Amazon's, its product page names the same manufacturer, and the photo check says SAME.
Exactly one confirmed survivor → MATCH; anything else leaves the result as Possible match."""
from __future__ import annotations

import asyncio

import httpx

from app.extract import myntra_pdp_maker
from app.matcher import Match, decide, score
from app.models import Category, Decision, FetchStatus, Platform, SourceProduct
from app.sources.http import fetch
from app.vision import same_product

TOP = 3


async def _passes(client, src: SourceProduct, cand, vision) -> bool:
    s, c = src.canon, cand.canon
    if not (s.mrp and c.mrp and s.mrp == c.mrp):
        return False
    if s.maker:
        if cand.platform != Platform.MYNTRA:
            return False
        st, html = await fetch(client, cand.url)
        if st != FetchStatus.OK or myntra_pdp_maker(html) != s.maker:
            return False
    return await vision(src, cand) == "SAME"


async def confirm(client: httpx.AsyncClient, src: SourceProduct, m: Match, vision=same_product) -> Match:
    if src.category != Category.APPAREL or m.decision != Decision.AMBIGUOUS or src.missing_required:
        return m
    top = sorted(m.survivors, key=lambda c: -score(src.canon, c, src.category))[:TOP]
    ok = await asyncio.gather(*(_passes(client, src, c, vision) for c in top))
    passed = [c for c, good in zip(top, ok) if good]
    if len(passed) != 1:
        return m
    passed[0].confirmed = True
    return decide(src, [passed[0]])
