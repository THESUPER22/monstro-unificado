#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROBO TRADER MONSTRO - ESTRUTURA COMPLETA PARA EXECUTAVEL
Criacao da estrutura completa com todos os arquivos necessarios
"""

import json
import os
import shutil
from datetime import datetime, timedelta


def criar_estrutura_completa():
    """Cria a estrutura completa do projeto para empacotamento"""

    print("Criando estrutura completa do Robo Trader Monstro...")

    # Arquivos essenciais que devem ser copiados
    arquivos_essenciais = [
        # Script principal
        "monstro_unificado_v2.py",

        # Configuracoes
        "config_win_v2.json",
        "config.json",

        # Expert Advisor MQL5
        "EA_BookData_Universal.mq5",

        # Modelos de IA (se existirem)
        "modelo_monstro.h5",
        "modelo_monstro_win.h5",
        "modelo_monstro.keras",
        "modelo_monstro_win.keras",
        "modelo_monstro_metadata.json",

        # Historicos e dados
        "historico_contexto.csv",
        "historico_contexto_win.csv",
        "historico_evolucao.csv",
        "historico_evolucao_hibrida.csv",
        "decisions.csv",
        "memoria.pkl",

        # Parametros IA
        "parametros_ia_saida.json",
        "experiencias.json",
        "experiencias_finais.json",
        "estatisticas_finais.json",

        # Dependencias
        "requirements.txt",

        # Diagnostico
        "diagnostico_monstro.py",

        # Scripts auxiliares
        "dashboard_tempo_real.py",
        "plot_evolucao.py",
        "sistema_evolucao_adaptativa.py",
        "sistema_evolucao_hibrido.py",
        "sistema_filtros_evolutivos.py",
    ]

    # Cria pasta se nao existir
    if not os.path.exists("robo_trader_exe"):
        os.makedirs("robo_trader_exe")

    # Copia arquivos existentes
    arquivos_copiados = []
    arquivos_faltando = []

    for arquivo in arquivos_essenciais:
        caminho_origem = os.path.join("..", arquivo)
        if os.path.exists(caminho_origem):
            try:
                shutil.copy2(caminho_origem, ".")
                arquivos_copiados.append(arquivo)
                print(f"Copiado: {arquivo}")
            except Exception as e:
                print(f"Erro ao copiar {arquivo}: {e}")
                arquivos_faltando.append(arquivo)
        else:
            arquivos_faltando.append(arquivo)
            print(f"Nao encontrado: {arquivo}")

    # Cria arquivos padrao se nao existirem
    criar_arquivos_padrao()

    print(f"\nRESUMO:")
    print(f"Arquivos copiados: {len(arquivos_copiados)}")
    print(f"Arquivos faltando: {len(arquivos_faltando)}")

    if arquivos_faltando:
        print(f"\nArquivos que serao criados como padrao:")
        for arquivo in arquivos_faltando:
            print(f"   - {arquivo}")

    return arquivos_copiados, arquivos_faltando


def criar_arquivos_padrao():
    """Cria arquivos padrao necessarios se nao existirem"""

    # Historico de contexto padrao
    if not os.path.exists("historico_contexto.csv"):
        with open("historico_contexto.csv", "w", encoding="utf-8") as f:
            f.write("timestamp,bid_qty,ask_qty,spread,volatility,candle_type,entropia_book,rsi_14,volume_tick,is_in_trade,floating_profit,tempo_em_trade,acao,lucro,score_distancia\n")

    # Historico WIN
    if not os.path.exists("historico_contexto_win.csv"):
        with open("historico_contexto_win.csv", "w", encoding="utf-8") as f:
            f.write("timestamp,bid_qty,ask_qty,spread,volatility,candle_type,entropia_book,rsi_14,volume_tick,is_in_trade,floating_profit,tempo_em_trade,acao,lucro,score_distancia\n")

    # Decisions.csv
    if not os.path.exists("decisions.csv"):
        with open("decisions.csv", "w", encoding="utf-8") as f:
            f.write("timestamp,acao,probabilidade,contexto,resultado\n")

    # Parametros IA padrao
    if not os.path.exists("parametros_ia_saida.json"):
        parametros_padrao = {
            "threshold_buy": 0.6,
            "threshold_sell": 0.4,
            "contador_buy": 0,
            "contador_sell": 0,
            "total_operacoes": 0,
            "ultima_atualizacao": datetime.now().isoformat()
        }
        with open("parametros_ia_saida.json", "w", encoding="utf-8") as f:
            json.dump(parametros_padrao, f, indent=2, ensure_ascii=False)

    # Experiencias padrao
    if not os.path.exists("experiencias.json"):
        with open("experiencias.json", "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    # Estatisticas padrao
    if not os.path.exists("estatisticas_finais.json"):
        stats_padrao = {
            "total_operacoes": 0,
            "lucro_total": 0.0,
            "taxa_acerto": 0.0,
            "drawdown_maximo": 0.0,
            "ultima_atualizacao": datetime.now().isoformat()
        }
        with open("estatisticas_finais.json", "w", encoding="utf-8") as f:
            json.dump(stats_padrao, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    criar_estrutura_completa()
    print("\nEstrutura completa criada! Execute build_exe.py para gerar o executavel.")
