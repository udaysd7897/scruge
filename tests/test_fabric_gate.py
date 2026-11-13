"""Fabric gate (user report 2026-11-13, Jockey B0H3QHNZGQ): Amazon "Jockey Polyester AM74 ... Microfiber ...
Round Neck ... Activewear T-Shirt" vs Myntra "Jockey Men Black Solid Round Neck Pure Cotton T-shirt" passed
every text gate; only a photo check (flaky: "neck differs") told them apart. Titles name the fabric."""
from app.matcher import veto
from app.models import Candidate, Canonical, Category, Platform
from app.normalize import fabric_set

A = Category.APPAREL
AMZ = "Jockey Polyester AM74 Men Microfiber Fabric Round Neck Half Sleeve Activewear T-Shirt, Regular Fit"


def src(title=AMZ, brand="jockey"):
    return Canonical(brand=brand, product_type="tee", neck="round", base_colour="black", gender="men", title=title)


def cand(title, brand="jockey"):
    return Candidate(Platform.MYNTRA, "u", title, Canonical(brand=brand, product_type="tee", neck="round",
                                                            base_colour="black", gender="men", title=title), True)


def test_fabric_set():
    assert fabric_set(AMZ, "jockey") == {"polyester"}  # microfiber is polyester
    assert fabric_set("Pure Cotton T-shirt", None) == {"cotton"}
    assert fabric_set("Poly Cotton Tee", None) == {"polyester", "cotton"}
    assert fabric_set("Cotton Blend Tee", None) is None  # a blend may hold anything: unknown
    assert fabric_set("Cotton County Premium Men Tee", "cotton county") == frozenset()  # brand words aren't fabric


def test_polyester_vs_pure_cotton_is_never_a_match_but_shown_as_closest():
    # user 2026-11-13: a different fabric is not the exact product, but it passed every hard check: show it
    # under "Not listed" as a closest option instead of hiding it
    from app.matcher import decide
    from app.models import Decision, SourceProduct
    sp = SourceProduct(url="u", asin="B0H3QHNZGQ", title=AMZ, image=None, category=A, canon=src())
    cotton = cand("Jockey Men Black Solid Round Neck Pure Cotton T-shirt")
    assert veto(src(), cotton, A) is None
    m = decide(sp, [cotton])
    assert m.decision == Decision.NONE and [(c.title, d) for c, d in m.closest] == [(cotton.title, ["fabric"])]


def test_unknown_or_overlapping_fabric_is_not_a_difference():
    from app.matcher import fabric_clash
    for t in ("Jockey Men Black Solid Round Neck T-shirt",          # no fabric named
              "Jockey Men Black Microfiber Round Neck T-shirt",     # same fabric
              "Jockey Men Black Cotton Blend Round Neck T-shirt",   # blend
              "Jockey Men Black Poly Cotton Round Neck T-shirt"):   # overlap
        assert not fabric_clash(src(), cand(t), A)


def test_not_listed_reason_names_the_fabric():
    from app.matcher import decide, to_result
    from app.models import FetchStatus, Outcome, SourceProduct
    sp = SourceProduct(url="u", asin="B0H3QHNZGQ", title=AMZ, image=None, category=A, canon=src())
    r = to_result(Platform.MYNTRA, decide(sp, [cand("Jockey Men Black Solid Round Neck Pure Cotton T-shirt")]),
                  [FetchStatus.OK], "Black")
    assert r.outcome == Outcome.NOT_LISTED and "none had the same fabric (polyester)" in r.reason
    assert r.closest[0]["differs"] == "fabric differs"


async def test_photo_none_keeps_the_fabric_different_listing_as_closest():
    import httpx
    from app import confirm
    from app.matcher import decide
    from app.models import Decision, SourceProduct
    sp = SourceProduct(url="u", asin="B0H3QHNZGQ", title=AMZ, image=None, category=A, canon=src())
    other = cand("Jockey Men Black Round Neck Activewear T-shirt")
    other.url = "o"
    cotton = cand("Jockey Men Black Solid Round Neck Pure Cotton T-shirt")

    async def picker(src_, shown):
        return {"match": "none", "table": {"1": {"print": "different"}}}
    async with httpx.AsyncClient() as cl:
        m = await confirm.confirm(cl, sp, decide(sp, [other, cotton]), picker=picker)
    assert m.decision == Decision.NONE and [d for _, d in m.closest] == [["print"], ["fabric"]]
