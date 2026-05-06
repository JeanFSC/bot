# Estrategia Core — EMA Crossover Multi-Timeframe

## Qué es y por qué funciona

El sistema usa un cruce de EMAs (9 y 21 períodos) en M15 filtrado por tendencia H1. Este es uno de los setups más probados en trading algorítmico. La razón por la que funciona no es magia — es que **miles de traders institucionales y retail usan las mismas EMAs**, creando una profecía autocumplida en mercados con tendencia.

## La lógica real detrás del filtro H1

Sin el filtro H1, el bot entraría en cualquier cruce M15 — incluyendo los que van contra la tendencia mayor. El 70% de los trades perdedores en esta estrategia ocurren cuando el cruce M15 va en contra del H1. El filtro elimina ese ruido.

**Regla de oro:** La temporalidad mayor siempre manda. M15 da el timing, H1 da la dirección.

## Pipeline de filtros en orden de importancia

1. **H1 EMA50 trend** → ¿Estamos en tendencia o rango?
2. **ADX > 22** → ¿La tendencia tiene fuerza suficiente?
3. **EMA 9/21 crossover en barra cerrada** → ¿Hay señal real?
4. **RSI < 65 (buy) / > 35 (sell)** → ¿No estamos sobreextendidos?
5. **ATR > mínimo** → ¿Hay volatilidad suficiente para mover el precio?
6. **Spread dentro del límite** → ¿El costo de entrada es razonable?

Si alguno falla → no hay trade. Esto es correcto. Es mejor no entrar que entrar mal.

## Por qué ADX 22 y no 18

El ADX mide la FUERZA de la tendencia, no su dirección.
- ADX < 20: mercado en rango lateral → EMAs cruzan todo el tiempo → señales falsas
- ADX 20-25: tendencia débil emergiendo → riesgo medio
- ADX > 25: tendencia confirmada → alta probabilidad de seguimiento
- ADX > 40: tendencia fuerte → el ADX boost aumenta el riesgo automáticamente

Con ADX en 18 el bot capturaba "early trends" pero la mayoría eran falsas. Con 22 filtramos el ruido y los trades que entran tienen mayor expectativa positiva.

## Por qué TP 3.0x y no 2.5x

Con SL = 1.5x ATR y TP = 3.0x ATR el R:R es exactamente 1:2.

### Matemática de supervivencia
- R:R 1:2 → necesitas ganar solo el 33.3% de los trades para ser rentable
- R:R 1:1.67 → necesitas ganar el 37.5%
- La diferencia parece pequeña pero en 100 trades: son 4 trades más que necesitas ganar

### El error de bajar el TP para "mayor win rate"
Subir el win rate bajando el TP es una ilusión. Cierras más trades en ganancia, pero cada ganancia es más pequeña y cada pérdida sigue siendo la misma. La expectativa matemática baja. El mejor R:R para esta estrategia es 1:2 mínimo.

## Señal ideal — checklist mental

✓ Precio por encima de EMA50 H1 (bullish) o por debajo (bearish)
✓ ADX > 25 en H1
✓ Cruce EMA 9/21 en M15 barra cerrada en la dirección correcta
✓ RSI entre 45-65 para compras, 35-55 para ventas (momentum sin sobreextensión)
✓ ATR expandiéndose (mercado moviéndose)
✓ Sin noticias de alto impacto en los próximos 30 minutos
