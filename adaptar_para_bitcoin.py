#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adaptar o Monstro para operar BITN25
Mantém backup e permite volta rápida para WDO
"""

import json
import shutil
import os
from datetime import datetime

def criar_backup():
    """Cria backup dos arquivos principais"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_wdo_{timestamp}"

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    arquivos_backup = [
        "monstro_unificado.py",
        "config.json",
        "modelo_monstro.h5"
    ]

    for arquivo in arquivos_backup:
        if os.path.exists(arquivo):
            shutil.copy2(arquivo, os.path.join(backup_dir, arquivo))
            print(f"✅ Backup: {arquivo} → {backup_dir}/")

    return backup_dir

def adaptar_codigo_para_bitcoin():
    """Adapta o código principal para BITN25"""

    print("📝 Adaptando código para BITN25...")

    # Ler o arquivo atual
    with open("monstro_unificado.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Substituições necessárias
    adaptacoes = [
        # Função de símbolo dinâmico
        ('def get_front_month_symbol_dynamic(prefix="WDO") -> str:',
         'def get_front_month_symbol_dynamic(prefix="BITN") -> str:'),

        # Comentário da função
        ('"""Busca no MT5 todos os contratos prefixados por WDO, filtra por trade_mode FULL',
         '"""Busca no MT5 todos os contratos prefixados por BITN, filtra por trade_mode FULL'),

        # Mensagem de erro
        ('logging.error("❌ Nenhum contrato mensal WDO* ativo encontrado. Usando WDO$ como fallback.")',
         'logging.error("❌ Nenhum contrato mensal BITN* ativo encontrado. Usando BITN25 como fallback.")'),

        # Fallback symbol
        ('return "WDO$"', 'return "BITN25"'),

        # Volume padrão
        ('VOLUME_PADRAO = 1.0', 'VOLUME_PADRAO = 10.0'),

        # Volume mínimo book
        ('VOLUME_MINIMO_BOOK = 10', 'VOLUME_MINIMO_BOOK = 100'),

        # Drawdown ajustado
        ('MAX_DRAWDOWN = -250.0', 'MAX_DRAWDOWN = -1000.0'),

        # SL maior para Bitcoin
        ('SL_MAX_PONTOS = 15', 'SL_MAX_PONTOS = 50'),

        # Exemplo no comentário
        ('# Extrai a validade do símbolo (ex: WDON25 -> N25)',
         '# Extrai a validade do símbolo (ex: BITN25 -> N25)'),
    ]

    for original, novo in adaptacoes:
        if original in conteudo:
            conteudo = conteudo.replace(original, novo)
            print(f"✅ Adaptado: {original[:50]}...")
        else:
            print(f"⚠️  Não encontrado: {original[:50]}...")

    # Salvar arquivo adaptado
    with open("monstro_unificado.py", "w", encoding="utf-8") as f:
        f.write(conteudo)

    print("✅ Código adaptado para BITN25!")

def aplicar_config_bitcoin():
    """Substitui config.json pelo config_bitcoin.json"""

    print("📝 Aplicando configuração Bitcoin...")

    # Backup do config atual
    shutil.copy2("config.json", "config_wdo_backup.json")

    # Copiar config bitcoin
    shutil.copy2("config_bitcoin.json", "config.json")

    print("✅ Configuração Bitcoin aplicada!")

def main():
    """Executa a adaptação completa"""

    print("🤖 ADAPTADOR MONSTRO → BITCOIN 🪙")
    print("=" * 50)

    # 1. Backup
    backup_dir = criar_backup()
    print(f"✅ Backup criado em: {backup_dir}")

    # 2. Adaptar código
    adaptar_codigo_para_bitcoin()

    # 3. Aplicar config
    aplicar_config_bitcoin()

    print("\n" + "=" * 50)
    print("🎯 ADAPTAÇÃO CONCLUÍDA!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Execute: python monstro_unificado.py")
    print("2. Verifique se conecta no BITN25")
    print("3. Monitore logs em: monstro_bitcoin.log")
    print("\n🔄 PARA VOLTAR WDO:")
    print("1. Pare o bot")
    print(f"2. Restaure do backup: {backup_dir}")
    print("3. Execute: python reverter_para_wdo.py")

    # Criar script de reversão
    criar_script_reversao(backup_dir)

def criar_script_reversao(backup_dir):
    """Cria script para reverter para WDO"""

    script_reversao = f'''#!/usr/bin/env python3
# Script para reverter do Bitcoin para WDO

import shutil
import os

def reverter():
    print("🔄 Revertendo para WDO...")

    backup_dir = "{backup_dir}"

    arquivos = ["monstro_unificado.py", "config.json", "modelo_monstro.h5"]

    for arquivo in arquivos:
        backup_path = os.path.join(backup_dir, arquivo)
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, arquivo)
            print(f"✅ Restaurado: {{arquivo}}")

    print("✅ Reversão concluída! WDO restaurado.")

if __name__ == "__main__":
    reverter()
'''

    with open("reverter_para_wdo.py", "w", encoding="utf-8") as f:
        f.write(script_reversao)

    print("✅ Script de reversão criado: reverter_para_wdo.py")

if __name__ == "__main__":
    main()
