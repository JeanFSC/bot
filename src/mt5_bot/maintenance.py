from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from mt5_bot.agent_runner import load_agent_config, learn_from_closed_deals
from mt5_bot.backup import create_backup, prune_backups
from mt5_bot.config import load_config
from mt5_bot.experiments import ExperimentLog
from mt5_bot.local_reports import write_local_report


def run_maintenance(
    *,
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    reports_dir: str | Path = "reports",
    backups_dir: str | Path = "backups",
    backup_keep: int = 48,
) -> dict[str, object]:
    agent_config = load_agent_config(agent_config_path)
    learned = learn_from_closed_deals(agent_config)
    dbs = [load_config(cfg).database_path for cfg in agent_config.configs]
    report = write_local_report(dbs, reports_dir, name="maintenance")
    ExperimentLog().write_markdown(Path(reports_dir) / "experiments.md")
    backup = create_backup(output_dir=backups_dir, name="mt5_agent")
    pruned = prune_backups(backups_dir, keep=backup_keep)
    return {"learned": learned, "report": report, "backup": backup, "pruned": pruned}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_maintenance")
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--backups-dir", default="backups")
    parser.add_argument("--backup-keep", type=int, default=48)
    args = parser.parse_args(argv)
    result = run_maintenance(
        agent_config_path=args.agent_config,
        reports_dir=args.reports_dir,
        backups_dir=args.backups_dir,
        backup_keep=args.backup_keep,
    )
    print(f"MAINTENANCE_OK learned={result['learned']} backup={result['backup']} pruned={result['pruned']}")
    print(f"REPORT_MD {result['report']['markdown_path']}")
    print(f"REPORT_JSON {result['report']['json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
