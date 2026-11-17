"""Historico LIVE do Sniper %R: quantas entradas por dia nos logs e P&L do dia no MT5.

SOMENTE LEITURA. Objetivo: sair da amostra de 2 dias.
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta

import MetaTrader5 as mt5

BASE = r"C:\AIOFEN"
SYMBOL = "WDOZ26"
MAGIC = 123456

# ---------- 1) logs: entradas SNIPER por dia ----------
pat_dia = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]")
pat_sniper = re.compile(r"SNIPER %R INICIA (BUY|SELL)")
pat_reg = re.compile(r"SNIPER %R \| wr=(-?\d+)")

logs = sorted(glob.glob(os.path.join(BASE, "monstro_wdo_*.log"))) + [os.path.join(BASE, "monstro_wdo.log")]
por_dia = {}
for p in logs:
    if not os.path.exists(p):
        continue
    for linha in io.open(p, encoding="utf-8", errors="replace"):
        m = pat_dia.match(linha)
        if not m:
            continue
        dia = m.group(1)
        d = por_dia.setdefault(dia, {"sniper_buy": 0, "sniper_sell": 0, "sniper_sinal": 0})
        if pat_sniper.search(linha):
            if "BUY" in linha:
                d["sniper_buy"] += 1
            else:
                d["sniper_sell"] += 1
        if pat_reg.search(linha):
            d["sniper_sinal"] += 1

# ---------- 2) MT5: P&L por dia ----------
mt5.initialize()
ini = datetime.now() - timedelta(days=45)
fim = datetime.now() + timedelta(days=1)
deals = mt5.history_deals_get(ini, fim)
mt5.shutdown()

pl_dia = {}
n_dia = {}
if deals is not None:
    for dl in deals:
        if dl.symbol != SYMBOL or dl.magic != MAGIC or dl.entry not in (1, 2):
            continue
        k = datetime.fromtimestamp(dl.time).strftime("%Y-%m-%d")
        pl_dia[k] = pl_dia.get(k, 0.0) + dl.profit
        n_dia[k] = n_dia.get(k, 0) + 1

print(f"{'dia':>12} {'snip_B':>7} {'snip_S':>7} {'saidas':>7} {'P&L R$':>9} {'pts':>8}")
tot = 0.0
dias_pos = dias_neg = 0
for dia in sorted(set(por_dia) | set(pl_dia)):
    s = por_dia.get(dia, {})
    pl = pl_dia.get(dia, 0.0)
    if dia in pl_dia:
        tot += pl
        if pl > 0:
            dias_pos += 1
        elif pl < 0:
            dias_neg += 1
    print(f"{dia:>12} {s.get('sniper_buy',0):>7} {s.get('sniper_sell',0):>7} "
          f"{n_dia.get(dia,0):>7} {pl:>9.2f} {pl/10:>8.1f}")

print()
print(f"total R$ {tot:.2f} | pts {tot/10:.1f} | dias +{dias_pos} / -{dias_neg}")

res = {"por_dia": {k: {"logs": por_dia.get(k, {}), "pl_rs": pl_dia.get(k, 0.0),
                       "saidas": n_dia.get(k, 0)} for k in sorted(set(por_dia) | set(pl_dia))},
       "total_rs": round(tot, 2), "dias_pos": dias_pos, "dias_neg": dias_neg}
json.dump(res, open(os.path.join(BASE, "logs", "_autopsia_17_11_historico.json"), "w",
                    encoding="utf-8"), ensure_ascii=True, indent=1)
print("OK -> logs\\_autopsia_17_11_historico.json")
