# Attribute-aware verification for "is this the same clothing item?" (images + text)

Research date: 2026-11-13. Coverage: about 20 search and fetch calls. No paid API calls. Some primary PDFs could not be read in full (marked under Gaps).

## Q1. Zero-shot garment attribute extraction (category, neckline/collar, sleeve, fit, pattern, colour, gender): which models, and how accurate?

### Takeaway
Fashion-tuned embedding models (Marqo-FashionSigLIP, FashionCLIP) are reliable for **coarse category**. They get roughly 0.75 P@1 on category-to-product retrieval, which is enough to veto a "watch vs T-shirt" or "slides vs polo" confusion. They are not reliable for fine attributes. Even recent VLMs are weak on **neckline**: zero-shot neckline F1 was 15% for GPT-4o-mini and 48% for Gemini 2.0 Flash on DeepFashion-MultiModal. VLMs reach about 71% F1 on fine-grained attributes once the attribute is visible, but they struggle to say "not applicable / not visible". Neckline and collar should therefore come from title text first, with image-derived values used only when confidence is high.

### Cited Findings
- **Marqo-FashionSigLIP** (Apache-2.0, fine-tuned from ViT-B-16-SigLIP webli with Generalised Contrastive Learning on text, categories, styles, colours, materials). Averaged benchmark results from the model card:
  - Category-to-product (avg of 5 datasets): P@1 **0.758**, vs FashionCLIP2.0 0.681, OpenFashionCLIP 0.653, base SigLIP 0.690.
  - Sub-category-to-product (avg of 4): P@1 **0.767**, vs 0.676 for FashionCLIP2.0.
  - Text-to-image Recall@1: **0.121**, vs 0.077 for FashionCLIP2.0.
  - The card says a "Marqo Fashion SigLIP 2" exists and claims a further 78% improvement in MRR and recall.
  - Source: [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)
- Marqo's evaluation covers seven public datasets: DeepFashion In-shop (52,591 images), DeepFashion Multimodal (42,537), Fashion200K (201,624), KAGL (44,434), Atlas (78,370), Polyvore (94,096) and iMaterialist (721,065). Relative gains over FashionCLIP2.0 are +57% text-to-image R@1, +11% category P@1 and +13% sub-category P@1. The blog gives aggregates only, with no per-dataset or per-attribute numbers. — [Marqo blog (dated Oct 26 2025 on page)](https://www.marqo.ai/blog/search-model-for-fashion)
- The model is usable as a zero-shot classifier: softmax over scaled image–text similarities via `AutoModel`/`AutoProcessor` with `trust_remote_code=True`, or via OpenCLIP `hf-hub:Marqo/marqo-fashionSigLIP`. — [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)
- **GPT-4o-mini vs Gemini 2.0 Flash, zero-shot, image only** (arXiv 2507.09950, Jul 2025). Setup: DeepFashion-MultiModal, 1,000-image stratified subset, 18 attributes. Collar was not evaluated; neckline is the closest attribute. F1 at temperature 0:
  - Neckline: **15.07% (GPT-4o-mini) vs 47.92% (Gemini)**
  - Sleeve length: 61.69% vs 58.52%
  - Upper colour: 57.80% vs 69.03%
  - Upper fabric: 39.67% vs 46.90%
  - Macro-F1: 43.28% vs 56.79%
  - Neckline and waist accessories were the weakest attributes.
  - Temperature 0 beat temperature 1 by about 6–7 F1 points.
  - Source: [arXiv 2507.09950](https://arxiv.org/html/2507.09950v1)
- **Nine VLMs in a three-tier evaluation** (arXiv 2601.15711, Jan 2026, WACV 2026 PRAW workshop). Models include GPT-5, Gemini 2.5 Pro, GPT-5 Mini, Gemini 2.5 Flash, GPT-5 Nano and Gemini 2.5 Flash-Lite. Setup: DeepFashion-MultiModal, 5,000 images, 18 attributes, with explicit NA labels.
  - Zero-shot VLMs reach **64.0% macro-F1**, about 3x a logistic-regression baseline on Fashion-CLIP embeddings.
  - Fine-grained classification when the attribute is determinable: **70.8% F1**.
  - Applicability detection (NA): only **34.1% NA-F1**. The authors call this the key bottleneck.
  - Efficient-tier models reach over 90% of flagship performance at lower cost.
  - Source: [arXiv 2601.15711](https://arxiv.org/abs/2601.15711)
- Expert-written, attribute-specific prompts beat naive prompts for CLIP zero-shot classification of fine fashion attributes, including sleeve style. — [NeurIPS 2022 workshop](https://neurips.cc/virtual/2022/57500)
- VL-CLIP (arXiv 2507.17080) reports a zero-shot neckline experiment with six neckline classes and text-prompt descriptions, and says it beats other CLIP variants. I could not retrieve the table because the PDF was too large to fetch. — [arXiv 2507.17080](https://arxiv.org/pdf/2507.17080)
- Claude vision limitations: the model may hallucinate on low-quality, rotated or very small images (under 200 px). Spatial reasoning and counting are approximate. — [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)

### Inferences
- **Category is the highest-value hard constraint.** It is also the easiest one. Title keywords combined with FashionSigLIP zero-shot (top-1 around 0.76 P@1 on retrieval, likely higher on coarse classes like watch/shoe/top) should eliminate watch-for-tee and slides-for-polo errors almost entirely.
- **Neckline/collar is the hardest attribute.**
  - Title text ("polo", "crew neck", "V-neck", "collared", "henley") is far more reliable than the image. The best measured zero-shot image result is about 48% F1, on a multi-class neckline taxonomy.
  - A binary question ("does this top have a fold-over collar with placket: yes/no/unclear") is probably much easier than six-way neckline classification. However, I found no published binary collar-vs-round-neck accuracy.
- Every attribute extractor should output `unknown`. The 34% NA-F1 result shows that VLMs over-commit when an attribute is not visible. The veto should fire only on confident, *contradictory* values, never on `unknown`.
- Use temperature 0 and a constrained enum schema (JSON with fixed label sets). Both choices are supported by the measured temperature effect.

### Gaps
- No source found with zero-shot accuracy for **collar specifically**, or for **fit** or **gender**, for any model.
- No per-attribute results found for SigLIP2, Qwen2-VL/Qwen2.5-VL, Claude, or GroundingDINO on fashion attributes.
- Per-attribute tables for 2601.15711 are not in the abstract. The full PDF was not read.
- Neckline numbers for VL-CLIP are unavailable (fetch failed).
- No published numbers found for iMaterialist-Fashion, Fashionpedia (which has a neckline/collar taxonomy) or FashionIQ attribute accuracy under zero-shot CLIP or VLM models.

## Q2. Using attributes as hard constraints before similarity

### Takeaway
I found no published e-commerce paper that measures "attribute veto then similarity" directly. The production cascade literature (arXiv 2608.25037) and entity-matching work (ComEM) both support the general pattern of cheap filtering first, then expensive verification. The attribute veto is the cheap filter that best addresses the reported errors.

### Cited Findings
- **Production cascade** (arXiv 2608.25037, Aug 25 2026, "Retrieve, Match, Escalate"): retrieval, then a text cross-encoder that auto-accepts high-confidence links, then an agentic VLM for the ambiguous tail.
  - The cross-encoder is distilled from **dual-VLM-consensus labels**, not human labels.
  - It is calibrated to a **98% precision** bar and validated with an operator-certified audit.
  - Escalation lifts coverage from **68% to 77%**.
  - Source: [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- ComEM ranks and filters candidates with a cheap model (Flan-T5-XL), keeps the **top 4**, then runs a stronger LLM on them with the "select" strategy.
  - It improves mean F1 over select-only (85.61 vs 81.60 with GPT-3.5; 86.42 vs 82.26 with GPT-4o-mini).
  - It roughly halves cost (GPT-4o-mini: 0.09 vs 0.17 cost units).
  - Source: [arXiv 2405.16884](https://arxiv.org/html/2405.16884v3)
- Older multimodal product-matching work found that adding images to WDC product offers raises recall and overall match quality. — [Wilke et al., Leipzig](https://dbs.uni-leipzig.de/research/publications/towards-multi-modal-entity-resolution-for-product-matching)

### Inferences
- Recommended veto logic. Hard-reject a candidate only when both sides have a confident, known value and they conflict on:
  - category, e.g. tee ≠ polo ≠ watch ≠ slides
  - collar presence
  - sleeve length (short vs long)
  - gender, when explicit in the title
  - primary colour family
- Treat brand mismatch as a hard reject when both titles name a brand.
- Pattern or graphic mismatch should be a strong penalty, not a veto. Small logos are often invisible at thumbnail resolution.
- Colour should be a soft constraint, or a family-level constraint (navy ≈ dark blue). Photography and white balance shift colour; colour F1 was only 57–69% in 2507.09950.

### Gaps
- No public benchmark found that quantifies the precision gain from attribute pre-filtering on apparel. This should be measured on the app's own labeled pairs.

## Q3. VLM pairwise/listwise "same product" verification: accuracy, failure modes, prompting, cost, latency

### Takeaway
Listwise selection (anchor plus K candidates plus a "none" option) beats independent pairwise yes/no. It adds about 16 F1 points on average in text entity matching, but it is position-sensitive. In production, a self-hosted VLM agent reached about 88% recall vs about 92% for a frontier VLM at similar precision, at about 1/7 the cost. Per-call cost in Nov 2026 is well under a cent for Haiku- or Flash-class models.

### Cited Findings
- **Match vs Compare vs Select** (Wang et al., COLING 2025, arXiv 2405.16884):
  - Selecting (anchor plus candidate list) gives an **average +16.02% F1** over pairwise matching.
  - Product datasets, GPT-4o-mini, F1 for Match / Compare / Select:
    - Abt-Buy: 81.37 / 89.24 / 82.37
    - Amazon-Google: 51.95 / 65.61 / 69.01
    - Walmart-Amazon: 74.92 / 83.85 / 76.66
  - The prompt includes a **"none of the above" ([0])** option, which the authors flag as a challenge.
  - Selecting is **"highly sensitive" to the position** of the true match: accuracy degrades the further down the list it sits.
  - Source: [arXiv 2405.16884](https://arxiv.org/html/2405.16884v3)
- Listwise LLM rerankers have known failure modes: missing items and inconsistent rankings caused by input-order sensitivity. — [Findings of EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.305.pdf)
- **Text-only LLM entity matching on WDC Products:**
  - Zero-shot GPT-4o and GPT-4o-mini scored about the same F1 (81.61 vs 81.60), with GPT-4o costing $0.89 vs $0.05 per run.
  - Fine-tuning GPT-4o reached 87.07 F1 but generalised poorly across datasets.
  - Source: [arXiv 2409.08185](https://arxiv.org/html/2409.08185v2)
  - I found no GPT-4o *with images* WDC result.
- **Production VLM agent** (arXiv 2608.25037): the open-weight agent inspects product images and runs web searches. It approaches frontier-VLM precision with **88% vs 92% recall** at **about 1/7 per-pair cost**, without fine-tuning. — [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- **Prompting multiple images (Claude docs):** multiple images in one request are analyzed jointly. Introduce each with a text label (`Image 1:`, `Image 2:` …) so the prompt can refer to them by name. — [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- **Image token cost (Claude):**
  - Formula: `ceil(w/28) × ceil(h/28)` visual tokens.
  - A 1000×1000 image is 1,296 tokens and a 200×200 image is 64 tokens.
  - Standard-tier max long edge is 1,568 px. Claude 4.7+ high-res tier goes to 2,576 px and up to 4,784 tokens, roughly 3x cost, so downsample when that fidelity is not needed.
  - Heavy JPEG compression can hurt detail.
  - Source: [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- **Claude pricing (Nov 2026, per MTok input / output):**
  - Haiku 5.5: **$0.10 / $0.50** for prompts up to 100k tokens
  - Haiku 4.5: $1 / $5
  - Sonnet 5.5: $2 / $10
  - Sonnet 5: $2 / $10 (introductory price made permanent)
  - Sonnet 4.6: $3 / $15
  - The Batch API is 50% off, and caching stacks with batch. Cache hits on Haiku 5.5 are $0.01/MTok.
  - Source: [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- **Gemini pricing (paid tier, per MTok input / output):**
  - Gemini 3.8 Flash: **$0.75 / $3.75** through Dec 31 2026, rising to $1.50 / $7.50 from Jan 1 2027
  - Gemini 3.5 Flash-Lite: $0.30 / $2.50
  - Gemini 3.1 Flash-Lite: $0.25 / $1.50
  - Gemini 2.5 Flash-Lite: $0.10 / $0.40
  - Gemini 2.5 Flash is deprecated and is routed to 3.5 Flash-Lite from Dec 1 2026.
  - Batch is 50% off. A free tier exists, but its data may be used to improve Google products.
  - Source: [Google AI Studio pricing](https://aistudio.google.com/docs/pricing)
- **Measured throughput and cost of zero-shot attribute extraction (2025 models), per 1,000 images:**
  - GPT-4o-mini: $3.20 and 33 min
  - Gemini 2.0 Flash: $2.80 and 25 min
  - That is about 1.5–2 s per image when run sequentially.
  - Source: [arXiv 2507.09950](https://arxiv.org/html/2507.09950v1)

### Inferences
- **Worked cost estimate** (my arithmetic, using the prices above). Assumed listwise call: anchor plus 5 candidates at 512×512 (about 361 tokens each, about 2.2k image tokens), plus about 800 text tokens, plus about 300 output tokens.
  - Claude Haiku 5.5: about **$0.0005 per call**
  - Claude Sonnet 5.5: about **$0.009**
  - Gemini 3.8 Flash: about **$0.0034**, if Gemini image tokens are similar. The Gemini page does not state image token counts for Flash.
  - Batch halves all of these.
- **Prompting best practice**, drawn from the sources above plus inference:
  1. Label images (`Anchor:`, `Candidate 1:` …) and include each title under its image.
  2. Ask for a per-attribute comparison table first, then the verdict: category, collar/neckline, sleeve, placket/buttons, logo position/size, graphic/print, colour, brand text.
  3. Require the verdict to be one of `exact | same_style_different_colour | similar | none`, with an explicit `unclear` per attribute.
  4. Shuffle or randomise candidate order. Optionally run two orders and require agreement, to counter position bias.
  5. Keep K small. ComEM used top-4.
  6. Use temperature 0.
- **Expected failure modes:**
  - Small logo or embroidery differences are lost at downsampled thumbnails; the docs warn about images under 200 px.
  - Colour shifts from lighting.
  - Lifestyle vs flat-lay photos hide the collar.
  - Hallucinated attributes when the attribute is not visible (the NA problem from Q1).
  - Position bias in listwise prompts.

### Gaps
- No public benchmark found reporting VLM image-pair "same product" precision specifically for **apparel**. Abt-Buy, Amazon-Google and WDC are mostly electronics, text-only.
- No measured per-call latency for Claude Haiku/Sonnet or Gemini Flash multi-image calls was found. The 2507.09950 throughput is the only data point.
- The full tables of 2608.25037 (exact precision of the agent stage, model names) were not accessible beyond the abstract.

## Q4. Calibration and abstention so "exact" is claimed only with strong evidence

### Takeaway
The strongest documented practice is to calibrate the auto-accept stage to a fixed precision target, 98% in 2608.25037. Everything below that threshold escalates or abstains. Agreement between two VLMs serves as a label and confidence source. LLM verbal confidence is poorly calibrated on its own, so thresholds should be set on a labeled audit set.

### Cited Findings
- **Calibrated cascade (2608.25037):**
  - The cross-encoder is calibrated to a **98% precision bar** and validated by an operator-certified audit.
  - Training labels come from **dual-VLM consensus**.
  - Ambiguous cases are escalated rather than auto-linked, which accepts lower coverage (68% → 77% only with escalation) in exchange for precision.
  - Source: [arXiv 2608.25037](https://arxiv.org/abs/2608.25037)
- Scores from listwise LLM rerankers are poorly comparable across queries, which motivates explicit calibration methods. — [Self-Calibrated Listwise Reranking, WWW 2025](https://dl.acm.org/doi/pdf/10.1145/3696410.3714658)
- "Learning from Emptiness" (arXiv 2604.10150) proposes content-agnostic probability calibration to de-bias listwise rerankers. Only the title and references were seen; the method is unverified. — [arXiv 2604.10150](https://arxiv.org/pdf/2604.10150)
- VLMs are weak at deciding when an attribute is undeterminable (34.1% NA-F1). Model abstention therefore cannot be trusted by itself. — [arXiv 2601.15711](https://arxiv.org/abs/2601.15711)

### Inferences
**Practical recipe for the app**, synthesised from the sources above:

1. **Per-candidate attribute JSON.** Built from title (regex/keyword parse first) plus image (FashionSigLIP zero-shot for category and colour family; VLM batch call for collar, sleeve and graphic, with `unknown` allowed). Cache it per product.
2. **Deterministic veto.** Applies only to confident known-vs-known conflicts on category, collar presence, sleeve length, gender and brand.
3. **Similarity rank** on the survivors using FashionSigLIP embeddings. Keep the top 3–5.
4. **Listwise VLM pick** (Haiku 5.5 or Gemini Flash-Lite for cost; Sonnet for the hard tail):
   - side-by-side labeled images
   - attribute-by-attribute table
   - a `none` option
   - randomised order
5. **Labels.** Claim "exact" only when all of the following hold:
   - the VLM says exact
   - all checked attributes match, with no `unclear` on collar or graphic
   - the brand matches
   - optionally, a second order or a second model agrees

   Otherwise label the result "similar". Set the thresholds so that measured precision on about 200–500 hand-labeled apparel pairs reaches 95–98% or higher.

### Gaps
- No apparel-specific calibration study found.
- No reported numbers on how often VLM "abstain/none" is correct in product selection; ComEM did not break out no-match cases.
