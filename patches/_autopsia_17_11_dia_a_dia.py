"""Tabela dia-a-dia do historico LIVE (10 dias) com custo canonico e slippage do gate."""
from __future__ import annotations

import json

h = json.load(open(r"C:\AIOFEN\logs\_autopsia_17_11_historico.json", encoding="utf-8"))
dias = [(k, v) for k, v in h["por_dia"].items() if v["saidas"] > 0]
dias.sort()

CUSTO_RS = 1.20      # entrada + saida, 1 contrato
SLIP_PTS = 2.0       # 1,0 pt por lado

print(f"{'dia':>12} {'tr':>3} {'bruto_pts':>10} {'custo_pts':>10} {'slip_pts':>9} "
      f"{'liq_pts':>8} {'liq_R$':>9} {'acum_R$':>10}")
acum = 0.0
tot = {"tr": 0, "bruto": 0.0, "custo": 0.0, "slip": 0.0, "liq": 0.0}
for dia, v in dias:
    n = v["saidas"]
    bruto = v["pl_rs"] / 10.0
    custo = n * CUSTO_RS / 10.0
    slip = n * SLIP_PTS
    liq = bruto - custo - slip
    acum += liq * 10
    tot["tr"] += n
    tot["bruto"] += bruto
    tot["custo"] += custo
    tot["slip"] += slip
    tot["liq"] += liq
    print(f"{dia:>12} {n:>3} {bruto:>10.1f} {custo:>10.2f} {slip:>9.1f} "
          f"{liq:>8.2f} {liq*10:>9.2f} {acum:>10.2f}")

print("-" * 78)
print(f"{'TOTAL':>12} {tot['tr']:>3} {tot['bruto']:>10.1f} {tot['custo']:>10.2f} "
      f"{tot['slip']:>9.1f} {tot['liq']:>8.2f} {tot['liq']*10:>9.2f}")
print(f"\nexpectancia com gate: {tot['liq']/tot['tr']:+.2f} pts/trade")
print(f"expectancia so com custo: {(tot['bruto']-tot['custo'])/tot['tr']:+.2f} pts/trade")
print(f"sem custo nenhum: {tot['bruto']/tot['tr']:+.2f} pts/trade")

# cenarios de slippage
print("\ncenarios de slippage (total 10 dias):")
for sp in (0.0, 0.5, 1.0, 1.5, 2.0):
    liq = tot["bruto"] - tot["custo"] - tot["tr"] * sp
    print(f"  {sp:.1f} pt/trade -> {liq:>+7.2f} pts  = R$ {liq*10:>+9.2f}  "
          f"exp {liq/tot['tr']:>+6.2f}")

# e sem os 2 ultimos dias
ant = [d for d in dias if d[0] < "2026-11-16"]
tr = sum(v["saidas"] for _, v in ant)
br = sum(v["pl_rs"] for _, v in ant) / 10.0
print(f"\nso os 8 dias ANTES de 16/11: {tr} trades, bruto {br:+.1f} pts, "
      f"com gate {br - tr*0.12 - tr*2:+.1f} pts")
