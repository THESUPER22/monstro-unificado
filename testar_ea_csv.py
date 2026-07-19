#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 TESTE ARQUENDPOINTS DE EVOLUÇÃO
Script para testar os endpoints de API do sistema evolutivo
"""

import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

# URL base do servidor
BASE_URL = "http://localhost:5001"

# Endpoints a serem testados
ENDPOINTS = [
    "/api/evolution/metrics",
    "/api/evolution/parameters",
    "/api/evolution/impact",
    "/api/evolution/status",
    "/api/evolution/alerts"
]


def criar_dados_teste():
    """Cria arquivos de dados de teste se não existirem."""
    # Cria historico_contexto.csv se não existir
    if not os.path.exists("historico_contexto.csv"):
        print("📝 Criando arquivo historico_contexto.csv de teste...")

        # Cria dados simulados
        dados = []
        for i in range(500):
            # Simula alternância entre BUY e SELL
            acao = "BUY" if i % 2 == 0 else "SELL"

            # Simula rewards com tendência de melhoria
            base_reward = np.random.normal(0, 50)
            tendencia = i / 100  # Melhora gradual
            reward = base_reward + tendencia

            # Adiciona ruído aos dados
            dados.append({
                'bid_qty': np.random.randint(100, 500),
                'ask_qty': np.random.randint(100, 500),
                'spread': np.random.uniform(0.5, 3.0),
                'volatility': np.random.uniform(0.5, 5.0),
                'candle_type': np.random.choice(['alta', 'baixa', 'doji']),
                'entropia_book': np.random.uniform(0.2, 0.8),
                'rsi_14': np.random.uniform(30, 70),
                'volume_tick': np.random.randint(10, 100),
                'is_in_trade': np.random.choice([0, 1]),
                'floating_profit': np.random.normal(0, 20),
                'tempo_em_trade': np.random.randint(0, 300),
                'action': acao,
                'reward': reward
            })

        # Cria DataFrame e salva
        df = pd.DataFrame(dados)
        df.to_csv("historico_contexto.csv", index=False)
        print("✅ Arquivo historico_contexto.csv criado com sucesso!")

    # Cria historico_evolucao_hibrida.csv se não existir
    if not os.path.exists("historico_evolucao_hibrida.csv"):
        print("📝 Criando arquivo historico_evolucao_hibrida.csv de teste...")

        # Cria dados simulados
        dados = []
        niveis = ['iniciante', 'intermediario', 'avancado', 'expert', 'mestre']
        nivel_atual = 'iniciante'

        for i in range(20):
            # Simula evolução de nível a cada 5 ciclos
            if i > 0 and i % 5 == 0 and niveis.index(nivel_atual) < len(niveis) - 1:
                nivel_atual = niveis[niveis.index(nivel_atual) + 1]

            # Simula melhoria gradual nas métricas
            taxa_acerto = 0.5 + (i * 0.01)
            profit_factor = 1.0 + (i * 0.05)

            # Data simulada (um registro por dia)
            data = (datetime.now() - timedelta(days=20-i)).isoformat()

            dados.append({
                'timestamp': data,
                'nivel': nivel_atual,
                'ciclo_adaptacao': i,
                'taxa_acerto': taxa_acerto,
                'profit_factor': profit_factor,
                'max_drawdown': 0.02 - (i * 0.001),
                'threshold_final': 0.6 + (i * 0.005),
                'max_trades_hora_final': 20 - i,
                'min_entropia_final': 0.3 + (i * 0.01)
            })

        # Cria DataFrame e salva
        df = pd.DataFrame(dados)
        df.to_csv("historico_evolucao_hibrida.csv", index=False)
        print("✅ Arquivo historico_evolucao_hibrida.csv criado com sucesso!")

    # Cria historico_evolucao.csv se não existir
    if not os.path.exists("historico_evolucao.csv"):
        print("📝 Criando arquivo historico_evolucao.csv de teste...")

        # Cria dados simulados
        dados = []

        for i in range(15):
            # Data simulada (um registro por dia)
            data = (datetime.now() - timedelta(days=15-i)).isoformat()

            dados.append({
                'timestamp': data,
                'ciclo': i,
                'taxa_acerto': 0.55 + (i * 0.01),
                'profit_factor': 1.2 + (i * 0.04),
                'max_drawdown': 0.03 - (i * 0.001),
                'total_operacoes': 50 + (i * 10),
                'threshold_confianca': 0.65 + (i * 0.005),
                'max_trades_por_hora': 15 - (i * 0.5),
                'min_entropia_book': 0.35 + (i * 0.01)
            })

        # Cria DataFrame e salva
        df = pd.DataFrame(dados)
        df.to_csv("historico_evolucao.csv", index=False)
        print("✅ Arquivo historico_evolucao.csv criado com sucesso!")


def testar_endpoints():
    """Testa os endpoints da API de evolução."""
    print("\n🧪 TESTANDO ENDPOINTS DE EVOLUÇÃO")
    print("="*50)

    for endpoint in ENDPOINTS:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n📡 Testando endpoint: {url}")

        try:
            # Faz requisição GET
            response = requests.get(url)

            # Verifica status code
            if response.status_code == 200:
                print(f"✅ Status: {response.status_code} OK")

                # Tenta parsear JSON
                data = response.json()

                # Mostra resumo dos dados
                print("📊 Resumo dos dados:")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict):
                            print(f"  - {key}: {len(value)} itens")
                        elif isinstance(value, list):
                            print(f"  - {key}: {len(value)} itens")
                        else:
                            print(f"  - {key}: {value}")
            else:
                print(f"❌ Erro: Status {response.status_code}")
                print(f"Resposta: {response.text}")

        except requests.exceptions.ConnectionError:
            print(
                f"❌ Erro de conexão: Verifique se o servidor está rodando em {BASE_URL}")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)}")


if __name__ == "__main__":
    print("🚀 TESTE DOS ENDPOINTS DE EVOLUÇÃO")
    print("="*50)

    # Cria dados de teste
    criar_dados_teste()

    # Pergunta se o servidor está rodando
    resposta = input("\n⚠️ O servidor do Monstro está rodando? (s/n): ")
    if resposta.lower() != 's':
        print("❌ Por favor, inicie o servidor antes de executar este teste.")
        sys.exit(1)

    # Testa endpoints
    testar_endpoints()

    print("\n✅ Teste concluído!")
    print("\n✅ Teste concluído!")
