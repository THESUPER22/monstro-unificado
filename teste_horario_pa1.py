#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE DA TRAVA DE HORÁRIO PA1
Testa se a função horario_permitido está funcionando corretamente
"""

from datetime import datetime
from datetime import time as dtime


def horario_permitido() -> bool:
    """
    ✅ PA1: TRAVA DE HORÁRIO: Só permite operações entre 09:00-10:00 e 15:00-17:30
    """
    agora = datetime.now().time()

    # DEBUG: Log detalhado do horário atual
    horario_str = agora.strftime("%H:%M:%S")

    # Horário 1: 09:00 às 10:00 (abertura - alta volatilidade)
    if dtime(9, 0) <= agora <= dtime(10, 0):
        print(f"✅ PA1 HORÁRIO PERMITIDO: {horario_str} (janela 09:00-10:00)")
        return True

    # Horário 2: 15:00 às 17:30 (final do dia - movimentos institucionais)
    if dtime(15, 0) <= agora <= dtime(17, 30):
        print(f"✅ PA1 HORÁRIO PERMITIDO: {horario_str} (janela 15:00-17:30)")
        return True

    # Fora dos horários permitidos
    print(
        f"🚫 PA1 HORÁRIO BLOQUEADO: {horario_str} (fora das janelas permitidas)")
    return False


if __name__ == "__main__":
    print("🧪 TESTE DA TRAVA DE HORÁRIO PA1")
    print("=" * 50)

    horario_atual = datetime.now().strftime("%H:%M:%S")
    print(f"Horário atual: {horario_atual}")

    resultado = horario_permitido()

    print("=" * 50)
    print(f"Resultado: {'PERMITIDO' if resultado else 'BLOQUEADO'}")
    print("\n📋 Horários permitidos:")
    print("  • 09:00 às 10:00 (abertura)")
    print("  • 15:00 às 17:30 (final do dia)")
