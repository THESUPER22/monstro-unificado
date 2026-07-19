#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 INTEGRAÇÃO DOS FILTROS EVOLUTIVOS COM O MONSTRO
Integra o sistema híbrido de evolução no código principal
"""

import logging
import os
import sys

from sistema_evolucao_hibrido import SistemaEvolucaoHibrido


def integrar_sistema_evolutivo():
    """Integra o sistema evolutivo híbrido com o Monstro."""
    print("🧬 INTEGRANDO SISTEMA DE EVOLUÇÃO HÍBRIDO")
    print("="*50)

    # Inicializa sistema híbrido
    sistema = SistemaEvolucaoHibrido()

    # Mostra status atual
    print(sistema.gerar_relatorio_status())

    # Executa ciclo de evolução
    print("\n🔄 Executando ciclo de evolução...")
    sucesso = sistema.executar_ciclo_evolucao()

    if sucesso:
        print("✅ Ciclo de evolução executado com sucesso!")
        print("\n" + sistema.gerar_relatorio_status())
    else:
        print("❌ Erro no ciclo de evolução")

    return sistema


def exemplo_uso_filtros():
    """Exemplo de como usar os filtros no código do Monstro."""
    print("\n📝 EXEMPLO DE USO NO CÓDIGO PRINCIPAL:")
    print("="*50)

    # Inicializa sistema
    sistema = SistemaEvolucaoHibrido()

    # Exemplo de contexto de trading
    contexto_exemplo = {
        'confianca': 0.72,
        'entropia_book': 0.45,
        'spread': 1.2,
        'volume_book': 350,
        'rsi_14': 45,
        'volatility': 2.5
    }

    # Verifica se deve executar trade
    deve_executar, motivo = sistema.deve_executar_trade(contexto_exemplo)

    print(f"Contexto de exemplo: {contexto_exemplo}")
    print(f"Deve executar trade: {deve_executar}")
    print(f"Motivo: {motivo}")

    # Mostra filtros ativos
    filtros = sistema.obter_filtros_finais()
    print(f"\nFiltros ativos:")
    for chave, valor in filtros.items():
        print(f"  {chave}: {valor}")


def gerar_codigo_integracao():
    """Gera código para integrar no monstro_unificado.py"""
    codigo = '''
# ===== INTEGRAÇÃO DO SISTEMA EVOLUTIVO HÍBRIDO =====
# Adicione estas linhas no início do monstro_unificado.py

from sistema_evolucao_hibrido import SistemaEvolucaoHibrido

# Inicializa sistema evolutivo (adicionar após outras inicializações)
sistema_evolutivo = SistemaEvolucaoHibrido()

# Função para verificar se deve executar trade (substituir lógica existente)
def deve_executar_trade_evolutivo(contexto):
    """Verifica se deve executar trade usando filtros evolutivos."""
    return sistema_evolutivo.deve_executar_trade(contexto)

# Função para executar evolução periódica (chamar a cada X operações)
def executar_evolucao_periodica():
    """Executa ciclo de evolução do sistema."""
    global sistema_evolutivo
    try:
        sistema_evolutivo.executar_ciclo_evolucao()
        logging.info("🧬 Evolução executada com sucesso")
    except Exception as e:
        logging.error(f"❌ Erro na evolução: {e}")

# ===== EXEMPLO DE USO NO LOOP PRINCIPAL =====
# Substitua a lógica de decisão existente por:

# No loop principal, antes de decidir ação:
contexto_atual = {
    'confianca': probabilidade_ia,
    'entropia_book': entropia_calculada,
    'spread': spread_atual,
    'volume_book': volume_book_total,
    'rsi_14': rsi_atual,
    'volatility': atr_atual
}

# Verifica filtros evolutivos
deve_operar, motivo_filtro = deve_executar_trade_evolutivo(contexto_atual)

if not deve_operar:
    logging.info(
        f"🚫 Trade bloqueado pelos filtros evolutivos: {motivo_filtro}")
    continue  # Pula para próxima iteração

# Se passou nos filtros, executa a lógica normal de trading...

# ===== EVOLUÇÃO PERIÓDICA =====
# Adicione no final do loop principal (a cada 50 operações):

contador_operacoes += 1
if contador_operacoes % 50 == 0:
    executar_evolucao_periodica()
'''

    print("\n💻 CÓDIGO PARA INTEGRAÇÃO:")
    print("="*50)
    print(codigo)

    # Salva código em arquivo
    with open("codigo_integracao_evolutivo.txt", "w", encoding="utf-8") as f:
        f.write(codigo)

    print("\n✅ Código de integração salvo em: codigo_integracao_evolutivo.txt")


def main():
    """Função principal de integração."""
    print("🤖 INTEGRAÇÃO DE FILTROS EVOLUTIVOS - MONSTRO DAS NEGOCIAÇÕES")
    print("="*60)

    try:
        # 1. Integra sistema
        sistema = integrar_sistema_evolutivo()

        # 2. Mostra exemplo de uso
        exemplo_uso_filtros()

        # 3. Gera código de integração
        gerar_codigo_integracao()

        print("\n🎉 INTEGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Revisar o código de integração gerado")
        print("2. Integrar no monstro_unificado.py")
        print("3. Testar com dados reais")
        print("4. Monitorar evolução dos filtros")

        return True

    except Exception as e:
        print(f"\n❌ ERRO NA INTEGRAÇÃO: {e}")
        return False


if __name__ == "__main__":
    main()
    main()
