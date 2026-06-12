#!/usr/bin/env python3
"""Entrypoint de ALERTAS INTRADÍA. Corre por launchd cada N minutos en rueda.

Respeta la ventana horaria (11:00-17:30 ART, lun-vie) salvo --force.
Uso:
    python3 scripts/intraday_alerts.py
    python3 scripts/intraday_alerts.py --force      # ignora ventana horaria
    python3 scripts/intraday_alerts.py --dry-run     # no envía, lista alertas
"""
import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import _bootstrap  # noqa: F401

from finlab import config
from finlab.alerts import dispatch, rules

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("intraday")


def _in_window() -> bool:
    s = config.settings()
    tz = ZoneInfo(s["timezone"])
    now = datetime.now(tz)
    ia = s["intraday_alerts"]
    if ia.get("weekdays_only", True) and now.weekday() >= 5:
        return False
    start = datetime.strptime(ia["window_start"], "%H:%M").time()
    end = datetime.strptime(ia["window_end"], "%H:%M").time()
    return start <= now.time() <= end


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.force and not _in_window():
        log.info("Fuera de ventana horaria; salgo.")
        return

    alerts = rules.collect_all()
    if args.dry_run:
        for a in alerts:
            print(f"[{a.category}] {a.headline} — {a.detail}")
        print(f"\nTotal: {len(alerts)} alertas (antes de dedupe).")
        return

    sent = dispatch.dispatch(alerts)
    log.info("Alertas enviadas: %d", sent)


if __name__ == "__main__":
    main()
