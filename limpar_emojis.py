#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para remover emojis problemáticos do código
"""

import re


def limpar_emojis():
    """Remove emojis que causam problemas de sintaxe."""

    # Lê o arquivo
    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        codigo = f.read()

    # Lista de substituições de emojis problemáticos
    substituicoes = [
        ('🎯', ''),
        ('✅', ''),
        ('❌', ''),
        ('⚠️', ''),
        ('🚀', ''),
        ('🛡️', ''),
        ('🚑', ''),
        ('🔥', ''),
        ('⚡', ''),
        ('💀', ''),
        ('✂️', ''),
        ('🧹', ''),
        ('🔄', ''),
        ('📊', ''),
        ('📡', ''),
        ('🐌', ''),
        ('🚨', ''),
        ('🚪', ''),
        ('📈', ''),
        ('⚖️', ''),
        ('🎲', ''),
        ('🔒', ''),
        ('📅', ''),
        ('📘', ''),
        ('🎮', ''),
        ('🔚', ''),
        ('🎊', ''),
        ('🎉', ''),
        ('🏁', ''),
        ('🎪', ''),
        ('🎭', ''),
        ('🎨', ''),
        ('🎬', ''),
        ('🎤', ''),
        ('🎧', ''),
        ('🎵', ''),
        ('🎶', ''),
        ('🎸', ''),
        ('🎹', ''),
        ('🎺', ''),
        ('🎻', ''),
        ('🥁', ''),
        ('🎼', ''),
        ('🎵', ''),
        ('🎶', ''),
        ('🎙️', ''),
        ('🎚️', ''),
        ('🎛️', ''),
        ('🎤', ''),
        ('🎧', ''),
        ('📻', ''),
        ('🎷', ''),
        ('🪗', ''),
        ('🪘', ''),
        ('🎸', ''),
        ('🪕', ''),
        ('🎺', ''),
        ('🎻', ''),
        ('🪄', ''),
        ('🔮', ''),
        ('🪬', ''),
        ('🧿', ''),
        ('🪆', ''),
        ('🎎', ''),
        ('🎏', ''),
        ('🎐', ''),
        ('🎑', ''),
        ('🧧', ''),
        ('🎀', ''),
        ('🎁', ''),
        ('🎗️', ''),
        ('🎟️', ''),
        ('🎫', ''),
        ('🎖️', ''),
        ('🏆', ''),
        ('🏅', ''),
        ('🥇', ''),
        ('🥈', ''),
        ('🥉', ''),
        ('⚽', ''),
        ('⚾', ''),
        ('🥎', ''),
        ('🏀', ''),
        ('🏐', ''),
        ('🏈', ''),
        ('🏉', ''),
        ('🎾', ''),
        ('🥏', ''),
        ('🎳', ''),
        ('🏏', ''),
        ('🏑', ''),
        ('🏒', ''),
        ('🥍', ''),
        ('🏓', ''),
        ('🏸', ''),
        ('🥊', ''),
        ('🥋', ''),
        ('🥅', ''),
        ('⛳', ''),
        ('⛸️', ''),
        ('🎣', ''),
        ('🤿', ''),
        ('🎽', ''),
        ('🎿', ''),
        ('🛷', ''),
        ('🥌', ''),
    ]

    # Aplica as substituições
    for emoji, substituto in substituicoes:
        codigo = codigo.replace(emoji, substituto)

    # Remove espaços duplos que podem ter ficado
    codigo = re.sub(r'  +', ' ', codigo)

    # Remove linhas vazias excessivas
    codigo = re.sub(r'\n\n\n+', '\n\n', codigo)

    # Salva o arquivo limpo
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        f.write(codigo)

    print("Emojis removidos com sucesso!")


if __name__ == "__main__":
    limpar_emojis()
