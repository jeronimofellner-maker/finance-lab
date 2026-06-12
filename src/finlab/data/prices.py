"""Precios de mercado: BYMA local (data912) + US (yfinance) + MEP.

Diseño: cada fetch es tolerante a fallos. Si una fuente se cae, devuelve {} y el
resto del sistema sigue (un brief sin precios BYMA es mejor que ningún brief).
"""
from __future__ import annotations

import logging
from functools import lru_cache

import requests

from finlab import config

log = logging.getLogger(__name__)
_TIMEOUT = 15
_DATA912 = config.sources()["apis"]["data912_base"]

# Mapeo asset_class -> endpoint data912
_BYMA_ENDPOINTS = {
    "accion_ar": "arg_stocks",
    "cedear": "arg_cedears",
    "bono_ar": "arg_bonds",
    "ons": "arg_corp",
}


@lru_cache(maxsize=8)
def _fetch_data912(endpoint: str) -> tuple:
    """Trae un panel de data912. Cacheado por proceso (tuple = hashable)."""
    try:
        r = requests.get(f"{_DATA912}/{endpoint}", timeout=_TIMEOUT)
        r.raise_for_status()
        return tuple(r.json())
    except Exception as exc:  # noqa: BLE001
        log.warning("data912 %s falló: %s", endpoint, exc)
        return tuple()


def byma_snapshot(asset_class: str) -> dict[str, dict]:
    """{symbol: {last, pct_change, bid, ask}} para una clase BYMA."""
    endpoint = _BYMA_ENDPOINTS.get(asset_class)
    if not endpoint:
        return {}
    out = {}
    for row in _fetch_data912(endpoint):
        sym = row.get("symbol")
        if not sym:
            continue
        out[sym] = {
            "last": row.get("c"),
            "pct_change": row.get("pct_change"),
            "bid": row.get("px_bid"),
            "ask": row.get("px_ask"),
        }
    return out


@lru_cache(maxsize=1)
def get_mep() -> float | None:
    """MEP de referencia vía AL30/AL30D (fallback GD30/GD30D)."""
    bonds = {r.get("symbol"): r.get("c") for r in _fetch_data912("arg_bonds")}
    for ars, usd in (("AL30", "AL30D"), ("GD30", "GD30D"), ("AL30", "AL30C")):
        p_ars, p_usd = bonds.get(ars), bonds.get(usd)
        if p_ars and p_usd:
            return round(p_ars / p_usd, 2)
    log.warning("No pude calcular MEP desde data912.")
    return None


@lru_cache(maxsize=1)
def get_ccl() -> float | None:
    """CCL (contado con liqui) vía AL30/AL30C (fallback GD30/GD30C)."""
    bonds = {r.get("symbol"): r.get("c") for r in _fetch_data912("arg_bonds")}
    for ars, cable in (("AL30", "AL30C"), ("GD30", "GD30C")):
        p_ars, p_cable = bonds.get(ars), bonds.get(cable)
        if p_ars and p_cable:
            return round(p_ars / p_cable, 2)
    return None


def history_usd(tickers: list[str], period: str = "1mo") -> dict[str, list[float]]:
    """Cierres diarios en USD por ticker (yfinance) para sparklines. Degrada a []."""
    if not tickers:
        return {}
    import yfinance as yf

    out: dict[str, list[float]] = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period=period)
            closes = [round(float(c), 4) for c in hist["Close"].tolist() if c == c]
            out[t] = closes
        except Exception as exc:  # noqa: BLE001
            log.warning("history %s falló: %s", t, exc)
            out[t] = []
    return out


def _yahoo_chart(ticker: str) -> dict | None:
    """Fallback directo al chart endpoint de Yahoo (cuando fast_info no trae datos)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    try:
        r = requests.get(url, params={"range": "1d", "interval": "1d"},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=_TIMEOUT)
        r.raise_for_status()
        meta = r.json()["chart"]["result"][0]["meta"]
        last = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        pct = ((last / prev - 1) * 100) if last and prev else None
        return {"last": last, "prev_close": prev,
                "pct_change": round(pct, 2) if pct is not None else None,
                "currency": meta.get("currency", "USD")}
    except Exception as exc:  # noqa: BLE001
        log.warning("Yahoo chart %s falló: %s", ticker, exc)
        return None


def us_prices(tickers: list[str]) -> dict[str, dict]:
    """{ticker: {last, prev_close, pct_change, currency}} vía yfinance.

    Las claves de fast_info son camelCase (lastPrice/previousClose). Si Yahoo
    devuelve None (rate limit / sin dato), cae al chart endpoint.
    """
    if not tickers:
        return {}
    import yfinance as yf

    out = {}
    for t in tickers:
        rec = None
        try:
            fi = yf.Ticker(t).fast_info
            last = fi.get("lastPrice")
            prev = fi.get("previousClose")
            if last and prev:
                pct = (last / prev - 1) * 100
                rec = {"last": last, "prev_close": prev,
                       "pct_change": round(pct, 2),
                       "currency": fi.get("currency", "USD")}
        except Exception as exc:  # noqa: BLE001
            log.warning("yfinance %s falló: %s", t, exc)
        out[t] = rec or _yahoo_chart(t) or {
            "last": None, "prev_close": None, "pct_change": None, "currency": "USD"}
    return out


def byma_find(symbol: str) -> dict | None:
    """Busca un símbolo en todos los paneles BYMA (acciones, cedears, bonos, ONs).

    Útil como respaldo cuando Yahoo falla: casi todo el universo lista local.
    """
    for endpoint in ("arg_stocks", "arg_cedears", "arg_bonds", "arg_corp"):
        for row in _fetch_data912(endpoint):
            if row.get("symbol") == symbol:
                return {"last": row.get("c"), "pct_change": row.get("pct_change"),
                        "bid": row.get("px_bid"), "ask": row.get("px_ask")}
    return None


def price_lookup(ticker: str, asset_class: str) -> dict | None:
    """Resuelve precio de un instrumento según su clase. Devuelve dict o None.

    Para bonos/ONs/acciones/cedears -> precio en ARS (data912, panel pesos).
    Para us_equity -> precio en USD (yfinance).
    """
    if asset_class in _BYMA_ENDPOINTS:
        return byma_snapshot(asset_class).get(ticker)
    if asset_class == "us_equity":
        return us_prices([ticker]).get(ticker)
    return None
