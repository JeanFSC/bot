@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
echo.
echo === FORCE ORDER DEMO - EURUSD BUY 0.01 LOT ===
echo.
python _force_order.py
