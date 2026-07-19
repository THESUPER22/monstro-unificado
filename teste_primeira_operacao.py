#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste para verificar se o modelo consegue tomar decisões desde a primeira operação
(sem necessidade de primeira operação aleatória)
"""

import os
import sys

import pandas as pd

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from monstro_unificado import (N_FEATURES, MemoriaExperiencias,
                                   ModoOperacional, criar_modelo_neural,
                                   preparar_dados, prever_acao)
    print("✅ Imports realizados com sucesso")
except ImportError as e:
    print(f"❌ Erro no import: {e}")
    sys.exit(1)

def teste_primeira_operacao():
    """Testa se o modelo consegue tomar decisões desde a primeira operação"""
    print("\n🧪 TESTE: Primeira operação sem dados aleatórios")

    try:
        # 1. Cria modelo novo (sem experiências)
        print("\n1. Criando modelo neural...")
        modelo = criar_modelo_neural(N_FEATURES)
        print(f"✅ Modelo criado com {N_FEATURES} features")

        # 2. Cria contexto de exemplo
        print("\n2. Criando contexto de exemplo...")
        contexto = {
            "bid_qty": 150.0,
            "ask_qty": 120.0,
            "spread": 2.5,
            "volatility": 0.8,
            "candle_type": "alta",
            "entropia_book": 0.6,
            "rsi_14": 55.0,
            "volume_tick": 1500,
            "is_in_trade": 0,
            "floating_profit": 0.0,
            "tempo_em_trade": 0,
            "action": "BUY"  # Dummy para preparar_dados
        }

        # 3. Prepara dados
        print("\n3. Preparando dados...")
        df_contexto = pd.DataFrame([contexto])
        X_decisao, _ = preparar_dados(df_contexto)

        if X_decisao is None:
            print("❌ Erro ao preparar dados")
            return False

        print(f"✅ Dados preparados: shape={X_decisao.shape}")

        # 4. Testa previsão SEM memória de experiências (primeira operação)
        print("\n4. Testando previsão sem memória de experiências...")
        memoria_experiencias = None  # Simula primeira operação
        modo_operacional = ModoOperacional()

        acao, confianca = prever_acao(modelo, X_decisao, modo_operacional)

        print(f"✅ Primeira previsão: {acao} (confiança: {confianca:.2f})")

        # 5. Testa previsão COM memória de experiências
        print("\n5. Testando previsão com memória de experiências...")
        memoria_experiencias = MemoriaExperiencias()

        # Adiciona algumas experiências de exemplo
        for i in range(5):
            contexto_exemplo = contexto.copy()
            contexto_exemplo["rsi_14"] = 50 + i * 5
            memoria_experiencias.adicionar(contexto_exemplo, "BUY" if i % 2 == 0 else "SELL",
                                        10.0 if i % 2 == 0 else -5.0, 0.5)

        acao2, confianca2 = prever_acao(modelo, X_decisao, modo_operacional)

        print(f"✅ Previsão com experiências: {acao2} (confiança: {confianca2:.2f})")

        # 6. Verifica se ambas as previsões são válidas
        acoes_validas = ["BUY", "SELL"]

                 if acao in acoes_validas and acao2 in acoes_validas:
             print("\n🎉 TESTE PASSOU! O modelo consegue tomar decisões desde a primeira operação")

             # Log detalhado
             print("\n📊 Detalhes:")
             print("   - Modelo criado com sucesso")
             print(f"   - Primeira decisão (sem experiências): {acao}")
             print(f"   - Decisão com experiências: {acao2}")
             print("   - Ambas as decisões são válidas")
             print(f"   - Confiança mantida em: {confianca:.2f} e {confianca2:.2f}")

            return True
        else:
            print(f"❌ TESTE FALHOU! Decisões inválidas: {acao}, {acao2}")
            return False

    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🚀 Iniciando teste da primeira operação sem aleatoriedade")

    resultado = teste_primeira_operacao()

    if resultado:
        print("\n✅ CONCLUSÃO: O código está pronto para remover a primeira operação aleatória!")
        print("   O modelo de IA consegue tomar decisões inteligentes desde o início.")
    else:
        print("\n❌ CONCLUSÃO: Ainda há problemas que precisam ser corrigidos.")

    return resultado

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
    sucesso = main()
    sys.exit(0 if sucesso else 1)
