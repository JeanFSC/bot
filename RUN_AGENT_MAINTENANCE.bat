@echo off
cls
echo ===============================================
echo  MT5 AGENT MAINTENANCE
echo  Aprende deals, genera reporte local y backup
echo ===============================================
cd /d "%~dp0"
uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48 --notify
pause
