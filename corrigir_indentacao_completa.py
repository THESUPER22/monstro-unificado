#!/usr/bin/env python3
"""
Script para corrigir todos os erros de indentação do monstro_unificado_v2.py
"""

import re


def corrigir_indentacao(arquivo_entrada, arquivo_saida):
    """Corrige problemas de indentação no arquivo Python."""

    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    linhas_corrigidas = []
    nivel_indentacao = 0
    dentro_classe = False
    dentro_funcao = False

    for i, linha in enumerate(linhas):
        linha_original = linha
        linha_limpa = linha.strip()

        # Pula linhas vazias e comentários
        if not linha_limpa or linha_limpa.startswith('#'):
            linhas_corrigidas.append(linha_original)
            continue

        # Detecta definições de classe
        if linha_limpa.startswith('class '):
            nivel_indentacao = 0
            dentro_classe = True
            dentro_funcao = False
            linhas_corrigidas.append(linha_limpa + '\n')
            continue

        # Detecta definições de função
        if linha_limpa.startswith('def '):
            if dentro_classe:
                nivel_indentacao = 1  # Método de classe
            else:
                nivel_indentacao = 0  # Função global
            dentro_funcao = True
            linhas_corrigidas.append(
                '    ' * nivel_indentacao + linha_limpa + '\n')
            continue

        # Detecta estruturas de controle
        if any(linha_limpa.startswith(palavra) for palavra in ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ']):
            if dentro_funcao:
                if dentro_classe:
                    nivel_base = 2  # Dentro de método de classe
                else:
                    nivel_base = 1  # Dentro de função global
            elif dentro_classe:
                nivel_base = 1  # Dentro de classe mas fora de método
            else:
                nivel_base = 0  # Código global

            # Conta níveis de indentação baseado em dois pontos anteriores
            nivel_atual = nivel_base
            for j in range(i-1, -1, -1):
                linha_anterior = linhas[j].strip()
                if linha_anterior.endswith(':') and not linha_anterior.startswith('#'):
                    nivel_atual += 1
                    break
                elif linha_anterior and not linha_anterior.startswith('#'):
                    break

            linhas_corrigidas.append('    ' * nivel_atual + linha_limpa + '\n')
            continue

        # Conteúdo normal
        if dentro_funcao:
            if dentro_classe:
                nivel_base = 2  # Dentro de método de classe
            else:
                nivel_base = 1  # Dentro de função global
        elif dentro_classe:
            nivel_base = 1  # Dentro de classe mas fora de método
        else:
            nivel_base = 0  # Código global

        # Ajusta nível baseado em estruturas de controle anteriores
        nivel_atual = nivel_base
        for j in range(i-1, -1, -1):
            linha_anterior = linhas[j].strip()
            if linha_anterior.endswith(':') and not linha_anterior.startswith('#'):
                if any(linha_anterior.startswith(palavra) for palavra in ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ']):
                    nivel_atual += 1
                break
            elif linha_anterior and not linha_anterior.startswith('#'):
                break

        linhas_corrigidas.append('    ' * nivel_atual + linha_limpa + '\n')

    # Salva arquivo corrigido
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.writelines(linhas_corrigidas)

    print(f"Arquivo corrigido salvo como: {arquivo_saida}")


if __name__ == "__main__":
    corrigir_indentacao("monstro_unificado_v2.py",
                        "monstro_unificado_v2_corrigido.py")
