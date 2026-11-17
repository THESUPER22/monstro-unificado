"""Tabela trade-a-trade do dia 17/11 em hora LOCAL (servidor + 3h). Somente leitura."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

P = r"C:\AIOFEN\logs\_autopsia_17_11_mt5.json"
d = json.load(open(P, encoding="utf-8"))
deals = d["deals_hoje"]

entradas = {x["position_id"]: x for x in deals if x["entry"] == 0}
saidas = [x for x in deals if x["entry"] in (1, 2)]


def local(s):
    return (datetime.strptime(s, "%Y-%m-%d %H:%M:%S") + timedelta(hours=3)).strftime("%H:%M:%S")


linhas = []
for s in saidas:
    e = entradas.get(s["position_id"])
    if not e:
        continue
    c = s["comment"]
    if c.startswith("[tp"):
        tipo = "TP"
    elif c.startswith("[sl"):
        tipo = "SL"
    else:
        tipo = "OUTRO:" + c
    pts = round(s["profit"] / 10.0, 2)
    linhas.append({
        "pos": s["position_id"],
        "lado": e["type"],
        "hora_ent": local(e["servidor"]),
        "hora_sai": local(s["servidor"]),
        "entrada": e["price"],
        "saida": s["price"],
        "pts": pts,
        "tipo": tipo,
        "comentario_saida": c,
    })

linhas.sort(key=lambda x: x["hora_sai"])

print(f"{'#':>2} {'lado':>4} {'ent':>6} {'sai':>6} {'entrada':>8} {'saida':>8} {'pts':>7}  tipo")
for i, t in enumerate(linhas, 1):
    print(f"{i:>2} {t['lado']:>4} {t['hora_ent']:>6} {t['hora_sai']:>6} "
          f"{t['entrada']:>8.1f} {t['saida']:>8.1f} {t['pts']:>7.2f}  {t['tipo']}")

print()
print("comentarios distintos de saida:")
from collections import Counter
for k, v in Counter(t["comentario_saida"] for t in linhas).most_common():
    print(f"  {v:>2}x  {k!r}")

json.dump(linhas, open(r"C:\AIOFEN\logs\_autopsia_17_11_trades_local.json", "w", encoding="utf-8"),
          ensure_ascii=True, indent=1)
print("\nOK -> logs\\_autopsia_17_11_trades_local.json")
