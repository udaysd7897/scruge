"""Extraction of platform payloads into canonical records + category detection."""
from __future__ import annotations

import json
import re
from html import unescape

from app.models import Candidate, Canonical, Category, Platform, SourceProduct
from app.normalize import (
    base_colour, clean_ean, norm_brand, norm_family, parse_gb, parse_ram_storage, screen_inches,
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


def detect_category(breadcrumbs: str | None, title: str) -> Category:
    if breadcrumbs:
        for cat, rx in _CRUMB_RULES:
            if rx.search(breadcrumbs):
                return cat
    for cat, rx in _TITLE_RULES:
        if rx.search(title or ""):
            return cat
    return Category.UNSUPPORTED


def missing_required(c: Canonical, cat: Category) -> list[str]:
    out = []
    for f in REQUIRED.get(cat, []):
        if getattr(c, f, None):
            continue
        if cat == Category.TV and f == "family" and c.model_code:
            continue
        out.append(f)
    return out


def _title_family(title: str, brand: str | None) -> str | None:
    head = (title or "").split("(")[0]
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
    canon = Canonical(
        brand=brand,
        family=_title_family(title, item.get("brand") or at.get("Brand Name")),
        ram_gb=ram if cat == Category.PHONE else None,
        storage_gb=storage if cat == Category.PHONE else None,
        screen_in=screen_inches(title) if cat == Category.TV else None,
        colour=colour,
        base_colour=base_colour(colour),
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
        family=norm_family(sp.get("Model Series")),
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
            if isinstance(d, dict) and d.get("@type") == "Product" or (isinstance(d, dict) and "offers" in d):
                out.append(d)
    return out


def from_flipkart_page(html: str, url: str) -> list[Candidate]:
    prods = _ld_products(html)
    if not prods:
        return []
    p = prods[0]
    toks = _tokens(html)
    labels = ("Model Number", "Model Name", "RAM", "Internal Storage", "Color", "Display Size")
    spec: dict[str, str] = {}
    for i, t in enumerate(toks[:-1]):
        if t in labels and t not in spec:
            spec[t] = toks[i + 1]
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
    canon = Canonical(
        brand=norm_brand(brand), family=norm_family(spec.get("Model Name")),
        model_code=spec.get("Model Number"), ram_gb=ram, storage_gb=storage,
        screen_in=screen_inches(spec.get("Display Size")),
        colour=colour, base_colour=base_colour(colour), title=p.get("name") or "",
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
        fam = re.sub(re.escape(brand), " ", name, count=1, flags=re.I) if brand else name
        colour = p.get("primaryColour")
        canon = Canonical(
            brand=norm_brand(brand), family=norm_family(fam),
            colour=colour, base_colour=base_colour(colour),
            product_type=None if "shoe" in art or "sneaker" in art else _MYNTRA_TYPES.get(art),
            title=name,
        )
        inv = p.get("inventoryInfo") or []
        out.append(Candidate(Platform.MYNTRA, "https://www.myntra.com/" + (p.get("landingPageUrl") or ""),
                             name, canon, any(x.get("available") for x in inv),
                             int(p["price"]) if p.get("price") is not None else None,
                             str(p.get("productId")) if p.get("productId") is not None else None))
    return out
