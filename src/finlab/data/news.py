"""Agregador de noticias por RSS con dedupe persistente.

El dedupe evita mandarte la misma noticia dos veces entre brief y alertas.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import feedparser

from finlab import config

log = logging.getLogger(__name__)
_SEEN_FILE = config.DATA_DIR / "news_cache" / "seen.json"
_MAX_PER_FEED = 15


def _load_seen() -> set[str]:
    if _SEEN_FILE.exists():
        try:
            return set(json.loads(_SEEN_FILE.read_text()))
        except Exception:  # noqa: BLE001
            return set()
    return set()


def _save_seen(seen: set[str]) -> None:
    _SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Cap para no crecer infinito: guardamos los últimos 2000 ids.
    _SEEN_FILE.write_text(json.dumps(list(seen)[-2000:]))


def fetch(region: str, mark_seen: bool = True) -> list[dict]:
    """Trae noticias nuevas de una región ('global' | 'argentina').

    Devuelve [{title, link, source, published}]. Solo items no vistos antes.
    """
    feeds = config.sources().get("rss", {}).get(region, [])
    seen = _load_seen()
    fresh = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:  # noqa: BLE001
            log.warning("RSS %s falló: %s", feed.get("source"), exc)
            continue
        for entry in parsed.entries[:_MAX_PER_FEED]:
            uid = entry.get("id") or entry.get("link")
            if not uid or uid in seen:
                continue
            seen.add(uid)
            fresh.append(
                {
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "source": feed["source"],
                    "published": entry.get("published", ""),
                }
            )
    if mark_seen:
        _save_seen(seen)
    return fresh


def classify(title: str) -> list[str]:
    """Devuelve las categorías de alerta que matchea un título (ma/rating/regulatory)."""
    kw = config.sources().get("alert_keywords", {})
    low = title.lower()
    hits = []
    for cat, words in kw.items():
        if any(w.lower() in low for w in words):
            hits.append(cat)
    return hits
