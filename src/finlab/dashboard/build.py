"""Arma el contexto de datos del dashboard (sin HTML).

Privacidad: modo solo-% (settings.dashboard.show_absolute_values). En ese modo NO
se exponen valores absolutos (USD/ARS) ni cantidades.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from finlab import config
from finlab.calendar import econ
from finlab.data import macro, news, prices
from finlab.portfolio import holdings, metrics

log = logging.getLogger(__name__)

# idVariable BCRA usados en el panel macro (mismos que el brief + extras de serie)
_BCRA = {"reservas": 1, "tamar": 44, "infl_m": 27, "infl_ia": 28}


def _portfolio(positions, meta) -> dict:
    show_abs = config.settings()["dashboard"].get("show_absolute_values", False)
    conc = metrics.concentration(positions)            # {ticker: peso 0..1}
    pnl = metrics.total_pnl(positions)

    # P&L del día ponderado por peso de cartera
    day = sum((p.pct_change or 0) * conc.get(p.ticker, 0)
              for p in positions if p.pct_change is not None)

    # Sparklines 30d en USD (yfinance; degrada a [] si Yahoo falla)
    spark = prices.history_usd([p.ticker for p in positions])

    rows = []
    for p in sorted(positions, key=lambda x: conc.get(x.ticker, 0), reverse=True):
        rows.append({
            "ticker": p.ticker,
            "sector": p.sector,
            "weight_pct": round(conc.get(p.ticker, 0) * 100, 1),
            "pnl_day": p.pct_change,
            "pnl_total": p.pnl_pct,
            "pnl_in_ars": p.pnl_in_ars,
            "spark": spark.get(p.ticker, []),
        })

    out = {
        "pnl_day_pct": round(day, 2),
        "pnl_total_pct": pnl["pnl_pct"],
        "holdings": rows,
        "alloc_actual": {k: round(v * 100, 1)
                         for k, v in metrics.exposures(positions)["by_asset_class"].items()},
        "alloc_target": {k: round(v * 100, 1)
                         for k, v in config.targets().get("by_asset_class", {}).items()},
    }
    if show_abs:  # solo si se habilita explícitamente
        out["total_usd"] = round(meta["total_usd"], 0) if meta["total_usd"] else None
        out["total_ars"] = round(meta["total_ars"], 0) if meta["total_ars"] else None
    return out


def _coverage() -> list[dict]:
    repo = config.settings()["dashboard"]["repo_url"]
    notes_dir = config.RESEARCH_DIR / "notes"
    cov = config.coverage().get("names", []) or []
    us = [n["us_ticker"] for n in cov if n.get("us_ticker")]
    quotes = prices.us_prices(us)
    out = []
    for n in cov:
        t = n.get("us_ticker")
        pct = quotes.get(t, {}).get("pct_change")
        if pct is None and n.get("byma_ticker"):
            b = prices.byma_find(n["byma_ticker"])
            pct = b.get("pct_change") if b else None
        # Buscar nota publicada más reciente para este ticker
        note_url = None
        if notes_dir.exists():
            matches = sorted(notes_dir.glob(f"*-{(t or n['name']).lower()}.md"))
            if matches:
                note_url = f"{repo}/blob/main/research/notes/{matches[-1].name}"
        out.append({"name": n["name"], "ticker": t, "pct_day": pct, "note_url": note_url})
    return out


def _macro() -> dict:
    hl = {h["descripcion"]: h for h in macro.bcra_highlights()}
    rp = macro.riesgo_pais()
    return {
        "mep": {"valor": prices.get_mep(), "serie": macro.dolar_series("bolsa")},
        "ccl": {"valor": prices.get_ccl(), "serie": macro.dolar_series("contadoconliqui")},
        "reservas": {"valor": next((v["valor"] for v in hl.values() if "Reservas" in v["descripcion"]), None),
                     "serie": macro.bcra_series(_BCRA["reservas"])},
        "riesgo_pais": {"valor": rp["valor"], "serie": rp["serie"]},
        "tamar": {"valor": next((v["valor"] for v in hl.values() if "TAMAR" in v["descripcion"]), None),
                  "serie": macro.bcra_series(_BCRA["tamar"])},
        "infl_m": {"valor": next((v["valor"] for v in hl.values() if "mensual" in v["descripcion"]), None),
                   "serie": macro.bcra_series(_BCRA["infl_m"], n=12)},
        "infl_ia": {"valor": next((v["valor"] for v in hl.values() if "interanual" in v["descripcion"]), None),
                    "serie": macro.bcra_series(_BCRA["infl_ia"], n=12)},
    }


def build_context() -> dict:
    positions, meta = holdings.load()
    tz = ZoneInfo(config.settings()["timezone"])
    return {
        "updated_at": datetime.now(tz).strftime("%Y-%m-%d %H:%M ART"),
        "portfolio": _portfolio(positions, meta),
        "coverage": _coverage(),
        "macro": _macro(),
        "news": (news.fetch("argentina", mark_seen=False)
                 + news.fetch("global", mark_seen=False))[:10],
        "agenda": econ.upcoming_events(min_impact="High", days=7),
    }
