"""Fundamentals y eventos corporativos: SEC EDGAR (filings) + yfinance (earnings).

SEC pide un User-Agent identificable (SEC_USER_AGENT en .env).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from functools import lru_cache

import requests

from finlab import config

log = logging.getLogger(__name__)
_TIMEOUT = 15


def _headers() -> dict:
    ua = config.env("SEC_USER_AGENT", "finance-lab research tool")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


@lru_cache(maxsize=1)
def _cik_map() -> dict[str, str]:
    """{ticker: CIK zero-padded} desde SEC."""
    url = config.sources()["apis"]["sec_tickers"]
    try:
        r = requests.get(url, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return {
            row["ticker"].upper(): str(row["cik_str"]).zfill(10)
            for row in data.values()
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("SEC tickers falló: %s", exc)
        return {}


def recent_filings(ticker: str, forms=("8-K", "10-Q", "10-K"), since_days: int = 3) -> list[dict]:
    """Filings recientes de un ticker US. [{form, date, url}]."""
    cik = _cik_map().get(ticker.upper())
    if not cik:
        return []
    url = config.sources()["apis"]["sec_submissions"].format(cik=cik)
    try:
        r = requests.get(url, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        recent = r.json().get("filings", {}).get("recent", {})
    except Exception as exc:  # noqa: BLE001
        log.warning("SEC submissions %s falló: %s", ticker, exc)
        return []

    out = []
    forms_l = {f.upper() for f in forms}
    today = date.today()
    for form, fdate, acc, doc in zip(
        recent.get("form", []),
        recent.get("filingDate", []),
        recent.get("accessionNumber", []),
        recent.get("primaryDocument", []),
    ):
        if form.upper() not in forms_l:
            continue
        try:
            d = datetime.strptime(fdate, "%Y-%m-%d").date()
        except ValueError:
            continue
        if (today - d).days > since_days:
            continue
        acc_nodash = acc.replace("-", "")
        out.append(
            {
                "form": form,
                "date": fdate,
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{doc}",
            }
        )
    return out


def next_earnings(ticker: str) -> date | None:
    """Próxima fecha de earnings vía yfinance, o None."""
    import yfinance as yf

    try:
        cal = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if cal is None or cal.empty:
            return None
        future = [d.date() for d in cal.index if d.date() >= date.today()]
        return min(future) if future else None
    except Exception as exc:  # noqa: BLE001
        log.warning("earnings %s falló: %s", ticker, exc)
        return None
