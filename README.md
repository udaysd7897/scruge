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
  read through Apify actors. Without it (and with no cached response) a check stops with
  "APIFY_KEY is not set — see README".
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

Cache-only mode is the `APIFY_OFFLINE=1` environment variable, which `golden.py` sets by
default. With it set, a missing Apify cache entry is treated as an error ("Couldn't check")
and no paid Apify call is made. Leave it **unset** when running the app (`./run.sh`).
Otherwise any Amazon link or Croma search that isn't already cached fails.

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
                    └─ per platform, concurrently (Croma 90 s, Flipkart 45 s, Myntra 20 s budget):
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
  storage + colour. Apple's Amazon listings don't state RAM, so for brand Apple RAM is not
  required: an iPhone is matched on family + storage + colour, and the RAM veto applies only
  when both sides show RAM.
- A TV whose Amazon page has no model number is never answered confidently. Its family comes
  from the title with sizes and generic words removed ("LG 139 cms (55 inches) NU87 AI Series
  Nano ..." becomes "nu87 nano"). Listings are filtered by brand, screen size and overlapping
  series words, and the closest one is shown as "Possible match – verify" ("Couldn't read model
  number on Amazon"). A TV listing without a model number is likewise never confirmed. When both
  sides have one, the model numbers must match exactly (after removing spaces), so a regional
  suffix on one store gives "Not listed" rather than a guess.
- Flipkart/Myntra markup can change, or they can start rate-limiting. Failures show as
  "Couldn't check", never as "Not listed". One live Flipkart run hit the old 20 s budget and
  came back "Couldn't check", so Flipkart now gets 45 s (a search page plus up to 10 product
  pages, 3 at a time). If any Flipkart product page fails to load, a match among the pages that
  did load still wins, but "no match" becomes "Couldn't check": the unread page may have been it.
- Croma search returns nearby models when the exact one is missing (for example "S26 Plus"
  returns only S22/S23). The vetoes drop them, so the result is "Not listed".
- Stock is a snapshot at check time. Myntra counts a product as in stock if any size is available.
- Apparel identity is a heuristic (brand, type, base colour, pack count and distinctive-word overlap).
  The product type (polo / jersey / tee) comes from the title or the last breadcrumb ("Polo T-Shirt"
  is a polo; brand names like "U.S. Polo Assn." are ignored). When two listings look equally close,
  the answer is "Possible match – verify", never a guess.
- Sneaker and apparel names are worded differently per store ("Grand Court 3.0 Sneaker" vs
  "Grand Court 3.0 Tennis Shoes"), so their model line needn't be identical: the distinctive-word
  veto decides, and every source model-line word must appear in the listing. A survivor that is
  only weakly confirmed (a generic title such as "Puma Men Polo T-shirt", listing words the Amazon
  title doesn't have such as "Graphic Printed" or "React", or a sneaker model line that differs)
  is shown as "Possible match – verify", never as a confident match. Many Myntra/Flipkart apparel
  titles are generic, so expect more "Possible match" than "In stock" for T-shirts.
- None of the sneaker or apparel golden cases could be captured (Apify budget), so those rules
  are tested only against synthetic, real-shaped listings.
