"""Read an Amazon product page fetched with plain HTTP into the same item shape the Apify actor returns,
so extract.from_amazon works on either. Used first; Apify is the fallback when the page is blocked."""
from __future__ import annotations

import html as H
import json
import re

_MARKS = re.compile(r"[‎‏​]|&lrm;|&rlm;")


def _text(s: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    return " ".join(H.unescape(_MARKS.sub("", re.sub(r"<[^>]+>", " ", s))).split()).strip(" :")


def _rows(h: str) -> list[tuple[str, str]]:
    """Label/value pairs from the spec tables (<th>/<td>), overview tables and detail bullets."""
    out = []
    for th, td in re.findall(r"<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", h, re.S | re.I):
        out.append((_text(th), _text(td)))
    for k, v in re.findall(r'<td class="a-span3"[^>]*>(.*?)</td>\s*<td class="a-span9"[^>]*>(.*?)</td>', h, re.S):
        out.append((_text(k), _text(v)))
    for k, v in re.findall(r'<span class="a-text-bold">(.*?)</span>\s*<span[^>]*>(.*?)</span>', h, re.S):
        out.append((_text(k), _text(v)))
    return [(k, v) for k, v in out if k and v and len(k) < 60]


def _money(s: str | None) -> int | None:
    m = re.search(r"₹\s*([\d,]+)", s or "")
    return int(m.group(1).replace(",", "")) if m else None


def parse_amazon_page(h: str, url: str) -> dict:
    asin = re.search(r"/dp/([A-Z0-9]{10})", url)
    title = re.search(r'id="productTitle"[^>]*>(.*?)</span>', h, re.S)
    crumbs = re.search(r'id="wayfinding-breadcrumbs_feature_div".*?</ul>', h, re.S)
    byline = re.search(r'id="bylineInfo"[^>]*>(.*?)</a>', h, re.S)
    rows, seen = [], set()
    for k, v in _rows(h):
        if k not in seen:
            seen.add(k)
            rows.append({"key": k, "value": v})
    at = {r["key"]: r["value"] for r in rows}
    overview = re.search(r'id="productOverview_feature_div".*?</table>', h, re.S)
    mrp = re.search(r'a-price a-text-price[^"]*"[^>]*data-a-strike="true".*?</span>', h, re.S)
    price = re.search(r'class="a-price-whole">([\d,]+)', h)
    imgs = re.findall(r'"hiRes":"(https://[^"]+)"', h) or re.findall(r'"large":"(https://[^"]+)"', h)
    avail = re.search(r'id="availability".*?</div>', h, re.S)
    brand = at.get("Brand") or at.get("Brand Name")
    if not brand and byline:
        brand = re.sub(r"^(Visit the|Brand:)\s*|\s*Store$", "", _text(byline.group(1)))
    return {
        "asin": asin.group(1) if asin else "",
        "url": url,
        "title": _text(title.group(1)) if title else "",
        "brand": brand,
        "breadCrumbs": " > ".join(_text(x) for x in re.findall(r"<a[^>]*>(.*?)</a>", crumbs.group(0), re.S))
        if crumbs else "",
        "attributes": rows,
        "productOverview": [{"key": k, "value": v} for k, v in _rows(overview.group(0))] if overview else [],
        "listPrice": {"value": _money(mrp.group(0)) if mrp else None, "currency": "₹"},
        "price": {"value": int(price.group(1).replace(",", "")) if price else None, "currency": "₹"},
        "highResolutionImages": imgs[:3],
        "thumbnailImage": imgs[0] if imgs else None,
        "inStock": bool(avail and re.search(r"in stock|only \d+ left", _text(avail.group(0)), re.I)),
        "variantAttributes": [],
        "bestsellerRanks": [{"url": u} for u in re.findall(r'href="(/gp/bestsellers/[^"]+)"', h)],
        "source": "page",
    }


def looks_like_product(item: dict) -> bool:
    return bool(item.get("title") and item.get("asin"))
