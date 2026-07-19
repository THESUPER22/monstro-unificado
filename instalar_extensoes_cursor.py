#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para instalar apenas as extensões essenciais do Cursor
"""

import os
import subprocess
import sys

def instalar_extensao(extensao, descricao):
    """Instala uma extensão do Cursor."""
    print(f"🔧 Instalando {descricao}...")
    try:
        result = subprocess.run(f"cursor --install-extension {extensao}",
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {descricao} instalado!")
        else:
            print(f"   ⚠️ Aviso: {descricao} - {result.stderr}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

def main():
    print("🚀 INSTALADOR DE EXTENSÕES ESSENCIAIS DO CURSOR")
    print("=" * 55)

    # Extensões essenciais
    extensoes = [
        ("MS-CEINTL.vscode-language-pack-pt-BR", "🇧🇷 Português Brasil"),
        ("ms-python.python", "🐍 Python"),
        ("ms-python.vscode-pylance", "🐍 Python Pylance"),
        ("ms-python.debugpy", "🐍 Python Debug"),
        ("ms-python.black-formatter", "🐍 Python Black Formatter"),
        ("ms-toolsai.jupyter", "📊 Jupyter Notebook"),
        ("eamodio.gitlens", "🔧 Git Lens"),
        ("PKief.material-icon-theme", "🎨 Material Icons"),
        ("dracula-theme.theme-dracula", "🎨 Dracula Theme"),
        ("mechatroner.rainbow-csv", "📈 Rainbow CSV"),
        ("streetsidesoftware.code-spell-checker", "🔍 Spell Checker"),
        ("streetsidesoftware.code-spell-checker-portuguese-brazil", "🇧🇷 Spell Checker PT-BR"),
        ("aaron-bond.better-comments", "💬 Better Comments")
    ]

    for extensao, descricao in extensoes:
        instalar_extensao(extensao, descricao)

    print("\n" + "=" * 55)
    print("✅ INSTALAÇÃO CONCLUÍDA!")
    print("=" * 55)
    print("🎉 Extensões essenciais do Cursor instaladas!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. 🔄 Reinicie o Cursor")
    print("2. 🇧🇷 Confirme idioma português")
    print("3. 🎨 Selecione tema Dracula")
    print("4. 🚀 Comece a usar!")

if __name__ == "__main__":
    main()
