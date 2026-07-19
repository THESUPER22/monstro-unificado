#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DIAGNÓSTICO DO BOOK WIN - Debug do arquivo book_data_win.csv
"""

import os
import json
import MetaTrader5 as mt5


def debug_book_win():
    """Diagnostica o arquivo book_data_win.csv"""

    print("🔍 DIAGNÓSTICO DO BOOK WIN")
    print("=" * 50)

    # Inicializa MT5 para obter o caminho
    if not mt5.initialize():
        print("❌ Erro ao inicializar MT5")
        return

    # Obtém o caminho do arquivo
    terminal_info = mt5.terminal_info()
    if not terminal_info:
        print("❌ Erro ao obter informações do terminal")
        return

    book_file_path = os.path.join(
        terminal_info.data_path, 'MQL5', 'Files', 'book_data_win.csv')

    print(f"📁 Caminho do arquivo: {book_file_path}")

    # Verifica se arquivo existe
    if not os.path.exists(book_file_path):
        print("❌ Arquivo não existe!")
        return

    # Verifica tamanho do arquivo
    file_size = os.path.getsize(book_file_path)
    print(f"📊 Tamanho do arquivo: {file_size} bytes")

    if file_size < 4:
        print("⚠️ Arquivo muito pequeno!")
        return

    # Tenta ler o arquivo
    try:
        with open(book_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"📄 Conteúdo do arquivo ({len(content)} caracteres):")
        print("-" * 30)
        print(content[:500])  # Primeiros 500 caracteres
        if len(content) > 500:


nt("... (truncado)")
        print("-" * 30)

        # Tenta interpretar como JSON
        try:
            data = json.loads(content)
            print("✅ Arquivo é JSON válido!")
            print(f"🔍 Estrutura: {list(data.keys())}")

            if 'bids' in data:
                print(f"📈 BIDs: {len(data['bids'])} níveis")
                if data['bids']:
                    print(f"   Primeiro BID: {data['bids'][0]}")

            if 'asks' in data:
                print(f"📉 ASKs: {len(data['asks'])} níveis")
                if data['asks']:
                    print(f"   Primeiro ASK: {data['asks'][0]}")

        except json.JSONDecodeError as e:
            print(f"❌ Não é JSON válido: {e}")
            print("🔄 Tentando interpretar como CSV...")

            lines = content.strip().split('\n')
            print(f"📄 Linhas no CSV: {len(lines)}")
            for i, line in enumerate(lines[:5]):  # Primeiras 5 linhas
                print(f"   Linha {i+1}: {line}")

    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")

    finally:
        mt5.shutdown()

if __name__ == "__main__":
    debug_book_win()
