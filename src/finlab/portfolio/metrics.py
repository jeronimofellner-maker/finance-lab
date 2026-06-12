"""Métricas de cartera: exposición por clase / moneda / sector y P&L."""
from __future__ import annotations

from collections import defaultdict

from finlab.portfolio.holdings import Position


def _weights(positions: list[Position], key) -> dict[str, float]:
    total = sum(p.value_usd for p in positions if p.value_usd) or 1.0
    agg = defaultdict(float)
    for p in positions:
        if p.value_usd:
            agg[key(p)] += p.value_usd
    return {k: round(v / total, 4) for k, v in sorted(agg.items(), key=lambda x: -x[1])}


def exposures(positions: list[Position]) -> dict:
    return {
        "by_asset_class": _weights(positions, lambda p: p.asset_class),
        "by_currency": _weights(positions, lambda p: p.moneda),
        "by_sector": _weights(positions, lambda p: p.sector),
    }


def concentration(positions: list[Position]) -> dict[str, float]:
    """Peso de cada posición individual (para chequear el límite de 15%)."""
    return _weights(positions, lambda p: p.ticker)


def total_pnl(positions: list[Position]) -> dict:
    """P&L agregado en USD. Usa cost_usd/value_usd ya calculados por posición."""
    invested = sum(p.cost_usd for p in positions if p.cost_usd)
    current = sum(p.value_usd for p in positions
                  if p.value_usd and p.cost_usd)  # solo las que tienen costo
    pnl = current - invested
    return {
        "invested_usd": round(invested, 2),
        "current_usd": round(current, 2),
        "pnl_usd": round(pnl, 2),
        "pnl_pct": round((pnl / invested * 100), 2) if invested else None,
    }
