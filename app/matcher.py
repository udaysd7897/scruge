from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from app.extract import REQUIRED, missing_required
from app.models import (Candidate, Canonical, Category, Decision, FetchStatus, Outcome, Platform,
                        PlatformResult, SourceProduct)
from app.normalize import (DESCRIPTOR_WORDS, base_colour, clean_ean, colour_key, distinctive_words, is_accessory,
                           model_base, norm_brand, pack_count)


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
    # sneaker/apparel model lines are worded differently per store ("Grand Court 3.0 Sneaker" vs
    # "Grand Court 3.0 Tennis Shoes"): they rely on the distinctive-word veto below instead
    if src.family and c.family and src.family != c.family and cat not in (Category.SNEAKER, Category.APPAREL):
        if cat != Category.TV or not _tv_family_overlap(src.family, c.family, cand.title):
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
        if _both(src.gender, c.gender) and "unisex" not in (src.gender, c.gender) and src.gender != c.gender:
            return "gender"
        if cat == Category.APPAREL and _both(src.product_type, c.product_type) \
                and src.product_type != c.product_type:
            return "type"
        if _both(src.style_code, c.style_code) and not same_style(src, c):
            return "style code"
        if _both(src.base_colour, c.base_colour) and src.base_colour != c.base_colour:
            return "colour"
        if cat == Category.APPAREL and max(src.pack_count, pack_count(src.title)) != max(c.pack_count, pack_count(cand.title)):
            return "pack count"
        # an equal brand style code is identity: store titles are rewritten per store, so title words
        # are only compared when no shared code proves the product
        if not same_style(src, c) and (cat == Category.APPAREL or not _both(src.style_code, c.style_code)) \
                and _distinct_veto(src, cand):
            return "distinctive words"
    return None


def same_style(a: Canonical, b: Canonical) -> bool:
    """Both listings carry the same brand style code (case/space/-/_ insensitive: 528856_01 = 52885601)."""
    return _both(a.style_code, b.style_code) and _style_key(a.style_code) == _style_key(b.style_code)


def _doubt(src: Canonical, cand: Candidate, cat: Category) -> str | None:
    """Why a sneaker/apparel survivor can't be confirmed even though no veto applies (§ anti-goal:
    a doubtful survivor is shown as "Possible match", never as a confident one)."""
    if cat not in (Category.SNEAKER, Category.APPAREL):
        return None
    if same_style(src, cand.canon):
        return None  # the brand style code proves the product
    a, b = distinctive_words(_src_text(src), src.brand), distinctive_words(cand.title, cand.canon.brand)
    if not a or not b:
        return "Title too generic to confirm the model"
    # listing words the Amazon title never mentions ("Graphic Printed", "React"): a different design
    src_toks = set(re.findall(r"[a-z0-9]+", _src_text(src).lower().replace("t-shirt", "tshirt")))
    if b - src_toks - DESCRIPTOR_WORDS:
        return "Listing title has words the Amazon title doesn't"
    if cat == Category.SNEAKER and src.family and cand.canon.family and src.family != cand.canon.family:
        return "Model name differs slightly on this listing"
    if cat == Category.APPAREL and not cand.confirmed:
        # no shared style code (Myntra never shows one): name agreement alone is not proof
        return NEEDS_CONFIRM
    return None


NEEDS_CONFIRM = "No style code on this listing: matched by name only"


def _tv_family_overlap(a: str, b: str, title: str) -> bool:
    """TV series names differ per store ("nu87 nano" / "nu870b" / "55nu870bpla"): compatible when a
    series word of one appears inside the other (or the candidate title)."""
    ca, cb = a.replace(" ", ""), (b + (title or "")).lower().replace(" ", "")
    return any(len(t) >= 3 and t in cb for t in a.split()) or \
        any(len(t) >= 3 and t in ca for t in b.split())


def _style_key(code: str) -> str:
    return re.sub(r"[\s_]+", "", code.upper().replace("/", "-"))


def _src_text(src: Canonical) -> str:
    """What the listing title is compared with: the brand's official product name when known (Amazon's
    fashion titles are generic: "Puma Men Polyester Solid Regular Fit T-Shirt"), else Amazon's title."""
    return f"{src.brand or ''} {src.official_name}".strip() if src.official_name else src.title


def _distinct_veto(src: Canonical, cand: Candidate) -> bool:
    if not _src_text(src):
        return False
    a = distinctive_words(_src_text(src), src.brand)
    b = distinctive_words(cand.title, cand.canon.brand)
    if not a or not b:
        # one title is too generic to compare: not a veto; decide() caps it at "Possible match"
        return False
    if a or b:
        m = min(len(a), len(b))
        score = len(a & b) / (m if m >= 2 else len(a | b))
        if score < 0.5:
            return True
    if src.family and not src.official_name:
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
    if cat == Category.PHONE and sk:  # spec §6.2: TV colour is ignored
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
    doubt = None
    if cat in (Category.SNEAKER, Category.APPAREL):
        doubts = {id(c): _doubt(s, c, cat) for c in pool}
        clear = [c for c in pool if doubts[id(c)] is None]
        # listings whose only gap is the missing style code come before ones with other doubts:
        # confirm.py can still prove them (MRP + manufacturer + photo)
        name_only = [c for c in pool if doubts[id(c)] == NEEDS_CONFIRM]
        if clear:
            pool = clear
        elif name_only:
            pool, doubt = name_only, NEEDS_CONFIRM
        else:
            doubt = doubts[id(max(pool, key=lambda c: score(s, c, cat)))]
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
    if doubt:
        # before the tie check: the LLM tie-break must not turn a doubtful listing into a match
        return Match(Decision.AMBIGUOUS, top, doubt, fallback, pool, **base)
    if len(scored) >= 2 and not fallback:
        if scores[id(top)] - scores[id(scored[1])] < MARGIN:
            group = [c for c in scored if scores[id(top)] - scores[id(c)] < MARGIN]
            if not _all_duplicates(group):
                return Match(Decision.AMBIGUOUS, top, "tie", fallback, pool, **base)
            top = min(group, key=lambda c: (c.in_stock is not True, c.price is None,
                                            c.price or 0, -scores[id(c)]))
    miss = _unconfirmed(s, top, cat)
    if cat == Category.TV and not s.model_code:
        return Match(Decision.AMBIGUOUS, top, "Couldn't read model number on Amazon", fallback, pool, **base)
    if miss:
        return Match(Decision.AMBIGUOUS, top, "Listing doesn't show " + _labels(miss),
                     fallback, pool, **base)
    return Match(Decision.MATCH, top, _matched_on(s, top, cat), fallback, pool, **base)


def _unconfirmed(s: Canonical, cand: Candidate, cat: Category) -> list[str]:
    """Required fields the listing doesn't show. A TV identified by model number on Amazon can only
    be confirmed by a listing that shows a model number too."""
    miss = missing_required(cand.canon, cat)
    if cat == Category.TV and not (s.model_code and cand.canon.model_code):
        miss.append("model_code")  # no model number on one side: identity can't be confirmed
    return miss


def _dup_code(c: Candidate) -> str | None:
    mc = c.canon.model_code
    return re.sub(r"\s+", "", mc).upper() if mc else None


def _all_duplicates(group: list[Candidate]) -> bool:
    """True when every listing in group is the same product listed more than once."""
    eans = {clean_ean(c.canon.ean) if c.canon.ean else None for c in group}
    if len(eans) == 1 and None not in eans:
        return True
    codes = {_dup_code(c) for c in group}
    if len(codes) != 1 or None in codes:
        return False
    return len({(c.canon.ram_gb, c.canon.storage_gb, colour_key(c.canon.colour), c.canon.screen_in)
                for c in group}) == 1


_LABELS = {"ram_gb": "RAM", "storage_gb": "storage", "screen_in": "screen size", "base_colour": "colour",
           "colour": "colour", "family": "model", "model_code": "model number", "product_type": "product type", "brand": "brand"}


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
    if m.category and _unconfirmed(m.src or Canonical(), chosen, m.category):
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
    elif same_style(s, c):
        facts.append(f"style {c.style_code}")
    elif cand.confirmed:
        facts.append("name, MRP, manufacturer and photo")
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
