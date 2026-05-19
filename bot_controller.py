"""
MT5 Bot Controller v3 — dashboard 12 bots

Metodología Claude: operación agresiva pero controlada. Este controller no toma
trades; solo lanza/detiene bats, cuenta procesos mt5_bot y muestra logs vivos
por bot para detectar rápido CHECK failed, crashes, señales y ejecuciones.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BOT_DIR = Path(__file__).resolve().parent
BAT_FILE = BOT_DIR / "_run_all_pro_autorestart.bat"  # legacy launcher; controller now starts wrappers hidden
LOG_DIR = BOT_DIR / "logs"
FLAGS = 0x08000000  # CREATE_NO_WINDOW

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
WATCHDOG_CMD = ["python", "WATCHDOG_SAFE_24H.py", "--mode", "live-demo", "--watch", "--interval", "300"]


BG = "#0f0f1a"
CARD = "#1a1a2e"
BORDER = "#2a2a4a"
WHITE = "#e8e8f0"
GRAY = "#6c7086"
GREEN = "#69f0ae"
GDIM = "#164b3a"
RED = "#ff5252"
RDIM = "#5a1a24"
YELLOW = "#ffd166"
BLUE = "#9fa8da"


@dataclass(frozen=True)
class BotPanel:
    key: str
    title: str
    window_title: str
    log_file: str


BOTS: list[BotPanel] = [
    BotPanel("eurusd", "EURUSD", "PRO EURUSD", "bot_eurusd.log"),
    BotPanel("gbpusd", "GBPUSD", "PRO GBPUSD", "bot_gbpusd.log"),
    BotPanel("jpy", "USDJPY", "PRO USDJPY", "bot_jpy.log"),
    BotPanel("gold", "XAUUSD", "PRO XAUUSD (Gold)", "bot_gold.log"),
    BotPanel("aud", "AUDUSD", "PRO AUDUSD", "bot_aud.log"),
    BotPanel("gold_m5", "GOLD M5", "PRO XAUUSD M5 (Gold 24h)", "bot_gold_m5.log"),
    BotPanel("usdcad", "USDCAD", "PRO USDCAD", "bot_usdcad.log"),
    BotPanel("nzdusd", "NZDUSD", "PRO NZDUSD", "bot_nzdusd.log"),
    BotPanel("gbpjpy", "GBPJPY", "PRO GBPJPY", "bot_gbpjpy.log"),
    BotPanel("silver", "XAGUSD", "PRO XAGUSD (Silver)", "bot_silver.log"),
    BotPanel("jpy_asia", "JPY ASIA", "PRO USDJPY ASIA", "bot_jpy_asia.log"),
    BotPanel("usdchf", "USDCHF", "PRO USDCHF", "bot_usdchf.log"),
]
BOT_TITLES = [b.window_title for b in BOTS]


def controller_log(message: str) -> None:
    try:
        LOG_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().isoformat(timespec="seconds")
        with (LOG_DIR / "controller.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")
    except Exception:
        pass


def _run_ps(script: str, timeout: int = 8) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=FLAGS,
    )
    return r.stdout or ""


def count_restarts() -> int:
    try:
        ps = (
            "$p=Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -eq 'cmd.exe' -and $_.CommandLine -match '_restart_' }; "
            "@($p).Count"
        )
        out = _run_ps(ps)
        return int((out or "0").strip().splitlines()[-1])
    except Exception:
        return 0


def count_watchdogs() -> int:
    try:
        ps = (
            "$p=Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'python|cmd' -and $_.CommandLine -match 'WATCHDOG_SAFE_24H.py --mode live-demo --watch' }; "
            "@($p).Count"
        )
        out = _run_ps(ps)
        return int((out or "0").strip().splitlines()[-1])
    except Exception:
        return 0


def start_watchdog_hidden() -> None:
    if count_watchdogs() > 0:
        controller_log("live-demo watchdog already running")
        return
    subprocess.Popen(WATCHDOG_CMD, cwd=str(BOT_DIR), creationflags=FLAGS)
    controller_log("started live-demo watchdog hidden")


def start_suite_hidden() -> None:
    """Start all restart wrappers hidden, without the 12 visible cmd windows."""
    if count_bots() > 0 or count_restarts() > 0:
        controller_log("start skipped: suite processes already running")
        return
    LOG_DIR.mkdir(exist_ok=True)
    start_watchdog_hidden()
    for bat in RESTART_BATS:
        path = BOT_DIR / bat
        subprocess.Popen(
            ["cmd.exe", "/c", str(path)],
            cwd=str(BOT_DIR),
            creationflags=FLAGS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        controller_log(f"started hidden wrapper {bat}")
        time.sleep(0.15)


def stop_suite_processes() -> None:
    """Stop suite through watchdog stop, then kill residual wrappers/trade loops."""
    subprocess.run(
        ["python", "WATCHDOG_SAFE_24H.py", "--stop"],
        cwd=str(BOT_DIR),
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=FLAGS,
    )
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { ($_.Name -match 'python|cmd') -and $_.CommandLine -match 'mt5_bot trade|_restart_|_run_all_pro_autorestart' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, creationflags=FLAGS)
    controller_log("stop requested for suite processes")


def count_bots() -> int:
    """Count mt5_bot Python processes. Uses CIM because WMIC is absent on newer Windows."""
    try:
        ps = (
            "$p=Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'mt5_bot' }; "
            "@($p).Count"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=FLAGS,
        )
        return int((r.stdout or "0").strip().splitlines()[-1])
    except Exception:
        return 0


def kill_bots() -> None:
    stop_suite_processes()
    for title in BOT_TITLES:
        subprocess.run(
            ["taskkill", "/F", "/FI", f"WINDOWTITLE eq {title}"],
            capture_output=True,
            creationflags=FLAGS,
        )


def read_tail(path: Path, n: int = 8) -> list[str]:
    if not path.exists():
        return ["(sin log)"]
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-n:] if lines else ["(log vacío)"]
    except Exception as exc:
        return [f"(error leyendo log: {exc})"]


def fmt_color(line: str) -> str:
    raw = line.lower()
    if "signal=buy" in raw:
        return GREEN
    if "signal=sell" in raw:
        return RED
    if "status=sent" in raw or "check ok" in raw:
        return GREEN
    if "check failed" in raw or "crasheo" in raw or "crash" in raw or "exception" in raw or "error" in raw:
        return RED
    if "spread filter" in raw or "session filter" in raw or "no_closed_bar" in raw or "retest_" in raw:
        return YELLOW
    if "=====" in raw:
        return WHITE
    return BLUE


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MT5 Bot Controller v3 — 12 bots")
        self.geometry("1400x820")
        self.minsize(1180, 720)
        self.configure(bg=BG)
        self._busy = False
        self.cards: dict[str, dict[str, object]] = {}
        self._build()
        self._loop()

    def _build(self) -> None:
        header = tk.Frame(self, bg=CARD, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="MT5 PRO BOT SUITE v3", font=("Segoe UI", 20, "bold"), bg=CARD, fg=WHITE).pack()
        tk.Label(
            header,
            text="12 bots · cobertura 24h · portfolio guard max 5 trades · ADX boost + compounding",
            font=("Segoe UI", 10), bg=CARD, fg=GRAY,
        ).pack(pady=(2, 0))
        tk.Frame(self, bg=BORDER, height=2).pack(fill="x")

        status = tk.Frame(self, bg=BG, pady=10)
        status.pack(fill="x", padx=18)
        self.dot = tk.Label(status, text="●", font=("Segoe UI", 16), bg=BG, fg=GRAY)
        self.dot.pack(side="left")
        self.status_lbl = tk.Label(status, text="Verificando...", font=("Segoe UI", 12, "bold"), bg=BG, fg=GRAY)
        self.status_lbl.pack(side="left", padx=(8, 0))
        self.process_lbl = tk.Label(status, text="", font=("Segoe UI", 9), bg=BG, fg=GRAY)
        self.process_lbl.pack(side="right")

        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill="x", padx=18, pady=(0, 10))
        self.start_btn = tk.Button(
            buttons, text="▶ INICIAR 12 BOTS", font=("Segoe UI", 13, "bold"), bg=GREEN, fg="#000",
            activebackground="#00b890", activeforeground="#000", relief="flat", padx=16, pady=12,
            command=self._start, cursor="hand2",
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.stop_btn = tk.Button(
            buttons, text="■ DETENER BOTS", font=("Segoe UI", 13, "bold"), bg=RED, fg="#fff",
            activebackground="#cc3344", activeforeground="#fff", relief="flat", padx=16, pady=12,
            command=self._stop, cursor="hand2",
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(8, 0))

        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        for r in range(4):
            grid.rowconfigure(r, weight=1)
        for c in range(3):
            grid.columnconfigure(c, weight=1)

        for i, bot in enumerate(BOTS):
            frame = tk.Frame(grid, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            frame.grid(row=i // 3, column=i % 3, sticky="nsew", padx=5, pady=5)
            top = tk.Frame(frame, bg=CARD)
            top.pack(fill="x", padx=8, pady=(6, 2))
            dot = tk.Label(top, text="●", font=("Segoe UI", 11), bg=CARD, fg=GRAY)
            dot.pack(side="left")
            tk.Label(top, text=bot.title, font=("Segoe UI", 10, "bold"), bg=CARD, fg=WHITE).pack(side="left", padx=(6, 0))
            age = tk.Label(top, text="", font=("Segoe UI", 8), bg=CARD, fg=GRAY)
            age.pack(side="right")
            txt = tk.Text(frame, font=("Consolas", 7), bg="#111827", fg=BLUE, relief="flat", bd=5, wrap="word", height=7)
            txt.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            txt.configure(state="disabled")
            self.cards[bot.key] = {"dot": dot, "age": age, "text": txt}

        footer = tk.Frame(self, bg=CARD, pady=6)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer, text="demo_only=true · trade_enabled vía .bat · no sube .env", font=("Segoe UI", 8), bg=CARD, fg=GRAY).pack()

    def _start(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_status("Iniciando bots...", YELLOW)
        threading.Thread(target=self._do_start, daemon=True).start()

    def _do_start(self) -> None:
        try:
            start_suite_hidden()
            time.sleep(3)
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"Error: {exc}", RED))
        finally:
            self._busy = False

    def _stop(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_status("Deteniendo bots...", YELLOW)
        threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_stop(self) -> None:
        try:
            kill_bots()
            time.sleep(2)
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"Error: {exc}", RED))
        finally:
            self._busy = False

    def _set_status(self, msg: str, color: str) -> None:
        self.status_lbl.configure(text=msg, fg=color)
        self.dot.configure(fg=color)

    def _loop(self) -> None:
        self._refresh()
        self.after(2000, self._loop)

    def _refresh(self) -> None:
        n = count_bots()
        r = count_restarts()
        w = count_watchdogs()
        running = n > 0 or r > 0
        if not self._busy:
            self._set_status("BOTS ACTIVOS" if running else "BOTS DETENIDOS", GREEN if running else RED)
            self.process_lbl.configure(text=f"{n} trade loop(s) ? {r} wrapper(s) ? {w} watchdog(s)", fg=GREEN if running else GRAY)
            self.start_btn.configure(bg=GDIM if running else GREEN, fg=GRAY if running else "#000", cursor="arrow" if running else "hand2")
            self.stop_btn.configure(bg=RED if running else RDIM, fg="#fff" if running else GRAY, cursor="hand2" if running else "arrow")

        now = time.time()
        for bot in BOTS:
            card = self.cards[bot.key]
            log = LOG_DIR / bot.log_file
            lines = read_tail(log)
            fresh = log.exists() and now - log.stat().st_mtime < 90
            dot = card["dot"]
            age = card["age"]
            txt = card["text"]
            assert isinstance(dot, tk.Label) and isinstance(age, tk.Label) and isinstance(txt, tk.Text)
            dot.configure(fg=GREEN if fresh else GRAY)
            if log.exists():
                delta = int(now - log.stat().st_mtime)
                age.configure(text=f"{delta}s" if delta < 120 else f"{delta//60}m")
            else:
                age.configure(text="sin log")
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            for line in lines:
                tag = fmt_color(line)
                tag_name = f"c_{tag.replace('#', '')}"
                txt.tag_config(tag_name, foreground=tag)
                txt.insert("end", line + "\n", tag_name)
            txt.configure(state="disabled")


if __name__ == "__main__":
    os.chdir(BOT_DIR)
    App().mainloop()
