#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR DO EA WIN - Diagnóstico do Expert Advisor
Verifica se otá funcionando corretamente
"""

import time
from datetime import datetime

import MetaTrader5 as mt5


def verificar_mt5_connection():
    """Verifica conexão com MT5"""
    print("🔗 VERIFICANDO CONEXÃO MT5:")
    print("=" * 40)

    if not mt5.initialize():
        print("   ❌ Erro ao conectar MT5:", mt5.last_error())
        return False

    # Info do terminal
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"   ✅ Terminal conectado: {terminal_info.name}")
        print(f"   📁 Caminho dos dados: {terminal_info.data_path}")
        print(f"   🕒 Servidor: {terminal_info.company}")

    # Info da conta
    account_info = mt5.account_info()
    if account_info:
        print(f"   👤 Conta: {account_info.login}")
        print(f"   🏦 Servidor: {account_info.server}")
        print(f"   💰 Saldo: {account_info.balance}")

    return True


def verificar_contratos_win():
    """Verifica contratos WIN disponíveis"""
    print("\n📊 CONTRATOS WIN DISPONÍVEIS:")
    print("=" * 40)

    symbols = mt5.symbols_get()
    win_symbols = []

    for symbol in symbols:
        if symbol.name.startswith('WIN'):
            win_symbols.append(symbol)
            status = "ATIVO" if symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL else "INATIVO"
            print(f"   📈 {symbol.name}: {status}")

            if symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                print(f"      💱 Tick size: {symbol.point}")
                print(f"      📏 Digits: {symbol.digits}")

                # Verifica se está no Market Watch
                if mt5.symbol_select(symbol.name, True):
                    print(f"      ✅ Adicionado ao Market Watch")
                else:
                    print(f"      ❌ Erro ao adicionar ao Market Watch")

    return win_symbols


def testar_book_direto(symbol_name):
    """Testa o book diretamente via MT5"""
    print(f"\n📖 TESTANDO BOOK DIRETO - {symbol_name}:")
    print("=" * 50)

    # Garante que símbolo está selecionado
    if not mt5.symbol_select(symbol_name, True):
        print(f"   ❌ Erro ao selecionar {symbol_name}")
        return

    # Ativa book
    if not mt5.market_book_add(symbol_name):
        print(f"   ❌ Erro ao ativar book: {mt5.last_error()}")
        return

    print(f"   ✅ Book ativado para {symbol_name}")

    # Coleta dados do book
    for i in range(3):  # 3 tentativas
        book = mt5.market_book_get(symbol_name)

        if book is None:
            print(f"   ❌ Tentativa {i+1}: Book retornou None")
            time.sleep(1)
            continue

        if len(book) == 0:
            print(f"   ⚠️  Tentativa {i+1}: Book vazio")
            time.sleep(1)
            continue

        # Processa dados
        bids = []
        asks = []

        for level in book:
            if level.type == mt5.BOOK_TYPE_BUY:
                bids.append(level.volume)
            elif level.type == mt5.BOOK_TYPE_SELL:
                asks.append(level.volume)

        print(f"   📊 Tentativa {i+1}:")
        print(f"      🟢 BIDs: {len(bids)} níveis, volumes: {bids[:10]}")
        print(f"      🔴 ASKs: {len(asks)} níveis, volumes: {asks[:10]}")
        print(f"      💧 Total BID: {sum(bids)}, Total ASK: {sum(asks)}")
        print(f"      🌊 Liquidez total: {sum(bids) + sum(asks)}")

        # Verifica se volumes são normais
        if sum(bids) + sum(asks) > 500:
            print(f"      ✅ Volumes normais detectados!")
        else:
            print(f"      ⚠️  Volumes baixos (pode ser horário/mercado)")

        time.sleep(1)

    # Remove book
    mt5.market_book_release(symbol_name)


def comparar_book_vs_arquivo():
    """Compara book MT5 com arquivo CSV"""
    print("\n🔄 COMPARAÇÃO BOOK MT5 vs ARQUIVO:")
    print("=" * 45)

    # Encontra contrato WIN ativo
    symbols = mt5.symbols_get()
    win_active = None

    for symbol in symbols:
        if symbol.name.startswith('WIN') and symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            win_active = symbol.name
            break

    if not win_active:
        print("   ❌ Nenhum contrato WIN ativo")
        return

    print(f"   📊 Usando contrato: {win_active}")

    # Ativa book e coleta dados
    if mt5.market_book_add(win_active):
        book = mt5.market_book_get(win_active)

        if book:
            bids_mt5 = [
                level.volume for level in book if level.type == mt5.BOOK_TYPE_BUY]
            asks_mt5 = [
                level.volume for level in book if level.type == mt5.BOOK_TYPE_SELL]

            print(
                f"   🟢 MT5 BIDs: {sum(bids_mt5)} total ({len(bids_mt5)} níveis)")
            print(
                f"   🔴 MT5 ASKs: {sum(asks_mt5)} total ({len(asks_mt5)} níveis)")

            # Lê arquivo
            try:
                with open('book_data_win.csv', 'r') as f:
                    lines = f.readlines()

                if len(lines) >= 2:
                    bids_csv = [int(v.strip())
                                for v in lines[0].strip().split(',') if v.strip()]
                    asks_csv = [int(v.strip())
                                for v in lines[1].strip().split(',') if v.strip()]

                    print(
                        f"   📄 CSV BIDs: {sum(bids_csv)} total ({len(bids_csv)} níveis)")
                    print(
                        f"   📄 CSV ASKs: {sum(asks_csv)} total ({len(asks_csv)} níveis)")

                    # Análise da diferença
                    diff_bid = sum(bids_mt5) - sum(bids_csv)
                    diff_ask = sum(asks_mt5) - sum(asks_csv)

                    print(f"\n   📊 DIFERENÇAS:")
                    print(
                        f"      BID: MT5({sum(bids_mt5)}) - CSV({sum(bids_csv)}) = {diff_bid}")
                    print(
                        f"      ASK: MT5({sum(asks_mt5)}) - CSV({sum(asks_csv)}) = {diff_ask}")

                    if abs(diff_bid) > 1000 or abs(diff_ask) > 1000:
                        print(f"   🚨 GRANDE DISCREPÂNCIA! EA pode estar com problema")
                    else:
                        print(f"   ✅ Diferenças normais")

            except Exception as e:
                print(f"   ❌ Erro ao ler CSV: {e}")

        mt5.market_book_release(win_active)


def main():
    """Função principal"""
    print("🔍 VERIFICADOR DO EA WIN - DIAGNÓSTICO COMPLETO")
    print("Vamos descobrir se o EA está funcionando corretamente!")
    print()

    # 1. Verifica conexão MT5
    if not verificar_mt5_connection():
        return

    # 2. Lista contratos WIN
    win_symbols = verificar_contratos_win()

    if not win_symbols:
        print("❌ Nenhum contrato WIN encontrado!")
        return

    # 3. Testa book direto
    active_win = None
    for symbol in win_symbols:
        if symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            active_win = symbol.name
            break

    if active_win:
        testar_book_direto(active_win)

    # 4. Compara book vs arquivo
    comparar_book_vs_arquivo()

    # Finaliza MT5
    mt5.shutdown()

    print("\n" + "=" * 60)
    print("✅ DIAGNÓSTICO CONCLUÍDO!")
    print("\n💡 PRÓXIMOS PASSOS:")
    print("1. Se volumes MT5 são normais mas CSV baixos → Problema no EA")
    print("2. Se ambos são baixos → Mercado fechado ou pouca liquidez")
    print("3. Se EA não detectado → Verificar se está rodando")


if __name__ == "__main__":
    main()
