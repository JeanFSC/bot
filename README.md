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

## Mejora Progresiva

Primero recopila datos demo. Luego revisa reportes semanales y ajusta parametros solo si mejoran metricas fuera de muestra. La futura capa ML debe funcionar como filtro de senales, no como trader autonomo.
