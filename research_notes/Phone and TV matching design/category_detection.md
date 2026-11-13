# Robust category detection (smartphone / television / other) for Amazon.in, Flipkart, Croma listings

Method note: fixture findings come from reading the files in `/Users/sid/scruge/tests/fixtures/` with Python (read-only). Flipkart findings also use two public category pages fetched once each with plain HTTP and a browser User-Agent (2026-11-12, HTTP 200, no bot protection met). No Apify or paid API calls were made. Fixture citations use `file://` paths. Web citations use URLs.

## 1. Which structured fields in the data we already receive identify the category?

### Takeaway
Every source already carries at least one machine-assigned category field that does not depend on model names. On Amazon: `breadCrumbs`, `bestsellerRanks[].url` (holds the browse-node ID), the "Best Sellers Rank" attribute, and the `Item Type Name` attribute. On Flipkart: the PID prefix, JSON-LD `category`, `analyticsData.{superCategory,subCategory,vertical}`, and the image-URL path segment. On Croma: `breadcrumbs`, `category_l0/l1/l2`, and `specs["Mobile Type"]`. The iPhone 17 Pro capture is the hard case. It lacks every Amazon category field, so it can only be rescued by weaker signals: `Generic Name`, `productOverview` "Operating System = iOS", `Included Components`, and `Product Dimensions` / weight.

### Cited Findings

**Amazon (Apify junglee/amazon-crawler). 7 items in total: 4 in amz_apify (Galaxy S25U/S26U/S26/S26+), 2 in amz_golden (OnePlus 15, LG NU87 TV), 1 iPhone 17 Pro, 1 Puma tee.**
- `breadCrumbs` is a non-empty string in 7/8 items. Phones show `Electronics > Mobiles & Accessories > Smartphones & Basic Mobiles > Smartphones`. The TV shows `Electronics > Home Theater, TV & Video > Televisions > Smart Televisions`. The tee shows `Clothing & Accessories > Men > Sportswear > ...`. For the iPhone 17 Pro (B0FQG1LPVF) it is `""` (empty string). — [amz_apify.json](file:///Users/sid/scruge/tests/fixtures/amz_apify.json), [amz_golden.json](file:///Users/sid/scruge/tests/fixtures/amz_golden.json), [amz_iphone17pro.json](file:///Users/sid/scruge/tests/fixtures/amz_iphone17pro.json), [amz_puma_tee.json](file:///Users/sid/scruge/tests/fixtures/amz_puma_tee.json)
- `bestsellerRanks` (a structured list of `{rank, category, url}`) is present in 5/8 items: the 4 Samsung items and the tee. It is `None` in amz_golden (a trimmed fixture) and in the iPhone item. Every phone entry has `category: "Smartphones"` and `url: https://www.amazon.in/gp/bestsellers/electronics/1805560031/...`. That URL embeds the leaf browse-node ID 1805560031 = Smartphones on amazon.in. The tee's leaf is node 25965168031 "Men's Activewear T-Shirts". — [amz_apify.json](file:///Users/sid/scruge/tests/fixtures/amz_apify.json), [amz_puma_tee.json](file:///Users/sid/scruge/tests/fixtures/amz_puma_tee.json)
- The `attributes` key "Best Sellers Rank" (free text) is present in 7/8 items, including the trimmed golden items. Examples: `#3 in Electronics ...#3 in Smartphones`, and for the TV `#489 in Electronics ...#10 in Smart Televisions`. It is absent for the iPhone. — same files
- `attributes` "Item Type Name" is present in 6/8 items. All 5 phones have `Smartphone`. The TV has `NANO 4K UHD AI TV`, which is marketing text but still contains "TV". The tee has `Tees`. The iPhone does not have it. — same files
- `attributes` "Generic Name" appears only in the iPhone (`iPhone 17 Pro`, just the model name and no category) and the tee (`Tees`). It is unreliable as a category field. — [amz_iphone17pro.json](file:///Users/sid/scruge/tests/fixtures/amz_iphone17pro.json)
- `attributes` "Form Factor = Bar" and "Operating System = Android 16..." appear in all 5 Android phones. The TV has "Operating Systems = WebOS", plus TV-only keys: "Display Technology", "Total Number of HDMI Ports", "Tuner Type", "VESA Mount Standard", "Display Size Class", "Remote Control Technology". — [amz_golden.json](file:///Users/sid/scruge/tests/fixtures/amz_golden.json)
- The iPhone 17 Pro item has only 13 attributes, none of them category-bearing: Manufacturer, Country of Origin, Item model number `MG8H4HN/A`, Product Dimensions `0.87 x 7.19 x 15 cm; 206 g`, Item Weight, Net Quantity, `Included Components = USB-C Charge Cable, iPhone 17 Pro`, `Generic Name = iPhone 17 Pro`. Its `productOverview` does carry `Operating System = iOS`, `Memory Storage Capacity = 256 GB` and `RAM Memory Installed Size` (bogus 0.1 GB). `bestsellerRanks`, `productComparison`, `description` and `aPlusContent` are all null, and `manufacturerAttributes` is `[]`. `variantAttributes` has `Size = 256 GB` and `Configuration = Without Protect+`. — [amz_iphone17pro.json](file:///Users/sid/scruge/tests/fixtures/amz_iphone17pro.json)
- `categoryPageData` holds only search-position info (`pageNumber`, `productPosition`, `isSponsored`) and no category. It appears only when the item came from a search-URL input. — [amz_apify.json](file:///Users/sid/scruge/tests/fixtures/amz_apify.json)

**Croma. 5 detail items in croma_apify, 20 search-style items in croma_golden.**
- croma_apify (5/5 Samsung S26 Ultra): `breadcrumbs = ['Phones & Wearables','Mobile Phones','Android Phones', <title>]`, `category_l0='1'`, `category_l1='10'`, `category_l2='95'`, `product_type='SA'` (SA looks like a brand/sales code, not a category; unverified), `ean` present, `specs['Mobile Type']='Android Smartphone'`, `specs['Mobile Design']='Touch'`. — [croma_apify.json](file:///Users/sid/scruge/tests/fixtures/croma_apify.json)
- croma_golden (20/20) has only `brand, ean, in_stock, item_id, price, productTitle, specs, url`. It has no breadcrumbs or category codes. Its `specs` is a 5–7 key subset: phones have `Internal Storage` + `RAM` + `Screen Size in Inches` (~6.78). TVs have `Screen Size in Inches` (55) and sometimes `RAM`. Laptops have `RAM` and no screen size. The URL slug carries words such as "tv", "laptop" or "5g". — [croma_golden.json](file:///Users/sid/scruge/tests/fixtures/croma_golden.json)

**Flipkart (HTML fixtures: 3 phone PDPs/listing pages, 1 phone search, 1 tee PDP, 1 tee search, 2 TV JSON-LD stubs).**
- The PID/FSN prefix is consistent with the vertical on every page. Phone pages show only `MOB…` (107/145/104/174 occurrences). Tee pages show `TSH…`, plus `KTB…` for kids' tees on search. The TVs are `TVSHMYS2G69WGGAK` and `TVSHCAYXEGC76H9F`. The S26 listing page also contains accessory PIDs `MBP…` (mobile body panel), `ACC…` (charger) and `MCP…` (camera lens protector). — [fk_pdp.html](file:///Users/sid/scruge/tests/fixtures/fk_pdp.html), [fk_s26.html](file:///Users/sid/scruge/tests/fixtures/fk_s26.html), [fk_search_puma_tad.html](file:///Users/sid/scruge/tests/fixtures/fk_search_puma_tad.html), [fk_tv_lg_nu870.html](file:///Users/sid/scruge/tests/fixtures/fk_tv_lg_nu870.html)
- JSON-LD `Product.category` is present in all 8 fixtures. Values are `mobile`/`Mobile` for phones, `television` for both TV stubs, and `t_shirt` for the tee. JSON-LD `sku` equals the FSN. — same files
- `analyticsData` is present on full pages (not on the 2 TV stubs). Phones: `{"category":"Mobile","subCategory":"Handset","superCategory":"Mobile","vertical":"Handset"}`. Accessories on the same page: `{"category":"RestOfMobileAccessory","subCategory":"MobileSpares","vertical":"MobileBodyPanel"}`, `{"category":"MobileProtection",...,"vertical":"CameraLensProtector"}` and `{"category":"RestOfMobileAccessory","subCategory":"MobileCharging","vertical":"MobileChargingMobileCharger"}`. PDP tracking also includes `"businessUnit":"Mobiles"` and `"fsn":"MOBH…"`. — [fk_s26.html](file:///Users/sid/scruge/tests/fixtures/fk_s26.html), [fk_pdp.html](file:///Users/sid/scruge/tests/fixtures/fk_pdp.html)
- Image CDN paths carry the vertical slug: `rukmini1.flixcart.com/image/1500/1500/xif0q/television/...`, `/mobile/`, `/t-shirt/`, `/mobile-panel/`, `/battery-charger/`, `/mobile-camera-lens-protector/`. This holds in every fixture, including the 7 KB TV stubs. — same files
- The PDP links include Flipkart browse `sid` codes such as `sid=tyy,4io` (Mobiles). — [fk_pdp.html](file:///Users/sid/scruge/tests/fixtures/fk_pdp.html)
- Live check, 2026-11-12: `flipkart.com/mobiles/pr?sid=tyy,4io` returned 199 PIDs, all `MOB…`, with analyticsData `{"category":"Mobile","subCategory":"Handset","superCategory":"Mobile","vertical":"Handset"}`. `flipkart.com/televisions/pr?sid=ckf,czl` returned 139 PIDs, all `TVS…`, with analyticsData `{"category":"Television","subCategory":"Television","superCategory":"HomeEntertainmentLarge","vertical":"Television"}`. — [Flipkart mobiles](https://www.flipkart.com/mobiles/pr?sid=tyy,4io), [Flipkart televisions](https://www.flipkart.com/televisions/pr?sid=ckf,czl)
- No `BreadcrumbList` JSON-LD was found in any Flipkart fixture. The breadcrumb is rendered by an `ATLAS_BREADCRUMB` widget whose tracking carries `superCategory`/`category`. — [fk_pdp.html](file:///Users/sid/scruge/tests/fixtures/fk_pdp.html)

**Presence and reliability summary (from the fixtures above)**

| Source | Field | Present | Reliability for phone/TV |
|---|---|---|---|
| Amazon | breadCrumbs | 7/8 (missing for iPhone 17 Pro) | High when present. Exact leaf "Smartphones" / "Televisions > Smart Televisions" |
| Amazon | bestsellerRanks[].url node ID | 5/8 (2 trimmed fixtures + iPhone missing) | High. Node 1805560031 = Smartphones |
| Amazon | attributes "Best Sellers Rank" text | 7/8 | High. "in Smartphones" / "in Smart Televisions" |
| Amazon | attributes "Item Type Name" | 6/8 | High for phones ("Smartphone"); TV value is free text containing "TV" |
| Amazon | Form Factor / OS / TV-only keys | 6/8 | Medium. Good supporting evidence |
| Amazon | productOverview OS | iPhone yes | Medium. "iOS" alone could also be an iPad |
| Flipkart | PID prefix | 8/8 | High (observed). Not officially documented |
| Flipkart | JSON-LD category | 8/8 | High |
| Flipkart | analyticsData vertical/superCategory | 6/8 (not in TV stubs) | High. Also separates accessories |
| Flipkart | image path vertical | 8/8 | High |
| Croma | breadcrumbs / category_l0-2 | 5/25 (detail mode only) | High |
| Croma | specs keys and URL slug | 25/25 | Medium |

### Inferences
- For the Amazon iPhone case, the most robust non-model-name rescue is a combination. Strong supporting signals: `productOverview.Operating System ∈ {iOS, Android*}`, `Memory Storage Capacity` present, weight ≤ ~300 g and thickness < ~1.2 cm from `Product Dimensions`, and `Included Components` containing "Charge Cable". Negative signals: no "case/cover/screen guard/tempered" words, and a price above some floor. Together these say "smartphone" with no model regex. iPad needs care: iOS/iPadOS, weight > 400 g, and a display of 8 inches or more.
- A second rescue is to refetch the page or call a second extractor. The empty breadCrumbs is probably an actor parsing gap: Apple listings on amazon.in use a different, brand-store-heavy template. Not verified.
- Croma's `category_l2='95'` is an internal ID with only one value observed (Android Phones). The breadcrumb text is safer than the numeric codes.

### Gaps
- Only one Amazon TV and no Amazon accessory items are captured, so the breadcrumbs of accessory items (for example "Mobile Accessories > Cases & Covers") could not be checked on disk.
- No Croma TV detail-mode item was captured, so Croma TV `category_l*` values and breadcrumb text are unknown.
- The Croma `product_type='SA'` meaning was not found.

## 2. Amazon taxonomy: browse nodes, product_type / item_type_keyword, actor exposure, bestseller rank

### Takeaway
The Apify actor exposes the leaf browse node indirectly through the `bestsellerRanks[].url` path and the "Best Sellers Rank" text. It does not expose `product_type` (SP-API, for example CELLULAR_PHONE) or `item_type_keyword`. Browse-node ID 1805560031 (Smartphones) is confirmed from the captured data. Other node IDs could not be verified from public sources.

### Cited Findings
- `https://www.amazon.in/gp/bestsellers/electronics/1805560031/` is labelled "Smartphones" in actor output for 4 different Samsung ASINs. — [amz_apify.json](file:///Users/sid/scruge/tests/fixtures/amz_apify.json)
- Amazon Product Type Definitions (SP-API) describe each product type's attribute requirements as JSON schemas. A search operation lists available product types per marketplace, and definitions default to the LATEST version. This needs seller credentials and cannot be used from scraped data. — [SP-API Product Type Definitions](https://developer-docs.amazon.com/sp-api/docs/product-type-api-use-case-guide), [python-amazon-sp-api docs](https://python-amazon-sp-api.readthedocs.io/en/latest/endpoints/product_type_definitions.html)
- No actor field in the 54-key output schema is named productType, itemTypeKeyword or browseNode. The full key list is in the fixtures. — [amz_iphone17pro.json](file:///Users/sid/scruge/tests/fixtures/amz_iphone17pro.json)
- Web search could not confirm the amazon.in node IDs for Televisions or Mobiles & Accessories. A third-party result linked node=1389401031 as an amazon.in mobile phones page, but this was not verified. — [search results via globallinker / desidime](https://www.desidime.com/discussions/amazon-india-search)

### Inferences
- Match on the node ID in the bestseller URL rather than on text. A whitelist such as `{1805560031: smartphone}` is stable across model launches because Amazon reuses nodes. The Smart Televisions node ID can be harvested from the first TV item captured with `bestsellerRanks`. The golden TV fixture is trimmed, so the ID is not available yet.
- Leaf text matching ("Smartphones", "Televisions", "Smart Televisions", "Basic Mobiles") is the fallback when only the "Best Sellers Rank" string is present. Accessories have their own leaves (for example "Basic Cases", "Screen Protectors"), so a leaf-equality test naturally excludes them. Accessory leaf names were not verified on disk.
- `Item Type Name` mirrors the seller-entered item-type keyword. "Smartphone" is consistent, but TVs use free text, so `\btv\b|television` matching on that field is needed.

### Gaps
- Exact SP-API product type names (CELLULAR_PHONE, TELEVISION) were not confirmed from a fetched source in this session; they are believed to exist from prior knowledge.
- amazon.in browse-node IDs for Televisions (parent) and Smart Televisions were not found from a public, reliable source.

## 3. Flipkart PID prefix, verticals, and Croma codes

### Takeaway
Flipkart officially documents the FSN only as a unique product identifier "similar to ISBN". The 3-letter prefix is not documented as a category code. Empirically it maps one-to-one to the vertical on every page checked (MOB=handset, TVS=television, TSH=t-shirt, MBP=mobile body panel, ACC=charger, MCP=camera lens protector, KTB=kids t-shirt). The fields to rely on are JSON-LD `category` and `analyticsData.vertical/superCategory`, with the prefix as a cross-check.

### Cited Findings
- Flipkart seller documentation describes the FSN as "the unique product identifier for Flipkart, similar to ISBN for Books", and says products are defined under a sub-category (for example T-shirt or Mobile). It gives no prefix semantics. — [Flipkart Marketplace Seller Platform overview](https://seller.flipkart.com/api-docs/FMPlatOverview.html), [Fynd Flipkart FAQ](https://documentation.fynd.com/commerce/docs/openapi/listings-management/flipkart/faq-flipkart)
- A third-party Flipkart scraper exposes PID, category and vertical as separate fields, which implies the vertical is not derived from the PID. — [Apify parseforge/flipkart-scraper](https://apify.com/parseforge/flipkart-scraper)
- The live observations (199 MOB on Mobiles, 139 TVS on Televisions) and the analyticsData values are in Q1. — [Flipkart mobiles](https://www.flipkart.com/mobiles/pr?sid=tyy,4io), [Flipkart televisions](https://www.flipkart.com/televisions/pr?sid=ckf,czl)
- Vertical names observed: `Handset` (superCategory `Mobile`), `Television` (superCategory `HomeEntertainmentLarge`), `MobileBodyPanel`, `MobileChargingMobileCharger`, `CameraLensProtector` (superCategories `RestOfMobileAccessory` / `MobileProtection`), `MensRoundAndOthersTShirt`, `MensPoloTShirt`. — [fk_s26.html](file:///Users/sid/scruge/tests/fixtures/fk_s26.html), [fk_puma_tad_tee.html](file:///Users/sid/scruge/tests/fixtures/fk_puma_tad_tee.html)
- Croma: the category path is `Phones & Wearables > Mobile Phones > Android Phones`, with `category_l0/l1/l2 = 1/10/95`. — [croma_apify.json](file:///Users/sid/scruge/tests/fixtures/croma_apify.json)

### Inferences
- The prefix appears to be the first 3 letters of the vertical code assigned at FSN creation, so it should stay stable for a product's lifetime. Flipkart could still add new prefixes, for example foldables, which are probably still MOB. Treat it as `{MOB: smartphone, TVS: television}` and send anything else to the next layer, not straight to "unsupported".
- `MOB` may also cover feature phones (Flipkart's "Mobile" vertical includes basic phones). Use `analyticsData.subCategory` and specs if feature phones must be excluded. Not verified.

### Gaps
- No official Flipkart list of FSN prefixes or vertical codes was found.
- Croma's numeric category codes for TV and accessories are unknown.

## 4. Classifier options when structured fields are missing

### Takeaway
For a three-way label (smartphone / television / other) on titles, a small LLM with a fixed label set, or an embedding plus nearest-centroid classifier, is sufficient as the last layer. Literature on full taxonomies (thousands of leaves) reports roughly 85% weighted F1 for title-only classifiers. A coarse 3-class task with an "accessory" trap is much easier. Production systems (Shopify) use multimodal VLMs, LLM-annotated training data, judge models and taxonomy-rule validation.

### Cited Findings
- Google Product Taxonomy IDs: `267 - Electronics > Communications > Telephony > Mobile Phones`, `264 - … > Mobile Phone Accessories`, `2353 - … > Mobile Phone Cases`, `5468 - Electronics > Electronics Accessories > Electronics Films & Shields > Screen Protectors`, `404 - Electronics > Video > Televisions`, `4458 - … > Television Parts & Accessories > TV & Monitor Mounts`. — [Google taxonomy-with-ids](https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt)
- The Shopify Product Taxonomy (MIT licence, GitHub) has the category "Electronics > Communications > Telephony > Mobile & Smart Phones" (id `el-4-8-5`), with a crosswalk to Google 267. It spans 26+ verticals and 10,000+ categories. — [Shopify/product-taxonomy](https://github.com/Shopify/product-taxonomy), [WisePIM guide](https://wisepim.com/guides/product-taxonomy/shopify-product-taxonomy)
- Shopify's classifier moved through LLaVA 1.5 7B, then LLaMA 3.2 11B, then Qwen2VL 7B (FP8). It predicts category first and then attributes, runs 30M+ predictions a day, has an 85% merchant acceptance rate of predicted categories, and doubled hierarchical precision/recall over its earlier neural approach. Multiple LLM annotators are arbitrated by judge models, and predictions are validated against taxonomy rules. — [Shopify Engineering: evolution of product classification](https://shopify.engineering/evolution-product-classification)
- Rakuten Data Challenge (SIGIR eCom 2018) used 1M product titles and 26 teams. The top weighted F1 was 0.8513 (balanced-pooling LSTM) and second was about 0.84 (CNN/BiLSTM). Baselines: LinearSVC 0.81, logistic regression 0.79 (Uplab paper). — [Rakuten Data Challenge](https://sigir-ecom.github.io/ecom2018/data-task.html), [Winning paper](https://sigir-ecom.github.io/ecom18DCPapers/ecom18DC_paper_9.pdf)
- An e-commerce LLM study (2024) found that zero-shot large LLMs are not a clear win over smaller fine-tuned models (BERT/T5) on e-commerce classification tasks, and that few-shot beats zero-shot. — [Investigating LLM Applications in E-Commerce (arXiv 2408.12779)](https://arxiv.org/pdf/2408.12779)
- A 10-LLM zero-shot categorisation comparison found that larger or newer models do not guarantee higher categorisation accuracy, and it measured hallucination and "inflation" (invented categories). — [Order from Chaos (arXiv 2510.13885)](https://arxiv.org/html/2510.13885v1)
- Superlinked benchmarked NLI zero-shot, text-retrieval, image-retrieval and cross-encoder reranking approaches on Shopify's taxonomy with the HF `Shopify/product-catalogue` dataset. Accuracy numbers were not captured. — [Superlinked taxonomy classification](https://www.superlinked.com/docs/examples/taxonomy-classification.md)

### Inferences
- Use a closed label set with an explicit accessory class: `{smartphone, television, phone_accessory, tv_accessory, other}`. Map the accessory classes to "unsupported". This removes the main failure mode, a case titled "for iPhone 17 Pro" being labelled smartphone. It also avoids the "inflation" hallucination risk, because output is constrained to an enum (JSON schema or tool call).
- Cost and latency: one short title plus a few attributes is about 150–300 input tokens and a 1-token label. With a small model this is fractions of a cent and sub-second, and it is cacheable per ASIN/FSN. No pricing numbers were verified here.
- A cheap, local alternative is to embed `title + key attributes` with a small sentence-embedding model and compare to label centroids built from about 20 known examples per class. It can also be trained as a logistic regression on titles harvested from our own Flipkart/Croma captures, which carry reliable labels (PID prefix or breadcrumbs). That gives free weak supervision.

### Gaps
- No published accuracy for 3-class phone/TV/other on Indian marketplace titles was found.
- Flipkart and Meesho published categorisation papers were not retrieved in this session.
- Google/GS1 GPC brick codes for phones and TVs were not fetched.

## 5. Recommended layered design and accessory protection

### Takeaway
Order the layers as: (1) marketplace-assigned category fields, (2) taxonomy and ID codes, (3) attribute/spec fingerprint, (4) constrained LLM or embedding fallback with explicit accessory classes, (5) "unsupported". Every layer must be able to say "accessory → unsupported" before any title-keyword logic says "phone".

### Cited Findings
- Accessories sit in separate taxonomy branches in every system examined. Google has 264/2353/5468/4458, separate from 267/404. Flipkart uses `RestOfMobileAccessory` / `MobileProtection` superCategories and `MBP/ACC/MCP` prefixes. — [Google taxonomy](https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt), [fk_s26.html](file:///Users/sid/scruge/tests/fixtures/fk_s26.html)
- Production practice (Shopify) is to validate predictions against taxonomy rules and route disagreements to judges or humans. — [Shopify Engineering](https://shopify.engineering/evolution-product-classification)

### Inferences (proposed design)
1. **Structured category (decisive):**
   - Amazon: the last breadCrumbs segment, or the bestsellerRanks leaf, or the "Best Sellers Rank" text leaf. The node ID whitelist is preferred (1805560031 → smartphone). Leaf ∈ {Smartphones, Basic Mobiles?} → phone. Leaf ∈ {Televisions, Smart Televisions, Standard Televisions} → TV. Any "Accessories/Cases/Screen Protectors/Mounts" leaf → unsupported.
   - Flipkart: JSON-LD `category` ∈ {mobile} or analyticsData.vertical = Handset → phone; television → TV.
   - Croma: a breadcrumbs[1] value of "Mobile Phones" or "Televisions" decides the category. These strings are inferred from the observed phone path; the TV path is not yet observed.
2. **Codes:** Flipkart PID prefix MOB/TVS, then the image path vertical slug. Amazon `Item Type Name` normalised: smartphone, or containing tv/television.
3. **Spec fingerprint (no model names):**
   - Phone: OS ∈ iOS/Android and storage present, with RAM/storage pattern, weight < 350 g, thickness < 1.5 cm, or Croma `Mobile Type` / `Internal Storage` + screen 5.5–7.5".
   - TV: any of HDMI ports, Tuner Type, VESA, Display Size Class ≥ 24", Remote Control Technology, or screen-size-in-inches ≥ 24 with no RAM/storage-phone pattern.
   - This rescues B0FQG1LPVF: iOS, 256 GB, 206 g, 0.87 cm.
4. **Fallback classifier:** constrained LLM or embedding over title + top attributes, with labels {smartphone, television, phone_accessory, tv_accessory, other}. Accept only above a confidence threshold, cache by ID, and log for review.
5. **Unsupported** otherwise.

**Accessory guards (applied before layers 3–4):**
- Title patterns "for <brand/model>", "compatible with", "case", "cover", "tempered", "screen guard/protector", "mount", "bracket", "stand", "remote", "cable", "charger", "skin".
- Price sanity: a phone below ~₹3,000 or a TV below ~₹5,000 is suspect.
- An Amazon `Item Type Name`, or a Flipkart vertical/superCategory, containing Case/Cover/Protector/Mount/Accessory.
- Weight vs. claimed screen size: a "55 inch" item under 5 kg is likely a mount or remote.

**Self-labelling:** use layers 1–2 outputs as training labels for the layer-4 embedding classifier and as a regression test set, including every fixture listed in Q1.

### Gaps
- Thresholds (weights, prices, confidence) are proposals and have not been validated on data.
- No accessory fixtures exist on disk to test the guards. Capturing a phone case and a TV wall mount from each marketplace is recommended.
