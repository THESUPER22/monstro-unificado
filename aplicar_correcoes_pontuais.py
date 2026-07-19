#!/usr/bin/env python3
"""
🔧 APLICAÇÃO PONTUAL DAS CORREÇÕES CRÍT
Aplica apenas as correções essenciais sem quebrar o código
"""


def aplicar_correcoes_pontuais():
    """Aplica correções pontuais no arquivo do robô."""

    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # CORREÇÃO 1: Parâmetros de treinamento
    for i, line in enumerate(lines):
        if "MIN_EXPERIENCIAS_TREINO = 3" in line:
            lines[i] = "MIN_EXPERIENCIAS_TREINO = 50   # 🔧 AUMENTADO (era 3)\n"
            print("✅ MIN_EXPERIENCIAS_TREINO corrigido: 3 → 50")

        elif "EPOCHS_TREINO = 3" in line:
            lines[i] = "EPOCHS_TREINO = 5              # 🔧 AUMENTADO (era 3)\n"
            print("✅ EPOCHS_TREINO corrigido: 3 → 5")

        elif "BATCH_SIZE = 32" in line:
            lines[i] = "BATCH_SIZE = 64                # 🔧 AUMENTADO (era 32)\n"
            print("✅ BATCH_SIZE corrigido: 32 → 64")

        elif "PESO_REPLAY = 0.3" in line:
            lines[i] = "PESO_REPLAY = 1.0              # 🔧 AUMENTADO (era 0.3)\n"
            print("✅ PESO_REPLAY corrigido: 0.3 → 1.0")

        elif "LIMITE_EXPERIENCIAS_PARA_TREINO = 10" in line:
            lines[i] = "LIMITE_EXPERIENCIAS_PARA_TREINO = 5  # 🔧 REDUZIDO (era 10)\n"
            print("✅ LIMITE_EXPERIENCIAS_PARA_TREINO corrigido: 10 → 5")

    # CORREÇÃO 2: Circuit breakers
    for i, line in enumerate(lines):
        if '"max_loss_diario", -1000.0' in line:
            lines[i] = line.replace(
                '-1000.0', '-500.0   # 🔧 REDUZIDO (era -1000)')
            print("✅ MAX_LOSS_DIARIO corrigido: -1000 → -500")

        elif "LOSS_DIARIO_CB = -1000.0" in line:
            lines[i] = "LOSS_DIARIO_CB = -500.0      # 🔧 REDUZIDO (era -1000)\n"
            print("✅ LOSS_DIARIO_CB corrigido: -1000 → -500")

        elif "SPREAD_MAXIMO_CB = 20" in line:
            lines[i] = "SPREAD_MAXIMO_CB = 10        # 🔧 REDUZIDO (era 20)\n"
            print("✅ SPREAD_MAXIMO_CB corrigido: 20 → 10")

    # CORREÇÃO 3: Reativar circuit breaker de 3 losses
    for i, line in enumerate(lines):
        if "# CB1: 3 losses seguidos - TEMPORARIAMENTE DESABILITADO" in line:
            # Encontra o bloco comentado e descomenta
            j = i + 1
            while j < len(lines) and ("# return True" not in lines[j]):
                if lines[j].strip().startswith("# if self.losses_seguidos >= 3:"):
                    lines[j] = "        if self.losses_seguidos >= 3:\n"
                elif lines[j].strip().startswith("#     self.bloqueado = True"):
                    lines[j] = "            self.bloqueado = True\n"
                elif lines[j].strip().startswith("#     self.motivo_bloqueio ="):
                    lines[
                        j] = "            self.motivo_bloqueio = f\"🚨 3 losses seguidos (atual: {self.losses_seguidos})\"\n"
                elif lines[j].strip().startswith("#     return True"):
                    lines[j] = "            return True\n"
                j += 1
            print("✅ Circuit breaker de 3 losses REATIVADO")
            break

    # Salva arquivo corrigido
    with open("monstro_unificado_v2.py", "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("\n🎯 RESUMO DAS CORREÇÕES APLICADAS:")
    print("1. Parâmetros de treinamento otimizados")
    print("2. Circuit breakers mais rigorosos")
    print("3. Circuit breaker de 3 losses reativado")
    print("\n⚠️  AINDA NECESSÁRIO (manual):")
    print("1. Corrigir função obter_batch_replay para incluir experiências negativas")
    print("2. Adicionar sistema anti-overtrading")
    print("3. Melhorar logging de monitoramento")


if __name__ == "__main__":
    aplicar_correcoes_pontuais()
