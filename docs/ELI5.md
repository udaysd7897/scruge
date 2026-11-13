# How the matcher works (explained like you're 5)

## The toy shop game

You are holding a toy. Your friend says: "Go to the other toy shops and tell me if
they have **this exact toy**, and if I can take one home today."

Every shop has a big pile of toys that *look* a bit like yours. Some are the same toy in
another colour. Some come in a bigger box. Some are just the sticker for the toy.

So you look at each toy in the pile and ask:

1. **Same maker?** (Samsung, not "BlackZone".)
2. **Same name?** (a "Galaxy S26 Ultra", not an "S26".)
3. **Same important detail?** Every kind of toy has one thing that really matters:
   - **Phones:** how much memory (12GB / 512GB), and the colour.
   - **TVs:** how big the screen is, and the model number on the box.
   - **Sneakers and T-shirts:** the secret code printed on the tag, if both shops show it.
     If not, the colour, the kind of shirt, how many are in the pack, and the special words.

If a toy fails **any** question, it goes back on the pile. No arguing.

## The secret code on the tag

Shops love to write the toy's name in their own way. Look at one Puma T-shirt:

- Amazon calls it "Puma Men Polyester Solid Regular Fit T-Shirt"
- Flipkart calls it "PUMA M Train All Day ESSENTIAL Tee"
- Myntra calls it "Puma Train All Day Tee"

Three different names! But on the tag inside, all three say **52885601**. Same secret
code means same toy, so we don't fuss about the names. (And if two tags have *different*
codes, it is a different toy, even if the names look alike.)

## Same name, different toy

A phone called "Galaxy S26 Ultra" with **256GB** is *not* the "Galaxy S26 Ultra" with **512GB**.
Same name, different toy. So memory has to match too.

## If we're not sure, we say so

Sometimes two toys look equally right. Sometimes a tag has no code (Myntra never prints one).
Then we don't guess. We check more clues: Is the price on the box the same? Does the box name the
same factory? Does a picture of the toy look the same? Only if everything fits do we say yes.
Otherwise we say **"Possible match - verify"** and show you the toy so you can look yourself.

Pointing at the wrong toy is the worst thing we can do. Saying "I'm not sure" is fine.

## "Couldn't check" is not "Not listed"

- **Not listed:** we looked through the whole pile and your toy isn't there.
- **Couldn't check:** the shop door was locked, or the shopkeeper took too long. We never saw the
  pile, so we can't say the toy isn't there. (Same if some boxes wouldn't open.)

Saying "they don't have it" when we never looked would be a fib.

---

## For grown-ups

- **Reading Amazon:** the product page is fetched with a plain request first; only if it is
  blocked or unreadable do we fall back to the Apify Amazon actor (needs `APIFY_KEY`). We never
  bypass bot checks. Category comes from Amazon's own signals: breadcrumb, bestseller browse node,
  "Item Type Name", then a spec fingerprint (not model-name lists).
- **Canonical record** per listing: brand, model line, RAM/storage (phones), screen size and model
  number (TVs), colour, product type, pack count, gender, MRP, manufacturer and brand style code
  (Amazon Style Number / Item model number / Part Number; Flipkart Style Code / Article Number).
- **Query ladder:** model code, then brand + name + key attributes, then brand + name. For apparel
  the brand's official name (Puma style code looked up on in.puma.com; Puma only) and Amazon's
  Model Name are tried first.
- **Sources:** Flipkart over plain HTTPS (search, product pages, then sibling variants of the top
  hits); Myntra over plain HTTPS (embedded search JSON); Croma through Apify, capped at 5 results.
- **Hard vetoes:** accessory, brand, gender, model line (phones/TVs), model code (TVs: size +
  normalised code), RAM, storage, screen size (>1"), product type, different style code, colour,
  pack count, and too little overlap in distinctive title words (only when no shared style code).
- **Phones use strict colour;** TV colour is ignored. Score (identity 0.40, colour 0.25, title
  0.20, completeness 0.15) only ranks survivors; ties within 0.15 are "Possible match" unless the
  listings share an EAN or model code, or an optional Claude tie-break (`ANTHROPIC_API_KEY`) picks one.
- **No shared code (Myntra apparel):** matched by name only is never enough. `confirm.py` requires
  equal MRP, the same manufacturer on the Myntra product page, and a SAME verdict from a photo
  comparison (needs `ANTHROPIC_API_KEY`), with exactly one survivor passing. Otherwise "Possible match".
- **Closest options:** when listings pass every hard check but the photo check shows none has the same
  design, the status stays "Not listed" and up to 3 closest listings are shown under it, fewest
  differences first, each with what differs (e.g. "logo, print differ"). If nothing passed the hard
  checks, nothing is shown: a wrong brand, neck or colour is never offered as "close".
- **States:** In stock / Out of stock (link + "Matched on ..."), Not listed, Possible match - verify,
  Couldn't check (blocked, error or timeout: Croma 90 s, Flipkart 45 s, Myntra 20 s). A failed fetch
  never becomes "Not listed".
- **Known gaps:** brands whose style code differs per store (Van Heusen) can be wrongly rejected;
  Amazon bot checks and exhausted Apify credit (as of 2026-11-13) cause "Couldn't check"; the golden
  set is small. See the README.
