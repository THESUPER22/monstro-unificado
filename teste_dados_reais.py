"""
Teste com dados reais do book_data_win.csv
"""

import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("TESTE COM DADOS REAIS DO EA WIN")
print("=" * 50)

try:
    # Ler dados reais do arquivo
    with open('book_data_win.csv', 'r') as f:
        lines = f.readlines()

    if len(lines) >= 2:
        bids_str = lines[0].strip()
        asks_str = lines[1].strip()

        print(f"Dados brutos do EA:")
        print(f"   BIDs raw: {bids_str}")
        print(f"   ASKs raw: {asks_str}")

        # Processar dados
        bids = [int(v) for v in bids_str.split(',') if v.strip()]
        asks = [int(v) for v in asks_str.split(',') if v.strip()]

        dados_reais = {
            'bids': bids,
            'asks': asks
        }

        print(f"   BIDs processados: {bids} (total: {sum(bids)})")
        print(f"   ASKs processados: {asks} (total: {sum(asks)})")
        print()

        # Importar validador
        from monstro_unificado_v2 import CSVDataValidator

        validador = CSVDataValidator()
        resultado = validador.validate_book_data(dados_reais)

        print(f"RESULTADO DA VALIDACAO:")
        print(f"   Valido: {resultado['valid']}")
        print(f"   Recomendacao: {resultado['recommendation']}")
        print(f"   Issues: {len(resultado['issues'])}")

        if resultado['issues']:
            print(f"\nISSUES:")
            for issue in resultado['issues']:
                print(f"   - {issue}")

        if resultado['recommendation'] == 'accept':
            print(f"\nSUCESSO: Dados reais aceitos!")
        elif resultado['recommendation'] == 'sanitize':
            print(f"\nOK: Dados aceitos apos sanitizacao")
        else:
            print(f"\nERRO: Dados rejeitados!")

    else:
        print("ERRO: Arquivo CSV nao tem dados suficientes")

except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("TESTE CONCLUIDO")
