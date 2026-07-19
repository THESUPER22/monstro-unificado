#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para comentar toda a seção Flask
"""


def comentar_flask():
    """Comenta toda a seção Flask para permitir teste do código principal."""

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    linhas_comentadas = []
    dentro_flask = False

    for i, linha in enumerate(linhas):
        # Detecta início da seção Flask
        if '# region [Web Server]' in linha:
            dentro_flask = True
            linhas_comentadas.append(
                '# region [Web Server] - COMENTADO PARA TESTE\n')
            continue

        # Detecta fim da seção Flask
        if dentro_flask and '# endregion' in linha and i > 3275:
            dentro_flask = False
            linhas_comentadas.append(
                '# endregion - FIM SEÇÃO FLASK COMENTADA\n')
            continue

        # Comenta linhas da seção Flask
        if dentro_flask:
            if linha.strip():  # Não comenta linhas vazias
                linhas_comentadas.append('# ' + linha)
            else:
                linhas_comentadas.append(linha)
        else:
            linhas_comentadas.append(linha)

    # Salva arquivo com Flask comentado
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        f.writelines(linhas_comentadas)

    print("Seção Flask comentada com sucesso!")
    return True


if __name__ == "__main__":
    comentar_flask()
