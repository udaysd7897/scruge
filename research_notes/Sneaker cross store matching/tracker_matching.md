# How sneaker platforms and trackers match the same shoe across stores

Scope: the matching keys, normalization rules and fallbacks used by sneaker marketplaces, trackers and open-source tools, applied to matching Amazon.in listings to Flipkart and Myntra.

Research budget: about 18 tool calls. StockX and GOAT have not published any engineering write-ups on matching that I could find. Indian trackers such as BuyHatke and PriceHistory do not document their matching logic. So much of the practical guidance below is labelled as inference.

## Q1. What key do sneaker platforms and trackers match on, and how do they normalize SKUs?

### Takeaway
The main cross-marketplace key in the sneaker ecosystem is the manufacturer style code (Nike/Jordan format `DD1391-100`: a 6-character model code plus a 3-digit colourway code). GTIN/UPC sits one level lower, per size. Open-source tools such as Sneaks-API do almost no normalization: they send the style code as a free-text search query and trust the top hit. A careful service should normalize the code and then verify it against the returned record.

### Cited Findings
- Sneaks-API (druv5319) "scrapes StockX for sneaker information and then asynchronously scrapes Stadium Goods, Goat, and Flight Club". StockX is the base record. The public function `getProductPrices` "takes in a style ID" (example `FY2903`, an adidas code) and returns a price map across sites. — [Sneaks-API README](https://github.com/druv5319/Sneaks-API)
- Sneaks-API's GOAT scraper concatenates `shoe.styleID` unmodified into an Algolia query (`index product_variants_v2`, `query=' + shoe.styleID`). It takes `json.results[0].hits[0]` as the match without checking that the hit's SKU equals the input. It does no dash/space replacement, no case folding and no trimming. — [goat-scraper.js](https://raw.githubusercontent.com/druv5319/Sneaks-API/master/scrapers/goat-scraper.js)
- The Flight Club scraper works the same way: `query=" + shoe.styleID + "&hitsPerPage=1` against `product_variants_v2_flight_club`, and the top hit is accepted with no verification or URL-encoding. — [flightclub-scraper.js](https://raw.githubusercontent.com/druv5319/Sneaks-API/master/scrapers/flightclub-scraper.js)
- The Apify Wethenew scraper documents `styleCode` as "Manufacturer style code / SKU (join key across marketplaces)" (example `AQ9129-101`). It gives no normalization rules. — [Apify Wethenew scraper](https://apify.com/lulzasaur/wethenew-scraper.md)
- The SoleSearch API has lookups by SKU and by internal product_id. Its docs note that SKU formats vary by manufacturer and can collide across brands, so they recommend product_id or adding the brand to the query. — [SoleSearch API (via search summary)](https://www.github.com/SoleSearch-Demos/api)
- The `shoe-scrapper` npm package takes a SKU such as `CU0449-601` and returns per-size offers with GTIN-12 (UPC-A) values. GTIN is size-level, while the style code is model+colour-level. — [shoe-scrapper on npm](https://www.npmjs.com/package/shoe-scrapper)
- Nike style codes are typically 9 characters, configured as "6 characters followed by 3 characters". The 3-digit suffix identifies the colourway, e.g. Blazer Mid `DA2142-146` (white) vs `DA2142-046` (black). Older Jordans have 4-digit codes (e.g. 1989 "4363"), so the 6+3 pattern is not universal. — [allaboutanthony.com](https://www.allaboutanthony.com/identify-nikes/); [House of Heat](https://houseofheat.co/nike/nike-blazer-mid-77-color-code-white-da2142-146-black-da2142-046); [Underpriced Nike code tool](https://www.underpriced.app/tools/nike-style-code-lookup). These are secondary sources. No official Nike spec was found.
- GOAT URL slugs end with the style code lowercased, with dashes and spaces collapsed into hyphens: `dunk-low-black-white-dd1391-100`, `asics-gel-nyc-sneaker-cream-white-1203a383-113`, `golden-goose-...-gwf00102-f002472-10881`, `maison-mihara-...-a12fw706-wht`. So other brands' codes include spaces, multiple segments and alphabetic colour suffixes (`WHT`). — [GOAT Dunk Low](https://www.goat.com/en-sa/sneakers/dunk-low-black-white-dd1391-100); [GOAT Gel NYC](https://www.goat.com/en-de/apparel/asics-gel-nyc-sneaker-cream-white-1203a383-113); [GOAT Golden Goose](https://www.goat.com/sneakers/golden-goose-wmns-superstar-white-cream-leopard-gwf00102-f002472-10881)
- India: Nike's India pages show a "Style" field (e.g. `FQ8146-111`, `IB4357-001`) next to "Colour Shown" (e.g. "White|Black", "Cool Grey/Cerulean/Black/Black"). A Flipkart listing put the code in descriptive text: "Style code-833535-110". — [nike.in Court Shot](https://www.nike.in/nike-court-shot-men-s-shoes/p/24942536); [nike.com/in Lunar Roam](https://www.nike.com/in/t/lunar-roam-shoes-sfk4rj); [Flipkart Nike search](https://www.flipkart.com/q/nike-shoes)
- On Myntra, sellers' per-product ID is `vendorArticleNumber`: "ID that uniquely identifies the product", up to 40 characters, example `INTR000142-Chambray`. `styleGroupId` groups "all sizes of a product with same MRP and colour", and `Color Variant GroupId` links colour variants of a style. This is a seller-chosen ID, not necessarily the brand style code. — [Fynd docs: Myntra attributes](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra)
- Academic product matching (the WDC corpus, which has a shoes category) built its training labels from shared schema.org identifiers (GTIN/MPN) mined from pages. The shoes gold standard has 1,100 pairs (300 positive, 800 negative). This shows that identifier-based matching is the accepted "silver" standard, with manual checks for the test set. — [WDC ECNLP 2019 paper](https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Research/Web-based_Systems/pub/ECNLP_19_PrimpeliPeetersBizer.pdf); [HF wdc/products-2017](https://huggingface.co/datasets/wdc/products-2017/blob/main/README.md?code=true)

### Inferences
- Recommended normalization for code matching: uppercase; replace any run of whitespace, `-`, `_`, `/` or `.` with a single separator (or strip them all for the comparison key); trim. Then compare in two forms:
  - **full key**, e.g. `DD1391100`, which means the same model and colourway;
  - **base key**, e.g. `DD1391`, which means the same model in some colourway. A base-only match is a candidate that must pass colour checks.
- Extract codes with regexes from the title, bullets, "Model number"/"Style code"/"Item model number" fields and the description. Useful patterns:
  - Nike/Jordan: `\b[A-Z]{2}\d{4}[-\s]?\d{3}\b` and legacy `\b\d{6}[-\s]?\d{3}\b`
  - adidas: `\b[A-Z]{1,2}\d{4}\b` (e.g. FY2903, JR5410)
  - ASICS: `\b1\d{3}[A-Z]\d{3}[-\s]?\d{3}\b`
  - New Balance: model+colour codes like `BB550WT1`
  - Puma: 6 digits plus a 2-digit colour, e.g. `374915-01`
- Always verify after a search hit, unlike Sneaks-API. The top Algolia/marketplace search result for a code is often a related colourway or kids version. Require the extracted code on the candidate page to equal the query (full key), or treat it as a weaker match.
- Seller-made IDs (Myntra `vendorArticleNumber`, Amazon seller SKUs, Flipkart seller SKUs) are not reliable join keys unless they contain a recognizable brand style-code pattern.
- GTIN/EAN would be the strongest key, but it is per size. Indian marketplaces rarely expose it publicly (unverified; see Gaps), so the style code is the practical key.

### Gaps
- I found no StockX or GOAT engineering blog posts on catalog deduplication. KicksDB (kicks.dev) docs returned 404, so I could not confirm its SKU/GTIN normalization.
- I could not confirm which Amazon.in field (Item model number, Style code, Model name) carries the Nike style code. My search returned no Amazon.in pages.
- I found nothing on whether Flipkart or Myntra expose EAN/GTIN in page HTML or JSON.

## Q2. Colourway naming: how do official multi-colour names map to store colour fields?

### Takeaway
Even GOAT keeps two fields: a free-text "Colorway" (the official multi-part name) and a single "Main Color" facet. The mapping between them is inconsistent, even within GOAT (cream vs white vs tan). Indian marketplaces store one seller-chosen "prominent" colour from a dropdown. So colour should be compared on a coarse base-colour family with tolerance, never as an exact string.

### Cited Findings
- GOAT product pages carry a separate "Main Color" next to the free-text colourway, and the two disagree across listings:
  - adidas ATRIC23 "Cream White" → Main Color Cream
  - ASICS Gel NYC "Cream/White" → Cream
  - Dries Van Noten "Cream White" → White
  - Maison Mihara "White" → Cream
  - adidas Sambae "Cream White Clear Sky" → Tan

  — [GOAT ATRIC23](https://www.goat.com/apparel/atric23-cream-white-gz9800); [GOAT Dries Van Noten](https://www.goat.com/en-mx/sneakers/dries-van-noten-simple-sneaker-cream-white-252-021725-117-001); [GOAT Mihara](https://www.goat.com/apparel/maison-mihara-yasuhiro-peterson-low-garment-dyed-white-a12fw706-wht); [GOAT Sambae](https://www.goat.com/en-de/apparel/adidas-wmns-sambae-cream-white-clear-sky-js3957) (field values come from the search-result summary of these pages)
- Nike India's "Colour Shown" uses the official slash-separated multi-part name, in the order base/upper first, then accents, e.g. "White/Midnight Navy/University Red/Metallic Gold" and "Black/Neptune Blue/Blue Tint/Metallic Silver". — [nike.com/in Air Max Plus](https://nike.com/in/t/air-max-plus-shoes-BRVkLx); [nike.com/in Air Max Plus black](https://nike.com/in/t/air-max-plus-shoes-SCcSST)
- Myntra requires "Prominent Colour" ("Choose a colour from the dropdown options") and "Brand Colour (Remarks)" ("Fill the most prominent colour of article"). Only one colour is mandated. — [Fynd docs: Myntra attributes](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra)
- Myntra rejects listings that do not use "Myntra-approved color names", so a controlled vocabulary exists. — [Streamoid Myntra seller guide](https://streamoid.com/guide/myntra-seller-guide)
- In Nike style codes the 3-digit suffix encodes colourway. Same suffix means same colour group: `-100`/`-146`/`-111` are white-based, `-001`/`-046` black-based. These are examples only, not a full table. — [House of Heat Blazer](https://houseofheat.co/nike/nike-blazer-mid-77-color-code-white-da2142-146-black-da2142-046); [Underpriced decoder](https://www.underpriced.app/tools/nike-style-code-lookup)

### Inferences
- Use the first token of an official colourway (the part before the first `/`) as the primary colour. Nike orders colourways roughly upper/base-first, so "Sail/Gum Yellow/Midnight Navy" has primary "Sail". Compare a store's single colour against the set of all base families in the colourway, with a stronger score if it matches the first token.
- Suggested base-colour taxonomy. This is my synthesis and should be tuned on data.
  - **WHITE**: white, sail, summit white, off white/off-white, cream, ivory, bone, coconut milk, phantom, pale ivory, light bone, chalk, cloud white (adidas FTWWHT), core white, ecru
  - **BEIGE/TAN**: beige, tan, khaki, wheat, sand, hemp, light orewood brown, sanddrift, oatmeal, rattan, gum (when it is the upper colour; usually it is only the sole). GOAT puts Cream under Tan sometimes, so allow WHITE↔BEIGE as a soft match.
  - **GREY**: grey/gray, wolf grey, cool grey, cement, smoke grey, light smoke grey, pure platinum, photon dust, aluminium (silver-ish), iron grey, charcoal (charcoal can also map to black)
  - **BLACK**: black, core black (CBLACK), anthracite, off noir, dark smoke grey (soft)
  - **NAVY/BLUE**: navy, midnight navy, obsidian, college navy, royal, game royal, university blue, court blue, blue tint (light, accent)
  - **RED**: red, university red, varsity red, gym red, fire red, crimson, team red, pimento (soft orange)
  - **GREEN, YELLOW/GOLD, ORANGE, PINK, PURPLE, BROWN**: analogous lists (e.g. metallic gold → gold/yellow; baroque brown → brown).
  - **MULTI**: "Multicolor", "Multi-Colour" and "Assorted" act as a wildcard. They match any colourway with 3 or more distinct base families, but score low.
- Rules for comparing colours:
  1. If both sides have a full style code (`DD1391-100`), the code decides and colour is only a sanity check.
  2. If both sides have only colour text, map each to its set of base families. Match when the store's primary colour is in the other listing's set and the first-token families are equal or soft-equal (WHITE~BEIGE, BLACK~GREY(dark), NAVY~BLUE).
  3. Treat "Off White"/"Off-White" carefully: it is both a colour (→ WHITE) and a brand (Off-White™ collabs). Check the brand field.
  4. Ignore sole-only words when the store gives one colour ("gum" sole, "volt" accent).
- Indian marketplaces often reduce "Sail/Gum Yellow/Midnight Navy" to "White", "Off White" or "Multicolor". All three should pass the colour gate for that shoe, while "Black" or "Blue" should fail.

### Gaps
- No public, authoritative Nike colour-name → base-colour table was found. The taxonomy above is my synthesis, not a cited standard.
- I could not get Myntra's or Flipkart's actual colour dropdown value lists.

## Q3. Gender/age: how to avoid matching adult shoes to kids versions

### Takeaway
On Nike/Jordan, each gender/age split of the same colourway has a different base style code, not just a different size range. Matching on the full style code already separates men, women and kids. Without codes, use gender/age words and the size range as hard filters.

### Cited Findings
- Dunk Low "Panda" (same White/Black colourway) has five distinct codes:
  - Men's `DD1391-100`
  - Women's `DD1503-101`
  - GS `CW1590-100` ($90 vs $115 adult)
  - PS `CW1588-100`
  - TD `CW1589-100`

  — [Sole Retriever](https://soleretriever.com/sneaker-release-dates/nike/dunk-low/nike-dunk-low-white-black-dd1391-100); [House of Heat](https://houseofheat.co/nike/nike-dunk-low-panda-white-black-release-date-dd1503-101-dd1391-100)
- Nike India sells kids versions with "Older" in the URL/name (e.g. "c1ty-older-shoes", `HV6003-131`). — [nike.com/in C1TY Older](https://nike.com/in/t/c1ty-older-shoes-pbSF5g/HV6003-131)
- GOAT slugs flag women's versions with a "wmns" token (e.g. "adidas-wmns-sambae", "golden-goose-wmns-superstar"). — [GOAT Sambae](https://www.goat.com/en-de/apparel/adidas-wmns-sambae-cream-white-clear-sky-js3957)
- Myntra has a mandatory `AgeGroup` field (dropdown). The values were not shown on the docs page. — [Fynd docs: Myntra attributes](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra)
- Myntra/Pixelbin category taxonomy has separate kids categories such as "Boys' Formal and Sports Shoes" with their own baseColour attribute. — [Pixelbin AI product tagging](https://www.pixelbin.io/docs/transformations/ml/ai-product-tagging)

### Inferences
- Never match on the base code alone across gender. A same-colourway listing with a different base code (DD1391 vs DD1503 vs CW1590) is a different product. Women's codes may also differ in the colour suffix (`-101` vs `-100`).
- Gender/age gate when there is no code:
  - Map tokens to a segment:
    - "men", "men's", "male" → M
    - "women", "wmns", "w", "ladies" → W
    - "unisex" → U
    - "boys", "girls", "kids", "big kids", "gs", "grade school", "older kids", "junior", "youth", "y" → KIDS_BIG
    - "ps", "pre-school", "little kids", "younger kids" → KIDS_LITTLE
    - "td", "toddler", "infant", "baby", "crib" → KIDS_TODDLER
  - U matches M or W, M does not match W, and KIDS never matches an adult segment.
- Size signal for Indian (UK) sizing: adult men's ranges usually start at UK 6 and women's around UK 3–4. A listing whose only sizes are ≤ UK 5.5, or that uses "C" sizes or "10C/13C/1Y–7Y" style sizes, is likely kids. Overlap (UK 3–5.5) exists between GS and women's, so use size only as a tiebreaker, not as a sole rule. These thresholds are inferred, not cited.
- Price is a weak extra signal: GS retail is about 75–80% of adult ($90 vs $115 for the Panda).

### Gaps
- No tracker documented its adult-vs-kids exclusion logic. The rules above are inferred.
- I could not confirm the allowed values of Myntra's AgeGroup or Flipkart's "Ideal For" field.

## Q4. Title normalization for shoes without codes (Indian value brands)

### Takeaway
I found no published stopword lists from Indian trackers. Product-matching research (WDC shoes) and practice point to the same approach: strip category, marketing and audience words, keep brand + model name/number + colour, and compare token sets with fuzzy scoring after hard brand/gender gates.

### Cited Findings
- Myntra listing titles in India mix brand, model and marketing words, e.g. "Bersache Women Running Flyknit Non Marking Shoes Sports Shoes For Women". Note the duplicated audience and category words. — [DesiDime Myntra deal](https://www.desidime.com/deals/buy-bersache-women-running-flyknit-non-marking-shoes-sports-shoes-for-women-31294375-myntra)
- Indian brand sites put model and colour in the title, e.g. Lotto "Brasil Select OG Powder Blue Women Shoes" and "Autograph NXT Black Fuchsia Red Womens Shoes". — [Lotto India](https://lottosport.in/collections/women-new-arrivals/products/lotto-brasil-select-og-powder-blue-women-shoes); [Lotto India Autograph](https://lottosport.in/collections/women-sneakers-and-sport-lifestyle/products/lotto-autograph-nxt-black-fuchsia-red-womens-shoes)
- Ditto (a pre-trained language model matcher) was benchmarked on the WDC product sets including shoes. Shoe title matching is one of the harder WDC categories because titles differ mostly by small model and colour tokens. — [Ditto paper (arXiv 2004.00584)](https://arxiv.org/pdf/2004.00584) (a per-category difficulty claim from my reading of the WDC results; check before quoting exact F1)

### Inferences
- Noise words to drop:
  - category: shoes, shoe, sneakers, sneaker, casual, sports, running (keep only if a model is named "Running"), walking, training, gym, outdoor, footwear, trainers, lace up, slip on
  - audience (handled by the gender gate, then removed): for men, men's, mens, for women, boys, girls, kids
  - marketing: lightweight, comfortable, stylish, trendy, latest, new, best, breathable, anti-skid, non marking, memory foam, cushioned, durable, all day, everyday, partywear, combo, pack of 1
  - size/price fragments: uk 7, size, mrp
  - store boilerplate
- Identifying tokens to keep:
  - brand (normalized: "Campus Shoes" → campus; "Red Tape" → redtape; "Asian" vs "Asian Shoes")
  - model name or number (e.g. Campus "OG-07", "North Plus", Sparx "SM-482", Asian "Wonder-13", Bata "Power")
  - model-like alphanumerics (`[A-Z]{1,4}-?\d{2,4}`)
  - series words (Max, Pro, Lite, Plus, 2.0)
  - colour tokens (sent to the colour gate)
- Pipeline:
  1. Brand must equal (after alias map).
  2. Gender/age gate.
  3. If an alphanumeric model code exists on both sides, it must match after normalization (uppercase, strip `-` and spaces).
  4. Fuzzy token-set similarity (e.g. rapidfuzz `token_set_ratio`) on the cleaned model tokens, threshold about 85–90.
  5. Colour-family gate.
  6. Optional price-band sanity check (e.g. within ±40% of MRP).
- Numbers matter: "Wonder-13" vs "Wonder-11", "Air Max 90" vs "Air Max 97". Never let fuzzy scoring pass a mismatch of numeric tokens.

### Gaps
- I found no Indian tracker (BuyHatke, PriceHistory, Pricebefore) documentation of its title-matching or noise lists. BuyHatke coverage claims (Amazon, Flipkart, Myntra, Ajio, Meesho, Nykaa) are marketing only. — [BuyHatke App Store](https://apps.apple.com/us/app/-/id895452619); [Tribune partner article](https://www.tribuneindia.com/partner-exclusives/flipkart-big-billion-days-sale-how-buyhatke-assists-shoppers-in-comparing-deals)

## Q5. Known failure modes and how mature systems handle them

### Takeaway
The main failure modes are:
- trusting a top search hit (as Sneaks-API does)
- base-code-only matches that cross colourways or gender versions
- retro re-releases that reuse names but not always codes
- brand-code collisions
- seller-specific IDs

Mature catalogs handle these with one canonical product per style code, explicit verification, and treating codes as brand-scoped.

### Cited Findings
- Top-hit acceptance without verification (Sneaks-API GOAT and Flight Club scrapers). A search for one style code can return a different product, and the code never re-checks it. — [goat-scraper.js](https://raw.githubusercontent.com/druv5319/Sneaks-API/master/scrapers/goat-scraper.js); [flightclub-scraper.js](https://raw.githubusercontent.com/druv5319/Sneaks-API/master/scrapers/flightclub-scraper.js)
- Code collisions across brands: SoleSearch warns that SKU formats vary by manufacturer and can overlap, and advises scoping by brand. — [SoleSearch API](https://www.github.com/SoleSearch-Demos/api)
- Restocks under the same code: the Panda `DD1391-100` released in 2021 and restocked repeatedly (Dec 2023 restock reported by several outlets; sources disagree on the exact date). The same code spans multiple production runs, so the code identifies the product, not the release. — [Sneaker Freaker](https://www.sneakerfreaker.com/releases/nike-dunk-low-panda-black-white-DD1391-100-restock-breaking/?page=0); [Sole Retriever](https://soleretriever.com/sneaker-release-dates/nike/dunk-low/nike-dunk-low-white-black-dd1391-100)
- Retro re-releases may get new codes. Early Jordans used 4-digit codes (e.g. "4363" for a 1989 Black/Cement Grey), while later retros of the same colourway carry modern codes. Name + colourway alone can therefore conflate OG and retro. — [House of Heat AJ6 guide](https://houseofheat.co/jordan/complete-guide-every-air-jordan-6-colorway)
- Seller IDs: Myntra's `vendorArticleNumber` is seller-defined, e.g. `INTR000142-Chambray`. — [Fynd docs](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra)
- Colour facet inconsistency even on GOAT (see Q2), so a single-colour field cannot be the deciding signal.

### Inferences
- Defenses for the Python service:
  1. Make the key (brand, normalized full style code) and verify it on the candidate page.
  2. Treat the same code at different times as the same product (restocks), but treat the same name with a different code as a different product (retro, regional or gender versions).
  3. Scope codes by brand.
  4. Flag listings whose brand is not authorized or whose price is far below MRP (e.g. <50% of nike.in price for a current model) as suspect third-party/fake, and do not auto-match them.
  5. Mark matches with confidence tiers:
     - exact full code
     - base code + colour family + gender
     - fuzzy title + colour + gender
  6. Regional variants: Nike's India site uses the same global style codes (e.g. `FQ8146-111`, `HV6003-131`), so codes should be stable across India marketplaces. — [nike.in Court Shot](https://www.nike.in/nike-court-shot-men-s-shoes/p/24942536)

### Gaps
- I found no published data on India-specific regional SKUs (e.g. India-exclusive codes) or on how BuyHatke/PriceHistory handle fakes or third-party sellers.
- I found no engineering write-ups from StockX/GOAT on deduplication or counterfeit catalog handling. StockX's official v2 Catalog API is gated, with a closed-beta developer registration. — [Apify StockX scraper notes](https://apify.com/crawlerbros/stockx-scraper.md)
