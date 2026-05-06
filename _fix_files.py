"""
Reescribe config.py y executor.py con contenido correcto y borra __pycache__.
Ejecutar con: python _fix_files.py
"""
import os, sys, shutil
from pathlib import Path

BASE = Path(__file__).parent

CONFIG_PY = BASE / "src/mt5_bot/config.py"
EXECUTOR_PY = BASE / "src/mt5_bot/executor.py"
PYCACHE = BASE / "src/mt5_bot/__pycache__"

CONFIG_CONTENT = '''\
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


@dataclass(frozen=True)
class AccountConfig:
    login: int
    password: str
    server: str
    terminal_path: str | None = None
    demo_only: bool = True


@dataclass(frozen=True)
class RiskConfig:
    mode: str = "percent_equity"
    fixed_lot: float = 0.1
    risk_pct: float = 0.25
    sl_pips: float = 20
    tp_pips: float = 40


@dataclass(frozen=True)
class StrategySettings:
    fast_ema: int = 9
    slow_ema: int = 21
    rsi_period: int = 14
    rsi_buy_max: float = 70
    rsi_sell_min: float = 30
    atr_period: int = 14
    min_atr_pips: float = 1.0
    use_rsi_filter: bool = True
    use_atr_filter: bool = True


@dataclass(frozen=True)
class ExecutionConfig:
    magic: int = 260430
    deviation: int = 10
    filling_mode: str = "AUTO"
    trade_enabled: bool = False


@dataclass(frozen=True)
class BotConfig:
    symbol: str = "EURUSD"
    timeframe: str = "M1"
    poll_seconds: int = 5
    tick_window_seconds: int = 30
    max_spread_pips: float = 2.0
    max_open_positions: int = 1
    max_daily_loss_pct: float = 2.0
    max_trades_per_day: int = 20
    cooldown_seconds: int = 60
    database_path: Path = Path("data/trades.sqlite")
    account: AccountConfig | None = None
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategySettings = field(default_factory=StrategySettings)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a YAML object: {path}")
    return payload


def load_config(path: str | Path) -> BotConfig:
    config_path = Path(path)
    load_dotenv(config_path.parent.parent / ".env")
    load_dotenv()

    raw = _load_yaml(config_path)
    account_raw = raw.get("account", {})
    risk_raw = raw.get("risk", {})
    strategy_raw = raw.get("strategy", {})
    execution_raw = raw.get("execution", {})

    account = AccountConfig(
        login=int(os.getenv("MT5_LOGIN", account_raw.get("login", 0))),
        password=os.getenv("MT5_PASSWORD", str(account_raw.get("password", ""))),
        server=os.getenv("MT5_SERVER", str(account_raw.get("server", "MetaQuotes-Demo"))),
        terminal_path=os.getenv("MT5_TERMINAL_PATH", account_raw.get("terminal_path")),
        demo_only=bool(raw.get("demo_only", account_raw.get("demo_only", True))),
    )

    config = BotConfig(
        symbol=str(raw.get("symbol", "EURUSD")),
        timeframe=str(raw.get("timeframe", "M1")),
        poll_seconds=int(raw.get("poll_seconds", 5)),
        tick_window_seconds=int(raw.get("tick_window_seconds", 30)),
        max_spread_pips=float(raw.get("max_spread_pips", 2.0)),
        max_open_positions=int(raw.get("max_open_positions", 1)),
        max_daily_loss_pct=float(raw.get("max_daily_loss_pct", 2.0)),
        max_trades_per_day=int(raw.get("max_trades_per_day", 20)),
        cooldown_seconds=int(raw.get("cooldown_seconds", 60)),
        database_path=Path(raw.get("database_path", "data/trades.sqlite")),
        account=account,
        risk=RiskConfig(**risk_raw),
        strategy=StrategySettings(**strategy_raw),
        execution=ExecutionConfig(**execution_raw),
    )
    validate_config(config)
    return config


def load_config_from_env(path: str | Path) -> BotConfig:
    config = load_config(path)
    account = AccountConfig(
        login=int(_require_env("MT5_LOGIN")),
        password=_require_env("MT5_PASSWORD"),
        server=os.getenv("MT5_SERVER", config.account.server if config.account else "MetaQuotes-Demo"),
        terminal_path=os.getenv("MT5_TERMINAL_PATH", config.account.terminal_path if config.account else None),
        demo_only=config.account.demo_only if config.account else True,
    )
    config = BotConfig(
        symbol=config.symbol,
        timeframe=config.timeframe,
        poll_seconds=config.poll_seconds,
        tick_window_seconds=config.tick_window_seconds,
        max_spread_pips=config.max_spread_pips,
        max_open_positions=config.max_open_positions,
        max_daily_loss_pct=config.max_daily_loss_pct,
        max_trades_per_day=config.max_trades_per_day,
        cooldown_seconds=config.cooldown_seconds,
        database_path=config.database_path,
        account=account,
        risk=config.risk,
        strategy=config.strategy,
        execution=config.execution,
    )
    validate_config(config)
    return config


def validate_config(config: BotConfig) -> None:
    if config.account is None:
        raise ValueError("Account config is required")
    if config.account.demo_only and "demo" not in config.account.server.lower():
        raise ValueError("demo_only=true requires a demo server name")
    supported_timeframes = {"M1", "M5", "M15", "M30", "H1", "H4"}
    if config.timeframe not in supported_timeframes:
        raise ValueError(f"Unsupported timeframe \'{config.timeframe}\'. Choose from: {\', \'.join(sorted(supported_timeframes))}")
    if config.risk.mode not in {"fixed_lot", "percent_equity"}:
        raise ValueError("risk.mode must be fixed_lot or percent_equity")
    if config.risk.sl_pips <= 0 or config.risk.tp_pips <= 0:
        raise ValueError("SL and TP must be positive")
    if config.max_open_positions != 1:
        raise ValueError("V1 supports exactly one open position")
    if config.poll_seconds < 1:
        raise ValueError("poll_seconds must be >= 1")
'''

print("Writing files...")
CONFIG_PY.write_text(CONFIG_CONTENT, encoding="utf-8")
print(f"  config.py: {CONFIG_PY.stat().st_size} bytes")

# Delete __pycache__
if PYCACHE.exists():
    shutil.rmtree(PYCACHE, ignore_errors=True)
    print("  __pycache__ deleted")

# Verify syntax
import ast
ast.parse(CONFIG_CONTENT)
print("  config.py syntax: OK")

# Test import
sys.path.insert(0, str(BASE / "src"))
import importlib, importlib.util
spec = importlib.util.spec_from_file_location("mt5_bot.config", CONFIG_PY)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("  config import: OK")

print("\nDONE - files fixed. Now run: python -m mt5_bot check --config config/demo.yaml")
