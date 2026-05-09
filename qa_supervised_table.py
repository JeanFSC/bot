from pathlib import Path
import re, subprocess, json, os, sys
ROOT=Path(__file__).resolve().parent
LOGS=[('EURUSD','bot_eurusd.log'),('GBPUSD','bot_gbpusd.log'),('USDJPY','bot_jpy.log'),('XAUUSD','bot_gold.log'),('AUDUSD','bot_aud.log'),('GOLD_M5','bot_gold_m5.log'),('USDCAD','bot_usdcad.log'),('NZDUSD','bot_nzdusd.log'),('GBPJPY','bot_gbpjpy.log'),('XAGUSD','bot_silver.log'),('JPY_ASIA','bot_jpy_asia.log'),('USDCHF','bot_usdchf.log')]
err=re.compile(r'ERROR|Exception|Traceback|CHECK failed|crasheo|rejected|retcode|failed',re.I)
sent=re.compile(r'Execution status=sent|status=sent',re.I)
print('BOT      lines err sent last_state')
print('-'*90)
for name,fn in LOGS:
    p=ROOT/'logs'/fn
    lines=p.read_text('utf-8','replace').splitlines() if p.exists() else []
    errs=sum(1 for l in lines if err.search(l)); sends=sum(1 for l in lines if sent.search(l))
    state='NO_LOG'
    for l in reversed(lines):
        if 'Signal=' in l or 'Session filter:' in l or 'Execution status=' in l or 'CHECK failed' in l:
            state=l.split(' mt5_bot - ')[-1][-120:]
            break
    print(f'{name:<8} {len(lines):>5} {errs:>3} {sends:>4} {state}')
# count bots
ps = "@((Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'mt5_bot' })).Count"
r=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,timeout=10)
print('PROCESS_COUNT', (r.stdout or '').strip())
