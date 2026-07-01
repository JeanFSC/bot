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
