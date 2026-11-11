"""Search for the model, then walk to the exact variant through the product page's sibling links
(Croma ranked the exact S26 Ultra 6th–7th; design report 2026-11-12)."""
from pathlib import Path

import httpx

from app.sources.flipkart import flipkart_candidates, sibling_links

FX = Path(__file__).parent / "fixtures"
PAGE = (FX / "fk_s26_512blk.html").read_text(encoding="utf-8", errors="ignore")
URL = "https://www.flipkart.com/samsung-galaxy-s26-ultra-5g-black-512-gb/p/itmf4799d3841c43?pid=MOBHKGAPBMXRGGXZ"
SKY = "https://www.flipkart.com/samsung-galaxy-s26-ultra-5g-sky-blue-512-gb/p/itmf4799d3841c43?pid=MOBHKGAPHZHYA5GQ"


def test_sibling_links_same_product_other_variants():
    sibs = sibling_links(PAGE, URL)
    assert SKY in sibs and URL not in sibs and len(sibs) == 4


async def test_candidates_include_siblings_of_search_hits():
    search = f'<a href="/samsung-galaxy-s26-ultra-5g-black-512-gb/p/itmf4799d3841c43?pid=MOBHKGAPBMXRGGXZ">x</a>' + " " * 5000
    def h(req):
        return httpx.Response(200, text=search if "/search" in str(req.url) else PAGE)
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        st, cands = await flipkart_candidates(c, "samsung galaxy s26 ultra")
    urls = {x.url for x in cands}
    assert URL in urls and SKY in urls
