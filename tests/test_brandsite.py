import json
from pathlib import Path

import httpx

from app import brandsite
from app.extract import from_amazon
from app.models import Platform
from app.queries import ladder

FX = Path(__file__).parent / "fixtures"


def test_puma_name_from_site_search():
    html = (FX / "puma_site_search_528856.html").read_text(encoding="utf-8", errors="ignore")
    assert brandsite.puma_name(html, "52885601") == "train all day mens breathable training tee"


async def test_official_name_only_for_supported_brand_and_code():
    html = (FX / "puma_site_search_528856.html").read_text(encoding="utf-8", errors="ignore")
    calls = []
    def h(req):
        calls.append(req.url); return httpx.Response(200, text=html)
    brandsite._CACHE.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        assert await brandsite.official_name(c, "puma", "52885601") == "train all day mens breathable training tee"
        assert await brandsite.official_name(c, "puma", "52885601") is not None  # cached
        assert await brandsite.official_name(c, "nike", "HJ5228-101") is None
    assert len(calls) == 1


def test_apparel_ladder_searches_official_name_first():
    sp = from_amazon(json.loads((FX / "amz_puma_tee.json").read_text())[0])
    sp.canon.official_name = "train all day mens breathable training tee"
    for p in (Platform.FLIPKART, Platform.MYNTRA):
        assert ladder(sp, p)[0] == "puma train all day mens breathable training tee black"
