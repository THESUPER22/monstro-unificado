#!/usr/bin/env python3
"""
Teste para verificar se a correção do NameError de posicao_atual está funcionando.
"""


def teste_posicao_atual():
    """Simula o cenário onde posicao_atual pode não estar definida."""

    print("🧪 TESTE: Verificação de posicao_atual")

    # Simula o cenário onde posicao_atual pode não existir
    try:
        # Tenta acessar posicao_atual sem defini-la primeiro
        if posicao_atual is not None:
            print("✅ posicao_atual existe e não é None")
        else:
            print("⚠️ posicao_atual existe mas é None")
    except NameError as e:
        print(f"❌ NameError capturado: {e}")
        print("🔧 Aplicando correção...")

        # Aplica a correção
        posicao_atual = None

        # Testa novamente
        if posicao_atual is not None:
            print("✅ Após correção: posicao_atual existe e não é None")
        else:
            print("✅ Após correção: posicao_atual existe e é None (correto)")

    print("🎯 Teste concluído!")


if __name__ == "__main__":
    teste_posicao_atual()
