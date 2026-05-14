from __future__ import annotations

import glob
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MT5_LOGIN", "1")
os.environ.setdefault("MT5_PASSWORD", "x")
os.environ.setdefault("MT5_SERVER", "MetaQuotes-Demo")

from mt5_bot.config import load_config
from mt5_bot.strategy import SignalType, candle_confirms_retest
import pandas as pd

CORE_CONFIGS = [
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

print("== CONFIG QA ==")
magics = set()
for rel in CORE_CONFIGS:
    c = load_config(ROOT / rel)
    assert c.account.demo_only is True, rel
    assert c.execution.trade_enabled is False, rel
    assert c.execution.magic not in magics, f"duplicate magic {c.execution.magic}"
    magics.add(c.execution.magic)
    assert c.max_portfolio_open_positions == 5, rel
    assert c.use_global_risk_guard is True, rel
    assert c.max_daily_loss_pct <= 5.0, rel
    assert c.risk.risk_pct > 0, rel
    assert c.strategy.use_adx_filter is True, rel
    assert c.strategy.atr_tp_multiplier >= 3.0, rel
    print(f"OK {rel:<26} {c.symbol:<6} {c.timeframe:<3}/{c.trend_timeframe:<3} risk={c.risk.risk_pct:<3} adx={c.strategy.adx_min_value:<4} retest={c.strategy.use_retest_filter} candle={c.strategy.use_candle_confirm} magic={c.execution.magic}")

print("\n== BAT QA ==")
launcher = (ROOT / "_run_all_pro_autorestart.bat").read_text(encoding="utf-8")
for rel in CORE_CONFIGS:
    stem = Path(rel).stem.replace("pro", "").strip("_") or "eurusd"
for bat in sorted(ROOT.glob("_restart_*.bat")):
    s = bat.read_text(encoding="utf-8", errors="replace")
    assert "--trade-enabled" not in s, f"{bat.name} must respect config execution.trade_enabled=false by default"
    assert ">> logs\\bot_" in s, bat.name
    assert "python -m mt5_bot check" in s, bat.name
    assert "python -m mt5_bot trade" in s, bat.name
    print(f"OK {bat.name}")
assert launcher.count("start ") >= 12, "launcher should start 12 consoles"
print("OK _run_all_pro_autorestart.bat starts", launcher.count("start "), "windows")

print("\n== STRATEGY CANDLE QA ==")
buy_rates = pd.DataFrame([
    {"time":"t0","open":1.00,"high":1.02,"low":0.99,"close":1.00},
    {"time":"t1","open":1.00,"high":1.01,"low":0.98,"close":0.99},
    {"time":"t2","open":0.99,"high":1.05,"low":0.985,"close":1.04},
    {"time":"t3","open":1.04,"high":1.04,"low":1.03,"close":1.035},
])
ok, reason = candle_confirms_retest(buy_rates, SignalType.BUY, 1.01)
assert ok, reason
print("OK BUY candle", reason)

sell_rates = pd.DataFrame([
    {"time":"t0","open":1.00,"high":1.02,"low":0.99,"close":1.00},
    {"time":"t1","open":1.00,"high":1.02,"low":0.99,"close":1.01},
    {"time":"t2","open":1.01,"high":1.015,"low":0.96,"close":0.97},
    {"time":"t3","open":0.97,"high":0.98,"low":0.96,"close":0.965},
])
ok, reason = candle_confirms_retest(sell_rates, SignalType.SELL, 0.99)
assert ok, reason
print("OK SELL candle", reason)

print("\nQA_STATIC_OK")
