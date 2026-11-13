# External tools and methods for matching Myntra listings to the same product on other sites

Research date: 2026-11-12. Scope: India, 2020–2026. Method: web search and fetch of public pages, `gh search repos`, and a few low-volume plain-HTTP GETs with a browser User-Agent (no bot-protection bypass, no Apify or paid APIs). Two of the tests below were run directly against Myntra and the Puma India site. Their results count as primary evidence, but each covers only one product.

## 1. Price trackers and comparators that support Myntra: do they compare across stores, and how do they key products?

### Takeaway
Consumer trackers key Myntra products on Myntra's own URL or style id and track price history for that one listing. Cross-store "same product" features exist (PriceHistory's "Compare with Ajio & Nykaa", Buyhatke's "Lookalike"), but none documents its matching method, and both say they return "the same product (or a close match)" or "similar products". In practice they are fuzzy similar-item finders, not exact style-code matchers. I found no tracker that publishes a match rate for fashion.

### Cited Findings
- **PriceHistory (pricehistoryapp.com):**
  - The Myntra page takes a Myntra product URL as input. It says "We crawl Myntra multiple times daily and timestamp every price point."
  - "Typical price" is "the median of every selling price we recorded for it over the last 365 days". Only listings with at least five recorded prices count.
  - Cross-store feature: "One click shows you what the same product (or a close match) costs on Ajio and Nykaa." No matching method is described.
  - Its product URLs use its own slug plus a numeric id (e.g. `/product/puma-men-white-black-colourblocked-idp-sneakers-2708`). The page does not say whether that id is the Myntra style id.
  - Page © 2026.
  - [PriceHistory Myntra page](https://pricehistoryapp.com/myntra-price-history)
- **Buyhatke:**
  - Chrome Web Store listing: version 5.1.177, updated November 11, 2026, "1,000,000 users".
  - It says "Use Lookalike to find exact products across stores and never miss a deal" and, in the same listing, "Find similar products at a lower cost". The wording mixes exact and similar.
  - Myntra and Ajio are named only under Auto Coupons. The listing describes no fashion-specific matching.
  - [Chrome Web Store](https://chromewebstore.google.com/detail/buyhatke/ojplmecpdpgccookcobabopnaifgidhf?hl=en)
- **Buyhatke, older descriptions:**
  - Earlier descriptions call the feature "Ditto" ("find the same product at a lower cost on other e-commerce platforms").
  - Digit's article on the Compare Hatke extension says it "will automatically search for the same product on every shopping portal". That implies search by title or keyword, not by identifier.
  - Its worked examples are electronics, e.g. a Flipkart item at ₹74,900 vs ₹69,999 elsewhere.
  - [Digit](https://www.digit.in/features/general/shop-online-smarter-with-the-compare-hatke-browser-extension-20245.html); [Tribune partner piece](https://www.tribuneindia.com/partner-exclusives/flipkart-big-billion-days-sale-how-buyhatke-assists-shoppers-in-comparing-deals); [App Store](https://apps.apple.com/in/app/id895452619)
- **Other trackers:**
  - KabSasta (Amazon, Flipkart, Myntra, Reliance Digital) shows a price chart and a deal score per listing. [Toolradar](https://toolradar.com/tools/kabsasta)
  - "Real Price History Tracker" shows price-history graphs on Amazon, Flipkart and Myntra pages. [Chrome Web Store](https://chromewebstore.google.com/detail/real-price-history-tracke/lbeodfloccamodnjkpklnikhjbelndea)
  - Neither describes cross-store matching for Myntra.
- **Google Shopping India:**
  - Launched in 2018–19 with a Shopping tab showing "prices from across multiple retailers" and "style search in Google Lens". Merchant listing was free through Merchant Center.
  - Coverage named Flipkart, Amazon and Snapdeal. I found no confirmation that Myntra feeds Google Shopping.
  - [Search Engine Land](https://searchengineland.com/google-shopping-expands-to-india-in-english-and-hindi-309454); [Inc42](https://inc42.com/buzz/google-launches-shopping-homepage-in-india-with-an-eye-on-200-bn-ecommerce-space); [Google India blog](https://blog.google/intl/en-in/products/explore-communicate/shopping-on-google-brings-new-features/)

### Inferences
- These consumer tools probably build the cross-store lookup by sending the Myntra title (brand + product name) to each other store's search and ranking the results. The "or a close match" and "similar" wording points to no identifier-level matching. This is inferred from the wording only; no tool documents it.
- None of these tools solves the Amazon style code → Myntra direction better than a title search would.

### Gaps
- I could not find documentation of how PriceHistory or Buyhatke actually match. Their extensions were not reverse-engineered.
- No match-rate or precision figures for any consumer tool.
- Smartprix (fashion), Pricebefore, Lyst, and Fynd as an aggregator: no relevant Myntra matching material surfaced within the search budget.
- Whether Myntra currently appears in Google Shopping India or Lens results is unconfirmed (all sources are 2018–19).

## 2. Price-intelligence vendors: how they say they match Indian fashion, and with what precision or coverage

### Takeaway
Every vendor describes the same pipeline:
1. Identifiers (GTIN/EAN/UPC) where they exist.
2. LLM/NLP attribute extraction and normalization (brand, colour, size, fit, material).
3. Text and image embeddings (CLIP, Siamese networks, CNNs) for candidate retrieval.
4. Human review of edge cases.

The most honest figure comes from DataWeave: apparel match rates "typically sit between 40% and 60%", against about 95% for electronics, with precision above 85% in fashion. The 95–99%+ "accuracy" claims (Actowiz, Intelligence Node, DataWeave headline) are marketing with no test set described.

### Cited Findings
- **DataWeave, "From Mess To Match" (1 June 2026):**
  - Pipeline: identifier matching (UPC/GTIN/EAN) is high precision but identifiers are often missing; fuzzy title matching is "also brittle"; LLMs extract attributes; a graph store does normalization; transformer text embeddings plus CLIP, Siamese and CNN image features run over more than 100M indexed images.
  - "Close to 90%" of matches are auto-processed. Edge cases go to specialist reviewers, and each decision becomes a training example.
  - Apparel "match rates typically sit between 40% and 60%", versus about 95% in electronics. "Precision exceeding 85% in electronics and fashion." Accuracy is up more than 15% over baseline. Attribute tagging exceeds 75% for the top five categories. 40M+ verified product pairs.
  - Fashion difficulties: "Similarity is subjective"; "Size charts vary by brand, country, and style"; "Fast-fashion brands launch new styles constantly"; sets and bundles; third-party seller variability.
  - [DataWeave blog](https://dataweave.com/blog/from-mess-to-match-solving-product-identity-at-retail-scale)
- **DataWeave product page:** "95%+ accuracy and <5% misses across categories, retailers, and formats". This is marketing. [DataWeave](https://dataweave.com/us/product-matching)
- **DataWeave fashion case study (US retailer, not Indian):** 200,000 SKUs tracked daily, "95%+ matching accuracy and a 75% match rate for high-priority products, surpassing the fashion industry benchmark of 50%". [DataWeave case study](https://dataweave.com/pages/using-dataweaves-ai-powered-pricing-intelligence-for-fashion-ecommerce-retailer)
- **DataWeave, 2017 talk:** text + image matching at more than 90% accuracy, general e-commerce. [DataWeave/Medium](https://medium.com/dataweave/-e5eb8934704a)
- **Actowiz, "Product variant mapping across Myntra, Ajio, Meesho, Amazon" (Dec 26, 2025):**
  - Collects parent and variant IDs, colour, size, material, seller, MRP and selling price.
  - Normalizes attribute strings (e.g. "Olive Green" = "Green – Olive"). NLP extracts material, pattern, fit, gender, brand and usage from titles. A separate size and fit step runs for fashion.
  - "AI-based image comparison" catches the same product under different titles, from multiple sellers, or from "the same photoshoot across platforms".
  - Claims "99%+ accuracy" with no test set or methodology. The example tables are labelled "Example Data". No failure cases are given.
  - [Actowiz](https://www.actowizsolutions.com/product-variant-mapping-myntra-ajio-meesho-amazon-retail-intelligence.php)
  - Actowiz's Myntra/Ajio/Flipkart fashion price-tracking report gives no matching method or figures, only generic "LLM… text and image embeddings" boilerplate. [Actowiz](https://actowizsolutions.com/fashion-product-price-tracking-myntra-ajio-flipkart.php)
- **Intelligence Node:**
  - CNN image-embedding similarity for candidate pairs. Attributes are split into "mandatory" and "non-mandatory".
  - Claims 99% accuracy backed by contractual SLAs, and "Attribute Identification = 99% Accuracy". No dataset or category is given.
  - [IN product-matching blog](https://www.intelligencenode.com/blog/product-matching-ai-for-ecommerce/); [IN 2022 guide PDF](https://info.intelligencenode.com/hubfs/ebooks/2022/A-Guide-to-AI-driven-Product-Matching-2022.pdf)
- **Zilliz/Milvus case study of an unnamed Indian retailer ("the 'Amazon of India'", likely Flipkart; not confirmed):**
  - Competitor matching uses 1024-dim embeddings of "product images and descriptions" and cosine similarity.
  - Results are pre-filtered by category, brand and price range, then thresholded, with manual review.
  - Scale: more than 20M own SKUs plus about 5M SKUs per competitor catalog. Jobs went from 12 days to about 2 days.
  - No precision or recall figures. Undated.
  - [Zilliz](https://zilliz.com/customers/indian-online-retailer)
- **Flipkart research:** Indian catalogs have India-specific categories (sari, kurta, kurti), and "few attributes are mandatory for the sellers", which makes attribute extraction harder. [SIGIR eCom'23 paper](https://sigir-ecom.github.io/eCom23Papers/paper_7.pdf)
- **Multimodal deduplication at a Turkish marketplace (not Indian, 2025):** text + image dedup reached F1 0.90, versus 0.83 for a third-party solution. Fashion matching "has to heavily rely on both images and text". [arXiv 2509.15858](https://arxiv.org/abs/2509.15858)

### Inferences
- Verified detail versus marketing: the pipeline shape is consistent across vendors and credible. The only accuracy numbers with a stated split are DataWeave's (40–60% apparel match rate; above 85% precision). Treat 95–99%+ as unverified marketing.
- Fashion coverage is the bottleneck, not precision. Even well-funded vendors find a match for only about half of apparel items. So a pipeline built for us should expect a large share of "no confident match" outcomes and route them to review rather than force a match.
- Pre-filtering by brand, category and price, then image + text embedding similarity, then a threshold and human review is the common recipe (Zilliz, DataWeave).

### Gaps
- Increff, Unbxd, PromptCloud and Fynd: no Myntra-matching method or figures surfaced within the search budget.
- No vendor publishes Myntra-specific precision or recall.
- The DataWeave apparel figures are global, not India-specific.

## 3. Open-source GitHub projects that match Myntra with Amazon, Flipkart or Ajio

### Takeaway
I found no maintained open-source project that does real cross-site product matching involving Myntra. Repos that mention Myntra plus Ajio or Flipkart are toy deal or affiliate bots or student storefront clones (0 stars). The Amazon/Flipkart comparison projects do keyword search on both sites and show the results side by side, without identity matching.

### Cited Findings
- `gh search repos` (run 2026-11-12):
  - "myntra price comparison", "myntra flipkart compare", "myntra product matching" and "myntra amazon compare" returned 0 repos.
  - "myntra ajio" returned only 0-star repos. Examples: `manojrathaus39-wq/orderkaro` ("Sabse saste deals ka comparison – Myntra, Ajio, Flipkart", 2026-10-16), `vinayaknaik999/gold-deal-finder-myntra-ajio`, `yadavji971/affiliate-link-bot`, `BuyTheLookFit/buy-the-look`, and Excel or "Online-Store" student projects.
- Amazon–Flipkart comparison repos:
  - [Amazon-Flipkart-Price-Comparison-Engine](https://kandi.openweaver.com/python/sushantPatrikar/Amazon-Flipkart-Price-Comparison-Engine) (about 43 stars, compares "price of the product entered by the user").
  - [priceChamp](https://github.com/2k4sm/priceChamp) (BeautifulSoup scraping).
  - [Smart-Pick NLP](https://github.com/mayureshagashe2105/Smart-Pick-NLP-Product-Comaprison-Amazon-vs-Flipkart) (NLP similarity to "suggest best matches").
  - [Product-Matching-Milvus](https://github.com/sreelalhari/Product-Matching-Milvus) (Amazon and Flipkart scrapers plus attribute- or embedding-based matching script).
  - None include Myntra.
- Generic fashion matching code: [Product_Matching_Using_CNN](https://github.com/Ruparna25/Product_Matching_Using_CNN) (Shopee-style image matching).

### Inferences
- There is no reusable open-source baseline for the Myntra side. The design has to be built from the vendor recipe (brand filter, title/attribute similarity, image embeddings).

### Gaps
- GitHub code search, as opposed to repo search, was not run. Small private scripts inside unrelated repos may exist.

## 4. Brand-site bridging: style code to canonical name to Myntra search

### Takeaway
The bridge works, at least for Puma.
- On in.puma.com, the style number (first 6 digits of the Amazon code, e.g. 528856 from 52885601; the last 2 digits are the colour or swatch) resolves by plain HTTP to a canonical product name: "Train All Day Men's Breathable Training Tee".
- Myntra product names for Puma reuse that name almost verbatim, so a Myntra search on brand + canonical name returns the right family, split by colour.
- Final disambiguation still needs colour and an image check, because Myntra lists the same name and colour under more than one style id.
- Several brand sites block or rate-limit plain HTTP: adidas.co.in, Nike India and H&M India returned 403; levi.in and uspoloassn.in search returned 429.

### Cited Findings (own plain-HTTP tests, 2026-11-12, browser UA, one request each)
- **Puma India:**
  - `https://in.puma.com/in/en/pd/x/528856?swatch=01` returned 200 (about 1.1 MB HTML).
  - Canonical URL: `https://in.puma.com/in/en/pd/train-all-day-mens-breathable-training-tee/528856`. og:image path `global/528856/01/.../Train-All-Day-Men's-Breathable-Training-Tee`, app link `puma://products/528856`.
  - `https://in.puma.com/in/en/search?q=52885601` returned 200, titled "52885601 | PUMA India".
  - This confirms the style + colour code format and that the name is readable without JavaScript.
- **Myntra search by canonical name** (`https://www.myntra.com/puma-train-all-day-breathable-training-tee`) returned 200 with 645 results. Top hits:
  - 35720668 "Puma Train All Day Men Breathable Training Tee", Black
  - 35720666, same name, Green
  - 35720667, same name, Blue
  - 44935702 "Puma Train All Day Men's Breathable Training Tee", Blue
  - 44935701, same name, Purple
  - The same name and colour (Blue) appears under two Myntra style ids, 35720667 and 44935702, so name + colour alone can be ambiguous.
- **Myntra search with the shorter phrase** "puma-train-all-day-tee" returned 106 results, dominated by other "Train All Day Essentials …" tees (e.g. 39018690, 44903727). A shortened or paraphrased name pulls in many sibling styles. Use the full canonical name.
- **Pitfall:** `https://www.myntra.com/528856`, the bare brand style number, resolved to an unrelated Myntra product page, "Blackberrys Men Khaki Sharp Fit Trousers". Myntra treats a bare numeric path as its own style id, so brand style numbers must never be put into Myntra URLs or searches as bare numbers.
- **Access results:**

| Site | Request | Result |
|---|---|---|
| adidas.co.in | `/search?q=IF8065` | 403 |
| Nike India | `nike.com/in/w?q=DV0788` (redirected to `www.nike.in/nike_store/c/2`) | 403 |
| H&M India | `www2.hm.com/en_in/index.html` | 403 |
| levi.in | homepage | 200 |
| levi.in | `/search?q=511` | 429 |
| uspoloassn.in | homepage | 200 |
| uspoloassn.in | `/search?q=shirt` | 429 |
| allensolly.abfrl.in | homepage | 200 |
| myntra.com | `/puma` | 200 |

### Inferences
- For Puma, and probably other brands whose Indian site uses the global article-number scheme (style + colour), the reliable chain is:
  1. Amazon style code
  2. Brand site, which gives the canonical name and the colour for the swatch
  3. Myntra search on brand + full canonical name
  4. Filter by colour
  5. Image similarity against the brand or Amazon image to choose among duplicate style ids
- Adidas, Nike and H&M block plain HTTP. For those brands the bridge would need another public source of the code-to-name mapping (e.g. the Amazon title itself, or search engines), not the brand site.
- The 429s on levi.in and uspoloassn.in mean any bridging must be cached and very low rate.

### Gaps
- Tested on one Puma style only. I did not test whether Puma's colour code 01 maps to Myntra "Black" for this item; the Puma page colour name was not extracted.
- Did not check whether ABFRL brand sites (Allen Solly) or USPA expose a style code on their product pages.
- Did not test Ajio, Tata CLiQ or Nykaa Fashion. Ajio and Tata CLiQ are believed to show brand style codes, but this was not verified here.

## 5. Google or Bing as a bridge ("site:myntra.com <brand> <name>", Google Shopping, Lens)

### Takeaway
I found no documentation or worked examples showing that `site:myntra.com` queries or Google Shopping/Lens reliably surface the exact Myntra product. Google Shopping India and Lens "style search" exist (2018–19 launch coverage), but Myntra's participation is unconfirmed. Google was not scraped, per the constraints.

### Cited Findings
- Google Shopping India launched with a Shopping tab ("prices from across multiple retailers") and "style search in Google Lens". [Search Engine Land](https://searchengineland.com/google-shopping-expands-to-india-in-english-and-hindi-309454); [Inc42](https://inc42.com/buzz/google-launches-shopping-homepage-in-india-with-an-eye-on-200-bn-ecommerce-space)
- Launch coverage named Flipkart, Amazon and Snapdeal as participants, not Myntra. [Swarajya](https://swarajyamag.com/amp/story/insta/on-the-tail-of-e-tail-now-know-whats-on-amazon-flipkart-and-other-sites-through-google-shopping)
- Myntra itself licensed image search from ViSenze (case study PDF, 2024; not read in detail). Lens-style visual lookup is plausible for Myntra imagery. [ViSenze Myntra case study](https://www.visenze.com/wp-content/uploads/2024/04/ViSenze-Case-Study-Myntra.pdf)
- Third-party Myntra APIs search by keyword and filter by brand, or fetch by Myntra style id or URL. None offers lookup by brand article number. [anysite docs](https://docs.anysite.io/api-reference/myntra/myntraproductssearch); [Scrapingdog](https://docs.scrapingdog.com/myntra-scraper-api/myntra-product-api)

### Inferences
- Because Myntra product names copy the brand's canonical name (Section 4), a `site:myntra.com "<brand> <canonical name>"` query would plausibly reach the right family. But Myntra's own search already does this without a search-engine dependency, and colour and image disambiguation is still needed either way.

### Gaps
- No empirical hit rate for search-engine bridging. That would need a sanctioned search API, which is out of scope here.
- No current (2024–26) confirmation that Myntra is a Google Shopping India merchant.
