from __future__ import annotations

import argparse
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

DEFAULT_PATTERNS = [
    "data/*.sqlite",
    "data/*.jsonl",
    "config/*.yaml",
    "*.md",
    "*.bat",
]


def create_backup(
    *,
    root: str | Path = ".",
    output_dir: str | Path = "backups",
    patterns: Sequence[str] | None = None,
    name: str = "mt5_agent",
) -> Path:
    root_path = Path(root).resolve()
    out = Path(output_dir)
    if not out.is_absolute():
        out = root_path / out
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = out / f"{name}_{stamp}.zip"
    selected: list[Path] = []
    for pattern in patterns or DEFAULT_PATTERNS:
        selected.extend(path for path in root_path.glob(pattern) if path.is_file())
    unique = sorted(set(selected))
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in unique:
            zf.write(path, path.relative_to(root_path).as_posix())
    return target


def prune_backups(output_dir: str | Path = "backups", keep: int = 24) -> int:
    out = Path(output_dir)
    if not out.exists():
        return 0
    backups = sorted(out.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    removed = 0
    for path in backups[max(0, keep):]:
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_backup")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default="backups")
    parser.add_argument("--name", default="mt5_agent")
    parser.add_argument("--keep", type=int, default=24)
    parser.add_argument("--pattern", action="append", dest="patterns")
    args = parser.parse_args(argv)
    backup = create_backup(root=args.root, output_dir=args.output_dir, patterns=args.patterns, name=args.name)
    removed = prune_backups(Path(args.root) / args.output_dir if not Path(args.output_dir).is_absolute() else args.output_dir, keep=args.keep)
    print(f"BACKUP_CREATED {backup}")
    print(f"BACKUP_PRUNED removed={removed} keep={args.keep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
