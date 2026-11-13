# -*- coding: utf-8 -*-
"""
filtros_faixa1.py — Estudo READ-ONLY: entrada por stop order + filtros de
seletividade na Faixa 1 (WDO).

Nao envia ordem, nao altera config, nao toca no robo.

Pergunta: o edge da Faixa 1 melhora se (a) entrarmos no rompimento por stop
order em vez de esperar o fechamento da barra M5 e (b) filtrarmos os dias?

Modelo de saida (igual a producao, sem trailing):
  SL = max(8, min(dist_da_caixa, 2.5 * ATR14_manha))
  TP = 1.5 * tamanho_da_caixa (ou multiplo de R na grade)
  EOD = 17:30
  custo = R$ 1,20 por contrato por operacao | 1 pt = R$ 10 | 1 contrato

Entradas comparadas:
  mercado : sinal na barra M5 fechada; entra no primeiro M1 seguinte (open)
  stop    : ordem stop no high/low da caixa + buffer, ativa 10:30-11:00;
            fill no nivel (ou no open, se gap) + slippage

Slippage explicito POR LADO: 0 / 0,5 / 1,0 ponto (0 / 1 / 2 ticks).
M1 e usado para sequenciar o intrabar (SL antes do TP, conservador).

Filtros sao pre-registrados (poucos, para limitar data mining) e avaliados
com IS 2021-2024 / OOS 2025-2026. Gate: OOS exp > 0, OOS PF > 1,0 e
n_OOS >= 40 com slippage 1,0 pt/lado.

Uso:
    python backtest/filtros_faixa1.py
    python backtest/filtros_faixa1.py --start 2025-01-01
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_trailing_faixa1 import (  # noqa: E402
    atr14,
    linha,
    load_m5,
    stats,
    stop_distance,
    TP_K,
)

FILTROS = (
    "todos",
    "bias",
    "bias_forte",
    "range_hi",
    "range_lo",
    "vol_hi",
    "atr_hi",
    "tendencia",
    "gap_alinhado",
    "rng_ge_6",
    "rng_le_20",
    "bias_vol",
    "bias_range",
    "bias_tend",
    "bias_vol_range",
    "bias_vol_tend",
)


# ---------------- DADOS ----------------
def load_m1(symbol: str, start: datetime) -> pd.DataFrame:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise SystemExit(f"MT5 init falhou: {mt5.last_error()}")
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, datetime.now())
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise SystemExit("sem dados M1 para o simbolo")

    df = pd.DataFrame(rates)
    df["ts"] = pd.to_datetime(df["time"], unit="s")
    df = df[["ts", "open", "high", "low", "close", "tick_volume"]].sort_values("ts")
    df["day"] = df["ts"].dt.date
    df["hm"] = df["ts"].dt.strftime("%H:%M")
    df = df[(df["hm"] >= "09:00") & (df["hm"] <= "17:30")]
    return df.reset_index(drop=True)


# ---------------- FEATURES POR DIA ----------------
def _media(hist, n=20):
    if len(hist) < n:
        return None
    return float(np.mean(hist[-n:]))


def _pct(hist, x, n=60, min_n=20):
    h = hist[-n:]
    if len(h) < min_n:
        return None
    return sum(1 for v in h if v < x) / len(h)


def build_days(m5: pd.DataFrame, m1: pd.DataFrame) -> list[dict]:
    m1_by_day = {d: g.sort_values("ts").reset_index(drop=True)
                 for d, g in m1.groupby("day")}
    days: list[dict] = []
    closes: list[float] = []
    hist_rng: list[float] = []
    hist_atr: list[float] = []
    hist_vol: list[float] = []
    prev_close = None

    for day, g in m5.groupby("day", sort=True):
        g = g.sort_values("ts")
        box = g[(g["hm"] >= "09:00") & (g["hm"] < "10:00")]
        if len(box) < 8:
            continue
        box_bars = [(r.ts, float(r.open), float(r.high), float(r.low),
                     float(r.close), float(r.tick_volume)) for r in box.itertuples()]
        bars = [(r.ts, float(r.open), float(r.high), float(r.low),
                 float(r.close), float(r.tick_volume)) for r in g.itertuples()]
        hi = max(b[2] for b in box_bars)
        lo = min(b[3] for b in box_bars)
        rng = hi - lo
        if rng <= 0:
            continue
        atr = atr14(box_bars)
        vol = sum(b[5] for b in box_bars)
        box_open = box_bars[0][1]
        box_close = box_bars[-1][4]
        pos = (box_close - lo) / rng
        m_rng = _media(hist_rng)
        m_atr = _media(hist_atr)
        m_vol = _media(hist_vol)
        sma20 = _media(closes)
        trend_up = (prev_close > sma20) if (prev_close is not None and sma20) else None
        gap = (box_open - prev_close) if prev_close is not None else None
        feat = dict(
            rng=rng, atr=atr, vol=vol, box_open=box_open, box_close=box_close,
            pos=pos,
            bias_up=box_close > box_open,
            bias_down=box_close < box_open,
            bias_strength=abs(pos - 0.5) * 2.0,
            trend_up=trend_up,
            gap=gap,
            gap_atr=(gap / atr) if (gap is not None and atr > 0) else None,
            rng_ratio=(rng / m_rng) if m_rng else None,
            atr_ratio=(atr / m_atr) if m_atr else None,
            vol_ratio=(vol / m_vol) if m_vol else None,
            rng_pct=_pct(hist_rng, rng),
            atr_pct=_pct(hist_atr, atr),
            vol_pct=_pct(hist_vol, vol),
            dow=day.weekday(),
        )
        m1_day = m1_by_day.get(day)
        m1_arr = None
        if m1_day is not None and len(m1_day):
            m1_arr = dict(
                ts=m1_day["ts"].values,
                open=m1_day["open"].values.astype(float),
                high=m1_day["high"].values.astype(float),
                low=m1_day["low"].values.astype(float),
                close=m1_day["close"].values.astype(float),
            )
        days.append(dict(day=day, hi=hi, lo=lo, rng=rng, atr=atr,
                         bars=bars, m1=m1_arr, feat=feat))
        prev_close = bars[-1][4]
        closes.append(prev_close)
        hist_rng.append(rng)
        hist_atr.append(atr)
        hist_vol.append(vol)
    return days


# ---------------- SINAIS ----------------
def signal_market(d: dict):
    """Sinal na barra M5 fechada; entrada no primeiro M1 seguinte (open)."""
    m1 = d["m1"]
    if m1 is None or len(m1["ts"]) == 0:
        return None
    for b in d["bars"]:
        hm = b[0].strftime("%H:%M")
        if hm < "10:30":
            continue
        if hm >= "11:00":
            break
        if b[2] >= d["hi"]:
            side = "BUY"
        elif b[3] <= d["lo"]:
            side = "SELL"
        else:
            continue
        entry_time = b[0].to_datetime64() + np.timedelta64(5, "m")
        j = int(np.searchsorted(m1["ts"], entry_time, side="left"))
        if j >= len(m1["ts"]):
            return None
        return dict(side=side, entry=float(m1["open"][j]), entry_idx=j)
    return None


def signal_stop(d: dict, buffer=0.5):
    """Ordem stop no high/low da caixa + buffer, ativa 10:30-11:00.

    Retorna (sinal|None, n_ambiguos). Se high e low da mesma barra M1
    rompem os dois lados, a sequencia e desconhecida -> ignora (conservador).
    """
    m1 = d["m1"]
    if m1 is None or len(m1["ts"]) == 0:
        return None, 0
    ts = m1["ts"]
    start = np.datetime64(str(d["day"]) + "T10:30:00")
    end = np.datetime64(str(d["day"]) + "T11:00:00")
    j0 = int(np.searchsorted(ts, start, side="left"))
    j1 = int(np.searchsorted(ts, end, side="left"))
    buy_lvl = d["hi"] + buffer
    sell_lvl = d["lo"] - buffer
    for j in range(j0, j1):
        hb = float(m1["high"][j]) >= buy_lvl
        hs = float(m1["low"][j]) <= sell_lvl
        if hb and hs:
            return None, 1
        if hb:
            return dict(side="BUY", entry=max(buy_lvl, float(m1["open"][j])),
                        entry_idx=j), 0
        if hs:
            return dict(side="SELL", entry=min(sell_lvl, float(m1["open"][j])),
                        entry_idx=j), 0
    return None, 0


def signal_retest(d: dict, buffer=0.5, deadline_hm="11:00"):
    """Sinal na barra M5 fechada + entrada LIMIT no reteste do nivel da caixa.

    Diferente da stop order (que entra no primeiro toque, inclusive pavio),
    aqui espera o preco voltar ao nivel da caixa depois do fechamento que
    confirmou o rompimento. Exige penetracao de `buffer` para assumir fill
    (fila/queue conservadora) e entra no nivel, sem slippage de entrada.
    """
    m1 = d["m1"]
    if m1 is None or len(m1["ts"]) == 0:
        return None
    sig = None
    for b in d["bars"]:
        hm = b[0].strftime("%H:%M")
        if hm < "10:30":
            continue
        if hm >= "11:00":
            break
        if b[2] >= d["hi"]:
            sig = ("BUY", b[0].to_datetime64() + np.timedelta64(5, "m"))
            break
        if b[3] <= d["lo"]:
            sig = ("SELL", b[0].to_datetime64() + np.timedelta64(5, "m"))
            break
    if sig is None:
        return None
    side, t_signal = sig
    ts = m1["ts"]
    j0 = int(np.searchsorted(ts, t_signal, side="left"))
    j1 = int(np.searchsorted(
        ts, np.datetime64(str(d["day"]) + "T" + deadline_hm + ":00"), side="left"))
    level = d["hi"] if side == "BUY" else d["lo"]
    for j in range(j0, j1):
        if side == "BUY" and float(m1["low"][j]) <= level - buffer:
            return dict(side="BUY", entry=level, entry_idx=j)
        if side == "SELL" and float(m1["high"][j]) >= level + buffer:
            return dict(side="SELL", entry=level, entry_idx=j)
    return None


def preparar_sinais(days, buffer=0.5):
    for d in days:
        d["sig_market"] = signal_market(d)
        d["sig_stop"], d["amb"] = signal_stop(d, buffer)
        d["sig_retest"] = signal_retest(d, buffer)


# ---------------- SAIDA (M1) ----------------
def _saida(entry, fill, side, slip, motivo, mfe, mae):
    exit_fill = fill - slip if side == "BUY" else fill + slip
    pnl = (exit_fill - entry) if side == "BUY" else (entry - exit_fill)
    return {"pnl": pnl, "exit": motivo, "mfe": mfe, "mae": mae}


def simulate_m1(d: dict, sig: dict, slip: float, tp_r=None,
                tp_box=TP_K, eod_hm="17:30"):
    """Simula a saida com M1. SL conferido antes do TP (conservador).

    tp_r: se informado, TP = entry +/- tp_r * distancia_do_stop.
    tp_box: senao, TP = entry +/- tp_box * tamanho_da_caixa.
    """
    m1 = d["m1"]
    if m1 is None or len(m1["ts"]) == 0:
        return None
    side = sig["side"]
    entry = sig["entry"] + (slip if side == "BUY" else -slip)
    dist = stop_distance(d, side, entry, "caixa")
    if dist <= 0:
        return None
    stop = entry - dist if side == "BUY" else entry + dist
    if tp_r is not None:
        tp = entry + tp_r * dist if side == "BUY" else entry - tp_r * dist
    else:
        tp = entry + tp_box * d["rng"] if side == "BUY" else entry - tp_box * d["rng"]

    ts = m1["ts"]
    op, hi, lo, cl = m1["open"], m1["high"], m1["low"], m1["close"]
    eod_idx = int(np.searchsorted(
        ts, np.datetime64(str(d["day"]) + "T" + eod_hm + ":00"), side="left"))
    j0 = sig["entry_idx"]
    end = min(eod_idx, len(ts))
    if j0 >= end:
        return _saida(entry, float(cl[min(j0, len(ts) - 1)]), side, slip,
                      "EOD", 0.0, 0.0)

    mfe = mae = 0.0
    last_close = float(cl[j0])
    for j in range(j0, end):
        last_close = float(cl[j])
        h = float(hi[j])
        l = float(lo[j])
        if side == "BUY":
            if h - entry > mfe:
                mfe = h - entry
            if l - entry < mae:
                mae = l - entry
            if l <= stop:
                fill = float(op[j]) if float(op[j]) < stop else stop
                return _saida(entry, fill, side, slip, "SL", mfe, mae)
            if h >= tp:
                return _saida(entry, tp, side, slip, "TP", mfe, mae)
        else:
            if entry - l > mfe:
                mfe = entry - l
            if entry - h < mae:
                mae = entry - h
            if h >= stop:
                fill = float(op[j]) if float(op[j]) > stop else stop
                return _saida(entry, fill, side, slip, "SL", mfe, mae)
            if l <= tp:
                return _saida(entry, tp, side, slip, "TP", mfe, mae)

    return _saida(entry, last_close, side, slip, "EOD", mfe, mae)


# ---------------- COLETA ----------------
def coletar(days, entry_model, slip, tp_r=None, tp_box=TP_K, eod_hm="17:30"):
    trades = []
    amb = 0
    sem = 0
    for d in days:
        if entry_model == "stop":
            sig = d.get("sig_stop")
            amb += d.get("amb", 0)
        elif entry_model == "retest":
            sig = d.get("sig_retest")
        else:
            sig = d.get("sig_market")
        if sig is None:
            sem += 1
            continue
        out = simulate_m1(d, sig, slip, tp_r=tp_r, tp_box=tp_box, eod_hm=eod_hm)
        if out is None:
            sem += 1
            continue
        out.update(year=d["day"].year, day=d["day"], side=sig["side"],
                   feat=d["feat"], entry_model=entry_model)
        trades.append(out)
    return trades, amb, sem


# ---------------- FILTROS ----------------
def passes(t: dict, name: str) -> bool:
    f = t["feat"]
    side = t["side"]
    if name == "todos":
        return True
    if name == "bias":
        return (side == "BUY" and f["bias_up"]) or (side == "SELL" and f["bias_down"])
    if name == "bias_forte":
        return passes(t, "bias") and f["bias_strength"] >= 0.5
    if name == "range_hi":
        return f["rng_ratio"] is not None and f["rng_ratio"] >= 1.0
    if name == "range_lo":
        return f["rng_ratio"] is not None and f["rng_ratio"] < 1.0
    if name == "vol_hi":
        return f["vol_ratio"] is not None and f["vol_ratio"] >= 1.0
    if name == "atr_hi":
        return f["atr_ratio"] is not None and f["atr_ratio"] >= 1.0
    if name == "tendencia":
        return f["trend_up"] is not None and (
            (side == "BUY" and f["trend_up"]) or (side == "SELL" and not f["trend_up"]))
    if name == "gap_alinhado":
        return f["gap"] is not None and (
            (side == "BUY" and f["gap"] > 0) or (side == "SELL" and f["gap"] < 0))
    if name == "rng_ge_6":
        return f["rng"] >= 6.0
    if name == "rng_le_20":
        return f["rng"] <= 20.0
    if name == "bias_vol":
        return passes(t, "bias") and passes(t, "vol_hi")
    if name == "bias_range":
        return passes(t, "bias") and passes(t, "range_hi")
    if name == "bias_tend":
        return passes(t, "bias") and passes(t, "tendencia")
    if name == "bias_vol_range":
        return passes(t, "bias") and passes(t, "vol_hi") and passes(t, "range_hi")
    if name == "bias_vol_tend":
        return passes(t, "bias") and passes(t, "vol_hi") and passes(t, "tendencia")
    return False


def split_is_oos(trades):
    return ([t for t in trades if t["year"] <= 2024],
            [t for t in trades if t["year"] >= 2025])


def avaliar(trades, name):
    sub = [t for t in trades if passes(t, name)]
    v = stats(sub, name)
    is_sub, oos_sub = split_is_oos(sub)
    return sub, v, stats(is_sub, "IS"), stats(oos_sub, "OOS")


def gate(v, vis, voos, min_oos=40):
    return (voos.get("n", 0) >= min_oos
            and voos.get("exp_rs", -1) > 0
            and voos.get("pf", 0) > 1.0
            and vis.get("exp_rs", -1) > 0
            and v.get("exp_rs", -1) > 0)


# ---------------- RELATORIOS ----------------
def comparar_entradas(days, slip):
    print(f"\n--- entrada: mercado vs stop vs reteste | slippage {slip:.1f} pt/lado ---")
    for model in ("mercado", "stop", "retest"):
        tr, amb, sem = coletar(days, model, slip)
        v = stats(tr, model)
        print("  " + linha(v) + f" | sem_sinal={sem} ambiguos={amb}")


def ranking(days, entry_model, slip):
    print(f"\n--- filtros | entrada {entry_model} | slippage {slip:.1f} pt/lado ---")
    print(f"  {'filtro':<16} {'n':>4} {'WR%':>5} {'exp':>7} {'PF':>5} "
          f"{'total':>7} | {'IS exp':>7} {'IS PF':>5} {'OOS n':>5} "
          f"{'OOS exp':>7} {'OOS PF':>5}  gate")
    tr, _amb, _sem = coletar(days, entry_model, slip)
    for name in FILTROS:
        _sub, v, vis, voos = avaliar(tr, name)
        if v["n"] == 0:
            continue
        ok = gate(v, vis, voos)
        print(f"  {name:<16} {v['n']:>4} {v['win%']:>5.1f} {v['exp_rs']:>7.2f} "
              f"{v['pf']:>5.2f} {v['total_rs']:>7.0f} | "
              f"{vis.get('exp_rs', 0):>7.2f} {vis.get('pf', 0):>5.2f} "
              f"{voos.get('n', 0):>5} {voos.get('exp_rs', 0):>7.2f} "
              f"{voos.get('pf', 0):>5.2f}  {'PASSA' if ok else 'nao'}")


def detalhe_por_ano(trades, name, slip, entry_model):
    sub = [t for t in trades if passes(t, name)]
    print(f"\n--- detalhe {entry_model}/{name} | slip {slip:.1f} ---")
    by = {}
    for t in sub:
        by.setdefault(t["year"], []).append(t)
    for y in sorted(by):
        print("  " + linha(stats(by[y], str(y))))
    is_sub, oos_sub = split_is_oos(sub)
    print("  " + linha(stats(is_sub, "IS 2021-2024")))
    print("  " + linha(stats(oos_sub, "OOS 2025-2026")))


def grade_saida(days, entry_model, name, slip):
    """Grade de TP (multiplos de R) x EOD, para o filtro escolhido."""
    print(f"\n--- grade de saida | {entry_model}/{name} | slip {slip:.1f} ---")
    tr_all, _a, _s = coletar(days, entry_model, slip)
    sub = [t for t in tr_all if passes(t, name)]
    print("  base (TP=1.5xcaixa, EOD 17:30): " + linha(stats(sub, "base")))
    for eod in ("15:00", "16:00", "17:30"):
        for tp_r in (1.0, 1.5, 2.0, None):
            tr, _a, _s = coletar(days, entry_model, slip, tp_r=tp_r, eod_hm=eod)
            tr = [t for t in tr if passes(t, name)]
            v = stats(tr, f"TP={tp_r or 'box'} EOD={eod}")
            is_sub, oos_sub = split_is_oos(tr)
            vis, voos = stats(is_sub, "IS"), stats(oos_sub, "OOS")
            print(f"  {('TP=%s' % (tp_r if tp_r is not None else 'caixa')):<9} "
                  f"EOD={eod}  n={v['n']:>4} WR={v['win%']:>5.1f} "
                  f"exp={v['exp_rs']:>7.2f} PF={v['pf']:>5.2f} "
                  f"tot={v['total_rs']:>7.0f} | IS {vis.get('exp_rs',0):>7.2f}/"
                  f"{vis.get('pf',0):>4.2f} OOS {voos.get('exp_rs',0):>7.2f}/"
                  f"{voos.get('pf',0):>4.2f}")


# ---------------- MAIN ----------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="WDO$")
    ap.add_argument("--start", default="2021-11-01")
    ap.add_argument("--buffer", type=float, default=0.5)
    a = ap.parse_args()

    start = datetime.strptime(a.start, "%Y-%m-%d")
    m5 = load_m5(a.symbol, start)
    m1 = load_m1(a.symbol, start)
    days = build_days(m5, m1)
    if not days:
        raise SystemExit("sem dias validos")
    preparar_sinais(days, a.buffer)

    print("=" * 108)
    print(f"FAIXA 1 - ENTRADA STOP + FILTROS | {a.symbol} | "
          f"M5={len(m5)} M1={len(m1)} dias={len(days)}")
    print(f"periodo: {days[0]['day']} -> {days[-1]['day']} | "
          f"buffer stop={a.buffer:.1f} pt | custo R$1,20 | 1 contrato")
    print("modelo: SL producao (caixa/ATR), TP 1,5xcaixa, EOD 17:30, "
          "M1 para intrabar (SL antes do TP)")
    print("=" * 108)

    for slip in (0.0, 0.5, 1.0):
        comparar_entradas(days, slip)

    for slip in (1.0, 0.5):
        for model in ("retest", "stop", "mercado"):
            ranking(days, model, slip)

    # melhor candidato entre stop e reteste (maior OOS exp com n>=40)
    cand = []
    for model in ("stop", "retest"):
        tr_model, _a, _s = coletar(days, model, 1.0)
        for name in FILTROS:
            if name == "todos":
                continue
            sub, v, vis, voos = avaliar(tr_model, name)
            if voos.get("n", 0) >= 40:
                cand.append((voos.get("exp_rs", -1), model, name, v, vis, voos))
    cand.sort(reverse=True)
    if cand:
        _e, best_model, best, v, vis, voos = cand[0]
        print("\n" + "=" * 108)
        print(f"MELHOR CANDIDATO ({best_model}, slip 1.0, OOS n>=40): {best} "
              f"(OOS exp {voos.get('exp_rs',0):.2f}, PF {voos.get('pf',0):.2f})")
        print("=" * 108)
        tr_best, _a, _s = coletar(days, best_model, 1.0)
        detalhe_por_ano(tr_best, best, 1.0, best_model)
        grade_saida(days, best_model, best, 1.0)
    else:
        print("\nNenhum candidato com OOS n>=40.")


if __name__ == "__main__":
    main()
