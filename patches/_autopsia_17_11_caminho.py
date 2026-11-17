"""Caminho intraday de hoje (M1 -> blocos de 30 min, hora local). Somente leitura."""
from __future__ import annotations

from datetime import datetime, timedelta

import MetaTrader5 as mt5

SYMBOL = "WDOZ26"
mt5.initialize()

ini = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
r = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, ini, datetime.now() + timedelta(minutes=1))
mt5.shutdown()

if r is None or len(r) == 0:
    print("sem dados M1")
    raise SystemExit(1)

# hora local = hora do servidor + 3h
def local(ts):
    return datetime.fromtimestamp(int(ts)) + timedelta(hours=3)

print("barras:", len(r), "| local", local(r[0]["time"]).strftime("%H:%M"),
      "->", local(r[-1]["time"]).strftime("%H:%M"))
print(f"{'bloco':>10} {'open':>8} {'high':>8} {'low':>8} {'close':>8} {'range':>7} {'drift':>7}")
bloco = None
agg = None
for row in r:
    t = local(row["time"])
    b = t.replace(minute=(t.minute // 30) * 30, second=0)
    if b != bloco:
        if agg:
            print(f"{bloco.strftime('%H:%M'):>10} {agg[0]:>8.1f} {agg[1]:>8.1f} "
                  f"{agg[2]:>8.1f} {agg[3]:>8.1f} {agg[1]-agg[2]:>7.1f} {agg[3]-agg[0]:>7.1f}")
        bloco = b
        agg = [float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])]
    else:
        agg[1] = max(agg[1], float(row["high"]))
        agg[2] = min(agg[2], float(row["low"]))
        agg[3] = float(row["close"])
if agg:
    print(f"{bloco.strftime('%H:%M'):>10} {agg[0]:>8.1f} {agg[1]:>8.1f} "
          f"{agg[2]:>8.1f} {agg[3]:>8.1f} {agg[1]-agg[2]:>7.1f} {agg[3]-agg[0]:>7.1f}")

hi = max(r, key=lambda x: x["high"])
lo = min(r, key=lambda x: x["low"])
print("maxima", float(hi["high"]), "as", local(hi["time"]).strftime("%H:%M"),
      "| minima", float(lo["low"]), "as", local(lo["time"]).strftime("%H:%M"))
