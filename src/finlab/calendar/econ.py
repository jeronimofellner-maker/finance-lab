"""Agenda económica del día vía ForexFactory (JSON semanal free).

Limitación conocida: ForexFactory cubre bien USD/EUR/global, pobre en eventos
puramente locales de Argentina (INDEC/BCRA). Para AR complementamos con noticias.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from finlab import config

log = logging.getLogger(__name__)
_TIMEOUT = 15
_CURRENCIES = {"USD", "ALL"}  # foco; ARS casi nunca aparece


def today_events(min_impact: str = "Medium") -> list[dict]:
    """Eventos de hoy. [{time, currency, impact, title}]."""
    url = config.sources()["apis"]["econ_calendar"]
    try:
        r = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "finance-lab"})
        r.raise_for_status()
        events = r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("Calendario económico falló: %s", exc)
        return []

    rank = {"Low": 0, "Medium": 1, "High": 2, "Holiday": 0}
    floor = rank.get(min_impact, 1)
    today = date.today().isoformat()
    out = []
    for ev in events:
        ddate = (ev.get("date") or "")[:10]
        if ddate != today:
            continue
        if rank.get(ev.get("impact", "Low"), 0) < floor:
            continue
        out.append(
            {
                "time": ev.get("date", "")[11:16] or "—",
                "currency": ev.get("country", ev.get("currency", "")),
                "impact": ev.get("impact", ""),
                "title": ev.get("title", ""),
            }
        )
    return out


def upcoming_events(min_impact: str = "High", days: int = 7) -> list[dict]:
    """Eventos desde hoy hasta +days (limitado a la semana del feed ForexFactory)."""
    from datetime import timedelta

    url = config.sources()["apis"]["econ_calendar"]
    try:
        r = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "finance-lab"})
        r.raise_for_status()
        events = r.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("Calendario económico falló: %s", exc)
        return []

    rank = {"Low": 0, "Medium": 1, "High": 2, "Holiday": 0}
    floor = rank.get(min_impact, 2)
    today = date.today()
    horizon = today + timedelta(days=days)
    out = []
    for ev in events:
        raw = (ev.get("date") or "")[:10]
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            continue
        if not (today <= d <= horizon):
            continue
        if rank.get(ev.get("impact", "Low"), 0) < floor:
            continue
        out.append(
            {
                "date": raw,
                "time": ev.get("date", "")[11:16] or "—",
                "currency": ev.get("country", ev.get("currency", "")),
                "impact": ev.get("impact", ""),
                "title": ev.get("title", ""),
            }
        )
    out.sort(key=lambda e: (e["date"], e["time"]))
    return out
