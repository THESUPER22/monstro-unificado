"""Estatistica do dia 17/11 a partir do JSON do MT5 (somente leitura)."""
from __future__ import annotations

import json
import math

P = r"C:\AIOFEN\logs\_autopsia_17_11_mt5.json"
d = json.load(open(P, encoding="utf-8"))
deals = d["deals_hoje"]

entradas = {x["position_id"]: x for x in deals if x["entry"] == 0}
saidas = [x for x in deals if x["entry"] in (1, 2)]

trades = []
for s in saidas:
    e = entradas.get(s["position_id"])
    if not e:
        continue
    pts = s["profit"] / 10.0
    kind = "TP" if s["comment"].startswith("[tp") else (
        "SL" if s["comment"].startswith("[sl") else "OUTRO")
    trades.append({
        "pos": s["position_id"], "lado": e["type"], "entrada": e["price"],
        "saida": s["price"], "pts": round(pts, 2), "rs": s["profit"],
        "tipo": kind, "hora_local": s["servidor"],
    })

trades.sort(key=lambda t: t["hora_local"])
n = len(trades)
wins = [t for t in trades if t["pts"] > 0]
losses = [t for t in trades if t["pts"] <= 0]
gp = sum(t["pts"] for t in wins)
gl = -sum(t["pts"] for t in losses)

# custo canonico R$1,20 por contrato por operacao (entrada+saida)
custo_rs = n * 1.20
# slippage canonico do gate: 1,0 pt por lado = 2,0 pts por trade
slip_pts = n * 2.0

res = {
    "n_trades": n,
    "buy": sum(1 for t in trades if t["lado"] == "BUY"),
    "sell": sum(1 for t in trades if t["lado"] == "SELL"),
    "tp": sum(1 for t in trades if t["tipo"] == "TP"),
    "sl_loss": sum(1 for t in trades if t["tipo"] == "SL" and t["pts"] < 0),
    "sl_trailing_win": sum(1 for t in trades if t["tipo"] == "SL" and t["pts"] > 0),
    "wins": len(wins), "losses": len(losses),
    "wr": round(100.0 * len(wins) / n, 1),
    "bruto_pts": round(gp - gl, 2),
    "bruto_rs": round((gp - gl) * 10, 2),
    "gross_profit_pts": round(gp, 2),
    "gross_loss_pts": round(gl, 2),
    "pf_bruto": round(gp / gl, 2) if gl else None,
    "media_win_pts": round(gp / len(wins), 2) if wins else None,
    "media_loss_pts": round(-gl / len(losses), 2) if losses else None,
    "custo_rs": custo_rs,
    "liquido_rs": round((gp - gl) * 10 - custo_rs, 2),
    "liquido_pts": round((gp - gl) - custo_rs / 10.0, 2),
    "slip_gate_pts": slip_pts,
    "liquido_com_slip_pts": round((gp - gl) - custo_rs / 10.0 - slip_pts, 2),
    "liquido_com_slip_rs": round(((gp - gl) - custo_rs / 10.0 - slip_pts) * 10, 2),
    "exp_pts_custo": round(((gp - gl) - custo_rs / 10.0) / n, 2),
    "exp_pts_gate": round(((gp - gl) - custo_rs / 10.0 - slip_pts) / n, 2),
    "pf_gate": round((gp - n * 1.2) / (gl + n * 0.8), 2),
}

# p-valor binomial unilateral (12/16 sob p=0,5)
k = len(wins)
p = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
res["p_binomial_unilateral"] = round(p, 5)
res["p_binomial_pct"] = round(100 * p, 3)

# comparacao com ontem (9 trades, 9/9)
k2, n2 = 9 + len(wins), 9 + n
res["acumulado_2d"] = {
    "trades": n2, "wins": k2, "wr": round(100 * k2 / n2, 1),
    "p_binomial": round(sum(math.comb(n2, i) for i in range(k2, n2 + 1)) / 2 ** n2, 6),
}

res["trades"] = trades
print(json.dumps(res, ensure_ascii=True, indent=1))
