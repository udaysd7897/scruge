# Cross-Platform Product Matcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A locally-run web app: paste an Amazon.in link → per platform (Flipkart+Croma for phones/TVs, Flipkart+Myntra for sneakers/apparel) show In stock / Out of stock / Not listed (plus Possible match / Couldn't check), with links and a one-line reason.

**Architecture:** Pure, fixture-tested core (`normalize` → `extract` → `matcher`) turns raw platform data into canonical records and decisions. Thin `sources/` adapters fetch raw data (plain HTTP for Flipkart/Myntra, Apify for Amazon/Croma, with an on-disk cache). `pipeline` runs platforms concurrently and yields events; `server` streams them over SSE to one static HTML page.

**Tech Stack:** Python ≥3.11 via `uv`, FastAPI + uvicorn, httpx (async), beautifulsoup4, rapidfuzz, anthropic (optional), pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-11-11-product-matcher-design.md` — read it before any task; section numbers (§) below refer to it.

## Global Constraints

- Runs locally only; one command: `./run.sh` → serves `http://localhost:8000`.
- `APIFY_KEY` env var required for Amazon/Croma; `ANTHROPIC_API_KEY` optional — app must fully work without it.
- Apify actors: Amazon `junglee~amazon-crawler` (input `{"categoryOrProductUrls":[{"url":...}],"maxItemsPerStartUrl":1,"scrapeProductDetails":true}`); Croma `sian.agency~croma-product-scraper` (input `{"keywords":[q],"scrapeMode":"detail","sort":"relevance","maxResults":10}`). Endpoint: `POST https://api.apify.com/v2/acts/<actor>/run-sync-get-dataset-items?timeout=<s>` with header `Authorization: Bearer $APIFY_KEY`. Never put the key in URLs or logs.
- Never attempt to bypass bot protection (no TLS impersonation, no captcha solving). A block is reported as `BLOCKED` → "Couldn't check".
- Direct HTTP headers: `User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36`, `Accept-Language: en-IN,en;q=0.9`, follow redirects.
- Timeouts: Apify-backed platform 90 s, direct-HTTP platform 20 s.
- Never use `rapidfuzz.fuzz.token_set_ratio` (scores subset titles 100); use `token_sort_ratio`.
- A wrong match is worse than "Not listed": when in doubt → `AMBIGUOUS` ("Possible match – verify").
- UI state labels exactly: `In stock`, `Out of stock`, `Not listed`, `Possible match – verify`, `Couldn't check`.
- Tests never hit the network; all platform tests run on fixtures in `tests/fixtures/`.

## Review Focus

1. **Amazon short/tracking links** (`https://amzn.in/d/abc`, `https://www.amazon.in/Samsung-.../dp/B0GL8GXNTS/ref=sr_1_1?crid=...`) → resolve to canonical `https://www.amazon.in/dp/<ASIN>`; non-Amazon URL → friendly error. Tests in Task 6.
2. **Lookalikes and accessories in search results** (Flipkart "BlackZone BZ S26 Ultra", "back camera lens glass protector samsung galaxy s26 ultra") → vetoed, never matched. Tests in Task 4.
3. **Adjacent model returned when exact one absent** (Croma "samsung galaxy s24" → only S26 Ultra) → `NONE` → "Not listed". Test in Task 5.
4. **Blocked page served with HTTP 200** (Amazon `bm-verify` meta-refresh page; tiny HTML; "Access Denied") → `BLOCKED`, not `EMPTY`. Tests in Task 6.
5. **Variant-only difference** (same family, 256 GB vs 512 GB; Black vs Sky Blue) → storage vetoed; colour handled by §6.6 preference. Tests in Task 5.

---

## File Structure

```
pyproject.toml            deps + pytest config (asyncio_mode=auto)
run.sh                    uv sync && uv run uvicorn app.server:app --port 8000
README.md                 how to run, env vars, architecture sketch
docs/ELI5.md              deliverable: matching explained to a 5-year-old
app/models.py             all dataclasses/enums shared across modules
app/normalize.py          pure string→value normalisers
app/extract.py            raw platform data → Canonical; category detection
app/matcher.py            vetoes, score, decide, status mapping
app/queries.py            query ladder
app/sources/http.py       async fetch + FetchStatus classification
app/sources/apify.py      Apify run-sync client with disk cache
app/sources/amazon.py     URL resolve + source product
app/sources/flipkart.py   search links + product page → Candidate
app/sources/croma.py      search → Candidates
app/sources/myntra.py     search → Candidates
app/llm.py                optional Claude tie-break
app/pipeline.py           orchestrates one check, yields events
app/server.py             FastAPI: static page + SSE endpoint
static/index.html         single-page UI
tests/fixtures/           captured real responses
tests/test_*.py           one per module
scripts/golden.py         golden-set runner; scripts/golden.json cases
```

---

### Task 1: Project skeleton, fixtures, shared models

**Files:**
- Create: `pyproject.toml`, `run.sh`, `.gitignore` (`.venv/`, `.cache/`, `__pycache__/`), `app/__init__.py`, `app/sources/__init__.py`, `app/models.py`, `tests/fixtures/*`, `tests/test_models.py`

**Interfaces:**
- Produces (`app/models.py`):
  - `class Category(str, Enum)`: `PHONE="phone"`, `TV="tv"`, `SNEAKER="sneaker"`, `APPAREL="apparel"`, `UNSUPPORTED="unsupported"`
  - `class Platform(str, Enum)`: `FLIPKART`, `CROMA`, `MYNTRA` (values lowercase names)
  - `class FetchStatus(str, Enum)`: `OK`, `EMPTY`, `BLOCKED`, `ERROR`
  - `class Decision(str, Enum)`: `MATCH`, `AMBIGUOUS`, `NONE`
  - `class Outcome(str, Enum)`: `IN_STOCK="In stock"`, `OUT_OF_STOCK="Out of stock"`, `NOT_LISTED="Not listed"`, `POSSIBLE="Possible match – verify"`, `COULDNT_CHECK="Couldn't check"`
  - `@dataclass class Canonical`: `brand: str|None`, `family: str|None`, `model_code: str|None`, `ram_gb: int|None`, `storage_gb: int|None`, `screen_in: int|None`, `colour: str|None` (official name, as given), `base_colour: str|None`, `style_code: str|None`, `product_type: str|None`, `pack_count: int = 1`, `ean: str|None`, `title: str = ""`
  - `@dataclass class Candidate`: `platform: Platform`, `url: str`, `title: str`, `canon: Canonical`, `in_stock: bool|None`, `price: int|None = None`, `variant_group: str|None = None`
  - `@dataclass class SourceProduct`: `url: str`, `asin: str`, `title: str`, `image: str|None`, `category: Category`, `canon: Canonical`, `missing_required: list[str]`
  - `@dataclass class PlatformResult`: `platform: Platform`, `outcome: Outcome`, `url: str|None`, `reason: str`, `colour_fallback_note: str|None = None`

- [ ] **Step 1:** `git init` in `/Users/sid/scruge`; create `pyproject.toml` (`requires-python=">=3.11"`, deps above, dev deps `pytest`, `pytest-asyncio`; `[tool.pytest.ini_options] asyncio_mode="auto"`), `.gitignore`, `run.sh` (executable). Run `uv sync`. Expected: `.venv` created, no errors.
- [ ] **Step 2:** Copy fixtures from `/private/tmp/claude-501/-Users-sid-scruge/9894d44e-ef13-4970-bb5d-fc2f36f1d80c/scratchpad/probe/` into `tests/fixtures/`: `amz_apify.json`, `croma_apify.json`, `fk_s26_512blk.html`, `fk_pdp.html`, `fk_s26.html`, `fk_search.html`, `my_search.html`, and `gunzip -c amz_s26.html > tests/fixtures/amazon_bm_verify.html` (the bot-challenge page). This directory is temporary — do this first.
- [ ] **Step 3: Write failing test** `tests/test_models.py::test_outcome_labels` asserting `Outcome.POSSIBLE.value == "Possible match – verify"` and `Outcome.COULDNT_CHECK.value == "Couldn't check"`, and `Canonical().pack_count == 1`; `test_fixtures_present` asserting all 8 fixture files exist.
- [ ] **Step 4:** Run `uv run pytest tests/test_models.py -v` → FAIL (no module).
- [ ] **Step 5:** Implement `app/models.py` as listed. Run tests → PASS.
- [ ] **Step 6: Commit** `git add -A && git commit -m "chore: scaffold project, fixtures, shared models"`

---

### Task 2: Normalisers

**Files:** Create `app/normalize.py`, `tests/test_normalize.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `norm_brand(s: str|None) -> str|None`
  - `norm_family(s: str|None) -> str|None` — lowercase tokens; drops `5g 4g`, years, parentheticals; `+`→`plus`; keeps qualifiers `pro max ultra plus fe lite mini neo edge fold flip`
  - `parse_ram_storage(s: str) -> tuple[int|None, int|None]`
  - `parse_gb(s: str|None) -> int|None` (`"12GB"`, `"512 GB"`, `"1 TB"`→1024)
  - `screen_inches(s: str|None) -> int|None` — accepts `"55 inch"`, `"139 cm (55 inch)"`, `"138.71 cm"`, `"6.88"`(float string from Croma); cm÷2.54, snap to {24,32,40,43,50,55,65,75,85,98} (phones' small sizes returned rounded, not snapped, when < 20)
  - `model_base(code: str|None) -> str|None`
  - `split_style_code(code: str|None) -> tuple[str|None, str|None]`
  - `colour_key(s: str|None) -> str|None` — lowercase, collapse spaces (exact-name comparison for phones/TVs)
  - `base_colour(s: str|None) -> str|None` — one of 15: black white grey navy blue red green yellow orange pink purple brown beige maroon multi
  - `clean_ean(s: str|None) -> str|None` — digits only; valid length (8/12/13/14) + GS1 check digit, else None
  - `is_accessory(title: str) -> bool`
  - `distinctive_words(title: str, brand: str|None) -> set[str]`

- [ ] **Step 1: Write failing tests** (one test function per normaliser):
```python
assert norm_brand("SAMSUNG") == "samsung"; assert norm_brand("Mi") == "xiaomi"
assert norm_family("Galaxy S26 Ultra 5G") == norm_family("galaxy s26 ultra") == "galaxy s26 ultra"
assert norm_family("Galaxy S26+") == "galaxy s26 plus"
assert norm_family("Galaxy S26") != norm_family("Galaxy S26 FE")
assert parse_ram_storage("Samsung Galaxy S26 Ultra 5G (Sky Blue, 12GB RAM, 512GB Storage)") == (12, 512)
assert parse_ram_storage("8 GB RAM | 256 GB ROM") == (8, 256)
assert parse_ram_storage("12GB + 512GB") == (12, 512)
assert parse_ram_storage("256 GB + 8 GB") == (8, 256)          # smaller is RAM
assert parse_ram_storage("8GB RAM + 8GB Virtual RAM, 128GB") == (8, 128)
assert parse_ram_storage("(1 TB, 16GB RAM)") == (16, 1024)
assert screen_inches("139 cm (55 inch)") == 55; assert screen_inches("138.71 cm") == 55
assert screen_inches("164 cm") == 65; assert screen_inches("6.88") == 7
assert model_base("SM-S948BZKCINS") == model_base("SM-S948B/DS") == model_base("SM-S948B") == "SM-S948"
assert model_base("KD-55X80L") == "KD-55X80L"
assert split_style_code("DV2789-100") == ("DV2789", "100")
assert colour_key("BLACK") == colour_key("Black"); assert colour_key("Titanium Black") != colour_key("Black")
assert base_colour("Navy Blue") == "navy"; assert base_colour("White/Black-Volt") == "white"
assert base_colour("Onyx Black") == "black"; assert base_colour("Charcoal") == "grey"
assert clean_ean("8806097852605N") == "8806097852605"; assert clean_ean("8806097852606") is None
assert is_accessory("Gello Back Camera Lens Glass Protector for Samsung Galaxy S26 Ultra 5G")
assert is_accessory("SeriousShoppers Samsung S26 Ultra Panel with Logo Back")
assert not is_accessory("Samsung Galaxy S26 Ultra 5G (Black, 512 GB)")
assert distinctive_words("Puma Men Essentials Logo Slim Fit Polo T-shirt Black", "puma") == {"essentials", "logo", "slim", "fit"}
```
- [ ] **Step 2:** `uv run pytest tests/test_normalize.py -v` → FAIL.
- [ ] **Step 3:** Implement `app/normalize.py`. Brand alias map and colour synonym table are module-level dicts (builder fills; must satisfy tests). `model_base`: Samsung `^SM-[A-Z]\d{3}`; otherwise uppercase, strip spaces and `/DS`-style suffixes. Accessory keywords include `case cover glass protector tempered screen guard back panel skin charger cable adapter lens ring strap`.
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5: Commit** `feat: add normalisers`

---

### Task 3: Extraction to canonical records + category detection

**Files:** Create `app/extract.py`, `tests/test_extract.py`

**Interfaces:**
- Consumes: Task 1 models, Task 2 normalisers.
- Produces:
  - `REQUIRED: dict[Category, list[str]]` = phone `["brand","family","ram_gb","storage_gb","colour"]`; tv `["brand","family","screen_in"]` (family satisfied by `model_code` too); sneaker `["brand","family","base_colour"]`; apparel `["brand","product_type","base_colour"]` (§6.4 table)
  - `detect_category(breadcrumbs: str|None, title: str) -> Category` — breadcrumbs first (`"Smartphones"`, `"Televisions"`, shoes/sneakers, `T-shirts`/`Polos`/`Jerseys`), else title keywords
  - `missing_required(c: Canonical, cat: Category) -> list[str]`
  - `from_amazon(item: dict) -> SourceProduct` (Apify amazon-crawler item)
  - `from_croma(item: dict) -> Candidate`
  - `from_flipkart_page(html: str, url: str) -> list[Candidate]` — JSON-LD Product + specs table rows (`Model Number`, `Model Name`, `RAM`, `Internal Storage`, `Color`, `Display Size`); `variant_group` = the `itm…` id from url
  - `from_myntra_search(html: str) -> list[Candidate]` — `window.__myx` → `searchData.results.products[]`; url = `https://www.myntra.com/` + `landingPageUrl`; `in_stock = any(i["available"] for i in inventoryInfo)`

- [ ] **Step 1: Write failing tests** using fixtures:
```python
# Amazon: B0GL8GXNTS
sp = from_amazon(item_with_asin("B0GL8GXNTS"))
assert sp.category == Category.PHONE
assert (sp.canon.brand, sp.canon.family, sp.canon.ram_gb, sp.canon.storage_gb, colour_key(sp.canon.colour)) == ("samsung","galaxy s26 ultra",12,512,"sky blue")
assert sp.missing_required == []
# Croma: item_id 327249
c = croma_item("327249")
assert (c.canon.model_code, c.canon.ram_gb, c.canon.storage_gb, c.canon.ean, c.in_stock) == ("SM-S948BZKCINS",12,512,"8806097852605",True)
assert c.canon.family == "galaxy s26 ultra"
# Flipkart product page
[fk] = from_flipkart_page(read("fk_s26_512blk.html"), "https://www.flipkart.com/samsung-galaxy-s26-ultra-5g-black-512-gb/p/itmf4799d3841c43?pid=MOBHKGAPBMXRGGXZ")
assert (fk.canon.model_code, fk.canon.ram_gb, fk.canon.storage_gb, colour_key(fk.canon.colour), fk.in_stock, fk.price, fk.variant_group) == ("SM-S948B",12,512,"black",True,159999,"itmf4799d3841c43")
# Myntra
ms = from_myntra_search(read("my_search.html"))
assert len(ms) == 50 and ms[0].canon.brand == "nike" and ms[0].canon.base_colour == "white" and ms[0].in_stock is True
assert ms[0].url.startswith("https://www.myntra.com/sports-shoes/nike/")
# Category + missing
assert detect_category(None, "Puma Men Polo T-shirt") == Category.APPAREL
assert detect_category(None, "Sony Bravia 139 cm (55 inches) 4K Ultra HD Smart LED Google TV K-55XR70") == Category.TV
assert detect_category(None, "Prestige Pressure Cooker 5L") == Category.UNSUPPORTED
assert missing_required(Canonical(brand="samsung", family="galaxy s26 ultra", ram_gb=12, colour="Black"), Category.PHONE) == ["storage_gb"]
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Amazon field sources: brand ← `brand`/`Brand Name`; ram ← `RAM Memory Installed`; storage ← `Memory Storage Capacity`; colour ← `Colour`; then `variantAttributes` (`Size: "12GB + 512GB"`), then title regex. Family = title text before the first `(` minus brand, normalised. Croma family ← `specs["Model Series"]`. Flipkart family ← specs `Model Name`. Specs table parse: strip tags to text tokens, value = token following the label token.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: extract canonical records from all platforms`

---

### Task 4: Vetoes

**Files:** Create `app/matcher.py` (veto part), `tests/test_matcher_veto.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: `veto(src: Canonical, cand: Candidate, cat: Category) -> str|None` — returns a short reason (`"storage 256≠512"`, `"accessory"`, `"brand"`, `"family"`, `"model code"`, `"ram"`, `"screen size"`, `"style code"`, `"colour"`, `"pack count"`, `"type"`, `"distinctive words"`) or None. Compares a field only if both sides have it (§6.4). Phone/TV colour is **not** a veto here (handled in Task 5).

- [ ] **Step 1: Write failing tests:**
```python
src = Canonical(brand="samsung", family="galaxy s26 ultra", ram_gb=12, storage_gb=512, colour="Black")
assert veto(src, cand(family="galaxy s26 ultra", ram_gb=12, storage_gb=256, colour="Black"), PHONE) == "storage 256≠512"
assert veto(src, cand(family="galaxy s26 plus", ram_gb=12, storage_gb=512), PHONE) == "family"
assert veto(src, cand(brand="blackzone", family="bz s26 ultra", title="BlackZone BZ S26 Ultra (White, 128 GB)"), PHONE) == "brand"
assert veto(src, cand(title="Gello Back Camera Lens Glass Protector samsung galaxy s26 ultra 5g", brand="samsung"), PHONE) == "accessory"
assert veto(src, cand(family="galaxy s26 ultra", ram_gb=12, storage_gb=512, colour="Sky Blue"), PHONE) is None   # colour not vetoed for phones
assert veto(src, cand(family="galaxy s26 ultra", model_code="SM-S948B", ram_gb=12, storage_gb=512), PHONE) is None
tv = Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55)
assert veto(tv, cand(brand="sony", family="bravia 3", model_code="K-65S30", screen_in=65), TV) is not None
shoe = Canonical(brand="nike", family="air max 270", base_colour="white", style_code="DV2789-100")
assert veto(shoe, cand(brand="nike", family="air max 270", base_colour="black"), SNEAKER) == "colour"
polo = Canonical(brand="puma", product_type="polo", base_colour="black", title="Puma Men Essentials Logo Slim Fit Polo Black")
assert veto(polo, cand(brand="puma", product_type="polo", base_colour="black", title="Puma Men Graphic Regular Fit Polo Black"), APPAREL) == "distinctive words"
assert veto(polo, cand(brand="puma", product_type="polo", base_colour="black", title="PUMA Essentials Logo Slim Fit Polo T-Shirt", pack_count=2), APPAREL) == "pack count"
```
(`cand(**kw)` is a test helper building a `Candidate` with a `Canonical`.)
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement `veto` per §6.4 (Jaccard ≥ 0.5 on `distinctive_words`, plus all source model-line tokens present). **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add hard vetoes`

---

### Task 5: Scoring, decision, colour preference, outcome mapping

**Files:** Modify `app/matcher.py`; Create `tests/test_matcher_decide.py`

**Interfaces:**
- Consumes: Task 4 `veto`, Task 3 `missing_required`.
- Produces:
  - `score(src: Canonical, cand: Candidate, cat: Category) -> float` (weights §6.5: 0.40 model_code-base or EAN exact, 0.25 exact `colour_key`, 0.20 `token_sort_ratio/100`, 0.15 required-present ratio)
  - `@dataclass Match`: `decision: Decision`, `candidate: Candidate|None`, `reason: str`, `colour_fallback: bool = False`, `survivors: list[Candidate]`
  - `decide(src: SourceProduct, cands: list[Candidate]) -> Match` — §6.6 incl. phone/TV colour preference and "source missing required → never better than AMBIGUOUS"
  - `to_result(platform: Platform, match: Match, statuses: list[FetchStatus], src_colour: str|None) -> PlatformResult` — §6.7 mapping; `reason` strings like `"Matched on model SM-S948B, 12GB/512GB, Black"` / `"Not listed: 8 candidates checked, none had 512GB"`; colour fallback note `"Not available in Black; showing Sky Blue"`
  - `decide` is synchronous and never calls an LLM: unresolved ties → `AMBIGUOUS` with `reason="tie"` and `survivors` filled. `resolve_tie(m: Match, chosen: Candidate|None) -> Match` turns a tie into `MATCH(chosen)` (only if `chosen in m.survivors`) or leaves it `AMBIGUOUS`. Task 7 calls the LLM and then `resolve_tie`. A tie is never resolved when the source is missing a required field.

- [ ] **Step 1: Write failing tests** with the Croma fixture (5 S26 Ultra variants) and synthetic candidates:
```python
src = phone_src(colour="Black", ram=12, storage=512)          # SourceProduct, family galaxy s26 ultra
m = decide(src, croma_candidates())
assert m.decision == MATCH and m.candidate.url.endswith("/p/327249") and not m.colour_fallback
# colour preference: same-colour OOS beats other-colour in-stock
m = decide(src, [c(colour="Black", in_stock=False), c(colour="Sky Blue", in_stock=True)])
assert m.decision == MATCH and m.candidate.canon.colour == "Black"
r = to_result(FLIPKART, m, [OK], "Black"); assert r.outcome == Outcome.OUT_OF_STOCK
# colour fallback when source colour absent
m = decide(phone_src(colour="Titanium Black"), [c(colour="Sky Blue", in_stock=True)])
assert m.colour_fallback; r = to_result(FLIPKART, m, [OK], "Titanium Black")
assert r.outcome == Outcome.IN_STOCK and r.colour_fallback_note == "Not available in Titanium Black; showing Sky Blue"
# adjacent model only (Croma 'S24' search returned S26 Ultras)
m = decide(phone_src(family="galaxy s24", ram=8, storage=256), croma_candidates())
assert m.decision == NONE
assert to_result(CROMA, m, [OK, OK, EMPTY], "Black").outcome == Outcome.NOT_LISTED
assert to_result(CROMA, m, [OK, BLOCKED], "Black").outcome == Outcome.COULDNT_CHECK
# source missing required → never MATCH
m = decide(phone_src(storage=None), croma_candidates()); assert m.decision == AMBIGUOUS
assert to_result(CROMA, m, [OK], "Black").outcome == Outcome.POSSIBLE
# tie without tiebreak → AMBIGUOUS (two apparel listings equally good)
assert decide(polo_src(), [polo_c("a"), polo_c("b")]).decision == AMBIGUOUS
```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement per §6.5–6.7. Flipkart stock: `InStock`, `LimitedAvailability`, `OnlineOnly` → in stock (extract sets `in_stock` already; mapping lives in `from_flipkart_page`). **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add scoring, decision and outcome mapping`

---

### Task 6: Source adapters (HTTP, Apify, Amazon, Flipkart, Croma, Myntra)

**Files:** Create `app/sources/{http,apify,amazon,flipkart,croma,myntra}.py`, `tests/test_sources.py`

**Interfaces:**
- Consumes: Task 3 extractors.
- Produces:
  - `async def fetch(client: httpx.AsyncClient, url: str) -> tuple[FetchStatus, str]` — `BLOCKED` on 403/429/503/529, on bodies containing `bm-verify`, `Access Denied`, `Robot Check`, `captcha`, or HTML < 3000 bytes with a meta refresh; `ERROR` on exceptions/timeouts/other non-2xx.
  - `async def run_actor(client, actor: str, payload: dict, timeout_s: int = 90) -> tuple[FetchStatus, list[dict]]` — cache at `.cache/apify/<sha1(actor+json(payload, sort_keys))>.json`; cache hit skips network; `[]` → `EMPTY`; missing `APIFY_KEY` → `ERROR`.
  - `resolve_amazon_url(client, url: str) -> str` (raises `ValueError("Please paste an Amazon.in product link")`) — follows redirects for `amzn.in`/`amzn.to`; extracts ASIN from `/dp/`, `/gp/product/`; returns `https://www.amazon.in/dp/<ASIN>`
  - `async def get_source(client, url) -> SourceProduct`
  - `async def flipkart_search(client, q) -> tuple[FetchStatus, list[str]]` (product URLs, deduped, max 10) and `async def flipkart_candidates(client, q) -> tuple[FetchStatus, list[Candidate]]` (search + fetch each product page, concurrency 3)
  - `async def croma_candidates(client, q) -> tuple[FetchStatus, list[Candidate]]`
  - `async def myntra_candidates(client, q) -> tuple[FetchStatus, list[Candidate]]` — URL `https://www.myntra.com/<slugified q>?rawQuery=<urlencoded q>`

- [ ] **Step 1: Write failing tests** using `httpx.MockTransport` serving fixtures:
```python
assert classify(200, read("amazon_bm_verify.html")) == BLOCKED
assert classify(403, "<H1>Access Denied</H1>") == BLOCKED
assert resolve_amazon_url_sync("https://www.amazon.in/Samsung-Galaxy/dp/B0GL8GXNTS/ref=sr_1_1?crid=X") == "https://www.amazon.in/dp/B0GL8GXNTS"
assert resolve_with_redirect("https://amzn.in/d/abc" -> 301 Location .../dp/B0GL8GXNTS) == "https://www.amazon.in/dp/B0GL8GXNTS"
with pytest.raises(ValueError): resolve_amazon_url_sync("https://www.flipkart.com/x/p/itm1")
st, urls = await flipkart_search(mock(fk_s26.html), "samsung galaxy s26 ultra"); assert st == OK and any("pid=MOBHZ7T3MPKXGDXJ" in u for u in urls)
st, cs = await myntra_candidates(mock(my_search.html), "nike running shoes"); assert st == OK and len(cs) == 50
st, cs = await croma_candidates(apify_mock(croma_apify.json), "samsung galaxy s24"); assert st == OK and len(cs) == 5
# cache: second identical run_actor call makes zero HTTP requests
```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5: Live smoke (manual, costs ~1 Apify run):** `uv run python -c "import asyncio,httpx; from app.sources.amazon import get_source; ..."` on `https://www.amazon.in/dp/B0GL8GXNTS` → prints category phone, 12/512, Sky Blue. Save the Apify response into `tests/fixtures/` if new.
- [ ] **Step 6: Commit** `feat: add platform source adapters`

---

### Task 7: Query ladder, LLM tie-break, pipeline

**Files:** Create `app/queries.py`, `app/llm.py`, `app/pipeline.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: Tasks 3, 5, 6.
- Produces:
  - `ladder(src: SourceProduct, platform: Platform) -> list[str]` (§6.3; dedupe, skip rungs with missing parts)
  - `async def llm_tiebreak(src: SourceProduct, survivors: list[Candidate]) -> Candidate|None` — returns None if no `ANTHROPIC_API_KEY`; model `claude-sonnet-5-5`; prompt lists source + each survivor's canonical fields as JSON; asks for the index of the identical product or `none`; only indices of given survivors accepted
  - `PLATFORMS: dict[Category, list[Platform]]` — phone/tv → [FLIPKART, CROMA]; sneaker/apparel → [FLIPKART, MYNTRA]
  - `async def check(url: str) -> AsyncIterator[dict]` — events: `{"type":"source","data":SourceProduct-as-dict}`, `{"type":"progress","platform":p,"message":"Searching Croma…"}`, `{"type":"result","data":PlatformResult-as-dict}`, `{"type":"error","message":...}`, `{"type":"done"}`. Unsupported category → `error` with "This product isn't a phone, TV, sneaker or T-shirt/polo/jersey." then `done`. Platforms run concurrently (`asyncio.as_completed`), each wrapped in its timeout (Global Constraints); timeout → `Couldn't check`. Per platform: walk the ladder; stop at first rung whose decision is MATCH or AMBIGUOUS; collect statuses of all rungs tried. On `AMBIGUOUS` with `reason=="tie"`, call `llm_tiebreak` then `resolve_tie`. (Spec §6.2's optional LLM *extraction* fallback is deliberately not built in v1 — structured fields + regex cover the fixtures; add only if the golden set shows extraction gaps.)

- [ ] **Step 1: Write failing tests** with monkeypatched adapters:
```python
assert ladder(s26_black_512_src_with_model("SM-S948B"), FLIPKART)[0] == "SM-S948B"
assert ladder(s26_src_no_model, CROMA) == ["samsung galaxy s26 ultra 12gb 512gb black", "samsung galaxy s26 ultra"]
events = [e async for e in check(URL)]   # amazon→phone; flipkart returns fk_s26_512blk candidate; croma returns fixture
assert events[0]["type"] == "source" and events[-1]["type"] == "done"
results = {e["data"]["platform"]: e["data"] for e in events if e["type"] == "result"}
assert results["flipkart"]["outcome"] == "In stock" and "pid=MOBHKGAPBMXRGGXZ" in results["flipkart"]["url"]
assert results["croma"]["outcome"] == "In stock" and results["croma"]["url"].endswith("/p/327249")
# croma adapter raises TimeoutError → "Couldn't check"; unsupported category → error event, no result events
assert await llm_tiebreak(src, survivors) is None   # with ANTHROPIC_API_KEY unset
```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add query ladder, tie-break and pipeline`

---

### Task 8: Server and UI

**Files:** Create `app/server.py`, `static/index.html`, `tests/test_server.py`

**Interfaces:**
- Consumes: Task 7 `check`.
- Produces: `GET /` → `static/index.html`; `GET /api/check?url=<amazon url>` → `text/event-stream`, one `data: <json event>\n\n` per event.

- [ ] **Step 1: Write failing test** (`fastapi.testclient`, `check` monkeypatched to yield 3 fixed events): response content-type starts with `text/event-stream` and body contains the three `data:` lines in order; `GET /` returns 200 and contains `<input`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement server (`StreamingResponse`). Implement `index.html` with vanilla JS `EventSource`:
  - input + "Check" button; disables while running
  - source summary block: image, title, category, attribute chips (e.g. `Samsung · Galaxy S26 Ultra · 12GB/512GB · Black`), and `Couldn't read: <field>` when `missing_required` non-empty
  - one card per platform appearing immediately in a "searching…" state, replaced by its result
  - five visually distinct states (colour + icon + label): In stock green ✓ with "View on <platform>" link; Out of stock amber ⏸ with link; Not listed grey ✕ no link; Possible match – verify blue ? with link; Couldn't check red ⚠ no link
  - reason line under each card; colour-fallback note shown prominently when present
  - error event → message banner
- [ ] **Step 4:** Run tests → PASS. **Step 5:** `./run.sh`, open `http://localhost:8000`, paste `https://www.amazon.in/dp/B0GL8GXNTS`; verify cards appear progressively and states render. (Uses live Apify — ~2 runs.)
- [ ] **Step 6: Commit** `feat: add web UI with streaming results`

---

### Task 9: Golden set, ELI5 doc, README

**Files:** Create `scripts/golden.json`, `scripts/golden.py`, `docs/ELI5.md`, `README.md`

**Interfaces:**
- Consumes: Task 7 `check`.
- Produces: `uv run python scripts/golden.py [--live]` — for each case runs `check`, compares outcomes, prints per-category/per-platform precision (wrong MATCH counted as error) and coverage, exits non-zero on any wrong match. Default mode uses the Apify cache only (no new spend); `--live` allows network.

- [ ] **Step 1:** Assemble `golden.json` with ~20 cases `{url, category, expected: {platform: outcome}}`: ≥5 phones (incl. a storage sibling and an FE/Plus/Ultra sibling), ≥5 TVs (incl. 55" vs 65" of one series), ≥5 sneakers (two colourways of one model), ≥5 apparel (incl. a multi-pack). Expected outcomes are verified by hand on each site.
- [ ] **Step 2:** Implement `golden.py`; run with `--live` once to fill the cache. Expected: script prints the table; fix any wrong MATCH by adjusting normalisers/vetoes (with a new unit test each) until wrong matches = 0.
- [ ] **Step 3:** Write `docs/ELI5.md` (~1 page, §9): toy-shop analogy; the four "must be the same" checks per category; "if we're not sure, we say so"; the S26 Ultra Black 512 walk-through (8 Flipkart candidates → 1 survives); why "Couldn't check" ≠ "Not listed".
- [ ] **Step 4:** Write `README.md`: prerequisites (`uv`, `APIFY_KEY`, optional `ANTHROPIC_API_KEY`), `./run.sh`, how to run tests and golden set, architecture diagram (text), known limitations (§11).
- [ ] **Step 5:** `uv run pytest -q` → all pass. **Step 6: Commit** `docs: add golden set, ELI5 explainer and README`
