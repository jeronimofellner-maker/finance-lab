"""Macro Argentina vía API oficial del BCRA (v4.0/monetarias).

Un solo GET trae todas las series con su último valor. Filtramos las que importan.
"""
from __future__ import annotations

import logging

import requests

from finlab import config

log = logging.getLogger(__name__)
_TIMEOUT = 15


def bcra_highlights() -> list[dict]:
    """[{descripcion, valor, fecha}] para las variables (por idVariable) de sources.yaml."""
    src = config.sources()
    url = src["apis"]["bcra_monetarias"]
    wanted = {h["id"]: h.get("label") for h in src.get("bcra_highlights", [])}
    try:
        # verify=False: la cadena de cert del BCRA a veces falla; es API pública.
        r = requests.get(url, timeout=_TIMEOUT, verify=False)
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as exc:  # noqa: BLE001
        log.warning("BCRA falló: %s", exc)
        return []

    by_id = {row.get("idVariable"): row for row in results}
    out = []
    for vid, label in wanted.items():  # respeta el orden del config
        row = by_id.get(vid)
        if not row:
            continue
        out.append(
            {
                "descripcion": label or row.get("descripcion"),
                "valor": row.get("ultValorInformado"),
                "fecha": row.get("ultFechaInformada"),
            }
        )
    return out


def bcra_series(id_var: int, n: int = 30) -> list[float]:
    """Últimos n valores de una serie BCRA (ascendente, para sparkline)."""
    base = config.sources()["apis"]["bcra_monetarias"]
    try:
        r = requests.get(f"{base}/{id_var}", params={"limit": n}, timeout=_TIMEOUT, verify=False)
        r.raise_for_status()
        detalle = r.json().get("results", [{}])[0].get("detalle", [])
    except Exception as exc:  # noqa: BLE001
        log.warning("BCRA serie %s falló: %s", id_var, exc)
        return []
    # La API devuelve más reciente primero; lo doy ascendente.
    vals = [d.get("valor") for d in detalle if d.get("valor") is not None]
    return list(reversed(vals))


def riesgo_pais(n: int = 30) -> dict:
    """Riesgo país (EMBI) actual + serie de n puntos. {valor, fecha, serie}."""
    url = config.sources()["apis"]["riesgo_pais"]
    try:
        r = requests.get(url, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        serie = [p["valor"] for p in data[-n:] if p.get("valor") is not None]
        last = data[-1] if data else {}
        return {"valor": last.get("valor"), "fecha": last.get("fecha"), "serie": serie}
    except Exception as exc:  # noqa: BLE001
        log.warning("Riesgo país falló: %s", exc)
        return {"valor": None, "fecha": None, "serie": []}


def dolar_series(casa: str, n: int = 30) -> list[float]:
    """Serie histórica de un dólar (casa: 'bolsa'=MEP, 'contadoconliqui'=CCL)."""
    base = config.sources()["apis"]["dolar_hist"]
    try:
        r = requests.get(f"{base}/{casa}", timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return [p.get("venta") for p in data[-n:] if p.get("venta") is not None]
    except Exception as exc:  # noqa: BLE001
        log.warning("Dólar serie %s falló: %s", casa, exc)
        return []
