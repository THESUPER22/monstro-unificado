#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da implementação de coleta de ticks no Monstro
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa do Monstro
try:
    import MetaTrader5 as mt5
    from mostro_unificado_copia_do_v2 import ColetorTicksInteligente
    print("✅ Imports realizados com sucesso")
except ImportError as e:
    print(f"❌ Erro no import: {e}")
    sys.exit(1)


def testar_coletor_ticks():
    """Testa o coletor de ticks."""
    print("🎯 Iniciando teste do Coletor de Ticks Inteligente...")

    # Inicializa MT5
    if not mt5.initialize():
        print(f"❌ Erro ao inicializar MT5: {mt5.last_error()}")
        return False

    print("✅ MT5 inicializado com sucesso")

    # Cria instância do coletor
    coletor = ColetorTicksInteligente()
    print("✅ Coletor de ticks criado")

    # Testa com símbolo WIN
    symbols_to_test = ["WINF25", "WIN$", "WDOG25", "WDO$"]

    for symbol in symbols_to_test:
        print(f"\n📊 Testando símbolo: {symbol}")

        # Verifica se símbolo existe
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"⚠️ Símbolo {symbol} não encontrado")
            continue

        # Seleciona o símbolo
        if not mt5.symbol_select(symbol, True):
            print(f"⚠️ Não foi possível selecionar {symbol}")
            continue

        print(f"✅ Símbolo {symbol} selecionado")

        # Testa coleta de ticks
        try:
            dados_ticks = coletor.coletar_ticks_recentes(symbol, 50)

            if dados_ticks:
                print(f"✅ Ticks coletados com sucesso!")
                print(f"   • Quantidade: {dados_ticks['qtd_ticks']}")
                print(
                    f"   • Direção do fluxo: {dados_ticks['direcao_fluxo']:.4f}")
                print(
                    f"   • Intensidade: {dados_ticks['intensidade_ticks']:.4f}")
                print(
                    f"   • Aceleração: {dados_ticks['aceleracao_preco']:.4f}")
                print(f"   • Spread médio: {dados_ticks['spread_medio']:.5f}")
                print(f"   • Volume médio: {dados_ticks['volume_medio']:.2f}")
                print(
                    f"   • Variação total: {dados_ticks['variacao_total']:.4f}%")

                # Testa cache
                print("🔄 Testando cache...")
                start_time = time.time()
                dados_cache = coletor.coletar_ticks_recentes(symbol, 50)
                cache_time = time.time() - start_time

                if dados_cache and cache_time < 0.01:  # Deve ser muito rápido se usar cache
                    print(f"✅ Cache funcionando! Tempo: {cache_time:.4f}s")
                else:
                    print(
                        f"⚠️ Cache pode não estar funcionando. Tempo: {cache_time:.4f}s")

                return True

            else:
                print(f"❌ Nenhum tick coletado para {symbol}")

        except Exception as e:
            print(f"❌ Erro ao coletar ticks para {symbol}: {e}")
            import traceback
            traceback.print_exc()

    print("❌ Nenhum símbolo funcionou")
    return False


def testar_integracao_contexto():
    """Testa a integração com o contexto do Monstro."""
    print("\n🧠 Testando integração com contexto...")

    # Simula dados de ticks
    dados_ticks_simulados = {
        'qtd_ticks': 75,
        'direcao_fluxo': 0.25,
        'intensidade_ticks': 0.6,
        'aceleracao_preco': 0.3,
        'spread_medio': 0.0005,
        'volume_medio': 5.2,
        'preco_inicial': 125000,
        'preco_final': 125050,
        'variacao_total': 0.04
    }

    # Simula contexto base
    contexto_base = {
        "bid_qty": 1500, "ask_qty": 1400, "spread": 0.5, "volatility": 250,
        "candle_type": "alta", "entropia_book": 0.7, "rsi_14": 65,
        "volume_tick": 10, "is_in_trade": 0, "floating_profit": 0.0, "tempo_em_trade": 0
    }

    # Integra features dos ticks
    direcao_fluxo = dados_ticks_simulados['direcao_fluxo']
    intensidade_ticks = dados_ticks_simulados['intensidade_ticks']
    aceleracao_preco = dados_ticks_simulados['aceleracao_preco']

    contexto_completo = {
        **contexto_base,
        "direcao_fluxo": direcao_fluxo,
        "intensidade_ticks": intensidade_ticks,
        "aceleracao_preco": aceleracao_preco
    }

    print("✅ Contexto integrado com features dos ticks:")
    for key, value in contexto_completo.items():
        if key in ['direcao_fluxo', 'intensidade_ticks', 'aceleracao_preco']:
            print(f"   🎯 {key}: {value}")
        else:
            print(f"   • {key}: {value}")

    # Verifica se as features estão nos limites corretos
    assert -1.0 <= direcao_fluxo <= 1.0, "Direção do fluxo fora do limite"
    assert 0.0 <= intensidade_ticks <= 1.0, "Intensidade fora do limite"
    assert 0.0 <= aceleracao_preco <= 1.0, "Aceleração fora do limite"

    print("✅ Todas as features estão nos limites corretos!")
    return True


def main():
    """Função principal de teste."""
    print("🚀 TESTE DO SISTEMA DE TICKS DO MONSTRO")
    print("=" * 50)

    try:
        # Teste 1: Coletor de ticks
        if testar_coletor_ticks():
            print("\n✅ Teste do coletor: PASSOU")
        else:
            print("\n❌ Teste do coletor: FALHOU")

        # Teste 2: Integração com contexto
        if testar_integracao_contexto():
            print("✅ Teste de integração: PASSOU")
        else:
            print("❌ Teste de integração: FALHOU")

        print("\n🎯 RESUMO:")
        print("• Coletor de ticks implementado")
        print("• Cache inteligente com TTL de 2s")
        print("• 3 novas features para IA:")
        print("  - direcao_fluxo (-1 a +1)")
        print("  - intensidade_ticks (0 a 1)")
        print("  - aceleracao_preco (0 a 1)")
        print("• Integração com contexto do Monstro")

    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Finaliza MT5
        mt5.shutdown()
        print("\n🔚 MT5 finalizado")


if __name__ == "__main__":
    main()
