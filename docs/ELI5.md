# How the matcher works (explained like you're 5)

## The toy shop game

Imagine you have a toy in your hand. Your friend says: "Go to the other toy shops
and tell me if they have **this exact toy**, and if you can take one home today."

At every shop there is a big pile of toys that *look* a bit like yours. Some are
the same toy in a different colour. Some are a bigger box. Some are a cheap copy.
Some are not even toys, just a sticker for the toy.

So you check each toy in the pile, one by one, and ask three questions:

1. **Same maker?** Is it Samsung, like mine? (Not "BlackZone", not a phone case.)
2. **Same name?** Is it a "Galaxy S26 Ultra", like mine? (Not an "S26", not an "S26 FE".)
3. **Same important detail?** Every kind of toy has one detail that really matters:
   - **Phones:** how much memory it has (like 12GB / 512GB). We also check the colour.
   - **TVs:** how big the screen is (a 55-inch TV is not a 65-inch TV) and the model number on the box. If the box has no model number, we can only say "maybe".
   - **Sneakers:** the colour (white shoes are not burgundy shoes).
   - **T-shirts, polos, jerseys:** the colour, the kind of shirt, how many come in the pack, and the special words in its name.

If a toy fails **any** question, we put it back. We don't argue with it.

## If we're not sure, we say so

Sometimes two toys are left and they look equally right. Sometimes the label is
smudged, so we can't read the memory size. Then we don't guess. We say
**"Possible match – verify"** and show you the toy, so you can look yourself.

Pointing at the wrong toy is the worst thing we can do. Saying "I'm not sure" is fine.

## A real example: the Galaxy S26 Ultra

You bring a **Samsung Galaxy S26 Ultra, 12GB / 512GB, Sky Blue** from Amazon.

**Flipkart** shows us 10 things:
- 6 are back panels (one has a camera ring). They're phone covers, not phones. Out.
- 3 are the right phone in Black, White and Cobalt Violet. Wrong colour. Out.
- **1 is left**: S26 Ultra, 12GB / 512GB, Sky Blue. The shop says you can buy it, so the answer is **In stock**, with the link.

**Croma** shows us 8 things: 4 plain "Galaxy S26" phones (wrong name), 2 that are
the S26 Ultra but only 256GB (wrong memory), and 2 that are exactly our phone.
Two of the same? We read the **barcode** on each box. Both have the same barcode,
so it's really **one toy put on the shelf twice**. We show just one of them: **In stock**.

## "Couldn't check" is not "Not listed"

- **Not listed** means: we looked at the whole pile, and your toy isn't there.
- **Couldn't check** means: the shop's door was locked, or the shopkeeper didn't answer in time.
  We never saw the pile, so we can't say the toy isn't there.

Saying "they don't have it" when we never looked would be a fib. So we say
"Couldn't check" instead.

---

## For grown-ups

1. **Read the source.** The Amazon link is normalised to `amazon.in/dp/<ASIN>` (short links are followed) and fetched through the Apify Amazon actor. We detect the category from breadcrumbs/title and build a canonical record: brand, family, RAM/storage, screen size, model number (TVs), colour → base colour, product type, pack count.
2. **Search each platform with a query ladder.** We search the model code first, then brand + family + key attributes, then brand + family, and stop at the first rung that yields a match or a close call. Flipkart and Myntra are plain HTTPS; Croma goes through an Apify actor because direct access is bot-protected.
3. **Extract the same canonical record** from every candidate: Flipkart product pages (JSON-LD + spec rows), the Croma `specs` dict, Myntra's embedded search JSON.
4. **Apply hard vetoes.** Accessory, a different brand, family or model code, different RAM or storage, a screen more than 1" off, a different style code, base colour, product type or pack count, or too little overlap in the distinctive words of the title (apparel). Any veto drops the candidate. A TV is confirmed only when both sides show the same model number. Without one, the best answer is "Possible match".
5. **Phones and TVs use strict colour.** We use only the exact source colour. If the platform has none in that colour, we may show another colour with a note. A listing with no visible colour next to other colours gives "Possible match".
6. **Score the survivors** (identity code/EAN 0.40, exact colour 0.25, title similarity 0.20, completeness 0.15). The score only ranks the survivors; it never accepts a candidate on its own. If the top two are within 0.15, the result is a tie, unless all tied listings share an EAN or full model code, in which case they are one product.
7. **Optional LLM tie-break.** Only when `ANTHROPIC_API_KEY` is set, and only on a tie between survivors, Claude may pick one. Otherwise the answer stays "Possible match – verify".
8. **Map to a state.** In stock / Out of stock (with link and a "Matched on …" reason), Not listed (with "N candidates checked, none had …"), Possible match – verify, or Couldn't check (blocked, error or timeout). A failed fetch never becomes "Not listed".
