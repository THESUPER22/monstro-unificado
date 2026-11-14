# -*- coding: utf-8 -*-
"""
tendencia_h1_robustez.py — Validacao READ-ONLY do candidato de tendencia H1.

Roda, para o sinal ema_8_21:
  1. detalhe ano a ano do candidato (SL 1.5*ATR, EOD), slip 0,5/1,0/1,5;
  2. controles (mirror, long, shift) no candidato;
  3. walk-forward ancorado: escolhe (SL, TP) no passado e testa no ano seguinte;
  4. Monte Carlo bootstrap (10k) do candidato;
  5. t-stat da expectancia (full, IS, OOS).

Nao envia ordem, nao altera config, nao toca no robo.

Uso:
    python backtest/tendencia_h1_robustez.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filtros_faixa1 import load_m1  # noqa: E402
from tendencia_h1_wdo import (  # noqa: E402
    build_h1, coletar, gerar_sinal, preparar_dias, split_is_oos,
)
from backtest_trailing_faixa1 import linha, stats  # noqa: E402

COST_RS = 1.20
RS = 10.0
GRID = [(k, tp) for k in (1.5, 2.0, 2.5)
        for tp in (2.0, 3.0, 4.0, None)]
SLIP = 1.0


def net(trades):
    return np.array([t["pnl"] * RS - COST_RS for t in trades], dtype=float)


def tstat(trades):
    x = net(trades)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return 0.0
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def resumo_curto(trades, label):
    v = stats(trades, label)
    x = net(trades)
    t = tstat(trades)
    print(f"  {label:<22} n={v.get('n',0):>4} WR={v.get('win%',0):>5.1f} "
          f"exp={v.get('exp_rs',0):>7.2f} PF={v.get('pf',0):>5.2f} "
          f"tot={v.get('total_rs',0):>8.0f} DD={v.get('maxdd_rs',0):>7.0f} "
          f"t={t:>5.2f}")


def detalhe_por_ano(trades, label):
    print(f"\n--- {label} ---")
    by = {}
    for t in trades:
        by.setdefault(t["year"], []).append(t)
    for y in sorted(by):
        resumo_curto(by[y], str(y))
    is_sub, oos_sub = split_is_oos(trades)
    resumo_curto(is_sub, "IS 2021-2024")
    resumo_curto(oos_sub, "OOS 2025-2026")
    resumo_curto(trades, "FULL")


def walk_forward(sinal, h1, m1_by_day):
    print("\n--- walk-forward ancorado (escolhe SL/TP no passado, testa no ano) ---")
    trades_by = {}
    for k, tp in GRID:
        trades_by[(k, tp)] = coletar(h1, m1_by_day, sinal, k, tp, SLIP)

    oos = []
    for ano in (2023, 2024, 2025, 2026):
        candidatos = []
        for key, tr in trades_by.items():
            train = [t for t in tr if t["year"] < ano]
            if len(train) < 80:
                continue
            v = stats(train, "train")
            if v.get("exp_rs", -1) > 0:
                candidatos.append((v["exp_rs"], key, v))
        if not candidatos:
            print(f"  {ano}: sem candidato no treino -> nao opera")
            continue
        candidatos.sort(key=lambda x: x[0], reverse=True)
        exp_tr, key, vtr = candidatos[0]
        test = [t for t in trades_by[key] if t["year"] == ano]
        vt = stats(test, "test")
        oos.extend(test)
        tp_label = "EOD" if key[1] is None else f"{key[1]}R"
        print(f"  {ano}: escolhido SL={key[0]:.1f} TP={tp_label:<4} "
              f"(treino exp {exp_tr:>7.2f}) -> teste n={vt.get('n',0):>3} "
              f"exp={vt.get('exp_rs',0):>7.2f} PF={vt.get('pf',0):>5.2f} "
              f"tot={vt.get('total_rs',0):>7.0f}")
    print()
    resumo_curto(oos, "WALK-FORWARD OOS")
    return oos


def monte_carlo(trades, n_iter=10000, seed=42):
    print("\n--- Monte Carlo bootstrap (10.000 reamostragens) ---")
    x = net(trades)
    n = len(x)
    if n < 10:
        print("  amostra insuficiente")
        return
    rng = np.random.default_rng(seed)
    totais = np.empty(n_iter)
    pfs = np.empty(n_iter)
    wrs = np.empty(n_iter)
    dds = np.empty(n_iter)
    for i in range(n_iter):
        s = rng.choice(x, size=n, replace=True)
        eq = np.cumsum(s)
        dd = float(np.min(eq - np.maximum.accumulate(eq)))
        pos = s[s > 0].sum()
        neg = -s[s < 0].sum()
        totais[i] = s.sum()
        pfs[i] = pos / neg if neg > 0 else float("inf")
        wrs[i] = 100.0 * (s > 0).mean()
        dds[i] = dd
    pct = lambda a, p: float(np.percentile(a, p))
    print(f"  total: mediana {pct(totais,50):>8.0f} | p5 {pct(totais,5):>8.0f} | "
          f"p95 {pct(totais,95):>8.0f} | P(total>0)={100*(totais>0).mean():>5.1f}%")
    print(f"  PF:    mediana {pct(pfs,50):>8.2f} | p5 {pct(pfs,5):>8.2f} | "
          f"p95 {pct(pfs,95):>8.2f} | P(PF>1)={100*(pfs>1).mean():>5.1f}%")
    print(f"  WR:    mediana {pct(wrs,50):>8.1f}% | p5 {pct(wrs,5):>8.1f}% | "
          f"p95 {pct(wrs,95):>8.1f}%")
    print(f"  maxDD: mediana {pct(dds,50):>8.0f} | p5 {pct(dds,5):>8.0f}")


def main() -> None:
    m1 = load_m1("WDO$", datetime(2021, 11, 1))
    h1 = build_h1(m1)
    m1_by_day = preparar_dias(h1, m1)
    s = gerar_sinal(h1, "ema", (8, 21))

    print("=" * 100)
    print(f"ROBUSTEZ TENDENCIA H1 | ema_8_21 | H1={len(h1)} "
          f"dias={h1['day'].nunique()} | custo R$1,20 | 1 contrato")
    print("=" * 100)

    # 1. candidato SL 1.5 / EOD, varios slippages
    for slip in (0.5, 1.0, 1.5):
        tr = coletar(h1, m1_by_day, s, 1.5, None, slip)
        detalhe_por_ano(tr, f"ema_8_21 SL=1.5 EOD slip={slip}")

    # 2. controles no candidato
    print("\n--- controles ema_8_21 SL=1.5 EOD slip 1.0 ---")
    for mode, label in (("normal", "normal"), ("mirror", "CTRL-MIRROR"),
                        ("long", "CTRL-LONG")):
        trc = coletar(h1, m1_by_day, s, 1.5, None, 1.0, side_mode=mode)
        resumo_curto(trc, label)
    trs = coletar(h1, m1_by_day, s, 1.5, None, 1.0, shift=1)
    resumo_curto(trs, "CTRL-SHIFT-1")

    # 3. walk-forward
    walk_forward(s, h1, m1_by_day)

    # 4. Monte Carlo do candidato
    tr = coletar(h1, m1_by_day, s, 1.5, None, 1.0)
    monte_carlo(tr)

    # 5. t-stat resumido
    print("\n--- significancia (candidato SL=1.5 EOD slip 1.0) ---")
    is_sub, oos_sub = split_is_oos(tr)
    for label, sub in (("FULL", tr), ("IS", is_sub), ("OOS", oos_sub)):
        print(f"  {label:<5} n={len(sub):>4} exp={net(sub).mean():>7.2f} "
              f"t={tstat(sub):>5.2f}")


if __name__ == "__main__":
    main()
