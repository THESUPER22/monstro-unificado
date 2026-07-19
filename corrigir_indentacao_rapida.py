#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir rapidamente problemas de indentação
"""


def corrigir_indentacao_rapida():
    """Corrige problemas de indentação de forma rápida."""

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    linhas_corrigidas = []

    for i, linha in enumerate(linhas):
        linha_original = linha.rstrip()
        linha_stripped = linha.strip()

        # Pula linhas vazias
        if not linha_stripped:
            linhas_corrigidas.append('')
            continue

        # Mantém comentários como estão
        if linha_stripped.startswith('#'):
            linhas_corrigidas.append(linha_original)
            continue

        # Detecta nível de indentação necessário
        if linha_stripped.startswith('class '):
            # Classe no nível global
            linhas_corrigidas.append(linha_stripped)
        elif linha_stripped.startswith('def ') and i > 0:
            # Verifica se é método de classe ou função global
            # Procura por 'class' nas linhas anteriores
            eh_metodo = False
            for j in range(i-1, max(0, i-20), -1):
                linha_anterior = linhas[j].strip()
                if linha_anterior.startswith('class '):
                    eh_metodo = True
                    break
                elif linha_anterior.startswith('def ') and not linha_anterior.startswith('    def'):
                    break

            if eh_metodo:
                linhas_corrigidas.append('    ' + linha_stripped)
            else:
                linhas_corrigidas.append(linha_stripped)
        elif linha_stripped.startswith(('import ', 'from ', '# region', '# endregion')):
            # Imports e regiões no nível global
            linhas_corrigidas.append(linha_stripped)
        else:
            # Conteúdo normal - detecta contexto
            # Verifica se está dentro de função ou classe
            dentro_funcao = False
            dentro_classe = False

            for j in range(i-1, -1, -1):
                linha_anterior = linhas[j].strip()
                if linha_anterior.startswith('def '):
                    dentro_funcao = True
                    # Verifica se é método de classe
                    if linhas[j].startswith('    def'):
                        dentro_classe = True
                    break
                elif linha_anterior.startswith('class '):
                    dentro_classe = True
                    break
                elif linha_anterior and not linha_anterior.startswith(('#', 'import', 'from')):
                    continue

            # Aplica indentação apropriada
            if dentro_funcao and dentro_classe:
                linhas_corrigidas.append('        ' + linha_stripped)


lif dentro_funcao or dentro_classe:
                linhas_corrigidas.append('    ' + linha_stripped)
            else:
                linhas_corrigidas.append(linha_stripped)

    # Salva arquivo corrigido
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        for linha in linhas_corrigidas:
            f.write(linha + '\n')

    print("Indentação corrigida rapidamente!")
    return True

if __name__ == "__main__":
    corrigir_indentacao_rapida()
