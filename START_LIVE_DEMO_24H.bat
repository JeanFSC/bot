@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   MT5 PRO SUITE - LIVE DEMO MODE
echo   Allows --trade-enabled on demo account. Watchdog will NOT
echo   kill the suite just because trades are enabled or positions exist.
echo ============================================================
echo.
python WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running
if %errorlevel%==0 (
    echo.
    echo Live-demo suite already running. No duplicate launch needed.
    echo Use STATUS_SUITE.bat to inspect or STOP_SUITE.bat to close.
    pause
    exit /b 0
)
echo.
echo Starting live-demo watchdog...
start "MT5 LIVE DEMO WATCHDOG" cmd /k "python WATCHDOG_SAFE_24H.py --mode live-demo --watch --interval 300"
echo.
echo Starting 12-bot autorestart suite...
start "MT5 PRO LIVE DEMO SUITE" cmd /k "_run_all_pro_autorestart.bat"
echo.
echo Live-demo suite launched.
pause
