# -*- coding: utf-8 -*-
"""
backtest_trailing_faixa1.py — Estudo READ-ONLY: trailing na Faixa 1 (WDO M5).

Nao envia ordem, nao altera config, nao toca no robo.

Modelo fiel a producao (rompimento_orquestrador.py):
  caixa    = 09:00-10:00 BRT (primeira hora)
  gatilho  = janela de 60 min apos 10:00 (primario validado: 10:30-11:00)
  sinal    = primeira barra M5 FECHADA que rompe o high/low da caixa
  entrada  = fechamento da barra de sinal + slippage (producao entra a mercado)
  SL       = max(8, min(entry - lado_oposto, 2.5 * ATR14_manha))  [modo caixa]
  TP       = 1.5 * tamanho_da_caixa
  EOD      = 17:30 (ultima barra 17:25)
  custo    = R$ 1,20 por contrato por operacao (0,60 entrada + 0,60 saida)
  1 ponto  = R$ 10,00 | sempre 1 contrato

Slippage explicito POR LADO (0 / 0,5 / 1,0 ponto = 0 / 1 / 2 ticks).
O trailing e atualizado no FECHAMENTO da barra e aplicado na barra seguinte
(sem look-ahead). SL e conferido antes do TP (conservador).

Uso:
    python backtest/backtest_trailing_faixa1.py
    python backtest/backtest_trailing_faixa1.py --start 2021-11-01
"""
from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

SHIFT_H = 0
COST_RS = 1.20
RS_PER_POINT = 10.0
BOX_START, BOX_END = "09:00", "10:00"
EOD_LAST_BAR = "17:25"      # barra 17:25 fecha as 17:30 (EOD de producao)
TP_K = 1.5
SL_ATR_FACTOR = 2.5
SL_PISO = 8.0

EXIT_RULES = ("sem", "trail8_4", "be8", "be8_lock70")


def load_m5(symbol: str, start: datetime) -> pd.DataFrame:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise SystemExit(f"MT5 init falhou: {mt5.last_error()}")
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, datetime.now())
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise SystemExit("sem dados M5 para o simbolo")

    df = pd.DataFrame(rates)
    df["ts"] = pd.to_datetime(df["time"], unit="s") + pd.Timedelta(hours=SHIFT_H)
    df = df[["ts", "open", "high", "low", "close", "tick_volume"]].sort_values("ts")
    df["day"] = df["ts"].dt.date
    df["hm"] = df["ts"].dt.strftime("%H:%M")
    df = df[(df["hm"] >= BOX_START) & (df["hm"] <= EOD_LAST_BAR)]
    return df.reset_index(drop=True)


def atr14(bars, periodo=14):
    """ATR de Wilder identico ao _atr14 do orquestrador."""
    trs = []
    prev_c = None
    for _ts, _o, hi, lo, cl, _v in bars:
        if prev_c is None:
            prev_c = cl
            continue
        trs.append(max(hi - lo, abs(hi - prev_c), abs(lo - prev_c)))
        prev_c = cl
    if not trs:
        return 0.0
    p = min(periodo, len(trs))
    atr = trs[0]
    for tr in trs[1:]:
        atr = ((p - 1) * atr + tr) / p
    return atr


def build_days(df: pd.DataFrame) -> list[dict]:
    days = []
    for day, g in df.groupby("day", sort=True):
        g = g.sort_values("ts")
        box = g[(g["hm"] >= BOX_START) & (g["hm"] < BOX_END)]
        if len(box) < 8:
            continue
        bars = [(r.ts, float(r.open), float(r.high), float(r.low),
                 float(r.close), float(r.tick_volume)) for r in g.itertuples()]
        box_bars = bars[:len(box)]
        hi = max(b[2] for b in box_bars)
        lo = min(b[3] for b in box_bars)
        rng = hi - lo
        if rng <= 0:
            continue
        days.append({
            "day": day,
            "hi": hi,
            "lo": lo,
            "rng": rng,
            "box_open": box_bars[0][1],
            "box_close": box_bars[-1][4],
            "atr": atr14(box_bars),
            "bars": bars,
        })
    return days


def find_signal(d: dict, lo_hm: str, hi_hm: str, bias: bool = False):
    """Primeira barra FECHADA na janela que rompe a caixa.

    Retorna (side, idx) ou None. Prioriza o high (igual ao trig() de producao).
    Com bias=True, so aceita o lado alinhado ao vies da 1a hora.
    """
    for i, b in enumerate(d["bars"]):
        hm = b[0].strftime("%H:%M")
        if hm < lo_hm:
            continue
        if hm >= hi_hm:
            break
        if b[2] >= d["hi"]:
            side = "BUY"
        elif b[3] <= d["lo"]:
            side = "SELL"
        else:
            continue
        if bias:
            if side == "BUY" and not (d["box_close"] > d["box_open"]):
                return None
            if side == "SELL" and not (d["box_close"] < d["box_open"]):
                return None
        return side, i
    return None


def stop_distance(d: dict, side: str, entry: float, mode: str) -> float:
    if mode == "fixed5":
        return 5.0
    if mode == "0.5x":
        return 0.5 * d["rng"]
    # modo caixa = producao: distancia ao lado oposto, limitada pelo ATR e piso
    dist = (entry - d["lo"]) if side == "BUY" else (d["hi"] - entry)
    dist = max(0.0, dist)
    if d["atr"] > 0 and SL_ATR_FACTOR > 0:
        dist = max(SL_PISO, min(dist, SL_ATR_FACTOR * d["atr"]))
    return dist


def simulate(d: dict, idx: int, side: str, mode: str, rule: str,
             slip: float, tp_on: bool = True):
    """Retorna dict(pnl_pts, exit, mfe, mae) ou None.

    pnl_pts ja inclui o slippage dos dois lados (entrada e saida).
    """
    bars = d["bars"]
    if idx + 1 >= len(bars):
        return None
    sig_close = bars[idx][4]
    entry = sig_close + slip if side == "BUY" else sig_close - slip
    dist = stop_distance(d, side, entry, mode)
    if dist <= 0:
        return None
    stop = entry - dist if side == "BUY" else entry + dist
    stop_inicial = stop
    tp = None
    if tp_on:
        tp = entry + TP_K * d["rng"] if side == "BUY" else entry - TP_K * d["rng"]

    mfe = mae = 0.0
    stop_movido = False
    for j in range(idx + 1, len(bars)):
        _ts, op, hi, lo, cl, _v = bars[j]
        if side == "BUY":
            mfe = max(mfe, hi - entry)
            mae = min(mae, lo - entry)
        else:
            mfe = max(mfe, entry - lo)
            mae = min(mae, entry - hi)

        # 1) stop (gap atraves do stop -> fill no open, pior)
        if side == "BUY" and lo <= stop:
            fill = op if op < stop else stop
            return _saida(entry, fill, side, slip, "TRAIL" if stop_movido else "SL", mfe, mae)
        if side == "SELL" and hi >= stop:
            fill = op if op > stop else stop
            return _saida(entry, fill, side, slip, "TRAIL" if stop_movido else "SL", mfe, mae)

        # 2) TP
        if tp is not None:
            if side == "BUY" and hi >= tp:
                return _saida(entry, tp, side, slip, "TP", mfe, mae)
            if side == "SELL" and lo <= tp:
                return _saida(entry, tp, side, slip, "TP", mfe, mae)

        # 3) trailing no fechamento, aplicado na proxima barra
        if rule != "sem":
            if side == "BUY":
                lucro_close = cl - entry
                if rule == "trail8_4" and lucro_close >= 8.0:
                    novo = cl - 4.0
                    if novo > stop:
                        stop, stop_movido = novo, True
                if rule in ("be8", "be8_lock70") and mfe >= 8.0 and cl >= entry + 1.0 + slip:
                    novo = entry + 1.0 + slip   # BE liquido do slippage de saida
                    if novo > stop:
                        stop, stop_movido = novo, True
                    if rule == "be8_lock70":
                        novo = min(entry + 0.70 * mfe + slip, cl)
                        if novo > stop:
                            stop, stop_movido = novo, True
            else:
                lucro_close = entry - cl
                if rule == "trail8_4" and lucro_close >= 8.0:
                    novo = cl + 4.0
                    if novo < stop:
                        stop, stop_movido = novo, True
                if rule in ("be8", "be8_lock70") and mfe >= 8.0 and cl <= entry - 1.0 - slip:
                    novo = entry - 1.0 - slip
                    if novo < stop:
                        stop, stop_movido = novo, True
                    if rule == "be8_lock70":
                        novo = max(entry - 0.70 * mfe - slip, cl)
                        if novo < stop:
                            stop, stop_movido = novo, True

    # 4) EOD: fecha no ultimo fechamento
    fill = bars[-1][4]
    return _saida(entry, fill, side, slip, "EOD", mfe, mae)


def _saida(entry, fill, side, slip, motivo, mfe, mae):
    exit_fill = fill - slip if side == "BUY" else fill + slip
    pnl = (exit_fill - entry) if side == "BUY" else (entry - exit_fill)
    return {"pnl": pnl, "exit": motivo, "mfe": mfe, "mae": mae}


def stats(trades: list[dict], label: str) -> dict:
    if not trades:
        return {"label": label, "n": 0}
    pts = np.array([t["pnl"] for t in trades], dtype=float)
    net = pts * RS_PER_POINT - COST_RS
    eq = np.cumsum(net)
    dd = float(np.min(eq - np.maximum.accumulate(eq))) if len(eq) else 0.0
    wins, losses = net[net > 0], net[net < 0]
    pf = float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    saidas = {}
    for t in trades:
        saidas[t["exit"]] = saidas.get(t["exit"], 0) + 1
    return {
        "label": label,
        "n": len(trades),
        "win%": 100.0 * len(wins) / len(trades),
        "exp_rs": float(net.mean()),
        "pf": pf,
        "total_rs": float(net.sum()),
        "maxdd_rs": dd,
        "saidas": saidas,
        "mfe": float(np.mean([t["mfe"] for t in trades])),
        "mae": float(np.mean([t["mae"] for t in trades])),
    }


def coletar(days, lo_hm, hi_hm, mode, rule, slip, tp_on=True, bias=False):
    tr = []
    for d in days:
        sig = find_signal(d, lo_hm, hi_hm, bias=bias)
        if sig is None:
            continue
        side, idx = sig
        out = simulate(d, idx, side, mode, rule, slip, tp_on=tp_on)
        if out is None:
            continue
        out["year"] = d["day"].year
        tr.append(out)
    return tr


def linha(v: dict) -> str:
    saidas = ",".join("%s:%d" % (k, n) for k, n in sorted(v["saidas"].items()))
    return (f"{v['label']:<22} n={v['n']:>4} win%={v['win%']:>5.1f} "
            f"exp_R$={v['exp_rs']:>7.2f} PF={v['pf']:>5.2f} "
            f"total_R$={v['total_rs']:>8.0f} maxDD_R$={v['maxdd_rs']:>7.0f} | {saidas}")


def tabela(days, lo_hm, hi_hm, slip):
    print(f"\n--- janela {lo_hm}-{hi_hm} | slippage {slip:.1f} pt/lado ---")
    base = None
    for mode in ("caixa", "0.5x", "fixed5"):
        for rule in EXIT_RULES:
            tr = coletar(days, lo_hm, hi_hm, mode, rule, slip)
            v = stats(tr, f"{mode}/{rule}")
            print("  " + linha(v))
            if mode == "caixa" and rule == "sem":
                base = v
    return base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="WDO$")
    ap.add_argument("--start", default="2021-11-01")
    a = ap.parse_args()

    df = load_m5(a.symbol, datetime.strptime(a.start, "%Y-%m-%d"))
    days = build_days(df)
    sinais = {w: sum(1 for d in days if find_signal(d, *w)) for w in
              (("10:30", "11:00"), ("10:00", "11:00"))}
    print("=" * 100)
    print(f"FAIXA 1 - TRAILING | simbolo={a.symbol} barras={len(df)} dias_validos={len(days)}")
    print(f"periodo: {days[0]['day']} -> {days[-1]['day']}")
    print(f"sinais: 10:30-11:00={sinais[('10:30','11:00')]} | "
          f"10:00-11:00={sinais[('10:00','11:00')]}")
    print("modelo: sinal em barra fechada, entrada no close, EOD 17:30, "
          "custo R$1,20, 1 contrato")
    print("=" * 100)

    for slip in (0.0, 0.5, 1.0):
        tabela(days, "10:30", "11:00", slip)

    print("\n" + "=" * 100)
    print("GATE: trailing so promove se melhorar WR E PF vs 'sem' (mesmo stop/slip)")
    print("=" * 100)
    for slip in (0.5, 1.0):
        print(f"\n[slippage {slip:.1f} pt/lado]")
        for mode in ("caixa", "0.5x", "fixed5"):
            base = stats(coletar(days, "10:30", "11:00", mode, "sem", slip), "base")
            for rule in EXIT_RULES[1:]:
                v = stats(coletar(days, "10:30", "11:00", mode, rule, slip), rule)
                passa = (v["win%"] > base["win%"]) and (v["pf"] > base["pf"])
                print(f"  {mode:<7} {rule:<12} dWR={v['win%']-base['win%']:>+5.1f} "
                      f"dPF={v['pf']-base['pf']:>+5.2f} dExpR$={v['exp_rs']-base['exp_rs']:>+7.2f} "
                      f"-> {'PASSA' if passa else 'NAO'}")

    # detalhe do melhor candidato (se algum passar): por ano + IS/OOS
    print("\n" + "=" * 100)
    print("DETALHE caixa/trail8_4 e caixa/be8 (10:30-11:00, slip 1.0) por ano")
    print("=" * 100)
    for rule in ("sem", "trail8_4", "be8", "be8_lock70"):
        tr = coletar(days, "10:30", "11:00", "caixa", rule, 1.0)
        print(f"\n[{rule}] n={len(tr)}")
        by_y = {}
        for t in tr:
            by_y.setdefault(t["year"], []).append(t)
        for y in sorted(by_y):
            print("  " + linha(stats(by_y[y], str(y))))
        for lbl, sub in (("IS 2021-2024", [t for t in tr if t["year"] <= 2024]),
                         ("OOS 2025-2026", [t for t in tr if t["year"] >= 2025])):
            print("  " + linha(stats(sub, lbl)))

    # trailing como substituto do TP (sem TP)
    print("\n" + "=" * 100)
    print("TRAILING NO LUGAR DO TP (sem TP, 10:30-11:00, caixa, slip 1.0)")
    print("=" * 100)
    for rule in ("sem", "trail8_4", "be8", "be8_lock70"):
        v = stats(coletar(days, "10:30", "11:00", "caixa", rule, 1.0, tp_on=False), rule)
        print("  " + linha(v))

    # filtro de vies da 1a hora (box_close vs box_open) no modelo fiel
    print("\n" + "=" * 100)
    print("FILTRO VIES 1a HORA (so opera o lado do corpo da caixa) | 10:30-11:00")
    print("=" * 100)
    for slip in (0.0, 0.5, 1.0):
        print(f"\n[slippage {slip:.1f} pt/lado]")
        for mode in ("caixa", "0.5x"):
            for rule in ("sem", "be8"):
                sem_bias = stats(coletar(days, "10:30", "11:00", mode, rule, slip,
                                         bias=False), f"{mode}/{rule} semvies")
                com_bias = stats(coletar(days, "10:30", "11:00", mode, rule, slip,
                                         bias=True), f"{mode}/{rule} vies")
                print("  " + linha(sem_bias))
                print("  " + linha(com_bias))

    print("\n" + "=" * 100)
    print("DETALHE VIES + stop 0.5x (10:30-11:00, por ano e IS/OOS)")
    print("=" * 100)
    for slip in (0.5, 1.0):
        for rule in ("sem", "be8"):
            tr = coletar(days, "10:30", "11:00", "0.5x", rule, slip, bias=True)
            print(f"\n[vies + 0.5x + {rule} | slip {slip:.1f}] n={len(tr)}")
            by_y = {}
            for t in tr:
                by_y.setdefault(t["year"], []).append(t)
            for y in sorted(by_y):
                print("  " + linha(stats(by_y[y], str(y))))
            for lbl, sub in (("IS 2021-2024", [t for t in tr if t["year"] <= 2024]),
                             ("OOS 2025-2026", [t for t in tr if t["year"] >= 2025])):
                print("  " + linha(stats(sub, lbl)))

    # janela de producao 10:00-11:00, so caixa, para comparar
    print("\n" + "=" * 100)
    print("JANELA DE PRODUCAO 10:00-11:00 (caixa, slip 1.0)")
    print("=" * 100)
    for rule in EXIT_RULES:
        v = stats(coletar(days, "10:00", "11:00", "caixa", rule, 1.0), rule)
        print("  " + linha(v))


if __name__ == "__main__":
    main()
