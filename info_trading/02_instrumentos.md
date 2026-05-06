# Características de los 5 Instrumentos

## EURUSD — El más predecible

**Personalidad:** Tendencias largas y limpias. Respeta el análisis técnico mejor que cualquier otro par.
**Sesión óptima:** London (07:00-12:00 UTC) y overlap London/NY (12:00-17:00 UTC)
**ATR M15 típico:** 5-12 pips
**Spread demo:** 0.2 pips | Real: 0.6-1.2 pips
**Riesgo config actual:** 1.5%

**Lo que hay que saber:**
- Es el par más líquido del mundo (30% del volumen FX global)
- Reacciona fuerte a: NFP, CPI USA, decisiones BCE/Fed
- En Asia generalmente está muerto (rango de 10-20 pips en toda la sesión)
- El filtro de sesión 07:00-20:00 UTC es correcto para este par

**Correlaciones:**
- GBPUSD: +0.85 (muy alta) → si EURUSD está en BUY, GBPUSD probablemente también
- USDJPY: -0.60 (inversa moderada)
- XAUUSD: +0.30 (baja, buena diversificación)

---

## GBPUSD — El más volátil del grupo

**Personalidad:** Movimientos más amplios que EUR, más falsos breakouts, spreads más altos.
**Sesión óptima:** London (07:00-12:00 UTC). Evitar primeros 30 min de NY si hay datos UK.
**ATR M15 típico:** 8-18 pips
**Spread demo:** 0.6 pips | Real: 1.0-2.5 pips
**Riesgo config actual:** 1.2% (correcto, más conservador por mayor volatilidad)

**Lo que hay que saber:**
- GBP reacciona violentamente a datos UK (CPI, employment, BoE)
- Los "cable spikes" (movimientos de 50+ pips en segundos) son reales en noticias
- El news filter es especialmente importante aquí
- Alta correlación con EURUSD → cuidado con tener ambos abiertos simultáneamente (portfolio guard)

**Riesgo específico:** Si hay un trade en EURUSD ya abierto y el bot GBP también quiere entrar en la misma dirección, es exposición doble al USD. El portfolio guard con `max_same_currency_positions: 2` lo controla.

---

## USDJPY — El más diferente

**Personalidad:** Tendencias largas pero reversiones abruptas por intervención del Banco de Japón.
**Sesión óptima:** Tokyo (00:00-04:00 UTC) + London (07:00-12:00 UTC)
**ATR M15 típico:** 8-25 pips (pip = 0.01)
**Spread demo:** 0.3 pips | Real: 0.5-1.5 pips
**Riesgo config actual:** 1.2%

**Lo que hay que saber:**
- JPY es moneda refugio → en crisis globales, JPY se aprecia rápido
- El Banco de Japón (BoJ) interviene activamente cuando el par sube demasiado
- A niveles de 155-160 hay riesgo de intervención (el trade ganador del 05/05 fue a 157 — zona caliente)
- La sesión Tokyo (00:00-04:00 UTC) está activada en el config → bien
- use_trend_filter: true es correcto (cambiado de false)

**Operación ganadora de referencia (05/05/2026):**
- Entrada BUY: 157.279 | Salida TP: 157.546
- Volumen: 18.65 lotes | Ganancia: $3,160
- Condición: cruce EMA fuerte con impulso post-noticias

---

## XAUUSD (Gold) — El más rentable por movimiento

**Personalidad:** Tendencias macro largas, movimientos intradía amplios, reacciona a geopolítica y USD.
**Sesión óptima:** London/NY overlap (12:00-17:00 UTC) — máximo volumen y movimiento
**ATR M15 típico:** $5-25 (500-2500 pips con pip=0.01)
**Spread demo:** 17-30 pips | Real: 20-50 pips
**Riesgo config actual:** 1.0% (correcto — más conservador)

**Lo que hay que saber:**
- Gold sube cuando: USD baja, inflación sube, hay miedo/crisis, Fed dovish
- Gold baja cuando: USD sube, tasas reales suben, risk-on en mercados
- El spread de 17-30 pips es el mayor costo de entrada del grupo → el ATR tiene que ser grande para justificar el trade
- Con precio actual ~$4,645, cada lote estándar = $100 por pip ($1 por pip con micro)
- RSI más permisivo (70/30 en vez de 65/35) es correcto → Gold puede correr overbought semanas

**Cálculo real de costo de entrada Gold:**
- Spread 20 pips × $0.01/pip por micro lot × 0.01 lotes = $0.002 (mínimo)
- Con 0.1 lotes y spread 20 pips = $0.20 de costo fijo de entrada
- El SL/TP ATR-dinámico compensa esto correctamente

---

## AUDUSD — El más silencioso (pero consistente)

**Personalidad:** Tendencias suaves, correlacionado con commodities (hierro, carbón). Predecible.
**Sesión óptima:** Asia (00:00-06:00 UTC) y London (07:00-12:00 UTC)
**ATR M15 típico:** 4-10 pips
**Spread demo:** 0.4-0.8 pips | Real: 0.8-1.5 pips
**Riesgo config actual:** 1.2%

**Lo que hay que saber:**
- AUD sube cuando: China crece, commodities suben, risk-on global
- AUD baja cuando: China desacelera, RBA dovish, risk-off
- Menor volatilidad = menos trades pero más fiables
- La segunda fuente de diversificación real del portafolio (junto con Gold)
- Buena combinación con USDJPY que es la mayor fuente de movimiento

## Tabla Resumen de Correlaciones (aprox)

|           | EURUSD | GBPUSD | USDJPY | XAUUSD | AUDUSD |
|-----------|--------|--------|--------|--------|--------|
| EURUSD    | —      | +0.85  | -0.60  | +0.30  | +0.65  |
| GBPUSD    | +0.85  | —      | -0.55  | +0.25  | +0.60  |
| USDJPY    | -0.60  | -0.55  | —      | -0.40  | -0.50  |
| XAUUSD    | +0.30  | +0.25  | -0.40  | —      | +0.20  |
| AUDUSD    | +0.65  | +0.60  | -0.50  | +0.20  | —      |

**Implicación práctica:** El portfolio guard que limita `max_same_currency_positions: 2` es correcto pero no suficiente. Si EURUSD y GBPUSD están ambos en BUY, el sistema tiene exposición doble al USD bajista aunque sean "pares distintos".
