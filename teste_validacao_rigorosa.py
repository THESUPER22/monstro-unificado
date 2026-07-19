#!/usr/bin/env pyt
"""
Teste da validação rigorosa contra race condition
"""

import json


def testar_validacao_rigorosa():
    print("🧪 Testando validação rigorosa contra race condition...")

    # Casos de teste
    casos = [
        # JSON completo (válido)
        ('JSON completo', '{"bids":[{"price":140020,"volume":182.0}],"asks":[{"price":140060,"volume":1596}],"metadata":{"symbol":"WINV25","timestamp":"2025.08.27","total_bid_volume":182,"total_ask_volume":1596,"bid_levels":1,"ask_levels":1}}'),

        # JSON muito pequeno (race condition)
        ('JSON pequeno', '{"bids":[]}'),

        # JSON sem fim (race condition)
        ('JSON sem fim',
         '{"bids":[{"price":140020,"volume":182.0}],"asks":[{"price":140060'),

        # JSON sem metadata (incompleto)
        ('JSON sem metadata',
         '{"bids":[{"price":140020,"volume":182.0}],"asks":[{"price":140060,"volume":1596}]}'),

        # JSON com bids/asks vazios
        ('JSON vazios',
         '{"bids":[],"asks":[],"metadata":{"symbol":"WINV25"}}'),
    ]

    for nome, json_str in casos:
        print(f"\n🔍 Testando: {nome}")

        # Aplica a mesma lógica da função corrigida
        valido = False

        # 1. Valida tamanho mínimo
        if len(json_str) < 200:
            print(f"   ❌ Muito pequeno ({len(json_str)} chars)")
            continue

        # 2. Valida estrutura básica
        if not (json_str.startswith('{') and json_str.endswith('}')):
            print("   ❌ Estrutura inválida")
            continue

        try:
            # 3. Tenta parse
            data = json.loads(json_str)

            # 4-6. Validações
            if not isinstance(data, dict):
                print("   ❌ Não é dict")
                continue

            if "bids" not in data or "asks" not in data:
                print("   ❌ Sem bids/asks")
                continue

            if not isinstance(data["bids"], list) or not isinstance(data["asks"], list):
                print("   ❌ bids/asks não são listas")
                continue

            if len(data["bids"]) == 0 or len(data["asks"]) == 0:
                print("   ❌ bids/asks vazios")
                continue

            if "metadata" not in data:
                print("   ❌ Sem metadata")
                continue

            print("   ✅ VÁLIDO!")
            valido = True

        except json.JSONDecodeError as e:
            print(f"   ❌ JSONDecodeError: {str(e)[:30]}...")

    print("\n🎉 Validação rigorosa implementada!")


if __name__ == "__main__":
    testar_validacao_rigorosa()
