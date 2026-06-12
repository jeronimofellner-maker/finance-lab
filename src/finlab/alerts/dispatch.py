"""Dedupe de alertas (ventana horaria) + envío por mail."""
from __future__ import annotations

import json
import logging
import time

from finlab import config
from finlab.alerts.rules import Alert
from finlab.mail import smtp

log = logging.getLogger(__name__)
_CACHE = config.DATA_DIR / "news_cache" / "alerts_sent.json"


def _load_cache() -> dict[str, float]:
    if _CACHE.exists():
        try:
            return json.loads(_CACHE.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_cache(c: dict) -> None:
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(json.dumps(c))


def _dedupe(alerts: list[Alert]) -> list[Alert]:
    window = config.settings()["mail"]["dedupe_window_hours"] * 3600
    cache = _load_cache()
    now = time.time()
    cache = {k: v for k, v in cache.items() if now - v < window}  # purge viejos
    fresh = []
    for a in alerts:
        if a.key not in cache:
            cache[a.key] = now
            fresh.append(a)
    _save_cache(cache)
    return fresh


def _render(alerts: list[Alert]) -> str:
    by_cat: dict[str, list[Alert]] = {}
    for a in alerts:
        by_cat.setdefault(a.category, []).append(a)
    labels = {"move": "📈 Movimientos >umbral", "earnings": "🗓️ Earnings",
              "ma": "🤝 M&A", "rating": "🏦 Rating", "regulatory": "⚖️ Regulatorio",
              "filing": "📄 SEC Filings"}
    parts = ['<div style="font-family:-apple-system,Arial,sans-serif;max-width:640px">']
    parts.append('<h2 style="color:#b00">Alertas Finance Lab</h2>')
    for cat, items in by_cat.items():
        parts.append(f'<h3>{labels.get(cat, cat)}</h3><ul>')
        for a in items:
            link = f' — <a href="{a.link}">link</a>' if a.link else ""
            parts.append(f"<li><b>{a.headline}</b><br><small>{a.detail}{link}</small></li>")
        parts.append("</ul>")
    parts.append("</div>")
    return "".join(parts)


def dispatch(alerts: list[Alert]) -> int:
    """Deduplica y envía. Devuelve cuántas alertas se mandaron."""
    fresh = _dedupe(alerts)
    if not fresh:
        log.info("Sin alertas nuevas.")
        return 0
    prefix = config.settings()["mail"]["subject_prefix_alert"]
    subject = f"{prefix} · {len(fresh)} evento(s)"
    smtp.send(subject, _render(fresh))
    return len(fresh)
