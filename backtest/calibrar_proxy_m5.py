# -*- coding: utf-8 -*-
"""Calibracao do proxy M5 do Sniper %R contra deals reais (03-19/11/2026).

READ-ONLY: so le barras/deals do MT5 e escreve um CSV local de exportacao.
Nao envia ordem, nao altera config, nao toca no robo.

Comparacoes:
  1. agregada por dia: n, acerto, E bruta e E liquida (real vs proxy A0);
  2. casamento sinal-a-sinal: mesma barra M5 de entrada + mesmo lado;
  3. veredito: o proxy reproduce (ou nao) o sinal e o resultado do vivo.

Convencao de relogio (ROADMAP 23.20.1): o terminal gravou 09-18 "UTC" que
ja sao 09-18 BRT de parede. Por isso NAO se aplica astimezone(FUSO_BR) nem
aos deals nem as barras exportadas aqui.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

import MetaTrader5 as mt5

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triagem_m5_sltp import (  # noqa: E402
    CUSTO_PTS, SLIPPAGES, SLIP_PADRAO,
    bruto_da_barra, carregar_barras_mt5, metrica, sinais_do_dia,
)

EXPORT = Path(
    r"C:\AIOFEN\backtest\dados_mt5\baixa_tudo\filtrados"
    r"\WDOZ26_M5_exportado_2026-11-03_2026-11-19.csv"
)
INICIO = datetime(2026, 11, 3)
FIM = datetime(2026, 11, 20)   # exclusivo
SIMBOLO = "WDOZ26"
MAGIC = 123456
VARIANTE = "A0"


def exportar_barras() -> None:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init falhou: {mt5.last_error()}")
    try:
        rates = mt5.copy_rates_range(SIMBOLO, mt5.TIMEFRAME_M5, INICIO, FIM)
        if rates is None or len(rates) == 0:
            raise SystemExit("sem barras M5 no periodo pedido")
        campos = ["time", "open", "high", "low", "close", "tick_volume", "real_volume"]
        with open(EXPORT, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            for r in rates:
                w.writerow({c: r[c] for c in campos})
        print(f"exportadas {len(rates)} barras M5 -> {EXPORT.name}")
    finally:
        mt5.shutdown()


def deals_reais() -> dict:
    """{position_id: dict(lado, entrada, resultado_pts, data, hora, n_deals)}."""
    if not mt5.initialize():
        raise SystemExit(f"MT5 init falhou: {mt5.last_error()}")
    try:
        ds = mt5.history_deals_get(INICIO, FIM)
    finally:
        mt5.shutdown()
    if ds is None:
        raise SystemExit("sem deals no periodo")

    por_pid = defaultdict(list)
    for d in ds:
        if d.magic != MAGIC or d.symbol != SIMBOLO:
            continue
        por_pid[d.position_id].append(d)

    trades = {}
    for pid, ds_pid in por_pid.items():
        ds_pid.sort(key=lambda d: d.time)
        aberturas = [d for d in ds_pid if d.entry == mt5.DEAL_ENTRY_IN]
        if not aberturas:
            continue
        ab = aberturas[0]
        dt = datetime.fromtimestamp(ab.time, tz=timezone.utc)
        resultado_rs = sum(d.profit + d.commission + d.swap + d.fee
                           for d in ds_pid)
        trades[pid] = dict(
            lado=1 if ab.type == mt5.DEAL_TYPE_BUY else -1,
            entrada_dt=dt,
            data=dt.date(),
            hora=dt.time(),
            resultado_pts=resultado_rs / 10.0,
            n_deals=len(ds_pid),
        )
    return trades


def barra_de(t: datetime.time) -> int:
    return t.hour * 12 + t.minute // 5


def ponto_entrada(barras: list, i: int) -> datetime:
    return barras[i + 1][0]


def main() -> None:
    exportar_barras()
    por_dia = carregar_barras_mt5(EXPORT)
    trades = deals_reais()

    # sinais proxy por dia -> entrada prevista na abertura da barra seguinte
    sinais = {}
    for dia, barras in por_dia.items():
        sinais[dia] = [
            dict(i=i, lado=lado, atr=atr,
                 entrada_dt=ponto_entrada(barras, i),
                 bruto_pess=bruto_da_barra(VARIANTE, atr, barras, i, lado, "pess"),
                 bruto_otim=bruto_da_barra(VARIANTE, atr, barras, i, lado, "otim"))
            for i, lado, atr in sinais_do_dia(barras)
        ]

    # casamento: mesma barra M5 de entrada (tolerancia 0) e mesmo lado.
    # 'tol=1' permite uma barra de diferenca (sensibilidade).
    casados = {}
    for tol in (0, 1):
        usados = defaultdict(set)   # indice do sinal dentro do dia
        mapa = {}
        for pid, t in sorted(trades.items(), key=lambda kv: kv[1]["entrada_dt"]):
            melhor = None
            for k, s in enumerate(sinais.get(t["data"], [])):
                if s["lado"] != t["lado"] or k in usados[t["data"]]:
                    continue
                diff = abs(barra_de(s["entrada_dt"].time()) -
                           barra_de(t["hora"]))
                if diff <= tol and (melhor is None or diff < melhor[0]):
                    melhor = (diff, k, s)
            if melhor:
                usados[t["data"]].add(melhor[1])
                mapa[pid] = melhor[2]
        casados[tol] = mapa

    # ---------------- tabela 1: por dia ----------------
    print("\nTABELA 1 - CALIBRACAO DO PROXY M5 vs DEALS REAIS (por dia)")
    print(f"simbolo {SIMBOLO} magic {MAGIC} | variante proxy {VARIANTE} | "
          f"slippage {SLIP_PADRAO} pt/lado")
    print(f"{'dia':>11} {'n_real':>6} {'n_proxy':>7} {'casados':>7} "
          f"{'acerto%':>8} {'E_bruta':>9} {'E_liq':>9} "
          f"{'proxy_pess':>11} {'proxy_otim':>11}")
    for dia in sorted(set(t["data"] for t in trades.values()) | set(por_dia)):
        reais = [t for t in trades.values() if t["data"] == dia]
        Br = [t["resultado_pts"] for t in reais]
        Lr = [v - CUSTO_PTS - 2 * SLIP_PADRAO for v in Br]
        sig = sinais.get(dia, [])
        Pp = [s["bruto_pess"] - CUSTO_PTS - 2 * SLIP_PADRAO for s in sig]
        Po = [s["bruto_otim"] - CUSTO_PTS - 2 * SLIP_PADRAO for s in sig]
        acerto = 100.0 * sum(1 for v in Br if v > 0) / len(Br) if Br else 0.0
        nc = sum(1 for pid, t in trades.items()
                 if t["data"] == dia and pid in casados[0])
        print(f"{str(dia):>11} {len(Br):>6} {len(sig):>7} {nc:>7} "
              f"{acerto:>7.1f}% {(mean(Br) if Br else 0):>+9.2f} "
              f"{(mean(Lr) if Lr else 0):>+9.2f} "
              f"{(mean(Pp) if Pp else 0):>+11.2f} "
              f"{(mean(Po) if Po else 0):>+11.2f}")

    def linha_total(titulo: str, valores: list) -> None:
        m = metrica(valores)
        print(f"{titulo:<30} n={m['n']:>4} acerto={m['acerto']:>5.1f}% "
              f"payoff={m['payoff'] if m['payoff'] is not None else float('nan'):>5.2f} "
              f"E={m['esperanca']:>+7.2f}")

    Br_all = [t["resultado_pts"] for t in trades.values()]
    Lr_all = [v - CUSTO_PTS - 2 * SLIP_PADRAO for v in Br_all]
    sig_all = [s for dia in sorted(sinais) for s in sinais[dia]]
    Pp_all = [s["bruto_pess"] - CUSTO_PTS - 2 * SLIP_PADRAO for s in sig_all]
    Po_all = [s["bruto_otim"] - CUSTO_PTS - 2 * SLIP_PADRAO for s in sig_all]
    print("\nTOTAIS 03/11-19/11")
    linha_total("real BRUTO", Br_all)
    linha_total("real LIQUIDO (0,5/lado)", Lr_all)
    linha_total("proxy A0 PESS (0,5/lado)", Pp_all)
    linha_total("proxy A0 OTIM (0,5/lado)", Po_all)

    # ---------------- tabela 2: casamento ----------------
    print("\nTABELA 2 - CASAMENTO SINAL A SINAL (mesma barra M5 + mesmo lado)")
    for tol in (0, 1):
        mp = casados[tol]
        resultados = [trades[pid]["resultado_pts"] for pid in mp]
        buy = sum(1 for pid in mp if trades[pid]["lado"] == 1)
        sell = len(mp) - buy
        print(f"tolerancia {tol} barra(s): casados {len(mp)}/{len(trades)} "
              f"({100.0*len(mp)/max(1,len(trades)):.1f}% dos trades reais) | "
              f"BUY {buy} / SELL {sell} | "
              f"E bruta dos casados {mean(resultados) if resultados else 0:+.2f} pts")
    print("\nCobertura do proxy sobre os sinais reais (que trades reais o proxy "
          "conseguiu explicar):")
    print("- 0 barras = a barra de entrada do proxy bate exatamente com a barra "
          "do deal de entrada real;")
    print("- 1 barra = tolerancia de 5 min para atraso de execucao/feed.")
    # ---------- sensibilidade: sinal sem trava de zona + casamento por parte ----------
    from triagem_m5_sltp import FATOR_M1, WR_BUY, WR_SELL, PERIODO, atr_diario, williams_r

    sinais_livres = {}
    for dia, barras in por_dia.items():
        atrs = atr_diario(barras)
        achados = []
        anterior = 0
        for i in range(PERIODO - 1, len(barras) - 1):
            wr = williams_r(barras, i)
            if wr is None:
                continue
            lado = 1 if wr <= WR_BUY else (-1 if wr >= WR_SELL else 0)
            if lado and lado != anterior and atrs[i] and atrs[i] > 0:
                achados.append(dict(i=i, lado=lado, atr=atrs[i] / FATOR_M1,
                                    entrada_dt=barras[i + 1][0]))
            if lado:
                anterior = lado
        sinais_livres[dia] = achados

    def casar(sig_map, exigir_lado: bool, exigir_hora: bool) -> int:
        usados = defaultdict(set)
        n = 0
        for pid, t in sorted(trades.items(), key=lambda kv: kv[1]["entrada_dt"]):
            for k, s in enumerate(sig_map.get(t["data"], [])):
                if k in usados[t["data"]]:
                    continue
                if exigir_lado and s["lado"] != t["lado"]:
                    continue
                if exigir_hora and barra_de(s["entrada_dt"].time()) != barra_de(t["hora"]):
                    continue
                usados[t["data"]].add(k)
                n += 1
                break
        return n

    print("\nTABELA 3 - DECOMPOSICAO DO CASAMENTO (o que o proxy consegue explicar)")
    print(f"{'proxy':>10} {'lado+hora':>10} {'so lado':>9} {'so hora':>9} {'n_proxy':>8}")
    for nome, sm in (("com trava", sinais), ("sem trava", sinais_livres)):
        nlh = casar(sm, True, True)
        nsl = casar(sm, True, False)
        nsh = casar(sm, False, True)
        print(f"{nome:>10} {nlh:>10} {nsl:>9} {nsh:>9} "
              f"{sum(len(v) for v in sm.values()):>8}")
    print(f"{'real':>10} {len(trades):>10} {len(trades):>9} {len(trades):>9} {'':>8}")

    print("\nLIMITACOES: o proxy usa %R M5 (com/sem trava de zona), sem DOL, "
          "multi-TF, book, cooldown ou veto; o vivo usa %R M1 e gates. "
          "Mesmo casando hora e lado, o resultado depende do SL/TP real, "
          "que o proxy so aproxima.")


if __name__ == "__main__":
    main()
