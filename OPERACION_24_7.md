# Operación 24/7 sin Telegram ni Dashboard

Estado objetivo: el agente corre en demo real, supervisado por watchdog, con reportes locales, backups rotativos y post-mortems automáticos.

## Componentes

- `src/mt5_bot/agent_watchdog.py`: supervisa MT5 y reinicia el agente si cae.
- `src/mt5_bot/postmortem.py`: analiza operaciones cerradas en pérdida y registra causas/acciones.
- `src/mt5_bot/local_reports.py`: genera reportes Markdown/JSON.
- `src/mt5_bot/experiments.py`: bitácora de experimentos y cambios de parámetros.
- `src/mt5_bot/backup.py`: backup ZIP rotativo de memoria/configs/logs.
- `src/mt5_bot/maintenance.py`: ejecuta aprendizaje + postmortem + reporte + backup.

## Comandos locales

### Watchdog 24/7

```bat
START_AGENT_WATCHDOG_24_7.bat
```

O manual:

```bash
uv run python -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 3600 --report-path data/watchdog_health.jsonl
```

### Mantenimiento manual

```bat
RUN_AGENT_MAINTENANCE.bat
```

O manual:

```bash
uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48
```

Genera:

- `reports/maintenance_latest.md`
- `reports/maintenance_latest.json`
- `reports/experiments.md`
- `backups/mt5_agent_*.zip`

## VPS Windows recomendado

Requisitos mínimos:

- Windows Server
- 2 vCPU
- 4 GB RAM
- 40 GB disco
- RDP activo
- MT5 instalado en ruta estable
- Python/uv instalado
- Repo en carpeta estable, por ejemplo `C:\MT5\bot`

## Instalación en VPS

1. Copiar repo al VPS.
2. Crear `.env` con credenciales MT5.
3. Instalar dependencias:

```bash
uv sync
```

4. Abrir MT5, loguear demo, activar Algo Trading.
5. Verificar:

```bash
uv run pytest -q
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight
```

6. Probar mantenimiento:

```bash
uv run python -m mt5_bot.maintenance
```

7. Instalar servicio con NSSM:

```bat
INSTALL_VPS_NSSM_SERVICE.bat
```

8. Instalar mantenimiento horario:

```bat
INSTALL_HOURLY_MAINTENANCE_TASK.bat
```

## Reglas importantes

- No cambiar `execution.trade_enabled` en YAML; el runner lo activa solo en modo demo.
- Mantener `demo_only: true`.
- Mantener `floor_equity` activo.
- No borrar `data/autonomous_agent_memory.sqlite`; ahí vive el aprendizaje.
- Antes de subir riesgo, crear experimento en `data/experiments.jsonl`.

## Flujo de aprendizaje

Cada ciclo:

1. Runner sincroniza deals cerrados.
2. Postmortem analiza pérdidas.
3. EvolutionMemory actualiza setup stats.
4. Mantenimiento genera reporte y backup.
5. Watchdog verifica salud y reinicia si cae.

## Sin Telegram / sin panel

Este setup no depende de Telegram ni dashboard. Todo queda en archivos locales:

- health: `data/watchdog_health.jsonl`
- reportes: `reports/`
- backups: `backups/`
- experimentos: `data/experiments.jsonl`
