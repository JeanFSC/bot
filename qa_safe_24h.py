from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_FILES = [
    "START_SAFE_24H.bat",
    "STOP_SUITE.bat",
    "STATUS_SUITE.bat",
    "WATCHDOG_SAFE_24H.py",
    "qa_safe_24h.py",
]
RESTART_BATS = sorted(ROOT.glob("_restart_*.bat"))


def assert_file(path: Path) -> str:
    assert path.exists(), f"missing {path.name}"
    assert path.stat().st_size > 0, f"empty {path.name}"
    return path.read_text(encoding="utf-8", errors="replace")


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())
    assert proc.returncode == 0, f"command failed rc={proc.returncode}: {' '.join(cmd)}"


def main() -> int:
    print("== SAFE 24H FILE QA ==")
    for name in EXPECTED_FILES:
        text = assert_file(ROOT / name)
        print("OK", name)
        if name.endswith(".bat"):
            assert "--trade-enabled" not in text, f"{name} must not contain --trade-enabled"

    print("\n== SAFE 24H LAUNCHER QA ==")
    start_text = assert_file(ROOT / "START_SAFE_24H.bat")
    assert "WATCHDOG_SAFE_24H.py --preflight" in start_text
    assert "WATCHDOG_SAFE_24H.py --watch" in start_text
    assert "_run_all_pro_autorestart.bat" in start_text
    assert "STOP_SUITE.bat" in start_text or "STATUS_SUITE.bat" in start_text
    print("OK START_SAFE_24H.bat calls preflight, watchdog, launcher")

    stop_text = assert_file(ROOT / "STOP_SUITE.bat")
    assert "WATCHDOG_SAFE_24H.py --stop" in stop_text
    print("OK STOP_SUITE.bat calls watchdog stop")

    status_text = assert_file(ROOT / "STATUS_SUITE.bat")
    assert "WATCHDOG_SAFE_24H.py" in status_text
    assert "--mode live-demo" in status_text
    assert "--status" in status_text
    assert "--expect-running" in status_text
    print("OK STATUS_SUITE.bat calls status")

    print("\n== RESTART BAT SAFETY QA ==")
    assert len(RESTART_BATS) == 12, f"expected 12 restart bats, got {len(RESTART_BATS)}"
    for bat in RESTART_BATS:
        text = assert_file(bat)
        assert "--trade-enabled" not in text, f"{bat.name} contains dangerous --trade-enabled"
        assert "python -m mt5_bot check" in text, bat.name
        assert "python -m mt5_bot trade" in text, bat.name
        print("OK", bat.name)

    print("\n== WATCHDOG PREFLIGHT QA ==")
    run([sys.executable, "WATCHDOG_SAFE_24H.py", "--preflight"])

    print("\n== WATCHDOG STATUS QA ==")
    run([sys.executable, "WATCHDOG_SAFE_24H.py", "--mode", "live-demo", "--status", "--expect-running"])

    print("\nQA_SAFE_24H_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
