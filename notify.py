"""
LNDg Notification Module

Supports two backends:
  - Telegram  : Bot API (sendMessage)
  - NOSTR     : NIP-01 signed text-note (kind 1) published to WebSocket relays.
                Schnorr signing is implemented in pure Python (BIP-340) so no
                extra native libraries are required.

Settings are stored in the ``NotificationSettings`` DB model (singleton row).

Optional dependency:
  ``websocket-client`` is required for NOSTR relay connections.
  Install via:  pip install websocket-client
  Without it, Telegram notifications still work but NOSTR publishing is skipped.
"""

import hashlib
import json
import secrets
import time
from datetime import datetime

import requests

# Warn at import time if websocket-client is missing (NOSTR will be unavailable).
try:
    import websocket as _websocket_check  # noqa: F401
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    _WEBSOCKET_AVAILABLE = False
    print(
        f"{datetime.now().strftime('%c')} : [Notify] : "
        "Optional package 'websocket-client' not installed. "
        "NOSTR relay publishing will be disabled. "
        "Run: pip install websocket-client"
    )

# ---------------------------------------------------------------------------
# secp256k1 curve parameters (BIP-340 / NOSTR)
# ---------------------------------------------------------------------------
_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)


def _point_add(P1, P2):
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    if P1[0] == P2[0]:
        if P1[1] != P2[1]:
            return None
        lam = (3 * P1[0] * P1[0] * pow(2 * P1[1], _P - 2, _P)) % _P
    else:
        lam = ((P2[1] - P1[1]) * pow(P2[0] - P1[0], _P - 2, _P)) % _P
    x3 = (lam * lam - P1[0] - P2[0]) % _P
    return (x3, (lam * (P1[0] - x3) - P1[1]) % _P)


def _point_mul(P, n):
    R = None
    for i in range(256):
        if (n >> i) & 1:
            R = _point_add(R, P)
        P = _point_add(P, P)
    return R


def _tagged_hash(tag: str, msg: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + msg).digest()


def _privkey_to_xonly_pubkey(privkey: bytes) -> bytes:
    """Return the 32-byte x-only public key for *privkey*."""
    d = int.from_bytes(privkey, "big")
    point = _point_mul(_G, d)
    return point[0].to_bytes(32, "big")


def _schnorr_sign(msg: bytes, privkey: bytes) -> bytes:
    """BIP-340 Schnorr signature (deterministic with random aux bytes)."""
    aux_rand = secrets.token_bytes(32)
    d0 = int.from_bytes(privkey, "big")
    if not (1 <= d0 < _N):
        raise ValueError("NOSTR private key value is out of the valid range [1, N-1]")
    point = _point_mul(_G, d0)
    # negate key if Y is odd
    d = d0 if point[1] % 2 == 0 else _N - d0
    t = (d ^ int.from_bytes(_tagged_hash("BIP0340/aux", aux_rand), "big")).to_bytes(32, "big")
    rand = _tagged_hash("BIP0340/nonce", t + point[0].to_bytes(32, "big") + msg)
    k0 = int.from_bytes(rand, "big") % _N
    if k0 == 0:
        raise ValueError("NOSTR signature generation failed. Please try again or use a different private key.")
    R = _point_mul(_G, k0)
    k = k0 if R[1] % 2 == 0 else _N - k0
    e_bytes = R[0].to_bytes(32, "big") + point[0].to_bytes(32, "big") + msg
    e = int.from_bytes(_tagged_hash("BIP0340/challenge", e_bytes), "big") % _N
    return R[0].to_bytes(32, "big") + ((k + e * d) % _N).to_bytes(32, "big")


# ---------------------------------------------------------------------------
# NOSTR helpers
# ---------------------------------------------------------------------------

def nostr_pubkey_from_privkey(privkey_hex: str) -> str:
    """Return the hex x-only public key for a 32-byte hex private key."""
    return _privkey_to_xonly_pubkey(bytes.fromhex(privkey_hex)).hex()


def _build_nostr_event(privkey_hex: str, content: str, kind: int = 1) -> dict:
    """Create and sign a NIP-01 NOSTR event."""
    privkey = bytes.fromhex(privkey_hex)
    pubkey_hex = _privkey_to_xonly_pubkey(privkey).hex()
    created_at = int(time.time())
    tags: list = []
    # Canonical serialisation for event ID (NIP-01)
    serialised = json.dumps(
        [0, pubkey_hex, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    sig = _schnorr_sign(bytes.fromhex(event_id), privkey)
    return {
        "id": event_id,
        "pubkey": pubkey_hex,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig.hex(),
    }


def _publish_nostr_event(event: dict, relays: list, timeout: int = 8) -> dict:
    """
    Publish *event* to every relay in *relays* via WebSocket.

    Returns a dict { relay_url: True/False } with success status per relay.
    Falls back gracefully when *websocket-client* is not installed.
    """
    results: dict = {}
    if not _WEBSOCKET_AVAILABLE:
        print(f"{datetime.now().strftime('%c')} : [Notify] : websocket-client not installed; NOSTR publish skipped")
        for relay in relays:
            results[relay] = False
        return results

    import websocket
    payload = json.dumps(["EVENT", event])
    for relay in relays:
        try:
            ws = websocket.create_connection(relay.strip(), timeout=timeout)
            ws.send(payload)
            ws.close()
            results[relay] = True
            print(f"{datetime.now().strftime('%c')} : [Notify] : NOSTR event published to {relay}")
        except Exception as exc:
            results[relay] = False
            print(f"{datetime.now().strftime('%c')} : [Notify] : NOSTR relay error [{relay}]: {exc}")
    return results


# ---------------------------------------------------------------------------
# Telegram helper
# ---------------------------------------------------------------------------

def _send_telegram(bot_token: str, chat_id: str, message: str, timeout: int = 10) -> bool:
    """Send *message* via the Telegram Bot API."""
    # Basic sanity check: bot tokens look like NNN:AAA... (no spaces or slashes)
    if not bot_token or ':' not in bot_token or '/' in bot_token or ' ' in bot_token:
        print(f"{datetime.now().strftime('%c')} : [Notify] : Telegram bot token appears invalid")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=timeout,
        )
        ok = resp.status_code == 200 and resp.json().get("ok", False)
        if not ok:
            print(f"{datetime.now().strftime('%c')} : [Notify] : Telegram error: {resp.text}")
        return ok
    except Exception as exc:
        print(f"{datetime.now().strftime('%c')} : [Notify] : Telegram exception: {exc}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_notification(message: str) -> dict:
    """
    Send *message* via all enabled notification backends.

    Reads configuration from the ``NotificationSettings`` singleton in the DB.

    Returns a dict with keys ``telegram`` (bool) and ``nostr`` (list of relay
    results), both ``None`` when the respective backend is disabled.
    """
    result = {"telegram": None, "nostr": None}

    try:
        from gui.models import NotificationSettings  # import here to avoid circular deps
        cfg = NotificationSettings.load()
    except Exception as exc:
        print(f"{datetime.now().strftime('%c')} : [Notify] : Cannot load settings: {exc}")
        return result

    # Telegram
    if cfg.tg_enabled and cfg.tg_bot_token and cfg.tg_chat_id:
        result["telegram"] = _send_telegram(cfg.tg_bot_token, cfg.tg_chat_id, message)

    # NOSTR
    if cfg.nostr_enabled and cfg.nostr_privkey:
        relays = [r.strip() for r in cfg.nostr_relays.split(",") if r.strip()]
        if relays:
            try:
                event = _build_nostr_event(cfg.nostr_privkey, message)
                result["nostr"] = _publish_nostr_event(event, relays)
            except Exception as exc:
                print(f"{datetime.now().strftime('%c')} : [Notify] : NOSTR event build error: {exc}")
                result["nostr"] = {}

    return result
