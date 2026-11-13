"""Amazon product pages read with plain HTTP (no Apify credit needed). Root cause of "Amazon link not
working in the UI" (2026-11-12): Apify credit exhausted, and Apify was the only way to read Amazon."""
from pathlib import Path

import httpx

from app.extract import from_amazon
from app.models import Category, FetchStatus
from app.sources import amazon
from app.sources.amazon_page import parse_amazon_page

FX = Path(__file__).parent / "fixtures"
VH = (FX / "amz_page_vanheusen.html").read_text(encoding="utf-8", errors="ignore")
KAB = (FX / "amz_page_kabfit.html").read_text(encoding="utf-8", errors="ignore")


def test_parse_van_heusen_page():
    it = parse_amazon_page(VH, "https://www.amazon.in/dp/B073WC56W7")
    assert it["asin"] == "B073WC56W7"
    assert it["title"].startswith("Van Heusen")
    assert "T-Shirts" in it["breadCrumbs"]
    at = {a["key"]: a["value"] for a in it["attributes"]}
    assert at["Style Number"] == "60001" and at["Colour"] == "Blue Melange" and at["Department"] == "Men"
    assert it["listPrice"]["value"] == 599
    assert it["highResolutionImages"][0].startswith("https://m.media-amazon.com/")
    sp = from_amazon(it)
    assert sp.category == Category.APPAREL
    assert (sp.canon.brand, sp.canon.style_code, sp.canon.base_colour, sp.canon.gender) == ("van heusen", "60001", "blue", "men")


def test_parse_kabfit_page():
    sp = from_amazon(parse_amazon_page(KAB, "https://www.amazon.in/dp/B0HNM9C2VL"))
    assert sp.category == Category.APPAREL and sp.canon.style_code is None  # seller SKU is not a style code


async def test_get_source_reads_page_without_apify(monkeypatch):
    async def fail(*a, **k):
        raise AssertionError("Apify must not be called when the page loads")
    monkeypatch.setattr(amazon, "run_actor", fail)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=VH))) as c:
        sp = await amazon.get_source(c, "https://www.amazon.in/Van-Heusen-T-Shirt/dp/B073WC56W7/ref=x?th=1")
    assert sp.asin == "B073WC56W7" and sp.canon.style_code == "60001"


async def test_blocked_page_falls_back_to_apify(monkeypatch):
    called = []
    async def actor(*a, **k):
        called.append(1)
        return FetchStatus.ERROR, []
    monkeypatch.setattr(amazon, "run_actor", actor)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503, text="no"))) as c:
        try:
            await amazon.get_source(c, "https://www.amazon.in/dp/B073WC56W7")
        except amazon.SourceError:
            pass
    assert called
