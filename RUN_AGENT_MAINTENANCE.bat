@echo off
cls
echo ===============================================
echo  MT5 AGENT MAINTENANCE
echo  Aprende deals, genera reporte local y backup
echo ===============================================
cd /d "%~dp0"
call MT5_AGENT.bat maintenance
pause
