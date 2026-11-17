"""Captura o fecho automatico das 17:35 (17/11) - SOMENTE LEITURA.

Espera ate 17:40 local (o fecho comeca 17:35 e leva ~1-3 min) e fotografa:
posicoes, deals finais, logs e arquivos gerados pelo fecho.
"""
from __future__ import annotations

import glob
import io
import json
import os
import time
from datetime import datetime, timedelta

BASE = r"C:\AIOFEN"
ALVO = datetime.now().replace(hour=17, minute=40, second=0, microsecond=0)
while datetime.now() < ALVO:
    time.sleep(10)

import MetaTrader5 as mt5

res = {"capturado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

if mt5.initialize():
    pos = mt5.positions_get() or []
    res["posicoes"] = [
        {"ticket": p.ticket, "symbol": p.symbol, "type": "BUY" if p.type == 0 else "SELL",
         "volume": p.volume, "magic": p.magic, "open": p.price_open,
         "sl": p.sl, "tp": p.tp, "profit": p.profit, "comment": p.comment}
        for p in pos
    ]
    deals = mt5.history_deals_get(datetime.now() - timedelta(hours=1),
                                  datetime.now() + timedelta(minutes=5)) or []
    res["deals_finais"] = [
        {"position_id": d.position_id, "entry": d.entry,
         "type": "BUY" if d.type == 0 else "SELL", "price": d.price,
         "profit": d.profit, "comment": d.comment,
         "servidor": datetime.fromtimestamp(d.time).strftime("%H:%M:%S")}
        for d in deals if d.symbol == "WDOZ26"
    ]
    res["resumo_bruto_rs"] = round(sum(d.profit for d in deals if d.symbol == "WDOZ26"), 2)
    mt5.shutdown()
else:
    res["erro_mt5"] = str(mt5.last_error())

# arquivos tocados depois das 17:30
tocados = []
limite = time.time() - 25 * 60
for p in glob.glob(os.path.join(BASE, "*.log")) + glob.glob(os.path.join(BASE, "logs", "*.log")) \
        + glob.glob(os.path.join(BASE, "*.txt")) + glob.glob(os.path.join(BASE, "logs", "*.txt")):
    try:
        st = os.stat(p)
    except OSError:
        continue
    if st.st_mtime >= limite:
        item = {"arquivo": os.path.relpath(p, BASE), "bytes": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%H:%M:%S")}
        try:
            linhas = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
            item["n_linhas"] = len(linhas)
            item["ultimas"] = linhas[-12:]
        except Exception as e:
            item["erro"] = str(e)
        tocados.append(item)
res["arquivos_tocados"] = tocados

with open(os.path.join(BASE, "logs", "_autopsia_17_11_fecho.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=True, indent=1, default=str)

print("capturado", res["capturado"])
print("posicoes:", len(res.get("posicoes", [])))
print("bruto R$:", res.get("resumo_bruto_rs"))
print("arquivos tocados:", [a["arquivo"] for a in tocados])
