#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 LIMPEZA CRÍTICA - MEMÓRIA CONTAMINADA
Remove arquivos de dados antigos para permitir que o robô comece com memória limpa
focada apenas em experiências positivas.

CORREÇÕES IMPLEMENTADAS:
✅ C1: Filtro de memória (apenas experiências positivas)
✅ C2: Features de profundidade do book corrigidas
✅ C3: Treinamento acelerado (3 experiências)
✅ C4: Lucro real dominante (85% vs 15%)
"""

import logging
import os
import shutil
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def fazer_backup_seguro(arquivo):
    """Faz backup do arquivo antes de deletar."""
    if os.path.exists(arquivo):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_nome = f"{arquivo}.backup_contaminado_{timestamp}"
        try:
            shutil.copy2(arquivo, backup_nome)
            logging.info(f"✅ Backup criado: {backup_nome}")
            return True
        except Exception as e:
            logging.error(f"❌ Erro ao criar backup de {arquivo}: {e}")
            return False
    return True


def limpar_memoria_contaminada():
    """Remove arquivos de dados contaminados para reinício limpo."""

    arquivos_para_limpar = [
        'historico_contexto_win.csv',
        'decisions.csv',
        'experiencias.json',
        'experiencias_finais.json',
        'monstro_v2.log'
    ]

    print("🚨 INICIANDO LIMPEZA DE MEMÓRIA CONTAMINADA")
    print("=" * 60)
    print("PROBLEMA IDENTIFICADO:")
    print("• Apenas 1.10% das experiências eram positivas")
    print("• Modelo aprendia com 98.9% de fracassos")
    print("• Features de book com valores NaN")
    print("• Perda de R$1000/dia por 30 dias")
    print("=" * 60)

    arquivos_removidos = 0

    for arquivo in arquivos_para_limpar:
        if os.path.exists(arquivo):
            # Faz backup antes de remover
            if fazer_backup_seguro(arquivo):
                try:
                    os.remove(arquivo)
                    logging.info(f"🗑️ REMOVIDO: {arquivo}")
                    arquivos_removidos += 1
                except Exception as e:
                    logging.error(f"❌ Erro ao remover {arquivo}: {e}")
            else:
                logging.warning(f"⚠️ Backup falhou, mantendo {arquivo}")
        else:
            logging.info(f"ℹ️ Arquivo não existe: {arquivo}")

    print("\n" + "=" * 60)
    print("✅ CORREÇÕES IMPLEMENTADAS NO CÓDIGO:")
    print("• C1: Filtro agressivo - apenas experiências positivas")
    print("• C2: Features de profundidade do book corrigidas")
    print("• C3: Treinamento acelerado (10→3 experiências)")
    print("• C4: Lucro real dominante (60%→85% peso)")
    print("=" * 60)

    print(f"\n🧹 LIMPEZA CONCLUÍDA: {arquivos_removidos} arquivos removidos")
    print("\n🚀 PRÓXIMOS PASSOS:")
    print("1. Execute: python monstro_unificado_v2.py")
    print("2. Monitore os logs para confirmar aprendizado positivo")
    print("3. Verifique se features de book estão sendo registradas")
    print("4. Acompanhe a taxa de acerto nas primeiras operações")

    return arquivos_removidos > 0


if __name__ == "__main__":
    try:
        sucesso = limpar_memoria_contaminada()
        if sucesso:
            print("\n✅ SISTEMA PRONTO PARA REINÍCIO COM MEMÓRIA LIMPA!")
        else:
            print("\n⚠️ Nenhum arquivo foi removido. Sistema pode já estar limpo.")
    except Exception as e:
        logging.error(f"❌ Erro durante limpeza: {e}")
        print("\n❌ ERRO DURANTE LIMPEZA - Verifique os logs")
