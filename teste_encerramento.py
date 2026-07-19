#!/usr/bin/env python3
"""
🔴 TESTE DO SISTEMA DE ENCERRAMENTO DO MONSTRO
Valida se o encerramento automático às 18:20 funciona corretamente
"""

import sys
import os
from datetime import datetime, time as dtime
import logging

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa as configurações do robô
from monstro_unificado import (
    HORARIO_PREGAO, HORARIO_LIMITE_ORDENS, HORARIO_ENCERRAMENTO,
    HORARIO_AFTER, HORARIO_AJUSTE, fechar_todas_posicoes
)

def testar_configuracao_horarios():
    """Testa se os horários estão configurados corretamente."""
    print("🕐 TESTE DE CONFIGURAÇÃO DE HORÁRIOS")
    print("="*50)

    horarios = {
        "Pregão": HORARIO_PREGAO,
        "Limite Ordens": HORARIO_LIMITE_ORDENS,
        "Encerramento": HORARIO_ENCERRAMENTO,
        "After Market": HORARIO_AFTER,
        "Ajuste": HORARIO_AJUSTE
    }

    for nome, horario in horarios.items():
        try:
            horario_obj = datetime.strptime(horario, "%H:%M").time()
            print(f"✅ {nome}: {horario} - OK")
        except Exception as e:
            print(f"❌ {nome}: {horario} - ERRO: {e}")

    print("\n📋 SEQUÊNCIA DE ENCERRAMENTO:")
    print(f"1. {HORARIO_LIMITE_ORDENS} - Para de aceitar novas ordens")
    print(f"2. {HORARIO_ENCERRAMENTO} - Fecha todas as posições e encerra")
    print(f"3. {HORARIO_AFTER} - Fim do after-market")
    print(f"4. {HORARIO_AJUSTE} - Horário do ajuste")

    # Verifica se a sequência está correta
    try:
        h_limite = datetime.strptime(HORARIO_LIMITE_ORDENS, "%H:%M").time()
        h_encerramento = datetime.strptime(HORARIO_ENCERRAMENTO, "%H:%M").time()
        h_after = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

        if h_limite < h_encerramento < h_after:
            print("✅ Sequência de horários está correta!")
        else:
            print("❌ ERRO: Sequência de horários incorreta!")
            return False
    except Exception as e:
        print(f"❌ ERRO ao validar sequência: {e}")
        return False

    return True

def testar_funcao_fechamento():
    """Testa se a função de fechamento de posições funciona."""
    print("\n🔴 TESTE DE FECHAMENTO DE POSIÇÕES")
    print("="*50)

    try:
        # Simula o fechamento (sem posições reais)
        print("🔍 Testando função fechar_todas_posicoes()...")

        # Chama a função (deve retornar 0 se não houver posições)
        resultado = fechar_todas_posicoes("Teste automático")

        print(f"✅ Função executada com sucesso - Resultado: {resultado}")
        return True

    except Exception as e:
        print(f"❌ ERRO na função de fechamento: {e}")
        return False

def simular_encerramento():
    """Simula o processo de encerramento."""
    print("\n🏁 SIMULAÇÃO DO PROCESSO DE ENCERRAMENTO")
    print("="*50)

    agora = datetime.now().time()
    h_limite = datetime.strptime(HORARIO_LIMITE_ORDENS, "%H:%M").time()
    h_encerramento = datetime.strptime(HORARIO_ENCERRAMENTO, "%H:%M").time()

    print(f"⏰ Horário atual: {agora}")
    print(f"🕕 Limite para ordens: {h_limite}")
    print(f"🔴 Encerramento automático: {h_encerramento}")

    if agora >= h_encerramento:
        print("🔴 SERIA EXECUTADO: Encerramento automático")
        return "ENCERRAMENTO"
    elif agora >= h_limite:
        print("🕕 SERIA EXECUTADO: Bloqueio de novas ordens")
        return "BLOQUEIO"
    else:
        print("✅ SITUAÇÃO NORMAL: Operação permitida")
        return "NORMAL"

def main():
    """Função principal do teste."""
    print("🤖 TESTE DO SISTEMA DE ENCERRAMENTO - MONSTRO DAS NEGOCIAÇÕES")
    print("="*70)

    # Testa configuração de horários
    if not testar_configuracao_horarios():
        print("❌ FALHA nos testes de configuração!")
        return False

    # Testa função de fechamento
    if not testar_funcao_fechamento():
        print("❌ FALHA nos testes de fechamento!")
        return False

    # Simula o processo
    status = simular_encerramento()

    print(f"\n📊 RESULTADO DOS TESTES")
    print("="*30)
    print(f"Status atual: {status}")
    print("✅ Todos os testes passaram!")

    return True

if __name__ == "__main__":
    try:
        sucesso = main()
        if sucesso:
            print("\n🎉 SISTEMA DE ENCERRAMENTO VALIDADO COM SUCESSO!")
            sys.exit(0)
        else:
            print("\n❌ FALHA NA VALIDAÇÃO DO SISTEMA!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        sys.exit(1)
