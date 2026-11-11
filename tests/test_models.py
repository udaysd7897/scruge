from pathlib import Path

FIX = Path(__file__).parent / "fixtures"


def test_outcome_labels():
    from app.models import Canonical, Outcome

    assert Outcome.POSSIBLE.value == "Possible match – verify"
    assert Outcome.COULDNT_CHECK.value == "Couldn't check"
    assert Canonical().pack_count == 1


def test_fixtures_present():
    names = ["amz_apify.json", "croma_apify.json", "fk_s26_512blk.html", "fk_pdp.html",
             "fk_s26.html", "fk_search.html", "my_search.html", "amazon_bm_verify.html"]
    for n in names:
        assert (FIX / n).exists(), n
