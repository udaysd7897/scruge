import json
from pathlib import Path

from app.extract import from_amazon, from_croma
from app.matcher import Match, decide, resolve_tie, score, to_result
from app.models import (Candidate, Canonical, Category, Decision, FetchStatus, Outcome, Platform,
                        SourceProduct)
from app.normalize import base_colour

MATCH, AMBIGUOUS, NONE = Decision.MATCH, Decision.AMBIGUOUS, Decision.NONE
OK, EMPTY, BLOCKED, ERROR = FetchStatus.OK, FetchStatus.EMPTY, FetchStatus.BLOCKED, FetchStatus.ERROR
FLIPKART, CROMA = Platform.FLIPKART, Platform.CROMA
FIX = Path(__file__).parent / "fixtures"


def croma_candidates():
    return [from_croma(i) for i in json.loads((FIX / "croma_apify.json").read_text())]


def phone_src(colour="Black", ram=12, storage=512, family="galaxy s26 ultra", model_code=None):
    canon = Canonical(brand="samsung", family=family, model_code=model_code, ram_gb=ram,
                      storage_gb=storage, colour=colour, base_colour=base_colour(colour),
                      title=f"Samsung Galaxy S26 Ultra 5G ({colour}, {ram}GB RAM, {storage}GB Storage)")
    missing = [f for f, v in (("ram_gb", ram), ("storage_gb", storage), ("colour", colour)) if v is None]
    return SourceProduct(url="https://www.amazon.in/dp/B0X", asin="B0X", title=canon.title, image=None,
                         category=Category.PHONE, canon=canon, missing_required=missing)


_n = iter(range(10_000))


def c(colour="Black", in_stock=True, ram=12, storage=512, family="galaxy s26 ultra", model_code=None,
      platform=FLIPKART, ean=None, url=None, price=None):
    title = f"SAMSUNG Galaxy S26 Ultra 5G ({colour}, {storage} GB) ({ram} GB RAM)"
    canon = Canonical(brand="samsung", family=family, model_code=model_code, ean=ean, ram_gb=ram, storage_gb=storage,
                      colour=colour, base_colour=base_colour(colour), title=title)
    return Candidate(platform, url or f"https://www.flipkart.com/p/itm{next(_n)}", title, canon, in_stock,
                     price=price)


def polo_src():
    t = "Puma Men Essentials Logo Slim Fit Polo Black"
    canon = Canonical(brand="puma", product_type="polo", base_colour="black", colour="Black", title=t)
    return SourceProduct(url="https://www.amazon.in/dp/B0P", asin="B0P", title=t, image=None,
                         category=Category.APPAREL, canon=canon)


def polo_c(suffix):
    t = "PUMA Essentials Logo Slim Fit Polo T-Shirt"
    canon = Canonical(brand="puma", product_type="polo", base_colour="black", colour="Black", title=t)
    return Candidate(Platform.MYNTRA, f"https://www.myntra.com/{suffix}", t, canon, True)


def test_brief_binding_assertions():
    src = phone_src(colour="Black", ram=12, storage=512)
    m = decide(src, croma_candidates())
    assert m.decision == MATCH and m.candidate.url.endswith("/p/327249") and not m.colour_fallback
    # colour preference: same-colour OOS beats other-colour in-stock
    m = decide(src, [c(colour="Black", in_stock=False), c(colour="Sky Blue", in_stock=True)])
    assert m.decision == MATCH and m.candidate.canon.colour == "Black"
    r = to_result(FLIPKART, m, [OK], "Black"); assert r.outcome == Outcome.OUT_OF_STOCK
    # colour fallback when source colour absent
    m = decide(phone_src(colour="Titanium Black"), [c(colour="Sky Blue", in_stock=True)])
    assert m.colour_fallback; r = to_result(FLIPKART, m, [OK], "Titanium Black")
    assert r.outcome == Outcome.IN_STOCK and r.colour_fallback_note == "Not available in Titanium Black; showing Sky Blue"
    # adjacent model only (Croma 'S24' search returned S26 Ultras)
    m = decide(phone_src(family="galaxy s24", ram=8, storage=256), croma_candidates())
    assert m.decision == NONE
    assert to_result(CROMA, m, [OK, OK, EMPTY], "Black").outcome == Outcome.NOT_LISTED
    assert to_result(CROMA, m, [OK, BLOCKED], "Black").outcome == Outcome.COULDNT_CHECK
    # source missing required → never MATCH
    m = decide(phone_src(storage=None), croma_candidates()); assert m.decision == AMBIGUOUS
    assert to_result(CROMA, m, [OK], "Black").outcome == Outcome.POSSIBLE
    # tie without tiebreak → AMBIGUOUS (two apparel listings equally good)
    assert decide(polo_src(), [polo_c("a"), polo_c("b")]).decision == AMBIGUOUS


def test_score_weights():
    src = phone_src(model_code="SM-S948B")
    full = c(model_code="SM-S948BZKCINS")
    s = score(src.canon, full, Category.PHONE)
    assert 0.80 < s <= 1.0  # 0.40 + 0.25 + 0.15 + title share
    other = c(colour="Sky Blue")
    assert score(src.canon, full, Category.PHONE) - score(src.canon, other, Category.PHONE) > 0.6
    ean_src = phone_src(); ean_src.canon.ean = "8806097852605"
    cand = c(); cand.canon.ean = "8806097852605"
    assert score(ean_src.canon, cand, Category.PHONE) >= 0.40 + 0.25 + 0.15


def test_match_reason_and_url():
    src = phone_src(model_code="SM-S948B")
    m = decide(src, [c(colour="Black", in_stock=True, model_code="SM-S948B")])
    r = to_result(FLIPKART, m, [OK], "Black")
    assert r.outcome == Outcome.IN_STOCK and r.url == m.candidate.url
    assert r.reason == "Matched on model SM-S948B, 12GB/512GB, Black"
    assert r.colour_fallback_note is None


def test_match_unknown_stock_is_possible():
    m = decide(phone_src(), [c(in_stock=None)])
    assert m.decision == MATCH
    r = to_result(FLIPKART, m, [OK], "Black")
    assert r.outcome == Outcome.POSSIBLE and r.reason == "Matched, but stock status couldn't be read"
    assert r.url == m.candidate.url


def test_not_listed_reasons():
    cands = [c(storage=256), c(storage=256, colour="White"), c(ram=8)]
    m = decide(phone_src(), cands)
    assert m.decision == NONE
    r = to_result(FLIPKART, m, [OK], "Black")
    assert r.outcome == Outcome.NOT_LISTED and r.url is None
    assert r.reason == "Not listed: 3 candidates checked, none had 512GB"
    r = to_result(CROMA, decide(phone_src(), []), [EMPTY], "Black")
    assert r.outcome == Outcome.NOT_LISTED and r.reason == "Not listed: no results on Croma"
    r = to_result(CROMA, decide(phone_src(), []), [ERROR], "Black")
    assert r.outcome == Outcome.COULDNT_CHECK and r.url is None


def test_fallback_prefers_in_stock_then_base_colour():
    src = phone_src(colour="Titanium Black")
    m = decide(src, [c(colour="Sky Blue", in_stock=False), c(colour="White", in_stock=True),
                     c(colour="Black", in_stock=True)])
    assert m.decision == MATCH and m.colour_fallback and m.candidate.canon.colour == "Black"
    m = decide(src, [c(colour="Black", in_stock=False), c(colour="White", in_stock=True)])
    assert m.candidate.canon.colour == "White"


def test_candidate_missing_required_is_ambiguous():
    cand = c(); cand.canon.colour = None; cand.canon.base_colour = None
    m = decide(phone_src(colour=None), [cand])  # source colour unknown too
    assert m.decision == AMBIGUOUS
    m = decide(phone_src(), [c(ram=None)])  # same colour, but candidate lacks RAM
    assert m.decision == AMBIGUOUS
    r = to_result(FLIPKART, m, [OK], "Black")
    assert r.outcome == Outcome.POSSIBLE and r.url == m.candidate.url


def test_source_missing_reason_and_none():
    m = decide(phone_src(storage=None), croma_candidates())
    assert "storage" in m.reason and m.candidate is not None
    m = decide(phone_src(storage=None, family="galaxy s24"), croma_candidates())
    assert m.decision == NONE


def test_resolve_tie():
    a, b = polo_c("a"), polo_c("b")
    m = decide(polo_src(), [a, b])
    assert m.reason == "tie" and set(x.url for x in m.survivors) == {a.url, b.url}
    assert resolve_tie(m, b).decision == MATCH and resolve_tie(m, b).candidate is b
    assert resolve_tie(m, None).decision == AMBIGUOUS
    assert resolve_tie(m, polo_c("z")).decision == AMBIGUOUS
    # source missing required → never resolved
    ms = decide(phone_src(storage=None), croma_candidates())
    assert resolve_tie(ms, ms.survivors[0]).decision == AMBIGUOUS
    # a tie among phones lacking a distinguishing feature
    m2 = decide(phone_src(), [c(), c()])
    assert m2.decision == AMBIGUOUS and m2.reason == "tie"
    r = to_result(FLIPKART, m2, [OK], "Black")
    assert r.outcome == Outcome.POSSIBLE and r.url == m2.candidate.url


def test_tv_reason_and_margin():
    tv = Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55, title="Sony Bravia 3 55 inch K-55S30")
    src = SourceProduct("u", "a", tv.title, None, Category.TV, tv)
    good = Candidate(FLIPKART, "https://fk/1", "Sony Bravia 3 139 cm (55 inch) K-55S30",
                     Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55, title="x"), True)
    weak = Candidate(FLIPKART, "https://fk/2", "Sony Bravia 3 139 cm (55 inch)",
                     Canonical(brand="sony", family="bravia 3", screen_in=55, title="x"), True)
    m = decide(src, [weak, good])
    assert m.decision == MATCH and m.candidate is good
    assert to_result(FLIPKART, m, [OK], None).reason == 'Matched on model K-55S30, 55"'
    assert isinstance(m, Match)


def test_fix1_unknown_colour_with_other_colour_is_ambiguous():
    m = decide(phone_src(), [c(colour=None, in_stock=False), c(colour="Sky Blue", in_stock=True)])
    assert m.decision == AMBIGUOUS and m.reason == "Colour unclear on this platform"
    assert not m.colour_fallback
    r = to_result(FLIPKART, m, [OK], "Black")
    assert r.outcome == Outcome.POSSIBLE and r.colour_fallback_note is None


def test_fix1_tv_unknown_colour_only_uses_gap_rule():
    tv = Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55, colour="Black",
                   title="Sony Bravia 3 55 inch K-55S30 Black")
    src = SourceProduct("u", "a", tv.title, None, Category.TV, tv)
    good = Candidate(FLIPKART, "https://fk/g", "Sony Bravia 3 139 cm (55 inch) K-55S30",
                     Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55), False)
    weak = Candidate(FLIPKART, "https://fk/w", "Sony Bravia 3 139 cm (55 inch)",
                     Canonical(brand="sony", family="bravia 3", screen_in=55), True)
    m = decide(src, [weak, good])
    assert m.decision == MATCH and m.candidate is good and not m.colour_fallback
    r = to_result(FLIPKART, m, [OK], "Black")
    assert r.outcome == Outcome.OUT_OF_STOCK and r.colour_fallback_note is None


def test_fix1_fallback_tie_group_prefers_in_stock():
    src = phone_src(colour="Titanium Black")
    m = decide(src, [c(colour="White", in_stock=False), c(colour="Sky Blue", in_stock=True)])
    assert m.decision == MATCH and m.colour_fallback and m.candidate.canon.colour == "Sky Blue"
    r = to_result(FLIPKART, m, [OK], "Titanium Black")
    assert r.outcome == Outcome.IN_STOCK
    assert r.colour_fallback_note == "Not available in Titanium Black; showing Sky Blue"


def test_fix1_fallback_never_picks_outside_tie_group():
    src = phone_src(colour="Titanium Black", model_code="SM-S948B")
    strong = c(colour="White", in_stock=False, model_code="SM-S948B")
    weak = c(colour="Sky Blue", in_stock=True)
    m = decide(src, [weak, strong])
    assert m.candidate is strong and m.colour_fallback
    assert to_result(FLIPKART, m, [OK], "Titanium Black").outcome == Outcome.OUT_OF_STOCK


def test_fix1_matched_on_without_model_code():
    m = decide(phone_src(), [c(colour="Black", model_code="SM-S948BZKCINS")])
    r = to_result(FLIPKART, m, [OK], "Black")
    assert "model" not in r.reason
    assert r.reason == "Matched on Galaxy S26 Ultra, 12GB/512GB, Black"
    src = phone_src(); src.canon.ean = "8806097852605"
    cand = c(); cand.canon.ean = "8806097852605"
    assert decide(src, [cand]).reason == "Matched on barcode, 12GB/512GB, Black"


def test_fix1_user_facing_labels_and_empty_statuses():
    m = decide(phone_src(storage=None), croma_candidates())
    assert to_result(CROMA, m, [OK], "Black").reason == "Couldn't read storage on Amazon"
    m = decide(phone_src(), [c(ram=None)])
    assert to_result(FLIPKART, m, [OK], "Black").reason == "Listing doesn't show RAM"
    assert to_result(CROMA, decide(phone_src(), []), [], "Black").outcome == Outcome.COULDNT_CHECK


def test_fix2_colour_unclear_links_colourless_listing():
    unknown = c(colour=None, in_stock=False)
    m = decide(phone_src(), [unknown, c(colour="Sky Blue", in_stock=True)])
    assert m.decision == AMBIGUOUS
    assert to_result(FLIPKART, m, [OK], "Black").url == unknown.url


def test_fix2_source_missing_beats_colour_unclear():
    m = decide(phone_src(storage=None), [c(colour=None, storage=None), c(colour="Sky Blue", storage=None)])
    assert m.decision == AMBIGUOUS
    assert to_result(FLIPKART, m, [OK], "Black").reason == "Couldn't read storage on Amazon"


def test_fix2_empty_statuses_reason():
    r = to_result(CROMA, decide(phone_src(), []), [], "Black")
    assert r.reason == "Couldn't check Croma: no search was completed"


def test_duplicate_listings_are_one_product():
    from dataclasses import replace
    src = phone_src(colour="Sky Blue", ram=12, storage=512)
    kw = dict(colour="Sky Blue", in_stock=True, model_code="SM-S948BLBCINS", ean="8806097852056", price=159999)
    a, b = c(url=".../p/327248", **kw), c(url=".../p/321503", **kw)
    assert decide(src, [a, b]).decision == MATCH
    b2 = replace(b, in_stock=False)
    assert decide(src, [b2, a]).candidate is a
    assert decide(src, [b2, a]).decision == MATCH
    # cheaper duplicate preferred among in-stock
    cheap = replace(b, price=149999)
    assert decide(src, [a, cheap]).candidate is cheap
    # same base code, different full codes, no ean: still a tie
    x = c(colour="Sky Blue", model_code="SM-S948BLBCINS")
    y = c(colour="Sky Blue", model_code="SM-S948BZBCINS")
    assert decide(src, [x, y]).decision == AMBIGUOUS
    # no identifiers: still a tie
    assert decide(src, [c(colour="Sky Blue"), c(colour="Sky Blue", url="other")]).decision == AMBIGUOUS
    # source missing required stays ambiguous
    assert decide(phone_src(colour="Sky Blue", storage=None), [a, b]).decision == AMBIGUOUS


def test_oneplus15_croma_picks_exact_variant_out_of_stock():
    # Golden case: Croma lists OnePlus 15 in 4 variants sharing model code CPH2745; only
    # 12/256 Infinite Black (p/323981, out of stock) is the Amazon product.
    fx = Path(__file__).parent / "fixtures"
    item = next(i for i in json.loads((fx / "amz_golden.json").read_text()) if i["asin"] == "B0FTR5NGHJ")
    src = from_amazon(item)
    cands = [from_croma(i) for i in json.loads((fx / "croma_golden.json").read_text())]
    m = decide(src, cands)
    assert m.decision == Decision.MATCH and m.candidate.url.endswith("/p/323981")
    assert m.candidate.in_stock is False
