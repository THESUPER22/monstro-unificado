#!/usr/bin/env python3
"""
Script para corrigir problemas de indentação no arquivo monstro_unificado_copia_do_v2.py
"""

import re


def corrigir_indentacao(arquivo_entrada, arquivo_saida):
    """Corrige problemas de indentação em arquivo Python"""

    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    linhas_corrigidas = []

    for i, linha in enumerate(linhas):
        linha_original = linha

        # Remove espaços em branco no final da linha
        linha = linha.rstrip() + '\n'

        # Corrige indentação incorreta - substitui tabs por 4 espaços
        linha = linha.expandtabs(4)

        # Detecta e corrige problemas específicos de indentação
        if linha.strip():  # Se a linha não está vazia
            # Conta espaços no início
            espacos_inicio = len(linha) - len(linha.lstrip())

            # Se a linha anterior termina com ':' e esta linha não está indentada corretamente
            if i > 0 and linhas[i-1].strip().endswith(':'):
                if espacos_inicio == 0 and linha.strip() and not linha.strip().startswith('#'):
                    # Adiciona indentação de 4 espaços
                    linha = '    ' + linha.lstrip()
                elif espacos_inicio > 0 and espacos_inicio % 4 != 0:
                    # Corrige indentação para múltiplo de 4
                    novo_nivel = ((espacos_inicio + 3) // 4) * 4
                    linha = ' ' * novo_nivel + linha.lstrip()

        linhas_corrigidas.append(linha)

    # Segunda passada para corrigir problemas específicos
    linhas_finais = []
    for i, linha in enumerate(linhas_corrigidas):
        # Corrige linhas que começam com espaços mas deveriam estar mais indentadas
        if linha.strip() and not linha.startswith('    ') and not linha.startswith('#'):
            # Verifica se é uma continuação de bloco
            if i > 0:
                linha_anterior = linhas_corrigidas[i-1].strip()
                if (linha_anterior.endswith(':') or
                    linha_anterior.endswith('\\') or
                        '(' in linha_anterior and ')' not in linha_anterior):
                    if not linha.startswith('    '):
                        linha = '    ' + linha.lstrip()

        linhas_finais.append(linha)

    # Salva arquivo corrigido
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        f.writelines(linhas_finais)

    print(f"Arquivo corrigido salvo como: {arquivo_saida}")


if __name__ == "__main__":
    corrigir_indentacao("mostro _unificado_copia_do_v2.py",
                        "mostro_unificado_corrigido.py")
