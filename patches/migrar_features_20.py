"""Migracao offline 22 -> 20 features (item 34 / 23.50).

Remove do vetor do modelo os precos ABSOLUTOS das escoras:
  - preco_maior_escora_bid
  - preco_maior_escora_ask
mantendo as distancias relativas (distancia_maior_escora_bid/ask).

O modelo vivo tem 22 entradas. Em vez de retreinar (bloqueado pelo gate de
dados da proposta 23.29), faz-se CIRURGIA EXATA de pesos:

  * BatchNorm de entrada: corta as 2 posicoes.
  * 1a Dense: corta as 2 linhas do kernel e joga a contribuicao constante
    (as 2 features hoje saturam em 1.0, sempre) para o bias.
  * Demais camadas: copiadas 1:1.

Resultado: para os dados atuais, a saida do modelo e IDENTICA (erro < 1e-5),
porque as 2 features removidas sao constantes em 1.0. Nenhuma logica de trade
muda.

READ-ONLY sobre o robo: nao importa monstro_unificado_v22, nao toca no MT5.
Grava apenas artefatos *_20f.* e o JSON de metricas. A instalacao e feita
depois, com --install, e so se a verificacao passar.

Uso:
  venv310\\Scripts\\python.exe patches\\migrar_features_20.py
  venv310\\Scripts\\python.exe patches\\migrar_features_20.py --install
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELO = os.path.join(BASE, "modelo_monstro_wdo.h5")
SCALER = os.path.join(BASE, "modelo_monstro_wdo_scaler.json")
HIST = os.path.join(BASE, "historico_contexto_wdo.csv")
METRICAS = os.path.join(BASE, "patches", "migracao_20f_metricas.json")

REMOVER = ["preco_maior_escora_bid", "preco_maior_escora_ask"]


def clonar_arquitetura(antigo: tf.keras.Model, n_features: int) -> tf.keras.Model:
    """Recria a arquitetura REAL do modelo vivo com n_features entradas.

    O modelo em producao nao segue criar_modelo_neural(): ele tem uma
    GaussianNoise na entrada. Por isso clonamos camada a camada a partir do
    config do modelo carregado, trocando apenas a dimensao da entrada.
    """
    inp = tf.keras.Input(shape=(n_features,))
    x = inp
    for i, layer in enumerate(antigo.layers):
        cfg = dict(layer.get_config())
        cfg.pop("name", None)
        cfg.pop("batch_input_shape", None)
        if i <= 2:
            # primeiras camadas: recriadas explicitamente (entrada nova)
            if isinstance(layer, tf.keras.layers.BatchNormalization):
                nl = tf.keras.layers.BatchNormalization(**cfg)
            elif isinstance(layer, tf.keras.layers.Dense):
                nl = tf.keras.layers.Dense(**cfg)
            else:
                nl = layer.__class__.from_config(cfg)
        else:
            nl = layer.__class__.from_config(cfg)
        x = nl(x)
    novo = tf.keras.Model(inp, x)
    novo.compile(optimizer=tf.keras.optimizers.Adam(0.001),
                 loss="binary_crossentropy", metrics=["accuracy"])
    return novo


def scaler_estendido(mins: np.ndarray, maxs: np.ndarray) -> MinMaxScaler:
    """Replica forcar_recreacao_scaler(): range estendido em 20%."""
    rng = maxs - mins
    rng = np.where(rng == 0, 1.0, rng)
    sc = MinMaxScaler()
    sc.fit(np.vstack([mins - rng * 0.2, maxs + rng * 0.2]))
    return sc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true",
                    help="copia os artefatos *_20f.* sobre os originais")
    args = ap.parse_args()

    info = json.load(open(SCALER, encoding="utf-8"))
    features22 = list(info["feature_names"])
    mins22 = np.asarray(info["min"], dtype=float)
    maxs22 = np.asarray(info["max"], dtype=float)
    if len(features22) != len(mins22) or len(features22) != len(maxs22):
        raise SystemExit("scaler inconsistente: nomes/min/max com tamanhos diferentes")
    if not all(f in features22 for f in REMOVER):
        raise SystemExit("features a remover nao estao no scaler")

    keep_idx = [i for i, f in enumerate(features22) if f not in REMOVER]
    features20 = [features22[i] for i in keep_idx]
    print("features: %d -> %d" % (len(features22), len(features20)))
    print("removidas:", REMOVER)

    antigo = tf.keras.models.load_model(MODELO)
    print("\ncamadas do modelo antigo:")
    for i, l in enumerate(antigo.layers):
        print("  %2d %-22s %s" % (i, l.name, type(l).__name__))
    if not isinstance(antigo.layers[0], tf.keras.layers.GaussianNoise):
        print("aviso: 1a camada nao e GaussianNoise:", type(antigo.layers[0]).__name__)
    if not isinstance(antigo.layers[1], tf.keras.layers.BatchNormalization):
        raise SystemExit("camada 1 nao e BatchNormalization - abortando")
    if not isinstance(antigo.layers[2], tf.keras.layers.Dense):
        raise SystemExit("camada 2 nao e Dense - abortando")
    in_dim = int(antigo.input_shape[-1])
    if in_dim != len(features22):
        raise SystemExit("modelo tem %d entradas, scaler tem %d" % (in_dim, len(features22)))

    bn = antigo.layers[1]
    d1 = antigo.layers[2]
    gamma, beta, mean, var = bn.get_weights()
    eps = float(bn.epsilon)
    k1, b1 = d1.get_weights()

    # Contribuicao constante das 2 features removidas (entrada = 1.0, hoje 100%)
    saida_bn = {}
    for f in REMOVER:
        i = features22.index(f)
        saida_bn[f] = float(gamma[i] * (1.0 - mean[i]) / np.sqrt(var[i] + eps) + beta[i])
    print("\ncontribuicao constante (BN out @ 1.0):",
          {k: round(v, 6) for k, v in saida_bn.items()})

    novo = clonar_arquitetura(antigo, len(features20))
    # Keras 3 inclui o InputLayer em model.layers; alinhamos com antigo.layers
    novo_layers = [l for l in novo.layers
                   if not isinstance(l, tf.keras.layers.InputLayer)]
    bn_new, d1_new = novo_layers[1], novo_layers[2]
    bn_new.set_weights([w[keep_idx] for w in (gamma, beta, mean, var)])

    k_new = k1[keep_idx, :]
    b_new = b1.copy()
    for f in REMOVER:
        i = features22.index(f)
        b_new = b_new + k1[i, :] * saida_bn[f]
    d1_new.set_weights([k_new, b_new])

    copiadas = 0
    for i in range(3, len(novo_layers)):
        w_old = antigo.layers[i].get_weights()
        if not w_old:
            continue
        novo_layers[i].set_weights(w_old)
        copiadas += 1
    print("camadas com pesos copiados 1:1:", copiadas)

    # ---------- verificacao nos dados reais recentes ----------
    df = pd.read_csv(HIST, on_bad_lines="skip")
    for f in features22:
        if f not in df.columns:
            df[f] = 0.0
    df = df.fillna(0.0)
    X22 = df[features22].astype(float).values
    X20 = df[features20].astype(float).values

    sc22 = scaler_estendido(mins22, maxs22)
    X22s = np.clip(sc22.transform(X22), 0.0, 1.0)
    sc20 = scaler_estendido(mins22[keep_idx], maxs22[keep_idx])
    X20s = np.clip(sc20.transform(X20), 0.0, 1.0)

    p_old = antigo.predict(X22s, verbose=0).ravel()
    p_new = novo.predict(X20s, verbose=0).ravel()
    delta = np.abs(p_old - p_new)

    clip_old = int((sc22.transform(X22) < 0).sum() + (sc22.transform(X22) > 1).sum())
    clip_new = int((sc20.transform(X20) < 0).sum() + (sc20.transform(X20) > 1).sum())

    print("\n=== verificacao (%d linhas reais) ===" % len(df))
    print("max |delta pred|: %.3e" % float(delta.max()))
    print("media |delta|   : %.3e" % float(delta.mean()))
    print("valores clipped: antigo=%d novo=%d" % (clip_old, clip_new))

    ok = bool(delta.max() < 1e-5)
    metricas = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "n_features_antes": len(features22),
        "n_features_depois": len(features20),
        "removidas": REMOVER,
        "linhas_verificacao": int(len(df)),
        "delta_max": float(delta.max()),
        "delta_medio": float(delta.mean()),
        "clipped_antes": clip_old,
        "clipped_depois": clip_new,
        "equivalencia_ok": ok,
    }
    json.dump(metricas, open(METRICAS, "w", encoding="utf-8"), indent=2)

    if not ok:
        print("\nFALHOU: modelo novo nao reproduz o antigo. Nada foi instalado.")
        return 1

    out_h5 = os.path.join(BASE, "modelo_monstro_wdo_20f.h5")
    out_keras = os.path.join(BASE, "modelo_monstro_wdo_20f.keras")
    out_scaler = os.path.join(BASE, "modelo_monstro_wdo_scaler_20f.json")
    novo.save(out_h5)
    novo.save(out_keras)
    json.dump({"min": mins22[keep_idx].tolist(),
               "max": maxs22[keep_idx].tolist(),
               "feature_names": features20},
              open(out_scaler, "w", encoding="utf-8"), indent=2)
    print("\nartefatos gerados:")
    for p in (out_h5, out_keras, out_scaler, METRICAS):
        print("  ", p, os.path.getsize(p), "bytes")

    if args.install:
        for src, dst in ((out_h5, os.path.join(BASE, "modelo_monstro_wdo.h5")),
                         (out_keras, os.path.join(BASE, "modelo_monstro_wdo.keras")),
                         (out_scaler, os.path.join(BASE, "modelo_monstro_wdo_scaler.json"))):
            shutil.copy2(src, dst)
            print("instalado:", dst)
    else:
        print("\n(dry-run: use --install para substituir os originais)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
