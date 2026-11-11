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
