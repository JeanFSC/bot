"""
MT5 Bot Controller v3 — Dashboard 12 bots con logs individuales en tiempo real
"""
import re
import subprocess
import threading
import time
import os
import tkinter as tk
from pathlib import Path
from datetime import datetime

BOT_DIR  = Path(__file__).resolve().parent
BAT_FILE = BOT_DIR / "_run_all_pro_autorestart.bat"
LOG_DIR  = BOT_DIR / "logs"
FLAGS    = 0x08000000  # CREATE_NO_WINDOW

BOTS = [
    {"id": "eurusd",    "display": "EURUSD",   "tf": "M15", "log": "bot_eurusd.log",  "title": "PRO EURUSD",               "color": "#4fc3f7"},
    {"id": "gbpusd",    "display": "GBPUSD",   "tf": "M15", "log": "bot_gbpusd.log",  "title": "PRO GBPUSD",               "color": "#4fc3f7"},
    {"id": "usdjpy",    "display": "USDJPY",   "tf": "M15", "log": "bot_jpy.log",     "title": "PRO USDJPY",               "color": "#4fc3f7"},
    {"id": "xauusd",    "display": "XAUUSD",   "tf": "M15", "log": "bot_gold.log",    "title": "PRO XAUUSD (Gold)",        "color": "#ffd54f"},
    {"id": "audusd",    "display": "AUDUSD",   "tf": "M15", "log": "bot_aud.log",     "title": "PRO AUDUSD",               "color": "#4fc3f7"},
    {"id": "xauusd_m5", "display": "XAUUSD",   "tf": "M5",  "log": "bot_gold_m5.log", "title": "PRO XAUUSD M5 (Gold 24h)", "color": "#ffd54f"},
    {"id": "usdcad",    "display": "USDCAD",   "tf": "M15", "log": "bot_usdcad.log",  "title": "PRO USDCAD",               "color": "#4fc3f7"},
    {"id": "nzdusd",    "display": "NZDUSD",   "tf": "M15", "log": "bot_nzdusd.log",  "title": "PRO NZDUSD",               "color": "#80cbc4"},
    {"id": "gbpjpy",    "display": "GBPJPY",   "tf": "M15", "log": "bot_gbpjpy.log",  "title": "PRO GBPJPY",               "color": "#ce93d8"},
    {"id": "xagusd",    "display": "XAGUSD",   "tf": "M15", "log": "bot_silver.log",  "title": "PRO XAGUSD (Silver 24h)",  "color": "#b0bec5"},
    {"id": "jpy_asia",  "display": "JPY ASIA", "tf": "M15", "log": "bot_jpy_asia.log","title": "PRO USDJPY ASIA (nocturno)","color": "#80cbc4"},
    {"id": "usdchf",    "display": "USDCHF",   "tf": "M15", "log": "bot_usdchf.log",  "title": "PRO USDCHF",               "color": "#4fc3f7"},
]

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = "#0a0a14"
CARD    = "#0f0f1e"
CARDBRD = "#1a1a30"
WHITE   = "#e8e8f4"
DIM     = "#3a3a5a"
DIMLT   = "#6a6a9a"
GREEN   = "#00e676"
GDIM    = "#003320"
RED     = "#ff1744"
RDIM    = "#3a0010"
YELLOW  = "#ffab40"
TOPBAR  = "#080814"

C_BUY   = "#00e676"   # bright green
C_SELL  = "#ff5252"   # red
C_SENT  = "#69ffb0"   # mint — trade confirmed
C_WARN  = "#ffab40"   # amber
C_ERR   = "#ff1744"   # bright red
C_INFO  = "#7986cb"   # indigo-blue
C_DIM   = "#2e2e4e"   # very dim
C_BOOST = "#ffe082"   # gold — adx/compound boost
C_SEP   = "#1c1c3a"   # separator line

# ── Human-readable reason map ──────────────────────────────────────────────────
_REASON = {
    "no_closed_bar_crossover":  "sin cruce de medias",
    "not_enough_bars":          "cargando barras...",
    "atr_too_low":              "mercado quieto (ATR bajo)",
    "rsi_buy_filter":           "RSI alto — evita compra",
    "rsi_sell_filter":          "RSI bajo — evita venta",
    "rsi_momentum_not_rising":  "RSI sin momentum alcista",
    "rsi_momentum_not_falling": "RSI sin momentum bajista",
    "trend_filter_blocked_buy": "tendencia ↓ bloquea BUY",
    "trend_filter_blocked_sell":"tendencia ↑ bloquea SELL",
    "adx_not_available":        "ADX calculando...",
    "retest_waiting":           "esperando pullback",
    "portfolio_positions":      "portfolio lleno",
    "cooldown":                 "en cooldown",
}


# ── Log helpers ────────────────────────────────────────────────────────────────

def _log_tail(log_file: str, n: int = 8) -> list:
    path = LOG_DIR / log_file
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = [l for l in text.splitlines() if l.strip()]
        return lines[-n:]
    except Exception:
        return []


def _log_mtime(log_file: str) -> float:
    try:
        return (LOG_DIR / log_file).stat().st_mtime
    except Exception:
        return 0.0


# ── Line formatter ─────────────────────────────────────────────────────────────

def _fmt(raw: str):
    """Parse a raw log line → (display_text, color_tag)."""
    raw = raw.strip()
    if not raw:
        return None

    # ── Python logging format: "YYYY-MM-DD HH:MM:SS LEVEL name - msg" ─────────
    m = re.match(r'\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2}) (\w+) \S+ - (.+)', raw)
    if m:
        ts, level, msg = m.group(1), m.group(2), m.group(3).strip()
        hm = ts[:5]  # HH:MM

        # ERROR / exception lines
        if level == "ERROR" or "Traceback" in raw or "Exception" in raw:
            return f"{hm}  ❌  {msg[:80]}", "err"

        # WARNING block
        if level == "WARNING":
            if "Daily loss limit" in msg:
                return f"{hm}  🛑  Límite de pérdida diaria alcanzado", "warn"
            if "consecutive losses" in msg or "Equity curve" in msg:
                n_ = re.search(r'(\d+) consecutive', msg)
                nc = n_.group(1) if n_ else "?"
                return f"{hm}  ⚠  {nc} pérdidas seguidas — riesgo reducido 50%", "warn"
            if "Portfolio guard" in msg:
                if "positions" in msg:
                    return f"{hm}  🔒  Portfolio lleno — nueva entrada bloqueada", "warn"
                if "margin" in msg:
                    return f"{hm}  🔒  Margen alto — nueva entrada bloqueada", "warn"
                if "currency" in msg:
                    return f"{hm}  🔒  Misma divisa — exposición limitada", "warn"
                return f"{hm}  🔒  Portfolio guard activo", "warn"
            if "Equity stop" in msg:
                return f"{hm}  🛑  Equity stop activado", "err"
            return f"{hm}  ⚠  {msg[:80]}", "warn"

        # INFO block — parse specific patterns
        # Balance / equity
        if msg.startswith("Balance="):
            bal = re.search(r'Balance=([\d.]+)', msg)
            eq  = re.search(r'Equity=([\d.]+)', msg)
            sp  = re.search(r'Spread=([\d.]+)', msg)
            b_v = float(bal.group(1)) if bal else 0
            e_v = float(eq.group(1))  if eq  else 0
            s_v = float(sp.group(1))  if sp  else 0
            diff = e_v - b_v
            pnl  = (f"  PnL {'+' if diff >= 0 else ''}{diff:,.0f}" if abs(diff) > 0.5 else "")
            return f"{hm}  💰  ${b_v:>10,.0f}{pnl}   Spread {s_v:.1f}p", "info"

        # Signal BUY
        if "Signal=BUY" in msg:
            rsi = re.search(r'rsi=([\d.]+)', msg)
            atr = re.search(r'atr_pips=([\d.]+)', msg)
            adx = re.search(r'adx=([\d.]+)', msg)
            parts = []
            if rsi: parts.append(f"RSI {float(rsi.group(1)):.0f}")
            if atr: parts.append(f"ATR {float(atr.group(1)):.0f}p")
            if adx: parts.append(f"ADX {float(adx.group(1)):.0f}")
            extra = "   " + "  ".join(parts) if parts else ""
            return f"{hm}  ▲  BUY{extra}", "buy"

        # Signal SELL
        if "Signal=SELL" in msg:
            rsi = re.search(r'rsi=([\d.]+)', msg)
            atr = re.search(r'atr_pips=([\d.]+)', msg)
            adx = re.search(r'adx=([\d.]+)', msg)
            parts = []
            if rsi: parts.append(f"RSI {float(rsi.group(1)):.0f}")
            if atr: parts.append(f"ATR {float(atr.group(1)):.0f}p")
            if adx: parts.append(f"ADX {float(adx.group(1)):.0f}")
            extra = "   " + "  ".join(parts) if parts else ""
            return f"{hm}  ▼  SELL{extra}", "sell"

        # Signal NONE
        if "Signal=NONE" in msg:
            rm = re.search(r'reason=(\S+)', msg)
            r  = rm.group(1) if rm else ""
            if r.startswith("adx_weak_trend"):
                val_s = r.rsplit("_", 1)[-1]
                try:    return f"{hm}  ○  ADX débil ({float(val_s):.0f}) — sin tendencia", "dim"
                except: return f"{hm}  ○  ADX débil — sin tendencia", "dim"
            human = _REASON.get(r, r.replace("_", " "))
            rsi = re.search(r'rsi=([\d.]+)', msg)
            adx = re.search(r'adx=([\d.]+)', msg)
            xtra = []
            if rsi: xtra.append(f"RSI {float(rsi.group(1)):.0f}")
            if adx: xtra.append(f"ADX {float(adx.group(1)):.0f}")
            suffix = f"   ({' '.join(xtra)})" if xtra else ""
            return f"{hm}  ○  {human}{suffix}", "dim"

        # Trade sent
        if "status=sent" in msg:
            vol = re.search(r'volume=([\d.]+)', msg)
            v = f"  {vol.group(1)} lots" if vol else ""
            return f"{hm}  ✅  ORDEN EJECUTADA{v}", "sent"
        if "Execution status=" in msg and "sent" not in msg:
            st = re.search(r'status=(\S+)', msg)
            re_ = re.search(r'reason=(\S+)', msg)
            reason = (re_.group(1) if re_ else "").replace("_", " ")
            return f"{hm}  ○  No entrada — {reason}", "dim"

        # ADX tiered boost
        if "ADX boost:" in msg:
            adx = re.search(r'adx=([\d.]+)', msg)
            rsk = re.search(r'risk_pct=([\d.]+)', msg)
            a = f"ADX {float(adx.group(1)):.0f}" if adx else ""
            r = f"→ riesgo {rsk.group(1)}%" if rsk else ""
            return f"{hm}  ⚡  {a} {r}", "boost"

        # ADX reduce
        if "ADX reduce:" in msg:
            adx = re.search(r'adx=([\d.]+)', msg)
            a = f"ADX {float(adx.group(1)):.0f}" if adx else ""
            return f"{hm}  ↓  {a} — riesgo reducido (tendencia débil)", "dim"

        # Compound boost
        if "Compound boost:" in msg:
            fac = re.search(r'factor=([\d.]+)x', msg)
            rsk = re.search(r'risk_pct=([\d.]+)', msg)
            f = f"×{fac.group(1)}" if fac else ""
            r = f"→ riesgo {rsk.group(1)}%" if rsk else ""
            return f"{hm}  📈  Compounding {f} {r}", "boost"

        # Spread filter
        if "Spread filter:" in msg:
            val = re.search(r'([\d.]+) >', msg)
            v = val.group(1) if val else "?"
            return f"{hm}  ○  Spread alto ({v}p) — esperando", "dim"

        # Session filter
        if "Session filter:" in msg:
            h = re.search(r'UTC hour=(\d+)', msg)
            hr = h.group(1) if h else "?"
            return f"{hm}  ○  Fuera de sesión ({hr}:xx UTC)", "dim"

        # News filter
        if "News filter:" in msg:
            return f"{hm}  📰  Noticia importante — entrada pausada", "warn"

        # Weekend gap
        if "Weekend gap" in msg:
            return f"{hm}  😴  Fin de semana — mercados cerrados", "dim"

        # Correlation guard (risk halved)
        if "Correlation guard:" in msg:
            sym = re.search(r'(\w+) already', msg)
            s = sym.group(1) if sym else ""
            return f"{hm}  🔗  Correlación con {s} — riesgo 50%", "warn"

        # Starting loop
        if "Starting PRO loop:" in msg:
            sym = re.search(r'symbol=(\S+)', msg)
            tf  = re.search(r'tf=(\S+)', msg)
            s = sym.group(1) if sym else ""
            t = tf.group(1)  if tf  else ""
            return f"{hm}  🚀  Loop iniciado  {s} {t}", "sent"

        # MT5 connected
        if "MT5 demo ready" in msg or "MT5 permissions" in msg:
            sym = re.search(r'symbol=(\S+)', msg)
            s = sym.group(1) if sym else ""
            return f"{hm}  ✓   MT5 conectado  {s}", "sent"

        # Trailing stop / breakeven
        if "trailing" in msg.lower() or "breakeven" in msg.lower() or "PartialClose" in msg:
            return f"{hm}  📍  {msg[:70]}", "info"

        # Cooldown
        if "Cooldown" in msg.lower() or "cooldown" in msg:
            secs = re.search(r'([\d.]+)\s*s', msg)
            s = f"({secs.group(1)}s)" if secs else ""
            return f"{hm}  ⏱   Cooldown {s}", "dim"

        # Daily trade limit
        if "Daily trade count" in msg:
            return f"{hm}  ○  Límite de trades diario — esperando mañana", "warn"

        # Fallback INFO
        short = msg[:90]
        return f"{hm}  {short}", "info"

    # ── Bat echo format: "[HH:MM:SS.xx] text" ─────────────────────────────────
    bm = re.match(r'\[(\d{2}:\d{2}:\d{2})[^\]]*\]\s*(.*)', raw)
    if bm:
        hm, msg = bm.group(1)[:5], bm.group(2).strip()
        if "=====" in msg:
            return f"{hm}  ▶   {msg}", "sep"
        if "CHECK OK" in msg:
            return f"{hm}  ✓   CHECK OK — trade loop arrancando", "sent"
        if "CHECK failed" in msg:
            return f"{hm}  ❌  CHECK fallido — reintentando en 30s", "err"
        if "crasheo" in msg:
            return f"{hm}  💥  Crash — reiniciando en 10s", "err"
        if "detenido" in msg:
            return f"{hm}  ■   Bot detenido por el usuario", "dim"
        return f"{hm}  {msg[:80]}", "dim"

    # ── Unknown / stack trace continuation ────────────────────────────────────
    if raw.startswith(" ") or raw.startswith("\t"):
        return f"     {raw.strip()[:85]}", "err"

    return f"  {raw[:90]}", "dim"


# ── Process helpers ────────────────────────────────────────────────────────────

def _count_bots() -> int:
    try:
        r = subprocess.run(
            ["wmic", "process", "where",
             "name='python.exe' and commandline like '%mt5_bot%'",
             "get", "ProcessId", "/format:list"],
            capture_output=True, text=True, timeout=8, creationflags=FLAGS,
        )
        return sum(1 for l in r.stdout.splitlines() if l.strip().startswith("ProcessId="))
    except Exception:
        return 0


def _kill_bots():
    subprocess.run(
        ["wmic", "process", "where",
         "name='python.exe' and commandline like '%mt5_bot%'",
         "call", "terminate"],
        capture_output=True, creationflags=FLAGS,
    )
    for bot in BOTS:
        subprocess.run(
            ["taskkill", "/F", "/FI", f"WINDOWTITLE eq {bot['title']}"],
            capture_output=True, creationflags=FLAGS,
        )


# ── Bot panel widget ───────────────────────────────────────────────────────────

class BotPanel(tk.Frame):
    LINES = 7

    def __init__(self, parent, bot: dict, **kw):
        super().__init__(parent, bg=CARD, highlightbackground=CARDBRD,
                         highlightthickness=1, **kw)
        self.bot    = bot
        self._mtime = 0.0
        self._build()

    def _build(self):
        accent = self.bot["color"]

        # Top accent stripe (3px)
        tk.Frame(self, bg=accent, height=3).pack(fill="x")

        # Header row
        hdr = tk.Frame(self, bg=CARD, padx=8, pady=5)
        hdr.pack(fill="x")

        self.dot = tk.Label(hdr, text="○", font=("Segoe UI", 11),
                            bg=CARD, fg=DIM)
        self.dot.pack(side="left")

        tk.Label(hdr, text=f" {self.bot['display']} ",
                 font=("Segoe UI", 10, "bold"), bg=CARD, fg=accent).pack(side="left")
        tk.Label(hdr, text=self.bot["tf"],
                 font=("Segoe UI", 8), bg=CARD, fg=DIMLT).pack(side="left")

        self.ago_lbl = tk.Label(hdr, text="offline",
                                font=("Segoe UI", 7), bg=CARD, fg=DIM)
        self.ago_lbl.pack(side="right")

        # Thin separator
        tk.Frame(self, bg=CARDBRD, height=1).pack(fill="x")

        # Log text
        tf = tk.Frame(self, bg=CARD, padx=5, pady=4)
        tf.pack(fill="both", expand=True)

        self.txt = tk.Text(
            tf,
            font=("Consolas", 7),
            bg=CARD, fg=C_INFO,
            relief="flat", bd=0,
            state="disabled", wrap="none",
            height=self.LINES,
            highlightthickness=0,
            insertbackground=CARD,
        )
        self.txt.pack(fill="both", expand=True)

        # Color tags
        self.txt.tag_configure("buy",   foreground=C_BUY,   font=("Consolas", 7, "bold"))
        self.txt.tag_configure("sell",  foreground=C_SELL,  font=("Consolas", 7, "bold"))
        self.txt.tag_configure("sent",  foreground=C_SENT,  font=("Consolas", 7, "bold"))
        self.txt.tag_configure("warn",  foreground=C_WARN)
        self.txt.tag_configure("err",   foreground=C_ERR,   font=("Consolas", 7, "bold"))
        self.txt.tag_configure("info",  foreground=C_INFO)
        self.txt.tag_configure("dim",   foreground=C_DIM)
        self.txt.tag_configure("boost", foreground=C_BOOST)
        self.txt.tag_configure("sep",   foreground="#2e3a5e")

    def refresh(self):
        mtime = _log_mtime(self.bot["log"])
        now   = time.time()

        # Status dot
        if mtime == 0:
            self.dot.configure(fg=DIM, text="○")
            self.ago_lbl.configure(text="sin log", fg=DIM)
        elif now - mtime < 45:
            self.dot.configure(fg=GREEN, text="●")
            self.ago_lbl.configure(text=f"{int(now - mtime)}s", fg=GREEN)
        elif now - mtime < 180:
            self.dot.configure(fg=YELLOW, text="●")
            self.ago_lbl.configure(text=f"{int((now - mtime)//60)}m", fg=YELLOW)
        else:
            self.dot.configure(fg=RED, text="●")
            self.ago_lbl.configure(text=f">{int((now - mtime)//60)}m", fg=RED)

        # Only redraw if file changed
        if mtime == self._mtime:
            return
        self._mtime = mtime

        lines = _log_tail(self.bot["log"], self.LINES)
        parsed = [_fmt(l) for l in lines]
        parsed = [p for p in parsed if p]

        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        for text, tag in parsed:
            self.txt.insert("end", text + "\n", tag)
        self.txt.configure(state="disabled")


# ── Main application ───────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MT5 Pro Suite — Bot Dashboard")
        self.geometry("1400x820")
        self.minsize(1100, 620)
        self.configure(bg=BG)
        self._busy      = False
        self._proc_count = 0
        self._panels: list[BotPanel] = []
        self._build()
        self._start_proc_thread()
        self._loop()

    def _build(self):
        # ── Top bar ────────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=TOPBAR, pady=10)
        top.pack(fill="x")

        left = tk.Frame(top, bg=TOPBAR)
        left.pack(side="left", padx=(18, 0))

        tk.Label(left, text="MT5 PRO SUITE",
                 font=("Segoe UI", 15, "bold"), bg=TOPBAR, fg=WHITE).pack(side="left")
        tk.Label(left, text="  12 BOTS",
                 font=("Segoe UI", 9), bg=TOPBAR, fg=DIMLT).pack(side="left", pady=(4, 0))

        self.proc_lbl = tk.Label(left, text="",
                                  font=("Segoe UI", 8), bg=TOPBAR, fg=DIMLT)
        self.proc_lbl.pack(side="left", padx=(20, 0), pady=(4, 0))

        right = tk.Frame(top, bg=TOPBAR)
        right.pack(side="right", padx=(0, 18))

        self.clock_lbl = tk.Label(right, text="",
                                   font=("Segoe UI", 8, "bold"), bg=TOPBAR, fg=DIMLT)
        self.clock_lbl.pack(side="right", padx=(14, 0))

        self.bstop = tk.Button(
            right, text="■  DETENER BOTS",
            font=("Segoe UI", 10, "bold"),
            bg=RDIM, fg=RED,
            activebackground="#550010", activeforeground=RED,
            relief="flat", bd=0, cursor="hand2", padx=14, pady=7,
            command=self._stop,
        )
        self.bstop.pack(side="right", padx=(0, 6))

        self.bstart = tk.Button(
            right, text="▶  INICIAR BOTS",
            font=("Segoe UI", 10, "bold"),
            bg=GDIM, fg=GREEN,
            activebackground="#004a28", activeforeground=GREEN,
            relief="flat", bd=0, cursor="hand2", padx=14, pady=7,
            command=self._start,
        )
        self.bstart.pack(side="right", padx=(0, 6))

        # ── Thin accent line ───────────────────────────────────────────────────
        tk.Frame(self, bg="#161630", height=2).pack(fill="x")

        # ── 4×3 bot grid ───────────────────────────────────────────────────────
        grid = tk.Frame(self, bg=BG, padx=6, pady=6)
        grid.pack(fill="both", expand=True)

        COLS = 4
        for c in range(COLS):
            grid.columnconfigure(c, weight=1, uniform="col")
        for r in range(3):
            grid.rowconfigure(r, weight=1, uniform="row")

        for idx, bot in enumerate(BOTS):
            row, col = divmod(idx, COLS)
            panel = BotPanel(grid, bot)
            panel.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            self._panels.append(panel)

    # ── Background process counter ─────────────────────────────────────────────

    def _start_proc_thread(self):
        def _worker():
            while True:
                self._proc_count = _count_bots()
                time.sleep(10)
        threading.Thread(target=_worker, daemon=True).start()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _start(self):
        if self._busy:
            return
        self._busy = True
        self.proc_lbl.configure(text="  Iniciando bots...", fg=YELLOW)
        threading.Thread(target=self._do_start, daemon=True).start()

    def _do_start(self):
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", str(BAT_FILE)],
                cwd=str(BOT_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            time.sleep(3)
        except Exception as exc:
            self.after(0, lambda: self.proc_lbl.configure(
                text=f"  Error: {exc}", fg=RED))
        finally:
            self._busy = False

    def _stop(self):
        if self._busy:
            return
        self._busy = True
        self.proc_lbl.configure(text="  Deteniendo bots...", fg=YELLOW)
        threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_stop(self):
        try:
            _kill_bots()
            time.sleep(2)
        except Exception as exc:
            self.after(0, lambda: self.proc_lbl.configure(
                text=f"  Error: {exc}", fg=RED))
        finally:
            self._busy = False

    # ── Refresh loop ───────────────────────────────────────────────────────────

    def _loop(self):
        self._refresh()
        self.after(2000, self._loop)

    def _refresh(self):
        # UTC clock
        self.clock_lbl.configure(
            text=datetime.utcnow().strftime("UTC  %H:%M:%S"))

        # Process count
        if not self._busy:
            n = self._proc_count
            active = sum(
                1 for p in self._panels
                if time.time() - _log_mtime(p.bot["log"]) < 45
            )
            if n > 0:
                self.proc_lbl.configure(
                    text=f"  ● {n} proceso(s)   {active}/12 activos",
                    fg=GREEN)
            else:
                self.proc_lbl.configure(
                    text="  ○ bots detenidos", fg=DIM)

        # Refresh panels
        for panel in self._panels:
            panel.refresh()


if __name__ == "__main__":
    os.chdir(BOT_DIR)
    App().mainloop()
