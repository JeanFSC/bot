from __future__ import annotations
import os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIGS = [
 ('EURUSD','config/pro.yaml'),
 ('GBPUSD','config/pro_gbp.yaml'),
 ('USDJPY','config/pro_jpy.yaml'),
 ('XAUUSD','config/pro_gold.yaml'),
 ('AUDUSD','config/pro_aud.yaml'),
 ('GOLD_M5','config/pro_gold_m5.yaml'),
 ('USDCAD','config/pro_usdcad.yaml'),
 ('NZDUSD','config/pro_nzdusd.yaml'),
 ('GBPJPY','config/pro_gbpjpy.yaml'),
 ('XAGUSD','config/pro_silver.yaml'),
 ('JPY_ASIA','config/pro_jpy_asia.yaml'),
 ('USDCHF','config/pro_usdchf.yaml'),
]

env=os.environ.copy()
env['PYTHONPATH']=str(ROOT/'src')
results=[]
for name,cfg in CONFIGS:
    print(f'\n== CHECK {name} {cfg} ==', flush=True)
    t=time.time()
    p=subprocess.run([sys.executable,'-m','mt5_bot','check','--config',cfg], cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
    out=(p.stdout or '') + (p.stderr or '')
    tail='\n'.join(out.splitlines()[-12:])
    print(tail, flush=True)
    results.append((name,cfg,p.returncode,time.time()-t,tail))
print('\n== SUMMARY ==')
for name,cfg,code,sec,tail in results:
    status='OK' if code==0 else 'FAIL'
    print(f'{status:<4} {name:<8} {cfg:<26} code={code} sec={sec:.1f}')
if any(code for _,_,code,_,_ in results):
    raise SystemExit(1)
print('MT5_CHECKS_ALL_OK')
