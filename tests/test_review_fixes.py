"""Code review of poc/sneakers (2026-11-13): one Critical + five Important findings, each pinned here."""
import json
from dataclasses import replace
from pathlib import Path

from app.confirm import confirm
from app.extract import from_amazon, sneaker_code_like
from app.matcher import _all_duplicates, decide, same_style, veto
from app.models import Candidate, Canonical, Category, Decision, Platform
from app.normalize import audience, colour_set

FX = Path(__file__).parent / "fixtures"
S, A = Category.SNEAKER, Category.APPAREL


def cand(title, brand, colour="White", code=None, url="u", mrp=None, gender=None):
    return Candidate(Platform.FLIPKART, url, title, Canonical(brand=brand, colour=colour, style_code=code, mrp=mrp,
                                                             gender=gender, title=title), True)


def sparse(title, crumbs="Shoes & Handbags > Shoes > Men's Shoes > Casual Shoes > Sneakers"):
    return from_amazon({"title": title, "breadCrumbs": crumbs, "asin": "X",
                        "variantAttributes": [{"key": "Colour", "value": "White"}]})


# 1 (Critical) the title's first word is a guess: "Red Tape" must not become a hard "red" brand veto
def test_title_brand_guess_never_vetoes_multi_word_brand():
    sp = sparse("Red Tape Men's Casual Sneakers")
    assert veto(sp.canon, cand("Red Tape Men Sneakers", "red tape"), S) != "brand"
    assert veto(sp.canon, cand("Puma Men Sneakers", "puma"), S) == "brand"
    assert sparse("Men's Casual Sneakers").canon.brand is None  # a gender word is not a brand


# 2 Amazon's apparel "Model Name" is a search hint, never identity: it must not feed the apparel word veto
def test_apparel_model_name_stays_out_of_title_check():
    src = Canonical(brand="levis", product_type="tee", base_colour="white", model_name="housemark tee",
                    title="Levis Men Soft Pure Cotton Round Neck Tshirt")
    c = Candidate(Platform.FLIPKART, "u", "Levi's Batwing Logo Men Round Neck White T-Shirt",
                  Canonical(brand="levis", product_type="tee", base_colour="white",
                            title="Levi's Batwing Logo Men Round Neck White T-Shirt"), True)
    assert veto(src, c, A) != "distinctive words"


# 3 a number-only code match (SM-734 ~ SX-734, BBMH9103A ~ BBMH9103B) finds candidates, it doesn't prove them
def test_relaxed_code_match_is_not_proof():
    a = Canonical(brand="sparx", style_code="SM-734")
    assert not same_style(a, Canonical(brand="sparx", style_code="SX-734"))
    assert not same_style(Canonical(brand="bacca bucci", style_code="BBMH9103A-09"),
                          Canonical(brand="bacca bucci", style_code="BBMH9103B"))
    assert same_style(Canonical(brand="bacca bucci", style_code="BBMH9103A-09"),
                      Canonical(brand="bacca bucci", style_code="BBMH9103A"))
    # AUSK (user-confirmed) keeps working: AUSK-04065-L = AUSKB-04065
    assert same_style(Canonical(brand="ausk", style_code="AUSK-04065-L"), Canonical(brand="ausk", style_code="AUSKB-04065"))
    sp = from_amazon(json.loads((FX / "amz_sparx_B09PVFDLSK.json").read_text()))
    m = decide(sp, [cand("Sparx SM 734 Sneakers For Men", "sparx", code="SD0734G", gender="men")])
    assert m.decision == Decision.AMBIGUOUS  # goes to the photo check, not straight to "In stock"


# 4 short model numbers only for brands whose codes we don't trust
def test_short_codes_only_for_untrusted_brands():
    assert sneaker_code_like("NB 574", "new balance") is None
    assert sneaker_code_like("SM-734", "sparx") == "SM-734"
    src = Canonical(brand="new balance", family="574", style_code=sneaker_code_like("NB 574", "new balance"))
    assert veto(src, cand("New Balance 574 Sneakers", "new balance", code="ML574EVG"), S) != "style code"


# 5 "w/" is not women
def test_w_slash_is_not_women():
    assert audience("Sparx Sneakers w/ laces") is None
    assert audience("NIKE W KILLSHOT 2") == "women"


# 6 generic Flipkart titles must not collapse different shoes into one photo slot
async def test_generic_titles_keep_separate_photo_slots():
    sp = from_amazon(json.loads((FX / "amz_bacca_B0CVF22V83.json").read_text()))
    a = cand("Sneakers For Men", "bacca bucci", "Black, White", url="a", mrp=2999, gender="men")
    b = cand("Sneakers For Men", "bacca bucci", "Black, White", url="b", mrp=1999, gender="men")
    seen = []

    async def picker(src, cands):
        seen.extend(c.url for c in cands)
        return {}
    await confirm(None, sp, decide(sp, [a, b]), picker=picker)
    assert sorted(seen) == ["a", "b"]


# minors
def test_multicolour_is_unknown_and_colourless_siblings_are_not_duplicates():
    assert colour_set("Multicolor") == frozenset()
    a = cand("x", "ausk", None, code="AUSK04065", url="a")
    b = cand("x", "ausk", None, code="AUSK04065", url="b")
    assert not _all_duplicates([a, b])


def test_nike_code_veto_itself():
    src = Canonical(brand="nike", style_code="432997-107", colour="White", family="killshot 2 leather")
    assert veto(src, cand("NIKE KILLSHOT 2 LEATHER", "nike", "White", "432997-070"), S) == "style code"
