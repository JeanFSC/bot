@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src

:: Try pythonw first (runs without console window)
where pythonw >nul 2>&1
if %errorlevel% == 0 (
    start "" pythonw "%~dp0bot_controller.py"
    exit /b
)

:: Fallback: derive pythonw.exe path from python.exe location
for /f "tokens=*" %%p in ('where python 2^>nul') do (
    set PYDIR=%%~dpp
    goto found_python
)
goto no_python

:found_python
if exist "%PYDIR%pythonw.exe" (
    start "" "%PYDIR%pythonw.exe" "%~dp0bot_controller.py"
    exit /b
)

:: Last resort: plain python (shows console window)
:no_python
python "%~dp0bot_controller.py"
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado. Instala Python 3.8+ y agrega al PATH.
    pause
)
