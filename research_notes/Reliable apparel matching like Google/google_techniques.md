# How Google matches the same product across retailers and finds similar products (Shopping Graph, Lens, price comparison)

Research date: 2026-11-13. "Documented" means Google's own pages say it. "Inference" is my reasoning and is labelled as such. Google has never published a technical spec for how the Shopping Graph clusters offers, so the clustering mechanics below are pieced together from Merchant Center rules, Google blog posts and Google Research papers.

## 1. Shopping Graph: how offers are clustered into products, and how apparel variants are grouped

### Takeaway
Google's public documentation makes **unique product identifiers (GTIN, then brand + MPN)** the main key for matching offers across sellers. **item_group_id plus the variant attributes** (color, size, pattern, material, age_group, gender) define the variant structure, with each colour/size variant treated as its own product with its own GTIN. Google does not document how it clusters offers that have no identifiers, which is common for marketplace apparel. It only says such products are "difficult to classify" and that matching "can't be assured".

### Cited Findings
- The Shopping Graph is described as an "ML-powered, real-time dataset of products and sellers", "a similar model" to the Knowledge Graph, with >35B listings. Data comes from Merchant Center feeds plus brand/retailer info "across the web" (images, descriptions, reviews, YouTube). It stores availability, reviews, materials, colors and sizes, and uses ML to infer attributes such as "packability". It does **not** explain how the same product is linked across sellers. — [Google blog, 2023-02-07](https://blog.google/products/shopping/shopping-graph-explained/)
- The Shopping Graph has ">50 billion product listings… each with details like reviews, prices, color options, and availability", and ">2 billion of those product listings are refreshed every hour". — [Google blog, I/O, 2025-05-20](https://blog.google/products/shopping/google-shopping-ai-mode-virtual-try-on-update/). A later figure of 60B listings is reported secondhand in [PPC Land](https://ppc.land/googles-heiko-hotz-pitches-60-billion-listings-as-fuel-for-shopping-agents/) (not verified against Google's primary source). PPC Land also notes Google has published no technical spec for the graph — [PPC Land](https://ppc.land/shopping-graph/)
- GTIN help page: "A GTIN helps us make your ad or unpaid listing easier for your customers to find"; "Accurate matching to products can't be assured when GTIN is missing"; "Products submitted without any unique product identifiers are difficult to classify"; **each variant (color/size) needs its own GTIN**; private-label items without a GTIN should send brand + MPN; "Only provide a GTIN if you're sure it's correct". Restricted prefixes (02, 04, 2) and coupon prefixes (05, 98, 99) are rejected, and check digits are validated. — [Merchant Center Help: GTIN](https://support.google.com/merchants/answer/6324461) (accessed 2026-11)
- If offers share a GTIN but have conflicting attributes (e.g. different item_group_id), Merchant Center raises the "Same GTIN but differing value" issue. The fix: "Submit the same value for all products with the same GTIN". — [Merchant Center Help 12473099](https://support.google.com/merchants/answer/12473099). Different products that share a GTIN *and* the same variant attributes are treated as ambiguous and disapproved — [Merchant Center Help: Duplicate GTIN](https://support.google.com/merchants/answer/12470642?hl=en); enforcement covered by [SERoundtable](https://www.seroundtable.com/google-merchant-center-enforce-unique-product-identifiers-32087.html)
- item_group_id rules:
  - Variants are defined by **color, pattern, material, age_group, gender, size** (plus a "variant option" attribute for other dimensions).
  - Each variant is submitted as its own product sharing one item_group_id. Google's T-shirt example has 3 sizes × 3 colors = 9 items.
  - Shoes are handled the same way.
  - Don't use it for non-variants (e.g. a suit sold as a set), don't reuse IDs across products, and keep IDs stable.
  - IDs are case-insensitive, 1–50 chars.
  - Each variant gets its own landing URL, and grouping should match what the landing page lets the user pick.
  - Source: [Merchant Center Help: item_group_id](https://support.google.com/merchants/answer/6324507) (accessed 2026-11)
- GS1 UK published "Google changes in March 2026: how to get GTINs and product IDs right", which suggests tighter identifier enforcement in 2026 — [GS1 UK](https://www.gs1uk.org/insights/news/Google-changes-in-March-2026-how-to-get-GTINs-and-product-IDs-right). The page returned 403, so I could not read its contents.

### Inferences
- In Google's model, the **product** is identified at the variant level: GTIN = one colour + one size. **item_group_id is the "style" level** (the parent across colours and sizes). Price comparison works at the GTIN level. "More options/colours" works at the group level. For an app, the equivalent split is **style match** (same model/design) vs **exact variant match** (same colour; size usually ignored for price comparison).
- Google does not say that **neck style (polo vs crew), sleeve length or print** are variant attributes. In its taxonomy, a polo and a crew-neck tee from the same brand are *different products*, not variants. Only colour/size/pattern/material/gender/age_group can vary inside a group. An app should therefore treat a neckline or sleeve mismatch as a hard "different product".
- Indian marketplaces (Amazon.in, Flipkart, Myntra) rarely expose GTINs on apparel pages. Google's own wording ("can't be assured", "difficult to classify") suggests even Google relies on weaker signals (brand + MPN/style code, title, images) for this inventory. Identifier-first matching only helps when a style code/MPN can be pulled from the listing (common for sneakers, e.g. Nike style codes like "DD1391-100"; rare for unbranded tees).

### Gaps
- No Google source describes the clustering algorithm for offers without identifiers (title/image-based). I found no Google engineering blog on Shopping Graph entity resolution for 2020–2026.
- I could not read the March 2026 GS1 UK / Merchant Center change details (page returned 403).

## 2. Google Lens / visual product search: exact match vs visually similar, and attributes

### Takeaway
Lens uses two separate paths. **Exact identification** comes from identifiers (barcode/OCR) or from finding the same image/product. **Visually similar** results come from embedding-based retrieval, which for fashion Google explicitly describes as "stylistically similar". Google Research's published work focuses on **instance-level universal image embeddings**, and it calls out that the product domain needs "very fine-grained" discrimination between similar items from different brands.

### Cited Findings
- 2018: Lens "recognizes over 1 billion products". It uses OCR plus Search's language/spell-correction models to match barcodes, QR codes, ISBNs and other alphanumeric identifiers to Google Shopping listings. For outfits and home decor it "recommends items that are stylistically similar" (not exact). It was trained on labelled images, including datasets that look like smartphone photos. — [VentureBeat, 2018-12-19](https://venturebeat.com/ai/google-lens-now-recognizes-over-1-billion-products)
- Current Lens results have a filter bar with **"Exact matches"** and **"Visual matches"** tabs. Visual matches return title, source, price, rating and in_stock. Exact matches may carry price/stock. — [SerpApi Lens Visual Matches API](https://serpapi.com/google-lens-visual-matches-api); [SerpApi Lens Exact Matches API](https://serpapi.com/google-lens-exact-matches-api); [SerpApi blog on the new Lens layout](https://serpapi.com/blog/scraping-google-lens-new-layout-visual-matches.md) (third-party descriptions of Google's UI, not Google docs)
- In Oct 2024 Lens was updated so that visual matches show specific product info, including price across retailers — [Retail Brew, 2024-10-03](https://retailbrew.com/stories/2024/10/03/google-lens-gets-a-precise-tweak-before-the-holidays-to-push-shopping)
- "Shop the look" (built on the Shopping Graph) surfaces styling ideas and similar products — [Google blog, 2023-02-07](https://blog.google/products/shopping/shopping-graph-explained/)
- Google Research + Google Lens ran the **Google Universal Image Embedding Challenge** (Kaggle, 2022): one embedding model for instance-level recognition across domains including apparel and products. Google says the product domain must "distinguish very fine-grained details between similar-looking products from different brands". — [Google Research blog](https://research.google/blog/introducing-the-google-universal-image-embedding-challenge/)
- The follow-up **UnED** benchmark has 241k queries, 1.4M index images and 2.8M training images across 8 domains, including products/apparel. It drew >1k researchers and 21k submissions. — [arXiv 2309.01858 (Ypsilantis et al., Google, 2023)](https://arxiv.org/abs/2309.01858); [Google Research pub page](https://research.google/pubs/pub52604)
- Virtual try-on ("try it on") launched in Search Labs on 2025-05-20 and covers "billions of apparel items" in the Shopping Graph — [Google blog, 2025-05-20](https://blog.google/products/shopping/google-shopping-ai-mode-virtual-try-on-update/)

### Inferences
- The Exact vs Visual split in Lens suggests a **threshold or second-stage decision**, not one ranked list. My working model is: exact = same product entity in the Shopping Graph (identifier match, or a near-duplicate image of the same catalog item); visual = nearest neighbours in embedding space. An app can copy this. Show "same product" only when a stricter test passes (identifier match, or very high image similarity plus brand and key-attribute agreement). Everything else goes under "similar".
- Using attributes (neckline, sleeve, pattern) as filters for "similar" is consistent with Google's attribute-rich graph ("colors and sizes", inferred attributes). However, I found **no Google document** describing Lens using neckline/sleeve as explicit verification filters. Treat that as an inference.

### Gaps
- I found no Google paper that describes the production Lens shopping pipeline (detector → embedding → index → re-rank) end to end. I also found no public Google detail on MUM's role in Lens shopping beyond marketing posts.

## 3. Google Research / DeepMind models relevant to product matching

### Takeaway
Google's published building blocks are contrastive image–text dual encoders (ALIGN → CoCa → SigLIP/SigLIP 2) and universal instance-level image embeddings (UnED). Its developer product is now **Gemini Embedding 2** (multimodal). There is no published Google paper titled "Universal Product Matching". The closest work is the Universal Image Embedding challenge/benchmark.

### Cited Findings
- ALIGN: noisy image–alt-text contrastive dual encoder (Google, 2021) — [arXiv 2102.05918](https://arxiv.org/abs/2102.05918)
- CoCa: contrastive + captioning image–text model (Google, 2022) — [arXiv 2205.01917](https://arxiv.org/abs/2205.01917)
- SigLIP: sigmoid-loss image–text pretraining (Google, 2023). Open weights make it a practical free option — [arXiv 2303.15343](https://arxiv.org/abs/2303.15343)
- Gecko: Google's text embedding model distilled from LLMs (2024) — [arXiv 2403.20327](https://arxiv.org/abs/2403.20327)
- UnED / Universal Image Embedding (instance-level, includes products) — [arXiv 2309.01858](https://arxiv.org/abs/2309.01858). A 2024 follow-up reports mMP@5 0.721 on the challenge — [arXiv 2409.13513](https://arxiv.org/abs/2409.13513)
- (The four arXiv IDs for ALIGN/CoCa/SigLIP/Gecko come from my background knowledge, not from fetches in this session. The IDs are standard and well known.)

### Inferences
- A typical pipeline in this literature, and one an app can copy:
  1. Recall candidates with a dual-encoder embedding (image and/or text) using ANN search.
  2. Re-rank or verify with stricter signals: identifiers, brand, attributes, instance-level image similarity.
- For apparel, CLIP/SigLIP-type models are good at category, colour and style. They are weaker at fine instance details (logo, print, collar construction). That gap is why Google treats instance-level embeddings separately.

### Gaps
- I found no Google/DeepMind paper specifically on cross-retailer **offer matching / entity resolution** for Shopping.

## 4. Developer APIs available in 2026, and their cost

### Takeaway
- **Gemini Embedding 2** (`gemini-embedding-2`) is the current Google multimodal embedding model, with text and images in one vector space. The older `multimodalembedding@001` is still documented.
- **Vision API Product Search** is still documented, with no formal deprecation entry. A non-English page snippet calls it maintenance mode.
- **Vertex AI Search for commerce** (Retail API) is a full retail search/recs product at $2.50 per 1k search queries. It is overkill for matching.

### Cited Findings
- Vertex AI multimodal embeddings docs:
  - Models: `gemini-embedding-2` (default 3072 dims, 128–3072; 8192-token shared context; up to 6 images/request; text, image, PDF, audio, video) and `multimodalembedding@001` (1408 dims; text max 32 tokens, English only; images resized to 512×512).
  - "Image and text embedding vectors are in the same semantic space."
  - The preview model `gemini-embedding-2-preview` "might be deleted in the future". No dated deprecation for @001 is shown.
  - Source: [Vertex AI docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-multimodal-embeddings) (accessed 2026-11)
- Gemini Embedding 2 pricing (secondary sources conflict):
  - OpenRouter: $0.20/M text tokens and $0.45/M image tokens — [OpenRouter](https://openrouter.ai/google/gemini-embedding-2)
  - Tracker for Vertex: $0.25/M tokens, batch at half that rate — [CostBench](https://www.costbench.com/software/embedding-apis/vertex-ai-embeddings/)
  - Launch timing: preview around March–April 2026, GA listing around May 2026 — [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/google-launches-gemini-embedding-2-its-first-multimodal-embedding-model/)
  - Not verified on Google's official pricing page. Docs say images are 258 tokens each, so per-image cost is about $0.00006–0.00012 (my arithmetic).
- Vision API Product Search:
  - Docs still describe it: products with multiple reference images, grouped into product sets, queried with an image, returning ranked visually + semantically similar results. Categories are homegoods, apparel, toys, packaged goods, general. — [Product Search docs](https://docs.cloud.google.com/vision/product-search/docs)
  - The Vision deprecations page lists only Celebrity Recognition and OCR On-Prem (both shut down 2025-09-16), not Product Search — [Vision deprecations](https://docs.cloud.google.com/vision/docs/deprecations)
  - A Hebrew-locale page snippet says Product Search is in **maintenance mode** and recommends an alternative — [search snippet of docs.cloud.google.com/vision/product-search?hl=he](https://docs.cloud.google.com/vision/product-search?hl=he) (unverified; English page didn't state it)
- Vertex AI Search for commerce:
  - Pricing: search/browse $2.50 per 1,000 requests; conversational $6.00 per 1,000; recommendations from $0.27 per 1,000 predictions — [Google Cloud pricing](https://cloud.google.com/retail/pricing)
  - Trackers report a 2026 rename ("Agent Search for commerce" / "AI Commerce Search") — [pricingsaas](https://pricingsaas.com/companies/google.cloud/diffs/2026W22) (unconfirmed)
- SerpApi Google Immersive Product API (third-party scraping of Google, paid):
  - Takes a `page_token` from a Shopping result and returns `stores[]` with per-seller price, total, shipping and stock. Returns 3–5 stores by default, up to 13 with `more_stores`.
  - `more_options` lists related products. No explicit variant/size fields.
  - Source: [SerpApi docs](https://serpapi.com/google-immersive-product-api)

### Inferences
- For a small app, the cheapest Google-native option is Gemini Embedding 2, or free open SigLIP weights run locally, plus your own vector index. Vision Product Search should be avoided for new builds because of its maintenance-mode signal.
- SerpApi "compare prices" results are Google's clustering exposed as a paid scrape. Per the constraints, they are not usable here. They are also unlikely to cover Myntra/Flipkart apparel well (inference).

### Gaps
- No official Google per-image price was verified for gemini-embedding-2. I also did not confirm Vision Product Search pricing or an official shutdown date.

## 5. Lessons that generalise to a small app (clothing + sneakers, Amazon.in / Flipkart / Myntra)

### Takeaway
Copy Google's layering:
1. **Identifiers first.**
2. Then **brand + model/style code**.
3. Then **embedding recall** (image + title).
4. Then **attribute verification** to separate "exact" from "similar".
5. Keep **variant level (colour)** separate from **style level (group)**.
6. Feed **user feedback** back into the system.

### Cited Findings
- Identifier primacy and per-variant GTINs: [GTIN help](https://support.google.com/merchants/answer/6324461)
- Variant axes are color/size/pattern/material/gender/age_group, and anything else makes a separate product: [item_group_id help](https://support.google.com/merchants/answer/6324507)
- Conflicting attributes under the same ID get flagged, which is a form of consistency checking: [Same GTIN differing value](https://support.google.com/merchants/answer/12473099)
- Fashion "similar" results are stylistic, and identifier/OCR matches give exact results: [VentureBeat 2018](https://venturebeat.com/ai/google-lens-now-recognizes-over-1-billion-products)
- Fine-grained, brand-level discrimination needs instance-level embeddings: [Google Research blog](https://research.google/blog/introducing-the-google-universal-image-embedding-challenge/)
- Lens has an explicit "Feedback" entry in its filter bar (third-party description): [Advanced Web Ranking](https://www.advancedwebranking.com/seo/google-lens-visual-search)

### Inferences (proposed rules, not Google-documented)
- **Sneakers:**
  - Extract the brand style code (Nike/Adidas/Puma SKUs) from title or specs.
  - An exact style code plus the same colourway counts as an exact match.
  - Size is ignored for price comparison (as with GTIN-per-size, which shares item_group).
- **Tees/polos/jerseys:**
  - Brand must match.
  - Then require agreement on product type (polo vs tee vs jersey), neckline, sleeve length, colour and pattern/print. Use image-embedding similarity above a high threshold, ideally with a crop of the garment.
  - A neckline or sleeve mismatch is a hard reject, because Google treats those as different products, not variants.
  - A colour mismatch means "same style, other colour", i.e. a group-level match.
- **Jerseys:** also verify team, season, and kit type (home/away) plus version (replica vs authentic), because these look nearly identical. Title text is usually the decisive signal here.
- Show three tiers, like Lens:
  - "Same product" (strict verification passed)
  - "Same style, other colour"
  - "Similar" (embedding neighbours that fail verification)
- Log user "not the same" clicks as hard negatives for threshold tuning.
