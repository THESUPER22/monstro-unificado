# -*- coding: utf-8 -*-
"""Triagem grossa de SL/TP (A0, B, C, D) com o historico M5 do WDO.

ESTE SCRIPT E SEPARADO e NAO altera `avaliar_shadow_sltp.py` (congelado).
Ele NAO promove nada: only poda variantes claramente ruins. A decisao real
continua sendo o shadow ao vivo com bid/ask a 1 s.

Regras (definidas pelo usuario em 20/11/2026):
  1. sinal = Williams %R(14) em M5, -80 BUY / -20 SELL, com trava de zona
     (so dispara na ENTRADA da zona). PROXY do Sniper %R M1.
  2. ATR M1-equivalente = ATR M5 / sqrt(5) (aproximacao declarada), usado por
     A0 e B. ATR M5 e Wilder com semente no primeiro TR, igual a
     `calcular_atr()` do robo.
  3. se SL e TP cabem na mesma barra M5, rodar DOIS cenarios: pessimista
     (SL primeiro) e otimista (TP primeiro). Os dois sao reportados.
  4. custo = R$ 1,20 (= 0,12 pt) + slippage 0 / 0,5 / 1,0 pt POR LADO
     (entrada + saida), igual ao avaliador congelado.
  5. horario = 09:00 as 15:25 (todo o range do CSV M5). Janela maxima de
     avaliacao = 6 barras (30 min), igual ao path do avaliador congelado.
  6. tabela por variante/ano: n, acerto, payoff, expectativa liquida
     (pessimista e otimista). Poda: descartar se a expectativa OTIMISTA for
     <= 0 em >= 4 dos 5 anos 2022-2026 (2021 e parcial, informativo).

Uso:
    python backtest/triagem_m5_sltp.py
"""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

CSV = Path(
    r"C:\AIOFEN\backtest\dados_mt5\baixa_tudo\filtrados"
    r"\WDO_FULL_M5_2021_2026.csv"
)
FUSO_BR = ZoneInfo("America/Sao_Paulo")
HORA_INI = time(9, 0)
HORA_FIM = time(15, 25)
PERIODO = 14
WR_BUY = -80.0
WR_SELL = -20.0
FATOR_M1 = math.sqrt(5.0)
MAX_BARRAS = 6            # 30 min em M5
CUSTO_PTS = 1.20 / 10.0   # R$ 1,20 / R$ 10,00 por ponto
SLIPPAGES = (0.0, 0.5, 1.0)
SLIP_PADRAO = 0.5
ANOS_PODA = (2022, 2023, 2024, 2025, 2026)
VARIANTES = ("A0", "B", "C", "D")
CENARIOS = ("pess", "otim")


# ------------------------------------------------------------------- dados --
def carregar_barras() -> dict:
    """Agrupa barras M5 por dia local (America/Sao_Paulo), 09:00-15:25."""
    por_dia = defaultdict(list)
    with open(CSV, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            dt = datetime.fromtimestamp(int(linha["time"]), tz=timezone.utc)
            dt = dt.astimezone(FUSO_BR)
            if not (HORA_INI <= dt.time() <= HORA_FIM):
                continue
            por_dia[dt.date()].append((
                dt,
                float(linha["open"]), float(linha["high"]),
                float(linha["low"]), float(linha["close"]),
            ))
    return {dia: barras for dia, barras in sorted(por_dia.items())
            if len(barras) >= PERIODO + MAX_BARRAS}


def atr_diario(barras: list) -> list:
    """ATR Wilder por barra; semente = primeiro TR (igual ao robo)."""
    atrs = [None] * len(barras)
    anterior = None
    atr = None
    for i, (_, _, high, low, close) in enumerate(barras):
        if anterior is None:
            anterior = close
            continue
        tr = max(high - low, abs(high - anterior), abs(low - anterior))
        anterior = close
        atr = tr if atr is None else (((PERIODO - 1) * atr + tr) / PERIODO)
        atrs[i] = atr
    return atrs


def williams_r(barras: list, i: int) -> float | None:
    if i < PERIODO - 1:
        return None
    janela = barras[i - PERIODO + 1:i + 1]
    hh = max(b[2] for b in janela)
    ll = min(b[3] for b in janela)
    if hh == ll:
        return None
    return -100.0 * (hh - barras[i][4]) / (hh - ll)


# ------------------------------------------------------------------ sinal --
def sinais_do_dia(barras: list) -> list:
    """(indice_da_barra_de_sinal, lado, atr_m1eq) com trava de zona."""
    atrs = atr_diario(barras)
    zona = 0
    achados = []
    for i in range(PERIODO - 1, len(barras) - 1):
        wr = williams_r(barras, i)
        if wr is None:
            continue
        lado = None
        if wr <= WR_BUY and zona != 1:
            zona, lado = 1, 1
        elif wr >= WR_SELL and zona != -1:
            zona, lado = -1, -1
        elif WR_BUY < wr < WR_SELL:
            zona = 0
        if lado is None or not atrs[i] or atrs[i] <= 0:
            continue
        achados.append((i, lado, atrs[i] / FATOR_M1))
    return achados


def sl_tp(variante: str, atr_m1: float) -> tuple:
    if variante == "A0":
        return max(1.5 * atr_m1, 8.0), 3.0 * atr_m1
    if variante == "B":
        return max(1.5 * atr_m1, 3.0), 3.0 * atr_m1
    if variante == "C":
        return 8.0, 8.0
    if variante == "D":
        return 8.0, 12.0
    raise ValueError(variante)


def bruto_da_barra(variante: str, atr_m1: float, barras: list,
                   i_sinal: int, lado: int, cenario: str) -> float:
    """Pontos brutos. Entrada na abertura da barra seguinte, 0,5 contra."""
    i_entrada = i_sinal + 1
    entrada = barras[i_entrada][1] + lado * 0.5
    sl, tp = sl_tp(variante, atr_m1)
    nivel_sl = entrada - lado * sl
    nivel_tp = entrada + lado * tp
    limite = min(i_entrada + MAX_BARRAS, len(barras))

    for j in range(i_entrada, limite):
        _, _, high, low, close = barras[j]
        toca_sl = (low <= nivel_sl) if lado == 1 else (high >= nivel_sl)
        toca_tp = (high >= nivel_tp) if lado == 1 else (low <= nivel_tp)
        if not (toca_sl or toca_tp):
            continue
        if toca_sl:
            # gap: se abriu pior que o nivel, o fill e o pior preco da barra
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

    # sem SL/TP na janela de 30 min: fecha no ultimo close disponivel
    return lado * (barras[limite - 1][4] - entrada)


# -------------------------------------------------------------- metricas ---
def coletar_resultados() -> dict:
    """{(ano, variante, cenario, slip): [liquido pts]}."""
    resultados = defaultdict(list)
    n_sinais = 0
    for dia, barras in carregar_barras().items():
        for i, lado, atr_m1 in sinais_do_dia(barras):
            n_sinais += 1
            for variante in VARIANTES:
                for cenario in CENARIOS:
                    bruto = bruto_da_barra(
                        variante, atr_m1, barras, i, lado, cenario)
                    for slip in SLIPPAGES:
                        liquido = bruto - 2.0 * slip - CUSTO_PTS
                        resultados[(dia.year, variante, cenario, slip)].append(
                            liquido)
    return resultados, n_sinais


def metrica(valores: list) -> dict:
    if not valores:
        return {"n": 0, "acerto": 0.0, "payoff": None, "esperanca": 0.0}
    wins = [v for v in valores if v > 0]
    losses = [v for v in valores if v < 0]
    payoff = (mean(wins) / abs(mean(losses))) if wins and losses else None
    return {
        "n": len(valores),
        "acerto": 100.0 * len(wins) / len(valores),
        "payoff": payoff,
        "esperanca": mean(valores),
    }


def fmt(v, casas=2):
    return "n/d" if v is None else f"{v:.{casas}f}"


# ----------------------------------------------------------------- saida ---
def imprimir(resultados: dict, n_sinais: int) -> None:
    anos = sorted({k[0] for k in resultados})
    print("TRIAGEM M5 - PROXY DO SNIPER %R M1 (NAO PROMOVE, SO PODA)")
    print(f"CSV: {CSV.name} | sinais brutos: {n_sinais} | "
          f"anos: {anos[0]}-{anos[-1]}")
    print("Regras: %R(14) M5 -80/-20 com trava de zona; ATR M1 = ATR M5/sqrt(5);")
    print("        entrada na abertura seguinte (0,5 contra); janela 6 barras/30min;")
    print("        custo 0,12 pt + slippage por lado (0/0,5/1,0); SL e TP na mesma")
    print("        barra => cenario pessimista (SL) e otimista (TP).")

    print("\nTABELA PRINCIPAL - slippage 0,5 pt/lado (padrao do avaliador)")
    print(f"{'ano':>5} {'var':>4} {'n':>5} {'acerto':>8} {'payoff':>8} "
          f"{'E_pess':>9} {'E_otim':>9}")
    for ano in anos:
        for variante in VARIANTES:
            p = metrica(resultados[(ano, variante, "pess", SLIP_PADRAO)])
            o = metrica(resultados[(ano, variante, "otim", SLIP_PADRAO)])
            print(f"{ano:>5} {variante:>4} {p['n']:>5} "
                  f"{p['acerto']:>7.1f}% {fmt(p['payoff']):>8} "
                  f"{p['esperanca']:>+9.2f} {o['esperanca']:>+9.2f}")

    print("\nSENSIBILIDADE AO SLIPPAGE (todos os anos somados)")
    print(f"{'var':>4} {'cenario':>8} {'0.0':>9} {'0.5':>9} {'1.0':>9}")
    for variante in VARIANTES:
        for cenario in CENARIOS:
            vals = []
            for slip in SLIPPAGES:
                todos = [v for ano in anos
                         for v in resultados[(ano, variante, cenario, slip)]]
                vals.append(metrica(todos)["esperanca"])
            print(f"{variante:>4} {cenario:>8} " +
                  " ".join(f"{v:>+9.2f}" for v in vals))

    print("\nPODA (expectativa OTIMISTA <= 0; anos 2022-2026)")
    print(f"{'var':>4} {'slip':>5} {'anos<=0':>8} {'decisao':>14}")
    for variante in VARIANTES:
        for slip in SLIPPAGES:
            ruins = sum(
                1 for ano in ANOS_PODA
                if metrica(resultados[(ano, variante, "otim", slip)])[
                    "esperanca"] <= 0)
            decisao = "DESCARTAR" if ruins >= 4 else "manter na triagem"
            print(f"{variante:>4} {slip:>5.1f} {ruins:>5}/5 {decisao:>14}")

    print("\nLIMITACOES (obrigatorias)")
    print("- M5 nao resolve ordem dentro da barra: os dois cenarios (SL/TP")
    print("  primeiro) são limites, nao probabilidades. A realidade fica entre eles.")
    print("- CSV cobre so 09:00-15:25 BRT, sem leilao/after e sem 17:35.")
    print("- ATR M5/sqrt(5) e aproximacao; o Sniper real usa ATR de M1.")
    print("- Sem DOL, multi-TF, book, cooldown de 120 s nem veto de tendencia:")
    print("  o numero de sinais e maior que o do robo real.")
    print("- Sem bid/ask: fill e no mid +/- 0,5; o custo/slippage e aplicado")
    print("  como no avaliador congelado (2 sides), nao como spread real.")
    print("- Poda e irreversivel so nesta triagem; NAO e promocao. A decisao")
    print("  continua exigindo o shadow ao vivo pre-registrado (200 sinais/15 dias).")


if __name__ == "__main__":
    if not CSV.exists():
        sys.exit(f"CSV nao encontrado: {CSV}")
    res, total = coletar_resultados()
    imprimir(res, total)
