# Cross-platform product matcher

Paste an Amazon.in product link. For each competing platform the app says whether that
platform sells the **exact same product** and whether you can buy it now.

| Category | Platforms checked | Identity rests on |
|---|---|---|
| Smartphones | Flipkart, Croma | brand + model line + RAM + storage (+ colour) |
| Televisions | Flipkart, Croma | brand + screen size + model number |
| Sneakers | Flipkart, Myntra | brand style code, else name words + colour |
| T-shirts, polos, jerseys | Flipkart, Myntra | brand style code, else name words + colour + type + pack count |

Plain-words explanation of the matching: [docs/ELI5.md](docs/ELI5.md).

## Run

Prerequisite: [uv](https://docs.astral.sh/uv/) (installs Python >= 3.11 and dependencies).

```bash
./run.sh     # uv sync + uvicorn -> http://127.0.0.1:8000
```

| Env var | Meaning |
|---|---|
| `APIFY_KEY` | Apify token. Used for Croma (always) and as the Amazon fallback when the plain product page can't be read. Without it (and no cached answer) the check says "APIFY_KEY is not set - see README". |
| `ANTHROPIC_API_KEY` | Optional. Enables (a) the LLM tie-break between equally good listings and (b) the photo check that confirms Myntra apparel. Without it those cases stay "Possible match - verify". |
| `APIFY_OFFLINE=1` | Cache-only mode: a missing Apify cache entry is an error, never a paid call. `scripts/golden.py` sets it; leave it **unset** when running the app. |
| `LOG_LEVEL` | Python log level for the app log (default `INFO`; `DEBUG` also logs every successful fetch). |

Results stream to the page (Server-Sent Events) per platform as each finishes.

## Architecture / flow

```
browser (static/index.html)
   | GET /api/check?url=...   SSE: progress -> source -> result x N -> done
   v
app/server.py -> app/pipeline.py: check(url)
  1. sources/amazon.py   normalise link to amazon.in/dp/<ASIN> (short links followed)
        a. plain GET of the product page -> sources/amazon_page.py (title, breadcrumbs, spec rows,
           MRP, image, bestseller links)
        b. if blocked/unreadable: Apify junglee~amazon-crawler (paid, cached)
        -> extract.from_amazon -> SourceProduct {category, canonical record}
  2. Apparel with a style code: brandsite.official_name (Puma only) -> official product name
  3. per platform, concurrently (Croma 90 s, Flipkart 45 s, Myntra 20 s):
        queries.ladder(src, platform)       rung by rung, stop at first MATCH/AMBIGUOUS
          -> flipkart.py | croma.py | myntra.py  -> extract.from_* -> Candidates
        matcher.decide: vetoes -> colour pool -> doubts -> score -> MATCH / AMBIGUOUS / NONE
        tie            -> llm.llm_tiebreak (optional)
        NEEDS_CONFIRM  -> confirm.py: MRP + manufacturer + photo (vision.py), 45 s cap
        matcher.to_result -> PlatformResult {state, link, reason}
```

**Category** (`extract.amazon_category`) comes from what Amazon states, not from model-name lists:
breadcrumb leaf (then its parent) -> bestseller browse node (smartphones) -> "Item Type Name" ->
spec fingerprint (phone: Android/iOS + storage + light; TV: HDMI ports / tuner / VESA / display
size class) -> title -> unsupported. Accessories, remotes, sandals, slippers, flip-flops and socks
are unsupported.

**Query ladder** (`app/queries.py`), first rung that yields a match or close call wins:
- phones: model code, then brand + family + RAM + storage + colour (missing parts skipped), then brand + family
- TVs: model code, then brand + family/code + size + "inch", then brand + family
- sneakers: model code, brand + family + colour, brand + family
- apparel: model code (not on Myntra); brand + **official name** + colour; brand + official name; brand + **Amazon "Model Name"** + colour + "t-shirt"; brand + type + colour + up to 3 distinctive words; brand + up to 4 distinctive words

**Official name** (`app/brandsite.py`): the Puma style code is looked up on in.puma.com search to
get the product name Myntra lists. Only Puma; other brands fall back to Amazon's title.

## Matching rules

A candidate must survive every veto (`matcher.veto`); the score (identity code/EAN 0.40, exact
colour 0.25, title similarity 0.20, completeness 0.15) only ranks survivors, it never accepts one.
Candidates within 0.15 of the best are a tie unless they are provably one product (same EAN, or same
model code + same specs).

- **Phones**: accessory, brand, family, model code, RAM and storage must agree (RAM/storage only
  when both sides show them; iPhones need no RAM). Colour is strict: only the exact colour counts;
  if the store has none, another colour may be shown with a note; a colourless listing next to
  other colours is "Possible match".
- **TVs**: brand, family (series words may overlap), screen within 1 inch, and model code compared
  as size + normalised code (`tv_code`). Colour is ignored. Confirmed only when both sides show a
  model number; otherwise "Possible match".
- **Sneakers / apparel**: accessory, brand, gender (unisex is compatible), product type (polo /
  jersey / tee), style code, base colour, pack count, distinctive words. A shared brand style code
  (`same_style`; case/space/-/_ insensitive, so 528856_01 = 52885601) is identity: titles are then not
  compared, because stores rewrite titles. A *different* style code is a veto. Style codes come from
  Amazon "Style Number / Item model number / Manufacturer Part Number / Model Number" and Flipkart
  "Style Code / Article Number"; Flipkart's displayed title is used instead of its generated JSON-LD
  name. Myntra search data has brand, name, colour, article type, gender, MRP, size availability
  but **no style code**.
- **No shared code (NEEDS_CONFIRM)**: name agreement is not proof. `confirm.py` checks the top 3
  survivors: MRP equals Amazon's, the Myntra product page names the same manufacturer, and the photo
  check says SAME. Exactly one passing survivor becomes a match ("name, MRP, manufacturer and
  photo"); otherwise "Possible match". Needs `ANTHROPIC_API_KEY`; Flipkart candidates cannot pass when
  Amazon states a manufacturer. Other doubts (generic title, listing words Amazon lacks, sneaker model
  line differs) also cap the result at "Possible match", and the LLM can't upgrade them.

### Result states

| State | Meaning |
|---|---|
| In stock / Out of stock | One surviving listing, confidently the same product, with link and a "Matched on ..." reason. Stock is a snapshot (Myntra: any size available). |
| Not listed | Every search completed, none of the candidates survived. Reason names the most common veto. |
| Possible match - verify | Link shown, but identity or stock is not proven (tie, missing attribute, doubt, unreadable stock, or unconfirmed). |
| Couldn't check | Blocked, errored or timed out. A failed fetch is never turned into "Not listed"; if any Flipkart product page failed, a match among the loaded ones still wins but "no match" becomes "Couldn't check". |

## Data sources and cost

| Platform | How | Cost / notes |
|---|---|---|
| Amazon.in (input) | Plain HTTPS product page first; Apify `junglee~amazon-crawler` fallback | Page: free. Apify ~ $0.005 per product, cached on disk. |
| Flipkart | Plain HTTPS: search page (top 10 links), each product page (JSON-LD + spec rows / page-state JSON), then sibling variants (same `itm` id) of the top 3 hits, up to 12 extra pages | Free. 3 pages fetched at a time. |
| Croma | Apify `sian.agency~croma-product-scraper`, detail mode, **max 5 results** per search | ~ $0.07 per result (measured 2026-11-11), so up to ~$0.35 per search, more when the ladder walks several rungs. Cached; larger cached answers are reused. Direct access is bot-protected and is not bypassed. |
| Myntra | Plain HTTPS search page with embedded `window.__myx` JSON; product page for manufacturer during confirmation | Free. |
| Brand site (Puma) | Plain search page for the style code | Free. |
| Anthropic | Tie-break (20 s cap) and photo check, model `claude-sonnet-5-5` | Only with `ANTHROPIC_API_KEY`. |

Timeouts: Croma 90 s, Flipkart 45 s, Myntra 20 s per platform, confirmation 45 s.

## Logging

`logs/app.log` (plus stderr) records, per check: the Amazon read (page vs Apify, extracted fields),
each query, fetch status, candidate count and veto reasons, the decision per rung, confirmation, and
the final result per platform. Set `LOG_LEVEL=DEBUG` for every successful fetch too.

## Tests and golden set

```bash
uv run pytest -q    # offline: runs on saved responses in tests/fixtures/
```

`scripts/golden.json` holds real Amazon.in links with hand-checked expected outcomes.
`scripts/golden.py` runs the real pipeline on them and prints precision (correct confident answers
/ all confident answers) and coverage (correct confident answers / cases where the product is
really listed). A confident answer pointing at a different product is a "wrong match": it is
printed loudly and exits non-zero.

```bash
uv run python scripts/golden.py                 # cache only: no network, no spend
uv run python scripts/golden.py --refresh-http  # re-fetch Flipkart/Myntra (free); Apify stays cached
uv run python scripts/golden.py --live          # live; spends Apify credit on cache misses
```

Caches live in `.cache/` (gitignored): `.cache/apify/` and golden replays in `.cache/golden/`.

## Known limitations

- **Amazon bot checks.** Amazon intermittently serves bot-check pages to plain requests. The app
  then falls back to Apify, which needs credit. It never tries to bypass a bot check.
- **Apify credit is exhausted as of 2026-11-13.** Croma checks, and any Amazon link whose page is
  blocked (and not cached), fail with "Couldn't check" / "Couldn't read this Amazon product".
- **Brand-site name lookup is Puma only.** Other apparel brands search with Amazon's generic title,
  which finds fewer Myntra listings.
- **Style codes that differ per store can be wrongly rejected.** Some brands use another code on
  each store (Van Heusen 60001 vs IHQTS1LDS60001); when both sides show a code and they differ, the
  candidate is vetoed, so the real listing may come back "Not listed".
- **Myntra shows no style code.** Myntra apparel is confirmed only by MRP + manufacturer + photo,
  which needs `ANTHROPIC_API_KEY`; without it (or if any check fails) the answer is "Possible match".
  Generic titles also produce more "Possible match" than "In stock" for T-shirts.
- **Phones/TVs without codes.** Amazon rarely gives phone model numbers/EANs, so phones are matched
  on family + RAM + storage + colour. A TV with no model number on Amazon (or on the listing) is never
  confirmed. Croma search returns neighbouring models when the exact one is missing; the vetoes drop
  them, giving "Not listed".
- **Fragile scraping.** Flipkart/Myntra markup can change or start rate-limiting (shown as
  "Couldn't check").
- **Terms of use.** Amazon, Flipkart and Myntra restrict automated access. Use this low-volume and
  user-triggered only; it is not built for bulk crawling.
- **Small golden set.** Only 4 of 12 planned cases (3 phones, 1 TV) are captured; the sneaker,
  apparel and other TV cases are `pending`, so those rules are tested mainly on synthetic,
  real-shaped fixtures.
