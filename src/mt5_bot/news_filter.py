"""
news_filter.py — High-impact economic news filter
==================================================
Blocks trade entries 30 min before and 15 min after high-impact
economic events (NFP, FOMC, CPI, etc.) fetched from ForexFactory.

API: https://nfs.faireconomy.media/ff_calendar_thisweek.json
Cache: 1-hour in-memory cache (avoids hammering the API each tick)

Usage:
    from mt5_bot.news_filter import is_high_impact_news_nearby

    if is_high_impact_news_nearby("EURUSD"):
        # skip entry
        continue
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger("mt5_bot.news_filter")

_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
_CACHE_TTL_SECONDS = 3600  # refresh cache every hour
_STALE_CACHE_SECONDS = 6 * 3600  # on 429/network errors, stale news is better than none
_CACHE_FILE = Path(os.getenv("MT5_NEWS_CACHE_FILE", "data/forexfactory_calendar_cache.json"))
_LOCK_FILE = _CACHE_FILE.with_suffix(".lock")

# In-memory cache
_cache_data: list[dict] = []
_cache_timestamp: float = 0.0


def _load_file_cache(max_age_seconds: int) -> Optional[list[dict]]:
    """Load shared on-disk cache if present and not too old."""
    try:
        if not _CACHE_FILE.exists():
            return None
        payload = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        saved_at = float(payload.get("saved_at", 0))
        if time.time() - saved_at > max_age_seconds:
            return None
        events = payload.get("events", [])
        return events if isinstance(events, list) else None
    except Exception as exc:
        LOGGER.debug("news_filter: failed to read file cache: %s", exc)
        return None


def _save_file_cache(events: list[dict]) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"saved_at": time.time(), "events": events}), encoding="utf-8")
        tmp.replace(_CACHE_FILE)
    except Exception as exc:
        LOGGER.debug("news_filter: failed to save file cache: %s", exc)


def _acquire_fetch_lock(timeout_seconds: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            # Remove abandoned locks after 30s.
            try:
                if time.time() - _LOCK_FILE.stat().st_mtime > 30:
                    _LOCK_FILE.unlink(missing_ok=True)
                    continue
            except Exception:
                pass
            time.sleep(0.25)
    return False


def _release_fetch_lock() -> None:
    try:
        _LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _fetch_calendar_raw() -> list[dict]:
    """Fetch ForexFactory JSON calendar. Returns list of event dicts."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _CALENDAR_URL,
            headers={"User-Agent": "Mozilla/5.0 (MT5-Bot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, list):
            _save_file_cache(data)
            return data
        return []
    except Exception as exc:
        stale = _load_file_cache(_STALE_CACHE_SECONDS)
        if stale is not None:
            LOGGER.warning("news_filter: fetch failed (%s); using stale shared cache with %d events", exc, len(stale))
            return stale
        LOGGER.warning("news_filter: failed to fetch calendar and no usable cache exists: %s", exc)
        return []


def fetch_calendar(force: bool = False) -> list[dict]:
    """Return cached calendar data, refreshing if stale (> 1 hour).

    Multiple bot processes run at once. Use a shared disk cache + lock so five
    bots do not hammer ForexFactory simultaneously and trigger HTTP 429.
    """
    global _cache_data, _cache_timestamp
    now = time.monotonic()
    if not force and (now - _cache_timestamp) <= _CACHE_TTL_SECONDS:
        return _cache_data

    shared = None if force else _load_file_cache(_CACHE_TTL_SECONDS)
    if shared is not None:
        _cache_data = shared
        _cache_timestamp = now
        LOGGER.info("news_filter: loaded %d events from shared cache", len(_cache_data))
        return _cache_data

    have_lock = _acquire_fetch_lock()
    try:
        # Another process may have fetched while we waited for the lock.
        shared = None if force else _load_file_cache(_CACHE_TTL_SECONDS)
        if shared is not None:
            _cache_data = shared
            _cache_timestamp = now
            LOGGER.info("news_filter: loaded %d events from shared cache", len(_cache_data))
            return _cache_data

        LOGGER.debug("news_filter: refreshing calendar cache")
        _cache_data = _fetch_calendar_raw() if have_lock else (_load_file_cache(_STALE_CACHE_SECONDS) or [])
        _cache_timestamp = now
        LOGGER.info("news_filter: loaded %d events from ForexFactory/cache", len(_cache_data))
        return _cache_data
    finally:
        if have_lock:
            _release_fetch_lock()


def _currencies_for_symbol(symbol: str) -> list[str]:
    """Extract the two currencies from a forex symbol.

    Examples:
        EURUSD → ['EUR', 'USD']
        USDJPY → ['USD', 'JPY']
        GBPUSD → ['GBP', 'USD']
    """
    sym = symbol.upper().replace("/", "")
    if len(sym) >= 6:
        return [sym[:3], sym[3:6]]
    return []


def _parse_event_time(event: dict) -> Optional[datetime]:
    """Parse ForexFactory event date/time into a UTC datetime."""
    try:
        # ForexFactory format: "2024-01-05T08:30:00-05:00" or "2024-01-05T13:30:00Z"
        date_str = event.get("date", "")
        if not date_str:
            return None
        # Try ISO 8601 with offset
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            # Assume UTC if no timezone provided
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def is_high_impact_news_nearby(
    symbol: str,
    minutes_before: int = 30,
    minutes_after: int = 15,
    now: Optional[datetime] = None,
) -> bool:
    """Return True if a high-impact event for this symbol's currencies is nearby.

    Args:
        symbol:         Forex pair, e.g. 'EURUSD', 'USDJPY'
        minutes_before: Block entries N minutes before event time
        minutes_after:  Block entries N minutes after event time
        now:            Current UTC datetime (uses datetime.now(utc) if None)

    Returns:
        True → entry should be BLOCKED (news window active)
        False → safe to trade
    """
    if now is None:
        now = datetime.now(timezone.utc)

    currencies = _currencies_for_symbol(symbol)
    if not currencies:
        return False

    events = fetch_calendar()
    if not events:
        # If we can't fetch calendar, be conservative and allow trading
        LOGGER.debug("news_filter: no calendar data — allowing entry")
        return False

    window_start = now - timedelta(minutes=minutes_after)
    window_end   = now + timedelta(minutes=minutes_before)

    for event in events:
        # Only block high-impact events
        impact = str(event.get("impact", "")).lower()
        if impact != "high":
            continue

        # Check if event currency matches our symbol
        event_currency = str(event.get("currency", "")).upper()
        if event_currency not in currencies:
            continue

        event_time = _parse_event_time(event)
        if event_time is None:
            continue

        # Event is within our window?
        if window_start <= event_time <= window_end:
            title = event.get("title", "Unknown event")
            LOGGER.warning(
                "news_filter: HIGH-IMPACT event blocking entry — "
                "symbol=%s currency=%s event='%s' event_time=%s",
                symbol, event_currency, title,
                event_time.strftime("%Y-%m-%d %H:%M UTC"),
            )
            return True

    return False
