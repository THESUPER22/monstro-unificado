#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_quarentena.py

Monitoramento READ-ONLY do Protocolo de Quarentena (Blindagem 04/09/2026).

Nao altera NENHUM arquivo. Apenas le:
  - logs/modelo_a_shadow.csv          (Shadow Mode / Modelo A)
  - logs/sete_velas_trades.csv        (incubacao 7 Velas)

Calcula o progresso rumo as 3 metas do protocolo:
  1. Core v22: n >= 100 trades com PnL fechado APOS 04/09/2026.
  2. Modelo A : correlacao Pearson prob_modelo_a x resultado >= 0.15.
  3. 7 Velas  : n >= 30, WR >= 45%, PF >= 1.1, MaxDD <= R$ 3.600.

Uso: python analisar_quarentena.py
"""
import csv
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SHADOW_CSV = os.path.join(BASE, "logs", "modelo_a_shadow.csv")
SETE_VELAS_CSV = os.path.join(BASE, "logs", "sete_velas_trades.csv")

CUTOFF_CORE = "2026-09-04"          # marcador de quarentena
META_N_CORE = 100
META_CORR = 0.15
META_N_SV = 30
META_WR_SV = 0.45
META_PF_SV = 1.1
META_MAXDD_SV = 3600.0
# Valor do ponto WDO (R$/ponto por contrato) para projecoes de PnL
R_POR_PONTO = 10.0
# Lote padrao do orquestrador 7 Velas (5 contratos WDO)
LOTE_SETE_VELAS = 5.0

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


def analisar_sete_velas():
    if not os.path.exists(SETE_VELAS_CSV):
        print("  (sete_velas_trades.csv nao encontrado)")
        return
    linhas = []
    with open(SETE_VELAS_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            linhas.append(r)

    # Filtra linhas de veto (nao sao trades)
    trades_sv = []
    for r in linhas:
        motivo = _col(r.get("motivo", ""))
        if "vetado" in motivo or "macro" in motivo or "sem_dados" in motivo:
            continue
        trades_sv.append(r)

    # Projeta PnL em R$ a partir de 'pts' (se preenchido), senao reporta vazio
    resultados = []
    for r in trades_sv:
        pts = _to_float(r.get("pts"))
        if pts is None:
            continue
        # pts em pontos WDO: 1 pt = R$10/conta; lote 7 Velas = 5 contratos
        resultados.append(pts * LOTE_SETE_VELAS * R_POR_PONTO)

    print("== INCUBACAO SETE VELAS ==")
    print(f"  linhas no CSV (com v0 abertas/vetos inclusos): {len(linhas)}")
    print(f"  trades validos (sem veto) no CSV: {len(trades_sv)}")
    print(f"  trades com 'pts' preenchido: {len(resultados)}  [meta n>={META_N_SV}]")

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
        print(f"  WR: {wins}/{len(resultados)} = {wr*100:.1f}%  [>= {META_WR_SV*100:.0f}%]")
        print(f"  PF: {pf_txt}  [>= {META_PF_SV}]")
        print(f"  MaxDD (R$): {dd:.2f}  [>= -{META_MAXDD_SV:.0f}]")
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
    analisar_sete_velas()
    print()
    print("Metas: Core n>=100 | corr>=0.15 | 7Velas n>=30, WR>=45%, PF>=1.1, MaxDD<=R$3.600")
    return 0


if __name__ == "__main__":
    sys.exit(main())