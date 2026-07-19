#!/usr/bin/env python3
# -utf-8 -*-
"""
Teste de Configuração WIN v2
Verifica se todas as configurações estão corretas para o Mini Índice
"""

import json
import os
import sys


def testar_configuracao_win():
    """Testa se a configuração WIN v2 está correta."""
    print("🎯 TESTE DE CONFIGURAÇÃO WIN V2")
    print("=" * 50)

    # Verifica se arquivo de configuração existe
    config_file = "config_win_v2.json"
    if not os.path.exists(config_file):
        print(f"❌ ERRO: {config_file} não encontrado!")
        return False

    # Carrega configuração
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ Configuração carregada: {config_file}")
    except Exception as e:
        print(f"❌ ERRO ao carregar configuração: {e}")
        return False

    # Testa configurações críticas
    testes = [
        ("Symbol Prefix", config.get("symbol_prefix"), "WIN"),
        ("Volume Padrão", config.get("volume_padrao"), 5.0),
        ("SL Points", config.get("sl_points"), 90),
        ("TP Points", config.get("tp_points"), 35),
        ("Max Loss Diário", config.get("max_loss_diario"), -1000.0),
        ("Max Spread", config.get("max_spread"), 10),
        ("Min Volume Book", config.get("min_volume_book"), 500),
        ("Magic Number", config.get("geral", {}).get("magic_number"), 123457),
        ("Port Dashboard", config.get("web_dashboard", {}).get("port"), 5002),
        ("Tick Size", config.get("contrato", {}).get("tick_size"), 0.2),
        ("Ticks Por Ponto", config.get("contrato", {}).get("ticks_por_ponto"), 10000),
    ]

    print("\n📊 VERIFICAÇÃO DE CONFIGURAÇÕES:")
    print("-" * 50)

    erros = 0
    for nome, valor_atual, valor_esperado in testes:
        if valor_atual == valor_esperado:
            print(f"✅ {nome}: {valor_atual}")
        else:
            print(f"❌ {nome}: {valor_atual} (esperado: {valor_esperado})")
            erros += 1

    # Testa cálculos críticos
    print("\n🧮 VERIFICAÇÃO DE CÁLCULOS:")
    print("-" * 50)

    tick_size = config.get("contrato", {}).get("tick_size", 0.2)
    ticks_por_ponto = config.get("contrato", {}).get("ticks_por_ponto", 10000)
    sl_points = config.get("sl_points", 90)
    tp_points = config.get("tp_points", 35)

    # Cálculos WIN
    sl_ticks = sl_points * ticks_por_ponto  # 90 * 10000 = 900000
    tp_ticks = tp_points * ticks_por_ponto  # 35 * 10000 = 350000

    print(f"✅ SL: {sl_points} pontos = {sl_ticks:,} ticks")
    print(f"✅ TP: {tp_points} pontos = {tp_ticks:,} ticks")
    print(f"✅ Tick Size: {tick_size}")
    print(f"✅ Ticks por Ponto: {ticks_por_ponto:,}")

    # Verifica se os valores estão na faixa correta
    if sl_ticks != 900000:
        print(f"❌ ERRO: SL ticks incorreto: {sl_ticks} (esperado: 900000)")
        erros += 1

    if tp_ticks != 350000:
        print(f"❌ ERRO: TP ticks incorreto: {tp_ticks} (esperado: 350000)")
        erros += 1

    # Testa arquivos necessários
    print("\n📁 VERIFICAÇÃO DE ARQUIVOS:")
    print("-" * 50)

    arquivos_necessarios = [
        "monstro_unificado_v2.py",
        "config_win_v2.json",
        "EA_BookData_Universal.mq5",
        "iniciar_monstro_win_v2.bat",
        "README_WIN_V2.md"
    ]

    for arquivo in arquivos_necessarios:
        if os.path.exists(arquivo):
            print(f"✅ {arquivo}")
        else:
            print(f"❌ {arquivo} - NÃO ENCONTRADO")
            erros += 1

    # Resultado final
    print("\n" + "=" * 50)
    if erros == 0:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Sistema WIN v2 está configurado corretamente")
        print("🚀 Pronto para operar Mini Índice")
        return True
    else:
        print(f"❌ {erros} ERRO(S) ENCONTRADO(S)")
        print("🔧 Corrija os problemas antes de iniciar o sistema")
        return False


def mostrar_comparacao():
    """Mostra comparação entre WDO e WIN."""
    print("\n📊 COMPARAÇÃO WDO vs WIN:")
    print("=" * 60)
    print(f"{'Aspecto':<20} {'WDO (Principal)':<20} {'WIN (v2)':<20}")
    print("-" * 60)
    print(f"{'Tick Size':<20} {'0.5':<20} {'0.2':<20}")
    print(f"{'Ticks/Ponto':<20} {'1.000':<20} {'10.000':<20}")
    print(f"{'Volume Padrão':<20} {'1 contrato':<20} {'5 contratos':<20}")
    print(f"{'SL':<20} {'5 pontos':<20} {'90 pontos':<20}")
    print(f"{'TP':<20} {'10 pontos':<20} {'35 pontos':<20}")
    print(f"{'Magic Number':<20} {'123456':<20} {'123457':<20}")
    print(f"{'Port Dashboard':<20} {'5001':<20} {'5002':<20}")
    print(f"{'Log File':<20} {'monstro.log':<20} {'monstro_v2.log':<20}")
    print(f"{'Modelo':<20} {'modelo_monstro.h5':<20} {'modelo_monstro_win.h5':<20}")


if __name__ == "__main__":
    print("🤖 MONSTRO WIN V2 - TESTE DE CONFIGURAÇÃO")
    print("Verificando se o sistema está pronto para operar Mini Índice...")
    print()

    sucesso = testar_configuracao_win()
    mostrar_comparacao()

    if sucesso:
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("1. Abra o MetaTrader 5")
        print("2. Compile o EA_BookData_Universal.mq5")
        print("3. Adicione o EA em um gráfico WIN (ex: WINF25)")
        print("4. Execute: iniciar_monstro_win_v2.bat")
        print("5. Acesse dashboard: http://localhost:5002")
        sys.exit(0)
    else:
        print("\n🔧 CORRIJA OS PROBLEMAS ANTES DE CONTINUAR")
        sys.exit(1)
