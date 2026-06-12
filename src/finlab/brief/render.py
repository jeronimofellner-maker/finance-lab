"""Render del brief diario a HTML (email)."""
from __future__ import annotations


def _pct(v) -> str:
    if v is None:
        return '<span style="color:#888">s/d</span>'
    color = "#0a0" if v >= 0 else "#c00"
    return f'<span style="color:{color}">{v:+.1f}%</span>'


def _news_list(items) -> str:
    if not items:
        return '<p style="color:#888">Sin novedades.</p>'
    li = "".join(
        f'<li><a href="{i["link"]}" style="color:#06c;text-decoration:none">{i["title"]}</a>'
        f' <small style="color:#999">· {i["source"]}</small></li>'
        for i in items
    )
    return f'<ul style="padding-left:18px">{li}</ul>'


def render(brief: dict) -> str:
    s = brief["sections"]
    p = ['<div style="font-family:-apple-system,Arial,sans-serif;max-width:680px;color:#222">']
    p.append(f'<h1 style="margin-bottom:0">Brief diario · {brief["date"]}</h1>')
    p.append('<hr style="border:none;border-top:2px solid #111">')

    # Cartera
    pf = s.get("portfolio_movers")
    if pf:
        p.append("<h2>📊 Mi cartera</h2>")
        if pf["total_usd"]:
            p.append(
                f'<p>Valor total: <b>US$ {pf["total_usd"]:,.0f}</b> '
                f'(ARS {pf["total_ars"]:,.0f}) · MEP {pf["mep"]}</p>'
            )
        if pf["missing_prices"]:
            p.append(f'<p style="color:#c00"><small>⚠️ Sin precio: '
                     f'{", ".join(pf["missing_prices"])}</small></p>')
        if pf["movers"]:
            rows = "".join(
                f'<tr><td>{m["ticker"]}</td><td>{_pct(m["pct_change"])}</td>'
                f'<td>P&amp;L {_pct(m["pnl_pct"])}'
                f'{" <small style=\'color:#999\'>(en ARS)</small>" if m.get("pnl_in_ars") else ""}'
                f'</td></tr>'
                for m in pf["movers"]
            )
            p.append(f'<table style="border-collapse:collapse">{rows}</table>')
            p.append('<p style="color:#999;font-size:11px">P&amp;L "(en ARS)" = retorno '
                     'nominal en pesos, no ajustado por dólar.</p>')
        exp = pf["exposures"]["by_asset_class"]
        if exp:
            p.append("<p><small>Exposición: " +
                     " · ".join(f"{k} {v*100:.0f}%" for k, v in exp.items()) + "</small></p>")

    # Cobertura
    cov = s.get("coverage_movers")
    if cov:
        p.append("<h2>🎯 Cobertura</h2><table style='border-collapse:collapse'>")
        for c in cov:
            p.append(f'<tr><td>{c["name"]} ({c["ticker"]})</td>'
                     f'<td>{_pct(c["pct_change"])}</td></tr>')
        p.append("</table>")

    # Macro global
    if "macro_global" in s:
        p.append("<h2>🌎 Macro global</h2>")
        p.append(_news_list(s["macro_global"]))

    # Macro Argentina
    ar = s.get("macro_argentina")
    if ar:
        p.append("<h2>🇦🇷 Argentina</h2>")
        if ar.get("bcra"):
            li = "".join(f'<li>{b["descripcion"]}: <b>{b["valor"]}</b> '
                         f'<small>({b["fecha"]})</small></li>' for b in ar["bcra"])
            p.append(f'<ul style="padding-left:18px">{li}</ul>')
        p.append(_news_list(ar.get("news", [])))

    # Agenda
    cal = s.get("econ_calendar")
    if cal is not None:
        p.append("<h2>🗓️ Agenda económica de hoy</h2>")
        if cal:
            li = "".join(f'<li>{e["time"]} · {e["currency"]} · '
                         f'<b>{e["title"]}</b> <small>({e["impact"]})</small></li>' for e in cal)
            p.append(f'<ul style="padding-left:18px">{li}</ul>')
        else:
            p.append('<p style="color:#888">Sin eventos relevantes.</p>')

    p.append('<hr><p style="color:#aaa;font-size:11px">Finance Lab · generado automáticamente. '
             'No es asesoramiento financiero.</p></div>')
    return "".join(p)
