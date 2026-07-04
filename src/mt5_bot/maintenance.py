from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from mt5_bot import notifier
from mt5_bot.agent_runner import load_agent_config, learn_from_closed_deals
from mt5_bot.backup import create_backup, prune_backups
from mt5_bot.config import load_config
from mt5_bot.experiments import ExperimentLog
from mt5_bot.local_reports import write_local_report
from mt5_bot.process_guard import audit_duplicate_trades


def run_maintenance(
    *,
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    reports_dir: str | Path = "reports",
    backups_dir: str | Path = "backups",
    backup_keep: int = 48,
    notify: bool = False,
) -> dict[str, object]:
    agent_config = load_agent_config(agent_config_path)
    learned = learn_from_closed_deals(agent_config)
    dbs = [load_config(cfg).database_path for cfg in agent_config.configs]
    report = write_local_report(dbs, reports_dir, name="maintenance")
    exp_log = ExperimentLog()
    exp_log.snapshot_configs(agent_config.configs)
    exp_log.write_markdown(Path(reports_dir) / "experiments.md")
    process_audit = audit_duplicate_trades()
    backup = create_backup(output_dir=backups_dir, name="mt5_agent")
    pruned = prune_backups(backups_dir, keep=backup_keep)
    result = {"learned": learned, "report": report, "backup": backup, "pruned": pruned, "process_audit": process_audit}
    if notify:
        notifier.notify(format_maintenance_summary(result))
    return result


def format_maintenance_summary(result: dict[str, Any]) -> str:
    report = result.get("report", {})
    metrics = _read_json(Path(report["latest_json_path"])) if isinstance(report, dict) and report.get("latest_json_path") else {}
    totals = metrics.get("totals", {}) if isinstance(metrics, dict) else {}
    top_reasons = metrics.get("top_reasons", []) if isinstance(metrics, dict) else []
    reason_text = "none"
    if top_reasons:
        reason, count = top_reasons[0]
        reason_text = f"{reason} ({count})"
    return (
        "[MT5 Maintenance]\n"
        f"Learned: {result.get('learned', 0)}\n"
        f"Closed trades: {totals.get('closed_trades', 0)} | Net PnL: {float(totals.get('net_pnl', 0.0)):.2f} USD\n"
        f"W/L: {totals.get('wins', 0)}/{totals.get('losses', 0)} | Win rate: {totals.get('win_rate_pct', 'n/a')}\n"
        f"Top block reason: {reason_text}\n"
        f"Duplicate processes: {_duplicate_summary(result.get('process_audit', {}))}\n"
        f"Report: {report.get('latest_markdown_path', 'n/a') if isinstance(report, dict) else 'n/a'}"
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _duplicate_summary(process_audit: Any) -> str:
    if not isinstance(process_audit, dict):
        return "unknown"
    groups = process_audit.get("duplicate_groups") or []
    if not groups:
        return "none"
    return ", ".join(f"{group.get('config_path')} ({group.get('process_count')})" for group in groups)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_maintenance")
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--backups-dir", default="backups")
    parser.add_argument("--backup-keep", type=int, default=48)
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args(argv)
    result = run_maintenance(
        agent_config_path=args.agent_config,
        reports_dir=args.reports_dir,
        backups_dir=args.backups_dir,
        backup_keep=args.backup_keep,
        notify=args.notify,
    )
    print(f"MAINTENANCE_OK learned={result['learned']} backup={result['backup']} pruned={result['pruned']}")
    print(f"REPORT_MD {result['report']['markdown_path']}")
    print(f"REPORT_JSON {result['report']['json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
