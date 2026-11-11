# Cross-Platform Product Matcher — Design

Date: 2026-11-11
Source assignment: `/Users/sid/scruge/founding_backend_engineer_assignment.md`
Background research: `/Users/sid/scruge/reports/Cross platform product matching.md`

## 1. Intent

A take-home for a Founding Backend Engineer role. A reviewer pastes one Amazon.in product link and the app tells them, per competing platform, whether the **exact same product** is sold there and whether it can be bought now. The reviewer is judging how well we handle messy real-world data, so **trustworthiness of each answer matters more than coverage or polish**.

Deliverables:
1. A locally-run web app (paste link → results).
2. A short "explain it like I'm 5" document describing how matching works.

## 2. Scope (from the assignment)

| Category | Platforms searched | Must match (in addition to brand + model) |
|---|---|---|
| Smartphones | Flipkart, Croma | RAM and storage |
| Televisions | Flipkart, Croma | Screen size |
| Sneakers | Flipkart, Myntra | Colour |
| T-shirts, polos, jerseys | Flipkart, Myntra | Colour |

Per-platform result states (each rendered visibly differently):
- **In stock** — same product found, buyable. Show link.
- **Out of stock** — same product found, not buyable now. Show link.
- **Not listed** — the platform does not sell this product. No link.

## 3. Goals, non-goals, anti-goals

**Goals**
- High precision: when we say "In stock"/"Out of stock", it is the same brand, model and variant.
- Honest uncertainty: failures and ambiguity are surfaced, not hidden.
- Explainable: each result says *why* (which attributes matched, or why nothing matched).
- One-command local run.

**Non-goals**
- Public hosting / deployment.
- Price comparison, price history, alerts, accounts.
- Categories or platforms beyond the table above.
- Scale/throughput beyond one reviewer using it interactively.

**Anti-goals (failure even if it "works")** — ranked by the user:
1. A confident wrong answer (e.g. "In stock" pointing at the 256GB variant when the input is 512GB). A wrong match is worse than an honest "Not listed".
2. A long silent wait. Checks take ~30–60 s total; the UI must show progress and render each platform as soon as it is ready.
3. Crashing on unexpected input (short `amzn.in` links, tracking params, unsupported categories, non-Amazon URLs).

## 4. Decided by the user

- **Runs locally only.** Starts with one command, opens on `localhost`. Requires `APIFY_KEY` in the environment (already configured on the user's machine).
- **Stack:** Python + FastAPI backend; a single static HTML/JS page as frontend (no build step).
- **LLM:** Claude used *only* as an optional tie-breaker; app must fully work without `ANTHROPIC_API_KEY`.
- **Output page (approved playback):**
  - Input box + button.
  - Source product summary at top: title, image, detected category, extracted attributes (e.g. "Samsung · Galaxy S26 Ultra · 12GB/512GB · Black").
  - One card per platform in one of the states, each visually distinct, with link where applicable.
  - A one-line "why" on each card (e.g. "Matched on model SM-S948B, 12GB/512GB, Black" or "Not listed: 8 candidates checked, none had 512GB").
  - A 4th state **"Couldn't check"** when a platform blocked us / errored — never reported as "Not listed".
  - Unsupported category → clear message, no platform cards.
  - (Ambiguous result after tie-breaking, see §6.6 → shown as **"Possible match – verify"** with link.)
- **Matching algorithm** as described in §6 (agreed in conversation).
- **Phones/TVs colour (user chose "strict colour, fallback only if absent"):** the exact colour must match. Example: Amazon = 12/512 Black; Flipkart has 12/512 Black (out of stock) and 12/512 Blue (in stock) → answer is **Out of stock**, linking the Black one. Only if the platform lists **no** variant in the source colour may a same-model/same-variant listing in another colour be used (see §6.6 for how that is shown).
- **Apparel identity (user chose "brand + colour + distinctive-word overlap"):** T-shirts/polos/jerseys match only when brand, product type, base colour and pack count agree **and** the distinctive product words overlap strongly (§6.4). If two or more listings still look equally good → "Possible match – verify".

## 5. Data sources (verified live on 2026-11-11)

| Platform | Access | What we get |
|---|---|---|
| **Amazon.in (input)** | Apify actor `junglee/amazon-crawler` (plain HTTP is blocked by a bot challenge). Pass the product URL; `scrapeProductDetails: true`. | `asin`, `title`, `brand`, `attributes[]` (e.g. `RAM Memory Installed`, `Memory Storage Capacity`, `Colour`, `Model Year`), `variantAttributes` (e.g. `Size: "12GB + 512GB"`), `inStock`, `price`, images, `breadCrumbs`. Note: model number and EAN were **absent** for the phones tested. |
| **Flipkart** | Plain HTTPS GET with a normal browser User-Agent + `Accept-Language: en-IN`. | Search `https://www.flipkart.com/search?q=<q>` → product links `/<slug>/p/itm<id>?pid=<PID>`. Product page → JSON-LD `Product` (`name`, `brand.name`, `color`, `sku`=Flipkart PID, `offers.price`, `offers.availability`) + specs table rows (`Model Number`, `Model Name`, `RAM`, `Internal Storage`, `Color`, display size for TVs). Variants of one product share the `itm` id and differ by `pid`. Searching by model code (e.g. `SM-S948B`) returned exactly the right family. |
| **Croma** | Apify actor `sian.agency/croma-product-scraper` (direct HTTP is blocked by Akamai; do **not** attempt to bypass). Input: `keywords`, `scrapeMode: "detail"`, `maxResults` ≈ 10. | `productTitle`, `url`, `brand`, `price`, `in_stock`, `ean` (may contain junk chars, e.g. trailing `N`), `specs` dict (`Model Series`, `Model Number` e.g. `SM-S948BZKCINS`, `RAM`, `Internal Storage`, `Screen Size in Inches`, `Brand Color`, `Color`). ~8 s per run. Cost on free plan ≈ $0.05/run + per-item fee. |
| **Myntra** | Plain HTTPS GET of search URL `https://www.myntra.com/<slug>?rawQuery=<q>`. | Embedded `window.__myx` JSON → `searchData.results.products[]` with `productId`, `productName`, `brand`, `primaryColour`, `articleType.typeName`, `price`, `mrp`, `inventoryInfo[]` (`available` per size), `landingPageUrl`. |

Search results are noisy on every platform (lookalike brands like "BlackZone S26 Ultra", accessories/cases, adjacent models). The matcher must assume this.

## 6. Matching algorithm

### 6.1 Category detection
From Amazon `breadCrumbs` / product type first; fall back to title keywords. Map to one of `phone | tv | sneaker | apparel | unsupported`. Apparel = T-shirts, polos, jerseys only.

### 6.2 Canonical record (both source and each candidate)
Fill each field from the most reliable source available: **structured field → title regex → (optional) LLM extraction with evidence quoted from source text**.

| Category | Fields |
|---|---|
| phone | brand, model family, base model code, RAM (GB), storage (GB), colour name |
| tv | brand, model code, model family, screen size (inches), colour (ignored) |
| sneaker | brand, model line, style code (if any), base colour, full colour name |
| apparel | brand, product type (tee/polo/jersey), base colour, pack count, key style words |

Normalisation:
- Brand: lowercase + alias map (e.g. `mi`→`xiaomi`; "Apple" covers iPhone).
- Model family: lowercase, strip `5g/4g`, years, marketing tails; **keep qualifiers** (`pro, max, ultra, plus, +, fe, lite, mini, neo, edge, fold, flip`). Family equality requires identical qualifier sets (S26 ≠ S26+ ≠ S26 Ultra ≠ S26 FE).
- RAM/storage: parse `8 GB RAM | 256 GB ROM`, `(8GB+256GB)`, `12GB + 512GB`, `1 TB`→1024. Ignore "virtual/extended RAM".
- Screen size: cm ÷ 2.54, snap to nearest standard size (24, 32, 40, 43, 50, 55, 65, 75, 85, 98). Cross-check digits in model code.
- Model code: uppercase, strip spaces/`/DS`; compare on base (Samsung `SM-S948BZKCINS`→`SM-S948`; Nike `DV2789-100` → model `DV2789`, colourway `100`).
- Colour: phones/TVs compare official colour name case-insensitively. Sneakers/apparel map to ~15 base colours via a hand-built synonym table (black, white, grey, navy, blue, red, green, yellow, orange, pink, purple, brown, beige, maroon, multi); multi-colour names take the first colour.
- EAN (Croma only): digits only, validate length + check digit; usable only if Amazon also has one.

### 6.3 Query ladder (per platform; stop at the first rung that yields relevant candidates)
1. Model code (if known).
2. Brand + family + key attribute(s) (e.g. "samsung galaxy s26 ultra 512gb black").
3. Brand + family.
4. Apparel/sneakers: brand + type/model line + colour.

### 6.4 Hard vetoes (a candidate is dropped if any applies)
A field is compared only when both sides have a value. Vetoes:
- Brand differs. Accessory / lookalike detected (case, cover, glass, back panel, charger; brand not equal).
- Family differs (incl. qualifier mismatch). Base model code differs when both present.
- Phone: RAM differs; storage differs.
- TV: screen size differs by > 1 inch.
- Phone/TV colour: handled as a *preference with fallback*, not a plain veto — see §6.6.
- Sneaker/apparel: style code differs (when both present); base colour differs; apparel pack count differs; apparel product type differs.
- Sneakers without a style code on either side, and all apparel: **distinctive-word veto.** Distinctive words = title tokens after removing brand, colour words, product-type words (t-shirt, tee, polo, jersey, shoes, sneakers…), gender words, generic marketing words (men, women, pure cotton, regular fit is *kept*: fit is distinctive), sizes and pack counts. Require Jaccard overlap of distinctive-word sets ≥ 0.5 **and** that every model-line token on the source side (e.g. "air max 270", "rs-x", "essentials") appears in the candidate. *(Thresholds are the builder's starting point; tune on the golden set.)*

**Required fields** (my call — a confident MATCH needs these present on **both** sides):

| Category | Required |
|---|---|
| phone | brand, family, RAM, storage, colour |
| tv | brand, family or model code, screen size |
| sneaker | brand, model line, base colour |
| apparel | brand, product type, base colour |

**Source missing a required field** (my call): if the Amazon listing itself lacks a required field after all extraction steps, the app still searches, but no platform result can be better than **"Possible match – verify"**, and the source summary shows "Couldn't read: <field>". This prevents the 256 GB-vs-512 GB failure when the source attribute is unknown.

### 6.5 Scoring (ranks survivors only; never accepts on its own)
```
score = 0.40*model_code_or_ean_exact + 0.25*exact_colour_name
      + 0.20*title_similarity(token_sort_ratio) + 0.15*required_fields_present
```
(`token_set_ratio` must not be used: it scores subset titles 100.)

### 6.6 Decision
- 0 survivors → NONE.
- 1 survivor with all required fields present → MATCH.
- ≥2 survivors and top − second ≥ 0.15 → MATCH(top).
- Otherwise tie-break: exact colour name → (optional) one Claude call choosing among survivors or "none", given side-by-side extracted attributes → MATCH or AMBIGUOUS.
- Missing a required field on the only survivor → AMBIGUOUS.
- **Phone/TV colour preference** (user decision): first restrict survivors to those whose colour name equals the source colour (case-insensitive, after alias normalisation e.g. "Titanium Black" ≠ "Black"). If ≥1 such survivor exists, decide among them only; the other-colour siblings are ignored even if in stock. If **none** of the platform's survivors has the source colour, decide among the other-colour survivors and mark the result **colour fallback**: the card shows the normal In stock / Out of stock state *plus* a prominent note "Not available in <source colour>; showing <other colour>" (my call on presentation). If several other colours remain, prefer an in-stock one, then the closest base colour.
- For Flipkart, multiple PIDs under one `itm` are separate variants; each is a candidate.

### 6.7 Status mapping
Each platform tracks fetch status per request: `OK | EMPTY | BLOCKED | ERROR`.
- MATCH → stock from the matched variant:
  - Flipkart: `offers.availability` ∈ {InStock, LimitedAvailability, OnlineOnly} → In stock; other schema.org values → Out of stock.
  - Croma: `in_stock`.
  - Myntra: any size with `available: true` → In stock.
- AMBIGUOUS → "Possible match – verify" (with link).
- NONE and all rungs ran OK/EMPTY → **Not listed**.
- NONE and any rung BLOCKED/ERROR → **Couldn't check**.

## 7. Runtime behaviour
- Platforms run concurrently. The UI receives results incrementally (streaming or polling) and shows per-platform progress ("searching Croma…").
- Reasonable per-platform timeout (~90 s for Apify-backed, ~20 s for direct HTTP), then "Couldn't check".
- Input handling: accept `amazon.in/dp/…`, `/gp/product/…`, long URLs with tracking params, and `amzn.in`/`amzn.to` short links (resolve redirect). Non-Amazon or unparsable → friendly error. Unsupported category → friendly message.
- Small on-disk cache of Apify responses keyed by query to save credits during development/demo.
- Polite request volume to Flipkart/Myntra (low concurrency, a handful of requests per check).

## 8. Quality bar / evaluation
- Unit tests for normalisers and veto rules using saved real responses. Existing captures to copy into the repo's test fixtures: `/private/tmp/claude-501/-Users-sid-scruge/9894d44e-ef13-4970-bb5d-fc2f36f1d80c/scratchpad/probe/` — `croma_apify.json` (Croma Apify, 5 S26 Ultra variants, detail mode), `amz_apify.json` (Amazon Apify, 4 Samsung phones), `fk_s26_512blk.html`, `fk_pdp.html` (Flipkart product pages), `fk_search.html`, `fk_s26.html` (Flipkart search pages), `my_search.html` (Myntra search). This is a temp directory — copy early.
- **Apify budget** (my call): free tier ≈ $5/month. Every Apify response is captured once to disk and replayed offline in tests and golden-set runs; live runs only when capturing new fixtures or for the final demo. Flipkart/Myntra are free to fetch but also captured for repeatability.
- A small golden set (target ~20 Amazon links across the 4 categories, deliberately including near-variants: other storage, other colour, FE/Plus/Ultra, 55" vs 65") with expected per-platform outcomes; a script reports precision and coverage. Rules tuned for precision.

## 9. ELI5 document
Plain-language explanation (≈1 page) of the matching: "same brand, same name, same important detail, and if we're not sure we say so", using a toy-shop analogy and the S26 Ultra example. Lives in the repo as Markdown.

## 10. Left to the builder
- Project layout, module boundaries, HTTP client library, HTML parsing library.
- Exact streaming mechanism (SSE vs polling).
- Visual styling of cards (must keep the states clearly distinct).
- Exact regexes, colour synonym table contents, accessory keyword list.
- Cache format and location.
- Which Claude model to use for the tie-breaker (latest available).

## 11. Known risks / open facts
- Amazon data for some products lacks model number/EAN; matching then relies on family + attributes.
- Flipkart/Myntra HTML structure may change or start rate-limiting; failures must surface as "Couldn't check".
- Croma search returns adjacent models when the exact one is absent (seen: "S24" → only S26 Ultra) — vetoes must catch this.
- Apify free-tier credit (~$5/month) bounds how much live testing we can do; caching mitigates.
