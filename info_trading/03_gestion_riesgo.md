# Gestión de Riesgo

## Capas
1. `max_daily_loss_pct: 5.0` corta nuevas entradas si el día se deteriora.
2. `max_portfolio_open_positions: 5` limita exposición agregada aunque corran 12 bots.
3. `max_same_currency_positions: 2` evita concentración por divisa.
4. Correlation guard reduce riesgo si EURUSD/GBPUSD/AUDUSD ya están alineados.
5. Equity curve filter reduce lotaje después de racha perdedora.
6. Compounding positivo aumenta riesgo solo con equity sobre baseline.

## Riesgo agresivo
Con `risk_pct` base hasta 2% y ADX extreme boost 2x, un trade puede llegar a 4% de equity antes de otros recortes. Esto es agresivo; solo tiene sentido con demo/prop challenge y monitoreo.

## Invalidación operacional
Si portfolio guard, daily loss o logging fallan, no escalar.
