import zipfile
from pathlib import Path

from mt5_bot.backup import create_backup, prune_backups


def test_create_backup_includes_requested_files(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "data").mkdir()
    (root / "config").mkdir()
    (root / "data" / "memory.sqlite").write_text("memory", encoding="utf-8")
    (root / "config" / "agent.yaml").write_text("mode: demo", encoding="utf-8")

    backup = create_backup(root=root, output_dir=tmp_path / "backups", patterns=["data/*.sqlite", "config/*.yaml"], name="test")

    assert backup.exists()
    with zipfile.ZipFile(backup) as zf:
        names = set(zf.namelist())
    assert "data/memory.sqlite" in names
    assert "config/agent.yaml" in names


def test_prune_backups_keeps_newest_files(tmp_path: Path):
    for idx in range(5):
        path = tmp_path / f"backup_{idx}.zip"
        path.write_text(str(idx), encoding="utf-8")

    removed = prune_backups(tmp_path, keep=2)

    assert removed == 3
    assert len(list(tmp_path.glob("*.zip"))) == 2
