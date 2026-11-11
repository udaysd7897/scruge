import json
from pathlib import Path

from app.extract import (detect_category, from_amazon, from_croma, from_flipkart_page,
                         from_myntra_search, missing_required)
from app.models import Canonical, Category
from app.normalize import colour_key

FX = Path(__file__).parent / "fixtures"


def read(n):
    return (FX / n).read_text()


def test_amazon():
    item = next(i for i in json.loads(read("amz_apify.json")) if i["asin"] == "B0GL8GXNTS")
    sp = from_amazon(item)
    assert sp.category == Category.PHONE
    assert (sp.canon.brand, sp.canon.family, sp.canon.ram_gb, sp.canon.storage_gb,
            colour_key(sp.canon.colour)) == ("samsung", "galaxy s26 ultra", 12, 512, "sky blue")
    assert sp.missing_required == []


def test_croma():
    c = from_croma(next(i for i in json.loads(read("croma_apify.json")) if str(i["item_id"]) == "327249"))
    assert (c.canon.model_code, c.canon.ram_gb, c.canon.storage_gb, c.canon.ean, c.in_stock) == (
        "SM-S948BZKCINS", 12, 512, "8806097852605", True)
    assert c.canon.family == "galaxy s26 ultra"


def test_flipkart():
    [fk] = from_flipkart_page(read("fk_s26_512blk.html"),
        "https://www.flipkart.com/samsung-galaxy-s26-ultra-5g-black-512-gb/p/itmf4799d3841c43?pid=MOBHKGAPBMXRGGXZ")
    assert (fk.canon.model_code, fk.canon.ram_gb, fk.canon.storage_gb, colour_key(fk.canon.colour),
            fk.in_stock, fk.price, fk.variant_group) == ("SM-S948B", 12, 512, "black", True, 159999,
                                                          "itmf4799d3841c43")


def test_myntra():
    ms = from_myntra_search(read("my_search.html"))
    assert len(ms) == 50 and ms[0].canon.brand == "nike" and ms[0].canon.base_colour == "white"
    assert ms[0].in_stock is True
    assert ms[0].url.startswith("https://www.myntra.com/sports-shoes/nike/")


def test_category_and_missing():
    assert detect_category(None, "Puma Men Polo T-shirt") == Category.APPAREL
    assert detect_category(None, "Sony Bravia 139 cm (55 inches) 4K Ultra HD Smart LED Google TV K-55XR70") == Category.TV
    assert detect_category(None, "Prestige Pressure Cooker 5L") == Category.UNSUPPORTED
    assert detect_category("Electronics > Smartphones", "x") == Category.PHONE
    assert missing_required(Canonical(brand="samsung", family="galaxy s26 ultra", ram_gb=12, colour="Black"),
                            Category.PHONE) == ["storage_gb"]
    assert missing_required(Canonical(brand="sony", model_code="K-55XR70", screen_in=55), Category.TV) == []


def test_model_line():
    from app.normalize import model_line
    assert model_line("Nike Downshifter 14 Women's Road Running Shoe", "nike") == "downshifter 14"
    assert model_line("Nike Air Max 270 Men's Shoes White/Black", "nike") == "air max 270"


def test_myntra_family_clean():
    assert from_myntra_search(read("my_search.html"))[0].canon.family == "downshifter 14"


def test_accessory_breadcrumbs():
    assert detect_category("Electronics > Mobiles & Accessories > Mobile Accessories > Mobile Phone Cases",
                          "Spigen case for Galaxy S26") == Category.UNSUPPORTED
    assert detect_category("Electronics > TV & Home Theater Accessories > Wall Mounts", "TV wall mount") == Category.UNSUPPORTED
    assert detect_category("Electronics > Mobiles & Accessories > Smartphones & Basic Mobiles > Smartphones",
                          "x") == Category.PHONE


def _golden_amz(asin):
    return next(i for i in json.loads(read("amz_golden.json")) if i["asin"] == asin)


def test_amazon_family_pipe_separated_title():
    # "OnePlus 15 | 12GB+256GB | Infinite Black | India's First ..." has no "(": family must stop at "|"
    sp = from_amazon(_golden_amz("B0FTR5NGHJ"))
    assert (sp.canon.brand, sp.canon.family, sp.canon.ram_gb, sp.canon.storage_gb, sp.canon.colour) == (
        "oneplus", "15", 12, 256, "Infinite Black")
