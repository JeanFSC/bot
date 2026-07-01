from datetime import datetime, timezone
from types import SimpleNamespace

from mt5_bot.config import ExecutionConfig, RiskConfig
from mt5_bot.executor import TradeExecutor, build_market_order_request, should_open_new_position, with_filling_mode
from mt5_bot.risk import calculate_volume
from mt5_bot.strategy import Signal, SignalType


def _symbol_info():
    return SimpleNamespace(
        digits=5,
        point=0.00001,
        trade_tick_value=1.0,
        trade_tick_size=0.00001,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
    )


def test_should_not_open_second_position_for_same_symbol_and_magic():
    positions = [SimpleNamespace(symbol="EURUSD", magic=260430, type=0)]

    assert not should_open_new_position(positions, symbol="EURUSD", magic=260430, max_open_positions=1)


def test_build_buy_market_order_request_contains_mt5_fields():
    signal = Signal(type=SignalType.BUY, price=1.1000, time=None, reason="ema_cross_above", fast_ema=1.1, slow_ema=1.099, rsi=55, atr=0.0005)
    risk = RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.25, sl_pips=20, tp_pips=40)
    execution = ExecutionConfig(magic=260430, deviation=10, filling_mode="RETURN")

    request = build_market_order_request(
        signal=signal,
        symbol="EURUSD",
        bid=1.0999,
        ask=1.1000,
        symbol_info=_symbol_info(),
        risk=risk,
        execution=execution,
        mt5_constants={
            "TRADE_ACTION_DEAL": 1,
            "ORDER_TYPE_BUY": 0,
            "ORDER_TYPE_SELL": 1,
            "ORDER_TIME_GTC": 0,
            "ORDER_FILLING_RETURN": 2,
        },
        equity=10_000,
    )

    assert request["action"] == 1
    assert request["symbol"] == "EURUSD"
    assert request["type"] == 0
    assert request["price"] == 1.1000
    assert request["sl"] == 1.0980
    assert request["tp"] == 1.1040
    assert request["volume"] == 0.1
    assert request["magic"] == 260430
    assert request["type_time"] == 0
    assert request["type_filling"] == 2


def test_metal_position_size_uses_contract_value_floor_when_tick_value_is_underreported():
    symbol_info = SimpleNamespace(
        digits=2,
        point=0.01,
        trade_tick_value=0.1,   # MetaQuotes demo reports XAUUSD this way.
        trade_tick_size=0.01,
        trade_contract_size=100.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
    )
    risk = RiskConfig(mode="percent_equity", fixed_lot=0.1, risk_pct=0.75, sl_pips=750, tp_pips=1500)

    volume = calculate_volume(risk, equity=80_000, symbol_info=symbol_info)

    assert volume == 0.8


def test_risk_firewall_reduces_oversized_volume_using_broker_loss():
    signal = Signal(type=SignalType.SELL, price=4555.90, time=None, reason="ema_cross_below", fast_ema=4555, slow_ema=4556, rsi=50, atr=5.0)
    gateway = _GatewayWithInvalidFirstFill()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="XAUUSD",
        cooldown_seconds=0,
        reverse_cooldown_seconds=0,
        max_open_positions=1,
        max_order_volume=0.0,
        risk_firewall_enabled=True,
        risk_firewall_tolerance=1.0,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=7.9, risk_pct=0.75, sl_pips=772, tp_pips=1544),
        execution=ExecutionConfig(magic=260436, deviation=20, filling_mode="AUTO", trade_enabled=False),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "dry_run"
    assert result.request["volume"] == 0.09


def test_risk_firewall_applies_hard_volume_cap_before_check():
    signal = Signal(type=SignalType.SELL, price=4555.90, time=None, reason="ema_cross_below", fast_ema=4555, slow_ema=4556, rsi=50, atr=5.0)
    gateway = _GatewayWithInvalidFirstFill()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="XAUUSD",
        cooldown_seconds=0,
        reverse_cooldown_seconds=0,
        max_open_positions=1,
        max_order_volume=1.0,
        risk_firewall_enabled=True,
        risk_firewall_tolerance=20.0,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=7.9, risk_pct=0.75, sl_pips=772, tp_pips=1544),
        execution=ExecutionConfig(magic=260436, deviation=20, filling_mode="AUTO", trade_enabled=False),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "dry_run"
    assert result.request["volume"] == 1.0


def test_executor_auto_filling_retries_after_invalid_fill():
    signal = Signal(type=SignalType.SELL, price=1.1000, time=None, reason="ema_cross_below", fast_ema=1.099, slow_ema=1.1, rsi=45, atr=0.0005)
    gateway = _GatewayWithInvalidFirstFill()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="EURUSD",
        cooldown_seconds=0,
        max_open_positions=1,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.25, sl_pips=20, tp_pips=40),
        execution=ExecutionConfig(magic=260430, deviation=10, filling_mode="AUTO", trade_enabled=False),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "dry_run"
    assert [request["type_filling"] for request in gateway.checked_requests] == [2, 1]


def test_reverse_cooldown_does_not_block_before_any_reverse_close():
    signal = Signal(type=SignalType.SELL, price=1.1000, time=None, reason="ema_cross_below", fast_ema=1.099, slow_ema=1.1, rsi=45, atr=0.0005)
    gateway = _GatewayWithSignedProfit()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="EURUSD",
        cooldown_seconds=0,
        reverse_cooldown_seconds=600,
        max_open_positions=1,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.25, sl_pips=20, tp_pips=40),
        execution=ExecutionConfig(magic=260430, deviation=10, filling_mode="AUTO", trade_enabled=False),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "dry_run"
    assert result.reason == "trade_enabled_false"


def test_executor_rejects_failed_order_send_retcode():
    signal = Signal(type=SignalType.SELL, price=1.1000, time=None, reason="ema_cross_below", fast_ema=1.099, slow_ema=1.1, rsi=45, atr=0.0005)
    gateway = _GatewayOrderSendRejected()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="EURUSD",
        cooldown_seconds=0,
        max_open_positions=1,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.25, sl_pips=20, tp_pips=40),
        execution=ExecutionConfig(magic=260430, deviation=10, filling_mode="AUTO", trade_enabled=True),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "rejected"
    assert result.reason == "order_send_retcode_10027"
    assert gateway.sent_requests


def test_loss_reentry_cooldown_blocks_fresh_entry_after_losing_exit():
    signal = Signal(type=SignalType.SELL, price=1.1000, time=None, reason="ema_cross_below", fast_ema=1.099, slow_ema=1.1, rsi=45, atr=0.0005)
    gateway = _GatewayWithInvalidFirstFill()
    storage = _StorageSpy(latest_losing_exit=(datetime.now(timezone.utc).isoformat(), -690.44, 1, 156.64, 8157374286))
    config = SimpleNamespace(
        symbol="EURUSD",
        cooldown_seconds=0,
        reverse_cooldown_seconds=600,
        max_open_positions=1,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.25, sl_pips=20, tp_pips=40),
        execution=ExecutionConfig(magic=260430, deviation=10, filling_mode="AUTO", trade_enabled=False),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "skipped"
    assert result.reason.startswith("loss_reentry_cooldown_")
    assert gateway.checked_requests == []


def test_filling_retry_keeps_mt5_comment_short():
    request = {"comment": "mt5_bot:ema_cross_above", "type_filling": 2}

    patched = with_filling_mode(request, "RETURN", {"ORDER_FILLING_RETURN": 2})

    assert patched["comment"] == "mt5bot_buy_ret"
    assert len(patched["comment"]) <= 31


def test_partial_close_retries_invalid_fill_before_send():
    gateway = _GatewayForPartialClose()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="XAUUSD",
        use_partial_close=True,
        partial_close_ratio=0.5,
        strategy=SimpleNamespace(breakeven_atr_multiplier=0.8, use_trailing_stop=True),
        execution=ExecutionConfig(magic=260440, deviation=20, filling_mode="AUTO", trade_enabled=True),
    )

    result = TradeExecutor(gateway, storage, config).manage_partial_close(atr_pips=100)[0]

    assert result.status == "partial_close"
    assert [request["type_filling"] for request in gateway.checked_requests] == [2, 1]
    assert gateway.sent_requests[0]["type_filling"] == 1


def test_trailing_breakeven_uses_spread_buffer():
    gateway = _GatewayForTrailingStop()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="XAUUSD",
        strategy=SimpleNamespace(
            use_trailing_stop=True,
            breakeven_atr_multiplier=0.8,
            trailing_atr_multiplier=99.0,
        ),
        execution=ExecutionConfig(magic=260440, deviation=20, filling_mode="AUTO", trade_enabled=True),
    )

    result = TradeExecutor(gateway, storage, config).manage_trailing_stops(atr_pips=100)[0]

    assert result.status == "trailing_stop"
    # Sell entry 4708.08, spread 0.17 = 17 pips, buffer = spread + 1 pip -> SL 4707.90.
    assert gateway.modified[0][1] == 4707.9


def test_execute_applies_minimum_effective_sl_floor():
    signal = Signal(
        type=SignalType.BUY,
        price=1.1000,
        time=None,
        reason="ema_cross_above",
        fast_ema=1.1,
        slow_ema=1.099,
        rsi=55,
        atr=0.0002,
        atr_pips=2.0,
    )
    gateway = _GatewayWithSignedProfit()
    storage = _StorageSpy()
    config = SimpleNamespace(
        symbol="EURUSD",
        cooldown_seconds=0,
        reverse_cooldown_seconds=0,
        max_open_positions=1,
        min_effective_sl_pips=8.0,
        risk_firewall_enabled=True,
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.35, sl_pips=12, tp_pips=24),
        strategy=SimpleNamespace(use_atr_sl_tp=True, atr_sl_multiplier=1.5, atr_tp_multiplier=3.0),
        execution=ExecutionConfig(magic=260430, deviation=10, filling_mode="AUTO", trade_enabled=False),
    )

    result = TradeExecutor(gateway, storage, config).execute(signal)

    assert result.status == "dry_run"
    assert result.request["sl"] == 1.0992
    assert result.request["tp"] == 1.1016
    assert result.metadata["projected_loss"] == 8.0
    assert result.metadata["projected_profit"] == 16.0


def test_profit_lock_closes_after_mfe_retrace():
    gateway = _GatewayForProfitLock(current_bid=1.1006, current_ask=1.1007)
    storage = _StorageSpy(position_metrics={9366528834: {"mfe_pips": 10.0}})
    config = _profit_lock_config()

    result = TradeExecutor(gateway, storage, config).manage_profit_lock(atr_pips=2.0)[0]

    assert result.status == "profit_lock"
    assert result.request["position"] == 9366528834
    assert result.request["type"] == 1
    assert gateway.sent_requests


def test_profit_lock_waits_until_trigger_reached():
    gateway = _GatewayForProfitLock(current_bid=1.1002, current_ask=1.1003)
    storage = _StorageSpy(position_metrics={9366528834: {"mfe_pips": 3.0}})
    config = _profit_lock_config()

    results = TradeExecutor(gateway, storage, config).manage_profit_lock(atr_pips=2.0)

    assert results == []
    assert gateway.sent_requests == []


def _profit_lock_config():
    return SimpleNamespace(
        symbol="EURUSD",
        profit_lock_enabled=True,
        profit_lock_trigger_rr=0.25,
        profit_lock_min_pips=2.0,
        profit_lock_retrace_rr=0.35,
        profit_lock_buffer_pips=0.5,
        strategy=SimpleNamespace(atr_tp_multiplier=3.0),
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=0.35, sl_pips=8, tp_pips=16),
        execution=ExecutionConfig(magic=260430, deviation=10, filling_mode="AUTO", trade_enabled=True),
    )


class _StorageSpy:
    def __init__(self, latest_losing_exit=None, position_metrics=None):
        self.latest_losing_exit = latest_losing_exit
        self.position_metrics = position_metrics or {}
        self.pruned = []

    def record_order_request(self, request, check):
        pass

    def record_order_result(self, request, result):
        pass

    def get_latest_losing_exit(self, symbol, magic):
        return self.latest_losing_exit

    def prune_position_metrics(self, symbol, magic, open_tickets):
        self.pruned.append((symbol, magic, open_tickets))
        return 0

    def get_position_metrics(self, ticket):
        return self.position_metrics.get(int(ticket))


class _GatewayWithInvalidFirstFill:
    def __init__(self):
        self.checked_requests = []

    def positions_get(self, symbol):
        return []

    def symbol_info_tick(self, symbol):
        if symbol == "XAUUSD":
            return SimpleNamespace(bid=4555.90, ask=4556.07)
        return SimpleNamespace(bid=1.0999, ask=1.1000)

    def symbol_info(self, symbol):
        if symbol == "XAUUSD":
            return SimpleNamespace(
                digits=2,
                point=0.01,
                trade_tick_value=0.1,
                trade_tick_size=0.01,
                trade_contract_size=100.0,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
            )
        return _symbol_info()

    def account_info(self):
        return SimpleNamespace(equity=10_000)

    def order_calc_profit(self, order_type, symbol, volume, price_open, price_close):
        if symbol == "XAUUSD":
            return -abs(price_close - price_open) * 100.0 * float(volume)
        pip = 0.0001
        return -abs(price_close - price_open) / pip * 10.0 * float(volume)

    def constants(self):
        return {
            "TRADE_ACTION_DEAL": 1,
            "ORDER_TYPE_BUY": 0,
            "ORDER_TYPE_SELL": 1,
            "ORDER_TIME_GTC": 0,
            "ORDER_FILLING_RETURN": 2,
            "ORDER_FILLING_IOC": 1,
            "ORDER_FILLING_FOK": 0,
        }

    def order_check(self, request):
        self.checked_requests.append(request)
        retcode = 10030 if len(self.checked_requests) == 1 else 10009
        return SimpleNamespace(retcode=retcode, comment="Invalid fill" if retcode == 10030 else "Done")


class _GatewayWithSignedProfit(_GatewayWithInvalidFirstFill):
    def order_calc_profit(self, order_type, symbol, volume, price_open, price_close):
        pip = 0.0001
        signed_pips = (float(price_close) - float(price_open)) / pip
        if int(order_type) == 1:
            signed_pips *= -1
        return round(signed_pips * 10.0 * float(volume), 2)


class _GatewayOrderSendRejected(_GatewayWithInvalidFirstFill):
    def __init__(self):
        super().__init__()
        self.sent_requests = []

    def order_send(self, request):
        self.sent_requests.append(request)
        return SimpleNamespace(retcode=10027, comment="No money")


class _GatewayForPartialClose(_GatewayWithInvalidFirstFill):
    def __init__(self):
        super().__init__()
        self.sent_requests = []

    def positions_get(self, symbol):
        return [SimpleNamespace(
            ticket=8539285679,
            magic=260440,
            type=1,
            price_open=4708.08,
            volume=13.55,
        )]

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=4700.86, ask=4701.03)

    def symbol_info(self, symbol):
        return SimpleNamespace(
            digits=2,
            point=0.01,
            trade_tick_value=1.0,
            trade_tick_size=0.01,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
        )

    def order_send(self, request):
        self.sent_requests.append(request)
        return SimpleNamespace(retcode=10009, comment="Request executed")


class _GatewayForTrailingStop(_GatewayForPartialClose):
    def __init__(self):
        super().__init__()
        self.modified = []

    def positions_get(self, symbol):
        return [SimpleNamespace(
            ticket=8539285679,
            magic=260440,
            type=1,
            price_open=4708.08,
            sl=4719.73,
            tp=4685.01,
        )]

    def order_modify(self, ticket, sl, tp):
        self.modified.append((ticket, sl, tp))
        return SimpleNamespace(retcode=10009, comment="Request executed")


class _GatewayForProfitLock(_GatewayWithInvalidFirstFill):
    def __init__(self, current_bid, current_ask):
        super().__init__()
        self.current_bid = current_bid
        self.current_ask = current_ask
        self.sent_requests = []

    def positions_get(self, symbol):
        return [SimpleNamespace(
            ticket=9366528834,
            magic=260430,
            type=0,
            price_open=1.1000,
            volume=0.10,
            sl=1.0992,
            tp=1.1016,
        )]

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=self.current_bid, ask=self.current_ask)

    def order_check(self, request):
        self.checked_requests.append(request)
        return SimpleNamespace(retcode=10009, comment="Done")

    def order_send(self, request):
        self.sent_requests.append(request)
        return SimpleNamespace(retcode=10009, comment="Request executed")
