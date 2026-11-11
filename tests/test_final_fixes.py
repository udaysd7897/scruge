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
