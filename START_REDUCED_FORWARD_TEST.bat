@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

echo ============================================================
echo  MT5 REDUCED FORWARD TEST - USDCHF / XAUUSD / GBPJPY
echo ============================================================
echo.
echo This launcher starts only the reduced candidate set selected
echo from the 2026-05-15+ audit. It is still live-demo trading:
echo each restart script uses --trade-enabled.
echo.
echo Use STOP_SUITE.bat to stop.
echo.

python WATCHDOG_SAFE_24H.py --mode live-demo --preflight
if errorlevel 1 (
    echo.
    echo PREFLIGHT FAILED. Reduced suite NOT started.
    pause
    exit /b 1
)

echo Starting reduced candidates...
start "PRO USDCHF" cmd /k "_restart_usdchf.bat"
timeout /t 3 /nobreak >nul
start "PRO GOLD" cmd /k "_restart_gold.bat"
timeout /t 3 /nobreak >nul
start "PRO GBPJPY" cmd /k "_restart_gbpjpy.bat"

echo.
echo Reduced forward-test launch requested.
echo Run: python scriptssuite_status_report.py --since 2026-05-15 --write
echo.
pause
