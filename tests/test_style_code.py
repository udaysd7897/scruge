"""Same Puma tee, three very different titles (user report 2026-11-12):

Amazon   B0FGJ6FVZ6  "Puma Men Polyester Solid Regular Fit T-Shirt"   Style Number 52885601, Model Name "TAD ESSENTIAL"
Flipkart TSHHEYWZMK66DDSE  JSON-LD "PUMA Printed Men Round Neck Black T-Shirt",
         shown title "M Train All Day ESSENTIAL Men Printed Round Neck Polyester Black T-Shirt", Style Code 52885601
Myntra   35720668  "Puma Train All Day Men Breathable Training Tee" (no style code anywhere on the page)

Root cause (systematic debugging, 2026-11-12): apparel identity was built only from title words, so the
"distinctive words" veto rejected the right listing on both stores; the style codes were never read.
"""
import json
from pathlib import Path

from app.extract import from_amazon, from_flipkart_page, style_code_like
from app.matcher import decide, to_result, veto
from app.models import Candidate, Canonical, Category, Decision, FetchStatus, Outcome, Platform

FX = Path(__file__).parent / "fixtures"
FK_URL = "https://www.flipkart.com/puma-printed-men-round-neck-black-t-shirt/p/itm9888009d23d72?pid=TSHHEYWZMK66DDSE"


def amazon():
    return from_amazon(json.loads((FX / "amz_puma_tee.json").read_text())[0])


def flipkart():
    return from_flipkart_page((FX / "fk_puma_tad_tee.html").read_text(encoding="utf-8", errors="ignore"), FK_URL)[0]


def test_style_code_like():
    assert style_code_like("52885601") == "52885601"
    assert style_code_like("528856_01") == "528856_01"
    assert style_code_like("DV2789-100") == "DV2789-100"
    assert style_code_like("IF4405") == "IF4405"
    assert style_code_like("TAD ESSENTIAL | GYM_2891") is None
    assert style_code_like("Classic") is None
    assert style_code_like("1.0 Count") is None
    assert style_code_like("LINING-PLUS-HS-PKT-NVY- 5XL") is None  # seller SKU with a size in it
    assert style_code_like(None) is None


def test_amazon_apparel_reads_style_number_and_model_name():
    sp = amazon()
    assert sp.category == Category.APPAREL
    assert sp.canon.style_code == "52885601"
    assert sp.canon.model_name == "tad essential"
    assert (sp.canon.brand, sp.canon.product_type, sp.canon.base_colour) == ("puma", "tee", "black")
    assert sp.missing_required == []


def test_flipkart_apparel_reads_style_code_and_shown_title():
    c = flipkart()
    assert c.canon.style_code == "52885601"
    assert c.title == "PUMA M Train All Day ESSENTIAL Men Printed Round Neck Polyester Black T-Shirt"
    assert c.canon.product_type == "tee" and c.canon.base_colour == "black"


def test_same_style_code_is_a_confident_match_despite_different_titles():
    sp, c = amazon(), flipkart()
    assert veto(sp.canon, c, Category.APPAREL) is None
    m = decide(sp, [c])
    assert m.decision == Decision.MATCH
    r = to_result(Platform.FLIPKART, m, [FetchStatus.OK], sp.canon.colour)
    assert r.outcome in (Outcome.IN_STOCK, Outcome.OUT_OF_STOCK)
    assert "pid=TSHHEYWZMK66DDSE" in r.url
    assert "style 52885601" in r.reason


def test_different_style_code_is_vetoed_for_apparel():
    sp, c = amazon(), flipkart()
    other = Candidate(Platform.FLIPKART, "u", c.title, Canonical(**{**vars(c.canon), "style_code": "52885699"}), True)
    assert veto(sp.canon, other, Category.APPAREL) == "style code"


def test_style_code_match_beats_lookalike_without_code():
    sp, c = amazon(), flipkart()
    look = Candidate(Platform.FLIPKART, "look", "PUMA Printed Men Round Neck Black T-Shirt",
                     Canonical(brand="puma", product_type="tee", base_colour="black", colour="Black",
                               title="PUMA Printed Men Round Neck Black T-Shirt"), True)
    m = decide(sp, [look, c])
    assert m.decision == Decision.MATCH and m.candidate is c
