#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_quarentena.py

Monitoramento READ-ONLY do Protocolo de Quarentena (Blindagem 04/09/2026).

Nao altera NENHUM arquivo. Apenas le:
  - logs/modelo_a_shadow.csv           (Shadow Mode / Modelo A)
  - logs/rompimento/rompimento_trades.csv   (Faixa 1 - Rompimento 1a Hora)

Calcula o progresso rumo as 3 metas do protocolo:
  1. Core v22: n >= 100 trades com PnL fechado APOS 04/09/2026.
  2. Modelo A : correlacao Pearson prob_modelo_a x resultado >= 0.15.
  3. Rompimento: n >= 30, WR >= 45%, PF >= 1.1, MaxDD <= R$ 3.600.

Uso: python analisar_quarentena.py
"""
import csv
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SHADOW_CSV = os.path.join(BASE, "logs", "modelo_a_shadow.csv")
ROMPIMENTO_CSV = os.path.join(BASE, "logs", "rompimento", "rompimento_trades.csv")

CUTOFF_CORE = "2026-09-04"          # marcador de quarentena
META_N_CORE = 100
META_CORR = 0.15
META_N_RP = 30
META_WR_RP = 0.45
META_PF_RP = 1.1
META_MAXDD_RP = 3600.0
# Valor do ponto WDO (R$/ponto por contrato) para projecoes de PnL
R_POR_PONTO = 10.0
# Lote padrao da Faixa 1 - Rompimento 1H (5 contratos WDO)
LOTE_ROMPIMENTO = 5.0

# Tickets da anomalia 03/09 (nao cabe na contagem de trades do Core)
ANOMALIA_INICIO = "2026-09-03 11:15"
ANOMALIA_FIM = "2026-09-03 11:30"


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _corr(xs, ys):
    """Correlacao de Pearson (statistics puro, sem dependencia)."""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def _col(s):
    return s.strip().lower()


def analisar_shadow():
    if not os.path.exists(SHADOW_CSV):
        print("  (shadow CSV nao encontrado)")
        return
    linhas = []
    with open(SHADOW_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            linhas.append({
                "ts": r.get("timestamp", "").strip(),
                "ticket": str(r.get("ticket_mt5", "")).strip(),
                "dir": _col(r.get("direcao", "")),
                "prob": _to_float(r.get("prob_modelo_a")),
                "res": _to_float(r.get("resultado_bruto")),
            })

    anteriory = [l for l in linhas if l["res"] is not None and not (
        ANOMALIA_INICIO <= l["ts"] <= ANOMALIA_FIM)]

    # Core apos o marcador: trades com PnL fechado
    posy = [l for l in linhas if l["ts"] >= CUTOFF_CORE and l["res"] is not None]
    posy_total = [l for l in linhas if l["ts"] >= CUTOFF_CORE]
    anomalia = [l for l in linhas if ANOMALIA_INICIO <= l["ts"] <= ANOMALIA_FIM]

    print("== SHADOW MODE / MODELO A ==")
    print(f"  registros totais no CSV : {len(linhas)}")
    print(f"  trades na anomalia 03/09: {len(anomalia)}")
    print(f"  Core pos-{CUTOFF_CORE} (todos)      : {len(posy_total)}")
    print(f"  Core pos-{CUTOFF_CORE} (P&L fechado): {len(posy)}  [meta n>={META_N_CORE}]")

    # Correlacao Pearson (base expandida: todos com PnL, ex-anomalia)
    pares = [(l["prob"], l["res"]) for l in anteriory
             if l["prob"] is not None and l["res"] is not None]
    if len(pares) >= 3:
        r_full = _corr([p[0] for p in pares], [p[1] for p in pares])
        print(f"  corr prob vs PnL (todos) : {r_full:+.4f}")
    else:
        print("  corr prob vs PnL (todos) : amostra insuficiente")

    # Correlacao pos-marcador
    pares_pos = [(l["prob"], l["res"]) for l in posy
                 if l["prob"] is not None and l["res"] is not None]
    if len(pares_pos) >= 3:
        r_pos = _corr([p[0] for p in pares_pos], [p[1] for p in pares_pos])
        print(f"  corr prob vs PnL (pos-{CUTOFF_CORE}): {r_pos:+.4f}  [meta corr>={META_CORR}]")
    else:
        print(f"  corr prob vs PnL (pos-{CUTOFF_CORE}): amostra insuficiente")

    if posy:
        wins = sum(1 for l in posy if l["res"] > 0)
        gp = sum(l["res"] for l in posy if l["res"] > 0)
        gl = abs(sum(l["res"] for l in posy if l["res"] < 0))
        pf = (gp / gl) if gl else float("inf")
        net = sum(l["res"] for l in posy)
        print(f"  WR pos-{CUTOFF_CORE}: {wins}/{len(posy)} = {wins/len(posy)*100:.1f}% | "
              f"PF {pf if pf != float('inf') else 'inf':.2f} | net R$ {net:+.2f}")


def analisar_rompimento():
    if not os.path.exists(ROMPIMENTO_CSV):
        print("  (rompimento_trades.csv nao encontrado)")
        return
    linhas = []
    with open(ROMPIMENTO_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            linhas.append(r)

    # Filtra registros sem trade efetivo (S/TRADE = caixa sem gatilho)
    trades_rp = []
    for r in linhas:
        saida = _col(r.get("saida", ""))
        if saida in ("s/trade", ""):
            continue
        trades_rp.append(r)

    # Projeta PnL em R$ a partir de 'pts': 1 pt = R$10/conta; lote = 5 contratos
    resultados = []
    for r in trades_rp:
        pts = _to_float(r.get("pts"))
        if pts is None:
            continue
        resultados.append(pts * LOTE_ROMPIMENTO * R_POR_PONTO)

    print("== FAIXA 1 - ROMPIMENTO 1H (magic 7008) ==")
    print(f"  linhas no CSV (inclui S/TRADE): {len(linhas)}")
    print(f"  trades validos no CSV: {len(trades_rp)}")
    print(f"  trades com 'pts' preenchido: {len(resultados)}  [meta n>={META_N_RP}]")

    if resultados:
        wins = sum(1 for x in resultados if x > 0)
        gp = sum(x for x in resultados if x > 0)
        gl = abs(sum(x for x in resultados if x < 0))
        pf = (gp / gl) if gl else float("inf")
        # MaxDD aproximado (equity incremental)
        eq = 0.0
        pico = 0.0
        dd = 0.0
        for x in resultados:
            eq += x
            pico = max(pico, eq)
            dd = min(dd, eq - pico)
        wr = wins / len(resultados) if resultados else 0.0
        pf_txt = f"{pf:.2f}" if pf != float("inf") else "inf"
        print(f"  WR: {wins}/{len(resultados)} = {wr*100:.1f}%  [>= {META_WR_RP*100:.0f}%]")
        print(f"  PF: {pf_txt}  [>= {META_PF_RP}]")
        print(f"  MaxDD (R$): {dd:.2f}  [>= -{META_MAXDD_RP:.0f}]")
        print(f"  Net (R$): {sum(resultados):+.2f}")
    else:
        print("  (sem trades validos com PnL ainda)")


def main():
    print("=" * 62)
    print("ANALISADOR DE QUARENTENA — Protocolo 04/09/2026")
    print("(modo somente-leitura; nenhum arquivo e alterado)")
    print("=" * 62)
    analisar_shadow()
    print()
    analisar_rompimento()
    print()
    print("Metas: Core n>=100 | corr>=0.15 | Rompimento n>=30, WR>=45%, PF>=1.1, MaxDD<=R$3.600")
    return 0


if __name__ == "__main__":
    sys.exit(main())