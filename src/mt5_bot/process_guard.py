from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class ProcessRow:
    pid: int
    parent_pid: int | None
    command_line: str


@dataclass(frozen=True)
class DuplicateTradeGroup:
    config_path: str
    process_count: int
    pids: list[int]
    command_lines: list[str]


def parse_trade_config(command_line: str) -> str | None:
    text = command_line.strip()
    if "mt5_bot" not in text or " trade" not in text or "--config" not in text:
        return None
    match = re.search(r"--config\s+(\"[^\"]+\"|'[^']+'|[^\s]+)", text)
    if not match:
        return None
    return match.group(1).strip("\"'")


def find_duplicate_trade_groups(rows: Sequence[ProcessRow], *, expected_processes_per_trade: int = 2) -> list[DuplicateTradeGroup]:
    groups: dict[str, list[ProcessRow]] = {}
    current_pid = os.getpid()
    for row in rows:
        if row.pid == current_pid:
            continue
        config = parse_trade_config(row.command_line)
        if config is None:
            continue
        groups.setdefault(_normalize_config(config), []).append(row)

    duplicates: list[DuplicateTradeGroup] = []
    for config, group_rows in sorted(groups.items()):
        if len(group_rows) <= expected_processes_per_trade:
            continue
        duplicates.append(
            DuplicateTradeGroup(
                config_path=config,
                process_count=len(group_rows),
                pids=[row.pid for row in group_rows],
                command_lines=[row.command_line for row in group_rows],
            )
        )
    return duplicates


def collect_process_rows() -> list[ProcessRow]:
    if os.name == "nt":
        return _collect_windows_process_rows()
    return _collect_posix_process_rows()


def audit_duplicate_trades() -> dict[str, object]:
    duplicates = find_duplicate_trade_groups(collect_process_rows())
    return {
        "ok": not duplicates,
        "duplicate_groups": [asdict(group) for group in duplicates],
    }


def _collect_windows_process_rows() -> list[ProcessRow]:
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'mt5_bot' } | "
        "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    return [
        ProcessRow(
            pid=int(item.get("ProcessId")),
            parent_pid=int(item["ParentProcessId"]) if item.get("ParentProcessId") is not None else None,
            command_line=str(item.get("CommandLine") or ""),
        )
        for item in payload
        if item.get("ProcessId") is not None
    ]


def _collect_posix_process_rows() -> list[ProcessRow]:
    completed = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, check=False, timeout=20)
    if completed.returncode != 0:
        return []
    rows: list[ProcessRow] = []
    for raw in completed.stdout.splitlines():
        parts = raw.strip().split(maxsplit=2)
        if len(parts) < 3 or "mt5_bot" not in parts[2]:
            continue
        rows.append(ProcessRow(int(parts[0]), int(parts[1]), parts[2]))
    return rows


def _normalize_config(config: str) -> str:
    text = config.replace("/", "\\")
    try:
        path = Path(text)
        if path.is_absolute():
            return str(path.resolve()).lower()
    except Exception:
        pass
    return text.lower()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_process_guard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = audit_duplicate_trades()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif report["ok"]:
        print("PROCESS_GUARD_OK no duplicate mt5_bot trade configs")
    else:
        print("PROCESS_GUARD_DUPLICATES")
        for group in report["duplicate_groups"]:
            print(f"- {group['config_path']}: count={group['process_count']} pids={group['pids']}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
