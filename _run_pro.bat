@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1

echo.
echo ============================================================
echo   MT5 PRO BOT  ^|  EURUSD  ^|  H1 trend + M15 signal
echo   Strategy: EMA(9/21) + H1 EMA(50) trend filter
echo   RSI(14) confirmation + ATR dynamic SL/TP
echo   Risk/Reward: minimum 1:2  ^|  Trailing stop: ON
echo   Session: London+NY only (07:00-20:00 UTC)
echo   Lot: 0.5  ^|  Max spread: 1.2 pips
echo ============================================================
echo.

python -m mt5_bot check --config config/pro.yaml
if errorlevel 1 (
    echo [ERROR] CHECK failed. Verify MT5 connection.
    pause
    exit /b 1
)

echo.
echo [CHECK OK] Starting PRO loop...
echo Ctrl+C to stop.
echo.

python -m mt5_bot trade ^
    --config config/pro.yaml ^
    --db data/pro.sqlite ^
    --trade-enabled

echo.
echo ============================================================
echo   PRO LOOP ENDED — generating report
echo ============================================================
echo.

python -m mt5_bot report --db data/pro.sqlite

echo.
pause
