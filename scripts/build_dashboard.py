#!/usr/bin/env python3
"""Genera docs/index.html (dashboard estático para GitHub Pages).

Uso:
    python3 scripts/build_dashboard.py
"""
import logging

import _bootstrap  # noqa: F401

from finlab import config
from finlab.dashboard import build, render

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dashboard")


def main() -> None:
    ctx = build.build_context()
    html = render.render(ctx)
    out_dir = config.ROOT / "docs"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    # .nojekyll evita que GitHub Pages procese el sitio con Jekyll.
    (out_dir / ".nojekyll").touch()
    log.info("Dashboard generado en %s", out_dir / "index.html")


if __name__ == "__main__":
    main()
