#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INVESTIGADOR DO BOOK WIN - Diagnóstico Completo
Analisa o arquivo book_data_win.csv para entender os dados estranhos
"""

import csv
import os
import time
from datetime import datetime

import pandas as pd


def analisar_arquivo_book():
    """Analisa o arquivo book_data_win.csv em detalhes"""

    arquivo = "book_data_win.csv"

    print("🔍 INVESTIGADOR DO BOOK WIN")
    print("=" * 60)

    # 1. VERIFICAÇÕES BÁSICAS DO ARQUIVO
    print("\n📁 INFORMAÇÕES DO ARQUIVO:")
    if os.path.exists(arquivo):
        tamanho = os.path.getsize(arquivo)
        modificado = datetime.fromtimestamp(os.path.getmtime(arquivo))
        print(f"   ✅ Arquivo existe: {arquivo}")
        print(f"   📏 Tamanho: {tamanho} bytes")
        print(f"   🕒 Última modificação: {modificado}")
    else:
        print(f"   ❌ Arquivo não encontrado: {arquivo}")
        return

    # 2. LEITURA RAW DO ARQUIVO
    print("\n📖 CONTEÚDO RAW DO ARQUIVO:")
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        print(f"   📊 Total de linhas: {len(linhas)}")

        for i, linha in enumerate(linhas):
            linha_limpa = linha.strip()
            print(
                f"   Linha {i+1}: '{linha_limpa}' (tamanho: {len(linha_limpa)})")

            # Mostra caracteres especiais
            if any(ord(c) > 127 for c in linha_limpa):
                print(f"   ⚠️  Caracteres especiais detectados!")

    except Exception as e:
        print(f"   ❌ Erro ao ler arquivo: {e}")
        return

    # 3. ANÁLISE DOS DADOS BID/ASK
    print("\n📈 ANÁLISE DOS DADOS:")

    if len(linhas) >= 2:
        bids_raw = linhas[0].strip()
        asks_raw = linhas[1].strip()

        print(f"   🟢 BIDs raw: {bids_raw}")
        print(f"   🔴 ASKs raw: {asks_raw}")

        # Processa BIDs
        try:
            bids = [int(v.strip()) for v in bids_raw.split(',') if v.strip()]
            print(f"   🟢 BIDs processados: {bids}")
            print(
                f"   🟢 Total BIDs: {len(bids)} níveis, Volume total: {sum(bids)}")
            print(
                f"   🟢 BID mín: {min(bids)}, máx: {max(bids)}, média: {sum(bids)/len(bids):.1f}")
        except Exception as e:
            print(f"   ❌ Erro ao processar BIDs: {e}")

        # Processa ASKs
        try:
            asks = [int(v.strip()) for v in asks_raw.split(',') if v.strip()]
            print(f"   🔴 ASKs processados: {asks}")
            print(
                f"   🔴 Total ASKs: {len(asks)} níveis, Volume total: {sum(asks)}")
            print(
                f"   🔴 ASK mín: {min(asks)}, máx: {max(asks)}, média: {sum(asks)/len(asks):.1f}")
        except Exception as e:
            print(f"   ❌ Erro ao processar ASKs: {e}")

    # 4. ANÁLISE DE PADRÕES SUSPEITOS
    print("\n🔍 ANÁLISE DE PADRÕES:")

    if len(linhas) >= 2:
        try:
            bids = [int(v.strip()) for v in bids_raw.split(',') if v.strip()]
            asks = [int(v.strip()) for v in asks_raw.split(',') if v.strip()]

            # Verifica volumes muito baixos
            volumes_baixos_bid = [v for v in bids if v < 10]
            volumes_baixos_ask = [v for v in asks if v < 10]

            if volumes_baixos_bid:
                print(
                    f"   ⚠️  BIDs com volume < 10: {volumes_baixos_bid} ({len(volumes_baixos_bid)} de {len(bids)})")

            if volumes_baixos_ask:
                print(
                    f"   ⚠️  ASKs com volume < 10: {volumes_baixos_ask} ({len(volumes_baixos_ask)} de {len(asks)})")

            # Verifica volumes repetidos
            bids_unicos = len(set(bids))
            asks_unicos = len(set(asks))

            if bids_unicos < len(bids):
                print(
                    f"   🔄 BIDs com valores repetidos: {len(bids) - bids_unicos} repetições")

            if asks_unicos < len(asks):
                print(
                    f"   🔄 ASKs com valores repetidos: {len(asks) - asks_unicos} repetições")

            # Verifica se volumes são típicos do WIN
            volume_total = sum(bids) + sum(asks)
            if volume_total < 500:
                print(
                    f"   ⚠️  Volume total muito baixo para WIN: {volume_total} (esperado > 500)")

            # Verifica proporção BID/ASK
            ratio = sum(bids) / sum(asks) if sum(asks) > 0 else 0
            print(f"   ⚖️  Ratio BID/ASK: {ratio:.2f}")

        except Exception as e:
            print(f"   ❌ Erro na análise de padrões: {e}")


def monitorar_arquivo_tempo_real():
    """Monitora o arquivo em tempo real para ver as mudanças"""

    arquivo = "book_data_win.csv"
    print("\n🔄 MONITORAMENTO EM TEMPO REAL (pressione Ctrl+C para parar)")
    print("=" * 60)

    ultima_modificacao = 0
    contador = 0

    try:
        while True:
            if os.path.exists(arquivo):
                modificacao_atual = os.path.getmtime(arquivo)

                if modificacao_atual != ultima_modificacao:
                    contador += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")

                    print(f"\n[{timestamp}] UPDATE #{contador}")

                    try:
                        with open(arquivo, 'r', encoding='utf-8') as f:
                            linhas = f.readlines()

                        if len(linhas) >= 2:
                            bids_raw = linhas[0].strip()
                            asks_raw = linhas[1].strip()

                            bids = [int(v.strip())
                                    for v in bids_raw.split(',') if v.strip()]
                            asks = [int(v.strip())
                                    for v in asks_raw.split(',') if v.strip()]

                            print(f"   BIDs: {bids} (total: {sum(bids)})")
                            print(f"   ASKs: {asks} (total: {sum(asks)})")
                            print(
                                f"   Liquidez total: {sum(bids) + sum(asks)}")

                    except Exception as e:
                        print(f"   ❌ Erro ao ler: {e}")

                    ultima_modificacao = modificacao_atual

            time.sleep(1)  # Verifica a cada segundo

    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoramento interrompido pelo usuário")


def comparar_com_mt5():
    """Tenta comparar os dados do arquivo com dados diretos do MT5"""

    print("\n🔗 COMPARAÇÃO COM MT5:")
    print("=" * 40)

    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            print("   ❌ Não foi possível conectar ao MT5")
            return

        # Procura contratos WIN ativos
        symbols = mt5.symbols_get()
        win_symbols = [s for s in symbols if s.name.startswith(
            'WIN') and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL]

        if not win_symbols:
            print("   ❌ Nenhum contrato WIN ativo encontrado")
            return

        symbol = win_symbols[0].name
        print(f"   📊 Testando com símbolo: {symbol}")

        # Ativa book
        if not mt5.market_book_add(symbol):
            print(f"   ❌ Não foi possível ativar book para {symbol}")
            return

        # Obtém dados do book
        book = mt5.market_book_get(symbol)

        if book:
            bids_mt5 = [
                level.volume for level in book if level.type == mt5.BOOK_TYPE_BUY]
            asks_mt5 = [
                level.volume for level in book if level.type == mt5.BOOK_TYPE_SELL]

            print(f"   🟢 BIDs MT5: {bids_mt5[:10]} (primeiros 10)")
            print(f"   🔴 ASKs MT5: {asks_mt5[:10]} (primeiros 10)")
            print(
                f"   📊 Total BID MT5: {sum(bids_mt5)}, Total ASK MT5: {sum(asks_mt5)}")

            # Compara com arquivo
            arquivo = "book_data_win.csv"
            if os.path.exists(arquivo):
                with open(arquivo, 'r', encoding='utf-8') as f:
                    linhas = f.readlines()

                if len(linhas) >= 2:
                    bids_arquivo = [
                        int(v.strip()) for v in linhas[0].strip().split(',') if v.strip()]
                    asks_arquivo = [
                        int(v.strip()) for v in linhas[1].strip().split(',') if v.strip()]

                    print(f"\n   📋 COMPARAÇÃO:")
                    print(
                        f"   MT5 BID total: {sum(bids_mt5)} vs Arquivo BID total: {sum(bids_arquivo)}")
                    print(
                        f"   MT5 ASK total: {sum(asks_mt5)} vs Arquivo ASK total: {sum(asks_arquivo)}")

                    if sum(bids_mt5) > sum(bids_arquivo) * 10:
                        print(
                            f"   ⚠️  DISCREPÂNCIA GRANDE! MT5 tem volumes muito maiores")

        mt5.shutdown()

    except ImportError:
        print("   ⚠️  MetaTrader5 não disponível para comparação")
    except Exception as e:
        print(f"   ❌ Erro na comparação: {e}")


def main():
    """Função principal"""

    print("🤖 INVESTIGADOR DO BOOK WIN - DIAGNÓSTICO COMPLETO")
    print("Mestre Super, vamos descobrir o que está acontecendo!")
    print()

    # Análise inicial
    analisar_arquivo_book()

    # Comparação com MT5
    comparar_com_mt5()

    # Pergunta se quer monitorar
    print("\n" + "=" * 60)
    resposta = input(
        "🔄 Deseja monitorar o arquivo em tempo real? (s/n): ").lower()

    if resposta in ['s', 'sim', 'y', 'yes']:
        monitorar_arquivo_tempo_real()

    print("\n✅ Investigação concluída!")


if __name__ == "__main__":
    main()
