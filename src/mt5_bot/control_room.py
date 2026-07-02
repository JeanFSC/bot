from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from mt5_bot.process_guard import audit_duplicate_trades


@dataclass(frozen=True)
class ControlRoomSnapshot:
    created_at: str
    level: str
    reasons: list[str]
    process_guard: dict[str, Any]
    supervisor: dict[str, Any] | None
    portfolio_heat: dict[str, Any] | None
    watchdog: dict[str, Any] | None


def build_snapshot(
    *,
    supervisor_path: str | Path = "data/live_position_supervisor.jsonl",
    heat_path: str | Path = "data/portfolio_heat.jsonl",
    watchdog_path: str | Path = "data/watchdog_health.jsonl",
    supervisor_stale_after_seconds: int = 20,
    heat_stale_after_seconds: int = 60,
    watchdog_stale_after_seconds: int = 1800,
    now: datetime | None = None,
) -> ControlRoomSnapshot:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    process_report = audit_duplicate_trades()
    supervisor = read_latest_jsonl(supervisor_path)
    heat = read_latest_jsonl(heat_path)
    watchdog = read_latest_jsonl(watchdog_path)

    reasons: list[str] = []
    if not process_report.get("ok"):
        reasons.append("process_guard_not_ok")
    if supervisor is None:
        reasons.append("supervisor_report_missing")
    else:
        supervisor_age = report_age_seconds(supervisor, now)
        supervisor["age_seconds"] = supervisor_age
        if supervisor_age is None or supervisor_age > supervisor_stale_after_seconds:
            reasons.append("supervisor_report_stale")
    if heat is None:
        reasons.append("portfolio_heat_missing")
    else:
        heat_age = report_age_seconds(heat, now)
        heat["age_seconds"] = heat_age
        if heat_age is None or heat_age > heat_stale_after_seconds:
            reasons.append("portfolio_heat_stale")
    if heat and int(heat.get("unprotected_positions", 0) or 0) > 0:
        reasons.append(f"unprotected_positions_{heat.get('unprotected_positions')}")
    if heat and str(heat.get("decision")) == "block_new_entries_recommended":
        reasons.append("portfolio_heat_blocks_new_entries")
    if watchdog is None:
        reasons.append("watchdog_report_missing")
    else:
        watchdog_age = report_age_seconds(watchdog, now)
        watchdog["age_seconds"] = watchdog_age
        if watchdog_age is None or watchdog_age > watchdog_stale_after_seconds:
            reasons.append("watchdog_report_stale")
        if str(watchdog.get("level", "")).lower() == "critical":
            reasons.append("watchdog_critical")

    level = "critical" if any(reason in {"process_guard_not_ok", "watchdog_critical"} for reason in reasons) else (
        "warn" if reasons else "ok"
    )
    return ControlRoomSnapshot(
        created_at=now.isoformat(),
        level=level,
        reasons=reasons or ["ok"],
        process_guard=process_report,
        supervisor=supervisor,
        portfolio_heat=heat,
        watchdog=watchdog,
    )


def read_latest_jsonl(path: str | Path) -> dict[str, Any] | None:
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


def report_age_seconds(payload: dict[str, Any], now: datetime | None = None) -> float | None:
    created_at = payload.get("created_at")
    if not created_at:
        return None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (now - created.astimezone(timezone.utc)).total_seconds())


def snapshot_to_dict(snapshot: ControlRoomSnapshot) -> dict[str, Any]:
    return {
        "created_at": snapshot.created_at,
        "level": snapshot.level,
        "reasons": snapshot.reasons,
        "process_guard": snapshot.process_guard,
        "supervisor": snapshot.supervisor,
        "portfolio_heat": snapshot.portfolio_heat,
        "watchdog": snapshot.watchdog,
    }


def render_summary(snapshot: ControlRoomSnapshot) -> str:
    heat = snapshot.portfolio_heat or {}
    supervisor = snapshot.supervisor or {}
    lines = [
        f"CONTROL_ROOM {snapshot.level.upper()}",
        f"created_at={snapshot.created_at}",
        f"reasons={','.join(snapshot.reasons)}",
        f"process_guard_ok={bool(snapshot.process_guard.get('ok'))}",
        (
            "positions="
            f"{heat.get('owned_positions', 'n/a')}/{heat.get('checked_positions', 'n/a')} "
            f"unknown={heat.get('unknown_positions', 'n/a')} "
            f"unprotected={heat.get('unprotected_positions', 'n/a')}"
        ),
        (
            "freshness="
            f"supervisor_age={_age_text(supervisor.get('age_seconds'))} "
            f"heat_age={_age_text(heat.get('age_seconds'))} "
            f"watchdog_age={_age_text((snapshot.watchdog or {}).get('age_seconds'))}"
        ),
        (
            "equity="
            f"{heat.get('equity', 'n/a')} floating_pnl={heat.get('floating_pnl', 'n/a')} "
            f"risk_to_sl_usd={heat.get('risk_to_sl_usd', 'n/a')} "
            f"risk_to_sl_pct={heat.get('risk_to_sl_pct', 'n/a')}"
        ),
        f"heat_decision={heat.get('decision', 'n/a')}",
        (
            "supervisor="
            f"managed={supervisor.get('managed_positions', 'n/a')} "
            f"unknown={supervisor.get('unknown_positions', 'n/a')} "
            f"actions={len(supervisor.get('actions', [])) if isinstance(supervisor.get('actions'), list) else 'n/a'}"
        ),
    ]
    return "\n".join(lines)


def _age_text(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.0f}s"
    except (TypeError, ValueError):
        return "n/a"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_control_room")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--supervisor-path", default="data/live_position_supervisor.jsonl")
    parser.add_argument("--heat-path", default="data/portfolio_heat.jsonl")
    parser.add_argument("--watchdog-path", default="data/watchdog_health.jsonl")
    args = parser.parse_args(argv)

    snapshot = build_snapshot(
        supervisor_path=args.supervisor_path,
        heat_path=args.heat_path,
        watchdog_path=args.watchdog_path,
    )
    if args.json:
        print(json.dumps(snapshot_to_dict(snapshot), indent=2, sort_keys=True))
    else:
        print(render_summary(snapshot))
    return 0 if snapshot.level != "critical" else 2


if __name__ == "__main__":
    raise SystemExit(main())
