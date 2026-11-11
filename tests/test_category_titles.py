"""Amazon sometimes returns no breadcrumbs (iPhone 17 Pro B0FQG1LPVF, 2026-11-12): the title alone must
identify the phone, while accessories naming a phone stay unsupported."""
import json
from pathlib import Path

import pytest

from app.extract import detect_category, from_amazon
from app.models import Category, Platform
from app.queries import ladder

FX = Path(__file__).parent / "fixtures"


def test_iphone_without_breadcrumbs_is_a_phone():
    sp = from_amazon(json.loads((FX / "amz_iphone17pro.json").read_text())[0])
    assert sp.category == Category.PHONE
    assert (sp.canon.brand, sp.canon.family, sp.canon.storage_gb) == ("apple", "iphone 17 pro", 256)
    assert sp.canon.colour == "Cosmic Orange"
    assert sp.missing_required == []  # Apple doesn't publish RAM
    assert "apple iphone 17 pro 256gb cosmic orange" in ladder(sp, Platform.FLIPKART)


@pytest.mark.parametrize("title", [
    "Apple iPhone 17 Pro 256 GB: 15.93 cm (6.3″) Display",
    "Samsung Galaxy S26 Ultra 5G (Black, 12GB RAM, 512GB Storage)",
    "Samsung Galaxy Z Fold7 5G (Blue Shadow, 12GB RAM, 256GB)",
    "Google Pixel 10 Pro (Obsidian, 16GB RAM, 256GB)",
    "OnePlus 15 | 12GB+256GB | Infinite Black",
    "Redmi Note 15 Pro 5G (8GB RAM, 256GB)",
    "Nothing Phone (3a) 5G (Black, 8GB RAM, 128GB)",
])
def test_phone_titles(title):
    assert detect_category("", title) == Category.PHONE


@pytest.mark.parametrize("title", [
    "Spigen Ultra Hybrid Back Cover Case for iPhone 17 Pro",
    "Tempered Glass Screen Protector for Samsung Galaxy S26 Ultra",
    "Apple Watch Series 11",
])
def test_non_phone_titles(title):
    assert detect_category("", title) == Category.UNSUPPORTED
