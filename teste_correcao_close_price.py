#!/usr/bin/env python3
"""
Teste para verificar se a correção doe_price funcionou
"""
from monstro_unificado_v2 import inicializar_mt5, obter_dados_mercado
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa apenas as funções necessárias


def teste_obter_dados():
    """Testa a função obter_dados_mercado"""
    print("🔧 Testando correção do close_price...")

    # Inicializa MT5
    if not inicializar_mt5():
        print("❌ Falha ao inicializar MT5")
        return False

    # Testa a função
    try:
        resultado = obter_dados_mercado()
        print(f"✅ Função executou sem erro: {type(resultado)}")
        print(f"📊 Resultado: {resultado}")
        return True
    except Exception as e:
        print(f"❌ Erro na função: {e}")
        return False


if __name__ == "__main__":
    teste_obter_dados()
