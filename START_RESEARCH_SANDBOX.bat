@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

echo ============================================================
echo  MT5 RESEARCH SANDBOX - NON-LIVE CANDIDATES
echo ============================================================
echo.
echo This launcher starts research candidates WITHOUT --trade-enabled.
echo It observes signals and writes telemetry, but must not open trades.
echo.

start "SANDBOX USDJPY LONDON V2" cmd /k "_sandbox_usdjpy_london_v2.bat"

echo.
echo Research sandbox launch requested.
echo Live reduced suite remains separate.
echo.
pause
