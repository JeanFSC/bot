@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1

echo ===DEBUG=== > _debug.log 2>&1
python --version >> _debug.log 2>&1
echo PYTHONPATH=%PYTHONPATH% >> _debug.log 2>&1
echo CWD=%CD% >> _debug.log 2>&1
python -c "import sys; sys.stderr.write('STDERR TEST\n'); import mt5_bot.config; print('config OK')" >> _debug.log 2>&1
python -c "
import sys, traceback
sys.stdout.reconfigure(line_buffering=True)
try:
    from mt5_bot.config import load_config_from_env
    cfg = load_config_from_env('config/demo.yaml')
    print('CONFIG OK login=' + str(cfg.account.login))
except Exception as e:
    traceback.print_exc()
" >> _debug.log 2>&1
type _debug.log
pause
