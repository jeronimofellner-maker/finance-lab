#!/usr/bin/env python3
"""Entrypoint del BRIEF DIARIO. Corre por GitHub Actions (o a mano).

Uso:
    python3 scripts/daily_brief.py            # arma y envía por mail
    python3 scripts/daily_brief.py --dry-run  # imprime el HTML, NO envía
"""
import argparse
import logging

import _bootstrap  # noqa: F401

from finlab.brief import daily, render
from finlab.mail import smtp
from finlab import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="No envía: imprime el HTML.")
    args = ap.parse_args()

    brief = daily.build()
    html = render.render(brief)

    if args.dry_run:
        print(html)
        return

    prefix = config.settings()["mail"]["subject_prefix_brief"]
    smtp.send(f"{prefix} · {brief['date']}", html)


if __name__ == "__main__":
    main()
