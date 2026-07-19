#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de configuração do sistema
"""


def testar_dependencias():
    """Testa se as dependências estão instaladas"""
    print("=" * 50)
    print("TESTE DE CONFIGURAÇÃO DO SISTEMA")
    print("=" * 50)

    # Teste MetaTrader5
    try:
        import MetaTrader5
        print("✅ MetaTrader5: OK")
    except ImportError:
        print("⚠️ MetaTrader5: Não encontrado")

    # Teste TensorFlow
    try:
        import tensorflow as tf
        print(f"✅ TensorFlow: OK (versão {tf.__version__})")
    except ImportError:
        print("⚠️ TensorFlow: Não encontrado")

    # Teste outras dependências
    libs = [
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("sklearn", "Scikit-learn"),
        ("flask", "Flask"),
        ("requests", "Requests"),
        ("threading", "Threading"),
        ("json", "JSON"),
        ("datetime", "DateTime"),
        ("os", "OS"),
        ("sys", "System")
    ]

    for lib, nome in libs:
        try:
            __import__(lib)
            print(f"✅ {nome}: OK")
        except ImportError:
            print(f"⚠️ {nome}: Não encontrado")

    print("=" * 50)
    print("TESTE CONCLUÍDO!")
    print("=" * 50)


if __name__ == "__main__":
    testar_dependencias()
