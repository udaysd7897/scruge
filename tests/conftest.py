import pytest


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    """Tests simulate failures; don't actually wait between retries."""
    from app.sources import http
    monkeypatch.setattr(http, "BACKOFF", (0, 0))
