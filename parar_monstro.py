#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para parar o Monstro das Negociações de forma segura
"""

import time
import psutil
from pathlib import Path


def encontrar_processo_monstro():
    """Encontra o processo do Monstro em execução."""
    processos_encontrados = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Verifica se é um processo Python executando monstro_unificado.py
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('monstro_unificado.py' in arg
                                   for arg in cmdline):
                    processos_encontrados.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied,
                psutil.ZombieProcess):
            pass

    return processos_encontrados


def parar_monstro_gracefully():
    """Para o Monstro de forma elegante."""
    print("🔍 Procurando processos do Monstro das Negociações...")

    processos = encontrar_processo_monstro()

    if not processos:
        print("❌ Nenhum processo do Monstro encontrado em execução.")
        return False

    print(f"✅ Encontrado(s) {len(processos)} processo(s) do Monstro:")

    for i, proc in enumerate(processos, 1):
        try:
            cmd_str = ' '.join(proc.cmdline())
            print(f"   {i}. PID: {proc.pid} - Comando: {cmd_str}")
        except Exception:
            print(f"   {i}. PID: {proc.pid} - "
                  f"(não foi possível obter comando)")

    print("\n🛑 Enviando sinal de parada segura (SIGTERM)...")

    for proc in processos:
        try:
            proc.terminate()  # Envia SIGTERM para parada elegante
            print(f"✅ Sinal enviado para processo PID {proc.pid}")
        except Exception as e:
            print(f"❌ Erro ao enviar sinal para PID {proc.pid}: {e}")

    # Aguarda alguns segundos para o processo finalizar
    print("\n⏳ Aguardando finalização dos processos...")
    time.sleep(5)

    # Verifica se os processos realmente pararam
    processos_restantes = encontrar_processo_monstro()

    if not processos_restantes:
        print("✅ Todos os processos do Monstro foram finalizados!")
        return True
    else:
        print(f"⚠️ Ainda restam {len(processos_restantes)} processo(s).")
        print("💀 Forçando finalização (SIGKILL)...")

        for proc in processos_restantes:
            try:
                proc.kill()  # Força finalização
                print(f"💀 Processo PID {proc.pid} finalizado forçadamente")
            except Exception as e:
                print(f"❌ Erro ao finalizar processo PID {proc.pid}: {e}")

        time.sleep(2)
        processos_finais = encontrar_processo_monstro()

        if not processos_finais:
            print("✅ Todos os processos foram finalizados!")
            return True
        else:
            count = len(processos_finais)
            print(f"❌ Falha ao finalizar {count} processo(s)")
            return False


def criar_arquivo_stop():
    """Cria arquivo de flag para parada elegante."""
    stop_file = Path("monstro_stop.flag")
    try:
        stop_file.touch()
        print(f"✅ Arquivo de flag criado: {stop_file.absolute()}")
        print("💡 O Monstro detectará este arquivo e parará na próxima "
              "iteração.")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar arquivo de flag: {e}")
        return False


def main():
    """Função principal."""
    print("🤖 PARADOR DO MONSTRO DAS NEGOCIAÇÕES")
    print("=" * 50)

    # Tenta primeiro a parada elegante por flag
    print("1️⃣ Tentando parada elegante via arquivo de flag...")
    if criar_arquivo_stop():
        print("⏳ Aguarde até 30 segundos para o Monstro detectar...")

        # Monitora por 30 segundos
        for i in range(30):
            processos = encontrar_processo_monstro()
            if not processos:
                print("✅ Monstro parou elegantemente!")
                return
            time.sleep(1)
            if i % 5 == 0:
                print(f"⏳ Aguardando... {30-i}s restantes")

    print("\n2️⃣ Parada por flag não funcionou. Tentando parada direta...")

    # Se a flag não funcionou, força a parada
    if parar_monstro_gracefully():
        print("\n🎉 Monstro parado com sucesso!")
    else:
        print("\n❌ Falha ao parar o Monstro. Verifique manualmente.")

    # Remove arquivo de flag se existir
    stop_file = Path("monstro_stop.flag")
    if stop_file.exists():
        try:
            stop_file.unlink()
            print("🧹 Arquivo de flag removido.")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")

    print("\n👋 Finalizando parador do Monstro...")
    input("Pressione ENTER para fechar...")
