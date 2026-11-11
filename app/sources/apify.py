from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import httpx

from app.models import FetchStatus

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "apify"
# Cache-only mode (golden-set replays): a cache miss is an ERROR instead of a paid Apify call.
OFFLINE = os.environ.get("APIFY_OFFLINE") == "1"


def _cache_path(actor: str, payload: dict) -> Path:
    key = hashlib.sha1((actor + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


async def run_actor(
    client: httpx.AsyncClient, actor: str, payload: dict, timeout_s: int = 90
) -> tuple[FetchStatus, list[dict]]:
    path = _cache_path(actor, payload)
    try:
        if path.exists():
            items = json.loads(path.read_text())
            if items:
                return FetchStatus.OK, items
    except (OSError, ValueError):
        pass
    key = os.environ.get("APIFY_KEY")
    if OFFLINE or not key:
        return FetchStatus.ERROR, []
    url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?timeout={timeout_s}"
    try:
        r = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout_s + 15,
        )
        if r.status_code not in (200, 201):
            return FetchStatus.ERROR, []
        items = r.json()
    except (httpx.HTTPError, ValueError):
        return FetchStatus.ERROR, []
    if not isinstance(items, list):
        return FetchStatus.ERROR, []
    if not items:
        return FetchStatus.EMPTY, []
    if not all(isinstance(i, dict) for i in items):
        return FetchStatus.OK, items
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items))
    except OSError:
        pass
    return FetchStatus.OK, items
