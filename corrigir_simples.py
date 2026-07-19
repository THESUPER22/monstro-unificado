#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def corrigir_simples():
    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Correções específicas para os erros conhecidos
    correcoes = [
        # Corrige indentação após if
        ('        if acao not in ["BUY", "SELL"]:\n        logging.debug(',
         '        if acao not in ["BUY", "SELL"]:\n            logging.debug('),

        ('        f"Ignorando registro de operação para ação inválida: {acao}")\n        return',
         '                f"Ignorando registro de operação para ação inválida: {acao}")\n            return'),

        ('        if len(self.historico_acoes) > 10:\n        self.historico_acoes.pop(0)',
         '        if len(self.historico_acoes) > 10:\n            self.historico_acoes.pop(0)'),

        ('        if lucro < -25.0:\n        self.losses_sequencia[acao] += 1',
         '        if lucro < -25.0:\n            self.losses_sequencia[acao] += 1'),

        ('        if self.losses_sequencia[acao] >= MAX_LOSSES_SEQUENCIA:\n        self.bloquear_lado(acao)',
         '        if self.losses_sequencia[acao] >= MAX_LOSSES_SEQUENCIA:\n            self.bloquear_lado(acao)'),

        # Corrige outras indentações comuns
        ('    for s in symbols:\n    if re.fullmatch',
         '    for s in symbols:\n        if re.fullmatch'),

        ('        if exp_ts and exp_ts > agora_ts:\n        candidatas.append(s)',
         '            if exp_ts and exp_ts > agora_ts:\n                candidatas.append(s)'),
    ]

    for antes, depois in correcoes:
        conteudo = conteudo.replace(antes, depois)

    # Salva arquivo corrigido
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        f.write(conteudo)

    print("Correções aplicadas!")


if __name__ == "__main__":
    corrigir_simples()
