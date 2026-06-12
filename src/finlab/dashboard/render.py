"""Render del dashboard a HTML estático (dark, mobile-first, Chart.js + SVG)."""
from __future__ import annotations

import json

# Paleta sobria, dark por default
_CSS = """
:root{
  --bg:#0b0e14; --card:#151a23; --line:#222a36; --txt:#e6edf3; --muted:#8b95a5;
  --green:#3fb950; --red:#f85149; --accent:#58a6ff; --chip:#1c2330;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Helvetica,Arial,sans-serif;
  line-height:1.5;-webkit-font-smoothing:antialiased;padding:0 0 48px}
.wrap{max-width:960px;margin:0 auto;padding:0 16px}
header{padding:28px 0 18px;border-bottom:1px solid var(--line);margin-bottom:24px}
h1{font-size:20px;font-weight:650;letter-spacing:-.2px}
.sub{color:var(--muted);font-size:12.5px;margin-top:3px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.chip{background:var(--chip);border:1px solid var(--line);border-radius:8px;
  padding:8px 12px;min-width:96px}
.chip .k{color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.4px}
.chip .v{font-size:17px;font-weight:650;margin-top:2px}
section{margin:30px 0}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);
  margin-bottom:14px;font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;color:var(--muted);font-weight:500;font-size:11px;text-transform:uppercase;
  letter-spacing:.4px;padding:0 0 10px;border-bottom:1px solid var(--line)}
td{padding:11px 0;border-bottom:1px solid var(--line);vertical-align:middle}
tr:last-child td{border-bottom:none}
.t-ticker{font-weight:600}.t-sec{color:var(--muted);font-size:11.5px}
.num{text-align:right;font-variant-numeric:tabular-nums}
.pos{color:var(--green)}.neg{color:var(--red)}.mut{color:var(--muted)}
.tag{font-size:9.5px;color:var(--muted);border:1px solid var(--line);border-radius:4px;
  padding:1px 4px;margin-left:5px;vertical-align:middle}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.gridM{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.mcard .k{color:var(--muted);font-size:11px}
.mcard .v{font-size:19px;font-weight:650;margin:3px 0 6px}
.news a{color:var(--accent);text-decoration:none}.news a:hover{text-decoration:underline}
.news li{list-style:none;padding:9px 0;border-bottom:1px solid var(--line);font-size:13.5px}
.news li:last-child{border-bottom:none}.news .src{color:var(--muted);font-size:11px}
.ag li{list-style:none;padding:8px 0;border-bottom:1px solid var(--line);font-size:13px;
  display:flex;gap:10px;align-items:baseline}
.ag li:last-child{border-bottom:none}.ag .d{color:var(--muted);font-size:11px;min-width:74px}
.cc{color:var(--accent);font-size:11px;min-width:34px}
a.note{color:var(--accent);text-decoration:none;font-size:11.5px}
footer{margin-top:36px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--muted);font-size:11px}
.canvasbox{position:relative;height:170px}
@media(max-width:560px){.grid2{grid-template-columns:1fr}h1{font-size:18px}}
"""

# Colores por clase de activo (consistentes entre los dos donuts)
_CLASS_COLORS = {
    "cedear": "#58a6ff", "us_equity": "#bc8cff", "accion_ar": "#3fb950",
    "bono_ar": "#f0883e", "ons": "#e3b341", "cash": "#8b95a5", "plazo_fijo": "#6e7681",
}


def _pct(v, suffix="%") -> str:
    if v is None:
        return '<span class="mut">s/d</span>'
    cls = "pos" if v >= 0 else "neg"
    return f'<span class="{cls}">{v:+.1f}{suffix}</span>'


def _sparkline(values: list[float], w=110, h=26) -> str:
    """SVG sparkline inline. Verde/rojo según pendiente total."""
    vals = [v for v in (values or []) if v is not None]
    if len(vals) < 2:
        return '<span class="mut" style="font-size:11px">s/d</span>'
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    n = len(vals)
    pts = " ".join(
        f"{round(i/(n-1)*(w-2)+1,1)},{round(h-1-((v-lo)/rng)*(h-2),1)}"
        for i, v in enumerate(vals)
    )
    color = "var(--green)" if vals[-1] >= vals[0] else "var(--red)"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'preserveAspectRatio="none"><polyline fill="none" stroke="{color}" '
            f'stroke-width="1.5" points="{pts}"/></svg>')


def _holdings_table(hold) -> str:
    rows = []
    for h in hold:
        ars = '<span class="tag">en ARS</span>' if h["pnl_in_ars"] else ""
        rows.append(
            f'<tr><td><span class="t-ticker">{h["ticker"]}</span><br>'
            f'<span class="t-sec">{h["sector"]}</span></td>'
            f'<td class="num">{h["weight_pct"]:.1f}%</td>'
            f'<td class="num">{_pct(h["pnl_day"])}</td>'
            f'<td class="num">{_pct(h["pnl_total"])}{ars}</td>'
            f'<td class="num">{_sparkline(h["spark"])}</td></tr>'
        )
    return (
        '<table><tr><th>Posición</th><th class="num">Peso</th>'
        '<th class="num">Día</th><th class="num">P&L</th>'
        '<th class="num">30d (USD)</th></tr>' + "".join(rows) + "</table>"
    )


def _coverage_table(cov) -> str:
    rows = []
    for c in cov:
        note = f'<a class="note" href="{c["note_url"]}">ver nota ↗</a>' if c["note_url"] else '<span class="mut">—</span>'
        rows.append(
            f'<tr><td>{c["name"]} <span class="t-sec">({c["ticker"]})</span></td>'
            f'<td class="num">{_pct(c["pct_day"])}</td><td class="num">{note}</td></tr>'
        )
    return ('<table><tr><th>Nombre</th><th class="num">Día</th>'
            '<th class="num">Nota</th></tr>' + "".join(rows) + "</table>")


def _macro_cards(m) -> str:
    def card(label, valstr, serie):
        return (f'<div class="card mcard"><div class="k">{label}</div>'
                f'<div class="v">{valstr}</div>{_sparkline(serie)}</div>')

    def fmt(v, dec=0, pre="", suf=""):
        return f"{pre}{v:,.{dec}f}{suf}" if v is not None else "s/d"

    return (
        '<div class="gridM">'
        + card("Dólar MEP", fmt(m["mep"]["valor"], 0, "$"), m["mep"]["serie"])
        + card("Dólar CCL", fmt(m["ccl"]["valor"], 0, "$"), m["ccl"]["serie"])
        + card("Riesgo país", fmt(m["riesgo_pais"]["valor"], 0, "", " pb"), m["riesgo_pais"]["serie"])
        + card("Reservas BCRA", fmt(m["reservas"]["valor"], 0, "US$", "M"), m["reservas"]["serie"])
        + card("Tasa TAMAR", fmt(m["tamar"]["valor"], 1, "", "%"), m["tamar"]["serie"])
        + card("Inflación m/m", fmt(m["infl_m"]["valor"], 1, "", "%"), m["infl_m"]["serie"])
        + card("Inflación i.a.", fmt(m["infl_ia"]["valor"], 1, "", "%"), m["infl_ia"]["serie"])
        + "</div>"
    )


def _news_list(items) -> str:
    if not items:
        return '<p class="mut">Sin novedades.</p>'
    li = "".join(
        f'<li><a href="{i["link"]}">{i["title"]}</a> '
        f'<span class="src">· {i["source"]}</span></li>' for i in items
    )
    return f'<ul class="news">{li}</ul>'


def _agenda_list(items) -> str:
    if not items:
        return '<p class="mut">Sin eventos de alto impacto en los próximos 7 días.</p>'
    li = "".join(
        f'<li><span class="d">{e["date"]} {e["time"]}</span>'
        f'<span class="cc">{e["currency"]}</span><span>{e["title"]}</span></li>'
        for e in items
    )
    return f'<ul class="ag">{li}</ul>'


def render(ctx: dict) -> str:
    pf = ctx["portfolio"]
    # Datos para los donuts (Chart.js)
    def chart_data(alloc):
        labels = list(alloc.keys())
        return {"labels": labels, "data": [alloc[k] for k in labels],
                "colors": [_CLASS_COLORS.get(k, "#8b95a5") for k in labels]}
    donut = {"actual": chart_data(pf["alloc_actual"]), "target": chart_data(pf["alloc_target"])}

    abs_chip = ""
    if pf.get("total_usd"):  # solo si show_absolute_values=true
        abs_chip = (f'<div class="chip"><div class="k">Total</div>'
                    f'<div class="v">US${pf["total_usd"]:,.0f}</div></div>')

    return f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Finance Lab · Jero Fellner</title>
<style>{_CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head><body><div class="wrap">

<header>
  <h1>Finance Lab</h1>
  <div class="sub">Research &amp; gestión de cartera · Jero Fellner · actualizado {ctx["updated_at"]}</div>
  <div class="chips">
    <div class="chip"><div class="k">P&amp;L día</div><div class="v">{_pct(pf["pnl_day_pct"])}</div></div>
    <div class="chip"><div class="k">P&amp;L total</div><div class="v">{_pct(pf["pnl_total_pct"])}</div></div>
    <div class="chip"><div class="k">Dólar MEP</div><div class="v">${(ctx["macro"]["mep"]["valor"] or 0):,.0f}</div></div>
    <div class="chip"><div class="k">Riesgo país</div><div class="v">{ctx["macro"]["riesgo_pais"]["valor"] or "s/d"}</div></div>
    {abs_chip}
  </div>
</header>

<section><h2>Cartera</h2><div class="card">{_holdings_table(pf["holdings"])}</div></section>

<section><h2>Asignación · actual vs target</h2>
  <div class="grid2">
    <div class="card"><div style="font-size:12px;color:var(--muted);margin-bottom:8px">Actual</div>
      <div class="canvasbox"><canvas id="cActual"></canvas></div></div>
    <div class="card"><div style="font-size:12px;color:var(--muted);margin-bottom:8px">Target</div>
      <div class="canvasbox"><canvas id="cTarget"></canvas></div></div>
  </div>
</section>

<section><h2>Cobertura</h2><div class="card">{_coverage_table(ctx["coverage"])}</div></section>

<section><h2>Macro Argentina · valor + tendencia 30d</h2>{_macro_cards(ctx["macro"])}</section>

<section><h2>Noticias del día</h2><div class="card">{_news_list(ctx["news"])}</div></section>

<section><h2>Agenda económica · próximos 7 días</h2><div class="card">{_agenda_list(ctx["agenda"])}</div></section>

<footer>
  Generado automáticamente por Finance Lab. Datos: data912, BCRA, argentinadatos,
  yfinance, SEC EDGAR, RSS. No es asesoramiento financiero.
</footer>
</div>

<script>
const DON = {json.dumps(donut)};
const opts = (t)=>({{type:'doughnut',data:{{labels:t.labels,
  datasets:[{{data:t.data,backgroundColor:t.colors,borderColor:'#0b0e14',borderWidth:2}}]}},
  options:{{cutout:'62%',plugins:{{legend:{{position:'bottom',
    labels:{{color:'#8b95a5',font:{{size:11}},boxWidth:10,padding:8}}}}}}}}}});
new Chart(document.getElementById('cActual'), opts(DON.actual));
new Chart(document.getElementById('cTarget'), opts(DON.target));
</script>
</body></html>"""
