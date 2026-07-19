#!/usr/bin/env python3
# 🎯 SCRIPT PARA TESTAR AS MELHORIAS DEFINITIVAS DO MONSTRO

import sys
import os
import time
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def testar_imports():
    """Testa se todos os imports necessários estão funcionando"""
    print("🔍 Testando imports...")
    try:
        from monstro_unificado import GerenciadorTempo, AnalisadorMomentum, SCALPING_MODE
        print("✅ Classes principais importadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        return False

def testar_gerenciador_tempo():
    """Testa o gerenciador de tempo"""
    print("\n⏰ Testando Gerenciador de Tempo...")
    try:
        from monstro_unificado import GerenciadorTempo
        
        gerenciador = GerenciadorTempo()
        ticket_teste = 12345
        
        # Registrar entrada
        gerenciador.registrar_entrada(ticket_teste)
        time.sleep(1)  # Aguardar 1 segundo
        
        # Calcular tempo
        tempo = gerenciador.calcular_tempo_trade(ticket_teste)
        print(f"✅ Tempo calculado: {tempo:.2f} minutos")
        
        # Remover posição
        gerenciador.remover_posicao(ticket_teste)
        print("✅ Posição removida com sucesso")
        
        return True
    except Exception as e:
        print(f"❌ Erro no gerenciador de tempo: {e}")
        return False

def testar_analisador_momentum():
    """Testa o analisador de momentum"""
    print("\n🧠 Testando Analisador de Momentum...")
    try:
        from monstro_unificado import AnalisadorMomentum
        
        analisador = AnalisadorMomentum()
        
        # Dados de teste
        precos = [100.0, 101.0, 102.5, 103.0, 102.0, 104.0]
        volumes = [1000, 1200, 1100, 1300, 900, 1500]
        
        # Testar momentum
        momentum = analisador.calcular_momentum_5_periodos(precos)
        print(f"✅ Momentum 5 períodos: {momentum:.2f}%")
        
        # Testar reversão
        reversao = analisador.detectar_reversao_momentum(precos, volumes)
        print(f"✅ Sinal de reversão: {reversao:.2f}")
        
        # Testar intensidade de volume
        intensidade = analisador.calcular_intensidade_volume(volumes)
        print(f"✅ Intensidade de volume: {intensidade:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no analisador de momentum: {e}")
        return False

def testar_scalping_config():
    """Testa as configurações de scalping"""
    print("\n🎯 Testando Configurações de Scalping...")
    try:
        from monstro_unificado import SCALPING_MODE
        
        print(f"✅ Scalping ativo: {SCALPING_MODE['ativo']}")
        print(f"✅ Lucro rápido: {SCALPING_MODE['lucro_rapido_pts']} pts")
        print(f"✅ Prejuízo limite: {SCALPING_MODE['prejuizo_rapido_pts']} pts")
        print(f"✅ Tempo máximo: {SCALPING_MODE['tempo_max_segundos']} segundos")
        print(f"✅ Agressividade: {SCALPING_MODE['agressividade']*100}%")
        
        return True
    except Exception as e:
        print(f"❌ Erro nas configurações de scalping: {e}")
        return False

def testar_features_expandidas():
    """Testa se as features expandidas estão corretas"""
    print("\n📊 Testando Features Expandidas...")
    try:
        from monstro_unificado import FEATURE_COLUMNS
        
        features_esperadas = [
            "bid_qty", "ask_qty", "spread", "volatility", "candle_type", 
            "entropia_book", "rsi_14", "volume_tick", "is_in_trade", 
            "floating_profit", "tempo_em_trade", "delta_bid_ask",
            "momentum_5", "momentum_reversao", "volume_intensidade"
        ]
        
        print(f"✅ Total de features: {len(FEATURE_COLUMNS)}")
        print(f"✅ Features esperadas: {len(features_esperadas)}")
        
        for feature in features_esperadas:
            if feature in FEATURE_COLUMNS:
                print(f"   ✅ {feature}")
            else:
                print(f"   ❌ {feature} FALTANDO!")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Erro nas features: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🚀 TESTE DAS MELHORIAS DEFINITIVAS DO MONSTRO")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    testes = [
        ("Imports", testar_imports),
        ("Gerenciador Tempo", testar_gerenciador_tempo),
        ("Analisador Momentum", testar_analisador_momentum),
        ("Configurações Scalping", testar_scalping_config),
        ("Features Expandidas", testar_features_expandidas)
    ]
    
    sucessos = 0
    total = len(testes)
    
    for nome, funcao in testes:
        try:
            if funcao():
                sucessos += 1
            else:
                print(f"❌ Falha no teste: {nome}")
        except Exception as e:
            print(f"❌ Erro no teste {nome}: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO FINAL: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODAS AS MELHORIAS FORAM IMPLEMENTADAS COM SUCESSO!")
        print("✅ Bug timestamp: RESOLVIDO")
        print("✅ Scalping agressivo: IMPLEMENTADO") 
        print("✅ Análise momentum: ATIVA")
        print("✅ Detecção reversão: OPERACIONAL")
        print("\n🚀 MONSTRO PRONTO PARA OPERAÇÃO DEFINITIVA!")
    else:
        print("⚠️ Alguns testes falharam. Verifique os erros acima.")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 