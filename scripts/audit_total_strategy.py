from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

ACTIVE_RESTART_BATS = [
    "_restart_eurusd.bat", "_restart_gbpusd.bat", "_restart_jpy.bat", "_restart_gold.bat",
    "_restart_aud.bat", "_restart_gold_m5.bat", "_restart_usdcad.bat", "_restart_nzdusd.bat",
    "_restart_gbpjpy.bat", "_restart_silver.bat", "_restart_jpy_asia.bat", "_restart_usdchf.bat",
]

@dataclass
class BotAudit:
    config: str
    db: str | None
    active: bool
    symbol: str
    timeframe: str
    magic: int
    risk_pct: float
    sl_pips: float
    tp_pips: float
    rr: float | None
    max_order_volume: float
    risk_firewall_enabled: bool
    max_effective_risk_pct: float
    max_spread_to_sl_ratio: float
    min_sl_atr_ratio: float
    max_symbol_daily_loss_pct: float
    max_symbol_weekly_loss_pct: float
    max_trades_hour: int
    trades: int
    wins: int
    losses: int
    realized_pnl: float
    profit_factor: float | None
    expectancy: float | None
    avg_win: float | None
    avg_loss: float | None
    max_drawdown: float
    sent_orders_24h: int
    avg_slippage_pips: float | None
    risk_blocks_24h: int
    score: float
    blockers: list[str]


def _safe_yaml(path: Path) -> dict[str, Any]:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def active_config_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for bat in ACTIVE_RESTART_BATS:
        path = ROOT / bat
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"--config\s+([^\s]+)", text)
        if m:
            out[m.group(1).replace("/", "\\")] = bat
    return out


def db_for_config(config_path: Path) -> Path | None:
    stem = config_path.stem
    candidates = [DATA_DIR / f"{stem}.sqlite"]
    # legacy names: pro_gbp.yaml -> pro_gbp.sqlite, pro.yaml -> pro.sqlite
    for c in candidates:
        if c.exists():
            return c
    return None


def _rows(con: sqlite3.Connection, sql: str, args=()) -> list[sqlite3.Row]:
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error:
        return []


def _scalar(con: sqlite3.Connection, sql: str, args=(), default=None):
    try:
        row = con.execute(sql, args).fetchone()
        if not row:
            return default
        return row[0]
    except sqlite3.Error:
        return default


def max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for v in values:
        equity += v
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def score_bot(a: BotAudit) -> tuple[float, list[str]]:
    blockers: list[str] = []
    score = 10.0
    if not a.active:
        score -= 1.0
        blockers.append("not_in_active_12_launcher")
    if not a.risk_firewall_enabled:
        score -= 2.0
        blockers.append("risk_firewall_disabled")
    if a.max_effective_risk_pct > 1.0:
        score -= 0.8
        blockers.append("effective_risk_cap_too_high")
    if a.symbol in {"XAUUSD", "XAGUSD"} and a.max_order_volume <= 0:
        score -= 1.2
        blockers.append("metal_without_hard_lot_cap")
    if a.max_spread_to_sl_ratio <= 0 or a.max_spread_to_sl_ratio > 0.25:
        score -= 0.7
        blockers.append("weak_spread_vs_sl_guard")
    if a.max_symbol_daily_loss_pct <= 0:
        score -= 0.8
        blockers.append("missing_symbol_daily_loss_cap")
    if a.trades < 20:
        score -= 1.0
        blockers.append("insufficient_clean_trade_sample")
    if a.trades >= 5:
        if a.profit_factor is not None and a.profit_factor < 1.15:
            score -= 1.0
            blockers.append("profit_factor_below_validation_threshold")
        if a.expectancy is not None and a.expectancy <= 0:
            score -= 1.0
            blockers.append("non_positive_expectancy")
    else:
        score -= 0.5
        blockers.append("too_few_realized_trades")
    if a.avg_slippage_pips is not None and abs(a.avg_slippage_pips) > max(1.0, a.sl_pips * 0.15):
        score -= 0.5
        blockers.append("slippage_large_vs_sl")
    return round(max(0.0, min(10.0, score)), 2), blockers


def audit_config(path: Path, active_map: dict[str, str], since: datetime) -> BotAudit:
    raw = _safe_yaml(path)
    risk = raw.get("risk") or {}
    execution = raw.get("execution") or {}
    symbol = str(raw.get("symbol", "UNKNOWN")).upper()
    timeframe = str(raw.get("timeframe", "?"))
    magic = int(execution.get("magic", 0))
    risk_pct = float(risk.get("risk_pct", 0.0) or 0.0)
    sl_pips = float(risk.get("sl_pips", 0.0) or 0.0)
    tp_pips = float(risk.get("tp_pips", 0.0) or 0.0)
    rr = (tp_pips / sl_pips) if sl_pips > 0 else None
    db = db_for_config(path)
    realized: list[float] = []
    sent_orders_24h = 0
    avg_slippage = None
    risk_blocks_24h = 0
    if db and db.exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            realized = [float(r[0] or 0.0) for r in _rows(
                con,
                """
                SELECT COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0) pnl
                FROM deals
                WHERE symbol = ? AND magic = ?
                ORDER BY created_at ASC
                """,
                (symbol, magic),
            )]
            sent_orders_24h = int(_scalar(
                con,
                "SELECT COUNT(*) FROM orders WHERE phase='send' AND created_at >= ?",
                (since.isoformat(),), 0,
            ) or 0)
            avg_slippage = _scalar(
                con,
                "SELECT AVG(slippage_pips) FROM orders WHERE phase='send' AND created_at >= ? AND slippage_pips IS NOT NULL",
                (since.isoformat(),), None,
            )
            risk_blocks_24h = int(_scalar(
                con,
                """
                SELECT COUNT(*) FROM trade_journal
                WHERE created_at >= ? AND (
                    execution_reason LIKE 'risk_firewall%' OR
                    execution_reason LIKE '%loss%' OR
                    execution_reason LIKE 'spread_too_large%' OR
                    execution_reason LIKE 'sl_too_tight%'
                )
                """,
                (since.isoformat(),), 0,
            ) or 0)
        finally:
            con.close()
    wins = [x for x in realized if x > 0]
    losses = [x for x in realized if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (None if gross_win == 0 else math.inf)
    expectancy = statistics.mean(realized) if realized else None
    avg_win = statistics.mean(wins) if wins else None
    avg_loss = statistics.mean(losses) if losses else None
    obj = BotAudit(
        config=str(path.relative_to(ROOT)),
        db=str(db.relative_to(ROOT)) if db else None,
        active=str(path.relative_to(ROOT)).replace("/", "\\") in active_map,
        symbol=symbol,
        timeframe=timeframe,
        magic=magic,
        risk_pct=risk_pct,
        sl_pips=sl_pips,
        tp_pips=tp_pips,
        rr=rr,
        max_order_volume=float(raw.get("max_order_volume", 0.0) or 0.0),
        risk_firewall_enabled=bool(raw.get("risk_firewall_enabled", True)),
        max_effective_risk_pct=float(raw.get("max_effective_risk_pct", 0.0) or 0.0),
        max_spread_to_sl_ratio=float(raw.get("max_spread_to_sl_ratio", 0.0) or 0.0),
        min_sl_atr_ratio=float(raw.get("min_sl_atr_ratio", 0.0) or 0.0),
        max_symbol_daily_loss_pct=float(raw.get("max_symbol_daily_loss_pct", 0.0) or 0.0),
        max_symbol_weekly_loss_pct=float(raw.get("max_symbol_weekly_loss_pct", 0.0) or 0.0),
        max_trades_hour=int(raw.get("max_trades_per_symbol_per_hour", 0) or 0),
        trades=len(realized),
        wins=len(wins),
        losses=len(losses),
        realized_pnl=sum(realized),
        profit_factor=profit_factor,
        expectancy=expectancy,
        avg_win=avg_win,
        avg_loss=avg_loss,
        max_drawdown=max_drawdown(realized),
        sent_orders_24h=sent_orders_24h,
        avg_slippage_pips=float(avg_slippage) if avg_slippage is not None else None,
        risk_blocks_24h=risk_blocks_24h,
        score=0.0,
        blockers=[],
    )
    obj.score, obj.blockers = score_bot(obj)
    return obj


def render_markdown(rows: list[BotAudit], generated_at: str) -> str:
    active_rows = [r for r in rows if r.active]
    avg_score = statistics.mean([r.score for r in active_rows]) if active_rows else 0.0
    lines = [
        "# AUDIT_TOTAL_STRATEGY",
        "",
        f"Generated: `{generated_at}`",
        "",
        f"Suite score active 12: **{avg_score:.2f}/10**",
        "",
        "## Active bot scores",
        "",
        "| Bot | TF | Score | Trades | PnL | PF | Exp | DD | Key blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in sorted(active_rows, key=lambda x: (x.score, x.symbol)):
        pf = "INF" if r.profit_factor == math.inf else (f"{r.profit_factor:.2f}" if r.profit_factor is not None else "n/a")
        exp = f"{r.expectancy:.2f}" if r.expectancy is not None else "n/a"
        blockers = ", ".join(r.blockers[:4]) or "none"
        lines.append(f"| {r.symbol} `{Path(r.config).name}` | {r.timeframe} | {r.score:.2f} | {r.trades} | {r.realized_pnl:.2f} | {pf} | {exp} | {r.max_drawdown:.2f} | {blockers} |")
    inactive = [r for r in rows if not r.active]
    if inactive:
        lines += ["", "## Non-active configs found", ""]
        for r in inactive:
            lines.append(f"- `{r.config}` ({r.symbol}) — not in active 12 launcher")
    lines += [
        "",
        "## 10/10 checklist gate",
        "",
        "- [ ] Minimum 20–50 clean post-fix trades per active bot/group",
        "- [ ] Active suite score >= 9.0 for risk/execution/reporting before scaling",
        "- [ ] Profit factor >= 1.3 and positive expectancy on out-of-sample / forward sample",
        "- [ ] Metals results reported separately from FX majors",
        "- [ ] No open contaminated position mixed into clean validation",
        "- [ ] No duplicated trade loops or visible terminal sprawl; use controller workflow",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-hours", type=int, default=24)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    since = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
    active = active_config_map()
    rows = [audit_config(p, active, since) for p in sorted(CONFIG_DIR.glob("pro*.yaml"))]
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "bots": [asdict(r) for r in rows]}
    md = render_markdown(rows, payload["generated_at"])
    if args.write:
        REPORT_DIR.mkdir(exist_ok=True)
        (REPORT_DIR / "AUDIT_TOTAL_STRATEGY.md").write_text(md, encoding="utf-8")
        (REPORT_DIR / "audit_total_strategy.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
