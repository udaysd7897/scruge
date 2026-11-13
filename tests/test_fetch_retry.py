"""fetch retries transient failures (network errors, 429/5xx) with backoff; real answers return at once."""
import httpx

from app.models import FetchStatus
from app.sources import http


async def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(http, "BACKOFF", (0, 0))
    calls = []
    def h(req):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("slow")
        if len(calls) == 2:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, text="<html>" + "x" * 30000)
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        st, body = await http.fetch(c, "https://example.com/p")
    assert st == FetchStatus.OK and len(calls) == 3


async def test_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(http, "BACKOFF", (0, 0))
    calls = []
    def h(req):
        calls.append(1)
        raise httpx.ReadTimeout("slow")
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        st, _ = await http.fetch(c, "https://example.com/p")
    assert st == FetchStatus.ERROR and len(calls) == 3


async def test_no_retry_on_normal_answer(monkeypatch):
    monkeypatch.setattr(http, "BACKOFF", (0, 0))
    calls = []
    def h(req):
        calls.append(1)
        return httpx.Response(404, text="nope")
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        await http.fetch(c, "https://example.com/p")
    assert len(calls) == 1
