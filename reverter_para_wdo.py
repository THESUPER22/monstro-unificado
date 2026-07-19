#!/usr/bin/env python3
# Script para reverter do Bitcoin para WDO

import shutil
import os

def reverter():
    print("🔄 Revertendo para WDO...")

    backup_dir = "backup_wdo_20250714_155743"

    arquivos = ["monstro_unificado.py", "config.json", "modelo_monstro.h5"]

    for arquivo in arquivos:
        backup_path = os.path.join(backup_dir, arquivo)
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, arquivo)
            print(f"✅ Restaurado: {arquivo}")

    print("✅ Reversão concluída! WDO restaurado.")

if __name__ == "__main__":
    reverter()
