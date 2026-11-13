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


async def test_myntra_short_attempts_more_retries():
    # 2026-11-13: Myntra stalls on and off (ReadTimeout). One 20 s attempt x 3 used up the 60 s budget; it
    # normally answers in ~1 s, so: 8 s attempts, 4 tries, a fresh try usually goes through
    from app.sources import myntra
    calls, limits = [], []
    def h(req):
        calls.append(1)
        limits.append(req.extensions["timeout"]["read"])
        if len(calls) < 4:
            raise httpx.ReadTimeout("stalled")
        return httpx.Response(200, text="<html>" + "x" * 30000)
    async with httpx.AsyncClient(transport=httpx.MockTransport(h), timeout=20) as c:
        st, _ = await myntra.myntra_fetch(c, "https://www.myntra.com/x")
    assert st == FetchStatus.OK and len(calls) == 4 and set(limits) == {myntra.ATTEMPT_TIMEOUT}


async def test_myntra_gives_up_after_four_tries():
    from app.sources import myntra
    calls = []
    def h(req):
        calls.append(1)
        raise httpx.ReadTimeout("stalled")
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        st, _ = await myntra.myntra_fetch(c, "https://www.myntra.com/x")
    assert st == FetchStatus.ERROR and len(calls) == 4


async def test_other_stores_keep_client_timeout_and_three_tries():
    calls, limits = [], []
    def h(req):
        calls.append(1)
        limits.append(req.extensions["timeout"]["read"])
        raise httpx.ReadTimeout("stalled")
    async with httpx.AsyncClient(transport=httpx.MockTransport(h), timeout=20) as c:
        st, _ = await http.fetch(c, "https://www.flipkart.com/x")
    assert st == FetchStatus.ERROR and len(calls) == 3 and set(limits) == {20}
