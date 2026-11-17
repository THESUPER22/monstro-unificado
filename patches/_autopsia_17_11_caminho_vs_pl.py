"""Cruza o 'caminho' (M1) de cada dia LIVE com o P&L do dia.

Se o caminho/amplitude explicar os dias bons e ruins, temos um filtro candidato.
SOMENTE LEITURA.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import MetaTrader5 as mt5

SYMBOL = "WDOZ26"
MAGIC = 123456

# P&L por dia (de _autopsia_17_11_historico.json)
h = json.load(open(r"C:\AIOFEN\logs\_autopsia_17_11_historico.json", encoding="utf-8"))
pl = {k: v["pl_rs"] for k, v in h["por_dia"].items() if v["saidas"] > 0}
n_tr = {k: v["saidas"] for k, v in h["por_dia"].items() if v["saidas"] > 0}

mt5.initialize()
r = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1,
                         datetime(2026, 10, 30), datetime(2026, 11, 18))
mt5.shutdown()
if r is None or len(r) == 0:
    print("sem dados")
    raise SystemExit(1)


def local(ts):
    return datetime.fromtimestamp(int(ts)) + timedelta(hours=3)


por_dia = {}
for row in r:
    t = local(row["time"])
    ini = datetime(t.year, t.month, t.day, 9, 0)
    fim = datetime(t.year, t.month, t.day, 17, 30)
    if ini <= t <= fim:
        por_dia.setdefault(t.strftime("%Y-%m-%d"), []).append(row)

linhas = []
print(f"{'dia':>12} {'range':>7} {'drift':>7} {'caminho':>8} {'efic':>8} {'c/r':>6} "
      f"{'tr':>3} {'P&L R$':>9} {'pts/tr':>7}")
for dia in sorted(pl):
    rows = por_dia.get(dia)
    if not rows:
        print(f"{dia:>12}   (sem M1)")
        continue
    o = float(rows[0]["open"])
    c = float(rows[-1]["close"])
    hi = max(float(x["high"]) for x in rows)
    lo = min(float(x["low"]) for x in rows)
    cam = sum(abs(float(rows[i]["close"]) - float(rows[i - 1]["close"])) for i in range(1, len(rows)))
    n = n_tr[dia]
    linhas.append({
        "dia": dia, "range": round(hi - lo, 1), "drift": round(c - o, 1),
        "caminho": round(cam, 1),
        "eficiencia": round(abs(c - o) / cam, 5) if cam else None,
        "cam_por_range": round(cam / (hi - lo), 2) if hi > lo else None,
        "trades": n, "pl_rs": pl[dia], "pts_por_trade": round(pl[dia] / 10 / n, 2),
    })
    print(f"{dia:>12} {hi-lo:>7.1f} {c-o:>7.1f} {cam:>8.1f} "
          f"{(abs(c-o)/cam if cam else 0):>8.5f} {(cam/(hi-lo) if hi>lo else 0):>6.2f} "
          f"{n:>3} {pl[dia]:>9.2f} {pl[dia]/10/n:>7.2f}")

# correlacao caminho vs pts/trade
xs = [l["caminho"] for l in linhas]
ys = [l["pts_por_trade"] for l in linhas]
if len(xs) > 2:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    print(f"\ncorrelacao(caminho, pts/trade) = {num/den:+.3f}   n={len(xs)}")

# medias por metade de caminho
med = sorted(linhas, key=lambda l: l["caminho"])
k = len(med) // 2
baixo, alto = med[:k], med[k:]
for nome, g in (("caminho BAIXO", baixo), ("caminho ALTO", alto)):
    tot = sum(x["pl_rs"] for x in g)
    tr = sum(x["trades"] for x in g)
    print(f"{nome}: n_dias={len(g)} caminho_med={sum(x['caminho'] for x in g)/len(g):.0f} "
          f"P&L={tot:+.2f} trades={tr} pts/trade={tot/10/tr:+.2f}")

json.dump(linhas, open(r"C:\AIOFEN\logs\_autopsia_17_11_caminho_vs_pl.json", "w", encoding="utf-8"),
          ensure_ascii=True, indent=1)
print("\nOK -> logs\\_autopsia_17_11_caminho_vs_pl.json")
