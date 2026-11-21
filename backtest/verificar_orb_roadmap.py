# -*- coding: utf-8 -*-
"""Diagnostico da divergencia ORB: entrada idealizada vs atrito real.

READ-ONLY. Exporta o continuo `WDO@` (antigo `WDO$`) do MT5 e repete a
variante canonica 10:30-11:00 do ROADMAP 23.20.2 de duas formas:

  (A) REPLICA: fill no nivel da caixa (como `entry_signal` de
      `backtest_orb_wdo.py`), saida 17:55, custo R$ 1,20;
  (B) ATRITO DO USUARIO: fill na abertura da barra seguinte + 0,5 contra,
      custo 0,12 pt + slippage 0/0,5/1,0 pt por lado.

Objetivo: separar "a tese nao tem edge" de "o edge some quando o fill e
realista", sem reativar nada.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triagem_m5_sltp import CUSTO_PTS, SLIPPAGES, metrica  # noqa: E402

EXPORT = Path(
    r"C:\AIOFEN\backtest\dados_mt5\baixa_tudo\filtrados"
    r"\WDO_CONTINUO_M5_exportado_2021_2026.csv"
)
INICIO = datetime(2021, 11, 1)
FIM = datetime(2026, 11, 20)
SIMBOLO = "WDO@"
CUSTO_RS = 1.20
RS_PT = 10.0


def carregar() -> dict:
    por_dia = defaultdict(list)
    with open(EXPORT, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            dt = datetime.fromtimestamp(int(linha["time"]), tz=timezone.utc)
            if not (9 <= dt.hour <= 18):
                continue
            por_dia[dt.date()].append((
                dt, float(linha["open"]), float(linha["high"]),
                float(linha["low"]), float(linha["close"]),
            ))
    return {d: b for d, b in sorted(por_dia.items()) if len(b) >= 100}


def sinal(barras: list):
    caixa = [b for b in barras if b[0].hour == 9]
    if len(caixa) < 8:
        return None
    hi = max(b[2] for b in caixa)
    lo = min(b[3] for b in caixa)
    if hi <= lo:
        return None
    for i, b in enumerate(barras):
        hm = (b[0].hour, b[0].minute)
        if hm < (10, 30):
            continue
        if hm >= (11, 0):
            break
        up, dn = b[2] > hi, b[3] < lo
        if up and dn:
            return None
        if up:
            return i, 1, hi, lo
        if dn:
            return i, -1, lo, hi
    return None


def simulada(barras: list, i0: int, lado: int, stop: float, entrada: float) -> float:
    """Pts brutos; comeca em i0, gap-through-stop so da 2a barra em diante."""
    eod_idx = max(j for j, b in enumerate(barras)
                  if (b[0].hour, b[0].minute) <= (17, 55))
    eod = barras[eod_idx][4]
    first = True
    for j in range(i0, len(barras)):
        _, op, high, low, _ = barras[j]
        gap = (not first) and (
            (op < stop) if lado == 1 else (op > stop))
        first = False
        if lado == 1:
            if low <= stop:
                return (op if gap else stop) - entrada
        else:
            if high >= stop:
                return entrada - (op if gap else stop)
    return (eod - entrada) if lado == 1 else (entrada - eod)


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init falhou: {mt5.last_error()}")
    try:
        rates = mt5.copy_rates_range(SIMBOLO, mt5.TIMEFRAME_M5, INICIO, FIM)
    finally:
        mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise SystemExit("sem dados WDO@ no periodo")
    campos = ["time", "open", "high", "low", "close", "tick_volume", "real_volume"]
    with open(EXPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in rates:
            w.writerow({c: r[c] for c in campos})
    print(f"exportadas {len(rates)} barras M5 de {SIMBOLO} -> {EXPORT.name}")

    # {(ano, modo, slip): [liquido pts]}
    res = defaultdict(list)
    for dia, barras in carregar().items():
        s = sinal(barras)
        if s is None:
            continue
        i, lado, nivel, stop = s
        # (A) replica ROADMAP: fill no nivel da caixa
        bruto_a = simulada(barras, i, lado, stop, nivel)
        # (B) atrito: proxima abertura + 0,5 contra
        if i + 1 >= len(barras):
            continue
        entrada_b = barras[i + 1][1] + lado * 0.5
        bruto_b = simulada(barras, i + 1, lado, stop, entrada_b)
        for slip in SLIPPAGES:
            res[(dia.year, "A_replica", slip)].append(
                bruto_a - CUSTO_RS / RS_PT - 2 * slip)
            res[(dia.year, "B_atrito", slip)].append(
                bruto_b - CUSTO_PTS - 2 * slip)

    print("\nDIAGNOSTICO - MESMO SINAL 10:30-11:00, DUAS FORMAS DE ENTRADA")
    print("A = fill no nivel da caixa (replica 23.20.2, saida 17:55, custo R$1,20)")
    print("B = abertura seguinte + 0,5 contra (atrito pedido), mesma saida 17:55")
    print(f"{'ano':>5} {'modo':>11} {'slip':>5} {'n':>5} {'acerto':>8} "
          f"{'E_pts':>9} {'E_R$':>9}")
    for ano in sorted({k[0] for k in res}):
        for modo in ("A_replica", "B_atrito"):
            for slip in (0.0, 0.5, 1.0):
                v = res[(ano, modo, slip)]
                m = metrica(v)
                e = m["esperanca"]
                print(f"{ano:>5} {modo:>11} {slip:>5.1f} {m['n']:>5} "
                      f"{m['acerto']:>7.1f}% {e:>+9.2f} {e*10:>+9.2f}")
    print("\nReferencia 23.20.2 (modo A, sem slippage explicito):")
    print("  n 190/176/164/175/142 (2022-2026); exp R$ 101/30/74/44/24; PF 1,62/1,25/1,67/1,41/1,25")
    print("\nLEITURA: se A reproduce o ROADMAP e B vira negativo, o edge estava no")
    print("fill idealizado no nivel da caixa, nao no sinal - reforca 23.41.")


if __name__ == "__main__":
    main()
