from __future__ import annotations

import argparse
import logging
import logging.handlers
import time
from dataclasses import replace
from datetime import datetime, time as datetime_time, timezone
from pathlib import Path

from mt5_bot.backtest import run_backtest
from mt5_bot.config import load_config, load_config_from_env
from mt5_bot.executor import TradeExecutor
from mt5_bot.mt5_gateway import MT5Gateway
from mt5_bot import notifier
from mt5_bot.news_filter import is_high_impact_news_nearby
from mt5_bot.portfolio_guard import portfolio_guard_decision, score_portfolio_overlap
from mt5_bot.report import format_report, generate_report
from mt5_bot.report_live import format_pnl_report, get_live_pnl
from mt5_bot.risk import DailyRiskState, is_daily_loss_limit_hit, is_trade_count_limit_hit, spread_pips
from mt5_bot.safety import equity_stop_decision
from mt5_bot.storage import BotStorage
from mt5_bot.strategy import (
    Signal,
    SignalType,
    StrategyConfig,
    candle_confirms_retest,
    detect_signal,
    detect_signal_mtf,
)


LOGGER = logging.getLogger("mt5_bot")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    trade_parser = subparsers.add_parser("trade", help="Run the demo trading loop")
    trade_parser.add_argument("--config", default="config/demo.yaml")
    trade_parser.add_argument("--stop-after-action", action="store_true")
    trade_parser.add_argument("--max-seconds", type=int, default=0)
    trade_parser.add_argument("--trade-enabled", action="store_true")
    trade_parser.add_argument("--db", default=None)
    trade_parser.add_argument("--cooldown-seconds", type=int, default=None)
    trade_parser.add_argument("--poll-seconds", type=int, default=None)
    trade_parser.add_argument("--timeframe", default=None)
    trade_parser.add_argument("--target-equity", type=float, default=None)
    trade_parser.add_argument("--floor-equity", type=float, default=None)

    backtest_parser = subparsers.add_parser("backtest", help="Run a simple MT5 historical backtest")
    backtest_parser.add_argument("--config", default="config/demo.yaml")
    backtest_parser.add_argument("--from", dest="from_date", required=True)
    backtest_parser.add_argument("--to", dest="to_date", required=True)

    report_parser = subparsers.add_parser("report", help="Print metrics from the SQLite database")
    report_parser.add_argument("--db", default="data/trades.sqlite")

    check_parser = subparsers.add_parser("check", help="Connect to MT5 and validate demo readiness")
    check_parser.add_argument("--config", default="config/demo.yaml")

    pnl_parser = subparsers.add_parser(
        "pnl", help="P&L aislado por magic number (consulta MT5 en tiempo real)"
    )
    pnl_parser.add_argument("--config", default="config/pro.yaml")
    pnl_parser.add_argument("--days", type=int, default=1)
    pnl_parser.add_argument("--magic", type=int, default=None)

    args = parser.parse_args(argv)
    setup_logging(log_name=_log_name_for_args(args))

    if args.command == "trade":
        return run_trade(
            args.config,
            stop_after_action=args.stop_after_action,
            max_seconds=args.max_seconds,
            trade_enabled_override=args.trade_enabled,
            db_override=args.db,
            cooldown_seconds_override=args.cooldown_seconds,
            poll_seconds_override=args.poll_seconds,
            timeframe_override=args.timeframe,
            target_equity=args.target_equity,
            floor_equity=args.floor_equity,
        )
    if args.command == "backtest":
        return run_backtest_command(args.config, args.from_date, args.to_date)
    if args.command == "report":
        print(format_report(generate_report(args.db)))
        return 0
    if args.command == "check":
        return run_check(args.config)
    if args.command == "pnl":
        return run_pnl_report(args.config, days=args.days, magic_filter=args.magic)
    return 2


def _log_name_for_args(args: argparse.Namespace) -> str:
    """Return a per-command/per-config log name.

    The 12-bot suite runs many Python processes at the same time. A single
    TimedRotatingFileHandler target (bot_YYYYMMDD.log) causes Windows file-lock
    races at midnight / rollover and emits noisy ``PermissionError`` logging
    errors. Each process already writes to its own redirected bot_<symbol>.log;
    this extra file handler is only for diagnostics, so keep it unique.
    """
    config = getattr(args, "config", None)
    if config:
        stem = Path(str(config)).stem.replace(".", "_").replace(" ", "_")
        return f"{args.command}_{stem}"
    return str(args.command)


def setup_logging(log_dir: str | None = None, log_name: str = "mt5_bot") -> None:
    """Console + rotating file logging (14 days retention)."""
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
    log_path = Path(log_dir or "logs")
    log_path.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    safe_name = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in log_name)
    fh = logging.handlers.TimedRotatingFileHandler(
        filename=log_path / f"{safe_name}_{today}.log",
        when="midnight", backupCount=14, encoding="utf-8", utc=True,
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def run_check(config_path: str) -> int:
    try:
        config = load_config_from_env(config_path)
    except Exception as exc:
        LOGGER.exception("CHECK failed loading config: %s", exc)
        return 1
    gateway = MT5Gateway()
    try:
        _connect_and_validate(gateway, config)
        tick = gateway.symbol_info_tick(config.symbol)
        symbol_info = gateway.symbol_info(config.symbol)
        LOGGER.info(
            "MT5 demo ready: symbol=%s bid=%s ask=%s spread_pips=%.2f",
            config.symbol, tick.bid, tick.ask, spread_pips(tick.bid, tick.ask, symbol_info),
        )
        return 0
    except Exception as exc:
        LOGGER.exception("CHECK failed connecting to MT5: %s", exc)
        return 1
    finally:
        gateway.shutdown()


def run_pnl_report(config_path: str, days: int = 1, magic_filter: int | None = None) -> int:
    """P&L aislado por magic number consultando MT5 en tiempo real."""
    config = load_config_from_env(config_path)
    gateway = MT5Gateway()
    try:
        gateway.initialize(config.account.terminal_path)
        gateway.login(config.account.login, config.account.password, config.account.server)
        results = get_live_pnl(gateway, days=days, magic_filter=magic_filter)
        print(format_pnl_report(results, days))
        return 0
    finally:
        gateway.shutdown()


def run_trade(
    config_path: str,
    stop_after_action: bool = False,
    max_seconds: int = 0,
    trade_enabled_override: bool = False,
    db_override: str | None = None,
    cooldown_seconds_override: int | None = None,
    poll_seconds_override: int | None = None,
    timeframe_override: str | None = None,
    target_equity: float | None = None,
    floor_equity: float | None = None,
) -> int:
    config = load_config_from_env(config_path)
    if trade_enabled_override:
        config = replace(config, execution=replace(config.execution, trade_enabled=True))
    if db_override is not None:
        config = replace(config, database_path=Path(db_override))
    if cooldown_seconds_override is not None:
        config = replace(config, cooldown_seconds=cooldown_seconds_override)
    if poll_seconds_override is not None:
        config = replace(config, poll_seconds=poll_seconds_override)
    if timeframe_override is not None:
        config = replace(config, timeframe=timeframe_override)

    gateway  = MT5Gateway()
    storage  = BotStorage(config.database_path)
    executor = TradeExecutor(gateway, storage, config)
    daily_state: DailyRiskState | None = None
    started_at = time.monotonic()

    trend_bars  = max(config.strategy.trend_ema * 3, 200)
    signal_bars = 300
    use_mtf = config.strategy.use_trend_filter and config.trend_timeframe != config.timeframe

    # â”€â”€ Retest state machine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # When use_retest_filter=True, after a crossover we wait for price to
    # pull back to the slow EMA before entering. pending_retest holds the
    # original crossover signal until the retest fires or is invalidated.
    pending_retest: Signal | None = None
    _adaptive_cooldown: float = 0.0   # extra sleep after a loss

    try:
        _connect_and_validate(gateway, config)
        strategy_config = StrategyConfig(**{
            f: getattr(config.strategy, f)
            for f in StrategyConfig.__dataclass_fields__  # type: ignore[attr-defined]
        })
        use_retest = getattr(config.strategy, "use_retest_filter", False)
        use_candle_confirm = getattr(config.strategy, "use_candle_confirm", False)
        LOGGER.info(
            "Starting PRO loop: symbol=%s tf=%s trend_tf=%s trade_enabled=%s "
            "trend_filter=%s adx_filter=%s rsi_momentum=%s partial_close=%s "
            "trailing_stop=%s atr_sl_tp=%s news_filter=%s retest=%s candle_confirm=%s equity_curve=%s",
            config.symbol, config.timeframe, config.trend_timeframe,
            config.execution.trade_enabled,
            strategy_config.use_trend_filter,
            strategy_config.use_adx_filter,
            strategy_config.use_rsi_momentum,
            config.use_partial_close,
            strategy_config.use_trailing_stop,
            strategy_config.use_atr_sl_tp,
            config.use_news_filter,
            use_retest,
            use_candle_confirm,
            config.use_equity_curve_filter,
        )
        notifier.bot_started(config.symbol, config.timeframe, config.execution.magic)

        while True:
            if max_seconds > 0 and time.monotonic() - started_at >= max_seconds:
                LOGGER.info("Stopped after max_seconds=%s", max_seconds)
                return 0

            # â”€â”€ Weekend gap protection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            now_utc = datetime.now(timezone.utc)
            weekday = now_utc.weekday()   # 0=Mon â€¦ 4=Fri, 5=Sat, 6=Sun
            is_weekend_close = (weekday == 4 and now_utc.hour >= 21) or weekday in {5, 6}
            if is_weekend_close:
                LOGGER.info("Weekend gap protection: markets closed â€” sleeping 5 min")
                time.sleep(300)
                continue

            account = gateway.account_info()
            storage.record_account(account)
            _sync_today_deals(gateway, storage, config.symbol, config.execution.magic)

            stop_decision = equity_stop_decision(
                float(account.equity), target_equity=target_equity, floor_equity=floor_equity,
            )
            if stop_decision.stop:
                LOGGER.warning("Equity stop: reason=%s equity=%.2f", stop_decision.reason, account.equity)
                return 0

            today = datetime.now(timezone.utc).date()
            if daily_state is None or daily_state.day != today:
                daily_state = DailyRiskState(
                    day=today, start_equity=float(account.equity),
                    current_equity=float(account.equity), trades_count=0,
                )
            else:
                daily_state = DailyRiskState(
                    day=daily_state.day, start_equity=daily_state.start_equity,
                    current_equity=float(account.equity), trades_count=daily_state.trades_count,
                )

            tick = gateway.symbol_info_tick(config.symbol)
            symbol_info = gateway.symbol_info(config.symbol)
            current_spread = spread_pips(float(tick.bid), float(tick.ask), symbol_info)
            storage.record_market_metrics(config.symbol, float(tick.bid), float(tick.ask), current_spread)
            LOGGER.info("Balance=%.2f Equity=%.2f Spread=%.2f pips",
                        account.balance, account.equity, current_spread)

            if is_daily_loss_limit_hit(daily_state, config.max_daily_loss_pct):
                LOGGER.warning("Daily loss limit hit. New entries blocked.")
                notifier.daily_limit_hit("daily_loss_pct", float(account.equity), config.symbol)
                _sleep_and_manage_trailing(executor, config, current_spread)
                continue
            if is_trade_count_limit_hit(daily_state, config.max_trades_per_day):
                LOGGER.warning("Daily trade count limit hit. New entries blocked.")
                notifier.daily_limit_hit("max_trades_per_day", float(account.equity), config.symbol)
                _sleep_and_manage_trailing(executor, config, current_spread)
                continue

            if current_spread > config.max_spread_pips:
                LOGGER.info("Spread filter: %.2f > %.2f", current_spread, config.max_spread_pips)
                _sleep_and_manage_trailing(executor, config, current_spread)
                continue

            if config.use_global_risk_guard:
                try:
                    guard = portfolio_guard_decision(config, account, gateway.positions_get())
                    if not guard.allow_new_entry:
                        LOGGER.warning(
                            "Portfolio guard: new entries blocked reason=%s margin_pct=%.1f open_positions=%s",
                            guard.reason, guard.margin_pct, guard.open_positions,
                        )
                        _sleep_and_manage_trailing(executor, config, current_spread)
                        continue
                except Exception as exc:
                    LOGGER.warning("Portfolio guard unavailable: %s", exc)

            if strategy_config.use_session_filter:
                hour_utc = datetime.now(timezone.utc).hour
                in_session1 = strategy_config.session_start_hour <= hour_utc < strategy_config.session_end_hour
                in_session2 = (
                    getattr(strategy_config, "use_session2", False)
                    and getattr(strategy_config, "session2_start_hour", 0) != getattr(strategy_config, "session2_end_hour", 0)
                    and getattr(strategy_config, "session2_start_hour", 0) <= hour_utc < getattr(strategy_config, "session2_end_hour", 0)
                )
                if not (in_session1 or in_session2):
                    LOGGER.info("Session filter: UTC hour=%d outside [%d,%d) and [%d,%d)",
                                hour_utc,
                                strategy_config.session_start_hour, strategy_config.session_end_hour,
                                getattr(strategy_config, "session2_start_hour", 0),
                                getattr(strategy_config, "session2_end_hour", 0))
                    _sleep_and_manage_trailing(executor, config, current_spread)
                    continue

            # â”€â”€ MEJORA 3: News filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if config.use_news_filter:
                if is_high_impact_news_nearby(
                    config.symbol,
                    minutes_before=config.news_minutes_before,
                    minutes_after=config.news_minutes_after,
                ):
                    LOGGER.info("News filter: high-impact event nearby â€” skipping entry")
                    pending_retest = None  # invalidate any pending retest during news
                    _sleep_and_manage_trailing(executor, config, current_spread)
                    continue

            signal_rates = gateway.copy_rates_from_pos(config.symbol, config.timeframe, 0, signal_bars)
            trend_rates  = None
            if use_mtf:
                trend_rates = gateway.copy_rates_from_pos(config.symbol, config.trend_timeframe, 0, trend_bars)

            if use_mtf:
                signal = detect_signal_mtf(signal_rates, trend_rates, strategy_config, symbol=config.symbol)
            else:
                signal = detect_signal(signal_rates, strategy_config)

            storage.record_signal(config.symbol, signal)
            LOGGER.info(
                "Signal=%s reason=%s price=%s trend=%s rsi=%s atr_pips=%s adx=%s",
                signal.type.value, signal.reason, signal.price, signal.trend_bias,
                f"{signal.rsi:.1f}" if signal.rsi else "n/a",
                f"{signal.atr_pips:.1f}" if signal.atr_pips else "n/a",
                f"{signal.adx:.1f}" if signal.adx else "n/a",
            )

            # Partial close at TP1 (every tick, before entry check)
            if signal.atr_pips:
                for pc in executor.manage_partial_close(signal.atr_pips):
                    LOGGER.info("PartialClose status=%s reason=%s", pc.status, pc.reason)
                    if pc.status == "partial_close" and pc.request:
                        notifier.trade_closed(
                            config.symbol, profit=0.0, magic=config.execution.magic,
                            reason="partial_close_tp1",
                            volume=pc.request.get("volume"), partial=True,
                        )

            # Trailing stop (every tick)
            if strategy_config.use_trailing_stop and signal.atr_pips:
                for tr in executor.manage_trailing_stops(signal.atr_pips):
                    LOGGER.info("TrailingStop status=%s reason=%s", tr.status, tr.reason)

            # â”€â”€ Correlation guard â€” reduce risk on correlated pairs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # EURUSD & GBPUSD ~85% correlated. If both signal same direction
            # simultaneously, effective risk doubles. Detect via open positions
            # on correlated magic numbers and halve size if conflict found.
            _correlated_pairs = {
                "EURUSD": [("GBPUSD", 260434), ("AUDUSD", 260437)],
                "GBPUSD": [("EURUSD", 260433), ("AUDUSD", 260437)],
                "AUDUSD": [("EURUSD", 260433), ("GBPUSD", 260434)],
            }
            _corr_risk_factor = 1.0
            if signal.type is not SignalType.NONE and config.symbol in _correlated_pairs:
                try:
                    all_positions = gateway.positions_get()
                    for _corr_sym, _corr_magic in _correlated_pairs[config.symbol]:
                        _corr_pos = [
                            p for p in (all_positions or [])
                            if p.symbol == _corr_sym and int(p.magic) == _corr_magic
                        ]
                        if _corr_pos:
                            _corr_type = int(_corr_pos[0].type)  # 0=buy, 1=sell
                            _same_dir = (
                                (signal.type is SignalType.BUY  and _corr_type == 0) or
                                (signal.type is SignalType.SELL and _corr_type == 1)
                            )
                            if _same_dir:
                                _corr_risk_factor = 0.5
                                LOGGER.info(
                                    "Correlation guard: %s already %s â†’ halving risk for %s",
                                    _corr_sym, signal.type.value, config.symbol,
                                )
                except Exception:
                    pass  # non-blocking

            # â”€â”€ MEJORA 4: Crossover + Retest state machine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # If retest filter is enabled:
            #   - On fresh crossover â†’ save as pending_retest, skip immediate entry
            #   - On subsequent ticks â†’ check if price touched slow EMA
            #   - On opposite crossover â†’ invalidate pending retest
            entry_signal = signal
            own_positions_open = [
                p for p in (gateway.positions_get(symbol=config.symbol) or [])
                if int(p.magic) == config.execution.magic
            ]
            if use_retest and own_positions_open:
                # Do not keep advancing/reconfirming the retest state machine while
                # this bot already owns a position. This prevents noisy repeated
                # "retest confirmed" + "same_direction_position" cycles, while
                # still allowing executor.execute(signal) to close an opposite
                # position if a true reversal signal appears.
                pending_retest = None
            elif use_retest:
                entry_signal = _apply_retest_filter(
                    signal,
                    pending_retest,
                    tick,
                    config.symbol,
                    signal_rates=signal_rates,
                    use_candle_confirm=use_candle_confirm,
                )
                if signal.type is not SignalType.NONE:
                    # Fresh crossover â€” save as pending (wait for retest)
                    pending_retest = signal
                    LOGGER.info("Retest filter: crossover detected, waiting for pullback to slow EMA")
                if entry_signal.type is not SignalType.NONE and entry_signal is not signal:
                    LOGGER.info("Retest filter: retest confirmed â€” entering trade")
                    pending_retest = None  # consumed

            # â”€â”€ MEJORA 5: Equity curve management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # After N consecutive losses, apply lot_reduction_factor to config
            overlap_score = None
            _portfolio_overlap_risk_factor = 1.0
            if entry_signal.type is not SignalType.NONE:
                try:
                    overlap_score = score_portfolio_overlap(config, gateway.positions_get(), entry_signal.type)
                    _portfolio_overlap_risk_factor = overlap_score.risk_multiplier
                    if not overlap_score.allow_new_entry:
                        LOGGER.warning(
                            "Portfolio overlap: blocking %s %s reason=%s details=%s",
                            config.symbol, entry_signal.type.value, overlap_score.reason,
                            ",".join(overlap_score.overlap_reasons) or "n/a",
                        )
                        entry_signal = Signal(
                            SignalType.NONE, entry_signal.price, entry_signal.time,
                            overlap_score.reason, entry_signal.fast_ema, entry_signal.slow_ema,
                            entry_signal.rsi, entry_signal.atr, entry_signal.atr_pips,
                            entry_signal.trend_bias, entry_signal.adx,
                        )
                    elif overlap_score.risk_multiplier < 1.0:
                        LOGGER.info(
                            "Portfolio overlap de-score: symbol=%s risk_multiplier=%.2f penalty=%.1f reason=%s details=%s",
                            config.symbol, overlap_score.risk_multiplier, overlap_score.score_penalty,
                            overlap_score.reason, ",".join(overlap_score.overlap_reasons) or "n/a",
                        )
                except Exception as exc:
                    LOGGER.warning("Portfolio overlap scorer unavailable: %s", exc)
            from dataclasses import replace as dc_replace
            # Positive compounding: for each +5% equity growth over baseline,
            # add +10% to risk, capped at 2.5x. This accelerates winners but
            # keeps a hard ceiling before ADX boost.
            baseline_equity = max(float(getattr(config, "baseline_equity", 102000.0)), 1.0)
            equity_growth_pct = max(0.0, (float(account.equity) - baseline_equity) / baseline_equity * 100.0)
            compound_factor = 1.0 + int(equity_growth_pct // 5.0) * 0.10
            compound_factor = min(compound_factor, 2.5)
            base_risk_pct = config.risk.risk_pct * compound_factor * _portfolio_overlap_risk_factor
            if compound_factor > 1.0:
                LOGGER.info(
                    "Compounding boost: equity=%.2f baseline=%.2f growth=%.1f%% factor=%.2fx risk_pct=%.2f%%",
                    account.equity, baseline_equity, equity_growth_pct, compound_factor, base_risk_pct,
                )

            # Compute adaptive cooldown from consecutive losses
            _consec = storage.get_consecutive_losses(config.symbol, config.execution.magic) if config.use_equity_curve_filter else 0
            if _consec == 1:
                _adaptive_cooldown = 90.0
            elif _consec == 2:
                _adaptive_cooldown = 180.0
            elif _consec >= 3:
                _adaptive_cooldown = 300.0

            # â”€â”€ MEJORA 6: Dynamic ADX risk scaling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Tiered risk: strongest trends get paid, weak trends shrink.
            if entry_signal.adx is not None:
                adx_val = entry_signal.adx
                if adx_val > 50:
                    base_risk_pct = base_risk_pct * 2.0
                    LOGGER.info("ADX extreme boost: adx=%.1f â†’ risk_pct=%.2f%%", adx_val, base_risk_pct)
                elif adx_val > 40:
                    base_risk_pct = base_risk_pct * 1.75
                    LOGGER.info("ADX strong boost: adx=%.1f â†’ risk_pct=%.2f%%", adx_val, base_risk_pct)
                elif adx_val > 30:
                    base_risk_pct = base_risk_pct * 1.25
                    LOGGER.info("ADX boost: adx=%.1f â†’ risk_pct=%.2f%%", adx_val, base_risk_pct)
                elif adx_val < strategy_config.adx_min_value:
                    base_risk_pct = base_risk_pct * 0.75
                    LOGGER.info("ADX reduce: adx=%.1f â†’ risk_pct=%.2f%%", adx_val, base_risk_pct)

            max_loss_hour_pct = getattr(config, "max_loss_per_symbol_per_hour_pct", 0.0)
            if entry_signal.type is not SignalType.NONE and max_loss_hour_pct > 0:
                pnl_last_hour = storage.get_pnl_last_hour(config.symbol, config.execution.magic)
                max_loss_hour_usd = float(account.equity) * max_loss_hour_pct / 100.0
                if pnl_last_hour <= -max_loss_hour_usd:
                    LOGGER.warning(
                        "Hourly symbol loss cap: blocking %s entry. pnl_last_hour=%.2f limit=-%.2f pct=%.2f%%",
                        config.symbol, pnl_last_hour, max_loss_hour_usd, max_loss_hour_pct,
                    )
                    entry_signal = Signal(
                        SignalType.NONE, signal.price, signal.time,
                        "max_loss_per_symbol_per_hour", signal.fast_ema, signal.slow_ema,
                        signal.rsi, signal.atr, signal.atr_pips, signal.trend_bias, signal.adx,
                    )

            exec_config_override = None
            if config.use_equity_curve_filter:
                consecutive_losses = storage.get_consecutive_losses(
                    config.symbol, config.execution.magic
                )
                if consecutive_losses >= config.max_consecutive_losses:
                    LOGGER.warning(
                        "Equity curve filter: %d consecutive losses â€” reducing risk %.0f%%",
                        consecutive_losses, config.lot_reduction_factor * 100,
                    )
                    reduced_risk_pct = base_risk_pct * config.lot_reduction_factor
                    reduced_risk = dc_replace(config.risk, risk_pct=reduced_risk_pct)
                    exec_config_override = dc_replace(config, risk=reduced_risk)
                    executor_override = TradeExecutor(gateway, storage, exec_config_override)
                    executor_override.last_trade_monotonic = executor.last_trade_monotonic
                    executor_override.last_reverse_close_monotonic = executor.last_reverse_close_monotonic
                    result = executor_override.execute(entry_signal)
                    executor.last_trade_monotonic = executor_override.last_trade_monotonic
                    executor.last_reverse_close_monotonic = executor_override.last_reverse_close_monotonic
                else:
                    if base_risk_pct != config.risk.risk_pct:
                        adjusted_risk = dc_replace(config.risk, risk_pct=base_risk_pct)
                        adjusted_config = dc_replace(config, risk=adjusted_risk)
                        executor_override = TradeExecutor(gateway, storage, adjusted_config)
                        executor_override.last_trade_monotonic = executor.last_trade_monotonic
                        executor_override.last_reverse_close_monotonic = executor.last_reverse_close_monotonic
                        result = executor_override.execute(entry_signal)
                        executor.last_trade_monotonic = executor_override.last_trade_monotonic
                        executor.last_reverse_close_monotonic = executor_override.last_reverse_close_monotonic
                    else:
                        result = executor.execute(entry_signal)
            else:
                if base_risk_pct != config.risk.risk_pct:
                    adjusted_risk = dc_replace(config.risk, risk_pct=base_risk_pct)
                    adjusted_config = dc_replace(config, risk=adjusted_risk)
                    executor_override = TradeExecutor(gateway, storage, adjusted_config)
                    executor_override.last_trade_monotonic = executor.last_trade_monotonic
                    executor_override.last_reverse_close_monotonic = executor.last_reverse_close_monotonic
                    result = executor_override.execute(entry_signal)
                    executor.last_trade_monotonic = executor_override.last_trade_monotonic
                    executor.last_reverse_close_monotonic = executor_override.last_reverse_close_monotonic
                else:
                    result = executor.execute(entry_signal)

            LOGGER.info("Execution status=%s reason=%s", result.status, result.reason)
            try:
                rr = None
                if float(config.risk.sl_pips or 0) > 0:
                    rr = float(config.risk.tp_pips) / float(config.risk.sl_pips)
                storage.record_trade_journal(
                    symbol=config.symbol,
                    magic=config.execution.magic,
                    signal=entry_signal,
                    decision="executed" if result.status == "sent" else ("candidate" if entry_signal.type is not SignalType.NONE else "blocked_or_no_signal"),
                    execution_status=result.status,
                    execution_reason=result.reason,
                    risk_pct=base_risk_pct,
                    risk_multiplier=(overlap_score.risk_multiplier if overlap_score else 1.0),
                    portfolio_reason=(overlap_score.reason if overlap_score else "not_scored"),
                    rr=rr,
                    context={
                        "spread_pips": current_spread,
                        "account_equity": float(account.equity),
                        "signal_reason": entry_signal.reason,
                        "trend_bias": entry_signal.trend_bias,
                        "rsi": entry_signal.rsi,
                        "atr_pips": entry_signal.atr_pips,
                        "adx": entry_signal.adx,
                        "overlap_reasons": list(overlap_score.overlap_reasons) if overlap_score else [],
                    },
                )
            except Exception as exc:
                LOGGER.warning("Trade journal write failed: %s", exc)

            if result.status == "sent":
                daily_state = DailyRiskState(
                    daily_state.day, daily_state.start_equity,
                    daily_state.current_equity, daily_state.trades_count + 1,
                )
                if result.request:
                    req = result.request
                    notifier.trade_opened(
                        symbol=config.symbol, direction=entry_signal.type.value,
                        volume=float(req.get("volume", 0)), price=float(req.get("price", 0)),
                        sl=float(req.get("sl", 0)), tp=float(req.get("tp", 0)),
                        magic=config.execution.magic,
                        atr_pips=entry_signal.atr_pips, adx=entry_signal.adx,
                    )

            if stop_after_action and result.status in {"dry_run", "sent", "rejected"}:
                LOGGER.info("Stopped after first action: %s %s", result.status, result.reason)
                return 0

            # â”€â”€ Adaptive cooldown post-loss â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # After a loss, increase wait time to avoid revenge trading
            # and let the market stabilize: 1 lossâ†’90s, 2â†’180s, 3+â†’300s
            if _adaptive_cooldown > 0:
                if max_seconds > 0:
                    remaining = max_seconds - (time.monotonic() - started_at)
                    if remaining <= 0:
                        LOGGER.info("Stopped after max_seconds=%s", max_seconds)
                        return 0
                    sleep_for = min(_adaptive_cooldown, remaining)
                else:
                    sleep_for = _adaptive_cooldown
                LOGGER.info("Adaptive cooldown: sleeping %.0fs after loss streak", sleep_for)
                time.sleep(sleep_for)
                _adaptive_cooldown = 0.0

            if max_seconds > 0 and time.monotonic() - started_at >= max_seconds:
                LOGGER.info("Stopped after max_seconds=%s", max_seconds)
                return 0
            time.sleep(config.poll_seconds)

    except KeyboardInterrupt:
        LOGGER.info("Stopped by user")
        notifier.bot_stopped(config.symbol, "keyboard_interrupt")
        return 0
    except Exception as exc:
        LOGGER.exception("Unhandled exception in trading loop")
        notifier.error_alert(config.symbol, str(exc))
        raise
    finally:
        storage.close()
        gateway.shutdown()


def run_backtest_command(config_path: str, from_date: str, to_date: str) -> int:
    config = load_config_from_env(config_path)
    gateway = MT5Gateway()
    try:
        _connect_and_validate(gateway, config)
        rates = gateway.copy_rates_range(
            config.symbol, config.timeframe, _parse_date(from_date), _parse_date(to_date),
        )
        result = run_backtest(rates, config)
        print(f"trades={result.trades} wins={result.wins} losses={result.losses} net_pips={result.net_pips}")
        return 0
    finally:
        gateway.shutdown()


def _connect_and_validate(gateway, config) -> None:
    gateway.initialize(config.account.terminal_path)
    gateway.login(config.account.login, config.account.password, config.account.server)
    account  = gateway.account_info()
    terminal = gateway.terminal_info()
    account_allowed  = getattr(account, "trade_allowed", True)
    account_expert   = getattr(account, "trade_expert", True)
    terminal_allowed = getattr(terminal, "trade_allowed", True)
    terminal_build   = getattr(terminal, "build", "unknown")
    account_server   = getattr(account, "server", config.account.server)
    LOGGER.info(
        "MT5 permissions: account_server=%s account_trade_allowed=%s "
        "account_trade_expert=%s terminal_trade_allowed=%s terminal_build=%s",
        account_server, account_allowed, account_expert, terminal_allowed, terminal_build,
    )
    if config.account.demo_only:
        trade_mode    = getattr(account, "trade_mode", None)
        demo_constant = getattr(gateway.mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        if demo_constant is not None and trade_mode != demo_constant:
            raise RuntimeError("Refusing to run: account is not DEMO")
        if (
            "demo" not in str(config.account.server).lower()
            and "demo" not in str(getattr(account, "server", "")).lower()
        ):
            raise RuntimeError("Refusing to run: demo_only=true but server does not look like DEMO")
    if not account_allowed:
        raise RuntimeError("Trading is not allowed on this MT5 account")
    if not account_expert:
        raise RuntimeError("Expert trading is not enabled on this MT5 account")
    if not terminal_allowed:
        raise RuntimeError(
            "Trading is not allowed in this MT5 terminal. "
            "Enable 'Trading algoritmico' in the toolbar, then Herramientas > Opciones > "
            "Asesores Expertos and uncheck 'Desactivar el comercio algoritmico a traves de Python'."
        )
    gateway.symbol_select(config.symbol)


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _sync_today_deals(gateway, storage: BotStorage, symbol: str, magic: int | None = None) -> None:
    now   = datetime.now(timezone.utc)
    start = datetime.combine(now.date(), datetime_time.min, tzinfo=timezone.utc)
    try:
        # Pull all account deals for today, not only group=*SYMBOL*. Some MT5
        # terminals/brokers return empty lists for symbol-group filters even
        # when balance changed. INSERT OR IGNORE keeps multi-bot sync safe.
        deals = gateway.history_deals_get(start, now)
        if symbol:
            deals = [d for d in deals if str(getattr(d, "symbol", "")).upper() == symbol.upper()]
        if magic is not None:
            magic_deals = [d for d in deals if int(getattr(d, "magic", 0) or 0) == int(magic)]
            # Some close deals can arrive with magic=0; do not drop everything
            # if the broker omits magic on close.
            deals = magic_deals or deals
        inserted = storage.record_deals(deals)
        if inserted:
            LOGGER.info("Synced %s new history deals", inserted)
    except RuntimeError as exc:
        LOGGER.warning("Could not sync history deals: %s", exc)


def _apply_retest_filter(
    signal: Signal,
    pending: Signal | None,
    tick,
    symbol: str,
    signal_rates=None,
    use_candle_confirm: bool = False,
) -> Signal:
    """Crossover + Retest filter state machine.

    Logic:
    - If there's a pending crossover signal and the current price has
      pulled back to (or through) the slow EMA, trigger entry.
    - If the new signal is in the opposite direction of the pending one,
      invalidate the pending retest.
    - If no pending retest and signal is NONE â†’ return NONE.

    Returns the signal to actually execute (may be the pending one).
    """
    if pending is None or pending.type is SignalType.NONE:
        # No pending retest â€” nothing to check
        return _none_signal("retest_waiting")

    # Opposite crossover invalidates pending retest
    if signal.type is not SignalType.NONE and signal.type is not pending.type:
        return _none_signal("retest_invalidated")

    if pending.slow_ema is None:
        return _none_signal("retest_no_slow_ema")

    current_price = float(tick.bid)  # use bid as conservative estimate

    # Check if price has retraced to within touching distance of slow EMA
    # Tolerance: use ATR-based buffer if available, otherwise 0.5 pips
    from mt5_bot.strategy import _pip_size_for_symbol

    pip = _pip_size_for_symbol(symbol)
    if pending.atr_pips and pending.atr_pips > 0:
        tolerance = pending.atr_pips * 0.3 * pip  # 30% of ATR
    else:
        tolerance = 5 * pip  # ~5 pips default

    slow_ema = pending.slow_ema
    if pending.type is SignalType.BUY:
        # Price should dip down toward slow EMA (from above)
        retest_hit = current_price <= slow_ema + tolerance
    else:
        # Price should rise toward slow EMA (from below)
        retest_hit = current_price >= slow_ema - tolerance

    if retest_hit:
        if use_candle_confirm:
            if signal_rates is None:
                return _none_signal("retest_candle_rates_missing")
            ok, reason = candle_confirms_retest(signal_rates, pending.type, slow_ema)
            if not ok:
                return _none_signal(reason)
            LOGGER.info("Retest candle confirmation: %s", reason)
        return pending
    return _none_signal("retest_pending")


def _none_signal(reason: str) -> Signal:
    from mt5_bot.strategy import Signal, SignalType
    return Signal(
        type=SignalType.NONE, price=None, time=None, reason=reason,
        fast_ema=None, slow_ema=None, rsi=None, atr=None,
    )


def _sleep_and_manage_trailing(executor: TradeExecutor, config, current_spread: float) -> None:
    """Sleep one poll cycle while keeping trailing stops and partial closes active."""
    if config.strategy.use_trailing_stop:
        try:
            signal_rates = executor.gateway.copy_rates_from_pos(
                config.symbol, config.timeframe, 0, 50
            )
            from mt5_bot.strategy import detect_signal, StrategyConfig
            sc = StrategyConfig(**{
                f: getattr(config.strategy, f)
                for f in StrategyConfig.__dataclass_fields__
            })
            sig = detect_signal(signal_rates, sc)
            if sig.atr_pips and sig.atr_pips > 0:
                for tr in executor.manage_trailing_stops(sig.atr_pips):
                    LOGGER.info("TrailingStop (idle) status=%s reason=%s", tr.status, tr.reason)
                if config.use_partial_close:
                    for pc in executor.manage_partial_close(sig.atr_pips):
                        LOGGER.info("PartialClose (idle) status=%s reason=%s", pc.status, pc.reason)
        except Exception as exc:
            LOGGER.debug("Trailing stop during idle: %s", exc)
    time.sleep(config.poll_seconds)


