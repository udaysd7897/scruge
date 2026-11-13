# Visual matching for sneaker confirmation (same model and same colourway)

Scope: one Claude multimodal call compares one Amazon.in sneaker photo with up to 5 Flipkart or Myntra candidate photos. It fills an attribute table, then gives a verdict. Research done 2026-11-13. CDN behaviour was checked live with curl from this machine on the same date.

## Q1. Which visual attributes discriminate sneakers best? (a compact 5–8 item list)

### Takeaway
No published, sneaker-specific attribute taxonomy for matching turned up. Enthusiast and retailer guides that tell look-alike models apart (Samba, Gazelle, Spezial) rely on toe shape, panel and eyestay layout, tongue shape, sole thickness and upper material. Colourway matching needs colour per zone, not one overall colour. A 7-attribute list that mirrors the apparel set is proposed under Inferences.

### Cited Findings
- Near-identical adidas terrace models are told apart by toe shape (Samba: almond toe, extra-long tongue, thinnest sole, narrow; Gazelle: round slim toe, uptick tongue sides, medium sole; Handball Spezial: round wide toe, short straight tongue, most cushioned sole) — [Woman&Home comparison](https://www.womanandhome.com/fashion/samba-vs-gazelle-adidas-trainers/)
- The Samba eyestay has a small notch where the Gazelle's runs straight. The Samba is usually leather with a suede toe; the Gazelle and Spezial are suede. This shows that panel cut lines and material are key discriminators — [Woman&Home](https://www.womanandhome.com/fashion/samba-vs-gazelle-adidas-trainers/)
- A "colorway" is the specific combination of colours on one version of a sneaker — [Complex sneaker terminology guide](https://content-prod.adc-blue.infra.complex.com/sneakers/a/complexstaff3/the-complete-guide-to-sneaker-terminology)
- Nike style codes are a 6-digit model code plus a 3-digit colour code (for example 317982-103). The 3 digits after the hyphen identify the colourway. This is a secondary source (a resale tool) — [Underpriced.app Nike style code decoder](https://www.underpriced.app/tools/nike-style-code-lookup)
- Official colourway strings list several colours in zone order, for example Dunk High 317982-103 "Sail/Black/Varsity Royal" and Air Max 270 GS CI4428-100 "White/University Red-Fire Red-Green" — [GOAT 317982-103](https://www.goat.com/en-sa/sneakers/dunk-high-317982-103); [GOAT CI4428-100](https://www.goat.com/en-nl/sneakers/air-max-270-gs-seattle-home-ci4428-100)
- Prior project research found that two Nike V5 RNR colourways on Myntra (all-white/silver vs white with black Swoosh and silver overlays) were easy to separate by eye, because the logo colour differed even though the base colour was the same — [local notes: myntra_public_data.md](file:///Users/sid/scruge/research_notes/Myntra%20product%20matching%20methods/myntra_public_data.md)

### Inferences
- **Proposed attribute table (7 rows, the sneaker analogue of neck/sleeve/colour/logo/stripes/print).** Score each row per candidate as match / mismatch / not visible:
  1. **Silhouette and cut**: low, mid or high top; overall profile; toe shape (almond, round, chunky); tongue shape and length. This identifies the model family.
  2. **Panel layout**: overlay and stitch lines, eyestay shape (notched or straight), toe cap or mudguard, heel counter or heel tab shape, perforations. This separates look-alike models such as AF1 vs Court Vision or Samba vs Gazelle.
  3. **Brand mark type, position and colour**: Swoosh, three stripes, Puma Formstrip, NB "N", Asics stripes, plus any heel or tongue branding. Record the mark's colour separately, because it often decides between colourways.
  4. **Upper base colour and material**: the dominant upper colour, using off-white, sail, cream and pure white as separate values; leather, suede, mesh or knit.
  5. **Accent colour per zone**: toe cap, eyestay, heel tab, collar lining, tongue label. Use a mini-list such as "heel: red".
  6. **Midsole and outsole**: midsole shape (cupsole, chunky, visible air unit, foam stack height) and colour (white, sail, gum, black, icy). Note tread colour if it is visible.
  7. **Laces and eyelets**: lace colour, and eyelet count and type if visible. This is a weak discriminator, but useful when the other rows agree.
- Rows 1–3 decide model and rows 3–7 decide colourway. A verdict of "same" should need rows 1–2 to match and no row among 3–6 to be a clear mismatch.

### Gaps
- No academic dataset or paper giving the relative discriminative power of each sneaker part turned up. The ranking above is reasoned from enthusiast guides, not measured.
- Nike's own definitions of "Sail" vs "White" were not found. The pattern (Sail = off-white or cream) is inferred from listings only.

## Q2. Pitfalls: near-duplicate colourways, angles, lifestyle images, resolution, kids vs adult, collabs and retros

### Takeaway
The main failure risks are: (a) subtle colour or tone differences, which current multimodal LLMs are weakest at and tend to call "no difference"; (b) images with mismatched views or content (pair vs single, on-foot vs studio); (c) GS/kids vs adult versions that look the same from outside. Tiny images under 200 px are also unreliable.

### Cited Findings
- On VDiff-Bench (1,756 four-way image-pair difference questions), the best model scored 89.6% overall (Gemini 3.1 Pro). The hardest categories were low-level changes such as noise/resolution, texture, whole-image colour and illumination. Smaller models often chose "no difference" when a subtle change existed (51–81% of low-level questions for 7–8B models). One frontier model scored 82.0% on semantic changes but 40.7% on low-level ones — [VDiff-Bench, HF papers page](https://huggingface.co/papers/2609.06245)
- SPD-Faith Bench (3,000 image pairs; colour, object-removal and position differences) names two systematic MLLM failure modes, "perceptual blindness" and "perception-reasoning dissociation". The second means the stated reasoning does not match what the model perceives — [arXiv 2602.07833](https://arxiv.org/abs/2602.07833)
- OddGridBench reports that MLLMs including Gemini-2.5-Pro and GPT-5 fall far below human level at detecting visual discrepancies. This comes from search-result summaries only and was not verified against the paper — [Emergent Mind 2603.09326](https://www.emergentmind.com/papers/2603.09326)
- Claude docs: Claude "might hallucinate or make mistakes when interpreting low-quality, rotated, or very small images under 200 pixels." Heavy lossy compression and multiple compression passes introduce artifacts that hurt performance — [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- In an LLM e-commerce evaluation, models "tend to overestimate the similarity of two products by comparing their product titles, overlooking subtle differences in their images" — [arXiv 2510.20632](https://arxiv.org/pdf/2510.20632)
- Zalando's fashionID found trousers the hardest category because of low visual variability (near-identical offers differing only in small cut details). Showing colour to human validators did not improve their accuracy, and Zalando recommends close-up photos when high precision is needed — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- GS (grade school) shoes keep the same design DNA as adult versions, with only "subtle differences". Women's (WMNS) vs men's releases often cannot be told apart from the outside; the size label inside is the reliable check. These are low-quality, blog-level sources — [Outsole.nl](https://www.outsole.nl/blog/the-differences-between-mens-and-womens-sneakers/); [Freaky Shoes GS explainer](https://freakyshoes.com/blogs/news-1/what-does-gs-mean-in-shoes-find-out-here)
- The same colourway exists in adult and GS SKUs under different style codes, for example Air Max 270 GS CI4428-100 — [GOAT](https://www.goat.com/en-nl/sneakers/air-max-270-gs-seattle-home-ci4428-100)
- Prior project research found that Myntra often uses its own photo shoot (different model and background) while Amazon and Flipkart reuse brand imagery. Exact or near-duplicate hashing therefore fails across Myntra for apparel, though it may work for footwear and brand pack shots — [local notes](file:///Users/sid/scruge/research_notes/Myntra%20product%20matching%20methods/myntra_public_data.md)

### Inferences
- **Near-duplicate colourways** (white/black vs black/white, sail vs white, "triple white" vs white with an off-white sole, same upper with a gum vs white sole) are the highest-risk false positives. The prompt should name these specific traps. Inverted colour pairs are caught by row 4 (base colour) vs row 3 (logo colour) being swapped.
- Sail vs white is unreliable across studios because of white balance and background. Treat a "sail vs white" difference alone as **unclear**, not mismatch, unless another zone (sole, logo, lining) differs. Text such as the colour name or style code should then break the tie.
- **Kids, GS and adult versions, and WMNS vs men's**, are visually near-identical. Vision alone cannot separate them reliably, so use title or size-range text (GS, PS, TD, Kids, Junior, "Women's") as a hard pre-filter outside the LLM, or in the same call.
- **Collab, retro, "SE", "Premium" and "Next Nature" editions** often differ only in materials (suede vs leather, a tongue tag, a heel embroidery). Upper material (row 4) and branding details (row 3) catch some of these. When the title flags such an edition on only one side, prefer "unclear".
- **Angle mismatch**: if the reference is a lateral side view and a candidate is top-down, sole-only or on-foot, rows 2, 5 and 6 are often "not visible". The verdict rule should count "not visible" as missing evidence, never as a match.
- **Lifestyle or on-foot images, pair shots and mirrored medial views**: the medial (inner) side often has a different or smaller logo, as on many Nike models. A lateral vs medial comparison can therefore look like a logo mismatch. Tell the model to check which side each image shows.

### Gaps
- No quantitative study of MLLM accuracy on sneaker colourway pairs specifically was found. The figures above are from general image-difference benchmarks.
- No reliable source was found on visual GS-vs-adult proportion differences.

## Q3. Research on fashion/footwear visual retrieval and product matching: accuracy and failures

### Takeaway
Embedding-only matching (CLIP, SigLIP, DINOv2) is good at shortlisting but not at confirming exact SKUs or colourways. CLIP beats DINOv2 for product matching. Generic encoders lag fashion-tuned ones on fine-grained attributes, and production systems add text features plus a human or LLM verifier for precision.

### Cited Findings
- Zalando fashionID, about 2M offers. Raw image-only embeddings out-of-domain: CLIP ViT-bigG-14 reached AUCPR 37.9 and R@1 70.1, against DINOv2 ViT-G-14 at AUCPR 13.0 and R@1 40.6. With a trained linear projection, image-only CLIP reached about 57–58 AUCPR. The full multimodal model (image, text and numeric features) reached about 63–66 AUCPR and 82–84 R@1. The paper says "CLIP outperforms DINO by a large margin", and that a text-only model was beaten even by raw CLIP image embeddings — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- Zalando also routes candidates to human validation to reach production precision. It shows validators the top 3 neighbours and uses trained experts rather than crowd workers — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)
- LookBench (2026): generic CLIP and SigLIP2 backbones underperform on fashion retrieval, especially on street photos. Fashion-specific fine-tuning narrows the gap but leaves "substantial headroom" — [arXiv 2601.14706](https://arxiv.org/html/2601.14706v3)
- One practitioner blog reports zero-shot DINOv2-Base at Fine Recall@1 39.49, about 24 points behind a fashion-specific model. The author blames general features that capture shape and texture but not fine attributes. This is not peer-reviewed — [Beating FashionSigLIP (Substack)](https://hopitai.substack.com/p/beating-fashionsiglip)
- A vendor guide says two SKUs of the same garment look identical to base CLIP embeddings, and that SKU-level matching usually needs domain fine-tuning — [width.ai](https://www.width.ai/post/image-embedding-models)
- Sneaker classifiers are mostly brand or authenticity CNNs, for example brand classification at about 82% test accuracy on Nike/Adidas/Converse, and counterfeit detection over 95% in a Sensors 2024 paper. No colourway-matching benchmark was found — [GitHub sneaker CNN](https://github.com/SebastiaanJohn/sneaker_classifier); [Sensors 2024, PMC11124814](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11124814/)

### Inferences
- For a small Python service, an optional free pre-step is a CLIP (open_clip) cosine score to pick the top candidate images and to discard obviously different shoes. Do not use it as the final colourway decision, since embedding similarity between colourways of the same model will be high.
- The single Claude call is the precision layer, equivalent to Zalando's human validator. Zalando's validator tips (show top-3, use close-ups, train with feedback) map to: send a few candidates, use side-view high-resolution images, and use a strict rubric.

### Gaps
- No public numbers were found on Google Lens or Pinterest exact-SKU footwear accuracy, and the queries did not surface 2022–2026 engineering posts on this. DeepFashion and Street2Shop are apparel-centric and pre-2022, so they were not pursued.

## Q4. LLM-as-judge for image comparison: position bias, structured table first, shuffling, consistency, thresholds, "unclear"

### Takeaway
Multi-image models are order-sensitive: shuffling changes about 25–30% of predictions on position-agnostic tasks, and judges are most position-biased when candidates are close in quality, which is the near-duplicate colourway case. Mitigations: label images, put images before text, shuffle candidates, keep the candidate count small, require a per-attribute table that the verdict must follow, and map missing evidence to "unclear".

### Cited Findings
- Shuffling image order changed predictions in about 30% of examples for most open models and about 25% for GPT-4o on position-agnostic tasks. Open models show recency bias; GPT-4o shows a U-shape that is worst for middle images ("lost in the middle") — [arXiv 2503.13792 (CVPR 2025)](https://arxiv.org/html/2503.13792v1)
- The same paper advises testing with shuffled order and evaluating per-position accuracy. Its SoFA fix is model-internal, so an API user cannot apply it — [arXiv 2503.13792](https://arxiv.org/html/2503.13792v1)
- "Judging the Judges" (15 judges, more than 150k instances): position bias is not random, varies by judge and task, and is "strongly affected by the quality gap between solutions". Bias is worst when candidates are similar — [arXiv 2406.07791](https://arxiv.org/abs/2406.07791)
- The MLLM-as-a-Judge benchmark covers scoring, pair comparison and batch ranking, and flags position bias among the limitations of multimodal judges — [arXiv 2402.04788](https://arxiv.org/pdf/2402.04788.pdf)
- SPD-Faith: MLLM reasoning traces can be dissociated from what the model actually perceives. A written table is therefore not proof of perception, but it does make the verdict checkable — [arXiv 2602.07833](https://arxiv.org/abs/2602.07833)
- Anthropic recommends introducing each image with a text label ("Image 1:", "Image 2:") and placing images before the text instruction: "Claude works best when images come before text" — [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- LLMs over-weight product titles and miss image differences when judging matches — [arXiv 2510.20632](https://arxiv.org/pdf/2510.20632)

### Inferences
- **Prompt layout:** `"Reference (Amazon):"` [img], then `"Candidate A:"` [img] … `"Candidate E:"` [img]. Use letters for candidates so they do not collide with numbered attribute rows. Put the instructions and output schema after the images. Shuffle candidate order with a random seed and map letters back in code.
- **Evaluate each candidate on its own against the reference**, one table row per candidate × attribute, rather than "pick the best of 5". This reduces the ranking-style position bias and lets several candidates match (for example, the same shoe from two sellers).
- **Force structure:** use tool use or JSON output with, per candidate: `view` (lateral, medial, top, pair, on-foot, sole, other), then one entry per attribute with value `{ref: "...", cand: "...", status: match|mismatch|not_visible}`, then `verdict: same|different|unclear` and a one-line `deciding_evidence`.
- **Enforce consistency in Python, not only in the prompt.** Recompute the verdict from the table and override the model's verdict when they disagree, either by downgrading to "unclear" or by trusting the table. Suggested rule:
  - `different` if row 1 (silhouette) or row 2 (panels) mismatch, or any colour row (3–6) is a clear mismatch.
  - `same` only if rows 1–3 match **and** at least 2 of rows 4–6 match **and** there are no mismatches.
  - Otherwise `unclear`. This includes the case where 2 or more key rows are not visible, or the only difference is a sail/white or off-white tone.
- **Keep text out of the vision judgment, or put it last.** Since titles bias LLMs, either omit titles or add them after the table, as a separate tie-breaker field covering GS/kids/WMNS, style code and colour name.
- **Calibration:** with no published thresholds for this task, build about 50–100 labelled Amazon↔Flipkart/Myntra pairs, half of them hard negatives (same model, other colourway). Run each twice with different shuffles. Accept "same" automatically only if both runs agree; otherwise return "unclear". This doubles cost. A cheaper alternative is to run once and fall back to a re-run only when the result is close.
- Set temperature to 0 or low, and ask for the table before the verdict. Extended thinking is optional but likely unnecessary.

### Gaps
- No published thresholds, and no Claude-specific position-bias measurements, were found for multi-image product matching. The numbers above come from GPT-4o and open models.

## Q5. Which image to pick from a gallery, and how to request sizes from Amazon, Flipkart and Myntra CDNs

### Takeaway
Use the lateral (outer-side) profile of a single shoe, which is usually image 1 on Amazon and Flipkart for footwear. Request about 800–1100 px on the long edge: enough for logos and panels, under Claude's resize cap, and small in tokens. All three CDNs resize via the URL (verified live).

### Cited Findings
- Claude image tokens are about ⌈w/28⌉×⌈h/28⌉. Standard-tier models downscale to a 1,568 px long edge (max about 1,568 visual tokens). Claude 4.7+ uses a high-res tier at 2,576 px (about 4,784 tokens). A 1000×1000 image costs about 1,296 tokens. Images under 200 px are unreliable. With more than 20 images per request, a stricter per-image size limit applies (keep under 3,000 px) — [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- Amazon officially documents `_SLxxx_` as "pixels on the longest side" — [Amazon Creators API images](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/api-reference/resources/images). Third-party guides say `_AC_SL1500_` is the zoom size, and that removing the modifier returns the largest file; this is unofficial — [easyparser](https://easyparser.com/blog/amazon-product-image-extraction)
- **Live test, 2026-11-13** (a Puma tee image id, so footwear may differ in native size):
  - Amazon `…/I/519awlkUeCL._SL400_.jpg` → 333×400. `._SL1000_.jpg` → 833×1000 (fits the long edge). No modifier `…/519awlkUeCL.jpg` → 1000×1200, the original. `._AC_SX800_.jpg` → 551×1170, an odd result, so avoid `SX` and prefer `SL`.
  - Flipkart `rukminim2.flixcart.com/image/{W}/{H}/…?q=70`: 416 → 311×416, 600 → 448×600, 832 → 622×832, 1664 → 1243×1664 at q=90 (196 KB). The box is fit-within, keeping aspect ratio.
  - Myntra `assets.myntassets.com/w_800,q_85/v1/assets/images/…` → 800×1067. `h_1440,q_90,w_1080/v1/…` → 1080×1440. Prior notes confirm the transform works on newer paths if `/v1/` is inserted — [local notes](file:///Users/sid/scruge/research_notes/Myntra%20product%20matching%20methods/myntra_public_data.md)
- Myntra PDP JSON exposes `media.albums[0].images[]` with `src` templates `h_($height),q_($qualityPercentage),w_($width)`. JSON-LD uses `h_1440,q_100,w_1080` — [local notes](file:///Users/sid/scruge/research_notes/Myntra%20product%20matching%20methods/myntra_public_data.md)
- Zalando recommends close-up photos when high precision matters — [arXiv 2403.11593](https://arxiv.org/html/2403.11593v1)

### Inferences
- **Recommended requests:**
  - Amazon `._SL1000_.jpg`, or `_SL1500_` on high-res models.
  - Flipkart `/image/832/832/…?q=80`, or 1664 for high-res.
  - Myntra `w_1080,q_85/v1/…`. Myntra images are 3:4 portrait with padding, so the shoe occupies less of the frame.
  - About 800–1100 px gives about 1,000–1,500 tokens per image, so 6 images cost about 6–9k input tokens per call.
- **Gallery choice:** footwear galleries usually go lateral side → medial → top → sole → heel → pair or lifestyle. That ordering is commonly observed but no source confirms it. Take image 1, or let Claude pick the view: send the reference plus each candidate's first 1–2 images and have it report the `view` per image.
- **Cheap upgrade within one call:** send 2 images per candidate (lateral plus top or heel) with fewer candidates, for example the top 3 by CLIP or title score. That stays at 7 images and resolves "not visible" rows.
- Avoid images of 416 px or smaller (thumbnails), because logos and stitch lines become illegible. Avoid recompressing; pass the CDN JPEG straight through as base64 or as a URL source.

### Gaps
- The Flipkart and Myntra CDN parameters are undocumented publicly. Behaviour was verified empirically on one product each and may change.
- No source documents the standard gallery order for footwear on Amazon.in, Flipkart or Myntra. Check it on a sample of sneaker PDPs before relying on "image 1 = lateral".
