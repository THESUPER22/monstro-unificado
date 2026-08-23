# -*- coding: utf-8 -*-
"""Backtest do setup Markov Tendencia WDO sobre os dias reais da semana.

Compara o resultado diario do setup validado (breakout_ratio=1.0,
stop emergencia) com o desempenho real do Sniper no mesmo periodo.
Requer MetaTrader 5 conectado.
"""
import sys
import pandas as pd
import MetaTrader5 as mt5

sys.path.insert(0, r"C:\AIOFEN")
import backtest_markov_4estados as bk

DE = "2026-08-14"
ATE = "2026-08-22"
SIMBOLOS = ["WDOU26", "WDOV26"]


def carregar(symbol):
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1,
                                 pd.Timestamp(DE), pd.Timestamp(ATE))
    if rates is None or len(rates) == 0:
        return None
    m1 = pd.DataFrame(rates)
    m1["time"] = pd.to_datetime(m1["time"], unit="s")
    m1.set_index("time", inplace=True)
    return m1.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def main():
    if not mt5.initialize():
        print("MT5 indisponivel agora. Rodar pre-pregao em dia util.")
        return 1
    try:
        d5 = None
        for s in SIMBOLOS:
            d5 = carregar(s)
            if d5 is not None and len(d5) > 100:
                print(f"Dados: {s} | {len(d5)} barras M5 "
                      f"({d5.index[0]:%d/%m} a {d5.index[-1]:%d/%m})")
                break
        if d5 is None:
            print("Sem dados M1 para o periodo nos simbolos testados.")
            return 1

        bk.calcular_indicadores(d5)
        bk.classificar_estados(d5, breakout_ratio=1.0)
        trades = bk.rodar(d5, pt_value=10, usar_consol=False,
                          breakout_ratio=1.0, stop_emergencia=True)
        if trades is None or (hasattr(trades, "empty") and trades.empty) or len(trades) == 0:
            print("Nenhum trade gerado no setup para o periodo.")
            return 0

        t = pd.DataFrame(trades)
        t["dia"] = pd.to_datetime(t["entrada"]).dt.date

        print("\nSetup Tendencia WDO (ratio=1.0, stop emergencia) por dia:")
        sniper_real = {"2026-08-21": -55.00}
        for dia, g in t.groupby("dia"):
            net = g["brl"].sum()
            wr = (g["brl"] > 0).mean() * 100
            ref = ""
            chave = str(dia)
            if chave in sniper_real:
                ref = f"  <- Sniper real fez R${sniper_real[chave]:.2f}"
            print(f"  {dia}  n={len(g):>2}  WR={wr:>3.0f}%  net=R${net:>8.2f}{ref}")

        sex = t[t["dia"] == pd.Timestamp("2026-08-21").date()]
        if len(sex):
            print("\nDetalhe de sexta (setup teria feito):")
            for _, r in sex.iterrows():
                print(f"  {pd.to_datetime(r['entrada']):%H:%M} {r['tipo']:<4} "
                      f"R${r['brl']:>7.2f} ({r['motivo']})")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
