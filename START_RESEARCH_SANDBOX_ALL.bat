@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

echo ============================================================
echo  MT5 RESEARCH SANDBOX ALL - NON-LIVE CANDIDATES
echo ============================================================
echo.
echo This starts redesigned/replacement candidates WITHOUT --trade-enabled.
echo They must not open trades. Live reduced suite remains separate.
echo.

set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1

start "SANDBOX USDJPY LONDON V2" cmd /c "python -m mt5_bot check --config config/research_usdjpy_london_v2.yaml && python -m mt5_bot trade --config config/research_usdjpy_london_v2.yaml --db data/research_usdjpy_london_v2.sqlite >> logs/sandbox_usdjpy_london_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX EURUSD LONDON V2" cmd /c "python -m mt5_bot check --config config/research_eurusd_london_v2.yaml && python -m mt5_bot trade --config config/research_eurusd_london_v2.yaml --db data/research_eurusd_london_v2.sqlite >> logs/sandbox_eurusd_london_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX GBPUSD LONDON V2" cmd /c "python -m mt5_bot check --config config/research_gbpusd_london_v2.yaml && python -m mt5_bot trade --config config/research_gbpusd_london_v2.yaml --db data/research_gbpusd_london_v2.sqlite >> logs/sandbox_gbpusd_london_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX NZDUSD LONDON V2" cmd /c "python -m mt5_bot check --config config/research_nzdusd_london_v2.yaml && python -m mt5_bot trade --config config/research_nzdusd_london_v2.yaml --db data/research_nzdusd_london_v2.sqlite >> logs/sandbox_nzdusd_london_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX USDCAD NY V2" cmd /c "python -m mt5_bot check --config config/research_usdcad_ny_v2.yaml && python -m mt5_bot trade --config config/research_usdcad_ny_v2.yaml --db data/research_usdcad_ny_v2.sqlite >> logs/sandbox_usdcad_ny_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX AUDUSD ASIA LONDON V2" cmd /c "python -m mt5_bot check --config config/research_audusd_asia_london_v2.yaml && python -m mt5_bot trade --config config/research_audusd_asia_london_v2.yaml --db data/research_audusd_asia_london_v2.sqlite >> logs/sandbox_audusd_asia_london_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX XAUUSD M5 V2" cmd /c "python -m mt5_bot check --config config/research_xauusd_m5_v2.yaml && python -m mt5_bot trade --config config/research_xauusd_m5_v2.yaml --db data/research_xauusd_m5_v2.sqlite >> logs/sandbox_xauusd_m5_v2.log 2>&1"
timeout /t 2 /nobreak >nul
start "SANDBOX XAGUSD V2" cmd /c "python -m mt5_bot check --config config/research_xagusd_v2.yaml && python -m mt5_bot trade --config config/research_xagusd_v2.yaml --db data/research_xagusd_v2.sqlite >> logs/sandbox_xagusd_v2.log 2>&1"

echo.
echo Research sandbox batch launch requested.
echo No --trade-enabled was used.
echo.
pause
