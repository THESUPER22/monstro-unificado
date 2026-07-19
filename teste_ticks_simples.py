#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples da implementação de ticks
"""

import os
import sys


def testar_sintaxe():
    """Testa se o arquivo tem erros de sintaxe."""
    print("Testando sintaxe do arquivo...")

    try:
        with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
            codigo = f.read()

        # Testa compilação
        compile(codigo, "mostro _unificado_copia_do_v2.py", 'exec')
        print("OK - Sintaxe correta, nenhum erro de compilacao")
        return True

    except SyntaxError as e:
        print(f"ERRO de sintaxe na linha {e.lineno}: {e.msg}")
        print(f"   Texto: {e.text}")
        return False
    except Exception as e:
        print(f"ERRO ao ler arquivo: {e}")
        return False


def testar_estrutura_codigo():
    """Testa a estrutura do código."""
    print("\nTestando estrutura do codigo...")

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        codigo = f.read()

    # Testa se as classes foram implementadas
    classes_esperadas = [
        'ColetorTicksInteligente',
        'TrailingStopInteligente',
        'BalanceadorOperacoes',
        'DetectorModoMercado',
        'CircuitBreakerEssencial',
        'SaidaInteligentePositions'
    ]

    classes_encontradas = []
    classes_faltando = []

    for classe in classes_esperadas:
        if f'class {classe}' in codigo:
            classes_encontradas.append(classe)
        else:
            classes_faltando.append(classe)

    print(f"Classes encontradas: {', '.join(classes_encontradas)}")
    if classes_faltando:
        print(f"Classes faltando: {', '.join(classes_faltando)}")

    # Testa se as funções principais existem
    funcoes_esperadas = [
        'obter_dados_mercado',
        'salvar_experiencia_csv',
        'coletar_ticks_recentes'
    ]

    funcoes_encontradas = []
    funcoes_faltando = []

    for funcao in funcoes_esperadas:
        if f'def {funcao}' in codigo or f'{funcao}(' in codigo:
            funcoes_encontradas.append(funcao)
        else:
            funcoes_faltando.append(funcao)

    print(f"Funcoes encontradas: {', '.join(funcoes_encontradas)}")
    if funcoes_faltando:
        print(f"Funcoes faltando: {', '.join(funcoes_faltando)}")

    # Testa se as novas features estão no código
    features_ticks = ['direcao_fluxo', 'intensidade_ticks', 'aceleracao_preco']
    features_encontradas = []

    for feature in features_ticks:
        if feature in codigo:
            features_encontradas.append(feature)

    print(f"Features de ticks encontradas: {', '.join(features_encontradas)}")

    return len(classes_faltando) == 0 and len(funcoes_faltando) == 0 and len(features_encontradas) == 3


def testar_configuracoes():
    """Testa se as configurações foram atualizadas."""
    print("\nTestando configuracoes...")

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        codigo = f.read()

    # Testa N_FEATURES
    if 'N_FEATURES = config.get("aprendizado", {}).get("n_features", 14)' in codigo:
        print("OK - N_FEATURES atualizado para 14")
        n_features_ok = True
    else:
        print("ERRO - N_FEATURES nao foi atualizado")
        n_features_ok = False

    # Testa colunas esperadas
    if 'direcao_fluxo' in codigo and 'intensidade_ticks' in codigo and 'aceleracao_preco' in codigo:
        print("OK - Novas colunas adicionadas")
        colunas_ok = True
    else:
        print("ERRO - Novas colunas nao encontradas")
        colunas_ok = False

    # Testa configurações de ticks
    configs_ticks = ['TICKS_ATIVO', 'TICKS_CACHE_TTL', 'TICKS_QUANTIDADE']
    configs_encontradas = []

    for config in configs_ticks:
        if config in codigo:
            configs_encontradas.append(config)

    print(f"Configuracoes de ticks: {', '.join(configs_encontradas)}")
    configs_ok = len(configs_encontradas) >= 2

    return n_features_ok and colunas_ok and configs_ok


def main():
    """Função principal de teste."""
    print("TESTE COMPLETO DO MONSTRO COM TICKS")
    print("=" * 50)

    testes_passaram = []

    # Teste 1: Sintaxe
    if testar_sintaxe():
        testes_passaram.append("Sintaxe")

    # Teste 2: Estrutura
    if testar_estrutura_codigo():
        testes_passaram.append("Estrutura")

    # Teste 3: Configurações
    if testar_configuracoes():
        testes_passaram.append("Configuracoes")

    print(f"\nRESULTADO FINAL:")
    print(f"Testes que passaram: {', '.join(testes_passaram)}")
    print(
        f"Taxa de sucesso: {len(testes_passaram)}/3 ({len(testes_passaram)*33:.0f}%)")

    if len(testes_passaram) == 3:
        print("\nTODOS OS TESTES PASSARAM!")
        print("Codigo pronto para uso no monstro_unificado_v2.py")
        return True
    else:
        print(f"\n{3-len(testes_passaram)} teste(s) falharam")
        print("Codigo precisa de correcoes antes do uso")
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
