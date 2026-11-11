# Cross-platform product matcher

Paste an Amazon.in product link. For each competing platform, the app says whether that
platform sells the **exact same product** and whether you can buy it now:

| Category | Platforms | Must match (besides brand + model) |
|---|---|---|
| Smartphones | Flipkart, Croma | RAM, storage (and colour) |
| Televisions | Flipkart, Croma | Screen size (and model number when Amazon has it) |
| Sneakers | Flipkart, Myntra | Colour |
| T-shirts, polos, jerseys | Flipkart, Myntra | Colour (plus type, pack count, distinctive words) |

Each platform gets one of: **In stock**, **Out of stock**, **Not listed**,
**Possible match – verify** or **Couldn't check**, with a one-line reason.

How the matching works, in plain words: [docs/ELI5.md](docs/ELI5.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs Python ≥ 3.11 and the dependencies for you)
- `APIFY_KEY` in the environment. It's required for Amazon (the input) and Croma, which are
  read through Apify actors.
- `ANTHROPIC_API_KEY` (optional). It's used only to break ties between equally good listings.
  Without it, a tie stays "Possible match – verify".

## Run

```bash
./run.sh            # uv sync + uvicorn → http://127.0.0.1:8000
```

Results stream in per platform as they finish. Flipkart and Myntra take a few seconds;
Croma (through Apify) takes ~10–60 s.

## Tests

```bash
uv run pytest -q    # offline: every platform test runs on saved responses in tests/fixtures/
```

## Golden set

`scripts/golden.json` holds real Amazon.in links with hand-checked expected outcomes per
platform. Each expectation has the listing id(s) it must point to and a note on the evidence.
`scripts/golden.py` runs the real pipeline on them and prints precision and coverage.

```bash
uv run python scripts/golden.py                 # replay from cache only: no network, no spend
uv run python scripts/golden.py --refresh-http  # re-fetch Flipkart/Myntra (free); Apify stays cached
uv run python scripts/golden.py --live          # full live run; spends Apify credit on cache misses
```

- **precision**: correct confident answers (In stock / Out of stock) ÷ all confident answers.
- **coverage**: correct confident answers ÷ cases where the product is really there.
- **wrong match**: a confident answer that links a different product. It's printed loudly
  and makes the script exit non-zero.

The caches live in `.cache/` (gitignored). Apify responses are in `.cache/apify/`, and the
golden-only replays of Flipkart/Myntra pages and LLM picks are in `.cache/golden/`.

## Architecture

```
browser (static/index.html)
   │  GET /api/check?url=…   (Server-Sent Events: source → progress → result×N → done)
   ▼
app/server.py ── app/pipeline.py: check(url)
                    │
                    ├─ sources/amazon.py   resolve link → Apify junglee~amazon-crawler
                    │      └─ extract.from_amazon → SourceProduct (category + canonical record)
                    │
                    └─ per platform, concurrently (Croma 90 s, Flipkart/Myntra 20 s budget):
                         queries.ladder(src, platform)  model code → brand+family+attrs → brand+family
                           └─ sources/flipkart.py  search page → ≤10 product pages (plain HTTPS)
                              sources/croma.py     Apify sian.agency~croma-product-scraper
                              sources/myntra.py    search page → embedded window.__myx JSON
                                 └─ extract.from_*  → Candidate (canonical record + stock)
                         matcher.decide   vetoes → strict colour pool → score → MATCH / AMBIGUOUS / NONE
                         llm.llm_tiebreak (optional, ties only)
                         matcher.to_result → PlatformResult (state, link, reason)
```

`app/normalize.py` holds the pure helpers: brand aliases, family, GB/TB and inch parsing,
colour → base colour, EAN checksum, accessory detection and distinctive words.
`app/sources/apify.py` caches every non-empty Apify response on disk.

## Data sources

| Platform | How | Notes |
|---|---|---|
| Amazon.in (input) | Apify `junglee~amazon-crawler`, product URL, `scrapeProductDetails` | Plain HTTP gets a bot challenge. Phones usually have no model number/EAN; TVs do. ≈ $0.005 per product. |
| Flipkart | Plain HTTPS: search page, then each product page (JSON-LD + spec rows, or page-state JSON when the table isn't rendered) | Variants share the `itm` id and differ by `pid`. |
| Croma | Apify `sian.agency~croma-product-scraper` (`detail` mode, 10 results) | Direct access is Akamai-protected, and we don't bypass it. Gives model number, EAN, RAM/storage, screen size and colour. |
| Myntra | Plain HTTPS search page with embedded `window.__myx` JSON | Gives brand, name, primary colour, article type, and per-size availability. |

## Known limitations

- **Croma is expensive.** Measured on 2026-11-11, the Croma actor costs about **$0.07 per
  detailed result**, so one run (up to 10 results) costs $0.18–0.71. The ~$0.05 first assumed was
  wrong. When a phone/TV check walks 2–3 query rungs (for example a product Croma doesn't carry),
  it costs $1.4–2.1. The free Apify tier ($5/month) covers only a handful of uncached phone/TV checks.
  Responses are cached, so a repeated check is free.
- **Thin golden set.** Only 4 of the 12 planned golden cases (3 phones, 1 TV) could be captured
  within the Apify budget. The sneaker, T-shirt and other TV cases are listed in
  `golden.json` as `pending`. Croma results for two cases were captured before a fix changed
  their search query, so in cache mode those show "Couldn't check".
- Amazon often lacks a model number/EAN for phones, so phones are matched on family + RAM +
  storage + colour. Apple's Amazon listings don't state RAM, so iPhones end up as
  "Possible match – verify".
- A TV whose Amazon page has no model number is matched on family + size only. It usually
  ends up as "Possible match". Model numbers have to match exactly (after removing spaces), so a
  regional suffix on one store gives "Not listed" rather than a guess.
- Flipkart/Myntra markup can change, or they can start rate-limiting. Failures show as
  "Couldn't check", never as "Not listed". One live Flipkart run hit the 20 s budget and
  came back "Couldn't check".
- Croma search returns nearby models when the exact one is missing (for example "S26 Plus"
  returns only S22/S23). The vetoes drop them, so the result is "Not listed".
- Stock is a snapshot at check time. Myntra counts a product as in stock if any size is available.
- Apparel identity is a heuristic (brand, type, base colour, pack count and distinctive-word overlap).
  When two listings look equally close, the answer is "Possible match – verify", never a guess.
