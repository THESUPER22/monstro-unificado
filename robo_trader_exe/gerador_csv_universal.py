#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEV UNIVERSAL - ROBO TRADER MONSTRO
Gera arquivos CSV com dados coletados do indice (WIN/WDO)
Funciona com qualquer MQL5 que gere book_data.csv
"""

import os
import csv
import time
import json
from datetime import datetime
import MetaTrader5 as mt5


class GeradorCSVUniversal:
    def __init__(self, config_file="config_win_v2.json"):
        """Inicializa o gerador CSV universal"""
        self.config = self.carregar_config(config_file)
        self.symbol_prefix = self.config.get("symbol_prefix", "WIN")
        self.csv_output = f"dados_coletados_{self.symbol_prefix.lower()}.csv"
        self.book_file = "book_data.csv"
        self.running = False

        # Headers do CSV de saida
        self.csv_headers = [
            "timestamp",
            "symbol",
            "bid_price",
            "ask_price",
            "spread",
            "bid_volume_total",
            "ask_volume_total",
            "bid_levels",
            "ask_levels",
            "volume_tick",
            "last_price"
        ]

        self.inicializar_csv()

    def carregar_config(self, config_file):
        """Carrega configuracao do arquivo JSON"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"symbol_prefix": "WIN"}

    def inicializar_csv(self):
        """Inicializa o arquivo CSV de saida"""
        if not os.path.exists(self.csv_output):
            with open(self.csv_output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)
            print(f"Arquivo CSV criado: {self.csv_output}")

    def conectar_mt5(self):
        """Conecta ao MetaTrader 5"""
        if not mt5.initialize():
            print("Erro ao conectar MT5")
            return False

        print("MT5 conectado com sucesso")
        return True

    def obter_symbol_ativo(self):
        """Obtem o simbolo ativo baseado no prefixo"""
        symbols = mt5.symbols_get()
        if not symbols:
            return None

        # Procura simbolos com o prefixo
        symbols_filtrados = [
            s for s in symbols if s.name.startswith(self.symbol_prefix)]

        if not symbols_filtrados:
            return None

        # Ordena por nome (pega o mais recente - front month)
        symbols_filtrados.sort(key=lambda x: x.name)
        return symbols_filtrados[-1].name

    def ler_book_data(self):
        """Le dados do book_data.csv gerado pelo EA"""
        try:
            if not os.path.exists(self.book_file):
                return None

            with open(self.book_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if len(lines) < 2:
                return None

            # Linha 1: volumes BID, Linha 2: volumes ASK
            bid_volumes = lines[0].strip().split(
                ',') if lines[0].strip() else []
            ask_volumes = lines[1].strip().split(
                ',') if lines[1].strip() else []

            # Converte para numeros
            bid_volumes = [int(v) for v in bid_volumes if v.isdigit()]
            ask_volumes = [int(v) for v in ask_volumes if v.isdigit()]

            return {
                'bid_volumes': bid_volumes,
                'ask_volumes': ask_volumes,
                'bid_total': sum(bid_volumes),
                'ask_total': sum(ask_volumes),
                'bid_levels': len(bid_volumes),
                'ask_levels': len(ask_volumes)
            }

        except Exception as e:
            print(f"Erro ao ler book_data.csv: {e}")
            return None

    def obter_dados_mt5(self, symbol):
        """Obtem dados adicionais do MT5"""
        try:
            # Tick atual
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return None

            return {
                'bid_price': tick.bid,
                'ask_price': tick.ask,
                'last_price': tick.last,
                'volume_tick': tick.volume
            }

        except Exception as e:
            print(f"Erro ao obter dados MT5: {e}")
            return None

    def processar_dados(self):
        """Processa e salva dados no CSV"""
        # Obtem simbolo ativo
        symbol = self.obter_symbol_ativo()
        if not symbol:
            print(f"Nenhum simbolo {self.symbol_prefix} encontrado")
            return False

        # Le dados do book
        book_data = self.ler_book_data()
        if not book_data:
            return False

        # Obtem dados do MT5
        mt5_data = self.obter_dados_mt5(symbol)
        if not mt5_data:
            return False

        # Calcula spread
        spread = (mt5_data['ask_price'] - mt5_data['bid_price']) / \
                  self.config.get('contrato', {}).get('tick_size', 0.2)

        # Monta linha do CSV
        linha = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            mt5_data['bid_price'],
            mt5_data['ask_price'],
            round(spread, 1),
            book_data['bid_total'],
            book_data['ask_total'],
            book_data['bid_levels'
    book_data['ask_levels'],
            mt5_data['volume_tick'],
            mt5_data['last_price']
        ]

        # Salva no CSV
        try:
            with open(self.csv_output, 'a', newline='', encoding='utf-8') as f:
                writer= csv.writer(f)
                writer.writerow(linha)
            return True
        except Exception as e:
            print(f"Erro ao salvar CSV: {e}")
            return False

    def iniciar_coleta(self, intervalo=1):
        """Inicia a coleta continua de dados"""
        print(f"Iniciando coleta de dados {self.symbol_prefix}...")
        print(f"Arquivo de saida: {self.csv_output}")
        print(f"Intervalo: {intervalo}s")

        if not self.conectar_mt5():
            return False

        self.running= True
        contador= 0

        try:
            while self.running:
                if self.processar_dados():
                    contador += 1
                    if contador % 10 == 0:  # Log a cada 10 registros
                        print(f"Registros coletados: {contador}")

                time.sleep(intervalo)

        except KeyboardInterrupt:
            print("\nColeta interrompida pelo usuario")
        except Exception as e:
            print(f"Erro na coleta: {e}")
        finally:
            self.parar_coleta()

    def parar_coleta(self):
        """Para a coleta de dados"""
        self.running= False
        mt5.shutdown()
        print("Coleta finalizada")

def main():
    """Funcao principal"""
    print("="*60)
    print("    GERADOR CSV UNIVERSAL - ROBO TRADER MONSTRO")
    print("="*60)

    # Verifica se existe config
    config_files= ["config_win_v2.json", "config.json"]
    config_file= None

    for cf in config_files:
        if os.path.exists(cf):
            config_file= cf
            break

    if not config_file:
        print("Nenhum arquivo de configuracao encontrado!")
        print("Criando configuracao padrao...")
        config_padrao= {
            "symbol_prefix": "WIN",
            "contrato": {"tick_size": 0.2}
        }
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(config_padrao, f, indent=2)
        config_file= "config.json"

    # Inicia gerador
    gerador= GeradorCSVUniversal(config_file)

    print(f"Configuracao carregada: {config_file}")
    print(f"Simbolo: {gerador.symbol_prefix}")
    print(f"Arquivo CSV: {gerador.csv_output}")
    print("\nPressione Ctrl+C para parar")

    # Inicia coleta
    gerador.iniciar_coleta(intervalo=1)

if __name__ == "__main__":
    main()
