from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIGS = [
    "config/pro.yaml",
    "config/pro_gbp.yaml",
    "config/pro_jpy.yaml",
    "config/pro_gold.yaml",
    "config/pro_aud.yaml",
    "config/pro_gold_m5.yaml",
    "config/pro_usdcad.yaml",
    "config/pro_nzdusd.yaml",
    "config/pro_gbpjpy.yaml",
    "config/pro_silver.yaml",
    "config/pro_jpy_asia.yaml",
    "config/pro_usdchf.yaml",
]


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=45)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())
    return proc.returncode


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    from mt5_bot.config import load_config

    launcher = (ROOT / "_run_all_pro_autorestart.bat").read_text(encoding="utf-8")
    assert launcher.count("start ") >= 12, "launcher must start 12 bot windows"
    print("LAUNCHER_OK starts=", launcher.count("start "))

    magics: set[int] = set()
    for rel in CONFIGS:
        cfg = load_config(ROOT / rel)
        assert cfg.account and cfg.account.demo_only is True, rel
        assert cfg.execution.trade_enabled is False, rel
        assert cfg.execution.magic not in magics, f"duplicate magic {cfg.execution.magic}"
        magics.add(cfg.execution.magic)
        assert cfg.use_global_risk_guard is True, rel
        print(f"CONFIG_OK {Path(rel).name:<18} {cfg.symbol:<6} {cfg.timeframe}/{cfg.trend_timeframe} magic={cfg.execution.magic}")

    if not (os.getenv("MT5_LOGIN") and os.getenv("MT5_PASSWORD")):
        print("MT5_CHECK_SKIPPED missing MT5_LOGIN/MT5_PASSWORD in environment")
        return 0

    failures: list[str] = []
    for rel in CONFIGS:
        code = run([sys.executable, "-m", "mt5_bot", "check", "--config", rel])
        if code != 0:
            failures.append(rel)
    if failures:
        print("MT5_CHECK_FAILED", failures)
        return 1
    print("SMOKE_OK all 12 configs passed MT5 check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
