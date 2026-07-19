import os
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta


def main():
    print("="*50)
    print("CRIANDO SEU ROBO TRADER EXECUTAVEL")
    print("="*50)

    # Passo 1: Instalar PyInstaller
    print("Passo 1: Instalando PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip",
                       "install", "pyinstaller"], check=True)
        print("PyInstaller instalado!")
    except:
        print("PyInstaller ja estava instalado!")

    # Passo 2: Adicionar protecao por data
    print("Passo 2: Adicionando protecao por data...")
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

verificar_expiracao()
'''

    # Le arquivo original
    with open("monstro_unificado_v2.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Adiciona protecao no inicio
    conteudo_protegido = protecao + "\n" + conteudo

    # Salva arquivo protegido
    with open("monstro_protegido.py", "w", encoding="utf-8") as f:
        f.write(conteudo_protegido)

    print(f"Protecao adicionada! Expira em: {data_str}")

    # Passo 3: Criar executavel
    print("Passo 3: Criando executavel (pode demorar alguns minutos)...")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "RoboTraderMonstro",
        "--distpath", "dist_final"
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

    cmd.append("monstro_protegido.py")

    resultado = subprocess.run(cmd)

    if resultado.returncode == 0:
        print("Executavel criado com sucesso!")

        # Passo 4: Criar ZIP
        print("Passo 4: Criando arquivo ZIP...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"RoboTraderMonstro_{timestamp}.zip"

        with zipfile.ZipFile(zip_name, 'w') as zipf:
            zipf.write("dist_final/RoboTraderMonstro.exe",
                       "RoboTraderMonstro.exe")
            zipf.write("EA_BookData_Universal.mq5",
                       "EA_BookData_Universal.mq5")

        print("\n" + "="*50)
        print("SEU ROBO ESTA PRONTO!")
        print("="*50)
        print("Arquivos criados:")
        print(f"- dist_final/RoboTraderMonstro.exe")
        print(f"- {zip_name}")
        print("\nVoce pode enviar o ZIP por WhatsApp/email!")

    else:
        print("Erro ao criar executavel!")


if __name__ == "__main__":
    main()
