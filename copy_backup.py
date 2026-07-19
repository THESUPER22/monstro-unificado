#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def copy_backup():
    """Copia o backup para o arquivo principal."""

    try:
        with open("monstro_unificado_v2.py.backup_syntax", 'r', encoding='utf-8') as f:
            content = f.read()

        with open("monstro_unificado_v2.py", 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ Backup restaurado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao restaurar backup: {e}")
        return False


if __name__ == "__main__":
    copy_backup()
