"""One-call photo check (proposal 2026-11-13): the model fills an attribute table for each candidate, then
answers; the code accepts the answer only when the table backs it (guards against position bias)."""
from app.vision import judge

S, D, U = "same", "different", "unclear"


def table(*rows):
    return {str(i + 1): dict(zip(("neck", "sleeve", "colour", "logo", "stripes", "print"), r)) for i, r in enumerate(rows)}


def test_clean_match():
    res = {"table": table((S, S, S, S, U, S), (S, S, S, D, S, S), (D, S, S, S, S, S)), "match": 1}
    assert judge(res, 3) == ("match", 0)


def test_two_clean_candidates_is_unclear():
    res = {"table": table((S, S, S, S, S, S), (S, S, S, S, U, S)), "match": 1}
    assert judge(res, 2) == ("unclear", None)


def test_answer_contradicting_table_is_unclear():
    res = {"table": table((S, S, D, S, S, S), (D, S, S, S, S, S)), "match": 1}
    assert judge(res, 2) == ("unclear", None)


def test_clean_none():
    res = {"table": table((D, S, S, S, S, S), (S, S, S, D, S, S)), "match": "none"}
    assert judge(res, 2) == ("none", None)


def test_none_without_named_difference_is_unclear():
    res = {"table": table((D, S, S, S, S, S), (S, U, S, S, S, S)), "match": "none"}
    assert judge(res, 2) == ("unclear", None)


def test_garbage_is_unclear():
    assert judge({}, 3) == ("unclear", None)
    assert judge({"match": 7, "table": table((S,) * 6)}, 1) == ("unclear", None)
    assert judge({"match": "unclear", "table": table((S,) * 6)}, 1) == ("unclear", None)


def test_reply_text_skips_thinking_blocks():
    # 2026-11-13: replies can start with a thinking block; reading content[0].text crashed and the check
    # silently returned nothing
    from types import SimpleNamespace as NS
    from app.vision import reply_text
    msg = NS(content=[NS(type="thinking", thinking="..."), NS(type="text", text='{"match": 1}')])
    assert reply_text(msg) == '{"match": 1}'
    assert reply_text(NS(content=[])) == ""
