from datetime import datetime, timezone

from mt5_bot import news_filter


NOW = datetime(2026, 6, 30, 15, 0, tzinfo=timezone.utc)


def _event(minutes_from_now: int, *, currency: str = "USD", impact: str = "High") -> dict:
    event_time = NOW.replace(minute=NOW.minute) + news_filter.timedelta(minutes=minutes_from_now)
    return {
        "date": event_time.isoformat(),
        "currency": currency,
        "impact": impact,
        "title": "Test Event",
    }


def test_blocks_high_impact_event_inside_before_window(monkeypatch):
    monkeypatch.setattr(news_filter, "fetch_calendar", lambda: [_event(20, currency="USD")])

    assert news_filter.is_high_impact_news_nearby("EURUSD", now=NOW) is True


def test_blocks_high_impact_event_inside_after_window(monkeypatch):
    monkeypatch.setattr(news_filter, "fetch_calendar", lambda: [_event(-10, currency="EUR")])

    assert news_filter.is_high_impact_news_nearby("EURUSD", now=NOW) is True


def test_allows_event_outside_window(monkeypatch):
    monkeypatch.setattr(news_filter, "fetch_calendar", lambda: [_event(45, currency="USD")])

    assert news_filter.is_high_impact_news_nearby("EURUSD", now=NOW) is False


def test_allows_non_high_or_unrelated_currency(monkeypatch):
    monkeypatch.setattr(
        news_filter,
        "fetch_calendar",
        lambda: [
            _event(10, currency="USD", impact="Medium"),
            _event(10, currency="JPY", impact="High"),
        ],
    )

    assert news_filter.is_high_impact_news_nearby("EURUSD", now=NOW) is False


def test_missing_calendar_data_fails_closed_by_default(monkeypatch):
    monkeypatch.delenv("MT5_NEWS_FAIL_MODE", raising=False)
    monkeypatch.setattr(news_filter, "fetch_calendar", lambda: [])

    assert news_filter.is_high_impact_news_nearby("EURUSD", now=NOW) is True


def test_missing_calendar_data_can_fail_open_with_explicit_env(monkeypatch):
    monkeypatch.setenv("MT5_NEWS_FAIL_MODE", "open")
    monkeypatch.setattr(news_filter, "fetch_calendar", lambda: [])

    assert news_filter.is_high_impact_news_nearby("EURUSD", now=NOW) is False
