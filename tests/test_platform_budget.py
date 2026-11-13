"""Code review 2026-11-13 (Myntra retries): a stalling store must not eat the whole budget across query rungs,
and progress made before the budget runs out must not be thrown away."""
import asyncio
import json
from pathlib import Path

from app import pipeline as pl
from app.extract import from_amazon
from app.models import Candidate, Canonical, FetchStatus, Outcome, Platform

FX = Path(__file__).parent / "fixtures"


def puma():
    return from_amazon(json.loads((FX / "amz_puma_tee.json").read_text())[0])


async def test_store_not_answering_stops_the_ladder(monkeypatch):
    calls = []

    async def down(client, q):
        calls.append(q)
        return FetchStatus.ERROR, []
    monkeypatch.setitem(pl.ADAPTERS, Platform.MYNTRA, down)
    sp = puma()
    assert len(pl.ladder(sp, Platform.MYNTRA)) > 1
    r = await pl.run_platform(None, sp, Platform.MYNTRA)
    assert len(calls) == 1 and r.outcome == Outcome.COULDNT_CHECK


async def test_budget_expiry_keeps_a_possible_match_already_found(monkeypatch):
    t = puma().title  # survives the gates; no style code → "Possible" pending the photo check
    found = Candidate(Platform.FLIPKART, "https://www.flipkart.com/x/p/itm1?pid=TSH1", t,
                      Canonical(brand="puma", product_type="tee", colour="Black", base_colour="black",
                                gender="men", title=t), True)

    async def code_rung(client, brand, colour, code, noun="t-shirt"):
        return FetchStatus.OK, [found]

    async def stall(client, q):
        await asyncio.sleep(30)
    monkeypatch.setattr(pl, "flipkart_code_candidates", code_rung)
    monkeypatch.setitem(pl.ADAPTERS, Platform.FLIPKART, stall)
    monkeypatch.setitem(pl.TIMEOUTS, Platform.FLIPKART, 0.3)
    r = await pl.run_platform(None, puma(), Platform.FLIPKART)
    assert r.outcome == Outcome.POSSIBLE and r.url == found.url
