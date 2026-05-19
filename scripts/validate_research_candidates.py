from __future__ import annotations

import json
from pathlib import Path

from mt5_bot.config import load_config


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"

CANDIDATES = [
    "config/research_usdjpy_london_v2.yaml",
    "config/research_eurusd_london_v2.yaml",
    "config/research_gbpusd_london_v2.yaml",
    "config/research_nzdusd_london_v2.yaml",
    "config/research_usdcad_ny_v2.yaml",
    "config/research_audusd_asia_london_v2.yaml",
    "config/research_xauusd_m5_v2.yaml",
    "config/research_xagusd_v2.yaml",
]


def main() -> int:
    rows: list[dict] = []
    magics: dict[int, str] = {}
    dbs: dict[str, str] = {}
    ok = True
    for rel in CANDIDATES:
        path = ROOT / rel
        item = {"config": rel}
        try:
            cfg = load_config(path)
            item.update({
                "symbol": cfg.symbol,
                "timeframe": cfg.timeframe,
                "session": f"{cfg.strategy.session_start_hour}-{cfg.strategy.session_end_hour}"
                + (f" + {cfg.strategy.session2_start_hour}-{cfg.strategy.session2_end_hour}" if cfg.strategy.use_session2 else ""),
                "magic": cfg.execution.magic,
                "trade_enabled": cfg.execution.trade_enabled,
                "risk_pct": cfg.risk.risk_pct,
                "database_path": str(cfg.database_path),
                "status": "PASS",
            })
            if cfg.execution.trade_enabled:
                item["status"] = "FAIL"
                item["reason"] = "research candidate must have trade_enabled=false"
                ok = False
            if cfg.execution.magic in magics:
                item["status"] = "FAIL"
                item["reason"] = f"duplicate magic with {magics[cfg.execution.magic]}"
                ok = False
            magics[cfg.execution.magic] = rel
            db_key = str(cfg.database_path)
            if db_key in dbs:
                item["status"] = "FAIL"
                item["reason"] = f"duplicate database with {dbs[db_key]}"
                ok = False
            dbs[db_key] = rel
        except Exception as exc:
            item.update({"status": "FAIL", "reason": str(exc)})
            ok = False
        rows.append(item)

    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "research_candidates_validation.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = ["# Research Candidates Validation", ""]
    lines += ["| Config | Symbol | Session | Magic | Risk % | Trade Enabled | Status |",
              "| --- | --- | --- | ---: | ---: | --- | --- |"]
    for row in rows:
        lines.append(
            f"| {row.get('config')} | {row.get('symbol','?')} | {row.get('session','?')} | "
            f"{row.get('magic','?')} | {row.get('risk_pct','?')} | {row.get('trade_enabled','?')} | {row.get('status')} |"
        )
    (REPORT_DIR / "RESEARCH_CANDIDATES_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
