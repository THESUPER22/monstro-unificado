"""Smoke test offline do item 34 / 23.50 (nao importa o robo, nao toca no MT5)."""
from __future__ import annotations

import ast
import io
import json
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

BASE = r"C:\AIOFEN"
MODELO = os.path.join(BASE, "modelo_monstro_wdo.h5")
SCALER = os.path.join(BASE, "modelo_monstro_wdo_scaler.json")
HIST = os.path.join(BASE, "historico_contexto_wdo.csv")
SRC = os.path.join(BASE, "monstro_unificado_v22.py")

FEATURES_ESPERADAS = [
    "bid_qty", "ask_qty", "spread", "volatility", "entropia_book",
    "rsi_14", "volume_tick", "is_in_trade", "floating_profit", "tempo_em_trade",
    "volume_maior_escora_bid", "distancia_maior_escora_bid",
    "volume_maior_escora_ask", "distancia_maior_escora_ask",
    "liquidez_top5_bid", "liquidez_top5_ask",
    "dolar_casado", "em_janela_ptax", "minutos_para_ptax", "dia_ptax",
]

falhas = []


def check(nome, cond, detalhe=""):
    print(("  OK  " if cond else "  FALHA ") + nome + (" | " + str(detalhe) if detalhe else ""))
    if not cond:
        falhas.append(nome)


print("== 1. scaler JSON ==")
info = json.load(io.open(SCALER, encoding="utf-8"))
check("feature_names == 20 e na ordem esperada",
      info["feature_names"] == FEATURES_ESPERADAS, info["feature_names"])
check("len(min)=len(max)=20", len(info["min"]) == 20 and len(info["max"]) == 20)

print("== 2. modelo ==")
modelo = tf.keras.models.load_model(MODELO)
dim = int(modelo.inputs[0].shape[-1])
check("input_shape == 20", dim == 20, dim)
check("ultima camada sigmoid(1)", int(modelo.outputs[0].shape[-1]) == 1)

print("== 3. scaler estendido (replica forcar_recreacao_scaler) ==")
mins = np.array(info["min"]).reshape(1, -1)
maxs = np.array(info["max"]).reshape(1, -1)
rng = maxs - mins
rng = np.where(rng == 0, 1.0, rng)
sc = MinMaxScaler()
sc.fit(np.vstack([mins - rng * 0.2, maxs + rng * 0.2]))
check("transform aceita (1,20)", sc.transform(np.zeros((1, 20))).shape == (1, 20))

print("== 4. predicao real do historico ==")
df = pd.read_csv(HIST, on_bad_lines="skip")
for c in FEATURES_ESPERADAS:
    if c not in df.columns:
        df[c] = 0.0
X = df[FEATURES_ESPERADAS].fillna(0.0).astype(float).values
Xs = np.clip(sc.transform(X), 0.0, 1.0)
p = modelo.predict(Xs, verbose=0).ravel()
check("X shape (n,20)", X.shape[1] == 20, X.shape)
check("predicoes finitas em [0,1]", bool(np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()))
check("n predicoes == n linhas", len(p) == len(df), (len(p), len(df)))

print("== 5. throttle de clipping (funcao extraida do fonte) ==")
src = io.open(SRC, encoding="utf-8", errors="surrogateescape").read()
tree = ast.parse(src)
fn = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "_registrar_clipping":
        fn = node
        break
check("_registrar_clipping existe no fonte", fn is not None)
if fn is not None:
    class FakeLog:
        def __init__(self):
            self.warnings = []
            self.debugs = []
        def warning(self, *a):
            self.warnings.append(a)
        def debug(self, *a):
            self.debugs.append(a)

    ns = {"logging": FakeLog(), "time": __import__("time"), "List": list,
          "_ultimo_aviso_clip": 0.0, "_INTERVALO_AVISO_CLIP_S": 600.0,
          "_clip_stats": {}}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<fn>", "exec"), ns)
    reg = ns["_registrar_clipping"]
    antes = np.array([[1.5, 0.5], [1.2, 0.9]])
    reg(3, antes, ["volatility", "bid_qty"])
    reg(3, antes, ["volatility", "bid_qty"])
    check("2 chamadas seguidas -> 1 warning + 1 debug",
          len(ns["logging"].warnings) == 1 and len(ns["logging"].debugs) == 1,
          (len(ns["logging"].warnings), len(ns["logging"].debugs)))
    check("stats por feature no warning",
          "volatility=2" in ns["logging"].warnings[0][0] % ns["logging"].warnings[0][1:],
          ns["logging"].warnings[0])

print()
if falhas:
    print("RESULTADO: FALHOU ->", falhas)
    raise SystemExit(1)
print("RESULTADO: TODOS OS CHECKS PASSARAM")
