from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


class ExperimentLog:
    def __init__(self, path: str | Path = "data/experiments.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, name: str, hypothesis: str, changes: dict[str, Any]) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4())[:12],
            "event": "start",
            "created_at": _now(),
            "name": name,
            "hypothesis": hypothesis,
            "changes": changes,
        }
        self._append(event)
        return event

    def note(self, experiment_id: str, note: str) -> dict[str, Any]:
        event = {"id": experiment_id, "event": "note", "created_at": _now(), "note": note}
        self._append(event)
        return event

    def finish(self, experiment_id: str, outcome: str, metrics: dict[str, Any]) -> dict[str, Any]:
        event = {"id": experiment_id, "event": "finish", "created_at": _now(), "outcome": outcome, "metrics": metrics}
        self._append(event)
        return event

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            events.append(json.loads(line))
        return events

    def render_markdown(self) -> str:
        lines = ["# Experiment Log", ""]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for event in self.read_all():
            grouped.setdefault(event["id"], []).append(event)
        if not grouped:
            lines.append("No experiments yet.")
            return "\n".join(lines) + "\n"
        for experiment_id, events in grouped.items():
            start = next((event for event in events if event["event"] == "start"), events[0])
            lines.extend([
                f"## {start.get('name', experiment_id)}",
                "",
                f"- ID: `{experiment_id}`",
                f"- Hypothesis: {start.get('hypothesis', 'n/a')}",
                f"- Changes: `{json.dumps(start.get('changes', {}), sort_keys=True)}`",
            ])
            for event in events:
                if event["event"] == "note":
                    lines.append(f"- Note `{event['created_at']}`: {event['note']}")
                elif event["event"] == "finish":
                    lines.append(f"- Outcome `{event['created_at']}`: **{event['outcome']}** `{json.dumps(event.get('metrics', {}), sort_keys=True)}`")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def write_markdown(self, output_path: str | Path = "reports/experiments.md") -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.render_markdown(), encoding="utf-8")
        return output

    def _append(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_experiments")
    parser.add_argument("action", choices=["start", "note", "finish", "render"])
    parser.add_argument("--path", default="data/experiments.jsonl")
    parser.add_argument("--id")
    parser.add_argument("--name")
    parser.add_argument("--hypothesis")
    parser.add_argument("--changes-json", default="{}")
    parser.add_argument("--note")
    parser.add_argument("--outcome")
    parser.add_argument("--metrics-json", default="{}")
    parser.add_argument("--markdown", default="reports/experiments.md")
    args = parser.parse_args(argv)
    log = ExperimentLog(args.path)
    if args.action == "start":
        event = log.start(args.name or "experiment", args.hypothesis or "", json.loads(args.changes_json))
        print(json.dumps(event, ensure_ascii=False))
    elif args.action == "note":
        event = log.note(args.id or "unknown", args.note or "")
        print(json.dumps(event, ensure_ascii=False))
    elif args.action == "finish":
        event = log.finish(args.id or "unknown", args.outcome or "unknown", json.loads(args.metrics_json))
        print(json.dumps(event, ensure_ascii=False))
    elif args.action == "render":
        print(f"EXPERIMENTS_MD {log.write_markdown(args.markdown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
