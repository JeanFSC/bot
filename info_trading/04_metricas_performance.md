# Métricas Performance

Validar por bot y portfolio:

- Profit Factor
- Win rate
- Expectancy por trade
- Max drawdown diario/semanal
- Trades por sesión
- Slippage y spread promedio
- Motivos de skip (`no_closed_bar_crossover`, `retest_pending`, `candle_no_*`)
- Distribución por ADX bucket: 18-30, 30-40, 40-50, >50

## SQL útil
```sql
select symbol, count(*) trades, sum(profit) pnl
from trades
group by symbol
order by pnl desc;
```

```sql
select reason, count(*)
from signals
group by reason
order by count(*) desc;
```

La meta no es más trades; es más trades con edge medible.
