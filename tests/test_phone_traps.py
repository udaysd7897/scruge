"""Phone data traps seen in real captures (design report 2026-11-12)."""
from app.normalize import parse_gb, parse_ram_storage


def test_placeholder_ram_is_unknown_not_zero():
    # Amazon iPhone productOverview: "RAM Memory Installed Size = 0.1 GB"
    assert parse_gb("0.1 GB") is None
    assert parse_gb("512 MB") is None
    assert parse_gb("8 GB") == 8 and parse_gb("1 TB") == 1024


def test_user_available_storage_is_ignored():
    # Flipkart: "User Available Internal Memory 479.2 GB" next to "Internal Storage 512 GB"
    assert parse_ram_storage("User Available 479.2 GB") == (None, None)
    assert parse_ram_storage("12 GB RAM | 512 GB ROM | User Available 479.2 GB") == (12, 512)
