@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTDIR=%~dp0

echo.
echo ================================================================
echo   MT5 PRO SUITE -- 5 BOTS
echo   EURUSD (magic 260433)  GBPUSD (magic 260434)
echo   USDJPY (magic 260435)  XAUUSD Gold (magic 260436)
echo   AUDUSD (magic 260437)
echo   News filter: ON  Equity curve filter: ON
echo   ADX dynamic risk: ON  Correlation guard: ON
echo   Weekend gap protection: ON  Trailing stop: ON
echo   Para detener un bot: cierra su ventana.
echo ================================================================
echo.

echo [%TIME%] Lanzando PRO EURUSD...
start "PRO EURUSD" "%BOTDIR%_restart_eurusd.bat"

timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO GBPUSD...
start "PRO GBPUSD" "%BOTDIR%_restart_gbpusd.bat"

timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO USDJPY...
start "PRO USDJPY" "%BOTDIR%_restart_jpy.bat"

timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO XAUUSD (Gold)...
start "PRO GOLD" "%BOTDIR%_restart_gold.bat"

timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO AUDUSD...
start "PRO AUDUSD" "%BOTDIR%_restart_aud.bat"

echo.
echo ================================================================
echo   5 bots activos.
echo   EURUSD / GBPUSD / USDJPY / XAUUSD / AUDUSD
echo   Logs en: %BOTDIR%logs\
echo ================================================================
echo.
pause
