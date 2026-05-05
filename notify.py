"""
LNDg Notification Module

Supported backend:
  - Telegram : Bot API (sendMessage)

Settings are stored in the ``NotificationSettings`` DB model (singleton row).
"""

from datetime import datetime

import requests


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

    Returns a dict with key ``telegram`` (bool or None when disabled).
    """
    result = {"telegram": None}

    try:
        from gui.models import NotificationSettings  # import here to avoid circular deps
        cfg = NotificationSettings.load()
    except Exception as exc:
        print(f"{datetime.now().strftime('%c')} : [Notify] : Cannot load settings: {exc}")
        return result

    # Telegram
    if cfg.tg_enabled and cfg.tg_bot_token and cfg.tg_chat_id:
        result["telegram"] = _send_telegram(cfg.tg_bot_token, cfg.tg_chat_id, message)

    return result

