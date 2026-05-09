from __future__ import annotations
import json, os, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
from mt5_bot.telegram_commander import _load_env, _get_status, HELP_TEXT, BOT_TITLES

env=_load_env()
token=env.get('MT5_TELEGRAM_TOKEN','')
chat_id=env.get('MT5_TELEGRAM_CHAT_ID','')
assert token, 'MT5_TELEGRAM_TOKEN missing'
assert chat_id, 'MT5_TELEGRAM_CHAT_ID missing'
assert len(BOT_TITLES) == 12, f'BOT_TITLES expected 12 got {len(BOT_TITLES)}'
api=f'https://api.telegram.org/bot{token}/'

def call(method,payload=None,timeout=20):
    data=json.dumps(payload or {}).encode('utf-8')
    req=urllib.request.Request(api+method,data=data,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

me=call('getMe')
assert me.get('ok'), me
print('GETME_OK', me['result'].get('username'), me['result'].get('id'))
status=_get_status()
assert 'Procesos:' in status, status
print('STATUS_FUNC_OK', status.replace('\n',' | ')[:220])
msg='QA Telegram MT5 OK ✅\nController v3 activo. 12 bots configurados. Prueba sin órdenes reales.\nUTC: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
sent=call('sendMessage',{'chat_id':int(chat_id),'text':msg})
assert sent.get('ok'), sent
print('SENDMESSAGE_OK message_id=', sent['result'].get('message_id'))
print('TELEGRAM_QA_OK')
