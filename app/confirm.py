"""Confirm a no-code apparel match (Myntra shows no brand style code): one photo-check call picks among the
top survivors; a confident result also needs MRP or the manufacturer to agree (user's option 2)."""
from __future__ import annotations

import random
import re
from dataclasses import replace

import httpx

from app.extract import myntra_pdp_maker
from app.normalize import distinctive_words
from app.matcher import Match, decide, score
from app.models import Category, Decision, FetchStatus, Platform, SourceProduct
from app.sources.myntra import myntra_fetch
from app.vision import HARD_ATTRS, PICK_MAX, attrs_for, differences, judge, pick

CLOSEST_MAX = 3



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


def _size_key(c):
    """Flipkart lists each shoe size separately ("Sparx SM 734 ... (White , 9)"): same specific title,
    colour and MRP is one shoe. A generic title ("Sneakers For Men") identifies nothing: keep it apart."""
    title = re.sub(r"\W+", " ", (c.title or "").lower()).strip()
    if len(distinctive_words(c.title, c.canon.brand)) < 2:
        return c.url
    return title, (c.canon.colour or "").lower(), c.canon.mrp


async def _maker_ok(client, src: SourceProduct, cand) -> bool:
    if not src.canon.maker:
        return False
    if cand.canon.maker:  # Flipkart shows it on the product page we already read
        return same_maker(src.canon.maker, cand.canon.maker)
    if cand.platform != Platform.MYNTRA:
        return False
    st, html = await myntra_fetch(client, cand.url)
    return st == FetchStatus.OK and same_maker(src.canon.maker, myntra_pdp_maker(html))


async def confirm(client: httpx.AsyncClient, src: SourceProduct, m: Match, picker=pick) -> Match:
    """One photo-check call over the top survivors (shuffled; the table must back the answer):
    match k + (MRP equal or same manufacturer) → MATCH; match k alone → Possible, linked to k;
    a clean "none" → NONE (Not listed); unclear/no key/error → unchanged (Possible)."""
    if src.category not in (Category.APPAREL, Category.SNEAKER) or m.decision != Decision.AMBIGUOUS \
            or src.missing_required:
        return m
    mrp = src.canon.mrp
    ranked = sorted(m.survivors, key=lambda c: (not (mrp and c.canon.mrp == mrp),
                                                -score(src.canon, c, src.category)))
    # sizes of one shoe are separate Flipkart listings: one photo slot per title + colour. Not for apparel:
    # two different prints often share a generic title ("Bewakoof Men Black T-shirt")
    top, seen = [], set()
    for c in ranked:
        key = _size_key(c) if src.category == Category.SNEAKER else c.url
        if key not in seen:
            seen.add(key)
            top.append(c)
    top = top[:PICK_MAX]
    attrs = attrs_for(src.category)
    shuffled = top[:]
    random.Random(src.asin or src.title).shuffle(shuffled)  # no listing is always "1"; reproducible per item
    res = await picker(src, shuffled)
    verdict, k = judge(res, len(shuffled), attrs)
    if verdict == "none":
        # still Not listed, but these passed every hard check: show the nearest designs (fewest
        # differing attributes; equal MRP / higher score break ties via the pre-shuffle order)
        diffs = {id(c): d for c, d in zip(shuffled, differences(res, len(shuffled), attrs))}
        # only near designs: a shoe that differs on 6 of 7 attributes is not "close", and neither is one
        # whose photo shows a different neck/colour/cut (the text gate would have rejected it, had the
        # text said so)
        near = sorted([c for c in top if len(diffs[id(c)]) <= len(attrs) // 2
                       and not HARD_ATTRS & set(diffs[id(c)])],
                      key=lambda c: len(diffs[id(c)]))[:CLOSEST_MAX]
        return Match(Decision.NONE, None, "photo", survivors=[], src=m.src, category=m.category,
                     checked=len(shuffled), none_had="the same design in its photo",
                     closest=([(c, diffs[id(c)]) for c in near] + m.closest)[:CLOSEST_MAX])  # + fabric-different
    if verdict != "match":
        return m
    cand = shuffled[k]
    if (mrp and cand.canon.mrp == mrp) or await _maker_ok(client, src, cand):
        cand.confirmed = True
        return decide(src, [cand])
    return replace(m, candidate=cand, reason="Photo matches, but neither MRP nor manufacturer confirms it")
