@echo off
cd /d "%~dp0"

echo.
echo ============================================================
echo   MT5 PRO SUITE — EURUSD + GBPUSD  [Dual Bot]
echo   Lanzando ambos bots en ventanas separadas...
echo ============================================================
echo.

echo [1/2] Verificando EURUSD...
start "PRO EURUSD" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0src && set PYTHONUNBUFFERED=1 && echo. && echo ============================================================ && echo   PRO BOT  EURUSD  H1 trend + M15 signal && echo   EMA(9/21) + RSI(14) + ATR SL/TP + Trailing stop && echo   Session: London+NY  Lot: 0.5  Magic: 260433 && echo ============================================================ && echo. && python -m mt5_bot check --config config/pro.yaml && python -m mt5_bot trade --config config/pro.yaml --db data/pro.sqlite --trade-enabled && python -m mt5_bot report --db data/pro.sqlite && pause"

timeout /t 3 /nobreak >nul

echo [2/2] Verificando GBPUSD...
start "PRO GBPUSD" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0src && set PYTHONUNBUFFERED=1 && echo. && echo ============================================================ && echo   PRO BOT  GBPUSD  H1 trend + M15 signal && echo   EMA(9/21) + RSI(14) + ATR SL/TP + Trailing stop && echo   Session: London+NY  Lot: 0.5  Magic: 260434 && echo ============================================================ && echo. && python -m mt5_bot check --config config/pro_gbp.yaml && python -m mt5_bot trade --config config/pro_gbp.yaml --db data/pro_gbp.sqlite --trade-enabled && python -m mt5_bot report --db data/pro_gbp.sqlite && pause"

echo.
echo ============================================================
echo   Ambos bots activos en ventanas separadas.
echo   Para detener: cerrar cada ventana o Ctrl+C en cada una.
echo   Reportes se generan automaticamente al cerrar.
echo ============================================================
echo.
pause
