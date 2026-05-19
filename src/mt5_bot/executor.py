from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace as _replace
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from mt5_bot.config import BotConfig, ExecutionConfig, RiskConfig
from mt5_bot.risk import calculate_volume, normalize_volume, pip_size, prices_for_order
from mt5_bot.strategy import Signal, SignalType


_log = logging.getLogger("mt5_bot")

MT5_BUY_POSITION  = 0
MT5_SELL_POSITION = 1
MT5_COMMENT_MAX_LENGTH = 31


@dataclass
class ExecutionResult:
    status: str
    reason: str
    request: Optional[dict[str, Any]] = None
    result: Any = None


# ─────────────────────────────────────────────────────────────────────────────
# Position helpers
# ─────────────────────────────────────────────────────────────────────────────

def should_open_new_position(positions, symbol: str, magic: int, max_open_positions: int) -> bool:
    matching = [p for p in positions if p.symbol == symbol and int(p.magic) == int(magic)]
    return len(matching) < max_open_positions


def opposite_position_type(signal_type: SignalType) -> int:
    if signal_type is SignalType.BUY:
        return MT5_SELL_POSITION
    if signal_type is SignalType.SELL:
        return MT5_BUY_POSITION
    raise ValueError("NONE signal has no opposite position type")


def position_matches_signal(position, signal_type: SignalType) -> bool:
    return (
        (signal_type is SignalType.BUY  and int(position.type) == MT5_BUY_POSITION) or
        (signal_type is SignalType.SELL and int(position.type) == MT5_SELL_POSITION)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Order builders
# ─────────────────────────────────────────────────────────────────────────────

def build_close_position_request(
    position, symbol: str, bid: float, ask: float,
    execution: ExecutionConfig, mt5_constants: dict[str, int],
) -> dict[str, Any]:
    is_buy = int(position.type) == MT5_BUY_POSITION
    close_type = mt5_constants["ORDER_TYPE_SELL"] if is_buy else mt5_constants["ORDER_TYPE_BUY"]
    price = bid if is_buy else ask
    filling_names = filling_mode_names(execution, mt5_constants)
    if not filling_names:
        raise ValueError(f"No supported MT5 filling constants for mode: {execution.filling_mode}")
    filling_key = f"ORDER_FILLING_{filling_names[0]}"
    return {
        "action":       mt5_constants["TRADE_ACTION_DEAL"],
        "symbol":       symbol,
        "volume":       float(position.volume),
        "type":         close_type,
        "position":     int(position.ticket),
        "price":        price,
        "deviation":    execution.deviation,
        "magic":        execution.magic,
        "comment":      safe_order_comment("close", filling_names[0]),
        "type_time":    mt5_constants["ORDER_TIME_GTC"],
        "type_filling": mt5_constants[filling_key],
    }


def build_market_order_request(
    signal: Signal,
    symbol: str,
    bid: float,
    ask: float,
    symbol_info,
    risk: RiskConfig,
    execution: ExecutionConfig,
    mt5_constants: dict[str, int],
    equity: float,
) -> dict[str, Any]:
    if signal.type is SignalType.NONE:
        raise ValueError("Cannot build an order for NONE signal")

    order_type = mt5_constants["ORDER_TYPE_BUY"] if signal.type is SignalType.BUY else mt5_constants["ORDER_TYPE_SELL"]
    price = ask if signal.type is SignalType.BUY else bid
    order_prices = prices_for_order(signal.type, price, risk.sl_pips, risk.tp_pips, symbol_info)
    filling_names = filling_mode_names(execution, mt5_constants)
    if not filling_names:
        raise ValueError(f"No supported MT5 filling constants for mode: {execution.filling_mode}")
    filling_key = f"ORDER_FILLING_{filling_names[0]}"

    return {
        "action":       mt5_constants["TRADE_ACTION_DEAL"],
        "symbol":       symbol,
        "volume":       calculate_volume(risk, equity, symbol_info),
        "type":         order_type,
        "price":        round(price, int(symbol_info.digits)),
        "sl":           order_prices.sl,
        "tp":           order_prices.tp,
        "deviation":    execution.deviation,
        "magic":        execution.magic,
        "comment":      safe_order_comment(_signal_comment_token(signal.type), filling_names[0]),
        "type_time":    mt5_constants["ORDER_TIME_GTC"],
        "type_filling": mt5_constants[filling_key],
    }


def filling_mode_names(execution: ExecutionConfig, mt5_constants: dict[str, int]) -> list[str]:
    requested = execution.filling_mode.upper()
    candidates = ["RETURN", "IOC", "FOK"] if requested == "AUTO" else [requested]
    return [name for name in candidates if f"ORDER_FILLING_{name}" in mt5_constants]


def with_filling_mode(request: dict[str, Any], filling_name: str, mt5_constants: dict[str, int]) -> dict[str, Any]:
    patched = dict(request)
    patched["type_filling"] = mt5_constants[f"ORDER_FILLING_{filling_name}"]
    token = _comment_token_from_existing(str(request.get("comment", "mt5bot")))
    patched["comment"] = safe_order_comment(token, filling_name)
    return patched


def safe_order_comment(token: str, filling_name: str) -> str:
    fill_tok = {"RETURN": "ret", "IOC": "ioc", "FOK": "fok"}.get(filling_name.upper(), filling_name.lower()[:3])
    cleaned = "".join(c for c in token.lower() if c.isalnum() or c == "_")[:12] or "ord"
    return f"mt5bot_{cleaned}_{fill_tok}"[:MT5_COMMENT_MAX_LENGTH]


def _signal_comment_token(signal_type: SignalType) -> str:
    return {"BUY": "buy", "SELL": "sell"}.get(signal_type.value, "none")


def _comment_token_from_existing(comment: str) -> str:
    c = comment.lower()
    if "close" in c:   return "close"
    if "sell" in c or "below" in c: return "sell"
    if "buy"  in c or "above" in c: return "buy"
    return "ord"


def _is_successful_check(check) -> bool:
    return getattr(check, "retcode", None) in {0, 10008, 10009}


def _is_successful_send(result) -> bool:
    return getattr(result, "retcode", None) in {0, 10008, 10009}


# ─────────────────────────────────────────────────────────────────────────────
# TradeExecutor
# ─────────────────────────────────────────────────────────────────────────────

class TradeExecutor:
    def __init__(self, gateway, storage, config: BotConfig):
        self.gateway = gateway
        self.storage = storage
        self.config  = config
        self.last_trade_monotonic = 0.0
        self.last_reverse_close_monotonic = 0.0
        # Track which position tickets have already been partially closed
        self._partial_closed_tickets: set[int] = set()

    # ── Main execute ──────────────────────────────────────────────────────────

    def execute(self, signal: Signal) -> ExecutionResult:
        """Evaluate the signal and send an order if all checks pass."""
        positions    = self.gateway.positions_get(symbol=self.config.symbol) or []
        own_positions = [p for p in positions if int(p.magic) == self.config.execution.magic]

        tick         = self.gateway.symbol_info_tick(self.config.symbol)
        symbol_info  = self.gateway.symbol_info(self.config.symbol)
        account      = self.gateway.account_info()

        # ── 1. Profit-target close ────────────────────────────────────────────
        if getattr(self.config, "profit_target_usd", None) is not None:
            for position in own_positions:
                if float(position.profit) >= self.config.profit_target_usd:
                    _log.info(
                        "Profit target hit: position=%s profit=%.2f >= target=%.2f — closing",
                        position.ticket, position.profit, self.config.profit_target_usd,
                    )
                    close_base = build_close_position_request(
                        position=position,
                        symbol=self.config.symbol,
                        bid=float(tick.bid), ask=float(tick.ask),
                        execution=self.config.execution,
                        mt5_constants=self.gateway.constants(),
                    )
                    close_req, close_chk = self._first_valid_order_check(close_base)
                    if close_req is None or close_chk is None:
                        return ExecutionResult("rejected", "profit_close_invalid_fill", close_base, None)
                    if not _is_successful_check(close_chk):
                        return ExecutionResult("rejected", f"profit_close_retcode_{getattr(close_chk, 'retcode', '?')}", close_req, close_chk)
                    if not self.config.execution.trade_enabled:
                        return ExecutionResult("dry_run", "profit_target_hit_dry", close_req, close_chk)
                    close_result = self.gateway.order_send(close_req)
                    self._record_order_result(close_req, close_result, symbol_info)
                    self.last_trade_monotonic = time.monotonic()
                    return ExecutionResult("sent", f"profit_target_hit_retcode_{getattr(close_result, 'retcode', '?')}", close_req, close_result)

        # ── 2. No signal → skip ───────────────────────────────────────────────
        if signal.type is SignalType.NONE:
            return ExecutionResult("skipped", signal.reason)

        # ── 3. Cooldown guard ─────────────────────────────────────────────────
        elapsed = time.monotonic() - self.last_trade_monotonic
        if elapsed < self.config.cooldown_seconds:
            return ExecutionResult("skipped", "cooldown")

        reverse_elapsed = time.monotonic() - self.last_reverse_close_monotonic
        reverse_cooldown = getattr(self.config, "reverse_cooldown_seconds", 0)
        if reverse_cooldown > 0 and reverse_elapsed < reverse_cooldown:
            remaining = max(0, int(reverse_cooldown - reverse_elapsed))
            return ExecutionResult("skipped", f"reverse_cooldown_{remaining}s")

        max_trades_hour = int(getattr(self.config, "max_trades_per_symbol_per_hour", 0) or 0)
        if max_trades_hour > 0:
            getter = getattr(self.storage, "get_sent_order_count_since", None)
            if getter is not None:
                since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                try:
                    sent_last_hour = getter(self.config.symbol, self.config.execution.magic, since)
                except Exception as exc:
                    _log.warning("Hourly trade count lookup failed: %s", exc)
                    sent_last_hour = 0
                if sent_last_hour >= max_trades_hour:
                    return ExecutionResult("skipped", f"max_trades_per_symbol_hour_{sent_last_hour}")

        # ── 4. Resolve existing positions ─────────────────────────────────────
        close_failed = False
        closed_opposite = False
        for position in own_positions:
            if position_matches_signal(position, signal.type):
                return ExecutionResult("skipped", "same_direction_position")
            close_base = build_close_position_request(
                position=position,
                symbol=self.config.symbol,
                bid=float(tick.bid), ask=float(tick.ask),
                execution=self.config.execution,
                mt5_constants=self.gateway.constants(),
            )
            close_req, close_chk = self._first_valid_order_check(close_base)
            if close_req is None or close_chk is None:
                return ExecutionResult("rejected", "close_check_invalid_fill", close_base, None)
            if not _is_successful_check(close_chk):
                return ExecutionResult("rejected", f"close_check_retcode_{getattr(close_chk, 'retcode', '?')}", close_req, close_chk)
            if self.config.execution.trade_enabled:
                _log.info(
                    "CLOSING opposite position: ticket=%s symbol=%s volume=%.2f profit=%.2f reason=signal_reverse",
                    position.ticket, self.config.symbol, float(position.volume), float(getattr(position, "profit", 0.0)),
                )
                close_result = self.gateway.order_send(close_req)
                self._record_order_result(close_req, close_result, symbol_info)
                # Fix #3: verify close succeeded before opening new position
                close_retcode = getattr(close_result, "retcode", None)
                if close_retcode not in {0, 10008, 10009}:
                    _log.warning(
                        "Close order failed retcode=%s — aborting new entry to avoid double position",
                        close_retcode,
                    )
                    close_failed = True
                else:
                    closed_opposite = True
                    self.last_trade_monotonic = time.monotonic()
                    self.last_reverse_close_monotonic = self.last_trade_monotonic
                    _log.info(
                        "CLOSED opposite position: ticket=%s symbol=%s volume=%.2f profit=%.2f retcode=%s",
                        position.ticket, self.config.symbol, float(position.volume),
                        float(getattr(position, "profit", 0.0)), close_retcode,
                    )
                    # Fix #2: notify Telegram of the closed trade with P&L
                    try:
                        from mt5_bot import notifier
                        profit = float(getattr(position, "profit", 0.0))
                        notifier.trade_closed(
                            symbol=self.config.symbol,
                            profit=profit,
                            magic=self.config.execution.magic,
                            reason="signal_reverse",
                        )
                    except Exception:
                        pass

        if close_failed:
            return ExecutionResult("rejected", "close_failed_skipping_entry")

        if closed_opposite:
            return ExecutionResult("closed_only", "opposite_position_closed_reverse_cooldown", close_req, close_result)

        # Persistent anti-flip guard: if the most recent closed deal for this
        # symbol/magic was a loss, block any fresh entry for the configured
        # reverse cooldown window. This covers broker-side SL exits and bot
        # restarts, not only in-memory signal-reversal closes.
        recent_loss_block = self._recent_loss_cooldown_reason()
        if recent_loss_block:
            return ExecutionResult("skipped", recent_loss_block)

        positions_after_close = [] if own_positions else own_positions
        if not should_open_new_position(
            positions_after_close, self.config.symbol, self.config.execution.magic, self.config.max_open_positions
        ):
            return ExecutionResult("skipped", "position_limit")

        # ── 5. Compute effective risk (ATR-based SL/TP) ───────────────────────
        risk_to_use = self.config.risk
        _strategy = getattr(self.config, "strategy", None)
        if (
            getattr(_strategy, "use_atr_sl_tp", False)
            and signal.atr_pips is not None
            and signal.atr_pips > 0
        ):
            sl_pips = signal.atr_pips * getattr(_strategy, "atr_sl_multiplier", 1.5)
            tp_pips = signal.atr_pips * getattr(_strategy, "atr_tp_multiplier", 3.0)
            risk_to_use = _replace(self.config.risk, sl_pips=sl_pips, tp_pips=tp_pips)
            _log.info("ATR-based SL/TP: atr=%.1f pips → sl=%.1f tp=%.1f pips",
                      signal.atr_pips, sl_pips, tp_pips)

        # ── 6. Build and check new order ──────────────────────────────────────
        base_request = build_market_order_request(
            signal=signal,
            symbol=self.config.symbol,
            bid=float(tick.bid), ask=float(tick.ask),
            symbol_info=symbol_info,
            risk=risk_to_use,
            execution=self.config.execution,
            mt5_constants=self.gateway.constants(),
            equity=float(account.equity),
        )

        firewall_result = self._apply_risk_firewall(base_request, risk_to_use, float(account.equity), symbol_info)
        if firewall_result.status != "ok":
            return ExecutionResult("rejected", firewall_result.reason, firewall_result.request, firewall_result.result)
        guarded_request = firewall_result.request or base_request

        request, check = self._first_valid_order_check(guarded_request)
        if request is None or check is None:
            return ExecutionResult("rejected", "order_check_invalid_fill", guarded_request, None)
        if not _is_successful_check(check):
            return ExecutionResult("rejected", f"order_check_retcode_{getattr(check, 'retcode', '?')}", request, check)

        if not self.config.execution.trade_enabled:
            _log.info(
                "DRY-RUN order: %s vol=%.2f price=%s sl=%s tp=%s trend=%s rsi=%.1f",
                request.get("type"), request.get("volume"), request.get("price"),
                request.get("sl"), request.get("tp"),
                signal.trend_bias, signal.rsi or 0,
            )
            return ExecutionResult("dry_run", "trade_enabled_false", request, check)

        _log.info(
            "OPENING position: symbol=%s side=%s volume=%.2f price=%s sl=%s tp=%s magic=%s",
            self.config.symbol, signal.type.value, float(request.get("volume", 0.0)),
            request.get("price"), request.get("sl"), request.get("tp"), self.config.execution.magic,
        )
        result = self.gateway.order_send(request)
        self._record_order_result(request, result, symbol_info)
        self.last_trade_monotonic = time.monotonic()
        fill_price = getattr(result, "price", None)
        if fill_price is not None and float(fill_price) > 0:
            pip = pip_size(symbol_info)
            slippage = (float(fill_price) - float(request.get("price", fill_price))) / pip
            if signal.type is SignalType.SELL:
                slippage *= -1
            _log.info("Order fill metrics: requested=%s filled=%s slippage=%.2f pips", request.get("price"), fill_price, slippage)
        elif fill_price is not None:
            _log.debug("Order result returned non-actionable fill price=%s; slippage will be left null", fill_price)
        return ExecutionResult("sent", f"order_send_retcode_{getattr(result, 'retcode', '?')}", request, result)

    def _recent_loss_cooldown_reason(self) -> str | None:
        cooldown = int(getattr(self.config, "reverse_cooldown_seconds", 0) or 0)
        if cooldown <= 0:
            return None
        getter = getattr(self.storage, "get_latest_losing_exit", None)
        if getter is None:
            return None
        try:
            row = getter(self.config.symbol, self.config.execution.magic)
        except Exception as exc:
            _log.warning("Loss cooldown lookup failed: %s", exc)
            return None
        if not row:
            return None

        created_at = row[0]
        try:
            closed_at = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            if closed_at.tzinfo is None:
                closed_at = closed_at.replace(tzinfo=timezone.utc)
        except Exception:
            return None

        age = (datetime.now(timezone.utc) - closed_at.astimezone(timezone.utc)).total_seconds()
        if 0 <= age < cooldown:
            remaining = max(0, int(cooldown - age))
            return f"loss_reentry_cooldown_{remaining}s"
        return None

    # ── Partial close engine ──────────────────────────────────────────────────

    def manage_partial_close(self, atr_pips: Optional[float] = None) -> list[ExecutionResult]:
        """Close partial_close_ratio of position when profit reaches breakeven_atr_mult * ATR.

        Fires once per position (tracked via _partial_closed_tickets).
        """
        if not self.config.use_partial_close:
            return []
        if not atr_pips or atr_pips <= 0:
            return []

        results: list[ExecutionResult] = []
        try:
            positions     = self.gateway.positions_get(symbol=self.config.symbol) or []
            own_positions = [p for p in positions
                             if int(p.magic) == self.config.execution.magic]
            if not own_positions:
                return []

            tick        = self.gateway.symbol_info_tick(self.config.symbol)
            symbol_info = self.gateway.symbol_info(self.config.symbol)
            pip         = pip_size(symbol_info)
            digits      = int(symbol_info.digits)
            constants   = self.gateway.constants()
            trigger_pips = atr_pips * self.config.strategy.breakeven_atr_multiplier

            for position in own_positions:
                ticket = int(position.ticket)
                if ticket in self._partial_closed_tickets:
                    continue

                is_buy      = int(position.type) == MT5_BUY_POSITION
                entry_price = float(position.price_open)
                cur_price   = float(tick.bid) if is_buy else float(tick.ask)
                volume      = float(position.volume)

                profit_pips = (
                    (cur_price - entry_price) / pip if is_buy
                    else (entry_price - cur_price) / pip
                )

                if profit_pips < trigger_pips:
                    continue

                step      = float(symbol_info.volume_step)
                min_vol   = float(symbol_info.volume_min)
                close_vol = max(min_vol, round(volume * self.config.partial_close_ratio / step) * step)
                close_vol = round(min(close_vol, volume - min_vol), 2)

                if close_vol <= 0 or close_vol >= volume:
                    continue

                close_type = constants["ORDER_TYPE_SELL"] if is_buy else constants["ORDER_TYPE_BUY"]
                price      = float(tick.bid) if is_buy else float(tick.ask)
                filling_names = filling_mode_names(self.config.execution, constants)
                if not filling_names:
                    continue
                fill_key = f"ORDER_FILLING_{filling_names[0]}"

                partial_req = {
                    "action":       constants["TRADE_ACTION_DEAL"],
                    "symbol":       self.config.symbol,
                    "volume":       close_vol,
                    "type":         close_type,
                    "position":     ticket,
                    "price":        round(price, digits),
                    "deviation":    self.config.execution.deviation,
                    "magic":        self.config.execution.magic,
                    "comment":      safe_order_comment("partial", filling_names[0]),
                    "type_time":    constants["ORDER_TIME_GTC"],
                    "type_filling": constants[fill_key],
                }

                _log.info(
                    "Partial close: ticket=%s profit_pips=%.1f vol_close=%.2f/%.2f",
                    ticket, profit_pips, close_vol, volume,
                )

                if self.config.execution.trade_enabled:
                    partial_req, partial_chk = self._first_valid_order_check(partial_req)
                    if partial_req is None or partial_chk is None:
                        results.append(ExecutionResult("rejected", "partial_close_invalid_fill", None, None))
                        continue
                    if not _is_successful_check(partial_chk):
                        results.append(ExecutionResult(
                            "rejected",
                            f"partial_close_check_retcode_{getattr(partial_chk, 'retcode', '?')}",
                            partial_req, partial_chk,
                        ))
                        continue
                    try:
                        send_result = self.gateway.order_send(partial_req)
                        self._record_order_result(partial_req, send_result, symbol_info)
                        if _is_successful_send(send_result):
                            self._partial_closed_tickets.add(ticket)
                            results.append(ExecutionResult(
                                "partial_close",
                                f"retcode_{getattr(send_result, 'retcode', '?')}",
                                partial_req, send_result,
                            ))
                        else:
                            results.append(ExecutionResult(
                                "rejected",
                                f"partial_close_send_retcode_{getattr(send_result, 'retcode', '?')}",
                                partial_req, send_result,
                            ))
                    except Exception as exc:
                        _log.warning("Partial close failed: %s", exc)
                        results.append(ExecutionResult("rejected", f"partial_close_exception_{exc}", partial_req, None))
                else:
                    self._partial_closed_tickets.add(ticket)
                    results.append(ExecutionResult(
                        "dry_run",
                        f"partial_close_would_close_{close_vol}_of_{volume}",
                        partial_req, None,
                    ))

        except Exception as exc:
            _log.warning("manage_partial_close error: %s", exc)

        return results

    # ── Trailing stop engine ──────────────────────────────────────────────────

    def manage_trailing_stops(self, atr_pips: Optional[float] = None) -> list[ExecutionResult]:
        """Move SL to breakeven / trail behind price as profit grows."""
        if not self.config.strategy.use_trailing_stop:
            return []
        if not atr_pips or atr_pips <= 0:
            return []

        results: list[ExecutionResult] = []
        try:
            positions    = self.gateway.positions_get(symbol=self.config.symbol) or []
            own_positions = [p for p in positions if int(p.magic) == self.config.execution.magic]
            if not own_positions:
                return []

            tick        = self.gateway.symbol_info_tick(self.config.symbol)
            symbol_info = self.gateway.symbol_info(self.config.symbol)
            pip         = pip_size(symbol_info)
            digits      = int(symbol_info.digits)

            be_threshold    = atr_pips * self.config.strategy.breakeven_atr_multiplier
            trail_threshold = atr_pips * self.config.strategy.trailing_atr_multiplier

            for position in own_positions:
                is_buy       = int(position.type) == MT5_BUY_POSITION
                entry_price  = float(position.price_open)
                current_sl   = float(position.sl)
                current_tp   = float(position.tp)
                cur_price    = float(tick.bid) if is_buy else float(tick.ask)

                profit_pips = (
                    (cur_price - entry_price) / pip if is_buy
                    else (entry_price - cur_price) / pip
                )

                if profit_pips <= 0:
                    continue

                new_sl = current_sl

                if profit_pips >= be_threshold:
                    spread_pips = max(0.0, (float(tick.ask) - float(tick.bid)) / pip)
                    breakeven_buffer_pips = max(1.0, spread_pips + 1.0)
                    be_sl = round(
                        entry_price + breakeven_buffer_pips * pip
                        if is_buy else entry_price - breakeven_buffer_pips * pip,
                        digits,
                    )
                    if is_buy and (current_sl == 0 or be_sl > current_sl):
                        new_sl = be_sl
                    elif not is_buy and (current_sl == 0 or be_sl < current_sl):
                        new_sl = be_sl

                if profit_pips >= trail_threshold:
                    trail_dist = trail_threshold * pip
                    if is_buy:
                        trail_sl = round(cur_price - trail_dist, digits)
                        if trail_sl > new_sl:
                            new_sl = trail_sl
                    else:
                        trail_sl = round(cur_price + trail_dist, digits)
                        if new_sl == 0 or trail_sl < new_sl:
                            new_sl = trail_sl

                if new_sl == current_sl or new_sl == 0:
                    continue

                _log.info(
                    "Trailing stop: ticket=%s profit_pips=%.1f old_sl=%.5f new_sl=%.5f",
                    position.ticket, profit_pips, current_sl, new_sl,
                )

                if self.config.execution.trade_enabled:
                    try:
                        modify_result = self.gateway.order_modify(int(position.ticket), new_sl, current_tp)
                        results.append(ExecutionResult(
                            "trailing_stop",
                            f"sl_updated_retcode_{getattr(modify_result, 'retcode', '?')}",
                            None, modify_result,
                        ))
                    except Exception as exc:
                        _log.warning("Trailing stop modify failed: %s", exc)
                else:
                    results.append(ExecutionResult(
                        "dry_run", f"trailing_stop_sl_would_be_{new_sl}", None, None,
                    ))

        except Exception as exc:
            _log.warning("manage_trailing_stops error: %s", exc)

        return results

    # ── Position telemetry + time stop ───────────────────────────────────────

    def record_position_metrics(self) -> list[ExecutionResult]:
        """Persist MFE/MAE-style telemetry for currently open positions."""
        results: list[ExecutionResult] = []
        recorder = getattr(self.storage, "record_position_metrics", None)
        if recorder is None:
            return results
        try:
            positions = self.gateway.positions_get(symbol=self.config.symbol) or []
            own_positions = [p for p in positions if int(p.magic) == self.config.execution.magic]
            pruner = getattr(self.storage, "prune_position_metrics", None)
            if pruner is not None:
                open_tickets = {int(p.ticket) for p in own_positions}
                removed = pruner(self.config.symbol, self.config.execution.magic, open_tickets)
                if removed:
                    results.append(ExecutionResult("telemetry", f"stale_position_metrics_pruned_{removed}"))
            if not own_positions:
                return results
            tick = self.gateway.symbol_info_tick(self.config.symbol)
            symbol_info = self.gateway.symbol_info(self.config.symbol)
            pip = pip_size(symbol_info)
            for position in own_positions:
                is_buy = int(position.type) == MT5_BUY_POSITION
                current_price = float(tick.bid) if is_buy else float(tick.ask)
                entry_price = float(position.price_open)
                current_pips = (
                    (current_price - entry_price) / pip if is_buy
                    else (entry_price - current_price) / pip
                )
                recorder(position, current_price, current_pips)
                results.append(ExecutionResult("telemetry", f"position_metrics_{int(position.ticket)}"))
        except Exception as exc:
            _log.warning("record_position_metrics error: %s", exc)
        return results

    def manage_time_stops(self) -> list[ExecutionResult]:
        """Close stale positions that failed to move enough after max_position_minutes.

        This prevents M5 scalps from becoming unattended swing trades. It only
        activates when max_position_minutes > 0.
        """
        max_minutes = int(getattr(self.config, "max_position_minutes", 0) or 0)
        if max_minutes <= 0:
            return []
        min_profit_pips = float(getattr(self.config, "time_stop_min_profit_pips", 0.0) or 0.0)
        results: list[ExecutionResult] = []
        try:
            positions = self.gateway.positions_get(symbol=self.config.symbol) or []
            own_positions = [p for p in positions if int(p.magic) == self.config.execution.magic]
            if not own_positions:
                return results
            tick = self.gateway.symbol_info_tick(self.config.symbol)
            symbol_info = self.gateway.symbol_info(self.config.symbol)
            pip = pip_size(symbol_info)
            constants = self.gateway.constants()
            now_ts = datetime.now(timezone.utc).timestamp()
            for position in own_positions:
                opened_ts = float(getattr(position, "time", 0) or 0)
                if opened_ts <= 0:
                    continue
                age_minutes = (now_ts - opened_ts) / 60.0
                if age_minutes < max_minutes:
                    continue
                is_buy = int(position.type) == MT5_BUY_POSITION
                current_price = float(tick.bid) if is_buy else float(tick.ask)
                entry_price = float(position.price_open)
                profit_pips = (
                    (current_price - entry_price) / pip if is_buy
                    else (entry_price - current_price) / pip
                )
                if profit_pips > min_profit_pips:
                    continue
                close_base = build_close_position_request(
                    position=position,
                    symbol=self.config.symbol,
                    bid=float(tick.bid), ask=float(tick.ask),
                    execution=self.config.execution,
                    mt5_constants=constants,
                )
                close_req, close_chk = self._first_valid_order_check(close_base)
                if close_req is None or close_chk is None:
                    results.append(ExecutionResult("rejected", "time_stop_invalid_fill", close_base, None))
                    continue
                if not _is_successful_check(close_chk):
                    results.append(ExecutionResult(
                        "rejected", f"time_stop_check_retcode_{getattr(close_chk, 'retcode', '?')}", close_req, close_chk,
                    ))
                    continue
                _log.info(
                    "Time stop closing stale position: ticket=%s age=%.1fmin profit_pips=%.1f threshold=%.1f",
                    position.ticket, age_minutes, profit_pips, min_profit_pips,
                )
                if self.config.execution.trade_enabled:
                    send_result = self.gateway.order_send(close_req)
                    self._record_order_result(close_req, send_result, symbol_info)
                    results.append(ExecutionResult("time_stop", f"retcode_{getattr(send_result, 'retcode', '?')}", close_req, send_result))
                else:
                    results.append(ExecutionResult("dry_run", "time_stop_would_close", close_req, close_chk))
        except Exception as exc:
            _log.warning("manage_time_stops error: %s", exc)
        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _record_order_result(self, request: dict[str, Any], result, symbol_info=None) -> None:
        try:
            self.storage.record_order_result(request, result, symbol_info=symbol_info)
        except TypeError:
            self.storage.record_order_result(request, result)

    def _apply_risk_firewall(self, request: dict[str, Any], risk: RiskConfig, equity: float, symbol_info) -> ExecutionResult:
        """Cap/verify real cash loss to SL before an entry reaches MT5.

        Long-term goal: allow aggressive testing, but make the maximum loss
        measurable by the broker itself (`order_calc_profit`) rather than only
        inferred from tick metadata. If the requested volume is too large, reduce
        it to the largest valid volume inside risk. If even minimum volume is too
        risky, reject the trade.
        """
        guarded = dict(request)
        original_volume = float(guarded.get("volume", 0.0) or 0.0)
        if original_volume <= 0:
            return ExecutionResult("rejected", "risk_firewall_invalid_volume", guarded)

        max_order_volume = float(getattr(self.config, "max_order_volume", 0.0) or 0.0)
        if max_order_volume > 0 and original_volume > max_order_volume:
            capped = normalize_volume(max_order_volume, symbol_info)
            if capped <= 0:
                return ExecutionResult("rejected", "risk_firewall_invalid_volume_cap", guarded)
            guarded["volume"] = capped
            _log.warning(
                "Risk firewall volume cap: symbol=%s original=%.2f capped=%.2f max_order_volume=%.2f",
                self.config.symbol, original_volume, capped, max_order_volume,
            )

        if not bool(getattr(self.config, "risk_firewall_enabled", True)):
            return ExecutionResult("ok", "risk_firewall_disabled", guarded)

        calc = getattr(self.gateway, "order_calc_profit", None)
        if calc is None:
            return ExecutionResult("rejected", "risk_firewall_no_order_calc_profit", guarded)

        price = float(guarded.get("price", 0.0) or 0.0)
        sl = float(guarded.get("sl", 0.0) or 0.0)
        order_type = int(guarded.get("type"))
        if price <= 0 or sl <= 0:
            return ExecutionResult("rejected", "risk_firewall_missing_price_or_sl", guarded)

        allowed_loss = equity * (float(risk.risk_pct) / 100.0) * float(getattr(self.config, "risk_firewall_tolerance", 1.15) or 1.15)
        if allowed_loss <= 0:
            return ExecutionResult("rejected", "risk_firewall_invalid_allowed_loss", guarded)

        try:
            projected = float(calc(order_type, self.config.symbol, float(guarded["volume"]), price, sl))
        except Exception as exc:
            _log.warning("Risk firewall order_calc_profit failed: %s", exc)
            return ExecutionResult("rejected", "risk_firewall_calc_failed", guarded, exc)

        projected_loss = max(0.0, -projected)
        if projected_loss <= allowed_loss:
            _log.info(
                "Risk firewall OK: symbol=%s volume=%.2f projected_loss=%.2f allowed=%.2f",
                self.config.symbol, float(guarded["volume"]), projected_loss, allowed_loss,
            )
            return ExecutionResult("ok", "risk_firewall_ok", guarded, {"projected_loss": projected_loss, "allowed_loss": allowed_loss})

        # Auto-reduce volume using broker-calculated loss per lot.
        current_volume = float(guarded["volume"])
        if current_volume <= 0:
            return ExecutionResult("rejected", "risk_firewall_invalid_volume", guarded)
        loss_per_lot = projected_loss / current_volume if projected_loss > 0 else 0.0
        if loss_per_lot <= 0:
            return ExecutionResult("rejected", "risk_firewall_invalid_loss_per_lot", guarded)
        target_volume = allowed_loss / loss_per_lot
        reduced = normalize_volume(target_volume, symbol_info)
        min_volume = float(getattr(symbol_info, "volume_min", 0.0) or 0.0)
        if reduced < min_volume or reduced <= 0:
            _log.warning(
                "Risk firewall reject: symbol=%s min_volume=%.2f projected_loss=%.2f allowed=%.2f",
                self.config.symbol, min_volume, projected_loss, allowed_loss,
            )
            return ExecutionResult("rejected", "risk_firewall_min_volume_too_risky", guarded, {"projected_loss": projected_loss, "allowed_loss": allowed_loss})

        guarded["volume"] = reduced
        try:
            reduced_projected = float(calc(order_type, self.config.symbol, reduced, price, sl))
        except Exception as exc:
            return ExecutionResult("rejected", "risk_firewall_recalc_failed", guarded, exc)
        reduced_loss = max(0.0, -reduced_projected)
        if reduced_loss > allowed_loss:
            return ExecutionResult("rejected", "risk_firewall_reduced_still_too_risky", guarded, {"projected_loss": reduced_loss, "allowed_loss": allowed_loss})
        _log.warning(
            "Risk firewall reduced volume: symbol=%s original=%.2f reduced=%.2f projected_loss=%.2f allowed=%.2f",
            self.config.symbol, original_volume, reduced, reduced_loss, allowed_loss,
        )
        return ExecutionResult("ok", "risk_firewall_reduced_volume", guarded, {"projected_loss": reduced_loss, "allowed_loss": allowed_loss})

    def _first_valid_order_check(self, base_request: dict[str, Any]):
        constants = self.gateway.constants()
        last_request = None
        last_check   = None
        for filling_name in filling_mode_names(self.config.execution, constants):
            request = with_filling_mode(base_request, filling_name, constants)
            check   = self.gateway.order_check(request)
            self.storage.record_order_request(request, check)
            last_request = request
            last_check   = check
            if getattr(check, "retcode", None) != 10030:
                return request, check
        return last_request, last_check
