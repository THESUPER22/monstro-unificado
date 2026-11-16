# -*- coding: utf-8 -*-
"""Diagnostico do estudo de viabilidade do agente (somente-leitura).

O screening inicial mostrou H=12 positivo com custo cheio, mas:
  - rotulos de H barras se sobrepoem (amostra efetiva ~ n/H);
  - walk-forward AUC ~0,50;
  - mercado em tendencia de alta no periodo (drift pode explicar tudo).
Aqui: amostra NAO sobreposta, PnL por lado, buy-and-hold e permutacao.

Uso: python backtest/viabilidade_agente_diag.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import viabilidade_agente as v  # reutiliza montar()/COLS/metricas()

OUT = os.path.join(v.BASE, "backtest", "resultados",
                   "viabilidade_agente_diag.json")


def nao_sobreposto(df, h):
    """Mantem 1 a cada h barras para reduzir autocorrelacao dos rotulos."""
    return df.iloc[::h].reset_index(drop=True)


def avaliar(df, h, custo, n_perm=20, seed=7):
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score

    df = nao_sobreposto(df, h)
    X = df[v.COLS].values.astype(np.float32)
    y = df["y"].values.astype(int)
    fwd = df["fwd_pts"].values.astype(float)
    n = len(df)
    corte = int(n * 0.70)
    emb = 1  # ja nao sobreposto

    Xtr, ytr = X[:corte - emb], y[:corte - emb]
    Xte, yte, fte = X[corte:], y[corte:], fwd[corte:]
    vv = int(len(Xtr) * 0.85)

    def fit(Xa, ya, Xb, yb):
        m = xgb.XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
            reg_lambda=1.0, eval_metric="logloss", n_jobs=2,
            early_stopping_rounds=30, random_state=seed)
        m.fit(Xa, ya, eval_set=[(Xb, yb)], verbose=False)
        return m

    m = fit(Xtr[:vv], ytr[:vv], Xtr[vv:], ytr[vv:])
    p = m.predict_proba(Xte)[:, 1]
    p_tr = m.predict_proba(Xtr)[:, 1]
    auc = float(roc_auc_score(yte, p))
    auc_tr = float(roc_auc_score(ytr, p_tr))
    sel = np.abs(p - 0.5) >= 0.02
    lado = np.where(p[sel] > 0.5, 1.0, -1.0)
    pnl = lado * fte[sel] - custo
    exp_real = float(pnl.mean()) if len(pnl) else 0.0

    # PnL por lado e buy-and-hold do periodo de teste
    long_sel = sel & (p > 0.5)
    short_sel = sel & (p <= 0.5)
    bh = float(fte.mean())  # comprado em toda barra de teste (sem custo)

    # permutacao: embaralha y no TREINO, mantem teste -> distribuicao nula
    rng = np.random.default_rng(seed)
    exps = []
    for _ in range(n_perm):
        yp = ytr.copy()
        rng.shuffle(yp)
        try:
            mp = fit(Xtr[:vv], yp[:vv], Xtr[vv:], yp[vv:])
            pp = mp.predict_proba(Xte)[:, 1]
            sp = np.abs(pp - 0.5) >= 0.05
            lp = np.where(pp[sp] > 0.5, 1.0, -1.0)
            exps.append(float((lp * fte[sp] - custo).mean()) if sp.sum() else 0.0)
        except Exception:
            pass
    exps = np.array(exps)

    return dict(
        h=h, n_nao_sobreposto=int(n), n_treino=int(len(Xtr)),
        n_teste=int(len(Xte)),
        teste_de=df["ts"].iloc[corte].strftime("%Y-%m-%d"),
        teste_ate=df["ts"].iloc[-1].strftime("%Y-%m-%d"),
        auc=round(auc, 4),
        auc_treino=round(auc_tr, 4),
        p_min=round(float(p.min()), 3), p_max=round(float(p.max()), 3),
        p_std=round(float(p.std()), 3),
        n_trades=int(sel.sum()),
        pct_longo=round(float(long_sel.sum() / max(sel.sum(), 1)) * 100, 1),
        exp_pts=round(exp_real, 3),
        exp_longo_pts=round(float((1.0 * fte[long_sel] - custo).mean()), 3)
        if long_sel.sum() else None,
        exp_curto_pts=round(float((-1.0 * fte[short_sel] - custo).mean()), 3)
        if short_sel.sum() else None,
        buy_hold_pts=round(bh, 3),
        permuta_n=n_perm,
        permuta_exp_media=round(float(exps.mean()), 3),
        permuta_exp_p95=round(float(np.percentile(exps, 95)), 3),
        p_valor_aprox=round(float((exps >= exp_real).mean()), 3),
    )


def main():
    print("=" * 72)
    print("DIAGNOSTICO - amostra nao sobreposta + permutacao (somente-leitura)")
    print("=" * 72)
    saida = []
    for h in (6, 12):
        df = v.montar(h)
        for nome, custo in (("custo+slippage", v.CUSTO_PT + v.SLIP_PT),
                            ("custo-zero", 0.0)):
            r = avaliar(df, h, custo)
            r["cenario"] = nome
            saida.append(r)
            print("\n[H=%d | %s] n_efetivo=%d | teste %s..%s"
                  % (h, nome, r["n_nao_sobreposto"], r["teste_de"],
                     r["teste_ate"]))
            print("  AUC=%.4f (treino %.4f) | p=[%.3f, %.3f] std=%.3f"
                  % (r["auc"], r["auc_treino"], r["p_min"], r["p_max"],
                     r["p_std"]))
            print("  trades=%d (%.0f%% longo) | exp=%+.3f pt"
                  % (r["n_trades"], r["pct_longo"], r["exp_pts"]))
            print("  exp longo=%s | exp curto=%s | buy&hold=%.3f pt"
                  % (r["exp_longo_pts"], r["exp_curto_pts"], r["buy_hold_pts"]))
            print("  permutacao: media=%+.3f p95=%+.3f | p-valor~%.2f"
                  % (r["permuta_exp_media"], r["permuta_exp_p95"],
                     r["p_valor_aprox"]))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    print("\nJSON salvo em:", OUT)


if __name__ == "__main__":
    main()
