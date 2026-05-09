@echo off
cd /d "%~dp0"
echo Installing MT5_TelegramCommander scheduled task...
schtasks /Create /TN "MT5_TelegramCommander" /SC ONLOGON /RL HIGHEST /F /TR "wscript.exe \"%CD%\_telegram_commander_autostart.vbs\""
if errorlevel 1 (
  echo Failed to install scheduled task.
  pause
  exit /b 1
)
echo OK. Telegram Commander will start at Windows login.
pause
