import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest_markov_4estados import (
    carregar_dados, calcular_indicadores, classificar_estados,
)

RR = 1.5
STOP_ATR = 1.5
HORIZONTE_BARRAS = 6

FEATS_MARKOV = [
    "estado_alta", "estado_baixa", "estado_consol", "estado_breakout",
    "estado_prev_alta", "estado_prev_baixa", "estado_prev_consol", "estado_prev_breakout",
    "atr_ratio", "slope", "dist_ema_atr", "corpo_atr",
    "sessao_manha", "sessao_almoco", "sessao_tarde",
]


def calcular_mtf_historico(df_m1):
    """Reconstrói features multi-timeframe (5m/15m/30m) a partir do M1."""
    def indicadores_tf(d, regra):
        t = d.resample(regra).agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "tick_volume": "sum"}).dropna()
        delta = t["close"].diff()
        ganho = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        perda = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rs = ganho / perda.replace(0, np.nan)
        t["rsi"] = 100 - 100 / (1 + rs)
        hl = t["high"] - t["low"]
        hc = (t["high"] - t["close"].shift()).abs()
        lc = (t["low"] - t["close"].shift()).abs()
        t["atr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(
            alpha=1 / 14, adjust=False).mean()
        maior = t["high"].rolling(14).max()
        menor = t["low"].rolling(14).min()
        t["wr"] = -100 * (maior - t["close"]) / (maior - menor).replace(0, np.nan)
        return t[["close", "rsi", "atr", "wr", "tick_volume"]]

    partes = {}
    for tf, regra in [("5", "5min"), ("15", "15min"), ("30", "30min")]:
        t = indicadores_tf(df_m1, regra)
        for col in t.columns:
            partes[f"mtf_{col}_{tf}"] = t[col]
    mtf = pd.DataFrame(partes)
    grade = df_m1.resample("5min").close.last().index
    mtf = mtf.reindex(grade).ffill()
    return mtf


def montar_dataset():
    if not mt5.initialize():
        raise SystemExit("Falha ao inicializar MT5")
    symbol = "WDO$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WDOV26"
        mt5.symbol_select(symbol, True)
    utc_to = datetime.now()
    rates = mt5.copy_rates_range(
        symbol, mt5.TIMEFRAME_M1, utc_to - timedelta(days=365), utc_to)
    df_m1 = pd.DataFrame(rates)
    df_m1["time"] = pd.to_datetime(df_m1["time"], unit="s")
    df_m1.set_index("time", inplace=True)

    mtf = calcular_mtf_historico(df_m1)

    df = carregar_dados(symbol)
    mt5.shutdown()
    df = calcular_indicadores(df)
    df = classificar_estados(df, 1.0)

    for k, nome in [(0, "alta"), (1, "baixa"), (2, "consol"), (3, "breakout")]:
        df[f"estado_{nome}"] = (df["estado"] == k).astype(int)
        df[f"estado_prev_{nome}"] = (df["estado"].shift(1) == k).astype(int)
    df["dist_ema_atr"] = (df["close"] - df["ema"]) / df["atr"]
    df["corpo_atr"] = (df["close"] - df["open"]) / df["atr"]
    h, m = df.index.hour, df.index.minute
    df["sessao_manha"] = (((h == 9) & (m >= 10)) | ((h >= 10) & (h < 12))).astype(int)
    df["sessao_almoco"] = ((h >= 12) & (h < 14)).astype(int)
    df["sessao_tarde"] = ((h >= 14) & (h < 17)).astype(int)

    df = df.join(mtf, how="left")
    return df


def criar_label(df):
    n = len(df)
    close = df["close"].values
    atr = df["atr"].values
    high = df["high"].values
    low = df["low"].values
    label = np.full(n, np.nan)

    for i in range(n - HORIZONTE_BARRAS):
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entrada = close[i]
        stop = entrada - STOP_ATR * a
        alvo = entrada + STOP_ATR * a * RR
        res = np.nan
        for j in range(i + 1, i + 1 + HORIZONTE_BARRAS):
            if low[j] <= stop:
                res = 0
                break
            if high[j] >= alvo:
                res = 1
                break
        label[i] = res if not np.isnan(res) else 0

    df["target"] = label
    return df.dropna(subset=["target"])


def main():
    df = montar_dataset()
    df = criar_label(df)

    feats = FEATS_MARKOV + [c for c in df.columns if c.startswith("mtf_")]
    df = df.dropna(subset=[f for f in feats if f.startswith("mtf_")])
    print(f"Barras alinhadas com MTF+Markov: {len(df)}")
    print(f"Distribuicao target: {df['target'].value_counts().to_dict()}")
    print(f"Periodo: {df.index.min()} -> {df.index.max()}")

    corte = df.index[int(len(df) * 0.7)]
    treino, teste = df[df.index < corte], df[df.index >= corte]
    print(f"Treino: {len(treino)} barras (ate {corte}) | Teste: {len(teste)} barras")

    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score, accuracy_score
    from tensorflow.keras import layers, models, callbacks

    X_tr, y_tr = treino[feats].values, treino["target"].values
    X_te, y_te = teste[feats].values, teste["target"].values

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    pos = y_tr.mean()
    model = models.Sequential([
        layers.Input(shape=(X_tr_s.shape[1],)),
        layers.Dense(32, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy",
                  metrics=["accuracy"])
    es = callbacks.EarlyStopping(monitor="val_loss", patience=15,
                                 restore_best_weights=True)
    model.fit(X_tr_s, y_tr, validation_split=0.2, epochs=150, batch_size=32,
              callbacks=[es], class_weight={0: 0.5 / (1 - pos), 1: 0.5 / pos},
              verbose=0)

    p = model.predict(X_te_s, verbose=0).ravel()
    auc = roc_auc_score(y_te, p)
    acc = accuracy_score(y_te, (p > 0.5).astype(int))
    print(f"\nAUC teste: {auc:.3f} | Acuracia: {acc:.3f}")

    for limiar in [0.5, 0.55, 0.6]:
        sel = p > limiar
        total = sel.sum()
        wr = y_te[sel].mean() * 100 if total else 0
        print(f"Filtro p>{limiar}: {total} sinais liberados | WR real {wr:.1f}%")

    model.save(r"C:\AIOFEN\modelo_a_filtro_wdo.keras")
    import json
    with open(r"C:\AIOFEN\modelo_a_scaler.json", "w") as f:
        json.dump({"mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist()}, f)
    print("\nModelo salvo: modelo_a_filtro_wdo.keras")


if __name__ == "__main__":
    main()
