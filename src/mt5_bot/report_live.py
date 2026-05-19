"""
report_live.py
──────────────
P&L aislado por magic number, consultando MT5 en tiempo real.

Cada bot tiene un magic único:
    260432 → Scalper  (EURUSD M1)
    260433 → PRO EURUSD (M15/H1)
    260434 → PRO GBPUSD (M15/H1)

Al filtrar history_deals_get por magic obtenemos el P&L exacto de cada bot
sin contaminación cruzada, aunque todos corran en la misma cuenta demo.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

# ── Mapa magic → etiqueta legible ────────────────────────────────────────────
MAGIC_LABELS: dict[int, str] = {
    260432: "SCALPER   EURUSD M1",
    260433: "PRO EUR   EURUSD M5/H1",
    260434: "PRO GBP   GBPUSD M5/H1",
    260435: "PRO JPY   USDJPY M5/H1",
    260436: "PRO GOLD  XAUUSD M5/M15",
    260437: "PRO AUD   AUDUSD M5/H1",
    260440: "PRO GOLD5 XAUUSD M5",
    260441: "PRO CAD   USDCAD M5/H1",
    260442: "PRO NZD   NZDUSD M5/H1",
    260443: "PRO GJ    GBPJPY M5/H1",
    260444: "PRO SILV  XAGUSD M5/M15",
    260445: "PRO JPY-A USDJPY ASIA M5/H1",
    260446: "PRO CHF   USDCHF M5/H1",
}

# Constantes de MT5 (entry direction)
DEAL_ENTRY_OUT = 1   # posición cerrada → tiene P&L realizado


def get_live_pnl(
    gateway,
    days: int = 1,
    magic_filter: int | None = None,
) -> list[dict[str, Any]]:
    """
    Obtiene deals históricos de MT5 y calcula métricas por magic number.

    Args:
        gateway:      Instancia conectada de MT5Gateway.
        days:         Ventana temporal (hacia atrás desde ahora, UTC).
        magic_filter: Si se especifica, sólo reporta ese magic.

    Returns:
        Lista de dicts con métricas por bot, ordenada por magic.
    """
    now   = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    # Sin filtro de grupo → todos los símbolos de la cuenta
    all_deals = gateway.history_deals_get(start, now)

    # Agrupar por magic
    by_magic: dict[int, list[Any]] = {}
    for deal in all_deals:
        magic = int(getattr(deal, "magic", 0))
        if magic_filter is not None and magic != magic_filter:
            continue
        by_magic.setdefault(magic, []).append(deal)

    results: list[dict[str, Any]] = []

    for magic, magic_deals in sorted(by_magic.items()):
        # Sólo deals de cierre con P&L registrado
        closing = [
            d for d in magic_deals
            if getattr(d, "entry", -1) == DEAL_ENTRY_OUT
        ]
        profits = [float(getattr(d, "profit", 0.0)) for d in closing
                   if float(getattr(d, "profit", 0.0)) != 0.0]

        commission = sum(float(getattr(d, "commission", 0.0)) for d in magic_deals)
        swap       = sum(float(getattr(d, "swap", 0.0)) for d in magic_deals)

        wins   = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]

        gross_profit = sum(wins)
        gross_loss   = sum(losses)          # valor negativo
        net_pnl      = sum(profits) + commission + swap

        results.append({
            "magic":         magic,
            "label":         MAGIC_LABELS.get(magic, f"Bot magic={magic}"),
            "trades":        len(profits),
            "wins":          len(wins),
            "losses":        len(losses),
            "win_rate":      round(len(wins) / len(profits) * 100, 1) if profits else 0.0,
            "gross_profit":  round(gross_profit, 2),
            "gross_loss":    round(gross_loss, 2),
            "net_pnl":       round(net_pnl, 2),
            "profit_factor": round(gross_profit / abs(gross_loss), 2)
                             if losses and wins else None,
            "avg_win":       round(statistics.mean(wins), 2) if wins else 0.0,
            "avg_loss":      round(statistics.mean(losses), 2) if losses else 0.0,
            "commission":    round(commission, 2),
            "swap":          round(swap, 2),
            "total_deals":   len(magic_deals),
            "period_days":   days,
            "as_of":         now.strftime("%Y-%m-%d %H:%M UTC"),
        })

    return results


def format_pnl_report(results: list[dict[str, Any]], days: int) -> str:
    """Formatea los resultados como tabla de texto para consola."""
    sep = "=" * 64
    lines = [
        sep,
        f"  P&L AISLADO POR BOT - ultimos {days} dia(s)  [{_now_utc()}]",
        sep,
    ]

    if not results:
        lines += ["", "  Sin operaciones registradas en este período.", "", sep]
        return "\n".join(lines)

    total_net = 0.0

    for r in results:
        net    = r["net_pnl"]
        net_s  = f"+${net:.2f}" if net >= 0 else f"-${abs(net):.2f}"
        pf     = f"{r['profit_factor']:.2f}" if r["profit_factor"] is not None else "  n/a"
        wr     = f"{r['win_rate']:.1f}%"
        wl     = f"{r['wins']}W / {r['losses']}L"
        avg_w  = f"+${r['avg_win']:.2f}"
        avg_l  = f"-${abs(r['avg_loss']):.2f}"

        lines += [
            "",
            f"  > {r['label']}   (magic {r['magic']})",
            f"    Trades cerrados : {r['trades']:>3}   {wl}   Win rate: {wr}",
            f"    Net P&L         : {net_s}",
            f"      bruto {'+' if r['gross_profit']>=0 else ''}{r['gross_profit']:.2f}"
            f"  comision {r['commission']:.2f}  swap {r['swap']:.2f}",
            f"    Profit factor   : {pf}",
            f"    Avg win / loss  : {avg_w} / {avg_l}",
        ]
        total_net += net

    total_s = f"+${total_net:.2f}" if total_net >= 0 else f"-${abs(total_net):.2f}"
    lines += [
        "",
        sep,
        f"  TOTAL NETO CONSOLIDADO (todos los bots): {total_s}",
        sep,
        "",
    ]
    return "\n".join(lines)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
