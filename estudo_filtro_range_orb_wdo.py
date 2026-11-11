"""
estudo_filtro_range_orb_wdo.py — Estudo de FILTRO DE LATERALIZACAO no ORB WDO.
SOMENTE PESQUISA. Read-only: nao envia ordem, nao altera config, nao toca no Core.

Pergunta: vale a pena NAO operar quando o mercado esta lateral/comprimido?

Regras do estudo:
  - Reaproveita o simulador validado de backtest_orb_wdo.py (mesma entrada,
    mesmo simulate, mesmo custo canonico R$ 1,20 por contrato).
  - Gatilho: rompimento da caixa 09:00-10:00 na janela 10:30-11:00 (o candidato
    validado no ROADMAP 23.20/23.21).
  - Features do filtro usam SOMENTE dados ate 10:25 (sem look-ahead).
  - Percentis/medianas usam os 20 dias ANTERIORES (sem look-ahead).
  - Slippage explicito por lado (o backtest de MT5 nao modela isso).
    1 tick WDO = 0.5 ponto = R$ 5,00. Slippage de 1 tick/lado = R$ 10/trade.
  - IS = 2021-2024 | OOS = 2025-2026. Filtro so vale se sobreviver no OOS.

Uso:
    python estudo_filtro_range_orb_wdo.py
    python estudo_filtro_range_orb_wdo.py --symbol "WDO$" --start 2021-11-01
"""
from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from backtest_orb_wdo import (
    COST_RS,
    RS_PER_POINT,
    build_days,
    entry_signal,
    load_m5,
    simulate,
    stats,
)

WIN_LO, WIN_HI = "10:30", "11:00"
CUTOFF = "10:25"          # ultima barra usada para calcular features
TICK_PTS = 0.5            # 1 tick de WDO = 0.5 ponto
HIST = 20                 # dias anteriores para percentis


# ----------------------------------------------------------------------------
# Indicadores (Wilder) calculados na serie continua, sem look-ahead
# ----------------------------------------------------------------------------
def _wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr = _wilder(tr, 14)
    plus_di = 100.0 * _wilder(plus_dm, 14) / atr.replace(0, np.nan)
    minus_di = 100.0 * _wilder(minus_dm, 14) / atr.replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df = df.copy()
    df["atr14"] = atr
    df["adx14"] = _wilder(dx.fillna(0.0), 14)
    return df


def add_features(days: list[dict]) -> None:
    """Features disponiveis as 10:25 (antes da janela de gatilho)."""
    hist_rng, hist_atr = [], []
    for d in days:
        g = d["all"]
        manha = g[g["hm"] <= CUTOFF]
        if len(manha) >= 6:
            hi, lo = float(manha["high"].max()), float(manha["low"].min())
            rng_manha = hi - lo
            move = abs(float(manha["close"].iloc[-1]) - float(manha["open"].iloc[0]))
            last = manha.iloc[-1]
            d["rng_manha"] = rng_manha
            d["eff_manha"] = move / rng_manha if rng_manha > 0 else 0.0
            d["atr14"] = float(last["atr14"])
            d["adx14"] = float(last["adx14"])
            d["rng_1a"] = d["box_high"] - d["box_low"]
        else:
            d["rng_manha"] = np.nan
            d["eff_manha"] = np.nan
            d["atr14"] = np.nan
            d["adx14"] = np.nan
            d["rng_1a"] = d["box_high"] - d["box_low"]

        # percentis com os 20 dias ANTERIORES
        def pct(hist, q):
            return float(np.percentile(hist[-HIST:], q)) if len(hist) >= HIST else None

        d["p_rng_30"] = pct(hist_rng, 30)
        d["p_rng_50"] = pct(hist_rng, 50)
        d["p_rng_70"] = pct(hist_rng, 70)
        d["p_atr_50"] = pct(hist_atr, 50)
        hist_rng.append(d["rng_manha"])
        hist_atr.append(d["atr14"])


# ----------------------------------------------------------------------------
# Execucao
# ----------------------------------------------------------------------------
def run_config(days: list[dict], cond, exit_mode: str, slip_ticks: float = 0.0):
    """Retorna (trades_aceitos, trades_bloqueados). PnL ja com slippage."""
    aceitos, bloqueados = [], []
    for d in days:
        side, entry, stop, _amb, ets = entry_signal(d, WIN_LO, WIN_HI)
        if side is None:
            continue
        rng = d["box_high"] - d["box_low"]
        if exit_mode == "caixa":
            st = stop
        elif exit_mode == "half":
            st = entry - 0.5 * rng if side == "BUY" else entry + 0.5 * rng
        elif exit_mode == "fixed5":
            st = entry - 5.0 if side == "BUY" else entry + 5.0
        else:
            raise ValueError(exit_mode)
        out = simulate(d, side, entry, st, None, ets)
        if out is None:
            continue
        pnl = out[0] - 2.0 * slip_ticks * TICK_PTS   # entrada + saida
        rec = {"pnl": pnl, "mfe": out[2], "mae": -out[3],
               "year": d["day"].year, "day": d["day"]}
        if cond(d, side, entry):
            aceitos.append(rec)
        else:
            bloqueados.append(rec)
    return aceitos, bloqueados


def tstat(trades: list[dict]) -> float:
    if len(trades) < 3:
        return 0.0
    x = np.array([t["pnl"] for t in trades]) * RS_PER_POINT - COST_RS
    sd = x.std(ddof=1)
    return float(x.mean() / (sd / np.sqrt(len(x)))) if sd > 0 else 0.0


def line(label: str, tr: list[dict], blocked: list[dict] | None = None) -> None:
    v = stats(tr, label)
    if v["n"] == 0:
        print(f"{label:<38} {'0':>5}")
        return
    extra = ""
    if blocked:
        vb = stats(blocked, "b")
        extra = f" | bloq n={vb['n']:>4} exp={vb['exp_rs']:>7.2f}"
    print(f"{label:<38} {v['n']:>5} {v['win%']:>6.1f} {v['exp_rs']:>8.2f} "
          f"{v['pf']:>6.2f} {v['total_rs']:>9.0f} {v['maxdd_rs']:>8.0f} "
          f"t={tstat(tr):>5.2f}{extra}")


def header() -> None:
    print(f"{'config':<38} {'n':>5} {'win%':>6} {'exp_R$':>8} {'PF':>6} "
          f"{'total_R$':>9} {'maxDD':>8} {'t':>7}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="WDO$")
    ap.add_argument("--start", default="2021-11-01")
    a = ap.parse_args()

    df = load_m5(a.symbol, datetime.strptime(a.start, "%Y-%m-%d"))
    df = add_indicators(df)
    days = build_days(df)
    add_features(days)
    prev = None
    for d in days:
        d["prev_eod"] = prev
        prev = d["eod_close"]

    hoje = days[-1]["day"]
    estudo = [d for d in days if d["day"] != hoje]   # ultimo dia pode estar aberto
    print(f"simbolo={a.symbol} barras={len(df)} dias={len(days)}")
    print(f"periodo estudo: {estudo[0]['day']} -> {estudo[-1]['day']} "
          f"| excluido (incompleto): {hoje}\n")

    # ------------------------------------------------------------------
    # 1) Distribuicao das features e diagnostico do dia atual
    # ------------------------------------------------------------------
    print("--- features de lateralizacao (calculadas ate 10:25) ---")
    for k, lbl in (("rng_manha", "range 09:00-10:25 (pts)"),
                   ("rng_1a", "range 1a hora (pts)"),
                   ("eff_manha", "eficiencia da manha (0=chop, 1=reta)"),
                   ("atr14", "ATR14 M5 (pts)"),
                   ("adx14", "ADX14 M5")):
        x = np.array([d[k] for d in estudo if not np.isnan(d[k])], dtype=float)
        print(f"  {lbl:<40} mediana={np.median(x):>6.2f}  p20={np.percentile(x,20):>6.2f}  "
              f"p80={np.percentile(x,80):>6.2f}")

    dh = days[-1]
    print(f"\n  HOJE ({dh['day']}): rng_manha={dh['rng_manha']:.1f}  rng_1a={dh['rng_1a']:.1f}  "
          f"eff={dh['eff_manha']:.2f}  atr={dh['atr14']:.2f}  adx={dh['adx14']:.1f}  "
          f"p30_20d={dh['p_rng_30']}")

    # ------------------------------------------------------------------
    # 2) Baseline (sem filtro) para as 3 saidas
    # ------------------------------------------------------------------
    print("\n--- baseline: sem filtro (janela 10:30-11:00) ---")
    header()
    for mode in ("caixa", "half", "fixed5"):
        tr, _ = run_config(estudo, lambda d, s, e: True, mode, 0.0)
        line(f"sem filtro / saida={mode}", tr)

    print("\n--- baseline com slippage (saida=half, a escolhida do paper) ---")
    header()
    for sl in (0.0, 0.5, 1.0, 2.0):
        tr, _ = run_config(estudo, lambda d, s, e: True, "half", sl)
        line(f"half / slippage {sl:g} tick/lado", tr)

    # ------------------------------------------------------------------
    # 3) Filtros no IS (2021-2024)
    # ------------------------------------------------------------------
    def cond_factory(name):
        if name == "rng>=p30":
            return lambda d, s, e: d["p_rng_30"] is not None and d["rng_manha"] >= d["p_rng_30"]
        if name == "rng>=p50":
            return lambda d, s, e: d["p_rng_50"] is not None and d["rng_manha"] >= d["p_rng_50"]
        if name == "rng<=p30 (contrario)":
            return lambda d, s, e: d["p_rng_30"] is not None and d["rng_manha"] <= d["p_rng_30"]
        if name == "atr>=p50":
            return lambda d, s, e: d["p_atr_50"] is not None and d["atr14"] >= d["p_atr_50"]
        if name == "adx>=20":
            return lambda d, s, e: d["adx14"] >= 20.0
        if name == "adx>=25":
            return lambda d, s, e: d["adx14"] >= 25.0
        if name == "adx<20 (contrario)":
            return lambda d, s, e: d["adx14"] < 20.0
        if name == "eff>=0.30":
            return lambda d, s, e: d["eff_manha"] >= 0.30
        if name == "eff>=0.40":
            return lambda d, s, e: d["eff_manha"] >= 0.40
        if name == "adx>=20 e rng>=p30":
            return lambda d, s, e: (d["adx14"] >= 20.0 and d["p_rng_30"] is not None
                                    and d["rng_manha"] >= d["p_rng_30"])
        raise ValueError(name)

    filtros = ["rng>=p30", "rng>=p50", "rng<=p30 (contrario)", "atr>=p50",
               "adx>=20", "adx>=25", "adx<20 (contrario)", "eff>=0.30",
               "eff>=0.40", "adx>=20 e rng>=p30"]

    print("\n--- filtros no IS 2021-2024 (saida=half, slippage 1 tick/lado) ---")
    header()
    is_days = [d for d in estudo if d["day"].year <= 2024]
    resultados_is = {}
    for f in filtros:
        tr, bl = run_config(is_days, cond_factory(f), "half", 1.0)
        v = stats(tr, f)
        resultados_is[f] = v
        line(f, tr, bl)

    # ------------------------------------------------------------------
    # 4) OOS dos filtros que melhoraram no IS
    # ------------------------------------------------------------------
    print("\n--- OOS 2025-2026 (saida=half, slippage 1 tick/lado) ---")
    header()
    oos_days = [d for d in estudo if d["day"].year >= 2025]
    base_is = stats(run_config(is_days, lambda d, s, e: True, "half", 1.0)[0], "base")
    base_oos = stats(run_config(oos_days, lambda d, s, e: True, "half", 1.0)[0], "base")
    print(f"{'(base OOS)':<38} {base_oos['n']:>5} {base_oos['win%']:>6.1f} {base_oos['exp_rs']:>8.2f} "
          f"{base_oos['pf']:>6.2f} {base_oos['total_rs']:>9.0f} {base_oos['maxdd_rs']:>8.0f}")
    for f in filtros:
        tr, bl = run_config(oos_days, cond_factory(f), "half", 1.0)
        line(f, tr, bl)

    # ------------------------------------------------------------------
    # 5) Periodo completo dos filtros com melhor IS
    # ------------------------------------------------------------------
    ordem = sorted(resultados_is.items(), key=lambda kv: kv[1].get("exp_rs", -999), reverse=True)
    top = [f for f, v in ordem[:4]]
    print("\n--- periodo completo (saida=half, slippage 1 tick/lado) ---")
    header()
    for f in ["(sem filtro)"] + top:
        cond = (lambda d, s, e: True) if f == "(sem filtro)" else cond_factory(f)
        tr, bl = run_config(estudo, cond, "half", 1.0)
        line(f, tr, bl)

    # ------------------------------------------------------------------
    # 6) Slippage stress do melhor filtro
    # ------------------------------------------------------------------
    best = top[0]
    print(f"\n--- slippage stress do melhor filtro IS: {best} (saida=half) ---")
    header()
    for sl in (0.0, 0.5, 1.0, 1.5, 2.0):
        tr, _ = run_config(estudo, cond_factory(best), "half", sl)
        line(f"{best} / slip {sl:g} tick/lado", tr)

    # ------------------------------------------------------------------
    # 7) Diagnostico do dia de hoje (o dia lateral)
    # ------------------------------------------------------------------
    print("\n--- diagnostico de HOJE ---")
    for f in ["rng>=p30", "rng>=p50", "adx>=20", "eff>=0.30", "eff>=0.40"]:
        try:
            ok = cond_factory(f)(dh, "BUY", 0.0)
        except Exception:
            ok = None
        print(f"  {f:<22} -> {'PASSA (operaria)' if ok else 'BLOQUEIA'}")

    # ------------------------------------------------------------------
    # 8) ROBUSTEZ do melhor filtro
    # ------------------------------------------------------------------
    f_best = lambda d, s, e: d["eff_manha"] >= 0.40

    print("\n--- robustez: eff>=0.40 nas 3 saidas (periodo completo, slip 1 tick) ---")
    header()
    for mode in ("caixa", "half", "fixed5"):
        tr, bl = run_config(estudo, f_best, mode, 1.0)
        line(f"eff>=0.40 / {mode}", tr, bl)

    print("\n--- robustez: eff>=0.40 por ano (saida=half, slip 1 tick) ---")
    tr, _ = run_config(estudo, f_best, "half", 1.0)
    by_y: dict[int, list] = {}
    for t in tr:
        by_y.setdefault(t["year"], []).append(t)
    for y in sorted(by_y):
        v = stats(by_y[y], str(y))
        print(f"  {y}  n={v['n']:>3}  win%={v['win%']:>5.1f}  exp_R$={v['exp_rs']:>7.2f}  "
              f"PF={v['pf']:>5.2f}  total_R$={v['total_rs']:>7.0f}")

    print("\n--- varredura do limiar de eficiencia (saida=half, slip 1 tick) ---")
    header()
    for thr in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
        cond = (lambda t: (lambda d, s, e: d["eff_manha"] >= t))(thr)
        tr2, bl2 = run_config(estudo, cond, "half", 1.0)
        line(f"eff>={thr:.2f}", tr2, bl2)

    print("\n--- dois lados: manha direcional mas dia nao caotico ---")
    header()
    cond_two = lambda d, s, e: (d["eff_manha"] >= 0.40 and d["p_rng_70"] is not None
                                and d["rng_manha"] <= d["p_rng_70"])
    tr3, bl3 = run_config(estudo, cond_two, "half", 1.0)
    line("eff>=0.40 e rng<=p70", tr3, bl3)

    # ------------------------------------------------------------------
    # 9) IS/OOS do limiar escolhido + candidato final
    # ------------------------------------------------------------------
    print("\n--- IS/OOS por limiar de eficiencia (saida=half, slip 1 tick) ---")
    header()
    for thr in (0.40, 0.45, 0.50):
        cond = (lambda t: (lambda d, s, e: d["eff_manha"] >= t))(thr)
        tr_is, _ = run_config(is_days, cond, "half", 1.0)
        tr_oos, _ = run_config(oos_days, cond, "half", 1.0)
        line(f"eff>={thr:.2f} IS", tr_is)
        line(f"eff>={thr:.2f} OOS", tr_oos)

    print("\n--- slippage stress de eff>=0.40 (saida=half) ---")
    header()
    for sl in (0.0, 0.5, 1.0, 1.5, 2.0):
        tr4, _ = run_config(estudo, f_best, "half", sl)
        line(f"eff>=0.40 / slip {sl:g} tick/lado", tr4)

    print("\n--- candidato final: eff>=0.40 + vies 1a hora + stop fixo 5 pts ---")
    f_bias = lambda d, s, e: ((s == "BUY" and d["box_close"] > d["box_open"])
                              or (s == "SELL" and d["box_close"] < d["box_open"]))
    header()
    for lbl, cond, mode in (
            ("eff>=0.40 + fixed5", f_best, "fixed5"),
            ("eff>=0.40 + vies + fixed5", lambda d, s, e: f_best(d, s, e) and f_bias(d, s, e), "fixed5"),
            ("eff>=0.40 + vies + half", lambda d, s, e: f_best(d, s, e) and f_bias(d, s, e), "half"),
    ):
        tr5, bl5 = run_config(estudo, cond, mode, 1.0)
        line(lbl, tr5, bl5)
        tr_is, _ = run_config(is_days, cond, mode, 1.0)
        tr_oos, _ = run_config(oos_days, cond, mode, 1.0)
        line(f"  {lbl} IS", tr_is)
        line(f"  {lbl} OOS", tr_oos)


if __name__ == "__main__":
    main()
