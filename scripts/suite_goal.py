from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"

CHECKS = [
    ("configs_load", "All pro*.yaml configs load and validate"),
    ("tests_pass", "Unit tests pass"),
    ("audit_report", "AUDIT_TOTAL_STRATEGY report generated"),
    ("controller_hidden_start", "Controller starts bots hidden; do not use direct 12-window launcher for normal ops"),
    ("risk_firewall", "Risk Firewall enabled on all active configs"),
    ("symbol_caps", "Metals have hard lot caps"),
    ("sl_noise_guard", "Spread/SL and SL/ATR guards configured"),
    ("sample_gate", "Clean post-fix sample is sufficient before claiming 10/10"),
]


def run(cmd: list[str], timeout: int = 120) -> tuple[bool, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    text = (p.stdout or "") + (p.stderr or "")
    return p.returncode == 0, text[-4000:]


def main() -> int:
    parser = argparse.ArgumentParser(description="/goal gate for MT5 suite 10/10 readiness")
    parser.add_argument("--full", action="store_true", help="run pytest too")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    results: dict[str, dict] = {}
    ok, out = run([sys.executable, "-c", "from pathlib import Path; from mt5_bot.config import load_config; [load_config(p) for p in Path('config').glob('pro*.yaml')]; print('configs_ok')"], 60)
    results["configs_load"] = {"ok": ok, "output": out}

    if args.full:
        ok, out = run([sys.executable, "-m", "pytest", "-q"], 180)
        results["tests_pass"] = {"ok": ok, "output": out}
    else:
        results["tests_pass"] = {"ok": None, "output": "skipped; run with --full"}

    ok, out = run([sys.executable, "scripts/audit_total_strategy.py", "--write"], 120)
    results["audit_report"] = {"ok": ok, "output": out[-2000:]}

    try:
        import yaml
        active_configs = []
        for bat in ["_restart_eurusd.bat", "_restart_gbpusd.bat", "_restart_jpy.bat", "_restart_gold.bat", "_restart_aud.bat", "_restart_gold_m5.bat", "_restart_usdcad.bat", "_restart_nzdusd.bat", "_restart_gbpjpy.bat", "_restart_silver.bat", "_restart_jpy_asia.bat", "_restart_usdchf.bat"]:
            text = (ROOT / bat).read_text(encoding="utf-8", errors="replace")
            marker = "--config "
            if marker in text:
                active_configs.append(text.split(marker,1)[1].split()[0])
        raws = []
        for c in active_configs:
            raws.append(yaml.safe_load((ROOT / c).read_text(encoding="utf-8")) or {})
        results["risk_firewall"] = {"ok": all(bool(r.get("risk_firewall_enabled", True)) for r in raws), "output": f"active_configs={len(raws)}"}
        metals = [r for r in raws if str(r.get("symbol", "")).upper() in {"XAUUSD", "XAGUSD"}]
        results["symbol_caps"] = {"ok": bool(metals) and all(float(r.get("max_order_volume", 0) or 0) > 0 for r in metals), "output": f"metals={len(metals)}"}
        results["sl_noise_guard"] = {"ok": all(float(r.get("max_spread_to_sl_ratio", 0) or 0) > 0 and float(r.get("min_sl_atr_ratio", 0) or 0) > 0 for r in raws), "output": "spread/sl and sl/atr present"}
        controller = (ROOT / "bot_controller.py").read_text(encoding="utf-8", errors="replace")
        results["controller_hidden_start"] = {"ok": "start_suite_hidden" in controller and "CREATE_NO_WINDOW" in controller, "output": "controller inspected"}
    except Exception as exc:
        for key in ["risk_firewall", "symbol_caps", "sl_noise_guard", "controller_hidden_start"]:
            results.setdefault(key, {"ok": False, "output": str(exc)})

    # This remains intentionally false until there is enough clean post-fix evidence.
    results["sample_gate"] = {"ok": False, "output": "requires 20-50 clean post-fix trades per active bot/group"}

    lines = ["# MT5 Suite /goal 10/10 Checklist", "", f"Generated: `{datetime.now(timezone.utc).isoformat()}`", ""]
    for key, label in CHECKS:
        r = results.get(key, {"ok": False, "output": "not run"})
        mark = "[x]" if r["ok"] is True else "[ ]" if r["ok"] is False else "[-]"
        lines.append(f"- {mark} **{label}** (`{key}`) — {str(r['output']).splitlines()[-1] if r['output'] else ''}")
    all_hard_ok = all(results.get(k, {}).get("ok") is True for k in ["configs_load", "audit_report", "controller_hidden_start", "risk_firewall", "symbol_caps", "sl_noise_guard"])
    lines += ["", f"Operational readiness gate: **{'PASS' if all_hard_ok else 'FAIL'}**", "", "Validation-to-10 gate: **WAITING ON CLEAN SAMPLE**"]
    text = "\n".join(lines) + "\n"
    if args.write:
        REPORT_DIR.mkdir(exist_ok=True)
        (REPORT_DIR / "GOAL_10_CHECKLIST.md").write_text(text, encoding="utf-8")
        (REPORT_DIR / "goal_10_checklist.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(text)
    return 0 if all_hard_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
