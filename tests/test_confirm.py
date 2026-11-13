"""Myntra shows no brand style code: a no-code apparel match is confident only when the official name,
MRP, manufacturer text and photo all agree (Puma 52885601 ↔ Myntra 35720668); otherwise Possible match."""
import json
from pathlib import Path

import httpx

from app import confirm
from app.extract import from_amazon, myntra_pdp_maker, norm_maker
from app.matcher import decide, veto
from app.models import Candidate, Canonical, Category, Decision, Platform

FX = Path(__file__).parent / "fixtures"
MY_URL = "https://www.myntra.com/tshirts/puma/puma-train-all-day-men-breathable-training-tee/35720668/buy"
PDP = (FX / "my_puma_tad_tee_pdp.html").read_text(encoding="utf-8", errors="ignore")


def src():
    sp = from_amazon(json.loads((FX / "amz_puma_tee.json").read_text())[0])
    sp.canon.official_name = "train all day mens breathable training tee"
    return sp


def myntra(title="Puma Train All Day Men Breathable Training Tee", mrp=1799, url=MY_URL, gender="men"):
    return Candidate(Platform.MYNTRA, url, title,
                     Canonical(brand="puma", product_type="tee", colour="Black", base_colour="black",
                               gender=gender, mrp=mrp, title=title), True, 719, image="https://img/x.jpg")


def test_amazon_reads_gender_mrp_maker():
    c = src().canon
    assert (c.gender, c.mrp) == ("men", 1799)
    assert c.maker == norm_maker("Aryan Apparels Private Limited Plot no 266 Sector 06 IMT Manesar 122051")


def test_myntra_pdp_maker_matches_amazon():
    assert myntra_pdp_maker(PDP) == src().canon.maker


def test_official_name_passes_name_check_but_needs_confirmation():
    s, c = src(), myntra()
    assert veto(s.canon, c, Category.APPAREL) is None
    m = decide(s, [c])
    assert m.decision == Decision.AMBIGUOUS and m.candidate is c


def test_gender_veto():
    assert veto(src().canon, myntra(gender="women"), Category.APPAREL) == "gender"


def client():
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=PDP)))


def picks(url=None, none=False):
    """Fake one-call photo check: a clean table for the candidate with `url`, a named difference for the
    others ("none" when none=True, an unclear table when url is None and not none)."""
    async def picker(src, cands):
        rows, ans = {}, ("none" if none else "unclear")
        for i, c in enumerate(cands, 1):
            hit = url is not None and c.url == url
            rows[str(i)] = {a: "same" for a in ("neck", "sleeve", "colour", "logo", "stripes", "print")}
            if not hit and (none or url is not None):
                rows[str(i)]["print"] = "different"
            if url is None and not none:
                rows[str(i)]["print"] = "unclear"
            if hit:
                ans = i
        return {"table": rows, "match": ans}
    return picker


async def test_all_signals_agree_confirms():
    s, c = src(), myntra()
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [c]), picker=picks(MY_URL))
    assert m.decision == Decision.MATCH and m.candidate.url == MY_URL
    assert "name, MRP, manufacturer and photo" in m.reason


async def test_photo_unclear_stays_possible_and_clean_none_is_not_listed():
    s = src()
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [myntra()]), picker=picks())
        assert m.decision == Decision.AMBIGUOUS
        m = await confirm.confirm(cl, s, decide(s, [myntra()]), picker=picks(none=True))
        assert m.decision == Decision.NONE and m.none_had == "the same design in its photo"


async def test_mrp_and_maker_mismatch_is_not_confirmed():
    # option 2 (2026-11-13): photo match + (MRP equal or same manufacturer). Neither → Possible, linked to it
    s = src()
    s.canon.maker = "some other maker plot 1 delhi 110001"
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [myntra(mrp=2299)]), picker=picks(MY_URL))
    assert m.decision == Decision.AMBIGUOUS and m.candidate.url == MY_URL


async def test_mrp_mismatch_with_same_maker_and_photo_is_confirmed():
    s = src()
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [myntra(mrp=2299)]), picker=picks(MY_URL))
    assert m.decision == Decision.MATCH


async def test_two_colour_siblings_both_clean_is_ambiguous():
    s = src()
    a, b = myntra(), myntra(url=MY_URL.replace("35720668", "35720666"))
    async def both_clean(src_, cands):
        return {"table": {str(i): {x: "same" for x in ("neck", "sleeve", "colour", "logo", "stripes", "print")}
                          for i in range(1, len(cands) + 1)}, "match": 1}
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [a, b]), picker=both_clean)
    assert m.decision == Decision.AMBIGUOUS


def test_name_only_listings_go_to_confirmation_before_doubtful_ones():
    # live run 2026-11-12: "Train All Day Brand Logo T-shirt" (extra words) was reported instead of the exact name
    s, exact = src(), myntra()
    logo = myntra(title="Puma Train All Day Brand Logo T-shirt", url=MY_URL.replace("35720668", "39654569"))
    m = decide(s, [logo, exact])
    assert m.decision == Decision.AMBIGUOUS and m.reason.startswith("No style code")
    # every surviving apparel listing goes to confirmation; the exact name ranks first
    assert m.candidate.url == MY_URL and {c.url for c in m.survivors} == {MY_URL, logo.url}
