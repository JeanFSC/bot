from __future__ import annotations
import os, re, time, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOGS={
 'EURUSD':'bot_eurusd.log','GBPUSD':'bot_gbpusd.log','USDJPY':'bot_jpy.log','XAUUSD':'bot_gold.log','AUDUSD':'bot_aud.log','GOLD_M5':'bot_gold_m5.log',
 'USDCAD':'bot_usdcad.log','NZDUSD':'bot_nzdusd.log','GBPJPY':'bot_gbpjpy.log','XAGUSD':'bot_silver.log','JPY_ASIA':'bot_jpy_asia.log','USDCHF':'bot_usdchf.log'}
ERR_PAT=re.compile(r'ERROR|Exception|Traceback|CHECK failed|crasheo|rejected|retcode|failed', re.I)
SENT_PAT=re.compile(r'Execution status=sent|status=sent', re.I)
SIG_PAT=re.compile(r'Signal=(BUY|SELL|NONE).*', re.I)
summary={}
for name,fn in LOGS.items():
    p=ROOT/'logs'/fn
    txt=p.read_text(encoding='utf-8', errors='replace') if p.exists() else ''
    lines=txt.splitlines()
    errs=[l for l in lines if ERR_PAT.search(l)]
    sent=[l for l in lines if SENT_PAT.search(l)]
    sigs=[l for l in lines if SIG_PAT.search(l)]
    balances=[l for l in lines if 'Balance=' in l and 'Equity=' in l]
    sessions=[l for l in lines if 'Session filter:' in l]
    summary[name]={
        'exists':p.exists(),'lines':len(lines),'errors':len(errs),'sent':len(sent),
        'last_signal':sigs[-1] if sigs else '', 'last_balance':balances[-1] if balances else '',
        'last_session_filter':sessions[-1] if sessions else '', 'last_error':errs[-1] if errs else '',
        'last_line':lines[-1] if lines else ''}
print(json.dumps(summary, indent=2, ensure_ascii=False))
if any(v['errors'] for v in summary.values()):
    print('MONITOR_FOUND_ERRORS')
else:
    print('MONITOR_NO_ERRORS')
print('MONITOR_SENT_TOTAL', sum(v['sent'] for v in summary.values()))
