"""TV identity is the manufacturer model code (design report 2026-11-12): size + series core parsed by one
generic pattern, store punctuation/suffixes ignored, no per-brand lists."""
from app.matcher import veto
from app.models import Candidate, Canonical, Category, Platform
from app.normalize import tv_code


def test_tv_code_parse():
    assert tv_code("55NU870BPLA") == (55, "55NU870BPLA")
    assert tv_code("55UR75006LC.ATR") == (55, "55UR75006LC")
    assert tv_code("K-55XR70") == tv_code("K55XR70") == (55, "K55XR70")
    assert tv_code("OLED55C6XLA") == (55, "OLED55C6XLA")
    assert tv_code("UA55DUE77AKLXL")[0] == 55
    assert tv_code("NU87 Nano") is None and tv_code(None) is None


def tv(code, size=55):
    return Canonical(brand="lg", model_code=code, screen_in=size, title="t")


def cand(code, size=55):
    return Candidate(Platform.FLIPKART, "u", "t", tv(code, size), True)


def test_store_punctuation_does_not_veto():
    assert veto(tv("55UR75006LC.ATR"), cand("55UR75006LC"), Category.TV) is None
    assert veto(tv("K-55XR70"), cand("K55XR70"), Category.TV) is None


def test_different_codes_and_sizes_veto():
    assert veto(tv("55NU870BPLA"), cand("55UA82006LA"), Category.TV) == "model code"
    assert veto(tv("55NU870BPLA"), cand("65NU870BPLA", 65), Category.TV) is not None
