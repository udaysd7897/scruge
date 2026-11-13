# Visual / Reverse-Image Product Search APIs for Matching Amazon.in Apparel on Flipkart & Myntra (as of 2026-11-13)

Research date: 2026-11-13. No paid APIs were called. Pricing came from vendor pages read on this date unless noted otherwise. Several official pages (Cloud Vision pricing and docs, TinEye API page, Yandex pricing, Search Engine Land) could not be fetched cleanly. Those items are marked below.

## Q1. Google Lens via SerpApi / SearchAPI.io / Oxylabs / Bright Data, plus the Google Shopping immersive product API: outputs, India coverage, pricing

### Takeaway
Scraped Google Lens is the strongest general-purpose "find this exact garment elsewhere" signal on the market. It is offered by SerpApi, SearchAPI.io, Oxylabs and Bright Data at about $1–$25 per 1,000 calls. Two changes in 2025–26 matter:
- Google removed the Lens **Products** tab, so `type=products` is gone. Price and store data now come back only on some `visual_matches` and `exact_matches` entries.
- SerpApi's `country` parameter has an open bug: results do not get localized.

I found no source showing Lens API results returning flipkart.com or myntra.com for `country=in`. This has to be tested empirically.

### Cited Findings
- **SerpApi Google Lens engine:** `type` = `all` | `exact_matches` | `visual_matches`. Optional parameters: `country` (2-letter code), `hl`, `q` (text refinement, only for all/visual_matches), `auto_crop`, `no_cache`. `visual_matches` items include `position, title, link, source, source_icon, thumbnail`. Cached results expire after 1 hour. — [SerpApi Google Lens API](https://serpapi.com/google-lens-api)
- **SerpApi Lens "Products" type discontinued:** "Google has discontinued the Products search type in Google Lens. As a result, this SerpApi feature is no longer available." The old fields were `title, link, source, rating, reviews, price, in_stock`. — [SerpApi Google Lens Products API](https://serpapi.com/google-lens-products-api)
- **SearchAPI.io confirms the same:** `search_type=products` "is no longer supported. Google Lens removed its Products tab." It recommends running the title of a visual match through the Google Shopping API to get priced listings. — [SearchAPI.io Google Lens docs](https://www.searchapi.io/docs/google-lens)
- **SearchAPI.io Lens fields:**
  - `visual_matches` include `title, link, source, price, extracted_price, currency, stock_information, thumbnail` ("some matches include price and stock").
  - `exact_matches` include `title, link, source, price, extracted_price, currency, stock_information, extensions`.
  - `country` (default US) sets results and currency, and "Shopping results are limited to a specific list of countries".
  - `crop` parameter takes a bounding box.
  - `zero_retention` is Enterprise only.
  - Google redirect links are resolved with the free Google Resolve API via `link_token`.
  — [SearchAPI.io Google Lens docs](https://www.searchapi.io/docs/google-lens)
- **SerpApi `country` localization bug (#3317):** opened 2025-12-09 and still open/queued as of Oct 2026. With `country=IT` the results were Zara Australia, Farfetch Bahrain and Amazon US. A UK user reported `country=GB` returned one UK result while Chrome Lens returned mostly UK results. A maintainer reproduced this and said the problem points to SerpApi's side. More reports came in Feb and Apr 2026. — [GitHub serpapi/public-roadmap #3317](https://github.com/serpapi/public-roadmap/issues/3317)
- **SerpApi pricing (2026-11-13):**

  | Plan | Price/month | Searches/month | Searches/hour |
  |---|---|---|---|
  | Free | $0 | 250 | 50 |
  | Starter | $25 | 1k | 200 |
  | Developer | $75 | 5k | 1,000 |
  | Production | $150 | 15k | 3,000 |
  | Big Data | $275 | 30k | — |

  Only successful searches count, and cached searches are not counted. The "U.S. Legal Shield" (up to $2M) applies from Production upward. — [SerpApi pricing](https://serpapi.com/pricing)
- **SearchAPI.io pricing (2026-11-13):**

  | Plan | Price/month | Searches/month | Cost per 1,000 |
  |---|---|---|---|
  | Developer | $40 | 10k | $4 |
  | Production | $100 | 35k | $3 |
  | BigData | $250 | 100k | $2.5 |
  | Scale | $500 | 250k | $2 |

  At most 20% of plan credits can be used per hour. New accounts get 100 free requests. — [SearchAPI.io pricing](https://www.searchapi.io/pricing)
- **Oxylabs Google Lens target:** "extracts visual search results from provided image URLs" as parsed JSON (15 data points), with `gl`/`hl`/`uule` geo parameters and proxies in 195 countries. No Lens-specific rate is published. General Google tiers start at $1.00/1K results (non-JS) and $1.35/1K (JS). There is a $5 welcome credit ("2K free results"). — [Oxylabs Google Lens API](https://oxylabs.io/products/scraper-api/serp/google/lens)
- **Bright Data:** third-party comparisons list its SERP API at $1.50/1K pay-as-you-go or $1.30/1K on the $499 Scale plan, with 5,000 free SERP requests per month. I found no Lens-specific price. (Aggregator figures, not verified on the vendor page.) — [costbench Bright Data vs SerpApi](https://costbench.com/compare/bright-data-vs-serpapi/); [usagepricing Bright Data](https://usagepricing.com/blueprint/bright-data)
- **SerpApi Google Immersive Product API:** takes a `page_token` from Google Shopping results. It returns `product_results.stores[]` with `name, link, price, extracted_price, shipping, total, original_price, discount, rating, reviews, payment_methods`. By default it returns 3–5 stores. `more_stores=true` returns up to 13, and `next_page_token` pages through more. The page does not state country support or credits per call. Cached results are free for 1 hour. — [SerpApi Immersive Product API](https://serpapi.com/google-immersive-product-api)
- **Google Shopping in India:** it has existed since 2018 (English and Hindi), and Merchant Center free listings are available to Indian retailers. — [Search Engine Land 2018](https://searchengineland.com/google-shopping-expands-to-india-in-english-and-hindi-309454); [Google blog APAC free listings](https://blog.google/around-the-globe/google-asia/apac-free-listings)

### Inferences
- Since the Products tab was removed, you have to read store and price data from `visual_matches` / `exact_matches` (SearchAPI.io exposes price/stock there), or take a two-step route: Lens → title → Google Shopping (gl=in) → immersive product stores. Each step is a separate billed call.
- Because of the open SerpApi `country` bug, Indian marketplace results from SerpApi Lens may be unreliable even with `country=in`. SearchAPI.io or Oxylabs (which route through geo-located proxies) may localize better. This is untested.
- Whether Flipkart and Myntra feed Google Shopping India (and so appear in immersive `stores`) is not confirmed by any source I found. Myntra product pages are heavily JS/app-driven, which may reduce how often they appear in Lens or Shopping. This is speculative.
- Latency: no vendor publishes Lens latency. Typical synchronous SERP-API calls are seconds, not milliseconds. Budget about 2–10 s per Lens call (unverified estimate).

### Gaps
- No public example or benchmark showed Lens API results with flipkart.com or myntra.com links for India. A small empirical test is needed (e.g., 20 Amazon.in apparel images through free tiers: SerpApi's 250 free searches, SearchAPI.io's 100, Oxylabs' $5 credit).
- SerpApi does not say how many credits an immersive product call costs.
- Bright Data's Lens-specific price could not be confirmed on the vendor page.

## Q2. Bing Visual Search, Yandex, TinEye, Google Cloud Vision Web Detection: status, pricing, marketplace coverage

### Takeaway
None of these four is a good primary retrieval step for Indian marketplaces:
- **Bing Visual Search API:** retired on 2025-08-11.
- **TinEye:** finds only exact or near-duplicate image copies, at about $0.01–$0.04 per search.
- **Cloud Vision Web Detection:** $3.50/1,000 after 1,000 free per month. It returns `pagesWithMatchingImages`, which can occasionally hit marketplace pages that reuse the brand's catalog image, but it has no shopping or price data.
- **Yandex:** has an official Search-by-image API in Yandex Cloud, but pricing could not be retrieved and Indian marketplace coverage is doubtful.

### Cited Findings
- **Bing Search APIs, including Visual Search, retired 2025-08-11.** The retirement was announced around 2025-05-12/13, and Microsoft points users to "Grounding with Bing Search" in Azure AI Agents. — [Microsoft Learn lifecycle announcement](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement); [The Register 2025-05-15](https://www.theregister.com/2025/05/15/bing_search_apis_retired/); [SE Roundtable](https://www.seroundtable.com/bing-search-apis-retiring-august-11-2025-39406.html)
- **Visual Search specifically:** the programmatic Bing Visual Search API was retired in August 2025, and only the manual web interface remains. — [archivarix echo (secondary)](https://echo.archivarix.net/de/archive/bing-visual-search)
- **Google Cloud Vision Web Detection pricing:** first 1,000 units per month free, then $3.50 per 1,000 units up to 5M per month, with higher volumes by contact. The official page could not be fetched directly. The figure is from search snippets of cloud.google.com localized pricing pages and a 2026 third-party guide. — [Cloud Vision pricing](https://cloud.google.com/vision/pricing); [vantaige.io 2026 guide](https://vantaige.io/blog/google-vision-ai-pricing-explained-alternatives-2026)
- **Web Detection docs** moved to docs.cloud.google.com, and the fetch timed out. The field list (`webEntities`, `fullMatchingImages`, `partialMatchingImages`, `pagesWithMatchingImages`, `visuallySimilarImages`, `bestGuessLabels`) is from prior knowledge and is not re-verified here. — [Cloud Vision Detect Web entities](https://docs.cloud.google.com/vision/docs/detecting-web)
- **TinEye API pricing:** prepaid bundles of 5,000 searches for $200, 10,000 for $300, 50,000 for $1,000, and 1,000,000 for $10,000. Bundles are valid 2 years, and auto top-up is available. The blog post is undated, so current 2026 rates are not confirmed. Aggregator claims (e.g., "$50/mo unlimited") conflict with TinEye's own docs. — [TinEye blog: new pricing](https://blog.tineye.com/new-image-search-pricing/); [TinEye help: bundles](https://help.tineye.com/article/169-purchasing-search-bundles); [TinEye auto top-up](https://blog.tineye.com/introducing-auto-top-up-for-the-tineye-api/)
- **Yandex Cloud Search API** has an official ImageSearch `searchByImage` endpoint (POST, accepting url, data or id). Billing is per request per month, and prices vary by region and contracting legal entity. The pricing page was updated 2025-12-03 and now redirects to aistudio.yandex.ru. Actual rates were not retrieved. — [Yandex search-by-image how-to](https://yandex.cloud/en/docs/search-api/operations/search-images-by-pic); [Yandex Search API pricing](https://aistudio.yandex.ru/docs/en/search-api/pricing)

### Inferences
- TinEye matches near-duplicate *images*, not products. It would only find Flipkart/Myntra listings that reuse the identical brand catalog photo and that TinEye has crawled. Its index is skewed toward the open web, not JS-rendered marketplace PDPs, so recall on Myntra/Flipkart is likely low.
- Cloud Vision Web Detection is officially supported and ToS-clean, so it is a reasonable cheap secondary signal. Its `pagesWithMatchingImages` and `fullMatchingImages` can surface marketplace pages when sellers reuse brand images (common for branded apparel sold on all three sites). Its `bestGuessLabels` and `webEntities` can supply query text. It returns no prices.
- Yandex works well for faces and generic reverse search, but its India e-commerce index is likely thin. Account and billing for non-Russian entities may be friction. Unverified.

### Gaps
- I could not fetch the official Cloud Vision pricing and Web Detection docs (redirect and timeout). Max results per feature and the `includeGeoResults` behavior were not verified.
- No current (2026) TinEye price page was confirmed.
- Yandex per-request price and availability to Indian accounts are unknown.
- No source benchmarks any of these on finding Flipkart/Myntra product pages.

## Q3. Self-hosted alternative: embedding candidates with CLIP / FashionSigLIP and ranking locally

### Takeaway
A practical design: get candidates by text search on Flipkart and Myntra using the Amazon title, brand and attributes, then rerank the candidate thumbnails against the Amazon image with Marqo FashionSigLIP (open weights). This avoids per-call SERP fees and gives you control over precision. CPU cost is roughly tens of milliseconds per image (unverified third-party figure), so scoring 20–50 candidates takes about 1–4 s on CPU.

### Cited Findings
- **Marqo FashionCLIP / FashionSigLIP:** about 150M-parameter fashion embedding models released under Apache 2.0, fine-tuned with Generalised Contrastive Learning. Marqo claims they are about 10% faster for inference than FashionCLIP 2.0 and OpenFashionCLIP, and better on fashion retrieval benchmarks. — [Marqo blog](https://www.marqo.ai/blog/search-model-for-fashion); [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP); [GitHub marqo-FashionCLIP](https://github.com/marqo-ai/marqo-FashionCLIP)
- **CPU latency:** a third-party listing gives about 70 ms per image on CPU and about 6 ms on an A100. The same page lists 86M parameters and an MIT license, which conflicts with Marqo's own statement of 150M parameters and Apache 2.0, so treat the latency as approximate. — [Mixpeek model page](https://www.mixpeek.com/model/Marqo/marqo-fashionSigLIP); contradicted (params and license) by [Marqo blog](https://www.marqo.ai/blog/search-model-for-fashion)
- **Newer checkpoint:** the model card mentions marqo-fashion-SigLIP-2 with a further "78% improvement in MMR and recall". — [HF model card](https://huggingface.co/Marqo/marqo-fashionSigLIP)

### Inferences
- Embedding similarity alone cannot separate near-identical variants (same print in a different colour or fabric, lookalikes from other brands). Use it as a reranker and combine it with hard filters: brand match, colour, style code or MPN, size availability, and fuzzy matching on the title.
- Candidate retrieval still needs some way to search Flipkart and Myntra (their own site search, or a SERP API with `site:flipkart.com` / `site:myntra.com`). Scraping those sites carries its own ToS risk (see Q4).

### Gaps
- No official CPU benchmark. Measure it yourself (e.g., ONNX or int8 on the target machine).
- No published benchmark of FashionSigLIP on cross-marketplace Indian apparel matching.

## Q4. Legal / ToS considerations

### Takeaway
All Google-Lens-via-SERP-API options rely on scraping Google, which Google's ToS prohibits. Google sued SerpApi in December 2025 under the DMCA. The core DMCA claims were reported dismissed in 2026, but litigation risk to vendors, and with it continuity risk for customers, remains. Official APIs (Cloud Vision, TinEye, Yandex Cloud) are contractually clean.

### Cited Findings
- **Google v. SerpApi:** Google sued SerpApi on 2025-12-19 in N.D. Cal., alleging DMCA §1201 circumvention of its "SearchGuard" anti-bot system, including automated CAPTCHA bypassing. — [IPWatchdog 2025-12-26](https://ipwatchdog.com/2025/12/26/google-sues-serpapi-parasitic-scraping-circumvention-protection-measures/); [SE Roundtable](https://www.seroundtable.com/google-sues-serpapi-40631.html)
- **Ruling:** Chief Judge Yvonne Gonzalez Rogers reportedly dismissed Google's DMCA claims on July 20 (2026, per article context). The court held that "To the extent that Google Search results do not contain any copyrighted content, SearchGuard cannot be said to effectively control access." It allowed an amended claim about copyrighted Knowledge Panel material and rejected SerpApi's standing argument. (The Search Engine Land page returned 403, so this is from the search snippet and secondary coverage.) — [Search Engine Land](https://searchengineland.com/google-loses-key-dmca-claims-against-serpapi-in-scraping-lawsuit-483185); [PPC Land](https://ppc.land/google-loses-dmca-bid-to-treat-search-scraping-like-dvd-piracy/)
- **Reddit suit:** Reddit separately sued SerpApi and others in October 2025. — [IPWatchdog](https://ipwatchdog.com/2025/12/26/google-sues-serpapi-parasitic-scraping-circumvention-protection-measures/)
- **SerpApi's Legal Shield:** covers customers up to $2M for scraping and parsing search-engine data, only on Production ($150/mo) and higher plans. — [SerpApi pricing](https://serpapi.com/pricing)
- **Caching:** SerpApi and SearchAPI.io cache results for 1 hour (cached hits are free on SerpApi). SearchAPI.io offers zero-retention on Enterprise. — [SerpApi Lens](https://serpapi.com/google-lens-api); [SearchAPI.io Lens](https://www.searchapi.io/docs/google-lens)

### Inferences
- For a small app, the main practical risks are vendor discontinuity and Google layout changes (the Products tab removal shows this), not direct liability. Wrap the provider behind an interface so you can switch between SerpApi, SearchAPI.io and Oxylabs.
- Flipkart's and Myntra's own terms likely restrict automated scraping of their sites. I did not verify those terms here. Displaying links and prices back to users is lower risk than bulk-storing catalog data.
- Cloud Vision's terms permit programmatic use. Long-term caching of results is governed by Google Cloud terms, which were not reviewed here.

### Gaps
- Did not read Google's Terms of Service text, Flipkart/Myntra ToS, or SearchAPI.io/Oxylabs legal terms directly.
- The exact year and status of the amended complaint after the July ruling were not confirmed from a primary docket.

## Q5. Recommendation: retrieval step and combining with identifiers and attributes for exact-match precision

### Takeaway
Use a hybrid pipeline:
1. **Text-first:** search Flipkart and Myntra (or Google Shopping with gl=in) using a query built from the Amazon title: brand + product type + colour + key attribute + style code if present.
2. **Lens as a parallel visual recall step:** SearchAPI.io or SerpApi Google Lens with `country=in`, plus `q`=brand. Keep only results whose link domain is flipkart.com or myntra.com.
3. **Optional cheap image-reuse signal:** Cloud Vision Web Detection (`pagesWithMatchingImages`), ToS-clean at $3.50/1K.
4. **Rerank** all candidates locally with FashionSigLIP image similarity plus attribute and identifier checks.

Avoid Bing (retired) and TinEye or Yandex as primary steps.

### Cited Findings
- Lens no longer has a Products tab. SearchAPI.io suggests chaining the visual-match title into the Google Shopping API for priced listings. — [SearchAPI.io Lens docs](https://www.searchapi.io/docs/google-lens)
- Lens supports a `q` text refinement alongside the image (all/visual_matches) and a crop box. — [SerpApi Lens](https://serpapi.com/google-lens-api); [SearchAPI.io Lens](https://www.searchapi.io/docs/google-lens)
- Immersive product API returns up to 13 stores with prices when `more_stores=true`. — [SerpApi Immersive Product](https://serpapi.com/google-immersive-product-api)
- **Cost at 1,000 lookups per month (2 Lens/Shopping calls each):**
  - SerpApi Developer: $75 for 5k searches
  - SearchAPI.io Developer: $40 for 10k searches
  - Cloud Vision: about $3.50 for 1k lookups after the free tier

  — [SerpApi pricing](https://serpapi.com/pricing); [SearchAPI.io pricing](https://www.searchapi.io/pricing); [Cloud Vision pricing](https://cloud.google.com/vision/pricing)

### Inferences
- **Precision rules for declaring an exact match:**
  - (a) Brand must match after normalisation.
  - (b) Style code, model number or EAN matches if present. Amazon.in apparel listings often carry a brand "style name/number". Myntra and Flipkart PDPs often show "Style ID"/"Model ID", but these differ per marketplace, so they are rarely shared.
  - (c) Colour family matches.
  - (d) FashionSigLIP cosine is above a tuned threshold and is the top-1 margin over runner-up.
  - (e) Price is within a plausible band.
  - Flag low-margin cases as "similar" rather than "same".
- **Crop before Lens:** apply a garment-only crop (the crop parameter, or local detection) to the Amazon image, because model and background reduce match quality.
- **Domain filtering:** request `country=in`, but filter by domain in code instead of trusting the parameter, given SerpApi bug #3317.
- **Validate first:** run a 20–50 item pilot on free tiers to measure how often Flipkart and Myntra appear in Lens results before committing. This is the largest open uncertainty.

### Gaps
- No empirical data on the Flipkart/Myntra hit rate for any service. A pilot is needed.
- No published latency figures for any SERP-API Lens endpoint.
