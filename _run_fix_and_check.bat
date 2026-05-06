@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set LOG=%~dp0_fix_log.txt

echo === Fixing source files === > "%LOG%"
python _fix_files.py >> "%LOG%" 2>&1
echo Fix exit: %errorlevel% >> "%LOG%"

echo === CHECK === >> "%LOG%"
python -m mt5_bot check --config config/demo.yaml >> "%LOG%" 2>&1
echo Check exit: %errorlevel% >> "%LOG%"

type "%LOG%"
pause
