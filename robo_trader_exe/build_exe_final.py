#!/usr/bin/env python3
# -*- codin8 -*-

import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta


def verificar_dependencias():
    print("Verificando dependencias...")

    dependencias = ['pyinstaller']
    faltando = []

    for dep in dependencias:
        try:
            __import__(dep)
            print(f"OK: {dep}")
        except ImportError:
            faltando.append(dep)
            print(f"FALTANDO: {dep}")

    if faltando:
        print(f"Instalando dependencias: {' '.join(faltando)}")
        for dep in faltando:
            subprocess.run([sys.executable, "-m", "pip",
                           "install", dep], check=True)
        print("Dependencias instaladas!")

    return True


def adicionar_protecao_data():
    print("Adicionando protecao por data...")

    data_expiracao = datetime.now() + timedelta(days=30)
    data_str = data_expiracao.strftime("%Y-%m-%d")

    codigo_protecao = f'''
# ========== PROTECAO POR DATA ==========
import sys
from datetime import datetime

def verificar_data_expiracao():
    data_expiracao = datetime.strptime("{data_str}", "%Y-%m-%d")
    data_atual = datetime.now()

    if data_atual > data_expiracao:
        print("\\n" + "="*60)
        print("        PRAZO EXPIRADO")
        print("="*60)
        print("Este software expirou em: {data_str}")
        print("Solicite nova versao para continuar usando.")
        print("="*60)
        input("\\nPressione ENTER para sair...")
        sys.exit(1)

    dias_restantes = (data_expiracao - data_atual).days
    if dias_restantes <= 7:
        print(
            f"\\nAVISO: Software expira em {{dias_restantes}} dias ({data_str})")

verificar_data_expiracao()
# ========== FIM PROTECAO ==========

'''

    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Insere a protecao logo apos os imports
    linhas = conteudo.split('\n')

    # Encontra onde inserir (apos endregion)
    for i, linha in enumerate(linhas):
        if '# endregion' in linha:
            linhas.insert(i + 1, codigo_protecao)
            break

    with open("monstro_unificado_v2_protegido.py", "w", encoding="utf-8") as f:
        f.write('\n'.join(linhas))

    print(f"Protecao adicionada! Expira em: {data_str}")
    return "monstro_unificado_v2_protegido.py"


def criar_executavel(arquivo_principal):
    print("Criando executavel com PyInstaller...")

    # Todos os arquivos que devem ser incluidos
    arquivos_dados = [
        "config_win_v2.json",
        "config.json",
        "EA_BookData_Universal.mq5",
        "modelo_monstro.h5",
        "modelo_monstro_win.h5",
        "modelo_monstro.keras",
        "modelo_monstro_win.keras",
        "historico_contexto.csv",
        "historico_contexto_win.csv",
        "decisions.csv",
        "memoria.pkl",
        "parametros_ia_saida.json",
        "experiencias.json",
        "diagnostico_monstro.py",
        "dashboard_tempo_real.py"
    ]

    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "RoboTraderMonstro",
        "--distpath", "dist_final",
        "--workpath", "build_temp",
        "--clean"
    ]

    # Adiciona arquivos de dados
    for arquivo in arquivos_dados:
        if os.path.exists(arquivo):
            cmd.extend(["--add-data", f"{arquivo};."])
            print(f"Incluindo: {arquivo}")

    # Bibliotecas importantes
    cmd.extend([
        "--hidden-import", "tensorflow",
        "--hidden-import", "keras",
        "--hidden-import", "sklearn",
        "--hidden-import", "MetaTrader5",
        "--hidden-import", "flask",
        "--hidden-import", "scipy",
        "--hidden-import", "numpy",
        "--hidden-import", "pandas"
    ])

    cmd.append(arquivo_principal)

    print("Executando PyInstaller...")
    resultado = subprocess.run(cmd)

    if resultado.returncode == 0:
        print("Executavel criado com sucesso!")
        return True
    else:
        print("Erro ao criar executavel!")
        return False


def criar_documentacao():
    print("Criando documentacao...")

    data_exp = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")

    doc = f'''ROBO TRADER MONSTRO - EXECUTAVEL

INSTALACAO:
1. Extraia todos os arquivos
2. Execute RoboTraderMonstro.exe
3. Certifique-se que MT5 esta aberto
4. Compile e ative o EA_BookData_Universal.mq5

REQUISITOS:
- Windows 10/11
- MetaTrader 5 instalado
- Conexao com internet

CONFIGURACAO MT5:
1. Abra MetaEditor (F4 no MT5)
2. Compile EA_BookData_Universal.mq5
3. Adicione EA no grafico WIN ou WDO
4. Configure: InpUpdateInterval=100

EXPIRACAO: {data_exp}

Para renovacao, entre em contato.
'''

    with open("dist_final/LEIA-ME.txt", "w", encoding="utf-8") as f:
        f.write(doc)


def criar_zip():
    print("Criando arquivo ZIP...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"RoboTraderMonstro_{timestamp}.zip"

    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Executavel
        if os.path.exists("dist_final/RoboTraderMonstro.exe"):
            zipf.write("dist_final/RoboTraderMonstro.exe",
                       "RoboTraderMonstro.exe")

        # EA MQL5
        if os.path.exists("EA_BookData_Universal.mq5"):
            zipf.write("EA_BookData_Universal.mq5",
                       "EA_BookData_Universal.mq5")
            "EA_BookData_Universal.mq5")

            # Documentacao
            if os.path.exists("dist_final/LEIA-ME.txt"):
                 zipf.write("dist_final/LEIA-ME.txt", "LEIA-ME.txt")

                 print(f"ZIP criado: {zip_name}")
            return zip_name


            def main():
                 print("="*60)
                 print("    ROBO TRADER MONSTRO - BUILD FINAL")
                 print("="*60)

                 try:
            # 1. Verificar dependencias
            verificar_dependencias()

                  # 2. Adicionar protecao
                  arquivo_protegido = adicionar_protecao_data()

                  # 3. Criar executavel
                  if not criar_executavel(arquivo_protegido):
                 return False

                  # 4. Criar documentacao
                 criar_documentacao()

                  # 5. Criar ZIP
                  zip_file = criar_zip()

                  print("\n" + "="*60)
                  print("    BUILD CONCLUIDO!")
                  print("="*60)
                  print("Arquivos gerados:")
                  print("- dist_final/RoboTraderMonstro.exe")
                  print("- dist_final/LEIA-ME.txt")
                  print(f"- {zip_file}")
                  print("\nPronto para distribuicao!")

                  return True

                  except Exception as e:
                  print(f"Erro: {e}")
                  return False


                  if __name__ == "__main__":
                  main()
