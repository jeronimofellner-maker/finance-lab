"""Reglas de alertas: movimiento ±X%, earnings próximos, M&A/rating/regulatorio.

Universo vigilado = cartera + cobertura + watchlist.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from finlab import config
from finlab.data import fundamentals, news, prices

log = logging.getLogger(__name__)


@dataclass
class Alert:
    category: str   # move | earnings | ma | rating | regulatory | filing
    ticker: str
    headline: str
    detail: str
    link: str = ""

    @property
    def key(self) -> str:
        """Clave de dedupe (categoría+ticker+headline)."""
        return f"{self.category}:{self.ticker}:{self.headline}"[:200]


def _watched_universe() -> dict[str, dict]:
    """{ticker: {us_ticker, byma_ticker, asset_class}} de cartera+cobertura+watchlist."""
    uni: dict[str, dict] = {}
    for p in config.portfolio().get("positions", []) or []:
        uni[p["ticker"]] = {"asset_class": p["asset_class"], "us_ticker": None,
                            "byma_ticker": p["ticker"]}
    for src in (config.coverage(), config.watchlist()):
        for n in (src.get("names") or []):
            label = n.get("us_ticker") or n.get("byma_ticker") or n.get("name")
            uni.setdefault(label, {})
            uni[label].update(
                {"us_ticker": n.get("us_ticker"), "byma_ticker": n.get("byma_ticker"),
                 "asset_class": uni[label].get("asset_class", "us_equity")}
            )
    return uni


def check_moves(threshold: float) -> list[Alert]:
    """Alertas por movimiento intradiario >= threshold (%)."""
    alerts = []
    uni = _watched_universe()
    # US tickers en un solo batch
    us = [v["us_ticker"] for v in uni.values() if v.get("us_ticker")]
    us_quotes = prices.us_prices(list(dict.fromkeys(us)))
    for label, info in uni.items():
        pct = None
        sym = info.get("us_ticker") or label
        if sym in us_quotes:
            pct = us_quotes[sym].get("pct_change")
        # Respaldo BYMA (sirve para US rate-limitado y para nombres solo-locales)
        if pct is None and info.get("byma_ticker"):
            q = prices.byma_find(info["byma_ticker"])
            pct = q.get("pct_change") if q else None
        if pct is not None and abs(pct) >= threshold:
            arrow = "▲" if pct > 0 else "▼"
            alerts.append(
                Alert("move", label, f"{label} {arrow} {pct:+.1f}%",
                      f"Movimiento intradiario de {pct:+.1f}%.")
            )
    return alerts


def check_earnings(lookahead_days: int) -> list[Alert]:
    alerts = []
    uni = _watched_universe()
    for label, info in uni.items():
        t = info.get("us_ticker")
        if not t:
            continue
        d = fundamentals.next_earnings(t)
        if d is not None:
            from datetime import date
            days = (d - date.today()).days
            if 0 <= days <= lookahead_days:
                alerts.append(
                    Alert("earnings", label, f"{label}: earnings en {days}d ({d})",
                          f"Reporta resultados el {d}.")
                )
    return alerts


def check_filings(since_days: int = 2) -> list[Alert]:
    alerts = []
    uni = _watched_universe()
    for label, info in uni.items():
        t = info.get("us_ticker")
        if not t:
            continue
        for f in fundamentals.recent_filings(t, since_days=since_days):
            alerts.append(
                Alert("filing", label, f"{label}: filing {f['form']} ({f['date']})",
                      f"Nuevo {f['form']} en SEC.", link=f["url"])
            )
    return alerts


def check_news() -> list[Alert]:
    """Noticias que matchean M&A / rating / regulatorio (sobre todo el feed)."""
    alerts = []
    for region in ("global", "argentina"):
        for item in news.fetch(region, mark_seen=True):
            cats = news.classify(item["title"])
            for cat in cats:
                if cat in ("ma", "rating", "regulatory"):
                    alerts.append(
                        Alert(cat, "—", item["title"],
                              f"[{item['source']}] {cat.upper()}", link=item["link"])
                    )
    return alerts


def collect_all() -> list[Alert]:
    s = config.settings()["intraday_alerts"]
    triggers = set(s.get("triggers", []))
    out: list[Alert] = []
    if "move" in triggers:
        out += check_moves(s["move_threshold_pct"])
    if "earnings" in triggers:
        out += check_earnings(s["earnings_lookahead_days"])
    if {"ma", "rating", "regulatory"} & triggers:
        out += check_news()
    out += check_filings()
    return out
