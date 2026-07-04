from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from mt5_bot.agent_runner import load_agent_config
from mt5_bot.backtest import run_backtest
from mt5_bot.cli import _connect_and_validate
from mt5_bot.config import load_config_from_env
from mt5_bot.mt5_gateway import MT5Gateway


@dataclass(frozen=True)
class ReplaySummary:
    config_path: str
    symbol: str
    timeframe: str
    from_time: str
    to_time: str
    trades: int
    wins: int
    losses: int
    win_rate_pct: float | None
    net_pips: float
    status: str = "ok"
    reason: str = ""


def summarize_backtest(config_path: str | Path, config: Any, rates, from_time: datetime, to_time: datetime) -> ReplaySummary:
    result = run_backtest(rates, config)
    win_rate = round((result.wins / result.trades) * 100, 2) if result.trades else None
    return ReplaySummary(
        config_path=str(config_path),
        symbol=config.symbol,
        timeframe=config.timeframe,
        from_time=from_time.isoformat(),
        to_time=to_time.isoformat(),
        trades=result.trades,
        wins=result.wins,
        losses=result.losses,
        win_rate_pct=win_rate,
        net_pips=result.net_pips,
    )


def write_replay_report(summaries: Sequence[ReplaySummary], out_dir: str | Path, name: str = "replay") -> dict[str, Path]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output / f"{name}_{stamp}.json"
    csv_path = output / f"{name}_{stamp}.csv"
    markdown_path = output / f"{name}_{stamp}.md"
    latest_json = output / f"{name}_latest.json"
    latest_csv = output / f"{name}_latest.csv"
    latest_markdown = output / f"{name}_latest.md"

    payload = [asdict(item) for item in summaries]
    json_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    csv_text = _render_csv(payload)
    md_text = render_replay_markdown(summaries)
    for path, text in [
        (json_path, json_text),
        (latest_json, json_text),
        (csv_path, csv_text),
        (latest_csv, csv_text),
        (markdown_path, md_text),
        (latest_markdown, md_text),
    ]:
        path.write_text(text, encoding="utf-8")
    return {"json_path": json_path, "csv_path": csv_path, "markdown_path": markdown_path}


def render_replay_markdown(summaries: Sequence[ReplaySummary]) -> str:
    lines = [
        "# MT5 Agent Replay Report",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "| Config | Symbol | TF | Trades | W | L | Win rate | Net pips | Status | Reason |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in summaries:
        wr = "n/a" if item.win_rate_pct is None else f"{item.win_rate_pct:.2f}%"
        lines.append(
            f"| `{item.config_path}` | {item.symbol} | {item.timeframe} | {item.trades} | {item.wins} | {item.losses} | {wr} | {item.net_pips:.2f} | {item.status} | {item.reason or 'n/a'} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def run_agent_replay(
    *,
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    days: int = 90,
    out_dir: str | Path = "reports",
    name: str = "replay",
) -> dict[str, Path]:
    agent_config = load_agent_config(agent_config_path)
    to_time = datetime.now(timezone.utc)
    from_time = to_time - timedelta(days=days)
    gateway = MT5Gateway()
    summaries: list[ReplaySummary] = []
    try:
        first_config = load_config_from_env(agent_config.configs[0])
        _connect_and_validate(gateway, first_config)
        for cfg_path in agent_config.configs:
            try:
                config = load_config_from_env(cfg_path)
                rates = gateway.copy_rates_range(config.symbol, config.timeframe, from_time, to_time)
                summaries.append(summarize_backtest(cfg_path, config, rates, from_time, to_time))
            except Exception as exc:
                summaries.append(
                    ReplaySummary(
                        config_path=str(cfg_path),
                        symbol="unknown",
                        timeframe="unknown",
                        from_time=from_time.isoformat(),
                        to_time=to_time.isoformat(),
                        trades=0,
                        wins=0,
                        losses=0,
                        win_rate_pct=None,
                        net_pips=0.0,
                        status="error",
                        reason=str(exc)[:200],
                    )
                )
    finally:
        gateway.shutdown()
    return write_replay_report(summaries, out_dir, name=name)


def _render_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    import io

    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_replay")
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--name", default="replay")
    args = parser.parse_args(argv)
    result = run_agent_replay(agent_config_path=args.agent_config, days=args.days, out_dir=args.out_dir, name=args.name)
    print(f"REPLAY_MD {result['markdown_path']}")
    print(f"REPLAY_JSON {result['json_path']}")
    print(f"REPLAY_CSV {result['csv_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
