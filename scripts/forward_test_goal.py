from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SRC = ROOT / "src"

ACTIVE_RESTART_BATS = [
    "_restart_eurusd.bat", "_restart_gbpusd.bat", "_restart_jpy.bat", "_restart_gold.bat",
    "_restart_aud.bat", "_restart_gold_m5.bat", "_restart_usdcad.bat", "_restart_nzdusd.bat",
    "_restart_gbpjpy.bat", "_restart_silver.bat", "_restart_jpy_asia.bat", "_restart_usdchf.bat",
]

GOAL_PHASES = [
    ("audit_review", "Review latest AUDIT_TOTAL_STRATEGY and identify weak bots"),
    ("legacy_xau_resolution", "Resolve/segregate the pre-fix XAUUSD open position before clean validation"),
    ("forward_clean_run", "Run 12-bot forward test from CONTROL_BOTS only, no direct 12-window launcher"),
    ("daily_reporting", "Generate daily_report + audit_total_strategy + suite_goal after each trading day"),
    ("no_scaling", "Keep risk capped until clean sample passes PF/expectancy/drawdown gates"),
    ("advanced_validation", "Add/execute walk-forward, Monte Carlo, and bot ranking before risk escalation"),
]


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def process_counts() -> dict[str, int]:
    ps = """
$p=Get-CimInstance Win32_Process
$trade=@($p | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'mt5_bot trade' }).Count
$restart=@($p | Where-Object { $_.Name -eq 'cmd.exe' -and $_.CommandLine -match '_restart_' }).Count
$controller=@($p | Where-Object { $_.CommandLine -match 'bot_controller.py' }).Count
[pscustomobject]@{trade_loops=$trade; restart_wrappers=$restart; controllers=$controller} | ConvertTo-Json -Compress
"""
    code, out = run(["powershell", "-NoProfile", "-Command", ps], 20)
    if code != 0:
        return {"trade_loops": -1, "restart_wrappers": -1, "controllers": -1}
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return {"trade_loops": -1, "restart_wrappers": -1, "controllers": -1}


def open_positions() -> list[dict]:
    try:
        import MetaTrader5 as mt5
    except Exception:
        return [{"error": "MetaTrader5 import failed"}]
    if not mt5.initialize():
        return [{"error": "MT5 initialize failed"}]
    try:
        positions = mt5.positions_get() or []
        out = []
        for p in positions:
            d = p._asdict() if hasattr(p, "_asdict") else dict(p)
            out.append({
                "ticket": d.get("ticket"),
                "symbol": d.get("symbol"),
                "type": d.get("type"),
                "volume": d.get("volume"),
                "price_open": d.get("price_open"),
                "sl": d.get("sl"),
                "tp": d.get("tp"),
                "profit": d.get("profit"),
                "magic": d.get("magic"),
            })
        return out
    finally:
        mt5.shutdown()


def latest_audit_summary() -> str:
    p = REPORTS / "AUDIT_TOTAL_STRATEGY.md"
    if not p.exists():
        return "missing AUDIT_TOTAL_STRATEGY.md"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    keep = []
    for line in lines:
        if "Suite score" in line or line.startswith("| XAU") or line.startswith("| AUD") or line.startswith("| GBPUSD") or line.startswith("| USDJPY"):
            keep.append(line)
    return "\n".join(keep[:20])


def build_report(allow_contaminated_open_position: bool) -> tuple[str, bool]:
    counts = process_counts()
    positions = open_positions()
    contaminated_open = any(str(p.get("symbol")) == "XAUUSD" and float(p.get("volume") or 0) >= 3.0 for p in positions if isinstance(p, dict))
    hard_ok = True
    checks: list[tuple[str, bool, str]] = []
    checks.append(("suite_stopped_for_audit", counts.get("trade_loops") == 0 and counts.get("restart_wrappers") == 0, str(counts)))
    checks.append(("reports_exist", (REPORTS / "AUDIT_TOTAL_STRATEGY.md").exists() and (REPORTS / "GOAL_10_CHECKLIST.md").exists(), "audit + goal reports"))
    checks.append(("controller_workflow_required", (ROOT / "CONTROL_BOTS.bat").exists() and (ROOT / "bot_controller.py").exists(), "CONTROL_BOTS.bat present"))
    checks.append(("legacy_xau_position_handled", (not contaminated_open) or allow_contaminated_open_position, f"open_positions={positions}"))
    checks.append(("validation_sample_gate", False, "requires 20-50 clean post-fix trades per active bot/group"))
    for name, ok, _ in checks:
        if name != "validation_sample_gate" and not ok:
            hard_ok = False
    lines = [
        "# Forward Test /goal",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Phase checklist",
        "",
    ]
    for _, label in GOAL_PHASES:
        lines.append(f"- [ ] {label}")
    lines += ["", "## Current gates", ""]
    for name, ok, detail in checks:
        mark = "[x]" if ok else "[ ]"
        lines.append(f"- {mark} `{name}` - {detail}")
    lines += [
        "",
        f"Preflight hard gate: **{'PASS' if hard_ok else 'BLOCKED'}**",
        "Validation gate: **WAITING ON CLEAN SAMPLE**",
        "",
        "## Latest audit summary",
        "",
        latest_audit_summary(),
        "",
        "## Operator rule",
        "",
        "Start only from `CONTROL_BOTS.bat` after Jean explicitly approves forward-test restart.",
    ]
    return "\n".join(lines) + "\n", hard_ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--allow-contaminated-open-position", action="store_true")
    args = parser.parse_args()
    text, hard_ok = build_report(args.allow_contaminated_open_position)
    if args.write:
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / "FORWARD_TEST_GOAL.md").write_text(text, encoding="utf-8")
    print(text)
    return 0 if hard_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
