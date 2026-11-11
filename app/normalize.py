"""Pure normalisation helpers for the product matcher."""
from __future__ import annotations

import re

BRAND_ALIASES: dict[str, str] = {
    "mi": "xiaomi",
    "redmi": "xiaomi",
    "one plus": "oneplus",
    "hewlett packard": "hp",
    "hewlett-packard": "hp",
    "us polo": "u.s. polo assn.",
}

FAMILY_DROP_TOKENS = {"5g", "4g", "3g", "lte"}

TV_SIZES = [24, 32, 40, 43, 50, 55, 65, 75, 85, 98]

# word -> one of the 15 base colours
COLOUR_SYNONYMS: dict[str, str] = {
    "black": "black", "onyx": "black", "jet": "black", "carbon": "black", "midnight": "black",
    "phantom": "black", "obsidian": "black", "ebony": "black",
    "white": "white", "ivory": "white", "cream": "white", "pearl": "white", "snow": "white",
    "grey": "grey", "gray": "grey", "charcoal": "grey", "silver": "grey", "slate": "grey",
    "graphite": "grey", "titanium": "grey", "ash": "grey", "steel": "grey",
    "navy": "navy",
    "blue": "blue", "sky": "blue", "royal": "blue", "teal": "blue", "cyan": "blue",
    "indigo": "blue", "azure": "blue", "aqua": "blue", "turquoise": "blue",
    "red": "red", "crimson": "red", "scarlet": "red", "wine": "red", "burgundy": "maroon",
    "green": "green", "olive": "green", "mint": "green", "lime": "green", "emerald": "green",
    "khaki": "green", "volt": "green", "sage": "green",
    "yellow": "yellow", "gold": "yellow", "golden": "yellow", "mustard": "yellow",
    "orange": "orange", "coral": "orange", "rust": "orange", "peach": "orange",
    "pink": "pink", "rose": "pink", "magenta": "pink", "blush": "pink", "fuchsia": "pink",
    "purple": "purple", "violet": "purple", "lavender": "purple", "lilac": "purple", "mauve": "purple",
    "brown": "brown", "tan": "brown", "coffee": "brown", "chocolate": "brown", "bronze": "brown",
    "camel": "brown", "copper": "brown",
    "beige": "beige", "sand": "beige", "nude": "beige", "taupe": "beige", "stone": "beige",
    "maroon": "maroon",
    "multi": "multi", "multicolor": "multi", "multicolour": "multi", "multicolored": "multi",
    "assorted": "multi",
}
# multi-word phrases checked before per-word lookup
COLOUR_PHRASES: dict[str, str] = {
    "navy blue": "navy",
    "off white": "white",
    "rose gold": "pink",
    "dark navy": "navy",
    "multi color": "multi",
    "multi colour": "multi",
}

ACCESSORY_TOKENS = {"case", "cover", "protector", "skin", "adapter"}
ACCESSORY_PATTERNS = [re.compile(p) for p in (
    r"\bscreen (?:protector|guard)\b", r"\btempered glass\b", r"\bback (?:cover|case|panel)\b",
    r"\blens (?:protector|glass)\b", r"\bcamera ring\b", r"\bphone case\b",
    r"\b(?:case|cover|skin|charger|cable|strap) for\b",
    r"\bpanel\b.*\bback\b", r"\bback\b.*\bpanel\b",
)]

GENDER_WORDS = {"men", "mens", "women", "womens", "boys", "boy", "girls", "girl", "unisex", "kids", "man", "woman"}
PRODUCT_TYPE_WORDS = {"t-shirt", "tshirt", "tee", "polo", "jersey", "shirt", "shoes", "shoe", "sneakers", "sneaker"}
SIZE_WORDS = {"xs", "s", "m", "l", "xl", "xxl", "xxxl", "2xl", "3xl", "4xl", "size"}
FILLER_WORDS = {"pure", "cotton", "round", "neck", "half", "full", "sleeve", "sleeves", "casual", "solid",
                "and", "with", "for", "of", "in", "the", "a"}


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def norm_brand(s: str | None) -> str | None:
    s = _clean(s)
    if s is None:
        return None
    s = s.lower()
    return BRAND_ALIASES.get(s, s)


def norm_family(s: str | None) -> str | None:
    s = _clean(s)
    if s is None:
        return None
    s = re.sub(r"\([^)]*\)", " ", s.lower())
    s = s.replace("+", " plus ")
    tokens = re.findall(r"[a-z0-9]+", s)
    tokens = [t for t in tokens if t not in FAMILY_DROP_TOKENS and not re.fullmatch(r"(19|20)\d{2}", t)]
    return " ".join(tokens) or None


_SIZE_RE = r"(\d+(?:\.\d+)?)\s*(tb|gb)\b"


def _gb(num: str, unit: str) -> int:
    v = float(num)
    return int(round(v * 1024)) if unit.lower() == "tb" else int(round(v))


def parse_gb(s: str | None) -> int | None:
    if not s:
        return None
    m = re.search(_SIZE_RE, s, re.I)
    return _gb(m.group(1), m.group(2)) if m else None


def parse_ram_storage(s: str) -> tuple[int | None, int | None]:
    s = re.sub(r"\d+(?:\.\d+)?\s*(?:gb|tb)?\s*(?:virtual|extended)\s*ram", " ", s or "", flags=re.I)
    ram = storage = None
    m = re.search(_SIZE_RE + r"\s*ram\b", s, re.I)
    if m:
        ram = _gb(m.group(1), m.group(2))
        s = s[:m.start()] + " " + s[m.end():]
    m = re.search(_SIZE_RE + r"\s*(?:rom|storage|ssd|internal)\b", s, re.I)
    if m:
        storage = _gb(m.group(1), m.group(2))
        s = s[:m.start()] + " " + s[m.end():]
    rest = sorted(_gb(n, u) for n, u in re.findall(_SIZE_RE, s, re.I))
    if rest:
        if ram is None and storage is None:
            if len(rest) >= 2:
                ram, storage = rest[0], rest[-1]
            else:
                storage = rest[0]
        elif ram is None:
            ram = rest[0]
        elif storage is None:
            storage = rest[-1]
    return ram, storage


def screen_inches(s: str | None) -> int | None:
    if not s:
        return None
    s = s.lower().strip()
    m = re.search(r"(\d+(?:\.\d+)?)[\s-]*(?:inch|inches|in\b|\")", s)
    if m:
        v = float(m.group(1))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*cm", s)
        if m:
            v = float(m.group(1)) / 2.54
        elif re.fullmatch(r"\d+(?:\.\d+)?", s):
            v = float(s)
        else:
            return None
    if v < 20:
        return int(v + 0.5)
    nearest = min(TV_SIZES, key=lambda t: abs(t - v))
    return nearest if abs(nearest - v) <= 2 else int(v + 0.5)


def model_base(code: str | None) -> str | None:
    code = _clean(code)
    if code is None:
        return None
    code = code.upper().split("/")[0]
    code = re.sub(r"\s+", "", code)
    m = re.match(r"^SM-[A-Z]\d{3}", code)
    return m.group(0) if m else (code or None)


def split_style_code(code: str | None) -> tuple[str | None, str | None]:
    code = _clean(code)
    if code is None:
        return None, None
    m = re.fullmatch(r"([A-Za-z0-9]+)[-\s]+(\d{2,3})", code)
    if m:
        return m.group(1), m.group(2)
    return code, None


def colour_key(s: str | None) -> str | None:
    s = _clean(s)
    return s.lower() if s else None


def base_colour(s: str | None) -> str | None:
    s = _clean(s)
    if s is None:
        return None
    for segment in re.split(r"[/\-,&]+", s.lower()):
        segment = " ".join(re.findall(r"[a-z]+", segment))
        for phrase, base in COLOUR_PHRASES.items():
            if phrase in segment:
                return base
        hits = [COLOUR_SYNONYMS[t] for t in segment.split() if t in COLOUR_SYNONYMS]
        if hits:
            return hits[-1]  # head noun is last ("Onyx Black", "Sky Blue")
    return None


def clean_ean(s: str | None) -> str | None:
    if not s:
        return None
    d = re.sub(r"\D", "", s)
    if len(d) not in (8, 12, 13, 14):
        return None
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(d[:-1])))
    return d if (10 - total % 10) % 10 == int(d[-1]) else None


def is_accessory(title: str) -> bool:
    t = (title or "").lower()
    if set(re.findall(r"[a-z0-9]+", t)) & ACCESSORY_TOKENS:
        return True
    return any(p.search(t) for p in ACCESSORY_PATTERNS)


def distinctive_words(title: str, brand: str | None) -> set[str]:
    t = (title or "").lower().replace("t-shirt", "tshirt")
    t = re.sub(r"pack of \d+|\d+\s*-?\s*pack|\bpack\b", " ", t)
    t = re.sub(r"\d+(?:\.\d+)?[\s-]*(?:gb|tb|inch|inches|cm|mm|ml|kg)\b|\buk\s*\d+\b", " ", t)
    drop = set(GENDER_WORDS) | PRODUCT_TYPE_WORDS | SIZE_WORDS | FILLER_WORDS | set(COLOUR_SYNONYMS)
    for b in (brand, norm_brand(brand)):
        if b:
            drop.update(re.findall(r"[a-z0-9]+", b.lower()))
    return {w for w in re.findall(r"[a-z0-9]+", t) if w not in drop and not re.fullmatch(r"(19|20)\d{2}", w)}


DESCRIPTOR_WORDS = {"running", "road", "sports", "sport", "casual", "training", "walking", "lifestyle",
                    "textile", "mesh", "lace", "up", "slip", "on", "lace-up", "slip-on", "shoes", "sneakers",
                    "tshirts", "tshirt", "shirts", "polos", "jerseys", "tees"}


def model_line(title: str, brand: str | None) -> str | None:
    """Model line only: strips brand, gender, product-type, descriptors, colours, pack/size tokens."""
    t = (title or "").lower().replace("\u2019", "'")
    t = re.sub(r"'s\b", "", t).replace("t-shirt", "tshirt")
    t = re.sub(r"pack of \d+|\d+\s*-?\s*pack|\bpack\b", " ", t)
    t = re.sub(r"\d+(?:\.\d+)?[\s-]*(?:gb|tb|inch|inches|cm|mm|ml|kg)\b|\buk\s*\d+\b", " ", t)
    drop = (set(GENDER_WORDS) | PRODUCT_TYPE_WORDS | SIZE_WORDS | FILLER_WORDS | DESCRIPTOR_WORDS
            | set(COLOUR_SYNONYMS))
    for b in (brand, norm_brand(brand)):
        if b:
            drop.update(re.findall(r"[a-z0-9]+", b.lower()))
    toks = [w for w in re.findall(r"[a-z0-9]+", t) if w not in drop]
    return " ".join(toks) or None
