# -*- coding: utf-8 -*-
"""
backtest_6p_contrafactual.py — Backtest PROXY da estrategia 6P (Hermann Greb).
Sem ticks gravados: reconstruct 6P boxes a partir de WDO$ M5 (OHLC + tick_volume)
e D1. Duas premissas de caminho intrabar (HL: high antes de low; LH: low antes de
high) -> banda de sensibilidade. Roda apenas como decisao de subir ou nao o
coletor 6P ao vivo; dados reais validam depois.

Spec (Hermann Greb / usuario):
  box 6P fecha quando |preco - open_box| >= 6.0; pavios; EMA9/EMA21 nos CLOSES dos
  boxes; crossover = batida (K=1, += por box); entrada so com K<=2; COMPRA:
  ema9>ema21 e close>vwap e close>ajuste[proxy D1 ant] e pavio_inf>=0.35; VENDA
  espelhada; SL extremidade do pavio +-0.5 (bloquear >4.5); parcial +2.5 (0.5 lote,
  SL -> breakeven); resto +6.0; fechamento forcado no fim do dia.
Friction WDO R$0,80/lote/trade. 1 pt = R$10/lote.
"""
import os
import json
import numpy as np
from datetime import datetime, timezone

BASE = r"C:\AIOFEN"
SYM = "WDO$"
START = datetime(2026, 7, 29)
END = datetime(2026, 10, 3)
BOX, PARC, TP_F, SL_M, MAX_SL, MIN_PAVIO, FRIC = 6.0, 2.5, 6.0, 0.5, 4.5, 0.35, 0.80


def load_rates():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5 nao inicializou")
    r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M5, START, END)
    d1 = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_D1, datetime(2026, 7, 1), END)
    mt5.shutdown()
    return r, d1


def build_boxes(r5, ordering):
    t = r5["time"].astype(np.int64); o = r5["open"].astype(float)
    h = r5["high"].astype(float); l = r5["low"].astype(float); c = r5["close"].astype(float)
    boxes, cur, lst = [], None, None
    for i in range(len(r5)):
        day = datetime.fromtimestamp(int(t[i]), timezone.utc).date()
        if day != lst:
            cur, lst = None, day
        path = [o[i], h[i], l[i], c[i]] if ordering == "HL" else [o[i], l[i], h[i], c[i]]
        for p in path:
            if cur is None:
                cur = {"open": p, "high": p, "low": p}
            cur["high"] = max(cur["high"], p); cur["low"] = min(cur["low"], p)
            disp = p - cur["open"]
            if disp >= BOX or disp <= -BOX:
                cl = cur["open"] + (BOX if disp >= BOX else -BOX)
                boxes.append({"open": cur["open"], "high": max(cur["high"], cl),
                              "low": min(cur["low"], cl), "close": cl,
                              "day": day, "t": int(t[i])})
                cur = {"open": cl, "high": cl, "low": cl}
    return boxes


def emas(closes):
    def ema(n):
        out, p = [], None
        for v in closes:
            p = v if p is None else v * (2 / (n + 1)) + p * (1 - 2 / (n + 1))
            out.append(p)
        return np.array(out)
    return ema(9), ema(21)


def zones_diarias(d1):
    out = {}
    for i in range(len(d1)):
        day = datetime.fromtimestamp(int(d1["time"][i]), timezone.utc).date()
        out[day] = {"fech_prev": float(d1["close"][i - 1]) if i else None,
                    "abertura": float(d1["open"][i])}
    return out


def vwap_por_dia(r5):
    t = r5["time"].astype(np.int64); h = r5["high"].astype(float)
    l = r5["low"].astype(float); c = r5["close"].astype(float); tv = r5["tick_volume"].astype(float)
    acc = {}
    for i in range(len(r5)):
        day = datetime.fromtimestamp(int(t[i]), timezone.utc).date()
        s = acc.setdefault(day, [0.0, 0.0])
        s[0] += (h[i] + l[i] + c[i]) / 3.0 * tv[i]; s[1] += tv[i]
    return {d: (s[0] / s[1]) for d, s in acc.items()}


def resolve(pos, bt, H, L, C):
    """Resolve a posicao a partir da barra bt. Retorna dict de trade quando fechada."""
    seq = [H, L] if pos["ord"] == "HL" else [L, H]
    pnl_acc = 0.0
    j = bt
    while j < len(H):
        # testa os dois extremos do candle na ordem da premissa
        for e in (seq[0][j], seq[1][j]):
            if pos["side"] == "BUY":
                if pos["step"] == 0 and e >= pos["par"]:
                    pnl_acc += 0.5 * PARC
                    pos["step"] = 1; pos["lot_rem"] = 0.5; pos["sl"] = pos["entry"]
                if pos["step"] == 1 and e >= pos["tp"]:
                    pnl_acc += 0.5 * TP_F; pos["lot_rem"] = 0; break
                if e <= pos["sl"]:
                    pnl_acc += (pos["sl"] - pos["entry"]) * pos["lot_rem"]; pos["lot_rem"] = 0; break
            else:
                if pos["step"] == 0 and e <= pos["par"]:
                    pnl_acc += 0.5 * PARC
                    pos["step"] = 1; pos["lot_rem"] = 0.5; pos["sl"] = pos["entry"]
                if pos["step"] == 1 and e <= pos["tp"]:
                    pnl_acc += 0.5 * TP_F; pos["lot_rem"] = 0; break
                if e >= pos["sl"]:
                    pnl_acc += (pos["entry"] - pos["sl"]) * pos["lot_rem"]; pos["lot_rem"] = 0; break
        if pos["lot_rem"] <= 0:
            return {"side": pos["side"], "pnl_pts": pnl_acc, "exit": "orders"}
        j += 1
    # fim da serie: EOD
    return {"side": pos["side"], "pnl_pts": pnl_acc, "exit": "EOD"}


def run(ordering, r5, d1, min_pavio=MIN_PAVIO, k_max=2, need_loc=True):
    bt = r5["time"].astype(np.int64)
    H = r5["high"].astype(float); L = r5["low"].astype(float); C = r5["close"].astype(float)
    boxes = build_boxes(r5, ordering)
    closes = np.array([b["close"] for b in boxes])
    ef, es = emas(closes)
    zones, vwapd = zones_diarias(d1), vwap_por_dia(r5)

    trades, K, pos = [], 0, None
    for i, b in enumerate(boxes):
        if i >= 1:
            cu = (ef[i - 1] <= es[i - 1] and ef[i] > es[i])
            cd = (ef[i - 1] >= es[i - 1] and ef[i] < es[i])
            K = 1 if (cu or cd) else K + 1
        else:
            K = 0

        if pos is not None:
            if pos["day"] != b["day"]:
                trades.append({"side": pos["side"], "pnl_pts": pos["pnl_acc"], "exit": "EOD"})
                pos = None
            else:
                tr = resolve(pos, pos["bt"], H, L, C)
                if tr is not None:
                    trades.append(tr); pos = None

        if pos is not None:
            continue
        if i < 22:
            continue
        z = zones.get(b["day"]); vw = vwapd.get(b["day"])
        if z is None or z["fech_prev"] is None or vw is None:
            continue
        rng = b["high"] - b["low"]
        if rng <= 0:
            continue
        psup = (b["high"] - max(b["open"], b["close"])) / rng
        pinf = (min(b["open"], b["close"]) - b["low"]) / rng
        if ef[i] > es[i]:
            side, pav = "BUY", pinf
            sl = b["low"] - SL_M
            loc = (not need_loc) or (b["close"] > vw and b["close"] > z["fech_prev"])
        else:
            side, pav = "SELL", psup
            sl = b["high"] + SL_M
            loc = (not need_loc) or (b["close"] < vw and b["close"] < z["fech_prev"])
        if not (pav >= min_pavio and loc and K <= k_max):
            continue
        if abs(b["close"] - sl) > MAX_SL:
            continue
        bstart = int(np.searchsorted(bt, b["t"])) + 1
        pos = {"side": side, "entry": b["close"], "sl": sl, "day": b["day"],
               "par": b["close"] + PARC if side == "BUY" else b["close"] - PARC,
               "tp": b["close"] + TP_F if side == "BUY" else b["close"] - TP_F,
               "bt": max(bstart, 0), "ord": ordering, "step": 0, "lot_rem": 1.0, "pnl_acc": 0.0,
               "t0_bar": b["t"]}
    if pos is not None:
        trades.append({"side": pos["side"], "pnl_pts": pos["pnl_acc"], "exit": "EOD"})
    return trades


def main():
    import sys
    r5, d1 = load_rates()
    if r5 is None or d1 is None:
        print("ERRO: sem dados"); return
    print("M5:", len(r5), "| D1:", len(d1))
    if "sens" in sys.argv:
        print("\n== SENSIBILIDADE (exploratorio - densidade do sinal) ==")
        for mp in [0.35, 0.25, 0.20, 0.15]:
            for km in [2, 5, 999]:
                for loc in [True, False]:
                    row = []
                    for ord_ in ["HL", "LH"]:
                        tr = run(ord_, r5, d1, min_pavio=mp, k_max=km, need_loc=loc)
                        pts = np.array([t["pnl_pts"] for t in tr])
                        row.append((len(tr), round(float(pts.mean()), 2) if len(pts) else None))
                    print("pavio=%.2f K<=%d loc=%d -> HL=%s LH=%s" % (mp, km, int(loc), row[0], row[1]))
        return
    out = {}
    for ordering in ["HL", "LH"]:
        trades = run(ordering, r5, d1)
        if not trades:
            print(ordering, "-> sem trades"); continue
        pts = np.array([t["pnl_pts"] for t in trades])
        wins = pts[pts > 0]; losses = pts[pts <= 0]
        pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
        rs = pts.sum() * 10.0 - FRIC * len(trades)
        out[ordering] = {"n": int(len(pts)), "pnl_medio_pts": round(float(pts.mean()), 3),
                         "total_RS": round(float(rs), 2), "win_pct": round(100 * float(np.mean(pts > 0)), 1),
                         "pf": round(float(pf), 2)}
        print("%s -> n=%d pnl_medio=%+.3f pts | R$ total %+.2f | WR %.1f%% | PF %.2f" % (
            ordering, len(pts), pts.mean(), rs, 100 * np.mean(pts > 0), pf))
    with open(os.path.join(BASE, "logs", "backtest_6p_resumo.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("salvo logs/backtest_6p_resumo.json")


if __name__ == "__main__":
    main()