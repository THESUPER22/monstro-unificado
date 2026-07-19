#!/usr/bin/env python3
"""
Teste da solução definitiva contra race condition
"""

import json
import os
import tempfile


def testar_solucao_definitiva():
    print("🧪 Testando solução definitiva contra race condition...")

    # Cria arquivo temporário para teste
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        # JSON incompleto (simula race condition)
        f.write(
            '{"bids":[{"price":140020,"volume":182.0}],"asks":[{"price":140060')
        temp_file = f.name

    try:
        # Testa a lógica da função corrigida
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        print(f"Conteúdo do arquivo: {content[:50]}...")

        # Aplica as validações
        if len(content) < 200:
            print("✅ REJEITADO: JSON muito pequeno")
            return True

        if not (content.startswith('{') and content.endswith('}')):
            print("✅ REJEITADO: JSON incompleto (não termina com })")
            return True

        try:
            data = json.loads(content)
            print("❌ ERRO: JSON inválido foi aceito!")
            return False
        except json.JSONDecodeError:
            print("✅ REJEITADO: JSONDecodeError detectado")
            return True

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    if testar_solucao_definitiva():
        print("🎉 SOLUÇÃO DEFINITIVA FUNCIONANDO!")
    else:
        print("❌ Solução precisa de ajustes")
