#!/usr/bin/env python3
"""Review semanal de cartera: valuación, exposición, P&L y rebalanceo.

Imprime en consola (tabla) y opcionalmente lo manda por mail.
Uso:
    python3 scripts/weekly_portfolio.py            # consola
    python3 scripts/weekly_portfolio.py --mail      # además, manda por mail
"""
import argparse
import logging

import _bootstrap  # noqa: F401
from tabulate import tabulate

from finlab.portfolio import holdings, metrics, rebalance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mail", action="store_true")
    args = ap.parse_args()

    positions, meta = holdings.load()
    print(f"\n=== CARTERA (MEP {meta['mep']}) ===")
    print(f"Total: US$ {meta['total_usd']:,.0f}  |  ARS {meta['total_ars']:,.0f}\n")

    rows = [[p.ticker, p.asset_class, p.qty, p.last_price,
             f"{p.value_usd:,.0f}" if p.value_usd else "—",
             f"{p.pnl_pct:+.1f}%" if p.pnl_pct is not None else "—",
             f"{p.pct_change:+.1f}%" if p.pct_change is not None else "—"]
            for p in positions]
    print(tabulate(rows, headers=["Ticker", "Clase", "Qty", "Precio", "USD", "P&L", "Día"]))

    print("\n=== EXPOSICIÓN POR CLASE ===")
    for k, v in metrics.exposures(positions)["by_asset_class"].items():
        print(f"  {k:<12} {v*100:5.1f}%")

    print("\n=== REBALANCEO ===")
    reb = rebalance.suggest(positions)
    rrows = [[r["asset_class"], f'{r["current_pct"]}%', f'{r["target_pct"]}%',
              f'{r["drift_pp"]:+}pp', r["action"], f'{r["usd_delta"]:+,.0f}']
             for r in reb["rows"]]
    print(tabulate(rrows, headers=["Clase", "Actual", "Target", "Drift", "Acción", "USD"]))
    if reb["concentration_breaches"]:
        print("\n⚠️  Exceden 15% por posición:")
        for b in reb["concentration_breaches"]:
            print(f"   {b['ticker']}: {b['weight_pct']}%")

    if args.mail:
        from finlab.mail import smtp
        exp = metrics.exposures(positions)["by_asset_class"]
        exp_html = "".join(f"<li>{k}: {v*100:.0f}%</li>" for k, v in exp.items())
        reb_html = "".join(
            f'<li>{r["asset_class"]}: {r["action"]} '
            f'({r["current_pct"]}% → {r["target_pct"]}%, {r["usd_delta"]:+,.0f} USD)</li>'
            for r in reb["rows"] if r["action"] != "MANTENER"
        ) or "<li>Sin rebalanceo necesario.</li>"
        body = (f"<h2>Review semanal de cartera</h2>"
                f"<p>Total: <b>US$ {meta['total_usd']:,.0f}</b> (MEP {meta['mep']})</p>"
                f"<h3>Exposición</h3><ul>{exp_html}</ul>"
                f"<h3>Acciones de rebalanceo</h3><ul>{reb_html}</ul>")
        smtp.send("[Finance Lab] Review semanal de cartera", body)


if __name__ == "__main__":
    main()
