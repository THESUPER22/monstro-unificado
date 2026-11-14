# -*- coding: utf-8 -*-
"""
viabilidade_book.py — READ-ONLY: os dados de profundidade de book bastam para
um estudo de absorcao/sweep?

Nao envia ordem, nao altera config, nao toca no robo. Apenas inventaria os
arquivos de contexto/profundidade e mede cobertura, cadencia e variancia.

Uso:
    python backtest/viabilidade_book.py
"""
from __future__ import annotations

import os

import pandas as pd

BASE = r"C:\AIOFEN"

FONTES = [
    (os.path.join(BASE, "historico_contexto_wdo.csv"), "contexto vivo (raiz)"),
    (os.path.join(BASE, "logs", "historico_contexto_wdo_20261111_pre_fix.csv"), "pre_fix 11/11"),
    (os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.pre_reinj_1609"), "arquivo 17/09"),
    (os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.vazio_2809"), "arquivo 28/09"),
    (os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.sem_timestamp.bak"), "sem_timestamp 20/08"),
    (os.path.join(BASE, "historico_contexto_wdo.csv.sem_timestamp.bak"), "sem_timestamp 08/10"),
    (os.path.join(BASE, "modelo_monstro_wdo_dados_treino.csv"), "corpus offline julho"),
    (os.path.join(BASE, "logs", "treino_corpus_real.csv"), "corpus real de trades"),
    (os.path.join(BASE, "logs", "herman_6p", "boxes_herman.csv"), "boxes Herman"),
]

BOOK = [
    "preco_maior_escora_bid", "volume_maior_escora_bid",
    "distancia_maior_escora_bid", "preco_maior_escora_ask",
    "volume_maior_escora_ask", "distancia_maior_escora_ask",
    "liquidez_top5_bid", "liquidez_top5_ask",
]


def main() -> None:
    print("=" * 100)
    print("VIABILIDADE BOOK/ABSORCAO - inventario READ-ONLY")
    print("=" * 100)
    print(f"\n{'fonte':<26} {'linhas':>7} {'timestamp':>10} {'periodo':>26} {'book zeros':>18}")
    print("-" * 100)

    # So entram na serie temporal os arquivos de CONTEXTO com profundidade
    # limpa. O corpus de trades tem timestamp, mas escoras 100% zero -> fora.
    SERIE = {
        os.path.join(BASE, "historico_contexto_wdo.csv"),
        os.path.join(BASE, "logs", "historico_contexto_wdo_20261111_pre_fix.csv"),
        os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.pre_reinj_1609"),
        os.path.join(BASE, "_arquivo_morto", "historico_contexto_wdo.csv.vazio_2809"),
    }

    ordenados = []
    for p, nome in FONTES:
        if not os.path.exists(p):
            print(f"{nome:<26} {'AUSENTE':>7}")
            continue
        try:
            d = pd.read_csv(p, encoding="utf-8-sig", on_bad_lines="skip")
        except Exception as e:  # noqa: BLE001
            print(f"{nome:<26} ERRO: {e}")
            continue
        tem_ts = "timestamp" in d.columns
        periodo = "-"
        if tem_ts:
            ts = pd.to_datetime(d["timestamp"], errors="coerce")
            if ts.notna().any():
                periodo = (f"{ts.min():%d/%m %H:%M} -> {ts.max():%d/%m %H:%M}")
        zbook = "n/a"
        cols = [c for c in BOOK if c in d.columns]
        if cols:
            z = sum(int((pd.to_numeric(d[c], errors="coerce") == 0).sum()) for c in cols)
            zbook = f"{z}/{len(d)*len(cols)}"
        print(f"{nome:<26} {len(d):>7} {str(tem_ts):>10} {periodo:>26} {zbook:>18}")
        if p in SERIE and tem_ts and cols:
            ordenados.append((nome, d))

    if not ordenados:
        print("\nSem fontes com timestamp + book: estudo impossivel.")
        return

    a = pd.concat([d for _, d in ordenados], ignore_index=True)
    a["ts"] = pd.to_datetime(a["timestamp"], errors="coerce")
    a = a.dropna(subset=["ts"])

    print("\n" + "=" * 100)
    print(f"SERIE TEMPORAL LIMPA: {len(a)} snapshots em {a['ts'].dt.date.nunique()} sessoes")
    print("=" * 100)
    for dia, g in a.groupby(a["ts"].dt.date):
        t = g["ts"].sort_values()
        dt = t.diff().dt.total_seconds().dropna()
        print(f"  {dia}: n={len(g):>5} cadencia_med={dt.median():>4.1f}s "
              f"janela={t.min():%H:%M}-{t.max():%H:%M}")

    print("\n--- variancia das features (p5 / mediana / p95) ---")
    for c in ("volume_maior_escora_bid", "distancia_maior_escora_bid",
              "liquidez_top5_bid", "entropia_book", "bid_qty", "ask_qty"):
        if c not in a.columns:
            continue
        s = pd.to_numeric(a[c], errors="coerce").dropna()
        print(f"  {c:>28}: {s.quantile(.05):>9.2f} / {s.median():>9.2f} / {s.quantile(.95):>9.2f}")

    print("\n--- proxy de absorcao (escora a <=2 pts) ---")
    for cv, cd, lbl in (("volume_maior_escora_bid", "distancia_maior_escora_bid", "BID"),
                        ("volume_maior_escora_ask", "distancia_maior_escora_ask", "ASK")):
        if cv not in a.columns:
            continue
        v = pd.to_numeric(a[cv], errors="coerce")
        dd = pd.to_numeric(a[cd], errors="coerce")
        perto = dd <= 2.0
        print(f"  {lbl}: {int(perto.sum())}/{int(perto.notna().sum())} snapshots "
              f"({100*perto.mean():.1f}%) | vol mediano nesses = {v[perto].median():.0f}")

    print("\nVEREDITO: ver secao 23.44 do ROADMAP.")
    print("  - 4 sessoes uteis, regime estreito (set/nov); sem backfill de")
    print("    profundidade no MT5; corpus de trades com escoras 100% zero.")
    print("  - Estudo honesto exige arquivar ~40-60 sessoes antes.")


if __name__ == "__main__":
    main()
