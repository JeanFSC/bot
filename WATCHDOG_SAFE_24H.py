from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
WATCHDOG_LOG = LOG_DIR / "watchdog_safe_24h.log"

CONFIGS = [
    "config/pro.yaml",
    "config/pro_gbp.yaml",
    "config/pro_jpy.yaml",
    "config/pro_gold.yaml",
    "config/pro_aud.yaml",
    "config/pro_gold_m5.yaml",
    "config/pro_usdcad.yaml",
    "config/pro_nzdusd.yaml",
    "config/pro_gbpjpy.yaml",
    "config/pro_silver.yaml",
    "config/pro_jpy_asia.yaml",
    "config/pro_usdchf.yaml",
]

RESTART_BATS = [
    "_restart_eurusd.bat",
    "_restart_gbpusd.bat",
    "_restart_jpy.bat",
    "_restart_gold.bat",
    "_restart_aud.bat",
    "_restart_gold_m5.bat",
    "_restart_usdcad.bat",
    "_restart_nzdusd.bat",
    "_restart_gbpjpy.bat",
    "_restart_silver.bat",
    "_restart_jpy_asia.bat",
    "_restart_usdchf.bat",
]

TRADE_MARKERS = [
    "--config config/pro.yaml",
    "--config config/pro_gbp.yaml",
    "--config config/pro_jpy.yaml",
    "--config config/pro_gold.yaml",
    "--config config/pro_aud.yaml",
    "--config config/pro_gold_m5.yaml",
    "--config config/pro_usdcad.yaml",
    "--config config/pro_nzdusd.yaml",
    "--config config/pro_gbpjpy.yaml",
    "--config config/pro_silver.yaml",
    "--config config/pro_jpy_asia.yaml",
    "--config config/pro_usdchf.yaml",
]

BAD_LOG_PATTERNS = ("ERROR", "Traceback", "Exception", "CRITICAL", "NameError")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(line: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    payload = f"{now()} {line}"
    print(payload)
    with WATCHDOG_LOG.open("a", encoding="utf-8") as fh:
        fh.write(payload + "\n")


def run_ps(script: str) -> str:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"powershell rc={proc.returncode}")
    return proc.stdout.strip()


def processes() -> list[dict]:
    script = r"""
$items = Get-CimInstance Win32_Process | Where-Object {
  ($_.CommandLine -match 'mt5_bot trade|_restart_(eurusd|gbpusd|jpy|gold|aud|usdcad|nzdusd|gbpjpy|silver|usdchf)|WATCHDOG_SAFE_24H|_run_all_pro_autorestart') -and
  ($_.Name -ne 'powershell.exe')
} | Select-Object ProcessId,Name,CommandLine
$items | ConvertTo-Json -Compress
"""
    raw = run_ps(script)
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        return [data]
    return list(data)


def suite_trade_processes(procs: list[dict]) -> list[dict]:
    return [p for p in procs if "mt5_bot trade" in str(p.get("CommandLine", ""))]


def restart_cmd_processes(procs: list[dict]) -> list[dict]:
    return [p for p in procs if "_restart_" in str(p.get("CommandLine", ""))]


def watchdog_processes(procs: list[dict]) -> list[dict]:
    return [p for p in procs if "WATCHDOG_SAFE_24H" in str(p.get("CommandLine", ""))]


def check_no_trade_enabled_in_files() -> list[str]:
    offenders: list[str] = []
    for rel in RESTART_BATS + ["_run_all_pro_autorestart.bat", "START_SAFE_24H.bat"]:
        path = ROOT / rel
        if path.exists() and "--trade-enabled" in path.read_text(encoding="utf-8", errors="replace"):
            offenders.append(rel)
    return offenders


def check_no_trade_enabled_in_processes(procs: list[dict]) -> list[int]:
    return [int(p["ProcessId"]) for p in procs if "--trade-enabled" in str(p.get("CommandLine", ""))]


def check_configs_safe() -> list[str]:
    sys.path.insert(0, str(ROOT / "src"))
    from mt5_bot.config import load_config

    bad: list[str] = []
    magics: set[int] = set()
    for rel in CONFIGS:
        cfg = load_config(ROOT / rel)
        if not cfg.account or cfg.account.demo_only is not True:
            bad.append(f"{rel}: demo_only not true")
        if cfg.execution.trade_enabled is not False:
            bad.append(f"{rel}: trade_enabled not false")
        if cfg.execution.magic in magics:
            bad.append(f"{rel}: duplicate magic {cfg.execution.magic}")
        magics.add(cfg.execution.magic)
        if not cfg.use_global_risk_guard:
            bad.append(f"{rel}: global risk guard disabled")
    return bad


def open_positions() -> tuple[int | None, str]:
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from mt5_bot.config import load_config_from_env
        from mt5_bot.mt5_gateway import MT5Gateway

        cfg = load_config_from_env(ROOT / "config/pro.yaml")
        gateway = MT5Gateway()
        try:
            gateway.initialize(cfg.account.terminal_path)
            gateway.login(cfg.account.login, cfg.account.password, cfg.account.server)
            account = gateway.account_info()
            positions = gateway.positions_get() or []
            return len(positions), f"account={account.login} balance={account.balance:.2f} equity={account.equity:.2f} open_positions={len(positions)}"
        finally:
            gateway.shutdown()
    except Exception as exc:
        return None, f"MT5_POSITION_CHECK_UNAVAILABLE {exc}"


def recent_log_errors(since_minutes: int = 90) -> list[str]:
    if not LOG_DIR.exists():
        return []
    cutoff = time.time() - since_minutes * 60
    findings: list[str] = []
    for path in LOG_DIR.glob("*.log"):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
        except Exception:
            continue
        for line in lines:
            if any(pat in line for pat in BAD_LOG_PATTERNS):
                findings.append(f"{path.name}: {line[:220]}")
                break
    return findings


def journal_summary() -> list[str]:
    out: list[str] = []
    for db in sorted((ROOT / "data").glob("pro*.sqlite")):
        try:
            con = sqlite3.connect(db)
            cur = con.execute("SELECT COUNT(*), MAX(created_at) FROM trade_journal")
            count, latest = cur.fetchone()
            con.close()
            out.append(f"{db.name}: trade_journal_rows={count or 0} latest={latest or 'n/a'}")
        except sqlite3.OperationalError:
            out.append(f"{db.name}: trade_journal_missing")
        except Exception as exc:
            out.append(f"{db.name}: journal_check_error={exc}")
    return out


def preflight() -> int:
    failures: list[str] = []
    file_offenders = check_no_trade_enabled_in_files()
    if file_offenders:
        failures.append("--trade-enabled found in files: " + ", ".join(file_offenders))
    failures.extend(check_configs_safe())
    launcher = ROOT / "_run_all_pro_autorestart.bat"
    if not launcher.exists():
        failures.append("missing _run_all_pro_autorestart.bat")
    else:
        starts = launcher.read_text(encoding="utf-8", errors="replace").count("start ")
        if starts < 12:
            failures.append(f"launcher starts only {starts} windows")
    if failures:
        for item in failures:
            log("PREFLIGHT_FAIL " + item)
        return 1
    log("PREFLIGHT_OK safe configs, safe launchers, 12-bot launcher present")
    return 0


def status(expect_running: bool = False, fail_on_error: bool = False) -> int:
    rc = 0
    procs = processes()
    trades = suite_trade_processes(procs)
    restarts = restart_cmd_processes(procs)
    bad_pids = check_no_trade_enabled_in_processes(procs)
    pos_count, pos_msg = open_positions()
    log(f"STATUS processes trade_loops={len(trades)} restart_windows={len(restarts)} watchdogs={len(watchdog_processes(procs))}")
    log("STATUS " + pos_msg)
    if bad_pids:
        log("DANGER --trade-enabled active in process ids: " + ",".join(map(str, bad_pids)))
        rc = 2
    if pos_count and pos_count > 0:
        log("DANGER unexpected open positions in safe 24h mode")
        rc = 3
    errors = recent_log_errors()
    if errors:
        log(f"STATUS recent_log_errors={len(errors)}")
        for item in errors[:12]:
            log("LOG_ERROR " + item)
        if fail_on_error:
            rc = 4
    else:
        log("STATUS recent_log_errors=0")
    for row in journal_summary()[:12]:
        log("JOURNAL " + row)
    if expect_running and len(trades) != 12:
        log(f"WARN expected 12 trade loops, got {len(trades)}")
        rc = max(rc, 5)
    return rc


def stop_suite() -> int:
    procs = processes()
    targets = [p for p in procs if "mt5_bot trade" in str(p.get("CommandLine", "")) or "_restart_" in str(p.get("CommandLine", "")) or "_run_all_pro_autorestart" in str(p.get("CommandLine", ""))]
    if not targets:
        log("STOP no suite processes found")
        return 0
    ids = [str(int(p["ProcessId"])) for p in targets]
    log("STOP killing process ids: " + ",".join(ids))
    run_ps(";".join([f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue" for pid in ids]))
    time.sleep(2)
    remaining = [p for p in processes() if "mt5_bot trade" in str(p.get("CommandLine", "")) or "_restart_" in str(p.get("CommandLine", ""))]
    if remaining:
        log("STOP_FAIL remaining suite processes: " + json.dumps(remaining)[:500])
        return 1
    log("STOP_OK suite closed")
    status(expect_running=False)
    return 0


def watch(interval: int, max_minutes: int) -> int:
    log(f"WATCH_START interval={interval}s max_minutes={max_minutes or 'infinite'}")
    end_at = time.time() + max_minutes * 60 if max_minutes > 0 else None
    while True:
        rc = status(expect_running=True, fail_on_error=True)
        if rc in {2, 3, 4}:
            log(f"WATCH_DANGER rc={rc}; stopping suite for safety")
            stop_suite()
            return rc
        if end_at and time.time() >= end_at:
            log("WATCH_DONE max_minutes reached")
            return 0
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe 24h watchdog/status/stop for MT5 suite")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--max-minutes", type=int, default=0)
    parser.add_argument("--expect-running", action="store_true")
    args = parser.parse_args()

    if args.preflight:
        return preflight()
    if args.stop:
        return stop_suite()
    if args.watch:
        return watch(max(args.interval, 30), args.max_minutes)
    return status(expect_running=args.expect_running)


if __name__ == "__main__":
    raise SystemExit(main())
