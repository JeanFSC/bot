@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1

echo.
echo ================================================================
echo   P^&L AISLADO POR BOT  —  Reporte en tiempo real via MT5
echo   Magic 260432: Scalper EURUSD M1
echo   Magic 260433: PRO EURUSD M15/H1
echo   Magic 260434: PRO GBPUSD M15/H1
echo ================================================================
echo.

REM ── Opciones de uso ───────────────────────────────────────────────
REM   Reporte de HOY (default):
REM     _run_pnl.bat
REM
REM   Últimos 7 días:
REM     python -m mt5_bot pnl --config config/pro.yaml --days 7
REM
REM   Sólo PRO EURUSD:
REM     python -m mt5_bot pnl --config config/pro.yaml --magic 260433
REM ──────────────────────────────────────────────────────────────────

python -m mt5_bot pnl --config config/pro.yaml --days 1

echo.
echo ================================================================
echo   Últimos 7 días:
echo ================================================================
python -m mt5_bot pnl --config config/pro.yaml --days 7

echo.
pause
