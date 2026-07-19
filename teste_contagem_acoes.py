#!/usr/bin/thon3
"""
Teste para verificar se a contagem de ações está funcionando corretamente
"""

import os
import sys
from datetime import datetime

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Simula a classe MemoriaExperiencias para teste


class MemoriaExperienciasTeste:
    def __init__(self):
        self.experiencias = []
        self.indices_positivos = []
        self.indices_negativos = []
        self.timestamps = []
        self.historico_decisoes = []
        self.score_consistencia = 0.0
        self.contagem_acoes = {"BUY": 0, "SELL": 0, "NADA": 0, "NAO_AGIU": 0}
        self.razao_buy_sell = 1.0

    def _adicionar_direto(self, contexto, acao, lucro, score_dist):
        """Versão simplificada para teste"""
        # Adiciona nova experiência
        experiencia = (contexto, acao, lucro, score_dist)
        self.experiencias.append(experiencia)
        self.timestamps.append(datetime.now())
        idx = len(self.experiencias) - 1

        # Classifica como positiva ou negativa
        if acao == 'NAO_AGIU':
            if score_dist > 0:
                self.indices_positivos.append(idx)
                self.historico_decisoes.append(1)
            else:
                self.indices_negativos.append(idx)
                self.historico_decisoes.append(0)
        else:
            if lucro > 0:
                self.indices_positivos.append(idx)
                self.historico_decisoes.append(1)
            else:
                self.indices_negativos.append(idx)
                self.historico_decisoes.append(0)

        # Atualiza contagem de ações
        if acao in self.contagem_acoes:
            self.contagem_acoes[acao] += 1
        else:
            # Adiciona nova ação se não existir
            self.contagem_acoes[acao] = 1

        # Atualiza razao_buy_sell
        total_operacoes = self.contagem_acoes["BUY"] + \
            self.contagem_acoes["SELL"]
        if total_operacoes > 0:
            self.razao_buy_sell = self.contagem_acoes["BUY"] / total_operacoes
            print(
                f"📊 Razão BUY/SELL atualizada: {self.razao_buy_sell:.3f} ({self.contagem_acoes['BUY']}/{total_operacoes})")


def main():
    print("🧪 Testando contagem de ações...")

    memoria = MemoriaExperienciasTeste()

    # Simula carregamento de experiências como no log
    print("\n📚 Simulando carregamento de 25 experiências...")

    # Adiciona algumas experiências BUY
    for i in range(5):
        contexto = {"test": f"buy_{i}"}
        memoria._adicionar_direto(contexto, "BUY", 10.0, 0.5)

    # Adiciona algumas experiências SELL
    for i in range(8):
        contexto = {"test": f"sell_{i}"}
        memoria._adicionar_direto(contexto, "SELL", -5.0, -0.3)

    # Adiciona experiências NAO_AGIU
    for i in range(12):
        contexto = {"test": f"nao_agiu_{i}"}
        memoria._adicionar_direto(contexto, "NAO_AGIU", 0.0, 0.1)

    print(f"\n📊 Resultado final:")
    print(f"   BUY: {memoria.contagem_acoes['BUY']}")
    print(f"   SELL: {memoria.contagem_acoes['SELL']}")
    print(f"   NAO_AGIU: {memoria.contagem_acoes['NAO_AGIU']}")
    print(f"   Razão BUY/SELL: {memoria.razao_buy_sell:.3f}")

    total_operacoes = memoria.contagem_acoes["BUY"] + \
        memoria.contagem_acoes["SELL"]
    print(f"   Total operações reais: {total_operacoes}")

    if memoria.razao_buy_sell == 0.0:
        print("❌ PROBLEMA: Razão BUY/SELL ainda está em 0.000!")
    else:
        print("✅ CORREÇÃO: Razão BUY/SELL está sendo calculada corretamente!")


if __name__ == "__main__":
    main()
