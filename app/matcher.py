from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from app.extract import REQUIRED, missing_required
from app.models import (Candidate, Canonical, Category, Decision, FetchStatus, Outcome, Platform,
                        PlatformResult, SourceProduct)
from app.normalize import (CODE_BRANDS, colour_set, fabric_set, DESCRIPTOR_WORDS, base_colour, clean_ean, colour_key, distinctive_words, is_accessory,
                           model_base, norm_brand, pack_count, tv_code)


def _fmt(x) -> str:
    return str(int(x)) if isinstance(x, float) and x == int(x) else str(x)


def _both(a, b) -> bool:
    return a is not None and b is not None


def veto(src: Canonical, cand: Candidate, cat: Category) -> str | None:
    c = cand.canon
    if is_accessory(cand.title):
        return "accessory"
    sb, cb = norm_brand(src.brand), norm_brand(c.brand)
    if _both(sb, cb) and sb != cb and not (src.brand_guessed and cb.startswith(sb + " ")):
        return "brand"  # a guessed "red" (title's first word) still fits "red tape"
    # sneaker/apparel model lines are worded differently per store ("Grand Court 3.0 Sneaker" vs
    # "Grand Court 3.0 Tennis Shoes"): they rely on the distinctive-word veto below instead
    if src.family and c.family and src.family != c.family and cat not in (Category.SNEAKER, Category.APPAREL):
        if cat != Category.TV or not _tv_family_overlap(src.family, c.family, cand.title):
            return "family"
    if cat == Category.TV and tv_code(src.model_code) and tv_code(c.model_code):
        if tv_code(src.model_code) != tv_code(c.model_code):
            return "model code"
    else:
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
        # hard gates (reports/Reliable apparel matching like Google.md): reject only when both sides
        # are known and differ; "unknown" never rejects
        if cat == Category.APPAREL and c.kind == "other":
            return "category"  # the store files it as a watch, slides, a shirt ...
        if _both(src.gender, c.gender) and "unisex" not in (src.gender, c.gender) and src.gender != c.gender:
            return "gender"
        if cat == Category.APPAREL and _both(src.neck, c.neck) and src.neck != c.neck:
            return "neck"  # collar vs round neck is a different product (only colour/size/pattern vary)
        if cat == Category.APPAREL and _both(src.product_type, c.product_type) \
                and src.product_type != c.product_type and {src.product_type, c.product_type} != {"tee", "polo"}:
            return "type"  # tee vs polo is decided by the neck gate (a "collared T-shirt" is a polo)
        if _both(src.style_code, c.style_code) and not same_style(src, c) and _code_brand(src, c):
            return "style code"
        if cat == Category.SNEAKER:
            if _colour_clash(src, c):
                return "colour"
        elif _both(src.base_colour, c.base_colour) and src.base_colour != c.base_colour:
            return "colour"
        if cat == Category.APPAREL and max(src.pack_count, pack_count(src.title)) != max(c.pack_count, pack_count(cand.title)):
            return "pack count"
        # an equal brand style code is identity: store titles are rewritten per store, so title words
        # are only compared when no shared code proves the product
        # unequal codes only stand in for the title check when the brand's codes are trusted (Nike, Puma):
        # Bacca Bucci BBMH9103A-09 vs the "Matrix" listing's BBMH9133 says nothing, the words do
        if not same_style(src, c) and (cat == Category.APPAREL or not _both(src.style_code, c.style_code)
                                       or not _code_brand(src, c)) \
                and _distinct_veto(src, cand, cat):
            return "distinctive words"
    return None




def _one(x: str | None) -> frozenset[str]:
    return frozenset([x]) if x else frozenset()


def _colour_clash(a: Canonical, b: Canonical) -> bool:
    """Sneaker colourways as colour sets (sole colours dropped): both multi-colour → the sets must be
    equal ("Black, White" = "Black and White" ≠ "Grey, White"); a single colour must be one of the other's
    ("White" fits "Sail/Gum Yellow/Midnight Navy" = {white, navy}). Unknown never clashes."""
    sa, sb = colour_set(a.colour) or _one(a.base_colour), colour_set(b.colour) or _one(b.base_colour)
    if not sa or not sb:
        return False
    if len(sa) >= 2 and len(sb) >= 2:
        return sa != sb
    return not (sa <= sb or sb <= sa)


def _code_brand(a: Canonical, b: Canonical) -> bool:
    return norm_brand(a.brand) in CODE_BRANDS or norm_brand(b.brand) in CODE_BRANDS


def same_style(a: Canonical, b: Canonical) -> bool:
    """Both listings carry the same brand style code. Equal ignoring case/space/-/_ (528856_01 = 52885601),
    or the same digit groups when stores add their own letters/size: AUSK-04065-L = ASSKC-04065,
    60001 = IHQTS1LDS60001. A different colourway number (DV2789-100 vs -101) is a different style."""
    if not _both(a.style_code, b.style_code):
        return False
    if _style_key(a.style_code) == _style_key(b.style_code):
        return True
    ka, kb = _style_key(a.style_code), _style_key(b.style_code)
    if ka.startswith(kb) or kb.startswith(ka):
        return True  # Amazon adds a suffix: BBMH9103A-09 vs Flipkart BBMH9103A
    ga, gb = _digit_groups(a.style_code), _digit_groups(b.style_code)
    if not (ga and ga == gb and any(len(g) >= 4 for g in ga)):
        return False  # a 3-digit-only overlap (SM-734 ~ SD0734G) helps ranking, it never proves the product
    # same digits, but a different letter right after them is a sibling: BBMH9103A vs BBMH9103B,
    # 9930-0105-WHITE vs 9930-0105-LTDML. A letter on one side only is a store suffix (AUSK-04065-L)
    for g in ga:
        na, nb = _after(ka, g), _after(kb, g)
        if na and nb and na != nb:
            return False
    return True


def _after(key: str, group: str) -> str:
    m = re.search(rf"(?<!\d){group}(?!\d)([A-Z]?)", key)
    return m.group(1) if m else ""


def _title_has_model_number(src: Canonical, cand: Candidate) -> bool:
    """A short brand model number printed in the listing's own title, same letters and number: Amazon
    SM-734 ↔ "Sparx SM 734 | Stylish ..." (not "SX 734"). Only for short codes (letters + 3-4 digits)."""
    m = re.fullmatch(r"([A-Z]{1,4})-(\d{3,4})", src.style_code or "")
    return bool(m) and bool(re.search(rf"\b{m.group(1)}[\s-]?0*{m.group(2)}\b", (cand.title or "").upper()))


def _digit_groups(code: str) -> frozenset[str]:
    return frozenset(re.findall(r"\d{3,}", code))


def _doubt(src: Canonical, cand: Candidate, cat: Category) -> str | None:
    """Why a sneaker/apparel survivor can't be confirmed even though no veto applies (§ anti-goal:
    a doubtful survivor is shown as "Possible match", never as a confident one)."""
    if cat not in (Category.SNEAKER, Category.APPAREL):
        return None
    if same_style(src, cand.canon) or _title_has_model_number(src, cand):
        return None  # the brand style code proves the product
    if cat in (Category.APPAREL, Category.SNEAKER):
        # store titles are rewritten per store; MRP + manufacturer + photo (confirm.py) decide instead
        return None if cand.confirmed else NEEDS_CONFIRM
    a, b = distinctive_words(_src_text(src, cat), src.brand), distinctive_words(cand.title, cand.canon.brand)
    if not a or not b:
        return "Title too generic to confirm the model"
    # listing words the Amazon title never mentions ("Graphic Printed", "React"): a different design
    src_toks = set(re.findall(r"[a-z0-9]+", _src_text(src, cat).lower().replace("t-shirt", "tshirt")))
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
    return re.sub(r"[\s_\-/]+", "", code.upper())


def _src_text(src: Canonical, cat: Category | None = None) -> str:
    """What the listing title is compared with: the brand's official product name when known (Amazon's
    fashion titles are generic: "Puma Men Polyester Solid Regular Fit T-Shirt"), else Amazon's title."""
    if src.official_name:
        return f"{src.brand or ''} {src.official_name}".strip()
    if cat == Category.SNEAKER and src.model_name and src.model_name not in (src.title or "").lower():
        return f"{src.brand or ''} {src.model_name} {src.title or ''}".strip()  # "Stride Eclipse" isn't in the title
    return src.title


def _distinct_veto(src: Canonical, cand: Candidate, cat: Category | None = None) -> bool:
    if not _src_text(src, cat):
        return False
    a = distinctive_words(_src_text(src, cat), src.brand)
    b = distinctive_words(cand.title, cand.canon.brand)
    if len(a) <= 1 or len(b) <= 1:
        # one title is too generic to compare ("Levis Men Soft Pure Cotton Round Neck Tshirt" → {soft}):
        # not a veto; decide() caps it at "Possible match" unless confirm.py proves it
        return False
    if a or b:
        m = min(len(a), len(b))
        score = len(a & b) / (m if m >= 2 else len(a | b))
        if score < 0.5:
            return True
    # Amazon's own model words ("025 premium soft") are store copy: when the source carries a brand style
    # code, a listing without the code can't contradict it on wording — confirm.py decides instead
    if src.family and not src.official_name and not src.style_code:
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
    title = fuzz.token_sort_ratio(_src_text(src, cat).lower(), (cand.title or "").lower()) / 100
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
    closest: list[tuple[Candidate, list[str]]] = field(default_factory=list)  # (listing, what differs)


def _stock_rank(c: Candidate) -> int:
    return {True: 0, None: 1, False: 2}[c.in_stock]


def fabric_clash(src: Canonical, cand: Candidate, cat: Category) -> bool:
    """Both titles name a fabric and they don't overlap (polyester microfiber vs pure cotton): not the exact
    product. Soft: such a listing is never a match, but it is shown as a closest option."""
    if cat != Category.APPAREL:
        return False
    fa, fb = fabric_set(src.title, src.brand), fabric_set(cand.title, cand.canon.brand)
    return bool(fa and fb and not fa & fb)


CLOSEST_MAX = 3


def decide(src: SourceProduct, cands: list[Candidate]) -> Match:
    """_decide on the listings that can be the product; listings that pass every hard check but differ in
    fabric are set aside as closest options (user 2026-11-13: show them, don't hide them)."""
    s, cat = src.canon, src.category
    off = [c for c in cands if veto(s, c, cat) is None and fabric_clash(s, c, cat)]
    if not off:
        return _decide(src, cands)
    m = _decide(src, [c for c in cands if not any(c is o for o in off)])
    m.checked = len(cands)
    m.closest = [(c, ["fabric"]) for c in sorted(off, key=lambda c: -score(s, c, cat))[:CLOSEST_MAX]]
    if m.decision == Decision.NONE and m.reason == "no survivors":
        vetoes = [r for c in cands if (r := veto(s, c, cat))] + ["fabric"] * len(off)
        m.none_had = _none_had(s, cat, vetoes)
    return m


def _decide(src: SourceProduct, cands: list[Candidate]) -> Match:
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
            group = _proven_same_model(s, group, cat) or group
            if not _all_duplicates(group) and len(group) > 1:
                return Match(Decision.AMBIGUOUS, top, "tie", fallback, pool, **base)
            top = min(group, key=lambda c: (c.in_stock is not True, c.price is None,
                                            c.price or 0, -scores[id(c)]))
    miss = _unconfirmed(s, top, cat)
    if same_style(s, top.canon):
        # the brand style code proves the product: a store that files it as "vest" rather than "tee"
        # (Flipkart's Jockey 9930) doesn't need to show a product type
        miss = [f for f in miss if f != "product_type"]
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


def _proven_same_model(s: Canonical, group: list[Candidate], cat: Category) -> list[Candidate] | None:
    """Sneakers whose every tied listing is proven the same model (style code or the model number in its
    title): keep those with exactly the source's colours; if they then all show the same colours, they are
    copies of one product (several sellers of "Sparx SM 734", White) → a one-item group."""
    if cat != Category.SNEAKER or not all(same_style(s, c.canon) or _title_has_model_number(s, c) for c in group):
        return None
    want = colour_set(s.colour)
    exact = [c for c in group if want and colour_set(c.canon.colour) == want]
    if not exact:
        return None
    return exact[:1] if len({colour_set(c.canon.colour) for c in exact}) == 1 else exact


def _dup_code(c: Candidate) -> str | None:
    mc = c.canon.model_code
    return re.sub(r"\s+", "", mc).upper() if mc else None


def _all_duplicates(group: list[Candidate]) -> bool:
    """True when every listing in group is the same product listed more than once."""
    eans = {clean_ean(c.canon.ean) if c.canon.ean else None for c in group}
    if len(eans) == 1 and None not in eans:
        return True
    styles = {_style_key(c.canon.style_code) if c.canon.style_code else None for c in group}
    if None not in styles and all(same_style(group[0].canon, c.canon) for c in group) \
            and len({colour_set(c.canon.colour) for c in group}) == 1 and colour_set(group[0].canon.colour):
        return True  # one fashion style in one colour listed twice (AUSKB-04065 / AUSK04065, both Maroon)
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
    elif _title_has_model_number(s, cand):
        facts.append(f"model {s.style_code}")
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
        "fabric": (fs := fabric_set(s.title, s.brand)) and f"the same fabric ({', '.join(sorted(fs))})",
        "neck": s.neck and f"a {s.neck} neck",
        "gender": s.gender and f"a {s.gender}'s version",
        "category": "the same kind of product",
    }.get(r)
    return what or r


# ---------------------------------------------------------------- outcome (§6.7)

def _differs(attrs: list[str]) -> str:
    if not attrs:
        return "design differs"
    return ", ".join(attrs) + (" differs" if len(attrs) == 1 else " differ")


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
        return PlatformResult(platform, Outcome.NOT_LISTED, None, reason, closest=[
            {"title": c.title, "url": c.url, "differs": _differs(d)} for c, d in m.closest])

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
