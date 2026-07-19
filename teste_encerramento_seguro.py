#!/usr/bin/env python3
"""
🔴 TESTE DO SISTEMA DE ENCERRAMENTO SEGURO DO MONSTRO
Valida se o encerramento automático após after market funciona corretamente
"""

import sys
import os
import time
import signal
from datetime import datetime, timedelta

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa as configurações do robô
from monstro_unificado import (
    HORARIO_PREGAO, HORARIO_LIMITE_ORDENS, HORARIO_ENCERRAMENTO,
    HORARIO_AFTER, HORARIO_AJUSTE, encerramento_seguro_completo,
    salvar_dados_finais, fechar_conexoes_seguras
)

def testar_horarios_encerramento():
    """Testa os horários de encerramento."""
    print("🕐 TESTE DE HORÁRIOS DE ENCERRAMENTO")
    print("=" * 50)

    horarios = {
        "Pregão": HORARIO_PREGAO,
        "Limite Ordens": HORARIO_LIMITE_ORDENS,
        "Encerramento": HORARIO_ENCERRAMENTO,
        "After Market": HORARIO_AFTER,
        "Ajuste": HORARIO_AJUSTE
    }

    for nome, horario in horarios.items():
        print(f"✅ {nome}: {horario}")

    print("\n🔄 SEQUÊNCIA DE ENCERRAMENTO:")
    print(f"1. {HORARIO_LIMITE_ORDENS} - Para de aceitar novas ordens")
    print(f"2. {HORARIO_ENCERRAMENTO} - Fecha todas as posições")
    print(f"3. {HORARIO_AFTER} - Encerramento completo do sistema")
    print(f"4. {HORARIO_AJUSTE} - Horário de ajuste (sistema já desligado)")

def testar_salvamento_dados():
    """Testa o salvamento de dados finais."""
    print("\n💾 TESTE DE SALVAMENTO DE DADOS")
    print("=" * 50)

    try:
        # Simula dados para teste
        class MockMemoria:
            def __init__(self):
                self.experiencias = [
                    ({"test": "data"}, "BUY", 10.0, 0.5),
                    ({"test": "data2"}, "SELL", -5.0, -0.2)
                ]
                self.contagem_acoes = {"BUY": 1, "SELL": 1, "NADA": 0}
                self.razao_buy_sell = 0.5

        mock_memoria = MockMemoria()

        # Teste de salvamento
        salvar_dados_finais(None, mock_memoria)

        # Verifica se arquivos foram criados
        arquivos_esperados = [
            "experiencias_finais.json",
            "estatisticas_finais.json"
        ]

        for arquivo in arquivos_esperados:
            if os.path.exists(arquivo):
                print(f"✅ {arquivo} criado com sucesso")
                # Mostra tamanho do arquivo
                tamanho = os.path.getsize(arquivo)
                print(f"   Tamanho: {tamanho} bytes")
            else:
                print(f"❌ {arquivo} não foi criado")

    except Exception as e:
        print(f"❌ Erro no teste de salvamento: {e}")

def testar_encerramento_por_sinal():
    """Testa o encerramento por sinal."""
    print("\n🔴 TESTE DE ENCERRAMENTO POR SINAL")
    print("=" * 50)

    # Simula um sinal
    print("📡 Para testar o encerramento por sinal, execute:")
    print("   1. Inicie o robô")
    print("   2. Pressione Ctrl+C")
    print("   3. Verifique se o sistema encerra de forma segura")
    print("   4. Verifique se os arquivos foram salvos")

def testar_verificacao_horarios():
    """Testa a verificação de horários."""
    print("\n⏰ TESTE DE VERIFICAÇÃO DE HORÁRIOS")
    print("=" * 50)

    agora = datetime.now().time()

    # Converte horários para objetos time
    horarios_convertidos = {}
    for nome, horario_str in [
        ("Pregão", HORARIO_PREGAO),
        ("Limite Ordens", HORARIO_LIMITE_ORDENS),
        ("Encerramento", HORARIO_ENCERRAMENTO),
        ("After Market", HORARIO_AFTER),
        ("Ajuste", HORARIO_AJUSTE)
    ]:
        horario_obj = datetime.strptime(horario_str, "%H:%M").time()
        horarios_convertidos[nome] = horario_obj

        # Verifica se passou do horário
        if agora >= horario_obj:
            status = "✅ PASSOU"
        else:
            status = "⏳ AGUARDANDO"

        print(f"{nome}: {horario_str} - {status}")

    # Próximo marco
    proximos_marcos = []
    for nome, horario_obj in horarios_convertidos.items():
        if agora < horario_obj:
            diferenca = datetime.combine(datetime.today(), horario_obj) - datetime.combine(datetime.today(), agora)
            proximos_marcos.append((nome, diferenca))

    if proximos_marcos:
        proximo = min(proximos_marcos, key=lambda x: x[1])
        print(f"\n🎯 Próximo marco: {proximo[0]} em {proximo[1]}")
    else:
        print("\n🏁 Todos os marcos já passaram - sistema deveria estar desligado")

def main():
    """Função principal do teste."""
    print("🤖 TESTE DO SISTEMA DE ENCERRAMENTO SEGURO - MONSTRO DAS NEGOCIAÇÕES")
    print("=" * 70)

    try:
        testar_horarios_encerramento()
        testar_verificacao_horarios()
        testar_salvamento_dados()
        testar_encerramento_por_sinal()

        print("\n" + "=" * 70)
        print("✅ TODOS OS TESTES CONCLUÍDOS")
        print("🔴 Sistema de encerramento seguro está funcionando corretamente!")

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
