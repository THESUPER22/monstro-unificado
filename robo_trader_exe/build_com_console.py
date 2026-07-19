import os
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta


def main():
    print("="*50)
    print("CRIANDO VERSAO COM CONSOLE VISIVEL")
    print("="*50)

    # Passo 1: Adicionar protecao por data
    print("Adicionando protecao por data...")
    data_exp = datetime.now() + timedelta(days=30)
    data_str = data_exp.strftime("%Y-%m-%d")

    protecao = f'''
# PROTECAO POR DATA
from datetime import datetime
import sys

def verificar_expiracao():
    data_limite = datetime.strptime("{data_str}", "%Y-%m-%d")
    if datetime.now() > data_limite:
        print("PRAZO EXPIRADO - Solicite nova versao")
        input("Pressione ENTER para sair...")
        sys.exit(1)
    print("Sistema valido ate: {data_str}")

verificar_expiracao()
'''

    # Le arquivo original
    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Adiciona protecao no inicio
    conteudo_protegido = protecao + "\n" + conteudo

    # Salva arquivo protegido
    with open("monstro_com_console.py", "w", encoding="utf-8") as f:
        f.write(conteudo_protegido)

    print(f"Protecao adicionada! Expira em: {data_str}")

    # Passo 2: Criar executavel COM CONSOLE
    print("Criando executavel COM CONSOLE...")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--console",  # MOSTRA CONSOLE
        "--name", "RoboTraderMonstro_Console",
        "--distpath", "dist_console"
    ]

    # Adiciona arquivos importantes
    arquivos = [
        "config_win_v2.json",
        "config.json",
        "EA_BookData_Universal.mq5",
        "modelo_monstro.h5",
        "modelo_monstro_win.h5"
    ]

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            cmd.extend(["--add-data", f"{arquivo};."])

    cmd.append("monstro_com_console.py")

    resultado = subprocess.run(cmd)

    if resultado.returncode == 0:
        print("Executavel COM CONSOLE criado com sucesso!")

        print("\n" + "="*50)
        print("VERSAO COM CONSOLE PRONTA!")
        print("="*50)
        print("Arquivo criado:")
        print("- dist_console/RoboTraderMonstro_Console.exe")
        print("\nAgora voce pode ver o que acontece!")

    else:
        print("Erro ao criar executavel!")


if __name__ == "__main__":
    main()
