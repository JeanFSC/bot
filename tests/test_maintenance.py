import json
from pathlib import Path

from mt5_bot.maintenance import format_maintenance_summary


def test_format_maintenance_summary_includes_core_metrics(tmp_path: Path):
    latest_json = tmp_path / "maintenance_latest.json"
    latest_md = tmp_path / "maintenance_latest.md"
    latest_json.write_text(
        json.dumps(
            {
                "totals": {
                    "closed_trades": 3,
                    "wins": 2,
                    "losses": 1,
                    "net_pnl": 4.25,
                    "win_rate_pct": 66.67,
                },
                "top_reasons": [["no_closed_bar_crossover", 12]],
            }
        ),
        encoding="utf-8",
    )
    latest_md.write_text("# report", encoding="utf-8")

    text = format_maintenance_summary(
        {
            "learned": 1,
            "report": {
                "latest_json_path": latest_json,
                "latest_markdown_path": latest_md,
            },
        }
    )

    assert "[MT5 Maintenance]" in text
    assert "Closed trades: 3" in text
    assert "Net PnL: 4.25 USD" in text
    assert "no_closed_bar_crossover (12)" in text
