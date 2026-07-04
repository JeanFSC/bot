# MT5 Demo Trading Bot

Bot Python para MetaTrader 5 en cuenta DEMO. Usa velas `M1` para detectar cruces EMA 9/21 y el tick actual para validar spread y construir ordenes. La ejecucion real esta apagada por defecto con `trade_enabled: false`.

No hay garantia de ganancias. Esta V1 prioriza seguridad, medicion y mejora progresiva con datos reales de demo.

## Requisitos

- Windows con MetaTrader 5 instalado.
- Cuenta DEMO abierta en MT5.
- Algo Trading habilitado en MT5.
- Python 3.10 o superior. Si `MetaTrader5` no instala en tu version actual, usa Python 3.11 o 3.12.

## Instalacion

Desde PowerShell:

```powershell
cd "C:\Users\jean_\Desktop\Pagina web\mt5_trading_bot"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Crear `.env` desde el ejemplo:

```powershell
Copy-Item .env.example .env
notepad .env
```

Edita `MT5_LOGIN`, `MT5_PASSWORD` y `MT5_SERVER`. No subas `.env` a ningun repositorio.

## Validar Conexion Sin Operar

Con MT5 abierto y conectado a la demo:

```powershell
python -m mt5_bot check --config config/demo.yaml
```

El comando valida login, cuenta demo, permisos de trading, simbolo `EURUSD`, bid/ask y spread.

## Ejecutar En Modo Seguro

Por defecto `config/demo.yaml` tiene:

```yaml
execution:
  trade_enabled: false
```

En este modo el bot calcula senales y hace `order_check()`, pero no envia operaciones reales a la demo:

```powershell
python -m mt5_bot trade --config config/demo.yaml
```

Para una prueba controlada que se detenga tras la primera senal procesada:

```powershell
python -m mt5_bot trade --config config/demo.yaml --stop-after-action --max-seconds 1200
```

## Activar Trading Demo

Solo despues de validar conexion y logs, cambia:

```yaml
execution:
  trade_enabled: true
```

Luego ejecuta:

```powershell
python -m mt5_bot trade --config config/demo.yaml
```

Tambien puedes hacer una prueba temporal sin editar el YAML:

```powershell
python -m mt5_bot trade --config config/demo.yaml --trade-enabled --stop-after-action --max-seconds 1200
```

Controles incluidos:

- Rechaza cuentas que no parezcan DEMO.
- Solo una posicion propia por `symbol + magic`.
- Cierra posicion contraria cuando aparece cruce opuesto.
- Bloquea entradas si el spread supera `max_spread_pips`.
- Bloquea entradas por perdida diaria maxima y maximo de trades diarios.
- Guarda senales, ordenes, checks, metricas de mercado y snapshots de cuenta en SQLite.
- Usa `filling_mode: AUTO` para probar `RETURN`, `IOC` y `FOK` cuando el broker rechaza un modo de llenado.

## Reporte

```powershell
python -m mt5_bot report --db data/trades.sqlite
```

## Backtest Basico

El backtest descarga historico desde MT5, asi que tambien requiere `.env` y MT5 disponible:

```powershell
python -m mt5_bot backtest --config config/demo.yaml --from 2026-04-01 --to 2026-04-30
```

## MCP MetaTrader5 Completo Para Hermes

Este repo incluye un servidor MCP local que expone la API publica completa de `MetaTrader5` mediante un dispatcher generico `mt5_call(name, args, kwargs)`, mas helpers para conexion, constantes y descubrimiento.

Por seguridad, el MCP bloquea por defecto llamadas de trading o estado como `order_send`, `login`, `shutdown` y `symbol_select`. Para habilitar acceso completo, arranca el servidor con `MT5_MCP_ENABLE_TRADING=1`; mantenlo en `0` para lectura/analisis.

Instala dependencias y registra el servidor en Hermes:

```bash
uv pip install -r requirements.txt
hermes mcp add mt5 \
  --command "C:/Users/JEAN/Desktop/MT5/bot/.venv/Scripts/python.exe" \
  --env PYTHONPATH=C:/Users/JEAN/Desktop/MT5/bot/src MT5_MCP_ENABLE_TRADING=0 \
  --args -m mt5_bot.mcp_server
```

Verifica y reinicia Hermes para que descubra herramientas `mcp_mt5_*`:

```bash
hermes mcp test mt5
```

Smoke test manual con MT5 abierto y `.env` configurado: llama `mt5_connect_from_env`, luego `mt5_call("account_info")` y `mt5_call("symbols_total")`. Antes de cualquier `order_send`, usa `order_check` y habilita `MT5_MCP_ENABLE_TRADING=1` solo si realmente quieres operar.

## Agente Autonomo Evolutivo DEMO

Este repo ahora incluye una capa autonoma sobre el bot MT5. No reemplaza los guardrails: los usa para operar en demo con riesgo bajo, memoria SQLite, post-mortems y watchdog.

Archivos principales:

- `config/autonomous_agent.yaml` — configura modo demo, simbolos, equity floor y rotacion.
- `src/mt5_bot/autonomous_agent.py` — memoria evolutiva por setup.
- `src/mt5_bot/agent_runner.py` — runner continuo `learn -> trade -> learn`.
- `src/mt5_bot/agent_watchdog.py` — supervisor que reinicia el agente si cae y escribe health JSONL.
- `src/mt5_bot/postmortem.py` — analiza perdidas cerradas y propone acciones correctivas.
- `src/mt5_bot/local_reports.py` — genera reportes locales Markdown/JSON.
- `src/mt5_bot/maintenance.py` — aprendizaje + postmortem + reporte + backup.

### Instalar en otra PC Windows

1. Instala MetaTrader 5 y entra a la cuenta demo.
2. Activa `Algo Trading` en MT5.
3. Clona el repo:

```bash
git clone https://github.com/JeanFSC/bot.git
cd bot
```

4. Instala dependencias:

```bash
uv sync
```

Si no usas `uv`:

```bash
python -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
```

5. Crea `.env` desde `.env.example` y completa credenciales MT5:

```bat
copy .env.example .env
notepad .env
```

No subas `.env` al repo.

6. Valida antes de operar:

```bash
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight
uv run pytest -q
```

7. Inicia watchdog + agente continuo:

```bat
START_AGENT_WATCHDOG_24_7.bat
```

O manual:

```bash
uv run python -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 3600 --report-path data/watchdog_health.jsonl
```

### Mantenimiento local

Ejecuta manualmente:

```bat
RUN_AGENT_MAINTENANCE.bat
```

O:

```bash
uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48
```

Genera:

- `reports/maintenance_latest.md`
- `reports/maintenance_latest.json`
- `reports/experiments.md`
- `backups/mt5_agent_*.zip`

Estos archivos son locales y estan ignorados por Git.

### VPS 24/7

Para correr aunque apagues tu PC, usa Windows VPS + MT5 + watchdog como servicio.

Documentacion:

```text
OPERACION_24_7.md
```

Scripts:

```text
INSTALL_VPS_NSSM_SERVICE.bat
INSTALL_HOURLY_MAINTENANCE_TASK.bat
```

### Seguridad demo

- Mantener `demo_only: true`.
- Mantener `.env` fuera de Git.
- Mantener `floor_equity` activo.
- No subir riesgo sin registrar experimento.
- Si MT5 muestra `AutoTrading disabled by client`, activa Algo Trading y verifica `terminal_trade_allowed: true`.

## Mejora Progresiva

Primero recopila datos demo. Luego revisa reportes semanales y ajusta parametros solo si mejoran metricas fuera de muestra. La futura capa ML debe funcionar como filtro de senales, no como trader autonomo.
