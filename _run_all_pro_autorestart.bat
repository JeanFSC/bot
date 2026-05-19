@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%TIME%] Lanzando MT5 PRO Bot Suite 12 bots...
start "PRO EURUSD" cmd /k "_restart_eurusd.bat %*"
start "PRO GBPUSD" cmd /k "_restart_gbpusd.bat %*"
start "PRO USDJPY" cmd /k "_restart_jpy.bat %*"
start "PRO XAUUSD (Gold)" cmd /k "_restart_gold.bat %*"
start "PRO AUDUSD" cmd /k "_restart_aud.bat %*"
start "PRO XAUUSD M5 (Gold 24h)" cmd /k "_restart_gold_m5.bat %*"
start "PRO USDCAD" cmd /k "_restart_usdcad.bat %*"
start "PRO NZDUSD" cmd /k "_restart_nzdusd.bat %*"
start "PRO GBPJPY" cmd /k "_restart_gbpjpy.bat %*"
start "PRO XAGUSD (Silver)" cmd /k "_restart_silver.bat %*"
start "PRO USDJPY ASIA" cmd /k "_restart_jpy_asia.bat %*"
start "PRO USDCHF" cmd /k "_restart_usdchf.bat %*"
echo [%TIME%] Suite lanzada. Portfolio guard limita exposicion total.
pause
