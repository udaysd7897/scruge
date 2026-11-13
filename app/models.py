from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    PHONE = "phone"
    TV = "tv"
    SNEAKER = "sneaker"
    APPAREL = "apparel"
    UNSUPPORTED = "unsupported"


class Platform(str, Enum):
    FLIPKART = "flipkart"
    CROMA = "croma"
    MYNTRA = "myntra"


class FetchStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"
    BLOCKED = "blocked"
    ERROR = "error"


class Decision(str, Enum):
    MATCH = "match"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


class Outcome(str, Enum):
    IN_STOCK = "In stock"
    OUT_OF_STOCK = "Out of stock"
    NOT_LISTED = "Not listed"
    POSSIBLE = "Possible match – verify"
    COULDNT_CHECK = "Couldn't check"


@dataclass
class Canonical:
    brand: str | None = None
    family: str | None = None
    model_code: str | None = None
    ram_gb: int | None = None
    storage_gb: int | None = None
    screen_in: int | None = None
    colour: str | None = None  # official name, as given
    base_colour: str | None = None
    style_code: str | None = None  # brand style/article code (Puma 52885601, Nike HJ5228-101)
    model_name: str | None = None  # brand's line name when the listing states it ("tad essential")
    official_name: str | None = None  # brand-site product name looked up by style code
    gender: str | None = None  # men / women / kids
    neck: str | None = None  # collar / mandarin / round / v / henley / hooded (None = unknown)
    kind: str | None = None  # store's own product kind: "top" (tee/polo/vest/jersey) or "other" (watch, shirt, slides)
    mrp: int | None = None
    maker: str | None = None  # manufacturer text, normalised (Amazon "Manufacturer", Myntra manufacturerInfo)
    product_type: str | None = None
    pack_count: int = 1
    ean: str | None = None
    title: str = ""


@dataclass
class Candidate:
    platform: Platform
    url: str
    title: str
    canon: Canonical
    in_stock: bool | None
    price: int | None = None
    variant_group: str | None = None
    image: str | None = None
    confirmed: bool = False  # no-code listing confirmed by MRP + manufacturer + photo (app/confirm.py)


@dataclass
class SourceProduct:
    url: str
    asin: str
    title: str
    image: str | None
    category: Category
    canon: Canonical
    missing_required: list[str] = field(default_factory=list)


@dataclass
class PlatformResult:
    platform: Platform
    outcome: Outcome
    url: str | None
    reason: str
    colour_fallback_note: str | None = None
    # Not listed, but these passed every hard check; the photo showed a different design
    # [{title, url, differs}] (user request 2026-11-13)
    closest: list[dict] = field(default_factory=list)
