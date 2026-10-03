# -*- coding: utf-8 -*-
"""
backtest_6p_herman.py — Backtest DEFINITIVO da ESTRATEGIA DO HERMAN.
Le logs/herman_6p/boxes_herman.csv (boxes 6P REAIS gravados pelo coletor em
shadow) e aplica os filtros do spec + simulacao de saída (parcial +2.5 ->
breakeven -> TP 6.0 / SL 0.5 alem do pavio; bloqueio se SL > 4.5), sob a banda
de caminho intrabox HL/LH (ordem high/low desconhecida).

Redescobre os sinais a partir dos boxes (nao confia na coluna "sinal" do
coletor) -> funciona como auditoria do bookkeeping + backtest.

Uso: python backtest_6p_herman.py [--csv CAMINHO] [--sens]
"""
import os
import sys
import csv
import json
import argparse
import numpy as np

BASE = r"C:\AIOFEN"
DEFAULT_CSV = os.path.join(BASE, "logs", "herman_6p", "boxes_herman.csv")
MIN_PAVIO, K_MAX, SL_M, MAX_SL, PARC, TP_F, FRIC, BOX = 0.35, 2, 0.5, 4.5, 2.5, 6.0, 0.80, 6.0


def load_boxes(csv_path, box_pts=None):
    """Lê boxes_herman.csv. Aceita coluna 'box_pts' (coletor dual 6P/3P) e
    filtro por tamanho (ex.: --box 6 lê só os 6P); CSVs antigos sem a coluna
    também são aceitos."""
    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        tem = "box_pts" in (rd.fieldnames or [])
        for r in rd:
            if tem and box_pts is not None and int(float(r["box_pts"])) != box_pts:
                continue
            try:
                rows.append({
                    "day": r["day"], "t": r["ts"],
                    "open": float(r["open"]), "high": float(r["high"]),
                    "low": float(r["low"]), "close": float(r["close"]),
                    "vwap": (float(r["vwap"]) if r.get("vwap") else None),
                    "ajuste": (float(r["ajuste"]) if r.get("ajuste") else None),
                })
            except (TypeError, ValueError):
                continue
    return rows


def emas(closes):
    def ema(n):
        out, p = [], None
        for v in closes:
            p = v if p is None else v * (2 / (n + 1)) + p * (1 - 2 / (n + 1))
            out.append(p)
        return np.array(out)
    return ema(9), ema(21)


def run(boxes, ordering, min_pavio=MIN_PAVIO, k_max=K_MAX, max_sl=MAX_SL):
    if len(boxes) < 23:
        return [], len(boxes)
    H = np.array([b["high"] for b in boxes])
    L = np.array([b["low"] for b in boxes])
    C = np.array([b["close"] for b in boxes])
    ef, es = emas(C)
    seq = [H, L] if ordering == "HL" else [L, H]
    trades, K = [], 0
    pos = None
    for i, b in enumerate(boxes):
        if i >= 1:
            cu = (ef[i - 1] <= es[i - 1] and ef[i] > es[i])
            cd = (ef[i - 1] >= es[i - 1] and ef[i] < es[i])
            K = 1 if (cu or cd) else K + 1
        # resolve posicao ativa
        if pos is not None:
            if b["day"] != pos["day"]:
                trades.append({"side": pos["side"], "pnl_pts": pos["pnl"], "exit": "EOD"})
                pos = None
            else:
                pnl_acc = pos["pnl"]
                fechou = False
                for e in (seq[0][i], seq[1][i]):
                    if pos["side"] == "BUY":
                        if pos["step"] == 0 and e >= pos["par"]:
                            pnl_acc += 0.5 * PARC
                            pos["step"], pos["sl"] = 1, pos["entry"]
                        if pos["step"] == 1 and e >= pos["tp"]:
                            pnl_acc += 0.5 * TP_F
                            fechou = True
                            break
                        if e <= pos["sl"]:
                            pnl_acc += (pos["sl"] - pos["entry"]) * pos["lot_rem"]
                            fechou = True
                            break
                    else:
                        if pos["step"] == 0 and e <= pos["par"]:
                            pnl_acc += 0.5 * PARC
                            pos["step"], pos["sl"] = 1, pos["entry"]
                        if pos["step"] == 1 and e <= pos["tp"]:
                            pnl_acc += 0.5 * TP_F
                            fechou = True
                            break
                        if e >= pos["sl"]:
                            pnl_acc += (pos["entry"] - pos["sl"]) * pos["lot_rem"]
                            fechou = True
                            break
                if fechou:
                    trades.append({"side": pos["side"], "pnl_pts": pnl_acc, "exit": "orders"})
                    pos = None
                else:
                    pos["pnl"] = pnl_acc
        if pos is not None:
            continue
        if i < 22:
            continue
        if b["vwap"] is None or b["ajuste"] is None:
            continue
        rng = b["high"] - b["low"]
        if rng <= 0:
            continue
        psup = (b["high"] - max(b["open"], b["close"])) / rng
        pinf = (min(b["open"], b["close"]) - b["low"]) / rng
        if ef[i] > es[i]:
            side, pav = "BUY", pinf
            sl = b["low"] - SL_M
            loc = b["close"] > b["vwap"] and b["close"] > b["ajuste"]
        else:
            side, pav = "SELL", psup
            sl = b["high"] + SL_M
            loc = b["close"] < b["vwap"] and b["close"] < b["ajuste"]
        if not (pav >= min_pavio and loc and K <= k_max):
            continue
        if abs(b["close"] - sl) > max_sl:
            continue
        pos = {"side": side, "entry": b["close"], "sl": sl, "day": b["day"],
               "par": b["close"] + PARC if side == "BUY" else b["close"] - PARC,
               "tp": b["close"] + TP_F if side == "BUY" else b["close"] - TP_F,
               "step": 0, "lot_rem": 1.0, "pnl": 0.0}
    if pos is not None:
        trades.append({"side": pos["side"], "pnl_pts": pos["pnl"], "exit": "EOD"})
    return trades, len(boxes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--box", type=int, default=None, help="filtrar por tamanho de box (6 ou 3); default = todos")
    ap.add_argument("--sens", action="store_true")
    ap.add_argument("--max-sl", type=float, default=MAX_SL, help="distancia maxima ao SL (default 4.5)")
    ap.add_argument("--pavio", type=float, default=MIN_PAVIO)
    ap.add_argument("--k-max", type=int, default=K_MAX)
    a = ap.parse_args()
    boxes = load_boxes(a.csv, a.box)
    print("boxes carregados:", len(boxes), "| fonte:", a.csv, "| box:", a.box,
          "| max-sl=%.1f pavio=%.2f k<=%d" % (a.max_sl, a.pavio, a.k_max))
    if not boxes:
        print("SEM DADOS ainda — rode o coletor_herman_6p_shadow.py no pregao para gerar boxes reais.")
        return
    dias = sorted(set(b["day"] for b in boxes))
    print("periodo:", dias[0], "a", dias[-1], "| sessoes:", len(dias))
    if a.sens:
        for mp in [0.35, 0.25, 0.20]:
            for km in [2, 5]:
                linha = []
                for ord_ in ["HL", "LH"]:
                    tr, _ = run(boxes, ord_, mp, km, a.max_sl)
                    pts = [t["pnl_pts"] for t in tr]
                    linha.append((len(tr), round(float(np.mean(pts)), 2) if pts else None))
                print("pavio=%.2f K<=%d -> HL=%s LH=%s" % (mp, km, linha[0], linha[1]))
        return
    resumo = {}
    for ord_ in ["HL", "LH"]:
        tr, nb = run(boxes, ord_, a.pavio, a.k_max, a.max_sl)
        if not tr:
            print(ord_, "-> sem trades"); continue
        pts = np.array([t["pnl_pts"] for t in tr])
        wins = pts[pts > 0]; losses = pts[pts <= 0]
        pf = wins.sum() / abs(losses.sum()) if losses.sum() else float("inf")
        rs = pts.sum() * 10.0 - FRIC * len(tr)
        resumo[ord_] = {"n": int(len(pts)), "pnl_medio_pts": round(float(pts.mean()), 3),
                        "total_RS": round(float(rs), 2), "win_pct": round(100 * float(np.mean(pts > 0)), 1),
                        "pf": round(float(pf), 2)}
        print("%s -> n=%d pnl_medio=%+.3f pts | R$ %+.2f | WR %.1f%% | PF %.2f" % (
            ord_, len(pts), pts.mean(), rs, 100 * np.mean(pts > 0), pf))
    if resumo:
        with open(os.path.join(BASE, "logs", "herman_6p", "resumo_herman_backtest.json"), "w",
                  encoding="utf-8") as f:
            json.dump(resumo, f, ensure_ascii=False, indent=2)
        print("salvo logs/herman_6p/resumo_herman_backtest.json")


if __name__ == "__main__":
    main()