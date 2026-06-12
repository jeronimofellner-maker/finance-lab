"""Carga de configuración (YAML) y secretos (.env).

Todo el resto del paquete importa desde acá para no hardcodear rutas.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Raíz del proyecto = dos niveles arriba de este archivo (src/finlab/config.py -> raíz)
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RESEARCH_DIR = ROOT / "research"
LOGS_DIR = ROOT / "logs"

# Cargar .env una sola vez (si existe). En GitHub Actions las vars vienen del entorno.
load_dotenv(ROOT / ".env")


@lru_cache(maxsize=None)
def load_yaml(name: str) -> dict:
    """Carga config/<name>.yaml. `name` sin extensión."""
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Falta config: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def env(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Lee una variable de entorno (de .env o del entorno real)."""
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(
            f"Falta la variable de entorno {key}. Completá .env (ver .env.example)."
        )
    return val


# Accesos directos a cada config
settings = lambda: load_yaml("settings")          # noqa: E731
sources = lambda: load_yaml("sources")            # noqa: E731
targets = lambda: load_yaml("targets")            # noqa: E731
portfolio = lambda: load_yaml("portfolio")        # noqa: E731
coverage = lambda: load_yaml("coverage")          # noqa: E731
watchlist = lambda: load_yaml("watchlist")        # noqa: E731
