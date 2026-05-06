# Escalado y Crecimiento — Cómo Maximizar Ganancias Reales

## La palanca más poderosa: el capital

La estrategia actual funciona igual con $10k que con $1M. Lo único que cambia es el tamaño de lote y las ganancias absolutas. Esta es la ventaja clave de un sistema algorítmico sobre el trading manual.

## Proyección con compounding (reinversión de ganancias)

Asumiendo rendimiento mensual conservador del 3% (sin compounding):

| Mes | Capital ($102k base) | Ganancia mensual | Acumulado |
|-----|---------------------|------------------|-----------|
| 1   | $102,000            | $3,060           | $105,060  |
| 3   | $108,243            | $3,247           | $111,490  |
| 6   | $118,405            | $3,552           | $121,957  |
| 12  | $137,206            | $4,116           | $141,322  |

Con compounding (reinvirtiendo ganancias):

| Mes | Capital     | Ganancia (3%) | Total     |
|-----|-------------|---------------|-----------|
| 1   | $102,000    | $3,060        | $105,060  |
| 6   | $121,957    | $3,659        | $125,616  |
| 12  | $145,228    | $4,357        | $149,585  |
| 24  | $206,803    | $6,204        | $213,007  |

**A 2 años con 3% mensual: el capital casi se duplica.**

El 3% mensual es conservador. La operación del 05/05 sola fue +$3,160 en 45 minutos = 3.1% en un trade.

## Cómo escalar sin cambiar el sistema

### Fase 1: Validación (ahora — primeros 3 meses en live)
- Capital: $100k demo
- Objetivo: 50+ trades, calcular métricas reales
- No tocar los parámetros durante esta fase

### Fase 2: Capital real pequeño
- Abrir cuenta real con $1,000-$5,000
- Mismo sistema, mismos parámetros
- Validar que las ejecuciones reales (spread, slippage) coincidan con demo
- Diferencia esperada demo vs real: -10 a -20% en ganancia por costos reales

### Fase 3: Escalado a prop firm
Con un sistema con Profit Factor > 1.5 probado en real, las opciones son:

**FTMO:**
- Challenge: $100k virtual con reglas estrictas (max DD 10%)
- Si pasas: te dan $100k real, te quedas el 80-90% de las ganancias
- Costo del challenge: $540
- Con tu sistema: muy viable si el max DD se mantiene < 8%

**MyFundedFX / The Funded Trader / E8 Funding:**
- Similar a FTMO, algunas con menos restricciones
- Algunas permiten trading algorítmico explícitamente

**ROI real con prop firm:**
- Capital de $100k prop + $100k propio = $200k operando
- Con 3% mensual: $6,000/mes
- Costo real: solo el challenge ($540 una vez)

### Fase 4: Múltiples cuentas / instancias
El sistema ya está diseñado para correr en paralelo. Con 3 cuentas de $100k cada una:
- $300k operando
- 3% mensual = $9,000/mes
- 15 instancias de bots (3 cuentas × 5 pares)

## Por qué NO escalar antes de validar

El error más común en trading algorítmico: escalar con capital real antes de tener estadísticas reales.

La cuenta demo muestra resultados con:
- Sin slippage real
- Sin requotes
- Sin problemas de conexión
- Sin ejecución en mercados con gap

La cuenta real puede ser 15-25% peor en condiciones normales y 50%+ peor en días de alta volatilidad (NFP, FOMC).

**Regla:** No escalar hasta tener 50 trades reales con Profit Factor > 1.3.

## Fuentes de ingreso adicionales con el mismo sistema

### 1. Signal selling (venta de señales)
Una vez que el sistema tiene historial probado, se pueden vender las señales en MQL5 Market o Telegram. Precio típico: $30-100/mes por suscriptor.

### 2. Copy trading
MetaTrader permite que otros copien tus trades automáticamente. El proveedor cobra una comisión. Con 10 copiadores × $50/mes = $500/mes extra sin trabajo adicional.

### 3. Optimización continua
Cada trimestre: revisar parámetros con los datos reales acumulados. Pequeñas mejoras en ADX, TP o filtros pueden aumentar el Profit Factor de 1.5 a 1.8 — eso es +20% en ganancias sin cambiar el capital.

## El número clave para tomar decisiones

**Expectancy × Frecuencia de trades × Capital = Ingreso esperado**

Con el sistema actual:
- Expectancy estimada: 0.35R
- Frecuencia: ~25 trades/mes (todos los pares)
- Capital por riesgo (1.2% de $102k): $1,224
- Ingreso esperado: 0.35 × 25 × $1,224 = **$10,710/mes**

Este es el número objetivo. Si los datos reales se acercan a esto en los primeros 3 meses, el sistema está funcionando correctamente y es momento de escalar.
