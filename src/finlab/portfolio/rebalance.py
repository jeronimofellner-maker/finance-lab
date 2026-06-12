"""Rebalanceo: drift de la foto actual vs targets.yaml + órdenes sugeridas."""
from __future__ import annotations

from finlab import config
from finlab.portfolio import metrics
from finlab.portfolio.holdings import Position


def suggest(positions: list[Position]) -> dict:
    """Compara pesos actuales vs target por clase y sugiere ajustes en USD."""
    tgt = config.targets()
    band = tgt.get("rebalance_band_pp", 5.0) / 100.0
    target_by_class = tgt.get("by_asset_class", {})
    current = metrics.exposures(positions)["by_asset_class"]
    total_usd = sum(p.value_usd for p in positions if p.value_usd) or 0.0

    rows = []
    for cls, target_w in target_by_class.items():
        cur_w = current.get(cls, 0.0)
        drift = cur_w - target_w
        action = "MANTENER"
        if drift > band:
            action = "VENDER"
        elif drift < -band:
            action = "COMPRAR"
        rows.append(
            {
                "asset_class": cls,
                "current_pct": round(cur_w * 100, 1),
                "target_pct": round(target_w * 100, 1),
                "drift_pp": round(drift * 100, 1),
                "action": action,
                "usd_delta": round(-drift * total_usd, 0),  # + = comprar, - = vender
            }
        )
    rows.sort(key=lambda r: abs(r["drift_pp"]), reverse=True)

    # Chequeo de límite de concentración (15% por nombre)
    max_w = tgt.get("risk", {}).get("max_weight_per_position", 0.15)
    breaches = [
        {"ticker": t, "weight_pct": round(w * 100, 1)}
        for t, w in metrics.concentration(positions).items()
        if w > max_w
    ]
    return {"rows": rows, "concentration_breaches": breaches, "total_usd": round(total_usd, 0)}
