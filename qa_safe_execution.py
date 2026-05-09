from __future__ import annotations
import os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CONFIGS=[
 ('EURUSD','config/pro.yaml'),('GBPUSD','config/pro_gbp.yaml'),('USDJPY','config/pro_jpy.yaml'),('XAUUSD','config/pro_gold.yaml'),
 ('AUDUSD','config/pro_aud.yaml'),('GOLD_M5','config/pro_gold_m5.yaml'),('USDCAD','config/pro_usdcad.yaml'),('NZDUSD','config/pro_nzdusd.yaml'),
 ('GBPJPY','config/pro_gbpjpy.yaml'),('XAGUSD','config/pro_silver.yaml'),('JPY_ASIA','config/pro_jpy_asia.yaml'),('USDCHF','config/pro_usdchf.yaml')]
env=os.environ.copy(); env['PYTHONPATH']=str(ROOT/'src')
results=[]
for name,cfg in CONFIGS:
    print(f'\n== SAFE LOOP {name} ==', flush=True)
    t=time.time()
    db=f'data/qa_{name.lower()}.sqlite'
    cmd=[sys.executable,'-m','mt5_bot','trade','--config',cfg,'--db',db,'--max-seconds','4','--poll-seconds','1']
    p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=25)
    out=(p.stdout or '')+(p.stderr or '')
    lines=out.splitlines()
    tail='\n'.join(lines[-18:])
    print(tail, flush=True)
    dangerous='status=sent' in out.lower()
    signal_line=next((l for l in reversed(lines) if 'Signal=' in l), '')
    exec_line=next((l for l in reversed(lines) if 'Execution status=' in l), '')
    results.append((name,cfg,p.returncode,time.time()-t,dangerous,signal_line,exec_line,tail))
print('\n== SAFE EXEC SUMMARY ==')
for name,cfg,code,sec,danger,signal,exe,tail in results:
    status='OK' if code==0 and not danger else 'FAIL'
    print(f'{status:<4} {name:<8} code={code} sec={sec:.1f} sent={danger} signal="{signal[-100:]}" exec="{exe[-100:]}"')
if any(code!=0 or danger for _,_,code,_,danger,_,_,_ in results):
    raise SystemExit(1)
print('SAFE_EXECUTION_ALL_OK_NO_REAL_ORDERS')
