@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title Telegram Commander - Control remoto de bots MT5

echo.
echo ============================================================
echo   TELEGRAM COMMANDER - Control remoto via Telegram
echo ============================================================
echo.
echo Mantene esta ventana abierta para poder controlar los bots
echo desde tu telefono via Telegram.
echo.
echo Comandos disponibles en Telegram:
echo   /start_bots  - Arranca los 3 bots
echo   /stop_bots   - Detiene todos los bots
echo   /status      - Estado actual
echo   /log         - Ultimas lineas del log
echo.

python src/mt5_bot/telegram_commander.py
echo.
echo Commander detenido. Presiona cualquier tecla para reiniciar...
pause
