from __future__ import annotations

import re

from app.models import Category, Platform, SourceProduct
from app.normalize import distinctive_words


def _join(*parts) -> str | None:
    if any(p is None or p == "" for p in parts):
        return None
    return " ".join(str(p) for p in parts).lower()


def _head(title: str | None) -> str:
    # drop the bracketed/comma tails ("(ASKPQRGFS12345_Navy_M)", ", Black/White, 8 UK")
    return re.split(r"[(,|]", title or "")[0]


def _distinct_in_order(title: str, brand: str | None, n: int = 3) -> list[str]:
    title = _head(title)
    words = distinctive_words(title, brand)
    out: list[str] = []
    t = title.lower().replace("t-shirt", "tshirt")
    for w in re.findall(r"[a-z0-9]+", t):
        if w in words and w not in out:
            out.append(w)
        if len(out) == n:
            break
    return out


def ladder(src: SourceProduct, platform: Platform) -> list[str]:
    """§6.3 query ladder: model code → brand+family+key attrs → brand+family. Deduped, order kept."""
    c, cat = src.canon, src.category
    rungs: list[str | None] = []
    if platform != Platform.MYNTRA:
        rungs.append(c.model_code)
    if cat == Category.PHONE:
        ram = f"{c.ram_gb}gb" if c.ram_gb is not None else None
        storage = f"{c.storage_gb}gb" if c.storage_gb is not None else None
        # build from the parts we have (iPhone listings carry no RAM): brand + family are the minimum
        rungs.append(_join(c.brand, c.family) and " ".join(
            p for p in (_join(c.brand, c.family), ram, storage, (c.colour or "").lower()) if p))
    elif cat == Category.TV:
        rungs.append(_join(c.brand, c.family or c.model_code, c.screen_in, "inch"))
    elif cat == Category.SNEAKER:
        rungs.append(_join(c.brand, c.family, c.base_colour))
    elif cat == Category.APPAREL:
        base = _join(c.brand, c.product_type, c.base_colour)
        if base:
            extra = _distinct_in_order(c.title or src.title, c.brand)
            base = " ".join([base, *extra])
        rungs.append(base)
        # fallback that needs neither type nor colour: the ladder is never empty when the brand is known
        if c.brand:
            rungs.append(" ".join([c.brand, *_distinct_in_order(c.title or src.title, c.brand, 4)]).lower())
    if cat in (Category.PHONE, Category.TV, Category.SNEAKER):
        rungs.append(_join(c.brand, c.family))
    out: list[str] = []
    for r in rungs:
        if r and r not in out:
            out.append(r)
    return out
