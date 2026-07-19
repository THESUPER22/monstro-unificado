#!/usr/bin/env python3
"""Script para testar se o treinamento do Monstro está funcionando"""

import json
import os
from datetime import datetime


def verificar_configuracao():
    print("Verificando configuracao...")
    try:
        with open('config_win_v2.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        horario_limite = config.get('horarios', {}).get(
            'limite_ordens', '18:15')
        print(f"Horario limite ordens: {horario_limite}")
        return horario_limite == "23:59"
    except Exception as e:
        print(f"Erro: {e}")
        return False


def main():
    print("TESTE DE TREINAMENTO DO MONSTRO")
    print("=" * 40)

    if verificar_configuracao():
        print("Configuracao OK para testes!")
    else:
        print("Configuracao precisa ajustar")

    print("\nProximos passos:")
    print("1. Inicie: python monstro_unificado_v2.py")
    print("2. Observe logs de treinamento")


if __name__ == "__main__":
    main()
