@echo off
setlocal
cd /d "%~dp0"
echo MT5 bot suite status...
python WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running
echo.
pause
