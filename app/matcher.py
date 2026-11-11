from __future__ import annotations

import re

from app.models import Candidate, Canonical, Category
from app.normalize import distinctive_words, is_accessory, model_base, norm_brand


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
        if cat == Category.APPAREL and src.pack_count != c.pack_count:
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
        if not a or not b or len(a & b) / len(a | b) < 0.5:
            return True
    if src.family:
        toks = set(re.findall(r"[a-z0-9]+", (cand.title or "").lower())) | b
        if not set(src.family.split()) <= toks:
            return True
    return False
