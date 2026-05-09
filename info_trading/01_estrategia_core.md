# Estrategia Core - EMA Crossover Multi-Timeframe

Sistema Claude reconstruido: entrada por cruce EMA en timeframe de señal, filtrada por tendencia superior, volatilidad, fuerza ADX y calidad de retest.

## Pipeline
1. **Sesión UTC**: solo operar cuando el instrumento tiene liquidez.
2. **Spread**: no entrar si el costo supera el umbral por símbolo.
3. **EMA crossover cerrado**: usa vela cerrada `[-2]`, no vela viva.
4. **Trend filter**: precio del timeframe superior alineado con EMA 50.
5. **RSI guard**: evita comprar sobrecomprado o vender sobrevendido.
6. **ATR gate**: evita mercados muertos.
7. **ADX gate**: exige tendencia real.
8. **Retest filter**: espera pullback a slow EMA antes de entrar.
9. **Candle confirmation**: confirma rechazo/rebote con cierre sobre EMA, engulfing o wick pattern.
10. **Risk engine**: portfolio guard + daily loss + ADX boost + compounding.

## Filosofía
No perseguir señales. Esperar tendencia + pullback + confirmación. Agresivo solo cuando el contexto lo justifica.
