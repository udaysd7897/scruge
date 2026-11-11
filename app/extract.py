"""Extraction of platform payloads into canonical records + category detection."""
from __future__ import annotations

import json
import re
from html import unescape

from app.models import Candidate, Canonical, Category, Platform, SourceProduct
from app.normalize import (
    base_colour, clean_ean, is_accessory, model_line, norm_brand, norm_family, parse_gb, parse_ram_storage,
    product_type, screen_inches, tv_family,
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
    # Amazon sometimes returns no breadcrumbs and titles rarely say "smartphone" ("Apple iPhone 17
    # Pro 256 GB: ..."): known phone lines followed by a model number identify the category
    (Category.PHONE, re.compile(
        r"\b(?:iphone\s*\d{1,2}|galaxy\s+(?:[samfz]\s?\d{1,3}|z\s*(?:fold|flip)\s*\d)|pixel\s*\d{1,2}"
        r"|oneplus\s*(?:\d{1,2}|nord)|redmi\s*(?:note\s*)?\d{1,2}|poco\s*[a-z]\d|vivo\s*[a-z]\d{1,3}"
        r"|oppo\s*(?:reno|find|[a-z]\d)|realme\s*(?:\d{1,2}|narzo|gt)|iqoo\s*(?:\d|z|neo)"
        r"|moto(?:rola)?\s*(?:g\d|edge|razr)|nothing\s*phone)", re.I)),
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


_AMAZON_STYLE_KEYS = ("Style Number", "Item model number", "Manufacturer Part Number", "Model Number")


def _amazon_style(at: dict[str, str]) -> str | None:
    for k in _AMAZON_STYLE_KEYS:
        code = style_code_like(at.get(k))
        if code:
            return code
    return None


def _amazon_model_name(at: dict[str, str]) -> str | None:
    """Amazon's "Model Name" for fashion is the brand line name ("TAD ESSENTIAL | GYM_2891"): a search
    hint, never identity. A code-like value is not a line name."""
    v = re.split(r"\|", at.get("Model Name") or "")[0].strip()
    return v.lower() if v and not style_code_like(v) else None


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


def _amazon_tv_code(at: dict[str, str], screen_in: int | None) -> str | None:
    for k in ("Model Number", "Manufacturer Part Number", "Model Name", "Item model number"):
        code = model_code_like(at.get(k), screen_in)
        if code:
            return code
    return None


def from_amazon(item: dict) -> SourceProduct:
    title = item.get("title") or ""
    cat = detect_category(item.get("breadCrumbs"), title)
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
        style_code=_amazon_style(at) if cat in (Category.SNEAKER, Category.APPAREL) else None,
        model_name=_amazon_model_name(at) if cat in (Category.SNEAKER, Category.APPAREL) else None,
        gender=_gender(at.get("Department")) if cat in (Category.SNEAKER, Category.APPAREL) else None,
        mrp=int((item.get("listPrice") or {}).get("value") or 0) or None,
        maker=norm_maker(at.get("Manufacturer Contact Information") or at.get("Manufacturer")),
        title=title,
    )
    img = item.get("thumbnailImage") or (item.get("highResolutionImages") or [None])[0]
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
              "Style Code", "Article Number")
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
    fk_cat = detect_category(None, p.get("name") or "")
    title = p.get("name") or ""
    style = None
    if fk_cat in (Category.SNEAKER, Category.APPAREL):
        # Flipkart's JSON-LD name for fashion is generated from attributes ("PUMA Printed Men Round Neck
        # Black T-Shirt"); the page shows the brand's own title ("PUMA M Train All Day ESSENTIAL ...")
        shown = _fk_shown_title(html, brand)
        title = shown or title
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
        title=title,
    )
    price = offers.get("price")
    return [Candidate(Platform.FLIPKART, url, canon.title, canon, _fk_stock(offers.get("availability")),
                      int(float(price)) if price is not None else None, m.group(1) if m else None)]


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
