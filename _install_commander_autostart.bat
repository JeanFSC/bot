@echo off
cd /d "%~dp0"

echo Registrando Telegram Commander en Task Scheduler...

schtasks /delete /tn "MT5_TelegramCommander" /f >nul 2>&1

schtasks /create ^
  /tn "MT5_TelegramCommander" ^
  /tr "\"%~dp0_telegram_commander_autostart.bat\"" ^
  /sc ONLOGON ^
  /delay 0001:00 ^
  /rl HIGHEST ^
  /f

if %errorlevel%==0 (
    echo OK - El commander arrancara automaticamente al iniciar Windows.
    echo Iniciando ahora...
    start "" "%~dp0_telegram_commander_autostart.bat"
) else (
    echo ERROR al registrar. Intenta ejecutar como Administrador.
)

pause
