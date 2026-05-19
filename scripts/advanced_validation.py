from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

GROUPS = {
    "fx_majors": {"EURUSD", "GBPUSD", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF"},
    "jpy_crosses": {"USDJPY", "GBPJPY"},
    "metals": {"XAUUSD", "XAGUSD"},
}


def group_for(symbol: str) -> str:
    sym = symbol.upper()
    for name, members in GROUPS.items():
        if sym in members:
            return name
    return "other"


def fetch_deals(db: Path) -> list[dict]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        try:
            rows = con.execute(
                """
                SELECT created_at, symbol, magic, volume, price,
                       COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0) pnl
                FROM deals
                ORDER BY created_at ASC
                """
            ).fetchall()
        except sqlite3.Error:
            return []
        return [dict(r) for r in rows]
    finally:
        con.close()


def profit_factor(pnls: list[float]) -> float | None:
    wins = sum(x for x in pnls if x > 0)
    losses = abs(sum(x for x in pnls if x < 0))
    if losses == 0:
        return math.inf if wins > 0 else None
    return wins / losses


def max_drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd


def monte_carlo(pnls: list[float], runs: int = 1000) -> dict:
    if len(pnls) < 10:
        return {"status": "insufficient_sample", "runs": 0}
    finals = []
    dds = []
    rng = random.Random(260430)
    for _ in range(runs):
        sample = [rng.choice(pnls) for _ in pnls]
        finals.append(sum(sample))
        dds.append(max_drawdown(sample))
    finals.sort(); dds.sort()
    return {
        "status": "ok",
        "runs": runs,
        "p05_final_pnl": finals[int(runs * 0.05)],
        "p50_final_pnl": finals[int(runs * 0.50)],
        "p95_drawdown": dds[int(runs * 0.95)],
    }


def walk_forward_proxy(pnls: list[float]) -> dict:
    if len(pnls) < 20:
        return {"status": "insufficient_sample", "folds": 0}
    folds = []
    size = max(5, len(pnls) // 4)
    for i in range(0, len(pnls) - size + 1, size):
        part = pnls[i:i+size]
        folds.append({
            "n": len(part),
            "pnl": sum(part),
            "expectancy": statistics.mean(part),
            "profit_factor": profit_factor(part),
            "max_drawdown": max_drawdown(part),
        })
    return {"status": "ok", "folds": folds}


def summarize() -> dict:
    deals = []
    for db in sorted(DATA.glob("pro*.sqlite")):
        for d in fetch_deals(db):
            d["db"] = db.name
            d["group"] = group_for(str(d.get("symbol", "")))
            deals.append(d)
    by_symbol: dict[str, list[float]] = {}
    by_group: dict[str, list[float]] = {}
    for d in deals:
        sym = str(d.get("symbol") or "UNKNOWN")
        pnl = float(d.get("pnl") or 0.0)
        by_symbol.setdefault(sym, []).append(pnl)
        by_group.setdefault(str(d.get("group") or "other"), []).append(pnl)
    def pack(name: str, pnls: list[float]) -> dict:
        return {
            "name": name,
            "trades": len(pnls),
            "pnl": sum(pnls),
            "expectancy": statistics.mean(pnls) if pnls else None,
            "profit_factor": profit_factor(pnls),
            "max_drawdown": max_drawdown(pnls),
            "monte_carlo": monte_carlo(pnls),
            "walk_forward": walk_forward_proxy(pnls),
            "validation_status": "PASS" if len(pnls) >= 50 and (profit_factor(pnls) or 0) >= 1.3 and (statistics.mean(pnls) if pnls else 0) > 0 else "WAITING_OR_FAIL",
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": [pack(k, v) for k, v in sorted(by_symbol.items())],
        "groups": [pack(k, v) for k, v in sorted(by_group.items())],
    }


def fmt_pf(v) -> str:
    if v == math.inf:
        return "INF"
    return f"{v:.2f}" if isinstance(v, (int, float)) else "n/a"


def render(data: dict) -> str:
    lines = ["# Advanced Validation Report", "", f"Generated: `{data['generated_at']}`", "", "## Group validation", "", "| Group | Trades | PnL | PF | Exp | DD | MC | Walk-forward | Status |", "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for r in data["groups"]:
        mc = r["monte_carlo"]["status"]
        wf = r["walk_forward"]["status"]
        exp = f"{r['expectancy']:.2f}" if r["expectancy"] is not None else "n/a"
        lines.append(f"| {r['name']} | {r['trades']} | {r['pnl']:.2f} | {fmt_pf(r['profit_factor'])} | {exp} | {r['max_drawdown']:.2f} | {mc} | {wf} | {r['validation_status']} |")
    lines += ["", "## Symbol validation", "", "| Symbol | Trades | PnL | PF | Exp | DD | Status |", "|---|---:|---:|---:|---:|---:|---|"]
    for r in data["symbols"]:
        exp = f"{r['expectancy']:.2f}" if r["expectancy"] is not None else "n/a"
        lines.append(f"| {r['name']} | {r['trades']} | {r['pnl']:.2f} | {fmt_pf(r['profit_factor'])} | {exp} | {r['max_drawdown']:.2f} | {r['validation_status']} |")
    lines += ["", "## Gate", "", "Advanced validation is functional, but most outputs will remain `insufficient_sample` until enough clean post-fix trades exist."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = summarize()
    text = render(data)
    if args.write:
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / "ADVANCED_VALIDATION.md").write_text(text, encoding="utf-8")
        (REPORTS / "advanced_validation.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
