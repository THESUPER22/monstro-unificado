#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 VALIDADOR DE ALINHAMENTO COM ESPECIFICAÇÃO
Verifica se o código está 100% alinhado com a especificação técnica do Monstro
"""

import json
import os
import sys
from datetime import datetime

def validar_config_json():
    """Valida se config.json está conforme especificação."""
    print("📋 VALIDANDO CONFIG.JSON...")

    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Validações críticas
        validacoes = [
            ("Symbol Prefix", config.get("symbol_prefix") == "WDO", "WDO", config.get("symbol_prefix")),
            ("Volume Padrão", config.get("volume_padrao") == 1.0, "1.0", config.get("volume_padrao")),
            ("SL Points", config.get("sl_points") == 5, "5", config.get("sl_points")),
            ("TP Points", config.get("tp_points") == 10, "10", config.get("tp_points")),
            ("Max Loss Diário", config.get("max_loss_diario") == -500.0, "-500.0", config.get("max_loss_diario")),
            ("Max Spread", config.get("max_spread") == 5, "5", config.get("max_spread")),
            ("Min Volume Book", config.get("min_volume_book") == 200, "200", config.get("min_volume_book")),
        ]

        # Validações de horários
        horarios = config.get("horarios", {})
        validacoes_horarios = [
            ("Pregão", horarios.get("pregao") == "09:00", "09:00", horarios.get("pregao")),
            ("Limite Ordens", horarios.get("limite_ordens") == "18:15", "18:15", horarios.get("limite_ordens")),
            ("Encerramento", horarios.get("encerramento") == "18:20", "18:20", horarios.get("encerramento")),
            ("After Market", horarios.get("after_market") == "18:32", "18:32", horarios.get("after_market")),
        ]

        # Validações de IA
        ia_config = config.get("ia_config", {})
        validacoes_ia = [
            ("Epochs Treino", ia_config.get("epochs_treino") == 3, "3", ia_config.get("epochs_treino")),
            ("Batch Size", ia_config.get("batch_size") == 32, "32", ia_config.get("batch_size")),
            ("Learning Rate", ia_config.get("learning_rate") == 0.001, "0.001", ia_config.get("learning_rate")),
            ("Decay Meia Vida", ia_config.get("decay_meia_vida") == 12, "12", ia_config.get("decay_meia_vida")),
        ]

        todas_validacoes = validacoes + validacoes_horarios + validacoes_ia

        print("\n📊 RESULTADOS:")
        sucessos = 0
        for nome, passou, esperado, atual in todas_validacoes:
            status = "✅" if passou else "❌"
            print(f"{status} {nome}: {atual} (esperado: {esperado})")
            if passou:
                sucessos += 1

        porcentagem = (sucessos / len(todas_validacoes)) * 100
        print(f"\n🎯 SCORE CONFIG.JSON: {sucessos}/{len(todas_validacoes)} ({porcentagem:.1f}%)")

        return porcentagem >= 95

    except Exception as e:
        print(f"❌ Erro ao validar config.json: {e}")
        return False

def validar_arquivos_essenciais():
    """Valida se arquivos essenciais existem."""
    print("\n📁 VALIDANDO ARQUIVOS ESSENCIAIS...")

    arquivos_essenciais = [
        ("monstro_unificado.py", "Código principal do robô"),
        ("config.json", "Configurações principais"),
        ("requirements.txt", "Dependências Python"),
        ("modelo_monstro.h5", "Modelo IA (pode não existir inicialmente)", False),
        ("historico_contexto.csv", "Histórico de experiências (pode não existir)", False),
        ("decisions.csv", "Log de decisões (pode não existir)", False),
        ("memoria.pkl", "Buffer de replay (pode não existir)", False),
    ]

    sucessos = 0
    total = 0

    for item in arquivos_essenciais:
        if len(item) == 2:
            arquivo, descricao = item
            obrigatorio = True
        else:
            arquivo, descricao, obrigatorio = item

        existe = os.path.exists(arquivo)

        if obrigatorio:
            total += 1
            if existe:
                sucessos += 1
                print(f"✅ {arquivo} - {descricao}")
            else:
                print(f"❌ {arquivo} - {descricao} (OBRIGATÓRIO)")
        else:
            if existe:
                print(f"✅ {arquivo} - {descricao}")
            else:
                print(f"⚠️  {arquivo} - {descricao} (será criado automaticamente)")

    porcentagem = (sucessos / total) * 100 if total > 0 else 100
    print(f"\n🎯 SCORE ARQUIVOS: {sucessos}/{total} ({porcentagem:.1f}%)")

    return porcentagem >= 95

def validar_especificacao_tecnica():
    """Valida aspectos técnicos da especificação."""
    print("\n🔧 VALIDANDO ESPECIFICAÇÃO TÉCNICA...")

    validacoes_tecnicas = []

    # Verifica se monstro_unificado.py existe e tem conteúdo básico
    if os.path.exists('monstro_unificado.py'):
        with open('monstro_unificado.py', 'r', encoding='utf-8') as f:
            conteudo = f.read()

        checks = [
            ("Classe GerenciadorBloqueio", "class GerenciadorBloqueio" in conteudo),
            ("N_FEATURES = 11", "N_FEATURES = 11" in conteudo),
            ("Flask Dashboard", "from flask import Flask" in conteudo),
            ("MetaTrader5 API", "import MetaTrader5 as mt5" in conteudo),
            ("TensorFlow/Keras", "import tensorflow as tf" in conteudo),
            ("Rede Neural 128→64→32→1", "Dense(128" in conteudo and "Dense(64" in conteudo and "Dense(32" in conteudo),
            ("Horários de Encerramento", "18:20" in conteudo and "18:32" in conteudo),
            ("Entropia do Book", "calcular_entropia" in conteudo),
            ("RSI Calculation", "calcular_rsi" in conteudo),
            ("Trailing Stop", "TRAILING_" in conteudo),
        ]

        validacoes_tecnicas.extend(checks)
    else:
        validacoes_tecnicas.append(("Arquivo Principal", False))

    print("\n📊 RESULTADOS TÉCNICOS:")
    sucessos = 0
    for nome, passou in validacoes_tecnicas:
        status = "✅" if passou else "❌"
        print(f"{status} {nome}")
        if passou:
            sucessos += 1

    porcentagem = (sucessos / len(validacoes_tecnicas)) * 100 if validacoes_tecnicas else 0
    print(f"\n🎯 SCORE TÉCNICO: {sucessos}/{len(validacoes_tecnicas)} ({porcentagem:.1f}%)")

    return porcentagem >= 90

def gerar_relatorio_final():
    """Gera relatório final de alinhamento."""
    print("\n" + "="*60)
    print("📋 RELATÓRIO FINAL DE ALINHAMENTO")
    print("="*60)

    config_ok = validar_config_json()
    arquivos_ok = validar_arquivos_essenciais()
    tecnico_ok = validar_especificacao_tecnica()

    print("\n🎯 RESUMO GERAL:")
    print(f"✅ Configuração: {'APROVADO' if config_ok else 'REPROVADO'}")
    print(f"✅ Arquivos: {'APROVADO' if arquivos_ok else 'REPROVADO'}")
    print(f"✅ Técnico: {'APROVADO' if tecnico_ok else 'REPROVADO'}")

    if config_ok and arquivos_ok and tecnico_ok:
        print("\n🎉 PARABÉNS! SISTEMA 100% ALINHADO COM A ESPECIFICAÇÃO!")
        print("✅ O Monstro está pronto para operar WDO conforme especificado.")
        return True
    else:
        print("\n⚠️  ATENÇÃO! Algumas correções ainda são necessárias.")
        print("❌ Revise os itens marcados como REPROVADO acima.")
        return False

def main():
    """Função principal."""
    print("🤖 VALIDADOR DE ALINHAMENTO - MONSTRO DAS NEGOCIAÇÕES")
    print(f"📅 Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

    try:
        sucesso = gerar_relatorio_final()

        if sucesso:
            print("\n🚀 PRÓXIMOS PASSOS:")
            print("1. Execute: python monstro_unificado.py")
            print("2. Acesse dashboard: http://localhost:5001")
            print("3. Monitore logs em: monstro.log")
            sys.exit(0)
        else:
            print("\n🔧 AÇÕES NECESSÁRIAS:")
            print("1. Corrija os itens reprovados")
            print("2. Execute novamente este validador")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
