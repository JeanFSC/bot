@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTDIR=%~dp0

echo.
echo ================================================================
echo   MT5 PRO SUITE -- 12 BOTS (24h Coverage)
echo   ---- BOTS ORIGINALES ----
echo   EURUSD (260433)  GBPUSD (260434)
echo   USDJPY (260435)  XAUUSD (260436)  AUDUSD (260437)
echo   ---- BOTS NUEVOS ----
echo   XAUUSD M5 (260440)  USDCAD (260441)  NZDUSD (260442)
echo   GBPJPY (260443)     XAGUSD (260444)  USDJPY Asia (260445)
echo   USDCHF (260446)
echo   ---- FEATURES ----
echo   ADX tiered boost: ON  Compounding: ON  24h Coverage: ON
echo   News filter: ON  Equity curve: ON  Portfolio guard: ON
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

echo [%TIME%] Lanzando PRO XAUUSD (Gold M15)...
start "PRO GOLD" "%BOTDIR%_restart_gold.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO AUDUSD...
start "PRO AUDUSD" "%BOTDIR%_restart_aud.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO XAUUSD M5 (Gold 24h)...
start "PRO GOLD M5" "%BOTDIR%_restart_gold_m5.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO USDCAD...
start "PRO USDCAD" "%BOTDIR%_restart_usdcad.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO NZDUSD...
start "PRO NZDUSD" "%BOTDIR%_restart_nzdusd.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO GBPJPY...
start "PRO GBPJPY" "%BOTDIR%_restart_gbpjpy.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO XAGUSD (Silver 24h)...
start "PRO SILVER" "%BOTDIR%_restart_silver.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO USDJPY ASIA (nocturno)...
start "PRO JPY ASIA" "%BOTDIR%_restart_jpy_asia.bat"
timeout /t 3 /nobreak >nul

echo [%TIME%] Lanzando PRO USDCHF...
start "PRO USDCHF" "%BOTDIR%_restart_usdchf.bat"

echo.
echo ================================================================
echo   12 bots activos. Logs en: %BOTDIR%logs\
echo   Cobertura: 24 horas / 7 dias
echo ================================================================
echo.
pause
