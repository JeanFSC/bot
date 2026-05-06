@echo off
cd /d "%~dp0"

echo.
echo ================================================================
echo   CONFIGURACION DE TELEGRAM PARA ALERTAS
echo ================================================================
echo.
echo Para recibir alertas en Telegram necesitas:
echo.
echo   1. Crear un bot en Telegram:
echo      - Abre Telegram y busca @BotFather
echo      - Escribe /newbot y sigue las instrucciones
echo      - Copia el TOKEN que te da (formato: 123456789:AABBccdd...)
echo.
echo   2. Obtener tu Chat ID:
echo      - Busca @userinfobot en Telegram
echo      - Escribe /start para obtener tu chat ID
echo      - O usa un canal/grupo (el ID empieza con -100...)
echo.
echo   3. Agregar las variables al archivo .env:
echo      Edita el archivo .env en esta carpeta y agrega:
echo.
echo      MT5_TELEGRAM_TOKEN=TU_TOKEN_AQUI
echo      MT5_TELEGRAM_CHAT_ID=TU_CHAT_ID_AQUI
echo.
echo ================================================================
echo.

REM Abrir el archivo .env para edicion
if exist ".env" (
    echo Abriendo .env existente...
    notepad .env
) else (
    echo Creando .env nuevo...
    echo # MT5 Bot Configuration > .env
    echo. >> .env
    echo # Telegram Alerts (opcional pero recomendado) >> .env
    echo MT5_TELEGRAM_TOKEN= >> .env
    echo MT5_TELEGRAM_CHAT_ID= >> .env
    echo. >> .env
    echo # MT5 Account (requerido) >> .env
    echo # MT5_LOGIN=TU_LOGIN >> .env
    echo # MT5_PASSWORD=TU_PASSWORD >> .env
    echo # MT5_SERVER=MetaQuotes-Demo >> .env
    notepad .env
)

echo.
echo Una vez configurado, cierra el Bloc de notas y reinicia los bots.
echo.
pause
