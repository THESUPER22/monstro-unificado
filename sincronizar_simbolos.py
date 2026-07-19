#!/r/bin/env python3
# -*- coding: utf-8 -*-
"""
SINCRONIZADOR DE SÍMBOLOS - EA vs Python
Garante que EA e Python usem o mesmo contrato WIN
"""

import os
import re
from datetime import datetime

import MetaTrader5 as mt5


def encontrar_contrato_ea():
    """Descobre qual contrato o EA está usando"""
    print("🔍 DESCOBRINDO CONTRATO DO EA:")
    print("=" * 40)

    # Lê o arquivo CSV para ver qual símbolo está sendo usado
    csv_file = "book_data_win.csv"

    if not os.path.exists(csv_file):
        print("   ❌ Arquivo CSV não encontrado")
        return None

    # Verifica timestamp do arquivo (EA ativo se arquivo recente)
    mod_time = datetime.fromtimestamp(os.path.getmtime(csv_file))
    agora = datetime.now()
    diff_segundos = (agora - mod_time).total_seconds()

    print(f"   📅 Última modificação: {mod_time}")
    print(f"   ⏱️  Diferença: {diff_segundos:.0f} segundos")

    if diff_segundos > 60:
        print("   ⚠️  Arquivo antigo - EA pode não estar rodando")
    else:
        print("   ✅ Arquivo recente - EA está ativo")

    return diff_segundos < 60


def listar_contratos_ativos():
    """Lista todos os contratos WIN ativos com volumes"""
    print("\n📊 CONTRATOS WIN COM VOLUMES REAIS:")
    print("=" * 50)

    if not mt5.initialize():
        print("   ❌ Erro ao conectar MT5")
        return []

    symbols = mt5.symbols_get()
    contratos_win = []

    for symbol in symbols:
        if (symbol.name.startswith('WIN') and
            symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL and
            not symbol.name.endswith('$') and
                not symbol.name.endswith('@')):

            # Ativa book temporariamente
            if mt5.market_book_add(symbol.name):
                book = mt5.market_book_get(symbol.name)

                if book:
                    bids = [
                        level.volume for level in book if level.type == mt5.BOOK_TYPE_BUY]
                    asks = [
                        level.volume for level in book if level.type == mt5.BOOK_TYPE_SELL]
                    total_volume = sum(bids) + sum(asks)

                    contratos_win.append({
                        'symbol': symbol.name,
                        'volume': total_volume,
                        'bid_levels': len(bids),
                        'ask_levels': len(asks),
                        'expiration': getattr(symbol, 'expiration_time', 0)
                    })

                    status = "🔥 ALTA" if total_volume > 1000 else "📊 NORMAL" if total_volume > 100 else "💤 BAIXA"
                    print(f"   📈 {symbol.name}: {total_volume:,}cc {status}")
                    print(f"      📊 {len(bids)} BIDs + {len(asks)} ASKs")

                mt5.market_book_release(symbol.name)

    # Ordena por volume (maior primeiro)
    contratos_win.sort(key=lambda x: x['volume'], reverse=True)

    mt5.shutdown()
    return contratos_win


def recomendar_melhor_contrato(contratos):
    """Recomenda o melhor contrato baseado em volume e vencimento"""
    print("\n🎯 RECOMENDAÇÃO DE CONTRATO:")
    print("=" * 35)

    if not contratos:
        print("   ❌ Nenhum contrato encontrado")
        return None

    # Filtra contratos com volume razoável (>50cc)
    contratos_validos = [c for c in contratos if c['volume'] > 50]

    if not contratos_validos:
        print("   ⚠️  Todos os contratos com volume muito baixo")
        print("   💡 Pode ser horário de baixa liquidez")
        # Retorna o com maior volume mesmo sendo baixo
        return contratos[0]['symbol']

    melhor = contratos_validos[0]

    print(f"   🏆 MELHOR OPÇÃO: {melhor['symbol']}")
    print(f"   📊 Volume: {melhor['volume']:,}cc")
    print(
        f"   📈 Níveis: {melhor['bid_levels']} BIDs + {melhor['ask_levels']} ASKs")

    # Mostra alternativas
    if len(contratos_validos) > 1:
        print(f"\n   🔄 ALTERNATIVAS:")
        # Top 3 alternativas
        for i, contrato in enumerate(contratos_validos[1:4], 1):
            print(f"      {i}. {contrato['symbol']}: {contrato['volume']:,}cc")

    return melhor['symbol']


def criar_config_simbolo(simbolo_recomendado):
    """Cria arquivo de configuração com símbolo recomendado"""
    print(f"\n⚙️ CRIANDO CONFIGURAÇÃO PARA {simbolo_recomendado}:")
    print("=" * 50)

    config = f"""# CONFIGURAÇÃO DE SÍMBOLO SINCRONIZADO
# Gerado automaticamente em {datetime.now()}

SYMBOL_SINCRONIZADO = "{simbolo_recomendado}"

# Para usar no monstro_unificado_v2.py:
# 1. Importe: from sincronizar_simbolos import SYMBOL_SINCRONIZADO
# 2. Use: SYMBOL = SYMBOL_SINCRONIZADO

# Para configurar o EA:
# 1. Abra o EA no MetaEditor
# 2. Altere a linha de símbolo para: {simbolo_recomendado}
# 3. Recompile e reinicie o EA
"""

    with open('config_simbolo.py', 'w') as f:
        f.write(config)

    print(f"   ✅ Arquivo criado: config_simbolo.py")
    print(f"   📝 Símbolo configurado: {simbolo_recomendado}")


def verificar_ea_ativo():
    """Verifica se EA está realmente ativo"""
    print("\n🤖 VERIFICANDO STATUS DO EA:")
    print("=" * 30)

    csv_file = "book_data_win.csv"

    if not os.path.exists(csv_file):
        print("   ❌ EA não está rodando (arquivo CSV não existe)")
        return False

    # Monitora arquivo por alguns segundos
    import time

    mod_time_inicial = os.path.getmtime(csv_file)
    print("   ⏳ Monitorando atividade do EA por 5 segundos...")

    time.sleep(5)

    mod_time_final = os.path.getmtime(csv_file)

    if mod_time_final > mod_time_inicial:
        print("   ✅ EA está ATIVO (arquivo sendo atualizado)")
        return True
    else:
        print("   ⚠️  EA pode estar INATIVO (arquivo não atualizado)")
        return False


def main():
    """Função principal"""
    print("🔄 SINCRONIZADOR DE SÍMBOLOS EA vs PYTHON")
    print("Vamos descobrir e sincronizar os contratos!")
    print()

    # 1. Verifica se EA está ativo
    ea_ativo = verificar_ea_ativo()

    # 2. Lista contratos com volumes
    contratos = listar_contratos_ativos()

    # 3. Recomenda melhor contrato
    melhor_simbolo = recomendar_melhor_contrato(contratos)

    if melhor_simbolo:
        # 4. Cria configuração
        criar_config_simbolo(melhor_simbolo)

        print("\n" + "=" * 60)
        print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
        print()
        print("📋 PRÓXIMOS PASSOS:")
        print(f"1. Configure o EA para usar: {melhor_simbolo}")
        print("2. Reinicie o EA no MT5")
        print("3. Execute: python monstro_unificado_v2.py")
        print("4. Verifique se ambos usam o mesmo símbolo")

        if not ea_ativo:
            print("\n⚠️  ATENÇÃO: EA parece inativo!")
            print("   - Verifique se o EA está rodando no MT5")
            print("   - Certifique-se que AutoTrading está habilitado")

    else:
        print("\n❌ Não foi possível determinar melhor contrato")
        print("💡 Verifique se o mercado está aberto")


if __name__ == "__main__":
    main()
