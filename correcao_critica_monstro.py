#!/usr/bin/env python3
"""
Correção crítica de indentação do monstro_unificado_v2.py
Abordagem manual para corrigir os erros mais críticos
"""

import re


def corrigir_arquivo():
    """Corrige os erros de indentação mais críticos."""

    # Lê o arquivo original
    with open('monstro_unificado_v2.py', 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Lista de correções específicas baseadas nos erros encontrados
    correcoes = [
        # Corrige problemas de indentação em blocos if/else/elif
        (r'^(\s*)if\s+.*:\s*\n(\s*)([^#\s])',
         r'\1if \2:\n\1    \3', re.MULTILINE),
        (r'^(\s*)elif\s+.*:\s*\n(\s*)([^#\s])',
         r'\1elif \2:\n\1    \3', re.MULTILINE),
        (r'^(\s*)else:\s*\n(\s*)([^#\s])', r'\1else:\n\1    \3', re.MULTILINE),
        (r'^(\s*)for\s+.*:\s*\n(\s*)([^#\s])',
         r'\1for \2:\n\1    \3', re.MULTILINE),
        (r'^(\s*)while\s+.*:\s*\n(\s*)([^#\s])',
         r'\1while \2:\n\1    \3', re.MULTILINE),

        # Corrige definições de função e classe
        (r'^(\s*)def\s+.*:\s*\n(\s*)([^#\s])',
         r'\1def \2:\n\1    \3', re.MULTILINE),
        (r'^(\s*)class\s+.*:\s*\n(\s*)([^#\s])',
         r'\1class \2:\n\1    \3', re.MULTILINE),
    ]

    # Aplica as correções
    conteudo_corrigido = conteudo
    for padrao, substituicao, flags in correcoes:
        conteudo_corrigido = re.sub(
            padrao, substituicao, conteudo_corrigido, flags=flags)

    # Correções específicas para problemas conhecidos
    linhas = conteudo_corrigido.split('\n')
    linhas_corrigidas = []

    i = 0
    while i < len(linhas):
        linha = linhas[i]
        linha_limpa = linha.strip()

        # Corrige linhas com indentação incorreta após dois pontos
        if i > 0 and linhas[i-1].strip().endswith(':'):
            if linha_limpa and not linha.startswith('    ') and not linha_limpa.startswith('#'):
                # Calcula indentação baseada na linha anterior
                indentacao_anterior = len(
                    linhas[i-1]) - len(linhas[i-1].lstrip())
                nova_indentacao = indentacao_anterior + 4
                linha = ' ' * nova_indentacao + linha_limpa

        linhas_corrigidas.append(linha)
        i += 1

    # Salva o arquivo corrigido
    conteudo_final = '\n'.join(linhas_corrigidas)

    with open('monstro_unificado_v2.py', 'w', encoding='utf-8') as f:
        f.write(conteudo_final)

    print("✅ Correções críticas aplicadas ao monstro_unificado_v2.py")


if __name__ == "__main__":
    corrigir_arquivo()
