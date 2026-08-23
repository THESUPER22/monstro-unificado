# -*- coding: utf-8 -*-
"""Analisa logs/modelo_a_shadow.csv ao final de cada pregao.

Uso:
    python analisar_shadow.py            # analisa tudo que ha no CSV
    python analisar_shadow.py 2026-08-21 # filtra por dia

Entrega: WR e resultado liquido por faixa de probabilidade, simulacao
do veto em varios cortes, e veredito sobre promover o Modelo A.
"""
import sys
import pandas as pd

CSV = r"C:\AIOFEN\logs\modelo_a_shadow.csv"
CORTES_VETO = [0.50, 0.55, 0.60, 0.65]
FAIXAS = [(0.0, 0.40), (0.40, 0.60), (0.60, 1.01)]


def carregar(dia=None):
    df = pd.read_csv(CSV)
    df = df.dropna(subset=["resultado_bruto"]).copy()
    if df.empty:
        return df
    df["resultado_bruto"] = df["resultado_bruto"].astype(float)
    if dia:
        df = df[df["timestamp"].astype(str).str.startswith(dia)]
    return df


def linha(n, wr, net, rotulo):
    wr_txt = f"{wr:.0f}%" if n else "  -"
    print(f"  {rotulo:<18} n={n:<3} WR={wr_txt:>4}  net=R${net:>8.2f}")


def analisar(dia=None):
    df = carregar(dia)
    titulo = f" ({dia})" if dia else ""
    print("=" * 62)
    print(f"SHADOW MODE - MODELO A{titulo}")
    print("=" * 62)

    if len(df) < 5:
        print(f"Apenas {len(df)} sinal(is) com resultado. "
              "Amostra insuficiente - continuar coletando (meta 30-60).")
        return

    n = len(df)
    wr = (df["resultado_bruto"] > 0).mean() * 100
    net = df["resultado_bruto"].sum()
    print(f"\nBase completa: n={n}  WR={wr:.0f}%  net=R${net:.2f}")

    print("\nPor faixa de probabilidade:")
    for lo, hi in FAIXAS:
        g = df[(df["prob_modelo_a"] >= lo) & (df["prob_modelo_a"] < hi)]
        rotulo = f"p {lo:.2f}-{hi:.2f}".replace(".", ",")
        linha(len(g), (g["resultado_bruto"] > 0).mean() * 100 if len(g) else 0,
              g["resultado_bruto"].sum(), rotulo)

    print("\nSimulacao do veto (o corte teria ajudado?):")
    base_net = df["resultado_bruto"].sum()
    for corte in CORTES_VETO:
        mantidos = df[df["prob_modelo_a"] < corte]
        vetados = df[df["prob_modelo_a"] >= corte]
        novo = mantidos["resultado_bruto"].sum()
        delta = novo - base_net
        wr_m = (mantidos["resultado_bruto"] > 0).mean() * 100 if len(mantidos) else 0
        print(f"  veto p>={corte:.2f}: cortaria {len(vetados):>2} trade(s) "
              f"| restariam n={len(mantidos):>2} WR={wr_m:>3.0f}% "
              f"net=R${novo:>8.2f} (delta R${delta:+.2f})")

    melhor_corte, melhor_delta = None, 0.0
    for corte in CORTES_VETO:
        d = df[df["prob_modelo_a"] < corte]["resultado_bruto"].sum() - base_net
        if d > melhor_delta:
            melhor_corte, melhor_delta = corte, d

    print("\nVeredito do periodo:")
    alta = df[df["prob_modelo_a"] >= 0.60]
    baixa = df[df["prob_modelo_a"] < 0.60]
    if len(alta) >= 3 and len(baixa) >= 3:
        wr_alta = (alta["resultado_bruto"] > 0).mean() * 100
        wr_baixa = (baixa["resultado_bruto"] > 0).mean() * 100
        if wr_alta < wr_baixa:
            print("  ALERTA: correlacao INVERTIDA (p alto rende menos que p baixo).")
        elif wr_alta > wr_baixa:
            print("  Positivo: p alto rende mais que p baixo - sinal de calibracao.")
        else:
            print("  Neutro: sem separacao entre p alto e p baixo ate agora.")
    else:
        print("  Amostragem por grupo ainda pequena; aguardar mais sinais.")
    if melhor_corte and melhor_delta > 0:
        print(f"  Melhor corte simulado: p>={melhor_corte:.2f} "
              f"(delta R${melhor_delta:+.2f}). NAO integrar so por isso - "
              "confirmar consistencia semana a semana.")
    else:
        print("  Nenhum corte de veto teria melhorado o resultado. "
              "Modelo A continua SEM poder de veto.")


if __name__ == "__main__":
    analisar(sys.argv[1] if len(sys.argv) > 1 else None)
