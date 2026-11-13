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


# --- cases 3 & 4 (Leriya → Myntra 38443941; AUSK → Flipkart TSHHZFA6CJKTGABG) -----------------------

def test_style_core_matches_across_store_formats():
    from app.matcher import same_style
    c = lambda code: __import__("app.models", fromlist=["Canonical"]).Canonical(style_code=code)
    assert same_style(c("AUSK-04065-L"), c("ASSKC-04065"))        # seller SKU with size vs store code
    assert same_style(c("60001"), c("IHQTS1LDS60001"))            # Van Heusen
    assert same_style(c("528856_01"), c("52885601"))               # punctuation
    assert same_style(c("9930-0105-WHITE"), c("9930-0105-WHITE"))
    assert not same_style(c("DV2789-100"), c("DV2789-101"))       # Nike: same model, other colourway
    assert not same_style(c("04065"), c("04066"))


def test_amazon_uses_high_resolution_image():
    sp = amz("B07XFMDXY4")
    assert "_SX342_" not in (sp.image or "") and "_SY445_" not in (sp.image or "")


async def test_flipkart_code_search_finds_cards_by_code_in_image_name():
    import httpx
    from app.sources.flipkart import flipkart_code_candidates
    search = (FX / "fk_search_ausk_maroon_p2.html").read_text(encoding="utf-8", errors="ignore")
    page = (FX / "fk_ausk_maroon.html").read_text(encoding="utf-8", errors="ignore")
    seen = []
    def h(req):
        seen.append(str(req.url))
        return httpx.Response(200, text=search if "/search" in str(req.url) else page)
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as cl:
        st, cands = await flipkart_code_candidates(cl, "ausk", "maroon", "AUSK-04065-L")
    urls = {c.url for c in cands}
    assert any("TSHHK46GDCBNUWC5" in u for u in urls)
    assert "facets.brand" in seen[0]
    assert sum("/search" not in u for u in seen) <= 6  # only cards whose image carries the code are opened


async def test_confirm_accepts_photo_plus_mrp_or_maker():
    import httpx
    from app import confirm
    from app.matcher import decide
    from app.models import Candidate, Canonical, Decision, Platform
    sp = amz("B07XFMDXY4")
    pdp = (FX / "my_levis_pdp.html").read_text(encoding="utf-8", errors="ignore")
    def cand(mrp):
        return Candidate(Platform.MYNTRA, "https://www.myntra.com/x/12027436/buy", "Levis Men Soft Pure Cotton Tshirt",
                         Canonical(brand="levis", product_type="tee", colour="White", base_colour="white", gender="men",
                                   mrp=mrp, title="Levis Men Soft Pure Cotton Tshirt"), True, 500, image="https://i/x.jpg")
    from test_confirm import picks
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=pdp))) as cl:
        # MRP differs between stores (Leriya ₹1,999 vs ₹999) but manufacturer + photo agree → confirmed
        m = await confirm.confirm(cl, sp, decide(sp, [cand(999)]), picker=picks("https://www.myntra.com/x/12027436/buy"))
        assert m.decision == Decision.MATCH
        # photo check unclear → never confirmed, whatever else agrees
        m = await confirm.confirm(cl, sp, decide(sp, [cand(649)]), picker=picks())
        assert m.decision == Decision.AMBIGUOUS


def test_model_name_made_searchable():
    from app.extract import _amazon_model_name
    assert _amazon_model_name({"Model Name": "Classic_3S_Tee_SMU"}) == "classic 3s tee"
    assert _amazon_model_name({"Model Name": "JE9356"}) is None           # just the code
    assert _amazon_model_name({"Model Name": "9930_Pack of 1"}) is None   # code + pack text
    assert _amazon_model_name({"Model Name": "TAD ESSENTIAL | GYM_2891"}) == "tad essential"


def test_seller_sku_model_name_is_not_a_query():
    from app.extract import _amazon_model_name
    assert _amazon_model_name({"Model Name": "LF-M.T-Shirt-DP-MT1213"}) is None


def test_apparel_ladder_always_has_brand_noun_colour():
    from app.models import Platform
    from app.queries import ladder
    sp = amz("B0HCW2KFCR")
    assert "leriya fashion t-shirt brown" in ladder(sp, Platform.MYNTRA)
