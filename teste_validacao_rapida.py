"""
Teste rapido da validacao de dados do book WIN
"""

import json
import logging
import os
import sys

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Simular dados tipicos do EA WIN
dados_teste = {
    'bids': [149, 120, 95, 80, 65, 50, 40, 35, 30, 25],
    'asks': [162, 140, 115, 90, 75, 60, 45, 38, 32, 28]
}

print("TESTE DE VALIDACAO DOS DADOS WIN")
print("=" * 50)

# Importar o validador do monstro
try:
    sys.path.append('.')
    from monstro_unificado_v2 import CSVDataValidator

    # Criar instancia do validador
    validador = CSVDataValidator()

    print(f"Dados de teste:")
    print(
        f"   BIDs: {dados_teste['bids']} (total: {sum(dados_teste['bids'])})")
    print(
        f"   ASKs: {dados_teste['asks']} (total: {sum(dados_teste['asks'])})")
    print()

    # Testar validacao
    resultado = validador.validate_book_data(dados_teste)

    print(f"RESULTADO DA VALIDACAO:")
    print(f"   Valido: {resultado['valid']}")
    print(f"   Recomendacao: {resultado['recommendation']}")
    print(f"   Issues: {len(resultado['issues'])}")
    print(f"   Padroes suspeitos: {len(resultado['suspicious_patterns'])}")

    if resultado['issues']:
        print(f"\nISSUES ENCONTRADAS:")
        for issue in resultado['issues']:
            print(f"   - {issue}")

    if resultado['suspicious_patterns']:
        print(f"\nPADROES SUSPEITOS:")
        for pattern in resultado['suspicious_patterns']:
            print(f"   - {pattern}")

    print(f"\nESTATISTICAS:")
    stats = resultado['statistics']
    print(f"   Niveis BID: {stats['bid_levels']}")
    print(f"   Niveis ASK: {stats['ask_levels']}")
    print(f"   Volume BID: {stats['total_bid_volume']}")
    print(f"   Volume ASK: {stats['total_ask_volume']}")
    print(f"   Liquidez total: {stats['total_liquidity']}")

    # Testar com dados sanitizados se necessario
    if resultado['recommendation'] == 'sanitize':
        dados_sanitizados = resultado['sanitized_data']
        print(f"\nDADOS SANITIZADOS:")
        print(
            f"   BIDs: {dados_sanitizados['bids']} (total: {sum(dados_sanitizados['bids'])})")
        print(
            f"   ASKs: {dados_sanitizados['asks']} (total: {sum(dados_sanitizados['asks'])})")

    # Resultado final
    if resultado['recommendation'] == 'accept':
        print(f"\nSUCESSO: Dados aceitos sem problemas!")
    elif resultado['recommendation'] == 'sanitize':
        print(f"\nATENCAO: Dados aceitos apos sanitizacao")
    else:
        print(f"\nERRO: Dados rejeitados!")

except Exception as e:
    print(f"ERRO NO TESTE: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("TESTE CONCLUIDO")
