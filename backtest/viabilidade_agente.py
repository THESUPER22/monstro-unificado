# -*- coding: utf-8 -*-
"""Viabilidade de um "agente" de decisao no WDO (somente-leitura).

Pergunta: existe sinal exploravel nas features que ja temos, capaz de pagar
custo (R$1,20/contrato ida+volta = 0,12 pt) + slippage (1,0 pt/lado = 2,0 pt)?
Se nao existir, trocar Keras por agente/RL/LLM nao resolve.

Metodo:
  - Barras M5 construidas dos ticks reais (williams_r_historico.csv).
  - Features MTF (historico_multitf.csv) via merge_asof BACKWARD (sem lookahead).
  - Label = retorno futuro em pontos (H barras), sempre dentro do mesmo dia.
  - Split temporal 70/30 + walk-forward expanding com embargo de H barras.
  - XGBoost binario; avaliacao economica com custo+slippage e com custo-zero.
  - Baseline "sempre comprado" para separar drift de timing (AUC e' o juiz).

Uso: python backtest/viabilidade_agente.py
Nao altera nenhum arquivo de producao. Salva JSON em backtest/resultados/.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKS = os.path.join(BASE, "williams_r_historico.csv")
MTF = os.path.join(BASE, "historico_multitf.csv")
OUT = os.path.join(BASE, "backtest", "resultados", "viabilidade_agente.json")

PONTO_RS = 10.0          # 1 ponto WDO = R$10 por contrato
CUSTO_PT = 1.20 / PONTO_RS   # R$1,20 ida+volta = 0,12 pt
SLIP_PT = 2.0            # 1,0 pt/lado = 2,0 pt ida+volta

FEATS_MTF = ["rsi_5", "atr_5", "wr_5", "vol_5",
             "rsi_15", "atr_15", "wr_15", "vol_15",
             "rsi_30", "atr_30", "wr_30", "vol_30"]


def carregar_barras():
    t = pd.read_csv(TICKS)
    t["ts"] = pd.to_datetime(t["timestamp"], errors="coerce")
    t = t.dropna(subset=["ts", "preco"]).sort_values("ts")
    t = t.set_index("ts")
    # sessoes de pregao (seg-sex, 09:00-18:00)
    t = t[(t.index.weekday < 5) & (t.index.hour >= 9) & (t.index.hour < 18)]
    b = t["preco"].resample("5min").agg(["first", "max", "min", "last", "count"])
    b.columns = ["open", "high", "low", "close", "n"]
    b = b.dropna(subset=["close"])
    b = b[b["n"] >= 5]  # barra sem liquidez minima
    b["dia"] = b.index.date
    return b.reset_index().rename(columns={"index": "ts"})


def carregar_features():
    m = pd.read_csv(MTF)
    m["ts"] = pd.to_datetime(m["timestamp"].str.replace(".", "-", regex=False),
                             errors="coerce")
    m = m.dropna(subset=["ts"]).sort_values("ts")
    m = m[["ts"] + FEATS_MTF].drop_duplicates("ts")
    return m


def montar(h=3):
    b = carregar_barras()
    m = carregar_features()
    b["bar_end"] = b["ts"] + pd.Timedelta(minutes=5)
    df = pd.merge_asof(b.sort_values("bar_end"), m.sort_values("ts"),
                       left_on="bar_end", right_on="ts",
                       direction="backward", suffixes=("", "_mtf"))
    df = df.sort_values("ts").reset_index(drop=True)

    # features de preco (sem lookahead: tudo em t ou antes)
    df["ret_1"] = df["close"].pct_change(1)
    df["ret_3"] = df["close"].pct_change(3)
    df["ret_6"] = df["close"].pct_change(6)
    df["ret_12"] = df["close"].pct_change(12)
    df["rng"] = (df["high"] - df["low"]) / df["close"]
    df["body"] = (df["close"] - df["open"]) / df["close"]
    df["pos_rng"] = ((df["close"] - df["low"]) /
                     (df["high"] - df["low"]).replace(0, np.nan))
    df["atr_rel"] = df["atr_5"] / df["close"]
    df["hora"] = df["ts"].dt.hour + df["ts"].dt.minute / 60.0
    df["hora_sin"] = np.sin(2 * np.pi * df["hora"] / 24)
    df["hora_cos"] = np.cos(2 * np.pi * df["hora"] / 24)
    df["dow"] = df["ts"].dt.weekday

    # label: retorno futuro em PONTOS, so dentro do mesmo dia
    fwd = df["close"].shift(-h) - df["close"]
    mesmo_dia = df["dia"].shift(-h) == df["dia"]
    df["fwd_pts"] = fwd.where(mesmo_dia)
    df["y"] = (df["fwd_pts"] > 0).astype(int)
    df.loc[df["fwd_pts"].isna(), "y"] = np.nan
    # remove movimentos irrelevantes do rotulo (ruido de tick)
    df.loc[df["fwd_pts"].abs() < 0.5, "y"] = np.nan
    return df.dropna(subset=["y"] + FEATS_MTF + ["ret_12", "atr_rel"])


COLS = FEATS_MTF + ["ret_1", "ret_3", "ret_6", "ret_12", "rng", "body",
                    "pos_rng", "atr_rel", "hora_sin", "hora_cos", "dow"]


def metricas(p, fwd, cost_pt):
    """p = prob de alta; opera se |p-0,5|>=margem. PnL em pontos - custo."""
    res = {}
    for margem in (0.02, 0.05, 0.08, 0.12):
        sel = np.abs(p - 0.5) >= margem
        if sel.sum() == 0:
            continue
        lado = np.where(p[sel] > 0.5, 1.0, -1.0)
        pnl = lado * fwd[sel] - cost_pt
        wins = pnl > 0
        perda = -pnl[~wins].sum()
        res[str(margem)] = dict(
            n=int(sel.sum()), wr=round(float(wins.mean() * 100), 1),
            exp_pts=round(float(pnl.mean()), 3),
            pf=round(float(pnl[wins].sum() / perda), 3) if perda > 0 else None,
            net_rs=round(float(pnl.sum() * PONTO_RS), 2),
        )
    return res


def treinar_e_avaliar(df, h, custo, label):
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score, accuracy_score

    X = df[COLS].values.astype(np.float32)
    y = df["y"].values.astype(int)
    fwd = df["fwd_pts"].values.astype(float)
    n = len(df)
    corte = int(n * 0.70)
    emb = h  # purga/embargo entre treino e teste

    # split temporal simples (holdout final)
    Xtr, ytr = X[:corte - emb], y[:corte - emb]
    Xte, yte, fte = X[corte:], y[corte:], fwd[corte:]
    # validacao interna = ultimos 15% do treino (sem embaralhar)
    v = int(len(Xtr) * 0.85)
    m = xgb.XGBClassifier(
        n_estimators=400, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
        reg_lambda=1.0, eval_metric="logloss", n_jobs=2,
        early_stopping_rounds=40, random_state=7)
    m.fit(Xtr[:v], ytr[:v], eval_set=[(Xtr[v:], ytr[v:])], verbose=False)
    p = m.predict_proba(Xte)[:, 1]

    out = dict(label=label, h_barras=h, n_total=int(n), n_treino=int(len(Xtr)),
               n_teste=int(len(Xte)),
               auc_holdout=round(float(roc_auc_score(yte, p)), 4),
               acc_holdout=round(float(accuracy_score(yte, (p > 0.5))), 4),
               base_rate_alta=round(float(yte.mean()), 4),
               sempre_comprado_pts=round(float(fte.mean()), 3),
               sempre_comprado_net_rs=round(float((fte - custo).sum() * PONTO_RS), 2))
    out["holdout_custo_cheio"] = metricas(p, fte, custo)
    out["holdout_custo_zero"] = metricas(p, fte, 0.0)

    # walk-forward expanding (4 blocos de teste, treino sempre no passado)
    folds = []
    tam = n // 5
    for k in range(1, 5):
        tr_end = tam * k
        te_ini, te_fim = tr_end + emb, min(tr_end + tam, n)
        if te_ini >= te_fim or tr_end < 200:
            continue
        mm = xgb.XGBClassifier(
            n_estimators=400, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
            reg_lambda=1.0, eval_metric="logloss", n_jobs=2, random_state=7)
        mm.fit(X[:tr_end - emb], y[:tr_end - emb], verbose=False)
        pp = mm.predict_proba(X[te_ini:te_fim])[:, 1]
        yy = y[te_ini:te_fim]
        ff = fwd[te_ini:te_fim]
        folds.append(dict(
            fold=k, n=int(len(yy)),
            auc=round(float(roc_auc_score(yy, pp)), 4) if len(set(yy)) > 1 else None,
            acc=round(float(accuracy_score(yy, (pp > 0.5))), 4),
            custo_cheio=metricas(pp, ff, custo),
        ))
    out["walk_forward"] = folds
    return out


def main():
    print("=" * 70)
    print("VIABILIDADE DE AGENTE/ML NO WDO - somente-leitura")
    print("custo ida+volta = %.2f pt | slippage = %.1f pt | total = %.2f pt"
          % (CUSTO_PT, SLIP_PT, CUSTO_PT + SLIP_PT))
    print("=" * 70)
    resultados = []
    for h in (3, 6, 12):
        df = montar(h)
        for nome, custo in (("custo+slippage", CUSTO_PT + SLIP_PT),
                            ("custo-zero", 0.0)):
            r = treinar_e_avaliar(df, h, custo, nome)
            resultados.append(r)
            print("\n[H=%d barras (%d min) | %s] n=%d | AUC=%.4f | acc=%.4f"
                  % (h, h * 5, nome, r["n_total"], r["auc_holdout"],
                     r["acc_holdout"]))
            print("  sempre-comprado: %.3f pts/trade | net R$ %.2f"
                  % (r["sempre_comprado_pts"], r["sempre_comprado_net_rs"]))
            for k, v in r["holdout_custo_cheio"].items():
                print("  margem %-4s n=%-4d WR=%5.1f%% exp=%7.3f pt PF=%s net R$ %8.2f"
                      % (k, v["n"], v["wr"], v["exp_pts"], v["pf"], v["net_rs"]))
            print("  walk-forward AUC:", [f["auc"] for f in r["walk_forward"]])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("\nJSON salvo em:", OUT)


if __name__ == "__main__":
    main()
