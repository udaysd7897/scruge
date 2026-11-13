"""Sneaker POC (2026-11-13, reports/Sneaker cross store matching.md): the three user links failed in parsing,
not matching. Bacca Bucci B0CVF22V83, Nike Killshot B00770CB12 (sparse record), Sparx B09PVFDLSK."""
import json
from pathlib import Path

from app.extract import from_amazon, sneaker_code_like
from app.matcher import _all_duplicates, same_style, veto
from app.models import Candidate, Canonical, Category, Platform
from app.normalize import agreed_audience, audience, colour_set
from app.queries import ladder

FX = Path(__file__).parent / "fixtures"
S = Category.SNEAKER


def amz(name):
    return from_amazon(json.loads((FX / f"{name}.json").read_text()))


def fk(title, colour, code=None, brand="sparx", gender="men", url="u"):
    return Candidate(Platform.FLIPKART, url, title, Canonical(brand=brand, colour=colour, style_code=code,
                                                               gender=gender, title=title), True)


def test_bacca_reads_model_name_gender_code():
    c = amz("amz_bacca_B0CVF22V83").canon
    assert (c.brand, c.family, c.gender, c.style_code) == ("bacca bucci", "stride eclipse", "men", "BBMH9103A-09")
    assert ladder(amz("amz_bacca_B0CVF22V83"), Platform.FLIPKART)[0] == "bacca bucci stride eclipse white"


def test_sparse_killshot_gets_brand_and_queries():
    sp = amz("amz_killshot_B00770CB12")
    assert (sp.canon.brand, sp.canon.family) == ("nike", "killshot 2 leather")
    assert sp.canon.gender is None  # title "Boys" vs breadcrumb "Men's Shoes": unknown, never a veto
    assert ladder(sp, Platform.FLIPKART)[0] == "nike killshot 2 leather white"


def test_sparx_short_model_number_is_the_code():
    sp = amz("amz_sparx_B09PVFDLSK")
    assert sp.canon.style_code == "SM-734" and sp.missing_required == []
    assert ladder(sp, Platform.FLIPKART)[0] == "sparx sm-734"
    assert sneaker_code_like("SM 734") == "SM-734" and sneaker_code_like("Stride") is None


def test_colour_sets():
    assert colour_set("Black and White") == colour_set("White, Black") == {"black", "white"}
    assert colour_set("Sail/Gum Yellow/Midnight Navy") == {"white", "navy"}  # gum = sole


def test_audience():
    assert [audience(t) for t in ("mens", "Sneakers For Men", "NIKE W KILLSHOT 2", "Nike Boys Killshot")] == \
        ["men", "men", "women", "kids"]
    assert agreed_audience("Nike Boys Killshot", "Shoes > Men's Shoes") is None


def test_bacca_colourway_gate():
    src = amz("amz_bacca_B0CVF22V83").canon
    t = "bacca bucci Stride Eclipse: Low-Top For Men"
    assert veto(src, fk(t, "Black, White", brand="bacca bucci"), S) is None
    assert veto(src, fk(t, "Grey, White", brand="bacca bucci"), S) == "colour"
    assert veto(src, fk(t, "Black, Blue", brand="bacca bucci"), S) == "colour"


def test_sparx_digit_group_codes():
    src = amz("amz_sparx_B09PVFDLSK").canon
    for code in ("SD0734G", "A1SD0734G-WHGY"):
        assert same_style(src, fk("Sparx SM 734", "White", code).canon)
    assert not same_style(src, fk("Sparx SM 482", "White", "SD0482G").canon)
    assert veto(src, fk("Sparx SM 734 Sneakers For Men", "Black", "SD0734G"), S) == "colour"
    assert veto(src, fk("Sparx SM 734 Sneakers For Women", "White", "SD0734G", gender="women"), S) == "gender"


def test_nike_colourway_code_still_vetoes():
    src = Canonical(brand="nike", style_code="432997-107", colour="White", family="killshot 2 leather")
    assert veto(src, fk("NIKE KILLSHOT 2 LEATHER", "Black", "432997-070", brand="nike"), S) is not None


def test_same_style_same_colour_listed_twice_is_one_product():
    a = fk("AUSK tee", "Maroon", "AUSKB-04065", brand="ausk", url="a")
    b = fk("AUSK tee", "Maroon", "AUSK04065", brand="ausk", url="b")
    assert _all_duplicates([a, b])


def test_unequal_untrusted_codes_fall_back_to_title_words():
    # live POC run: Bacca "Matrix" (BBMH9133) passed every check for Stride Eclipse (BBMH9103A-09)
    src = amz("amz_bacca_B0CVF22V83").canon
    matrix = fk("bacca bucci MATRIX Low-Top Court Sneakers Casuals For Men", "Black, White", "BBMH9133",
                brand="bacca bucci")
    assert veto(src, matrix, S) == "distinctive words"
    stride = fk("bacca bucci Stride Eclipse: Low-Top For Men", "Black, White", None, brand="bacca bucci")
    assert veto(src, stride, S) is None


def test_flipkart_mrp_from_price_block():
    # Flipkart's MRP lets the photo check confirm a no-code listing (Bacca Stride Eclipse 2999 = Amazon 2999)
    from app.extract import _FK_MRP
    html = '..."ppd":{"fsp":1599,"finalPrice":1599,"mrp":2999,"nepPrice":1359,"specialPrice":true},...'
    assert _FK_MRP.search(html).group(1) == "2999"


def test_flipkart_shoe_page_reads_as_sneaker_with_mrp_maker_gender():
    # JSON-LD category "shoe" (title has no "shoe"/"sneaker"), label "Ideal for", "Name and address of the
    # Manufacturer": price + maker confirm the Stride Eclipse listing against Amazon
    from app.confirm import same_maker
    from app.extract import from_flipkart_page
    html = (FX / "fk_bacca_stride_eclipse.html").read_text(encoding="utf-8", errors="ignore")
    c = from_flipkart_page(html, "https://www.flipkart.com/x/p/itm9a823e41ec865?pid=SHOGZJZURF59V3FH")[0]
    k = c.canon
    assert (k.gender, k.mrp, k.family) == ("men", 2999, "stride eclipse low top") and c.image
    src = amz("amz_bacca_B0CVF22V83").canon
    assert same_maker(src.maker, k.maker) and src.mrp == k.mrp
    assert veto(src, c, S) is None and same_style(src, k)
