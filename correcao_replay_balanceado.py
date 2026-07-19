#!/usr/bin/env python3
"""
🔧 CORREÇÃO CRÍTICA: REPLLANCEADO
Substitui a função obter_batch_replay para incluir experiências negativas
"""


def corrigir_replay_balanceado():
    """Corrige a função de replay para incluir experiências negativas."""

    # Lê o arquivo
    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Função de replay balanceado corrigida
    nova_funcao = '''    def obter_batch_replay(self) -> Tuple[List[Tuple[Dict[str, Any], str, float, float]], List[float]]:
        """🔧 CORREÇÃO CRÍTICA: Obtém batch BALANCEADO com experiências positivas E negativas."""
        self.ultimo_replay = datetime.now()

        # Separa experiências por tipo
        exp_positivas = [(i, exp) for i, exp in enumerate(self.experiencias)
                         if i in self.indices_positivos]
        exp_negativas = [(i, exp) for i, exp in enumerate(self.experiencias)
                         if i in self.indices_negativos]

        # Se não há experiências, retorna vazio
        if not exp_positivas and not exp_negativas:
            return [], []

        # Prioriza por valor absoluto do reward
        exp_positivas.sort(key=lambda x: abs(self.experiencias[x[0]][2]), reverse=True)
        exp_negativas.sort(key=lambda x: abs(self.experiencias[x[0]][2]), reverse=True)

        # Balanceamento 50/50
        n_batch = min(BATCH_SIZE, len(exp_positivas) + len(exp_negativas))
        n_positivas = min(n_batch // 2, len(exp_positivas))
        n_negativas = min(n_batch - n_positivas, len(exp_negativas))

        # Completa com o tipo disponível se necessário
        if n_positivas + n_negativas < n_batch:
            if len(exp_positivas) > n_positivas:
                n_positivas = min(n_batch - n_negativas, len(exp_positivas))
            elif len(exp_negativas) > n_negativas:
                n_negativas = min(n_batch - n_positivas, len(exp_negativas))

        # Seleciona experiências
        indices_replay = []
        if n_positivas > 0:
            indices_replay.extend([idx for idx, _ in exp_positivas[:n_positivas]])
        if n_negativas > 0:
            indices_replay.extend([idx for idx, _ in exp_negativas[:n_negativas]])

        batch = [self.experiencias[i] for i in indices_replay]
        decays = [PESO_REPLAY * self.calcular_decay(self.timestamps[i]) for i in indices_replay]

        # Log crítico para monitoramento
        logging.info(f"🎯 REPLAY BALANCEADO: {n_positivas} positivas + {n_negativas} negativas = {len(batch)} total")

        return batch, decays'''

    # Encontra e substitui a função original
    import re

    # Padrão para encontrar a função original
    pattern = r'def obter_batch_replay\(self\).*?return batch, decays'

    # Substitui
    content_novo = re.sub(pattern, nova_funcao.strip(),
                          content, flags=re.DOTALL)

    if content_novo != content:
        # Salva o arquivo corrigido
        with open("monstro_unificado_v2.py", "w", encoding="utf-8") as f:
            f.write(content_novo)
        print("✅ Função obter_batch_replay corrigida com sucesso!")
        print("🎯 Agora o robô vai aprender com experiências positivas E negativas")
    else:
        print("❌ Não foi possível encontrar/substituir a função")


if __name__ == "__main__":
    corrigir_replay_balanceado()
