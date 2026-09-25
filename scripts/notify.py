"""Telegram notifications for the research cycle. Reads TG_TOKEN / TG_CHAT_ID from env or ../.env."""
from __future__ import annotations

import os
from pathlib import Path

import requests

ENV = Path(__file__).resolve().parent.parent / ".env"


def load_env() -> None:
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def send(text: str, silent: bool = False) -> bool:
    load_env()
    tok, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not tok or not chat:
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=15,
                          json={"chat_id": chat, "text": text[:4000], "disable_notification": silent,
                                "disable_web_page_preview": True})
        return r.ok
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    import sys
    print("sent" if send(" ".join(sys.argv[1:]) or "vibe: test") else "not sent (check .env)")
