# Gestión de Riesgo — La Base de Todo

## La regla que separa a los que sobreviven de los que no

**Nunca arriesgues más de lo que puedes perder en una sola operación sin afectar tu capital de forma permanente.**

El sistema usa `risk_pct` (porcentaje del equity por trade). Esto es correcto. Es el método profesional.

## Cómo se calcula el tamaño del lote

```
Lote = (Equity × Risk%) / (SL en pips × Valor pip por lote)
```

**Ejemplo con USDJPY (el trade ganador):**
- Equity: $100,000
- Risk: 1.2% → $1,200 a arriesgar
- SL: ~10 pips (ATR 6.7 × 1.5 = ~10 pips)
- Valor pip USDJPY: $6.36/pip por lote estándar (a 157.28)
- Lote = $1,200 / (10 × $6.36) = 18.87 lotes ≈ 18.65 lotes ✓

Así se calcularon los 18.65 lotes que generaron $3,160 en 45 minutos.

## Los niveles de riesgo actuales del sistema

| Bot       | Risk% | Máx pérdida por trade |
|-----------|-------|-----------------------|
| EURUSD    | 1.5%  | ~$1,530 con $102k equity |
| GBPUSD    | 1.2%  | ~$1,224 |
| USDJPY    | 1.2%  | ~$1,224 |
| XAUUSD    | 1.0%  | ~$1,020 |
| AUDUSD    | 1.2%  | ~$1,224 |
| **TOTAL MÁXIMO SIMULTÁNEO** | **6.1%** | **~$6,222** |

Si los 5 bots pierden al mismo tiempo (escenario extremo): -$6,222 en un ciclo. El equity curve filter y el max_daily_loss_pct: 5% frenan antes de llegar ahí.

## ADX Boost — El multiplicador inteligente

El sistema tiene un multiplicador automático cuando el ADX es alto. Con ADX > 40:
- EURUSD: risk sube a 1.88% (log del 06/05 confirmado)
- Gold: risk sube a 1.25%

**Esto es correcto en teoría.** En tendencias fuertes, el mercado está menos aleatorio y la probabilidad de que el trade funcione es mayor. Pero hay un límite: nunca deberías escalar por encima del 2% por trade en un sistema todavía en validación.

## Las 3 capas de protección contra pérdidas grandes

### Capa 1: SL por trade (primera línea)
- SL = 1.5x ATR dinámico
- Se mueve con la volatilidad del mercado
- Nunca está en un número fijo arbitrario

### Capa 2: Max Daily Loss 5%
- Si el portafolio pierde 5% en un día, todos los bots se detienen
- Con $102k equity: para a los -$5,100
- Protege contra días de noticias inesperadas o errores múltiples

### Capa 3: Equity Curve Filter
- Si hay 3 pérdidas consecutivas, el bot reduce el tamaño del lote al 50%
- Permite que el sistema "respire" y evita el tilt algorítmico
- Se reactiva cuando el equity recupera

### Capa 4: Trailing Stop (protege ganancias)
- Una vez que el trade está en 0.8x ATR de ganancia → SL se mueve a breakeven
- Desde breakeven, el SL sigue al precio a 1.5x ATR de distancia
- Resultado: el trade ganador NUNCA se convierte en perdedor una vez activado el trailing

## Partial Close — Asegurar la mitad

Con `partial_close_ratio: 0.5`, cuando el trade llega a breakeven:
- Se cierra el 50% de la posición → ganancia asegurada
- El 50% restante sigue corriendo con el trailing stop
- Efecto psicológico/matemático: menor drawdown, mayor consistencia

## Por qué el tamaño de cuenta importa exponencialmente

| Equity   | Risk 1.2% | Trade ganador típico (2R) |
|----------|-----------|--------------------------|
| $10,000  | $120      | +$240                    |
| $50,000  | $600      | +$1,200                  |
| $100,000 | $1,200    | +$2,400                  |
| $500,000 | $6,000    | +$12,000                 |

La estrategia no cambia. Solo el capital. Por eso escalar es la mejor palanca de ganancia.

## El número que más importa: Expectancy

```
Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
```

Con el sistema actual (estimado):
- Win Rate: ~45% (típico para EMA crossover trend-following)
- Avg Win con R:R 1:2 = 2R
- Avg Loss = 1R
- Expectancy = (0.45 × 2) - (0.55 × 1) = 0.90 - 0.55 = **+0.35R por trade**

Eso significa que por cada $1 arriesgado, el sistema genera $0.35 de ganancia esperada en promedio. Con 30 trades/mes y $1,200 de riesgo: **+$12,600/mes esperado con $100k de capital**.

Este número hay que validarlo con datos reales después de 50-100 trades en live.
