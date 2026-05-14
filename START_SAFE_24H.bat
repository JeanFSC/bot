@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

echo ============================================================
echo  MT5 SAFE 24H MODE - trade_enabled=false / NO LIVE OVERRIDE
echo ============================================================
echo.

python WATCHDOG_SAFE_24H.py --preflight
if errorlevel 1 (
    echo.
    echo PREFLIGHT FAILED. Suite NOT started.
    pause
    exit /b 1
)

echo Starting safe watchdog...
start "MT5 SAFE WATCHDOG" cmd /k "python WATCHDOG_SAFE_24H.py --watch --interval 300"

echo Starting 12-bot safe suite...
start "MT5 SAFE SUITE LAUNCHER" cmd /k "_run_all_pro_autorestart.bat"

echo.
echo SAFE 24H launch requested. Use STATUS_SUITE.bat to inspect or STOP_SUITE.bat to close.
echo.
pause
