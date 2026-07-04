from pathlib import Path

from mt5_bot.autonomous_agent import (
    AgentDecision,
    EvolutionMemory,
    classify_setup,
    decide_trade,
    adjusted_risk_pct,
    signal_confidence,
)
from mt5_bot.strategy import Signal, SignalType


def _signal(signal_type=SignalType.BUY, reason="ema_cross_above", rsi=52.0, atr_pips=95.0, trend_bias="up", adx=28.0):
    return Signal(
        type=signal_type,
        price=1.2345,
        time=None,
        reason=reason,
        fast_ema=1.235,
        slow_ema=1.234,
        rsi=rsi,
        atr=0.001,
        atr_pips=atr_pips,
        trend_bias=trend_bias,
        adx=adx,
    )


def test_classify_setup_groups_signal_context():
    setup = classify_setup("XAUUSD", _signal(), hour_utc=14)

    assert setup == "XAUUSD:BUY:ema_cross_above:trend_up:session_london_ny"


def test_memory_records_loss_and_reduces_risk_multiplier(tmp_path: Path):
    memory = EvolutionMemory(tmp_path / "agent.sqlite")
    setup = "XAUUSD:BUY:ema_cross_above:trend_up:session_london_ny"

    memory.record_outcome(
        symbol="XAUUSD",
        setup_key=setup,
        pnl=-25.0,
        reason="sl_hit_after_high_spread",
        context={"spread_pips": 32.0},
    )

    stats = memory.get_setup_stats("XAUUSD", setup)
    assert stats.losses == 1
    assert stats.wins == 0
    assert stats.consecutive_losses == 1
    assert stats.risk_multiplier < 1.0


def test_decision_blocks_setup_after_consecutive_losses(tmp_path: Path):
    memory = EvolutionMemory(tmp_path / "agent.sqlite")
    signal = _signal()
    setup = classify_setup("XAUUSD", signal, hour_utc=14)
    memory.record_outcome("XAUUSD", setup, -10.0, "loss_1", {})
    memory.record_outcome("XAUUSD", setup, -12.0, "loss_2", {})

    decision = decide_trade(
        symbol="XAUUSD",
        signal=signal,
        memory=memory,
        hour_utc=14,
        spread_pips=20.0,
        max_spread_pips=35.0,
        min_confidence=0.55,
        max_consecutive_setup_losses=2,
    )

    assert decision == AgentDecision.BLOCK


def test_decision_allows_high_confidence_fresh_setup(tmp_path: Path):
    memory = EvolutionMemory(tmp_path / "agent.sqlite")

    decision = decide_trade(
        symbol="XAUUSD",
        signal=_signal(),
        memory=memory,
        hour_utc=14,
        spread_pips=20.0,
        max_spread_pips=35.0,
        min_confidence=0.55,
        max_consecutive_setup_losses=2,
    )

    assert decision == AgentDecision.ALLOW


def test_signal_confidence_accepts_strategy_trend_bias_names():
    buy = _signal(signal_type=SignalType.BUY, trend_bias="bullish")
    sell = _signal(signal_type=SignalType.SELL, trend_bias="bearish")

    assert signal_confidence(buy, spread_pips=0.0, max_spread_pips=10.0) >= 0.90
    assert signal_confidence(sell, spread_pips=0.0, max_spread_pips=10.0) >= 0.90


def test_adjusted_risk_pct_applies_memory_multiplier(tmp_path: Path):
    memory = EvolutionMemory(tmp_path / "agent.sqlite")
    setup = "XAUUSD:BUY:ema_cross_above:trend_up:session_london_ny"
    memory.record_outcome("XAUUSD", setup, -10.0, "loss", {})

    value = adjusted_risk_pct(memory, "XAUUSD", setup, base_risk_pct=0.25, floor_pct=0.05)

    assert 0.05 <= value < 0.25
