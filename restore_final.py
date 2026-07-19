#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil


def restore_final():
    """Restaura o backup final."""

    backup_file = "monstro_unificado_v2.py.backup_syntax"
    target_file = "monstro_unificado_v2.py"

    try:
        if os.path.exists(backup_file):
            # Lê o backup
            with open(backup_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Escreve no arquivo principal
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ Backup restaurado com sucesso!")
            print(f"📁 {backup_file} -> {target_file}")

            # Testa a sintaxe
            import ast
            try:
                ast.parse(content)
                print("✅ SINTAXE VERIFICADA - ARQUIVO OK!")
                return True
            except SyntaxError as e:
                print(f"❌ ERRO DE SINTAXE: {e}")
                return False
        else:
            print(f"❌ Backup não encontrado: {backup_file}")
            return False
    except Exception as e:
        print(f"❌ Erro ao restaurar: {e}")
        return False


if __name__ == "__main__":
    restore_final()
