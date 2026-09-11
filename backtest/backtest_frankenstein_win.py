# -*- coding: utf-8 -*-
"""
backtest_frankenstein_win.py
Frankenstein Operacional = Antecipacao do Rompimento da 1a Hora com o Sete Velas Invertido.
Ativo: WIN (mini indice). Timeframe: M15 (agregado de M5). Periodo: 2022-01-02 a 2026-09-09.

Regras (Frankenstein):
  1. Range 1a hora = max(high)/min(low) das barras M15 abertas 09:00-09:45 (4 barras). mid = (hi+lo)/2.
  2. As 10:30 (abertura da 7a vela) conta-se a cor das 6 velas 09:00-10:15.
  3. Maioria VERDE + preco(10:30) ACIMA do mid  -> VENDA a mercado.
  4. Maioria VERMELHA + preco(10:30) ABAIXO do mid -> COMPRA a mercado.
  5. Descarte: empate (3x3) ou preco 10:30 fora do range 1a hora. 1 trade/dia max.
  6. SL fixo 300 pts. TP: long->max(range), short->min(range). SL conferido ANTES do TP (intrabarra).

Base crua Sete Velas (comparacao): 7 velas 09:00-10:30 (fecho da 7a), maioria -> entrada no fecho da 7a
vela, SL 300 fixo, TP = extremidade oposta das 7 velas. Mesmo cost/fill/EOD.

LIMITACAO DE DADOS: o feed deste terminal so possui barras ate ~15:30 BRT (sem periodo da tarde).
EOD de cada dia = ultima barra M15 disponivel (~15:20). Resultado tem este enviesamento estrutural.

Custo: R$0,75/trade. Valor do ponto: R$0,20 (1cc). 1 trade/dia. Fill = abertura do gatilho (10:30) /
fecho da 7a vela.
"""
import csv
import os
from datetime import datetime
from collections import defaultdict

VALOR_PONTO = 0.20   # R$/ponto WIN 1cc
CUSTO = 0.75         # R$/trade
SL_PTS = 300.0
RTH_INI_MIN = 9 * 60        # 09:00 BRT
RTH_FIM_MIN = 18 * 60       # limite superior
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "dados_mt5", "baixa_tudo", "filtrados")
OUT_DIR = os.path.join(BASE, "resultados")
ANOS = [2022, 2023, 2024, 2025, 2026]


def load(ano):
    p = os.path.join(DATA_DIR, f"WING{ano}_M5.csv")
    if not os.path.exists(p):
        return {}
    rows = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = datetime.fromtimestamp(int(r["time"]))
            mins = t.hour * 60 + t.minute
            if mins < RTH_INI_MIN or mins >= RTH_FIM_MIN:
                continue
            rows.append((t, float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), int(r["tick_volume"])))
    if not rows:
        return {}
    days = defaultdict(list)
    for r in rows:
        days[r[0].date()].append(r)
    return {d: sorted(v) for d, v in days.items()}


def to_m15(day):
    """Agrega M5->M15 por bucket de 15min (RTH)."""
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
    return out  # [bucket_min, open, high, low, close, tick_volume]


def barras_por_bucket(m15):
    return {b[0]: b for b in m15}


def maioria(seis):
    gre = sum(1 for b in seis if b[4] > b[1])
    red = sum(1 for b in seis if b[4] < b[1])
    if gre > red:
        return "V", gre  # maioria verde -> mercado esticado -> VENDA
    if red > gre:
        return "C", red  # maioria vermelha -> repique -> COMPRA
    return None, None    # empate


def frankenstein_dia(dia, m15):
    """retorna dict(side, entry, sl, tp, pts) ou None se descartado."""
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
    trig = B.get(630)  # 10:30
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
        sl, tp = entry - SL_PTS, hi
    else:
        sl, tp = entry + SL_PTS, lo
    idx = next(i for i, b in enumerate(m15) if b[0] == 630)
    pts = resolve(m15[idx:], side, sl, tp, entry)
    return dict(dia=dia, side=side, entry=entry, sl=sl, tp=tp, pts=pts)


def sete_velas_dia(dia, m15):
    """Base crua: 7 velas, maioria -> entrada no fecho da 7a vela (close da barra 10:30-10:44)."""
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
    entry = B[630][4]  # fecho da 7a vela (barra 10:30-10:44)
    sl = entry - SL_PTS if side == "C" else entry + SL_PTS
    tp = hi7 if side == "C" else lo7
    nxt = next((i for i, b in enumerate(m15) if b[0] >= 645), len(m15))
    pts = resolve(m15[nxt:], side, sl, tp, entry)
    return dict(dia=dia, side=side, entry=entry, sl=sl, tp=tp, pts=pts)


def resolve(bars, side, sl, tp, entry):
    """SL conferido ANTES do TP dentro da mesma barra. EOD = ultima barra do dia."""
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


def linha(s, ano=None):
    if s is None:
        return None
    pf = "inf" if s["pf"] == float("inf") else f'{s["pf"]:.2f}'
    pay = "inf" if s["payoff"] == float("inf") else f'{s["payoff"]:.2f}'
    return (f'{ano or "TOTAL":<8}{s["n"]:>5}{s["wr"]:>7.1f}%{pf:>6}'
            f'{pay:>7}{s["net_rs"]:>10.2f}{s["mdd"]:>10.2f}')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_f, all_s, desc_f, desc_s = [], [], defaultdict(int), defaultdict(int)
    per_ano = {}
    dias_ok = 0
    print("=" * 106)
    print("FRANKENSTEIN (Sete Velas Inv. + Rompimento 1a Hora) vs SETE VELAS CRUA | WIN M15 | 2022-2026 | 1cc | R$0,75")
    print("SL=300 fixo | TP=extremidade oposta do range | fill=10:30 (Franken) / fecho 7a vela (crua) | SL antes do TP")
    print("ATENCAO: feed deste terminal so tem barras ate ~15:30 BRT -> EOD = ultima barra do dia (~15:20).")
    print("=" * 106)
    print(f'{"estrategia   ano":<14}{"n":>5}{"WR":>8}{"PF":>7}{"payoff":>8}{"net R$":>11}{"MaxDD R$":>10}')
    for ano in ANOS:
        days = load(ano)
        f, s = [], []
        for d in sorted(days):
            m15 = to_m15(days[d])
            if not m15:
                continue
            r1 = frankenstein_dia(d, m15)
            if r1 and "pts" in r1:
                f.append(r1)
            elif r1:
                desc_f[r1["motivo"]] += 1
            r2 = sete_velas_dia(d, m15)
            if r2 and "pts" in r2:
                s.append(r2)
            elif r2:
                desc_s[r2["motivo"]] += 1
        all_f += f
        all_s += s
        per_ano[ano] = (f, s)
        dias_ok += len(days)
        sf, ss = stats(f), stats(s)
        if sf:
            print("Franken " + linha(sf, str(ano)))
            with open(os.path.join(OUT_DIR, f"frankenstein_win_{ano}.csv"), "w", newline="",
                      encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["dia", "estrategia", "side", "entry", "sl", "tp", "pts"])
                for r in f:
                    w.writerow([r["dia"], "franken", r["side"], r["entry"], r["sl"], r["tp"], r["pts"]])
        if ss:
            print("SeteV  " + linha(ss, str(ano)))
            with open(os.path.join(OUT_DIR, f"setevelas_crua_win_{ano}.csv"), "w", newline="",
                      encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["dia", "estrategia", "side", "entry", "sl", "tp", "pts"])
                for r in s:
                    w.writerow([r["dia"], "setevelas", r["side"], r["entry"], r["sl"], r["tp"], r["pts"]])
    print("-" * 106)
    print("Franken " + linha(stats(all_f), "TOTAL"))
    print("SeteV  " + linha(stats(all_s), "TOTAL"))
    print("-" * 106)
    print(f"dias com sessao RTH analisada: {dias_ok} | trades Franken: {len(all_f)} | trades SeteV: {len(all_s)}")
    print("descarte Franken:", dict(desc_f))
    print("descarte SeteV  :", dict(desc_s))

    with open(os.path.join(OUT_DIR, "frankenstein_win_consolidado.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["estrategia", "ano", "n", "wr_pct", "pf", "payoff", "net_pts", "net_rs_1cc", "maxdd_rs"])
        for nome, regs, ano in ([("franken", all_f, "TOTAL"), ("setevelas", all_s, "TOTAL")] +
                                [(n, r, str(a)) for a in per_ano for n, r in
                                 (("franken", per_ano[a][0]), ("setevelas", per_ano[a][1]))]):
            s = stats(regs)
            if s:
                w.writerow([nome, ano, s["n"], round(s["wr"], 1), round(s["pf"], 2),
                            round(s["payoff"], 2), round(sum(r["pts"] for r in regs), 1),
                            round(s["net_rs"], 2), round(s["mdd"], 2)])
    print("resultados salvos em", OUT_DIR)


if __name__ == "__main__":
    main()