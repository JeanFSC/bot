@echo off
REM Runs a 30-day replay/backtest report for the autonomous agent configs.

cd /d "%~dp0"
call MT5_AGENT.bat replay-30d
pause
