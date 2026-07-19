#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil


def restore_backup():
    """Restaura o backup de sintaxe."""

    backup_file = "monstro_unificado_v2.py.backup_syntax"
    target_file = "monstro_unificado_v2.py"

    if os.path.exists(backup_file):
        shutil.copy2(backup_file, target_file)
        print(f"✅ Backup restaurado: {backup_file} -> {target_file}")
        return True
    else:
        print(f"❌ Backup não encontrado: {backup_file}")
        return False


if __name__ == "__main__":
    restore_backup()
