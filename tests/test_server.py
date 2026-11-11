import json

from fastapi.testclient import TestClient

from app import server

EVENTS = [
    {"type": "progress", "platform": "croma", "message": "Searching Croma…"},
    {"type": "result", "data": {"platform": "croma", "outcome": "Not listed", "url": None, "reason": "x", "colour_fallback_note": None}},
    {"type": "done"},
]


def _patch(monkeypatch, gen):
    monkeypatch.setattr(server, "check", gen)


def _events(resp):
    return [json.loads(b[len("data: "):]) for b in resp.text.split("\n\n") if b.startswith("data: ")]


def test_stream(monkeypatch):
    async def fake(url):
        for e in EVENTS:
            yield e
    _patch(monkeypatch, fake)
    r = TestClient(server.app).get("/api/check", params={"url": "https://www.amazon.in/dp/X"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["cache-control"] == "no-cache"
    assert _events(r) == EVENTS


def test_blank_url():
    r = TestClient(server.app).get("/api/check", params={"url": "  "})
    ev = _events(r)
    assert ev[0]["type"] == "error" and ev[-1] == {"type": "done"}


def test_exception(monkeypatch):
    async def boom(url):
        yield EVENTS[0]
        raise RuntimeError("x")
    _patch(monkeypatch, boom)
    ev = _events(TestClient(server.app).get("/api/check", params={"url": "u"}))
    assert ev[1] == {"type": "error", "message": "Something went wrong. Please try again."}
    assert ev[-1] == {"type": "done"}


def test_index():
    r = TestClient(server.app).get("/")
    assert r.status_code == 200 and "<input" in r.text
