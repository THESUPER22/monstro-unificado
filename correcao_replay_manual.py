#!/usr/bin/env python3
"""
🔧 CORREÇÃO MANUAL DO REPLAY ENVIESADO
Corrige manualmente a função que só aprende com lucros
"""


def corrigir_replay_manual():
    """Corrige manualmente a função de replay enviesado."""

    # Lê o arquivo
    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Encontra a linha que filtra só experiências positivas
    linha_problema = "if i in self.indices_positivos"

    if linha_problema in content:
        # Substitui por uma versão que inclui negativas também
        content = content.replace(
            "exp_positivas = [(i, exp) for i, exp in enumerate(self.experiencias)\n                         if i in self.indices_positivos]",
            """# 🔧 CORREÇÃO CRÍTICA: Inclui experiências positivas E negativas
        exp_positivas = [(i, exp) for i, exp in enumerate(self.experiencias)
                         if i in self.indices_positivos]
        exp_negativas = [(i, exp) for i, exp in enumerate(self.experiencias)
                         if i in self.indices_negativos]

        # Combina e prioriza por valor absoluto do reward
        todas_exp = exp_positivas + exp_negativas
        todas_exp.sort(key=lambda x: abs(self.experiencias[x[0]][2]), reverse=True)"""
        )

        # Substitui a seleção para usar todas as experiências
        content = content.replace(
            "if not exp_positivas:\n            return [], []",
            """if not todas_exp:
            return [], []"""
        )

        content = content.replace(
            "exp_positivas.sort(key=lambda x: self.timestamps[x[0]])",
            "# Já ordenado por valor absoluto do reward acima"
        )

        content = content.replace(
            "indices_replay = [idx for idx, _ in exp_positivas[:n_replay]]",
            "indices_replay = [idx for idx, _ in todas_exp[:n_replay]]"
        )

        # Salva arquivo corrigido
        with open("monstro_unificado_v2.py", "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ CORREÇÃO CRÍTICA APLICADA:")
        print("🎯 Replay agora inclui experiências POSITIVAS e NEGATIVAS")
        print("🎯 Priorização por valor absoluto do reward")
        print("🎯 Robô vai aprender com seus erros!")
    else:
        print("❌ Não foi possível encontrar a linha problema")


if __name__ == "__main__":
    corrigir_replay_manual()
