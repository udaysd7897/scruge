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
