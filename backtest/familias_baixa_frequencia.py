# -*- coding: utf-8 -*-
"""Backtest das 3 familias de baixa frequencia PRE-REGISTRADAS em 21/11/2026.

Leia `backtest/PRE_REGISTRO_FAMILIAS_23-11-2026.md` ANTES deste arquivo.
Este script nao altera nenhuma regra la: so as implementa. Nao otimiza, nao
faz varredura extra, nao reescreve parametros depois de ver o OOS.

READ-ONLY. Nao envia ordem, nao toca no robo, nao muda config.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import stdev

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triagem_m5_sltp import (  # noqa: E402
    CUSTO_PTS, SLIPPAGES, atr_diario, carregar_barras, metrica,
)
from triagem_faixa1_m5 import pf  # noqa: E402

ALPHA = 0.05
N_COMPARACOES = 15          # 6 novas + 9 ja testadas nos mesmos dados
ALPHA_AJUSTADO = ALPHA / N_COMPARACOES
SLIP_ACEITE = 1.0
N_OOS_MIN = 40


# ------------------------------------------------------------- simulacao --
def simular(barras: list, i0: int, lado: int, entrada: float,
            stop: float, alvo: float) -> tuple:
    """(bruto_pess, bruto_otim, desfecho_oficial)."""
    if i0 >= len(barras):
        return None

    def caminho(prioridade: str) -> tuple:
        first = True
        for j in range(i0, len(barras)):
            _, op, high, low, _ = barras[j]
            toca_sl = (low <= stop) if lado == 1 else (high >= stop)
            toca_tp = (high >= alvo) if lado == 1 else (low <= alvo)
            if toca_sl or toca_tp:
                usa = prioridade if (toca_sl and toca_tp) else (
                    "sl" if toca_sl else "tp")
                if usa == "sl":
                    gap = (not first) and (
                        (op < stop) if lado == 1 else (op > stop))
                    fill = op if gap else stop
                    return lado * (fill - entrada), "SL"
                return lado * (alvo - entrada), "TP"
            first = False
        return lado * (barras[-1][4] - entrada), "TIME"

    pess, desfecho = caminho("sl")
    otim, _ = caminho("tp")
    return pess, otim, desfecho


def registrar(barras: list, atrs: list, i_sinal: int, lado: int,
              stop: float, alvo: float) -> dict | None:
    i_entrada = i_sinal + 1
    if i_entrada >= len(barras):
        return None
    entrada = barras[i_entrada][1] + lado * 0.5   # 0,5 contra (pre-registro)
    out = simular(barras, i_entrada, lado, entrada, stop, alvo)
    if out is None:
        return None
    pess, otim, desfecho = out
    return dict(i_entrada=i_entrada, lado=lado, pess=pess,
                otim=otim, desfecho=desfecho)


def hm(b) -> tuple:
    return (b[0].hour, b[0].minute)


# ---------------------------------------------------------- familia (a) --
def familia_v_run(barras: list, atrs: list, k: float, m: float) -> list:
    """Rompimento de volatilidade: caixa 09:00-09:30, folga k*ATR, stop m*ATR."""
    caixa = [b for b in barras if hm(b) < (9, 30)]
    if len(caixa) < 6:
        return []
    hi = max(b[2] for b in caixa)
    lo = min(b[3] for b in caixa)
    out, bloqueados = [], set()
    ultima, n = -999, 0
    for i, b in enumerate(barras):
        if hm(b) < (9, 35):
            continue
        atr = atrs[i]
        if not atr or atr <= 0:
            continue
        up = b[2] >= hi + k * atr
        dn = b[3] <= lo - k * atr
        if up == dn:
            continue
        lado = 1 if up else -1
        if n >= 2 or lado in bloqueados or i - ultima < 12:
            continue
        i_ent = i + 1
        if i_ent >= len(barras):
            continue
        entrada = barras[i_ent][1] + lado * 0.5
        stop = entrada - lado * m * atr       # stop a m*ATR da entrada
        alvo = entrada + lado * 15.0         # alvo a 15 pts da entrada
        r = registrar(barras, atrs, i, lado, stop, alvo)
        if r is None:
            continue
        out.append(r)
        n += 1
        ultima = r["i_entrada"]
        if r["desfecho"] == "SL":
            bloqueados.add(lado)
    return out


# ---------------------------------------------------------- familia (b) --
def familia_r(barras: list, atrs: list, f: float, s: float, t: float) -> list:
    """Reversao nos extremos do range da manha; maximo 1 trade por dia."""
    ini = [b for b in barras if hm(b) < (9, 40)]
    if len(ini) < 8:
        return []
    hi = max(b[2] for b in ini)
    lo = min(b[3] for b in ini)
    for i, b in enumerate(barras):
        hmm = hm(b)
        if hmm < (9, 45) or i + 2 >= len(barras):
            continue
        hi_ref, lo_ref = hi, lo
        rng = hi_ref - lo_ref
        if rng <= 0:
            continue
        toque_top = b[2] >= hi_ref
        toque_base = b[3] <= lo_ref
        if toque_top == toque_base:
            continue
        prox = barras[i + 1]                   # barra seguinte fecha de volta
        if toque_top and prox[4] <= hi_ref - f * rng:
            lado, stop, alvo = -1, hi_ref + s * rng, max(15.0, t * rng)
        elif toque_base and prox[4] >= lo_ref + f * rng:
            lado, stop, alvo = 1, lo_ref - s * rng, max(15.0, t * rng)
        else:
            lado = 0
        if hmm < (10, 0):                      # range movel da manha
            hi = max(hi, b[2])
            lo = min(lo, b[3])
        if not lado:
            continue
        i_ent = i + 2
        if i_ent >= len(barras):
            continue
        entrada = barras[i_ent][1] + lado * 0.5
        alvo_nivel = entrada + lado * max(15.0, t * rng)
        r = registrar(barras, atrs, i + 1, lado, stop, alvo_nivel)
        if r is not None:
            return [r]
    return []


# ---------------------------------------------------------- familia (c) --
def familia_c(barras: list, atrs: list, k: float, m: float, tp: float) -> list:
    """Continuacao apos a primeira hora (09:00-10:00); 1 trade por dia."""
    indices = [i for i, b in enumerate(barras) if hm(b) < (10, 0)]
    if len(indices) < 12:
        return []
    i_sinal = indices[-1]
    open0 = barras[indices[0]][1]
    close10 = barras[i_sinal][4]
    atr = atrs[i_sinal]
    if not atr or atr <= 0:
        return []
    if close10 - open0 >= k * atr:
        lado = 1
    elif open0 - close10 >= k * atr:
        lado = -1
    else:
        return []
    i_ent = i_sinal + 1
    if i_ent >= len(barras):
        return []
    entrada = barras[i_ent][1] + lado * 0.5
    stop = entrada - lado * m * atr
    alvo_nivel = entrada + lado * tp
    r = registrar(barras, atrs, i_sinal, lado, stop, alvo_nivel)
    return [r] if r else []


# ------------------------------------------------------------- execucao --
FAMILIAS = {
    "V1": ("a) rompimento de volatilidade", lambda b, a: familia_v_run(b, a, 0.5, 2.0)),
    "V2": ("a) rompimento de volatilidade", lambda b, a: familia_v_run(b, a, 1.0, 3.0)),
    "R1": ("b) reversao nos extremos", lambda b, a: familia_r(b, a, 0.25, 1.0, 0.5)),
    "R2": ("b) reversao nos extremos", lambda b, a: familia_r(b, a, 0.50, 1.5, 1.0)),
    "C1": ("c) continuacao apos abertura", lambda b, a: familia_c(b, a, 0.5, 2.0, 20.0)),
    "C2": ("c) continuacao apos abertura", lambda b, a: familia_c(b, a, 1.0, 3.0, 30.0)),
}


def coletar() -> dict:
    res = defaultdict(list)
    for dia, barras in carregar_barras().items():
        atrs = atr_diario(barras)
        periodo = "IS" if dia.year <= 2024 else "OOS"
        for nome, (_, fn) in FAMILIAS.items():
            for r in fn(barras, atrs):
                for slip in SLIPPAGES:
                    res[(nome, periodo, slip)].append(
                        r["pess"] - CUSTO_PTS - 2 * slip)
    return res


def t_e_crit(valores: list) -> tuple:
    n = len(valores)
    if n < 2:
        return 0.0, 0.0
    m = metrica(valores)["esperanca"]
    sd = stdev(valores)
    t = 0.0 if sd == 0 else m / (sd / (n ** 0.5))
    crit = float(stats.t.ppf(1 - ALPHA_AJUSTADO, n - 1))
    return t, crit


def imprimir(res: dict) -> None:
    print("FAMILIAS DE BAIXA FREQUENCIA - PRE-REGISTRO 21/11/2026")
    print(f"Comparacoes consideradas: {N_COMPARACOES} | "
          f"alpha_ajustado = {ALPHA_AJUSTADO:.5f} (Bonferroni)")
    print("Atrito: abertura + 0,5 contra | custo 0,12 pt | "
          "slippage 0/0,5/1,0 por lado | M5 09:00-15:25")
    print(" Aceite: E_OOS@1,0 > 0, n_OOS >= 40, PF_OOS > 1, t > t_crit")

    for familia in ("a) rompimento de volatilidade",
                    "b) reversao nos extremos",
                    "c) continuacao apos abertura"):
        print(f"\nTABELA - {familia.upper()}")
        print(f"{'var':>4} {'n_IS':>5} {'E_IS@1':>8} {'n_OOS':>6} "
              f"{'E@0':>8} {'E@0,5':>8} {'E@1':>8} {'PF@1':>7} "
              f"{'t':>7} {'t_crit':>7} {'decisao':>12}")
        for nome, (fam, _) in FAMILIAS.items():
            if fam != familia:
                continue
            is10 = res[(nome, "IS", 1.0)]
            oos = {s: res[(nome, "OOS", s)] for s in SLIPPAGES}
            m_is = metrica(is10)
            n_oos = len(oos[SLIP_ACEITE])
            e_oos = {s: metrica(oos[s])["esperanca"] for s in SLIPPAGES}
            pf_oos = pf(oos[SLIP_ACEITE])
            t, crit = t_e_crit(oos[SLIP_ACEITE])
            passa = (e_oos[SLIP_ACEITE] > 0 and n_oos >= N_OOS_MIN
                     and pf_oos is not None and pf_oos > 1 and t > crit)
            print(f"{nome:>4} {m_is['n']:>5} {m_is['esperanca']:>+8.2f} "
                  f"{n_oos:>6} {e_oos[0.0]:>+8.2f} {e_oos[0.5]:>+8.2f} "
                  f"{e_oos[1.0]:>+8.2f} "
                  f"{(pf_oos if pf_oos is not None else float('nan')):>7.2f} "
                  f"{t:>+7.2f} {crit:>7.2f} "
                  f"{'PASSA' if passa else 'NAO PASSA':>12}")

    print("\nRESUMO DAS 6 VARIANTES (OOS, slippage 1,0 pt/lado)")
    aprovadas = []
    for nome in FAMILIAS:
        v = res[(nome, "OOS", 1.0)]
        e = metrica(v)["esperanca"]
        p = pf(v)
        t, crit = t_e_crit(v)
        ok = e > 0 and len(v) >= N_OOS_MIN and p is not None and p > 1 and t > crit
        if ok:
            aprovadas.append(nome)
        print(f"  {nome}: n={len(v):>4} E={e:>+7.2f} PF="
              f"{(p if p is not None else float('nan')):>5.2f} "
              f"t={t:>+6.2f} t_crit={crit:>5.2f} -> "
              f"{'PASSA' if ok else 'NAO PASSA'}")
    if aprovadas:
        print(f"\nConclusao: {', '.join(aprovadas)} passou. "
              "Ainda exige paper 20-30 sessoes antes de qualquer real.")
    else:
        print("\nCONCLUSAO: NENHUMA VARIANTE PASSOU. "
              "A decisao do projeto e NAO OPERAR. Resultado valido e final.")
    print("\nSem otimizacao pos-OOS. Nenhum parametro foi alterado depois "
          "do pre-registro (SHA-256 E1E85B90...0326).")


if __name__ == "__main__":
    imprimir(coletar())
