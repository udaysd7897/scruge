# How the product matcher works

A plain-English guide to the search and matching algorithm. You don't need to know the codebase to
follow it; file names are given at the end of each section for readers who want to look closer.

---

## 1. The problem in one paragraph

You paste one Amazon.in product link. The app finds **the same product** on other Indian stores and
tells you, per store, whether it is **In stock**, **Out of stock** (with a link) or **Not listed**.

- Phones and TVs are looked up on **Flipkart** and **Croma**.
- Sneakers and T-shirts (including polos and jerseys) are looked up on **Flipkart** and **Myntra**.

"The same product" is strict:

- **Brand and model must always match.**
- **Phones** must match RAM and storage.
- **TVs** must match screen size.
- **Sneakers and T-shirts** must match colour.

A Galaxy S26 Ultra with 256 GB is a *different product* from the 512 GB one, even though the names
look alike.

The hard part is that every store describes the same product differently. Here is one Puma T-shirt
on three stores:

| Store | Title |
|---|---|
| Amazon | Puma Men Polyester Solid Regular Fit T-Shirt |
| Flipkart | PUMA M Train All Day ESSENTIAL Men Printed Round Neck Polyester Black T-Shirt |
| Myntra | Puma Train All Day Men Breathable Training Tee |

A simple "compare the titles" approach fails here. It would also happily match a lookalike T-shirt
with a near-identical title. So the app compares **facts** (brand, codes, sizes, colours), not words.

---

## 2. The big picture

Every check runs the same pipeline, once per store, in parallel:

```
Amazon link
   │
   ▼
1. Read the Amazon listing  ──► a "canonical record": brand, model, storage, colour, codes …
   │
   ▼
2. Search the store         ──► a "query ladder": most specific search first, broader ones after
   │
   ▼
3. Read every result        ──► the same kind of record for each listing found
   │
   ▼
4. Hard checks              ──► reject anything that is provably a different product
   │
   ▼
5. Rank and decide          ──► MATCH / POSSIBLE / NONE
   │
   ▼
6. Confirm (fashion only)   ──► photo check + price/manufacturer when there's no shared code
   │
   ▼
Result per store: In stock · Out of stock · Not listed · Possible match – verify · Couldn't check
```

The guiding rule throughout: **pointing at the wrong product is the worst outcome**. When the
evidence isn't strong enough, the app says "Possible match – verify" and shows its best guess,
rather than claiming a match.

---

## 3. Step 1: Reading the Amazon listing

### Getting the page

1. The app first fetches the Amazon product page directly, with a normal browser-like request.
2. If Amazon shows a bot check, or the page can't be read, the app falls back to
   **Apify's Amazon scraper** (a paid service, needs `APIFY_KEY`). Answers from Apify are cached on
   disk, so the same product isn't paid for twice.
3. The app **never tries to get around a bot check**. If both routes fail, the result is
   "Couldn't check".

### Working out the category

The category decides which stores to search and which rules apply. The app trusts what Amazon
itself says, in this order:

1. **The breadcrumb** ("Electronics › Mobiles › Smartphones").
2. **The bestseller category** Amazon files the product under.
3. **"Item Type Name"** in the spec table ("Smartphone", "Sneaker").
4. **A spec fingerprint**, used when the page has none of the above:
   - **Phone:** a phone operating system (iOS/Android), plus a storage size, plus weight under 350 g.
     The storage can come from the spec table, Apple's "CAPACITY" row, the size selected on the page
     ("256 GB") or the title. Some iPhone pages lack the usual storage row.
   - **TV:** TV-only spec rows such as HDMI ports or a VESA mount.
5. **Keywords in the title**, as a last resort.

Anything else (an accessory, a phone case, a watch) is "unsupported". The app doesn't guess.

### The canonical record

Every listing, Amazon's and each store's, is turned into the same structured record, so that facts
can be compared directly:

| Field | Used for | Example |
|---|---|---|
| brand | all | `samsung`, `levis` (apostrophes and dots removed) |
| model / family | all | `galaxy s26 ultra`, `killshot 2 leather`, `stride eclipse` |
| RAM, storage | phones | 12 GB / 512 GB (1 TB is 1024 GB) |
| screen size, model code | TVs | 55", `K-55S30` |
| colour, base colour | all | "Sail/Gum Yellow/Midnight Navy" → base colours {white, navy} |
| style code | fashion | Puma `52885601`, Nike `432997-107`, Sparx `SM-734` |
| gender | fashion | men / women / kids / unisex |
| neck, product type | T-shirts | round / V / collar (polo) / henley / mandarin / hooded |
| pack count | T-shirts | "Pack of 2" = 2 |
| MRP, manufacturer | fashion | ₹1,799; "Aryan Apparels … Manesar 122051" |

Amazon-specific details that matter:

- **Style code:**
  - Read from "Style Number", "Item model number", "Manufacturer Part Number" or "Model Number",
    in any capitalisation.
  - Seller stock codes that contain a size ("LINING-PLUS-HS-PKT-NVY- 5XL") are ignored.
  - For sneakers, a short model number ("SM-734", "SM 734") also counts, but only for brands whose
    codes aren't globally trusted. "NB 574" on New Balance is a model name, not a code.
- **Colour:** read from the spec table, or from the variant picker at the top of the page
  ("Colour: Cosmic Orange"). For some iPhones the picker is the only place it appears.
- **Gender:** taken from "Department", the title and the breadcrumb. If they disagree (title says
  "Boys", breadcrumb says "Men's Shoes"), gender is treated as **unknown** rather than picking one.
- **Brand:**
  - When Amazon's record has no brand at all (rare, sparse records), the title's first word is used
    as a **guess**.
  - A guess can never reject a listing whose brand starts with it: a guessed "red" still fits
    "Red Tape".
- **Neck:** read from the title first, then the neck/collar rows. Rows that contradict each other
  are treated as unknown.
- **MRP:** the struck-through list price; if there's no discount, the selling price.

*Code: `app/sources/amazon.py`, `app/sources/amazon_page.py`, `app/extract.py`, `app/normalize.py`.*

---

## 4. Step 2: Searching each store

### Where the data comes from

| Store | How | What it gives |
|---|---|---|
| Flipkart | plain web requests | search page; each product page's structured data, spec table, price block (MRP), manufacturer, image |
| Myntra | plain web requests | search results embedded in the page (name, brand, colour, gender, MRP, image); product page for the manufacturer |
| Croma | Apify's Croma scraper (5 results per search) | specs, EAN barcode, stock |

### The query ladder

The app doesn't send one search. It tries a **ladder** of searches, the most specific first, and
**stops as soon as one gives an answer**. Specific searches find the exact product; broader ones are
a safety net when a store titles things differently.

| Category | Ladder (examples) |
|---|---|
| Phones | model code (not on Myntra) → `apple iphone 17 pro max 1 tb cosmic orange` → `apple iphone 17 pro max` |
| TVs | model code → `sony bravia 3 55 inch` → `sony bravia 3` |
| Sneakers | `bacca bucci stride eclipse white` → `bacca bucci bbmh9103a-09` → `bacca bucci stride eclipse` |
| T-shirts | official name (Puma: looked up on in.puma.com from the style code) → Amazon's model name → `leriya fashion t-shirt brown` → brand + type + colour + distinctive words → brand + 4 words |

Details that came from real failures:

- **Storage in TB:** written as "1 tb", not "1024gb". Flipkart finds nothing for "1024gb".
- **Brand + product noun + colour** ("leriya fashion t-shirt brown") is always tried for T-shirts.
  Small brands often only show up for this plain search.
- **Flipkart code search:** when a T-shirt or sneaker has a style code, the first rung is a
  brand-filtered (and colour-filtered) Flipkart listing.
  - Flipkart's text search doesn't index style codes, but its image file names often contain them.
  - The app scans two result pages and opens only the cards whose image names contain the code's
    digits.
- **Flipkart variants:** for the top 3 search hits, the app also opens their colour/storage variant
  pages (up to 12 more). The exact variant often isn't in the search results.

*Code: `app/queries.py`, `app/sources/flipkart.py`, `app/sources/myntra.py`, `app/sources/croma.py`,
`app/brandsite.py`.*

---

## 5. Step 3: Reading each result

Each store listing is turned into the same canonical record as Amazon's. Store quirks are handled
here:

- **Flipkart's two titles:**
  - The structured-data title for fashion is auto-generated ("PUMA Printed Men Round Neck Black
    T-Shirt").
  - The title shown on the page is the brand's own ("PUMA M Train All Day ESSENTIAL …").
  - The app uses the shown title, but only if it starts with the product's brand, so a recommended
    product's title is never picked up.
- **Flipkart sneakers:**
  - Each size can be its own listing, with the size in the title ("(White , 9)"). That tail is
    removed.
  - Flipkart files shoes under category "shoe", which is mapped to sneakers.
- **Flipkart MRP:** comes from the product's own price block (one per page).
- **Flipkart manufacturer:** comes from the "Name and address of the Manufacturer" row.
- **Myntra:** shows **no brand style code anywhere**. Matching there always relies on the name,
  colour, gender, MRP, manufacturer and photo.

---

## 6. Step 4: Hard checks (rejecting different products)

Each listing goes through a list of **hard checks**. Failing any one removes it.

**The most important rule:** a check only rejects when **both sides are known and differ**. Unknown
never rejects. If Amazon doesn't say the neck type, the neck check can't reject anything; if a
listing has no colour, the colour check can't reject it. That keeps "we couldn't read it" from
turning into "it doesn't exist".

| Check | Applies to | Rejects when … |
|---|---|---|
| accessory | all | the listing is a case, cover, protector, charger … |
| brand | all | brands differ (a guessed brand still fits a longer brand that starts with it) |
| model line | phones, TVs | "galaxy s26 ultra" vs "galaxy s26 plus" |
| model code | phones, TVs | TVs compare screen size + series ("K-55S30" vs "K-65S30") |
| RAM, storage | phones | 8 GB ≠ 12 GB; 256 GB ≠ 1 TB |
| screen size | TVs | differs by more than 1 inch |
| category | T-shirts | the store files it as something else (a watch, slides, a shirt) |
| gender | fashion | men's vs women's vs kids' (unisex fits both) |
| neck | T-shirts | round vs V vs collar (a "collared T-shirt" is a polo) |
| style code | fashion, trusted brands only | Nike `432997-107` vs `432997-070` (a different colourway) |
| colour | fashion | T-shirts: base colour. Sneakers: the **set** of colours (below) |
| pack count | T-shirts | single vs pack of 2 |
| distinctive words | fashion | the titles share too few model-specific words (below) |

### How colour is compared for sneakers

Shoe colours are often several colours, written differently on each store. So the app compares
**sets of base colours**:

- "Black and White" = "White, Black" = {black, white}. Order doesn't matter.
- Sole words are dropped: "Sail/**Gum** Yellow/Midnight Navy" = {white, navy}. "Gum" describes the
  sole, not the shoe; "sail" is an off-white.
- If both sides list two or more colours, the sets must be equal: "Black, White" ≠ "Grey, White".
- If one side lists a single colour, it must be one of the other's colours: "White" fits
  {white, navy}.
- "Multicolor" names no colour, so it counts as unknown.

### The distinctive-words check

Generic words are removed first: brand, gender, product type, sizes, colours, filler such as
"cotton", "regular", "casual", "round neck". Whatever is left is model-specific ("stride eclipse",
"train all day", "batman outline").

- If both titles still have **two or more** such words, they must overlap by **at least half**.
- If either title is too generic to compare (one word or none), this check does **not** reject. The
  listing goes on, and the confirmation step decides.
- A **shared brand style code overrides the words**: three wildly different Puma titles with the
  same code `52885601` are the same product.

*Code: `app/matcher.py` (`veto`), `app/normalize.py`.*

---

## 7. Step 5: Ranking and deciding

### Proving identity with codes

A **brand style code** is the strongest evidence that two fashion listings are the same product. Two
codes count as the same style when:

- they're equal after removing spaces, dashes, underscores and slashes (`528856_01` = `52885601`), or
- one is the other plus a suffix (`BBMH9103A-09` vs `BBMH9103A`), or
- they share the same 4+ digit number groups, and no conflicting letter follows those digits
  (`AUSK-04065-L` = `AUSKB-04065`).

Two codes do **not** count as the same style when a different letter follows the same digits.
`BBMH9103A` vs `BBMH9103B`, or `9930-0105-WHITE` vs `9930-0105-LTDML`, are colour siblings.

**Trusted vs untrusted brands:**

- For brands whose codes are their own and identical on every store (Puma, Nike, Adidas, Reebok,
  Skechers, Asics, New Balance, Jockey, AUSK), a *different* code rejects the listing.
- For other brands, store "codes" are often seller stock numbers. An equal code still proves the
  match, but a different one proves nothing, and the title words decide.

**Short model numbers (Indian brands):**

- A shared number on its own is only a hint: Amazon `SM-734` vs Flipkart `SD0734G` might also be
  `SX-734`.
- It becomes proof when **the listing's own title prints the same model number**: "Sparx **SM 734** |
  Stylish …".

### Scoring

The listings that survived the hard checks are scored, only to **rank** them:

| Part | Weight | Meaning |
|---|---|---|
| identity | 0.40 | same model code or same EAN barcode |
| colour | 0.25 | exactly the same colour text |
| title | 0.20 | how similar the titles are (word-order-insensitive fuzzy match) |
| completeness | 0.15 | how many required fields the listing shows |

### The decision

- **MATCH:** one clear winner that is proven to be the product.
- **Possible match – verify:** the app has a candidate but can't prove it. For example:
  - Amazon is missing a required field.
  - The listing doesn't show its colour.
  - A TV has no model number on Amazon.
  - A fashion listing has no shared style code (it goes to the confirmation step).
  - Two listings score within **0.15** of each other (a tie).
- **NONE:** nothing survived the hard checks → "Not listed".

Ties have a few escape hatches:

- **Duplicates:** listings that share an EAN, a model code, or (fashion) the same style in the same
  colour are the same product listed twice. The app picks the in-stock, cheapest one.
- **Proven sneaker copies:** when every tied listing is proven to be the same model, the one with
  exactly Amazon's colours wins. Several sellers listing "Sparx SM 734, White" count as one product.
- **AI tie-break:** if none of the above settles it, an optional Claude call (needs
  `ANTHROPIC_API_KEY`) can pick between them. If it can't, the result stays "Possible match".

**Phone colour fallback:** if a store has the exact phone but not in Amazon's colour, the app shows
the same phone in another colour, with the note "Not available in Cosmic Orange; showing Deep Blue".
If a listing's colour can't be read, it's shown as "Possible match" instead. TV colour is ignored.

*Code: `app/matcher.py` (`decide`, `score`, `same_style`), `app/llm.py`.*

---

## 8. Step 6: Confirming fashion matches without a code

Myntra never shows style codes, and many Flipkart listings don't either. A name match alone is
**never** enough to call a T-shirt or sneaker a match. Otherwise any black round-neck T-shirt of the
same brand would "match". So those candidates go through a confirmation step.

### The one-call photo check

1. Take the top 5 surviving listings, equal-MRP ones first. For sneakers, Flipkart's per-size copies
   of one shoe are merged into one slot.
2. **Shuffle** them. The model must not learn that "the first one is usually right".
3. Send **one** Claude vision request: the Amazon photo plus the candidate photos, all resized to
   save tokens.
4. The model must first fill in an **attribute table** for every candidate, then answer:

   | T-shirts | Sneakers |
   |---|---|
   | neck/collar, sleeve, colour, logo, stripes/panels, print/graphic | silhouette, panels, logo, upper colour, accents, sole, laces |

   Each cell is "same", "different" or "unclear".
5. The app **doesn't just trust the answer**; it checks the table backs it up:
   - "Candidate k is the match" is accepted only if k has no "different" and at least one "same",
     **and every other candidate has at least one "different"**.
   - "None of them" is accepted only if **every** candidate has a named "different".
   - Anything else counts as "unclear".

### Then a second, independent signal

A photo match alone still isn't enough. The app also needs **one of**:

- **the same MRP** as Amazon, or
- **the same manufacturer**: same 6-digit PIN code and at least 80% of the address words.
  Flipkart shows the manufacturer on the product page; for Myntra the app opens the product page.

| Photo check says | Price or maker agrees? | Result |
|---|---|---|
| this one matches | yes | **MATCH** ("Matched on name, MRP, manufacturer and photo") |
| this one matches | no | Possible match – "Photo matches, but neither MRP nor manufacturer confirms it" |
| none of them | – | **Not listed** (with closest options, below) |
| unclear / error / no API key / took more than 45 s | – | stays Possible match |

*Code: `app/confirm.py`, `app/vision.py`.*

---

## 9. What you see

| Status | Meaning |
|---|---|
| **In stock** / **Out of stock** | a confident match, with its link and what it matched on ("Matched on style JE9356, Grey") |
| **Possible match – verify** | the best candidate, with the reason it isn't proven; please check the link |
| **Not listed** | the store was searched properly and doesn't have this product |
| **Couldn't check** | the store blocked us, errored or took too long. **Never** reported as "Not listed": "we didn't look" isn't "it isn't there". |

### Closest options

When the answer is "Not listed" but some listings passed every hard check, up to 3 of them are shown
under it, each with what's different:

```
Myntra   Not listed
         Closest options (same brand, gender, colour and cut; not the exact product):
         • Jockey Men Black Solid Round Neck Pure Cotton T-shirt · fabric differs
         • ADIDAS Round Neck Sports T-shirt · logo, stripes differ
```

Two kinds of listing qualify:

1. **Photo differences.** The photo check said "different design", and the differences are minor:
   - at most half the attributes differ, and
   - none of them is a hard-check attribute.

   A listing whose photo shows a different neck, colour, silhouette or upper colour is a different
   product, not a "close" one, so it isn't listed.
2. **Fabric differences.** Both titles name a fabric and they don't overlap: "Polyester … Microfiber"
   vs "Pure Cotton".
   - Such a listing is never a match, but it passed every hard check, so it's shown as close.
   - Blends ("cotton blend", "cotton rich") and titles without a fabric word are never treated as
     different.

If nothing passed the hard checks, nothing is shown: a wrong brand, gender or neck is never offered
as "close".

---

## 10. Reliability: retries, time limits, honesty

- **Retries:**
  - Network errors and "busy" answers (429, 5xx) are retried with a pause.
  - Most requests get 3 tries, 20 s each, with 1 s and 3 s pauses.
  - Myntra stalls on and off, so it gets **4 short tries of 8 s** (pauses of 1, 2 and 4 s). A fresh
    try usually gets through quickly.
  - A real answer (a page, a 404, a bot check) is never retried. Retrying a bot check doesn't help
    and would hammer the store.
- **Time limits:**
  - Each store has 90 s for the whole search.
  - If a search fails outright even after retries, the remaining searches for that store are
    skipped and the store shows "Couldn't check".
  - If time runs out after a candidate was already found, that candidate is kept and shown.
- **Partial failures:**
  - If some Flipkart product pages fail to load, a match among the ones that did load still counts.
  - "No match" in that case becomes "Couldn't check", because the unread page might have been the
    product.
- **Cost:**
  - Croma is capped at 5 results per search, since Apify charges per result.
  - Apify answers are cached on disk.
  - The photo check is one request per store, with small images.

---

## 11. Worked examples (real runs, 2026-11-13)

**Puma T-shirt, three different titles.**
- Amazon's style number `52885601` matches Flipkart's style code `52885601`. That's a **MATCH**,
  despite completely different titles.
- On Myntra (no code), the official name "Train All Day" from in.puma.com finds the listing.
- Photo + MRP + manufacturer then confirm it.

**iPhone 17 Pro Max 1 TB, Cosmic Orange.**
- The colour appears only in Amazon's variant picker; the app reads it from there.
- Flipkart is searched as "1 tb", not "1024gb".
- The 256 GB / 512 GB / 2 TB listings are rejected on storage, and the iPhone 17 Pro on model line.

**Bacca Bucci Stride Eclipse, Black/White (sneaker).**
- The model name comes from Amazon's Model Name, not the generic title "Men Leather Sneaker Shoes".
- Flipkart has four Stride Eclipse colourways. The colour sets reject Grey/White, Black/Blue and
  White/Brown.
- A different Bacca model ("Matrix") is rejected on title words.
- Flipkart's code `BBMH9103A` is Amazon's `BBMH9103A-09` minus the suffix, so it's a MATCH.

**Sparx SM-734, White.**
- Flipkart sellers use codes like `SD0734G`, `A1SD0734G-WHGY` and `I0071328`.
- The number alone isn't proof, but the title "Sparx **SM 734** | …" is.
- Of the White and White/Grey listings, the exact White wins.

**Jockey AM74 polyester round-neck T-shirt.**
- V-neck, polo and henley listings are rejected on neck.
- The remaining round-neck T-shirts are **pure cotton**, so the result is **Not listed**.
- Those cotton T-shirts are shown as closest options ("fabric differs").

---

## 12. Known limits

- **Photo check consistency:** the same photo pair can get slightly different tables on different
  runs. The table-must-back-the-answer rule turns disagreement into "unclear" (Possible), not into a
  wrong match.
- **Store search varies between calls:** Flipkart may or may not show a given listing. When the
  exact phone colour is missing from the results, the app may fall back to another colour. Opening
  the listing's sibling pages first is a planned improvement.
- **Blocked sources:**
  - Amazon bot checks, and Apify running out of credit, show as "Couldn't check".
  - Brand sites that block automated requests (nike.in) aren't used. The app never works around a
    block.
- **Code rules for Indian brands** (Sparx-style numbers, Bacca suffixes) were derived from a few
  products and could collide across a large catalogue.
- **Small test set:** the ground truth so far is 10 T-shirts and 3 sneakers (`docs/golden/`).

---

## 13. Where things live

| File | Role |
|---|---|
| `app/pipeline.py` | runs the steps per store, query ladder loop, time limits |
| `app/sources/*` | Amazon (page + Apify), Flipkart, Myntra, Croma, fetch with retries |
| `app/extract.py` | turns each store's page into the canonical record |
| `app/normalize.py` | brands, colours, colour sets, gender, neck, fabric, sizes |
| `app/queries.py` | the query ladder |
| `app/matcher.py` | hard checks, style-code identity, scoring, decision, result text |
| `app/confirm.py`, `app/vision.py` | one-call photo check, price/manufacturer confirmation, closest options |
| `app/llm.py` | optional AI tie-break |
| `reports/` | the research behind the design |
| `tests/` | about 250 tests, many built from real pages that once failed |
