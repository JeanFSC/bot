"""
Fire-and-forget Telegram notifications for MT5 bot events.

Setup in .env or Windows environment variables:
    MT5_TELEGRAM_TOKEN=123456789:AABBccdd...
    MT5_TELEGRAM_CHAT_ID=987654321

If either variable is missing, notifications are disabled silently. Event
messages stay ASCII so Windows service logs cannot crash on console encoding.
"""
from __future__ import annotations

import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional

_log = logging.getLogger("mt5_bot.notifier")
_MAX_LEN = 4096


def _credentials() -> tuple[str, str]:
    token = os.getenv("MT5_TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("MT5_TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def _send_blocking(text: str) -> None:
    token, chat_id = _credentials()
    if not token or not chat_id:
        return

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text[:_MAX_LEN],
            "parse_mode": "Markdown",
        }
    ).encode("utf-8")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            _log.debug("Telegram OK: %s", resp.status)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:200]
        if exc.code == 403 and "bots can't send messages to bots" in body:
            _log.warning(
                "Telegram HTTP 403: MT5_TELEGRAM_CHAT_ID points to a chat the bot cannot message. "
                "Use Jean's numeric user chat_id, a group/channel id where the bot is a member, "
                "or disable MT5_TELEGRAM_* until fixed."
            )
        else:
            _log.warning("Telegram HTTP %s: %s", exc.code, body)
    except Exception as exc:
        _log.debug("Telegram send failed (non-blocking): %s", exc)


def notify(text: str) -> None:
    """Send a Telegram message in a daemon thread; never blocks the caller."""
    threading.Thread(target=_send_blocking, args=(text,), daemon=True).start()


def is_enabled() -> bool:
    token, chat_id = _credentials()
    return bool(token and chat_id)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M UTC")


def bot_started(symbol: str, timeframe: str, magic: int) -> None:
    notify(
        f"[BOT STARTED]\n"
        f"`{symbol}` {timeframe} | Magic `{magic}` | {_utc_now()}"
    )


def bot_stopped(symbol: str, reason: str) -> None:
    notify(
        f"[BOT STOPPED]\n"
        f"`{symbol}` | Reason: `{reason}` | {_utc_now()}"
    )


def trade_opened(
    symbol: str,
    direction: str,
    volume: float,
    price: float,
    sl: float,
    tp: float,
    magic: int,
    atr_pips: Optional[float] = None,
    adx: Optional[float] = None,
) -> None:
    side = "BUY" if direction == "BUY" else "SELL"
    extras = []
    if atr_pips is not None:
        extras.append(f"ATR `{atr_pips:.1f}p`")
    if adx is not None:
        extras.append(f"ADX `{adx:.1f}`")
    extra_str = " | " + " | ".join(extras) if extras else ""

    notify(
        f"[TRADE OPEN] `{symbol}` - `{side}`\n"
        f"Vol `{volume}` | Price `{price}` | SL `{sl}` | TP `{tp}`\n"
        f"Magic `{magic}` | {_utc_now()}{extra_str}"
    )


def trade_closed(
    symbol: str,
    profit: float,
    magic: int,
    reason: str = "",
    volume: Optional[float] = None,
    partial: bool = False,
) -> None:
    status = "WIN" if profit >= 0 else "LOSS"
    sign = "+" if profit >= 0 else ""
    tag = " partial" if partial else ""
    vol_s = f" | Vol `{volume}`" if volume is not None else ""
    reason_s = f" | `{reason}`" if reason else ""

    notify(
        f"[TRADE CLOSE{tag}] `{symbol}` - {status}\n"
        f"P&L `{sign}{profit:.2f}` USD{vol_s}{reason_s}\n"
        f"Magic `{magic}` | {_utc_now()}"
    )


def daily_limit_hit(reason: str, equity: float, symbol: str) -> None:
    notify(
        f"[DAILY LIMIT HIT] `{symbol}`\n"
        f"Reason: `{reason}` | Equity `{equity:.2f}` | {_utc_now()}"
    )


def trailing_stop_moved(
    symbol: str,
    ticket: int,
    old_sl: float,
    new_sl: float,
    profit_pips: float,
) -> None:
    notify(
        f"[TRAILING STOP] `{symbol}`\n"
        f"Ticket `{ticket}` | Profit `{profit_pips:.1f}p`\n"
        f"SL `{old_sl}` -> `{new_sl}` | {_utc_now()}"
    )


def error_alert(symbol: str, message: str) -> None:
    notify(
        f"[BOT ERROR] `{symbol}`\n"
        f"`{message[:300]}` | {_utc_now()}"
    )
