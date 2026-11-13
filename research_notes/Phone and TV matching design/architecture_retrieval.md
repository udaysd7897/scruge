# Architecture and retrieval for matching phone and TV variants across Amazon.in, Flipkart and Croma

Scope note: these notes cover (a) how comparators and production systems model variants, (b) candidate retrieval, and (c) a recommended architecture for a small app. The earlier background report (/Users/sid/scruge/reports/Cross platform product matching.md) already covers GTIN/model-code parsing rules, WDC benchmark numbers and the regex-plus-LLM extractor in detail, so these notes do not repeat that material. Several primary pages could not be fetched (idealo's Medium post and smartprix.com both returned HTTP 403, and SerpApi's Immersive Product docs timed out). Those gaps are listed below.

## How do comparators and production systems model phone/TV variants and attach retailer offers?

### Takeaway
Every system with published detail uses a two-level identity: a product or "group" (the model), with each sellable variant (storage/RAM, colour, screen size) as its own leaf. Offers attach to the leaf. Google's own feed spec names memory size and display size as variant-defining for electronics. Indian comparators visibly key pages at the model + storage/RAM level (91mobiles URLs such as `poco-m8-256gb-8gb-ram-price-in-india`). Large systems (Shopify, idealo) match offers with embeddings plus learned pairwise scorers tuned precision-first, and use LLMs offline as labellers rather than at serving time.

### Cited Findings
- Google Merchant Center: "Use the item group ID [item_group_id] attribute to group product variants"; each variant keeps its own `id` and is submitted "as a separate product". The standard variant attributes are color, size, pattern, material, age group and gender, plus a free-form "variant option". For electronics, variants differ by "memory sizes, display sizes, processors, and graphics options". Phone example: "if a phone is available in multiple colors and memory sizes, you can submit each as a variant". The Nexus 6 example uses the variant option `color:midnight blue,memory:32GB`. — [Google Merchant Center: item_group_id](https://support.google.com/merchants/answer/6324507?hl=en)
- Google warns that rows sharing an item_group_id must carry the same set of variant attributes. Per a third-party feed guide, rows with identical variant attributes inside one group are flagged as duplicates. A Shopify community thread notes that grouping into a single card is at Google's discretion even when item_group_id is correct. — [Google search summary of MC help](https://support.google.com/merchants/answer/6324507); [GoDataFeed guide](https://static.godatafeed.com/content/Guides/Feed+Forensics/variant-grouping-errors-issue_01); [Shopify community](https://community.shopify.com/t/adding-item-group-id-in-multifeeds/360593)
- Google Shopping exposes a cross-retailer product cluster: the Shopping result carries a `product_id`, visible in product links as `prds=catalogid:{product_id}`. SerpApi's Google Product engine with `offers=true` returned the seller list under `sellers_results.online_sellers`. A SerpApi blog says that engine is discontinued, replaced by the Google Immersive Product API, which takes a `page_token` from Shopping results. — [SerpApi Google Product API](https://serpapi.com/google-product-api); [SerpApi blog: online sellers](https://serpapi.com/blog/web-scraping-google-shopping-product-online-sellers-with-nodejs/)
- Shopify (billions of listings, millions of stores) runs a cascade. Retrieval uses ANN over embeddings. L1 is a GBDT on cheap features (embedding distance, title/vendor similarity, price relationships) and decides which pairs get expensive scoring. L2 is a fine-tuned multilingual E5 cross-encoder over titles, vendor, predicted category, URL and shop name. L3 is a fine-tuned open-model reranker with images. Clustering avoids naive connected components because pairwise judgments are non-transitive. A merge model uses "contradiction" features (low-scoring evidence against a merge). Thresholds are tuned "for precision first, then recall is maximized". An LLM judge labels sampled pairs offline, its labels are validated against humans, and those labels train L1–L3. LLMs are not used at serving time. No numeric thresholds or P/R figures are published. — [Shopify Engineering: Catalog clustering part II](https://shopify.engineering/catalog-clustering-part-ii)
- idealo imports offers from shops of all sizes daily. It clusters offers with Sentence-Transformers to auto-create products (the blog's focus is shoes), and its PyCon DE 2022 talk says millions of daily offers "cannot be mapped to their catalogue directly". Wikipedia describes matching against a backend product database using fuzzy logic, with human teams for quality control. — [PyCon DE 2022 talk](https://pycon.de/archive/2022/talks/transformer-based-clustering-identifying-product-clusters-for-e-commerce/); [idealo tech blog (403 when fetched; summary from search)](https://medium.com/idealo-tech-blog/automate-product-creation-by-clustering-millions-of-shops-offers-with-machine-learning-3db3162dbad4); [Wikipedia: Idealo](https://en.wikipedia.org/wiki/Idealo)
- 91mobiles uses separate URLs per storage variant, e.g. `oneplus-9-pro-256gb-price-in-india` and `poco-m8-256gb-8gb-ram-price-in-india?ty=prices` (titled "POCO M8 256GB, 8GB RAM Price In India"), with a base model page such as `lava-agni-3-5g-price-in-india`. Smartprix list pages group phones by RAM+ROM tier (`8gb-ram-256gb-rom-mobiles-list`) and tag prices with a store. — [91mobiles POCO M8 256GB](https://www.91mobiles.com/poco-m8-256gb-8gb-ram-price-in-india?ty=prices); [91mobiles OnePlus 9 Pro 256GB](https://www.91mobiles.com/oneplus-9-pro-256gb-price-in-india); [Smartprix 8GB/256GB list](https://smartprix.com/mobiles/8gb-ram-256gb-rom-mobiles-list)
- Manufacturer India SKUs encode colour and storage (Samsung `sm-m558blgcins`). Sony TV codes encode screen size (KD-55X80L). — cited in the background report: [Samsung IN](https://www.samsung.com/in/smartphones/galaxy-m/galaxy-m55s-green-256gb-sm-m558blgcins/); [Expert Reviews](https://www.expertreviews.co.uk/technology/tvs-home-cinema/sony-tv-model-numbers-explained)

### Inferences
- The right identity for this app is a hierarchy: `Model` (brand + family + generation + tier, e.g. Samsung / Galaxy S / 26 / Ultra) → `Variant` (RAM, storage for phones; screen size for TVs) → `Colour`. Colour is a leaf, and some products (e.g. stock comparison) can treat it as "same variant, different colour" rather than a hard reject. 91mobiles' per-storage pages and Google's phone example both put storage/RAM at the variant level.
- For TVs, the manufacturer model code (e.g. LG `55NU870BPLA`) is effectively a variant-level key, because it embeds size and series. Store-specific marketing family names ("NU87 Nano") should therefore be treated as aliases to resolve, not as identity. Store family text should never drive a hard veto. The size digits and the series core of the model code should.
- None of the large systems hand-code per-brand rules at serving time. They learn scorers from labelled pairs, and the labels increasingly come from an LLM judge checked against humans (Shopify). For a small app, the equivalent is to move per-brand knowledge into data (an alias table or a cached LLM-normalised record per listing) and to keep only generic, attribute-level vetoes in code.
- Comparators such as Smartprix and 91mobiles effectively maintain a curated model/variant spine and attach retailer URLs to it. That suggests a cheap "spine" source: resolve the Amazon listing to a comparator variant page, which already lists store links. This is an inference; I could not verify the page structure or terms of use (see Gaps).

### Gaps
- smartprix.com returned 403 to plain fetch, so I could not confirm how Smartprix attaches Amazon/Flipkart/Croma offers per variant, or whether colour is modelled. No published engineering detail was found for Smartprix, 91mobiles, MySmartPrice, PriceHistory or BuyHatke.
- No PriceRunner engineering write-up was found within budget.
- Google has published no detail of how Shopping clusters offers into a `product_id` (whether it is GTIN-first or learned).

## Variant-aware matching and where an LLM belongs

### Takeaway
Use the LLM as a cached, schema-constrained attribute normaliser (once per listing, with evidence spans), not as the final arbiter. Run deterministic vetoes after it. Use an LLM pairwise/listwise judge only on the few survivors that remain ambiguous. Small-model pricing in late 2026 makes this cost fractions of a cent per lookup. Published accuracy suggests LLM judges are strong but still err on small model-number differences, which is why deterministic checks on extracted codes must stay.

### Cited Findings
- GPT-4 attribute extraction with JSON schema and examples reaches about 90.5–91 F1 on WDC-PAVE, about 10 points above PLM extractors. Unit conversion is the hardest normalisation step. — [Brinkmann et al. arXiv 2403.02130](https://arxiv.org/abs/2403.02130v2)
- ExtractGPT reaches a best average F1 of 86% with GPT-4 using an ensemble of shuffled prompts. — [arXiv 2310.12537](https://arxiv.org/abs/2310.12537v3)
- In LLM entity matching on products, GPT-4's errors come mostly from overweighting shared attributes and misreading small model-number differences. The paper also evaluates GPT-4o-mini, which is far cheaper per prompt. — [Peeters et al. arXiv 2310.11244 (EDBT 2025)](https://arxiv.org/html/2310.11244v4)
- A 2026 Amazon paper (Zhu, Vedula, Malmasi) builds attribute graphs with an LLM offline and ranks over that structured representation online. It reports a 57% token reduction and better zero-shot precision. This supports "extract once, compare structurally". — [arXiv 2604.27410](https://arxiv.org/pdf/2604.27410)
- Shopify validates the LLM judge against human labels and uses it offline to train cheaper models. It is not used online. — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- Practitioner (low-reliability) reports: GPT-4o-mini as an ER judge on borderline Abt-Buy pairs gave about 66% F1 for about $0.04 total. Another 2026 blog cites 62–65% accuracy for GPT-4o-mini vs about 80% for larger models. — [Towards AI](https://pub.towardsai.net/using-gpt-4o-mini-as-an-entity-resolution-judge-95-precision-for-0-04-b216d44a7f20); [tianpan.co blog](https://tianpan.co/blog/2026-04-17-llm-data-normalization-production)
- Official Gemini API paid-tier pricing (fetched Nov 2026), per 1M tokens input/output: `gemini-2.5-flash-lite` $0.10/$0.40; `gemini-3.1-flash-lite` $0.25/$1.50; `gemini-3.5-flash-lite` $0.30/$2.50. Batch is half price, and context caching is available. `gemini-2.5-flash` is deprecated and routes to `gemini-3.5-flash-lite` from 1 Dec 2026. — [Google AI pricing](https://aistudio.google.com/docs/pricing)
- Claude Haiku 4.5 is $1/$5 per 1M tokens per aggregators. GPT-5 nano figures conflict across aggregators (around $0.05/$0.40 is commonly quoted); I did not verify them against OpenAI. — [anotherwrapper comparison](https://anotherwrapper.com/llm-pricing/gemini-2.5-flash-lite/claude-haiku-4-5-20251001); [anotherwrapper GPT-5 nano](https://anotherwrapper.com/tools/llm-pricing/gemini-2.5-flash-lite/gpt-5-nano-2025-08-07)
- Repo observation (read-only): `/Users/sid/scruge/app/llm.py` (54 lines) currently prompts the LLM as a pairwise judge ("it is the identical product (same model, variant and colour where known)"). No source adapter references variant siblings (grep for `variant`, `ean`, `gtin` and `breadcrumb` in `app/sources/*.py` found nothing). — local file

### Inferences
- Cost arithmetic (my calculation, not from a source): one extraction call of about 1,000 input and about 150 output tokens on `gemini-2.5-flash-lite` costs about $0.00016. Normalising 1 Amazon listing + 60 candidates is therefore about $0.01. A listwise judge over 5 survivors (about 3k in / 300 out) costs about $0.0004. A per-PID cache makes repeated lookups free. LLM cost is negligible next to Apify (about $0.07 per Croma result).
- Placement of the LLM, from most to least valuable:
  1. **Extractor/normaliser** (per listing, cached by ASIN/FSN/Croma PID): it outputs `{brand, line, model_number, generation, tier (base/Plus/Pro/Pro Max/Ultra/FE/Lite), ram_gb, storage_gb, screen_in, colour_raw, colour_family, category, mpn_codes[]}`, each value with an `evidence` substring. A deterministic check rejects any value whose evidence is not literally in the title/specs. For known facts, e.g. that iPhones do not list RAM, the RAM field stays null, which is a "neutral" rather than a "mismatch".
  2. **Category classifier**: phone vs TV vs accessory (case, charger, wall mount). This replaces the "smartphone" keyword and breadcrumb dependence, and it is a cheap enum output.
  3. **Listwise tie-breaker**: only when 2 or more candidates survive the vetoes with close scores. It gets the source record plus the survivors' normalised records, outputs the index or "none", and must cite the differing field. Deterministic vetoes are re-applied afterwards.
- Do not let the judge override a deterministic veto on numeric fields (storage, RAM, size) or on a model-code mismatch. The literature's main LLM failure mode is exactly small code and number differences.

### Gaps
- I found no published accuracy figure specific to Indian phone/TV listings, or for 2026 small models (Flash-Lite, GPT-5 nano, Haiku 4.5) on WDC Products. The app needs its own golden set to measure this.
- I could not read the CaRL-EM (arXiv 2609.01195) cost-aware LLM-EM results; only the reference list was surfaced.

## Retrieval: getting the exact variant into the candidate set

### Takeaway
Retailer search ranks by relevance and popularity, not by variant. The fix is to search for the model, then expand to its siblings, rather than to search deeper. Find any listing of the right model (model code or canonical name), then enumerate its variant siblings from the product page (Amazon twister/variant ASINs, Flipkart pid variants, Croma variant list) and pick the leaf that matches storage/RAM/colour. A Google Shopping cluster (via SerpApi) is a useful cross-retailer retrieval source, but it is paid, so it is outside this research's constraints and only an option.

### Cited Findings
- Google Shopping's `product_id` links one catalog product to multiple online sellers (`sellers_results.online_sellers`). The current SerpApi path is the Immersive Product API using a `page_token` from Shopping results. — [SerpApi Google Product API](https://serpapi.com/google-product-api); [SerpApi blog](https://serpapi.com/blog/web-scraping-google-shopping-product-online-sellers-with-nodejs/)
- I could not confirm India support (`gl=in`) from the docs. A third-party example used `location=India` with `uule`. — [Thordata Google Product docs](https://doc.thordata.com/doc/scraping/serp-api/query-parameters/google/google-product)
- SerpApi pricing: free tier of 250 searches/month; Starter $25 for 1,000; Developer $75 for 5,000. "Cached, errored, and failed searches" do not count toward the quota. — [SerpApi pricing](https://serpapi.com/pricing)
- Shopify notes that ANN shortlists can drop true matches, which it accepts because later builds recover them. A one-shot app cannot rely on that, so it needs explicit recall steps. — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- Google's own model treats colour and memory as siblings under one group. Retail product pages mirror this (one model page with variant selectors), which is what makes sibling expansion possible. — [Google Merchant Center](https://support.google.com/merchants/answer/6324507?hl=en)

### Inferences
- Recommended query ladder (stop at the first rung that yields a model-level hit):
  1. Exact manufacturer code (Samsung `SM-S948B`, LG `55NU870BPLA`, Sony `K-55S30`). This is precise and short.
  2. Canonical model name without variant tokens ("Samsung Galaxy S26 Ultra"). This retrieves the model page; any variant will do.
  3. Canonical name + storage (+ colour). Only if rungs 1–2 return nothing model-level.
  For TVs, query `brand + size + series core` (e.g. "LG 55 NU87") and the full code. Never query by store-specific marketing family alone.
- The Croma S26 Ultra observation (exact variant ranked 6th–7th) fits this. Search found the model; the variant was lower. Sibling expansion from any S26 Ultra hit (after the family/tier veto removes plain S26) reaches the exact storage variant without paying for deeper result pages. For Apify-based Croma, this means requesting few results (e.g. top 5) and then one product-detail fetch, rather than 20 results at about $0.07 each. That is a cost inference, to be checked against how the Apify actor bills detail fetches.
- Rank before truncation: drop candidates failing hard vetoes (tier, family, size, storage) before applying any "top-k" cut. This is a cheap fix for exact items being cut by k.
- Cache by retailer ID (ASIN/FSN/Croma PID → normalised record, 24h for price/stock, longer for attributes). Also cache a model → retailer-model-page map, so the second lookup for any S26 Ultra variant skips search entirely.
- A comparator page (Smartprix/91mobiles) found via plain web search could serve as a fallback "spine" giving store URLs, at low volume. This is unverified (see Gaps).

### Gaps
- I did not verify the exact JSON fields for siblings on each retailer (Amazon `variantAsins`/twister data, Flipkart `pid`/swatch data, Croma `variant_count`/variant API) in this session. The repo's source adapters currently do not parse them (grep found no references).
- I could not confirm SerpApi Google Shopping coverage of Croma and Flipkart offers in India, or `gl=in` behaviour.
- I could not verify whether Smartprix/91mobiles terms permit automated low-volume fetching.

## Evaluation: golden sets, hard negatives, precision-first thresholds

### Takeaway
Build a small labelled set (for example 40–80 source listings × the 3 stores) that deliberately includes the corner cases. Score precision on MATCH decisions and the abstention rate separately, and tune thresholds for precision first, the way Shopify does. Use an LLM to pre-label, and have a human verify.

### Cited Findings
- WDC Products deliberately includes up to 80% corner cases. Raising the corner-case share from 20% to 80% costs models 7–10 F1. Unseen products hurt more (Ditto falls from 79.1 to 68.4). Label noise is about 4%. — [WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- Shopify tunes thresholds "for precision first, then recall is maximized", and validates its LLM judge against human annotations. — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- An ICML 2026 paper uses an LLM to generate hard negatives for structured product matching. — [ICML 2026: LLM-Guided Hard Negative Mining](https://icml.cc/virtual/2026/71465)

### Inferences
- Golden set schema: `(source_asin, store, candidate_id, label ∈ {exact, same_model_other_variant, same_model_other_colour, different_model, accessory})`, plus `expected_decision` per (source, store). The richer label lets the eval report why something failed.
- Mandatory hard-negative pairs: Pro vs Pro Max; S26 vs S26+ vs S26 Ultra vs S26 FE; 128 vs 256 vs 512 GB; 8/256 vs 12/256; 55" vs 65" of the same series; NU87 vs NU85 (same size); previous-year model with the same name (S25 vs S26); phone vs its case/cover; refurbished/renewed listings.
- Also include source-side gaps: iPhone titles with no RAM, Amazon pages without breadcrumbs, and TV listings whose store family name differs from the manufacturer code.
- Metrics: precision of MATCH (target ≥ 0.98), recall of MATCH, abstain rate (AMBIGUOUS + NONE when an exact item exists), and retrieval recall@k (was the exact item in the candidate set at all?). Measured separately, these show whether a failure was retrieval or matching.
- Run the eval offline against recorded HTML/JSON fixtures, so the tests are deterministic and cost nothing (no Apify).

### Gaps
- I found no public Indian phone/TV golden set.

## Recommended architecture for the small app

### Takeaway
Replace regex model lists and per-brand special cases with (1) a cached LLM normaliser producing a typed, evidence-checked record per listing, (2) a small data-driven alias table, (3) generic attribute-level vetoes, (4) model-first retrieval plus sibling expansion, and (5) an optional listwise LLM tie-break. Precision is enforced by deterministic code at the end.

### Cited Findings
- The pattern follows Shopify's cascade (cheap features → stronger scorer, precision-first thresholds, contradiction features) and Amazon's "extract offline, rank over structure" approach. — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii); [arXiv 2604.27410](https://arxiv.org/pdf/2604.27410)
- Google's variant model (group → variant with memory/display/colour attributes) is the reference schema. — [Google Merchant Center](https://support.google.com/merchants/answer/6324507?hl=en)

### Inferences (proposed design)
**Data model**
- `ProductRecord {store, store_id, url, title, category, brand, line, gen, tier, model_codes[], ram_gb?, storage_gb?, screen_in?, colour_raw?, colour_family?, gtin?, price, stock, evidence{field: span}}`.
- Identity keys: `model_key = (brand, line, gen, tier)` and `variant_key = model_key + (ram, storage) | (screen_in)`. Colour is compared separately.

**Pipeline**
1. **Normalise the source** (Amazon): parse structured fields first (tech-details table: model number, RAM, storage, screen size; JSON-LD), then run an LLM normaliser with a JSON schema and evidence spans. Verify the spans, and snap units (cm→in to the nearest standard size; TB→GB). Cache by ASIN.
2. **Retrieve per store**: run the query ladder (code → canonical name → name + storage), take the top N (5–10), and normalise each candidate (from cache when available).
3. **Model-level filter**: keep candidates whose `model_key` matches (category, brand, tier, generation must agree; null on one side = unknown, not a mismatch).
4. **Sibling expansion**: for the best model-level hit(s), fetch the product page's variant list and add the siblings as candidates. This is what fixes the "exact variant ranked 6th" problem.
5. **Hard vetoes** (generic, table-driven): numeric conflicts on storage, RAM, screen size; model-code base conflict when both sides have codes; GTIN mismatch (strong); category ≠ phone/TV.
6. **Score survivors**: code match > GTIN > attribute agreement > title similarity. Colour match is a bonus; a colour mismatch → "same variant, other colour" label.
7. **Decide**: one survivor with full key agreement → MATCH. Several survivors → listwise LLM tie-break with forced field citation, then re-veto. Otherwise AMBIGUOUS. Nothing → NONE (kept distinct from "fetch failed").
8. **Stock**: read from the chosen leaf's own page/JSON, not from the model page.

**Stop hard-coding**
- Regex lists of model names per brand → LLM normaliser + cache, plus an `aliases.yaml` (e.g. `LG NU87 ↔ 55NU870*`) that grows from observed misses.
- Per-brand special cases (iPhone has no RAM) → null-is-neutral semantics in the veto engine.
- The "smartphone" keyword and breadcrumb dependence → LLM category enum + accessory detection.
- Store-specific family names as identity → model-code core + size as identity; family name is a soft signal only.

**Testability**
- Each stage is a pure function over recorded fixtures. The golden-set runner reports retrieval recall@k, veto false-rejects, MATCH precision and abstain rate. LLM outputs are cached in fixtures, so tests are deterministic.

**Budget**
- LLM is about $0.01 per lookup on `gemini-2.5-flash-lite` (calculated above). Retrieval is the real cost driver. Fetch fewer Croma results and expand siblings instead, and cache aggressively. SerpApi Google Shopping (250 free/month) is an optional paid cross-retailer recall source and was not tested here, per the constraints.

### Gaps
- None of the above has been benchmarked on this app's data. Expected precision is an inference from the literature, not a measured result.
