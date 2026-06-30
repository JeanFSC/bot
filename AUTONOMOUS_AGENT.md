# Agente Autónomo Evolutivo MT5

Objetivo: operar primero en DEMO con aprendizaje persistente, sin romper los guardrails existentes del bot.

## Qué hace

- Usa el motor técnico existente del bot MT5.
- Añade memoria evolutiva SQLite por setup/símbolo.
- Aprende de deals cerrados importados desde las bases SQLite del bot.
- Bloquea setups con rachas de pérdidas.
- Reduce riesgo en setups con historial negativo.
- Ejecuta solo el set reducido: USDCHF, XAUUSD y GBPJPY.
- Corre una configuración a la vez en el MVP para controlar exposición.

## Archivos principales

- `src/mt5_bot/autonomous_agent.py`: memoria, clasificación de setup, decisión y ajuste de riesgo.
- `src/mt5_bot/agent_runner.py`: runner operativo `preflight`, `learn`, `run-once`.
- `config/autonomous_agent.yaml`: configuración del agente.
- `START_AUTONOMOUS_AGENT_PREFLIGHT.bat`: validación segura.
- `START_AUTONOMOUS_AGENT_PAPER.bat`: corrida dry-run/paper.
- `START_AUTONOMOUS_AGENT_DEMO_ONCE.bat`: corrida demo con pausa y flag explícito.
- `tests/test_autonomous_agent.py`
- `tests/test_agent_runner.py`

## Comandos

Desde `C:/Users/JEAN/Desktop/MT5/bot`:

```bash
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml learn
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml run-once --max-seconds 30
```

## Activar operaciones DEMO

1. Cambiar en `config/autonomous_agent.yaml`:

```yaml
mode: demo
```

2. Ejecutar con flag explícito:

```bash
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml run-once --allow-demo-orders
```

O usar:

```text
START_AUTONOMOUS_AGENT_DEMO_ONCE.bat
```

## Límites actuales

- `floor_equity: 2925.0` para cuenta demo de USD 3000.
- `target_equity: 3030.0` por corrida.
- `max_parallel_bots: 1`.
- `allow_demo_orders: false` por defecto.
- Los YAML de estrategia siguen con `execution.trade_enabled: false`; el runner habilita trading demo solo por flag.

## Verificación realizada

- `uv run pytest -q` → 57 passed.
- `uv run python -m compileall -q src tests` → OK.
- `git diff --check` → exit 0, solo warnings CRLF existentes.
- `preflight` del agente → `AGENT_PREFLIGHT_OK configs=3`.
- `learn` inicial → importó 12 deals cerrados a memoria.
- `run-once --max-seconds 30` en paper → ejecutó USDCHF, XAUUSD, GBPJPY sin enviar órdenes.

## Nota honesta

Esto no garantiza ganar dinero. El diseño busca sobrevivir, medir, aprender y reducir daño cuando se equivoca. La promoción a demo con órdenes debe hacerse con ventanas cortas y revisión del journal.
