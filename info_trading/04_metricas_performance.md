# Métricas de Performance — Cómo Saber si el Bot Está Funcionando

## Las métricas que importan (en orden)

### 1. Expectancy (Expectativa) — LA más importante
```
Expectancy = (Win% × Avg_Win_R) - (Loss% × Avg_Loss_R)
```
- **Target:** > +0.3R por trade
- Si es negativa, el sistema pierde dinero a largo plazo sin importar nada más
- Calcular después de mínimo 50 trades

### 2. Profit Factor
```
Profit Factor = Suma de ganancias brutas / Suma de pérdidas brutas
```
- **< 1.0:** Sistema perdedor
- **1.0 - 1.5:** Marginal
- **1.5 - 2.0:** Bueno ✓ (target del sistema actual)
- **> 2.0:** Excelente (posiblemente over-optimizado)
- **Target real:** 1.5 - 1.8

### 3. Max Drawdown
```
Max DD = Caída máxima desde un pico de equity hasta el valle siguiente
```
- **< 10%:** Sistema muy controlado ✓
- **10-20%:** Aceptable para trend-following
- **> 20%:** Demasiado agresivo o mal diseñado
- El sistema actual con max_daily_loss 5% y equity curve filter debería mantenerse < 15%

### 4. Win Rate
```
Win Rate = Trades ganadores / Total trades
```
- Para estrategias trend-following con R:R 1:2: **35-50% es normal y rentable**
- No buscar win rates altos sacrificando R:R — es el error más común
- Un sistema con 60% win rate y R:R 1:1 es PEOR que uno con 40% y R:R 1:2

### 5. Sharpe Ratio
```
Sharpe = (Retorno promedio - Tasa libre de riesgo) / Desviación estándar de retornos
```
- **> 1:** Aceptable
- **> 2:** Muy bueno
- Mide retorno ajustado por riesgo
- No es fácil de calcular manualmente — los brokers lo muestran en reportes

### 6. Average R (R múltiple promedio)
```
Avg R = Promedio de (Ganancia o Pérdida / Riesgo inicial del trade)
```
- Un trade que gana 2× el riesgo = +2R
- Un trade que pierde = -1R
- **Target:** Avg R > 0.3 después de 50 trades

---

## Dashboard mínimo que deberías tener

Después de cada semana de trading, calcular:

| Métrica           | Esta semana | Acumulado | Target    |
|-------------------|-------------|-----------|-----------|
| Total trades      |             |           | 20-30/sem |
| Win Rate          |             |           | 35-50%    |
| Profit Factor     |             |           | > 1.5     |
| Max DD semana     |             |           | < 5%      |
| Ganancia neta ($) |             |           | +2% equity|
| Expectancy (R)    |             |           | > 0.3R    |

---

## Señales de que algo está mal

**Actuar inmediatamente si:**
- 5 pérdidas consecutivas sin ninguna ganancia
- Drawdown > 10% en una semana
- Win rate < 25% en 30 trades
- El bot entra y sale en segundos repetidamente (problema técnico)
- Profit factor < 0.8 después de 50 trades

**Revisar y ajustar si:**
- Win rate consistentemente > 60% (TP demasiado cercano — subir)
- Win rate consistentemente < 30% con R:R 1:2 (señales de mala calidad — subir ADX)
- Todos los trades se abren en la misma hora (posible bug de sesión)

---

## Cómo leer las métricas de la base de datos SQLite

Las DBs están en `data/pro_jpy.sqlite`, `data/pro.sqlite`, etc.

Consulta básica para extraer performance:
```sql
SELECT 
  COUNT(*) as total_trades,
  SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
  ROUND(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate,
  ROUND(SUM(profit), 2) as total_profit,
  ROUND(SUM(CASE WHEN profit > 0 THEN profit ELSE 0 END), 2) as gross_win,
  ROUND(ABS(SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END)), 2) as gross_loss
FROM trades
WHERE status = 'closed';
```

---

## Benchmark de referencia

Para poner en perspectiva lo que estamos construyendo:

| Tipo de sistema        | Profit Factor | Win Rate | Avg DD  | Retorno anual |
|------------------------|---------------|----------|---------|---------------|
| Retail manual promedio | 0.7-0.9       | 40-50%   | 30-50%  | Pierde        |
| Bot básico sin filtros | 1.0-1.2       | 45-55%   | 20-30%  | 5-15%         |
| **Sistema actual (objetivo)** | **1.5-1.8** | **38-48%** | **8-15%** | **25-40%** |
| Hedge fund top tier    | 1.8-2.5       | 45-60%   | 5-12%   | 20-35%        |

El sistema actual está diseñado para estar en la categoría "objetivo". Con el capital escalado, los retornos absolutos crecen linealmente.
