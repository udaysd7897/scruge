# Myntra's own engineering and research work related to product matching

Research date: 2026-11-12. All sources are dated where a date could be confirmed. Myntra's public research output is concentrated in 2017–2021. I found no Myntra-authored publication from 2022–2026 on deduplication, cross-platform matching, or LLM attribute extraction (see Gaps).

## Q1. What has the Myntra Engineering blog and tech site published on visual search, similar products, dedup, catalogue quality, attribute tagging and embeddings?

### Takeaway
Myntra's tech site (tech.myntra.com) lists its "DataScience" publications. The matching-relevant ones are: a style-dedup paper and a patent based on VGG-16 features plus unsupervised domain adaptation and KNN; similar-product work using collaborative filtering with a content (attribute-vector) baseline; a unified product embedding; colour-variant clustering; ShopLook (shop the look); and progressive attribute extraction. The Medium blog (medium.com/myntra-engineering) is mostly about search and query understanding. The one embeddings post could not be fetched (HTTP 403).

### Cited Findings
- tech.myntra.com's DataScience section lists these papers and patents (the page shows no dates): "Buy Me That Look", "Personalizing Similar Product Recommendations in Fashion E-commerce", "Discovering Similar Products in Fashion E-commerce", the patent "Domain Adaptation system and method for identification of similar images" (US20200285888A1), "System for Deduplication of Machine Generated Designs from Fashion Catalog", "Color Variants Identification…", "Attr2Style", "Progressive Fashion Attribute Extraction", "One Embedding to do them all", plus ranking and size-recommendation papers — [Myntra Engineering site](https://tech.myntra.com/)
- Medium posts listed on the same site include "Decoding the Fashion Signature using Embeddings", "Semantic Search — Innovation at scale!", "Category Prediction for Search Query Understanding" and "Decoding user search queries". The embeddings post returned HTTP 403 and was not read — [tech.myntra.com](https://tech.myntra.com/); [Medium post (unread)](https://medium.com/myntra-engineering/decoding-the-fashion-signature-using-embeddings-b21221806b7d)
- I found no Myntra Medium post on catalogue duplicate detection, seller-listing dedup or competitor matching. Searches returned only third-party write-ups — [secondary Medium summary of Myntra's pipeline](https://gk4444.medium.com/myntras-fashion-recommendation-pipeline-328ea98239c8)

### Inferences
- What Myntra has published on "same product" detection is image-centric: it uses pretrained CNN features and nearest-neighbour search, and adds domain alignment when the two image sources look different.

### Gaps
- The content of "Decoding the Fashion Signature using Embeddings" (403), including its date, model and metrics.
- No Myntra tech talk or slide deck on catalogue dedup or visual search was found within this research budget.

## Q2. Myntra papers: methods and reported metrics

### Takeaway
Six Myntra papers are relevant to matching:
1. **Style dedup (Banerjee et al., ~2019).** VGG-16 fc features (4096-d) go through an autoencoder with an adversarial domain classifier (gradient reversal), then KNN. This reduced KL divergence between catalogue and GAN images from 1.36 (VGG) to 0.075.
2. **Colour variants (Dutta et al., 2021).** A YOLOv2 crop feeds a ResNet34 (512-d embedding). The proposed self-supervised method, PBCNet, uses part-based slices with NT-Xent loss and Ward agglomerative clustering. It beat a supervised triplet baseline.
3. **Discovering Similar Products (SIGIR eCom 2017).** Similarity is computed per article type, using an NPMI co-browse graph (co-browse count ≥5, NPMI ≥0.15) or attribute vectors with cosine similarity.
4. **One Embedding (2019).** A weighted average of image-triplet and Word2Vec embeddings.
5. **ShopLook (MIPR 2021).** Detection followed by a triplet-network embedding.
6. **Progressive attribute extraction (KDD AI4Fashion 2019).**

### Cited Findings

**A. "System for Deduplication of Machine Generated Designs from Fashion Catalog"**
- Authors: Rajdeep H Banerjee, Anoop K R, Vikram Garg and Sumit Borar (Myntra Designs, Bangalore). The PDF is hosted on tech.myntra.com (uploaded 2021-03). The related patent's priority date is 2019-03-08 — [PDF](https://tech.myntra.com/wp-content/uploads/2021/03/System_for_Deduplication_of_Machine_Generated_Designs_from_Fashion_Catalog.pdf)
- Motivation is cross-platform: products "are catalogued differently in terms of background, model poses and lighting between the two different e-commerce platforms", so "fashion photographs exhibit different data distributions across different platforms" — [PDF](https://tech.myntra.com/wp-content/uploads/2021/03/System_for_Deduplication_of_Machine_Generated_Designs_from_Fashion_Catalog.pdf)
- Pipeline:
  - The article (t-shirt) is cropped with a bounding-box detector (Faster R-CNN is cited).
  - VGG-16 ImageNet features (4096-d) are extracted.
  - A fully connected autoencoder is trained with L1 reconstruction loss.
  - A binary cross-entropy domain classifier is attached via a gradient reversal layer (λ trades off the two losses), following Ganin & Lempitsky.
  - The encoded layer f_da is used as the feature, and dedup is done by KNN.
  — [PDF](https://tech.myntra.com/wp-content/uploads/2021/03/System_for_Deduplication_of_Machine_Generated_Designs_from_Fashion_Catalog.pdf)
- Data and evaluation:
  - About 44,000 Myntra catalogue t-shirt images. A DCGAN was trained with lr 0.0008, Adam β1=0.5, 256×256 output.
  - Domain adaptation was trained on 20,000 images per domain.
  - Evaluation: 100 GAN query images, each with 100 manually annotated similar catalogue images. Results are shown as precision-recall curves only, where f_da beats CORAL and raw VGG.
  - KL(source‖target): VGG 1.36, CORAL 0.455, f_da 0.075.
  - No numeric precision/recall and no match threshold are reported.
  — [PDF](https://tech.myntra.com/wp-content/uploads/2021/03/System_for_Deduplication_of_Machine_Generated_Designs_from_Fashion_Catalog.pdf)

**B. Patent US20200285888A1, "Domain adaptation system and method for identification of similar images"**
- Assignee: Myntra Designs. Inventors: Borar, Garg, Rajagopal and Banerjee.
- Dates: Indian priority 2019-03-08, US filing 2019-12-31, published 2020-09-10. The status is "abandoned", with a continuation (US 17/994,245) filed in 2022.
- The method is the same as paper A (VGG-16 features, autoencoder, adversarial domain classifier, KNN). It is framed as finding duplicate or similar images across platforms whose image distributions differ.
- It does not describe matching against competitor sites.
— [Google Patents](https://patents.google.com/patent/US20200285888A1/en)

**C. "Color Variants Identification in Fashion e-commerce via Contrastive Self-Supervised Representation Learning"**
- Authors: Ujjal Kr Dutta, Sandeep Repakula, Maulik Parmar and Abhinav Ravi.
- Dates and venue: arXiv 2104.08581, submitted 2021-04-17 (v2 2021-06-30). Accepted at the IJCAI-21 WSRL workshop. An extended version is arXiv 2112.02910 (~Dec 2021).
— [arXiv abs](https://arxiv.org/abs/2104.08581)
- Definition: colour variants are products that "match exactly in their design (or style), but only to differ in their color". The paper treats colour variants as "manifestations of color jitter based augmentations". A supervised triplet model first needed manual colour-variant annotations — [arXiv abs](https://arxiv.org/abs/2104.08581)
- Method (from 2112.02910):
  - YOLOv2 localises the primary product.
  - ResNet34 backbone at 224×224 input gives a 512-d avgpool embedding, trained 30 epochs.
  - Supervised baseline: triplet loss, margin 0.2.
  - PBCNet replaces random crops with 4 deterministic slices (left, right, top, bottom), sums their embeddings, and trains with NT-Xent loss (MoCo-style: queue 5k, temperature 0.05, momentum 0.999, SGD lr 0.001, batch 32). Augmentations are ColorJitter, grayscale and blur.
  - Groups are formed by agglomerative clustering with the Ward method, which was best among the clustering methods tried.
  — [ar5iv 2112.02910](https://ar5iv.labs.arxiv.org/html/2112.02910)
- Data and metrics:
  - Internal kurta images split into 6 sets by brand, gender and MRP.
  - Metrics: CGacc (internal "colour group accuracy"), ARI, FMS, and CScore (harmonic mean of ARI and FMS).
  - Data 6: triplet CScore 0.466 vs PBCNet 0.796. Data 4: triplet 0.700 vs PBCNet 0.756. Data 5: PBCNet 1.0.
  - The table's row labels are misaligned in the HTML rendering, so treat individual values as approximate.
  — [ar5iv 2112.02910](https://ar5iv.labs.arxiv.org/html/2112.02910)

**D. "Discovering Similar Products in Fashion E-commerce" (Amber Madvariya and Sumit Borar, Myntra; SIGIR 2017 eCom workshop, Tokyo, Aug 2017)** — [CEUR PDF](https://ceur-ws.org/Vol-2311/paper_19.pdf)
- All approaches split data at the article-type level (e.g. Men-Tshirts, Women-Dresses), "since products similar to a product p_i should be from the same article type" — [CEUR PDF](https://ceur-ws.org/Vol-2311/paper_19.pdf)
- Content baseline:
  - Each product has a binary vector of curated taxonomy attributes. These are general attributes (brand, colour, price band) plus article-type-specific attributes (ATSA; e.g. collar type, sleeve length, neck type).
  - Bigrams are pulled from descriptions using log-likelihood ratio, the vector is L2-normalised, and kNN uses cosine distance.
  - The stated weakness is that attribute sets are incomplete.
  — [CEUR PDF](https://ceur-ws.org/Vol-2311/paper_19.pdf)
- Item-item graph:
  - Edges come from session co-browse pairs weighted by NPMI.
  - Thresholds: co-browse count ≥5 and NPMI ≥0.15.
  - Only "coherent sessions" are used: at least 3 products of the same article type and no more than 2 article types.
  - Scale: about 200M training sessions and 12M users, giving similar products for about 1.3M products. The average click depth is about 90.
  — [CEUR PDF](https://ceur-ws.org/Vol-2311/paper_19.pdf)
- Every product carries a "style catalogued date (SCD)", the date the product entered the system — [CEUR PDF](https://ceur-ws.org/Vol-2311/paper_19.pdf)

**E. "One Embedding To Do Them All" (Singh, Arora, Singh and Borar; Myntra; arXiv 1906.12120, ~June 2019)**
- Separate embeddings are learned from clickstream (BPR-MF, Prod2Vec, DeepWalk), catalogue text (stacked denoising autoencoder), and images (a CNN with triplet loss in a fine-grained image-similarity architecture). Word2Vec embeddings are 100-d.
- Unified embedding = a weighted average, with weights grid-searched per task. For clicked-purchased similarity the weights were image 0.1 and Word2Vec 0.9.
- Data: 220k men's t-shirts.
- It evaluates attribute retrieval (brand, colour, price-band precision@k), not dedup.
— [ar5iv](https://ar5iv.labs.arxiv.org/html/1906.12120)

**F. "Buy Me That Look" / ShopLook (Ravi, Repakula, Dutta and Parmar; arXiv 2008.11638, Aug 2020; accepted at IEEE MIPR 2021)**
- Pipeline: human keypoint detection, then pose classification, then article localisation and object detection with active-learning feedback, then a "triplet network based image embedding model". Evaluated at Myntra — [arXiv](https://arxiv.org/abs/2008.11638)

**G. "Progressive Fashion Attribute Extraction" (Adhikari, Singh, Rajagopal and Rajan; Myntra Designs; arXiv 1907.00157; KDD 2019 AI for Fashion workshop)**
- Classifiers for one attribute are fine-tuned from weights learned for another attribute of the same garment type (networks branch from a base network). Reports accuracy gains over a multi-label baseline — [arXiv PDF](https://arxiv.org/pdf/1907.00157); [Myntra-hosted copy](https://tech.myntra.com/wp-content/uploads/2021/03/1907.00157.pdf)

**H. Related Myntra papers**
- "Attr2Style" (arXiv 2008.11662, IAAI 2021) infers style from attributes — [arXiv](https://arxiv.org/abs/2008.11662)
- "Personalizing Similar Product Recommendations in Fashion E-commerce" (Agarwal, Vempati and Borar; arXiv 1806.11371, 2018-06-29; KDD AI-for-Fashion workshop) combines collaborative-filtering similar products with personalisation. The abstract gives no numbers — [arXiv](https://arxiv.org/abs/1806.11371)

### Inferences
Methods a small Amazon.in-to-Myntra matcher could reuse:
- **Partition candidates hard by article type, gender, and (optionally) brand before any similarity step.** Myntra does this throughout: per-article-type similar products, and colour-variant datasets split by brand, gender and MRP.
- **Crop the garment before embedding.** Myntra uses a YOLOv2 or Faster R-CNN crop in both the dedup and colour-variant work. Amazon and Myntra shoots differ in background, pose and lighting, which is exactly the domain-shift problem the dedup paper names.
- **Expect off-the-shelf embeddings to confuse colour variants with the exact product.** Myntra's colour-variant work shows design embeddings deliberately ignore colour. An exact-SKU matcher should therefore add an explicit colour check (Myntra's "Prominent Colour" field, or a colour histogram) on top of a shape/design embedding.
- **Use image as a recall stage and text/attributes as a precision stage.** One Embedding's weights (image 0.1, text 0.9 for clicked-purchased similarity) hint that text signals dominate when the two can be combined.
- **No Myntra source gives a cosine threshold for "same product".** The only published thresholds are for co-browse graphs (≥5 co-browses, NPMI ≥0.15). Any threshold would need to be calibrated locally.

### Gaps
- Numeric precision/recall for the dedup work (only PR curves are given) and for ShopLook (abstract only fetched).
- The image-embedding dimension in One Embedding is not stated.
- I found no Myntra paper (2018–2026) on seller-listing dedup ("same style from multiple sellers") or on exact-product matching. A targeted search for Myntra catalogue near-duplicate papers returned only non-Myntra work, e.g. [An et al. 2017 binary-hashing near-duplicate detection](https://dl.acm.org/doi/abs/10.1145/3094243.3094260), whose affiliation is unconfirmed.
- I found no Myntra-authored 2023–2026 LLM/VLM attribute-extraction paper. Recent fashion-attribute arXiv papers (e.g. [2507.09950](https://arxiv.org/abs/2507.09950v2), [Fashion Florence 2605.09827](https://arxiv.org/html/2605.09827)) have unconfirmed affiliations.

## Q3. How Myntra models product identity (style id, colour, size SKUs, multi-seller merging)

### Takeaway
In Myntra's seller listing templates (as documented by integrators):
- **vendorArticleNumber (VAN)** is the seller-supplied unique product ID. It is mandatory, up to 40 characters.
- **styleGroupId** groups all sizes of one product with the same MRP and colour.
- An optional **Color Variant GroupId** links a style to the VAN of its colour sibling.
- **GTIN** is explicitly not mandatory.

A consumer-facing Myntra "style ID" (the number in PDP URLs) therefore corresponds to one colour plus MRP, with sizes as SKUs underneath. I found no public documentation of how Myntra merges the same brand article from multiple sellers.

### Cited Findings
- Fynd's Myntra attribute guidelines define these fields:
  - **vendorArticleNumber**: "ID that uniquely identifies the product - Vendor can use this id to track their order flow". Mandatory, 40 characters including spaces. Example: "INTR000142-Chambray".
  - **styleGroupId**: "A number to identify all sizes of a product with same MRP and colour". Mandatory.
  - **vendorArticleName**: a short name. Mandatory.
  - **brand** and **articleType**: chosen from dropdowns; articleType must match the sheet name. Mandatory.
  - **Prominent Colour**: a dropdown, mandatory. "Brand Colour (Remarks)" is also present.
  - **SKU Code** and **Vendor SKU Code**: optional.
  - **Color Variant GroupId**: optional, "Fill VAN of the style which is the color variant for this style".
  - The page states "All the columns that are highlighted yellow are mandatory (except GTIN)".
  — [Fynd docs: Myntra attribute guidelines](https://documentation.fynd.com/commerce/docs/openapi/listings-management/myntra/attribute-myntra) (undated page)
- Increff's Myntra checklist says a style must have status "P" and listing status "A" before inventory sync works. This implies style-level and listing-level records are separate — [Increff support](https://support.increff.com/support/solutions/articles/36000503826-myntra-listing-checklist) (undated; seen via search snippet)
- Vinculum says SKU pull is not available for Myntra's PPMP model because "Myntra does not have any API for this". Increff lists PPMP (dropship, "Myntra V3") as API-integrated — [Vinculum helpdesk](https://vinculumhelpdesk.freshdesk.com/support/solutions/articles/9000198514-myntra-ppmp); [Increff Myntra V4 Integration](https://increff.atlassian.net/wiki/spaces/IO/pages/368575333/Myntra+V4+Integration) (both seen via search snippets, undated)
- A third-party API (Anysite) fetches Myntra products "by product (style) ID or product URL", confirming that style ID is the public PDP key — [Anysite docs](https://docs.anysite.io/api-reference/myntra/myntraproducts.md) (third-party, not Myntra)
- Myntra's research also refers to a per-product "style catalogued date" and uses "style" as the product unit (e.g. "Style Dedup" running headers) — [CEUR PDF](https://ceur-ws.org/Vol-2311/paper_19.pdf); [Dedup PDF](https://tech.myntra.com/wp-content/uploads/2021/03/System_for_Deduplication_of_Machine_Generated_Designs_from_Fashion_Catalog.pdf)

### Inferences
- For matching an Amazon.in listing to "the exact Myntra product", the right target unit is a Myntra style ID: one colour and one MRP, with sizes collapsed. Amazon parent/child ASINs (colour × size) should be collapsed to colour level before matching.
- MRP is part of Myntra's style grouping, so the brand's MRP is a strong exact-match feature. Amazon shows "M.R.P." on Indian listings.
- The brand's own article code (VAN, e.g. "INTR000142-Chambray") is the most likely shared identifier across marketplaces. Brands often reuse their article or style codes, but this cross-platform reuse is not documented by any source found. GTIN is optional on Myntra, so barcode-based matching will often be unavailable.

### Gaps
- No official Myntra Partner Portal API documentation (e.g. field definitions for styleId vs skuId, or a seller "style group" merge policy) is public.
- How Myntra merges or de-duplicates the same brand article listed by multiple sellers (a "buy box" or single-style model vs separate styles) is undocumented in public sources found. Unicommerce, EasyEcom and Browntape docs were not reached within budget.
- Whether vendorArticleNumber is exposed in Myntra's public PDP data (page JSON) was not verified here.

## Q4. Flipkart/Myntra work on matching against competitors (price monitoring) or brand catalogue ingestion

### Takeaway
I found no public Myntra or Flipkart paper, blog post or talk on competitor product matching or price monitoring. The closest Myntra artefact is the style-dedup paper and patent. These explicitly motivate cross-platform image domain shift ("two different e-commerce platforms") but evaluate only catalogue-vs-GAN images. Public competitor-matching material for Indian marketplaces comes from vendors (Actowiz, Intelligence Node, Bright Data), not Flipkart or Myntra.

### Cited Findings
- The Myntra dedup paper's Figure 1 contrasts the same products shot differently on two e-commerce platforms, motivating domain adaptation. The experiments, however, use Myntra catalogue vs DCGAN images only — [Dedup PDF](https://tech.myntra.com/wp-content/uploads/2021/03/System_for_Deduplication_of_Machine_Generated_Designs_from_Fashion_Catalog.pdf)
- The patent frames the problem as duplicate or similar images across platforms but does not describe competitor-site identification — [Google Patents US20200285888A1](https://patents.google.com/patent/US20200285888A1/en)
- Vendor material, which is marketing rather than peer-reviewed:
  - Actowiz describes matching identical SKUs across Amazon, Flipkart and Croma using model numbers and identifiers, and offers Myntra/Amazon/Flipkart price tracking — [Actowiz](https://www.actowizsolutions.com/electronics-price-parity-same-sku.php); [Actowiz Myntra/Amazon/Flipkart](https://www.actowizsolutions.com/competitive-price-tracking-myntra-amazon-flipkart.php)
  - Intelligence Node markets ML plus human-in-the-loop product matching for apparel — [Intelligence Node](https://intelligencenode.com/solutions/product-matching)

### Inferences
- A small system cannot borrow a published Myntra competitor-matching recipe. The closest reusable idea is Myntra's own: treat Amazon vs Myntra photos as a domain shift. The paper's fix is cheap and label-free: an autoencoder with an adversarial domain classifier on frozen backbone features, then KNN. Today, a garment crop plus a modern pretrained embedding (e.g. CLIP or FashionCLIP) would likely be a stronger starting point, but that is my inference, not something Myntra published.

### Gaps
- No Flipkart Tech blog post on product matching or competitor monitoring was found in this pass (only one general search was run).
- No public information on Myntra's brand catalogue ingestion pipeline (e.g. automated QC or duplicate checks at onboarding) beyond the integrator listing templates above.
