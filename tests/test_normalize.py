from app.normalize import (
    base_colour, clean_ean, colour_key, distinctive_words, is_accessory,
    model_base, norm_brand, norm_family, parse_gb, parse_ram_storage,
    screen_inches, split_style_code,
)


def test_norm_brand():
    assert norm_brand("SAMSUNG") == "samsung"
    assert norm_brand("Mi") == "xiaomi"
    assert norm_brand(None) is None


def test_norm_family():
    assert norm_family("Galaxy S26 Ultra 5G") == norm_family("galaxy s26 ultra") == "galaxy s26 ultra"
    assert norm_family("Galaxy S26+") == "galaxy s26 plus"
    assert norm_family("Galaxy S26") != norm_family("Galaxy S26 FE")
    assert norm_family("Galaxy S26 (2026)") == "galaxy s26"
    assert norm_family(None) is None


def test_parse_ram_storage():
    assert parse_ram_storage("Samsung Galaxy S26 Ultra 5G (Sky Blue, 12GB RAM, 512GB Storage)") == (12, 512)
    assert parse_ram_storage("8 GB RAM | 256 GB ROM") == (8, 256)
    assert parse_ram_storage("12GB + 512GB") == (12, 512)
    assert parse_ram_storage("256 GB + 8 GB") == (8, 256)  # smaller is RAM
    assert parse_ram_storage("8GB RAM + 8GB Virtual RAM, 128GB") == (8, 128)
    assert parse_ram_storage("(1 TB, 16GB RAM)") == (16, 1024)
    assert parse_ram_storage("nothing here") == (None, None)


def test_parse_gb():
    assert parse_gb("12GB") == 12
    assert parse_gb("512 GB") == 512
    assert parse_gb("1 TB") == 1024
    assert parse_gb(None) is None
    assert parse_gb("abc") is None


def test_screen_inches():
    assert screen_inches("55 inch") == 55
    assert screen_inches("139 cm (55 inch)") == 55
    assert screen_inches("138.71 cm") == 55
    assert screen_inches("164 cm") == 65
    assert screen_inches("6.88") == 7
    assert screen_inches("55") == 55
    assert screen_inches(None) is None


def test_model_base():
    assert model_base("SM-S948BZKCINS") == model_base("SM-S948B/DS") == model_base("SM-S948B") == "SM-S948"
    assert model_base("KD-55X80L") == "KD-55X80L"
    assert model_base(None) is None


def test_split_style_code():
    assert split_style_code("DV2789-100") == ("DV2789", "100")
    assert split_style_code("DV2789") == ("DV2789", None)
    assert split_style_code(None) == (None, None)


def test_colour_key():
    assert colour_key("BLACK") == colour_key("Black")
    assert colour_key("Titanium Black") != colour_key("Black")
    assert colour_key("  Sky   Blue ") == "sky blue"


def test_base_colour():
    assert base_colour("Navy Blue") == "navy"
    assert base_colour("White/Black-Volt") == "white"
    assert base_colour("Onyx Black") == "black"
    assert base_colour("Charcoal") == "grey"
    assert base_colour("Xyzzy") is None


def test_clean_ean():
    assert clean_ean("8806097852605N") == "8806097852605"
    assert clean_ean("8806097852606") is None
    assert clean_ean("123") is None
    assert clean_ean(None) is None


def test_is_accessory():
    assert is_accessory("Gello Back Camera Lens Glass Protector for Samsung Galaxy S26 Ultra 5G")
    assert is_accessory("SeriousShoppers Samsung S26 Ultra Panel with Logo Back")
    assert not is_accessory("Samsung Galaxy S26 Ultra 5G (Black, 512 GB)")


def test_distinctive_words():
    assert distinctive_words("Puma Men Essentials Logo Slim Fit Polo T-shirt Black", "puma") == {
        "essentials", "logo", "slim", "fit"}
