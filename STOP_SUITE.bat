@echo off
setlocal
cd /d "%~dp0"
echo Closing MT5 bot suite processes...
python WATCHDOG_SAFE_24H.py --stop
echo.
echo Done. Review output above.
pause
