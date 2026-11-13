# Identifiers and attribute extraction for phone/TV variant matching (Amazon.in, Flipkart, Croma)

Scope note: fixture findings below come from a read-only inspection of `/Users/sid/scruge/tests/fixtures/` on 2026-11-12, cited as `[fixture: file]`. Web findings carry URLs. Few web sources were authoritative for model-code decoding: manufacturers do not publish decoders, so most decoding rules here are either confirmed from fixture data or marked as inference.

## 1. Manufacturer model-code conventions: what they encode, and whether a generic parser can split base model / size / variant

### Takeaway
For **phones**, the manufacturer "model number" (Apple A3xxx, OnePlus CPH2745, Samsung SM-S948B) identifies the hardware model and region only. It does **not** encode storage or colour. Only two kinds of code are per-variant SKUs: Apple part numbers (MG8H4HN/A) and Samsung full codes (SM-S948B**ZKC**INS). So for phones, the variant has to come from structured storage/RAM/colour fields. For **TVs**, the model code is per-variant and does encode screen size. A generic regex, "size = first 2-digit number 24–100 at the start or right after a 1–5 letter prefix/hyphen", recovers the size and base series for LG, Samsung and Sony without per-model lists.

### Cited Findings
- **Apple part numbers** follow the structure `SXXXXRR/U`, where RR is a region code, and a community list gives **HN = India**. Apple has never published an official region-code list, so these lists are community-compiled. — [gist: Apple part numbers](https://gist.github.com/donn/0c501ab625625c381fdf3210bf0ff275); [Apple Community](https://discussions.apple.com/thread/253263599)
- A forum answer says the part number always has five characters before the region code (so MG8H4 + HN + /A). — [Apple Community](https://discussions.apple.com/thread/253263599)
- **Apple model numbers (A-numbers)** are per model and region group, not per variant. For India ("other countries and regions"): iPhone 17 = A3520, iPhone Air = A3517, iPhone 17 Pro = A3523, iPhone 17 Pro Max = A3526. The US equivalents are A3258/A3260/A3256/A3257 and China mainland A3521/A3518/A3524/A3527. — [Apple: Identify your iPhone model](https://support.apple.com/en-in/108044). India is not named on the page, so placing it under "other countries" is an inference.
- On Amazon.in, the iPhone 17 Pro 256 GB Cosmic Orange listing has `Item model number = MG8H4HN/A`. It carries no A-number. — [fixture: amz_iphone17pro.json]
- **Samsung**: Samsung does not publish one universal decoder, and letter meanings shift between generations. — [itechguides](https://www.itechguides.com/what-do-samsung-galaxy-model-numbers-mean-a-simple-guide/). Samsung India's community forum says INS/INU are "product code AKA region code", with CSC for India = ODD. — [Samsung Members community](https://r2.community.samsung.com/t5/Galaxy-S/INS-vs-INU/td-p/39607). An undated blog says the base-code letter "B" means India/International 5G. — [TheTechOutlook](https://www.thetechoutlook.com/tech-blogs/check-out-the-list-of-samsung-suffix-codes-based-on-different-countries-regions/) (low authority)
- In the Croma captures, Samsung S26 Ultra variants share the base code SM-S948B and differ in a 3-letter middle block plus INS: Cobalt Violet 256 GB = SM-S948B**ZVB**INS, Sky Blue 256 GB = **LBB**, White 256 GB = **ZWB**, Black 512 GB = **ZKC**. The Flipkart S24 Marble Gray 256 GB is SM-S921E**ZAW**INS. — [fixture: croma_apify.json, fk_pdp.html]
- **OnePlus**: in the Croma captures, every OnePlus 15 variant (12+256 in Sand Storm, Infinite Black and Ultra Violet; 16+512 Infinite Black) has the same `Model Number = CPH2745`. OnePlus 13s = CPH2723. — [fixture: croma_golden.json]
- **LG TVs**: the LG model number starts with the screen size in inches, followed by letters/digits for series, region, tuner and design. A letter position encodes the year (e.g. P = 2021, N = 2020). — [Trusted Reviews](https://www.trustedreviews.com/news/what-do-the-lg-tv-product-codes-mean-4038909); [The Product Analyst](https://theproductanalyst.com/lg-tv-model-numbers-explained/). Fixture examples: 55NU870BPLA ("Model Series" NU870B, 2026), 55NU885BPLA, 55UA82006LA (Series "AI TV UA8200"), 55UQ8020PSB (UQ80, 2022), 55UR75006LC**.ATR** (note the dotted suffix), 55QNED85BXA, 55QNED70BLA, 55QNED82BXA, and **OLED55C6XLA**, where the size comes after the "OLED" prefix. — [fixture: croma_golden.json, amz_golden.json, fk_tv_lg_*.html]
- **Sony TVs**: until 2024 the "XR" prefix marked the BRAVIA XR line and other sets used "KD". Sony changed its model-number structure in 2024. — [Expert Reviews](https://www.expertreviews.co.uk/technology/tvs-home-cinema/sony-tv-model-numbers-2022). Sony India notices use India-only "K-" codes such as K-43S22M2. — [Sony India support](https://www.sony.co.in/electronics/support/articles/00409057). Croma fixture: BRAVIA 3 II 55" = **K-55XR35M2**. — [fixture: croma_golden.json]
- Samsung TVs use QE/UE (Europe) and QA/UA (Asia, India) prefixes followed by size, per general TV-decoding guides. — [tab-tv Samsung marking](https://en.tab-tv.com/marking-decoding-tvs-lg-samsung-sony-etc/labeling-and-marking-samsung-tv) (secondary source; not verified against fixtures, because no Samsung TV is in the fixtures)

### Inferences
- **Samsung middle block (inference from 5 fixture codes)**: the first two letters look like colour (ZK = black, ZW = white, ZV = violet, LB = light blue, ZA = gray) and the third letter looks like a storage tier (B = 256 GB, C = 512 GB on S948B). The S921E 256 GB code ends in W, so the storage letter is **model-relative, not global**. Do not decode it with a fixed table. Compare full codes for equality, and use the base `SM-[A-Z]\d{3}[A-Z]?` as the model key.
- **Phone generic parser**: a regex family covers model-level keys without per-model lists: `SM-[A-Z]\d{3}[A-Z]{0,2}`, `CPH\d{4}`, `RMX\d{4}`, `V\d{4}`/`I\d{4}` (vivo/iQOO), `A\d{4}` (Apple model, Nothing A0xx), `M[A-Z0-9]{4}HN/A` (Apple India part number), and Xiaomi `\d{4,5}[A-Z0-9]{3,6}I` style codes. Outside the Samsung/Apple/OnePlus fixtures these patterns are unverified, and the Xiaomi/vivo/Motorola/Pixel formats were not confirmed from sources. The variant itself (storage/RAM/colour) must always come from spec fields.
- **TV generic parser**: `^(?:[A-Z]{1,5}-?)?(\d{2,3})([A-Z].*)$` gives size + rest for 55NU870BPLA, 55UA82006LA, OLED55C6XLA, K-55XR35M2, UA55… and QA55…. Then normalise: uppercase; strip `.ATR`-style dotted suffixes; treat the size-stripped core (NU870B vs UA8200…) as the series. The size-stripped code must still be compared **in full**: NU870BPLA vs UA82006LA differ, while PLA/LA-type trailing letters are region/design and usually constant inside India. Cross-check size against the "Display Size"/"Screen Size" field.
- For TVs, exact equality of the normalised full model code (minus dotted suffix) is a near-sufficient match key. Amazon puts it in Model Name, Model Number and Manufacturer Part Number; Flipkart in "Model Name"; Croma in "Model Number".

### Gaps
- No primary source documents the Samsung colour/storage block, INS vs INU, or the meaning of LG's "A" (2025/26) year letter. A Samsung TV current-year letter scheme was not verified either.
- Formats for Google Pixel (G-codes), Xiaomi/Redmi/POCO, vivo/iQOO, OPPO/realme, Motorola, Nothing, and TCL/Hisense/Vu/Acer/Xiaomi TVs were not confirmed from sources or fixtures in this pass.

## 2. Where each platform exposes identifiers (verified against fixtures)

### Takeaway
**Croma** is the richest source: EAN plus "Model Number" (Samsung full SKU with colour/storage), "Model Series", RAM, Internal Storage, Brand Color and Color for phones and TVs. **Flipkart** has no EAN. It exposes "Model Number" (sometimes base-only SM-S948B, sometimes full SM-S921EZAWINS), "Model Name", RAM, Internal Storage, Color and Display Size. **Amazon** phones (Samsung/OnePlus) carry **no model number at all** in the Apify attributes, only RAM/storage/colour/size. Amazon TVs carry the full model code in three fields, and the Amazon iPhone carries the Apple part number. None of these captures has a usable iPhone RAM value.

### Cited Findings (all from `/Users/sid/scruge/tests/fixtures/`)
| Identifier | Amazon.in (Apify) | Flipkart (HTML) | Croma (Apify/golden) |
|---|---|---|---|
| EAN/GTIN | Not present in any phone/TV fixture | Not present: JSON-LD has only `sku` (FK internal, e.g. MOBHKGAPBMXRGGXZ, TVSHMYS2G69WGGAK), no gtin/mpn | `ean` field on every item; Samsung, LG and Sony EANs pass the GS1 check digit |
| Phone model code | **Absent** for Samsung S25U/S26/S26+/S26U and OnePlus 15; iPhone: `Item model number = MG8H4HN/A` (Apple part no.) | Specs "Model Number": `SM-S948B` (S26U, base only), `SM-S921EZAWINS` (S24, full) | Specs "Model Number": `SM-S948BZVBINS` etc. (full), `CPH2745` |
| Model name/series | iPhone: `Generic Name = iPhone 17 Pro`; OnePlus: `Model Series = OnePlus 15 Series`; Samsung: none (title only) | "Model Name" = `Galaxy S26 Ultra 5G`; "Series" = `S26 Ultra 5G` | "Model Series" = `Galaxy S26 Ultra`, `15`, `13s` |
| RAM | `RAM Memory Installed` = "12 GB"; iPhone `productOverview` "RAM Memory Installed Size = **0.1 GB**" (placeholder junk) | "RAM" = "12 GB" | "RAM" = "12GB"; LG TVs "RAM" = "1.5" (unitless) |
| Storage | `Memory Storage Capacity` = "256 GB"; variantAttributes "Size" = "12GB + 256GB" / "12 GB RAM, 256 GB Storage" / "256 GB" | "Internal Storage" = "512 GB" (+ "User Available Internal Memory", "Total Memory") | "Internal Storage" = "256GB"; key_features "Memory: 12GB RAM, 256GB ROM" |
| Colour | `Colour` + variantAttributes `Colour` (marketing name) | JSON-LD `color` + specs "Color" | "Brand Color" (marketing, e.g. "Ultra Voilet" [sic]) + "Color" (normalised family, e.g. PURPLE, WHITE for Sand Storm) |
| TV model code | `Model Name`, `Model Number`, `Manufacturer Part Number` = 55NU870BPLA; `Model Series = NU87 Series 2026` | specs "Model Name" = 55NU870BPLA / 55UA82006LA (inside `window.__INITIAL_STATE__` specs); "Series" = AI TV UA8200; the JSON-LD name lacks the code | "Model Number" = 55NU870BPLA, OLED55C6XLA, K-55XR35M2, 55UR75006LC.ATR |
| TV size | `Screen Size Unit of Measure`/`Display Size Class` = "55 Inches"; title "139 cms (55 inches)" | "Display Size" = "139 cm (55 inch)" | "Screen Size in Inches" = "55"; titles say "140 cm" or "139.7 cm" or "139 cm" for the same 55" |
| Variant siblings | `variantAsins`, `variantDetails[].name` (e.g. "Cosmic Orange 1 TB Without Protect+"), variantAttributes incl. non-product axes ("Style Name: With exchange bonus", "Configuration: Without Samsung Care/Protect+") | n/a in fixtures | `variant_count` |

Data-quality traps found in the fixtures:
- **Croma model-number copy error**: "SAMSUNG Galaxy S26 Ultra 5G (12GB RAM, 256GB, **Black**)" (EAN 8806097852773) has `Model Number = SM-S948B**LBB**INS`, identical to the **Sky Blue** item. So model suffixes can be wrong, and the title/Brand Color and EAN should win. — [fixture: croma_apify.json]
- **Croma EAN anomalies**: some EANs have a trailing "N" (`6921815630548N`, `8806097852605N`). Three OnePlus 15 EANs (`692181563051N`, `…052N`, `…053N`) are **12 digits and fail the check digit**, i.e. truncated. Strip a trailing N, validate the GS1 mod-10 check, and only then use the EAN as a hard key. — [fixture: croma_golden.json; check computed locally]
- **Amazon iPhone feature-bullet contamination**: the iPhone 17 **Pro** listing's bullet says "Ceramic Shield protects the back of iPhone 17 **Pro Max**". Free-text extraction that reads bullets would mislabel it. Prefer title + `Generic Name` + part number. — [fixture: amz_iphone17pro.json]
- Amazon `variantAttributes` mixes commercial options (exchange/EMI, Samsung Care, Protect+) with product axes, and these must be dropped from the variant key. — [fixture: amz_apify.json, amz_iphone17pro.json]
- Flipkart spec values precede their labels in `__INITIAL_STATE__` (`label_1/label_2` = value, `label_0` = label). Naive "label then next text" parsing shifts every value by one field. — [fixture: fk_s26_512blk.html, fk_pdp.html]
- Flipkart Samsung "Model Number" granularity is inconsistent: base `SM-S948B` on the S26 Ultra and full `SM-S921EZAWINS` on the S24. Match on the base prefix. — [fixture: fk_s26_512blk.html, fk_pdp.html]

### Inferences
- **Phones, by platform**: Amazon→Croma/Flipkart matching for Samsung/OnePlus cannot rely on model codes, because Amazon lacks them. It must use brand + normalised model name + storage + RAM + colour. Croma↔Flipkart can join on the Samsung base code, with Croma's full suffix as a tie-breaker.
- **iPhones**: no RAM is available reliably. Amazon's 0.1 GB value is junk, and Apple does not market RAM. Key iPhones on (model name incl. Pro/Pro Max/Air/e, storage, colour) and set RAM = null. Never treat RAM mismatch as negative evidence for Apple.
- **TVs**: the model code is present on all three platforms and is the primary key. Size is a consistency check.

### Gaps
- There are no Croma or Flipkart iPhone fixtures, so whether those platforms show the Apple part number, A-number or RAM for iPhones is unverified.
- There are no Amazon TV fixtures other than LG and no Samsung/Sony TV fixtures on Flipkart/Amazon.

## 3. EAN/GTIN availability and free lookup sources

### Takeaway
Of the three, only Croma exposes EANs, and some of those are malformed. EAN is therefore a high-precision key when valid but cannot be the primary join. Free external GTIN lookup is weak for Indian phones/TVs. GS1 India's validation portal is free per single lookup. Open Icecat is free but limited to sponsoring brands. UPCitemdb publishes no guarantees.

### Cited Findings
- GS1 India's GTIN Validation service (powered by DataKart and "Verified by GS1") lets marketplaces and retailers validate GTINs with core attributes, and is free for individual GTIN search. — [GS1 India GTIN validation](https://gs1india.org/gtin-validation/)
- DataKart originally validated only India-issued GTINs, and about 15% of BigBasket's queries failed because the GTINs were issued abroad. "Verified by GS1" was added to cover global GTINs. — [GS1 UK on GS1 India](https://www.gs1uk.org/insights/news/GS1India-building-trust-and-boosting-efficiency-with-verified-product-data). Relevance: Samsung/LG EANs are Korean (880…), Sony Japanese (4548…) and OnePlus Chinese (692…) per the fixtures.
- Open Icecat: free registration, data sponsored by manufacturers, a Fair Use Policy applies, and GTIN-only lookup is supported (GTIN is unique across Icecat; one product may have several GTINs). Coverage is limited by brand/category, with 500+ sponsoring brands vs tens of thousands in the paid Full Icecat. — [Icecat JSON manual](https://www.iceclog.com/manual-for-icecat-json-product-requests/); [Icecat FAQ](https://iceclog.com/faq-for-merchants/)
- UPCitemdb: "The information is all provided as-is, with no guarantees on availability or accuracy." Plan limits are on devs.upcitemdb.com and were not read. — [UPCitemdb API explorer](https://www.upcitemdb.com/api/explorer)

### Inferences
- Use EAN as an exact-match accelerator only after check-digit validation. Different colours/storages have different EANs (fixture S26U: …852162 violet, …852193 sky blue, …852773 black, …852902 white), so EAN equality implies the same variant.
- The cost/benefit of external GTIN APIs is low here. Amazon and Flipkart do not expose EANs, so a GTIN→model service only helps enrich Croma, which already has model codes.

### Gaps
- Whether Open Icecat includes Samsung/Apple/LG phones and TVs with India-specific GTINs is untested (a free account is needed). Open Product Data / UPCitemdb coverage for Indian SKUs was not measured.

## 4. External reference catalogues (model code → canonical model/variant)

### Takeaway
The only clean, free, authoritative mapping is Apple's own model-number page (A-number → model, per region). GSMArena routes automated access through a TollBit paywall (pay-per-crawl), so it should not be scraped. Icecat is usable within fair use. For Samsung, firmware databases (SamMobile) confirm base-code+region existence but not colour/storage.

### Cited Findings
- Apple publishes per-model A-numbers by region for iPhone 17/Air/17 Pro/17 Pro Max (table in §1). — [Apple support 108044](https://support.apple.com/en-in/108044)
- `gsmarena.com/terms.php3` returned a 302 redirect to `tollbit.gsmarena.com`, i.e. bot traffic is redirected to TollBit's paid-access gateway. Per the constraints the redirect was not followed. — observed via fetch on 2026-11-12 ([gsmarena terms](https://www.gsmarena.com/terms.php3))
- SamMobile lists India (INS) firmware per base code (e.g. SM-A266B/INS), which confirms which base codes ship in India. — [SamMobile](https://www.sammobile.com/samsung/galaxy-a26-5g/firmware/SM-A266B/INS/)
- Icecat: see §3.

### Inferences
- Rather than relying on external catalogues, build an internal canonical table bootstrapped from Croma (model number + model series + RAM/storage/colour + EAN). Croma already holds the cross-reference that other catalogues would supply.

### Gaps
- PhoneDB, samsung.com/in, lg.com/in and sony.co.in were not fetched for ToS or bulk usability in this pass.

## 5. Attribute extraction approaches: regex vs NER vs LLM structured extraction

### Takeaway
LLM extraction reaches roughly 85–91% F1 on open product attribute benchmarks, about 5–10 points above pre-trained language model (PLM) baselines such as SU-OpenTag, AVEQA and MAVEQA. For this narrow schema (brand, model, storage, RAM, colour, size, model code), most fields are already structured on the platforms. The design should therefore be deterministic first (spec fields + regex), with a small-model LLM fallback constrained by JSON schema, enumerated values and evidence spans. The per-item cost is a fraction of a cent.

### Cited Findings
- WDC-PAVE (offers from 59 schema.org sites, 5 categories, manually verified extraction and normalisation values): GPT-4 reaches about 91% F1, roughly 10 points above SU-OpenTag, AVEQA and MAVEQA. — [Brinkmann, Baumann, Bizer, arXiv 2403.02130](https://arxiv.org/abs/2403.02130v4). Leaderboard figures: GPT-4 90.54, GPT-3.5 88.02, AVEQA 80.83, MAVEQA 65.1, SU-OpenTag 60.44 (unverified). — [PapersWithCode](https://www.paperswithcode.com/paper/using-llms-for-the-extraction-and)
- ExtractGPT (Brinkmann, Shraga, Bizer): GPT-4 has an average F1 of 85% with attribute descriptions and demonstrations, beating the best PLM baseline by 5 points. Llama-3-70B is nearly as good. Fine-tuned GPT-3.5 matches GPT-4 but generalises worse to unseen values. — summarised from search results for [arXiv 2403.02130 / ExtractGPT](https://www.emergentmind.com/articles/2403.02130). Settings differ, so 85 and 91 are not directly comparable.
- MAVE (Google, WSDM 2022): 2.2M Amazon products, 3M attribute-value annotations, 1,257 categories, multi-source profile (title, description, features, price, brand). It is "challenging … especially on zero-shot". — [arXiv 2112.08663](https://arxiv.org/abs/2112.08663); [Google Research](https://research.google/pubs/mave-a-product-dataset-for-multi-source-attribute-value-extraction/)
- Pricing (per million tokens, as of 2026-11-12):
  - Claude Haiku 5.5: $0.10 in / $0.50 out for prompts ≤100k tokens; cache hits $0.01.
  - Claude Haiku 4.5: $1 / $5; cache hits $0.10.
  - The Batch API is 50% off both input and output.
  - Source: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
  - Gemini 2.5 Flash-Lite: $0.10 / $0.40 (deprecated).
  - Gemini 2.5 Flash: $0.30 / $2.50. From 2026-12-01, calls to `gemini-2.5-flash` are routed to Gemini 3.5 Flash-Lite.
  - Gemini 3 Flash Preview: $0.50 / $3.00.
  - Gemini 3.6/3.8 Flash: $0.75 / $3.75.
  - Gemini batch pricing is 50% off, and a free tier exists, but free-tier data may be used by Google.
  - Source: [Google AI Studio pricing](https://aistudio.google.com/docs/pricing)

### Inferences
- **Cost per item** (assumes a compacted ~1,500-token input of title + spec table and ~150 output tokens; my arithmetic):
  - Claude Haiku 5.5 ≈ $0.00023
  - Claude Haiku 4.5 ≈ $0.0023
  - Gemini 2.5 Flash-Lite ≈ $0.00021
  - Gemini 3 Flash Preview ≈ $0.0012
  - Batch API halves each figure. At 10k items, even Haiku 4.5 costs about $23. Sending the full raw Flipkart HTML (≈1.6 MB) instead of compacted fields would cost about 100× more, so pre-extract the spec table first.
- **Hallucination controls**:
  - JSON-schema/tool-call output with enums for colour family, storage ∈ {64,128,256,512,1024} GB and RAM ∈ {4,6,8,12,16,24} GB, nullable everywhere. Explicitly allow `null` for iPhone RAM.
  - Require an `evidence` substring per field and verify it verbatim in the source text; reject the field if it is missing.
  - Feed title + structured fields before bullets, since bullets can name sibling models (the Pro/Pro Max trap).
  - Cross-validate the LLM output against the deterministic extract, and send disagreements to review.
- **Caching**: key LLM results by `(platform, item_id, hash(normalised input))`, so re-scrapes with unchanged specs cost nothing. Put the static schema/instructions in a cached prompt prefix. Note the minimum cacheable prompt length: the pricing page lists 286–588 tokens for Haiku, depending on model.
- Regex/NER alone is enough for storage/RAM/size and most model codes. An LLM adds most value for model-name canonicalisation (e.g. "S26 Ultra 5G" vs "Galaxy S26 Ultra") and colour marketing-name → family mapping.

### Gaps
- OpenAI GPT-4o-mini/GPT-5-mini pricing was not fetched. No benchmark specific to Indian electronics listings was found.

## 6. Unit/format normalisation

### Takeaway
All observed storage/RAM/size formats are regex-normalisable. The two hard parts are colour (marketing name vs family, misspellings) and model-name tiers (Pro vs Pro Max, Plus vs Ultra, "5G" suffix), which need token-level comparison rather than substring match.

### Cited Findings (fixtures)
- **Storage/RAM formats seen**:
  - "256 GB", "256GB", "1 TB" (Amazon variant names)
  - "12GB + 256GB", "12 GB RAM, 256 GB Storage" (Amazon variantAttributes)
  - "OnePlus 15 | 12GB+256GB |" (Amazon title)
  - "Memory: 12GB RAM, 256GB ROM" (Croma key_features)
  - "(12GB RAM, 256GB, Cobalt Violet)" (Croma title)
  - "(Black, 512 GB)" (Flipkart JSON-LD name; no RAM in the name)
  - "User Available Internal Memory = 479.2 GB", which is a decoy, not the marketed capacity (Flipkart)
  - [fixtures: amz_*.json, croma_*.json, fk_s26_512blk.html]
- **Screen size formats seen**:
  - "139 cm (55 inch)" (Flipkart)
  - "139 cms (55 inches)" (Amazon title)
  - "140 cm (55 inch)" / "139.7 cm (55 inch)" / "139 cm (55 inch)" (Croma titles for 55" sets)
  - "55 Inches" (Amazon attr)
  - "Screen Size in Inches = 55" (Croma)
  - Phones: "17.53 cm (6.9 inch)" (Flipkart) vs "6.88" (Croma) vs "6.9 Inches" (Amazon) for the same S26 Ultra
- **Colour formats seen**:
  - Marketing names: "Cosmic Orange", "Sand Storm", "Titanium Silverblue"
  - Croma typo: "Ultra Voilet"
  - Croma's normalised "Color" family, e.g. Sand Storm → WHITE, Ultra Violet → PURPLE
- **Apple naming**: title "Apple iPhone 17 Pro 256 GB: 15.93 cm (6.3″) …; Cosmic Orange" (colour after a semicolon at the end); Generic Name "iPhone 17 Pro". Pro vs Pro Max is distinguished by name token and by different A-numbers (A3523 vs A3526 in India).

### Inferences
- Normalise capacities to integer GB (TB×1024). Parse "X+Y"/"X GB RAM, Y GB (Storage|ROM)" with the smaller value as RAM. Ignore "User Available"/"Total Memory".
- Screen size: take the inch value in parentheses or an explicit inch field. Compare phones with a ±0.1" tolerance (6.88 vs 6.9) and TVs by integer inch; never compare on cm.
- Colour: compare normalised marketing names first, using lowercase, collapsed whitespace and Levenshtein ≤2 to absorb "Voilet"/"Violet". Fall back to the family (Croma "Color" or an LLM-mapped family) only as a weak signal, because families collide (a "Black" vs "Infinite Black" family match is not proof).
- Model-name tiers: tokenise and require exact equality of the tier-token set {pro, max, plus, ultra, air, mini, lite, fe, e, neo, prime}. "5G" is noise and should be dropped. This blocks "iPhone 17 Pro" ⊂ "iPhone 17 Pro Max" substring false positives.

### Gaps
- No fixture data for Xiaomi/vivo/realme naming quirks (e.g. "(8GB+128GB)"), or for Hindi/regional colour names.
