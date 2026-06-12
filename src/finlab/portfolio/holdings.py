"""Valuación mark-to-market de la cartera, todo en USD-MEP (y equivalente ARS)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from finlab import config
from finlab.data import prices

log = logging.getLogger(__name__)


# Moneda en la que data912 / yfinance devuelven el PRECIO de mercado por clase.
# (Ojo: distinta de `moneda` del PPC, que es la que cargó el usuario.)
PRICE_CCY = {
    "cedear": "ARS", "accion_ar": "ARS", "bono_ar": "ARS", "ons": "ARS",
    "us_equity": "USD",
}


@dataclass
class Position:
    ticker: str
    asset_class: str
    qty: float
    ppc: float | None
    moneda: str                          # moneda del PPC
    sector: str
    tesis: str
    last_price: float | None = None      # en PRICE_CCY[asset_class]
    value_usd: float | None = None
    value_ars: float | None = None
    cost_usd: float | None = None        # costo en USD (aprox. con MEP actual si PPC en ARS)
    pnl_pct: float | None = None         # USD si PPC en USD; retorno ARS si PPC en ARS
    pnl_in_ars: bool = False             # True => el P&L es retorno en pesos, no USD
    pct_change: float | None = None      # intradiario

    @property
    def has_price(self) -> bool:
        return self.last_price is not None


def _to_usd(amount: float | None, ccy: str, mep: float | None) -> float | None:
    if amount is None:
        return None
    if ccy == "USD":
        return amount
    return amount / mep if mep else None


def _value_in_usd_ars(pos: Position, mep: float | None) -> tuple[float | None, float | None]:
    """Convierte el valor de mercado de la posición a (USD, ARS)."""
    if pos.asset_class in ("cash", "plazo_fijo"):
        # qty ya es el monto, en `moneda`.
        usd = _to_usd(pos.qty, pos.moneda, mep)
        ars = pos.qty if pos.moneda == "ARS" else (pos.qty * mep if mep else None)
        return usd, ars
    if pos.last_price is None:
        return None, None
    price_ccy = PRICE_CCY.get(pos.asset_class, "ARS")
    notional = pos.qty * pos.last_price          # en price_ccy
    usd = _to_usd(notional, price_ccy, mep)
    ars = notional if price_ccy == "ARS" else (notional * mep if mep else None)
    return usd, ars


def load() -> tuple[list[Position], dict]:
    """Carga portfolio.yaml, valúa cada posición. Devuelve (posiciones, meta)."""
    raw = config.portfolio()
    mep = prices.get_mep()
    positions: list[Position] = []

    for p in raw.get("positions", []):
        pos = Position(
            ticker=p["ticker"],
            asset_class=p["asset_class"],
            qty=float(p["qty"]),
            ppc=float(p["ppc"]) if p.get("ppc") is not None else None,
            moneda=p.get("moneda", "ARS"),
            sector=p.get("sector", "—"),
            tesis=p.get("tesis", ""),
        )
        quote = prices.price_lookup(pos.ticker, pos.asset_class)
        if quote:
            pos.last_price = quote.get("last")
            pos.pct_change = quote.get("pct_change")
        pos.value_usd, pos.value_ars = _value_in_usd_ars(pos, mep)

        # Costo y P&L en USD. Si el PPC está en ARS, lo paso a USD con el MEP
        # actual: el efecto FX se cancela y el P&L queda como retorno en pesos.
        if pos.ppc and pos.asset_class not in ("cash", "plazo_fijo"):
            pos.cost_usd = _to_usd(pos.qty * pos.ppc, pos.moneda, mep)
            if pos.cost_usd and pos.value_usd:
                pos.pnl_pct = round((pos.value_usd / pos.cost_usd - 1) * 100, 2)
                pos.pnl_in_ars = pos.moneda == "ARS"
        positions.append(pos)

    meta = {
        "mep": mep,
        "total_usd": sum(p.value_usd for p in positions if p.value_usd),
        "total_ars": sum(p.value_ars for p in positions if p.value_ars),
        "missing_prices": [p.ticker for p in positions if not p.has_price
                           and p.asset_class not in ("cash", "plazo_fijo")],
    }
    return positions, meta
