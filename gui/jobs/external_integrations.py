from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import requests
from asgiref.sync import async_to_sync

MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"
AMBOSS_GRAPHQL_URL = "https://api.amboss.space/graphql"
_MEMPOOL_CACHE_TTL_SECONDS = 600
_AMBOSS_CACHE_TTL_SECONDS = 600
_AMBOSS_MAX_PUBKEYS_PER_REQUEST = 30

_mempool_cache: dict = {"timestamp": 0.0, "value": None}
_amboss_cache: dict = {}


@dataclass(frozen=True)
class FeeSignal:
    light: str
    label: str
    wait_window: str


async def fetch_mempool_recommended_fees_async() -> dict | None:
    """Fetch mempool fee recommendations with retry/backoff on HTTP 429."""
    delays = [0.4, 0.8, 1.6]
    for delay in delays:
        try:
            response = await asyncio.to_thread(
                requests.get,
                MEMPOOL_FEES_URL,
                timeout=8,
            )
        except Exception:
            return None
        if response.status_code == 200:
            return response.json()
        if response.status_code == 429:
            await asyncio.sleep(delay)
            continue
        return None
    return None


def _cache_valid(cache_timestamp: float, ttl_seconds: int) -> bool:
    return cache_timestamp > 0 and (time.time() - cache_timestamp) < ttl_seconds


def get_mempool_recommended_fees(*, enabled: bool) -> dict | None:
    """Return cached mempool fees when integration is enabled."""
    if not enabled:
        return None
    if _cache_valid(_mempool_cache["timestamp"], _MEMPOOL_CACHE_TTL_SECONDS):
        return _mempool_cache["value"]
    payload = async_to_sync(fetch_mempool_recommended_fees_async)()
    if payload is None:
        return _mempool_cache["value"]
    _mempool_cache["timestamp"] = time.time()
    _mempool_cache["value"] = payload
    return payload


def classify_fee_signal(payload: dict | None) -> FeeSignal | None:
    """Build a fee traffic-light signal and wait-window hint from mempool payload."""
    if not payload:
        return None
    try:
        hour_fee = int(payload.get("hourFee", 0))
    except (TypeError, ValueError):
        return None
    if hour_fee <= 10:
        return FeeSignal(light="🟢", label="low", wait_window="good_now")
    if hour_fee <= 30:
        return FeeSignal(light="🟡", label="medium", wait_window="watch")
    return FeeSignal(light="🔴", label="high", wait_window="wait")


def _amboss_cache_key(pubkeys: list[str]) -> str:
    return "|".join(sorted(pubkeys))


def get_amboss_peer_context(*, enabled: bool, api_key: str, pubkeys: list[str]) -> dict[str, dict]:
    """Fetch Amboss peer context for a bounded list of already known/evaluated peers."""
    if not enabled or not api_key.strip() or not pubkeys:
        return {}
    limited_pubkeys = sorted({p for p in pubkeys if p})[:_AMBOSS_MAX_PUBKEYS_PER_REQUEST]
    cache_key = _amboss_cache_key(limited_pubkeys)
    entry = _amboss_cache.get(cache_key)
    if entry and _cache_valid(entry["timestamp"], _AMBOSS_CACHE_TTL_SECONDS):
        return entry["value"]
    query = """
    query GetNodes($pubkeys: [String!]!) {
      getNodes(pubkeys: $pubkeys) {
        publicKey
        rank
        capacity
        channels
      }
    }
    """
    try:
        response = requests.post(
            AMBOSS_GRAPHQL_URL,
            json={"query": query, "variables": {"pubkeys": limited_pubkeys}},
            headers={"Authorization": f"Bearer {api_key.strip()}"},
            timeout=10,
        )
        if response.status_code != 200:
            return {}
        nodes = response.json().get("data", {}).get("getNodes", []) or []
    except Exception:
        return {}
    mapped = {
        str(item.get("publicKey", "")): {
            "rank": item.get("rank"),
            "capacity": item.get("capacity"),
            "channels": item.get("channels"),
        }
        for item in nodes
        if item.get("publicKey")
    }
    _amboss_cache[cache_key] = {"timestamp": time.time(), "value": mapped}
    return mapped
