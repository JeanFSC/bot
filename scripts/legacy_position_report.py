from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
LEGACY_TICKETS = {8661985181: "XAUUSD pre-fix metals sizing bug / contaminated validation"}


def get_positions() -> list[dict]:
    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        return [{"error": f"MetaTrader5 import failed: {exc}"}]
    if not mt5.initialize():
        return [{"error": "MT5 initialize failed"}]
    try:
        out = []
        for p in mt5.positions_get() or []:
            d = p._asdict() if hasattr(p, "_asdict") else dict(p)
            ticket = int(d.get("ticket", 0) or 0)
            out.append({
                "ticket": ticket,
                "symbol": d.get("symbol"),
                "type": d.get("type"),
                "volume": d.get("volume"),
                "price_open": d.get("price_open"),
                "sl": d.get("sl"),
                "tp": d.get("tp"),
                "profit": d.get("profit"),
                "magic": d.get("magic"),
                "legacy": ticket in LEGACY_TICKETS,
                "legacy_reason": LEGACY_TICKETS.get(ticket),
            })
        return out
    finally:
        mt5.shutdown()


def render(positions: list[dict]) -> str:
    lines = ["# Legacy Position Segregation Report", "", f"Generated: `{datetime.now(timezone.utc).isoformat()}`", "", "This report does not close or modify positions. It only marks positions that must be excluded from clean forward-test validation.", "", "| Ticket | Symbol | Volume | Entry | SL | TP | Profit | Legacy | Reason |", "|---:|---|---:|---:|---:|---:|---:|---|---|"]
    for p in positions:
        if "error" in p:
            lines.append(f"| n/a | ERROR | 0 | 0 | 0 | 0 | 0 | yes | {p['error']} |")
            continue
        lines.append(f"| {p['ticket']} | {p['symbol']} | {p['volume']} | {p['price_open']} | {p['sl']} | {p['tp']} | {p['profit']} | {'yes' if p['legacy'] else 'no'} | {p.get('legacy_reason') or ''} |")
    legacy_open = [p for p in positions if p.get("legacy")]
    lines += ["", f"Legacy open positions: **{len(legacy_open)}**", "", "Gate: **BLOCKED** for clean validation while legacy positions are open, unless Jean explicitly chooses to segregate them and proceed."]
    return "\n".join(lines) + "\n"


def main() -> int:
    positions = get_positions()
    REPORTS.mkdir(exist_ok=True)
    text = render(positions)
    (REPORTS / "LEGACY_POSITION_SEGREGATION.md").write_text(text, encoding="utf-8")
    (REPORTS / "legacy_position_segmentation.json").write_text(json.dumps(positions, indent=2), encoding="utf-8")
    print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
