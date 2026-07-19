#!/usr/bin/env python3
# 🎯 DASHBOARD TEMPO REAL - MONSTRO DAS NEGOCIAÇÕES
# Monitora o lucro em tempo real através dos logs

import os
import time
import re
from datetime import datetime
from colorama import Fore, Back, Style, init

# Inicializar colorama para Windows
init()

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def extrair_pnl_do_log(linha_log):
    """Extrai P&L, pontos e tempo de uma linha de log"""
    # Procura por padrões como "P&L REAL: R$-5.00 | 2.5pts | ⏱️3min"
    match = re.search(r'P&L REAL: R\$(-?\d+\.?\d*)\s*\|\s*(-?\d+\.?\d*)pts\s*\|\s*⏱️(\d+)min', linha_log)
    if match:
        return float(match.group(1)), float(match.group(2)), int(match.group(3))
    return None, None, None

def extrair_ticket_do_log(linha_log):
    """Extrai número do ticket de uma linha de log"""
    match = re.search(r'Ticket:\s*(\d+)', linha_log)
    return match.group(1) if match else None

def mostrar_dashboard():
    log_file = "monstro_v2.log"
    
    if not os.path.exists(log_file):
        print(f"❌ Arquivo de log não encontrado: {log_file}")
        return
    
    ultima_posicao = None
    ultimo_pnl = 0.0
    ultimos_pontos = 0.0
    ultimo_tempo = 0
    ticket_atual = None
    
    while True:
        try:
            limpar_tela()
            
            # Ler as últimas linhas do log
            with open(log_file, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
            
            # Procurar informações relevantes nas últimas 50 linhas
            for linha in linhas[-50:]:
                # Detectar nova posição
                if "POSIÇÃO ATIVA:" in linha:
                    if "📈 COMPRA" in linha:
                        ultima_posicao = "COMPRA"
                    elif "📉 VENDA" in linha:
                        ultima_posicao = "VENDA"
                    ticket_atual = extrair_ticket_do_log(linha)
                
                # Extrair P&L em tempo real
                pnl, pontos, tempo = extrair_pnl_do_log(linha)
                if pnl is not None:
                    ultimo_pnl = pnl
                    ultimos_pontos = pontos
                    ultimo_tempo = tempo
                
                # Detectar fechamento de posição
                if "fechada" in linha and ticket_atual:
                    ultima_posicao = None
                    ticket_atual = None
            
            # Mostrar dashboard
            print("=" * 60)
            print(f"{Fore.CYAN}{Style.BRIGHT}🤖 MONSTRO DAS NEGOCIAÇÕES - DASHBOARD TEMPO REAL{Style.RESET_ALL}")
            print("=" * 60)
            print(f"⏰ Atualizado em: {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 60)
            
            if ultima_posicao and ticket_atual:
                # Posição ativa
                cor_posicao = Fore.GREEN if ultima_posicao == "COMPRA" else Fore.RED
                emoji_posicao = "📈" if ultima_posicao == "COMPRA" else "📉"
                
                print(f"{cor_posicao}{Style.BRIGHT}🎯 POSIÇÃO ATIVA: {emoji_posicao} {ultima_posicao}{Style.RESET_ALL}")
                print(f"🎫 Ticket: {ticket_atual}")
                print("-" * 60)
                
                # P&L com cores dinâmicas
                if ultimo_pnl > 0:
                    cor_pnl = Fore.GREEN + Style.BRIGHT
                    emoji_pnl = "💰"
                elif ultimo_pnl < 0:
                    cor_pnl = Fore.RED + Style.BRIGHT
                    emoji_pnl = "🔻"
                else:
                    cor_pnl = Fore.YELLOW
                    emoji_pnl = "➖"
                
                print(f"{cor_pnl}{emoji_pnl} P&L: R$ {ultimo_pnl:.2f}{Style.RESET_ALL}")
                print(f"📊 Pontos: {ultimos_pontos:.1f} pts")
                print(f"⏱️ Tempo: {ultimo_tempo} min")
                
                # Indicadores visuais
                if abs(ultimo_pnl) >= 20:
                    intensidade = "🚨 ATENÇÃO!" if ultimo_pnl < 0 else "🎯 EXCELENTE!"
                    cor_intensidade = Fore.RED if ultimo_pnl < 0 else Fore.GREEN
                    print(f"\n{cor_intensidade}{Style.BRIGHT}{intensidade}{Style.RESET_ALL}")
                elif abs(ultimo_pnl) >= 10:
                    intensidade = "⚠️ Monitorar" if ultimo_pnl < 0 else "✅ Bom"
                    cor_intensidade = Fore.YELLOW if ultimo_pnl < 0 else Fore.GREEN
                    print(f"\n{cor_intensidade}{intensidade}{Style.RESET_ALL}")
            else:
                print(f"{Fore.BLUE}💤 AGUARDANDO POSIÇÃO...{Style.RESET_ALL}")
                print("🔍 Monitorando sinais de entrada da IA")
            
            print("-" * 60)
            print(f"{Fore.CYAN}💡 Pressione Ctrl+C para sair{Style.RESET_ALL}")
            print("=" * 60)
            
            time.sleep(2)  # Atualiza a cada 2 segundos
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Dashboard encerrado pelo usuário{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Erro: {e}{Style.RESET_ALL}")
            time.sleep(5)

if __name__ == "__main__":
    print("🚀 Iniciando Dashboard Tempo Real...")
    mostrar_dashboard() 