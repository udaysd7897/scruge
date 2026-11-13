# Image and vision-language methods for exact-product matching in fashion (tees, polos, jerseys, sneakers)

Research date: 2026-11-12. No paid APIs were called. Sources are dated where possible. Several primary pages (Kaggle discussions, OpenAI pricing) blocked automated fetching; those gaps are flagged below.

## 1. Embeddings (CLIP/OpenCLIP, SigLIP, FashionCLIP, Marqo-FashionCLIP/FashionSigLIP, DINOv2): accuracy on exact-item retrieval, thresholds, zero-shot vs fine-tuned

### Takeaway
Zero-shot general embeddings are fine for building a shortlist but not for deciding whether two offers are the same product. The best head-to-head evidence comes from Zalando (2024), on cross-retailer exact-offer matching over about 2M fashion offers. Raw CLIP ViT-bigG-14 scored AUCPR 27.2 and R@1 62.9. Raw DINOv2 ViT-G-14 scored AUCPR 2.4 and R@1 22.7. A small contrastively trained projection over CLIP image+text embeddings ("fashionID") reached AUCPR 66.1 and R@1 84.2. So a light fine-tune on in-domain match pairs roughly doubles to triples precision-recall. Fashion-specific CLIP models (Marqo-FashionSigLIP) beat general CLIP/SigLIP on fashion text-to-image and category retrieval. However, they have not been benchmarked publicly on exact-SKU, image-to-image matching.

### Cited Findings
- **Zalando "End-to-end multi-modal product matching in fashion e-commerce"** (Tóth et al., arXiv 2403.11593, March 2024, submitted to KDD). The task is to find the same product offered by different merchants. The proprietary dataset has about 2M offers from 5 domains, about 4.5 images per offer, and over 99% of index offers have no match. Results are AUCPR / R@1 / R@3, given as in-domain | out-of-domain — [arXiv HTML](https://arxiv.org/html/2403.11593)
  - DINOv2 ViT-G-14 raw (1536-d): 2.4/22.7/32.4 | 13.0/40.6/53.7
  - CLIP ViT-bigG-14 raw (1664-d): 27.2/62.9/77.9 | 37.9/70.1/85.5
  - offerDNA (in-house ConvNeXt-Tiny, 28M params, 128-d): 56.9/74.0/88.5 | 63.9/78.8/90.9
  - CLIP image only + learned projection (192-d): 57.2/77.8/93.0 | 58.4/79.2/91.8
  - CLIP text only + projection: 0.6/11.1/23.5 | 2.6/17.9/36.0. Text alone is nearly useless for this fashion task because titles are generic.
  - fashionID (CLIP image + CLIP text + numeric features + projection, 192-d): **66.1/84.2/95.2** | 63.3/82.1/92.6. Numeric features added about 1 point of AUCPR.
  - The projection has only 0.6M parameters and trains in about 10 minutes for 50 epochs on one A100 (AdamW, lr 1e-3, τ=0.06, batch 16k).
  - Hard cases: trousers had the weakest PR curves because many look nearly identical and differ only in cut. The paper notes that packshot and model photos differ across domains but gives no failure rates for them.
  - Thresholds: the production distance threshold was tuned from PR curves. A figure uses similarity 0.80 for per-category points. Candidates are blocked by brand using fuzzy string matching.
  - Human-in-the-loop: the model alone had precision 0.162 (v1) and 0.285 (v2). With 3 expert judgments per row and a majority vote, output precision reached 0.896 (v1) and 0.937 (v2), with TPR around 0.79–0.83. Crowdsourced workers with 5 votes per row did not reach the precision target. Showing colour, price and sizes to validators did not help.
- **Marqo-FashionCLIP / Marqo-FashionSigLIP** (released August 2024; ViT-B-16 class). Benchmarks are averaged across 7 fashion datasets: DeepFashion In-shop, DeepFashion Multimodal, Atlas, Fashion200k, KAGL, Polyvore and iMaterialist. These are text-to-image and category tasks, not exact-item image-to-image retrieval — [GitHub marqo-FashionCLIP](https://github.com/marqo-ai/marqo-FashionCLIP); [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)
  - Text-to-image (6-dataset average) Recall@1: FashionSigLIP 0.121, Marqo-FashionCLIP 0.094, ViT-B-16-SigLIP-webli 0.111, ViT-B-16-laion2b 0.088, FashionCLIP2.0 (patrickjohncyh) 0.077, OpenFashionCLIP 0.060. MRR: 0.239 / 0.200 / 0.214 / 0.180 / 0.165 / 0.135.
  - Category-to-product P@1: FashionSigLIP 0.758, Marqo-FashionCLIP 0.734, SigLIP-webli 0.690, FashionCLIP2.0 0.681, laion CLIP 0.673.
  - Note that general SigLIP (webli) beats FashionCLIP2.0 and laion CLIP. Off-the-shelf SigLIP is therefore a strong baseline, and the fashion fine-tune adds a modest gain on top.
  - Marqo says a second-generation model improves MRR and recall by a further 78% over the original FashionSigLIP. This is a vendor claim that I did not verify — [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)
- **DeepFashion In-shop (same item, shop images, fine-tuned metric learning).** R@1 is about 94–97 for 2023–2024 methods. MGA (arXiv 2302.08902, 2023) reports R@1 94.3. Aggregators list 96.5–96.7 for CLIP-backbone methods, which I did not verify against the primary papers — [hyper.ai summary of 2302.08902](https://beta.hyper.ai/en/papers/2302.08902); [wizwand leaderboard](https://www.wizwand.com/sota/deep-metric-learning-on-inshop); [hyper.ai In-shop leaderboard](https://hyper.ai/en/sota/tasks/metric-learning/benchmark/metric-learning-on-in-shop-1)
- **DeepFashion Consumer-to-Shop is much harder:** GRNet (ICCV 2019) reports top-1 of only about 26% — [arXiv 1908.11754](https://arxiv.org/pdf/1908.11754.pdf)
- **E-commerce dedup with MAE image + BERT text embeddings and a learned "decider"** reached macro-F1 0.90, versus 0.83 for a third-party solution, on catalogs of more than 200M items. Embeddings are reduced to 128-d and searched in Milvus. This was published at IEEE BigData 2025, industrial track — [arXiv 2509.15858](https://arxiv.org/abs/2509.15858)
- **Colour sensitivity:** a multi-object instance retrieval study found that widely used embedding models often lack object-specific attributes, largely colour. One reported colour retrieval comparison was 63.5% vs 40.8% for DINOv2. This is relevant to same-tee/different-colour confusions — [search result summary of arXiv 2503.09867](https://arxiv.org/pdf/2503.09867.pdf). I saw this only through a search snippet.

### Inferences
- For exact-SKU decisions, raw cosine similarity from any off-the-shelf model is a weak classifier. Zalando's raw CLIP had AUCPR 27, meaning precision collapses at useful recall. Use the embeddings to rank and shortlist (raw CLIP R@3 was about 78–85%, and fine-tuned about 93–95%), then verify with something else.
- DINOv2 is clearly worse than CLIP for cross-retailer fashion offer matching in the only head-to-head test found (Zalando). Do not choose DINOv2 for this task without your own evaluation.
- Ranking for a zero-shot shortlist: Marqo-FashionSigLIP ≥ SigLIP (webli) > Marqo-FashionCLIP > laion CLIP ≈ FashionCLIP2.0. This order is inferred from fashion text-to-image and category benchmarks, not from exact-match tests.
- The gap between zero-shot and fine-tuned is large (AUCPR 27 → 57–66) and cheap to close. A 0.6M-parameter projection head trained on a few thousand to a few hundred thousand labelled match pairs is enough. A small system could bootstrap these labels from identifier (EAN/style-code) matches.
- Since no universal cosine threshold is published, calibrate one per model on about 200–500 labelled pairs from your own marketplaces.

### Gaps
- I found no public per-dataset numbers for Marqo-FashionSigLIP, SigLIP2 or FashionCLIP on DeepFashion In-shop image-to-image R@1, Street2Shop or DeepFashion2 retrieval. Marqo points to a LEADERBOARD.md that I did not retrieve.
- I found no published absolute cosine thresholds for "same product" with CLIP/SigLIP on fashion. Zalando tuned its threshold from PR curves and did not publish it.
- I found no SigLIP2-specific fashion results.

## 2. Perceptual hashing and local-feature matching for reused studio shots

### Takeaway
pHash/dHash detects the same image file reused across retailers (re-encoded or resized) and is nearly free to run. It is not a product-identity test, though. Centred products on white backgrounds produce false matches even at very small Hamming distances, and crops or mirroring break it. Treat a pHash hit as strong evidence only when combined with an attribute or brand agreement, and treat a pHash miss as no evidence.

### Cited Findings
- **pHash false positives on product shots:** a 2026 dataset-curation paper (MONET) found pHash false positives at Hamming distance d=1 among unrelated images, including centred products on white backgrounds (a pill icon, a shoe, an SD card). It concluded that pHash conflates global colour distribution and coarse layout with perceptual identity — [arXiv 2605.21272 (via search snippet; the full PDF was too large to fetch)](https://arxiv.org/pdf/2605.21272)
- **Practitioner thresholds** (developer guides, lower reliability): a distance of 0–5 out of 64 bits usually means the same image, around 10 is a common starting threshold to tune, and many production systems use ≤5. Crops and mirroring break both pHash and dHash. pHash is more robust to tonal and filter edits — [MojoAuth pHash vs dHash](https://mojoauth.com/security-guides/phash-vs-dhash); [DEV Community](https://dev.to/kencho/duplicate-image-detection-how-to-find-and-remove-duplicate-photos-5dod)

### Inferences
- Indian marketplaces often reuse brand-supplied studio packshots with different crops, padding or watermarks, so plain global pHash will miss many reuses. Hashing a centre crop or trimmed bounding box, or using local features (ORB/SIFT with RANSAC inlier counts, or LoFTR), is more robust to crop and padding. I found no numeric benchmarks for these on product images in this pass.
- Plain tees in the same colour on white backgrounds are exactly the "centred product on white" case where pHash false-matches. Never let pHash alone auto-accept a plain-tee match. Require a brand match plus a text/attribute match.
- Same-colourway reuse of one studio image is a strong positive signal. A colourway difference on the same template photo will show up as a pHash change only if the colour shift is large. Add a colour check.

### Gaps
- I found no published false-match rates for ORB/SIFT/LoFTR inlier thresholds on cross-retailer apparel images, and no study measuring how often Indian marketplaces reuse identical brand studio images.

## 3. Logo/print/graphic detection and colour histograms as tie-breakers

### Takeaway
I found no fashion-specific benchmark that quantifies how much logo or print detection, or colour histograms, help with exact matching. The evidence is indirect. Embeddings under-encode colour, and Zalando's validators found that colour metadata did not help humans. The approach therefore rests on reasoning, not on benchmarks: masked dominant-colour comparison (garment pixels only) as a cheap veto, plus OCR or VLM reading of graphics, numbers and logos.

### Cited Findings
- Embedding models often lack object-specific colour features — [arXiv 2503.09867 (search snippet)](https://arxiv.org/pdf/2503.09867.pdf)
- Zalando hid colour, price and sizes from human validators because those fields did not help, and colour variants were not discussed as a failure mode — [arXiv 2403.11593 HTML](https://arxiv.org/html/2403.11593)
- A practitioner blog says base CLIP embeddings make "two SKUs of the same shirt look identical". This is an unsupported claim of low reliability — [width.ai](https://www.width.ai/post/image-embedding-models)

### Inferences
- **Colour veto:** segment the garment (rembg or SAM, or a centre crop on packshots) and compare dominant colours in Lab space. A large ΔE suggests a different colourway even when embedding cosine is high. Model photos shift colour less predictably than flat-lays, so use the colour check as a veto with a loose threshold, never as an accept signal.
- **Prints and jerseys:** player names and numbers, sponsor logos and graphic text are best compared with OCR or a VLM prompt asking for the text visible on the garment. These are discrete tokens, unlike embeddings.

### Gaps
- I found no measured gains from logo or print detectors or colour histograms on exact fashion matching.

## 4. Multimodal LLM / VLM pairwise judging

### Takeaway
Published evidence for frontier VLMs judging product pairs from images is still thin. Most LLM entity-matching benchmarks (WDC Products, Abt-Buy) are text-only. On those, GPT-4-class models reach about 86–94 F1 zero-shot or fine-tuned. The best 2026 industrial paper uses a VLM only as an escalation stage behind a cheap model, at a 98% precision bar. Each VLM call is cheap at small-model rates, so for 10–50 candidates the main design question is how many pairs to escalate, not whether you can afford it.

### Cited Findings
- **"Retrieve, Match, Escalate"** (Wang et al., arXiv 2608.25037, 25 August 2026) — [arXiv](https://arxiv.org/abs/2608.25037)
  - The cascade is: retrieval, then a lightweight text cross-encoder distilled from millions of dual-VLM-consensus labels and calibrated to 98% precision for auto-accept, then an agentic multimodal VLM that inspects images and runs web searches for the ambiguous remainder.
  - Coverage rose from 68% (cheap stage alone) to 77% after escalation.
  - A self-hosted open-weight agent matched the frontier VLM's precision at recall 88% vs 92%, at about one-seventh of the per-pair cost.
  - Per-pair cost across stages spans nearly five orders of magnitude.
  - The abstract does not name the vendors.
- **Text-only LLM entity matching:**
  - Peeters & Bizer report that zero-shot GPT-4 beats fine-tuned PLMs on 3 of 5 datasets — [arXiv 2310.11244](https://arxiv.org/abs/2310.11244v1)
  - AnyMatch reports that GPT-4 (MatchGPT) has the best average F1 of 86.36 — [arXiv 2409.04073](https://arxiv.org/pdf/2409.04073)
  - Aggregator figures: fine-tuned gpt-4o-mini scores 94.09 F1 and gpt-4o-2024-08-06 scores 92.20 on Abt-Buy, and fine-tuned gpt-4o scores 87.10 on WDC Products 80% corner cases. These are unverified against the primary paper — [hyper.ai Abt-Buy](https://hyper.ai/en/sota/tasks/entity-resolution/benchmark/entity-resolution-on-abt-buy); [hyper.ai WDC](https://hyper.ai/en/sota/tasks/entity-resolution/benchmark/entity-resolution-on-wdc-products-80-cc-seen)
- **VLM perception limits** (not product-specific): on BlindTest, four commercial VLMs averaged 58.07% on simple visual tasks, with the best at 77.84%, and they struggled with precise spatial detail. This is a warning that small print or logo differences may be missed or hallucinated — [Vision language models are blind (2407.06581)](https://www.alphaxiv.org/abs/2407.06581)
- **Gemini API pricing** (paid tier, page fetched 2026-11-12, per 1M tokens) — [Google AI Studio pricing](https://aistudio.google.com/docs/pricing)
  - Gemini 3.1 Flash-Lite: $0.25 input (text or image) / $1.50 output.
  - Gemini 3.5 Flash-Lite: $0.30 / $2.50.
  - Gemini 3.8 Flash: $0.75 / $3.75 through 31 December 2026, rising to $1.50 / $7.50 from 1 January 2027.
  - Gemini 3.1 Pro Preview: $2 / $12.
  - The Batch API gives a 50% discount.
  - The page does not state tokens per input image.
- The OpenAI pricing page returned 403 to automated fetching, so I have no OpenAI prices. Anthropic prices were not fetched.

### Inferences
- **Rough cost per pair:** assume 2 product images at roughly 250–600 tokens each, plus about 300 text tokens. Tokens per image is my assumption, not sourced. That gives about 1–1.5k input tokens and about 100 output tokens. On Gemini 3.1 Flash-Lite this is about $0.0004–0.0005 per pair, or about $0.02 for 50 pairs. On a Pro-tier model it is about $0.004 per pair. Escalating only the top 3–5 candidates after cheap filtering keeps cost per source listing under about $0.01 even on mid-tier models.
- **Prompting:** send both images and both titles and attributes (brand, style code, colour name). Ask for a structured verdict over specific fields (brand, garment type, colour, graphic/logo text, collar/sleeve, sneaker colour-blocking), then an overall SAME/DIFFERENT/UNSURE. Treat UNSURE as no match. Require the model to quote visible text, such as logos or jersey numbers, to reduce hallucination.
- **Main risks:** the model may hallucinate agreement on plain tees ("both are white crew-neck tees, same product"), and it may miss small print differences. VLMs should be able to reject a match but should rarely be the sole reason to accept a plain-tee match.
- **Latency:** I found no sourced figure. Flash-class calls are typically seconds per call, so run candidate pairs in parallel or in batch.

### Gaps
- I found no peer-reviewed benchmark of GPT-4o/4.1, Claude, Gemini or Qwen-VL on image-pair fashion exact-product matching, with or without attributes. I also found no published hallucination rates for this task.
- OpenAI and Anthropic prices and image token counts were not retrieved.

## 5. Kaggle Shopee Price Match Guarantee (2021): how image and text were combined

### Takeaway
Top Shopee solutions trained ArcFace (ArcMargin) metric-learning heads on image backbones (EfficientNet, NFNet) and on multilingual BERT-family text models plus TF-IDF. They found neighbours by KNN on each modality, combined the modalities (union, voting or concatenation), then tuned similarity thresholds with a minimum-neighbour fallback. The best private scores were in the mid-0.7s of mean F1. Shopee groups are near-duplicate listings, a looser notion than exact fashion SKUs.

### Cited Findings
- The metric was sample-wise mean F1, and group sizes were capped at 50. The competition had 2,426 teams — [albumentations competition page](https://albumentations.ai/adoption/competitions/kaggle/shopee-product-matching/); [search summary of Kaggle page]
- A silver-medal solution scored 0.744 public / 0.733 private. It used EfficientNet-B3/B5 and NFNet-F0 with MLP + ArcMargin for images and RoBERTa + MLP + ArcMargin for text — [GitHub mfalfafa](https://github.com/mfalfafa/shopee-price-match-guarantee)
- An open solution reported test F1 of 0.8211 at baseline, 0.8285 after a "min2" threshold (guaranteeing at least one neighbour), and 0.8345 after INB (iterative neighbourhood blending; recall 0.866, precision 0.877). The tuned thresholds were 0.12 / 0.145 on its distance metric, and its best single text model was paraphrase-xlm-r-multilingual-v1. These numbers are on its own validation split, not the Kaggle LB — [GitHub jingxuanyang](https://github.com/jingxuanyang/Shopee-Product-Matching)
- An academic ensemble used NFNet, Swin and EfficientNet image embeddings with DistilBERT, ALBERT, mBERT and TF-IDF text embeddings, and 7 models voting — [XJTLU](https://scholar.xjtlu.edu.cn/en/publications/shopee-price-match-guarantee-algorithm-based-on-multimodal-learni/)
- One write-up says the most common top-10 approach was a BERT text model combined with an NFNet image model — [Medium 460J](https://medium.com/@tburford_27244/460j-final-project-175bcfce3bb6)

### Inferences
- Lessons for this system:
  - (a) Per-modality metric learning beats raw pretrained embeddings.
  - (b) Combining image OR text neighbours raises recall, but exact-SKU precision needs AND logic or a verifier.
  - (c) Thresholds are dataset-specific and must be tuned.
  - (d) "At least one match" fallbacks help F1 on Shopee, where every item has a group, but are harmful here, where many candidates have no true match.

### Gaps
- The 1st-place write-up ("From Embeddings to Matches", Kaggle discussion 238136) could not be fetched; only its title loaded. Its exact models, thresholds and private F1 are unverified.

## 6. Recommended cascade for one source vs 10–50 candidates per platform (low budget)

### Takeaway
Use a precision-first cascade: identifiers, then hard attribute filters, then image-hash fast-accept, then embedding shortlist, then colour and print vetoes, then VLM verification on the top few. This mirrors the published industrial pattern, where a cheap stage auto-accepts at high precision and a VLM or human handles the ambiguous rest. Here that is a 98% precision bar with 68%→77% coverage ([2608.25037](https://arxiv.org/abs/2608.25037)) and HITL lifting model precision from 0.29 to 0.94 ([Zalando 2403.11593](https://arxiv.org/html/2403.11593)).

### Cited Findings
- A cheap stage auto-accepts at a calibrated 98% precision, and a VLM agent handles the rest. The open-weight agent costs about one-seventh of a frontier VLM — [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- Fine-tuned multimodal embeddings put the true match in the top 3 for 93–95% of queries, versus 78–85% for raw CLIP. Raw DINOv2 is far worse — [arXiv 2403.11593](https://arxiv.org/html/2403.11593)
- pHash false-positives on white-background products even at d=1 — [arXiv 2605.21272](https://arxiv.org/pdf/2605.21272)

### Inferences (proposed cascade; thresholds are starting points to calibrate, not sourced constants unless cited)
1. **Identifier:** if both listings expose the same style code, EAN or brand article number, accept. Different brands means reject. Block candidates by brand, as Zalando did.
2. **Hard attribute filters (text):** reject on mismatched garment type (tee, polo or jersey; sneaker vs slide), gender, or an explicit, normalised colour name that disagrees.
3. **Image hash:** compute pHash on the trimmed or bounding-box crop of every image pair (source × candidate, all gallery images). A Hamming distance ≤4/64 plus same brand plus no colour conflict counts as a strong positive, a possible auto-accept for printed or graphic items. For plain or solid tees, send the pair to step 6 rather than auto-accepting, because of the white-background false-positive risk.
4. **Embedding shortlist:** use Marqo-FashionSigLIP or SigLIP (webli) image embeddings, taking the maximum cosine over image pairs. Keep the top 3–5 candidates above a calibrated floor. Fit the floor on about 300 labelled pairs; I found no published absolute value. Optionally fuse in title-embedding similarity. Later, train a Zalando-style projection head on accepted matches.
5. **Vetoes:** apply a masked dominant-colour ΔE check (different colourway), and an OCR or graphic-text mismatch check for jerseys and printed tees (number, name, sponsor, slogan).
6. **VLM verification:** send only the surviving 1–5 pairs to a Flash-Lite or Flash-class model with both images and attributes and a structured, field-by-field prompt. Accept only on SAME with no field conflicts. Estimated cost is about $0.0005–0.005 per pair, under about $0.01–0.03 per source listing per platform (my estimate from Gemini rates above).
7. **Abstain:** if the result is ambiguous (plain basics with no identifier and no exact image reuse), output "similar, not confirmed" rather than a match. This is the class where every published system needs humans or still errs: Zalando's near-identical trousers, and VLMs' weak fine-detail perception.
- **Model vs flat-lay photos:** compare across all gallery images and take the maximum similarity, since most listings include at least one packshot. Expect lower embedding scores for model-vs-flat-lay pairs, so lean on the VLM and the attributes.

### Gaps
- None of the cascade thresholds (pHash ≤4, embedding floors, ΔE) are validated on Indian-marketplace data. They need a small labelled set (about 300–500 pairs, balanced across exact, same-style-different-colour and look-alike plain basics).
