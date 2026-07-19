#!/usr/bin/env python3
"""
Correção final e definitiva dos erros de indentação
"""


def corrigir_arquivo_final():
    """Correção final do arquivo."""

    with open('monstro_unificado_v2.py', 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    linhas_corrigidas = []
    i = 0

    while i < len(linhas):
        linha = linhas[i]
        linha_limpa = linha.strip()

        # Pula linhas vazias e comentários
        if not linha_limpa or linha_limpa.startswith('#'):
            linhas_corrigidas.append(linha)
            i += 1
            continue

        # Detecta e corrige problemas específicos
        if i > 0:
            linha_anterior = linhas[i-1].strip()

            # Se linha anterior termina com : e linha atual não está indentada
            if linha_anterior.endswith(':') and linha_limpa and not linha.startswith('    '):
                # Calcula indentação necessária
                indentacao_anterior = len(
                    linhas[i-1]) - len(linhas[i-1].lstrip())

                # Se é uma definição de classe ou função no nível raiz
                if linha_anterior.startswith('class ') or (linha_anterior.startswith('def ') and indentacao_anterior == 0):
                    nova_indentacao = 4
                # Se é um método de classe
                elif linha_anterior.startswith('    def '):
                    nova_indentacao = 8
                # Outros casos
                else:
                    nova_indentacao = indentacao_anterior + 4

                linha = ' ' * nova_indentacao + linha_limpa + '\n'

        linhas_corrigidas.append(linha)
        i += 1

    # Salva arquivo corrigido
    with open('monstro_unificado_v2.py', 'w', encoding='utf-8') as f:
        f.writelines(linhas_corrigidas)

    print("✅ Correção final aplicada!")


if __name__ == "__main__":
    corrigir_arquivo_final()
