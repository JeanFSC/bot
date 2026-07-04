import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("autonomous_trade_review", ROOT / "scripts" / "autonomous_trade_review.py")
assert SPEC is not None and SPEC.loader is not None
autonomous_trade_review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = autonomous_trade_review
SPEC.loader.exec_module(autonomous_trade_review)


def test_review_loop_skips_when_lock_is_active(tmp_path: Path, capsys):
    state_path = tmp_path / "review_state.json"
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    lock_path.write_text('{"pid": 123, "created_at": "2026-07-01T00:00:00+00:00"}\n', encoding="utf-8")

    result = autonomous_trade_review.main(
        [
            "--state",
            str(state_path),
            "--lock-stale-minutes",
            "45",
        ]
    )

    assert result == 0
    assert "skipped=lock_active" in capsys.readouterr().out
    assert lock_path.exists()


def test_winner_diagnostics_flags_clean_scale_candidate():
    capture, quality, verdict = autonomous_trade_review._winner_diagnostics(
        pnl=10.0,
        mfe_pips=20.0,
        mae_pips=-3.0,
        mfe_profit=18.0,
    )

    assert round(capture, 2) == 0.56
    assert quality == "winner_left_money_on_table"
    assert verdict == "scale_candidate_clean_winner"


def test_winner_diagnostics_labels_high_capture_clean_winner():
    capture, quality, verdict = autonomous_trade_review._winner_diagnostics(
        pnl=16.0,
        mfe_pips=20.0,
        mae_pips=-3.0,
        mfe_profit=18.0,
    )

    assert round(capture, 2) == 0.89
    assert quality == "clean_winner"
    assert verdict == "scale_candidate_clean_winner"


def test_winner_diagnostics_rejects_survived_winner_scaling():
    capture, quality, verdict = autonomous_trade_review._winner_diagnostics(
        pnl=4.0,
        mfe_pips=8.0,
        mae_pips=-5.0,
        mfe_profit=5.0,
    )

    assert capture == 0.8
    assert quality == "survived_winner"
    assert verdict == "no_scale_survived_winner"


def test_update_proposals_written_for_actionable_reviews(tmp_path: Path):
    review = autonomous_trade_review.ReviewedTrade(
        source_id="data/pro.sqlite:123",
        db_path=tmp_path / "pro.sqlite",
        ticket=123,
        position_id=123,
        created_at="2026-07-02T00:00:00+00:00",
        symbol="EURUSD",
        magic=260533,
        side="BUY",
        pnl=1.23,
        volume=0.01,
        entry_price=1.1,
        exit_price=1.101,
        sl=1.099,
        tp=1.103,
        sl_pips=10.0,
        tp_pips=30.0,
        projected_loss=3.0,
        projected_gain=9.0,
        projected_cash_rr=3.0,
        mfe_pips=20.0,
        mae_pips=-2.0,
        mfe_profit=4.0,
        mae_profit=-0.4,
        mfe_capture_ratio=0.31,
        winner_quality="winner_left_money_on_table",
        scale_verdict="scale_candidate_clean_winner",
        comment="[tp]",
        causes=["profitable_exit", "low_mfe_capture"],
        lessons=["review_runner_or_winner_scaling_for_clean_winner"],
        action="review_winner_runner_or_scale_logic",
    )

    path = autonomous_trade_review._write_update_proposals(
        tmp_path,
        [review],
        autonomous_trade_review.ROOT / "reports" / "review.md",
    )

    assert path is not None
    payload = path.read_text(encoding="utf-8")
    assert "pending_review" in payload
    assert "review_winner_runner_or_scale_logic" in payload
    assert "zero positions and zero pending orders" in payload


def test_update_proposals_skips_record_only(tmp_path: Path):
    assert autonomous_trade_review._write_update_proposals(
        tmp_path,
        [],
        autonomous_trade_review.ROOT / "reports" / "review.md",
    ) is None
