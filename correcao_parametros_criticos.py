#!/usr/bin/env python3
"""
🔧 CORREÇÃO CRÍTICA: PARÂMETROS ESSENCIAIS
Corrige apenas os parâmetros mais críticos que estão causando perdas
"""


def corrigir_parametros_criticos():
    """Corrige os parâmetros mais críticos do robô."""

    # Lê o arquivo
    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Correções críticas
    correcoes = {
        'MIN_EXPERIENCIAS_TREINO = 3': 'MIN_EXPERIENCIAS_TREINO = 50   # 🔧 AUMENTADO: Mínimo de experiências para treino\n',
        'LIMITE_EXPERIENCIAS_PARA_TREINO = 10': 'LIMITE_EXPERIENCIAS_PARA_TREINO = 5  # 🔧 REDUZIDO: Treina mais frequentemente\n',
        'LOSS_DIARIO_CB = -1000.0': 'LOSS_DIARIO_CB = -500.0      # 🔧 REDUZIDO: Stop loss diário mais rigoroso\n',
        'SPREAD_MAXIMO_CB = 20': 'SPREAD_MAXIMO_CB = 10        # 🔧 REDUZIDO: Spread máximo mais rigoroso\n'
    }

    # Aplica correções
    for i, line in enumerate(lines):
        for original, correcao in correcoes.items():
            if original in line:
                lines[i] = correcao
                print(f"✅ Corrigido: {original.split('=')[0].strip()}")

    # Salva arquivo corrigido
    with open("monstro_unificado_v2.py", "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("\n🎯 CORREÇÕES APLICADAS:")
    print("1. Aumentado mínimo de experiências para treino (3 → 50)")
    print("2. Reduzido intervalo entre treinos (10 → 5)")
    print("3. Reduzido limite de perda diária (R$1000 → R$500)")
    print("4. Reduzido spread máximo permitido (20 → 10)")


if __name__ == "__main__":
    corrigir_parametros_criticos()
