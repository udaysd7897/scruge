"""Confirm a no-code apparel match (Myntra shows no brand style code). A survivor is confirmed only when
its MRP equals Amazon's, its product page names the same manufacturer, and the photo check says SAME.
Exactly one confirmed survivor → MATCH; anything else leaves the result as Possible match."""
from __future__ import annotations

import asyncio
import re

import httpx

from app.extract import myntra_pdp_maker
from app.matcher import Match, decide, score
from app.models import Category, Decision, FetchStatus, Platform, SourceProduct
from app.sources.http import fetch
from app.vision import same_product

TOP = 3


def same_maker(a: str | None, b: str | None) -> bool:
    """Same manufacturer despite wording: the same 6-digit PIN code and most words of the shorter text
    in the longer ("... kadubeesanahalli varthur hobli bengaluru 560103" vs "... kadubeesanahalli bengaluru
    560103"; "modenik lifestyle ... formerly dixcy textiles ..." vs "dixcy textiles ...")."""
    if not a or not b:
        return False
    pa, pb = re.findall(r"\b\d{6}\b", a), re.findall(r"\b\d{6}\b", b)
    if not pa or not pb or pa[-1] != pb[-1]:
        return False
    ta, tb = set(a.split()), set(b.split())
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return len(short & long_) / len(short) >= 0.8


async def _passes(client, src: SourceProduct, cand, vision) -> bool:
    s, c = src.canon, cand.canon
    if not (s.mrp and c.mrp and s.mrp == c.mrp):
        return False
    if s.maker:
        if cand.platform != Platform.MYNTRA:
            return False
        st, html = await fetch(client, cand.url)
        if st != FetchStatus.OK or not same_maker(s.maker, myntra_pdp_maker(html)):
            return False
    return await vision(src, cand) == "SAME"


async def confirm(client: httpx.AsyncClient, src: SourceProduct, m: Match, vision=same_product) -> Match:
    if src.category != Category.APPAREL or m.decision != Decision.AMBIGUOUS or src.missing_required:
        return m
    # equal MRP first (Levi's: ₹649 on both), then score; MRP is checked again in _passes
    same_mrp = [c for c in m.survivors if src.canon.mrp and c.canon.mrp == src.canon.mrp]
    top = sorted(same_mrp, key=lambda c: -score(src.canon, c, src.category))[:TOP]
    ok = await asyncio.gather(*(_passes(client, src, c, vision) for c in top))
    passed = [c for c, good in zip(top, ok) if good]
    if len(passed) != 1:
        return m
    passed[0].confirmed = True
    return decide(src, [passed[0]])
