# CLAUDE.md — Finance Lab

Sistema personal de **equity research + gestión de cartera** de Jero Fellner
(estudiante final de Administración, UTDT, orientación Finanzas y Estrategia).
Objetivo de fondo: construir track record público y gestionar la cartera real.

## Cómo trabajamos (reglas de interacción)
- **Idioma:** español rioplatense. Directo, sin vueltas.
- **Sin disclaimers repetidos.** El "esto no es asesoramiento financiero" se asume
  una vez (está en el README) y no se repite en cada respuesta.
- **Sé exigente.** Si una tesis está floja, si un activo de la cartera no tiene
  justificación, o si un número no cierra, decilo. No validar por validar.
- **Cada posición de cartera lleva una tesis de una línea.** Si no se puede
  escribir, la posición no va. (Acordado 2026-06-11.)

## Perfil de inversión (fuente de verdad: `config/targets.yaml`)
- Moneda base: **USD-MEP** (mostrar también ARS). No medir en ARS nominal.
- Horizonte 5+ años, drawdown tolerado ~25%, **máx 15% por posición**, sin
  derivados ni apalancamiento.
- Benchmark: 60% S&P 500 + 40% Merval en USD-CCL.

## Arquitectura
```
config/      YAML editables (cartera, targets, cobertura, watchlist, fuentes, settings)
src/finlab/  paquete: data/ portfolio/ alerts/ brief/ calendar/ mail/ + config.py
scripts/     entrypoints: daily_brief, intraday_alerts, weekly_portfolio, new_note
launchd/     plist de alertas intradía (macOS)
.github/     workflow del brief diario (GitHub Actions, en la nube)
research/    notas publicadas + templates + modelos de valuación
data/        cache (gitignored)
```

## Fuentes de datos (todas free-tier)
| Qué | Fuente | Módulo |
|---|---|---|
| BYMA: acciones, CEDEARs, bonos, ONs, MEP | data912.com | `data/prices.py` |
| US equities + earnings | yfinance | `data/prices.py`, `data/fundamentals.py` |
| Macro AR (reservas, base, A3500, tasas) | API BCRA v4.0 | `data/macro.py` |
| Filings corporativos US | SEC EDGAR | `data/fundamentals.py` |
| Noticias | RSS (Ámbito, Cronista, Infobae, Reuters, CNBC…) | `data/news.py` |
| Agenda económica | ForexFactory JSON | `calendar/econ.py` |

MEP = AL30/AL30D (fallback GD30/GD30D). Limitaciones de calidad documentadas en README.

## Flujos
- **Brief diario** (07:30 ART, lun-vie) → GitHub Actions → `scripts/daily_brief.py`.
- **Alertas intradía** (±5%, earnings, M&A, rating, regulatorio; 11:00-17:30 ART)
  → launchd local cada 20' → `scripts/intraday_alerts.py` (filtra ventana).
- **Review semanal** → `scripts/weekly_portfolio.py` (manual o agregable a cron).
- **Notas quincenales** (domingos, español) → `scripts/new_note.py` arma el esqueleto.
- **Dashboard web** → `scripts/build_dashboard.py` genera `docs/index.html` (estático),
  el workflow lo regenera y commitea tras el brief, GitHub Pages lo sirve en
  https://jeronimofellner-maker.github.io/finance-lab/. **Repo público.**

## Privacidad (repo público)
- `settings.dashboard.show_absolute_values: false` → el dashboard publica SOLO
  porcentajes (asignación, P&L %, pesos). NUNCA valor absoluto USD/ARS, qty ni PPC.
  El detalle absoluto va solo por mail (privado). Mantener este invariante.
- Secretos solo en `.env` (local) y GitHub Secrets (CI). El historial de git se
  mantiene sin mail ni credenciales.

## Convenciones de código
- Todo importa rutas/config desde `finlab.config`. No hardcodear paths.
- Cada fetch de datos es **tolerante a fallos**: si una fuente cae, devuelve vacío
  y el resto sigue. Un brief incompleto es mejor que ningún brief.
- Secretos solo en `.env` (local) o GitHub Secrets (nube). Nunca en el repo.

## Tareas típicas para Claude
- Agregar/editar nombres de cobertura → `config/coverage.yaml`.
- Ajustar umbrales/horarios → `config/settings.yaml`.
- Sumar una fuente RSS → `config/sources.yaml`.
- Escribir/criticar una nota → `research/notes/`, usando el template.
- Discutir rebalanceo → correr `weekly_portfolio.py` y razonar sobre el output.
