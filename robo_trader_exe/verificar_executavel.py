#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR DE EXECUTAVEL - ROBO TRADER MONSTRO
Verifica se todos os arquivos necessarios estao presentes
"""

import json
import os
from datetime import datetime


def verificar_arquivos_essenciais():
    """Verifica se todos os arquivos essenciais estao presentes"""
    print("Verificando arquivos essenciais...")

    arquivos_obrigatorios = [
        "monstro_unificado_v2.py",
        "config_win_v2.json",
        "config.json",
        "EA_BookData_Universal.mq5",
        "requirements.txt",
        "build_exe_final.py"
    ]

    arquivos_opcionais = [
        "modelo_monstro.h5",
        "modelo_monstro_win.h5",
        "historico_contexto.csv",
        "historico_contexto_win.csv",
        "decisions.csv",
        "memoria.pkl",
        "parametros_ia_saida.json"
    ]

    print("\n=== ARQUIVOS OBRIGATORIOS ===")
    faltando_obrigatorios = []
    for arquivo in arquivos_obrigatorios:
        if os.path.exists(arquivo):
            print(f"✅ {arquivo}")
        else:
            print(f"❌ {arquivo} - FALTANDO!")
            faltando_obrigatorios.append(arquivo)

    print("\n=== ARQUIVOS OPCIONAIS ===")
    for arquivo in arquivos_opcionais:
        if os.path.exists(arquivo):
            print(f"✅ {arquivo}")
        else:
            print(f"⚠️  {arquivo} - Sera criado automaticamente")

    return len(faltando_obrigatorios) == 0


def verificar_configuracoes():
    """Verifica se as configuracoes estao corretas"""
    print("\n=== VERIFICANDO CONFIGURACOES ===")

    configs = ["config.json", "config_win_v2.json"]

    for config_file in configs:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                print(f"✅ {config_file} - JSON valido")

                # Verifica campos importantes
                campos_importantes = ["symbol_prefix",
                                      "volume_padrao", "sl_points", "tp_points"]
                for campo in campos_importantes:
                    if campo in config:
                        print(f"   ✅ {campo}: {config[campo]}")
                    else:
                        print(f"   ⚠️  {campo}: Nao encontrado")

            except Exception as e:
                print(f"❌ {config_file} - Erro: {e}")
        else:
            print(f"❌ {config_file} - Nao encontrado")


def verificar_ea_mql5():
    """Verifica o Expert Advisor MQL5"""
    print("\n=== VERIFICANDO EA MQL5 ===")

    ea_file = "EA_BookData_Universal.mq5"
    if os.path.exists(ea_file):
        print(f"✅ {ea_file} encontrado")

        # Verifica conteudo basico
        with open(ea_file, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        verificacoes = [
            ("OnInit", "Funcao de inicializacao"),
            ("OnDeinit", "Funcao de finalizacao"),
            ("UpdateBookData", "Funcao de atualizacao do book"),
            ("book_data.csv", "Geracao de arquivo CSV"),
            ("MarketBookAdd", "Ativacao do book")
        ]

        for item, descricao in verificacoes:
            if item in conteudo:
                print(f"   ✅ {descricao}")
            else:
                print(f"   ⚠️  {descricao} - Nao encontrado")
    else:
        print(f"❌ {ea_file} - NAO ENCONTRADO!")


def verificar_dependencias():
    """Verifica o arquivo requirements.txt"""
    print("\n=== VERIFICANDO DEPENDENCIAS ===")

    if os.path.exists("requirements.txt"):
        with open("requirements.txt", 'r', encoding='utf-8') as f:
            deps = f.read()

        deps_importantes = [
            "tensorflow",
            "keras",
            "MetaTrader5",
            "flask",
            "numpy",
            "pandas",
            "scikit-learn"
        ]

        print("✅ requirements.txt encontrado")
        for dep in deps_importantes:
            if dep in deps:
                print(f"   ✅ {dep}")
            else:
                print(f"   ⚠️  {dep} - Nao listado")
    else:
        print("❌ requirements.txt - NAO ENCONTRADO!")


def gerar_relatorio():
    """Gera relatorio final"""
    print("\n" + "="*60)
    print("    RELATORIO FINAL DE VERIFICACAO")
    print("="*60)

    # Conta arquivos
    total_arquivos = len([f for f in os.listdir('.') if os.path.isfile(f)])
    print(f"Total de arquivos: {total_arquivos}")

    # Tamanho total
    tamanho_total = 0
    for f in os.listdir('.'):
        if os.path.isfile(f):
            tamanho_total += os.path.getsize(f)

    tamanho_mb = tamanho_total / (1024 * 1024)
    print(f"Tamanho total: {tamanho_mb:.1f} MB")

    # Status geral
    arquivos_ok = verificar_arquivos_essenciais()

    if arquivos_ok:
        print("\n✅ PROJETO PRONTO PARA BUILD!")
        print("Execute: executar_build.bat")
    else:
        print("\n❌ PROJETO NAO ESTA PRONTO!")
        print("Corrija os arquivos faltando primeiro")

    print(
        f"\nVerificacao realizada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


def main():
    """Funcao principal"""
    print("="*60)
    print("    VERIFICADOR DE EXECUTAVEL - ROBO TRADER MONSTRO")
    print("="*60)

    verificar_arquivos_essenciais()
    verificar_configuracoes()
    verificar_ea_mql5()
    verificar_dependencias()
    gerar_relatorio()


if __name__ == "__main__":
    main()
