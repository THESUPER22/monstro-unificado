#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast


def test_syntax():
    try:
        with open('monstro_unificado_v2.py', 'r', encoding='utf-8') as f:
            content = f.read()

        ast.parse(content)
        print("✅ SINTAXE OK!")
        return True
    except SyntaxError as e:
        print(f"❌ ERRO DE SINTAXE: {e}")
        print(f"Linha {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False


if __name__ == "__main__":
    test_syntax()
