#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re


def fix_duplicate_docstrings(filename):
    """Remove docstrings duplicadas consecutivas."""

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Padrão para encontrar docstrings duplicadas na mesma linha ou linhas consecutivas
    patterns = [
        # Docstrings duplicadas na mesma linha
        r'("""[^"]*""")\s*("""[^"]*""")',
        # Docstrings duplicadas em linhas consecutivas
        r'("""[^"]*"""\n\s*)("""[^"]*""")',
    ]

    original_content = content

    for pattern in patterns:
        # Substitui duplicações por apenas a primeira ocorrência
        content = re.sub(pattern, r'\1', content, flags=re.MULTILINE)

    # Verifica se houve mudanças
    if content != original_content:
        # Faz backup
        with open(f"{filename}.backup_docstrings", 'w', encoding='utf-8') as f:
            f.write(original_content)

        # Salva o arquivo corrigido
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Docstrings duplicadas corrigidas em {filename}")
        print(f"📁 Backup salvo como {filename}.backup_docstrings")
        return True
    else:
        print(f"ℹ️ Nenhuma docstring duplicada encontrada em {filename}")
        return False


if __name__ == "__main__":
    fix_duplicate_docstrings("monstro_unificado_v2.py")
