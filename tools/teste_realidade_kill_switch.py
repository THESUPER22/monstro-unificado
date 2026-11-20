# -*- coding: utf-8 -*-
"""Teste de realidade READ-ONLY do kill-switch (20/11/2026, feriado).

Nao cria ``parar.txt``, nao mata processo, nao fecha MT5 e nao escreve no repo.
Usa os deals REAIS de 19/11 do MT5 e a nova funcao pura
``agente_monstro_core.calcular_loss_com_deals`` com a data injetada.
O log do dia vem de ``aceite_pos_pregao.resolver_log`` (datado -> atual),
nao de um nome fixo.

Uso:
    python tools/teste_realidade_kill_switch.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time as dt_time

# basicConfig do agente abre o log na importacao: desvia para o dispositivo nulo.
os.environ.setdefault("MONSTRO_AGENTE_LOG", os.devnull)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import MetaTrader5 as mt5  # noqa: E402
import agente_monstro_core as ag  # noqa: E402
from aceite_pos_pregao import resolver_log  # noqa: E402
from pnl_dia import pnl_de_deals  # noqa: E402

DIA = date(2026, 11, 19)
LIMITE_1, LIMITE_2 = -250.0, -400.0
MINUTOS = (5, 20, 35, 50)  # grade REAL medida em agente_autonomo.log de 19/11


def deals_reais() -> list:
    if not mt5.initialize():
        raise SystemExit(f"MT5 nao inicializou: {mt5.last_error()}")
    try:
        ini = datetime.combine(DIA, dt_time.min)
        fim = datetime.combine(DIA, dt_time(23, 59, 59))
        return list(mt5.history_deals_get(ini, fim) or [])
    finally:
        mt5.shutdown()


def snapshots_do_dia(caminho: str) -> list:
    """Ultimos [pnl_dia] de 19/11, com o horario da linha."""
    achados = []
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for linha in f:
            m = ag.RE_PNL_DIARIO.search(linha)
            if not m or not m.group("quando").startswith(DIA.isoformat()):
                continue
            achados.append({
                "liquido": float(m.group("liquido")),
                "deals": int(m.group("deals")),
                "quando": datetime.strptime(
                    m.group("quando"), "%Y-%m-%d %H:%M:%S,%f"),
            })
    return achados


def nivel_de(acao: float) -> str:
    if acao <= LIMITE_2:
        return "N2"
    if acao <= LIMITE_1:
        return "N1"
    return "-"


def main() -> int:
    sinal_antes = os.path.exists(ag.PARAR)
    deals = deals_reais()
    magics = ag.magics_do_robo()
    liquido, n = pnl_de_deals(deals, DIA, magics)
    print(f"DEALS REAIS 19/11 (MT5): {liquido:+.2f} / {n} deals "
          f"(magics {sorted(magics)})")
    if (liquido, n) != (-1025.0, 54):
        print(f"ATENCAO: esperado -1025.00 / 54; obtido {liquido:+.2f} / {n}")

    caminho_log, motivo = resolver_log(BASE, DIA)
    if not caminho_log:
        raise SystemExit(f"log de {DIA.isoformat()} nao encontrado: {motivo}")
    snaps = snapshots_do_dia(caminho_log)
    print(f"LOG USADO: {os.path.basename(caminho_log)} ({motivo})")
    print(f"[pnl_dia] de 19/11 no log: {len(snaps)} linhas "
          f"(ultima {snaps[-1]['quando']:%H:%M:%S} {snaps[-1]['liquido']:+.2f})")
    print()
    cab = (f"{'HORA':<6} {'deals':>5} {'P&L deals':>10} {'[pnl_dia]':>10} "
           f"{'ate linha':>10} {'diverg.':>8} {'ACAO':>10} {'nivel':>5}")
    print(cab)
    print("-" * len(cab))

    primeiro_n1 = None
    for hora in range(9, 18):
        for minuto in MINUTOS:
            quando = datetime(DIA.year, DIA.month, DIA.day, hora, minuto)
            if quando > datetime(2026, 11, 19, 17, 20):
                continue
            snap = next((s for s in reversed(snaps) if s["quando"] <= quando), None)
            info = ag.calcular_loss_com_deals(
                deals, DIA, magics, snapshot=snap, agora=quando)
            nivel = nivel_de(info["acao"])
            if nivel != "-" and primeiro_n1 is None:
                primeiro_n1 = (quando, info, nivel)
            log_txt = f"{snap['liquido']:+.2f}" if snap else "-"
            ate_txt = (f"{info['pnl_ate_snapshot']:+.2f}"
                       if info["pnl_ate_snapshot"] is not None else "-")
            div_txt = (f"{info['divergencia']:+.2f}"
                       if info["divergencia"] is not None else "-")
            print(f"{quando:%H:%M}  {info['n_deals']:>5} "
                  f"{info['pnl_deals']:>+10.2f} {log_txt:>10} "
                  f"{ate_txt:>10} {div_txt:>8} "
                  f"{info['acao']:>+10.2f} {nivel:>5}")

    print()
    if primeiro_n1:
        quando, info, nivel = primeiro_n1
        print(f"PRIMEIRO ACIONAMENTO: {quando:%H:%M} -> {nivel} com acao "
              f"{info['acao']:+.2f} (deals {info['pnl_deals']:+.2f}, "
              f"[pnl_dia] {info['snapshot']['liquido']:+.2f})")
    else:
        print("NENHUM acionamento de nivel 1 na grade de 19/11")

    assert os.path.exists(ag.PARAR) == sinal_antes, "parar.txt foi alterado!"
    print("parar.txt NAO criado/alterado (nenhuma acao de parada executada)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
