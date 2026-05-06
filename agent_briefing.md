# Resumen Ejecutivo del Bot de Trading MT5 - Briefing para Agentes

Este documento resume el estado actual, la lógica operativa y los resultados del bot de trading MT5 para facilitar la continuidad del desarrollo y supervisión por parte de otros agentes.

## 1. Visión General del Proyecto
El sistema es un bot de trading modular escrito en Python que utiliza la API de MetaTrader 5. Está diseñado para operar múltiples símbolos simultáneamente usando instancias configurables.

### Estrategia Core
- **Indicadores**: Cruce de Medias Móviles Exponenciales (EMA 9 y EMA 21).
- **Temporalidad de Señal**: M15 (15 minutos).
- **Filtro de Tendencia**: H1 (1 hora). La operación solo se permite si el cruce coincide con la tendencia de la temporalidad mayor.
- **Salida**: Basada en ATR (Average True Range). Multiplicadores típicos: 1.5x para SL y 4.0x para TP.

## 2. Resultados Confirmados (Mayo 2026)
Se ha verificado una ganancia neta de **$3,160.70 USD** en la cuenta demo, proveniente de la base de datos `data/pro_jpy.sqlite`.

### Análisis de la Operación Maestra
- **Símbolo**: USDJPY
- **Fecha**: 05 de Mayo de 2026
- **Entrada**: 157.279 (BUY) | **Salida**: 157.546 (TP)
- **Volumen**: 18.65 Lotes (Calculado para arriesgar 1% de $100k con SL de 10 pips).
- **Lógica de Éxito**: La operación aprovechó un fuerte impulso tras un cruce de EMA confirmado por la tendencia H1. El TP se alcanzó en solo 45 minutos.

## 3. Arquitectura del Sistema
- **`src/mt5_bot/`**: Carpeta principal del código.
    - `cli.py`: Punto de entrada principal (gestiona los bucles de trading).
    - `executor.py`: Lógica de ejecución de órdenes y gestión de posiciones (Trailing Stops, Cierres parciales).
    - `strategy.py`: Detección de señales y cálculo de indicadores.
    - `gateway.py`: Interfaz de bajo nivel con la API de MT5.
- **`data/`**: Almacenamiento en SQLite (`trades.sqlite`, `pro_jpy.sqlite`, etc.) y caché de noticias.
- **`config/`**: Archivos YAML de configuración para diferentes perfiles (Demo, Pro, Scalper).

## 4. Gestión de Riesgo Avanzada
El bot implementa varias capas de seguridad verificadas en los logs:
- **Filtro de Spread**: Bloquea entradas si el spread supera el límite definido (ej. 2.0 pips).
- **Filtro de Sesión**: Restringe el trading a horarios específicos.
- **Filtro de Noticias**: Evita operar durante eventos económicos de alto impacto.
- **Filtro de Curva de Equidad**: Reduce el tamaño del lote automáticamente tras pérdidas consecutivas.
- **Escalado ADX**: Aumenta el riesgo en tendencias fuertes (ADX > 30) y lo reduce en mercados laterales.

## 5. Estado de Configuración Actual
- **Archivo `.env`**: Configurado con credenciales de MT5 y notificaciones.
- **ID de Telegram**: Actualizado recientemente a `8610401926`.
- **Modo de Ejecución**: El bot debe ejecutarse siempre desde la raíz del proyecto para asegurar que las variables de entorno se carguen correctamente.

## 6. Problemas Identificados y Soluciones
1.  **Error `MT5_LOGIN`**: Se identificó que ocurre por ejecutar el script fuera de la carpeta raíz. **Solución**: Usar `python -m mt5_bot`.
2.  **Error Telegram 403**: El bot recibía "Forbidden" al intentar notificar. **Solución**: Se ha actualizado el Chat ID. Se debe verificar si el nuevo ID pertenece a un usuario (no al bot mismo).

---
**Nota para el Agente**: Los logs históricos de Mayo 2026 en `logs/bot_20260505.log.2026-05-05` contienen la traza completa de la operación ganadora de $3k.
