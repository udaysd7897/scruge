"""Category comes from what Amazon itself says (breadcrumb, browse node, Item Type Name) and, when that is
missing, from a spec fingerprint — never from a list of phone model names (design report 2026-11-12).
The iPhone 17 Pro capture (B0FQG1LPVF) has no breadcrumb, no bestseller rank and no Item Type Name."""
import json
from pathlib import Path

from app.extract import _TITLE_RULES, amazon_category, from_amazon
from app.models import Category, Platform
from app.queries import ladder

FX = Path(__file__).parent / "fixtures"


def item(**kw):
    base = {"title": "Something", "breadCrumbs": "", "attributes": [], "productOverview": [], "bestsellerRanks": None}
    base.update(kw)
    return base


def attrs(**kv):
    return [{"key": k.replace("_", " "), "value": v} for k, v in kv.items()]


def test_iphone_without_breadcrumbs_is_a_phone_by_specs():
    sp = from_amazon(json.loads((FX / "amz_iphone17pro.json").read_text())[0])
    assert sp.category == Category.PHONE
    assert (sp.canon.brand, sp.canon.family, sp.canon.storage_gb) == ("apple", "iphone 17 pro", 256)
    assert sp.missing_required == []
    assert "apple iphone 17 pro 256gb cosmic orange" in ladder(sp, Platform.FLIPKART)


def test_no_phone_model_names_in_title_rules():
    pattern = " ".join(rx.pattern for _, rx in _TITLE_RULES).lower()
    for name in ("iphone", "galaxy", "pixel", "oneplus", "redmi"):
        assert name not in pattern


def test_store_signals():
    assert amazon_category(item(attributes=attrs(Item_Type_Name="Smartphone"))) == Category.PHONE
    assert amazon_category(item(bestsellerRanks=[{"url": "https://www.amazon.in/gp/bestsellers/electronics/1805560031/ref=x"}])) == Category.PHONE
    assert amazon_category(item(attributes=attrs(Item_Type_Name="NANO 4K UHD AI TV"))) == Category.TV
    assert amazon_category(item(breadCrumbs="Electronics > Televisions > Smart Televisions")) == Category.TV


def test_spec_fingerprints():
    phone = item(title="Foo X1 256 GB", productOverview=attrs(Operating_System="Android 16", Memory_Storage_Capacity="256 GB"),
                 attributes=attrs(Item_Weight="190 g"))
    assert amazon_category(phone) == Category.PHONE
    tablet = item(title="Foo Tab", productOverview=attrs(Operating_System="Android 16", Memory_Storage_Capacity="256 GB"),
                  attributes=attrs(Item_Weight="480 g"))
    assert amazon_category(tablet) == Category.UNSUPPORTED
    tv = item(title="Foo 139 cm (55 inches) 4K", attributes=attrs(HDMI_Ports="3", Tuner_Type="Digital"))
    assert amazon_category(tv) == Category.TV


def test_accessories_stay_unsupported():
    assert amazon_category(item(title="Spigen Ultra Hybrid Back Cover Case for iPhone 17 Pro")) == Category.UNSUPPORTED
    assert amazon_category(item(title="Tempered Glass Screen Protector for Galaxy S26 Ultra",
                                productOverview=attrs(Operating_System="Android"))) == Category.UNSUPPORTED
