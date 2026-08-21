import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from tensorflow.keras import layers, models, callbacks

from treinar_modelo_a import montar_dataset, criar_label, FEATS_MARKOV


def treinar_janela(X_tr, y_tr):
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X_tr)
    pos = y_tr.mean()
    model = models.Sequential([
        layers.Input(shape=(X_s.shape[1],)),
        layers.Dense(32, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    es = callbacks.EarlyStopping(monitor="val_loss", patience=10,
                                 restore_best_weights=True)
    model.fit(X_s, y_tr, validation_split=0.2, epochs=100, batch_size=32,
              callbacks=[es], class_weight={0: 0.5 / (1 - pos), 1: 0.5 / pos},
              verbose=0)
    return model, scaler


def main():
    df = criar_label(montar_dataset())
    feats = FEATS_MARKOV + [c for c in df.columns if c.startswith("mtf_")]
    df = df.dropna(subset=[f for f in feats if f.startswith("mtf_")])
    h, m = df.index.hour, df.index.minute
    df = df[((h == 9) & (m >= 10)) | ((h >= 10) & (h < 12)) | ((h >= 14) & (h < 17))]
    df["mes"] = df.index.to_period("M")

    meses = sorted(df["mes"].unique())
    print(f"Total barras: {len(df)} | Meses: {meses[0]} .. {meses[-1]}")
    print()
    print(f"{'Mes teste':<12} {'barras':>6} {'treino':>7} {'AUC':>6} "
          f"{'WR base':>8} {'WR p>.6':>8} {'sinais':>7}")

    aucs = []
    for mes_teste in meses:
        if mes_teste < meses[3]:
            continue
        tr = df[df["mes"] < mes_teste]
        te = df[df["mes"] == mes_teste]
        if len(te) < 50 or len(tr) < 300 or te["target"].nunique() < 2:
            continue

        model, scaler = treinar_janela(tr[feats].values, tr["target"].values)
        X_te = scaler.transform(te[feats].values)
        p = model.predict(X_te, verbose=0).ravel()

        auc = roc_auc_score(te["target"], p)
        wr_base = te["target"].mean() * 100
        sel = p > 0.60
        n_sel = int(sel.sum())
        wr_sel = te["target"].values[sel].mean() * 100 if n_sel else float("nan")

        aucs.append(auc)
        print(f"{str(mes_teste):<12} {len(te):>6} {len(tr):>7} {auc:>6.3f} "
              f"{wr_base:>7.1f}% {wr_sel:>7.1f}% {n_sel:>7}")

    print("-" * 62)
    print(f"AUC medio: {np.mean(aucs):.3f} | Min: {np.min(aucs):.3f} | "
          f"Max: {np.max(aucs):.3f}")


if __name__ == "__main__":
    main()
