# Laptop Handoff - MT5 Trading Bot Suite

Fecha: 2026-05-19
Rama de trabajo: claude/work
Repo remoto: https://github.com/JeanFSC/bot.git

Este documento es para abrir el proyecto en otra laptop con Codex/IDE y continuar desde cero sin perder el contexto actual.

## 1. Estado Actual Del Proyecto

La suite completa de 12 bots NO debe ejecutarse como antes.

Estado operativo actual:

- LIVE: 3 bots ganadores.
- SANDBOX/DRY-RUN: 8 candidatos redisenados.
- Los sandbox no abren operaciones reales porque no usan --trade-enabled.
- El objetivo es validar candidatos con datos antes de pasarlos a live.

Live actual:

- XAUUSD main: config/pro_gold.yaml
- USDCHF: config/pro_usdchf.yaml
- GBPJPY: config/pro_gbpjpy.yaml

Sandbox actual:

- USDJPY London V2: config/research_usdjpy_london_v2.yaml
- EURUSD London V2: config/research_eurusd_london_v2.yaml
- GBPUSD London V2: config/research_gbpusd_london_v2.yaml
- NZDUSD London V2: config/research_nzdusd_london_v2.yaml
- USDCAD NY V2: config/research_usdcad_ny_v2.yaml
- AUDUSD Asia/London V2: config/research_audusd_asia_london_v2.yaml
- XAUUSD_M5 V2: config/research_xauusd_m5_v2.yaml
- XAGUSD V2: config/research_xagusd_v2.yaml

## 2. Archivos Que Debe Leer Codex Primero

En este orden:

1. LAPTOP_HANDOFF.md
2. CODEX_RUNBOOK.md
3. docs/GOAL_NEXT_STEPS_MASTER_CHECKLIST.md
4. docs/BOT_12_INDIVIDUAL_AUDIT.md
5. docs/BOT_METHODOLOGY_V2.md
6. docs/GOAL_TRADER_METHOD_RESEARCH.md
7. reports/SUITE_STATUS_REPORT.md
8. reports/SANDBOX_SIGNAL_REPORT.md
9. reports/RESEARCH_CANDIDATES_VALIDATION.md

## 3. Instalar En La Laptop

Requisitos:

- Windows.
- MetaTrader 5 instalado.
- Cuenta demo abierta en MT5.
- Algo Trading habilitado en MT5.
- Python 3.10 a 3.12 recomendado si MetaTrader5 falla con otra version.
- Git.

Clonar rama:

```powershell
git clone -b claude/work https://github.com/JeanFSC/bot.git
cd bot
```

Crear entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Crear .env:

```powershell
Copy-Item .env.example .env
notepad .env
```

Completar MT5_LOGIN, MT5_PASSWORD, MT5_SERVER y MT5_TERMINAL_PATH si hace falta. Nunca subir .env al repo.

## 4. Verificacion Inicial

Con MT5 abierto y logueado:

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
python -m mt5_bot check --config config/pro_gold.yaml
python -m mt5_bot check --config config/pro_usdchf.yaml
python -m mt5_bot check --config config/pro_gbpjpy.yaml
python scripts\validate_research_candidates.py
```

Resultado esperado: tests pasan, los 3 configs live conectan, y todos los research candidates dicen PASS con trade_enabled False.

## 5. Ejecutar Suite Live Reducida

Solo si Jean confirma que quiere operar demo:

```powershell
START_REDUCED_FORWARD_TEST.bat
```

Esto inicia solo USDCHF, XAUUSD main y GBPJPY. No iniciar _run_all_pro_autorestart.bat ni la suite completa de 12 bots.

## 6. Ejecutar Sandbox De Candidatos

Esto NO abre operaciones reales:

```powershell
START_RESEARCH_SANDBOX_ALL.bat
```

Debe levantar 8 dry-run loops.

## 7. Reportes

Estado suite:

```powershell
$env:PYTHONPATH='src'
python scripts\suite_status_report.py --since 2026-05-15 --write
```

Estado sandbox:

```powershell
python scripts\sandbox_signal_report.py --write
```

Validacion candidatos:

```powershell
$env:PYTHONPATH='src'
python scripts\validate_research_candidates.py
```

Backtest research:

```powershell
$env:PYTHONPATH='src'
python scripts\research_backtest.py --configs config\pro_jpy.yaml --from-date 2026-04-15 --to-date 2026-05-20 --session london --write
```

## 8. Reglas De Operacion

No pasar candidatos sandbox a live hasta cumplir PF mayor a 1.25, expectancy positiva, avg win/loss sano, sin crash loops, reporte no stale, DB propia, magic unico y 20 a 50 trades limpios de forward/sandbox.

Solo promover un bot nuevo a la vez.

## 9. Decision Actual Por Bot

Mantener live: XAUUSD main, USDCHF, GBPJPY como scout.

Sandbox: USDJPY London V2 y otros 7 research candidates.

Pausados como live: EURUSD, GBPUSD, NZDUSD, USDCAD, AUDUSD, XAUUSD_M5, XAGUSD, USDJPY Asia.

## 10. Si Codex Toma El Proyecto

Primero debe correr:

```powershell
git status --short
$env:PYTHONPATH='src'
python -m pytest -q
python scripts\suite_status_report.py --since 2026-05-15 --write
python scripts\sandbox_signal_report.py --write
python scripts\validate_research_candidates.py
```

Despues debe leer docs/GOAL_NEXT_STEPS_MASTER_CHECKLIST.md y seguir el estado PASS/WAITING/BLOCKED.

## 11. Pendientes Inmediatos

1. Observar sandbox durante sesiones validas.
2. Recalibrar scoring A/B de USDJPY London V2.
3. Crear reporte agregado para los 8 sandbox candidates, no solo USDJPY.
4. Decidir candidatos que sobreviven con evidencia.
5. Promover solo uno a live si pasa gates.

## 12. Seguridad

- No subir .env.
- No subir data/*.sqlite.
- No subir logs.
- No operar cuenta real.
- No ejecutar suite completa de 12 bots sin nuevo gate.
- No cerrar/modificar posiciones manualmente sin confirmacion explicita de Jean.
