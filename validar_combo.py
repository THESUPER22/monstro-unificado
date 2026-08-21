import json
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

from backtest_markov_4estados import rodar
from treinar_modelo_a import montar_dataset, FEATS_MARKOV

PT_VALUE = 10.0
CUSTO = 1.20
CUTOFF_TREINO = "2026-05-07"


def metricas(sub, titulo):
    if sub.empty:
        print(f"{titulo:<28}: nenhum trade")
        return
    n = len(sub)
    wins = (sub["brl"] > 0).sum()
    wr = wins / n * 100
    saldo = sub["brl"].sum()
    gp = sub.loc[sub["brl"] > 0, "brl"].sum()
    gl = abs(sub.loc[sub["brl"] <= 0, "brl"].sum())
    pf = gp / gl if gl > 0 else float("inf")
    print(f"{titulo:<28}: {n:>4} trades | WR {wr:5.1f}% | "
          f"R$ {saldo:>9,.2f} | PF {pf:.2f}")


def main():
    print("Montando dataset e rodando estrategia Markov Tendencia...")
    df = montar_dataset()
    trades = rodar(df, PT_VALUE, usar_consol=False,
                   breakout_ratio=1.0, stop_emergencia=True)

    feats = FEATS_MARKOV + [c for c in df.columns if c.startswith("mtf_")]
    X_all = df[feats]

    model = load_model(r"C:\AIOFEN\modelo_a_filtro_wdo.keras")
    with open(r"C:\AIOFEN\modelo_a_scaler.json") as f:
        sp = json.load(f)
    mean = np.array(sp["mean"])
    scale = np.array(sp["scale"])

    entradas = pd.DatetimeIndex(trades["entrada"])
    X_trades = X_all.reindex(entradas)
    ok = ~X_trades.isna().any(axis=1)
    trades = trades[ok.values].copy()
    X_scaled = (X_trades[ok].values - mean) / scale
    prob = model.predict(X_scaled, verbose=0).ravel()
    trades["prob"] = prob

    oos = trades[trades["entrada"] >= CUTOFF_TREINO].copy()
    ins = trades[trades["entrada"] < CUTOFF_TREINO].copy()

    print(f"\nTotal de trades da estrategia: {len(trades)} "
          f"(in-sample: {len(ins)} | out-of-sample: {len(oos)})")

    print("\n=== OUT-OF-SAMPLE (07/05 a 20/08) - a unica contagem valida ===")
    metricas(oos, "Sem filtro (todos)")
    for limiar in [0.5, 0.55, 0.6, 0.65, 0.7]:
        metricas(oos[oos["prob"] >= limiar], f"Veto ML p>={limiar}")

    print("\n=== IN-SAMPLE (referencia apenas, nao valida) ===")
    metricas(ins, "Sem filtro (todos)")
    for limiar in [0.6, 0.65]:
        metricas(ins[ins["prob"] >= limiar], f"Veto ML p>={limiar}")

    if not oos.empty:
        print("\nDistribuicao de probabilidade nos trades OOS:")
        print(oos["prob"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
