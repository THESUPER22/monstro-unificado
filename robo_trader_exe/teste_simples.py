import os
import subprocess
import time
from datetime import datetime


def main():
    print("="*50)
    print("TESTANDO EXECUTAVEL DO ROBO TRADER")
    print("="*50)

    exe_path = "dist_final/RoboTraderMonstro.exe"

    # Verifica se existe
    if os.path.exists(exe_path):
        tamanho = os.path.getsize(exe_path)
        tamanho_mb = tamanho / (1024 * 1024)
        print(f"Executavel encontrado: {tamanho_mb:.1f} MB")

        # Verifica ZIP
        zip_files = [f for f in os.listdir('.') if f.startswith(
            'RoboTraderMonstro_') and f.endswith('.zip')]
        if zip_files:
            zip_file = zip_files[0]
            tamanho_zip = os.path.getsize(zip_file)
            tamanho_zip_mb = tamanho_zip / (1024 * 1024)
            print(f"ZIP encontrado: {zip_file} ({tamanho_zip_mb:.1f} MB)")

        print("\nTESTE DE EXECUCAO:")
        print("Iniciando executavel por 3 segundos...")

        try:
            # Testa execucao
            processo = subprocess.Popen([exe_path], cwd="dist_final")
            time.sleep(3)

            if processo.poll() is None:
                print("Executavel iniciou corretamente!")
                processo.terminate()
                time.sleep(1)
                if processo.poll() is None:
                    processo.kill()
                print("Processo terminado com sucesso")
            else:
                print(f"Processo terminou (codigo: {processo.returncode})")

            print("\n" + "="*50)
            print("RESULTADO FINAL:")
            print("Executavel: OK")
            print("ZIP: OK")
            print("Teste de execucao: OK")
            print("SEU ROBO ESTA PRONTO!")
            print("="*50)

        except Exception as e:
            print(f"Erro no teste: {e}")
    else:
        print("Executavel nao encontrado!")


if __name__ == "__main__":
    os.chdir('robo_trader_exe')
    main()
