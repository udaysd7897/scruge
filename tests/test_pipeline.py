import asyncio
import json
from pathlib import Path

import pytest

from app import llm, pipeline
from app.extract import from_amazon, from_croma, from_flipkart_page
from app.llm import llm_tiebreak
from app.models import Candidate, Canonical, Category, FetchStatus, Platform, SourceProduct
from app.normalize import base_colour
from app.pipeline import PLATFORMS, check
from app.queries import ladder
from app.sources.amazon import SourceError

FX = Path(__file__).parent / "fixtures"
FLIPKART, CROMA, MYNTRA = Platform.FLIPKART, Platform.CROMA, Platform.MYNTRA
URL = "https://www.amazon.in/dp/B0GL8GXNTS"
FK_URL = "https://www.flipkart.com/samsung-galaxy-s26-ultra-5g-black-512-gb/p/itmabc?pid=MOBHKGAPBMXRGGXZ"


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def phone_src(model_code=None, colour="Black"):
    canon = Canonical(brand="samsung", family="galaxy s26 ultra", model_code=model_code, ram_gb=12,
                      storage_gb=512, colour=colour, base_colour=base_colour(colour),
                      title=f"Samsung Galaxy S26 Ultra 5G ({colour}, 12GB RAM, 512GB Storage)")
    return SourceProduct(URL, "B0GL8GXNTS", canon.title, None, Category.PHONE, canon)


def amazon_src():
    item = next(i for i in json.loads((FX / "amz_apify.json").read_text()) if i["asin"] == "B0GL8GXNTS")
    return from_amazon(item)


def croma_fixture():
    return [from_croma(i) for i in json.loads((FX / "croma_apify.json").read_text())]


def fk_fixture():
    return from_flipkart_page((FX / "fk_s26_512blk.html").read_text(), FK_URL)


# ------------------------------------------------------------------ ladder

def test_ladder_phone():
    assert ladder(phone_src("SM-S948B"), FLIPKART)[0] == "SM-S948B"
    assert ladder(phone_src(), CROMA) == ["samsung galaxy s26 ultra 12gb 512gb black", "samsung galaxy s26 ultra"]
    assert ladder(phone_src("SM-S948B"), MYNTRA)[0] != "SM-S948B"


def test_ladder_skips_missing_parts_and_dedupes():
    s = phone_src()
    s.canon.ram_gb = None
    assert ladder(s, FLIPKART) == ["samsung galaxy s26 ultra"]


def test_ladder_tv_sneaker_apparel():
    tv = SourceProduct(URL, "A", "Sony Bravia 55 inch", None, Category.TV,
                       Canonical(brand="sony", family="bravia 2", model_code="K-55S25B", screen_in=55))
    assert ladder(tv, FLIPKART) == ["K-55S25B", "sony bravia 2 55 inch", "sony bravia 2"]
    sn = SourceProduct(URL, "B", "Nike Air Max 270 Black", None, Category.SNEAKER,
                       Canonical(brand="nike", family="air max 270", base_colour="black"))
    assert ladder(sn, MYNTRA) == ["nike air max 270 black", "nike air max 270"]
    ap = SourceProduct(URL, "C", "Puma Men Essentials Logo Regular Fit Polo T-Shirt Navy", None,
                       Category.APPAREL,
                       Canonical(brand="puma", product_type="polo", base_colour="blue",
                                 title="Puma Men Essentials Logo Regular Fit Polo T-Shirt Navy"))
    q = ladder(ap, MYNTRA)
    assert len(q) == 1 and q[0].startswith("puma polo blue ")
    assert q[0].split()[3:] == ["essentials", "logo", "regular"]


# ------------------------------------------------------------------ llm

async def test_llm_tiebreak_no_key():
    assert await llm_tiebreak(phone_src(), croma_fixture()[:2]) is None


async def test_llm_tiebreak_parses_choice(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    survivors = croma_fixture()[:3]
    replies = iter(["2", "none", "7", "garbage"])

    async def fake_ask(prompt):
        assert "Return ONLY" in prompt and survivors[1].title in prompt
        return next(replies)

    monkeypatch.setattr(llm, "_ask", fake_ask)
    assert await llm_tiebreak(phone_src(), survivors) is survivors[1]
    for _ in range(3):
        assert await llm_tiebreak(phone_src(), survivors) is None


async def test_llm_tiebreak_exception_is_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    async def boom(prompt):
        raise RuntimeError("x")

    monkeypatch.setattr(llm, "_ask", boom)
    assert await llm_tiebreak(phone_src(), croma_fixture()[:2]) is None


# ------------------------------------------------------------------ pipeline

def test_platforms():
    assert PLATFORMS[Category.PHONE] == [FLIPKART, CROMA] and PLATFORMS[Category.TV] == [FLIPKART, CROMA]
    assert PLATFORMS[Category.SNEAKER] == [FLIPKART, MYNTRA] and PLATFORMS[Category.APPAREL] == [FLIPKART, MYNTRA]


def patch(monkeypatch, src=None, fk=None, croma=None, myntra=None, src_exc=None):
    async def gs(client, url):
        if src_exc:
            raise src_exc
        return src or amazon_src()

    async def default_fk(client, q):
        return FetchStatus.OK, fk_fixture()

    async def default_croma(client, q):
        return FetchStatus.OK, croma_fixture()

    async def default_myntra(client, q):
        return FetchStatus.EMPTY, []

    monkeypatch.setattr(pipeline, "get_source", gs)
    monkeypatch.setitem(pipeline.ADAPTERS, FLIPKART, fk or default_fk)
    monkeypatch.setitem(pipeline.ADAPTERS, CROMA, croma or default_croma)
    monkeypatch.setitem(pipeline.ADAPTERS, MYNTRA, myntra or default_myntra)


async def run(url=URL):
    return [e async for e in check(url)]


async def test_check_e2e(monkeypatch):
    patch(monkeypatch)
    events = await run()
    json.dumps(events)  # JSON-serialisable
    assert events[0]["type"] == "source" and events[-1]["type"] == "done"
    assert events[0]["data"]["category"] == "phone"
    prog = [e for e in events if e["type"] == "progress"]
    assert [p["message"] for p in prog] == ["Searching Flipkart…", "Searching Croma…"]
    assert [p["platform"] for p in prog] == ["flipkart", "croma"]
    results = {e["data"]["platform"]: e["data"] for e in events if e["type"] == "result"}
    assert results["flipkart"]["outcome"] == "In stock" and "pid=MOBHKGAPBMXRGGXZ" in results["flipkart"]["url"]
    assert results["croma"]["outcome"] == "In stock" and results["croma"]["url"].endswith("/p/327249")
    assert results["flipkart"]["colour_fallback_note"] == "Not available in Sky Blue; showing Black"
    assert results["croma"]["colour_fallback_note"] == "Not available in Sky Blue; showing Black"


async def test_check_croma_timeout(monkeypatch):
    async def croma(client, q):
        raise TimeoutError

    patch(monkeypatch, croma=croma)
    events = await run()
    results = {e["data"]["platform"]: e["data"] for e in events if e["type"] == "result"}
    assert results["croma"]["outcome"] == "Couldn't check" and results["croma"]["url"] is None
    assert results["croma"]["reason"] == "Couldn't check Croma: timed out"
    assert results["flipkart"]["outcome"] == "In stock"


async def test_check_platform_wait_for_timeout(monkeypatch):
    async def slow(client, q):
        await asyncio.sleep(10)

    patch(monkeypatch, croma=slow)
    monkeypatch.setitem(pipeline.TIMEOUTS, CROMA, 0.05)
    results = {e["data"]["platform"]: e["data"] for e in await run() if e["type"] == "result"}
    assert results["croma"]["reason"] == "Couldn't check Croma: timed out"


async def test_check_unexpected_exception(monkeypatch):
    async def bad(client, q):
        raise KeyError("x")

    patch(monkeypatch, fk=bad)
    results = {e["data"]["platform"]: e["data"] for e in await run() if e["type"] == "result"}
    assert results["flipkart"]["outcome"] == "Couldn't check"
    assert results["flipkart"]["reason"] == "Couldn't check Flipkart: something went wrong"


async def test_check_unsupported(monkeypatch):
    src = amazon_src()
    src.category = Category.UNSUPPORTED
    patch(monkeypatch, src=src)
    events = await run()
    assert [e["type"] for e in events] == ["source", "error", "done"]
    assert events[1]["message"] == "This product isn't a phone, TV, sneaker or T-shirt/polo/jersey."


@pytest.mark.parametrize("exc", [ValueError("Please paste an Amazon.in product link"), SourceError("nope")])
async def test_check_source_errors(monkeypatch, exc):
    patch(monkeypatch, src_exc=exc)
    events = await run("https://x")
    assert events == [{"type": "error", "message": str(exc)}, {"type": "done"}]


async def test_ladder_walk_accumulates_and_stops(monkeypatch):
    seen = []
    fk = fk_fixture()

    async def flip(client, q):
        seen.append(q)
        # rung 1 (model code) finds nothing, rung 2 finds the phone
        return (FetchStatus.EMPTY, []) if len(seen) == 1 else (FetchStatus.OK, fk + fk)

    src = phone_src("SM-S948B")
    patch(monkeypatch, src=src, fk=flip)
    results = {e["data"]["platform"]: e["data"] for e in await run() if e["type"] == "result"}
    assert seen == ["SM-S948B", "samsung galaxy s26 ultra 12gb 512gb black"]
    assert results["flipkart"]["outcome"] == "In stock"


async def test_ladder_all_rungs_none_reports_statuses(monkeypatch):
    seen = []

    async def flip(client, q):
        seen.append(q)
        return (FetchStatus.BLOCKED, []) if len(seen) == 1 else (FetchStatus.EMPTY, [])

    patch(monkeypatch, src=phone_src(), fk=flip)
    results = {e["data"]["platform"]: e["data"] for e in await run() if e["type"] == "result"}
    assert len(seen) == 2
    assert results["flipkart"]["outcome"] == "Couldn't check"  # BLOCKED rung recorded


async def test_tie_calls_llm_and_resolves(monkeypatch):
    def cand(n):
        canon = Canonical(brand="samsung", family="galaxy s26 ultra", ram_gb=12, storage_gb=512,
                          colour="Black", base_colour="black", title="Samsung Galaxy S26 Ultra Black 512")
        return Candidate(CROMA, f"https://www.croma.com/x/p/{n}", canon.title, canon, True)

    a, b = cand(1), cand(2)

    async def croma(client, q):
        return FetchStatus.OK, [a, b]

    calls = []

    async def tb(src, survivors):
        calls.append(survivors)
        return survivors[1]

    patch(monkeypatch, src=phone_src(), croma=croma)
    monkeypatch.setattr(pipeline, "llm_tiebreak", tb)
    results = {e["data"]["platform"]: e["data"] for e in await run() if e["type"] == "result"}
    assert calls and results["croma"]["outcome"] == "In stock"
    assert results["croma"]["url"] == calls[0][1].url
