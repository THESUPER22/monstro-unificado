#!/usr/bin/env python3
# -*- coding: utf-8 -*-
️ SCRIPT DE ENCERRAMENTO GRACIOSO DO MONSTRO
Envia CTRL+C para os processos Python para encerramento seguro
"""

import os
import sys
import time
import psutil
import signal
import subprocess

def encontrar_processos_monstro():
    """Encontra processos Python do Monstro."""
    processos_monstro = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
       if proc.info['name
= 'python.exe' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'monstro_unificado.py' in cmdline or 'monstro_unificado_v2.py' in cmdline:
                    processos_monstro.append({
                        'pid': proc.info['pid'],
 'cmdline': cmdline,
                        'process
: proc
  })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cue

    return processos_monstro

def encerrar_gracioso():
    """Encerra os processos do Monstro de forma graciosa."""
    print("🛡️ ENCERRAMENTO GRACIOSO DO MONSTRO")
    print("=" * 50)

    # Encontra processos
    processos = encontrar_processos_monstro()

    if not processos:
        print("✅ Nenhum processo do Monstro encontrado")
        return

    print(f"🔍 Encontrados {len(processos)} processos do Monstro:")
    for proc in processos:
        if 'monstro_unificado_v2.py' in proc['cmdline']:
            print(f"   📈 WIN v2 (PID: {proc['pid']})")
        elif 'monstro_unificado.py' in proc['cmdline']:
            print(f"   💰 DÓLAR (PID: {proc['pid']})")

    print("\n📤 Enviando sinal SIGINT (CTRL+C) para encerramento gracioso...")

    # Envia SIGINT para cada processo
    for proc in processos:
        try:
            proc['processo'].send_signal(signal.SIGINT)
            print(f"   ✅ Sinal enviado para PID {pid']}")
        except Exception as e:
            print(f"   ❌ Erro ao enviar sinal para PID {proc['pid']}: {e}")

    # Aguarda encerramento gracioso
    print("\n⏳ Agu encerramento gracioso (15 segundos)...")
    print("   💾 Salvando modelos keras...")
    print("   📊 Fechando posições ativas...")
    print("   🔒 Protegendo arquivos...")

    for i in range(15):
        time.sleep(1)
        processos_restantes = encontrar_processos_monstro()
        if not processos_restantes:
            print(f"\n✅ Encerramento gracioso concluído em segundos!")
            break
        print(f"   ⏳ {15-i} segundos restantes...")
    else:
        # Se ainda houver processos após 15 segundos
        processos_restantes = encontrar_processos_monstro()
        if processos_restantes:
            print(f"\n⚠️ {len(processos_restantes)} processos ainda ativos após 15 segundos")
 print("🚨 FORÇANDO encerramento (pode corromper arquivos)...")

      for proc in processos_restantes:
       try
                    proc['processo'].terminate()
                    print(f"   🔴 Processo PID {proc['pid']} terminado à força")
                except Exception as e:
                    print(f"   ❌ Erro ao terminar PID {proc['pid']}: {e}")

...")uarara continnter pressione E\nP   input("
     o: {e}")
amentencerrte  durann❌ Erroint(f"\
        prion as e:xcept Except e  ")
 árioo usulada pel"\n⛔ Operint(        pInterrupt:
pt Keyboardce
    exoso()ar_gracincerr     e
      try:":
 "__main___name__ == f _e")

icorretamentlizados ✅ Logs fina print("
   ")protegidosncia s de experiêivo✅ Arquprint("
    samente")adas graciofechões Posiç"   ✅   print(
   salvos")eraselos k"   ✅ Modnt(pri
    :")cadaseções apli📊 Prot"\n   print()
 CLUÍDO!" CONMENTO SEGURO ENCERRAn🛡️\int("    pr

")T5: {e}izar Mfinalrro ao f"   ❌ E      print(on as e:
   Excepti   exceptado")
 alizer 5 finetaTradint(  pr
      ck=False)hetput=True, ce_ou  captur                  e'],
  l64.exermina '/im', 't', '/f',skkill.run(['taessbproc     su try:

   .")der 5..taTrazando Me"\n💹 Finali(rint   pader 5
 liza MetaTrna  # Fi
