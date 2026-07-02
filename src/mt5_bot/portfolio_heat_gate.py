from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PortfolioHeatGateDecision:
    allow_new_entry: bool
    reason: str
    risk_multiplier: float = 1.0
    stale: bool = False
    report_age_seconds: float | None = None
    heat_decision: str | None = None


def portfolio_heat_gate_decision(
    report_path: str | Path,
    *,
    max_age_seconds: int = 90,
    required: bool = True,
    reduce_risk_multiplier: float = 0.50,
    now: datetime | None = None,
) -> PortfolioHeatGateDecision:
    """Convert the Portfolio Heat Agent report into an Entry Agent gate.

    This is intentionally read-only. The heat monitor owns the expensive MT5
    account/risk projection; entry bots consume the latest JSONL line and only
    decide whether new entries remain allowed.
    """
    now = _utc(now or datetime.now(timezone.utc))
    payload = _read_latest_jsonl(report_path)
    if payload is None:
        return PortfolioHeatGateDecision(
            allow_new_entry=not required,
            reason="portfolio_heat_missing",
            risk_multiplier=0.0 if required else 1.0,
        )
    if payload.get("parse_error"):
        return PortfolioHeatGateDecision(
            allow_new_entry=not required,
            reason="portfolio_heat_parse_error",
            risk_multiplier=0.0 if required else 1.0,
        )

    created_at_raw = payload.get("created_at")
    age_seconds = _report_age_seconds(created_at_raw, now)
    stale = age_seconds is None or age_seconds > max_age_seconds
    if stale:
        return PortfolioHeatGateDecision(
            allow_new_entry=not required,
            reason="portfolio_heat_stale",
            risk_multiplier=0.0 if required else 1.0,
            stale=True,
            report_age_seconds=age_seconds,
            heat_decision=str(payload.get("decision", "")) or None,
        )

    heat_decision = str(payload.get("decision", ""))
    if heat_decision == "block_new_entries_recommended":
        return PortfolioHeatGateDecision(
            allow_new_entry=False,
            reason="portfolio_heat_block",
            risk_multiplier=0.0,
            report_age_seconds=age_seconds,
            heat_decision=heat_decision,
        )
    if heat_decision == "reduce_or_wait_recommended":
        return PortfolioHeatGateDecision(
            allow_new_entry=True,
            reason="portfolio_heat_reduce",
            risk_multiplier=max(0.0, min(1.0, reduce_risk_multiplier)),
            report_age_seconds=age_seconds,
            heat_decision=heat_decision,
        )
    return PortfolioHeatGateDecision(
        allow_new_entry=True,
        reason="portfolio_heat_ok",
        risk_multiplier=1.0,
        report_age_seconds=age_seconds,
        heat_decision=heat_decision or None,
    )


def _read_latest_jsonl(path: str | Path) -> dict[str, Any] | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    last_line = ""
    with file_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                last_line = raw.strip()
    if not last_line:
        return None
    try:
        payload = json.loads(last_line)
    except json.JSONDecodeError:
        return {"parse_error": True, "raw": last_line}
    return payload if isinstance(payload, dict) else {"payload": payload}


def _report_age_seconds(created_at: Any, now: datetime) -> float | None:
    if not created_at:
        return None
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, (_utc(now) - _utc(created)).total_seconds())


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
