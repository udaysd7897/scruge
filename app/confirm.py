"""Confirm a no-code apparel match (Myntra shows no brand style code): one photo-check call picks among the
top survivors; a confident result also needs MRP or the manufacturer to agree (user's option 2)."""
from __future__ import annotations

import random
import re
from dataclasses import replace

import httpx

from app.extract import myntra_pdp_maker
from app.matcher import Match, decide, score
from app.models import Category, Decision, FetchStatus, Platform, SourceProduct
from app.sources.http import fetch
from app.vision import PICK_MAX, judge, pick



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


async def _maker_ok(client, src: SourceProduct, cand) -> bool:
    if not (src.canon.maker and cand.platform == Platform.MYNTRA):
        return False
    st, html = await fetch(client, cand.url)
    return st == FetchStatus.OK and same_maker(src.canon.maker, myntra_pdp_maker(html))


async def confirm(client: httpx.AsyncClient, src: SourceProduct, m: Match, picker=pick) -> Match:
    """One photo-check call over the top survivors (shuffled; the table must back the answer):
    match k + (MRP equal or same manufacturer) → MATCH; match k alone → Possible, linked to k;
    a clean "none" → NONE (Not listed); unclear/no key/error → unchanged (Possible)."""
    if src.category != Category.APPAREL or m.decision != Decision.AMBIGUOUS or src.missing_required:
        return m
    mrp = src.canon.mrp
    top = sorted(m.survivors, key=lambda c: (not (mrp and c.canon.mrp == mrp),
                                             -score(src.canon, c, src.category)))[:PICK_MAX]
    shuffled = top[:]
    random.Random(src.asin or src.title).shuffle(shuffled)  # no listing is always "1"; reproducible per item
    verdict, k = judge(await picker(src, shuffled), len(shuffled))
    if verdict == "none":
        return Match(Decision.NONE, None, "photo", survivors=[], src=m.src, category=m.category,
                     checked=len(shuffled), none_had="the same design in its photo")
    if verdict != "match":
        return m
    cand = shuffled[k]
    if (mrp and cand.canon.mrp == mrp) or await _maker_ok(client, src, cand):
        cand.confirmed = True
        return decide(src, [cand])
    return replace(m, candidate=cand, reason="Photo matches, but neither MRP nor manufacturer confirms it")
