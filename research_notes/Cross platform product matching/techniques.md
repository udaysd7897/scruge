# Technical Methods for Cross-Platform E-commerce Product Matching (variant-level; Amazon India -> Flipkart / Croma / Myntra)

Scope note: the research covered ~15 searches/fetches. Strongest primary sources: Univ. Mannheim LLM entity-matching papers (Peeters, Steiner, Bizer, Brinkmann), Shopify Engineering, Google Merchant Center help, GS1, schema.org, RapidFuzz docs, an Aug-2026 arXiv production-cascade paper. India-specific engineering write-ups from Flipkart, Myntra or Croma on cross-platform matching were **not found**. Points marked "Inference" are engineering judgement, not sourced.

---

## 1. Identifier-based matching (GTIN/EAN/UPC, MPN/model number, style codes)

### Takeaway
When identifiers are present on both sides they are the strongest signal. GS1 rules require a distinct GTIN for every colour/size variant, so an exact EAN match is effectively a variant-level match. In practice, though, identifiers are often missing or unreliable across retailers (Shopify: barcodes "not consistently available or reliable"). Manufacturer model codes carry region, colour and storage suffixes, so you need to normalize them to a base code and compare their parts, not test them for string equality. Use identifiers as a strong positive or hard negative signal. Do not make them a prerequisite.

### Cited Findings
- GS1: each size, each colour and each size×colour combination is a separate variation needing its own GTIN. For example, a one-size T-shirt in 3 colours needs 3 GTINs — [GS1 support](https://support.gs1.org/support/solutions/articles/43000734083-how-many-gs1-gtins-do-i-need-when-i-have-a-product-with-many-sizes-and-colours-)
- GS1: one GTIN can be assigned to only one product, and different-sized trade items must have different GTINs — [GS1 support: more than one GTIN](https://support.gs1.org/support/solutions/articles/43000734121-can-a-product-have-more-than-one-gs1-gtin-); [GS1 GTIN rule: new size](https://www.gs1.org/1/gtinrules/en/rule/139/trade-item-supplied-in-new-size)
- Some product changes trigger a new GTIN, such as a change to the declared net content. The rules are industry-specific, and GS1 provides a decision-support tool — [GS1 NZ fact sheet](https://www.gs1nz.org/assets/Resources/Services/GS1NZ_Fact-sheet-gtin-allocation-rules.-V2.pdf); [GS1 GTIN decision tool](https://gs1.org/en/standards/id-keys/gtin/gtin-decision-support-tool/new-product-introduction)
- Google Merchant Center requires 2 of {brand, gtin, mpn} for most categories. For shoes, handbags, sunglasses and watches it requires brand plus one of UPC/EAN/JAN/MPN. Merchants must not guess GTINs or copy them from similar products. GTINs must have a valid check digit. Colour and size variants must each have their own identifiers — [Google Merchant Center: unique product identifiers](https://support.google.com/merchants/answer/160161); [GTIN attribute](https://support.google.com/merchants/answer/6324461)
- Shopify's cross-store clustering (billions of listings): "barcodes can help, but they are not consistently available or reliable". Their system relies mainly on learned text/image models instead — [Shopify Engineering, Catalog clustering part II](https://shopify.engineering/catalog-clustering-part-ii)
- A US patent on automatic product matching scores model numbers explicitly. The same model number in both descriptions scores 100, and model numbers present in both but different score 0. Model numbers are extracted with regular expressions — [USPTO patent 11367116](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11367116)
- In LLM entity matching on Walmart-Amazon, the largest false-negative class was "Model Number Mismatch": 9 of 15 errors involved slight model-number differences. The LLM is unreliable at treating a model number as identity — [Peeters et al., Entity Matching using LLMs, arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- Samsung model codes: the base code (e.g. SM-S921) identifies the device. The letter after the digits marks the regional or carrier variant: SM-S921B is Europe/International, SM-S921U is USA, SM-S921N is Korea, SM-S9210 is China — [iFixit Galaxy S24](https://ifixit.com/Device/Samsung_Galaxy_S24). A full retail SKU appends further codes, e.g. "SM-S921BLBQPHL" on Samsung Philippines — [Samsung PH support](https://www.samsung.com/ph/support/how-to-find-model-and-serial-number-of-samsung-product/). A Samsung community user reports that INU denotes an India-sold configuration (user-generated, indicative only) — [Samsung community](https://r2.community.samsung.com/t5/Tech-Talk/All-about-CSC-codes-And-debunked-Model-number/m-p/10095275/highlight/true)
- Nike style codes are 9 characters, usually 6 + 3 (e.g. DA2142-146). The 3 digits after the hyphen are the colour code, so DA2142-146 (White) and DA2142-046 (Black) are the same model in different colourways — [underpriced.app Nike style code decoder](https://www.underpriced.app/tools/nike-style-code-lookup); [House of Heat](https://houseofheat.co/nike/nike-blazer-mid-77-color-code-white-da2142-146-black-da2142-046)
- Sony TV codes: the digits after the prefix give the screen size (55 = 55"). The older style uses a KD- prefix for 4K, and X/Z mark LED/Mini-LED lines. From 2024 Sony moved to a "K-" prefix with tier names (e.g. Bravia 3 = K-xxS30). Year-letter conventions vary between sources — [Expert Reviews, Sony TV model numbers explained](https://www.expertreviews.co.uk/technology/tvs-home-cinema/sony-tv-model-numbers-explained); [What Hi-Fi, TV model numbers explained](https://www.whathifi.com/advice/tv-model-numbers-explained-how-to-identify-lg-sony-samsung-and-other-tvs)

### Inferences
- Normalization recipe: uppercase; strip spaces, hyphens, slashes and dots; parse into {base, variant suffix}.
  - Samsung phones: base = `SM-[A-Z]\d{3,4}[A-Z0-9]?`; the remaining characters encode colour, storage and region. Compare the bases as a hard constraint, and read colour/storage from the attributes instead of decoding the suffix.
  - Sony TVs: the code itself contains the size, so check that the size in `KD-55X80L` equals the extracted screen size. An `/IN5`-style trailing region tag should be stripped.
  - Nike: split the code at the hyphen. The prefix is the model and the suffix is the colourway, so a style-prefix match with a different colour code is a hard non-match at variant level.
- Treat an EAN match (after validating the GTIN-13 check digit and left-padding to 14) as near-certain. Treat an EAN mismatch as a strong but not absolute negative: sellers mis-enter EANs, and one product can carry different GTINs from different packers or importers. Missing EAN is neutral.
- Croma via Apify returns EAN and Model Number. Amazon sometimes exposes EAN/model in its technical-details table. Flipkart's JSON-LD `sku` is usually Flipkart's internal ID, not the MPN, so verify this before relying on it. Myntra exposes no model code at all. So identifier matching will mostly help for Amazon↔Croma electronics, and attribute matching must carry Flipkart/Myntra.
- For apparel (polos, jerseys), brand style codes (e.g. adidas `IP1234`, Puma 6-digit + 2-digit colour) appear in some titles and descriptions but rarely in structured fields.

### Gaps
- No source quantified how often EAN/MPN appears on Amazon.in, Flipkart, Croma or Myntra pages. Measure this on your own sample.
- No authoritative Samsung documentation for the meaning of India suffixes (INS vs INU) was found.
- Sony India's exact suffix conventions were not verified.

---

## 2. Attribute value extraction from titles (regex/rules, NER, LLM structured extraction)

### Takeaway
LLMs with JSON-schema output and a few demonstrations reach ~90-96% F1 on attribute extraction and normalization, about 10 points above the best pre-LLM extractors. Unit conversion is the weakest operation. For a small set of fixed attributes (RAM, storage, screen size, colour, model), deterministic regex rules with category-specific guards are cheap, fast and auditable. Use an LLM as fallback, or as the primary extractor with regex cross-checks.

### Cited Findings
- WDC-PAVE benchmark (Brinkmann, Baumann, Bizer, ADBIS 2024): 565 offers from 59 websites, 4,687 verified attribute-value pairs — [arXiv 2403.02130v4](https://arxiv.org/html/2403.02130v4)
  - Direct extraction: GPT-4 scores 74.4 F1 zero-shot and 90.5 with 10 example values + 10 demos. GPT-3.5 scores 70.7 and 88.0.
  - Extraction + normalization: GPT-4 scores 74.2 zero-shot and 91.3 with 10 values + 5 demos.
  - Normalization only: GPT-4 scores 86.4 zero-shot and 96.1 with examples.
  - PLM baselines for extraction: AVEQA 80.8, MAVEQA 65.1, SU-OpenTag 60.4.
  - Hardest operation: unit-of-measurement conversion, which "requires calculations" (GPT-4 83.5%). Easiest: name expansion (98%) and string wrangling (97%). Colour/product-type generalization is moderately hard.
  - Prompt design: target schema as JSON Schema; demos chosen by embedding similarity; temperature 0. 45% of gold pairs are "n/a", so the model must be allowed to answer null.
  - Cost per 1,000 attribute values with GPT-4 (2023 prices): extraction is $0.10 zero-shot and $4.60 with 10 values + 10 demos. GPT-3.5 costs ~10x less.
- A practitioner comparison of variant matching notes that string/embedding methods fail on synonyms (Navy Blue vs Dark Blue), unit formats (100*130cm vs 1x1.3m) and composite values. It reports LLMs as "unreliable unit reasoning" despite being the most accurate overall — [DEV Community, 5 ways to match variants](https://dev.to/_95a3e57463e6442feacd0/5-ways-to-match-aliexpress-product-variants-llm-embedding-vision-rules-and-why-i-chose-none-3afj) (author estimates, methodology undisclosed)

### Inferences
Regex and rule pitfalls specific to the Indian catalogue:
- **RAM vs virtual RAM:** "8GB RAM + 8GB Virtual RAM", "8GB+8GB RAM", "Up to 16GB RAM*". Take the first physical value and drop anything after "+" labelled virtual/extended/RAM Plus. Never sum.
- **Storage synonyms:** "128 GB ROM", "128GB Storage", "128 GB internal". Also expect "1TB", and the "8GB/128GB" or "(8+128)" patterns where the first number is RAM. Croma gives RAM and Internal Storage as separate fields, which is safest.
- **TV size:** titles are often "139 cm (55 inches)" or "108 cm (43)". Canonicalize to inches. Round cm/2.54 to the nearest standard size (32/40/43/50/55/65/75/85), allowing ±1 inch, because "164 cm (65)" gives 64.6. Also cross-check against the size digits in the model code.
- **Model-family suffixes:** S24 vs S24+ vs S24 Ultra vs S24 FE; iPhone 15 vs 15 Plus vs 15 Pro vs 15 Pro Max; Redmi Note 13 vs 13 Pro vs 13 Pro+ 5G; "5G" vs "4G" editions. Tokenize "+" as "plus". Treat the trailing qualifier set {plus, pro, max, ultra, fe, lite, neo, mini, 5g, 4g} as part of the model identity. Hard-fail if the qualifier sets differ.
- **Apparel:** size is not a matching attribute (one listing covers all sizes). Colour and fit/sleeve/collar type are. Jerseys add team, season and home/away/third.
- **LLM extraction:** use function calling / JSON schema with enum-constrained units, nullable fields, and an `evidence_span` field quoting the source text. Reject any value whose span is not a substring of the input; this is a cheap hallucination guard.
- Run extraction once per Amazon source product and once per candidate. Cache by URL/hash.

### Gaps
- No published accuracy figures were found specifically for Indian marketplace titles or for regex-vs-LLM on phone RAM/storage.
- No recent NER/sequence-tagging benchmark numbers were collected beyond the PLM baselines in WDC-PAVE (AVEQA, OpenTag variants).

---

## 3. Candidate generation / blocking

### Takeaway
At this scale (10-20 candidates per platform), the platform's own search engine is the blocker. Query construction matters more than any indexing method. Production systems at scale use embedding ANN retrieval followed by progressively more expensive scorers. The candidate set must have high recall, because nothing downstream can recover a missed product.

### Cited Findings
- Shopify: products are embedded, and approximate nearest-neighbour search proposes candidates. These are then scored by a cascade: L1 GBDT on cheap features (embedding distance, title/vendor similarity, price ratios), L2 fine-tuned multilingual-E5 cross-encoder on titles/vendor/category/URL, and L3 multimodal reranker on images + text + metadata for selected pairs only. Missed candidates only delay grouping in their batch setting — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- "Retrieve, Match, Escalate" (arXiv 2608.25037, Aug 2026) is a production product-linking cascade with three steps:
  - retrieval;
  - a lightweight text cross-encoder (distilled from dual-VLM consensus labels) that auto-accepts high-confidence links at a calibrated 98% precision;
  - an agentic open-weight VLM that inspects images and runs web searches on the ambiguous remainder.

  Coverage rises from 68% (cheap stage only) to 77% after escalation. The agent got 88% vs 92% for a closed frontier VLM at ~1/7 the per-pair cost — [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- Hybrid practitioner pattern: embeddings as a fast prefilter to the top ~10 candidates, then AI matching only on those — [Vantage blog](https://vantage-dash.vercel.app/blog/ai-vs-fuzzy-matching) (vendor blog)
- ComEM (2024): a medium-sized LLM ranks and filters the blocked candidates before a stronger model, a cost-efficient "select" strategy — [arXiv 2405.16884](https://arxiv.org/html/2405.16884v3)

### Inferences
- Query construction:
  - Use a tiered query ladder and stop at the first query that returns plausible candidates:
    1. brand + model code (e.g. "Sony KD-55X80L", "Nike DV2789-100"), if a model code exists;
    2. brand + model family + discriminating attrs ("Samsung Galaxy S24 8GB 256GB", "Sony Bravia 55 inch X80L");
    3. brand + model family only (lets you see all variants and verify absence);
    4. for apparel, brand + product type + key descriptors + colour ("Puma polo t-shirt navy").
  - Drop marketing fluff ("with AI features", "No Cost EMI"), parentheses content and seller names.
- Keep colour *out* of the phone/TV query: retailers often list colour inside the variant selector, not the title, so including it can hurt recall. Include colour for Myntra apparel, where each colour is a separate listing.
- Fetch the top 20-40 results per query and keep the top ~20 after a cheap brand filter. Union results from 2 query tiers before deciding "Not listed".
- On Flipkart, one search result is one product page, often for a specific variant, with sibling variants linked from that page. Following the variant selector from a family-level hit is often needed to reach the exact RAM/storage/colour page. Flipkart's DOM/JSON for variant swatches was not verified in this research.
- BM25/token blocking over your own cached snapshot is useful only if you crawl catalogues offline. For real-time use, rely on the platform search.

### Gaps
- No published data on recall of Flipkart, Myntra or Croma site search for model-code queries.
- No sourced optimal candidate count. The 10-20 figure is the project's own constraint, and the ~10 figure is from a vendor blog.

---

## 4. Similarity scoring (fuzzy string, TF-IDF, embeddings, cross-encoders)

### Takeaway
Similarity scores are good for ranking and recall but structurally bad at variant identity. Token-set fuzzy matching returns 100 when one title's tokens are a subset of the other's. Embeddings treat codes and numbers as near-noise. Two titles differing only in "128GB" vs "256GB" or "S24" vs "S24+" score ~95+. Use similarity as a soft feature and enforce attribute equality as hard constraints. Cross-encoders (joint encoding) are better at detecting the one differing detail, but they need training data.

### Cited Findings
- RapidFuzz `token_set_ratio` "returns 100.0 if one string is a subset of the other, regardless of extra content". For example, "fuzzy was a bear but not a dog" vs "fuzzy was a bear" scores 100. `token_sort_ratio` ignores word order. `partial_ratio` scores the best substring alignment. `WRatio` is a weighted combination — [RapidFuzz docs](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html)
- Shopify moved from embedding distance (L1 feature) to a joint-encoding cross-encoder (L2) because it matters "when most of the text agrees but one detail changes the identity" — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- Practitioner comparison (author estimates, methodology undisclosed) — [DEV Community](https://dev.to/_95a3e57463e6442feacd0/5-ways-to-match-aliexpress-product-variants-llm-embedding-vision-rules-and-why-i-chose-none-3afj):

  | Method | Accuracy | Latency | Main weakness |
  |---|---|---|---|
  | String rules (Levenshtein/Jaccard/TF-IDF) | 30-45% | ~0.01 ms/pair | — |
  | Sentence embeddings (MiniLM/SBERT) | 50-65% | ~5 ms/pair | Opaque codes ("03" vs "C") are "random noise", and short-string false positives (S vs M) |
  | LLM prompting | 75-90% | 3-10 s | $0.01-0.03/product |
  | Hybrid rules + synonym tables + unit parsing + dHash | 70-85% | ~1.5 ms | — |
- Fine-tuned PLM matchers on product benchmarks score F1 77.5 (RoBERTa) and 84.9 (Ditto) on WDC Products, the hardest set with 80% "corner cases" (near-identical surface forms). Zero-shot GPT-4 scores 89.6 — [Peeters et al. arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)

### Inferences
- Use rapidfuzz `token_set_ratio` / `WRatio` only for ranking candidates and for brand/family checks (e.g. require ≥85 on brand + family tokens). Never use them to accept a match.
- Build a "conflicting-numbers" feature: extract all numeric tokens with units from both titles and penalize any unit-matched number that differs (8 vs 12 GB, 55 vs 65 inch). This captures exactly what fuzzy scores hide.
- Off-the-shelf sentence-embedding cosine is fine for reranking 20 candidates. Without fine-tuning it is not useful as a match/no-match gate.
- A cross-encoder needs labelled pairs. For a small system, an LLM judge (Section 5) on 1-5 shortlisted pairs is the practical equivalent, and its decisions can later be distilled into a cross-encoder, as Shopify and arXiv 2608.25037 do.

### Gaps
- No controlled published benchmark for rapidfuzz vs TF-IDF vs embeddings on variant-level phone/TV titles was found.

---

## 5. LLM-as-judge pairwise matching

### Takeaway
Zero-shot frontier LLMs match or beat fine-tuned PLM matchers on product entity matching (GPT-4 F1 ~89.6 on WDC Products vs Ditto 84.9) at well under $1 per 1,000 pairs for small models. They do have known failure modes: they overweight shared attributes (false positives) and mishandle slight model-number differences. They are also prompt-sensitive, and small models are much worse. Use the LLM for structured extraction plus explanation, with deterministic code making the final decision from the extracted attributes.

### Cited Findings
- Peeters, Steiner, Bizer (EDBT 2025), zero-shot best-prompt F1 — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4):

  | Model | WDC Products | Abt-Buy | Walmart-Amazon | Amazon-Google |
  |---|---|---|---|---|
  | GPT-4 | 89.61 | 95.78 | 89.67 | 76.38 |
  | GPT-4o | 87.64 | 93.95 | 86.65 | 73.56 |
  | GPT-4o-mini | 81.15 | 91.93 | 86.58 | 72.18 |
  | Llama3.1-70B | 83.67 | 89.84 | 84.85 | 73.99 |
  | Mixtral | 53.37 | 82.20 | 70.44 | 40.98 |
  | Fine-tuned Ditto (baseline) | 84.90 | 91.31 | 86.39 | 80.07 |

  - "No single best prompt". GPT-4 is the least prompt-sensitive (SD 2.26 F1 across 10 prompts); other models range from SD 6.18 to 18.54.
  - In-context demos help GPT-4o on all datasets but hurt GPT-4o-mini and Mixtral on many (−4 to −26%). Related (similar) demos work best for GPT-4/4o.
  - Stating explicit matching rules did not help GPT-4 (−1 to −3%) but helped Mixtral (+3 to +17%).
  - Error analysis: false positives come from "overemphasis on matching attributes" (23 of 26 Walmart-Amazon FPs). False negatives come largely from slight model-number differences and missing attributes.
  - Approximate cost per 1,000 pairs (Aug-2024 prices, computed from per-prompt cost): GPT-4o-mini ~$0.06, GPT-4o ~$0.24, GPT-4 ~$4.74.
  - GPT-4 can generate structured explanations for its decisions.
- Fine-tuning (Steiner, Peeters, Bizer 2024), WDC Products F1 — [arXiv 2409.08185v2](https://arxiv.org/html/2409.08185v2):
  - GPT-4o-mini: 81.6 zero-shot → 83.4 fine-tuned.
  - GPT-4o: 81.6 → 87.1.
  - Llama-3.1-8B: 53.4 → 69.2.
  - Llama-3.1-70B: 75.2 → 72.7 (worse).
  - Fine-tuning cost: $5.52 (4o-mini) and $46 (4o).
  - Zero-shot inference on 4,500 pairs: $0.05 (4o-mini) vs $0.89 (4o).
  - Cross-domain generalization of fine-tuned models is weak.
  - Note: the zero-shot numbers differ slightly from 2310.11244 because of different prompts and versions.
- Production cascade: a cheap cross-encoder auto-accepts at 98% calibrated precision, and an agentic VLM handles the hard tail — [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- Shopify validates LLM-judge labels against human annotations because judge errors propagate. Expensive judgments are reused as training data and cached — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- Practitioner: LLM prompting is the most accurate method, but it is non-deterministic, rate-limited and 3-10 s per product — [DEV Community](https://dev.to/_95a3e57463e6442feacd0/5-ways-to-match-aliexpress-product-variants-llm-embedding-vision-rules-and-why-i-chose-none-3afj)

### Inferences
- Recommended pattern: "extract-then-decide".
  1. The LLM returns JSON per candidate: `{brand, model_family, model_qualifiers[], model_code, ram_gb, storage_gb, screen_in, colour_raw, colour_base, evidence_spans}`.
  2. Code then compares the fields to the source's fields under hard rules.
  3. Use a pairwise yes/no LLM judgement only as a tiebreaker when the extracted fields are null or ambiguous.
  This avoids the "overemphasis on matching attributes" failure, because a single differing field forces a reject.
- If you use a pairwise judge, use a forced enum output {match, different_variant, different_product, insufficient_info} with temperature 0. Require it to list each attribute comparison. Include domain hints, e.g. "S24 and S24 FE are different products"; "virtual RAM does not count".
- Listwise prompting (one source + all ~20 candidates in one call, "return index of exact match or none") cuts calls ~20x. ComEM-style "select" suggests this is competitive, but watch position bias and context length.
- Hallucination guards: evidence-span substring checks; never let the LLM supply an EAN/model code that is not present in the input text; cache results.

### Gaps
- No published evaluation of LLM matching specifically on Indian marketplace listings.
- No published figures for 2025-26 frontier models (Claude 4.x, GPT-5 family) on WDC Products were collected. The figures above are for 2023-24 models.

---

## 6. Colour normalization

### Takeaway
Marketing colour names must be mapped to a small base-colour vocabulary before comparison. Standard tools are a curated synonym dictionary (brand-specific names → base), a nearest-neighbour lookup in CIELAB with ΔE (CIEDE2000) when RGB/hex is available, and LLM normalization for unseen names. LLMs do well at this kind of normalization: GPT-4 reaches ~96% F1 on normalization-only tasks with examples.

### Cited Findings
- Wayfair groups colours by pairwise ΔE distance and assigns a scraped colour name to a group when ΔE < 3. It treats ΔE < 2 as negligibly different to the human eye. It notes that close shades ("medium turquoise", "blizzard blue", "middle blue") can still fall into different groups — [Wayfair Tech Blog](https://aboutwayfair.com/careers/tech-blog/from-rgb-to-descriptive-color-names-wayfairs-in-house-color-algorithms-to-improve-customer-shopping-experience)
- Empathy.co: RGB is not perceptually uniform. Their method converts RGB to LAB and takes the nearest colour (by ΔE) from a pre-classified list as the label — [Empathy.co on Medium](https://medium.com/empathyco/the-trials-and-tribulations-of-automating-colour-classification-ed3d3a750740)
- Lyst used the xkcd colour survey (~200k named colours) with nearest-neighbour lookup. They vectorised ΔE (CIE2000) because naive computation took over 5 s per name on their (2014, older) hardware — [Lyst engineering, 2014](https://making.lyst.com/2014/02/22/color-detection)
- CIEDE2000 agrees with human perception better than ΔE*ab and ΔE*94 — [Chemical Industry Journal](https://www.chemicalindustryjournal.co.uk/?p=9236)
- "Generalization" normalization (e.g. colour → base category) is moderately hard for LLMs. Example values and demos help GPT-4. Normalization-only reaches 96.1 F1 for GPT-4 with examples — [WDC-PAVE arXiv 2403.02130v4](https://arxiv.org/html/2403.02130v4)
- String and embedding methods fail on colour synonyms (Navy Blue vs Dark Blue) — [DEV Community](https://dev.to/_95a3e57463e6442feacd0/5-ways-to-match-aliexpress-product-variants-llm-embedding-vision-rules-and-why-i-chose-none-3afj)

### Inferences
- Phones and TVs: compare the **exact marketing colour name**, normalized (lowercase, strip brand prefixes), within the same brand+model. A model's official colour set is small and closed: S24 = Onyx Black / Marble Grey / Cobalt Violet / Amber Yellow. Retailers mostly reuse the official names, so exact-name-within-model is more precise than base-colour mapping. Map grey/gray and similar spellings. Fall back to base-colour equality only if one side lacks the official name. Croma's "Brand Color" vs "Color" fields map to this split: official name vs base.
- Sneakers: the multi-colour string ("White/Black-Volt") follows Nike's convention of primary / secondary - accent. Compare the ordered list. Require an equal primary base colour, and treat the set overlap of the rest as a soft score. Myntra `primaryColour` gives only one base colour (e.g. "White"), so compare only the primary when matching against Myntra. Style-code colour suffixes (-100, -001), when present on both sides, dominate.
- Apparel on Myntra: `primaryColour` is a base-colour vocabulary (Navy Blue, Black, White, Maroon...). Map Amazon's colour to the same vocabulary with a dictionary plus LLM fallback, and treat Navy Blue ≈ Blue as a soft match.
- A practical base vocabulary of ~15-20 colours (Black, White, Grey, Silver, Blue, Navy, Green, Olive, Red, Maroon, Pink, Purple, Yellow, Orange, Brown, Beige, Gold, Multi) plus a "family" grouping for soft matches.
- Image-based colour detection (dominant colour after background removal, then nearest base colour in LAB) is a useful tiebreaker for apparel. It is unreliable for multi-colour sneakers and lifestyle shots.

### Gaps
- No public e-commerce dataset mapping marketing colour names to base colours was found. You will need to build one, seeding it from Myntra's `primaryColour` vocabulary and brand colour lists.

---

## 7. Image similarity (CLIP, perceptual hashing) as tie-breaker

### Takeaway
Perceptual hashing (pHash/dHash) catches near-duplicate images, which is common because Indian retailers often reuse brand-supplied packshots. It breaks with different angles or photo styles and cannot separate variants. Off-the-shelf CLIP is better across styles but still weak at exact-SKU identity without fine-tuning. Use images only as a tie-breaker between candidates that already pass attribute constraints, mainly for apparel and sneaker colourways.

### Cited Findings
- Patent: matching retailer images to manufacturer images via perceptual hashes against a distance threshold fails when viewpoint or environment differ, and "where there are variants... may not be suitable" — [USPTO patent 12153623](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12153623)
- On fashion e-commerce product matching, CLIP-based models "strongly outperform DINO" in image-only matching. Images differ by domain (model poses, angles, lighting). A learned multimodal projection beats single-modality matching and raw CLIP — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- Vendor claim: base CLIP gave top-1 correct SKU 41% of the time on RP2K shelf photos, and a fine-tuned model gave 89%. These are vendor numbers, not independent — [Width.ai](https://www.width.ai/post/92-44-product-similarity-through-fine-tuning-clip-model-custom-pipeline-for-image-similarity)
- Shopify uses images only in its most expensive tier (L3), on selected comparisons, and notes that different angles add ambiguity — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- Practitioner: vision cannot tell quantities apart (2-pack vs 6-pack), and dHash is used as a secondary signal in their hybrid matcher — [DEV Community](https://dev.to/_95a3e57463e6442feacd0/5-ways-to-match-aliexpress-product-variants-llm-embedding-vision-rules-and-why-i-chose-none-3afj)

### Inferences
- Phones and TVs: images add almost nothing, because all storage variants share images. Skip them.
- Sneakers and apparel: compare the primary packshot of each attribute-passing candidate.
  - pHash Hamming distance ≤ ~10/64 means a near-certain same image. This threshold is a commonly used heuristic, not sourced.
  - Otherwise use CLIP cosine as a soft score.
  - Use a multimodal LLM ("same colourway? yes/no") only for residual ties.

### Gaps
- No head-to-head benchmark of CLIP vs perceptual hashing on cross-retailer product photos was found.
- No data was found on how often Amazon.in, Flipkart and Myntra share identical brand packshots.

---

## 8. Decision logic: hard constraints, thresholds, abstention, availability states

### Takeaway
Production systems use cascades with precision-first thresholds and abstention: Shopify tunes for precision first, and the Aug-2026 cascade paper calibrates auto-accept to 98% precision and escalates the rest. For this system, apply hard attribute constraints first, then soft scores to rank the survivors, then an accept threshold, with "uncertain" as a valid output. Separate "search failed/blocked" from "Not listed" explicitly. Read availability from structured data (schema.org ItemAvailability; Myntra inventoryInfo; Croma in_stock) at the variant level.

### Cited Findings
- Shopify: merge thresholds are tuned for precision first, then recall is maximized. Pairwise matches are non-transitive, and precision matters more than recall because a wrong merge is costly — [Shopify Engineering](https://shopify.engineering/catalog-clustering-part-ii)
- Cascade with a calibrated 98% precision auto-accept and escalation of ambiguous pairs — [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- Three-tier confidence (auto / review / unmatched) in a practitioner variant matcher — [DEV Community](https://dev.to/_95a3e57463e6442feacd0/5-ways-to-match-aliexpress-product-variants-llm-embedding-vision-rules-and-why-i-chose-none-3afj)
- Patent scoring: same model number → 100, different model numbers present on both sides → 0 (a hard negative) — [USPTO 11367116](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11367116)
- schema.org ItemAvailability has 12 values: BackOrder, Discontinued, InStock, InStoreOnly, LimitedAvailability, MadeToOrder, OnlineOnly, OutOfStock, PreOrder, PreSale, Reserved, SoldOut — [schema.org](https://schema.org/ItemAvailability)
- Variant-level monitoring: when price or availability differ by variant, each configuration should be tracked separately. Treating the cheapest variant as representative of the family is misleading — [Price2Spy](https://www.price2spy.com/blog/?p=12445); [Hypersonix](https://hypersonix.ai/blogs/why-accurate-product-matching-is-the-foundation-of-competitive-pricing-and-how-hypersonix-ai-does-it)
- Google requires distinct identifiers per colour/size variant — [Google Merchant Center](https://support.google.com/merchants/answer/160161)

### Inferences
Suggested pipeline per platform:
1. **Fetch health check.** Classify each fetch as OK, BLOCKED (captcha, 403/429, bot page, empty HTML with challenge JS), ERROR (timeout, 5xx) or EMPTY_RESULTS (valid search page with zero results). Use a page-structure sentinel to tell a genuine "no results" page apart from a bot wall: e.g. Flipkart's "Sorry, no results found" text, or Myntra's search JSON present with an empty products array. Only OK/EMPTY_RESULTS pages may lead to "Not listed". BLOCKED/ERROR leads to "Unknown/Check failed", never "Not listed".
2. **Hard filters**, applied when both sides have the field:
   - brand equal (alias map: "Mi" = "Xiaomi", "OnePlus" = "One Plus");
   - model family + qualifier set equal;
   - phones: RAM and storage equal;
   - TVs: screen size equal ±1" and model-code base equal if both present;
   - sneakers: style code equal if both present, otherwise primary base colour equal;
   - apparel: product type equal and base colour equal.

   A null field on one side is "unknown", not a pass. Allow it, but cap the confidence.
3. **Soft score** for ranking survivors: weighted fuzzy title score, numeric-conflict penalty, exact official colour-name match bonus, EAN match (instant accept), image similarity (apparel/sneakers).
4. **Accept** if exactly one survivor clears the threshold. If several pass, prefer exact colour name, then image similarity, then LLM tiebreak. If none pass, check whether the family exists with other variants. That justifies "Not listed (this variant)" with higher confidence than zero hits.
5. **"Not listed"** requires: the fetch was OK; at least 2 query tiers were tried; the family-level search returned results for the brand (proving search works); and no candidate passed the hard filters.
6. **Availability** comes from the matched variant's structured data:
   - Flipkart: JSON-LD `offers.availability`. InStock / LimitedAvailability / OnlineOnly / PreOrder → In stock (PreOrder may need its own flag). OutOfStock / SoldOut / Discontinued → Out of stock. Also check the visible "Sold Out" / "Coming Soon" / "Notify Me" banners, because JSON-LD can be stale on some pages.
   - Myntra: `inventoryInfo[].available` is per size. Product in stock = any size available. Optionally report the size-level detail.
   - Croma: `in_stock`. Croma availability can be pincode-dependent, so fix a pincode.
7. **Multi-variant URLs.** A Flipkart URL often represents one specific variant, with siblings in a selector. If the hit is a sibling (different RAM/colour), follow the selector link to the exact variant before reading availability. Never report a sibling's stock. If the exact variant is not offered in the selector, return "Not listed".
8. **Output** both the label and the evidence (matched URL, matched fields, confidence, fetch status) so errors are auditable. Build a labelled eval set (~100-200 Amazon products × 3 platforms) to tune thresholds for precision ≥ 95%.

### Gaps
- No sourced documentation was found on how reliably Flipkart's JSON-LD availability reflects the visible stock state, or on Croma's pincode dependence. Verify empirically.
- No published methods specific to telling bot-blocks apart from genuine zero-result pages on Indian retailers were found.
