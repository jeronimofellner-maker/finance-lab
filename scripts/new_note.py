#!/usr/bin/env python3
"""Crea el esqueleto de una nota de cobertura quincenal.

Uso:
    python3 scripts/new_note.py YPF
    python3 scripts/new_note.py MELI --stance long --target 2200
"""
import argparse
from datetime import date
from pathlib import Path

import _bootstrap  # noqa: F401
from finlab import config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--stance", default="watch", choices=["long", "hold", "short", "watch"])
    ap.add_argument("--target", default="", help="precio objetivo")
    args = ap.parse_args()

    template = (config.RESEARCH_DIR / "templates" / "nota_cobertura.md").read_text()
    today = date.today().isoformat()
    filled = (template
              .replace("{{TICKER}}", args.ticker.upper())
              .replace("{{FECHA}}", today)
              .replace("{{STANCE}}", args.stance)
              .replace("{{TARGET}}", args.target or "TBD"))

    out = config.RESEARCH_DIR / "notes" / f"{today}-{args.ticker.lower()}.md"
    if out.exists():
        print(f"Ya existe: {out}")
        return
    out.write_text(filled)
    print(f"Nota creada: {out}")


if __name__ == "__main__":
    main()
