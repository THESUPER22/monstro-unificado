#!/usr/bin/en3
"""
Teste para simular dados reais do book quando o mercado está fechado.
Cria um arquivo CSV temporário com dados simulados para testar o sistema.
"""

import json
import os
import time
from typing import Dict


def criar_dados_book_simulados():
    """Cria dados simulados do book para teste."""

    # Dados JSON simulados (formato novo do EA)
    book_data_json = {
        "bids": [
            {"price": 140080.0, "volume": 312},
            {"price": 140075.0, "volume": 150},
            {"price": 140070.0, "volume": 500},  # Escora grande
            {"price": 140065.0, "volume": 200},
            {"price": 140060.0, "volume": 100},
            {"price": 140055.0, "volume": 75},
            {"price": 140050.0, "volume": 250},
            {"price": 140045.0, "volume": 180},
            {"price": 140040.0, "volume": 90},
            {"price": 140035.0, "volume": 120}
        ],
        "asks": [
            {"price": 140085.0, "volume": 68},
            {"price": 140090.0, "volume": 299},
            {"price": 140095.0, "volume": 800},  # Escora grande
            {"price": 140100.0, "volume": 150},
            {"price": 140105.0, "volume": 75},
            {"price": 140110.0, "volume": 200},
            {"price": 140115.0, "volume": 300},
            {"price": 140120.0, "volume": 100},
            {"price": 140125.0, "volume": 50},
            {"price": 140130.0, "volume": 175}
        ],
        "metadata": {
            "symbol": "WINV25",
            "timestamp": int(time.time()),
            "total_bid_volume": 1977,
            "total_ask_volume": 2217,
            "bid_levels": 10,
            "ask_levels": 10
        }
    }

    return book_data_json


def criar_arquivo_csv_simulado():
    """Cria arquivo CSV com dados simulados (formato legado)."""

    # Volumes simulados (formato antigo)
    volumes_bid = [312, 150, 500, 200, 100, 75, 250, 180, 90, 120]
    volumes_ask = [68, 299, 800, 150, 75, 200, 300, 100, 50, 175]

    csv_content = ",".join(map(str, volumes_bid)) + "\n"
    csv_content += ",".join(map(str, volumes_ask)) + "\n"

    return csv_content


def testar_com_dados_simulados():
    """Testa o sistema com dados simulados."""

    print("🧪 TESTANDO SISTEMA COM DADOS SIMULADOS")
    print("=" * 50)

    # Backup do arquivo original
    arquivo_original = "book_data_win.csv"
    arquivo_backup = "book_data_win.csv.backup_teste"

    if os.path.exists(arquivo_original):
        print(f"📦 Fazendo backup: {arquivo_original} -> {arquivo_backup}")
        with open(arquivo_original, 'r') as f:
            conteudo_original = f.read()
        with open(arquivo_backup, 'w') as f:
            f.write(conteudo_original)

    try:
        # Teste 1: Formato JSON
        print("\n🧪 Teste 1: Criando arquivo JSON simulado...")
        dados_json = criar_dados_book_simulados()

        with open(arquivo_original, 'w', encoding='utf-8') as f:
            json.dump(dados_json, f, indent=2)

        print("✅ Arquivo JSON criado com dados simulados")
        print(f"   📊 BIDs: {len(dados_json['bids'])} níveis")
        print(f"   📊 ASKs: {len(dados_json['asks'])} níveis")
        print(
            f"   📊 Maior escora BID: {max(dados_json['bids'], key=lambda x: x['volume'])['volume']} contratos")
        print(
            f"   📊 Maior escora ASK: {max(dados_json['asks'], key=lambda x: x['volume'])['volume']} contratos")

        input("\n⏸️  Pressione ENTER para testar o Monstro com dados JSON...")

        # Teste 2: Formato CSV legado
        print("\n🧪 Teste 2: Criando arquivo CSV simulado...")
        csv_content = criar_arquivo_csv_simulado()

        with open(arquivo_original, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        print("✅ Arquivo CSV criado com dados simulados")
        print(f"   📊 Conteúdo: {csv_content.strip()}")

        input("\n⏸️  Pressione ENTER para testar o Monstro com dados CSV...")

    finally:
        # Restaura arquivo original
        if os.path.exists(arquivo_backup):
            print(f"\n🔄 Restaurando arquivo original...")
            with open(arquivo_backup, 'r') as f:
                conteudo_original = f.read()
            with open(arquivo_original, 'w') as f:
                f.write(conteudo_original)
            os.remove(arquivo_backup)
            print("✅ Arquivo original restaurado")

        print("\n🎯 TESTE CONCLUÍDO!")
        print("💡 Agora você pode executar o Monstro para ver se lê os dados corretamente")


if __name__ == "__main__":
    testar_com_dados_simulados()
