# -*- coding: utf-8 -*-
"""Triagem da Faixa 1 (ORB) com o MESMO atrito da triagem do Sniper.

READ-ONLY, separado do robo. Nao promove nada: so mede se a tese da Faixa 1
sobrevive ao custo canonico (R$ 1,20 = 0,12 pt + slippage 0/0,5/1,0 pt/lado)
e ao modelo de two scenarios (SL primeiro / TP primeiro) usado em
`triagem_m5_sltp.py`.

Sinais:
  - ORB-1030 (canonico ROADMAP 23.20.2): caixa 09:00-10:00, gatilho na
    primeira barra M5 de 10:30-11:00 que rompe high/low da caixa; stop no
    lado oposto da caixa; sem TP; saida no ultimo close disponivel (15:25
    no CSV, contra 17:55 no estudo original - ver LIMITACOES).
  - A0/B/C/D: MESMAS geometrias de SL/TP do Sniper aplicadas ao mesmo sinal
    ORB-1030, entrada na abertura da barra seguinte + 0,5 contra, janela de
    6 barras (30 min).

Tabela por ano: n, acerto, payoff, PF, E_pess, E_otim (slippage 0,5/lado).
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triagem_m5_sltp import (  # noqa: E402
    ANOS_PODA, CENARIOS, CUSTO_PTS, FATOR_M1, SLIPPAGES, SLIP_PADRAO,
    VARIANTES, atr_diario, carregar_barras, fmt, metrica, sl_tp,
)

MAX_BARRAS = 6           # 30 min para A0/B/C/D
GATILHO_INI = (10, 30)
GATILHO_FIM = (11, 0)
TODAS = VARIANTES + ("ORB-1030",)


# ------------------------------------------------------------------ sinal --
def sinal_orb(barras: list):
    """(indice do gatilho, lado, stop_em_pts) ou None.

    Caixa = 09:00-10:00. Gatilho = primeira barra M5 de 10:30-11:00 cujo
    high/low rompe a caixa. Se high e low rompem na mesma barra, o dia e
    ambiguo e e descartado (conservador, igual `signal_stop` de
    `filtros_faixa1.py`).
    """
    caixa = [b for b in barras if b[0].hour == 9]
    if len(caixa) < 8:
        return None
    hi = max(b[2] for b in caixa)
    lo = min(b[3] for b in caixa)
    rng = hi - lo
    if rng <= 0:
        return None
    for i, b in enumerate(barras):
        hm = (b[0].hour, b[0].minute)
        if hm < GATILHO_INI:
            continue
        if hm >= GATILHO_FIM:
            break
        rompeu_buy = b[2] >= hi
        rompeu_sell = b[3] <= lo
        if rompeu_buy and rompeu_sell:
            return None
        if rompeu_buy:
            return i, 1, rng
        if rompeu_sell:
            return i, -1, rng
    return None


def bruto(variante: str, atr_m1: float, stop_caixa: float, barras: list,
          i_sinal: int, lado: int, cenario: str) -> float:
    """Pontos brutos; entrada na abertura seguinte + 0,5 contra."""
    i_entrada = i_sinal + 1
    if i_entrada >= len(barras):
        return 0.0
    entrada = barras[i_entrada][1] + lado * 0.5
    if variante == "ORB-1030":
        sl, tp = stop_caixa, None
        limite = len(barras)                 # ate o ultimo close do dia
    else:
        sl, tp = sl_tp(variante, atr_m1)
        limite = min(i_entrada + MAX_BARRAS, len(barras))
    nivel_sl = entrada - lado * sl
    nivel_tp = entrada + lado * tp if tp is not None else None

    for j in range(i_entrada, limite):
        _, _, high, low, close = barras[j]
        toca_sl = (low <= nivel_sl) if lado == 1 else (high >= nivel_sl)
        toca_tp = (nivel_tp is not None and
                   ((high >= nivel_tp) if lado == 1 else (low <= nivel_tp)))
        if not (toca_sl or toca_tp):
            continue
        if toca_sl:
            fill_sl = min(low, nivel_sl) if lado == 1 else max(high, nivel_sl)
        if toca_tp:
            fill_tp = nivel_tp
        if toca_sl and toca_tp:
            fill = fill_sl if cenario == "pess" else fill_tp
        elif toca_sl:
            fill = fill_sl
        else:
            fill = fill_tp
        return lado * (fill - entrada)
    return lado * (barras[limite - 1][4] - entrada)


# -------------------------------------------------------------- metricas ---
def pf(valores: list) -> float | None:
    gains = sum(v for v in valores if v > 0)
    losses = -sum(v for v in valores if v < 0)
    return (gains / losses) if losses > 0 else None


def coletar() -> tuple:
    """{(ano, variante, cenario, slip): [liquido pts]}, n_sinais, n_dias."""
    res = defaultdict(list)
    n_sinais = n_dias = 0
    for dia, barras in carregar_barras().items():
        s = sinal_orb(barras)
        if s is None:
            continue
        n_dias += 1
        i, lado, stop_caixa = s
        n_sinais += 1
        atrs = atr_diario(barras)
        atr_m1 = atrs[i] / FATOR_M1 if atrs[i] else 0.0
        for variante in TODAS:
            for cenario in CENARIOS:
                bruto_pts = bruto(variante, atr_m1, stop_caixa, barras,
                                  i, lado, cenario)
                for slip in SLIPPAGES:
                    res[(dia.year, variante, cenario, slip)].append(
                        bruto_pts - CUSTO_PTS - 2.0 * slip)
    return res, n_sinais, n_dias


def imprimir(res: dict, n_sinais: int, n_dias: int) -> None:
    anos = sorted({k[0] for k in res})
    print("TRIAGEM FAIXA 1 (ORB) - MESMO ATRITO DA TRIAGEM DO SNIPER")
    print(f"CSV: WDO_FULL_M5_2021_2026.csv | sinais: {n_sinais} em {n_dias} dias")
    print("Caixa 09:00-10:00; gatilho 10:30-11:00; entrada na abertura seguinte")
    print("+0,5 contra; custo 0,12 pt + slippage por lado; same-bar SL/TP => pess/otim.")
    print("ORB-1030 = stop no lado oposto da caixa, sem TP, saida 15:25 (ver limite).")
    print("A0/B/C/D = geometrias do Sniper aplicadas ao mesmo sinal ORB, janela 30 min.")

    print("\nTABELA 1 - POR ANO (slippage 0,5 pt/lado)")
    print(f"{'ano':>5} {'var':>9} {'n':>5} {'acerto':>8} {'payoff':>8} "
          f"{'PF':>7} {'E_pess':>9} {'E_otim':>9}")
    for ano in anos:
        for variante in TODAS:
            p = [v for v in res[(ano, variante, "pess", SLIP_PADRAO)]]
            o = metrica(res[(ano, variante, "otim", SLIP_PADRAO)])
            m = metrica(p)
            print(f"{ano:>5} {variante:>9} {m['n']:>5} "
                  f"{m['acerto']:>7.1f}% {fmt(m['payoff']):>8} "
                  f"{fmt(pf(p)):>7} {m['esperanca']:>+9.2f} "
                  f"{o['esperanca']:>+9.2f}")

    print("\nTABELA 2 - SENSIBILIDADE AO SLIPPAGE ( Expectativa OTIMISTA, todos os anos )")
    print(f"{'var':>9} {'cenario':>8} {'0.0':>9} {'0.5':>9} {'1.0':>9} {'PF@1.0':>8}")
    for variante in TODAS:
        for cenario in CENARIOS:
            vals = []
            for slip in SLIPPAGES:
                todos = [v for ano in anos
                         for v in res[(ano, variante, cenario, slip)]]
                vals.append(metrica(todos)["esperanca"])
            todos10 = [v for ano in anos
                       for v in res[(ano, variante, cenario, 1.0)]]
            print(f"{variante:>9} {cenario:>8} " +
                  " ".join(f"{v:>+9.2f}" for v in vals) +
                  f" {fmt(pf(todos10)):>8}")

    print("\nPODA (expectativa OTIMISTA <= 0; anos 2022-2026)")
    print(f"{'var':>9} {'slip':>5} {'anos<=0':>8} {'decisao':>14}")
    for variante in TODAS:
        for slip in SLIPPAGES:
            ruins = sum(1 for ano in ANOS_PODA
                        if metrica(res[(ano, variante, "otim", slip)])[
                            "esperanca"] <= 0)
            decisao = "DESCARTAR" if ruins >= 4 else "manter na triagem"
            print(f"{variante:>9} {slip:>5.1f} {ruins:>5}/5 {decisao:>14}")

    print("\nLIMITACOES (obrigatorias)")
    print("- CSV cobre 09:00-15:25: a saida do ORB canonico do ROADMAP era 17:55.")
    print("  Aqui a saida e o ultimo close disponivel (15:25), entao NAO compare os")
    print("  numeros absolutos diretamente com 23.20.2 (WDO$, 17:55).")
    print("- Gatilho usa barra M5 fechada; o estudo original usou M5 idem, mas o")
    print("  forward real usa M1. Sem M1 nao ha sequencia intrabar exata.")
    print("- Sem book/DOL/filtros; 1 contrato; semLeilao/after.")
    print("- Poda e irreversivel so nesta triagem; NAO e reativacao da Faixa 1.")


if __name__ == "__main__":
    r, total, dias = coletar()
    imprimir(r, total, dias)
