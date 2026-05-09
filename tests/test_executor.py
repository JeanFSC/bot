from types import SimpleNamespace

from mt5_bot.config import ExecutionConfig, RiskConfig
from mt5_bot.executor import TradeExecutor, build_market_order_request, should_open_new_position, with_filling_mode
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


class _StorageSpy:
    def record_order_request(self, request, check):
        pass

    def record_order_result(self, request, result):
        pass


class _GatewayWithInvalidFirstFill:
    def __init__(self):
        self.checked_requests = []

    def positions_get(self, symbol):
        return []

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=1.0999, ask=1.1000)

    def symbol_info(self, symbol):
        return _symbol_info()

    def account_info(self):
        return SimpleNamespace(equity=10_000)

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
