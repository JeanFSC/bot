"""
MT5 Telegram Commander
======================
Controla los bots de trading via Telegram.
Comandos: /start_bots /stop_bots /status /log /balance /help
"""
from __future__ import annotations

import os, subprocess, sys, time, json
import urllib.request, urllib.parse, urllib.error
from datetime import datetime
from pathlib import Path

BOT_DIR   = Path(__file__).resolve().parent.parent.parent
BAT_START_LIVE = BOT_DIR / "START_REDUCED_FORWARD_TEST.bat"
BAT_START_SANDBOX = BOT_DIR / "START_RESEARCH_SANDBOX_ALL.bat"
LOG_DIR   = BOT_DIR / "logs"
ENV_FILE  = BOT_DIR / ".env"
BOT_TITLES = [
    "PRO USDCHF",
    "PRO GOLD",
    "PRO GBPJPY",
]
FLAGS = 0x08000000  # CREATE_NO_WINDOW
STATUS_SCRIPT = BOT_DIR / "scripts" / "suite_status_report.py"

def _load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    for k in ("MT5_TELEGRAM_TOKEN","MT5_TELEGRAM_CHAT_ID"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env

class TelegramBot:
    API = "https://api.telegram.org/bot{token}/{method}"
    def __init__(self, token, allowed_chat_id):
        self.token = token
        self.allowed_chat_id = allowed_chat_id
        self._offset = 0

    def _call(self, method, payload=None, timeout=30):
        import logging as _lg
        url = self.API.format(token=self.token, method=method)
        data = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
              headers={"Content-Type":"application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            _lg.getLogger("commander").warning("Telegram API error [%s]: %s", method, e)
            return {}

    def send(self, chat_id, text):
        self._call("sendMessage", {"chat_id":chat_id,"text":text,"parse_mode":"Markdown"})

    def get_updates(self):
        r = self._call("getUpdates", {"offset":self._offset,"timeout":20}, timeout=30)
        updates = r.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return updates

    def reply(self, update, text):
        self.send(update["message"]["chat"]["id"], text)

    def is_allowed(self, update):
        return update.get("message",{}).get("chat",{}).get("id") == self.allowed_chat_id

# ─── Helper functions ──────────────────────────────────────────────────────────

def _count_bots():
    try:
        ps = (
            "$p=Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'mt5_bot' }; "
            "@($p).Count"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=8, creationflags=FLAGS)
        return int((r.stdout or "0").strip().splitlines()[-1])
    except:
        return -1

def _suite_report_json():
    try:
        cmd = (
            f"$env:PYTHONPATH='{BOT_DIR / 'src'}'; "
            f"python '{STATUS_SCRIPT}' --since 2026-05-15 --write | Out-Null; "
            f"Get-Content -Raw '{BOT_DIR / 'reports' / 'suite_status_report.json'}'"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=45, creationflags=FLAGS,
        )
        if r.returncode != 0 or not (r.stdout or "").strip():
            return None
        return json.loads(r.stdout)
    except Exception:
        return None

def _start_bots():
    try:
        subprocess.Popen(["cmd.exe","/c",str(BAT_START_LIVE)],
                         cwd=str(BOT_DIR),
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        time.sleep(2)
        subprocess.Popen(["cmd.exe","/c",str(BAT_START_SANDBOX)],
                         cwd=str(BOT_DIR),
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        time.sleep(5)
        n = _count_bots()
        return f"Live + sandbox iniciados. Procesos activos: {n}"
    except Exception as e:
        return f"Error al iniciar: {e}"

def _stop_bots():
    try:
        ps = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'mt5_bot' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, creationflags=FLAGS)
        for t in BOT_TITLES:
            subprocess.run(["taskkill","/F","/FI",f"WINDOWTITLE eq {t}"],
                           capture_output=True, creationflags=FLAGS)
        time.sleep(2)
        return "Bots detenidos."
    except Exception as e:
        return f"Error al detener: {e}"

def _get_status():
    report = _suite_report_json()
    if report:
        mt5 = report.get("mt5") or {}
        account = mt5.get("account") or {}
        terminal = mt5.get("terminal") or {}
        positions = mt5.get("positions") or []
        live_loops = sum(
            1 for p in report.get("processes", [])
            if "mt5_bot trade" in str(p.get("CommandLine", ""))
            and "python" in str(p.get("Name", "")).lower()
            and "--trade-enabled" in str(p.get("CommandLine", ""))
        )
        dry_loops = sum(
            1 for p in report.get("processes", [])
            if "mt5_bot trade" in str(p.get("CommandLine", ""))
            and "python" in str(p.get("Name", "")).lower()
            and "--trade-enabled" not in str(p.get("CommandLine", ""))
        )
        return (
            f"*Estado suite: {report.get('status', 'UNKNOWN')}*\n"
            f"MT5 connected: {terminal.get('connected', 'n/a')}\n"
            f"Live loops: {live_loops}\n"
            f"Dry-run loops: {dry_loops}\n"
            f"Balance: {account.get('balance', 'n/a')}\n"
            f"Equity: {account.get('equity', 'n/a')}\n"
            f"Open positions: {len(positions)}"
        )
    n = _count_bots()
    if n < 0:
        return "No se pudo verificar el estado."
    status = "ACTIVOS" if n > 0 else "DETENIDOS"
    return (
        f"*Estado: {status}*\n"
        f"Procesos: {n}\n"
        f"UTC: {datetime.utcnow().strftime(chr(37)+'H:%M:%S')}"
    )

def _get_log():
    logs = sorted(LOG_DIR.glob("trade_*.log"), reverse=True) if LOG_DIR.exists() else []
    if not logs:
        logs = sorted(LOG_DIR.glob("check_*.log"), reverse=True) if LOG_DIR.exists() else []
    if not logs:
        return "Sin datos."
    log = logs[0]
    try:
        lines = log.read_text(encoding="utf-8",errors="replace").splitlines()
        last = "\n".join(lines[-20:])
        return f"*Log `{log.name}` (ultimas 20 lineas):*\n`{last[:3500]}`"
    except Exception as e:
        return f"Error: {e}"

def _get_balance():
    report = _suite_report_json()
    if not report:
        return "Sin datos de balance."
    mt5 = report.get("mt5") or {}
    account = mt5.get("account") or {}
    positions = mt5.get("positions") or []
    return (
        "*Balance actual:*\n"
        f"`Balance={account.get('balance', 'n/a')} "
        f"Equity={account.get('equity', 'n/a')} "
        f"OpenPositions={len(positions)}`"
    )

HELP_TEXT = (
    "*MT5 Reduced Suite Commander*\n\n"
    "/start\\_bots  - Iniciar live + sandbox\n"
    "/stop\\_bots   - Detener live + sandbox\n"
    "/status      - Estado actual\n"
    "/log         - Ultimas 20 lineas del log\n"
    "/balance     - Ultimo balance/equity registrado\n"
    "/help        - Este mensaje"
)

def handle_command(bot, update):
    text = update.get("message",{}).get("text","").strip()
    cmd = text.split()[0].lower().split("@")[0]
    if cmd == "/start_bots":
        bot.reply(update, "Iniciando bots...")
        bot.reply(update, _start_bots())
    elif cmd == "/stop_bots":
        bot.reply(update, "Deteniendo bots...")
        bot.reply(update, _stop_bots())
    elif cmd == "/status":
        bot.reply(update, _get_status())
    elif cmd == "/log":
        bot.reply(update, _get_log())
    elif cmd == "/balance":
        bot.reply(update, _get_balance())
    elif cmd in ("/help", "/start"):
        bot.reply(update, HELP_TEXT)
    else:
        bot.reply(update, f"Comando no reconocido: `{text}`\nUsa /help.")

def main():
    import logging
    log_file = str(LOG_DIR / "telegram_commander.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    log = logging.getLogger("commander")

    env = _load_env()
    token = env.get("MT5_TELEGRAM_TOKEN","")
    chat_id_str = env.get("MT5_TELEGRAM_CHAT_ID","")
    if not token or not chat_id_str:
        log.error("Falta MT5_TELEGRAM_TOKEN o MT5_TELEGRAM_CHAT_ID en .env")
        sys.exit(1)
    allowed_chat_id = int(chat_id_str)
    bot = TelegramBot(token, allowed_chat_id)
    log.info("Telegram Commander iniciado. Chat ID: %s | Token suffix: ...%s",
             allowed_chat_id, token[-8:])

    log.info("Drenando actualizaciones pendientes...")
    bot.get_updates()

    log.info("Enviando mensaje de inicio a chat_id=%s ...", allowed_chat_id)
    result = bot._call("sendMessage", {
        "chat_id": allowed_chat_id,
        "text": f"*MT5 Commander conectado*\nModo: suite reducida\nUTC: {datetime.utcnow().strftime(chr(37)+'Y-%m-%d %H:%M:%S')}\nUsa /help para ver comandos.",
        "parse_mode": "Markdown",
    })
    if result.get("ok"):
        log.info("Mensaje de inicio enviado OK.")
    else:
        log.warning("No se pudo enviar mensaje de inicio: %s", result)
        log.warning("Verifica que MT5_TELEGRAM_CHAT_ID sea tu ID personal (no el del bot).")
        log.warning("Usa @userinfobot en Telegram para obtener tu ID.")

    log.info("Esperando comandos...")
    while True:
        try:
            for update in bot.get_updates():
                if "message" not in update:
                    continue
                if not bot.is_allowed(update):
                    cid = update["message"]["chat"]["id"]
                    log.info("Acceso denegado a chat_id=%s", cid)
                    bot.send(cid, "No autorizado.")
                    continue
                text = update.get("message",{}).get("text","")
                log.info("Comando recibido: %r", text)
                handle_command(bot, update)
        except KeyboardInterrupt:
            log.info("Commander detenido por teclado.")
            break
        except Exception as e:
            log.error("Error en bucle principal: %s", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
