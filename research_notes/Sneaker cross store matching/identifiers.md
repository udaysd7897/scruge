# Sneaker product identifiers in India (style codes, article numbers, GTINs) and how they appear on Amazon.in, Flipkart and Myntra

Method note: Myntra and Flipkart product pages were fetched live on 2026-11-13 with `curl` (desktop Chrome UA) and parsed. Amazon.in returned a 2 KB bot-wall page to curl and HTTP 503 to WebFetch, so the Amazon findings come from search snippets of Amazon-data mirror sites (desertcart) and are lower confidence. Where a claim comes from background knowledge rather than a source fetched here, it is labelled "(background knowledge, not verified this session)".

## Q1. Global brands: identifier formats, colourway encoding, kids/gender variants, formatting variants

### Takeaway
On Flipkart, the brand's full colourway-level article number is in a spec row called **"Article Number"** for Nike (`DH2987-001`), Adidas (`KI5418`), Puma (`37491505`), Asics (`1011B962.402`). The `<meta name="Description">` carries a second, often **model-level (colour suffix dropped)** "style" value (`DH2987`, `374915`, `368466`). Normalise by stripping separators, then compare at two levels: model root and root plus colour.

### Cited Findings
- **Nike**: style code = 6 chars + "-" + 3 digits, e.g. Air Jordan 6 GS "Turbo Green" 543390-043. The first six identify the model and the last three the colourway. — [allaboutanthony.com](https://www.allaboutanthony.com/identify-nikes/); [House of Heat AJ6 guide](https://houseofheat.co/jordan/complete-guide-every-air-jordan-6-colorway)
- Nike's newer roots are 2 letters + 4 digits (`DH2987`, `AR5594`). Older roots are 6 digits (`304874`, `870020`, `599187`). Kids versions have their own roots. GOAT examples: Presto Extreme GS 870020-009 and AR5594-800, Team Hustle D6 GS 599187-007, Dunk Low 304874-171. — [GOAT 870020-009](https://www.goat.com/en-it/sneakers/presto-extreme-gs-grey-red-black-870020-009); [GOAT AR5594-800](https://www.goat.com/en-it/sneakers/presto-extreme-gs-what-the-90s-ar5594-800); [GOAT 599187-007](https://goat.com/en-ca/sneakers/team-hustle-d6-gs-grey-light-green-spark-599187-007); [GOAT 304874-171](https://www.goat.com/sneakers/dunk-low-304874-171)
- Flipkart Nike example: "NIKE court vision lo nn Sneakers For Men". Specs: Model name=COURT VISION LO NN; Brand Color=Black-Black; Color=Black; **Article Number=DH2987-001**. The meta description says "…- DH2987 only for Rs.4995" (model root only). One gallery image filename on the same page contains `dh2987-009` ("nike-black-or-grey"), so the page shows images from other colourways. — [Flipkart itm7f1dabd26d2ff](https://www.flipkart.com/nike-court-vision-lo-nn-sneakers-men/p/itm7f1dabd26d2ff) (fetched)
- **Puma**: Flipkart "PUMA Suede Classic SD" has Article Number=**37491505**, a Brand Color of Honey Mustard-White, and Season=EOSS-4-2022. The meta description gives "374915" and the image filename contains `374915-3-5-puma-honey-mustard-white`. — [Flipkart itm59d0d9bef5d1f](https://www.flipkart.com/puma-suede-classic-xxi-sneakers-men/p/itm59d0d9bef5d1f) (fetched)
- Puma Axis SL on Flipkart has a separate spec row **Style=368466** plus **Article Number=36846601**. But Brand Color reads "White-Glacier Gray" and every image filename reads `368466-13-puma-white-glacier-gray`, so the 2-digit colour suffix in the Article Number field (01) disagrees with the images (13). **Flipkart's Article Number can be wrong at colour level.** — [Flipkart itmfd98yaxyexhuh](https://www.flipkart.com/puma-axis-sl-sneakers-men/p/itmfd98yaxyexhuh) (fetched)
- Puma's own India site puts the 6-digit model in the URL path and the colour as `?swatch=NN`, e.g. `/pd/slipstream-sportstyle-sneakers/404690?swatch=01` and `?swatch=02`. Displayed style codes look like `391839_01`. — [in.puma.com 404690 swatch 01](https://in.puma.com/in/en/pd/slipstream-sportstyle-sneakers/404690?swatch=01); [swatch 02](https://in.puma.com/in/en/pd/slipstream-sportstyle-sneakers/404690?swatch=02); [in.puma.com 391839](https://in.puma.com/in/en/pd/rideric-mens-sneakers/391839)
- On Amazon.in (via mirrors), Puma "Item model number" values appear as 8 digits with no separator, e.g. Dazzler 39178201 and Ultimate Ease 37905101. — search-snippet summary of [desertcart Dazzler](https://www.desertcart.tw/zh/products/442805932-mens-dazzler-sneaker) and [desertcart Court Shatter](https://www.desertcart.lk/products/623289297-mens-court-shatter-low-sneaker) (pages 403'd on direct fetch; unverified)
- **Adidas**: Flipkart "ADIDAS Flowsoft Sneaker" has **Article Number=KI5418** (the same value appears in the meta description), with Brand Color "FTWWHT/CBLACK/GRETWO". That is Adidas's internal colour abbreviation string, which is useful as a secondary colour signal. — [Flipkart itm192f03a6920c9](https://www.flipkart.com/adidas-flowsoft-sneaker-sneakers-men/p/itm192f03a6920c9) (fetched)
- **Asics**: Flipkart "Asics GEL-PULSE 16" has **Article Number=1011B962.402**, which uses a **dot** instead of the usual dash (1011B962-402). Brand Color is MIDNIGHT/LUCID YELLOW. The size row reads "8 US" alongside UK/India Size=7, so Asics lists in **US** size where most brands use UK. — [Flipkart itm0d006f0f3cd41](https://www.flipkart.com/asics-gel-pulse-16-running-shoes-men/p/itm0d006f0f3cd41) (fetched)

### Inferences
- Proposed regexes. Apply them to the uppercased string after mapping `[ ._/]` to `-`:
  - Nike/Jordan: `^(?P<model>[A-Z]{2}\d{4}|\d{6})-?(?P<color>\d{3})$`. Check the 6-digit form after Puma's 8-digit form to avoid confusion: Puma is 6+2 = 8 digits and Nike is 6+3 = 9 digits.
  - Puma: `^(?P<model>\d{6})[-_ ]?(?P<color>\d{2})$`.
  - Adidas: `^[A-Z]{1,2}\d{4,5}$`. Background knowledge, not verified this session: older codes look like `B37…` and `S8…`, newer ones are 2 letters + 4 digits (GY, HQ, IF, IG, JH, JI, KI…). The whole code is colourway-specific and there is **no separable model part**, so model-level grouping needs the name.
  - Asics: `^(?P<model>1[01]\d{2}[A-Z]\d{3})[-.]?(?P<color>\d{3})$`. Background knowledge: 1011 = men's, 1012 = women's, 1013/1014 = kids, 1201/1203 = SportStyle/unisex, so **the gender is in the model prefix** and men's and women's versions of the "same" shoe have different codes.
  - New Balance (background knowledge, not verified): `^[A-Z]{1,3}\d{3,4}[A-Z0-9]{2,4}$`. Examples are ML574EVG, BB550…, U9060…, GC/PC/IV prefixes for kids (grade school / pre-school / infant), and M/W/U prefixes for men/women/unisex. The trailing letters encode the colourway, and width is sometimes appended (D/2E) or shown separately.
  - Skechers (background knowledge): `^\d{5,6}[A-Z]?-[A-Z]{3,6}$` (232040-BKW). The trailing letters are a colour code (BKW = black/white, NVY, WHT, BBK = all black). An `L` or `N` suffix often marks kids. Stores often drop the dash or the colour letters.
  - Vans (background knowledge): `^VN0[A-Z0-9]{5,7}$`. The colour is embedded in the final characters with no separator, so prefix matching on the first ~8 chars is fragile.
  - Converse (background knowledge): `^[A-Z]?\d{5,6}C$` (e.g. M9160C, 162050C). The whole code is colourway-specific.
  - Reebok (background knowledge): Adidas-era codes look like Adidas (`GZ1234`, `100033xxx` numeric after 2022). Not verified for India.
- Kids versions: Nike GS/PS/TD and Asics kids versions have different roots from the adult shoe. **Never fuzzy-match across GS/PS/TD or gender tokens.** Gender/age must be a hard filter (Flipkart "Ideal for"; Myntra `analytics.gender`).
- Store meta strings often truncate to the model root. Always prefer the explicit "Article Number" spec row and treat a meta-only value as model-level.

### Gaps
- I did not fetch New Balance, Skechers, Vans, Converse or Reebok listings, and I found no authoritative brand documentation for their formats. The formats above are background knowledge.
- I did not verify Nike India's own site format for India-exclusive releases.

## Q2. Indian brands: codes, colour encoding, cross-store presence

### Takeaway
Indian brands do populate Flipkart "Article Number", but the code is **not the name customers see**. For example, Sparx's "SM 323" model name maps to article SD0323G. Codes are per colour or carry a colour letter. Expect inconsistent formats and cross-colour contamination in images.

### Cited Findings
- **Sparx (Relaxo)**: the Flipkart title is "Sparx SM 323 | Stylish, Comfortable | Sneakers For Men". Model name is "SM 323 | Stylish, Comfortable |", **Article Number=SD0323G**, and Brand Color is "white11". Gallery image filenames carry several variants: `sd03230g` (white-b), `sd0323g` (multicolor), `sm323gg` (white). The codes for one product are clearly not normalised (zero-padding, SD vs SM, trailing G/GG). — [Flipkart itm591cf2de69726](https://www.flipkart.com/sparx-sm-323-stylish-comfortable-sneakers-men/p/itm591cf2de69726) (fetched)
- **Campus**: Flipkart "CAMPUS CIPHER" has Model name=CIPHER, **Article Number=22G-13407**, Brand Color=WHITE/R.SLATE and Label Size=G6. The image filenames include `22g-13407-…-campus-white-r-slate` and also `22g-13516-…-campus-off-wht-mrn`, which suggests **each colourway has its own 22G-xxxxx number**. Myntra lists Campus by model-name tokens such as "Campus HALL Women…" and "Campus Women OGL-4…". — [Flipkart itmb76b697fcb8a3](https://www.flipkart.com/campus-cipher-sneakers-men/p/itmb76b697fcb8a3); [Myntra 27922270](https://www.myntra.com/casual-shoes/campus/campus-hall-women-lace-up-sneakers/27922270/buy) (both fetched)
- **Red Tape**: the Flipkart title is "RED TAPE Low Cut Sneaker for Men in White Grey", with **Article Number=RSL1255A**. Image filenames show `rsl1255` (white-grey) and `rsl1258` (black). The base code differs per colour, and a trailing letter (A) is sometimes appended and sometimes dropped. — [Flipkart itm4cc3fbfad3994](https://www.flipkart.com/red-tape-low-cut-sneaker-men-white-grey-sneakers/p/itm4cc3fbfad3994) (fetched)
- **ASIAN**: the Flipkart Model name is "Casual Sneakers Shoes For Men Mexico-11" and **Article Number=MEXIKO-11** (spelled differently from the title). Asian codes are *model name + number*, and the colour sits in Brand Color (Green), not in the code. — [Flipkart itm27d9870cb12bf](https://www.flipkart.com/asian-casual-sneakers-shoes-men-mexico-11/p/itm27d9870cb12bf) (fetched)
- **Bacca Bucci**: on Amazon (via mirrors) the "Item model number" / "Model number" values look like `BBMH9004`, `BBMH9004I-06N`, `BBMH9004G-06`, `BBMH9118A-07` (Model Name "Boardroom") and `BBMH9039A-06` (Model Name "Neo"). The pattern is `BBMH` + 4-digit model + a variant letter + `-NN` (probably colour/size-run), but some listings give only the bare `BBMH9004`. — search-snippet summary of [desertcart 746594395](https://www.desertcart.sg/products/746594395-bacca-bucci-mens-sneaker), [desertcart 258565857](https://www.desertcart.lk/products/258565857-bacca-bucci-mens-grey-shoe) and related mirror pages (unverified)

### Inferences
- Indian-brand codes often use letter+digits with optional colour letters. Normalise with `re.sub(r'[^A-Z0-9]','',s.upper())`, strip leading zeros inside numeric runs (SD0323 → SD323), and fall back to the numeric core (`323`, `1255`, `13407`, `9004`) plus brand plus colour plus gender.
- The Sparx example shows that the consumer model name (SM-323) and the article code (SD0323G) can use different prefixes. Matching must try both the title tokens and the article code.

### Gaps
- I did not fetch Bata/North Star/Power, Woodland (GC/OGC), Liberty/Force 10, Bersache or HRX listings, so their formats are unverified. Background knowledge only: Woodland codes look like `GC 2654117` / `OGC 3045` with colour as a separate word, and HRX is a Myntra private label with little or no presence elsewhere.
- I could not confirm whether the colour suffix "-NN" in Bacca Bucci codes is colour or size-run.

## Q3. Where each store exposes the identifier

### Takeaway
**Flipkart is identifier-rich** (an "Article Number" spec row plus a code in the meta description and image filenames). **Myntra exposes no brand article code at all** in its PDP or search JSON, only Myntra's own styleId and skuId. **Amazon.in** carries the code in "Item model number" / "Model number" (seller-entered, inconsistent), but could not be scraped without a browser here.

### Cited Findings
- **Flipkart PDP structure** (from server-rendered HTML): specs are embedded as JSON objects shaped `{"label_2":{"value":{"text":["<value>"]}},"label_1":…,"label_0":{"value":{"text":"<Key>"}}}` inside the widget `ATLAS_RICH_PRODUCT_DETAILS_VERTICAL_LIST` with contentTitle "Specifications". The keys seen were: Brand, **Brand Color** (the brand's own colour name), **Color** (Flipkart's normalised colour), Secondary color, Outer material, **Model name**, Ideal for, Occasion, Type For Casual, Shoe Type, Size, UK/India Size, Euro Size, Sole material, Closure, Weight, Season, **Style** (sometimes, e.g. Puma 368466), **Article Number**, Label Size, Heel Height. **No row is called "Style Code"** on these 2026 pages. — all Flipkart URLs above (fetched)
- **Flipkart meta description** pattern: `"<Title> - Buy <Title> - <CODE> only for Rs.<price> from Flipkart.com…"`. CODE is the brand style/article, sometimes the model root only (Nike DH2987, Puma 374915) and sometimes full (Adidas KI5418, Asics 1011B962.402, Sparx SD0323G, Campus 22G-13407, Red Tape RSL1255A). — same Flipkart pages
- **Flipkart image URLs** follow `rukminim2.flixcart.com/image/<w>/<h>/<hash>/shoe/x/y/z/<size>-<article>-<size>-<brand>-<colour>-original-<id>.jpeg`. Example: `368466-13-puma-white-glacier-gray-original-…`. This is a useful extra signal, but **gallery images from sibling colourways appear on the same page**. — [Flipkart Axis SL](https://www.flipkart.com/puma-axis-sl-sneakers-men/p/itmfd98yaxyexhuh)
- Flipkart IDs are `itm…` (listing) plus `pid=SHO…` (per size/colour product ID), e.g. pid=SHOFD98XDPFAWDMW. — [WebFetch of Flipkart Axis SL](https://www.flipkart.com/puma-axis-sl-sneakers-men/p/itmfd98yaxyexhuh)
- **Myntra PDP**: the HTML embeds `window.__myx = {...}` with `pdpData`. Its keys are id, name, mrp, manufacturer, countryOfOrigin, colours, baseColour, brand, productDetails, articleAttributes, systemAttributes, catalogAttributes, sellers, sizes, analytics, and others. I searched the full JSON of six sneaker PDPs (Puma 19104462, Nike 31643044, Adidas 47326676, ASICS 43658461, Campus 27922270, Sparx 24338176): **none contains an articleNumber, vendor article, style code, EAN or GTIN**. "article" only appears as `articleType` / `articleAttributes`. The fields that are present:
  - `name` (e.g. "Nike Women Air Jordan 1 Mid Casual Shoes", "Puma Unisex Black Solid Regular Daze V2 Casual Sneakers"). The model name sometimes appears and sometimes does not (the Adidas one is just "ADIDAS Men Striped Sneakers").
  - `baseColour`, `analytics.gender`, `analytics.articleType`
  - `manufacturer` (the factory, e.g. "CHANGSHIN VIETNAM CO., LTD.", "MOCHIKO SHOES")
  - `sellers[].sellerName` (e.g. "Nike India Private Limited", "Puma Sports India Pvt. Ltd.(NSCM)", "RELAXO FOOTWEARS LIMITED")
  - `catalogAttributes` {season, year}
  - `articleAttributes` (materials, BIS Certificate Number, etc.)
  - `productDetails` HTML. No "Style Note" block was present on these sneaker pages.
  — [Myntra 19104462](https://www.myntra.com/casual-shoes/puma/puma-unisex-black-solid-regular-daze-v2-casual-sneakers/19104462/buy); [Myntra 31643044](https://www.myntra.com/casual-shoes/nike/nike-women-air-jordan-1-mid-casual-shoes/31643044/buy); [Myntra 47326676](https://www.myntra.com/casual-shoes/adidas/adidas-men-striped-sneakers/47326676/buy); [Myntra 43658461](https://www.myntra.com/casual-shoes/asics/asics-unisex-tiger-runner-ii-sneakers/43658461/buy); [Myntra 24338176](https://www.myntra.com/casual-shoes/sparx/sparx-men-round-toe-textile-sneakers/24338176/buy) (all fetched)
- **Myntra search page** (`https://www.myntra.com/<brand>-sneakers`) embeds `searchData.results.products[]` with keys including productId, productName, additionalInfo, brand, primaryColour, gender, colourVariants, colorVariantAvailable, relatedColoursCount, sizes, season, year, catalogDate, systemAttributes and landingPageUrl. **There is no article or style code.** Example: productId 43658461 "ASICS Unisex Tiger Runner II Sneakers", primaryColour Cream. — Myntra search pages for puma/nike/adidas/asics/campus/sparx (fetched)
- Myntra's `pdpData` scraping approach (window variable with pdpData) is documented by third parties. — [StackOverflow mirror](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/63290582/unable-to-scrape-myntra)
- **Amazon.in**: mirrors of Amazon data show "Item model number" (e.g. BBMH9004, 39178201), "Model number" (BBMH9004I-06N) and "Model Name" (Boardroom, Neo) rows, with the Manufacturer row naming the contract factory (e.g. Mochiko Shoes for Puma). — search snippets of desertcart mirrors above (unverified; live Amazon.in was blocked: curl got a 2 KB interstitial and WebFetch got HTTP 503)

### Inferences
- For Myntra, matching must rely on brand + name tokens (model name) + `baseColour` + `analytics.gender` + price/MRP + images (perceptual hash). A practical source of colour-level truth might be the Myntra image filename or the `colours[]` sibling list, but neither carries the brand code.
- `manufacturer` (factory) and season/year can act as weak tie-breakers between Myntra and Amazon, because both stores show the importer/manufacturer.
- For Amazon, prefer, in order: "Item model number" → "Model number" → "Manufacturer part number" → "Style" / title. Seller-entered values may be model-level only, may carry colour, or may be junk.

### Gaps
- I could not verify live Amazon.in attribute names ("Item model number", "Style Number", "Manufacturer part number") on 2026 footwear pages, or their presence rate. A browser (Claude in Chrome / Playwright) is needed.
- I did not check Myntra's mobile/gateway API (`/gateway/v2/product/<id>`) for hidden vendor fields. I only checked the web JSON.

## Q4. GTIN/EAN availability

### Takeaway
GTINs are **not usable** for cross-store matching in India: Flipkart and Myntra expose none in page data, and Amazon.in EAN could not be verified.

### Cited Findings
- None of the Flipkart sneaker PDP HTML fetched had an `ean` or `gtin` field (regex search returned nothing). — Flipkart pages above
- None of the six Myntra PDP JSONs contained EAN or GTIN (the only "ean" substring hits were inside words such as "clean"). — Myntra pages above
- Myntra exposes a BIS Certificate Number in articleAttributes (e.g. "CM/l-8300156912" on both Puma and ASICS pages, the same certificate). That is a factory/licence ID, not a product ID, so it is not a product identifier. — [Myntra 19104462](https://www.myntra.com/casual-shoes/puma/puma-unisex-black-solid-regular-daze-v2-casual-sneakers/19104462/buy); [Myntra 43658461](https://www.myntra.com/casual-shoes/asics/asics-unisex-tiger-runner-ii-sneakers/43658461/buy)

### Inferences
- Amazon sellers usually must supply a GTIN or have a brand exemption, but India footwear detail pages generally do not display it publicly (background knowledge). Treat it as unavailable.

### Gaps
- Amazon.in EAN display could not be checked live.

## Q5. Size and colourway variant structure

### Takeaway
On all three stores, **one listing = one colourway, with sizes as variants**. Colourways are separate IDs linked as siblings. Flipkart's `pid` is per size, and Myntra's `skuId` is per size under one `styleId`.

### Cited Findings
- **Myntra**: each `styleId` is one colour, and `sizes[]` holds per-size `skuId`s. For example, Puma 19104462 has sizes 3–8+ with skuIds 59117414, 59117416…, and each size entry carries `styleId` 19104462. Other colours appear in `pdpData.colours[]` as separate styleIds: Puma Daze V2 black 19104462 links to Navy Blue 19104468, and Campus HALL white 27922270 links to Blue 27922266 and Mauve 27922268. The search JSON has `colourVariants` / `relatedColoursCount`. — Myntra pages above (fetched)
- **Flipkart**: the listing title includes colour and size ("PUMA Axis SL Sneakers For Men (White , 7)"). Sizes show as buttons, and other colours as thumbnails labelled "Selected Color" that point to other listings. The spec table shows the currently selected size (Size=7 UK/India). — [Flipkart Axis SL WebFetch](https://www.flipkart.com/puma-axis-sl-sneakers-men/p/itmfd98yaxyexhuh)
- Several Flipkart search results for the same model returned different `itm` IDs (three for Court Vision Lo NN, two for Campus Cipher), which is consistent with separate listings per colourway and/or seller. — Flipkart search for "nike court vision low", "campus sneakers men" (fetched)

### Inferences
- Amazon.in (background knowledge): a parent ASIN with child ASINs per size × colour. The colour and size dimensions sit in the twister. Item model number may be set per parent or per child.
- Matching unit = (brand, article root, colour suffix or normalised colour, gender/age). Size is resolved afterwards via the size lists. Watch Asics/Nike US-vs-UK sizing (Flipkart Asics shows "8 US", UK=7).

### Gaps
- I did not verify how often Flipkart has multiple sellers each creating separate listings for the same colourway.
