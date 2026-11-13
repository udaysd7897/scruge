# Myntra public data for matching external fashion listings to exact Myntra products

Method: parsed the on-disk fixtures (`tests/fixtures/my_puma_tad_tee_pdp.html`, `my_search.html`, `fk_puma_tad_tee.html`, `amz_puma_tee.json`), then made 19 plain-HTTP GETs on 2026-11-12 with a desktop Chrome User-Agent: 14 to www.myntra.com and 5 to image CDNs. No login, cookies, or bypass were used. The two `/gateway/v2/*` probes returned 401, and I stopped probing the gateway at that point. Scratch copies of the pages are in `/private/tmp/claude-501/-Users-sid-scruge/9894d44e-ef13-4970-bb5d-fc2f36f1d80c/scratchpad/live/` and `.../scratchpad/img/`.

## 1. Product page (`window.__myx.pdpData`) fields and their matching value

### Takeaway
A PDP serves server-rendered JSON in `<script>window.__myx = {...}</script>`, with top-level keys `pdpData, pageName, atsa, countryCode, dataExpired, directLoad`. It is rich: Myntra style id, name, brand, article type, gender, base colour, colour-variant siblings, ~30 article attributes, per-size skuIds, seller ids, manufacturer, packer and importer strings, country of origin, MRP and price, images, and the catalog date. It contains **no brand style code (e.g. 52885601 or HJ5228-101), vendor article number, or EAN anywhere**: not in pdpData, JSON-LD, meta tags, image filenames, or size-chart data. The strongest cross-site signals are the verbatim **manufacturer/packer/importer strings** and the **brand "PRODUCT STORY" description**, which match Amazon word for word. These two signals plus `baseColour` and the article type usually narrow a match to one style. When colourways look alike, only images separate them.

### Cited Findings
**Identity fields** (Puma fixture, id 35720668) — [fixture my_puma_tad_tee_pdp.html](file:///Users/sid/scruge/tests/fixtures/my_puma_tad_tee_pdp.html)
- `id`: 35720668. `name`: "Puma Train All Day Men Breathable Training Tee". `brand.name`: "Puma". `styleType`: "P". `landingPageUrl`: "tshirts/puma/puma-train-all-day-men-breathable-training-tee/35720668/buy".
- `analytics`: `{"articleType":"Tshirts","subCategory":"Topwear","masterCategory":"Apparel","gender":"Men","brand":"Puma","colourHexCode":null}`. This is the best field set for category and gender gating.
- `baseColour`: "Black". `colours[]` lists the **colour-variant siblings** with styleId, label, URL, and thumbnail: 35720666 "Green / Orange", 35720667 "Blue / Yellow", 35902832 "Yellow / Black", 36087993 "Grey / Black", 40567926 "White / Black", 44935701 "Purple", 44935702 "Blue". So a single PDP fetch exposes the whole colour family. The label gives the two-tone colour name, which is more specific than `baseColour`.
- `articleAttributes` (34 keys), for example: Fabrics "Polyester", Fit "Regular Fit", Neck "Round Neck", Sleeve Length "Short Sleeves", Patterns "Solid", Print or Pattern Types "Brand Logo", Sport "Training or Gym", Weave Type "Knitted", Occasions "Sports", Multipack Set "Single", Number of Items "1".
- `catalogAttributes`: `{"catalogDate":"1752681145000","season":"fall","year":"2025"}`. The catalog date is epoch ms (16 Jul 2025), roughly the listing date. It is useful to rank new and old releases of the same name.
- `manufacturer` (top level): "Aryan Apparels Private Limited  Plot no 266 Sector 06 IMT Manesar  122051 , India". `countryOfOrigin`: "India".
- `sizes[]`: each entry has `skuId` (XS 114213721, S 114213722, M 114213723, L 114213724, XL 114213725, XXL 114213726, 3XL 114213727), `label`, garment `measurements` (XS Chest 35.5 in, Front Length 27.6 in, Across Shoulder 15.6 in), and `sizeSellerData[]`. Each `sizeSellerData` entry has `sellerPartnerId` 6206, mrp 1799, discountedPrice 719, `availableCount` 501, `countryOfOrigin` ["India"], `manufacturerInfo`, `importerInfo` (""), and `packerInfo` "PUMA Sports India Pvt Ltd., 496, Krrish Towers, Mahadevapura Main road, Next to Hewlett Packard service gate, Mahadevapura, Bangalore, 560048".
- `sellers[]`: 6206 "Puma Sports India Pvt. Ltd.(NSCM)" with full address, and 4027 "Omnitech Retail" (display name "Consulting Rooms Pvt Ltd"). `buyButtonSellerOrder` maps each skuId to its sellers.
- `mrp` 1799. `price` `{"mrp":1799,"discounted":719}`. `selectedSeller.discount.label` "(60% OFF)".
- `descriptors[]` / `productDetails[]` / `productContentGroupEntries[]` hold the description HTML. Here it is "PRODUCT STORY<p>Designed for active comfort, this training tee is built with breathable fabric and moisture-wicking technology…</p>FEATURES & BENEFITS… DETAILS<ul><li>Fabrics Type: Knitted</li>…<li>Main Material: Recycled Polyester</li>", plus `size_fit_desc` ("model (height 6') is wearing size M") and `materials_care_desc`.
- `ratings`: averageRating 4.56, totalCount 7588, reviewInfo.reviewsCount "807", with top reviews.
- `media.albums[0].images[]` (7 images) each have `src`/`secureSrc` templates such as `https://assets.myntassets.com/h_($height),q_($qualityPercentage),w_($width)/v1/assets/images/35720668/2025/7/29/9195d851-…1753794067116-Puma-Train-All-Day-Mens-Breathable-Training-Tee-490175379406-1.jpg`, plus a raw `imageURL`. `media.videos[]` has a Brightcove id "rw-35720668_cae700".
- Other keys that do not help matching: `sizechart` (`sizeRepresentationUrl` = a generic "Tshirts_men.png"), `crossLinks` (filter URLs such as `tshirts?f=Brand:Puma::Gender:men`), `relatedStyles` (null), `plaStyles` (ad-sponsored similar styles), `sizeRecoLazy.action` "/product/35720668/size/recommendation", `sizes[].action` "/product/35720668/related/XS?co=1", `systemAttributes`, `tagData`, `urgency`, `flags`, `serviceability`, `offers`, `discounts`, `shoppableLooks`.
- No field named styleGroupId or similar exists. The `colours[]` array is the only sibling grouping.

**Brand style code / EAN are absent.** Grepping the Puma PDP for "52885601" returns 0 hits. Grepping the live Nike PDP 38159155 for "HJ5228" also returns 0 hits — [fixture](file:///Users/sid/scruge/tests/fixtures/my_puma_tad_tee_pdp.html), [live PDP](https://www.myntra.com/38159155)
- JSON-LD `Product` block: `"sku":"35720668","mpn":"35720668"`. Both are the Myntra id, not the brand MPN. The block also has name, image, offers (INR 719, InStock, URL) and brand "Puma". Separate JSON-LD blocks hold Organization and BreadcrumbList (Clothing > Men > Tshirts > Puma) — [fixture](file:///Users/sid/scruge/tests/fixtures/my_puma_tad_tee_pdp.html)
- Meta `description`: "Buy Puma Train All Day Men Breathable Training Tee - Tshirts for Men from Puma at Rs. 719. Style ID: 35720668". `keywords`, `og:*` and `twitter:*` repeat the name, category and gender. `<link rel=canonical>` is the /buy URL — [fixture](file:///Users/sid/scruge/tests/fixtures/my_puma_tad_tee_pdp.html)
- The Puma image filenames contain "490175379406" in all 7 images. This is not the Puma style number 52885601, and I could not determine its meaning.

**Cross-site agreement (Amazon B0FGJ6FVZ6 vs Myntra 35720668)** — [fixture amz_puma_tee.json](file:///Users/sid/scruge/tests/fixtures/amz_puma_tee.json)
- Amazon attributes give "Style Number"/"Manufacturer Part Number" 52885601 and Model Name "TAD ESSENTIAL | GYM_2891". Its Manufacturer string "Aryan Apparels Private Limited Plot no 266 Sector 06 IMT Manesar 122051" is the same as Myntra's apart from whitespace and the ", India" suffix. Its Packer Contact Information "PUMA Sports India Pvt Ltd., 496, Krrish Towers, Mahadevapura Main road…560048" matches Myntra `packerInfo` exactly. Country of origin is India on both. Amazon's description starts "Product Story : Designed for active comfort, this training tee is built with breathable fabric and moisture-wicking technology…", which is the same brand copy as on Myntra. Colour is Black on both. Amazon also lists "Recycled Materials" and "Signature Style" bullets that Myntra omits.
- Flipkart has the style code as a "Style Code: 52885601" spec row, and its variant image filenames embed it (e.g. `xs-52885635-puma-original-…jpeg`, `xl-52885699-puma-original-…jpeg`). Its manufacturer string is also "Aryan Apparels Private Limited Plot no 266 Sector 06IM…" — [fixture fk_puma_tad_tee.html](file:///Users/sid/scruge/tests/fixtures/fk_puma_tad_tee.html)

**Nike V5 RNR (live)** — [https://www.myntra.com/38159155](https://www.myntra.com/38159155), [https://www.myntra.com/38159174](https://www.myntra.com/38159174)
- 38159155: name "Nike V5 RNR Men's Shoes"; analytics Casual Shoes / Shoes / Footwear / Men; baseColour White; mrp 7995, discounted 6796; manufacturer "SUMBER MASANDA JAYA, PT. Jl Raya Bangsri Desa Bangsri Brebes JT 52253"; countryOfOrigin Indonesia; importerInfo "NIKE INDIA PRIVATE LIMITED, GROUND &1ST FLOOR, OLYMPIA BUILDING, NO.66/1, BAGMAN…"; seller 22534 "Nike India Private Limited"; articleAttributes Collection Name "<p>V5 RNR</p>", Materials "Mesh", Sole Material "PU", Type "Sneakers"; catalogDate 1763980323000 (24 Nov 2025); 11 ratings; **`colours`: null**, so Nike exposes no sibling list.
- 38159174 is a second white "Nike V5 RNR Men's Shoes". Its pdpData has the same name, brand, analytics, baseColour, mrp/price, manufacturer, importer, seller and season. It differs only in id, skuIds (121814124…), images, Materials "Textile" vs "Mesh", a typo in the description ("every day" vs "everyday"), catalogDate (+372 s) and ratings (53). Its image shows a white/black/silver colourway, while 38159155 is all white/silver. Images were the only clear separator.
- A bare `https://www.myntra.com/<styleId>` returns the full PDP (200, ~97 KB, title "Buy Nike V5 RNR Men's Shoes - Casual Shoes for Men 38159155 | Myntra"). For a non-existent id, `/52885601`, Myntra returns 200 with `pageName:"Pdp"` and `pdpData: null` — [https://www.myntra.com/52885601](https://www.myntra.com/52885601)

### Inferences
- A brand style code can never be matched directly on Myntra. Matching has to rely on name, brand and articleType/gender, then baseColour or the `colours[].label`, then the manufacturer/packer/importer strings, then description text, and finally images.
- Manufacturer and packer strings are strong same-product evidence. They are not unique to a style, though: colour siblings and other styles from the same factory will share them. They work as confirmers, not as discriminators between colourways.
- When colourways share a name and a "White" baseColour (Nike 38159155 vs 38159174), only image comparison, or the hex fields in search JSON (identical here), can separate them. Getting the HJ5228-101 colourway right needs a vision check against the brand image from Amazon.
- `pdpData: null` is a cheap existence check for a candidate id.

### Gaps
- Meaning of "490175379406" in the Puma image filenames. It might be an internal vendor or upload id, but this is untested; comparing a sibling colour's filenames would show whether it varies per colour.
- I did not check whether any Myntra PDP ever exposes an EAN or `styleCode` (e.g. some brands put it in the name or description). Only 3 PDPs were examined.
- I did not test `/product/{id}/related/{size}` or `/product/{id}/size/recommendation`, to stay within the request budget.

## 2. Search: URL forms, embedded JSON, pagination, rank of the exact item

### Takeaway
Search pages are plain GET HTML at `https://www.myntra.com/<slug>?rawQuery=<query>`. They embed `window.__myx.searchData.results.products[]` (50 per page), with productId, name, brand, colour, colour hexes, price, sizes, catalogDate, articleType and images. Searching the **exact Myntra product name** found both targets in the top 5: Puma at rank 1, Nike V5 RNR at rank 4. Adding brand/gender/colour filters (`f=`) cut the Nike result set to 3 items with the target at rank 2. Short or style-code queries fail: "nike v5 rnr" was parsed as running shoes, and "HJ5228-101" returned unrelated watches.

### Cited Findings
- `/puma-train-all-day-men-breathable-training-tee?rawQuery=Puma%20Train%20All%20Day%20Men%20Breathable%20Training%20Tee` → totalCount 408. Rank 1 was **35720668** (Black, ₹719). Ranks 2–8 were all 7 colour siblings (35720666 Green, 35720667 Blue, 44935702, 44935701, 36087993, 35902832, 40567926) — [live](https://www.myntra.com/puma-train-all-day-men-breathable-training-tee?rawQuery=Puma%20Train%20All%20Day%20Men%20Breathable%20Training%20Tee)
- `/nike-v5-rnr?rawQuery=nike%20v5%20rnr` → totalCount 775. No V5 RNR in the top 10, and the first V5 item was at rank 38. `keywords.userQuery` shows the query was parsed as Brand=nike, Article Type=casual/sports shoes, Sport=**running** ("rnr" became running) — [live](https://www.myntra.com/nike-v5-rnr?rawQuery=nike%20v5%20rnr)
- `/nike-v5-rnr-mens-shoes?rawQuery=Nike%20V5%20RNR%20Men's%20Shoes` → totalCount 27, hasNextPage false. Ranks 1–7 were all "Nike V5 RNR Men's Shoes" variants: 46383989 Black, 47153224 White, 47153201 Ripstop Grey, **38159155 White (rank 4)**, 38159174 White, 38159300 Black, 38750824 Black. Kids and women versions came after — [live](https://www.myntra.com/nike-v5-rnr-mens-shoes?rawQuery=Nike%20V5%20RNR%20Men's%20Shoes)
- `/casual-shoes?f=Brand%3ANike%3A%3AGender%3Amen%2Cmen%20women%3A%3AColor%3AWhite&rawQuery=v5%20rnr` → totalCount 3: 47153224, **38159155**, 38159174. `appliedParams.filters` echoes Brand=[Nike], Gender=[men, men women], Color=[White]. Filter syntax is `f=Key:Value1,Value2::Key2:Value`. Filter ids seen include `Brand`, `Gender` (men, women, boys, girls), `Color` (plain names such as "Black", "Off White"; PDP crossLinks use `Color:Black_36454f`), `Categories`, `size_facet`, `Country of Origin`, plus secondaries like `Materials` and `Sport` — [live](https://www.myntra.com/casual-shoes?f=Brand%3ANike%3A%3AGender%3Amen%2Cmen%20women%3A%3AColor%3AWhite&rawQuery=v5%20rnr); [fixture my_search.html](file:///Users/sid/scruge/tests/fixtures/my_search.html)
- Style-code search: `/hj5228-101?rawQuery=HJ5228-101` → totalCount 664,304, with HARBOR watches and Roadster trackpants in the top 10. Style codes are not indexed — [live](https://www.myntra.com/hj5228-101?rawQuery=HJ5228-101). A purely numeric slug (`/52885601?rawQuery=52885601`) is routed to the PDP handler, not search — [live](https://www.myntra.com/52885601?rawQuery=52885601)
- Per-product search JSON keys: `productId, productName, product, brand, additionalInfo` (name without brand, e.g. "V5 RNR Men's Shoes"), `primaryColour, colourVariants[]` (styleId, baseColourHex, colour1Hex, colour2Hex, imageUrl), `mrp, price, discount, discountDisplayLabel, sizes` ("5,6,7,…"), `inventoryInfo[]` (skuId, label, inventory), `buyButtonWinnerSkuId/SellerPartnerId, gender, category, articleType{typeName}, subCategory, masterCategory, catalogDate, season, year, rating, ratingCount, searchImage, images[]` (views: default, front, back, left, right, top, bottom, search), `isPLA, adId, landingPageUrl, systemAttributes, colorVariantAvailable, relatedColoursCount` — [fixture my_search.html](file:///Users/sid/scruge/tests/fixtures/my_search.html). In the live Nike results, 38159155 and 38159174 had identical primaryColour (White), hexes (#f2f2f2/#f2f2f2/#b3b3b3), MRP/price, catalogDate and sizes. Only `searchImage` differed — [live](https://www.myntra.com/nike-v5-rnr-mens-shoes?rawQuery=Nike%20V5%20RNR%20Men's%20Shoes)
- Result-level keys: `totalCount, hasNextPage, filters{primaryFilters, secondaryFilters}, appliedParams, keywords` (query-understanding parse), `querySubstitution, sortOptions` (new, price_desc, popularity, discount, price_asc, Customer Rating), `plaProducts, relatedSearches`. `searchData.nextPaginationContext` is a JSON string with `paginationCacheKey` and a base64 `plaContext` (organicOffset 50). `seo.canonicalUri` is also present — [fixture my_search.html](file:///Users/sid/scruge/tests/fixtures/my_search.html)
- Pagination: `&p=2` on the Puma query returned 200 with 50 products. However totalCount changed (408 to 340), and page 2 repeated page-1 items: 35720666 at page 2 rank 1, plus 40567926 and 44935702. A stateless `p=2` is therefore not a clean continuation — [live](https://www.myntra.com/puma-train-all-day-men-breathable-training-tee?rawQuery=Puma%20Train%20All%20Day%20Men%20Breathable%20Training%20Tee&p=2)
- The Amazon title for the Puma tee is generic ("Puma Men Polyester Solid Regular Fit T-Shirt"). The distinctive phrase is in the Amazon description ("Train All Day" is absent from the Amazon title), and Amazon's model name is "TAD ESSENTIAL" — [fixture amz_puma_tee.json](file:///Users/sid/scruge/tests/fixtures/amz_puma_tee.json)

### Inferences
- Recommended query recipe: brand + model or collection name + gender + product type, in Myntra's naming style, e.g. "Nike V5 RNR Men's Shoes". Add `f=Brand:<b>::Gender:<g>::Color:<c>` to shrink the set. Avoid style codes and abbreviations ("rnr", "TAD") that the query parser may reinterpret.
- One page of 50 is usually enough. When totalCount is small (≤ ~30) after filtering, the whole candidate family is on page 1. Deep pagination via `p=` is unreliable.
- For the Puma case the Amazon title alone would be a poor query. The pipeline needs a phrase taken from the Amazon description or model name ("Train All Day"), or a Myntra-style name produced by an LLM.

### Gaps
- I did not test whether `sort=` or `rows=` work as query params on the HTML search page.
- Rank stability across sessions and personalisation (`upsInfo.isPersonalized` was false) is untested.

## 3. Hidden/JSON endpoints

### Takeaway
The JSON gateway endpoints that scrapers reference are **not** open to a plain GET. `/gateway/v2/product/{id}` and `/gateway/v2/search/{slug}` both returned **HTTP 401 with an empty body** without session cookies, and per the constraints I stopped probing there. Server-rendered HTML pages carrying `window.__myx` are the usable public channel. They give the same data as the JSON APIs for both PDP and search.

### Cited Findings
- `GET https://www.myntra.com/gateway/v2/product/38159155` (Accept: application/json, browser UA) → 401, 0 bytes — [endpoint](https://www.myntra.com/gateway/v2/product/38159155)
- `GET https://www.myntra.com/gateway/v2/search/nike-v5-rnr-mens-shoes?rawQuery=…&rows=50&o=0` → 401, 0 bytes — [endpoint](https://www.myntra.com/gateway/v2/search/nike-v5-rnr-mens-shoes?rawQuery=Nike%20V5%20RNR%20Men%27s%20Shoes&rows=50&o=0)
- A third-party Apify actor's sample output shows scrapers calling `https://www.myntra.com/gateway/v2/search/men-tshirts?rows=50&pageNo=1&o=0`. Search snippet only, not verified — [Apify listing via search](https://apify.com/automation-lab/myntra-catalog-monitor.md). Open-source references: [architrixs/myntra_scraper](https://awesome.ecosyste.ms/projects/github.com%2Farchitrixs%2Fmyntra_scraper) (2021, T-shirts only), [shibam120302/myntra-product-scraper](https://awesome.ecosyste.ms/projects/github.com%2Fshibam120302%2Fmyntra-product-scraper)
- Relative action paths in pdpData point to more internal APIs: `/product/{id}/size/recommendation`, `/product/{id}/related/{size}?co=1`, `/v1/shoppablelooks/style/{id}?…`, and `/free-gift-list?baseStyleId=…`. All were untested — [fixture](file:///Users/sid/scruge/tests/fixtures/my_puma_tad_tee_pdp.html)
- All 14 www.myntra.com GETs (HTML PDP, search, ToU, robots) returned 200 with full SSR data, and none hit a bot check — results above.

### Inferences
- Colour variants come from the PDP's `colours[]` (when present) and the search JSON's `colourVariants[]`. No separate open "colour variants API" is needed.
- The 401 suggests the gateway needs session cookies or tokens that the web app sets. Getting them programmatically would be circumventing access control, so it is out of scope.

### Gaps
- I did not test whether "More Similar Products" or related-style data is reachable without login.
- Bot-protection thresholds at higher volume are unknown. 14 requests over a few minutes were fine.

## 4. Image CDN (assets.myntassets.com) and cross-site image overlap

### Takeaway
Myntra images live on `assets.myntassets.com` and resize on the fly with a Cloudinary-style transform segment before `/v1/`: `h_400,q_80,w_300` or just `w_300,q_80`. That gives cheap ~7–10 KB 300×400 thumbnails. For Puma, Myntra uses its **own photo shoot**: a different model and a grey background. Amazon and Flipkart both use **Puma's global studio images** (same model; Flipkart adds a gradient and an "authorised seller" badge). So pixel or perceptual hashing between Myntra and Amazon will fail for this item, and product-level visual similarity is needed. For Nike, Myntra shows Nike-style studio pack shots (shoe pair on white).

### Cited Findings
- URL forms seen:
  - Templated: `https://assets.myntassets.com/h_($height),q_($qualityPercentage),w_($width)/v1/assets/images/<styleId>/<yyyy>/<m>/<d>/<uuid><epochms>-<Name-Slug>-<num>-<n>.jpg` (older style, with the style id and name in the path).
  - Newer: `http://assets.myntassets.com/assets/images/2025/NOVEMBER/21/NICokFUG_8373a0db18e44dec93d24d3e8b522c0e.jpg` (date plus a random token, with no id or name).
  - JSON-LD uses `h_1440,q_100,w_1080`. The og:image uses `h_200,w_200,c_fill,g_auto/h_1440,q_75,w_1080`. Sources: [fixture](file:///Users/sid/scruge/tests/fixtures/my_puma_tad_tee_pdp.html), [live PDP](https://www.myntra.com/38159155)
- Tested resize requests (all 200, image/jpeg, 300×400):
  - [Puma image 1 at h_400,q_80,w_300](https://assets.myntassets.com/h_400,q_80,w_300/v1/assets/images/35720668/2025/7/29/9195d851-5bc8-4868-aa84-5fb9e98150fc1753794067116-Puma-Train-All-Day-Mens-Breathable-Training-Tee-490175379406-1.jpg) → 10.5 KB
  - [Nike image at h_400,q_80,w_300](https://assets.myntassets.com/h_400,q_80,w_300/v1/assets/images/2025/NOVEMBER/21/NICokFUG_8373a0db18e44dec93d24d3e8b522c0e.jpg) → 6.9 KB. The transform also works on the newer path if `/v1/` is inserted.
  - [Width-only w_300,q_80](https://assets.myntassets.com/w_300,q_80/v1/assets/images/2025/NOVEMBER/21/YQGeAg33_ff91ea391f9047c4acc0278b1ecafa84.jpg) → 9.1 KB, still 300×400
- Visual comparison of the Puma black tee (viewed by me):
  - Myntra image 1: a light-skinned model with his hands behind his back, grey studio background, red outline Puma cat logo.
  - [Amazon 519awlkUeCL](https://m.media-amazon.com/images/I/519awlkUeCL._SL400_.jpg): a different, dark-skinned model on a white background.
  - [Flipkart imahq63m5a9jxmr2](https://rukminim2.flixcart.com/image/416/416/xif0q/t-shirt/s/x/r/-original-imahq63m5a9jxmr2.jpeg?q=70): the same Puma global shoot as Amazon (dark-skinned model), on a gradient background with a "BRAND AUTHORISED SELLER" badge.
  - Same garment and logo in all three; different photos.
- Nike V5 RNR: Myntra 38159155 image 1 is an all-white/silver pair on white. 38159174 image 1 is white with black Swoosh and silver overlays. Visual inspection separates the two colourways easily — [img 1](https://assets.myntassets.com/h_400,q_80,w_300/v1/assets/images/2025/NOVEMBER/21/NICokFUG_8373a0db18e44dec93d24d3e8b522c0e.jpg), [img 2](https://assets.myntassets.com/w_300,q_80/v1/assets/images/2025/NOVEMBER/21/YQGeAg33_ff91ea391f9047c4acc0278b1ecafa84.jpg)
- Search JSON already gives `searchImage` plus up to 8 view images per product, and colour-sibling thumbnails sit in `colours[].image`. So candidates can be compared visually without fetching each PDP — [fixture my_search.html](file:///Users/sid/scruge/tests/fixtures/my_search.html)

### Inferences
- Use small transformed thumbnails (`w_300,q_80`) for cheap visual checks. Compare at the product level, with a vision LLM or embeddings focused on the garment, logo and colour. Do not rely on exact or near-duplicate hashing. Hashing may work for footwear and brand pack shots (as with Nike), but it did not work for Myntra-shot apparel.
- Because Amazon and Flipkart shared the same Puma studio image here, an Amazon-to-Flipkart hash match is plausible, but Amazon-to-Myntra is not.

### Gaps
- No pHash numbers were computed (PIL is not installed in the environment), so the similarity judgements are visual only.
- I did not fetch Nike's Amazon image for HJ5228-101, so I could not confirm whether Myntra's Nike shots are identical to Amazon's.

## 5. Robots.txt and Terms of Use

### Takeaway
robots.txt (`User-agent: *`, `Allow: /`) does not block product pages (`/<cat>/<brand>/<slug>/<id>/buy`, `/<id>`) or slug search pages. It disallows `*/filters*`, `*/size-chart/*`, `*ajax_search*`, `/user/*`, `*/brand/*` and `/proxy/apify/*`, among others. It has no `/gateway` rule and no crawl-delay. However, Myntra's Terms of Use expressly forbid any "page-scrape", "robot", "spider" or other automatic means to access or monitor the platform. Automated access is contractually prohibited whatever robots.txt says.

### Cited Findings
- robots.txt (738 lines) starts `User-agent: *` / `Allow: /`. Its disallow list includes `*/name/`, `*/filters*`, `*/size-chart/*`, `*ajax_search*`, `*captcha*`, `/user/*`, `*/brand/*`, `*/designer/*`, `*/search/track/*`, `/zara/*`, and `Disallow: /proxy/apify/*`. It ends with `Sitemap: https://www.myntra.com/sitemap-index.xml.gz`. It has no Crawl-delay and no gateway rule — [robots.txt](https://www.myntra.com/robots.txt)
- Terms of Use: "You shall not use any "deep-link", "page-scrape", "robot", "spider" or other automatic device, program, algorithm or methodology, or any similar or equivalent manual process, to access, acquire, copy or monitor any portion of the Platform or any Content, or in any way reproduce or circumvent the navigational structure or presentation of the Platform or any Content, to obtain or attempt to obtain any materials, documents or information through any means not purposely made available through the Platform." — [Myntra Terms of Use](https://www.myntra.com/termsofuse)
- Third-party scraper vendors only say users are responsible for complying with Myntra's ToS — [search results summary of Apify pages](https://apify.com/parseforge/myntra-india-scraper)

### Inferences
- `f=` filter query params are not covered by the `*/filters*` path rule, which targets a `/filters` path segment. Even so, the ToS clause covers any automated access. The app should keep Myntra lookups low-volume and user-triggered, and the product owner should accept the ToS risk explicitly.
- The sitemap index could serve as an id discovery source, but it was not fetched.

### Gaps
- I did not fetch the sitemap contents or check whether they list PDP URLs with ids.
- I did not assess Indian legal enforceability.
