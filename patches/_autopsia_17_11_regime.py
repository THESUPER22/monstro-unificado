"""Compara o 'caminho' de 16/11 e 17/11 (M1, hora local). Somente leitura.

Metrica central: amplitude de oscilacao (soma dos swings) vs deslocamento liquido.
Um setup de exaustao (%R) com SL 8pt / TP ~11pt precisa de swing, nao de tendencia.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import MetaTrader5 as mt5

SYMBOL = "WDOZ26"
mt5.initialize()

# pregões em hora local -> pega faixa ampla e filtra 09:00-17:30 local
ini = datetime(2026, 11, 15, 0, 0)
fim = datetime(2026, 11, 18, 0, 0)
r = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, ini, fim)
mt5.shutdown()

if r is None or len(r) == 0:
    print("sem dados")
    raise SystemExit(1)


def local(ts):
    return datetime.fromtimestamp(int(ts)) + timedelta(hours=3)


por_dia = {}
for row in r:
    t = local(row["time"])
    if not (datetime(t.year, t.month, t.day, 9, 0) <= t <= datetime(t.year, t.month, t.day, 17, 30)):
        continue
    por_dia.setdefault(t.strftime("%Y-%m-%d"), []).append(row)

saida = {}
for dia, rows in sorted(por_dia.items()):
    o = float(rows[0]["open"])
    c = float(rows[-1]["close"])
    hi = max(float(x["high"]) for x in rows)
    lo = min(float(x["low"]) for x in rows)
    soma_barra = sum(abs(float(x["close"]) - float(x["open"])) for x in rows)
    soma_close = sum(abs(float(rows[i]["close"]) - float(rows[i - 1]["close"]))
                     for i in range(1, len(rows)))
    # swings: soma das pernas > 3 pts (filtra ruido de 1-2 pts)
    pernas = []
    ancora = float(rows[0]["open"])
    direcao = 0
    extremo = ancora
    for x in rows:
        h, l, cl = float(x["high"]), float(x["low"]), float(x["close"])
        if direcao >= 0 and h > extremo:
            extremo = h
        if direcao <= 0 and l < extremo:
            extremo = l
        if direcao >= 0 and extremo - cl >= 3.0:
            pernas.append(extremo - cl)
            direcao, extremo = -1, cl
        elif direcao <= 0 and cl - extremo >= 3.0:
            pernas.append(cl - extremo)
            direcao, extremo = 1, cl
    saida[dia] = {
        "n_barras": len(rows),
        "open": o, "high": hi, "low": lo, "close": c,
        "range": round(hi - lo, 1),
        "drift": round(c - o, 1),
        "soma_abs_barra": round(soma_barra, 1),
        "soma_abs_close": round(soma_close, 1),
        "eficiencia": round(abs(c - o) / soma_close, 5) if soma_close else None,
        "caminho_por_range": round(soma_close / (hi - lo), 2) if hi > lo else None,
        "pernas_3pt": len(pernas),
        "soma_pernas": round(sum(pernas), 1),
        "perna_media": round(sum(pernas) / len(pernas), 2) if pernas else None,
        "perna_max": round(max(pernas), 1) if pernas else None,
        "pernas_ge_10pt": sum(1 for p in pernas if p >= 10.0),
        "pernas_ge_8pt": sum(1 for p in pernas if p >= 8.0),
    }

print(f"{'dia':>12} {'range':>7} {'drift':>7} {'caminho':>8} {'efic':>8} {'c/r':>6} "
      f"{'pernas':>7} {'perna_med':>10} {'>=8pt':>6} {'>=10pt':>7}")
for dia, s in saida.items():
    print(f"{dia:>12} {s['range']:>7.1f} {s['drift']:>7.1f} {s['soma_abs_close']:>8.1f} "
          f"{s['eficiencia']:>8.5f} {s['caminho_por_range']:>6.2f} {s['pernas_3pt']:>7} "
          f"{s['perna_media']:>10.2f} {s['pernas_ge_8pt']:>6} {s['pernas_ge_10pt']:>7}")

json.dump(saida, open(r"C:\AIOFEN\logs\_autopsia_17_11_regime.json", "w", encoding="utf-8"),
          ensure_ascii=True, indent=1)
print("\nOK -> logs\\_autopsia_17_11_regime.json")
