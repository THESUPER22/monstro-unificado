"""
backtest_orb_wdo.py — Estudo ORB (Opening Range Breakout) no WDO, SOMENTE PESQUISA.

Read-only: nao envia ordem, nao altera config, nao toca no Core.
Fonte: WDO$ M5 do terminal MT5 (serie continua), convertida para BRT (+3h).

Definicao testada (identica em espirito ao Rompimento da 1a Hora):
  caixa  = 09:00-10:00 BRT (primeira hora)
  gatilho= 10:00-11:00 BRT (rompimento do high/low da caixa)
  stop   = lado oposto da caixa (risco = tamanho da caixa)
  saida  = TP em multiplos de R ou EOD 17:55 BRT

Controles (para separar edge de deriva do dolar):
  CTRL-LONG : comprado as 10:00, sai no EOD (mede a deriva)
  CTRL-MIRROR: lado oposto do sinal ORB (se o ORB tem edge, isso perde)

Custos: R$ 1,20 por contrato por operacao (0,60 entrada + 0,60 saida),
        1 ponto = R$ 10,00 -> 0,12 ponto por trade.

Uso:
    python backtest_orb_wdo.py
    python backtest_orb_wdo.py --symbol WDO$ --start 2021-11-01
"""
from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

SHIFT_H = 0            # copy_rates_range ja devolve barra em BRT; o +3h vale para TICKS
COST_RS = 1.20         # R$ 0,60 entrada + R$ 0,60 saida, por contrato (canonico 10/11/2026)
RS_PER_POINT = 10.0
BOX_START, BOX_END = "09:00", "10:00"
TRIG_END = "11:00"
EOD = "17:55"


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
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["day"] = df["ts"].dt.date
    df["hm"] = df["ts"].dt.strftime("%H:%M")
    # sessao diurna apenas (09:00-18:00 BRT)
    df = df[(df["hm"] >= "09:00") & (df["hm"] <= "18:00")]
    return df.reset_index(drop=True)


def build_days(df: pd.DataFrame) -> list[dict]:
    days = []
    for day, g in df.groupby("day", sort=True):
        g = g.sort_values("ts")
        box = g[(g["hm"] >= BOX_START) & (g["hm"] < BOX_END)]
        trig = g[(g["hm"] >= BOX_END) & (g["hm"] < TRIG_END)]
        after = g[g["hm"] >= TRIG_END]
        if len(box) < 8 or len(trig) < 4 or len(after) < 10:
            continue
        tpv = float(((box["high"] + box["low"] + box["close"]) / 3 * box["tick_volume"]).sum())
        vol = float(box["tick_volume"].sum())
        days.append({
            "day": day,
            "box_high": float(box["high"].max()),
            "box_low": float(box["low"].min()),
            "box_open": float(box["open"].iloc[0]),
            "box_close": float(box["close"].iloc[-1]),
            "box_vol": vol,
            "box_vwap": tpv / vol if vol else float(box["close"].mean()),
            "box_ema20": float(box["ema20"].iloc[-1]),
            "box_ema50": float(box["ema50"].iloc[-1]),
            "trig": trig,
            "after": after,
            "eod_close": float(after["close"].iloc[-1]),
        })
    return days


def entry_signal(d: dict, lo="10:00", hi="11:00", confirm=False):
    """Retorna (side, entry, stop, ambiguous) do rompimento na janela de gatilho."""
    bh, bl = d["box_high"], d["box_low"]
    trig = d["trig"]
    trig = trig[(trig["hm"] >= lo) & (trig["hm"] < hi)]
    for _, bar in trig.iterrows():
        if confirm:
            up = bar["close"] > bh
            dn = bar["close"] < bl
            px_up, px_dn = float(bar["close"]), float(bar["close"])
        else:
            up = bar["high"] > bh
            dn = bar["low"] < bl
            px_up, px_dn = bh, bl
        if up and dn:
            return None, None, None, True      # barra ambigua: pula o dia
        if up:
            return "BUY", px_up, bl, False
        if dn:
            return "SELL", px_dn, bh, False
    return None, None, None, False


def simulate(d: dict, side: str, entry: float, stop: float, k_tp: float | None):
    """Retorna (pnl_pts_bruto, exit, mfe, mae). Conservador: stop antes do TP."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    tp = None if k_tp is None else (entry + k_tp * risk if side == "BUY" else entry - k_tp * risk)
    mfe = mae = 0.0
    for _, bar in d["after"].iterrows():
        hi, lo = bar["high"], bar["low"]
        if side == "BUY":
            mfe = max(mfe, hi - entry)
            mae = min(mae, lo - entry)
            hit_sl, hit_tp = lo <= stop, (tp is not None and hi >= tp)
            if hit_sl:
                return stop - entry, "SL", mfe, mae
            if hit_tp:
                return tp - entry, "TP", mfe, mae
        else:
            mfe = max(mfe, entry - lo)
            mae = min(mae, entry - hi)
            hit_sl, hit_tp = hi >= stop, (tp is not None and lo <= tp)
            if hit_sl:
                return entry - stop, "SL", mfe, mae
            if hit_tp:
                return entry - tp, "TP", mfe, mae
    return (d["eod_close"] - entry) if side == "BUY" else (entry - d["eod_close"]), "EOD", mfe, mae


def stats(trades: list[dict], label: str) -> dict:
    if not trades:
        return {"label": label, "n": 0}
    pts = np.array([t["pnl"] for t in trades], dtype=float)
    net_rs = pts * RS_PER_POINT - COST_RS
    eq = np.cumsum(net_rs)
    dd = float(np.min(eq - np.maximum.accumulate(eq))) if len(eq) else 0.0
    wins, losses = net_rs[net_rs > 0], net_rs[net_rs < 0]
    pf = float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    return {
        "label": label,
        "n": len(trades),
        "win%": 100.0 * len(wins) / len(trades),
        "exp_pts": float(pts.mean()),
        "exp_rs": float(net_rs.mean()),
        "pf": pf,
        "total_rs": float(net_rs.sum()),
        "maxdd_rs": dd,
        "avg_mfe": float(np.mean([t["mfe"] for t in trades])),
        "avg_mae": float(np.mean([t["mae"] for t in trades])),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="WDO$")
    ap.add_argument("--start", default="2021-11-01")
    a = ap.parse_args()

    df = load_m5(a.symbol, datetime.strptime(a.start, "%Y-%m-%d"))
    days = build_days(df)
    prev = None
    for d in days:
        d["prev_eod"] = prev
        prev = d["eod_close"]
    print(f"simbolo={a.symbol} barras={len(df)} dias_validos={len(days)}")
    print(f"periodo: {days[0]['day']} -> {days[-1]['day']}\n")

    box_rng = np.array([d["box_high"] - d["box_low"] for d in days])
    print("--- mecanismo: tamanho da caixa (1a hora) e o que sobra do dia ---")
    print(f"caixa (pts): mediana={np.median(box_rng):.1f} p20={np.percentile(box_rng,20):.1f} "
          f"p80={np.percentile(box_rng,80):.1f} max={box_rng.max():.1f}")

    rows, amb = [], 0
    for d in days:
        side, entry, stop, ambiguous = entry_signal(d)
        amb += int(ambiguous)
        if side is None:
            continue
        d.update({"side": side, "entry": entry, "stop": stop})
        rows.append(d)

    rompeu = len(rows)
    print(f"dias com rompimento na 1a hora seguinte: {rompeu}/{len(days)} "
          f"({100*rompeu/len(days):.1f}%) | ambiguos={amb}")

    # MFE/MAE: o edge bruto do rompimento
    res = [simulate(d, d["side"], d["entry"], d["stop"], None) for d in rows]
    mfe = np.array([r[2] for r in res])
    mae = np.array([-r[3] for r in res])
    print(f"apos o rompimento: MFE mediano={np.median(mfe):.1f} pts | "
          f"MAE mediano={np.median(mae):.1f} pts | razao={np.median(mfe)/max(np.median(mae),1e-9):.2f}")
    print(f"MFE/MAE por trade > 1 em {100*np.mean(mfe > mae):.1f}% dos dias\n")

    variants = []
    for k in (1.0, 1.5, 2.0, 3.0):
        tr = []
        for d in rows:
            out = simulate(d, d["side"], d["entry"], d["stop"], k)
            tr.append({"pnl": out[0], "mfe": out[2], "mae": -out[3]})
        variants.append(stats(tr, f"ORB TP={k:g}R"))

    tr = [{"pnl": simulate(d, d["side"], d["entry"], d["stop"], None)[0],
           "mfe": 0, "mae": 0} for d in rows]
    variants.append(stats(tr, "ORB sem TP (EOD)"))

    tr = [{"pnl": simulate(d, d["side"], d["entry"], d["stop"], None)[0], "mfe": 0, "mae": 0} for d in rows]
    tr_m = [{"pnl": -t["pnl"], "mfe": 0, "mae": 0} for t in tr]
    variants.append(stats(tr_m, "CTRL-MIRROR (lado oposto, EOD)"))

    ctrl_long = [{"pnl": d["eod_close"] - float(d["after"]["open"].iloc[0]), "mfe": 0, "mae": 0} for d in days]
    variants.append(stats(ctrl_long, "CTRL-LONG 10:00 -> EOD (deriva)"))

    print(f"{'variante':<32} {'n':>5} {'win%':>6} {'exp_pts':>8} {'exp_R$':>8} {'PF':>6} "
          f"{'total_R$':>10} {'maxDD_R$':>10}")
    for v in variants:
        print(f"{v['label']:<32} {v['n']:>5} {v['win%']:>6.1f} {v['exp_pts']:>8.2f} "
              f"{v['exp_rs']:>8.2f} {v['pf']:>6.2f} {v['total_rs']:>10.0f} {v['maxdd_rs']:>10.0f}")

    # filtro de regime: caixa entre p20 e p80 dos ultimos 20 dias (ideia do repo vespera)
    print("\n--- filtro de regime: caixa dentro de [p20,p80] dos ultimos 20 dias ---")
    kept = []
    hist = []
    for d in days:
        rng = d["box_high"] - d["box_low"]
        if len(hist) >= 20:
            lo, hi = np.percentile(hist[-20:], 20), np.percentile(hist[-20:], 80)
            d["_in_band"] = lo <= rng <= hi
        else:
            d["_in_band"] = True
        hist.append(rng)
        if d.get("_in_band") and any(x["day"] == d["day"] for x in rows):
            kept.append(d)
    tr = []
    for d in kept:
        side, entry, stop, _ = entry_signal(d)
        if side is None:
            continue
        tr.append({"pnl": simulate(d, side, entry, stop, None)[0], "mfe": 0, "mae": 0})
    v = stats(tr, "ORB filtrado (EOD)")
    print(f"{v['label']:<32} n={v['n']} win%={v['win%']:.1f} exp_R$={v['exp_rs']:.2f} "
          f"PF={v['pf']:.2f} total_R$={v['total_rs']:.0f} maxDD_R$={v['maxdd_rs']:.0f}")

    # por ano
    print("\n--- ORB sem TP (EOD), por ano ---")
    by_year: dict[int, list] = {}
    for d in rows:
        by_year.setdefault(d["day"].year, []).append(
            {"pnl": simulate(d, d["side"], d["entry"], d["stop"], None)[0], "mfe": 0, "mae": 0})
    for y in sorted(by_year):
        v = stats(by_year[y], str(y))
        print(f"{y}  n={v['n']:>3}  win%={v['win%']:>5.1f}  exp_R$={v['exp_rs']:>7.2f}  "
              f"PF={v['pf']:>5.2f}  total_R$={v['total_rs']:>8.0f}")

    # direcao
    longs = [d for d in rows if d["side"] == "BUY"]
    shorts = [d for d in rows if d["side"] == "SELL"]
    print(f"\ndirecao: BUY={len(longs)} SELL={len(shorts)}")
    for lbl, sub in (("BUY", longs), ("SELL", shorts)):
        tr = [{"pnl": simulate(d, d["side"], d["entry"], d["stop"], None)[0], "mfe": 0, "mae": 0} for d in sub]
        v = stats(tr, lbl)
        print(f"  {lbl:<5} n={v['n']:>3} win%={v['win%']:>5.1f} exp_R$={v['exp_rs']:>7.2f} PF={v['pf']:.2f}")

    # ------------------------------------------------------------------
    # SENSIBILIDADE: onde (se em algum lugar) o edge sobrevive
    # ------------------------------------------------------------------
    print("\n--- sensibilidade (saida EOD, custo R$1.20) ---")
    print(f"{'variante':<44} {'n':>5} {'win%':>6} {'exp_R$':>8} {'PF':>6} {'total_R$':>10} {'maxDD_R$':>10}")

    def run_cfg(label, lo="10:00", hi="11:00", confirm=False, stop_mult=1.0,
                need=None, vol_filter=False):
        tr = []
        for d in days:
            rng = d["box_high"] - d["box_low"]
            if need is not None and not need(d, rng):
                continue
            if vol_filter:
                v20 = d.get("_vol_med")
                if v20 and d["box_vol"] < v20:
                    continue
            side, entry, stop, _ = entry_signal(d, lo, hi, confirm)
            if side is None:
                continue
            if stop_mult != 1.0:
                stop = entry - stop_mult * rng if side == "BUY" else entry + stop_mult * rng
            pnl = simulate(d, side, entry, stop, None)[0]
            tr.append({"pnl": pnl, "mfe": 0, "mae": 0})
        v = stats(tr, label)
        if v["n"] == 0:
            print(f"{label:<44} {'0':>5}")
            return
        print(f"{label:<44} {v['n']:>5} {v['win%']:>6.1f} {v['exp_rs']:>8.2f} "
              f"{v['pf']:>6.2f} {v['total_rs']:>10.0f} {v['maxdd_rs']:>10.0f}")

    # percentis/mediana com 20 dias anteriores (sem lookahead)
    hist_rng, hist_vol = [], []
    for d in days:
        rng = d["box_high"] - d["box_low"]
        d["_p30"] = np.percentile(hist_rng[-20:], 30) if len(hist_rng) >= 20 else None
        d["_p70"] = np.percentile(hist_rng[-20:], 70) if len(hist_rng) >= 20 else None
        d["_vol_med"] = float(np.median(hist_vol[-20:])) if len(hist_vol) >= 20 else None
        d["_med20"] = float(np.median(hist_rng[-20:])) if len(hist_rng) >= 20 else None
        hist_rng.append(rng)
        hist_vol.append(d["box_vol"])

    run_cfg("base (gatilho 10:00-11:00, stop = caixa)")
    run_cfg("gatilho 10:00-10:30", lo="10:00", hi="10:30")
    run_cfg("gatilho 10:30-11:00 (abertura EUA)", lo="10:30", hi="11:00")
    run_cfg("confirmacao no fechamento da barra", confirm=True)
    run_cfg("stop 0.5x caixa", stop_mult=0.5)
    run_cfg("stop 1.5x caixa", stop_mult=1.5)
    run_cfg("caixa comprimida (< p30 20d)", need=lambda d, r: d["_p30"] is not None and r <= d["_p30"])
    run_cfg("caixa expandida (> p70 20d)", need=lambda d, r: d["_p70"] is not None and r >= d["_p70"])
    run_cfg("volume da caixa >= mediana 20d", vol_filter=True)
    run_cfg("comprimida + volume acima da mediana",
            need=lambda d, r: d["_p30"] is not None and r <= d["_p30"], vol_filter=True)

    # ------------------------------------------------------------------
    # VALIDACAO do gatilho 10:30-11:00 (o unico com PF relevante)
    # ------------------------------------------------------------------
    print("\n--- validacao: gatilho 10:30-11:00, stop = caixa, saida EOD ---")

    def collect(lo="10:30", hi="11:00", stop_mult=1.0, k_tp=None, subset=None):
        tr = []
        for d in days:
            if subset is not None and not subset(d):
                continue
            rng = d["box_high"] - d["box_low"]
            side, entry, stop, _ = entry_signal(d, lo, hi)
            if side is None:
                continue
            if stop_mult != 1.0:
                stop = entry - stop_mult * rng if side == "BUY" else entry + stop_mult * rng
            out = simulate(d, side, entry, stop, k_tp)
            tr.append({"pnl": out[0], "mfe": out[2], "mae": -out[3], "year": d["day"].year})
        return tr

    tr = collect()
    by_year = {}
    for t in tr:
        by_year.setdefault(t["year"], []).append(t)
    for y in sorted(by_year):
        v = stats(by_year[y], str(y))
        print(f"  {y}  n={v['n']:>3}  win%={v['win%']:>5.1f}  exp_R$={v['exp_rs']:>7.2f}  "
              f"PF={v['pf']:>5.2f}  total_R$={v['total_rs']:>8.0f}")

    def seg(name, sub):
        v = stats(sub, name)
        print(f"  {name:<22} n={v['n']:>3} win%={v['win%']:>5.1f} exp_R$={v['exp_rs']:>7.2f} "
              f"PF={v['pf']:>5.2f} total_R$={v['total_rs']:>8.0f}")

    seg("IS 2021-2024", [t for t in tr if t["year"] <= 2024])
    seg("OOS 2025-2026", [t for t in tr if t["year"] >= 2025])

    print("\n  stress de custo/slippage (por trade):")
    for extra_pts in (0.0, 0.5, 1.0, 2.0):
        net = np.array([t["pnl"] for t in tr]) * RS_PER_POINT - COST_RS - extra_pts * RS_PER_POINT
        print(f"    +{extra_pts:.1f} pt  exp_R$={net.mean():>7.2f}  total_R$={net.sum():>9.0f}  "
              f"win%={100*np.mean(net > 0):>5.1f}")

    print("\n  TP alternativo (mesma janela):")
    for k in (1.0, 2.0, 3.0):
        v = stats(collect(k_tp=k), f"10:30 TP={k:g}R")
        print(f"    TP={k:g}R  n={v['n']} win%={v['win%']:.1f} exp_R$={v['exp_rs']:.2f} "
              f"PF={v['pf']:.2f} total_R$={v['total_rs']:.0f}")

    print("\n  stop menor (mesma janela):")
    for m in (0.5, 0.75):
        v = stats(collect(stop_mult=m), f"10:30 stop={m:g}x")
        print(f"    stop={m:g}x  n={v['n']} win%={v['win%']:.1f} exp_R$={v['exp_rs']:.2f} "
              f"PF={v['pf']:.2f} total_R$={v['total_rs']:.0f} maxDD_R$={v['maxdd_rs']:.0f}")

    print("\n  risco medio por trade (stop = caixa):")
    risks = []
    for d in days:
        side, entry, stop, _ = entry_signal(d, "10:30", "11:00")
        if side is not None:
            risks.append(abs(entry - stop) * RS_PER_POINT)
    print(f"    mediana R$ {np.median(risks):.0f} | p80 R$ {np.percentile(risks,80):.0f} | max R$ {max(risks):.0f}")

    # ------------------------------------------------------------------
    # FILTROS: alguma coisa sobe acertividade de verdade?
    # ------------------------------------------------------------------
    print("\n--- filtros sobre o gatilho 10:30-11:00 (stop = caixa, EOD) ---")
    print(f"{'filtro':<40} {'n':>5} {'win%':>6} {'exp_R$':>8} {'PF':>6} {'total_R$':>10} {'maxDD_R$':>10}")

    def run_filter(label, cond, stop_mult=1.0):
        tr = []
        for d in days:
            if d["prev_eod"] is None:
                continue
            side, entry, stop, _ = entry_signal(d, "10:30", "11:00")
            if side is None or not cond(d, side, entry):
                continue
            rng = d["box_high"] - d["box_low"]
            if stop_mult != 1.0:
                stop = entry - stop_mult * rng if side == "BUY" else entry + stop_mult * rng
            pnl = simulate(d, side, entry, stop, None)[0]
            tr.append({"pnl": pnl, "mfe": 0, "mae": 0})
        v = stats(tr, label)
        if v["n"] == 0:
            print(f"{label:<40} {'0':>5}")
            return v
        print(f"{label:<40} {v['n']:>5} {v['win%']:>6.1f} {v['exp_rs']:>8.2f} "
              f"{v['pf']:>6.2f} {v['total_rs']:>10.0f} {v['maxdd_rs']:>10.0f}")
        return v

    f_vwap = lambda d, s, e: (s == "BUY" and e > d["box_vwap"]) or (s == "SELL" and e < d["box_vwap"])
    f_ema = lambda d, s, e: (s == "BUY" and d["box_ema20"] > d["box_ema50"]) or \
                            (s == "SELL" and d["box_ema20"] < d["box_ema50"])
    f_bias = lambda d, s, e: (s == "BUY" and d["box_close"] > d["box_open"]) or \
                             (s == "SELL" and d["box_close"] < d["box_open"])
    f_gap = lambda d, s, e: (s == "BUY" and d["box_open"] > d["prev_eod"]) or \
                            (s == "SELL" and d["box_open"] < d["prev_eod"])
    f_cap = lambda d, s, e: d["_med20"] is not None and \
                            (d["box_high"] - d["box_low"]) <= 2.0 * d["_med20"]

    run_filter("sem filtro (referencia)", lambda d, s, e: True)
    run_filter("+ rompimento acima/abaixo do VWAP", f_vwap)
    run_filter("+ alinhado com EMA20/EMA50", f_ema)
    run_filter("+ alinhado com o vies da 1a hora", f_bias)
    run_filter("+ alinhado com o gap (vs fecho anterior)", f_gap)
    run_filter("+ caixa <= 2x mediana 20d (dia nao caotico)", f_cap)
    run_filter("VWAP + caixa <= 2x mediana", lambda d, s, e: f_vwap(d, s, e) and f_cap(d, s, e))
    run_filter("VWAP + stop 0.5x", f_vwap, stop_mult=0.5)
    run_filter("vies 1a hora + stop 0.5x", f_bias, stop_mult=0.5)
    run_filter("EMA + caixa <= 2x mediana + stop 0.5x",
               lambda d, s, e: f_ema(d, s, e) and f_cap(d, s, e), stop_mult=0.5)

    # ------------------------------------------------------------------
    # VALIDACAO FINAL dos 2 candidatos (por ano + IS/OOS + stress)
    # ------------------------------------------------------------------
    print("\n--- validacao final dos candidatos ---")

    def collect_filter(cond, stop_mult):
        tr = []
        for d in days:
            if d["prev_eod"] is None:
                continue
            side, entry, stop, _ = entry_signal(d, "10:30", "11:00")
            if side is None or not cond(d, side, entry):
                continue
            rng = d["box_high"] - d["box_low"]
            if stop_mult != 1.0:
                stop = entry - stop_mult * rng if side == "BUY" else entry + stop_mult * rng
            out = simulate(d, side, entry, stop, None)
            tr.append({"pnl": out[0], "mfe": out[2], "mae": -out[3], "year": d["day"].year})
        return tr

    candidates = [
        ("vies 1a hora + stop 0.5x", f_bias, 0.5),
        ("EMA + caixa<=2x + stop 0.5x", lambda d, s, e: f_ema(d, s, e) and f_cap(d, s, e), 0.5),
    ]
    for name, cond, sm in candidates:
        tr = collect_filter(cond, sm)
        print(f"\n  [{name}] n={len(tr)}")
        by_y = {}
        for t in tr:
            by_y.setdefault(t["year"], []).append(t)
        for y in sorted(by_y):
            v = stats(by_y[y], str(y))
            print(f"    {y}  n={v['n']:>3}  win%={v['win%']:>5.1f}  exp_R$={v['exp_rs']:>7.2f}  "
                  f"PF={v['pf']:>5.2f}  total_R$={v['total_rs']:>8.0f}")
        for lbl, sub in (("IS 2021-2024", [t for t in tr if t["year"] <= 2024]),
                         ("OOS 2025-2026", [t for t in tr if t["year"] >= 2025])):
            v = stats(sub, lbl)
            print(f"    {lbl:<15} n={v['n']:>3} win%={v['win%']:>5.1f} exp_R$={v['exp_rs']:>7.2f} "
                  f"PF={v['pf']:>5.2f} total_R$={v['total_rs']:>8.0f}")
        for extra in (0.0, 1.0, 2.0):
            net = np.array([t["pnl"] for t in tr]) * RS_PER_POINT - COST_RS - extra * RS_PER_POINT
            print(f"    +{extra:.0f} pt slippage: exp_R$={net.mean():>7.2f} total_R$={net.sum():>9.0f}")


if __name__ == "__main__":
    main()
