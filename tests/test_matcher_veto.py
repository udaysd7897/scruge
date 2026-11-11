from app.matcher import veto
from app.models import Candidate, Canonical, Category, Platform

PHONE, TV, SNEAKER, APPAREL = Category.PHONE, Category.TV, Category.SNEAKER, Category.APPAREL


def cand(title="", **kw):
    kw.setdefault("brand", "samsung")
    return Candidate(platform=Platform.FLIPKART, url="http://x", title=title,
                     canon=Canonical(title=title, **kw), in_stock=True)


src = Canonical(brand="samsung", family="galaxy s26 ultra", ram_gb=12, storage_gb=512, colour="Black")


def test_phone_vetoes():
    assert veto(src, cand(family="galaxy s26 ultra", ram_gb=12, storage_gb=256, colour="Black"), PHONE) == "storage 256≠512"
    assert veto(src, cand(family="galaxy s26 plus", ram_gb=12, storage_gb=512), PHONE) == "family"
    assert veto(src, cand(brand="blackzone", family="bz s26 ultra", title="BlackZone BZ S26 Ultra (White, 128 GB)"), PHONE) == "brand"
    assert veto(src, cand(title="Gello Back Camera Lens Glass Protector samsung galaxy s26 ultra 5g", brand="samsung"), PHONE) == "accessory"
    assert veto(src, cand(family="galaxy s26 ultra", ram_gb=12, storage_gb=512, colour="Sky Blue"), PHONE) is None
    assert veto(src, cand(family="galaxy s26 ultra", model_code="SM-S948B", ram_gb=12, storage_gb=512), PHONE) is None
    assert veto(src, cand(family="galaxy s26 ultra", ram_gb=8, storage_gb=512), PHONE) == "ram 8≠12"


def test_tv():
    tv = Canonical(brand="sony", family="bravia 3", model_code="K-55S30", screen_in=55)
    assert veto(tv, cand(brand="sony", family="bravia 3", model_code="K-65S30", screen_in=65), TV) is not None
    assert veto(tv, cand(brand="sony", family="bravia 3", screen_in=65), TV) == "screen size"
    assert veto(tv, cand(brand="sony", family="bravia 3", screen_in=55.5), TV) is None


def test_sneaker_apparel():
    shoe = Canonical(brand="nike", family="air max 270", base_colour="white", style_code="DV2789-100")
    assert veto(shoe, cand(brand="nike", family="air max 270", base_colour="black"), SNEAKER) == "colour"
    assert veto(shoe, cand(brand="nike", family="air max 270", base_colour="white", style_code="DV2789-001"), SNEAKER) == "style code"
    polo = Canonical(brand="puma", product_type="polo", base_colour="black", title="Puma Men Essentials Logo Slim Fit Polo Black")
    assert veto(polo, cand(brand="puma", product_type="polo", base_colour="black", title="Puma Men Graphic Regular Fit Polo Black"), APPAREL) == "distinctive words"
    assert veto(polo, cand(brand="puma", product_type="polo", base_colour="black", title="PUMA Essentials Logo Slim Fit Polo T-Shirt", pack_count=2), APPAREL) == "pack count"
    assert veto(polo, cand(brand="puma", product_type="tee", base_colour="black"), APPAREL) == "type"
    assert veto(polo, cand(brand="puma", product_type="polo", base_colour="black", title="PUMA Essentials Logo Slim Fit Polo T-Shirt"), APPAREL) is None


def test_fix_round_1():
    s = Canonical(brand="nike", family="air max 270", base_colour="white",
                  title="Nike Air Max 270 Men White Running Shoes Breathable Mesh Lightweight")
    assert veto(s, cand(brand="nike", family="air max 270", base_colour="white", title="Nike Air Max 270 Sneakers"), SNEAKER) is None
    polo = Canonical(brand="puma", product_type="polo", base_colour="black", title="Puma Essentials Logo Slim Fit Polo Black")
    assert veto(polo, cand(brand="puma", product_type="polo", base_colour="black",
                           title="PUMA Essentials Logo Slim Fit Polo T-Shirt (Pack of 2)"), APPAREL) == "pack count"
