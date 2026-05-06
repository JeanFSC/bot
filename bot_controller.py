"""
MT5 Bot Controller v2 -- Panel de control simple
Bugs fixes: no state=disabled (Windows black text bug),
            wmic kill (no mata el controller), pythonw path robusto
"""
import subprocess, threading, time, os, sys, tkinter as tk
from pathlib import Path
from datetime import datetime

BOT_DIR  = Path(__file__).resolve().parent
BAT_FILE = BOT_DIR / "_run_all_pro_autorestart.bat"
LOG_DIR  = BOT_DIR / "logs"
BOT_TITLES = ["PRO EURUSD","PRO GBPUSD","PRO USDJPY","PRO GOLD","PRO AUDUSD"]

BG       = "#0f0f1a"
CARD     = "#1a1a2e"
GREEN    = "#00d2a0"
GDIM     = "#005a44"
RED      = "#ff4757"
RDIM     = "#5a0000"
YELLOW   = "#ffa502"
WHITE    = "#e8e8f0"
GRAY     = "#4a4a6a"
GRLT     = "#7a7a9a"
BORDER   = "#2a2a4a"
FLAGS    = 0x08000000  # CREATE_NO_WINDOW

def _count_bots():
    try:
        r = subprocess.run(
            ["wmic","process","where",
             "name='python.exe' and commandline like '%mt5_bot%'",
             "get","ProcessId","/format:list"],
            capture_output=True, text=True, timeout=8, creationflags=FLAGS)
        return sum(1 for l in r.stdout.splitlines() if l.strip().startswith("ProcessId="))
    except:
        return 0

def _kill_bots():
    subprocess.run(
        ["wmic","process","where",
         "name='python.exe' and commandline like '%mt5_bot%'",
         "call","terminate"],
        capture_output=True, creationflags=FLAGS)
    for t in BOT_TITLES:
        subprocess.run(["taskkill","/F","/FI",f"WINDOWTITLE eq {t}"],
                       capture_output=True, creationflags=FLAGS)

def _log_tail(n=14):
    today = datetime.now().strftime("%Y%m%d")
    log = LOG_DIR / f"bot_{today}.log"
    if not log.exists():
        logs = sorted(LOG_DIR.glob("bot_*.log"),reverse=True) if LOG_DIR.exists() else []
        if not logs: return "(sin log)"
        log = logs[0]
    try:
        lines = log.read_text(encoding="utf-8",errors="replace").splitlines()
        return "\n".join(lines[-n:]) if lines else "(vacio)"
    except Exception as e:
        return f"(error: {e})"

def _log_mtime():
    today = datetime.now().strftime("%Y%m%d")
    log = LOG_DIR / f"bot_{today}.log"
    try: return log.stat().st_mtime
    except: return 0.0

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MT5 Bot Controller")
        self.geometry("700x540")
        self.minsize(600,460)
        self.configure(bg=BG)
        self._busy = False
        self._mtime = 0.0
        self._build()
        self._loop()

    def _build(self):
        hdr = tk.Frame(self,bg=CARD,pady=14); hdr.pack(fill="x")
        tk.Label(hdr,text="MT5 PRO BOT SUITE",font=("Segoe UI",18,"bold"),bg=CARD,fg=WHITE).pack()
        tk.Label(hdr,text="EURUSD  |  GBPUSD  |  USDJPY  |  XAUUSD  |  AUDUSD",
                 font=("Segoe UI",9),bg=CARD,fg=GRLT).pack(pady=(2,0))
        tk.Frame(self,bg=BORDER,height=2).pack(fill="x")

        sf = tk.Frame(self,bg=BG,pady=12); sf.pack(fill="x",padx=20)
        self.dot = tk.Label(sf,text="●",font=("Segoe UI",16),bg=BG,fg=GRAY); self.dot.pack(side="left")
        self.slbl = tk.Label(sf,text="Verificando...",font=("Segoe UI",12,"bold"),bg=BG,fg=GRLT)
        self.slbl.pack(side="left",padx=(8,0))
        self.plbl = tk.Label(sf,text="",font=("Segoe UI",9),bg=BG,fg=GRAY)
        self.plbl.pack(side="right")

        bf = tk.Frame(self,bg=BG); bf.pack(fill="x",padx=20,pady=(0,14))
        # BUG FIX: NEVER use state=disabled -- colors turn black on Windows
        # Instead use _busy flag and change colors/cursor only
        self.bstart = tk.Button(bf,text="\u25b6  INICIAR BOTS",font=("Segoe UI",14,"bold"),
            bg=GREEN,fg="#000000",activebackground="#00b890",activeforeground="#000000",
            relief="flat",bd=0,cursor="hand2",padx=20,pady=18,command=self._start)
        self.bstart.pack(side="left",expand=True,fill="x",padx=(0,8))
        self.bstop = tk.Button(bf,text="\u25a0  DETENER BOTS",font=("Segoe UI",14,"bold"),
            bg=RED,fg="#ffffff",activebackground="#cc3344",activeforeground="#ffffff",
            relief="flat",bd=0,cursor="hand2",padx=20,pady=18,command=self._stop)
        self.bstop.pack(side="left",expand=True,fill="x",padx=(8,0))

        lh = tk.Frame(self,bg=BG); lh.pack(fill="x",padx=20,pady=(6,4))
        tk.Label(lh,text="LOG EN TIEMPO REAL",font=("Segoe UI",8,"bold"),bg=BG,fg=GRLT).pack(side="left")
        self.ltlbl = tk.Label(lh,text="",font=("Segoe UI",8),bg=BG,fg=GRAY); self.ltlbl.pack(side="right")

        lw = tk.Frame(self,bg=CARD,highlightbackground=BORDER,highlightthickness=1)
        lw.pack(fill="both",expand=True,padx=20,pady=(0,14))
        self.txt = tk.Text(lw,font=("Consolas",8),bg=CARD,fg="#a0c4a0",
                           relief="flat",bd=8,state="disabled",wrap="none")
        sb = tk.Scrollbar(lw,orient="vertical",command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right",fill="y"); self.txt.pack(side="left",fill="both",expand=True)

        ftr = tk.Frame(self,bg=CARD,pady=6); ftr.pack(fill="x",side="bottom")
        tk.Label(ftr,text="demo_only=true  |  trade_enabled via bat",
                 font=("Segoe UI",8),bg=CARD,fg=GRAY).pack()

    def _start(self):
        if self._busy: return
        self._busy = True
        self._setstatus("Iniciando bots...",YELLOW)
        threading.Thread(target=self._do_start,daemon=True).start()

    def _do_start(self):
        try:
            subprocess.Popen(["cmd.exe","/c",str(BAT_FILE)],
                             cwd=str(BOT_DIR),creationflags=subprocess.CREATE_NEW_CONSOLE)
            time.sleep(3)
        except Exception as e:
            self.after(0,lambda:self._setstatus(f"Error: {e}",RED))
        finally: self._busy = False

    def _stop(self):
        if self._busy: return
        self._busy = True
        self._setstatus("Deteniendo bots...",YELLOW)
        threading.Thread(target=self._do_stop,daemon=True).start()

    def _do_stop(self):
        try:
            _kill_bots(); time.sleep(2)
        except Exception as e:
            self.after(0,lambda:self._setstatus(f"Error: {e}",RED))
        finally: self._busy = False

    def _setstatus(self,msg,color):
        self.after(0,lambda:(self.slbl.configure(text=msg,fg=color),
                             self.dot.configure(fg=color)))

    def _loop(self):
        self._refresh(); self.after(2000,self._loop)

    def _refresh(self):
        n = _count_bots(); running = n > 0
        if not self._busy:
            if running:
                self.dot.configure(fg=GREEN)
                self.slbl.configure(text="BOTS ACTIVOS",fg=GREEN)
                self.plbl.configure(text=f"{n} proceso(s) activos",fg=GRLT)
                self.bstart.configure(bg=GDIM,fg=GRLT,cursor="arrow",
                    activebackground=GDIM,activeforeground=GRLT)
                self.bstop.configure(bg=RED,fg="#ffffff",cursor="hand2",
                    activebackground="#cc3344",activeforeground="#ffffff")
            else:
                self.dot.configure(fg=RED)
                self.slbl.configure(text="BOTS DETENIDOS",fg=RED)
                self.plbl.configure(text="0 procesos",fg=GRAY)
                self.bstart.configure(bg=GREEN,fg="#000000",cursor="hand2",
                    activebackground="#00b890",activeforeground="#000000")
                self.bstop.configure(bg=RDIM,fg=GRLT,cursor="arrow",
                    activebackground=RDIM,activeforeground=GRLT)
        mtime = _log_mtime()
        if mtime != self._mtime:
            self._mtime = mtime
            tail = _log_tail()
            self.txt.configure(state="normal")
            self.txt.delete("1.0","end")
            self.txt.insert("end",tail)
            self.txt.see("end")
            self.txt.configure(state="disabled")
        if mtime > 0:
            ago = int(time.time()-mtime)
            s = f"{ago}s" if ago<120 else f"{ago//60}m"
            self.ltlbl.configure(text=f"ultima: {datetime.fromtimestamp(mtime):%H:%M:%S} ({s} atras)")
        else:
            self.ltlbl.configure(text="sin log hoy")

if __name__ == "__main__":
    os.chdir(BOT_DIR)
    App().mainloop()
