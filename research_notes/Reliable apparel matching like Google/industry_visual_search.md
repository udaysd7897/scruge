# Production visual search and exact-product retrieval for fashion: architectures and what makes them reliable

Notes compiled 2026-11-13. Each item gives the publication date of its source. **[Measured]** means the source reports numbers from an offline or online evaluation. **[Claim]** means a marketing or press statement with no numbers behind it. Some search summaries were not checked against the full paper text, and those are flagged.

## Q1. Pipeline stages, metrics and failure modes at large companies

### Takeaway
Every large system uses the same cascade: (category/intent prediction) → (detection/crop) → (embedding ANN retrieval inside a category/partition) → (re-ranking with metadata/attributes/business signals) → (dedup). None of the public visual-search systems (Pinterest, Alibaba, Bing, eBay, Flipkart, Amazon StyleSnap) publishes a calibrated "exact vs similar" decision. They rank by similarity and report recall@K or human-graded relevance. Only offer/catalog *matching* systems (Zalando 2024, Amazon catalog-dup 2022) make a binary same-product decision, and they do it with a tuned distance threshold plus human validation.

### Cited Findings

**Alibaba Pailitao, "Visual Search at Alibaba" (KDD 2018; arXiv 2102.04674)**
- Stages: inventory selection plus a dedup module that removes "identical or highly similar items" → category prediction (GoogLeNet, 14 categories) fused with a search-based branch (top-30 neighbours from a 200M-image reference set) → joint weakly supervised detection and feature learning from user-click triplets → binary-code inverted index (coarse) with fine re-ranking on metadata and local features → GBDT+LR quality re-ranking of the top 60 on sales, conversion and user features — [arXiv/ar5iv 2102.04674](https://ar5iv.labs.arxiv.org/html/2102.04674)
- [Measured] Category Acc@1: model-only 88.86%, search-only 85.51%, fusion 91.01% — [ar5iv](https://ar5iv.labs.arxiv.org/html/2102.04674)
- [Measured] *Identical-item* recall, averaged over categories: R@1 46.5%, R@4 56.4%, R@20 62.9%. Generic ResNet101 features give R@1 0.128, versus 0.415 for the learned features. Click-triplet training adds +17 points identical R@1 over category-trained features — [ar5iv](https://ar5iv.labs.arxiv.org/html/2102.04674)
- [Measured] Weak categories by identical R@1: underdress 0.17, accessories 0.224. Weakly supervised localisation reaches IOU@0.7 70.2%, versus 95.1% for a supervised SSD. Re-ranking gave +7.85% CVR — [ar5iv](https://ar5iv.labs.arxiv.org/html/2102.04674)
- Hard negatives: non-clicked images are used as negatives *only if far enough* (margin γ) from both the query and the clicked item, so near-identical items are not pushed apart. The paper reports no precision figures, only recall and CVR — [ar5iv](https://ar5iv.labs.arxiv.org/html/2102.04674)
- A later Alibaba paper reports category prediction Acc@1 of 82.3%, more than 9 points over the online model (different setup; not comparable to the KDD numbers) — [arXiv 2102.04667](https://arxiv.org/pdf/2102.04667)

**Pinterest Shop The Look (KDD 2020; arXiv 2006.10866)**
- Stages: Faster R-CNN/FPN detector (ResNeXt101) produces box and category → crop embedding (multi-task Unified Embedding, binarised) → LSH-token inverted index → re-rank by embedding distance in a forward index — [ar5iv 2006.10866](https://ar5iv.labs.arxiv.org/html/2006.10866)
- Hard constraints live in *infrastructure*: separate per-category indexes, and predicted gender OR "unisex". Visual attributes (colour, pattern, fabric, length, dress style) are *auxiliary training tasks*, not filters. The authors say the filters "reduced the burden on the embedding" — [ar5iv](https://ar5iv.labs.arxiv.org/html/2006.10866)
- [Measured, relative] Category restriction: "Bad" top-5 results −17.1%. Gender restriction: "Extremely Similar" +12.7%, but A/B CTR −0.49%. Embedding V1.4: "Extremely Similar" +54.7%, CTR +5.99%. Colour attribute task: +3.2% fashion P@1 — [ar5iv](https://ar5iv.labs.arxiv.org/html/2006.10866)
- Human rubric: "Extremely Similar" (nearly identical), "Similar" (minor differences *such as colour or shape*), and Bad. A colourway is therefore graded "Similar", not exact — [ar5iv](https://ar5iv.labs.arxiv.org/html/2006.10866)
- [Measured] Label quality (consistency/accuracy): MTurk 47%/32.5%; in-house raters with an expert and edge-case guide 95%/89.5%. Dataset work had the biggest impact, ahead of model and infrastructure changes — [ar5iv](https://ar5iv.labs.arxiv.org/html/2006.10866)
- Unified embedding (KDD 2019): a multi-task softmax-proxy embedding trained on Flashlight, Lens and STL data. The STL set had about 340K images, 189 classes and 50K instance labels, where "instance" covers exact matches *or very visually similar* items on design/colour/material. Embeddings are binarised. Human judgement was added because engagement alone surfaces items that are not related to the query — [The Morning Paper, 2019-10-11](https://blog.acolyer.org/2019/10/11/learning-a-unified-embedding-for-visual-search-at-pinterest/)

**Microsoft Bing Visual Search, "Web-Scale Responsive Visual Search at Bing" (KDD 2018; arXiv 1802.04914)**
- Stages: query understanding (DNN, category, colour, *duplicate-detection* features, plus a shopping-intent trigger) → object detection (Faster R-CNN/SSD) only when intent fires; fashion and home were the first segments → L0 visual-word inverted index (billions to millions) → L1 single DNN feature with PCA+PQ (to thousands) → L2 LambdaMART over full features → dedup (MD5, local features) — [ar5iv 1802.04914](https://ar5iv.labs.arxiv.org/html/1802.04914)
- [Measured] NDCG@5: ResNet-50+PQ 70.81, full system 74.20. Latency p50 is 1083 ms for uploaded images, which contradicts the "<200 ms" claim in the abstract (that figure is for in-index images) — [ar5iv](https://ar5iv.labs.arxiv.org/html/1802.04914)
- No product-identity decision rule is published — [ar5iv](https://ar5iv.labs.arxiv.org/html/1802.04914)

**eBay, "Visual Search at eBay" (KDD 2017; arXiv 1706.03154)** *(from search summaries; full text not verified)*
- One ResNet-50 with split heads predicts category and a binary hash → search the predicted category partitions → aspect-based re-ranking using predicted aspects such as brand and colour — [arXiv 1706.03154](https://arxiv.org/pdf/1706.03154)
- eBay blog: when the top category is confident, skip other partitions; when it is uncertain, include competing ones (soft fallback on the hard filter) — [eBay Tech blog](https://www.ebayinc.com/stories/blogs/tech/tips-for-visual-search-at-scale/)

**Flipkart VisNet (arXiv 1703.02344, Mar 2017)**
- Triplet deep-ranking CNN for visual recommendations and search. Deployed over a 50M-product catalogue at 2K QPS and evaluated on Exact Street2Shop. Index freshness is named as a challenge — [ar5iv 1703.02344](https://ar5iv.labs.arxiv.org/html/1703.02344)
- Follow-up: "Visually Similar Products Retrieval for Shopsy" (Flipkart, 2022) — [ar5iv 2210.04560](https://ar5iv.labs.arxiv.org/html/2210.04560) (not read in detail)

**Myntra**
- No Myntra engineering post on exact-match visual search was found. Its "View Similar" carousel is reportedly powered by the vendor ViSenze, with "35% YoY image-search adoption" [Claim, vendor case study] — [ViSenze](https://www.visenze.com/featured-customers/myntra). Myntra research covers ShopLook / "Buy Me That Look" (2020) — [arXiv 2008.11638](https://arxiv.org/abs/2008.11638)

**Amazon**
- StyleSnap (announced at re:MARS, June 2019): CV/deep learning (residual nets) detects apparel and classifies it into categories. Recommendations also weigh brand, price range and reviews. Launched on dresses, tops and bottoms [Claim; no metrics] — [About Amazon](https://www.aboutamazon.com/shopping/stylesnap-will-change-the-way-you-shop-forever); [MIT Tech Review, 2019-06-07](https://www.technologyreview.com/2019/06/07/135047/amazon-ai-machine-learning-stylesnap-fashion-retail/)
- Amazon Shop the Look for fashion and home: detection plus embedding to bridge in-the-wild and catalogue domains (PDF too large to fetch; details unverified) — [Amazon Science PDF](https://cdn.amazon.science/2a/43/43c7dd6b4bffbfe72de627456a76/amazon-shop-the-look-a-visual-search-system-for-fashion-and-home.pdf)
- Same-product detection, MAPS (WACV 2022; blog 2022-01-10): metric learning on image+title, where the title guides spatial and channel attention to crop the relevant region. Positives share a product descriptor; **negatives come from the same subcategory (hard negatives)**, which gave a "significant" gain. [Measured] PR-AUC +5.2% over a multimodal baseline and up to +17% over image-only, on 3 unnamed categories — [Amazon Science blog](https://amazon.science/blog/using-computer-vision-to-weed-out-product-catalogue-errors); [WACV paper](https://openaccess.thecvf.com/content/WACV2022/papers/Das_MAPS_Multimodal_Attention_for_Product_Similarity_WACV_2022_paper.pdf)

**Zalando, "End-to-end multi-modal product matching in fashion e-commerce" (arXiv 2403.11593, 2024-03-18)**: the closest analogue to this task
- Blocking: fuzzy brand-name similarity restricts NN search to brands above a threshold → cosine kNN → a distance threshold tuned on PR curves (a 0.80 similarity appears per category in a figure; the production value is not stated) → human validation — [arXiv html](https://arxiv.org/html/2403.11593v1)
- Model "fashionID": frozen CLIP ViT-bigG image embeddings, averaged over an offer's images, concatenated with CLIP text and 3 numeric features, then a single linear projection to 192-d trained with supervised contrastive loss. Training takes about 10 minutes on one A100 — [arXiv html](https://arxiv.org/html/2403.11593v1)
- [Measured] In-domain AUCPR / R@1:
  - DINOv2 raw: 2.4 / 22.7
  - CLIP-bigG raw image: 27.2 / 62.9
  - CLIP-bigG image + linear: 57.2 / 77.8
  - Text-only + linear: 0.6 / 11.1
  - fashionID multimodal: 66.1 / 84.2 (R@3 95.2)

  Images carry most of the signal; text is weak on its own — [arXiv html](https://arxiv.org/html/2403.11593v1)
- Failure mode: trousers, which have low visual variability and differ only in small cut details. Colourways are not discussed — [arXiv html](https://arxiv.org/html/2403.11593v1)

### Inferences
- The recurring failure modes are colourways ("Similar", not exact, in Pinterest's rubric), low-variance garments (trousers at Zalando; plain tees and polos are likely analogous), category and gender confusion, and background or crop noise. All of them are addressed by structural constraints or hard negatives, not by a bigger general embedding.
- Off-the-shelf general embeddings are poor at *instance* identity. Raw DINOv2 AUCPR is 2.4 and raw CLIP 27 at Zalando; generic ResNet R@1 is 0.128 at Alibaba. Even a cheap linear head trained on same-product pairs doubles them.

### Gaps
- No public numbers from Myntra, Flipkart or Amazon on exact-match precision for apparel. eBay's numbers were not verified from the full text.
- None of the papers reports neckline (collar vs crew) as an explicit failure mode. That has to be inferred from the generic "minor shape differences" category.

## Q2. Combining image embeddings with text and attributes: hard constraints vs soft similarity

### Takeaway
Industry puts **coarse, reliably predicted facets as hard filters**: category partitions (Pinterest, eBay, Alibaba), gender+unisex (Pinterest), and brand blocking (Zalando). Fine visual attributes (colour, pattern, fabric) go in as **soft signals**: auxiliary embedding tasks, re-ranking features, or a human/VLM check. Hard filters get a fallback when the classifier is uncertain.

### Cited Findings
- Pinterest uses per-category indexes plus gender OR unisex as hard filters. Colour, pattern and fabric are auxiliary embedding tasks, and every attribute classifier exceeds 84% top-1 — [ar5iv 2006.10866](https://ar5iv.labs.arxiv.org/html/2006.10866)
- eBay includes competing category partitions when the top prediction is uncertain — [eBay Tech](https://www.ebayinc.com/stories/blogs/tech/tips-for-visual-search-at-scale/)
- Alibaba fuses model and kNN-vote category prediction to fix confusable categories (+2.15 points) — [ar5iv 2102.04674](https://ar5iv.labs.arxiv.org/html/2102.04674)
- Zalando uses fuzzy brand blocking and then late fusion of image, text and numeric features. Removing the numeric features costs about 1 AUCPR point; a different text encoder (MUSE) gives no gain — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- Amazon MAPS uses the title as *attention guidance* for image regions rather than as a separate score — [Amazon Science](https://amazon.science/blog/using-computer-vision-to-weed-out-product-catalogue-errors)
- Leipzig (GvDB 2024) found that intermediate fusion of RoBERTa and Swin beats unimodal and late-fusion baselines on WDC Shoes and Zalando data — [Uni Leipzig](https://dbs.uni-leipzig.de/research/publications/intermediate-fusion-for-multimodal-product-matching); [CEUR Vol-3710](https://ceur-ws.org/Vol-3710/paper14.pdf)

### Inferences
- For the target use, brand and category (tee/polo/jersey/sneaker) and gender are safe hard filters, with fallback to adjacent categories if the listing's category is ambiguous. Neckline, sleeve, colour and print are better checked as an explicit attribute checklist at the verification stage than as hard pre-filters, because marketplace metadata for them is noisy. Alibaba explicitly reports noisy and wrong inventory labels.

### Gaps
- No source quantifies how often hard attribute filters wrongly exclude true matches, beyond Pinterest's gender-filter A/B CTR of −0.49%.

## Q3. Thresholds and calibration for exact vs similar; human-in-the-loop; precision and recall

### Takeaway
Only Zalando publishes a full decision procedure: kNN, then a single distance threshold picked from PR curves, then expert humans viewing the top 3 candidates, reaching about 0.90–0.94 precision. Crowd workers could not hit 90% precision. Everyone else measures graded relevance or recall@K rather than calibrated match probability.

### Cited Findings
- Zalando HITL: validators see the query and its top 3 neighbours, with close-up images. Hard-to-interpret fields (colour, price, sizes) are hidden, there are 3 votes with majority rule, and **crowdworkers could not reach 90% precision even with 5 votes**, so experts were used — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- [Measured] Zalando input precision → HITL output precision: v1 0.162 → 0.896; v2 0.285 → 0.937. Validator TPR 0.794, FPR 0.018, LR+ 44. The paper argues for AUCPR over F1 because F1 ignores the high-precision region. "Near-perfect precision in production" is a claim in the abstract with no exact figure — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- Pinterest uses graded human labels (Extremely Similar / Similar / Bad) on the top 5. In-house raters reached 95% consistency versus 47% on MTurk — [ar5iv 2006.10866](https://ar5iv.labs.arxiv.org/html/2006.10866)
- Amazon MAPS reports PR-AUC with no operating threshold published — [Amazon Science](https://amazon.science/blog/using-computer-vision-to-weed-out-product-catalogue-errors)
- Alibaba reports identical recall only, with no precision — [ar5iv 2102.04674](https://ar5iv.labs.arxiv.org/html/2102.04674)

### Inferences
- Even with a trained model, input precision of the raw kNN output at Zalando was only 16–29%. The verifier stage, human there and VLM for a small system, does most of the precision work. A single global cosine threshold will not separate "same product" from "same style, other colour".
- Calibrate per category with a small labelled set of pairs and report AUCPR. Use a three-way output (exact / similar / no-match) instead of a binary one, mirroring Pinterest's rubric.

### Gaps
- No published production thresholds for any company. No public measurement of VLM verifiers replacing human validators for fashion offer matching was found.

## Q4. What a small system can realistically replicate

### Takeaway
For one source item against about 20–80 candidates per store, the expensive retrieval infrastructure (ANN, PQ, sharding) is unnecessary. What carries over is: hard brand+category(+gender) blocking; a fashion-tuned CLIP/SigLIP embedding to shortlist (multi-image average); and a verifier, which can be a VLM with an attribute checklist, replacing Zalando's expert humans. That verifier must be shown close-ups and must emit exact / similar / different.

### Cited Findings
- Marqo-FashionSigLIP (2024 model card) [Measured by vendor]: text-to-image average over 6 datasets R@1 0.121 / MRR 0.239, versus FashionCLIP2.0 0.077 / 0.165. It claims up to 57% MRR and recall improvement over FashionCLIP. These are *text→image* and category retrieval benchmarks, not instance matching — [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)
- A third-party LookBench image-to-image benchmark reports FashionSigLIP Fine R@1 of about 62.8 (blog, unverified) — [Substack](https://hopitai.substack.com/p/beating-fashionsiglip). A successor "marqo-fashionSigLIP-2" claims +78% [vendor claim] — [Superlinked](https://superlinked.com/models/marqo-marqo-fashionsiglip.md)
- Zalando: frozen CLIP plus one linear layer trained in about 10 minutes on one GPU lifted AUCPR from 27 to 57. Averaging embeddings across an offer's images is part of the method — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- LLMs show strong zero-shot product matching, comparable to fine-tuned PLMs, on *text* entity matching (Peeters & Bizer; Mannheim dissertation 2025) — [Peeters dissertation](https://madoc.bib.uni-mannheim.de/69425/1/Dissertation_RalphPeeters.pdf)
- VLM caution: general web-trained VLMs "struggle to understand… real-world e-commerce product images" (Amazon VIT-Pro, NAACL 2025 industry) — [ACL Anthology](https://preview.aclanthology.org/moar-dois/2025.naacl-industry.57.pdf). GPT-4V is "more prone to producing hallucinations" (VALOR-EVAL 2024) — [arXiv 2404.13874](https://arxiv.org/pdf/2404.13874)
- Hard negatives from the same subcategory are what teach fine distinctions (Amazon MAPS); near-identical items should not be used as negatives (Alibaba γ margin) — [Amazon Science](https://amazon.science/blog/using-computer-vision-to-weed-out-product-catalogue-errors); [ar5iv 2102.04674](https://ar5iv.labs.arxiv.org/html/2102.04674)

### Inferences
- Suggested small-system design, which is a synthesis and not a measured result:
  1. Normalise brand (fuzzy) and category, plus gender/unisex, as hard filters, with fallback when the category is ambiguous.
  2. Embed all images per listing with a local fashion SigLIP/CLIP, use max/mean pairwise similarity, and shortlist the top 3–5. As at Zalando, the shortlist has high recall but low precision.
  3. Run a VLM verifier per candidate, or listwise over the top 3, with structured outputs: neck type (crew/polo collar/V/henley), sleeve, primary colour(s), print/graphic/logo placement, team/player/number for jerseys, and colourway/style code for sneakers. Text title and model numbers serve as corroboration. Output exact / similar / different, and have the verifier abstain when it is unsure.
  4. Calibrate on a hand-labelled set of about 100–300 pairs per category and track AUCPR and precision at the chosen operating point. Route low-confidence cases to a human, which is Zalando's lesson that the verifier carries precision.
- Hiding noisy metadata from the verifier, as Zalando hid colour, price and size from validators, and showing close-ups are directly transferable to VLM prompts.

### Gaps
- No published benchmark measures VLM pairwise verification on fashion same-product matching, so its accuracy for collar vs crew, colourway or print must be measured locally.
- No instance-level (same-SKU) benchmark result was found for Marqo-FashionSigLIP versus plain SigLIP/CLIP on Indian marketplace imagery.
