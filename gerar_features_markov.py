import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest_markov_4estados import (
    carregar_dados, calcular_indicadores, classificar_estados, PARAMS,
)


def extrair_features(df, breakout_ratio=1.0):
    df = classificar_estados(df.copy(), breakout_ratio).copy()

    em_sessao = (
        ((df.index.hour == 9) & (df.index.minute >= 10))
        | ((df.index.hour >= 10) & (df.index.hour < 12))
        | ((df.index.hour >= 14) & (df.index.hour < 17))
    )
    almoco = (df.index.hour >= 12) & (df.index.hour < 14)

    feat = pd.DataFrame(index=df.index)
    for k, nome in [(0, "alta"), (1, "baixa"), (2, "consol"), (3, "breakout")]:
        feat[f"estado_{nome}"] = (df["estado"] == k).astype(int)
        feat[f"estado_prev_{nome}"] = (df["estado"].shift(1) == k).astype(int)
    feat["atr_ratio"] = df["atr_ratio"]
    feat["slope"] = df["slope"]
    feat["dist_ema_atr"] = (df["close"] - df["ema"]) / df["atr"]
    feat["corpo_atr"] = (df["close"] - df["open"]) / df["atr"]
    feat["sessao_manha"] = em_sessao.astype(int)
    feat["sessao_almoco"] = almoco.astype(int)
    feat["sessao_tarde"] = (
        (df.index.hour >= 14) & (df.index.hour < 17) & em_sessao
    ).astype(int)
    feat["close"] = df["close"]

    return feat.dropna()


if __name__ == "__main__":
    if not mt5.initialize():
        raise SystemExit("Falha ao inicializar MT5")

    ativos = {
        "WDO": {"symbol": "WDO$", "fallback": "WDOV26"},
        "WIN": {"symbol": "WIN$", "fallback": "WINV26"},
    }

    for nome, cfg in ativos.items():
        symbol = cfg["symbol"]
        if not mt5.symbol_select(symbol, True):
            symbol = cfg["fallback"]
            mt5.symbol_select(symbol, True)
        df = carregar_dados(symbol)
        if df is None:
            print(f"{nome}: sem dados")
            continue
        df = calcular_indicadores(df)
        feat = extrair_features(df, breakout_ratio=1.0)
        saida = rf"C:\AIOFEN\features_markov_{nome.lower()}.csv"
        feat.to_csv(saida)
        dist = feat[[c for c in feat.columns if c.startswith("estado_") and "prev" not in c]].sum()
        print(f"{nome}: {len(feat)} barras M5 -> {saida}")
        print(f"  Estados: {dict(dist.astype(int))}")

    mt5.shutdown()
