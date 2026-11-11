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


async def test_all_signals_agree_confirms():
    s, c = src(), myntra()
    async def same(a, b):
        return "SAME"
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [c]), vision=same)
    assert m.decision == Decision.MATCH and m.candidate.url == MY_URL
    assert "name, MRP, manufacturer and photo" in m.reason


async def test_photo_different_or_unsure_stays_possible():
    s = src()
    for verdict in ("DIFFERENT", "UNSURE"):
        async def v(a, b, verdict=verdict):
            return verdict
        async with client() as cl:
            m = await confirm.confirm(cl, s, decide(s, [myntra()]), vision=v)
        assert m.decision == Decision.AMBIGUOUS


async def test_mrp_mismatch_is_not_confirmed():
    s = src()
    async def same(a, b):
        return "SAME"
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [myntra(mrp=2299)]), vision=same)
    assert m.decision == Decision.AMBIGUOUS


async def test_two_colour_siblings_both_same_is_ambiguous():
    s = src()
    a, b = myntra(), myntra(url=MY_URL.replace("35720668", "35720666"))
    async def same(x, y):
        return "SAME"
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, [a, b]), vision=same)
    assert m.decision == Decision.AMBIGUOUS


def test_name_only_listings_go_to_confirmation_before_doubtful_ones():
    # live run 2026-11-12: "Train All Day Brand Logo T-shirt" (extra words) was reported instead of the exact name
    s, exact = src(), myntra()
    logo = myntra(title="Puma Train All Day Brand Logo T-shirt", url=MY_URL.replace("35720668", "39654569"))
    m = decide(s, [logo, exact])
    assert m.decision == Decision.AMBIGUOUS and m.reason.startswith("No style code")
    assert [c.url for c in m.survivors] == [MY_URL]
