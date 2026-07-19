#!/usr/bthon3
"""
Aplica apenas as correções essenciais de indentação identificadas
"""


def aplicar_correcoes():
    with open('monstro_unificado_v2.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Lista das correções específicas que já identificamos
    correcoes = [
        # Cooldown
        ('            if self.losses_seguidos == 1:\n        cooldown_segundos = 300',
         '            if self.losses_seguidos == 1:\n                cooldown_segundos = 300'),
        ('            elif self.losses_seguidos == 2:\n        cooldown_segundos = 600',
         '            elif self.losses_seguidos == 2:\n                cooldown_segundos = 600'),
        ('            else:\n        cooldown_segundos = 900',
         '            else:\n                cooldown_segundos = 900'),

        # MonitorPerformance
        ('        def registrar_operacao(self, lucro: float, modo: str):',
         '    def registrar_operacao(self, lucro: float, modo: str):'),
        ('        if len(self.operacoes_recentes) > 10:\n        self.operacoes_recentes.pop(0)',
         '        if len(self.operacoes_recentes) > 10:\n            self.operacoes_recentes.pop(0)'),

        # Classes
        ('        class MonitorPerformance:', 'class MonitorPerformance:'),
        ('        class GerenciadorDeSaida:', 'class GerenciadorDeSaida:'),
        ('        class FiltroSpreadDinamico:', 'class FiltroSpreadDinamico:'),
    ]

    # Aplica as correções
    for old, new in correcoes:
        content = content.replace(old, new)

    # Salva o arquivo
    with open('monstro_unificado_v2.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Correções essenciais aplicadas!")


if __name__ == "__main__":
    aplicar_correcoes()
