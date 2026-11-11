from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from app.extract import REQUIRED, missing_required
from app.models import (Candidate, Canonical, Category, Decision, FetchStatus, Outcome, Platform,
                        PlatformResult, SourceProduct)
from app.normalize import (base_colour, colour_key, distinctive_words, is_accessory, model_base,
                           norm_brand, pack_count)


def _fmt(x) -> str:
    return str(int(x)) if isinstance(x, float) and x == int(x) else str(x)


def _both(a, b) -> bool:
    return a is not None and b is not None


def veto(src: Canonical, cand: Candidate, cat: Category) -> str | None:
    c = cand.canon
    if is_accessory(cand.title):
        return "accessory"
    sb, cb = norm_brand(src.brand), norm_brand(c.brand)
    if _both(sb, cb) and sb != cb:
        return "brand"
    if src.family and c.family and src.family != c.family:
        return "family"
    sm, cm = model_base(src.model_code), model_base(c.model_code)
    if _both(sm, cm) and sm != cm:
        return "model code"
    if cat == Category.PHONE:
        if _both(src.ram_gb, c.ram_gb) and src.ram_gb != c.ram_gb:
            return f"ram {_fmt(c.ram_gb)}≠{_fmt(src.ram_gb)}"
        if _both(src.storage_gb, c.storage_gb) and src.storage_gb != c.storage_gb:
            return f"storage {_fmt(c.storage_gb)}≠{_fmt(src.storage_gb)}"
    if cat == Category.TV:
        if _both(src.screen_in, c.screen_in) and abs(src.screen_in - c.screen_in) > 1:
            return "screen size"
    if cat in (Category.SNEAKER, Category.APPAREL):
        if cat == Category.APPAREL and _both(src.product_type, c.product_type) \
                and src.product_type != c.product_type:
            return "type"
        if cat == Category.SNEAKER and src.style_code and c.style_code \
                and _style_key(src.style_code) != _style_key(c.style_code):
            return "style code"
        if _both(src.base_colour, c.base_colour) and src.base_colour != c.base_colour:
            return "colour"
        if cat == Category.APPAREL and max(src.pack_count, pack_count(src.title)) != max(c.pack_count, pack_count(cand.title)):
            return "pack count"
        no_style = not (src.style_code and c.style_code)
        if (cat == Category.APPAREL or no_style) and _distinct_veto(src, cand):
            return "distinctive words"
    return None


def _style_key(code: str) -> str:
    return re.sub(r"[\s_]+", "", code.upper().replace("/", "-"))


def _distinct_veto(src: Canonical, cand: Candidate) -> bool:
    if not src.title:
        return False
    a = distinctive_words(src.title, src.brand)
    b = distinctive_words(cand.title, cand.canon.brand)
    if a or b:
        if not a or not b:
            return True
        m = min(len(a), len(b))
        score = len(a & b) / (m if m >= 2 else len(a | b))
        if score < 0.5:
            return True
    if src.family:
        toks = set(re.findall(r"[a-z0-9]+", (cand.title or "").lower())) | b
        if not set(src.family.split()) <= toks:
            return True
    return False


# ---------------------------------------------------------------- scoring (§6.5)

MARGIN = 0.15


def score(src: Canonical, cand: Candidate, cat: Category) -> float:
    c = cand.canon
    sm, cm = model_base(src.model_code), model_base(c.model_code)
    ident = (_both(sm, cm) and sm == cm) or (_both(src.ean, c.ean) and src.ean == c.ean)
    sk, ck = colour_key(src.colour), colour_key(c.colour)
    colour = _both(sk, ck) and sk == ck
    title = fuzz.token_sort_ratio((src.title or "").lower(), (cand.title or "").lower()) / 100
    req = REQUIRED.get(cat, [])
    present = (len(req) - len(missing_required(c, cat))) / len(req) if req else 1.0
    return 0.40 * ident + 0.25 * colour + 0.20 * title + 0.15 * present


# ---------------------------------------------------------------- decision (§6.6)

@dataclass
class Match:
    decision: Decision
    candidate: Candidate | None
    reason: str
    colour_fallback: bool = False
    survivors: list[Candidate] = field(default_factory=list)
    src: Canonical | None = None
    category: Category | None = None
    src_missing: list[str] = field(default_factory=list)
    checked: int = 0
    none_had: str | None = None


def _stock_rank(c: Candidate) -> int:
    return {True: 0, None: 1, False: 2}[c.in_stock]


def decide(src: SourceProduct, cands: list[Candidate]) -> Match:
    s, cat = src.canon, src.category
    base = dict(src=s, category=cat, src_missing=list(src.missing_required), checked=len(cands))
    vetoes, survivors = [], []
    for cand in cands:
        r = veto(s, cand, cat)
        (vetoes.append(r) if r else survivors.append(cand))
    if not survivors:
        return Match(Decision.NONE, None, "no survivors",
                     none_had=_none_had(s, cat, vetoes), **base)

    pool, fallback = survivors, False
    sk = colour_key(s.colour)
    if cat in (Category.PHONE, Category.TV) and sk:
        same = [c for c in survivors if colour_key(c.canon.colour) == sk]
        unknown = [c for c in survivors if colour_key(c.canon.colour) is None]
        other = [c for c in survivors if colour_key(c.canon.colour) not in (None, sk)]
        if same:
            pool = same
        elif unknown and other:
            # link the colourless listing: it may be the right colour, the others are not
            top = max(unknown, key=lambda c: score(s, c, cat))
            reason = ("Couldn't read " + _labels(src.missing_required) + " on Amazon"
                      if src.missing_required else "Colour unclear on this platform")
            return Match(Decision.AMBIGUOUS, top, reason, False, survivors, **base)
        elif unknown:
            pool = unknown
        else:
            pool, fallback = other, True
    scores = {id(c): score(s, c, cat) for c in pool}
    scored = sorted(pool, key=lambda c: -scores[id(c)])
    if fallback:
        # only candidates within the margin of the best are eligible; among them
        # prefer in-stock, then same base colour, then score
        best = scores[id(scored[0])]
        group = [c for c in scored if best - scores[id(c)] < MARGIN]
        sb = base_colour(s.colour) or s.base_colour
        scored = sorted(group, key=lambda c: (_stock_rank(c), not (sb and c.canon.base_colour == sb),
                                              -scores[id(c)]))
    top = scored[0]

    if src.missing_required:
        return Match(Decision.AMBIGUOUS, top, "Couldn't read " + _labels(src.missing_required) + " on Amazon",
                     fallback, pool, **base)
    if len(scored) >= 2 and not fallback:
        if scores[id(top)] - scores[id(scored[1])] < MARGIN:
            return Match(Decision.AMBIGUOUS, top, "tie", fallback, pool, **base)
    miss = missing_required(top.canon, cat)
    if miss:
        return Match(Decision.AMBIGUOUS, top, "Listing doesn't show " + _labels(miss),
                     fallback, pool, **base)
    return Match(Decision.MATCH, top, _matched_on(s, top, cat), fallback, pool, **base)


_LABELS = {"ram_gb": "RAM", "storage_gb": "storage", "screen_in": "screen size", "base_colour": "colour",
           "colour": "colour", "family": "model", "product_type": "product type", "brand": "brand"}


def _labels(fields: list[str]) -> str:
    out = []
    for f in fields:
        lab = _LABELS.get(f, f.replace("_", " "))
        if lab not in out:
            out.append(lab)
    return ", ".join(out)


def resolve_tie(m: Match, chosen: Candidate | None) -> Match:
    if m.decision != Decision.AMBIGUOUS or m.reason != "tie" or m.src_missing:
        return m
    if chosen is None or not any(chosen is c for c in m.survivors):
        return m
    if m.category and missing_required(chosen.canon, m.category):
        return m
    return Match(Decision.MATCH, chosen, _matched_on(m.src or Canonical(), chosen, m.category),
                 m.colour_fallback, m.survivors, m.src, m.category, m.src_missing, m.checked)


def _matched_on(s: Canonical, cand: Candidate, cat: Category | None) -> str:
    c, facts = cand.canon, []
    sm, cm = model_base(s.model_code), model_base(c.model_code)
    if _both(sm, cm) and sm == cm:
        facts.append(f"model {c.model_code}")
    elif _both(s.ean, c.ean) and s.ean == c.ean:
        facts.append("barcode")
    elif c.family or s.family:
        facts.append((c.family or s.family).title())
    if cat == Category.PHONE and c.ram_gb and c.storage_gb:
        facts.append(f"{_fmt(c.ram_gb)}GB/{_fmt(c.storage_gb)}GB")
    if cat == Category.TV and c.screen_in:
        facts.append(f'{_fmt(c.screen_in)}"')
    if c.colour:
        facts.append(c.colour)
    return "Matched on " + ", ".join(facts) if facts else "Matched"


def _none_had(s: Canonical, cat: Category, vetoes: list[str]) -> str | None:
    if not vetoes:
        return None
    r = Counter(v.split(" ")[0] if v.startswith(("ram ", "storage ")) else v for v in vetoes).most_common(1)[0][0]
    what = {
        "storage": s.storage_gb and f"{_fmt(s.storage_gb)}GB",
        "ram": s.ram_gb and f"{_fmt(s.ram_gb)}GB RAM",
        "family": s.family and f"model {s.family}",
        "model code": s.model_code and f"model {s.model_code}",
        "brand": s.brand and f"brand {s.brand}",
        "accessory": "a non-accessory listing",
        "screen size": s.screen_in and f'{_fmt(s.screen_in)}"',
        "colour": (s.colour or s.base_colour) and f"colour {s.colour or s.base_colour}",
        "type": s.product_type and f"type {s.product_type}",
        "style code": s.style_code and f"style {s.style_code}",
        "pack count": f"pack of {max(s.pack_count, pack_count(s.title))}",
        "distinctive words": "a matching title",
    }.get(r)
    return what or r


# ---------------------------------------------------------------- outcome (§6.7)

def to_result(platform: Platform, match: Match, statuses: list[FetchStatus],
              src_colour: str | None) -> PlatformResult:
    m, cand = match, match.candidate
    if m.decision == Decision.NONE or cand is None:
        if not statuses:
            return PlatformResult(platform, Outcome.COULDNT_CHECK, None,
                                  f"Couldn't check {platform.value.capitalize()}: no search was completed")
        if any(st in (FetchStatus.BLOCKED, FetchStatus.ERROR) for st in statuses):
            return PlatformResult(platform, Outcome.COULDNT_CHECK, None,
                                  f"Couldn't check: {platform.value.capitalize()} was blocked or errored")
        if m.checked == 0:
            reason = f"Not listed: no results on {platform.value.capitalize()}"
        else:
            reason = f"Not listed: {m.checked} candidates checked, none had {m.none_had or 'a match'}"
        return PlatformResult(platform, Outcome.NOT_LISTED, None, reason)

    note = None
    if m.colour_fallback and src_colour and cand.canon.colour:
        note = f"Not available in {src_colour}; showing {cand.canon.colour}"
    if m.decision == Decision.AMBIGUOUS:
        reason = "Several listings look equally close" if m.reason == "tie" else m.reason
        return PlatformResult(platform, Outcome.POSSIBLE, cand.url, reason, note)
    if cand.in_stock is None:
        return PlatformResult(platform, Outcome.POSSIBLE, cand.url,
                              "Matched, but stock status couldn't be read", note)
    outcome = Outcome.IN_STOCK if cand.in_stock else Outcome.OUT_OF_STOCK
    return PlatformResult(platform, outcome, cand.url, m.reason, note)
