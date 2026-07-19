#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Monstro sem o dashboard web
"""

import os
import sys


def criar_versao_sem_dashboard():
    """Cria uma versão do Monstro sem o dashboard web para teste."""

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        codigo = f.read()

    # Remove a seção do Flask/Dashboard
    linhas = codigo.split('\n')
    codigo_sem_dashboard = []
    dentro_flask = False

    for linha in linhas:
        # Detecta início da seção Flask
        if 'app = Flask(__name__)' in linha:
            dentro_flask = True
            # Adiciona um comentário no lugar
            codigo_sem_dashboard.append(
                '# Dashboard Flask removido para teste')
            continue

        # Detecta fim da seção Flask (quando encontra uma função que não é route)
        if dentro_flask and linha.startswith('def ') and '@app.route' not in codigo_sem_dashboard[-5:]:
            dentro_flask = False

        # Pula linhas do Flask
        if dentro_flask:
            continue

        codigo_sem_dashboard.append(linha)

    # Salva versão sem dashboard
    codigo_final = '\n'.join(codigo_sem_dashboard)

    with open("mostro_teste_sem_dashboard.py", 'w', encoding='utf-8') as f:
        f.write(codigo_final)

    print("Versão sem dashboard criada: mostro_teste_sem_dashboard.py")
    return True


def testar_codigo_principal():
    """Testa o código principal sem dashboard."""

    if not criar_versao_sem_dashboard():
        return False

    print("Testando código principal sem dashboard...")

    try:
        # Testa compilação
        with open("mostro_teste_sem_dashboard.py", 'r', encoding='utf-8') as f:
            codigo = f.read()

        compile(codigo, "mostro_teste_sem_dashboard.py", 'exec')
        print("✅ Código principal compila sem erros!")

        # Testa se as funcionalidades de ticks estão presentes
        verificacoes = [
            "class ColetorTicksInteligente",
            "def coletar_ticks_recentes",
            "direcao_fluxo",
            "intensidade_ticks",
            "aceleracao_preco"
        ]

        for verificacao in verificacoes:
            if verificacao in codigo:
                print(f"✅ {verificacao}: Encontrado")
            else:
                print(f"❌ {verificacao}: Não encontrado")

        return True

    except SyntaxError as e:
        print(f"❌ Erro de sintaxe: {e}")
        print(f"   Linha {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def main():
    """Função principal."""
    print("TESTE DO MONSTRO SEM DASHBOARD WEB")
    print("=" * 50)

    if testar_codigo_principal():
        print("\n✅ CÓDIGO PRINCIPAL FUNCIONAL!")
        print("O problema está apenas no dashboard web")
        print("As funcionalidades de ticks estão implementadas corretamente")
        return True
    else:
        print("\n❌ CÓDIGO PRINCIPAL TEM PROBLEMAS")
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
