#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para reparar completamente o arquivo
"""

import re


def reparar_arquivo_completo():
    """Repara todo o arquivo corrigindo indentação e estrutura."""

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Divide em linhas
    linhas = conteudo.split('\n')
    linhas_reparadas = []

    nivel_indentacao = 0
    dentro_classe = False
    dentro_funcao = False
    dentro_string_multiline = False
    string_delimiter = None

    i = 0
    while i < len(linhas):
        linha = linhas[i]
        linha_stripped = linha.strip()

        # Detecta strings multiline
        if '"""' in linha_stripped and not dentro_string_multiline:
            dentro_string_multiline = True
            string_delimiter = '"""'
            linhas_reparadas.append(linha)
            i += 1
            continue
        elif '"""' in linha_stripped and dentro_string_multiline and string_delimiter == '"""':
            dentro_string_multiline = False
            string_delimiter = None
            linhas_reparadas.append(linha)
            i += 1
            continue
        elif "'''" in linha_stripped and not dentro_string_multiline:
            dentro_string_multiline = True
            string_delimiter = "'''"
            linhas_reparadas.append(linha)
            i += 1
            continue
        elif "'''" in linha_stripped and dentro_string_multiline and string_delimiter == "'''":
            dentro_string_multiline = False
            string_delimiter = None
            linhas_reparadas.append(linha)
            i += 1
            continue

        # Se estiver dentro de string multiline, mantém como está
        if dentro_string_multiline:
            linhas_reparadas.append(linha)
            i += 1
            continue

        # Pula linhas vazias e comentários
        if not linha_stripped or linha_stripped.startswith('#'):
            linhas_reparadas.append(linha)
            i += 1
            continue

        # Detecta início de classe
        if linha_stripped.startswith('class '):
            dentro_classe = True
            dentro_funcao = False
            nivel_indentacao = 0
            linhas_reparadas.append(linha_stripped)
            i += 1
            continue

        # Detecta função/método
        if linha_stripped.startswith('def '):
            if dentro_classe:
                dentro_funcao = True
                nivel_indentacao = 1
                linhas_reparadas.append('    ' + linha_stripped)
            else:
                dentro_funcao = True
                dentro_classe = False
                nivel_indentacao = 0
                linhas_reparadas.append(linha_stripped)
            i += 1
            continue

        # Detecta fim de classe/função (nova definição no nível global)
        if (linha_stripped.startswith(('class ', 'def ')) and
            not linha.startswith(('    ', '\t')) and
                (dentro_classe or dentro_funcao)):
            dentro_classe = False
            dentro_funcao = False
            nivel_indentacao = 0

        # Aplica indentação baseada no contexto
        if dentro_funcao and dentro_classe:
            # Conteúdo de método de classe
            linhas_reparadas.append('        ' + linha_stripped)
        elif dentro_funcao and not dentro_classe:
            # Conteúdo de função normal
            linhas_reparadas.append('    ' + linha_stripped)
        elif dentro_classe and not dentro_funcao:
            # Atributo de classe ou docstring
            linhas_reparadas.append('    ' + linha_stripped)
        else:
            # Código no nível global
            linhas_reparadas.append(linha_stripped)

        i += 1

    # Reconstrói o arquivo
    conteudo_reparado = '\n'.join(linhas_reparadas)

    # Salva o arquivo reparado
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        f.write(conteudo_reparado)

    print("Arquivo reparado completamente!")
    return True


if __name__ == "__main__":
    reparar_arquivo_completo()
