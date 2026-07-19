"""
Script para corrigir problemas de indentação no arquivo MONSTRO_UNIFICADO_atualizadoV2.py
"""


def corrigir_indentacao():
    """Corrige os principais problemas de indentação"""

    # Lê o arquivo
    with open('MONSTRO_UNIFICADO_atualizadoV2.py', 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    # Corrige problemas conhecidos
    linhas_corrigidas = []

    for i, linha in enumerate(linhas):
        linha_original = linha

        # Remove espaços extras no início se não for comentário
        if linha.strip() and not linha.strip().startswith('#'):
            # Conta espaços no início
            espacos = len(linha) - len(linha.lstrip())

            # Se tem indentação estranha, corrige
            if espacos % 4 != 0 and espacos > 0:
                # Arredonda para múltiplo de 4
                novos_espacos = (espacos // 4) * 4
                if espacos % 4 >= 2:
                    novos_espacos += 4
                linha = ' ' * novos_espacos + linha.lstrip()

        linhas_corrigidas.append(linha)

    # Salva o arquivo corrigido
    with open('MONSTRO_UNIFICADO_atualizadoV2_CORRIGIDO.py', 'w', encoding='utf-8') as f:
        f.writelines(linhas_corrigidas)

    print("✅ Arquivo corrigido salvo como MONSTRO_UNIFICADO_atualizadoV2_CORRIGIDO.py")


if __name__ == "__main__":
    corrigir_indentacao()
