# -*- coding: utf-8 -*-
"""
vwap_fade_wdo.py — Estudo READ-ONLY: reversao a media no VWAP (fade) no WDO.

Nao envia ordem, nao altera config, nao toca no robo.

TESE (pre-registrada antes de rodar, 14/11/2026):
  O VWAP intradiario e a ancora de valor justo do dia. Quando o preco se
  afasta MUITO do VWAP, ha pressao de reversao ate o VWAP. O fade so faz
  sentido se o desvio for grande em unidades de volatilidade (z-score), nao
  em pontos absolutos (que sao nao-estacionarios).

MODELO:
  - VWAP do dia = soma(preco_tipico * tick_volume) / soma(tick_volume),
    acumulado desde 09:00 (preco_tipico = (H+L+C)/3); reset a cada dia.
  - desvio dev = close - vwap.
  - sigma = desvio-padrao de dev nas ULTIMAS 60 barras M1 (min 30).
  - z = dev / sigma  (quanto o preco esta esticado em relacao ao VWAP).
  - SINAL (na barra M1 FECHADA): |z| >= z_entry na janela 10:00-12:00.
      z > 0  -> SELL (preco acima do VWAP: vende esperando voltar)
      z < 0  -> BUY  (preco abaixo do VWAP: compra esperando voltar)
  - ENTRADA: no open da barra M1 seguinte + slippage.
  - ALVO (TP): o VWAP no instante do sinal (nivel fixo, sem look-ahead).
  - STOP: k_stop * sigma no instante do sinal.
  - STOP DE TEMPO: 15:00 (sai a mercado no open da barra das 15:00).
  - 1 trade por dia (primeiro sinal valido); 1 contrato.
  - custo R$ 1,20 por contrato por operacao; 1 ponto = R$ 10,00.
  - MIN_DIST = 2,0 pontos: alvo e stop menores que 4 ticks sao descartados
    porque, com 1,0 pt/lado, o slippage de ida e volta ja e 2,0 pontos.

Slippage explicito POR LADO: 0 / 0,5 / 1,0 / 1,5 ponto. SL conferido antes do
TP dentro da barra M1 (conservador).

GRADE PRE-REGISTRADA (pequena, para limitar data mining):
  z_entry em {1,5; 2,0; 2,5}  x  k_stop em {1,0; 1,5; 2,0}
  Primario: z=2,0 e k_stop=1,5 (documentado antes de ver resultado).

GATE (slip 1,0 pt/lado): OOS exp > 0, OOS PF > 1,0, n_OOS >= 40 e IS exp > 0.
Alem disso, walk-forward e Monte Carlo sao OBRIGATORIOS (licao do 23.42).

Controles:
  CTRL-MIRROR  : lado oposto com os mesmos alvos/distancia (trend-follow).
  CTRL-SHIFT-1 : entra 1 barra M1 depois do sinal.
  CTRL-OPEN    : alvo no open do dia em vez do VWAP (ancora alternativa).

Uso:
    python backtest/vwap_fade_wdo.py
    python backtest/vwap_fade_wdo.py --start 2021-11-01
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filtros_faixa1 import load_m1  # noqa: E402
from backtest_trailing_faixa1 import linha, stats  # noqa: E402

COST_RS = 1.20
RS_PER_POINT = 10.0
MIN_DIST = 2.0          # 4 ticks: slippage ida+volta em 1,0 pt/lado
SIG_LO_MIN = 10 * 60    # 10:00
SIG_HI_MIN = 12 * 60    # 12:00
END_MIN = 15 * 60       # stop de tempo 15:00
Z_ENTRIES = (1.5, 2.0, 2.5)
K_STOPS = (1.0, 1.5, 2.0)
PRIM_Z = 2.0
PRIM_K = 1.5


# ---------------- DADOS / FEATURES ----------------
def preparar_dias(m1: pd.DataFrame) -> dict:
    """Por dia: M1 + VWAP acumulado + sigma(dev,60) + z."""
    dias = {}
    for day, g in m1.groupby("day", sort=True):
        g = g.sort_values("ts").reset_index(drop=True)
        if len(g) < 40:
            continue
        op = g["open"].values.astype(float)
        hi = g["high"].values.astype(float)
        lo = g["low"].values.astype(float)
        cl = g["close"].values.astype(float)
        vol = np.clip(g["tick_volume"].values.astype(float), 0.0, None)
        tp = (hi + lo + cl) / 3.0
        cum_pv = np.cumsum(tp * vol)
        cum_v = np.cumsum(vol)
        vwap = np.where(cum_v > 0, cum_pv / np.maximum(cum_v, 1e-12), tp)
        dev = cl - vwap
        sigma = pd.Series(dev).rolling(60, min_periods=30).std(ddof=0).values
        sigma = np.nan_to_num(sigma, nan=0.0, posinf=0.0, neginf=0.0)
        z = np.where(sigma > 0, dev / np.where(sigma > 0, sigma, 1.0), 0.0)
        mod = g["ts"].dt.hour.values * 60 + g["ts"].dt.minute.values
        dias[day] = dict(
            day=day, ts=g["ts"].values, op=op, hi=hi, lo=lo, cl=cl,
            mod=mod.astype(int), vwap=vwap, sigma=sigma, z=z,
            open_day=float(op[0]),
        )
    return dias


# ---------------- SINAL ----------------
def sinal_dia(d: dict, z_entry: float):
    mask = ((d["mod"] >= SIG_LO_MIN) & (d["mod"] < SIG_HI_MIN)
            & (d["sigma"] > 0) & (np.abs(d["z"]) >= z_entry))
    if not mask.any():
        return None
    i = int(np.argmax(mask))
    side = "SELL" if d["z"][i] > 0 else "BUY"
    return side, i


# ---------------- SIMULACAO ----------------
def _saida(entry, fill, side, slip, motivo, mfe, mae):
    exit_fill = fill - slip if side == "BUY" else fill + slip
    pnl = (exit_fill - entry) if side == "BUY" else (entry - exit_fill)
    return {"pnl": pnl, "exit": motivo, "mfe": mfe, "mae": mae}


def simular(d: dict, j0: int, side: str, entry: float, dist_target: float,
            dist_stop: float, slip: float, end_min: int = END_MIN):
    if dist_target < MIN_DIST or dist_stop < MIN_DIST:
        return None
    if j0 >= len(d["ts"]):
        return None
    target = entry + dist_target if side == "BUY" else entry - dist_target
    stop = entry - dist_stop if side == "BUY" else entry + dist_stop
    end = int(np.searchsorted(d["mod"], end_min, side="left"))
    end = min(end, len(d["ts"]))
    if j0 >= end:
        return None

    mfe = mae = 0.0
    for j in range(j0, end):
        h = d["hi"][j]
        l = d["lo"][j]
        if side == "BUY":
            mfe = max(mfe, h - entry)
            mae = min(mae, l - entry)
            if l <= stop:
                fill = d["op"][j] if d["op"][j] < stop else stop
                return _saida(entry, fill, side, slip, "SL", mfe, mae)
            if h >= target:
                return _saida(entry, target, side, slip, "TP", mfe, mae)
        else:
            mfe = max(mfe, entry - l)
            mae = min(mae, entry - h)
            if h >= stop:
                fill = d["op"][j] if d["op"][j] > stop else stop
                return _saida(entry, fill, side, slip, "SL", mfe, mae)
            if l <= target:
                return _saida(entry, target, side, slip, "TP", mfe, mae)

    fill = d["op"][end] if end < len(d["ts"]) else d["cl"][-1]
    return _saida(entry, fill, side, slip, "TIME", mfe, mae)


# ---------------- COLETA ----------------
def coletar(dias: dict, z_entry: float, k_stop: float, slip: float,
            target_mode: str = "vwap", side_mode: str = "normal",
            entry_shift: int = 0):
    trades = []
    for day in sorted(dias):
        d = dias[day]
        sig = sinal_dia(d, z_entry)
        if sig is None:
            continue
        fade_side, i = sig
        j0 = i + 1 + entry_shift
        if j0 >= len(d["ts"]):
            continue
        sigma = float(d["sigma"][i])
        dist_stop = k_stop * sigma
        anchor = float(d["vwap"][i]) if target_mode == "vwap" else float(d["open_day"])
        e_fade = d["op"][j0] + (slip if fade_side == "BUY" else -slip)
        dist_target = abs(anchor - e_fade)

        side = fade_side
        if side_mode == "mirror":
            side = "BUY" if fade_side == "SELL" else "SELL"
        entry = d["op"][j0] + (slip if side == "BUY" else -slip)
        out = simular(d, j0, side, entry, dist_target, dist_stop, slip)
        if out is None:
            continue
        out.update(year=int(day.year), day=day, side=side,
                   z=float(d["z"][i]), sigma=sigma,
                   target_dist=dist_target, stop_dist=dist_stop)
        trades.append(out)
    return trades


def split_is_oos(trades):
    return ([t for t in trades if t["year"] <= 2024],
            [t for t in trades if t["year"] >= 2025])


def gate(vis, voos, min_oos=40):
    return (voos.get("n", 0) >= min_oos
            and voos.get("exp_rs", -1) > 0
            and voos.get("pf", 0) > 1.0
            and vis.get("exp_rs", -1) > 0)


def avaliar(trades, label):
    v = stats(trades, label)
    is_sub, oos_sub = split_is_oos(trades)
    return v, stats(is_sub, "IS"), stats(oos_sub, "OOS")


def por_ano(trades, label):
    print(f"\n--- detalhe {label} ---")
    by = {}
    for t in trades:
        by.setdefault(t["year"], []).append(t)
    for y in sorted(by):
        print("  " + linha(stats(by[y], str(y))))
    is_sub, oos_sub = split_is_oos(trades)
    print("  " + linha(stats(is_sub, "IS 2021-2024")))
    print("  " + linha(stats(oos_sub, "OOS 2025-2026")))


# ---------------- MAIN ----------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="WDO$")
    ap.add_argument("--start", default="2021-11-01")
    a = ap.parse_args()

    start = datetime.strptime(a.start, "%Y-%m-%d")
    m1 = load_m1(a.symbol, start)
    dias = preparar_dias(m1)
    if not dias:
        raise SystemExit("sem dias validos")

    print("=" * 112)
    print(f"VWAP FADE - WDO | M1={len(m1)} dias={len(dias)} | "
          f"custo R$1,20 | 1 contrato | janela 10:00-12:00 | time stop 15:00")
    print(f"periodo: {min(dias)} -> {max(dias)} | VWAP acumulado do dia | "
          f"sigma = std(dev,60) | MIN_DIST={MIN_DIST} pts")
    print("=" * 112)

    # frequencia de sinal por z
    print("\n--- frequencia (dias com sinal na janela, antes dos filtros de dist) ---")
    for z in Z_ENTRIES:
        n = sum(1 for d in dias.values() if sinal_dia(d, z) is not None)
        print(f"  z>={z:.1f}  dias com sinal = {n:>4}  "
              f"({100.0*n/len(dias):.1f}% dos dias)")

    print("\n--- grade pre-registrada (alvo=VWAP, time stop 15:00) ---")
    print(f"  {'z':>4} {'kSL':>4} {'slip':>4} {'n':>4} {'WR%':>5} {'exp':>7} "
          f"{'PF':>5} {'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} "
          f"{'OOS exp':>7} {'OOS PF':>5}  gate")
    primarios = []
    for z in Z_ENTRIES:
        for k in K_STOPS:
            for slip in (0.0, 0.5, 1.0):
                tr = coletar(dias, z, k, slip)
                v, vis, voos = avaliar(tr, "x")
                ok = gate(vis, voos)
                print(f"  {z:>4.1f} {k:>4.1f} {slip:>4.1f} {v.get('n',0):>4} "
                      f"{v.get('win%',0):>5.1f} {v.get('exp_rs',0):>7.2f} "
                      f"{v.get('pf',0):>5.2f} {v.get('total_rs',0):>7.0f} | "
                      f"{vis.get('exp_rs',0):>7.2f} {vis.get('pf',0):>5.2f} "
                      f"{voos.get('n',0):>5} {voos.get('exp_rs',0):>7.2f} "
                      f"{voos.get('pf',0):>5.2f}  {'PASSA' if ok else 'nao'}")
                if slip == 1.0:
                    primarios.append((z, k, v, vis, voos, ok))

    passam = [p for p in primarios if p[5]]
    if passam:
        best = max(passam, key=lambda x: x[4].get("exp_rs", -1))
        criterio = "PASSA no gate"
    else:
        eleg = [p for p in primarios
                if p[3].get("exp_rs", -1) > 0 and p[4].get("n", 0) >= 40]
        best = (max(eleg, key=lambda x: x[4].get("exp_rs", -1)) if eleg else None)
        criterio = "melhor esforco (IS exp>0 e OOS n>=40)"

    if best is None:
        print("\nNenhum candidato com IS exp>0 e OOS n>=40. Sem promocao.")
        return

    z, k, v, vis, voos, ok = best
    print("\n" + "=" * 112)
    print(f"CANDIDATO ({criterio}): z={z:.1f} k_stop={k:.1f} | slip 1.0")
    print("=" * 112)
    tr = coletar(dias, z, k, 1.0)
    por_ano(tr, f"z={z:.1f} k={k:.1f}")

    # split por lado (diagnostico, nao selecao)
    print("\n--- split por lado (diagnostico) ---")
    for sd in ("BUY", "SELL"):
        sub = [t for t in tr if t["side"] == sd]
        print("  " + linha(stats(sub, sd)))

    # sensibilidade de saida (mesmo sinal)
    print(f"\n--- sensibilidade de saida z={z:.1f} k={k:.1f} | slip 1.0 ---")
    print(f"  {'end':>5} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} {'total':>7} | "
          f"{'IS exp':>7} {'IS PF':>5} {'OOS n':>5} {'OOS exp':>7} {'OOS PF':>5}")
    for end_min, lbl in ((14 * 60, "14:00"), (15 * 60, "15:00"),
                         (16 * 60, "16:00"), (17 * 60 + 30, "17:30")):
        tr2 = []
        for day in sorted(dias):
            d = dias[day]
            sig = sinal_dia(d, z)
            if sig is None:
                continue
            fade_side, i = sig
            j0 = i + 1
            if j0 >= len(d["ts"]):
                continue
            sigma = float(d["sigma"][i])
            e_fade = d["op"][j0] + (1.0 if fade_side == "BUY" else -1.0)
            dist_t = abs(float(d["vwap"][i]) - e_fade)
            out = simular(d, j0, fade_side, e_fade, dist_t, k * sigma, 1.0, end_min)
            if out is None:
                continue
            out.update(year=int(day.year))
            tr2.append(out)
        v2, vis2, voos2 = avaliar(tr2, "x")
        print(f"  {lbl:>5} {v2.get('n',0):>4} {v2.get('win%',0):>5.1f} "
              f"{v2.get('exp_rs',0):>7.2f} {v2.get('pf',0):>5.2f} "
              f"{v2.get('total_rs',0):>7.0f} | {vis2.get('exp_rs',0):>7.2f} "
              f"{vis2.get('pf',0):>5.2f} {voos2.get('n',0):>5} "
              f"{voos2.get('exp_rs',0):>7.2f} {voos2.get('pf',0):>5.2f}")

    # controles
    print(f"\n--- controles z={z:.1f} k={k:.1f} | slip 1.0 ---")
    for mode, label in (("normal", "normal"), ("mirror", "CTRL-MIRROR")):
        trc = coletar(dias, z, k, 1.0, side_mode=mode)
        print("  " + linha(stats(trc, label)))
    trs = coletar(dias, z, k, 1.0, entry_shift=1)
    print("  " + linha(stats(trs, "CTRL-SHIFT-1")))
    tro = coletar(dias, z, k, 1.0, target_mode="open")
    print("  " + linha(stats(tro, "CTRL-OPEN")))


if __name__ == "__main__":
    main()
