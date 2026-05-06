@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
pythonw bot_controller.py
if errorlevel 1 (
    echo Error lanzando la app. Intentando con python...
    python bot_controller.py
    pause
)
