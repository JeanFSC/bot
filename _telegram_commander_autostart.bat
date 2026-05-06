@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title Telegram Commander (Auto-restart)

:loop
python src/mt5_bot/telegram_commander.py
echo [%TIME%] Commander reiniciando en 10s...
timeout /t 10 /nobreak >nul
goto loop
