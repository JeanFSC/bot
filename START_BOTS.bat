@echo off
cd /d "C:\Users\jean_\Desktop\mt5_trading_bot"
set PYTHONPATH=C:\Users\jean_\Desktop\mt5_trading_bot\src
set PYTHONUNBUFFERED=1
echo ============================================================
echo  MT5 PRO SUITE - LAUNCHER DIRECT
echo  Python: .venv\Scripts\python.exe
echo ============================================================
".venv\Scripts\python.exe" LAUNCHER_DIRECT.py
pause
