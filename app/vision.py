"""Photo check for listings without a shared code: does the listing photo show the same product and
colourway as the Amazon photo? Returns SAME / DIFFERENT / UNSURE; UNSURE without ANTHROPIC_API_KEY."""
from __future__ import annotations

import base64
import json
import os
import re

import httpx

from app.models import Candidate, SourceProduct

MODEL = "claude-sonnet-5-5"


def reply_text(msg) -> str:
    """The reply's text, skipping thinking blocks (a reply may start with one)."""
    return "".join(getattr(b, "text", "") for b in getattr(msg, "content", None) or [] if getattr(b, "type", "") == "text")


async def _img(client: httpx.AsyncClient, url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    try:
        r = await client.get(url)
    except httpx.HTTPError:
        return None
    ct = r.headers.get("content-type", "").split(";")[0]
    return (ct, base64.b64encode(r.content).decode()) if r.status_code == 200 and ct.startswith("image/") else None


async def same_product(src: SourceProduct, cand: Candidate) -> str:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "UNSURE"
    try:
        import anthropic
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as hc:
            a, b = await _img(hc, src.image), await _img(hc, cand.image)
        if not a or not b:
            return "UNSURE"
        async with anthropic.AsyncAnthropic() as ac:
            msg = await ac.messages.create(model=MODEL, max_tokens=150, messages=[{"role": "user", "content": [
                {"type": "text", "text": f"Listing A: {src.title} (colour {src.canon.colour})"},
                {"type": "image", "source": {"type": "base64", "media_type": a[0], "data": a[1]}},
                {"type": "text", "text": f"Listing B: {cand.title} (colour {cand.canon.colour})"},
                {"type": "image", "source": {"type": "base64", "media_type": b[0], "data": b[1]}},
                {"type": "text", "text": "Are A and B the exact same product: same design AND same colourway "
                 "(size ignored)? Compare logo, print, panels and colour. Reply only JSON "
                 '{"verdict":"SAME"|"DIFFERENT"|"UNSURE"}.'}]}])
        m = re.search(r"\{.*\}", reply_text(msg), re.S)
        v = json.loads(m.group(0)).get("verdict") if m else None
        return v if v in ("SAME", "DIFFERENT", "UNSURE") else "UNSURE"
    except Exception:
        return "UNSURE"


# ---------------------------------------------------------------- one-call photo check (2026-11-13)

ATTRS = ("neck", "sleeve", "colour", "logo", "stripes", "print")
# sneakers (reports/Sneaker cross store matching.md): rows 1-2 decide the model, 3-7 the colourway
SHOE_ATTRS = ("silhouette", "panels", "logo", "upper_colour", "accents", "sole", "laces")
PICK_MAX = 5
# photo rows that mirror a hard text check (neck/colour gates; a shoe's cut/colourway): a listing that
# differs on one of these is a different product, never a "closest option"
HARD_ATTRS = {"neck", "colour", "silhouette", "upper_colour"}


def attrs_for(cat) -> tuple[str, ...]:
    return SHOE_ATTRS if getattr(cat, "value", cat) == "sneaker" else ATTRS

_PICK_PROMPT = (
    "Image A is the product to find. Images 1-{n} are candidate listings from another store.\n"
    "For EACH candidate compare it with A on: neck/collar, sleeve, colour, logo (type and position), "
    "stripes/panels, print or graphic (design and placement). Size, model, pose and background don't matter.\n"
    "Mark each attribute 'same', 'different' or 'unclear' (unclear when it can't be seen).\n"
    "Then answer which candidate is the exact same product as A, or 'none', or 'unclear'.\n"
    "Reply with JSON only: {{\"table\": {{\"1\": {{\"neck\": ..., \"sleeve\": ..., \"colour\": ..., \"logo\": ..., "
    "\"stripes\": ..., \"print\": ...}}, ...}}, \"match\": <number>|\"none\"|\"unclear\", "
    "\"differences\": {{\"<number>\": \"<the specific difference>\"}}}}")

_SHOE_PROMPT = (
    "Image A is the shoe to find. Images 1-{n} are candidate listings from another store.\n"
    "For EACH candidate compare the shoe with A on: silhouette (cut, toe, height), panels (overlay layout, "
    "toe cap, heel tab), logo (type, position, its colour), upper_colour (base colour and material; sail/"
    "off-white vs pure white counts), accents (colour of each trim zone), sole (midsole shape and colour, "
    "gum vs white), laces (and eyelets). The colourway must match exactly: the same model in other colours "
    "(black/white vs white/black) is 'different'. Camera angle, size, pair vs single and background don't "
    "matter; the inner side may show a smaller logo.\n"
    "Mark each attribute 'same', 'different' or 'unclear' (unclear when it can't be seen).\n"
    "Then answer which candidate is the exact same product as A, or 'none', or 'unclear'.\n"
    "Reply with JSON only: {{\"table\": {{\"1\": {{\"silhouette\": ..., \"panels\": ..., \"logo\": ..., "
    "\"upper_colour\": ..., \"accents\": ..., \"sole\": ..., \"laces\": ...}}, ...}}, "
    "\"match\": <number>|\"none\"|\"unclear\", \"differences\": {{\"<number>\": \"<the specific difference>\"}}}}")


def small_image(url: str | None) -> str | None:
    """Store CDN URLs resized for the check (fewer tokens, faster): Amazon _SL500_, Myntra w_360,
    Flipkart 416px."""
    if not url:
        return url
    url = re.sub(r"\._[A-Z0-9_,]+_\.", "._SL500_.", url)  # m.media-amazon.com
    url = re.sub(r"(assets\.myntassets\.com/)(?:[a-z]_[^/]+/)?(v1/)?", r"\1w_360,q_80/v1/", url, count=1) \
        if "assets.myntassets.com" in url and "/v1/" not in url else url
    url = re.sub(r"/image/\d+/\d+/", "/image/416/416/", url)  # flixcart
    return url


def differences(res: dict, n: int, attrs: tuple[str, ...] = ATTRS) -> list[list[str]]:
    """Attributes the table marks 'different' for each of the n candidates (in ATTRS order)."""
    table = res.get("table") if isinstance(res, dict) else None
    table = table if isinstance(table, dict) else {}
    return [[a for a in attrs if str((table.get(str(i + 1)) or {}).get(a, "")).lower() == "different"]
            for i in range(n)]


def judge(res: dict, n: int, attrs: tuple[str, ...] = ATTRS) -> tuple[str, int | None]:
    """Accept the model's answer only when its own table backs it:
    match k → k has no 'different' (and some 'same') and every other candidate has a 'different';
    none → every candidate has a named 'different'. Anything else is 'unclear'."""
    table = res.get("table") if isinstance(res, dict) else None
    if not isinstance(table, dict):
        return "unclear", None
    rows = [{a: str((table.get(str(i + 1)) or {}).get(a, "unclear")).lower() for a in attrs} for i in range(n)]
    differs = [any(v == "different" for v in r.values()) for r in rows]
    clean = [not d and any(v == "same" for v in r.values()) for r, d in zip(rows, differs)]
    ans = res.get("match")
    if isinstance(ans, str) and ans.strip().isdigit():
        ans = int(ans)
    if isinstance(ans, int) and 1 <= ans <= n:
        k = ans - 1
        others_differ = all(differs[i] for i in range(n) if i != k)
        return ("match", k) if clean[k] and others_differ else ("unclear", None)
    if ans == "none" and all(differs):
        return "none", None
    return "unclear", None


async def pick(src: SourceProduct, cands: list[Candidate]) -> dict:
    """One vision call: Amazon photo + up to 5 candidate photos → attribute table + answer. {} on any
    failure or without ANTHROPIC_API_KEY (the caller treats {} as unclear)."""
    if not os.environ.get("ANTHROPIC_API_KEY") or not cands:
        return {}
    try:
        import anthropic
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as hc:
            imgs = [await _img(hc, small_image(u)) for u in [src.image] + [c.image for c in cands]]
        if not imgs[0] or not all(imgs[1:]):
            return {}
        content: list[dict] = [{"type": "text", "text": f"Image A: {src.title} (colour {src.canon.colour})"},
                               {"type": "image", "source": {"type": "base64", "media_type": imgs[0][0], "data": imgs[0][1]}}]
        for i, (c, im) in enumerate(zip(cands, imgs[1:]), 1):
            content += [{"type": "text", "text": f"Image {i}: {c.title} (colour {c.canon.colour})"},
                        {"type": "image", "source": {"type": "base64", "media_type": im[0], "data": im[1]}}]
        prompt = _SHOE_PROMPT if attrs_for(src.category) is SHOE_ATTRS else _PICK_PROMPT
        content.append({"type": "text", "text": prompt.format(n=len(cands))})
        async with anthropic.AsyncAnthropic() as ac:
            msg = await ac.messages.create(model=MODEL, max_tokens=900, messages=[{"role": "user", "content": content}])
        m = re.search(r"\{.*\}", reply_text(msg), re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}
