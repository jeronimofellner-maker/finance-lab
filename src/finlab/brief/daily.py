"""Arma el contenido del brief diario (estructura de datos, sin HTML)."""
from __future__ import annotations

import logging
from datetime import date

from finlab import config
from finlab.calendar import econ
from finlab.data import macro, news, prices
from finlab.portfolio import holdings, metrics

log = logging.getLogger(__name__)


def _coverage_movers() -> list[dict]:
    """Variación del día de los nombres de cobertura."""
    out = []
    cov = config.coverage().get("names", [])
    us = [n["us_ticker"] for n in cov if n.get("us_ticker")]
    quotes = prices.us_prices(us)
    for n in cov:
        t = n.get("us_ticker")
        q = quotes.get(t, {})
        pct, last = q.get("pct_change"), q.get("last")
        # Respaldo BYMA si Yahoo no trajo el % (rate limit, etc.)
        if pct is None and n.get("byma_ticker"):
            byma = prices.byma_find(n["byma_ticker"])
            if byma:
                pct, last = byma["pct_change"], byma["last"]
        out.append({"name": n["name"], "ticker": t, "pct_change": pct, "last": last})
    out.sort(key=lambda x: abs(x["pct_change"] or 0), reverse=True)
    return out


def _portfolio_movers() -> dict:
    positions, meta = holdings.load()
    movers = sorted(
        [{"ticker": p.ticker, "pct_change": p.pct_change, "pnl_pct": p.pnl_pct,
          "pnl_in_ars": p.pnl_in_ars, "value_usd": p.value_usd}
         for p in positions if p.pct_change is not None],
        key=lambda x: abs(x["pct_change"] or 0), reverse=True,
    )
    return {
        "total_usd": round(meta["total_usd"], 0) if meta["total_usd"] else None,
        "total_ars": round(meta["total_ars"], 0) if meta["total_ars"] else None,
        "mep": meta["mep"],
        "movers": movers[:8],
        "missing_prices": meta["missing_prices"],
        "exposures": metrics.exposures(positions),
    }


def build() -> dict:
    """Devuelve un dict con todas las secciones del brief."""
    s = config.settings()
    enabled = set(s["daily_brief"]["sections"])
    brief = {"date": date.today().isoformat(), "sections": {}}

    if "macro_global" in enabled:
        brief["sections"]["macro_global"] = news.fetch("global", mark_seen=False)[:8]
    if "macro_argentina" in enabled:
        brief["sections"]["macro_argentina"] = {
            "news": news.fetch("argentina", mark_seen=False)[:8],
            "bcra": macro.bcra_highlights(),
        }
    if "portfolio_movers" in enabled:
        brief["sections"]["portfolio_movers"] = _portfolio_movers()
    if "coverage_movers" in enabled:
        brief["sections"]["coverage_movers"] = _coverage_movers()
    if "econ_calendar" in enabled:
        brief["sections"]["econ_calendar"] = econ.today_events()
    return brief
