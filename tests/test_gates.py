"""Hard gates from reports/Reliable apparel matching like Google.md (2026-11-13): a candidate is rejected only
when both sides are KNOWN and differ — category, neckline/collar, plus code rules by brand."""
from pathlib import Path

from app.extract import from_flipkart_page
from app.matcher import veto
from app.models import Candidate, Canonical, Category, Platform
from app.normalize import base_colour, neck_type, store_kind

FX = Path(__file__).parent / "fixtures"


def test_neck_type_from_text():
    assert neck_type("Tommy Hilfiger Men Brand Logo Polo Collar T-shirt") == "collar"
    assert neck_type("VAN HEUSEN Solid Men Polo Neck Blue T-Shirt") == "collar"
    assert neck_type("Puma Men Round Neck T-shirt") == "round"
    assert neck_type("Van Heusen Girls Crew Neck T-shirt") == "round"
    assert neck_type("Men V Neck Tee") == "v"
    assert neck_type("Symbol Polo T Shirt | Mandarin Collar") == "mandarin"
    assert neck_type("Puma Men Polyester Solid Regular Fit T-Shirt") is None
    assert neck_type("Collarless") == "round"  # Amazon "Collar Style: Collarless"


def test_store_kind():
    assert store_kind("watch") == "other" and store_kind("slipper_flip_flop") == "other"
    assert store_kind("Flip Flops") == "other" and store_kind("Shirts") == "other"
    assert store_kind("t_shirt") == "top" and store_kind("Tshirts") == "top" and store_kind("vest") == "top"
    assert store_kind(None) is None


def test_flipkart_reads_neck_and_kind():
    u = "https://www.flipkart.com/ausk-printed-men-round-neck-maroon-white-t-shirt/p/itma5227395b62a8?pid=TSHHZFA6CJKTGABG"
    c = from_flipkart_page((FX / "fk_ausk_maroon.html").read_text(encoding="utf-8", errors="ignore"), u)[0]
    assert c.canon.neck == "round" and c.canon.kind == "top"


def src(**kw):
    return Canonical(brand="tommy hilfiger", product_type="tee", base_colour="green", title="Tommy Hilfiger Men T-Shirt", **kw)


def cand(**kw):
    t = kw.pop("title", "Tommy Hilfiger Men T-shirt")
    return Candidate(Platform.FLIPKART, "u", t, Canonical(brand="tommy hilfiger", title=t, **kw), True)


def test_category_gate_rejects_watch_and_shirt():
    assert veto(src(), cand(kind="other", title="Tommy Hilfiger Analog Watch"), Category.APPAREL) == "category"


def test_neck_gate_only_when_both_known():
    s = src(neck="collar")
    assert veto(s, cand(neck="round", base_colour="green"), Category.APPAREL) == "neck"
    assert veto(s, cand(neck=None, base_colour="green"), Category.APPAREL) != "neck"


def test_seller_code_mismatch_does_not_veto_but_brand_code_does():
    bew = Canonical(brand="bewakoof", product_type="tee", base_colour="black", style_code="1053011", title="Bewakoof Batman tee")
    other = Candidate(Platform.FLIPKART, "u", "Bewakoof Batman tee",
                      Canonical(brand="bewakoof", product_type="tee", base_colour="black", style_code="BWK-77821",
                                title="Bewakoof Batman tee"), True)
    assert veto(bew, other, Category.APPAREL) != "style code"
    nike = Canonical(brand="nike", base_colour="white", style_code="DV2789-100", title="t")
    n2 = Candidate(Platform.FLIPKART, "u", "t", Canonical(brand="nike", base_colour="white", style_code="DV2789-101", title="t"), True)
    assert veto(nike, n2, Category.SNEAKER) == "style code"


def test_brand_colour_abbreviations():
    assert base_colour("LGTGRE") == "grey"
    assert base_colour("BLK") == "black"
