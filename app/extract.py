"""Extraction of platform payloads into canonical records + category detection."""
from __future__ import annotations

import json
import re
from html import unescape

from app.models import Candidate, Canonical, Category, Platform, SourceProduct
from app.normalize import (
    base_colour, clean_ean, is_accessory, model_line, norm_brand, norm_family, parse_gb, parse_ram_storage,
    neck_type, product_type, screen_inches, store_kind, tv_family, agreed_audience, audience,
    CODE_BRANDS, GENDER_WORDS,
)

REQUIRED: dict[Category, list[str]] = {
    Category.PHONE: ["brand", "family", "ram_gb", "storage_gb", "colour"],
    Category.TV: ["brand", "family", "screen_in"],
    Category.SNEAKER: ["brand", "family", "base_colour"],
    Category.APPAREL: ["brand", "product_type", "base_colour"],
}

_CRUMB_RULES: list[tuple[Category, re.Pattern]] = [
    (Category.PHONE, re.compile(r"smartphones?|mobile phones?", re.I)),
    (Category.TV, re.compile(r"televisions?|\btvs?\b", re.I)),
    (Category.SNEAKER, re.compile(r"shoes|sneakers", re.I)),
    (Category.APPAREL, re.compile(r"t-?shirts?|polos?\b|jerseys?", re.I)),
]
_TITLE_RULES: list[tuple[Category, re.Pattern]] = [
    (Category.TV, re.compile(r"\b(?:smart|led|oled|qled|google|android)?\s*tv\b|televisions?", re.I)),
    (Category.PHONE, re.compile(r"smartphones?|mobile phones?", re.I)),
    (Category.SNEAKER, re.compile(r"\b(?:shoes?|sneakers?)\b", re.I)),
    (Category.APPAREL, re.compile(r"t-?shirts?|\bpolos?\b|\bjerseys?\b|\btshirts?\b", re.I)),
]


_ACCESSORY_CRUMB = re.compile(
    r"\b(?:cases?|covers?|accessor\w*|protectors?|chargers?|cables?|mounts?|stands?)\b", re.I)


# leaf categories that sit under a supported parent but are not supported products
_EXCLUDED_CRUMB = re.compile(
    r"\bremotes?\b|\bsandals?\b|\bfloaters?\b|\bslippers?\b|\bflip[\s-]?flops?\b|\bsocks?\b", re.I)
_TV_PARENT = re.compile(r"televisions?", re.I)  # "Home Theater, TV & Video" is not a TV category


def detect_category(breadcrumbs: str | None, title: str) -> Category:
    if breadcrumbs:
        segs = [x for x in re.split(r"\s*>\s*", breadcrumbs.strip()) if x]
        leaf = segs[-1] if segs else ""
        if _ACCESSORY_CRUMB.search(leaf) or _EXCLUDED_CRUMB.search(leaf):
            return Category.UNSUPPORTED
        # the leaf decides, then its parent ("... > Smartphones & Basic Mobiles > Basic Mobiles");
        # never the whole path ("Clothing & Shoes > Polos" is not a shoe)
        for i, seg in enumerate(reversed(segs[-2:])):
            for cat, rx in _CRUMB_RULES:
                if i == 1 and cat == Category.SNEAKER:
                    continue  # sneakers need "shoes"/"sneakers" in the leaf
                if i == 1 and cat == Category.TV:
                    rx = _TV_PARENT
                if rx.search(seg):
                    return cat
    if is_accessory(title or ""):
        return Category.UNSUPPORTED  # "Spigen case for iPhone 17 Pro" names a phone but isn't one
    for cat, rx in _TITLE_RULES:
        if rx.search(title or ""):
            return cat
    return Category.UNSUPPORTED


def missing_required(c: Canonical, cat: Category) -> list[str]:
    out = []
    for f in REQUIRED.get(cat, []):
        if getattr(c, f, None):
            continue
        if cat == Category.PHONE and f == "ram_gb" and norm_brand(c.brand) == "apple":
            continue  # Apple doesn't publish iPhone RAM; the RAM veto still applies when both sides show it
        if cat == Category.TV and f == "family" and c.model_code:
            continue
        if cat == Category.SNEAKER and f == "family" and c.style_code:
            continue  # Sparx "SM-734": the model number is the model
        out.append(f)
    return out


def _title_family(title: str, brand: str | None) -> str | None:
    # family ends at the first "(", "|", ",", ":" or " - " ("OnePlus 15 | 12GB+256GB | ...",
    # "Apple iPhone 17 Pro 256 GB: 15.93 cm ...", "Apple iPhone 16 - Black"); sizes are not family
    head = re.split(r"[(|,:]|\s[-–]\s", title or "")[0]
    head = re.sub(r"\b\d+(?:\.\d+)?\s*(?:gb|tb)\b(?:\s*ram)?", " ", head, flags=re.I)
    if brand:
        head = re.sub(re.escape(brand), " ", head, count=1, flags=re.I)
    head = re.sub(r"\b(?:ai|smartphone|smart ?phone|mobile phone)\b", " ", head, flags=re.I)
    return norm_family(head)


def _attrs(item: dict) -> dict[str, str]:
    d: dict[str, str] = {}
    for a in item.get("attributes") or []:
        if a.get("key") and a.get("value"):
            d.setdefault(a["key"], str(a["value"]))
    return d


_CODE = re.compile(r"(?=[A-Z0-9./-]*\d)(?=[A-Z0-9./-]*[A-Z])[A-Z0-9][A-Z0-9./-]{4,}")


def model_code_like(s: str | None, screen_in: int | None = None) -> str | None:
    """s if it looks like a manufacturer model code (one token, letters and digits), else None.
    For a TV of known size the code must carry the size ("55QNED82SRA", not the series "QNED82")."""
    s = (s or "").strip()
    if not _CODE.fullmatch(s.upper()):
        return None
    if screen_in is not None and str(screen_in) not in s:
        return None
    return s


_STYLE = re.compile(r"[A-Z0-9][A-Z0-9_-]{4,14}")


def style_code_like(s: str | None) -> str | None:
    """s if it looks like a brand style/article code: one token of letters/digits with optional - or _
    and at least 4 digits (Puma 52885601 / 528856_01, Nike DV2789-100, adidas IF4405). Free text
    ("TAD ESSENTIAL | GYM_2891") and seller SKUs carrying a size ("...-NVY- 5XL") are rejected."""
    s = (s or "").strip()
    if not _STYLE.fullmatch(s.upper()) or sum(ch.isdigit() for ch in s) < 4:
        return None
    return s


_SHORT_CODE = re.compile(r"([A-Z]{1,4})[\s-]?(\d{3,})")


def sneaker_code_like(s: str | None, brand: str | None = None) -> str | None:
    """A brand code, or a short model number of letters + 3 digits ("SM-734", "SM 734" → "SM-734"). Short
    numbers only for brands whose codes aren't trusted: New Balance "NB 574" is a model name, not a code."""
    code = style_code_like(s)
    if code:
        return code
    if norm_brand(brand) in CODE_BRANDS:
        return None
    m = _SHORT_CODE.fullmatch((s or "").strip().upper())
    return f"{m.group(1)}-{m.group(2)}" if m else None


_AMAZON_STYLE_KEYS = ("Style Number", "Item model number", "Manufacturer Part Number", "Model Number")


def _amazon_style(at: dict[str, str], like=style_code_like) -> str | None:
    at = {k.lower(): v for k, v in at.items()}  # "Manufacturer part number" vs "Manufacturer Part Number"
    keys = [k.lower() for k in _AMAZON_STYLE_KEYS]
    for k in keys:  # the whole value is a code ("52885601")
        code = like(at.get(k))
        if code:
            return code
    for k in keys:  # a code followed by colour/size ("9930-0105-WHITE White L")
        first = (at.get(k) or "").split(" ")[0]
        if not re.search(r"pack|set|combo", first, re.I):
            code = like(first)
            if code:
                return code
    return None


def _amazon_model_name(at: dict[str, str]) -> str | None:
    """Amazon's "Model Name" for fashion is the brand line name ("TAD ESSENTIAL | GYM_2891"): a search
    hint, never identity. A code-like value is not a line name."""
    v = re.split(r"\|", at.get("Model Name") or "")[0].strip()
    if not v or style_code_like(v) or style_code_like(v.split("_")[0]) or re.search(r"pack of", v, re.I):
        return None  # the code itself ("JE9356", "9930_Pack of 1") is not a name
    if re.search(r"\d{3,}", v) and re.search(r"[-.]", v):
        return None  # a seller SKU ("LF-M.T-Shirt-DP-MT1213") is not a name either
    words = [w for w in re.split(r"[_\s]+", v.lower()) if w and w not in _MODEL_NAME_TAGS]
    return " ".join(words) or None


_GENERIC_SHOE = {"leather", "stylish", "classic", "trendy", "comfortable", "lightweight", "premium", "new"}


def _sneaker_model(at: dict[str, str], brand: str | None) -> str | None:
    """Amazon "Model Name" minus brand words ("Bacca Bucci Stride Eclipse" → "stride eclipse"). A model
    number ("Sm-734") is a code, not a name."""
    v = ({k.lower(): x for k, x in at.items()}.get("model name") or "").strip()
    if not v or sneaker_code_like(v, brand):
        return None
    drop = set(re.findall(r"[a-z0-9]+", (brand or "").lower()))
    words = [w for w in re.findall(r"[a-z0-9]+", v.lower()) if w not in drop]
    name = " ".join(words)
    return name if name and name not in _GENERIC_SHOE else None


_MODEL_NAME_TAGS = {"smu", "nos", "ss", "aw", "fw", "core"}  # internal season/channel tags in brand line names


def norm_maker(s: str | None) -> str | None:
    """Manufacturer text up to its 6-digit PIN code, lowercase words only: Amazon's "Aryan Apparels Private
    Limited Plot no 266 ... Manesar 122051, Puma" equals Myntra's "Aryan Apparels ... Manesar  122051 , India"."""
    s = (s or "").lower()
    m = re.search(r"\b\d{6}\b", s)
    s = s[: m.end()] if m else s
    return " ".join(re.findall(r"[a-z0-9]+", s)) or None


def _gender(s: str | None) -> str | None:
    s = (s or "").lower()
    for g in ("women", "men", "unisex"):
        if re.search(rf"\b{g}\b", s):
            return g
    return "kids" if re.search(r"\b(kids?|boys?|girls?)\b", s) else None


def _amazon_neck(item: dict, at: dict[str, str]) -> str | None:
    """Neckline: the title first (most specific), then Amazon's neck fields; fields that contradict each
    other ("Collar Style: classic collar" + "Neck Style: Round Neck" on a crew-neck Levi's) mean unknown.
    Bullets/description last. Text beats image (image neckline accuracy is 15-48%)."""
    n = neck_type(item.get("title"))
    if n:
        return n
    fields = {neck_type(at.get(k)) for k in ("Neck Style", "Neck Type", "Collar Style")} - {None}
    if len(fields) == 1:
        return fields.pop()
    if len(fields) > 1:
        return None
    text = " ".join(str(x) for x in (item.get("features") or []) if x) + " " + str(item.get("description") or "")
    return neck_type(text)


def _amazon_tv_code(at: dict[str, str], screen_in: int | None) -> str | None:
    for k in ("Model Number", "Manufacturer Part Number", "Model Name", "Item model number"):
        code = model_code_like(at.get(k), screen_in)
        if code:
            return code
    return None


_PHONE_NODES = {"1805560031"}  # amazon.in browse node: Smartphones
_PHONE_OS = re.compile(r"\b(ios|android)\b", re.I)
_TV_SPEC_KEYS = ("HDMI Ports", "Tuner Type", "VESA Mount Standard", "Display Size Class")


def _grams(s: str | None) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilograms?|g|grams?)\b", (s or "").lower())
    if not m:
        return None
    return float(m.group(1)) * (1000 if m.group(2).startswith("k") else 1)


def amazon_category(item: dict) -> Category:
    """Category from what Amazon states, then a spec fingerprint — no model-name lists (design report
    2026-11-12): breadcrumb → bestseller browse node → Item Type Name → specs → unsupported."""
    title = item.get("title") or ""
    if is_accessory(title):
        return Category.UNSUPPORTED
    crumbs = item.get("breadCrumbs")
    if crumbs:
        cat = detect_category(crumbs, title)
        if cat != Category.UNSUPPORTED:
            return cat
    for b in item.get("bestsellerRanks") or []:
        if any(f"/{n}/" in (b.get("url") or "") for n in _PHONE_NODES):
            return Category.PHONE
    at = _attrs(item)
    po = {x.get("key"): str(x.get("value")) for x in item.get("productOverview") or [] if x.get("key") and x.get("value")}
    itn = (at.get("Item Type Name") or "").lower()
    if re.search(r"smart ?phone|mobile phone", itn):
        return Category.PHONE
    if re.search(r"\b(tv|television)\b", itn):
        return Category.TV
    os_ = po.get("Operating System") or at.get("Operating System")
    va = {x.get("key"): x.get("value") for x in item.get("variantAttributes") or []}
    # the storage row is missing on some pages (17 Pro Max 256 GB B0FQFV2XKS): Apple's own "CAPACITY" row,
    # the variant picker's Size or the title carry it too
    storage = (po.get("Memory Storage Capacity") or at.get("Memory Storage Capacity") or at.get("CAPACITY")
               or (parse_gb(va.get("Size")) and va.get("Size")) or (parse_gb(title) and title))
    weight = _grams(at.get("Item Weight") or at.get("Product Dimensions"))
    if os_ and _PHONE_OS.search(os_) and storage and (weight is None or weight < 350):
        return Category.PHONE
    if any(at.get(k) or po.get(k) for k in _TV_SPEC_KEYS):
        return Category.TV
    return detect_category(None, title)


def from_amazon(item: dict) -> SourceProduct:
    title = item.get("title") or ""
    cat = amazon_category(item)
    at = _attrs(item)
    va = {a.get("key"): a.get("value") for a in item.get("variantAttributes") or []}
    brand = norm_brand(item.get("brand") or at.get("Brand Name"))
    ram, storage = parse_gb(at.get("RAM Memory Installed")), parse_gb(at.get("Memory Storage Capacity"))
    colour = at.get("Colour") or va.get("Colour")
    if ram is None or storage is None:
        r, s = parse_ram_storage(va.get("Size") or "")
        ram, storage = ram or r, storage or s
    if ram is None or storage is None:
        r, s = parse_ram_storage(title)
        ram, storage = ram or r, storage or s
    if colour is None:
        m = re.search(r"\(([^,)]+),", title)
        colour = m.group(1).strip() if m else None
    raw_brand = item.get("brand") or at.get("Brand Name")
    guessed = False
    first = re.sub(r"'s$", "", title.split()[0].lower()) if title.split() else ""
    if not raw_brand and cat in (Category.SNEAKER, Category.APPAREL) and first and first not in GENDER_WORDS:
        # sparse Apify record (Nike Killshot B00770CB12 has no brand): fashion titles open with the brand.
        # Only a guess ("Red Tape" → "red"): it may fall short of a listing's brand but never contradicts it
        raw_brand, guessed = title.split()[0], True
        brand = norm_brand(raw_brand)
    code = _amazon_tv_code(at, screen_inches(title)) if cat == Category.TV else None
    if cat in (Category.SNEAKER, Category.APPAREL):
        # model line ends at the first "(", "," or "|" ("..., Black/White-Anthracite, 8 UK")
        family = model_line(re.split(r"[(,|]", title)[0], raw_brand)
    elif cat == Category.TV:
        # TV titles open with the size ("LG 139 cms (55 inches) NU87 ...") and series names differ
        # per store (Croma "NU870B", Flipkart's Model Name is the code): identify by model number,
        # and without one fall back to the cleaned series words (or None).
        family = None if code else tv_family(title, raw_brand)
    else:
        family = _title_family(title, raw_brand)
    canon = Canonical(
        brand=brand,
        family=family,
        model_code=code,
        ram_gb=ram if cat == Category.PHONE else None,
        storage_gb=storage if cat == Category.PHONE else None,
        screen_in=screen_inches(title) if cat == Category.TV else None,
        colour=colour,
        base_colour=base_colour(colour),
        product_type=product_type(title, item.get("breadCrumbs")) if cat == Category.APPAREL else None,
        style_code=(_amazon_style(at, lambda v: sneaker_code_like(v, raw_brand)) if cat == Category.SNEAKER
                    else _amazon_style(at) if cat == Category.APPAREL else None),
        model_name=(_sneaker_model(at, raw_brand) if cat == Category.SNEAKER
                    else _amazon_model_name(at) if cat == Category.APPAREL else None),
        gender=(agreed_audience(at.get("Department"), title, item.get("breadCrumbs")) if cat == Category.SNEAKER
                else _gender(at.get("Department")) if cat == Category.APPAREL else None),
        neck=_amazon_neck(item, at) if cat == Category.APPAREL else None,
        # no strike-through list price means the product isn't discounted: the price is the MRP
        mrp=int((item.get("listPrice") or {}).get("value") or (item.get("price") or {}).get("value") or 0) or None,
        maker=norm_maker(at.get("Manufacturer Contact Information") or at.get("Manufacturer")),
        title=title,
        brand_guessed=guessed,
    )
    if cat == Category.SNEAKER:
        # the model name ("Stride Eclipse") is the shoe's identity; a title remnant like "leather" or
        # "stylish" is not
        canon.family = canon.model_name or (family if family and family not in _GENERIC_SHOE else None)
    img = (item.get("highResolutionImages") or [None])[0] or item.get("thumbnailImage")
    return SourceProduct(url=item.get("url") or "", asin=item.get("asin") or "", title=title, image=img,
                         category=cat, canon=canon, missing_required=missing_required(canon, cat))


def from_croma(item: dict) -> Candidate:
    sp = item.get("specs") or {}
    title = item.get("productTitle") or ""
    colour = sp.get("Brand Color") or sp.get("Color")
    ram, storage = parse_gb(sp.get("RAM")), parse_gb(sp.get("Internal Storage"))
    canon = Canonical(
        brand=norm_brand(item.get("brand")),
        family=(tv_family(sp.get("Model Series"), item.get("brand"))
                if detect_category(None, title) == Category.TV else norm_family(sp.get("Model Series"))),
        model_code=sp.get("Model Number"),
        ram_gb=ram, storage_gb=storage,
        screen_in=screen_inches(sp.get("Screen Size in Inches")),
        colour=colour, base_colour=base_colour(colour),
        ean=clean_ean(item.get("ean")),
        title=title,
    )
    price = item.get("price")
    return Candidate(Platform.CROMA, item.get("url") or "", title, canon, item.get("in_stock"),
                     int(price) if price is not None else None)


_FK_IN_STOCK = ("InStock", "LimitedAvailability", "OnlineOnly")


def _fk_stock(av: str | None) -> bool | None:
    if not av:
        return None
    return av.endswith(_FK_IN_STOCK)


def _tokens(html: str) -> list[str]:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return [unescape(x).strip() for x in re.split(r"<[^>]+>", t) if x.strip()]


def _ld_products(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict) and (d.get("@type") == "Product" or "offers" in d):
                out.append(d)
    return out


# Some pages render the spec table client-side; the rows are then only in the page-state JSON:
# ..."label_1":{"value":{"text":["55UA82006LA"]}},"label_0":{"value":{"text":"Model Name"}}...
_FK_STATE_SPEC = re.compile(
    r'"label_1":\{"value":\{"text":\["((?:[^"\\]|\\.)*)"\]\}\},"label_0":\{"value":\{"text":"([^"]+)"\}\}')


# Flipkart's own JSON-LD category: "JOCKEY Men Vest" says nothing about clothing, its category "vest" does
_FK_LD_CATEGORY = {"t_shirt": Category.APPAREL, "vest": Category.APPAREL, "polo": Category.APPAREL,
                   "jersey": Category.APPAREL, "mobile": Category.PHONE, "television": Category.TV,
                   "shoe": Category.SNEAKER, "shoes": Category.SNEAKER, "sneaker": Category.SNEAKER}


# the product's own price block: "ppd":{"fsp":1599,"finalPrice":1599,"mrp":2999,...} (one per page)
_FK_MRP = re.compile(r'"ppd":\{[^{}]*?"mrp":(\d+)')
_FK_SHOWN = re.compile(r'"prependingText":"((?:[^"\\]|\\.)+)"')


def _fk_shown_title(html: str, brand: str | None) -> str | None:
    """The product title as displayed (brand + seller title). Only trusted when it starts with the
    product's brand, so a recommended product's title is never picked up."""
    m = _FK_SHOWN.search(html)
    if not m:
        return None
    try:
        t = json.loads(f'"{m.group(1)}"').strip()
    except ValueError:
        return None
    return t if brand and t.lower().startswith(brand.lower()) else None


def from_flipkart_page(html: str, url: str) -> list[Candidate]:
    prods = _ld_products(html)
    if not prods:
        return []
    p = prods[0]
    toks = _tokens(html)
    labels = ("Model Number", "Model Name", "RAM", "Internal Storage", "Color", "Display Size",
              "Style Code", "Article Number", "Type", "Neck", "Ideal For", "Ideal for", "Model name",
              "Name and address of the Manufacturer")
    spec: dict[str, str] = {}
    for i, t in enumerate(toks[:-1]):
        if t in labels and t not in spec:
            spec[t] = toks[i + 1]
    for value, label in _FK_STATE_SPEC.findall(html):
        if label in labels and label not in spec:
            try:
                spec[label] = json.loads(f'"{value}"')
            except ValueError:
                continue
    m = re.search(r"/(itm[0-9a-z]+)", url, re.I)
    offers = p.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    brand = p.get("brand")
    brand = brand.get("name") if isinstance(brand, dict) else brand
    colour = spec.get("Color") or p.get("color")
    ram, storage = parse_gb(spec.get("RAM")), parse_gb(spec.get("Internal Storage"))
    if ram is None and storage is None:
        ram, storage = parse_ram_storage(p.get("name") or "")
    fk_cat = _FK_LD_CATEGORY.get(str(p.get("category") or "").lower()) or detect_category(None, p.get("name") or "")
    title = p.get("name") or ""
    style = None
    if fk_cat in (Category.SNEAKER, Category.APPAREL):
        # Flipkart's JSON-LD name for fashion is generated from attributes ("PUMA Printed Men Round Neck
        # Black T-Shirt"); the page shows the brand's own title ("PUMA M Train All Day ESSENTIAL ...")
        shown = _fk_shown_title(html, brand)
        title = shown or title
        if fk_cat == Category.SNEAKER:
            # "Sparx SM 734 | Stylish ... For Men (White , 9)": the bracket is colour + size
            title = re.sub(r"\s*\([^()]*,\s*[\d.]+\s*\)\s*$", "", title)
            style = sneaker_code_like(spec.get("Style Code") or spec.get("Article Number"), brand)
            fam = model_line(re.split(r"[|:]", spec.get("Model Name") or spec.get("Model name") or title)[0], brand)
        else:
            style = style_code_like(spec.get("Style Code") or spec.get("Article Number"))
            fam = model_line(spec.get("Model Name") or title, brand)
    elif fk_cat == Category.TV:
        fam = tv_family(spec.get("Model Name"), brand)
    else:
        fam = norm_family(spec.get("Model Name"))
    code = spec.get("Model Number")
    if not code and fk_cat == Category.TV:
        # Flipkart TVs put the model code here
        code = model_code_like(spec.get("Model Name"), screen_inches(spec.get("Display Size")))
    canon = Canonical(
        brand=norm_brand(brand), family=fam,
        model_code=code, ram_gb=ram, storage_gb=storage,
        screen_in=screen_inches(spec.get("Display Size")),
        colour=colour, base_colour=base_colour(colour),
        product_type=product_type(p.get("name"), None) if fk_cat == Category.APPAREL else None,
        style_code=style,
        neck=(neck_type(spec.get("Neck")) or neck_type(spec.get("Type")) or neck_type(title))
        if fk_cat == Category.APPAREL else None,
        kind=store_kind(str(p.get("category") or "") or None),
        gender=(agreed_audience(spec.get("Ideal For") or spec.get("Ideal for"), title)
                if fk_cat == Category.SNEAKER else None),
        maker=norm_maker(spec.get("Name and address of the Manufacturer")),
        mrp=int(mm.group(1)) if (mm := _FK_MRP.search(html)) else None,
        title=title,
    )
    price = offers.get("price")
    img = p.get("image")
    img = (img[0] if isinstance(img, list) and img else img) if img else None
    return [Candidate(Platform.FLIPKART, url, canon.title, canon, _fk_stock(offers.get("availability")),
                      int(float(price)) if price is not None else None, m.group(1) if m else None,
                      image=img if isinstance(img, str) else None)]


_MYNTRA_TYPES = {"tshirts": "tee", "t-shirts": "tee", "polo": "polo", "polo tshirts": "polo", "jerseys": "jersey"}


def from_myntra_search(html: str) -> list[Candidate]:
    i = html.find("window.__myx = ")
    if i < 0:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html[i + len("window.__myx = "):])
    except ValueError:
        return []
    prods = (((data.get("searchData") or {}).get("results") or {}).get("products")) or []
    out = []
    for p in prods:
        brand = p.get("brand") or ""
        name = p.get("productName") or ""
        art = ((p.get("articleType") or {}).get("typeName") or "").lower()
        fam = model_line(name, brand)
        colour = p.get("primaryColour")
        canon = Canonical(
            brand=norm_brand(brand), family=fam,
            colour=colour, base_colour=base_colour(colour),
            # Myntra files polos under "Tshirts": the name decides first, the article type second
            product_type=(None if "shoe" in art or "sneaker" in art
                          else product_type(name, None) or _MYNTRA_TYPES.get(art)),
            gender=_gender(p.get("gender")),
            mrp=int(p["mrp"]) if p.get("mrp") else None,
            neck=neck_type(name),
            kind=store_kind((p.get("articleType") or {}).get("typeName")),
            title=name,
        )
        inv = [x for x in p.get("inventoryInfo") or [] if isinstance(x, dict)]
        out.append(Candidate(Platform.MYNTRA, "https://www.myntra.com/" + (p.get("landingPageUrl") or ""),
                             name, canon, any(x.get("available") for x in inv) if inv else None,
                             int(p["price"]) if p.get("price") is not None else None,
                             str(p.get("productId")) if p.get("productId") is not None else None,
                             image=(p.get("searchImage") or "").replace("http://", "https://") or None))
    return out


def myntra_pdp_maker(html: str) -> str | None:
    """Manufacturer text from a Myntra product page (window.__myx.pdpData sizes[].sizeSellerData[])."""
    i = html.find("window.__myx = ")
    if i < 0:
        return None
    try:
        d, _ = json.JSONDecoder().raw_decode(html[i + len("window.__myx = "):])
    except ValueError:
        return None
    for sz in ((d.get("pdpData") or {}).get("sizes") or []):
        for ssd in sz.get("sizeSellerData") or []:
            if ssd.get("manufacturerInfo"):
                return norm_maker(ssd["manufacturerInfo"])
    return None
