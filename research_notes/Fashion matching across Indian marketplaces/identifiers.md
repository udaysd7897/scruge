# Product identifiers for fashion (tees/polos/jerseys, sneakers) on Amazon.in, Flipkart, Myntra

Method note: all "live" findings below come from plain HTTP GETs (desktop Chrome User-Agent, ~20 requests total) on 2026-11-12. Raw pages were saved under the session scratchpad. Myntra PDPs and listing pages, Flipkart search pages and PDPs, and one Amazon.in PDP all returned full HTML with HTTP 200. **Amazon.in search (`/s?k=`) returned an Akamai `bm-verify` JS-challenge interstitial**, which I did not try to get around. Amazon search by style code is therefore unverified with plain HTTP.

## (a) Brand style-code / article-number conventions

### Takeaway
Big sportswear brands use a stable, colourway-level code that brand-direct sellers copy onto Flipkart and Amazon: Puma's 6-digit style plus a 2-digit colour, Nike's 6+3 (`DH2987-100`), Adidas's 6-character article (`KW4826`), and Skechers' style number with an India suffix and colour (`999889ID-CHAR`). Indian-licensee brands such as U.S. Polo Assn. (Arvind) also have internal style codes (`UDTSHC0021`). Unbranded or small-brand sellers put arbitrary SKU strings in the same fields (`LINING-PLUS-HS-PKT-NVY- 5XL`).

### Cited Findings
- **Puma:** in.puma.com product URLs carry the 6-digit style in the path and the 2-digit colour as `swatch`. Example: `/in/en/pd/train-all-day-mens-breathable-training-tee/528856?swatch=01` = PUMA Black. Other colours of the same style are 73 Persian Blue, 18 Speed Blue, 46 Light Lavender, 99 Cast Iron, 75 Green Terrain, 02 PUMA White, 35 Gold Moon. Image paths use `/global/528856/73/`. — [in.puma.com search "528856"](https://in.puma.com/in/en/search?q=528856)
- Puma style 528856 + colour 01 appears as `52885601` (no separator) in Flipkart "Style Code" and in Amazon "Style Number", "Item model number" and "Manufacturer Part Number" (live fetch, see sections below). Flipkart image filenames for sibling colours use `52885699` and `52885635` (live fetch of [Flipkart TSHHEYWZMK66DDSE](https://www.flipkart.com/x/p/itm?pid=TSHHEYWZMK66DDSE)).
- **Nike:** the style code is usually 6 alphanumerics + "-" + a 3-digit colour code. Same base + different suffix = different colourway (e.g. DA2142-146 White vs DA2142-046 Black). Older models (e.g. some Air Jordan 4) don't follow the hyphenated format. — [GOAT listing DA2142-146](https://www.goat.com/en-gb/sneakers/wmns-blazer-mid-77-color-code-pack-white-da2142-146); [underpriced.app Nike style code decoder](https://www.underpriced.app/tools/nike-style-code-lookup)
- nike.com/in PDP URLs end with the style code: `/t/court-vision-low-next-nature-shoes-N2fFHb/DH2987-101`, `.../DH2987-113`, `.../DH2987-006`. The 6-char "N2fFHb" segment is a Nike model-group slug, not the style code. — [nike.com/in DH2987-101](https://www.nike.com/in/t/court-vision-low-next-nature-shoes-N2fFHb/DH2987-101); [nike.com/in DH2987-113](https://nike.com/in/t/court-vision-low-next-nature-shoes-N2fFHb/DH2987-113)
- nike.in (Nike's India storefront, sold by Nykaa Fashion) uses its own numeric product ids (`/p/24926271`). A search snippet indicates its page lists "style DH2987-100" in the text. — [nike.in 24926271](https://www.nike.in/nike-court-vision-low-next-nature-men-s-shoes/p/24926271) (snippet only, page not fetched)
- **Adidas:** the article number is a 6-character alphanumeric code (2 letters + 4 digits in current usage, e.g. FX5502, ID3947, KW4826). It appears in adidas URLs as `/<slug>/FX5502.html`. A retailer-level manufacturer number can append colour and size ("FX 5502-White Green-9"). — [Galaxus Q&A](https://www.galaxus.be/en/s8/questionandanswer/what-is-the-adidas-article-identifier-for-this-product-the-reason-for-my-question-is-that-there-are--512282); [Skatedeluxe ID3947](https://www.skatedeluxe.com/en/p/adidas-originals-adimatic-shoes-dark-brown-white_p169006?cic=PT). There is no official adidas format document. A Tempo article claiming a "10-character SKU" conflicts with this and probably describes a different identifier ([Tempo](https://en.tempo.co/read/1913731/easy-ways-to-check-if-your-adidas-shoes-are-authentic)).
- **Adidas on Flipkart (live):** Style Code = `KW4826` (ADIDAS Solid Men Polo Neck Blue T-Shirt, pid TSHHJXCPFDZY65DU, sold by Adidas India). "Brand Color" carried adidas's internal colour abbreviation `SIGCYA` rather than a plain colour. Flipkart image filenames of other adidas tees embed lower-cased articles: `m-kr6956-adidas-original-...`, `m-ku9850-adidas-...`, `m-ly8838-adidas-...`. — [Flipkart TSHHJXCPFDZY65DU](https://www.flipkart.com/x/p/itm2064871066e94?pid=TSHHJXCPFDZY65DU)
- **Skechers on Flipkart (live):** "Article Number" = `999889ID-CHAR` (style 999889, "ID" = India-specific suffix, CHAR = charcoal colour). JSON-LD description ends "- 999889ID" without the colour. A sibling image filename shows `894317id`. — [Flipkart SHOH3PYMJWR2HRGU](https://www.flipkart.com/skechers-summits-field-day-sneakers-men/p/itmd7d39298e0910?pid=SHOH3PYMJWR2HRGU)
- **U.S. Polo Assn. (Arvind licensee) on Flipkart (live):** Style Code = `UDTSHC0021`. The image filename also embeds it (`4xl-udtshc0021-u-s-polo-assn-original-...`). The listed manufacturer/packer is "Shyam Tex Exports, Faridabad". — [Flipkart TSHGHYTJPHEKHNYH](https://www.flipkart.com/u-s-polo-assn-solid-men-neck-green-t-shirt/p/itm17e98ab09cd71?pid=TSHGHYTJPHEKHNYH)
- **Small/unbranded seller (live):** Flipkart Style Code = `LINING-PLUS-HS-PKT-NVY- 5XL` (brand SMAN). This is a seller SKU that even includes the size, so the field is not a reliable brand identifier for non-major brands. — [Flipkart TSHHR5HCZSHSKH9U](https://www.flipkart.com/sman-solid-men-polo-neck-navy-blue-t-shirt/p/itm7d3435a6770f9?pid=TSHHR5HCZSHSKH9U)

### Inferences
- Normalise codes before matching: uppercase, then strip `-`, `_` and spaces. `528856_01`, `528856-01` and `52885601` then collapse to one key. Nike `DH2987-100` becomes `DH2987100`. Keep a "base style" key (Puma first 6 digits, Nike part before the hyphen, Skechers digits before `ID`) for colour-agnostic matching, and the full key for colourway-level matching.
- Some size-bearing codes are seller SKUs rather than brand style codes. Treat a code as a brand style code only if it matches a brand-specific regex and contains no size token. Starting regexes:
  - Puma: `^\d{6}[-_ ]?\d{2}$`
  - Nike: `^[A-Z]{2}\d{4}-?\d{3}$` (also older all-digit `^\d{6}-\d{3}$`)
  - Adidas: `^[A-Z]{1,2}\d{4,5}$`
  - Skechers: `^\d{5,6}[A-Z]{0,3}(-[A-Z]{3,5})?$`
- Indian-licensee and house brands appear to use internal alphanumeric codes, such as USPA's `UD…`/`US…` prefixes. Whether the same code is used across retailers is unverified (see Gaps).

### Gaps
- I didn't verify live formats for Reebok, ASICS, New Balance, Levi's, H&M, Jack & Jones, Tommy Hilfiger, Allen Solly / Van Heusen / Louis Philippe (ABFRL), HRX or Roadster. The Flipkart query "allen solly polo" returned an SMAN listing as the first result, so no ABFRL page was inspected. From general knowledge (unsourced, treat as hypothesis):
  - ASICS: `1011B548.001`
  - New Balance: model + colour letters, e.g. `ML574EVG`
  - Levi's: 5-digit style + 4-digit PC, e.g. `00501-0115`
  - ABFRL: codes like `ASKPQRGFT12345`
- Not established: whether Indian licensees (Arvind for USPA/Arrow, ABFRL, Reliance for Tommy) put the same style code on Amazon, Flipkart and their own D2C sites. Only one USPA listing was seen, and its seller was a third-party manufacturer/packer.

## (b1) Amazon.in: where identifiers live

### Takeaway
On the brand-direct Puma tee, one value (`52885601`) appears three times: "Style Number" (Item details table), "Item model number" (detail bullets) and "Manufacturer Part Number" (additional details). "Model Name" carries the brand's product-line name ("M TAD ESSENTIAL Tee"), not a code. Amazon groups colour × size children under a parent ASIN, and the canonical URL points to the parent.

### Cited Findings
- **Live fetch of [amazon.in/dp/B0FGJ6FVZ6](https://www.amazon.in/dp/B0FGJ6FVZ6)** (HTTP 200, no captcha). The visible text contained:
  - `Style Number 52885601`
  - `Item model number : 52885601`
  - `Manufacturer Part Number 52885601`
  - `Model Name : M TAD ESSENTIAL Tee`
  - `Style Name : Tees`
  - `Generic Name Tees`
  - `Manufacturer : Aryan Apparels Private Limited …`
  - `Date First Available : 3 July 2025`
  
  No EAN/GTIN/UPC string appeared.
- **Variations on the same page:**
  - Parent ASIN `B0FMFDYQXD`; the canonical URL is `https://www.amazon.in/Puma-Polyester-Solid-Regular-T-Shirt/dp/B0FMFDYQXD`.
  - `dimensionValuesDisplayData` maps child ASINs to [size, colour], e.g. `"B0FK9T2H49":["XS","Grey"]` and `"B0DX76P1SX":["S","Red"]`.
  - About 67 distinct ASINs were referenced on the page.
  - The parent spans several colours, and therefore several Puma style codes. Use child-level attributes for the code.
- The caller earlier observed Model Name = "TAD ESSENTIAL | GYM_2891" on the same ASIN. Today's fetch shows "M TAD ESSENTIAL Tee". Model Name is evidently seller-edited free text that changes over time. — live fetch vs. caller context
- **Amazon attribute semantics:**
  - A copy of an Amazon inventory template labels `part_number` as "Manufacturer Part Number" and `model` as "Model Number". — [Scribd template copy](https://www.scribd.com/document/556209533/Flat-File-InventoryLoader) (secondary, unverified against the current template)
  - GoDataFeed reports that for Clothing under Brand Registry, Style Number / Part Number can serve as the key attribute in place of a UPC. A registered-brand SKU without one won't go live. — [GoDataFeed help](https://help.godatafeed.com/hc/en-us/articles/115002064628-Feed-Amazon-Amazon-Clothing-StyleNumber-as-key-attribute-in-brand-registry)
  - An Amazon seller wiki says part/model numbers are often just the seller's own SKU or UPC, so they are not guaranteed to be the brand code. — [Amazowl wiki](https://wiki.amazowl.com/sop/amazon-foundations/part-model-numbers)
- Amazon search by keyword (`/s?k=KW4826`, `DH2987-100`, `UDTSHC0021`) returned an Akamai bot-challenge page (`bm-verify`, meta-refresh + JS) to plain curl. I did not proceed. — live fetch

### Inferences
- For Amazon, read identifiers from the detail sections in this order: "Style Number" → "Manufacturer Part Number" → "Item model number" → "Model Number". Use whichever matches a brand regex.
- Also scan the URL slug and title. The caller saw `528856_Black` in a slug; the canonical slug I saw had no code. Slugs vary by entry URL.
- On brand-direct listings the three fields agree. On reseller listings they may hold a seller SKU, so validate with a brand regex.

### Gaps
- I couldn't measure how often Style Number / Model Number is present across Amazon fashion. Only one ASIN was fetched, and search was blocked. A Nike or Adidas Amazon.in PDP was not inspected because no ASIN was obtainable without search.
- EAN/GTIN is not shown on the Amazon.in PDP I fetched. Amazon holds the GTIN internally (sellers supply it or an exemption), but it is not exposed publicly.

## (b2) Flipkart: where identifiers live

### Takeaway
Flipkart exposes the brand code in the specifications block of the page-state JSON:
- **Apparel:** spec label **"Style Code"** (Puma `52885601`, Adidas `KW4826`, USPA `UDTSHC0021`).
- **Footwear:** spec label **"Article Number"** (Nike `DH2987-100`, Skechers `999889ID-CHAR`), with a separate **"Model name"** row holding the brand model name.

Footwear JSON-LD `description` also includes the code ("… - DH2987-100 only for Rs.4995.0"). Image filenames often embed `<size>-<code>-<brand>-original-<hash>.jpeg`. Flipkart does not show an EAN.

### Cited Findings
- **Spec JSON shape (live, all six PDPs):** `"label_1":{"value":{"text":["<VALUE>"]}},"label_0":{"value":{"text":"<LABEL>"}}`. The value is an array; Country of Origin can hold several values. The regex `"label_1":\{"value":\{"text":\[([^\]]*)\]\}\},"label_0":\{"value":\{"text":"([^"]+)"` extracted every row.
- **Nike Court Vision LO NN** ([SHOGRVJPSM9MFYYE](https://www.flipkart.com/nike-court-vision-lo-nn-sneakers-men/p/itmde6fa6fc67661?pid=SHOGRVJPSM9MFYYE)):
  - Spec rows: `Model name`="COURT VISION LO NN", `Article Number`="DH2987-100", `Brand Color`="White/White-White"
  - JSON-LD: `sku`="SHOGRVJPSM9MFYYE" (Flipkart PID); `description` contains "- DH2987-100"
  - Image filenames: `8-dh2987-8-nike-white-white-white-original-imaheh4f….jpeg` (base style without the colour suffix)
- **Puma tee** ([TSHHEYWZMK66DDSE](https://www.flipkart.com/x/p/itm?pid=TSHHEYWZMK66DDSE)): `Style Code`="52885601"; JSON-LD `name`="PUMA Printed Men Round Neck Black T-Shirt", `sku`=PID; images `xl-52885699-puma-original-…`, `xs-52885635-puma-original-…`.
- **Adidas polo** ([TSHHJXCPFDZY65DU](https://www.flipkart.com/x/p/itm2064871066e94?pid=TSHHJXCPFDZY65DU)): `Style Code`="KW4826", `Brand Color`="SIGCYA". The page title is generic ("ADIDAS Solid Men Polo Neck Blue T-Shirt"), so the title alone carries no model information.
- **Skechers** ([SHOH3PYMJWR2HRGU](https://www.flipkart.com/skechers-summits-field-day-sneakers-men/p/itmd7d39298e0910?pid=SHOH3PYMJWR2HRGU)): `Model name`="SUMMITS - FIELD DAY", `Article Number`="999889ID-CHAR"; JSON-LD description "- 999889ID".
- **USPA** ([TSHGHYTJPHEKHNYH](https://www.flipkart.com/u-s-polo-assn-solid-men-neck-green-t-shirt/p/itm17e98ab09cd71?pid=TSHGHYTJPHEKHNYH)): `Style Code`="UDTSHC0021"; image `4xl-udtshc0021-u-s-polo-assn-original-…`.
- **SMAN** ([TSHHR5HCZSHSKH9U](https://www.flipkart.com/sman-solid-men-polo-neck-navy-blue-t-shirt/p/itm7d3435a6770f9?pid=TSHHR5HCZSHSKH9U)): `Style Code`="LINING-PLUS-HS-PKT-NVY- 5XL", i.e. a seller SKU.
- Every one of the 6 PDPs (4 apparel, 2 footwear) had a Style Code or Article Number row: 6/6, including the unbranded seller.
- Other spec rows useful for matching: "Name and address of the Manufacturer/Importer/Packer" and "Country of Origin". Myntra also exposes these (manufacturer "Aryan Apparels … IMT Manesar" appears on both Flipkart and Myntra for the Puma tee).
- **Pitfalls:**
  - PDP HTML also contains image filenames of *recommended* products (e.g. adidas `m-ly8838-adidas` on the Puma page). Only trust filenames whose code matches the product's own spec value, or which come from the main gallery.
  - Some gallery images have no code (`-resized-original-…`, `-watermarked-original-…`).
- No EAN/GTIN field appeared in any spec table. Raw "EAN" substring hits were inside other words.
- Flipkart JSON-LD `sku` is always Flipkart's PID, not the brand code. — live fetches

### Inferences
- Extract in this order: spec "Style Code" (apparel) or "Article Number" (footwear) → JSON-LD description suffix after " - " → image filename token between the size prefix and the brand slug.
- "Model name" (footwear) is the brand's model name, a good secondary text key (e.g. "COURT VISION LO NN" vs Nike's "Court Vision Low Next Nature").
- Flipkart PIDs are size-specific. One `itm…` id groups sizes, and the Style Code is the same across sizes of one colour.

### Gaps
- The prevalence figure comes from a sample of only 6 PDPs; a larger sample is needed to estimate the share of branded listings that carry the code.
- I didn't check whether Flipkart ever uses a "Model Number" label for fashion. It did not appear in any of the six pages.

## (b3) Myntra: does it expose any brand style identifier?

### Takeaway
No. Across 5 Myntra PDPs (Puma tee, two Nike sneakers, Adidas polo, USPA tee, all brand-direct or authorised sellers) and 3 listing pages, I found no brand style code, article number, vendorArticleNumber or EAN in `window.__myx`, JSON-LD or image names.
- JSON-LD `sku` and `mpn` are both just Myntra's styleId.
- The number in older image filenames is a 3-digit prefix followed by an upload timestamp, not an EAN or SKU.

The matching signals Myntra does offer:
- The product **name**: brand-direct sellers often use the brand's official product name, e.g. "Train All Day Men's Breathable Training Tee" for Puma 528856.
- Manufacturer and packer address
- `catalogAttributes` season/year
- Colour-variant styleIds
- Size measurements

### Cited Findings
- **Live, [Myntra 35720668](https://www.myntra.com/tshirts/puma/x/35720668/buy):**
  - `pdpData` keys: id, name, mrp, manufacturer, countryOfOrigin, colours, baseColour, brand, media, analytics, crossLinks, productDetails, articleAttributes, systemAttributes, catalogAttributes, descriptors, sellers, sizes, styleType, etc.
  - `sizes[]` keys: skuId, styleId, label, measurements, sizeSellerData(mrp, sellerPartnerId, manufacturerInfo, importerInfo, packerInfo, …). There are no vendor/article/EAN fields.
  - `catalogAttributes`={"catalogDate":"1752681145000","season":"fall","year":"2025"}
  - Sellers: "Puma Sports India Pvt. Ltd.(NSCM)" (sellerPartnerId 6206) and "Omnitech Retail".
  - JSON-LD Product: `"sku":"35720668","mpn":"35720668"`.
  - Grepping for `528856`, `52885`, `vendorArticle`, `articleNumber`, `styleCode`, `Style Code`, `Product Code`, `gtin`, `ean` found nothing.
- **Myntra name ≈ brand-site name:** Myntra "Puma Train All Day Men Breathable Training Tee" corresponds to in.puma.com "Train All Day Men's Breathable Training Tee" (style 528856). Myntra lists colour variants as separate styleIds (35720666 Green/Orange, 35720667 Blue/Yellow, 35902832 Yellow/Black, 36087993 Grey/Black, …), and Puma lists 8 colours. — live fetch; [in.puma.com](https://in.puma.com/in/en/search?q=528856)
- **Nike on Myntra (live):**
  - [39235378](https://www.myntra.com/x/x/x/39235378/buy) "Nike Court Vision Low FL Men's Shoes" and [45863237](https://www.myntra.com/x/x/x/45863237/buy) "Nike Air Max TL 2.5 Premium Men's Shoes", both seller "Nike India Private Limited".
  - productDetails holds nike.com marketing copy, with no "Style:" line.
  - Manufacturer: "TKG TAEKWANG VINA JOINT STOCK COMPANY … BIEN HOA". This is the factory, not a code.
  - A style-code regex over the whole pdpData JSON matched nothing.
  - Image filenames are random hashes (`zjgGpIl5_016fae7f….jpg`, `590a6ac5….jpg`).
- **Adidas on Myntra (live):** [39852025](https://www.myntra.com/x/x/x/39852025/buy) "ADIDAS A230 M Prfrm Po Polo Collar T-Shirt" (seller ADIDAS INDIA MARKETING PRIVATE LIMITED).
  - The name holds adidas's internal short product name ("A230 M PRFRM PO"), which can be useful text.
  - There is no article code anywhere, and the image filename is a random hash.
- **USPA on Myntra (live):** [36468833](https://www.myntra.com/x/x/x/36468833/buy) (sellers ARVIND LIFESTYLE BRANDS LIMITED, Supercom Net). There is no style code, and the manufacturer is "GARLAND APPARELS … TIRUPPUR".
  - One older USPA listing-page image filename embedded a product token: `…USPoloAssnCrewNeckEmbroideredLogoI633LoungeT-Shirt-PackOf1FI1.jpg`. "I633" looks like a USPA Innerwear style code, so older filenames are sometimes seller-supplied file names with codes. — live listing page `myntra.com/us-polo-assn-tshirts`
- **Image-filename number decoded (live):**
  - `…1753794067116-Puma-Train-All-Day-Mens-Breathable-Training-Tee-490175379406-1.jpg`: the leading part `1753794067116` is a ms epoch upload timestamp (29 Jul 2025, matching path `/2025/7/29/`). `490175379406` = `490` + `175379406`, the first 9 digits of that timestamp.
  - `ADIDAS-Women-Tshirts-4911711529079303-1.jpg` = `491` + `1711529079303`, with timestamp prefix `1711529079802` in the same filename.
  - `ADIDAS-Men-Tshirts-5971754300059031-1.jpg` = `597` + `1754300059031`.
  - `US-Polo-Assn-Men-Lounge-Tshirts-7671581660125176-1.jpg` = `767` + `1581660125176`.
  - So the number is a 3-digit prefix plus a timestamp, not an EAN (`490` happens to look like a Japan GS1 prefix, but it isn't one here). It is useless for cross-platform matching.
  - Newer uploads (2025–26) use random-hash filenames (`zjgGpIl5_…`, `07e04b84….jpg`).
- **Myntra listing/search JSON (live, `searchData.results.products[]`):** keys include productId, productName, brand, additionalInfo (short name, e.g. "Court Vision Low FL Men's Shoe"), primaryColour, catalogDate, season, year, colourVariants, sizes, images, searchImage, buyButtonWinnerSkuId, buyButtonWinnerSellerPartnerId, systemAttributes, productMeta. None are brand style codes.
- **Myntra seller-side fields exist but aren't public:**
  - Myntra cataloging (via the Fynd integration) requires `vendorArticleNumber` ("ID that uniquely identifies the product - Vendor can use this id to track their order flow") and `styleGroupId` ("a number to identify all sizes of a product with same MRP and colour").
  - `Vendor SKU Code` and `Style ID` are optional, and GTIN is explicitly not mandatory. — [Fynd docs: Myntra attributes](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra.md)
  - Integrator docs say Myntra's packing list carries vendor article number / client SKU / EAN. — [Increff Myntra packing list](https://increff.atlassian.net/wiki/spaces/IO/pages/663521885/Myntra+Packing+List) (title/snippet only)
  - None of these appear in public PDP HTML.

### Inferences
- A Myntra matcher can't rely on codes. Use:
  - brand + normalised name, matched against the brand-site name (Myntra brand-direct names track brand naming: "Train All Day … Training Tee", "Court Vision Low FL", "A230 M Prfrm Po")
  - colour
  - manufacturer/packer address, an exact string shared with Flipkart and Amazon for the Puma tee
  - catalog year/season
  - MRP: ₹1799 for the Puma tee on both Myntra and Flipkart
  - size-chart measurements
- A practical bridge is to resolve the brand-site product (e.g. search in.puma.com by name) to get the style code, then look that code up on Flipkart and Amazon.

### Gaps
- I checked only 5 PDPs and 3 listing pages. Some categories or brands could still expose a "Product Code" in productDetails text, but none of the sampled ones did.
- I didn't check Myntra sitemaps or the mobile app API (gateway `/v2/product/<id>`), so it is unknown whether they carry vendorArticleNumber.

## EAN/GTIN availability

### Takeaway
None of the three marketplaces publicly exposes EAN/GTIN for fashion on the PDPs sampled. Codes exist only in seller back-ends (Myntra GTIN optional, Amazon GTIN or exemption). Barcodes are not a usable cross-platform key from public pages.

### Cited Findings
- **Amazon.in B0FGJ6FVZ6:** no EAN/GTIN/UPC text in the page. — live fetch
- **Flipkart (6 PDPs):** no EAN/GTIN spec row; JSON-LD has only `sku`=PID. — live fetches
- **Myntra (5 PDPs):** JSON-LD `sku`/`mpn` = styleId, with no gtin field. — live fetches
- **Myntra cataloging:** GTIN is the one exception to the "mandatory columns" rule. — [Fynd docs](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra.md)

### Inferences
- Rank cross-platform keys as:
  1. Normalised brand style code: Flipkart Style Code / Article Number ↔ Amazon Style Number / MPN / Item model number ↔ brand site URL
  2. For Myntra: brand + official product name + colour + MRP + manufacturer string

### Gaps
- I couldn't confirm whether Amazon exposes GTIN in any public surface for India fashion, because Amazon search and other PDPs were blocked or not sampled.
