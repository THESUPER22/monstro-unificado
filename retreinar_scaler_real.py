#!/usr/bin/env python3
"""
RETREINO DO SCALER COM DADOS REAIS COMBINADOS

Descoberta na investigação (01/08):
- historico_contexto_wdo.csv: bid_qty/ask_qty/volume_tick = 0 em todas as linhas
  e entropia_book truncada a 1.0 (bug de gravação no salvar_experiencia_csv).
  Confiáveis nele: spread, volatility, rsi_14 e as 8 features de escora/liquidez
  (nas 1368 linhas com ação real).
- decisions_wdo.csv (358 linhas): bid_qty, ask_qty, spread, volatility,
  entropia_book, rsi_14, volume_tick REAIS.

Estratégia: combinar as duas fontes.
- 7 features principais de book: decisions_wdo.csv
- 8 features de escora/liquidez: historico_contexto_wdo.csv (linhas com ação)
- is_in_trade/floating_profit/tempo_em_trade: domínio fixo (sem dados reais)
- 4 features PTAX: domínio fixo

Formato de saída: modelo_monstro_wdo_scaler.json (compatível com
forcar_recreacao_scaler() do monstro_unificado_v22.py)
"""
import os
import json
import shutil
import datetime
import sys

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_HISTORICO = os.path.join(BASE, "historico_contexto_wdo.csv")
CSV_DECISIONS = os.path.join(BASE, "decisions_wdo.csv")
SCALER_PATH = os.path.join(BASE, "modelo_monstro_wdo_scaler.json")

# Ordem exata das 22 features do scaler
FEATURES_ORDER = [
    "bid_qty", "ask_qty", "spread", "volatility", "entropia_book", "rsi_14",
    "volume_tick", "is_in_trade", "floating_profit", "tempo_em_trade",
    "preco_maior_escora_bid", "volume_maior_escora_bid", "distancia_maior_escora_bid",
    "preco_maior_escora_ask", "volume_maior_escora_ask", "distancia_maior_escora_ask",
    "liquidez_top5_bid", "liquidez_top5_ask",
    "dolar_casado", "em_janela_ptax", "minutos_para_ptax", "dia_ptax",
]

# Fontes das 22 features
# spread vem do histórico (decisions tem spread fixo 0.5; histórico varia 0.5-1.0)
FONTE_DECISIONS = {"bid_qty", "ask_qty", "volatility",
                   "entropia_book", "rsi_14", "volume_tick"}
FONTE_HISTORICO = {"spread",
                   "preco_maior_escora_bid", "volume_maior_escora_bid",
                   "distancia_maior_escora_bid", "preco_maior_escora_ask",
                   "volume_maior_escora_ask", "distancia_maior_escora_ask",
                   "liquidez_top5_bid", "liquidez_top5_ask"}

# Domínio fixo (sem dados reais confiáveis): trade-state + PTAX
DOMINIO_FIXO = {
    # is_in_trade: flag 0/1
    "is_in_trade": (0.0, 1.0),
    # floating_profit: lucro flutuante em reais de posição ativa
    "floating_profit": (-500.0, 500.0),
    # tempo_em_trade: segundos em posição (máx ~10 min = 600s)
    "tempo_em_trade": (0.0, 600.0),
    # dolar_casado = (preco_wdo - ptax)*1000; WDO vs PTAX varia em pontos
    "dolar_casado": (-200.0, 200.0),
    "em_janela_ptax": (0.0, 1.0),
    "minutos_para_ptax": (0.0, 60.0),
    "dia_ptax": (0.0, 1.0),
}


def _extrair_min_max(df, feature):
    col = pd.to_numeric(df[feature], errors="coerce").dropna()
    if len(col) == 0:
        print(f"  AVISO: '{feature}' sem dados válidos na fonte")
        return 0.0, 0.0
    return float(col.min()), float(col.max())


def main():
    if not os.path.exists(CSV_DECISIONS):
        print(f"ERRO: CSV não encontrado: {CSV_DECISIONS}")
        sys.exit(1)
    if not os.path.exists(CSV_HISTORICO):
        print(f"ERRO: CSV não encontrado: {CSV_HISTORICO}")
        sys.exit(1)

    decisions = pd.read_csv(CSV_DECISIONS, encoding="utf-8-sig")
    historico = pd.read_csv(CSV_HISTORICO, encoding="utf-8-sig")
    historico_vivo = historico[historico["action"] != "NADA"]
    print(f"decisions_wdo.csv: {len(decisions)} linhas")
    print(f"historico_contexto_wdo.csv: {len(historico)} linhas "
          f"({len(historico_vivo)} com ação real)")

    mins, maxs, origens = [], [], []
    for f in FEATURES_ORDER:
        if f in FONTE_DECISIONS:
            lo, hi = _extrair_min_max(decisions, f)
            origem = f"REAL decisions ({int(len(decisions))} linhas)"
        elif f in FONTE_HISTORICO:
            lo, hi = _extrair_min_max(historico_vivo, f)
            origem = f"REAL historico ({int(len(historico_vivo))} linhas)"
        else:
            lo, hi = DOMINIO_FIXO[f]
            origem = "FIXO"
        mins.append(lo)
        maxs.append(hi)
        origens.append(origem)

    # Validação: nenhuma feature REAL deve ficar constante
    print("\n=== FEATURES CONSTANTES (ERRO SE REAL) ===")
    tem_constante = False
    for f, lo, hi, origem in zip(FEATURES_ORDER, mins, maxs, origens):
        if abs(hi - lo) < 1e-9:
            print(f"  [CONSTANTE] {f}: min={lo} max={hi} ({origem})")
            tem_constante = True
    if not tem_constante:
        print("  Nenhuma feature constante. OK.")

    novo_scaler = {
        "min": mins,
        "max": maxs,
        "feature_names": FEATURES_ORDER,
    }

    # Backup do scaler atual antes de sobrescrever
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(SCALER_PATH):
        backup = SCALER_PATH.replace(".json", f".backup_anterior_{ts}.json")
        shutil.copy2(SCALER_PATH, backup)
        print(f"\nBackup do scaler anterior: {backup}")

    with open(SCALER_PATH, "w", encoding="utf-8") as f:
        json.dump(novo_scaler, f)
    print(f"Scaler salvo: {SCALER_PATH} ({len(FEATURES_ORDER)} features)")

    print("\n=== RESUMO FINAL ===")
    for name, lo, hi, origem in zip(FEATURES_ORDER, mins, maxs, origens):
        print(f"  [{origem}] {name}: min={lo} max={hi}")

    print("\nOK: retreino do scaler concluído.")


if __name__ == "__main__":
    main()
