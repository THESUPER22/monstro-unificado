# -*- coding: utf-8 -*-
"""
backtest_frankenstein_wdo.py - Frankenstein/Sete Velas no WDO$ com dados completos
(09:00-18:00) e SL ESCALADO para o ativo.

Escalado por volatilidade (ADR): WIN ADR (jan 2025-07-14..2026-07-31) ~2826 pts, WDO ADR ~51 pts.
SL 300 pts no WIN = 300 x 0,20 = R$60  ->  equivalente WDO = 300 * (51/2826) ~ 5 pts (=R$50).
SL padrao = 5 pts WDO (R$10/ponto, 1cc). TP = extremidade oposta da 1a hora (R$ por contrato):
  TP->max(range) em COMPRA; ->min(range) em VENDA. Custo R$0,75/trade. EOD 18:00.
Uso:  python backtest_frankenstein_wdo.py [sl1 sl2 ...]   (default: 5 10 20 40 60)
"""
import csv
import os
import sys
from collections import defaultdict
import pandas as pd

VALOR_PONTO = 10.0
CUSTO = 0.75
RTH_INI_MIN = 9 * 60
RTH_FIM_MIN = 18 * 60
SRC = r"C:\AIOFEN\barras_1min_wdo.csv"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")


def load():
    df = pd.read_csv(SRC, parse_dates=["datetime"])
    rows = []
    for d, o, h, l, c, v in zip(df["datetime"], df["open"], df["high"],
                                df["low"], df["close"], df["tick_volume"]):
        mins = d.hour * 60 + d.minute
        if mins < RTH_INI_MIN or mins >= RTH_FIM_MIN:
            continue
        rows.append((d.to_pydatetime(), float(o), float(h), float(l), float(c), float(v)))
    days = defaultdict(list)
    for r in rows:
        days[r[0].date()].append(r)
    return {d: sorted(v) for d, v in days.items()}


def to_m15(day):
    out = []
    cur = None
    for r in day:
        mm = r[0].hour * 60 + r[0].minute
        bucket = mm - (mm % 15)
        if cur is None or cur[-1] != bucket:
            if cur is not None:
                out.append(cur)
            cur = [bucket, r[1], r[2], r[3], r[4], r[5]]
        else:
            cur[2] = max(cur[2], r[2])
            cur[3] = min(cur[3], r[3])
            cur[4] = r[4]
            cur[5] += r[5]
    if cur is not None:
        out.append(cur)
    return out


def barras_por_bucket(m15):
    return {b[0]: b for b in m15}


def maioria(seis):
    gre = sum(1 for b in seis if b[4] > b[1])
    red = sum(1 for b in seis if b[4] < b[1])
    if gre > red:
        return "V", gre
    if red > gre:
        return "C", red
    return None, None


def resolve(bars, side, sl, tp, entry):
    for b in bars:
        if side == "C":
            if b[3] <= sl:
                return sl - entry
            if b[2] >= tp:
                return tp - entry
        else:
            if b[2] >= sl:
                return entry - sl
            if b[3] <= tp:
                return entry - tp
    if not bars:
        return 0.0
    fec = bars[-1][4]
    return (fec - entry) if side == "C" else (entry - fec)


def frankenstein_dia(dia, m15, sl_pts):
    B = barras_por_bucket(m15)
    range_buckets = [540, 555, 570, 585]
    if not all(b in B for b in range_buckets):
        return {"motivo": "dados_manha_incompletos"}
    hi = max(B[b][2] for b in range_buckets)
    lo = min(B[b][3] for b in range_buckets)
    mid = (hi + lo) / 2
    if hi <= lo:
        return {"motivo": "range_invalido"}
    seis = [540, 555, 570, 585, 600, 615]
    if not all(b in B for b in seis):
        return {"motivo": "dados_manha_incompletos"}
    side, _ = maioria([B[b] for b in seis])
    if side is None:
        return {"motivo": "empate"}
    trig = B.get(630)
    if trig is None:
        return {"motivo": "sem_barra_1030"}
    entry = trig[1]
    if entry > hi or entry < lo:
        return {"motivo": "fora_do_range"}
    if entry == mid:
        return {"motivo": "empate_mid"}
    if side == "C" and entry > mid:
        return {"motivo": "preco_acima_mid"}
    if side == "V" and entry < mid:
        return {"motivo": "preco_abaixo_mid"}
    if side == "C":
        sl, tp = entry - sl_pts, hi
    else:
        sl, tp = entry + sl_pts, lo
    idx = next(i for i, b in enumerate(m15) if b[0] == 630)
    pts = resolve(m15[idx:], side, sl, tp, entry)
    return dict(dia=dia, side=side, entry=entry, sl=sl, tp=tp, pts=pts)


def sete_velas_dia(dia, m15, sl_pts):
    B = barras_por_bucket(m15)
    sete = [540, 555, 570, 585, 600, 615, 630]
    if not all(b in B for b in sete):
        return {"motivo": "dados_manha_incompletos"}
    hi7 = max(B[b][2] for b in sete)
    lo7 = min(B[b][3] for b in sete)
    if hi7 <= lo7:
        return {"motivo": "range_invalido"}
    side, _ = maioria([B[b] for b in sete])
    if side is None:
        return {"motivo": "empate"}
    entry = B[630][4]
    sl = entry - sl_pts if side == "C" else entry + sl_pts
    tp = hi7 if side == "C" else lo7
    nxt = next((i for i, b in enumerate(m15) if b[0] >= 645), len(m15))
    pts = resolve(m15[nxt:], side, sl, tp, entry)
    return dict(dia=dia, side=side, entry=entry, sl=sl, tp=tp, pts=pts)


def stats(regs):
    if not regs:
        return None
    n = len(regs)
    wins = [r["pts"] for r in regs if r["pts"] > 0]
    los = [r["pts"] for r in regs if r["pts"] <= 0]
    gw = sum(wins)
    gl = abs(sum(los))
    wr = len(wins) / n * 100
    pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    payoff = ((gw / len(wins)) / (gl / len(los))) if wins and los else (float("inf") if gw > 0 else 0.0)
    net_rs = sum(r["pts"] for r in regs) * VALOR_PONTO - n * CUSTO
    eq = 0.0
    pico = 0.0
    mdd = 0.0
    for r in regs:
        eq += r["pts"] * VALOR_PONTO - CUSTO
        pico = max(pico, eq)
        mdd = min(mdd, eq - pico)
    return dict(n=n, wr=wr, pf=pf, payoff=payoff, net_rs=net_rs, mdd=mdd)


def run(sl_pts):
    days = load()
    f, s = [], []
    for d in sorted(days):
        m15 = to_m15(days[d])
        if not m15:
            continue
        r1 = frankenstein_dia(d, m15, sl_pts)
        if r1 and "pts" in r1:
            f.append(r1)
        r2 = sete_velas_dia(d, m15, sl_pts)
        if r2 and "pts" in r2:
            s.append(r2)
    return f, s


def main():
    if len(sys.argv) > 1:
        sls = [float(a) for a in sys.argv[1:]]
    else:
        sls = [5.0, 10.0, 20.0, 40.0, 60.0]
    print("=" * 108)
    print("FRANKENSTEIN vs SETE VELAS | WDO$ M15 09:00-18:00 | 2025-07-14 a 2026-07-31 | 1cc R$10/pt | custo R$0,75")
    print("esc.: SL 300 pts WIN (R$60) ~ SL 5 pts WDO (R$50) por ADR (2826 vs 51 pts)")
    print("TP = extremidade oposta da 1a hora (estrutural). SL antes do TP. EOD = ultima barra do dia.")
    print("=" * 108)
    print(f'{"SL pts":>7}{"estr":>8}{"n":>5}{"WR":>8}{"PF":>7}{"payoff":>8}{"net R$":>13}{"MaxDD R$":>13}')
    for sl in sls:
        f, s = run(sl)
        for nome, regs in (("FkF", f), ("SVc", s)):
            st = stats(regs)
            if not st:
                continue
            pf = "inf" if st["pf"] == float("inf") else f'{st["pf"]:.2f}'
            pay = "inf" if st["payoff"] == float("inf") else f'{st["payoff"]:.2f}'
            print(f'{sl:>7.1f}{nome:>8}{st["n"]:>5}{st["wr"]:>7.1f}%{pf:>7}{pay:>8}'
                  f'{st["net_rs"]:>13.2f}{st["mdd"]:>13.2f}')
    print("-" * 108)

    sl_padrao = sls[0]
    f, s = run(sl_padrao)
    dest = os.path.join(OUT_DIR, "frankenstein_wdo_2025_2026.csv")
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["dia", "estrategia", "sl_pts", "side", "entry", "sl", "tp", "pts", "net_rs_1cc"])
        for r in f + s:
            w.writerow([r["dia"], "franken" if r in f else "setevelas", sl_padrao, r["side"],
                        r["entry"], r["sl"], r["tp"], r["pts"],
                        round(r["pts"] * VALOR_PONTO - CUSTO, 2)])
    print(f"detalhe (SL {sl_padrao:.0f} pts) salvo em {dest}")


if __name__ == "__main__":
    main()