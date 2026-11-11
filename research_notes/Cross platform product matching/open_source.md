# Open-Source Entity Matching / Product Matching Libraries and Projects (status as of Nov 2026)

Use case: match one Amazon India product against roughly 10-20 search-result candidates each from Flipkart, Croma and Myntra, in real time, with an exact variant match (brand + model + RAM/storage for phones, screen size for TVs, colour for sneakers/apparel).

Metadata method: star counts, last push dates, licenses and archived flags were pulled from the GitHub REST API (`gh api repos/<owner>/<repo>`) on 2026-11-11. Latest release versions and dates came from the PyPI JSON API on the same day. Source links point to each repo or PyPI page.

## 1. General entity-matching libraries: approach, blocking, training data, stack, status, license, fit

### Takeaway
None of the classic EM libraries fits this use case well. Their main value is in two areas: (a) blocking and deduplication over large tables, which we do not need because a store's search engine already returns about 15 candidates, and (b) supervised or active-learning matchers that need labelled pairs. Only two kinds of option work off the shelf without training data. One is the LLM-based approach (the MatchGPT prompts, Jellyfish, ComEM "select" strategy) used with zero-shot prompts. The other is Splink's unsupervised Fellegi-Sunter model, which is built for structured person/record tables rather than free-text product titles. The research systems (Ditto, DeepMatcher, HierGAT, Sudowoodo, PromptEM, Unicorn, AnyMatch) are mostly dormant paper code with no PyPI release.

### Cited Findings

**Summary table (GitHub API and PyPI, 2026-11-11)**

| Project | Approach | Labels needed? | Stack | Stars | Last push / release | License |
|---|---|---|---|---|---|---|
| Ditto (megagonlabs/ditto) | Fine-tuned PLM (RoBERTa/DistilBERT) on serialized pairs, plus domain-knowledge injection, summarization and data augmentation | Yes (labelled pairs) | Python/PyTorch | 321 | push 2024-04-17 | Apache-2.0 |
| DeepMatcher (anhaidgroup) | Deep learning (RNN/attention attribute summarization) | Yes | Python/PyTorch | 624 | push 2024-06; PyPI 0.1.2.post2, 2021-06-13 | BSD-3 |
| py_entitymatching / Magellan (anhaidgroup) | Rules + classic ML (RF, SVM, etc.) on similarity features; explicit blockers (attribute equivalence, overlap, rule-based) | Yes (for ML); rules can be hand-written | Python | 195 | push 2024-05; PyPI 0.4.2, 2024-02-07 | BSD-3 |
| Dedupe (dedupeio/dedupe) | Active learning + logistic regression on string distances; learned blocking predicates; clustering | Yes (interactive active-learning labelling) | Python | 4,529 | push 2025-07-29; PyPI 3.0.3, 2024-08-15 | MIT |
| Splink (moj-analytical-services) | Probabilistic Fellegi-Sunter with EM estimation; SQL backends (DuckDB, Spark, Athena, Postgres) | No (unsupervised EM) | Python + SQL | 2,572 | push 2026-11-11; PyPI 5.0.0, 2026-09-28 | MIT |
| recordlinkage (J535D165) | Indexing (full, blocking, sorted neighbourhood), comparison features, supervised and unsupervised classifiers (ECM, KMeans) | Optional | Python/pandas | 1,067 | push 2024-02; PyPI 0.16, 2023-07-20 | BSD-3 |
| Zingg (zinggAI/zingg) | Active-learning ML on Spark; learned blocking | Yes (interactive labelling) | Java/Scala/Spark, Python API | 1,271 | push 2026-11-03; PyPI 0.7.0, 2026-08-10 | AGPL-3.0 |
| pyJedAI (AI-team-UoA) | End-to-end ER workflows: blocking (token, embedding/FAISS), block cleaning, similarity/embedding matching, clustering | Mostly no (schema-agnostic, unsupervised workflows) | Python | 100 | push 2026-03-22; PyPI 0.3.6, 2025-11-03 | Apache-2.0 |
| JedAI Toolkit (scify) | Java predecessor of pyJedAI | No | Java | 224 | **archived**; push 2025-07 | Apache-2.0 |
| AnyMatch (Jantory/anymatch) | Small LM (GPT-2 default in examples) fine-tuned on other datasets, then applied zero-shot to the target (leave-one-dataset-out) | No target labels, but needs training on the public EM benchmarks first | Python/PyTorch | 10 | push 2025-01 | none stated |
| Unicorn (ruc-datalab) | Unified multi-task matching model (EM, schema matching, etc.) with a mixture-of-experts encoder | Pretrained model; supports zero-shot on new tasks | Python/PyTorch | 32 | push 2023-04 | none stated |
| HierGAT (CGCL-codes) | Hierarchical graph attention + Transformer | Yes | Python/PyTorch | 24 | push 2023-08 | MIT |
| Sudowoodo (megagonlabs) | Self-supervised contrastive pretraining; semi-supervised or unsupervised matching; also blocking | Few or none | Python/PyTorch | 19 | push 2023-05 | BSD-3 |
| PromptEM (ZJU-DAILY) | Prompt-tuning PLMs for low-resource generalized EM | Few | Python/PyTorch | 27 | push 2022-09 | Apache-2.0 |
| MatchGPT (wbsg-uni-mannheim) | LLM prompting (zero-shot, few-shot, in-context demos, rule-augmented prompts) | No (zero-shot) | Python + LangChain/OpenAI | 68 | push 2024-10 | none stated |
| TailorMatch (wbsg-uni-mannheim) | Fine-tuning LLMs for EM | Yes | Python | 10 | push 2025-06 | none stated |
| contrastive-product-matching (wbsg-uni-mannheim) | Supervised contrastive learning (R-SupCon) for product offers | Yes | Python | 38 | push 2022-02 | BSD-3 |
| ComEM (tshu-w) | LLM strategies: "match" (pairwise), "compare", and "select" (pick the match from a candidate list); compound pipelines combine a cheap filter with an LLM | No (zero-shot) | Python | 22 | push 2026-05-27 | none stated |
| Jellyfish-7B/8B/13B (NECOUDBFM, Hugging Face) | Instruction-tuned open LLM for data preprocessing (EM, error detection, imputation, schema matching) | No (zero-shot prompt) | HF Transformers | n/a | HF model | see model card |

Sources: [ditto](https://github.com/megagonlabs/ditto), [deepmatcher](https://github.com/anhaidgroup/deepmatcher), [deepmatcher PyPI](https://pypi.org/project/deepmatcher/), [py_entitymatching](https://github.com/anhaidgroup/py_entitymatching), [py-entitymatching PyPI](https://pypi.org/project/py-entitymatching/), [dedupe](https://github.com/dedupeio/dedupe), [dedupe PyPI](https://pypi.org/project/dedupe/), [splink](https://github.com/moj-analytical-services/splink), [splink PyPI](https://pypi.org/project/splink/), [recordlinkage](https://github.com/J535D165/recordlinkage), [recordlinkage PyPI](https://pypi.org/project/recordlinkage/), [zingg](https://github.com/zinggAI/zingg), [zingg PyPI](https://pypi.org/project/zingg/), [pyJedAI](https://github.com/AI-team-UoA/pyJedAI), [pyjedai PyPI](https://pypi.org/project/pyjedai/), [JedAIToolkit](https://github.com/scify/JedAIToolkit), [anymatch](https://github.com/Jantory/anymatch), [Unicorn](https://github.com/ruc-datalab/Unicorn), [HierGAT](https://github.com/CGCL-codes/HierGAT), [sudowoodo](https://github.com/megagonlabs/sudowoodo), [PromptEM](https://github.com/ZJU-DAILY/PromptEM), [MatchGPT](https://github.com/wbsg-uni-mannheim/MatchGPT), [TailorMatch](https://github.com/wbsg-uni-mannheim/TailorMatch), [contrastive-product-matching](https://github.com/wbsg-uni-mannheim/contrastive-product-matching), [ComEM](https://github.com/tshu-w/ComEM), [Jellyfish HF](https://huggingface.co/NECOUDBFM/Jellyfish)

**LLM-based EM findings**
- Peeters, Steiner and Bizer ("Entity Matching using Large Language Models", EDBT 2025): the best LLMs need "no or only a few training examples" to match PLMs (BERT/RoBERTa) fine-tuned on thousands of examples. LLM matchers are also more robust to unseen entities. No single prompt is best, so prompts must be tuned per model and dataset. GPT-4 can generate structured explanations of its matching decisions. — [arXiv 2310.11244](https://arxiv.org/abs/2310.11244)
- The same group finds that open-source LLMs are a viable alternative to hosted LLMs when data cannot be shared, provided a small amount of training data or matching rules is available. — [arXiv PDF](https://arxiv.org/pdf/2310.11244)
- MatchGPT holds the code and prompt examples for "Using ChatGPT for Entity Matching" and "Entity Matching using Large Language Models". It is a reproduction repo, not a packaged library. — [MatchGPT](https://github.com/wbsg-uni-mannheim/MatchGPT)
- Jellyfish is fine-tuned from OpenOrca-Platypus2-13B (13B) and Mistral-7B-Instruct-v0.2 (7B). The authors say it runs on a single low-cost GPU. The model card reports entity-matching F1 of 81.34 on Amazon-Google for Jellyfish-13B against 74.21 for GPT-4 (authors' own numbers). — [Jellyfish HF](https://huggingface.co/NECOUDBFM/Jellyfish), [arXiv 2312.01678](https://arxiv.org/abs/2312.01678v1)
- The AnyMatch repo does zero-shot EM with a small LM. Its `loo.py` trains on the other benchmark datasets and evaluates on a held-out one (`--base_model gpt2`). Base-model ablations cover t5-base and bert-base. Setup requires downloading nine raw datasets and preprocessing them. — [anymatch](https://github.com/Jantory/anymatch)
- ComEM (COLING 2025, "Match, Compare, or Select?") studies the "select" strategy, where the LLM picks the matching record from a list of candidates. This is the same shape as our problem: one anchor and about 15 candidates per store. — [ComEM](https://github.com/tshu-w/ComEM)

### Inferences
- **Usable off the shelf without training data:** Splink (unsupervised EM; better for structured fields than free-text titles), pyJedAI (unsupervised similarity and embedding workflows), recordlinkage (the ECM/KMeans classifiers), Jellyfish (a local LLM, zero-shot prompt), MatchGPT/ComEM prompt designs used with any hosted LLM, and Unicorn's pretrained model (zero-shot in principle, but the code is stale). **Need labels:** Ditto, DeepMatcher, Magellan ML, Dedupe, Zingg, HierGAT, TailorMatch, contrastive-product-matching. **Need few labels:** PromptEM, Sudowoodo.
- **Blocking is irrelevant here.** Each store's own search engine is the blocker, and with at most 60 candidates per query every pair can be scored. The batch frameworks (Splink, Zingg, Dedupe, pyJedAI) are designed for table-to-table linkage at scale, so they are overkill for a per-request web app. Zingg's AGPL-3.0 license is also a concern for a hosted web app.
- **Best fit for the app:** a hybrid pipeline:
  1. Extract structured attributes (brand, model, RAM, storage, screen size, colour) with regex plus an LLM using structured output.
  2. Apply hard-constraint equality on the variant attributes, which gives exact-variant guarantees.
  3. Score the survivors by fuzzy or embedding similarity, using RapidFuzz or a sentence embedding.
  4. Optionally use an LLM "select"-style prompt (ComEM/MatchGPT) to break ties among the remaining 1-3 candidates.

  None of the general-purpose libraries offers exact-variant matching. Off-the-shelf PLM matchers like Ditto are known to struggle on near-duplicate variants that differ only in numbers. That last point is from general knowledge of the WDC Products benchmark design, not verified in this session.

### Gaps
- Per-dataset zero-shot F1 numbers for GPT-4/4o/open LLMs on WDC Products were not extracted, because the abstract has no numbers. See the HTML version of arXiv 2310.11244 for the tables.
- Latency and cost comparisons between local Jellyfish and hosted LLMs at the scale of about 45 candidate pairs per request were not found.
- Whether Unicorn's pretrained checkpoint is still downloadable was not verified.

## 2. Product-matching-specific repos and Kaggle solutions (combining text and image)

### Takeaway
The Shopee Price Match Guarantee (Kaggle 2021, 2,426 teams) top solutions all follow one pattern. They train separate image (NFNet/EfficientNet/ViT/CLIP) and text (BERT/XLM/tf-idf/CLIP) embedding models with ArcFace-type metric-learning losses on product-group labels. They then run kNN search per modality, union the matches or feed pairwise similarity features to a second-stage GBDT (LightGBM/CatBoost/XGBoost), and finally apply graph or neighbourhood post-processing. This approach needs a large labelled set of product groups. It also finds "same or similar product" rather than an exact variant. Image similarity is weak for variant discrimination: a 128GB and a 256GB phone look identical, though image signals can help with sneaker colour.

### Cited Findings
- **Shopee 1st place:** NFNet (image) plus BERT and XLM (text), trained with ArcFace. Image and text matches were unioned. DBA (database-side augmentation) was applied to the embeddings. "Iterative Neighborhood Blending" repeatedly applies DBA, blending only neighbours above a cosine threshold. Samples that would otherwise match only themselves get a looser threshold. — [Speaker Deck summary by 2nd-place author](https://speakerdeck.com/lyakaap/shopee-2nd-place-solutiontoshang-wei-jie-fa-matome); [Kaggle 1st place write-up "From Embeddings to Matches"](https://www.kaggle.com/competitions/shopee-product-matching/writeups/upstage-making-ai-beneficial-1st-place-solution-fr). The Kaggle page did not render for fetch, so details come from the Speaker Deck summary.
- **Shopee 2nd place:** NFNet image model and tf-idf, Indonesian BERT, multilingual BERT and paraphrase-XLM text models, trained with CurricularFace, plus a joint NFNet+BERT multimodal model. A LightGBM second stage takes image/title similarity, edit distance, neighbour-similarity statistics, image size and title length, which reduces tuning to a single threshold. They add alpha query expansion and PageRank graph features, and ensemble a GAT on edges with four similarity features. Score was 0.792 public LB. The authors noted the per-modality thresholds were hard to tune because CV and LB disagreed. — [Speaker Deck](https://speakerdeck.com/lyakaap/shopee-2nd-place-solutiontoshang-wei-jie-fa-matome)
- **3rd to 5th place:** 3rd used EfficientNet, ViT (DINO) and CLIP for images and BERT, tf-idf and CLIP for text, with a CatBoost second stage and agglomerative clustering. 4th used a weighted average of similarities with sparse random projection on tf-idf. 5th used a ViT/Swin image ensemble and DistilBERT/tf-idf text models, with DBA, XGBoost and agglomerative clustering. — [Speaker Deck](https://speakerdeck.com/lyakaap/shopee-2nd-place-solutiontoshang-wei-jie-fa-matome)
- **Silver-medal open repo:** EfficientNet B3/B5, NFNet-F0/F1 and RoBERTa, each with an ArcMargin head. Scores were 0.744 public and 0.733 private. 20 stars, MIT, last push 2021-06. — [mfalfafa/shopee-price-match-guarantee](https://github.com/mfalfafa/shopee-price-match-guarantee)
- **Shopee National Data Science Challenge 2020 winner** (a different competition) treated numbers in titles as meaningful variant markers during text cleaning. — [Medium](https://budiryan.medium.com/first-place-solution-for-shopee-national-data-science-challenge-2020-b12211242f22)
- **Mannheim "Supervised Contrastive Learning for Product Matching"** code is for WDC product offers. It is supervised, 38 stars, and has not been pushed since 2022. — [contrastive-product-matching](https://github.com/wbsg-uni-mannheim/contrastive-product-matching)
- Other generic product-matching repos found: [Product-Matching-Milvus](https://github.com/sreelalhari/Product-Matching-Milvus) (vector search with Milvus), [jingxuanyang/Shopee-Product-Matching](https://github.com/jingxuanyang/Shopee-Product-Matching), [nogibjj/Shopee-Product-Price-Match-Guarantee](https://github.com/nogibjj/Shopee-Product-Price-Match-Guarantee). Their exact methods were not inspected.

### Inferences
- The transferable lessons from Shopee for our app are:
  - Give numbers and model tokens in titles special treatment.
  - Use a second-stage scorer over several similarity features instead of hand-tuning one threshold per modality.
  - Fall back to a looser threshold when nothing matches.
- Training ArcFace models is not feasible without a labelled corpus of Indian cross-store product groups. The approach also targets recall over a catalog, not exact-variant precision over about 15 candidates.
- Images could be useful as a tie-breaker for apparel and sneaker colour, for example with CLIP zero-shot text-image similarity. This idea is not verified by any sourced project.

### Gaps
- The full text of the 1st-place write-up (exact thresholds, INB parameters) could not be fetched from Kaggle.
- No Mercari-specific product-matching solution was researched. Mercari's Kaggle competition was about price prediction, not matching.

## 3. Indian cross-store price-comparison projects on GitHub and how they match

### Takeaway
No open-source Indian project was found that matches better than the Kifayati rules already known. Most repos scrape Amazon and Flipkart and take the first or top search result. A few use TF-IDF or fuzzy thresholds. The most rigorous approach found is a commercial, non-OSS method (Actowiz): match on model number and product identifiers. Kifayati's strict rules (brand present, every query number present, tier modifiers equal, at least 35% token overlap) remain the best open reference for exact-variant matching.

### Cited Findings
- **ravadakaran/Kifayati** covers Amazon, Flipkart, Croma, Myntra and JioMart. It has 0 stars, was last pushed 2026-09-19, and has no license. — [Kifayati](https://github.com/ravadakaran/Kifayati) (matching rules as previously noted by the coordinator)
- **Hiteshgottapu/mobile-price-compare** is a Streamlit app using SerpApi Google Shopping. It clusters results and caches in SQLite. It has 1 star, was last pushed 2025-09-22, and has no license. — [mobile-price-compare](https://github.com/Hiteshgottapu/mobile-price-compare)
- **paritoshtripathi935/Product-Matching** has 19 stars, was last pushed 2024-07, and has no license. Its README claims NLP, image recognition and collaborative filtering, with Amazon and Flipkart scraper topics, but describes no concrete matching pipeline, thresholds or blocking. — [Product-Matching](https://github.com/paritoshtripathi935/Product-Matching)
- **sushantPatrikar/Amazon-Flipkart-Price-Comparison-Engine** has 71 stars, MIT license, and was last pushed 2022-12. It compares prices for a user-entered product (search-based, with no matching logic described). — [repo](https://github.com/sushantPatrikar/Amazon-Flipkart-Price-Comparison-Engine)
- **mayureshagashe2105/Smart-Pick** "compares products from Amazon & Flipkart by NLP". It has 0 stars and was last pushed 2022-02. — [repo](https://github.com/mayureshagashe2105/Smart-Pick-NLP-Product-Comaprison-Amazon-vs-Flipkart)
- **2k4sm/priceChamp** is a BeautifulSoup scraper for Amazon and Flipkart prices with no matching logic. — [priceChamp](https://github.com/2k4sm/priceChamp)
- **ElectroFind** is a final-year B.E. AI project, with no public repo linked. It lowercases and cleans titles, extracts brand, storage, colour and model number with regex/NLP rules, builds TF-IDF vectors (5,000 features, 1-2 grams), and requires cosine similarity of at least 0.85 to match. It claims 94% accuracy on an undescribed test set. Live search covers Amazon, Flipkart, Best Buy and eBay via Oxylabs, plus Google Shopping via Serper.dev. — [ElectroFind docs](https://electro-find.vercel.app/docs)
- **A dev.to tutorial** uses RapidFuzz fuzzy matching to align Amazon and Flipkart phone listings. — [dev.to](https://dev.to/ayeshashaikh1325/building-a-real-time-product-price-comparison-website-using-python-43ip)
- **DesiDupe** is an MCP server that searches Flipkart, Amazon.in, Meesho, Myntra, Ajio and Tata Cliq for similar or cheaper "dupes". It does similarity search, not exact matching, and its method was not confirmed. — [LobeHub listing](https://lobehub.com/ko/mcp/b24repo-desidupe)
- **Commercial reference:** Actowiz matches identical electronics SKUs across Amazon, Flipkart and Croma "by model number and product identifiers" and advertises LLM-based attribute extraction for matching. — [Actowiz](https://www.actowizsolutions.com/electronics-price-parity-same-sku.php)
- **PriceTrackr** is an academic paper (ICSIAIML-25) describing a live Indian comparison site covering Amazon, Flipkart, Snapdeal, Meesho, Croma and Myntra. — [Atlantis Press](https://www.atlantis-press.com/proceedings/icsiaiml-25/126021191)

### Inferences
- The Indian OSS ecosystem is student-grade: low stars, no licenses, and mostly first-result or TF-IDF/fuzzy thresholds. A TF-IDF cosine of 0.85 (ElectroFind) or a token_sort_ratio of 85 (mobile-price-compare) will produce false positives across storage and colour variants, because those differ by one token.
- The most robust design, consistent with the commercial Actowiz approach and Kifayati's rules, is attribute-level equality on model number and variant fields, with fuzzy similarity only as a ranking signal.

### Gaps
- Kifayati's and mobile-price-compare's code was not re-inspected in this session; the coordinator had already summarized them.
- The PriceTrackr paper's matching method was not retrieved.
- No OSS project specifically handling Myntra apparel colour/size variant matching was found.

## 4. Attribute extraction and colour normalization OSS

### Takeaway
For product-title attribute extraction, the practical OSS route in 2026 is regex for well-formed specs (GB, inches, model codes) plus LLM structured extraction with Instructor or Outlines, using Pydantic schemas. Pretrained English product-title NER checkpoints on Hugging Face are scarce. Most attribute-value-extraction (AVE) work is research code on MAVE/AE-110k. For colour, use webcolors for CSS names, Stitch Fix's colornamer for nearest-XKCD-name mapping via CIEDE2000 on RGB, and a hand-built synonym map for marketing colour names (for example "Midnight", "Titanium Black").

### Cited Findings
- **Instructor** (567-labs/instructor): structured LLM outputs via Pydantic. 14,106 stars, MIT, v1.17.0 released 2026-09-09, pushed 2026-11-10. — [instructor](https://github.com/567-labs/instructor), [PyPI](https://pypi.org/project/instructor/)
- **Outlines** (dottxt-ai/outlines): constrained-generation structured outputs, which also work with local models. 16,007 stars, Apache-2.0, v1.3.3 released 2026-08-06. — [outlines](https://github.com/dottxt-ai/outlines), [PyPI](https://pypi.org/project/outlines/)
- **RapidFuzz**: string similarity metrics (token_sort_ratio, etc.). 4,198 stars, MIT, v3.14.6 released 2026-08-30. — [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz), [PyPI](https://pypi.org/project/rapidfuzz/)
- **MAVE dataset** (Google): 3M attribute-value annotations across 1,257 categories on 2.2M Amazon product profiles. Archived repo, 160 stars. — [MAVE](https://github.com/google-research-datasets/MAVE)
- **clw8998/Product-Name-NER-model** on Hugging Face: a Traditional Chinese token-classification model extracting brand, name, colour, capacity and similar fields from product names. Apache-2.0, macro F1 0.78, capacity F1 about 0.92. It is not usable as-is for English Indian titles. — [HF model](https://huggingface.co/clw8998/Product-Name-NER-model)
- **Research AVE approaches:** OpenTag/SUOT-style BIO tagging with an attribute-as-query formulation (ACL 2019) — [ACL P19-1514](https://aclanthology.org/P19-1514/). Generative joint extraction — [arXiv 2208.07130](https://arxiv.org/pdf/2208.07130). Product information extraction with ChatGPT — [arXiv 2306.14921](https://arxiv.org/pdf/2306.14921). Open LLMs (LLaMA-3, Mistral, OLMo) for attribute-value identification — [arXiv 2409.12695](https://arxiv.org/html/2409.12695v1)
- **webcolors**: HTML/CSS colour name and hex/RGB conversions. 176 stars, BSD-3, v25.10.0 released 2025-10-31, pushed 2026-10. — [webcolors](https://github.com/ubernostrum/webcolors), [PyPI](https://pypi.org/project/webcolors/)
- **colornamer** (Stitch Fix): maps RGB to the nearest of about 950 XKCD colour names using CIEDE2000, with a hierarchy of colour families. — [colornamer](https://github.com/stitchfix/colornamer), [PyPI](https://pypi.org/project/colornamer/0.2.3/)
- **pyciede2000**: CIEDE2000 colour difference, MIT, with no name list. — [AUR listing](https://aur.archlinux.org/packages/python-pyciede2000). Other options: xkcdcolors (R package, XKCD survey names) — [r-packages.io](https://r-packages.io/packages/xkcdcolors); colory (nearest colour name from hex) — [github](https://www.github.com/apoorvaeternity/colory)

### Inferences
- Colour libraries work on RGB/hex values, while our inputs are text colour names from listings ("Phantom Black", "Midnight Blue", "Triple White"). The practical approach is a synonym dictionary that maps each name to a base colour family, building on the XKCD/CSS names and colornamer's family hierarchy. The LLM extraction step can assist by emitting both `colour_raw` and `colour_family`. Exact match should use the brand's marketing colour name where both sides have it, and fall back to the family otherwise.
- With Instructor or Outlines, one LLM call per candidate batch can extract `{brand, model, ram_gb, storage_gb, screen_in, colour}` for all ~45 titles. Deterministic equality checks then enforce the exact-variant rules. This avoids training any matcher.

### Gaps
- No maintained English product-title NER checkpoint on Hugging Face was confirmed. A targeted search for MAVE-trained checkpoints might find one.
- colornamer's latest release date and star count were not pulled; the GitHub API call was not made for that repo.
