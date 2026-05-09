from __future__ import annotations
import os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'src'))
os.environ.setdefault('MT5_LOGIN','1')
os.environ.setdefault('MT5_PASSWORD','x')
os.environ.setdefault('MT5_SERVER','MetaQuotes-Demo')
from mt5_bot.config import load_config

# Expected table sent by Jean / Claude
EXPECTED = [
 ('EURUSD M15','config/pro.yaml',8.3, dict(symbol='EURUSD', timeframe='M15', trend_timeframe='H1', risk=2.0, adx=22, tp=3.0, retest=True, candle=True, rsi=(65,35), session=(7,20), session2=None)),
 ('GBPUSD M15','config/pro_gbp.yaml',8.3, dict(symbol='GBPUSD', timeframe='M15', trend_timeframe='H1', risk=1.8, adx=22, tp=3.0, retest=True, candle=True, rsi=(65,35), session=(7,20), session2=None)),
 ('USDJPY M15','config/pro_jpy.yaml',8.7, dict(symbol='USDJPY', timeframe='M15', trend_timeframe='H1', risk=1.8, adx=22, tp=3.0, retest=True, candle=True, rsi=(70,30), session=(7,20), session2=None)),
 ('XAUUSD M15','config/pro_gold.yaml',8.7, dict(symbol='XAUUSD', timeframe='M15', trend_timeframe='H1', risk=1.5, adx=22, tp=3.0, retest=True, candle=True, session=(7,20), session2=None)),
 ('AUDUSD M15','config/pro_aud.yaml',8.5, dict(symbol='AUDUSD', timeframe='M15', trend_timeframe='H1', risk=1.8, adx=22, tp=3.0, retest=True, candle=True, rsi=(65,35), session=(7,20), session2=None)),
 ('XAUUSD M5','config/pro_gold_m5.yaml',8.5, dict(symbol='XAUUSD', timeframe='M5', trend_timeframe='M15', risk=1.5, adx=18, tp=3.0, retest=True, candle=True, session=(0,24), session2=None)),
 ('USDCAD M15','config/pro_usdcad.yaml',8.3, dict(symbol='USDCAD', timeframe='M15', trend_timeframe='H1', risk=1.5, adx=22, tp=3.0, retest=True, candle=True, session=(11,20), session2=None)),
 ('NZDUSD M15','config/pro_nzdusd.yaml',8.5, dict(symbol='NZDUSD', timeframe='M15', trend_timeframe='M30', risk=1.2, adx=22, tp=3.0, retest=True, candle=True, session=(20,24), session2=(0,7))),
 ('GBPJPY M15','config/pro_gbpjpy.yaml',7.7, dict(symbol='GBPJPY', timeframe='M15', trend_timeframe='H1', risk=1.5, adx=22, tp=3.0, retest=False, candle=False, rsi=(70,30), session=(7,17), session2=None)),
 ('XAGUSD M15','config/pro_silver.yaml',8.0, dict(symbol='XAGUSD', timeframe='M15', trend_timeframe='H1', risk=1.0, adx=20, tp=3.0, retest=True, candle=True, session=(0,23), session2=None)),
 ('USDJPY Asia','config/pro_jpy_asia.yaml',8.7, dict(symbol='USDJPY', timeframe='M15', trend_timeframe='M30', risk=1.5, adx=22, tp=3.0, retest=True, candle=True, rsi=(70,30), session=(20,24), session2=(0,7))),
 ('USDCHF M15','config/pro_usdchf.yaml',8.3, dict(symbol='USDCHF', timeframe='M15', trend_timeframe='H1', risk=1.2, adx=22, tp=3.0, retest=True, candle=True, session=(6,18), session2=None)),
]

def close(a,b): return abs(float(a)-float(b)) < 1e-9
print('BOT | SCORE | MATCH | CHECKLIST')
print('-'*160)
all_ok=True
for bot,path,score,exp in EXPECTED:
    c=load_config(ROOT/path)
    s=c.strategy
    checks=[]
    def add(name, ok, got=None, want=None):
        global all_ok
        checks.append((name,ok,got,want))
    add('symbol', c.symbol==exp['symbol'], c.symbol, exp['symbol'])
    add('tf', c.timeframe==exp['timeframe'], c.timeframe, exp['timeframe'])
    add('trend_tf', c.trend_timeframe==exp['trend_timeframe'], c.trend_timeframe, exp['trend_timeframe'])
    add('risk', close(c.risk.risk_pct, exp['risk']), c.risk.risk_pct, exp['risk'])
    add('adx', close(s.adx_min_value, exp['adx']), s.adx_min_value, exp['adx'])
    add('tp', close(s.atr_tp_multiplier, exp['tp']), s.atr_tp_multiplier, exp['tp'])
    add('retest', s.use_retest_filter==exp['retest'], s.use_retest_filter, exp['retest'])
    add('candle', s.use_candle_confirm==exp['candle'], s.use_candle_confirm, exp['candle'])
    add('session', (s.session_start_hour,s.session_end_hour)==exp['session'], (s.session_start_hour,s.session_end_hour), exp['session'])
    if exp.get('session2'):
        add('session2', s.use_session2 and (s.session2_start_hour,s.session2_end_hour)==exp['session2'], (s.use_session2,s.session2_start_hour,s.session2_end_hour), exp['session2'])
    else:
        add('session2_off', not s.use_session2, s.use_session2, False)
    if exp.get('rsi'):
        add('rsi', (s.rsi_buy_max,s.rsi_sell_min)==exp['rsi'], (s.rsi_buy_max,s.rsi_sell_min), exp['rsi'])
    # Claude methodology guardrails common to all
    add('demo_only', c.account.demo_only is True, c.account.demo_only, True)
    add('trade_enabled_false', c.execution.trade_enabled is False, c.execution.trade_enabled, False)
    add('portfolio_guard', c.use_global_risk_guard and c.max_portfolio_open_positions==5, (c.use_global_risk_guard,c.max_portfolio_open_positions), (True,5))
    add('daily_loss<=5', c.max_daily_loss_pct <= 5.0, c.max_daily_loss_pct, '<=5')
    ok=all(x[1] for x in checks)
    all_ok = all_ok and ok
    bad=[f"{n}: got {g} want {w}" for n,passed,g,w in checks if not passed]
    print(f"{bot:<12} | {score:<4} | {'OK' if ok else 'NO'} | " + ('all checks passed' if ok else '; '.join(bad)))
print('-'*160)
print('OVERALL', 'OK_MATCHES_CLAUDE_SCORE_TABLE' if all_ok else 'MISMATCH_FOUND')
