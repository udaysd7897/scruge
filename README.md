# Cross-platform product matcher

Paste an Amazon.in product link. For each competing store, the app says whether that store sells the
**exact same product** and whether you can buy it now: **In stock**, **Out of stock** (with link),
**Not listed**, **Possible match – verify**, or **Couldn't check**.

| Category | Stores checked | Identity rests on |
|---|---|---|
| Smartphones | Flipkart, Croma | brand + model line + RAM + storage (+ colour) |
| Televisions | Flipkart, Croma | brand + screen size + model number |
| Sneakers | Flipkart, Myntra | brand style code / model number; else model name + colour set + gender + photo |
| T-shirts, polos, jerseys | Flipkart, Myntra | brand style code; else name + colour + neck + gender + pack + photo |

**How the matching works, in plain English: [docs/ELI5.md](docs/ELI5.md)**, written for any graduate,
with worked examples. The research behind the design is in [`reports/`](reports/).

## Run

Prerequisite: [uv](https://docs.astral.sh/uv/) (installs Python ≥ 3.11 and the dependencies).

```bash
./run.sh     # uv sync + uvicorn → http://127.0.0.1:8000
```

| Env var | Meaning |
|---|---|
| `APIFY_KEY` | Apify token. Used for **Croma** (always) and as the **Amazon fallback** when the plain product page is blocked or unreadable. Without it (and no cached answer) those checks fail with a clear message. |
| `ANTHROPIC_API_KEY` | Optional. Enables (a) the **photo check** that confirms fashion listings without a shared style code, and (b) the AI **tie-break** between equally good listings. Without it those cases stay "Possible match – verify". |
| `APIFY_OFFLINE=1` | Cache-only mode: a missing Apify cache entry is an error, never a paid call. Used by tests/scripts; leave it **unset** when running the app normally. |
| `LOG_LEVEL` | Log level for `logs/app.log` (default `INFO`; `DEBUG` also logs every successful fetch). |

Results stream to the page per store as each finishes (Server-Sent Events).

## Architecture / flow

```
browser (static/index.html)
   │ GET /api/check?url=…    SSE: progress → source → result × N → done
   ▼
app/server.py → app/pipeline.py: check(url)
  1. sources/amazon.py  normalise the link to amazon.in/dp/<ASIN>, then read it:
       a. a cached Apify answer for this product (free, richest)
       b. plain GET of the product page → sources/amazon_page.py (title, breadcrumb, spec rows,
          variant picker, MRP, images, bestseller links)                                   (free)
       c. Apify junglee~amazon-crawler, only if the page is blocked/unreadable      (paid, cached)
       → extract.from_amazon → SourceProduct {category, canonical record}
  2. T-shirts with a Puma style code: brandsite.official_name → the official product name
  3. per store, concurrently (90 s budget each):
       queries.ladder(src, store)  rung by rung; stop at the first MATCH / Possible
         (Flipkart fashion with a style code: a brand/colour-filtered "code search" rung first)
         → flipkart.py | croma.py | myntra.py → extract.from_* → Candidates
       matcher.decide: hard checks → identity (style codes) → score → MATCH / AMBIGUOUS / NONE
         (fabric-different listings set aside as closest options)
       tie            → llm.llm_tiebreak (optional)
       NEEDS_CONFIRM  → confirm.py: one-call photo check (vision.py) + MRP or manufacturer, 45 s cap
       matcher.to_result → PlatformResult {state, link, reason, closest options}
```

**Category** (`extract.amazon_category`) comes from what Amazon states, never from model-name lists:
breadcrumb → bestseller browse node → "Item Type Name" → spec fingerprint (phone: iOS/Android +
storage + under 350 g, with storage also taken from Apple's CAPACITY row, the variant picker or the
title; TV: HDMI / tuner / VESA / display-size rows) → title keywords → unsupported.

**Query ladder** (`app/queries.py`), the first rung that yields a match or close call wins:

- **Phones:** model code (not on Myntra) → brand + family + RAM + storage + colour (1 TB searched as "1 tb") → brand + family
- **TVs:** model code → brand + family/code + size + "inch" → brand + family
- **Sneakers:** brand + model name + colour → brand + style code / model number → brand + model name
- **T-shirts:** official name (+ colour) → Amazon Model Name + colour → brand + noun + colour ("leriya fashion t-shirt brown") → brand + type + colour + distinctive words → brand + 4 words

## Matching rules (summary; details in [docs/ELI5.md](docs/ELI5.md))

**Hard checks** (`matcher.veto`) reject a listing only when **both sides are known and differ**;
"unknown" never rejects. The score (identity code/EAN 0.40, exact colour 0.25, title similarity 0.20,
completeness 0.15) only **ranks** survivors. Listings within 0.15 of the best are a tie, unless
they're provably one product: same EAN, same model code, or (fashion) the same style in the same colour.

- **Phones:** accessory, brand, family, model code, RAM, storage. Colour is strict: the exact colour
  first. If the store doesn't have it, another colour is shown with a note. A colourless listing next
  to other colours is "Possible match".
- **TVs:** brand, family (series words may overlap), screen within 1 inch, model code as
  size + normalised code. Colour is ignored. Confirmed only when both sides show a model number.
- **T-shirts:**
  - Checks: category (not a watch or a shirt), gender, neck (round / V / collar / henley / mandarin /
    hooded), style code (trusted brands), base colour, pack count, distinctive title words.
  - **Fabric** is a soft check: "polyester" vs "pure cotton" is never a match, but the listing is
    shown as a closest option.
- **Sneakers:**
  - Checks: gender (Department / title / breadcrumb; conflicting signals = unknown), style code
    (trusted brands), **colour sets** ("Black and White" = "White, Black" ≠ "Grey, White"; sole words
    like "gum" ignored), distinctive words.
  - Indian short model numbers (`SM-734`) are read for brands whose codes aren't globally trusted.
- **Style-code identity** (`same_style`):
  - Codes are the same when they're equal ignoring case/space/-/_ (`528856_01` = `52885601`), when one
    is a prefix of the other (`BBMH9103A-09` ~ `BBMH9103A`), or when they share 4+ digit groups with
    no conflicting letter after them (`AUSK-04065-L` = `AUSKB-04065`; `BBMH9103A` ≠ `BBMH9103B`).
  - For trusted brands (Puma, Nike, Adidas, Reebok, Skechers, Asics, New Balance, Jockey, AUSK), a
    *different* code rejects the listing. For others, a different code proves nothing and the title
    words decide.
  - A short model number counts as proof only when the listing's own title prints it ("Sparx SM 734 | …").
- **No shared code** (all of Myntra, many Flipkart listings) → `confirm.py`:
  - **One** Claude vision call over the top 5 survivors, shuffled. The model fills an attribute table
    (T-shirts: neck, sleeve, colour, logo, stripes, print; sneakers: silhouette, panels, logo, upper
    colour, accents, sole, laces), then answers.
  - The code accepts the answer only when the table backs it: the pick has no "different", and every
    other candidate has one.
  - A photo match also needs **equal MRP or the same manufacturer** (same PIN + ≥ 80% of the address
    words), from Flipkart's product page or Myntra's.
  - Photo "none" → Not listed; unclear → Possible match.

### Result states

| State | Meaning |
|---|---|
| In stock / Out of stock | One listing, confidently the same product, with link and a "Matched on …" reason. Stock is a snapshot (Myntra: any size available). |
| Possible match – verify | Link shown, but identity or stock isn't proven (tie, missing attribute, unconfirmed, unreadable stock). |
| Not listed | Every search completed; nothing is the product. The reason names the most common rejection ("none had a round neck"). |
| Couldn't check | Blocked, errored or timed out. A failed fetch is **never** turned into "Not listed". |

**Closest options:** under "Not listed", up to 3 listings that passed every hard check are shown with
what differs. That means photo differences on at most half the attributes, none of them neck, colour
or cut, plus fabric-different listings. A wrong brand, gender or neck is never offered as "close".

## Data sources and cost

| Store | How | Cost / notes |
|---|---|---|
| Amazon.in (input) | Apify cache → plain HTTPS product page → Apify `junglee~amazon-crawler` | Page: free. Apify ≈ $0.005 per product, cached on disk. |
| Flipkart | Plain HTTPS: search page (top 10 links), each product page (JSON-LD, spec rows, price block for MRP, manufacturer row, image), variant pages of the top 3 hits (up to 12 more) | Free. 3 pages fetched at a time. |
| Croma | Apify `sian.agency~croma-product-scraper`, detail mode, **max 5 results** per search | ≈ $0.07 per result, so up to ≈ $0.35 per search. Cached; larger cached answers are reused. Direct access is bot-protected and isn't bypassed. |
| Myntra | Plain HTTPS search page (embedded `window.__myx` JSON); product page for the manufacturer during confirmation | Free. |
| Brand site (Puma) | in.puma.com search for the style code | Free. (nike.in blocks automated requests, so it isn't used.) |
| Anthropic | Photo check (one call per store) and tie-break (20 s cap), model `claude-sonnet-5-5` | Only with `ANTHROPIC_API_KEY`. |

**Retries and time limits:**

- Network errors and 429/5xx are retried with backoff: 3 tries of up to 20 s (pauses 1 s, 3 s).
- **Myntra** stalls on and off, so it gets 4 tries of 8 s (pauses 1, 2, 4 s).
- A real answer (page, 404, bot check) is never retried.
- Every store has a 90 s budget, and confirmation 45 s.
- A search that fails outright stops that store's ladder ("Couldn't check").
- If the budget runs out after a candidate was found, the candidate is kept.

## Logging

`logs/app.log` (plus stderr) records, per check:

- the Amazon read (cache / page / Apify, and the extracted fields)
- each query, with fetch status, candidate count and rejection reasons
- the decision per rung, the confirmation, and the final result per store

Set `LOG_LEVEL=DEBUG` to log every successful fetch too.

## Tests and ground truth

```bash
uv run pytest -q    # 246 tests, offline: saved real pages/responses in tests/fixtures/
```

Many tests are built from real pages that once failed (Puma, Jockey, AUSK, Leriya, Bacca Bucci,
Sparx, Nike Killshot, iPhone 17 Pro Max), so each bug stays fixed.

- **Hand-checked ground truth** (user-verified links): `docs/golden/tshirts_mockrun_2026-11-13.md`
  (10 T-shirts) and `docs/golden/sneakers_poc_2026-11-13.md` (3 sneakers).
- **Golden runner:** `scripts/golden.py` runs the real pipeline on `scripts/golden.json`. It prints
  precision (correct confident answers / all confident answers) and coverage. A confident answer
  pointing at a different product is printed loudly and exits non-zero.

```bash
uv run python scripts/golden.py                 # cache only: no network, no spend
uv run python scripts/golden.py --refresh-http  # re-fetch Flipkart/Myntra (free); Apify stays cached
uv run python scripts/golden.py --live          # live; spends Apify credit on cache misses
```

Caches live in `.cache/` (gitignored): `.cache/apify/` and golden replays in `.cache/golden/`.

## Known limitations

- **Amazon bot checks and Apify credit.**
  - Amazon sometimes serves bot-check pages to plain requests. The app then needs Apify credit, and
    never bypasses a bot check.
  - Croma always needs Apify. A 403 from Apify (exhausted credit or key) shows as "Couldn't check".
- **Photo-check consistency.** The same photo pair can get slightly different tables between runs.
  The table-must-back-the-answer rule turns disagreement into "Possible", not a wrong match.
- **Store search varies between calls.** Flipkart may not return a given listing every time. When an
  exact phone colour is missing from the results, the app may fall back to another colour (with a
  note). Opening the listing's sibling pages first is a planned improvement.
- **Brand-site name lookup is Puma only.** Other brands search with Amazon's own name words.
- **Codes that differ per store.** Some brands use a different code on each store; for trusted brands
  a different code rejects the listing, so a real listing could come back "Not listed".
- **Indian-brand code rules** (Sparx numbers, Bacca suffixes) come from a handful of products and
  could collide across a large catalogue.
- **Fragile scraping.** Flipkart/Myntra markup can change or start rate-limiting (shown as
  "Couldn't check").
- **Terms of use.** Amazon, Flipkart and Myntra restrict automated access. Use this low-volume and
  user-triggered only; it isn't built for bulk crawling.
- **Small golden set.** `scripts/golden.json` has 4 of 12 cases captured (3 phones, 1 TV); the rest
  are pending Amazon captures. Ground truth for fashion is the 13 hand-checked links in `docs/golden/`.
