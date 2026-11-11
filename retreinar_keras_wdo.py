"""Retreino + validacao offline do modelo Keras do Monstro (WDO).

READ-ONLY em relacao ao robo:
  - NAO envia ordens, NAO importa monstro_unificado_v22 (evita subir MT5/threads).
  - NAO sobrescreve modelo_monstro_wdo.h5 nem o scaler vivo.
  - Grava apenas arquivos *_candidato* e um JSON de metricas.

O que faz:
  1. Monta o dataset rotulado (BUY=1 / SELL=0). NAO_AGIU/NADA sao descartados
     (antes viravam SELL falso).
  2. Filtra linhas com features de book incompletas (zeros), que envenenariam
     o treino (o corpus real antigo tem 10/18 features zeradas).
  3. Split TEMPORAL: treino/val no corpus offline; holdout externo nas
     operacoes reais recentes com features completas.
  4. Scaler ajustado SOMENTE no treino.
  5. Treina um modelo candidato com a MESMA arquitetura do modelo vivo
     (clone_model) e avalia contra o baseline majoritario.
  6. Salva candidatos separados + metricas. Nunca promove sozinho.

Uso:
  venv310\\Scripts\\python.exe retreinar_keras_wdo.py
  venv310\\Scripts\\python.exe retreinar_keras_wdo.py --epochs 60 --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.preprocessing import MinMaxScaler

BASE = os.path.dirname(os.path.abspath(__file__))

MODELO_VIVO = os.path.join(BASE, "modelo_monstro_wdo.h5")
SCALER_VIVO = os.path.join(BASE, "modelo_monstro_wdo_scaler.json")

CORPUS_OFFLINE = os.path.join(BASE, "modelo_monstro_wdo_dados_treino.csv")
CORPUS_REAL = os.path.join(BASE, "logs", "treino_corpus_real.csv")
HISTORICO_VIVO = os.path.join(BASE, "historico_contexto_wdo.csv")

# Ordem EXATA das 22 features de preparar_dados() em monstro_unificado_v22.py
FEATURES = [
    "bid_qty", "ask_qty", "spread", "volatility", "entropia_book",
    "rsi_14", "volume_tick", "is_in_trade", "floating_profit", "tempo_em_trade",
    "preco_maior_escora_bid", "volume_maior_escora_bid", "distancia_maior_escora_bid",
    "preco_maior_escora_ask", "volume_maior_escora_ask", "distancia_maior_escora_ask",
    "liquidez_top5_bid", "liquidez_top5_ask",
    "dolar_casado", "em_janela_ptax", "minutos_para_ptax", "dia_ptax",
]

# Features de book que precisam estar preenchidas para a amostra ser util.
# (as 4 de ptax sao sempre 0 no CSV; nao entram no gate)
BOOK_FEATURES = [
    "preco_maior_escora_bid", "volume_maior_escora_bid", "distancia_maior_escora_bid",
    "preco_maior_escora_ask", "volume_maior_escora_ask", "distancia_maior_escora_ask",
    "liquidez_top5_bid", "liquidez_top5_ask",
]

MIN_BOOK_FEATURES = 6      # exige 6 de 8 features de book nao nulas
MIN_HOLDOUT = 30           # abaixo disso a validacao e considerada insuficiente
EPOCHS_MAX = 60
PATIENCE = 8


def _carregar(caminho: str, origem: str, tem_timestamp: bool) -> pd.DataFrame | None:
    if not os.path.exists(caminho):
        print(f"  [skip] {origem}: arquivo nao existe ({caminho})")
        return None
    df = pd.read_csv(caminho, on_bad_lines="skip")
    if "action" not in df.columns:
        print(f"  [skip] {origem}: sem coluna action")
        return None
    antes = len(df)
    df = df[df["action"].isin(["BUY", "SELL"])].copy()
    if df.empty:
        print(f"  [skip] {origem}: nenhuma linha BUY/SELL ({antes} linhas)")
        return None
    for c in FEATURES:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    # Gate de completude das features de book
    preenchidas = (df[BOOK_FEATURES] != 0).sum(axis=1)
    completas = int((preenchidas >= MIN_BOOK_FEATURES).sum())
    df = df[preenchidas >= MIN_BOOK_FEATURES].copy()

    if tem_timestamp and "timestamp" in df.columns:
        df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("_ts", kind="stable")
    else:
        df["_ts"] = pd.NaT

    df["_origem"] = origem
    df["_label"] = (df["action"] == "BUY").astype(int)
    print(f"  {origem:22s}: {antes:5d} linhas -> {completas:5d} com book completo"
          f" ({len(df)} usadas)")
    return df


def _resumo(y: np.ndarray, p: np.ndarray, nome: str) -> dict:
    y = np.asarray(y).astype(int)
    p = np.asarray(p).ravel()
    pred = (p >= 0.5).astype(int)
    base = float(max(y.mean(), 1 - y.mean()))
    out = {
        "conjunto": nome,
        "n": int(len(y)),
        "buy": int(y.sum()),
        "sell": int((1 - y).sum()),
        "baseline_majoritario": round(base, 4),
        "acuracia": round(float(accuracy_score(y, pred)), 4),
        "auc": None,
        "p_min": round(float(p.min()), 4),
        "p_max": round(float(p.max()), 4),
        "p_media": round(float(p.mean()), 4),
        "p_desvio": round(float(p.std()), 4),
        "p_gt_0.5": int((p > 0.5).sum()),
        "matriz_confusao": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }
    if len(np.unique(y)) > 1:
        out["auc"] = round(float(roc_auc_score(y, p)), 4)
    return out


def _aplicar_scaler(scaler: MinMaxScaler, X: pd.DataFrame) -> np.ndarray:
    return np.clip(scaler.transform(X[FEATURES]), 0.0, 1.0)


def _taxa_clip(scaler: MinMaxScaler, X: pd.DataFrame) -> float:
    antes = scaler.transform(X[FEATURES])
    depois = np.clip(antes, 0.0, 1.0)
    return float((antes != depois).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=EPOCHS_MAX)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--prefixo", default="modelo_monstro_wdo_candidato")
    args = ap.parse_args()

    tf.keras.utils.set_random_seed(args.seed)

    print("=" * 78)
    print("RETREINO KERAS WDO - validacao offline (read-only no robo)")
    print("=" * 78)

    print("\n[1] Fontes de dados rotuladas")
    offline = _carregar(CORPUS_OFFLINE, "corpus_offline", tem_timestamp=False)
    real = _carregar(CORPUS_REAL, "corpus_real", tem_timestamp=True)
    vivo = _carregar(HISTORICO_VIVO, "historico_vivo", tem_timestamp=True)

    if offline is None or offline.empty:
        print("\nERRO: corpus offline ausente/vazio. Sem base minima para treinar.")
        return 1

    # Ordem temporal: offline (jul) -> real (ago-nov) -> vivo (nov)
    partes = [d for d in (offline, real, vivo) if d is not None and not d.empty]
    for i, d in enumerate(partes):
        if d["_ts"].isna().all():
            d["_ts"] = pd.Timestamp("2026-07-01") + pd.Timedelta(minutes=i)

    # Split temporal do corpus offline: 80/20
    n = len(offline)
    corte = int(n * 0.8)
    treino = offline.iloc[:corte].copy()
    val = offline.iloc[corte:].copy()

    # Holdout externo = operacoes reais com book completo (regime atual)
    externo = pd.concat([d for d in (real, vivo) if d is not None and not d.empty],
                        ignore_index=True) if (real is not None or vivo is not None) else None

    print(f"\n[2] Split temporal")
    print(f"  treino : {len(treino):5d} (offline, primeiras 80%)")
    print(f"  val    : {len(val):5d} (offline, ultimas 20%)")
    if externo is not None and not externo.empty:
        print(f"  externo: {len(externo):5d} (trades reais com book completo)")
    else:
        print("  externo: 0 (nenhum trade real com book completo)")

    # Scaler ajustado SOMENTE no treino
    scaler = MinMaxScaler()
    scaler.fit(treino[FEATURES])
    X_tr = _aplicar_scaler(scaler, treino)
    y_tr = treino["_label"].values
    X_va = _aplicar_scaler(scaler, val)
    y_va = val["_label"].values

    # Class weight para desbalanceamento
    from sklearn.utils.class_weight import compute_class_weight
    classes = np.unique(y_tr)
    pesos = compute_class_weight("balanced", classes=classes, y=y_tr)
    cw = {int(c): float(w) for c, w in zip(classes, pesos)}

    # Arquitetura identica ao modelo vivo
    print(f"\n[3] Modelo")
    vivo_model = tf.keras.models.load_model(MODELO_VIVO, compile=False)
    print(f"  vivo: input={vivo_model.input_shape} output={vivo_model.output_shape} "
          f"camadas={len(vivo_model.layers)}")
    cand = tf.keras.models.clone_model(vivo_model)
    cand.compile(optimizer=tf.keras.optimizers.Adam(0.001),
                 loss="binary_crossentropy", metrics=["accuracy"])
    print(f"  candidato: arquitetura clonada, pesos reinicializados")

    es = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=PATIENCE, restore_best_weights=True)
    hist = cand.fit(
        X_tr, y_tr,
        validation_data=(X_va, y_va),
        epochs=args.epochs,
        batch_size=32,
        verbose=2,
        callbacks=[es],
        class_weight=cw,
        shuffle=True,
    )
    epocas = len(hist.history["loss"])

    print(f"\n[4] Metricas")
    p_va = cand.predict(X_va, verbose=0).ravel()
    res_va = _resumo(y_va, p_va, "validacao_offline")

    res_ext = None
    res_vivo_ext = None
    clip_ext = None
    if externo is not None and not externo.empty:
        X_ext = _aplicar_scaler(scaler, externo)
        clip_ext = round(_taxa_clip(scaler, externo), 4)
        res_ext = _resumo(externo["_label"].values,
                          cand.predict(X_ext, verbose=0).ravel(),
                          "externo_recente")
        res_ext["taxa_clip_scaler"] = clip_ext

        # Modelo vivo com o scaler DELE (como roda hoje em producao)
        with open(SCALER_VIVO, encoding="utf-8") as f:
            sc = json.load(f)
        mins = np.array(sc["min"], dtype=float)
        maxs = np.array(sc["max"], dtype=float)
        rng = np.where((maxs - mins) == 0, 1.0, maxs - mins)
        scaler_vivo = MinMaxScaler().fit(
            np.vstack([mins - rng * 0.2, maxs + rng * 0.2]))
        X_ext_vivo = np.clip(scaler_vivo.transform(externo[FEATURES]), 0.0, 1.0)
        res_vivo_ext = _resumo(externo["_label"].values,
                               vivo_model.predict(X_ext_vivo, verbose=0).ravel(),
                               "externo_modelo_vivo")
        res_vivo_ext["taxa_clip_scaler"] = round(
            float((scaler_vivo.transform(externo[FEATURES]) != X_ext_vivo).mean()), 4)

    for r in [res_va, res_ext, res_vivo_ext]:
        if r is None:
            continue
        print(f"\n  --- {r['conjunto']} ---")
        for k, v in r.items():
            if k != "conjunto":
                print(f"    {k:22s}: {v}")

    # Veredito
    print(f"\n[5] Veredito")
    motivos = []
    if res_va["auc"] is None:
        motivos.append("validacao sem as duas classes")
    else:
        if res_va["auc"] <= 0.55:
            motivos.append(f"AUC validacao {res_va['auc']} <= 0.55 (sem poder discriminativo)")
        if res_va["acuracia"] <= res_va["baseline_majoritario"] + 0.03:
            motivos.append(
                f"acuracia {res_va['acuracia']} nao supera baseline "
                f"{res_va['baseline_majoritario']} + 0.03")
    if externo is None or len(externo) < MIN_HOLDOUT:
        motivos.append(
            f"holdout recente insuficiente ({0 if externo is None else len(externo)} < {MIN_HOLDOUT})")

    aprovado = len(motivos) == 0
    if aprovado:
        print("  APTO a promocao (validar ainda no paper antes de ativar).")
    else:
        print("  NAO PROMOVER. Motivos:")
        for m in motivos:
            print(f"    - {m}")

    # Salvar candidatos (nunca sobrescreve o vivo)
    pref = os.path.join(BASE, args.prefixo)
    cand.save(pref + ".h5")
    cand.save(pref + ".keras")
    with open(pref + "_scaler.json", "w", encoding="utf-8") as f:
        json.dump({
            "min": scaler.data_min_.tolist(),
            "max": scaler.data_max_.tolist(),
            "feature_names": FEATURES,
            "origem": "retreinar_keras_wdo.py",
            "treinado_em": datetime.now().isoformat(timespec="seconds"),
        }, f, indent=2)

    metricas = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "epochs_pedidos": args.epochs,
        "epochs_rodados": epocas,
        "n_treino": int(len(treino)),
        "n_val": int(len(val)),
        "n_externo": 0 if externo is None else int(len(externo)),
        "features": FEATURES,
        "min_book_features": MIN_BOOK_FEATURES,
        "validacao": res_va,
        "externo_candidato": res_ext,
        "externo_modelo_vivo": res_vivo_ext,
        "aprovado": aprovado,
        "motivos": motivos,
        "arquivos": {
            "modelo_h5": pref + ".h5",
            "modelo_keras": pref + ".keras",
            "scaler": pref + "_scaler.json",
        },
    }
    saida = os.path.join(BASE, "logs",
                         f"retreino_keras_{datetime.now():%Y%m%d_%H%M%S}.json")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)
    print(f"\n[6] Arquivos")
    print(f"  modelo : {pref}.h5")
    print(f"  scaler : {pref}_scaler.json")
    print(f"  metricas: {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
