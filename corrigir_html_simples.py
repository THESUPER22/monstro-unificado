#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simples para corrigir o HTML quebrado
"""


def corrigir_html():
    """Corrige o HTML que foi quebrado."""

    # Lê o arquivo
    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        codigo = f.read()

    # Corrige as tags HTML mais comuns que foram quebradas
    codigo = codigo.replace('< html >', '<html>')
    codigo = codigo.replace('< /html >', '</html>')
    codigo = codigo.replace('< head >', '<head>')
    codigo = codigo.replace('< /head >', '</head>')
    codigo = codigo.replace('< title >', '<title>')
    codigo = codigo.replace('< /title >', '</title>')
    codigo = codigo.replace('< body >', '<body>')
    codigo = codigo.replace('< /body >', '</body>')
    codigo = codigo.replace('< style >', '<style>')
    codigo = codigo.replace('< /style >', '</style>')
    codigo = codigo.replace('< /script >', '</script>')
    codigo = codigo.replace('< div', '<div')
    codigo = codigo.replace('< /div >', '</div>')
    codigo = codigo.replace('< h1 >', '<h1>')
    codigo = codigo.replace('< /h1 >', '</h1>')
    codigo = codigo.replace('< h2 >', '<h2>')
    codigo = codigo.replace('< /h2 >', '</h2>')
    codigo = codigo.replace('< h3 >', '<h3>')
    codigo = codigo.replace('< /h3 >', '</h3>')
    codigo = codigo.replace('< p >', '<p>')
    codigo = codigo.replace('< /p >', '</p>')
    codigo = codigo.replace('< button', '<button')
    codigo = codigo.replace('< /button >', '</button>')

    # Corrige cores CSS
    codigo = codigo.replace('# ddd', '#ddd')
    codigo = codigo.replace('# 333', '#333')
    codigo = codigo.replace('# 007bff', '#007bff')
    codigo = codigo.replace('# fff', '#fff')
    codigo = codigo.replace('# 28a745', '#28a745')
    codigo = codigo.replace('# dc3545', '#dc3545')
    codigo = codigo.replace('# ffc107', '#ffc107')
    codigo = codigo.replace('# 6c757d', '#6c757d')
    codigo = codigo.replace('# 17a2b8', '#17a2b8')
    codigo = codigo.replace('# f8f9fa', '#f8f9fa')
    codigo = codigo.replace('# e9ecef', '#e9ecef')
    codigo = codigo.replace('# 000', '#000')

    # Salva o arquivo corrigido
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        f.write(codigo)

    print("HTML corrigido com sucesso!")


if __name__ == "__main__":
    corrigir_html()
