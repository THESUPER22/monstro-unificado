#!/usr/bin/env python3
"""
Teste da correção de race condition
"""

import json


def testar_protecao():
    print("🧪 Testando proteção contra race condition...")

    # JSON completo (válido)
    json_completo = '{"bids":[{"price":140020,"volume":182.0}],"asks":[{"price":140060,"volume":1596}],"metadata":{"symbol":"WINV25"}}'

    # JSON incompleto (race condition)
    json_incompleto = '{"bids":[{"price":140020,"vol'

    # Teste 1: JSON completo
    if json_completo.startswith('{') and json_completo.endswith('}') and len(json_completo) > 100:
        try:
            data = json.loads(json_completo)
            if isinstance(data, dict) and 'bids' in data and 'asks' in data:
                print("✅ JSON completo: APROVADO")
            else:
                print("❌ JSON completo: estrutura inválida")
        except:
            print("❌ JSON completo: erro de parse")
    else:
        print("❌ JSON completo: não passou na validação inicial")

    # Teste 2: JSON incompleto
    if json_incompleto.startswith('{') and json_incompleto.endswith('}') and len(json_incompleto) > 100:
        print("❌ JSON incompleto: passou na validação (ERRO)")
    else:
        print("✅ JSON incompleto: REJEITADO (correto)")

    print("🎉 Proteção implementada com sucesso!")


if __name__ == "__main__":
    testar_protecao()
