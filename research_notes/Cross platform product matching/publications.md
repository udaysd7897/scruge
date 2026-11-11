# Academic publications and benchmarks: product matching and attribute value extraction

Research date: 2026-11-11. Numbers marked "verified" were read from the primary source page (arXiv, WDC site or paper HTML) during this session. Items marked "(unverified, from background knowledge)" were not checked against a fetched source this session and should be treated with caution or re-checked.

---

## Q1. Benchmarks (WDC Products, WDC LSPC, Abt-Buy / Amazon-Google / Walmart-Amazon): SOTA F1 and hard cases

### Takeaway
WDC Products (2023) is the current hard product-matching benchmark. It scores three things separately: how many corner cases (near-identical variants) the data contains, whether test products were seen in training, and how much training data there is. On the hardest version (80% corner cases), fine-tuned PLMs reach about 78–85 F1 on seen products and fall to about 53–70 F1 on unseen ones. Zero-shot GPT-4 reaches 89.6 F1 and fine-tuned GPT-4o-mini reaches 88.9 F1. The classic Magellan/DeepMatcher sets are close to saturated: Abt-Buy is in the mid-90s and Walmart-Amazon about 87–93. Amazon-Google (about 76–87) is the exception.

### Cited Findings
**WDC Products (Peeters, Der, Bizer; EDBT 2024 / arXiv 2023)**
- Built from schema.org product offers in Common Crawl (2020) from 3,259 e-shops: 11,715 offers describing 2,162 products. The splits are strictly separated, each covering 500 products. Attributes are title, description, price, priceCurrency and brand. — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- There are 27 variants along 3 dimensions: corner-case ratio (80/50/20%), unseen entities in test (0/50/100%), and dev-set size (pair-wise Small 2,500 / Medium 6,000 / Large 19,835 pairs). Test sets have 4,500 pairs. A multi-class variant also exists. — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- Label noise is about 4% (two annotators, 600 pairs, Cohen's kappa 0.91). This implies a practical ceiling of about 96 F1. — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- Baselines, verified (F1, 80% corner cases, Large dev set; Seen / Half-Seen / Unseen):
  - Word-Cooc 56.67 / 50.24 / 30.26
  - Magellan 31.96 / 36.42 / 34.95
  - RoBERTa 78.15 / 75.52 / 69.75
  - Ditto 79.12 / 75.43 / 68.35
  - HierGAT 75.42 / 73.20 / 68.53
  - R-SupCon 82.15 / 67.27 / 53.31

  — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- Easiest variant (20% corner cases, Large, Seen): R-SupCon 89.04, RoBERTa 87.80, Ditto 87.52. Unseen: RoBERTa 78.64, Ditto 76.29, R-SupCon 62.45. — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- Multi-class micro-F1, 80% corner cases, Large: R-SupCon 89.33, RoBERTa 78.77, word-occurrence 79.40. — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- The site's own takeaways:
  - Performance drops as the corner-case ratio rises.
  - Unseen entities cause large drops, especially for R-SupCon. Contrastive learning memorises seen product clusters.
  - Model rankings stay largely stable.

  — [WDC Products site](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)

**Classic benchmarks with LLMs and PLMs (from Peeters, Steiner, Bizer, EDBT 2025)**
- Zero-shot best-prompt F1, verified (WDC Products 80% cc / Abt-Buy / Walmart-Amazon / Amazon-Google):

  | Model | WDC Products | Abt-Buy | Walmart-Amazon | Amazon-Google |
  |---|---|---|---|---|
  | GPT-4 | 89.61 | 95.78 | 89.67 | 76.38 |
  | GPT-4o | 87.64 | 93.95 | 86.65 | 73.56 |
  | GPT-4o-mini | 81.15 | 91.93 | 86.58 | 72.18 |
  | Llama-3.1-70B | 83.67 | 89.84 | 84.85 | 73.99 |
  | Llama-2-70B | 69.09 | 82.03 | 63.91 | 57.93 |
  | Mixtral | 53.37 | 82.20 | 70.44 | 40.98 |
  | Fine-tuned RoBERTa | 77.53 | 91.21 | 87.02 | 79.27 |
  | Fine-tuned Ditto | 84.90 | 91.31 | 86.39 | 80.07 |

  — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- Amazon-Google is the one product benchmark where fine-tuned PLMs still beat zero-shot GPT-4. Its hard cases are software editions and versions. — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- R-SupCon (2022) reported 94.29 F1 on Abt-Buy and 79.28 on Amazon-Google (+3.24 and +3.7 over the prior SOTA) and +0.8 to +8.84 on WDC Computers. — [arXiv 2202.02098](https://arxiv.org/abs/2202.02098v2)

**WDC LSPC / Training Set for Large-Scale Product Matching (2019–2020)**
- The predecessor corpus, also built from schema.org offers clustered by product identifiers (GTIN/MPN). It has category-specific training sets (Computers, Cameras, Watches, Shoes, plus an "All" set) and a hand-verified gold standard. WDC Computers was the testbed for R-SupCon. — [WDC LSPC site](https://webdatacommons.org/largescaleproductcorpus/v2/index.html); [arXiv 2202.02098](https://arxiv.org/abs/2202.02098v2)

### Inferences
- For a variant-sensitive matcher, report results by corner-case or variant slice and by seen/unseen products. Aggregate F1 on Abt-Buy-style data hides variant failures.
- With about 4% label noise, a WDC Products score near 90 F1 is close to the ceiling. Remaining errors cluster in true corner cases.

### Gaps
- I did not fetch the WDC LSPC v2 page in this session, so its exact sizes and gold-standard F1 numbers are unverified (about 26M offers and 16M clusters, from background knowledge).
- No Papers With Code leaderboard snapshot was retrieved (the site was discontinued in 2025).

---

## Q2. Pre-LLM deep learning matchers

### Takeaway
The field moved through three stages:
1. **DeepMatcher (2018):** attribute-wise RNN and attention.
2. **Ditto (2020/21):** fine-tuned BERT/RoBERTa over serialised pairs, plus domain-knowledge highlighting, summarisation and augmentation.
3. **Specialisations:** contrastive (R-SupCon), semi- or self-supervised (Rotom, Sudowoodo), hierarchical graph attention (HierGAT) and multi-task (JointBERT).

On WDC Products, plain RoBERTa or Ditto is as good as or better than the fancier variants on unseen products.

### Cited Findings
- **Ditto** (Li, Li, Suhara, Doan, Tan; arXiv April 2020, VLDB 2021):
  - Treats matching as sequence-pair classification with a fine-tuned BERT, DistilBERT or RoBERTa.
  - Adds domain-knowledge injection (highlighting key spans such as product IDs and numbers), summarisation of long strings, and data augmentation.
  - Gains up to 29% F1 over the prior SOTA, plus up to 9.8% from the optimisations. Matches the previous SOTA with at most half the labels. Reaches 96.5% F1 on a real company-matching task (789K × 412K records).

  — [arXiv 2004.00584](https://arxiv.org/abs/2004.00584)
- Ditto on the Magellan sets (as reported in Narayan et al.'s comparison): Walmart-Amazon 86.76, Amazon-Google 75.58, Beer 94.37, iTunes-Amazon 97.06, DBLP-ACM 98.99. — [Narayan et al., ar5iv 2205.09911](https://ar5iv.labs.arxiv.org/html/2205.09911)
- **Magellan** (classical features plus random forest) on the same sets: Walmart-Amazon 71.9 and Amazon-Google 49.1. — [ar5iv 2205.09911](https://ar5iv.labs.arxiv.org/html/2205.09911)
- **R-SupCon** (Peeters & Bizer; WWW'22 Companion; arXiv Feb 2022):
  - Pre-trains RoBERTa-base with supervised contrastive loss using product-ID clusters, then fine-tunes a pair classifier.
  - Self-supervised contrastive pre-training without IDs hurt performance (attributed to label noise).
  - Strong on seen products but weak on unseen ones (WDC Products, see Q1).

  — [arXiv 2202.02098](https://arxiv.org/abs/2202.02098v2); [WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- **HierGAT** (hierarchical graph attention): 75.42 / 73.20 / 68.53 F1 (Seen / Half / Unseen) on WDC Products, 80% cc, Large. That is below RoBERTa and Ditto. — [WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- **JointMatcher** (Knowledge-Based Systems, 2022): a "numerically-aware" PLM matcher with attention concentration. It was motivated by PLMs' "number insensitiveness" for product IDs. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0950705122005044)
- **Paganelli et al., "Analyzing How BERT Performs Entity Matching"** (PVLDB 15, 2022): a probing analysis of what BERT attends to in EM. — [VLDB PDF](https://www.vldb.org/pvldb/vol15/p1726-paganelli.pdf)

The following papers are known references, but their details were not verified in this session:
- **DeepMatcher** (Mudgal et al., SIGMOD 2018). — [ACM DL](https://dl.acm.org/doi/10.1145/3183713.3196926)
- **JointBERT** (Peeters & Bizer, "Dual-Objective Fine-Tuning of BERT for Entity Matching", PVLDB 14, 2021). It adds a multi-class product-ID objective to binary matching.
- **Rotom** (Miao, Li, Wang, Tan; SIGMOD 2021): meta-learned augmentation for low-resource EM.
- **Sudowoodo** (Wang, Li, Wang; ICDE 2023): contrastive self-supervised representation learning for data integration.

### Inferences
- Contrastive or ID-cluster methods (R-SupCon, JointBERT) behave like product-ID classifiers. They suit closed catalogues (seen products) and degrade sharply on new SKUs, which is the normal case in cross-platform matching.
- Ditto's "highlight the key spans" idea is the earliest mainstream acknowledgement that numbers and model codes need special treatment.

### Gaps
- Exact Rotom, Sudowoodo and JointBERT F1 numbers were not retrieved this session.

---

## Q3. LLM-based matching

### Takeaway
GPT-4-class models zero-shot already match or beat fine-tuned PLMs on product benchmarks, especially on unseen products. Fine-tuning a small hosted model (GPT-4o-mini) closes most of the gap at about half the zero-shot inference cost. Small fine-tuned open models (AnyMatch on GPT-2, Jellyfish-13B) trail GPT-4 by about 4 F1 on average but cost orders of magnitude less. Prompt choice, demonstration selection and batching matter a lot, but they matter differently for each model.

### Cited Findings
- **Narayan et al., "Can Foundation Models Wrangle Your Data?"** (arXiv May 2022, PVLDB 16(4) 2022). GPT-3 175B results (k = number of demonstrations):

  | Dataset | k=0 | k=10 |
  |---|---|---|
  | Walmart-Amazon | 60.6 | 87.0 (Ditto 86.76) |
  | Amazon-Google | 54.3 | 63.5 (Ditto 75.58) |
  | Beer | 78.6 | 100 |
  | iTunes-Amazon | 65.9 | 98.2 |

  Hand-crafted demonstrations (≤1 hour of error analysis per task) beat random ones by 14.7 F1 on average. — [ar5iv 2205.09911](https://ar5iv.labs.arxiv.org/html/2205.09911); [PVLDB PDF](https://www.vldb.org/pvldb/vol16/p738-narayan.pdf)
- **Peeters, Steiner, Bizer, "Entity Matching using Large Language Models"** (arXiv Oct 2023, v4 Oct 2024; EDBT 2025). This line of work, including "Using ChatGPT for Entity Matching" (2023), is released as "MatchGPT".
  - **Zero-shot:** see the Q1 table (GPT-4 89.61 on WDC Products).
  - **Prompt sensitivity:** no single prompt is best. GPT-4 is least prompt-sensitive (SD 2.26).
  - **Transfer:** PLMs trained on other product datasets and tested on WDC Products collapse to 16–55 F1. GPT-4 zero-shot beats the best transferred PLM by 40–68 F1.

  — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4); [MatchGPT GitHub](https://www.github.com/wbsg-uni-mannheim/MatchGPT)
- **In-context learning** (same paper):
  - GPT-4o with 10 related demonstrations: WDC 91.74, Abt-Buy 94.87, Walmart-Amazon 90.63 (mean 91.21 vs 88.10 zero-shot).
  - GPT-4 changes little (89.95 → 90.80 mean) and drops on WDC (86.45).
  - GPT-4o-mini gets worse with demonstrations (85.51 → 76.56 mean).

  — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- **Matching rules in the prompt:**
  - GPT-4-learned rules cost GPT-4 1–3 F1.
  - Rules help weak models: Mixtral goes from 69.18 to 79.03 mean with hand-written rules and to 74.53 with learned rules.

  — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- **Fine-tuning GPT-4o-mini:**
  - Results: WDC 88.89 (zero-shot 81.15), Abt-Buy 94.17, Walmart-Amazon 92.99, Amazon-Google 87.11. It beats zero-shot GPT-4 on 4 of 6 datasets.
  - Fine-tuning Llama did not help on WDC Products.
  - Transfer from other product datasets to WDC Products costs at least 12 F1 against zero-shot.

  — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- **Cost** (per prompt on WDC, Aug 2024 prices): GPT-4o-mini zero-shot 0.006¢, GPT-4o 0.024¢, GPT-4 0.474¢, GPT-4 10-shot 3.037¢, fine-tuned GPT-4o-mini 0.003¢. — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- **Explanations:** GPT-4 can produce structured explanations and cluster errors into classes. Its accuracy at assigning errors to classes is 73–88%. — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- **Steiner, Peeters, Bizer, "Fine-tuning LLMs for Entity Matching"** (arXiv Sept 2024, rev. May 2025; ICDE 2025 workshops):
  - Fine-tuning helps small models most. Results for large models are mixed.
  - Adding structured explanations to training data helped 3 of 4 LLMs.
  - Example selection and generation helped Llama-3.1-8B but hurt GPT-4o-mini.
  - Fine-tuning improves in-domain generalisation but hurts cross-domain transfer. Fine-tuned GPT-4o gained most on WDC but beat its baseline on only 1 of 3 other datasets.

  — [arXiv 2409.08185](https://arxiv.org/html/2409.08185v2); [search summary of v1](https://arxiv.org/html/2409.08185v1)
- **AnyMatch** (Zhang, Groth, Calixto, Schelter; arXiv Sept 2024):
  - A GPT-2 sequence classifier fine-tuned with transfer learning and careful data selection, using no target labels.
  - Ranks 2nd of 14 methods. Its average F1 is only 4.4% below MatchGPT/GPT-4, at about 3,899× lower cost per 1K tokens.
  - Jellyfish-13B was pretrained on benchmark data, so its zero-shot scores are contaminated.

  — [arXiv 2409.04073](https://arxiv.org/abs/2409.04073); [PDF](https://arxiv.org/pdf/2409.04073)
- **Cross-dataset EM study** (UvA; EDBT 2025, "A Deep Dive Into Cross-Dataset Entity Matching with Large and Small Language Models"): notes that Jellyfish is evaluated on only two e-commerce datasets. — [UvA PDF](https://pure.uva.nl/ws/files/331179344/A_Deep_Dive_Into_Cross-Dataset_Entity_Matching_with_Large_and_Small_Language_Models.pdf); [OpenProceedings](https://openproceedings.org/2025/conf/edbt/paper-224.pdf)
- **BatchER** (Fan et al.; arXiv Dec 2023, ICDE 2024):
  - Batch prompting for ER, with demonstration selection plus question batching (several pairs per prompt).
  - Claimed to be more cost-effective than both fine-tuned PLMs and manually designed LLM prompting. Its best configuration combines the highest accuracy with the lowest cost.

  — [arXiv 2312.03987](https://arxiv.org/html/2312.03987v1)
- **Newer 2026 preprints surfaced but not read:**
  - "Labeling Training Data for Entity Matching Using LLMs" — [arXiv 2606.28823](https://arxiv.org/pdf/2606.28823)
  - "Beyond Scale and Generation: Understanding Language Model-based Entity Matching", which reports that embedding-oriented model variants work better as bi-encoders — [arXiv 2607.24688](https://arxiv.org/abs/2607.24688)

### Inferences
- **A practical architecture:**
  1. A cheap blocker or bi-encoder.
  2. A fine-tuned small LLM or PLM for most pairs.
  3. Escalation of uncertain pairs, or pairs with conflicting attributes, to a GPT-4-class model with an explicit attribute-comparison prompt.

  This matches the cost and accuracy profile reported above.
- LLMs beat PLMs most clearly on unseen products. That matters more for cross-platform matching than in-distribution F1 does.
- Using an LLM to label training data, then distilling into a small model, is the direction the 2024–2026 work is moving.

### Gaps
- I could not open Jellyfish's own paper (Zhang et al., 2023/2024). Its per-dataset numbers are unverified.
- Exact BatchER cost and F1 figures were not retrieved.
- No source this session reported GPT-5-era or Claude results on WDC Products.
- Self-consistency for EM: no specific paper retrieved.

---

## Q4. Product attribute value extraction (AVE)

### Takeaway
AVE moved through three stages:
1. Sequence tagging: OpenTag (2018, about 83 F1 on its own data).
2. QA-style extraction: AVEQA and MAVEQA (2021–22, about 98 F1 on MAVE, a dataset of 2.2M Amazon products).
3. LLMs: ExtractGPT, where GPT-4 reaches about 85% average F1 on harder open benchmarks, 5 points above the best PLM. Llama-3-70B comes close.

LLMs generalise better to unseen attribute values. Fine-tuned models overfit to the values they have seen.

### Cited Findings
- **OpenTag** (Zheng, Mao, Dong, Li; Amazon; KDD 2018): BiLSTM-CRF with attention and active learning. Reports an F-score of 83%. — [arXiv 1806.01264](https://arxiv.org/abs/1806.01264v2)
- **AdaTag** (Yan et al., arXiv June 2021): multi-attribute extraction with an adaptive CRF decoder. Improves on prior methods on a real e-commerce dataset (numbers not retrieved). — [arXiv 2106.02318](https://ar5iv.arxiv.org/html/2106.02318)
- **MAVE** (Yang et al., Google; WSDM 2022):
  - 2.2M Amazon products with 3M attribute-value annotations across 1,257 categories, using multiple sources (title, description, features).
  - The labels are released on GitHub and must be joined with Amazon Review Data 2018.
  - Secondary sources report MAVEQA at about 98.32 F1 vs AVEQA 98.14 and AD-OpenTag 79.73, but these are not verified against the paper.

  — [Google Research](https://research.google/pubs/mave-a-product-dataset-for-multi-source-attribute-value-extraction/); [arXiv 2112.08663](https://arxiv.org/abs/2112.08663v1); [liner review (secondary)](https://liner.com/review/mave-product-dataset-for-multisource-attribute-value-extraction)
- **ExtractGPT** (Brinkmann, Shraga, Bizer; arXiv Oct 2023, v5 Sept 2024):
  - GPT-4 achieves the best average F1, 85%, using detailed attribute descriptions plus demonstrations. That is 5 points above the best PLM baseline.
  - Llama-3-70B is nearly as good.
  - JSON vs textual target-schema representations were compared.
  - Fine-tuning GPT-3.5 reaches GPT-4 level but reduces generalisation to unseen attribute values.

  — [arXiv 2310.12537](https://arxiv.org/abs/2310.12537)
- **WDC-PAVE benchmark** (aggregator listing): SU-OpenTag 60.44 F1 and AVEQA 80.83 F1. The low PLM scores show that classical AVE models struggle on heterogeneous web-shop data. — [hyper.ai WDC-PAVE listing](https://hyper.ai/cn/sota/tasks/attribute-value-extraction/benchmark/attribute-value-extraction-on-wdc-pave)

### Inferences
- For variant-sensitive matching, run LLM-based AVE first to extract normalised RAM, storage, colour and screen size from both offers, then compare those fields deterministically. This combines LLM generalisation with exact numeric comparison.
- MAVE's near-98 F1 overstates real-world difficulty, because its values mostly appear verbatim in the text. WDC-PAVE and ExtractGPT-style evaluations are closer to cross-platform reality.

### Gaps
- I did not retrieve the related Brinkmann/Bizer work on attribute value normalisation (WDC-PAVE, 2024) or the "self-refinement" and "using LLMs for AVE with schema" follow-ups in primary form.
- AdaTag F1 numbers were not retrieved.

---

## Q5. Industry papers (Amazon, Flipkart, Walmart, eBay, Rakuten, Shopee) and multimodal matching

### Takeaway
Most published industry work comes from Amazon. It covers variant relationships, multimodal similarity and catalogue error detection. Flipkart has little public work on matching specifically. Multimodal (text + image) fusion consistently beats unimodal matching, but images cannot separate storage or RAM variants.

### Cited Findings
- **Amazon, VARM** ("Learning variant product relationship and variation attributes from e-commerce website structures", arXiv Oct 2024): defines variant-relationship ER, i.e. predicting whether two products are variants of each other, and extracts the variation attributes. — [arXiv 2410.02779](https://arxiv.org/abs/2410.02779)
- **Amazon, MAPS** ("Multimodal Attention for Product Similarity", WACV 2022): metric learning on catalogue images plus text that places identical items close together. — [CVF PDF](https://openaccess.thecvf.com:443/content/WACV2022/papers/Das_MAPS_Multimodal_Attention_for_Product_Similarity_WACV_2022_paper.pdf)
- **Amazon Science blog:** an image-plus-title model that links variants differing in colour, size or style, and detects catalogue errors. — [Amazon Science](https://amazon.science/blog/using-computer-vision-to-weed-out-product-catalogue-errors)
- **Amazon, schema matching** for catalogue enrichment based on attribute similarity and relevance. — [Amazon Science PDF](https://cdn.amazon.science/fc/c5/dc776a3a4b4993bb01afc5688048/a-ribute-similarity-and-relevance-based-product-schemamatching-for-targeted-catalog-enrichment.pdf)
- **VarSpot** (Amazon co-authors): detecting catalogue records that are variations of each other. — [NSF PAR](https://par.nsf.gov//servlets/purl/10181177)
- **Flipkart** (arXiv 2017, "Deep Learning based Large Scale Visual Recommendation and Search"): reuses visual similarity to remove near-duplicate listings uploaded by multiple sellers. — [arXiv 1703.02344](https://arxiv.org/pdf/1703.02344)
- **Turkish marketplace deduplication** (arXiv Sept 2025): a BERT text model plus masked-autoencoder image embeddings feeding a decider model. Macro-F1 0.90. — [arXiv 2509.15858](https://arxiv.org/html/2509.15858v2)
- **Intermediate fusion for multimodal product matching** (Leipzig, GvDB 2024): tested on data including Zalando's. It beats both unimodal and multimodal baselines. — [CEUR-WS](https://ceur-ws.org/Vol-3710/paper14.pdf)
- **Mexico cross-store matching** (Mathematics, 2022): text plus images beats unimodal for the two largest Mexican e-shops. — [MDPI](https://doi.org/10.3390/math10152564)

### Inferences
- Images help with colour variants (a shoe in different colours) and product type. They hurt storage or RAM variants (identical photos) and screen-size variants (often the same marketing image). Text and attribute signals must decide those cases.
- Amazon treats "is a variant of" as a separate relation from "is the same product". A useful design is three outputs: exact match, variant (same parent), and different product.

### Gaps
- I found no public Flipkart, Walmart, eBay, Rakuten or Shopee paper on pairwise product matching in this session. The Shopee Kaggle "Price Match Guarantee" (2021) competition is a known public multimodal resource but was not verified here.
- No industry paper reported precision on variant-only slices.

---

## Q6. Numeric and variant attributes: known weaknesses and fixes

### Takeaway
Transformer and embedding matchers, and even GPT-4, systematically mishandle near-identical variants. They over-weight shared brands and model numbers (false positives) and are thrown by small code or number differences (both error types). Subword tokenisation fragments numbers. The mitigations are:
- numeric-aware encoders and highlighting (Ditto, JointMatcher);
- explicit attribute extraction plus rule constraints;
- LLM prompts or rules that enumerate variant attributes;
- evaluation sets dense in corner cases (WDC Products).

### Cited Findings
- **GPT-4 error analysis on Walmart-Amazon:**
  - False positives: 23 of 26 are "overemphasis on matching attributes" (brand or model number), 21 "ignoring minor but significant differences", and 14 "price discrepancy overlooked".
  - False negatives: 9 of 15 are "model number mismatch" (slight code differences) and 7 "variant/accessory differences".

  — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- PLMs show "number insensitiveness", which is critical for product IDs. JointMatcher adds a numerically-aware component. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0950705122005044)
- Subword tokenisers split numbers such as "3418" into fragments, hiding their length and composition. This motivates numeric-pattern-aware transformers for fine-grained disambiguation. — [Complex & Intelligent Systems, 2025](https://link.springer.com/article/10.1007/s40747-025-01936-3)
- Pretrained transformers perform worst on numeric entities and handle different numeric representations of the same entity poorly. — [arXiv 2112.08327](https://arxiv.org/pdf/2112.08327)
- Ditto's domain-knowledge injection highlights spans such as numbers and IDs to steer attention. — [arXiv 2004.00584](https://arxiv.org/abs/2004.00584)
- Rules help weaker LLMs considerably (Mixtral +10 F1 mean with hand-written rules) but slightly hurt GPT-4. — [arXiv 2310.11244v4](https://arxiv.org/html/2310.11244v4)
- Raising WDC Products from 20% to 80% corner cases costs every model about 7–10 F1 (e.g. RoBERTa Large/Seen 87.80 → 78.15). — [WDC Products](https://webdatacommons.org/largescaleproductcorpus/wdc-products/)
- A 2025 heterogeneity survey finds that data with diverse, complex attributes (Walmart-Amazon) makes all models more vulnerable. — [arXiv 2508.08076](https://arxiv.org/html/2508.08076v1)

### Inferences (design lessons for a high-precision variant-aware matcher)
1. **Never let a single similarity score decide.**
   - Extract variant-defining attributes (storage, RAM, colour, size in inches, pack count, model code) from both offers using LLM AVE (Q4) plus regexes for units.
   - Normalise units: GB/TB, inch/cm, colour synonyms.
   - Apply hard veto rules: if both offers have a value for a variant attribute and the values differ, the result is non-match. Missing values go to a model or LLM rather than counting as matches.
2. **Treat model numbers or MPN/GTIN as strong but not sufficient evidence.** GPT-4's main false-positive mode is over-trusting them. Compare suffixes and region codes character by character, e.g. Samsung QE55… vs QE65… encodes 55 vs 65 inches.
3. **Use an LLM as the adjudicator for ambiguous pairs.**
   - Prompt it to list the differing attributes before deciding: structured explanation, which also improved fine-tuning in Steiner et al.
   - Use a three-way output: same / variant / different.
4. **Calibrate for precision.** Tune thresholds on a variant-dense validation set (WDC-style 80% corner cases), report precision on variant slices separately, and expect unseen-product performance to fall.
5. **Prefer approaches that generalise to unseen products** (LLMs, RoBERTa/Ditto-style cross-encoders) over ID-cluster contrastive models (R-SupCon) for open cross-platform catalogues.

### Gaps
- I found no paper that quantifies matcher accuracy specifically on RAM/storage or screen-size variant pairs. WDC Products corner cases are the nearest proxy, but they are not broken down by attribute type.
- No primary source was retrieved for hybrid "rule veto + neural" product matchers with measured precision gains. The design lessons above are inferences.
