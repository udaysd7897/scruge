import json
from pathlib import Path

import httpx
import pytest

from app.models import FetchStatus as S
from app.sources import apify
from app.sources.amazon import SourceError, amazon_dp_url, get_source, resolve_amazon_url
from app.sources.apify import run_actor
from app.sources.croma import croma_candidates
from app.sources.flipkart import flipkart_candidates, flipkart_search
from app.sources.http import classify, fetch
from app.sources.myntra import myntra_candidates

FX = Path(__file__).parent / "fixtures"


def read(n):
    return (FX / n).read_text()


def mock(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


def html_client(body, status=200):
    return mock(lambda req: httpx.Response(status, text=body))


@pytest.fixture(autouse=True)
def _cache(tmp_path, monkeypatch):
    monkeypatch.setattr(apify, "CACHE_DIR", tmp_path / "apify")
    monkeypatch.setenv("APIFY_KEY", "test-key")


def test_classify():
    assert classify(200, read("amazon_bm_verify.html")) == S.BLOCKED
    assert classify(403, "<H1>Access Denied</H1>") == S.BLOCKED
    for c in (429, 503, 529):
        assert classify(c, "x") == S.BLOCKED
    assert classify(200, "Please solve this CAPTCHA") == S.BLOCKED
    assert classify(200, '<meta http-equiv="refresh" content="0;url=/x">') == S.BLOCKED
    assert classify(200, "<html>" + "x" * 30000 + "captcha</html>") == S.OK  # big real page mentioning captcha
    assert classify(404, "nope") == S.ERROR
    assert classify(200, "<html>fine</html>") == S.OK


async def test_fetch():
    st, body = await fetch(html_client("<html>hello</html>"), "https://x.test/")
    assert st == S.OK and "hello" in body
    st, _ = await fetch(html_client("x", 403), "https://x.test/")
    assert st == S.BLOCKED

    def boom(req):
        raise httpx.ConnectTimeout("t")

    st, _ = await fetch(mock(boom), "https://x.test/")
    assert st == S.ERROR


def test_amazon_dp_url():
    assert amazon_dp_url("https://www.amazon.in/Samsung-Galaxy/dp/B0GL8GXNTS/ref=sr_1_1?crid=X") == "https://www.amazon.in/dp/B0GL8GXNTS"
    assert amazon_dp_url("https://amazon.in/gp/product/B0GL8GXNTS") == "https://www.amazon.in/dp/B0GL8GXNTS"
    assert amazon_dp_url("https://www.flipkart.com/x/p/itm1") is None
    assert amazon_dp_url("https://www.amazon.com/dp/B0GL8GXNTS") is None


async def test_resolve_amazon_url():
    def h(req):
        if req.url.host == "amzn.in":
            return httpx.Response(301, headers={"Location": "https://www.amazon.in/Foo/dp/B0GL8GXNTS?x=1"})
        return httpx.Response(200, text="ok")

    c = mock(h)
    assert await resolve_amazon_url(c, "https://amzn.in/d/abc") == "https://www.amazon.in/dp/B0GL8GXNTS"
    assert await resolve_amazon_url(c, "https://www.amazon.in/a/dp/B0GL8GXNTS") == "https://www.amazon.in/dp/B0GL8GXNTS"
    with pytest.raises(ValueError, match="Amazon.in product link"):
        await resolve_amazon_url(c, "https://www.flipkart.com/x/p/itm1")


async def test_flipkart_search():
    st, urls = await flipkart_search(html_client(read("fk_s26.html")), "samsung galaxy s26 ultra")
    assert st == S.OK and any("pid=MOBHZ7T3MPKXGDXJ" in u for u in urls)
    assert len(urls) <= 10 and len(set(urls)) == len(urls)
    assert all(u.startswith("https://www.flipkart.com/") and u.count("?") == 1 for u in urls)


async def test_flipkart_search_empty_and_blocked():
    st, urls = await flipkart_search(html_client("<html>" + "x" * 3000 + "</html>"), "q")
    assert st == S.EMPTY and urls == []
    st, _ = await flipkart_search(html_client("x", 403), "q")
    assert st == S.BLOCKED


async def test_flipkart_candidates():
    search, prod = read("fk_s26.html"), read("fk_s26_512blk.html")

    def h(req):
        return httpx.Response(200, text=search if "/search" in req.url.path else prod)

    st, cs = await flipkart_candidates(mock(h), "samsung galaxy s26 ultra")
    assert st == S.OK and len(cs) >= 1


async def test_flipkart_candidates_all_blocked():
    search = read("fk_s26.html")

    def h(req):
        return httpx.Response(200, text=search) if "/search" in req.url.path else httpx.Response(403, text="x")

    st, cs = await flipkart_candidates(mock(h), "q")
    assert st == S.BLOCKED and cs == []


async def test_myntra():
    seen = []

    def h(req):
        seen.append(str(req.url))
        return httpx.Response(200, text=read("my_search.html"))

    st, cs = await myntra_candidates(mock(h), "nike running shoes")
    assert st == S.OK and len(cs) == 50
    assert seen[0] == "https://www.myntra.com/nike-running-shoes?rawQuery=nike+running+shoes" or seen[0].startswith("https://www.myntra.com/nike-running-shoes?rawQuery=nike")


async def test_myntra_unexpected_page():
    st, cs = await myntra_candidates(html_client("<html>" + "y" * 4000 + "</html>"), "nike shoes")
    assert st == S.ERROR and cs == []


def apify_client(payload, calls):
    def h(req):
        calls.append(req)
        return httpx.Response(200, json=payload)

    return mock(h)


async def test_croma():
    calls = []
    st, cs = await croma_candidates(apify_client(json.loads(read("croma_apify.json")), calls), "samsung galaxy s24")
    assert st == S.OK and len(cs) == 5
    r = calls[0]
    assert "croma-product-scraper" in str(r.url) and "run-sync-get-dataset-items?timeout=90" in str(r.url)
    assert r.headers["authorization"] == "Bearer test-key" and "test-key" not in str(r.url)


async def test_run_actor_cache_and_empty():
    calls = []
    c = apify_client([{"a": 1}], calls)
    assert await run_actor(c, "x~y", {"k": 1}) == (S.OK, [{"a": 1}])
    assert await run_actor(c, "x~y", {"k": 1}) == (S.OK, [{"a": 1}])
    assert len(calls) == 1
    calls2 = []
    e = apify_client([], calls2)
    assert (await run_actor(e, "x~y", {"k": 2}))[0] == S.EMPTY
    await run_actor(e, "x~y", {"k": 2})
    assert len(calls2) == 2  # empty not cached


async def test_run_actor_no_key(monkeypatch):
    monkeypatch.delenv("APIFY_KEY")
    calls = []
    st, items = await run_actor(apify_client([{"a": 1}], calls), "x~y", {})
    assert st == S.ERROR and items == [] and not calls


async def test_run_actor_offline_cache_miss_is_error(monkeypatch):
    monkeypatch.setattr(apify, "OFFLINE", True)
    calls = []
    st, items = await run_actor(apify_client([{"a": 1}], calls), "x~off", {"k": 9})
    assert st == S.ERROR and items == [] and not calls


async def test_get_source():
    calls = []
    c = apify_client(json.loads(read("amz_apify.json")), calls)
    sp = await get_source(c, "https://www.amazon.in/Foo/dp/B0GL8GXNTS?x=1")
    assert sp.asin and sp.title
    assert json.loads(calls[0].content)["categoryOrProductUrls"] == [{"url": "https://www.amazon.in/dp/B0GL8GXNTS"}]
    with pytest.raises(SourceError):
        await get_source(apify_client([], []), "https://www.amazon.in/dp/B0AAAAAAAA")


@pytest.mark.parametrize("blob", ['{bad json', '{"searchData":{}}'])
async def test_myntra_bad_myx_is_error(blob):
    page = "<html><script>window.__myx = " + blob + "</script>" + "y" * 4000 + "</html>"
    st, cs = await myntra_candidates(html_client(page), "nike shoes")
    assert st == S.ERROR and cs == []


async def test_myntra_zero_products_is_empty():
    page = '<html><script>window.__myx = {"searchData":{"results":{"products":[]}}}</script>' + "y" * 4000 + "</html>"
    st, cs = await myntra_candidates(html_client(page), "nike shoes")
    assert st == S.EMPTY and cs == []


async def test_croma_junk_items_error():
    st, cs = await croma_candidates(apify_client([{"error": "x"}, "junk"], []), "samsung galaxy s24")
    assert st == S.ERROR and cs == []


async def test_flipkart_half_failed_is_blocked_not_empty():
    search = read("fk_s26.html")
    n = {"i": 0}

    def h(req):
        if "/search" in req.url.path:
            return httpx.Response(200, text=search)
        n["i"] += 1
        # half blocked, half valid pages with no products
        return httpx.Response(403, text="x") if n["i"] % 2 else httpx.Response(200, text="<html>" + "z" * 3000 + "</html>")

    st, cs = await flipkart_candidates(mock(h), "samsung galaxy s26 ultra")
    assert st == S.BLOCKED and cs == []


async def test_run_actor_no_cache_for_non_dict_items():
    calls = []
    c = apify_client([{"a": 1}, "junk"], calls)
    assert (await run_actor(c, "x~z", {"k": 1}))[1] == [{"a": 1}, "junk"]
    await run_actor(c, "x~z", {"k": 1})
    assert len(calls) == 2
