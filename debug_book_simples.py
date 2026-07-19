#!/usr/bin/env python3
"""Debples do arquivo de book."""

import json
import os


def debug_book():
    arquivo = "book_data_win.csv"

    print("🔍 DEBUG DO ARQUIVO DE BOOK")
    print("=" * 40)

    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não existe: {arquivo}")
        return

    tamanho = os.path.getsize(arquivo)
    print(f"📏 Tamanho: {tamanho} bytes")

    with open(arquivo, 'r') as f:
        conteudo = f.read()

    print(f"📄 Conteúdo:")
    print(f"'{conteudo}'")

    linhas = conteudo.strip().split('\n')


n📋 {len(linhas)} linhas: ")
    for i, linha in enumerate(linhas, 1):
        print(f"   {i}: '{linha}'")

    # Testa como CSV
    try:
        if len(linhas) >= 2:
            volumes_bid = [int(x) for x in linhas[0].split(',') if x.strip()]
            volumes_ask = [int(x) for x in linhas[1].split(',') if x.strip()]

            print(f"\n✅ CSV válido:")
            print(f"   BID: {volumes_bid} (soma: {sum(volumes_bid)})")
            print(f"   ASK: {volumes_ask} (soma: {sum(volumes_ask)})")

            # Simula dados para profundidade
            book_data = {
                "bids": [{"price": 0.0, "volume": vol} for vol in volumes_bid],
                "asks": [{"price": 0.0, "volume": vol} for vol in volumes_ask]
            }

            print(f"\n🔄 Crtido para análise:")
            print(f"   BIDs: {len(book_data['bids'])} níveis")
            print(f"   ASKs: {len(book_data['asks'])} níveis")

            if book_data['bids']:
                maior_bid = max(book_data['bids'], key=lambda x: x['volume'
              print(f"   Maior escora BID: {maior_bid['volume']} contratos")

            if book_data['asks']:
                maior_ask = max(book_data['asks'], key=lambda x: x['volume'])
                print(f"   Maior escora ASK: {maior_ask['volume']} contratos")

    except Exception as e:
        print(f"❌ Erro CSV: {e}")

if __name__ == "__main__":
    debug_book()
