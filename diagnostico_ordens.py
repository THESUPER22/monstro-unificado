#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO DE ORDENS - MONSTRO DAS NEGOCIAÇÕES
Identifica por que as ordens não estão sendo enviadas
"""

import MetaTrader5 as mt5
import os
import sys
from datetime import datetime, time as dtime
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações do robô
MT5_PATH = r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
MAGIC_NUMBER = 123456
VOLUME_PADRAO = 1.0
DEVIATION = 20
MAX_SPREAD = 5
HORARIO_PREGAO = "09:00"
HORARIO_LIMITE_ORDENS = "18:15"
HORARIO_ENCERRAMENTO = "18:20"
HORARIO_AFTER = "18:32"

def verificar_status_mt5():
    """Verifica status da conexão MT5"""
    print("🔍 DIAGNÓSTICO DA CONEXÃO MT5")
    print("=" * 50)

    # 1. Verificar se MT5 está instalado
    if not os.path.exists(MT5_PATH):
        print(f"❌ MetaTrader 5 não encontrado em: {MT5_PATH}")
        return False

    print(f"✅ MetaTrader 5 encontrado em: {MT5_PATH}")

    # 2. Tentar inicializar
    if not mt5.initialize(path=MT5_PATH):
        print(f"❌ Erro ao inicializar MT5: {mt5.last_error()}")
        return False

    print("✅ MT5 inicializado com sucesso")

    # 3. Verificar informações da conta
    account_info = mt5.account_info()
    if account_info is None:
        print("❌ Não foi possível obter informações da conta")
        return False

    print(f"✅ Conta: {account_info.login}")
    print(f"✅ Servidor: {account_info.server}")
    print(f"✅ Saldo: {account_info.balance}")
    print(f"✅ Margem livre: {account_info.margin_free}")
    print(f"✅ Trading permitido: {account_info.trade_allowed}")

    return True

def verificar_simbolo():
    """Verifica se o símbolo está disponível e configurado"""
    print("\n🔍 DIAGNÓSTICO DO SÍMBOLO")
    print("=" * 50)

    # Buscar contrato WDO ativo
    symbols = mt5.symbols_get()
    wdo_symbols = [s for s in symbols if s.name.startswith('WDO') and 'MINI' in s.description]

    if not wdo_symbols:
        print("❌ Nenhum símbolo WDO encontrado")
        return None

    print(f"✅ Encontrados {len(wdo_symbols)} símbolos WDO:")
    for sym in wdo_symbols[:5]:  # Mostra os primeiros 5
        print(f"   - {sym.name}: {sym.description}")

    # Pegar o primeiro símbolo ativo
    symbol = wdo_symbols[0].name

    # Verificar se está selecionado
    if not mt5.symbol_select(symbol, True):
        print(f"❌ Erro ao selecionar símbolo {symbol}")
        return None

    print(f"✅ Símbolo selecionado: {symbol}")

    # Verificar informações do símbolo
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Não foi possível obter informações do símbolo {symbol}")
        return None

    print(f"✅ Modo de trading: {symbol_info.trade_mode}")
    print(f"✅ Volume mín: {symbol_info.volume_min}")
    print(f"✅ Volume máx: {symbol_info.volume_max}")
    print(f"✅ Volume step: {symbol_info.volume_step}")
    print(f"✅ Digits: {symbol_info.digits}")
    print(f"✅ Point: {symbol_info.point}")

    # Verificar tick atual
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ Não foi possível obter tick do símbolo {symbol}")
        return None

    print(f"✅ Bid: {tick.bid}")
    print(f"✅ Ask: {tick.ask}")
    print(f"✅ Spread: {tick.ask - tick.bid:.1f} pontos")

    return symbol

def verificar_horario():
    """Verifica se está no horário de operação"""
    print("\n🔍 DIAGNÓSTICO DE HORÁRIO")
    print("=" * 50)

    agora = datetime.now().time()
    pregao = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    limite_ordens = datetime.strptime(HORARIO_LIMITE_ORDENS, "%H:%M").time()
    encerramento = datetime.strptime(HORARIO_ENCERRAMENTO, "%H:%M").time()
    after = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    print(f"⏰ Horário atual: {agora}")
    print(f"⏰ Pregão inicia: {pregao}")
    print(f"⏰ Limite ordens: {limite_ordens}")
    print(f"⏰ Encerramento: {encerramento}")
    print(f"⏰ After market: {after}")

    # Verificar dia da semana
    dia_semana = datetime.now().weekday()
    if dia_semana > 4:  # Sábado ou Domingo
        print("❌ Final de semana - mercado fechado")
        return False

    print(f"✅ Dia útil (dia {dia_semana})")

    # Verificar horário
    if agora < pregao:
        print("❌ Antes do horário do pregão")
        return False
    elif agora >= limite_ordens:
        print("❌ Após horário limite para ordens")
        return False
    else:
        print("✅ Dentro do horário de operação")
        return True

def testar_ordem_simples(symbol):
    """Testa envio de uma ordem simples"""
    print("\n🔍 TESTE DE ORDEM SIMPLES")
    print("=" * 50)

    # Obter tick atual
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("❌ Não foi possível obter tick")
        return False

    # Preparar ordem de compra
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": VOLUME_PADRAO,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "sl": tick.ask - 0.005,  # SL 5 pontos
        "tp": tick.ask + 0.010,  # TP 10 pontos
        "deviation": DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": "Teste Monstro",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    print(f"📋 Ordem preparada:")
    print(f"   Símbolo: {request['symbol']}")
    print(f"   Volume: {request['volume']}")
    print(f"   Tipo: {request['type']}")
    print(f"   Preço: {request['price']}")
    print(f"   SL: {request['sl']}")
    print(f"   TP: {request['tp']}")
    print(f"   Magic: {request['magic']}")

    # Enviar ordem (COMENTADO PARA SEGURANÇA)
    print("\n⚠️ ENVIANDO ORDEM DE TESTE...")
    resultado = mt5.order_send(request)

    if resultado is None:
        print("❌ Resultado é None - erro crítico")
        return False

    print(f"📊 Resultado da ordem:")
    print(f"   Retcode: {resultado.retcode}")
    print(f"   Deal: {resultado.deal}")
    print(f"   Order: {resultado.order}")
    print(f"   Volume: {resultado.volume}")
    print(f"   Price: {resultado.price}")
    print(f"   Comment: {resultado.comment}")

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        print("✅ ORDEM ENVIADA COM SUCESSO!")

        # Fechar a posição imediatamente
        print("🔄 Fechando posição de teste...")
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": resultado.order,
            "symbol": symbol,
            "volume": VOLUME_PADRAO,
            "type": mt5.ORDER_TYPE_SELL,
            "price": tick.bid,
            "deviation": DEVIATION,
            "magic": MAGIC_NUMBER,
            "comment": "Fechar teste",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        close_result = mt5.order_send(close_request)
        if close_result.retcode == mt5.TRADE_RETCODE_DONE:
            print("✅ Posição de teste fechada com sucesso")
        else:
            print(f"⚠️ Erro ao fechar posição: {close_result.comment}")

        return True
    else:
        print(f"❌ ERRO AO ENVIAR ORDEM: {resultado.comment}")
        return False

def verificar_permissoes():
    """Verifica permissões de trading"""
    print("\n🔍 VERIFICAÇÃO DE PERMISSÕES")
    print("=" * 50)

    account_info = mt5.account_info()
    if account_info is None:
        print("❌ Não foi possível obter informações da conta")
        return False

    print(f"✅ Trading permitido na conta: {account_info.trade_allowed}")
    print(f"✅ Trading expert permitido: {account_info.trade_expert}")

    # Verificar se há posições abertas
    positions = mt5.positions_get()
    if positions is None:
        print("✅ Nenhuma posição aberta")
    else:
        print(f"📊 Posições abertas: {len(positions)}")
        for pos in positions[:3]:  # Mostra as primeiras 3
            print(f"   - {pos.symbol}: {pos.type} {pos.volume} @ {pos.price_open}")

    return True

def main():
    """Função principal do diagnóstico"""
    print("🤖 DIAGNÓSTICO COMPLETO DE ORDENS - MONSTRO DAS NEGOCIAÇÕES")
    print("=" * 60)

    try:
        # 1. Verificar MT5
        if not verificar_status_mt5():
            print("\n❌ FALHA: Problema com MT5")
            return

        # 2. Verificar símbolo
        symbol = verificar_simbolo()
        if not symbol:
            print("\n❌ FALHA: Problema com símbolo")
            return

        # 3. Verificar horário
        if not verificar_horario():
            print("\n⚠️ AVISO: Fora do horário de operação")
            # Continua mesmo assim para outros testes

        # 4. Verificar permissões
        if not verificar_permissoes():
            print("\n❌ FALHA: Problema com permissões")
            return

        # 5. Testar ordem
        resposta = input("\n🚨 DESEJA ENVIAR UMA ORDEM DE TESTE? (s/N): ")
        if resposta.lower() == 's':
            if testar_ordem_simples(symbol):
                print("\n✅ DIAGNÓSTICO COMPLETO: Sistema funcionando!")
            else:
                print("\n❌ DIAGNÓSTICO COMPLETO: Problema identificado no envio de ordens")
        else:
            print("\n✅ DIAGNÓSTICO BÁSICO COMPLETO: Tudo parece estar funcionando")
            print("💡 Para teste completo, execute novamente e confirme o teste de ordem")

    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

    finally:
        mt5.shutdown()
        print("\n🔒 Conexão MT5 encerrada")

if __name__ == "__main__":
    main()
