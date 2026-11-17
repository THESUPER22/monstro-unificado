"""Testa um filtro COMPUTAVEL EM TEMPO REAL: caminho/ATR dos 60 min antes da entrada.

Para cada posicao fechada (magic 123456, WDOZ26):
  - hora de abertura (hora local)
  - caminho (soma |close-close| M1) dos 60 min anteriores
  - range dos 60 min anteriores
  - ATR14 do M1
  - resultado em pontos

Depois: correlacao e medias por tercil.
SOMENTE LEITURA. Hipotese, nao prova: n pequeno e descoberto in-sample.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import MetaTrader5 as mt5

SYMBOL = "WDOZ26"
MAGIC = 123456

mt5.initialize()
deals = mt5.history_deals_get(datetime(2026, 11, 1), datetime.now() + timedelta(days=1))
if deals is None:
    print("sem deals:", mt5.last_error())
    raise SystemExit(1)

ent = {}
sai = {}
for d in deals:
    if d.symbol != SYMBOL or d.magic != MAGIC:
        continue
    if d.entry == 0:
        ent[d.position_id] = d
    elif d.entry in (1, 2):
        sai[d.position_id] = d

r = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, datetime(2026, 10, 31), datetime.now() + timedelta(days=1))
mt5.shutdown()
if r is None or len(r) == 0:
    print("sem M1")
    raise SystemExit(1)

# barras em hora local
bars = [(datetime.fromtimestamp(int(x["time"])) + timedelta(hours=3),
         float(x["open"]), float(x["high"]), float(x["low"]), float(x["close"])) for x in r]

def janela(t_ini, t_fim):
    return [b for b in bars if t_ini <= b[0] <= t_fim]

linhas = []
for pid, e in ent.items():
    s = sai.get(pid)
    if not s:
        continue
    t = datetime.fromtimestamp(e.time) + timedelta(hours=3)
    w = janela(t - timedelta(minutes=60), t)
    if len(w) < 20:
        continue
    cam = sum(abs(w[i][4] - w[i - 1][4]) for i in range(1, len(w)))
    hi = max(b[2] for b in w)
    lo = min(b[3] for b in w)
    trs = [b[2] - b[3] for b in w]
    atr = sum(trs[-14:]) / min(14, len(trs))
    pts = round(s.profit / 10.0, 2)
    linhas.append({
        "dia": t.strftime("%Y-%m-%d"), "hora": t.strftime("%H:%M"),
        "lado": "BUY" if e.type == 0 else "SELL", "pts": pts,
        "cam60": round(cam, 1), "range60": round(hi - lo, 1),
        "atr14": round(atr, 2), "cam_por_range60": round(cam / (hi - lo), 2) if hi > lo else None,
        "tipo": "TP" if s.comment.startswith("[tp") else "SL",
    })

linhas.sort(key=lambda x: (x["dia"], x["hora"]))
print(f"n trades com janela valida: {len(linhas)}")

def corr(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return num / den if den else None

ys = [l["pts"] for l in linhas]
for feat in ("cam60", "range60", "atr14"):
    xs = [l[feat] for l in linhas]
    print(f"corr({feat}, pts) = {corr(xs, ys):+.3f}")

# tercis por cam60
ord_ = sorted(linhas, key=lambda l: l["cam60"])
k = len(ord_) // 3
grupos = [("terco BAIXO", ord_[:k]), ("terco MEDIO", ord_[k:2 * k]), ("terco ALTO", ord_[2 * k:])]
print()
for nome, g in grupos:
    if not g:
        continue
    tot = sum(x["pts"] for x in g)
    w = sum(1 for x in g if x["pts"] > 0)
    print(f"{nome}: n={len(g)} cam60_med={sum(x['cam60'] for x in g)/len(g):>6.0f} "
          f"pts={tot:>+8.1f} exp={tot/len(g):>+6.2f} WR={100*w/len(g):>5.1f}%")

# mesmos tercis por atr14
print()
ord2 = sorted(linhas, key=lambda l: l["atr14"])
k2 = len(ord2) // 3
for nome, g in (("ATR BAIXO", ord2[:k2]), ("ATR MEDIO", ord2[k2:2 * k2]), ("ATR ALTO", ord2[2 * k2:])):
    if not g:
        continue
    tot = sum(x["pts"] for x in g)
    w = sum(1 for x in g if x["pts"] > 0)
    print(f"{nome}: n={len(g)} atr_med={sum(x['atr14'] for x in g)/len(g):>5.2f} "
          f"pts={tot:>+8.1f} exp={tot/len(g):>+6.2f} WR={100*w/len(g):>5.1f}%")

json.dump(linhas, open(r"C:\AIOFEN\logs\_autopsia_17_11_filtro_cam60.json", "w", encoding="utf-8"),
          ensure_ascii=True, indent=1)
print("\nOK -> logs\\_autopsia_17_11_filtro_cam60.json")
