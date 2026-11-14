# -*- coding: utf-8 -*-
"""
arquivar_contexto.py — READ-ONLY: preserva o historico de profundidade de book.

Consolida o historico_contexto_wdo.csv em arquivos diarios
(logs/contexto_arquivo/YYYY-MM-DD.csv), deduplicando por linha. Roda a cada
15 min no pregao; como e INCREMENTAL, um reset do arquivo de origem no meio do
dia nao perde o que ja foi arquivado.

Nao envia ordem, nao altera config, nao toca no robo, nao reinicia nada.
So le o CSV de contexto e escreve em logs/contexto_arquivo/ (ignorado pelo git).

Uso:
    python arquivar_contexto.py            # incremental (uso agendado)
    python arquivar_contexto.py --seed     # importa tambem os arquivos limpos ja existentes
    python arquivar_contexto.py --force    # ignora a janela de horario (teste manual)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os

import pandas as pd

BASE = r"C:\AIOFEN"
SRC = os.path.join(BASE, "historico_contexto_wdo.csv")
OUT = os.path.join(BASE, "logs", "contexto_arquivo")
LOG = os.path.join(OUT, "arquivador.log")

# Arquivos de contexto com profundidade limpa que ja existem no disco.
SEED = [
    os.path.join(BASE, "logs", "historico_contexto_wdo_20261111_pre_fix.csv"),
    os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.pre_reinj_1609"),
    os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.vazio_2809"),
]

# Janela em que o pregao gera contexto (seg-sex). Fora dela o script nao faz nada,
# a menos que --force seja passado (teste manual).
JANELA_INI = dt.time(9, 0)
JANELA_FIM = dt.time(18, 10)


def _log(msg: str) -> None:
    try:
        os.makedirs(OUT, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} | {msg}\n")
    except Exception:  # noqa: BLE001
        pass


def _ler(p: str) -> pd.DataFrame | None:
    if not os.path.exists(p):
        return None
    try:
        d = pd.read_csv(p, encoding="utf-8-sig", on_bad_lines="skip")
    except Exception:  # noqa: BLE001
        return None
    if "timestamp" not in d.columns or d.empty:
        return None
    return d


def _arquivar(d: pd.DataFrame, origem: str) -> int:
    d = d.copy()
    d["_ts"] = pd.to_datetime(d["timestamp"], errors="coerce")
    d = d.dropna(subset=["_ts"])
    if d.empty:
        return 0
    d["_dia"] = d["_ts"].dt.date
    novos_total = 0
    for dia, g in d.groupby("_dia"):
        g = g.drop(columns=["_ts", "_dia"])
        p = os.path.join(OUT, f"{dia}.csv")
        old = _ler(p)
        n_old = 0 if old is None else len(old)
        base = pd.concat([old, g], ignore_index=True) if old is not None else g
        # Dedupe por linha inteira: reexecucoes nao duplicam; linhas distintas
        # com o mesmo timestamp (raro) sao preservadas.
        base = base.drop_duplicates(keep="last")
        novos = max(0, len(base) - n_old)
        if novos == 0 and os.path.exists(p):
            continue
        tmp = p + ".tmp"
        base.to_csv(tmp, index=False, encoding="utf-8")
        os.replace(tmp, p)
        novos_total += novos
        print(f"  {origem:<45} {dia}: +{novos:>5} (total {len(base)})")
    return novos_total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    agora = dt.datetime.now()
    dentro = agora.weekday() < 5 and JANELA_INI <= agora.time() <= JANELA_FIM
    if not a.force and not dentro:
        _log(f"fora da janela ({agora:%a %H:%M}) - nada a fazer")
        return 0

    fontes = [SRC] + (SEED if a.seed else [])
    total = 0
    lidos = 0
    for p in fontes:
        d = _ler(p)
        if d is None:
            continue
        lidos += 1
        total += _arquivar(d, os.path.basename(p))

    _log(f"ok: +{total} linhas novas | {lidos} arquivo(s) lido(s) | seed={a.seed}")
    print(f"ok: +{total} linhas novas | {lidos} arquivo(s) lido(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
