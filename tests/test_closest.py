"""Not listed, but hard checks passed (user request 2026-11-13): show up to 3 closest listings under
"Not listed", each with what the photo check found different. The status stays Not listed."""
from app import confirm
from app.matcher import Match, decide, to_result
from app.models import Decision, FetchStatus, Outcome, Platform
from app.vision import differences
from tests.test_confirm import client, myntra, src, MY_URL


def test_differences_lists_attributes_marked_different():
    res = {"table": {"1": {"logo": "different", "print": "different", "neck": "same"},
                     "2": {"stripes": "DIFFERENT"}, "3": {"neck": "same"}}}
    assert differences(res, 3) == [["logo", "print"], ["stripes"], []]
    assert differences({}, 2) == [[], []]


async def test_photo_none_keeps_closest_ranked_by_fewest_differences():
    s = src()
    urls = [MY_URL.replace("35720668", str(35720660 + i)) for i in range(4)]
    cands = [myntra(url=u) for u in urls]

    async def picker(src_, shown):
        diff = {urls[0]: ["logo", "print", "stripes"], urls[1]: ["logo"], urls[2]: ["print", "logo"], urls[3]: ["neck", "logo", "print"]}
        return {"match": "none", "table": {str(i): {a: ("different" if a in diff[c.url] else "same")
                for a in ("neck", "sleeve", "colour", "logo", "stripes", "print")} for i, c in enumerate(shown, 1)}}
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, cands), picker=picker)
    assert m.decision == Decision.NONE
    assert [(c.url, d) for c, d in m.closest] == [(urls[1], ["logo"]), (urls[2], ["logo", "print"]),
                                                  (urls[0], ["logo", "stripes", "print"])]
    r = to_result(Platform.MYNTRA, m, [FetchStatus.OK], "Black")
    assert r.outcome == Outcome.NOT_LISTED and r.url is None
    assert r.closest[0] == {"title": cands[1].title, "url": urls[1], "differs": "logo differs"}
    assert r.closest[1]["differs"] == "logo, print differ"


def test_veto_only_not_listed_has_no_closest():
    m = Match(Decision.NONE, None, "no survivors", checked=4, none_had="brand")
    r = to_result(Platform.FLIPKART, m, [FetchStatus.OK], None)
    assert r.outcome == Outcome.NOT_LISTED and r.closest == []


async def test_photo_difference_on_a_hard_check_is_not_close():
    # user report 2026-11-13 (Jockey B0H3QHNZGQ): Amazon title names no neck, so the text gate let a listing
    # through; the photo saw a different neck. A neck/colour difference would have been a hard reject: such
    # a listing is not a "closest option"
    s = src()
    urls = [MY_URL.replace("35720668", str(35720670 + i)) for i in range(3)]
    cands = [myntra(url=u) for u in urls]

    async def picker(src_, shown):
        diff = {urls[0]: ["neck"], urls[1]: ["colour", "logo"], urls[2]: ["logo"]}
        return {"match": "none", "table": {str(i): {a: ("different" if a in diff[c.url] else "same")
                for a in ("neck", "sleeve", "colour", "logo", "stripes", "print")} for i, c in enumerate(shown, 1)}}
    async with client() as cl:
        m = await confirm.confirm(cl, s, decide(s, cands), picker=picker)
    assert [c.url for c, _ in m.closest] == [urls[2]]
