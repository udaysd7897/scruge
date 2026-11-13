"""User report 2026-11-13: iPhone 17 Pro Max B0FQFPHB1W read via the plain page had no colour ("Couldn't read
colour on Amazon"). The colour isn't in the spec tables, only in the variant picker: "Colour: Cosmic Orange"."""
from pathlib import Path

from app.extract import from_amazon
from app.sources.amazon_page import parse_amazon_page

FX = Path(__file__).parent / "fixtures"
URL = "https://www.amazon.in/dp/B0FQFPHB1W"


def test_inline_twister_selected_colour_and_size():
    item = parse_amazon_page((FX / "amz_page_iphone17pm.html").read_text(encoding="utf-8", errors="ignore"), URL)
    va = {a["key"]: a["value"] for a in item["variantAttributes"]}
    assert va["Colour"] == "Cosmic Orange" and va["Size"] == "1 TB"
    sp = from_amazon(item)
    assert sp.canon.colour == "Cosmic Orange" and sp.canon.storage_gb == 1024 and sp.missing_required == []


def test_classic_twister_selection():
    h = ('<div id="variation_color_name" class="a-section"><label class="a-form-label">Colour: </label>'
         '<span class="selection">Deep Blue</span></div>'
         '<div id="variation_size_name"><label>Size: </label><span class="selection"> 256 GB </span></div>')
    va = {a["key"]: a["value"] for a in parse_amazon_page(h, URL)["variantAttributes"]}
    assert va == {"Colour": "Deep Blue", "Size": "256 GB"}


def test_terabyte_storage_is_searched_as_tb():
    # Flipkart returns the Cosmic Orange 1 TB for "... 1 tb cosmic orange", nothing for "... 1024gb ..."
    from app.models import Platform
    from app.queries import ladder
    item = parse_amazon_page((FX / "amz_page_iphone17pm.html").read_text(encoding="utf-8", errors="ignore"), URL)
    assert ladder(from_amazon(item), Platform.FLIPKART)[0] == "apple iphone 17 pro max 1 tb cosmic orange"


def test_phone_without_storage_row_is_still_a_phone():
    # user report 2026-11-13: B0FQFV2XKS (17 Pro Max 256 GB) came out "unsupported": no breadcrumb, no
    # bestseller node and, unlike the 1 TB page, no "Memory Storage Capacity" row. The storage is in the
    # title / variant picker ("256 GB")
    from app.models import Category
    item = parse_amazon_page((FX / "amz_page_iphone17pm_256.html").read_text(encoding="utf-8", errors="ignore"),
                             "https://www.amazon.in/dp/B0FQFV2XKS")
    sp = from_amazon(item)
    assert sp.category == Category.PHONE
    assert (sp.canon.storage_gb, sp.canon.colour, sp.missing_required) == (256, "Deep Blue", [])
