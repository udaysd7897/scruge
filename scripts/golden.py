"""Golden-set evaluation: run the real pipeline on hand-checked Amazon links and score it.

    uv run python scripts/golden.py          # replay from cache only (no network, no Apify spend)
    uv run python scripts/golden.py --live   # allow network; refreshes the caches (spends Apify credit)
    uv run python scripts/golden.py --refresh-http   # re-fetch Flipkart/Myntra (free), Apify still cache-only

Caches (all under .cache/, gitignored): Apify responses in .cache/apify/ (the app's own cache),
plus golden-only replays of Flipkart/Myntra pages, empty Apify results and LLM tie-break picks in
.cache/golden/. In cache mode a miss surfaces as "Couldn't check", never as a fresh request.

Scoring (cases marked "unsure" are shown but not scored):
  confident  = app said "In stock" / "Out of stock"
  correct    = confident, same outcome as expected, and the linked listing is one of the expected ids
  precision  = correct / confident
  coverage   = correct / cases where expected is In stock or Out of stock
  WRONG MATCH = confident answer linking a listing that is not the expected product
                (or a confident answer where we expected "Not listed"). Exit code 1 if any.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GOLDEN = Path(__file__).with_name("golden.json")
STORE = ROOT / ".cache" / "golden"
CONFIDENT = {"In stock", "Out of stock"}


def _key(*parts) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _load(kind: str, key: str):
    p = STORE / kind / f"{key}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _save(kind: str, key: str, value) -> None:
    p = STORE / kind / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))


def install_replay(live: bool, live_http: bool = False) -> None:
    """Patch the source/LLM seams so a run is replayable offline."""
    live_http = live or live_http
    from app import pipeline
    from app.models import FetchStatus
    from app.sources import amazon, apify, croma, flipkart, http, myntra

    apify.OFFLINE = not live
    real_fetch, real_actor, real_llm = http.fetch, apify.run_actor, pipeline.llm_tiebreak

    async def fetch(client, url):
        k = _key("http", url)
        if not live_http:
            hit = _load("http", k)
            return (FetchStatus(hit[0]), hit[1]) if hit else (FetchStatus.ERROR, "")
        st, body = await real_fetch(client, url)
        _save("http", k, [st.value, body])
        return st, body

    async def run_actor(client, actor, payload, timeout_s=90):
        # the app does not cache empty Apify results; remember them so replays stay faithful
        k = _key("empty", actor, payload)
        st, items = await real_actor(client, actor, payload, timeout_s)
        if st == FetchStatus.EMPTY:
            _save("apify_empty", k, True)
        elif st == FetchStatus.ERROR and not live and _load("apify_empty", k):
            return FetchStatus.EMPTY, []
        return st, items

    async def llm_tiebreak(src, survivors):
        k = _key("llm", src.asin, [c.url for c in survivors])
        if live_http:
            chosen = await real_llm(src, survivors)
            _save("llm", k, chosen.url if chosen else None)
            return chosen
        url = _load("llm", k)
        return next((c for c in survivors if c.url == url), None)

    flipkart.fetch = myntra.fetch = fetch
    amazon.run_actor = croma.run_actor = run_actor
    pipeline.llm_tiebreak = llm_tiebreak


async def run_case(url: str) -> tuple[dict | None, dict[str, dict], str | None]:
    from app.pipeline import check

    src, results, err = None, {}, None
    async for ev in check(url):
        if ev["type"] == "source":
            src = ev["data"]
        elif ev["type"] == "result":
            results[ev["data"]["platform"]] = ev["data"]
        elif ev["type"] == "error":
            err = ev["message"]
    return src, results, err


def grade(exp: dict, got: dict | None) -> str:
    """'ok' | 'wrong' (wrong product, confidently) | 'stock' (right product, wrong stock) | 'miss'."""
    out = (got or {}).get("outcome", "Couldn't check")
    url = (got or {}).get("url") or ""
    ids = exp.get("ids") or []
    same_product = bool(ids) and any(i in url for i in ids)
    if out in CONFIDENT:
        if not same_product:
            return "wrong"
        return "ok" if out == exp["outcome"] else "stock"
    return "ok" if out == exp["outcome"] else "miss"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="allow network (spends Apify credit on cache misses)")
    ap.add_argument("--refresh-http", action="store_true",
                    help="re-fetch Flipkart/Myntra pages and re-ask the LLM; Apify stays cache-only")
    ap.add_argument("--only", help="run only the case with this id")
    args = ap.parse_args()
    if not args.live:
        os.environ["APIFY_OFFLINE"] = "1"
    install_replay(args.live, args.refresh_http)

    cases = json.loads(GOLDEN.read_text())["cases"]
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
    rows, wrongs = [], []
    conf = defaultdict(int)       # (dim, key) -> confident answers
    correct = defaultdict(int)    # (dim, key) -> correct confident answers
    want = defaultdict(int)       # (dim, key) -> expected In/Out of stock
    covered = defaultdict(int)    # (dim, key) -> correct among want

    skipped = [c for c in cases if c.get("pending")]
    for case in cases:
        if case.get("pending"):
            continue
        src, results, err = asyncio.run(run_case(case["url"]))
        title = (src or {}).get("title", err or "?")[:60]
        print(f"\n[{case['id']}] {case['category']}  {case['url']}\n    {title}")
        for plat, exp in case["expected"].items():
            got = results.get(plat)
            g = grade(exp, got)
            out = (got or {}).get("outcome", "Couldn't check")
            mark = {"ok": "ok", "wrong": "WRONG MATCH", "stock": "stock differs", "miss": "miss"}[g]
            if case.get("unsure"):
                mark += " (unsure, not scored)"
            print(f"    {plat:<9} expected {exp['outcome']:<24} got {out:<24} {mark}")
            if got and got.get("url"):
                print(f"              -> {got['url']}")
            if got:
                print(f"              why: {got.get('reason')}")
            rows.append((case["id"], plat, exp["outcome"], out, g))
            if case.get("unsure"):
                continue
            for key in (("cat", case["category"]), ("plat", plat), ("all", "all")):
                if out in CONFIDENT:
                    conf[key] += 1
                    correct[key] += g == "ok"
                if exp["outcome"] in CONFIDENT:
                    want[key] += 1
                    covered[key] += g == "ok" and out in CONFIDENT
            if g == "wrong":
                wrongs.append((case["id"], plat, out, (got or {}).get("url")))

    def pct(a, b):
        return f"{a}/{b} = {a / b:.0%}" if b else "n/a"

    print("\n" + "=" * 72)
    print(f"{'':<14}{'precision':<22}{'coverage':<22}")
    for dim in ("cat", "plat", "all"):
        keys = sorted({k for (d, k) in list(conf) + list(want) if d == dim})
        for k in keys:
            print(f"{k:<14}{pct(correct[(dim, k)], conf[(dim, k)]):<22}{pct(covered[(dim, k)], want[(dim, k)]):<22}")
        print("-" * 72)
    for c in skipped:
        print(f"not run: {c['id']} ({c['pending']})")
    if wrongs:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        for w in wrongs:
            print(f"!!! WRONG MATCH: case {w[0]} on {w[1]}: said {w[2]} -> {w[3]}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        print("Wrong matches: 0")
    return 1 if wrongs else 0


if __name__ == "__main__":
    sys.exit(main())
