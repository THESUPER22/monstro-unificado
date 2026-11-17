"""Pre-autopsia 17/11/2026 - SOMENTE LEITURA (MT5 + arquivos).

Nao altera nada: apenas le posicoes, deals, candles e estado do terminal.
Saida em JSON ascii para evitar problemas de encoding no console.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import MetaTrader5 as mt5

OUT = r"C:\AIOFEN\logs\_autopsia_17_11_mt5.json"
SYMBOL = "WDOZ26"
MAGIC = 123456

res = {"agora_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

if not mt5.initialize():
    res["erro"] = f"initialize falhou: {mt5.last_error()}"
    print(json.dumps(res, ensure_ascii=True, indent=1))
    raise SystemExit(1)

ti = mt5.terminal_info()
ai = mt5.account_info()
res["terminal"] = {
    "conectado": bool(ti.connected) if ti else None,
    "conta": ai.login if ai else None,
    "servidor": ai.server if ai else None,
    "trade_allowed": bool(ti.trade_allowed) if ti else None,
}

# ---- posicoes abertas agora ----
pos = mt5.positions_get() or []
res["posicoes"] = [
    {
        "ticket": p.ticket, "symbol": p.symbol, "type": "BUY" if p.type == 0 else "SELL",
        "volume": p.volume, "magic": p.magic, "open": p.price_open,
        "sl": p.sl, "tp": p.tp, "atual": p.price_current, "profit": p.profit,
        "comentario": p.comment,
        "aberta_servidor": datetime.fromtimestamp(p.time).strftime("%Y-%m-%d %H:%M:%S"),
    }
    for p in pos
]

# ---- deals de hoje (janela ampla; o servidor esta em UTC-3 do local) ----
ini = datetime.now() - timedelta(days=2)
fim = datetime.now() + timedelta(days=1)
deals = mt5.history_deals_get(ini, fim) or []
hoje = datetime.now().date()
sel = []
for d in deals:
    dt = datetime.fromtimestamp(d.time)
    if d.symbol != SYMBOL and d.magic != MAGIC:
        continue
    sel.append({
        "ticket": d.ticket, "position_id": d.position_id, "magic": d.magic,
        "symbol": d.symbol, "entry": d.entry,  # 0=in,1=out,2=inout
        "type": "BUY" if d.type == 0 else "SELL",
        "volume": d.volume, "price": d.price, "profit": d.profit,
        "commission": d.commission, "swap": d.swap, "fee": d.fee,
        "comment": d.comment,
        "servidor": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "dia_local": dt.strftime("%Y-%m-%d"),
    })

por_dia = {}
for d in sel:
    por_dia.setdefault(d["dia_local"], []).append(d)
res["deals_por_dia"] = {k: len(v) for k, v in sorted(por_dia.items())}

hoje_deals = [d for d in sel if d["dia_local"] == hoje.strftime("%Y-%m-%d")]
res["deals_hoje"] = hoje_deals
res["resumo_hoje"] = {
    "n_deals": len(hoje_deals),
    "n_saidas": sum(1 for d in hoje_deals if d["entry"] in (1, 2)),
    "n_entradas": sum(1 for d in hoje_deals if d["entry"] == 0),
    "bruto": round(sum(d["profit"] for d in hoje_deals), 2),
    "comissao": round(sum(d["commission"] for d in hoje_deals), 2),
    "swap": round(sum(d["swap"] for d in hoje_deals), 2),
    "fee": round(sum(d["fee"] for d in hoje_deals), 2),
}

# ---- o dia no simbolo ----
si = mt5.symbol_info(SYMBOL)
if si:
    res["simbolo"] = {
        "bid": si.bid, "ask": si.ask, "spread": si.spread, "point": si.point,
        "digits": si.digits, "stops_level": si.trade_stops_level,
        "freeze": si.trade_freeze_level,
        "session_deals": getattr(si, "session_deals", None),
        "volume_min": getattr(si, "volume_min", None),
        "volume_max": getattr(si, "volume_max", None),
    }

# D1 de hoje e de ontem
d1 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_D1,
                          datetime.now() - timedelta(days=6),
                          datetime.now() + timedelta(days=1))
if d1 is None: d1 = []
res["d1"] = [
    {
        "dia": datetime.fromtimestamp(int(r["time"])).strftime("%Y-%m-%d"),
        "open": float(r["open"]), "high": float(r["high"]),
        "low": float(r["low"]), "close": float(r["close"]),
        "range": round(float(r["high"]) - float(r["low"]), 1),
        "drift": round(float(r["close"]) - float(r["open"]), 1),
        "tick_volume": int(r["tick_volume"]),
    }
    for r in d1
]

# M1 de hoje: caminho intraday, para medir direcionalidade real
m1 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1,
                          datetime.now().replace(hour=0, minute=0, second=0),
                          datetime.now() + timedelta(minutes=1))
if m1 is None: m1 = []
if len(m1):
    o = float(m1[0]["open"])
    c = float(m1[-1]["close"])
    hi = max(float(r["high"]) for r in m1)
    lo = min(float(r["low"]) for r in m1)
    # eficiencia direcional: |close-open| / soma dos movimentos absolutos
    soma_abs = sum(abs(float(m1[i]["close"]) - float(m1[i]["open"])) for i in range(len(m1)))
    soma_close = sum(abs(float(m1[i]["close"]) - float(m1[i - 1]["close"]))
                     for i in range(1, len(m1)))
    res["m1"] = {
        "n_barras": len(m1),
        "primeira": datetime.fromtimestamp(int(m1[0]["time"])).strftime("%H:%M"),
        "ultima": datetime.fromtimestamp(int(m1[-1]["time"])).strftime("%H:%M"),
        "open": o, "high": hi, "low": lo, "close": c,
        "range": round(hi - lo, 1),
        "drift": round(c - o, 1),
        "soma_abs_barra": round(soma_abs, 1),
        "soma_abs_close": round(soma_close, 1),
        "eficiencia": round(abs(c - o) / soma_close, 4) if soma_close else None,
    }

mt5.shutdown()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=True, indent=1)
print(json.dumps({k: res[k] for k in ("agora_local", "terminal", "resumo_hoje", "posicoes")},
                 ensure_ascii=True, indent=1))
print("JSON completo:", OUT)
