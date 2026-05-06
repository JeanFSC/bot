"""
LAUNCHER_DIRECT.py - Lanza 5 bots MT5 directamente sin archivos .bat
Auto-restart incluido. Ejecutar con: python LAUNCHER_DIRECT.py
"""
import subprocess
import threading
import time
import sys
import os

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BOT_DIR)

BOTS = [
    {"name": "EURUSD", "magic": 260433, "config": "config/pro.yaml",      "db": "data/pro.sqlite"},
    {"name": "GBPUSD", "magic": 260434, "config": "config/pro_gbp.yaml",  "db": "data/pro_gbp.sqlite"},
    {"name": "USDJPY", "magic": 260435, "config": "config/pro_jpy.yaml",  "db": "data/pro_jpy.sqlite"},
    {"name": "XAUUSD", "magic": 260436, "config": "config/pro_gold.yaml", "db": "data/pro_gold.sqlite"},
    {"name": "AUDUSD", "magic": 260437, "config": "config/pro_aud.yaml",  "db": "data/pro_aud.sqlite"},
]

PYTHON = sys.executable  # Ruta completa a python.exe actual

def log(name, msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{name}] {msg}", flush=True)

def run_bot(bot):
    name   = bot["name"]
    config = bot["config"]
    db     = bot["db"]

    env = os.environ.copy()
    env["PYTHONPATH"]      = os.path.join(BOT_DIR, "src")
    env["PYTHONUNBUFFERED"] = "1"

    os.makedirs("logs", exist_ok=True)

    while True:
        log(name, "========== iniciando CHECK ==========")
        check_log_path  = os.path.join(BOT_DIR, f"logs/check_errors_{name.lower()}.log")
        with open(check_log_path, "a") as check_log:
            result = subprocess.run(
                [PYTHON, "-m", "mt5_bot", "check", "--config", config],
                cwd=BOT_DIR,
                env=env,
                stderr=check_log,
                stdout=check_log,
            )

        if result.returncode != 0:
            log(name, f"CHECK failed (code={result.returncode}) — reintentando en 30s...")
            time.sleep(30)
            continue

        log(name, "CHECK OK — arrancando TRADE loop...")
        trade_log_path = os.path.join(BOT_DIR, f"logs/trade_errors_{name.lower()}.log")
        with open(trade_log_path, "a") as trade_log:
            subprocess.run(
                [PYTHON, "-m", "mt5_bot", "trade",
                 "--config", config,
                 "--db", db,
                 "--trade-enabled"],
                cwd=BOT_DIR,
                env=env,
                stderr=trade_log,
                stdout=trade_log,
            )

        log(name, "Trade loop terminado — reiniciando en 10s...")
        time.sleep(10)


if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("  MT5 PRO SUITE — LAUNCHER DIRECT (sin .bat)", flush=True)
    print(f"  Python: {PYTHON}", flush=True)
    print(f"  Dir:    {BOT_DIR}", flush=True)
    print("  Bots:   EURUSD / GBPUSD / USDJPY / XAUUSD / AUDUSD", flush=True)
    print("=" * 60, flush=True)

    threads = []
    for i, bot in enumerate(BOTS):
        t = threading.Thread(target=run_bot, args=(bot,), name=bot["name"], daemon=True)
        t.start()
        threads.append(t)
        log(bot["name"], "thread iniciado")
        if i < len(BOTS) - 1:
            time.sleep(3)   # escalonar arranques

    print(f"\n  5 bots corriendo. Ctrl+C para detener.\n", flush=True)

    try:
        while True:
            # Heartbeat cada minuto
            time.sleep(60)
            alive = [t.name for t in threads if t.is_alive()]
            log("MONITOR", f"Threads vivos: {alive}")
    except KeyboardInterrupt:
        print("\n[MONITOR] Detenido por usuario.", flush=True)
        sys.exit(0)
