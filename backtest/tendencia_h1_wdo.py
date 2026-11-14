# -*- coding: utf-8 -*-
"""
tendencia_h1_wdo.py — Estudo READ-ONLY: tese de tendencia/momentum em H1 (WDO).

Nao envia ordem, nao altera config, nao toca no robo.

Pergunta: existe edge de tendencia em H1 no WDO, com poucos trades e stop mais
largo, que sobreviva ao custo real (R$ 1,20) e a 1 tick/lado de slippage?

Modelo:
  - barras H1 construidas do M1, apenas 09:00-17:30 (day trade);
  - sinal na barra H1 FECHADA; entrada no primeiro M1 seguinte (open);
  - SL = k_atr * ATR14(H1)  (TR nao atravessa o gap overnight);
  - TP = m * R (ou sem TP, saida no EOD 17:30);
  - uma operacao por dia (primeiro sinal), 1 contrato;
  - custo R$ 1,20 por contrato por operacao; 1 ponto = R$ 10,00;
  - SL conferido antes do TP dentro da barra M1 (conservador).

Sinais pre-registrados (poucos, para limitar data mining):
  donchian_N : rompe maxima/minima das N barras H1 anteriores
  ema_f_s    : cruzamento de EMA(f) x EMA(s) em H1
  mom_K      : close - close[K] > 0,5 * ATR (momentum)

Gate (slippage 1,0 pt/lado): OOS exp > 0, OOS PF > 1,0, n_OOS >= 40 e
IS exp > 0. IS = 2021-2024; OOS = 2025-2026.

Uso:
    python backtest/tendencia_h1_wdo.py
    python backtest/tendencia_h1_wdo.py --start 2021-11-01
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
EOD_HM = "17:30"
LAST_SIGNAL_HOUR = 16  # barra 16:00 fecha 17:00; ainda da tempo ate o EOD

SINAIS = (
    ("donchian_12", "donchian", 12),
    ("donchian_24", "donchian", 24),
    ("donchian_36", "donchian", 36),
    ("ema_8_21", "ema", (8, 21)),
    ("ema_12_34", "ema", (12, 34)),
    ("ema_20_50", "ema", (20, 50)),
    ("mom_6", "mom", 6),
    ("mom_12", "mom", 12),
)


# ---------------- H1 ----------------
def build_h1(m1: pd.DataFrame) -> pd.DataFrame:
    m1 = m1.copy()
    m1["hour"] = m1["ts"].dt.floor("h")
    rows = []
    for (day, hour), g in m1.groupby(["day", "hour"], sort=True):
        g = g.sort_values("ts")
        rows.append(dict(
            day=day, hour=hour, start=hour,
            end=hour + pd.Timedelta(hours=1),
            open=float(g["open"].iloc[0]),
            high=float(g["high"].max()),
            low=float(g["low"].min()),
            close=float(g["close"].iloc[-1]),
        ))
    h1 = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)

    # ATR14 de Wilder; TR da primeira barra do dia = high-low (sem gap overnight)
    atrs = []
    trs = []
    atr = 0.0
    prev_close = None
    prev_day = None
    for r in h1.itertuples():
        hi, lo, cl = r.high, r.low, r.close
        if prev_day is None or r.day != prev_day:
            tr = hi - lo
        else:
            tr = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close))
        if len(trs) < 14:
            trs.append(tr)
            atr = float(np.mean(trs))
        else:
            atr = (13.0 * atr + tr) / 14.0
        atrs.append(atr)
        prev_close = cl
        prev_day = r.day
    h1["atr"] = atrs
    return h1


# ---------------- SINAIS ----------------
def _ema(arr: np.ndarray, span: int) -> np.ndarray:
    return pd.Series(arr).ewm(span=span, adjust=False).mean().values


def gerar_sinal(h1: pd.DataFrame, familia: str, param) -> np.ndarray:
    hi = h1["high"].values
    lo = h1["low"].values
    cl = h1["close"].values
    atr = h1["atr"].values
    n = len(h1)
    out = np.zeros(n, dtype=int)

    if familia == "donchian":
        N = int(param)
        for i in range(N, n):
            if cl[i] > hi[i - N:i].max():
                out[i] = 1
            elif cl[i] < lo[i - N:i].min():
                out[i] = -1

    elif familia == "ema":
        f, s = param
        ef = _ema(cl, f)
        es = _ema(cl, s)
        for i in range(1, n):
            if ef[i] > es[i] and ef[i - 1] <= es[i - 1]:
                out[i] = 1
            elif ef[i] < es[i] and ef[i - 1] >= es[i - 1]:
                out[i] = -1

    elif familia == "mom":
        K = int(param)
        for i in range(K, n):
            if atr[i] <= 0:
                continue
            d = cl[i] - cl[i - K]
            if d > 0.5 * atr[i]:
                out[i] = 1
            elif d < -0.5 * atr[i]:
                out[i] = -1
    return out


# ---------------- SIMULACAO ----------------
def _saida(entry, fill, side, slip, motivo, mfe, mae):
    exit_fill = fill - slip if side == "BUY" else fill + slip
    pnl = (exit_fill - entry) if side == "BUY" else (entry - exit_fill)
    return {"pnl": pnl, "exit": motivo, "mfe": mfe, "mae": mae}


def simular(dia_m1, entry_idx, side, entry, stop_dist, tp_r, slip):
    ts = dia_m1["ts"]
    op, hi, lo, cl = dia_m1["open"], dia_m1["high"], dia_m1["low"], dia_m1["close"]
    eod_idx = int(np.searchsorted(
        ts, np.datetime64(str(dia_m1["day"]) + "T" + EOD_HM + ":00"), side="left"))
    end = min(eod_idx, len(ts))
    if entry_idx >= end:
        return None

    entry_fill = entry + (slip if side == "BUY" else -slip)
    stop = entry_fill - stop_dist if side == "BUY" else entry_fill + stop_dist
    tp = None
    if tp_r is not None:
        tp = (entry_fill + tp_r * stop_dist if side == "BUY"
              else entry_fill - tp_r * stop_dist)

    mfe = mae = 0.0
    last_close = float(cl[entry_idx])
    for j in range(entry_idx, end):
        last_close = float(cl[j])
        h = float(hi[j])
        l = float(lo[j])
        if side == "BUY":
            mfe = max(mfe, h - entry_fill)
            mae = min(mae, l - entry_fill)
            if l <= stop:
                fill = float(op[j]) if float(op[j]) < stop else stop
                return _saida(entry_fill, fill, side, slip, "SL", mfe, mae)
            if tp is not None and h >= tp:
                return _saida(entry_fill, tp, side, slip, "TP", mfe, mae)
        else:
            mfe = max(mfe, entry_fill - l)
            mae = min(mae, entry_fill - h)
            if h >= stop:
                fill = float(op[j]) if float(op[j]) > stop else stop
                return _saida(entry_fill, fill, side, slip, "SL", mfe, mae)
            if tp is not None and l <= tp:
                return _saida(entry_fill, tp, side, slip, "TP", mfe, mae)

    fill = float(op[eod_idx]) if eod_idx < len(ts) else last_close
    return _saida(entry_fill, fill, side, slip, "EOD", mfe, mae)


# ---------------- COLETA ----------------
def preparar_dias(h1: pd.DataFrame, m1: pd.DataFrame):
    """Lista de dias com barras H1 e M1 indexadas."""
    m1_by_day = {}
    for day, g in m1.groupby("day"):
        g = g.sort_values("ts")
        m1_by_day[day] = dict(
            day=day,
            ts=g["ts"].values,
            open=g["open"].values.astype(float),
            high=g["high"].values.astype(float),
            low=g["low"].values.astype(float),
            close=g["close"].values.astype(float),
        )
    return m1_by_day


def coletar(h1, m1_by_day, sinal, k_atr, tp_r, slip, side_mode="normal",
            shift=0):
    trades = []
    dias_usados = set()
    for i in range(len(h1)):
        r = h1.iloc[i]
        if r["hour"].hour > LAST_SIGNAL_HOUR:
            continue
        if r["day"] in dias_usados:
            continue
        j = i - shift
        if j < 0:
            continue
        sig = int(sinal[j])
        if sig == 0:
            continue
        if r["atr"] <= 0:
            continue
        if side_mode == "mirror":
            sig = -sig
        elif side_mode == "long":
            sig = 1

        dia_m1 = m1_by_day.get(r["day"])
        if dia_m1 is None or len(dia_m1["ts"]) == 0:
            continue
        entry_idx = int(np.searchsorted(dia_m1["ts"], r["end"].to_datetime64(),
                                        side="left"))
        if entry_idx >= len(dia_m1["ts"]):
            continue
        entry = float(dia_m1["open"][entry_idx])
        side = "BUY" if sig > 0 else "SELL"
        stop_dist = k_atr * float(r["atr"])
        if stop_dist <= 0:
            continue
        out = simular(dia_m1, entry_idx, side, entry, stop_dist, tp_r, slip)
        if out is None:
            continue
        out.update(year=int(r["day"].year), day=r["day"], side=side,
                   entry_model="h1", sig_name=None)
        trades.append(out)
        dias_usados.add(r["day"])
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
    h1 = build_h1(m1)
    m1_by_day = preparar_dias(h1, m1)
    if len(h1) == 0:
        raise SystemExit("sem barras H1")

    print("=" * 108)
    print(f"TENDENCIA H1 - WDO | M1={len(m1)} H1={len(h1)} dias={h1['day'].nunique()}")
    print(f"periodo: {h1['day'].min()} -> {h1['day'].max()} | "
          f"custo R$1,20 | 1 contrato | EOD {EOD_HM}")
    print("modelo: sinal em H1 fechada, entrada no M1 seguinte, SL k*ATR14(H1), "
          "1 trade/dia, M1 intrabar (SL antes do TP)")
    print("=" * 108)

    # frequencia de sinais
    print("\n--- frequencia de sinais (barras H1 elegiveis) ---")
    for nome, fam, param in SINAIS:
        s = gerar_sinal(h1, fam, param)
        eleg = (h1["hour"].dt.hour <= LAST_SIGNAL_HOUR).values
        n = int(((s != 0) & eleg).sum())
        print(f"  {nome:<12} sinais={n:>4}")

    # tabela primaria: SL 2.0 ATR, TP 3R
    print("\n--- primario: SL=2.0*ATR, TP=3R, 1 trade/dia ---")
    print(f"  {'sinal':<12} {'slip':>4} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} "
          f"{'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} {'OOS exp':>7} "
          f"{'OOS PF':>5}  gate")
    primarios = []
    for nome, fam, param in SINAIS:
        s = gerar_sinal(h1, fam, param)
        for slip in (0.0, 0.5, 1.0):
            tr = coletar(h1, m1_by_day, s, 2.0, 3.0, slip)
            v, vis, voos = avaliar(tr, nome)
            ok = gate(vis, voos)
            print(f"  {nome:<12} {slip:>4.1f} {v.get('n',0):>4} "
                  f"{v.get('win%',0):>5.1f} {v.get('exp_rs',0):>7.2f} "
                  f"{v.get('pf',0):>5.2f} {v.get('total_rs',0):>7.0f} | "
                  f"{vis.get('exp_rs',0):>7.2f} {vis.get('pf',0):>5.2f} "
                  f"{voos.get('n',0):>5} {voos.get('exp_rs',0):>7.2f} "
                  f"{voos.get('pf',0):>5.2f}  {'PASSA' if ok else 'nao'}")
            if slip == 1.0:
                primarios.append((nome, fam, param, v, vis, voos, ok, tr))

    # melhor candidato: entre os que passam; senao, maior OOS exp com IS exp>0
    passam = [p for p in primarios if p[6]]
    if passam:
        best = max(passam, key=lambda x: x[5].get("exp_rs", -1))
        criterio = "PASSA no gate"
    else:
        eleg = [p for p in primarios
                if p[4].get("exp_rs", -1) > 0 and p[5].get("n", 0) >= 40]
        best = (max(eleg, key=lambda x: x[5].get("exp_rs", -1)) if eleg else None)
        criterio = "melhor esforco (IS exp>0 e OOS n>=40)"

    if best is None:
        print("\nNenhum candidato com IS exp>0 e OOS n>=40. Sem promocao.")
        return

    nome, fam, param, v, vis, voos, ok, tr = best
    print("\n" + "=" * 108)
    print(f"CANDIDATO ({criterio}): {nome} | SL=2.0*ATR TP=3R slip=1.0")
    print("=" * 108)
    por_ano(tr, nome)

    # sensibilidade (mesmo sinal): SL x TP, slip 1.0
    print(f"\n--- sensibilidade {nome} | slip 1.0 ---")
    print(f"  {'SL':>5} {'TP':>5} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} "
          f"{'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} {'OOS exp':>7} "
          f"{'OOS PF':>5}")
    s = gerar_sinal(h1, fam, param)
    for k_atr in (1.5, 2.0, 2.5):
        for tp_r in (2.0, 3.0, 4.0, None):
            tr2 = coletar(h1, m1_by_day, s, k_atr, tp_r, 1.0)
            v2, vis2, voos2 = avaliar(tr2, "x")
            print(f"  {k_atr:>5.1f} {('EOD' if tp_r is None else tp_r):>5} "
                  f"{v2.get('n',0):>4} {v2.get('win%',0):>5.1f} "
                  f"{v2.get('exp_rs',0):>7.2f} {v2.get('pf',0):>5.2f} "
                  f"{v2.get('total_rs',0):>7.0f} | {vis2.get('exp_rs',0):>7.2f} "
                  f"{vis2.get('pf',0):>5.2f} {voos2.get('n',0):>5} "
                  f"{voos2.get('exp_rs',0):>7.2f} {voos2.get('pf',0):>5.2f}")

    # controles: mirror, long, shift 1 barra
    print(f"\n--- controles {nome} | SL=2.0*ATR TP=3R slip 1.0 ---")
    for mode, label in (("normal", "normal"), ("mirror", "CTRL-MIRROR"),
                        ("long", "CTRL-LONG")):
        trc = coletar(h1, m1_by_day, s, 2.0, 3.0, 1.0, side_mode=mode)
        vc = stats(trc, label)
        print("  " + linha(vc))
    trs = coletar(h1, m1_by_day, s, 2.0, 3.0, 1.0, shift=1)
    print("  " + linha(stats(trs, "CTRL-SHIFT-1")))


if __name__ == "__main__":
    main()
