"""User-verified T-shirt cases from the 2026-11-13 mock run (docs/golden/tshirts_mockrun_2026-11-13.md).
Case 1 Levi's B07XFMDXY4 ↔ Myntra 12027436; case 2 Jockey 9930 vest B00W066XB2 ↔ Flipkart TSHFFTREMEHZDKEU,
Myntra 11443950."""
import json
from pathlib import Path

from app.extract import from_amazon, from_flipkart_page, from_myntra_search
from app.matcher import veto
from app.models import Category
from app.normalize import base_colour, norm_brand

FX = Path(__file__).parent / "fixtures"


def amz(asin):
    return from_amazon(json.loads((FX / f"amz_{asin}.json").read_text())[0])


def myntra(name, pid):
    cs = from_myntra_search((FX / name).read_text(encoding="utf-8", errors="ignore"))
    return next(c for c in cs if pid in c.url)


def test_brand_punctuation():
    assert norm_brand("Levi's") == norm_brand("Levis") == norm_brand("LEVI'S")


def test_colour_ignores_brackets():
    assert base_colour("White(Light Grey Mel)") == "white"


def test_levis_myntra_truth_not_vetoed():
    sp = amz("B07XFMDXY4")
    t = myntra("my_levis_search.html", "12027436")
    assert veto(sp.canon, t, Category.APPAREL) is None


def test_jockey_style_code_from_part_number():
    assert amz("B00W066XB2").canon.style_code == "9930-0105-WHITE"


def test_jockey_flipkart_vest_reads_style_code():
    u = "https://www.flipkart.com/jockey-men-vest/p/itme8044db58189f?pid=TSHFFTREMEHZDKEU"
    c = from_flipkart_page((FX / "fk_jockey_vest.html").read_text(encoding="utf-8", errors="ignore"), u)[0]
    assert c.canon.style_code == "9930-0105-WHITE"
    sp = amz("B00W066XB2")
    assert veto(sp.canon, c, Category.APPAREL) is None


def test_jockey_myntra_truth_not_vetoed_shared_model_number():
    sp = amz("B00W066XB2")
    t = myntra("my_jockey_search.html", "11443950")
    assert veto(sp.canon, t, Category.APPAREL) is None


def test_amazon_mrp_falls_back_to_price_when_no_list_price():
    assert amz("B00W066XB2").canon.mrp == 399  # no strike-through price on Amazon: price is the MRP


def test_same_maker_despite_wording():
    from app.confirm import same_maker
    a = "page industries limited umiya business bay tower 1 7th floor cessna business park kadubeesanahalli varthur hobli bengaluru 560103"
    b = "page industries limited umiya business bay tower 1 7th floor cessna business park kadubeesanahalli bengaluru 560103"
    assert same_maker(a, b)
    lv_a = "modenik lifestyle private limited formerly dixcy textiles pvt ltd dixcy campus d no 10 5 n maniosai nagar poosaripalayam chengapalli tirupur 638812"
    lv_b = "dixcy textiles pvt ltd d no 10 5 n maniosai nagar poosaripalayam chengappalli 638812"
    assert same_maker(lv_a, lv_b)
    assert not same_maker(a.replace("560103", "560001"), b)  # different PIN
    assert not same_maker("aryan apparels private limited plot 266 manesar 122051", b)


def test_jockey_flipkart_same_style_matches_without_product_type():
    from app.matcher import decide
    from app.models import Decision
    u = "https://www.flipkart.com/jockey-men-vest/p/itme8044db58189f?pid=TSHFFTREMEHZDKEU"
    c = from_flipkart_page((FX / "fk_jockey_vest.html").read_text(encoding="utf-8", errors="ignore"), u)[0]
    m = decide(amz("B00W066XB2"), [c])
    assert m.decision == Decision.MATCH and "9930-0105-WHITE" in m.reason
