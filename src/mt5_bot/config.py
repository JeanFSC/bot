from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

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
    terminal_path: Optional[str] = None
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
    trend_ema: int = 50
    use_trend_filter: bool = False
    rsi_period: int = 14
    rsi_buy_max: float = 70
    rsi_sell_min: float = 30
    use_rsi_filter: bool = True
    atr_period: int = 14
    min_atr_pips: float = 1.0
    use_atr_filter: bool = True
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 3.0
    use_atr_sl_tp: bool = False
    session_start_hour: int = 7
    session_end_hour: int = 20
    use_session_filter: bool = False
    session2_start_hour: int = 0
    session2_end_hour: int = 0
    use_session2: bool = False
    adx_period: int = 14
    adx_min_value: float = 25.0
    use_adx_filter: bool = False
    use_rsi_momentum: bool = False
    use_trailing_stop: bool = False
    breakeven_atr_multiplier: float = 1.0
    trailing_atr_multiplier: float = 1.5
    use_retest_filter: bool = False
    retest_timeout_bars: int = 4
    use_candle_confirm: bool = False


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
    trend_timeframe: str = "H1"
    poll_seconds: int = 5
    tick_window_seconds: int = 30
    max_spread_pips: float = 2.0
    max_open_positions: int = 1
    max_order_volume: float = 0.0
    risk_firewall_enabled: bool = True
    risk_firewall_tolerance: float = 1.15
    max_daily_loss_pct: float = 2.0
    max_trades_per_day: int = 20
    max_trades_per_symbol_per_hour: int = 0
    cooldown_seconds: int = 60
    reverse_cooldown_seconds: int = 0
    max_loss_per_symbol_per_hour_pct: float = 0.0
    max_symbol_daily_loss_pct: float = 1.0
    max_symbol_weekly_loss_pct: float = 2.0
    max_effective_risk_pct: float = 1.0
    max_spread_to_sl_ratio: float = 0.25
    min_sl_atr_ratio: float = 0.50
    min_effective_sl_pips: float = 0.0
    profit_lock_enabled: bool = False
    profit_lock_trigger_rr: float = 0.45
    profit_lock_min_pips: float = 0.0
    profit_lock_retrace_rr: float = 0.35
    profit_lock_buffer_pips: float = 0.5
    max_position_minutes: int = 0
    time_stop_min_profit_pips: float = 0.0
    profit_target_usd: Optional[float] = None
    baseline_equity: float = 0.0
    database_path: Path = Path("data/trades.sqlite")
    use_partial_close: bool = False
    partial_close_ratio: float = 0.5
    use_news_filter: bool = False
    news_minutes_before: int = 30
    news_minutes_after: int = 15
    use_equity_curve_filter: bool = False
    max_consecutive_losses: int = 3
    max_symbol_consecutive_losses: int = 1
    lot_reduction_factor: float = 0.5
    # Portfolio-level guardrails. These do NOT cap winning trades; they only
    # block new entries when the whole account is already too exposed.
    use_global_risk_guard: bool = True
    max_total_margin_pct: float = 85.0
    max_portfolio_open_positions: int = 3
    max_same_currency_positions: int = 2
    max_same_direction_theme_positions: int = 1
    account: Optional[AccountConfig] = None
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
    account_raw  = raw.get("account", {})
    risk_raw     = raw.get("risk", {})
    strategy_raw = raw.get("strategy", {})
    execution_raw = raw.get("execution", {})

    account = AccountConfig(
        login=int(os.getenv("MT5_LOGIN", account_raw.get("login", 0))),
        password=os.getenv("MT5_PASSWORD", str(account_raw.get("password", ""))),
        server=os.getenv("MT5_SERVER", str(account_raw.get("server", "MetaQuotes-Demo"))),
        terminal_path=os.getenv("MT5_TERMINAL_PATH", account_raw.get("terminal_path")),
        demo_only=bool(raw.get("demo_only", account_raw.get("demo_only", True))),
    )

    _profit_target_raw = raw.get("profit_target_usd")

    _strategy_fields = {f.name for f in StrategySettings.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    strategy_kwargs = {k: v for k, v in strategy_raw.items() if k in _strategy_fields}

    config = BotConfig(
        symbol=str(raw.get("symbol", "EURUSD")),
        timeframe=str(raw.get("timeframe", "M1")),
        trend_timeframe=str(raw.get("trend_timeframe", "H1")),
        poll_seconds=int(raw.get("poll_seconds", 5)),
        tick_window_seconds=int(raw.get("tick_window_seconds", 30)),
        max_spread_pips=float(raw.get("max_spread_pips", 2.0)),
        max_open_positions=int(raw.get("max_open_positions", 1)),
        max_order_volume=float(raw.get("max_order_volume", 0.0)),
        risk_firewall_enabled=bool(raw.get("risk_firewall_enabled", True)),
        risk_firewall_tolerance=float(raw.get("risk_firewall_tolerance", 1.15)),
        max_daily_loss_pct=float(raw.get("max_daily_loss_pct", 2.0)),
        max_trades_per_day=int(raw.get("max_trades_per_day", 20)),
        max_trades_per_symbol_per_hour=int(raw.get("max_trades_per_symbol_per_hour", 0)),
        cooldown_seconds=int(raw.get("cooldown_seconds", 60)),
        reverse_cooldown_seconds=int(raw.get("reverse_cooldown_seconds", 0)),
        max_loss_per_symbol_per_hour_pct=float(raw.get("max_loss_per_symbol_per_hour_pct", 0.0)),
        max_symbol_daily_loss_pct=float(raw.get("max_symbol_daily_loss_pct", 1.0)),
        max_symbol_weekly_loss_pct=float(raw.get("max_symbol_weekly_loss_pct", 2.0)),
        max_effective_risk_pct=float(raw.get("max_effective_risk_pct", 1.0)),
        max_spread_to_sl_ratio=float(raw.get("max_spread_to_sl_ratio", 0.25)),
        min_sl_atr_ratio=float(raw.get("min_sl_atr_ratio", 0.50)),
        min_effective_sl_pips=float(raw.get("min_effective_sl_pips", 0.0)),
        profit_lock_enabled=bool(raw.get("profit_lock_enabled", False)),
        profit_lock_trigger_rr=float(raw.get("profit_lock_trigger_rr", 0.45)),
        profit_lock_min_pips=float(raw.get("profit_lock_min_pips", 0.0)),
        profit_lock_retrace_rr=float(raw.get("profit_lock_retrace_rr", 0.35)),
        profit_lock_buffer_pips=float(raw.get("profit_lock_buffer_pips", 0.5)),
        max_position_minutes=int(raw.get("max_position_minutes", 0)),
        time_stop_min_profit_pips=float(raw.get("time_stop_min_profit_pips", 0.0)),
        profit_target_usd=float(_profit_target_raw) if _profit_target_raw is not None else None,
        baseline_equity=float(raw["baseline_equity"]) if "baseline_equity" in raw else 0.0,
        database_path=Path(raw.get("database_path", "data/trades.sqlite")),
        use_partial_close=bool(raw.get("use_partial_close", False)),
        partial_close_ratio=float(raw.get("partial_close_ratio", 0.5)),
        use_news_filter=bool(raw.get("use_news_filter", False)),
        news_minutes_before=int(raw.get("news_minutes_before", 30)),
        news_minutes_after=int(raw.get("news_minutes_after", 15)),
        use_equity_curve_filter=bool(raw.get("use_equity_curve_filter", False)),
        max_consecutive_losses=int(raw.get("max_consecutive_losses", 3)),
        max_symbol_consecutive_losses=int(raw.get("max_symbol_consecutive_losses", 1)),
        lot_reduction_factor=float(raw.get("lot_reduction_factor", 0.5)),
        use_global_risk_guard=bool(raw.get("use_global_risk_guard", True)),
        max_total_margin_pct=float(raw.get("max_total_margin_pct", 85.0)),
        max_portfolio_open_positions=int(raw.get("max_portfolio_open_positions", 3)),
        max_same_currency_positions=int(raw.get("max_same_currency_positions", 2)),
        max_same_direction_theme_positions=int(raw.get("max_same_direction_theme_positions", 1)),
        account=account,
        risk=RiskConfig(**risk_raw),
        strategy=StrategySettings(**strategy_kwargs),
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
    from dataclasses import replace
    config = replace(config, account=account)
    validate_config(config)
    return config


def validate_config(config: BotConfig) -> None:
    if config.account is None:
        raise ValueError("Account config is required")
    if config.account.demo_only and "demo" not in config.account.server.lower():
        raise ValueError("demo_only=true requires a demo server name")
    supported_timeframes = {"M1", "M5", "M15", "M30", "H1", "H4"}
    if config.timeframe not in supported_timeframes:
        raise ValueError(f"Unsupported timeframe '{config.timeframe}'. Choose from: {', '.join(sorted(supported_timeframes))}")
    if config.trend_timeframe not in supported_timeframes:
        raise ValueError(f"Unsupported trend_timeframe '{config.trend_timeframe}'.")
    if config.max_order_volume < 0:
        raise ValueError("max_order_volume must be >= 0")
    if config.risk_firewall_tolerance < 1.0:
        raise ValueError("risk_firewall_tolerance must be >= 1.0")
    if config.risk.mode not in {"fixed_lot", "percent_equity"}:
        raise ValueError("risk.mode must be fixed_lot or percent_equity")
    if config.risk.sl_pips <= 0 or config.risk.tp_pips <= 0:
        raise ValueError("SL and TP must be positive")
    if config.max_open_positions != 1:
        raise ValueError("V1 supports exactly one open position")
    if config.poll_seconds < 1:
        raise ValueError("poll_seconds must be >= 1")
    if config.reverse_cooldown_seconds < 0:
        raise ValueError("reverse_cooldown_seconds must be >= 0")
    if config.max_loss_per_symbol_per_hour_pct < 0:
        raise ValueError("max_loss_per_symbol_per_hour_pct must be >= 0")
    if config.baseline_equity <= 0:
        raise ValueError("baseline_equity must be explicitly set to a positive value")
    if config.max_symbol_daily_loss_pct < 0:
        raise ValueError("max_symbol_daily_loss_pct must be >= 0")
    if config.max_symbol_weekly_loss_pct < 0:
        raise ValueError("max_symbol_weekly_loss_pct must be >= 0")
    if config.max_symbol_consecutive_losses < 0:
        raise ValueError("max_symbol_consecutive_losses must be >= 0")
    if config.max_effective_risk_pct <= 0:
        raise ValueError("max_effective_risk_pct must be > 0")
    if config.max_spread_to_sl_ratio < 0:
        raise ValueError("max_spread_to_sl_ratio must be >= 0")
    if config.min_sl_atr_ratio < 0:
        raise ValueError("min_sl_atr_ratio must be >= 0")
    if config.min_effective_sl_pips < 0:
        raise ValueError("min_effective_sl_pips must be >= 0")
    if not (0.0 < config.profit_lock_trigger_rr <= 1.0):
        raise ValueError("profit_lock_trigger_rr must be > 0 and <= 1")
    if config.profit_lock_min_pips < 0:
        raise ValueError("profit_lock_min_pips must be >= 0")
    if not (0.0 < config.profit_lock_retrace_rr <= 1.0):
        raise ValueError("profit_lock_retrace_rr must be > 0 and <= 1")
    if config.profit_lock_buffer_pips < 0:
        raise ValueError("profit_lock_buffer_pips must be >= 0")
    if config.max_same_direction_theme_positions < 0:
        raise ValueError("max_same_direction_theme_positions must be >= 0")
    if not (0.0 < config.partial_close_ratio < 1.0):
        raise ValueError("partial_close_ratio must be between 0 and 1 (exclusive)")
