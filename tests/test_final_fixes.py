"""Final whole-branch review fixes (final-findings.md). Realistic source dicts, no hand-built source Canonical."""
from app.extract import from_amazon, from_flipkart_page, from_myntra_search
from app.models import Category, Platform
from app.normalize import product_type
from app.queries import ladder

FLIPKART, CROMA, MYNTRA = Platform.FLIPKART, Platform.CROMA, Platform.MYNTRA


def amz(title, brand, crumbs, colour=None, attrs=(), asin="B0TEST0001"):
    at = [{"key": k, "value": v} for k, v in attrs]
    if colour:
        at.append({"key": "Colour", "value": colour})
    return {"title": title, "brand": brand, "breadCrumbs": crumbs, "attributes": at,
            "url": f"https://www.amazon.in/dp/{asin}", "asin": asin}


ALLEN_SOLLY = amz("Allen Solly Men's Regular Fit Polo T-Shirt (ASKPQRGFS12345_Navy_M)", "Allen Solly",
                  "Clothing & Accessories > Men > T-Shirts & Polos > Polos", "Navy")


# ------------------------------------------------------------------ 1. apparel product type

def test_product_type():
    assert product_type("Allen Solly Men's Regular Fit Polo T-Shirt", None) == "polo"
    assert product_type("Puma Men Collar Polo", None) == "polo"
    assert product_type("Puma Men's Regular Fit T-Shirt", None) == "tee"
    assert product_type("Jockey Men's Round Neck Tshirt", None) == "tee"
    assert product_type("HRX Men Crew Neck Tee", None) == "tee"
    assert product_type("Puma Men teamLIGA Football Jersey", None) == "jersey"
    assert product_type("Allen Solly Men's Regular Fit Shirt", "Clothing > Men > T-Shirts & Polos > Polos") == "polo"
    assert product_type("Puma Men's Logo Top", "Clothing > Men > T-Shirts & Polos > T-Shirts") == "tee"
    # "U.S. Polo Assn." is a brand, not a product type
    assert product_type("U.S. Polo Assn. Men Round Neck T-Shirt", None) == "tee"
    assert product_type("Levi's Men's Jeans", None) is None


def test_amazon_apparel_has_product_type_and_ladder():
    sp = from_amazon(ALLEN_SOLLY)
    assert sp.category == Category.APPAREL
    assert (sp.canon.brand, sp.canon.product_type, sp.canon.base_colour) == ("allen solly", "polo", "navy")
    assert sp.missing_required == []
    assert ladder(sp, FLIPKART) and ladder(sp, MYNTRA)
    assert ladder(sp, MYNTRA)[0].startswith("allen solly polo navy")


def test_apparel_ladder_never_empty_with_brand():
    sp = from_amazon(amz("Puma Men's Essentials Logo Regular Fit Top", "Puma",
                         "Clothing & Accessories > Men > Tops"))
    assert sp.category == Category.APPAREL or sp.category == Category.UNSUPPORTED
    sp.category = Category.APPAREL  # source missing type and colour
    q = ladder(sp, MYNTRA)
    assert q == ["puma essentials logo regular fit"]


def test_flipkart_apparel_product_type():
    html = ('<script type="application/ld+json">{"@type":"Product","name":"Allen Solly Solid Men Polo Neck '
            'Navy Blue T-Shirt","brand":{"name":"Allen Solly"},"color":"Navy Blue","offers":{"price":999,'
            '"availability":"http://schema.org/InStock"}}</script>')
    [fk] = from_flipkart_page(html, "https://www.flipkart.com/x/p/itmabc?pid=TSHX")
    assert (fk.canon.product_type, fk.canon.base_colour) == ("polo", "navy")


def test_myntra_polo_listed_under_tshirts_is_polo():
    import json
    prods = [{"productId": 1, "productName": "Allen Solly Men Navy Blue Solid Regular Fit Polo T-shirt",
              "brand": "Allen Solly", "primaryColour": "Navy Blue", "articleType": {"typeName": "Tshirts"},
              "price": 999, "inventoryInfo": [{"available": True}], "landingPageUrl": "tshirts/allen-solly/1"},
             {"productId": 2, "productName": "Allen Solly Men Navy Blue Round Neck T-shirt",
              "brand": "Allen Solly", "primaryColour": "Navy Blue", "articleType": {"typeName": "Tshirts"},
              "price": 799, "inventoryInfo": [{"available": True}], "landingPageUrl": "tshirts/allen-solly/2"}]
    html = "<script>window.__myx = " + json.dumps({"searchData": {"results": {"products": prods}}}) + "</script>"
    a, b = from_myntra_search(html)
    assert (a.canon.product_type, b.canon.product_type) == ("polo", "tee")


# ------------------------------------------------------------------ 2. sneaker/apparel family + end-to-end

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from app.matcher import decide, to_result, veto  # noqa: E402
from app.models import FetchStatus, Outcome  # noqa: E402
from app.normalize import model_line  # noqa: E402

FX = Path(__file__).parent / "fixtures"
SNEAKER_CRUMBS = "Shoes & Handbags > Shoes > Men's Shoes > Sneakers"


def myntra(*prods):
    out = []
    for i, (name, brand, colour, art, avail) in enumerate(prods):
        out.append({"productId": 100 + i, "productName": name, "brand": brand, "primaryColour": colour,
                    "articleType": {"typeName": art}, "price": 2999,
                    "inventoryInfo": [{"available": avail}], "landingPageUrl": f"x/{brand}/{100 + i}/buy"})
    html = "<script>window.__myx = " + json.dumps({"searchData": {"results": {"products": out}}}) + "</script>"
    return from_myntra_search(html)


def fk_page(name, brand, price=9999, avail="InStock", colour=None, **spec):
    ld = {"@type": "Product", "name": name, "brand": {"name": brand},
          "offers": {"price": price, "availability": f"http://schema.org/{avail}"}}
    if colour:
        ld["color"] = colour
    rows = "".join(f"<tr><td>{k.replace('_', ' ')}</td><td>{v}</td></tr>" for k, v in spec.items())
    return f'<script type="application/ld+json">{json.dumps(ld)}</script><table>{rows}</table>'


def fk(name, brand, pid, **kw):
    return from_flipkart_page(fk_page(name, brand, **kw), f"https://www.flipkart.com/x/p/itm{pid.lower()}?pid={pid}")


def test_model_line_strips_uk_sizes():
    assert model_line("Nike Air Max 270 8 UK", "nike") == "air max 270"
    assert model_line("Nike Air Max 270 UK 8", "nike") == "air max 270"
    assert model_line("Nike Air Max 270 Size 9", "nike") == "air max 270"
    assert model_line("ADIDAS Men Grand Court 3.0 Tennis Shoes", "ADIDAS") == "grand court 3 0"


def test_amazon_sneaker_family_cut_at_comma():
    sp = from_amazon(amz("Nike Men's Air Max 270 Sneaker, Black/White-Anthracite, 8 UK", "Nike",
                         SNEAKER_CRUMBS, "Black/White-Anthracite"))
    assert sp.category == Category.SNEAKER
    assert (sp.canon.family, sp.canon.base_colour, sp.missing_required) == ("air max 270", "black", [])


def test_sneaker_family_wording_differences_not_vetoed():
    sp = from_amazon(amz("adidas Men's Grand Court 3.0 Sneaker", "adidas", SNEAKER_CRUMBS,
                         "Cloud White/Core Black"))
    [c] = myntra(("ADIDAS Men Grand Court 3.0 Tennis Shoes", "ADIDAS", "White", "Casual Shoes", True))
    assert veto(sp.canon, c, Category.SNEAKER) is None


def test_sneaker_different_model_still_vetoed():
    sp = from_amazon(amz("Nike Men's Air Max 270 Sneaker, Black/White-Anthracite, 8 UK", "Nike",
                         SNEAKER_CRUMBS, "Black"))
    [c] = myntra(("Nike Men Air Max 90 Sneakers", "Nike", "Black", "Casual Shoes", True))
    assert veto(sp.canon, c, Category.SNEAKER) is not None


def test_sneaker_extra_model_words_is_only_possible():
    # "Air Max 270 React" is not "Air Max 270": not vetoed by the word rules, so never a confident match
    sp = from_amazon(amz("Nike Men's Air Max 270 Sneaker", "Nike", SNEAKER_CRUMBS, "Black"))
    cands = myntra(("Nike Men Air Max 270 React Sneakers", "Nike", "Black", "Casual Shoes", True))
    r = to_result(MYNTRA, decide(sp, cands), [FetchStatus.OK], sp.canon.colour)
    assert r.outcome == Outcome.POSSIBLE


def _e2e(sp, platform, cands):
    assert ladder(sp, platform), "ladder must not be empty"
    return to_result(platform, decide(sp, cands), [FetchStatus.OK], sp.canon.colour)


def test_e2e_phone():
    sp = from_amazon(amz("Redmi Note 14 5G (Titan Black, 8GB RAM, 128GB Storage)", "Redmi",
                         "Electronics > Mobiles & Accessories > Smartphones & Basic Mobiles > Smartphones"))
    assert sp.missing_required == []
    assert ladder(sp, FLIPKART)[0] == "xiaomi note 14 8gb 128gb titan black"
    cands = (fk("REDMI Note 14 5G (Titan Black, 128 GB)", "REDMI", "MOBA", Model_Name="Note 14 5G", RAM="8 GB",
                Internal_Storage="128 GB", Color="Titan Black")
             + fk("REDMI Note 14 5G (Titan Black, 256 GB)", "REDMI", "MOBB", Model_Name="Note 14 5G", RAM="8 GB",
                  Internal_Storage="256 GB", Color="Titan Black")
             + fk("REDMI Note 14 Pro 5G (Titan Black, 128 GB)", "REDMI", "MOBC", Model_Name="Note 14 Pro 5G",
                  RAM="8 GB", Internal_Storage="128 GB", Color="Titan Black"))
    r = _e2e(sp, FLIPKART, cands)
    assert r.outcome == Outcome.IN_STOCK and "pid=MOBA" in r.url


def test_e2e_tv():
    item = next(i for i in json.loads((FX / "amz_golden.json").read_text()) if i["asin"] == "B0GTZ8WM5W")
    sp = from_amazon(item)
    url = "https://www.flipkart.com/lg-139-cm-55-inch/p/itmee9cd7f3011a2?pid=TVSHMYS2G69WGGAK"
    cands = from_flipkart_page((FX / "fk_tv_lg_nu870.html").read_text(), url) + \
        from_flipkart_page((FX / "fk_tv_lg_ua8200.html").read_text(),
                           "https://www.flipkart.com/lg/p/itm383c359293f5b?pid=TVSHCAYXEGC76H9F")
    r = _e2e(sp, FLIPKART, cands)
    assert r.outcome == Outcome.IN_STOCK and r.url == url


def test_e2e_sneaker():
    sp = from_amazon(amz("adidas Men's Grand Court 3.0 Sneaker", "adidas", SNEAKER_CRUMBS,
                         "Cloud White/Core Black"))
    assert ladder(sp, MYNTRA)[0] == "adidas grand court 3 0 white"
    cands = myntra(("ADIDAS Men Grand Court 3.0 Tennis Shoes", "ADIDAS", "White", "Casual Shoes", True),
                   ("ADIDAS Men Grand Court 3.0 Tennis Shoes", "ADIDAS", "Black", "Casual Shoes", True),
                   ("ADIDAS Men Grand Court 2.0 Tennis Shoes", "ADIDAS", "White", "Casual Shoes", True))
    r = _e2e(sp, MYNTRA, cands)
    assert r.outcome == Outcome.IN_STOCK and r.url == cands[0].url


def test_e2e_apparel():
    sp = from_amazon(ALLEN_SOLLY)
    cands = myntra(("Allen Solly Men Navy Blue Solid Regular Fit Polo T-shirt", "Allen Solly", "Navy Blue",
                    "Tshirts", True),
                   ("Allen Solly Men Navy Blue Regular Fit Round Neck T-shirt", "Allen Solly", "Navy Blue",
                    "Tshirts", True),
                   ("Allen Solly Men Black Solid Regular Fit Polo T-shirt", "Allen Solly", "Black", "Tshirts", True))
    r = _e2e(sp, MYNTRA, cands)
    assert r.outcome == Outcome.IN_STOCK and r.url == cands[0].url


# ------------------------------------------------------------------ 5. one side without distinctive words

def test_generic_candidate_title_is_not_vetoed_but_only_possible():
    sp = from_amazon(amz("Puma Men's Essentials Logo Regular Fit Polo T-Shirt", "Puma",
                         "Clothing & Accessories > Men > T-Shirts & Polos > Polos", "Black"))
    cands = myntra(("Puma Men Polo T-shirt", "Puma", "Black", "Tshirts", True))
    assert veto(sp.canon, cands[0], Category.APPAREL) is None
    r = to_result(MYNTRA, decide(sp, cands), [FetchStatus.OK], sp.canon.colour)
    assert r.outcome == Outcome.POSSIBLE


def test_apparel_candidate_with_extra_design_words_is_only_possible():
    sp = from_amazon(amz("Puma Men's Regular Fit T-Shirt", "Puma",
                         "Clothing & Accessories > Men > T-Shirts & Polos > T-Shirts", "Black"))
    cands = myntra(("Puma Men Graphic Printed Regular Fit T-shirt", "Puma", "Black", "Tshirts", True))
    assert veto(sp.canon, cands[0], Category.APPAREL) is None
    assert to_result(MYNTRA, decide(sp, cands), [FetchStatus.OK], "Black").outcome == Outcome.POSSIBLE


def test_polo_collar_wording_is_possible_not_not_listed():
    sp = from_amazon(amz("Allen Solly Men's Regular Fit Polo T-Shirt", "Allen Solly",
                         "Clothing & Accessories > Men > T-Shirts & Polos > Polos", "Navy Blue"))
    cands = myntra(("Allen Solly Men Navy Blue Solid Polo Collar T-shirt", "Allen Solly", "Navy Blue", "Tshirts",
                    True))
    assert to_result(MYNTRA, decide(sp, cands), [FetchStatus.OK], "Navy Blue").outcome == Outcome.POSSIBLE


# ------------------------------------------------------------------ 3. Flipkart partial failures

import httpx  # noqa: E402
import pytest  # noqa: E402

from app import pipeline  # noqa: E402
from app.sources.flipkart import flipkart_candidates  # noqa: E402

REDMI = amz("Redmi Note 14 5G (Titan Black, 8GB RAM, 128GB Storage)", "Redmi",
            "Electronics > Mobiles & Accessories > Smartphones & Basic Mobiles > Smartphones")


def _redmi_page(storage, colour="Titan Black"):
    return fk_page(f"REDMI Note 14 5G ({colour}, {storage} GB)", "REDMI", Model_Name="Note 14 5G", RAM="8 GB",
                   Internal_Storage=f"{storage} GB", Color=colour)


def _fk_client(pages: dict[str, tuple[int, str]]):
    links = "".join(f'<a href="/redmi-note-14-5g/p/itm{pid.lower()}?pid={pid}">x</a>' for pid in pages)
    search = "<html>" + links + "y" * 25_000 + "</html>"

    def h(req):
        if req.url.path == "/search":
            return httpx.Response(200, text=search)
        code, body = pages[req.url.params["pid"]]
        return httpx.Response(code, text=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(h))


@pytest.fixture
def _no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


async def test_flipkart_some_pages_blocked_returns_blocked_with_parsed_candidates():
    pages = {"MOB1": (403, "x"), "MOB2": (200, _redmi_page(256)), "MOB3": (200, _redmi_page(512))}
    st, cands = await flipkart_candidates(_fk_client(pages), "redmi note 14")
    assert st == FetchStatus.BLOCKED and len(cands) == 2


async def test_flipkart_partial_block_without_match_is_couldnt_check(_no_llm):
    sp = from_amazon(REDMI)
    pages = {"MOB1": (403, "x"), "MOB2": (403, "x"), "MOB3": (200, _redmi_page(256)),
             "MOB4": (200, _redmi_page(512)), "MOB5": (200, _redmi_page(64))}
    async with _fk_client(pages) as client:
        r = await pipeline.run_platform(client, sp, FLIPKART)
    assert r.outcome == Outcome.COULDNT_CHECK


async def test_flipkart_partial_block_with_exact_match_is_in_stock(_no_llm):
    sp = from_amazon(REDMI)
    pages = {"MOB1": (403, "x"), "MOB2": (200, _redmi_page(128)), "MOB3": (200, _redmi_page(256))}
    async with _fk_client(pages) as client:
        r = await pipeline.run_platform(client, sp, FLIPKART)
    assert r.outcome == Outcome.IN_STOCK and "pid=MOB2" in r.url


# ------------------------------------------------------------------ 4. iPhones (no RAM on Amazon)

PHONE_CRUMBS = "Electronics > Mobiles & Accessories > Smartphones & Basic Mobiles > Smartphones"
IPHONE = amz("Apple iPhone 17 Pro 256 GB: 15.93 cm (6.3″) Display with Promotion; A19 Pro Chip; Cosmic Orange",
             "Apple", PHONE_CRUMBS, "Cosmic Orange")


def test_iphone_source_without_ram():
    sp = from_amazon(IPHONE)
    assert (sp.canon.family, sp.canon.storage_gb, sp.canon.ram_gb) == ("iphone 17 pro", 256, None)
    assert sp.missing_required == []
    assert "apple iphone 17 pro 256gb cosmic orange" in ladder(sp, FLIPKART)


def test_title_family_cuts():
    from app.extract import _title_family
    assert _title_family("Apple iPhone 16 (128 GB) - Black", "Apple") == "iphone 16"
    assert _title_family("Apple iPhone 16 - Black", "Apple") == "iphone 16"
    assert _title_family("Samsung Galaxy S25, 256GB", "Samsung") == "galaxy s25"


def test_phone_ladder_skips_missing_ram_for_any_brand():
    sp = from_amazon(amz("Samsung Galaxy S26 Ultra 5G (Black, 512GB Storage)", "Samsung", PHONE_CRUMBS, "Black"))
    assert sp.canon.ram_gb is None and sp.missing_required == ["ram_gb"]
    assert ladder(sp, FLIPKART)[0] == "samsung galaxy s26 ultra 512gb black"


def test_iphone_matches_flipkart_listing_without_ram():
    sp = from_amazon(IPHONE)
    cands = (fk("Apple iPhone 17 Pro (Cosmic Orange, 256 GB)", "Apple", "MOBI1", Model_Name="iPhone 17 Pro",
                Internal_Storage="256 GB", Color="Cosmic Orange")
             + fk("Apple iPhone 17 Pro (Cosmic Orange, 512 GB)", "Apple", "MOBI2", Model_Name="iPhone 17 Pro",
                  Internal_Storage="512 GB", Color="Cosmic Orange")
             + fk("Apple iPhone 17 Pro Max (Cosmic Orange, 256 GB)", "Apple", "MOBI3", Model_Name="iPhone 17 Pro Max",
                  Internal_Storage="256 GB", Color="Cosmic Orange"))
    assert cands[0].canon.ram_gb is None
    r = _e2e(sp, FLIPKART, cands)
    assert r.outcome == Outcome.IN_STOCK and "pid=MOBI1" in r.url


# ------------------------------------------------------------------ 6. pack count

def test_pack_count_words_and_pieces():
    from app.normalize import distinctive_words, pack_count
    assert pack_count("Puma Men Polo T-Shirt Pack Of Two") == 2
    assert pack_count("Jockey Men Tee 2 pcs") == 2
    assert pack_count("Jockey Men Tee 3 Pieces") == 3
    assert pack_count("Jockey Men Tee 1 pc") == 1
    assert pack_count("Pack of 3 T-Shirts") == 3
    assert pack_count("Set of Three Tees") == 3
    assert pack_count("Combo of 2 Polos") == 2
    assert pack_count("Puma Men Polo") == 1
    assert pack_count("Puma Men's One8 Polo") == 1
    # the pack words themselves are not distinctive words
    assert distinctive_words("Puma Logo Polo Pack Of Two", "puma") == {"logo"}
    assert distinctive_words("Puma Logo Polo 2 pcs", "puma") == {"logo"}


# ------------------------------------------------------------------ 7-11. minor

def test_amazon_dp_url_without_scheme():
    from app.sources.amazon import amazon_dp_url
    assert amazon_dp_url("amazon.in/dp/B0GL8GXNTS") == "https://www.amazon.in/dp/B0GL8GXNTS"
    assert amazon_dp_url("www.amazon.in/Samsung-Galaxy/dp/B0GL8GXNTS/ref=x") == "https://www.amazon.in/dp/B0GL8GXNTS"
    assert amazon_dp_url("  www.amazon.in/gp/product/B0GL8GXNTS ") == "https://www.amazon.in/dp/B0GL8GXNTS"
    assert amazon_dp_url("www.amazon.com/dp/B0GL8GXNTS") is None


def test_detect_category_uses_leaf_segments():
    from app.extract import detect_category
    assert detect_category("Electronics > Home Theater, TV & Video > Remote Controls", "LG Smart TV Remote") \
        == Category.UNSUPPORTED
    assert detect_category("Fashion > Men > Shoes > Sandals & Floaters", "Sparx Men's Floaters") == Category.UNSUPPORTED
    assert detect_category("Shoes & Handbags > Men's Shoes > Flip-Flops & Slippers", "Crocs Slipper Shoes") \
        == Category.UNSUPPORTED
    assert detect_category("Clothing & Accessories > Men > Socks", "Puma Sneaker Socks") == Category.UNSUPPORTED
    assert detect_category("Clothing & Shoes > Polos", "Allen Solly Polo") == Category.APPAREL
    assert detect_category("Electronics > Home Theater, TV & Video > Televisions > Smart Televisions", "x") == Category.TV
    assert detect_category("Shoes & Handbags > Shoes > Men's Shoes > Sneakers", "x") == Category.SNEAKER
    assert detect_category("Shoes & Handbags > Shoes > Men's Shoes > Sports Shoes > Running Shoes", "x") \
        == Category.SNEAKER
    assert detect_category("Clothing & Accessories > Men > T-Shirts & Polos > T-Shirts", "x") == Category.APPAREL


def test_myntra_missing_inventory_is_unknown_stock():
    prods = [{"productId": 1, "productName": "Nike Men Air Max 270 Sneakers", "brand": "Nike",
              "primaryColour": "Black", "articleType": {"typeName": "Casual Shoes"}, "landingPageUrl": "a"},
             {"productId": 2, "productName": "Nike Men Air Max 270 Sneakers", "brand": "Nike",
              "primaryColour": "Black", "articleType": {"typeName": "Casual Shoes"}, "landingPageUrl": "b",
              "inventoryInfo": []},
             {"productId": 3, "productName": "Nike Men Air Max 270 Sneakers", "brand": "Nike",
              "primaryColour": "Black", "articleType": {"typeName": "Casual Shoes"}, "landingPageUrl": "c",
              "inventoryInfo": [{"available": False}]}]
    html = "<script>window.__myx = " + json.dumps({"searchData": {"results": {"products": prods}}}) + "</script>"
    assert [c.in_stock for c in from_myntra_search(html)] == [None, None, False]


async def test_missing_apify_key_is_a_clear_source_error(monkeypatch, tmp_path):
    from app.sources import apify
    from app.sources.amazon import SourceError, get_source
    monkeypatch.setattr(apify, "CACHE_DIR", tmp_path / "apify")
    monkeypatch.setattr(apify, "OFFLINE", False)
    monkeypatch.delenv("APIFY_KEY", raising=False)
    calls = []
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(500)))
    with pytest.raises(SourceError, match="APIFY_KEY is not set — see README"):
        await get_source(client, "https://www.amazon.in/dp/B0GL8GXNTS")
    assert not calls


def test_tv_colour_is_ignored_for_pooling():
    # spec §6.2: TV colour is ignored; a differently-coloured listing of the same model is no "fallback"
    from app.models import Candidate, Canonical, SourceProduct
    tv = Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55, colour="Black",
                   title="Sony Bravia 3 55 inch K-55S30 Black")
    src = SourceProduct("u", "a", tv.title, None, Category.TV, tv)
    titan = Candidate(FLIPKART, "https://fk/t", "Sony Bravia 3 139 cm (55 inch) K-55S30",
                      Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55,
                                colour="Titanium Black"), True)
    m = decide(src, [titan])
    assert m.decision.value == "match" and not m.colour_fallback
    assert to_result(FLIPKART, m, [FetchStatus.OK], "Black").colour_fallback_note is None
