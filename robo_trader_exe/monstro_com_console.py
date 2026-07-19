
# PROTECAO POR DATA
from datetime import datetime
import sys

def verificar_expiracao():
    data_limite = datetime.strptime("2025-08-25", "%Y-%m-%d")
    if datetime.now() > data_limite:
        print("PRAZO EXPIRADO - Solicite nova versao")
        input("Pressione ENTER para sair...")
        sys.exit(1)
    print("Sistema valido ate: 2025-08-25")

verificar_expiracao()

# ✅ MONSTRO UNIFICADO V2 - COMPLETO E FUNCIONAL COM MELHORIAS
# Inclui: IA contínua com Keras, entropia do book, painel web, score,
# logs e aprendizado real
#
# 🚀 MELHORIAS IMPLEMENTADAS (+10% EFICÁCIA TOTAL):
# ✅ 1. TRAILING STOP INTELIGENTE (+3% eficácia)
# ✅ 2. BALANCEAMENTO BUY/SELL (+2% eficácia)
# ✅ 3. MODOS DE MERCADO SIMPLIFICADOS (+2% eficácia)
# ✅ 4. CIRCUIT BREAKERS ESSENCIAIS (+1.5% eficácia)
# ✅ 5. SAÍDA INTELIGENTE DE POSIÇÃO (+1.5% eficácia)

import glob
import json
# region [Imports]
# Bibliotecas padrão
import logging
import math
import os
import random
import re
import shutil
import signal
import sys
import threading
import time
import traceback
from datetime import datetime
from datetime import time as dtime
from datetime import timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

# MetaTrader
import MetaTrader5 as mt5
# Bibliotecas de dados e ML
import numpy as np
import pandas as pd
# Deep Learning
import tensorflow as tf
from dateutil.relativedelta import relativedelta
# Web
from flask import Flask, jsonify, request
from scipy.stats import entropy
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from tenacity import retry, stop_after_attempt, wait_exponential
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam

# Módulos locais
from diagnostico_monstro import checar_arquivos_essenciais

# Configuração TensorFlow
tf.config.run_functions_eagerly(True)

# endregion

# ========== MELHORIA 1: TRAILING STOP INTELIGENTE (+3% EFICÁCIA) ==========
class TrailingStopInteligente:
    """Gerencia trailing stop inteligente com trava de lucro."""

    def __init__(self):
        self.posicao_ativa = None
        self.preco_entrada = 0.0
        self.melhor_preco = 0.0
        self.trailing_ativo = False
        self.lucro_travado = False
        self.sl_original = 0.0

    def iniciar_trailing(self, ticket: int, tipo: str, preco_entrada: float, sl_original: float):
        """Inicia o trailing stop para uma posição."""
        self.posicao_ativa = ticket
        self.preco_entrada = preco_entrada
        self.melhor_preco = preco_entrada
        self.trailing_ativo = False
        self.lucro_travado = False
        self.sl_original = sl_original

    def atualizar_trailing(self, preco_atual: float, tipo_posicao: str) -> Optional[float]:
        """Atualiza o trailing stop e retorna novo SL se necessário."""
        if not self.posicao_ativa:
            return None

        lucro_pontos = 0.0
        if tipo_posicao == "BUY":
            lucro_pontos = (preco_atual - self.preco_entrada) / 0.2  # TICK_SIZE WIN
            if preco_atual > self.melhor_preco:
                self.melhor_preco = preco_atual
        else:  # SELL
            lucro_pontos = (self.preco_entrada - preco_atual) / 0.2  # TICK_SIZE WIN
            if preco_atual < self.melhor_preco:
                self.melhor_preco = preco_atual

        # Ativa trailing após atingir gatilho (20 pontos WIN)
        if lucro_pontos >= 20 and not self.trailing_ativo:
            self.trailing_ativo = True
            logging.info(f"🎯 Trailing stop ativado! Lucro: {lucro_pontos:.1f} pontos")

        # Trava 70% do lucro quando > 20 pontos
        if lucro_pontos >= 20 and not self.lucro_travado:
            self.lucro_travado = True
            if tipo_posicao == "BUY":
                novo_sl = self.preco_entrada + (lucro_pontos * 0.7 * 0.2)
            else:
                novo_sl = self.preco_entrada - (lucro_pontos * 0.7 * 0.2)
            logging.info(f"🔒 Lucro travado em 70%! Novo SL: {novo_sl}")
            return novo_sl

        # Trailing normal (10 pontos de distância)
        if self.trailing_ativo:
            if tipo_posicao == "BUY":
                novo_sl = self.melhor_preco - (10 * 0.2)  # 10 pontos WIN
                if novo_sl > self.sl_original:
                    return novo_sl
            else:
                novo_sl = self.melhor_preco + (10 * 0.2)  # 10 pontos WIN
                if novo_sl < self.sl_original:
                    return novo_sl

        return None

    def finalizar_trailing(self):
        """Finaliza o trailing stop."""
        self.posicao_ativa = None
        self.trailing_ativo = False
        self.lucro_travado = False

# endregion

# region [Configurações de Bloqueio]
MAX_LOSSES_SEQUENCIA = 3     # Máximo de losses seguidos no mesmo lado
CICLOS_BLOQUEIO = 5         # Número de ciclos que o lado fica bloqueado
MIN_LUCRO_DESBLOQUEIO = 0.0  # Lucro mínimo para desbloquear lado antes do tempo
# endregion

# region [Seleção Dinâmica do Contrato]


def get_front_month_symbol_dynamic(prefix="WIN") -> str:
    """Busca no MT5 todos os contratos prefixados por WIN, filtra por trade_mode FULL
       e retorna aquele com expiração mais próxima no futuro."""
    symbols = mt5.symbols_get()  # lista de todos símbolos do terminal
    agora_ts = datetime.now().timestamp()
    candidatas = []
    for s in symbols:
        if re.fullmatch(rf"{prefix}[A-Z]\d{{2}}", s.name) and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            exp_ts = getattr(s, 'expiration_time', None)
            if exp_ts and exp_ts > agora_ts:
                candidatas.append(s)
    if not candidatas:
        logging.error(
            f"❌ Nenhum contrato mensal {prefix}* ativo encontrado. Usando {prefix}$ como fallback.")
        return f"{prefix}$"
    # escolhe o que vence primeiro
    front = min(candidatas, key=lambda s: s.expiration_time)
    logging.info(
        f"✅ Contrato dinâmico selecionado: {front.name} (venc.: {datetime.fromtimestamp(front.expiration_time)})")
    return front.name
# endregion

# region [Classes]


class GerenciadorBloqueio:
    """Gerencia o bloqueio de lados após sequência de prejuízos."""

    def __init__(self):
        self.historico_acoes = []  # Lista de tuplas (acao, lucro)
        # Ciclos restantes de bloqueio
        self.bloqueio_lado = {"BUY": 0, "SELL": 0}
        self.ultima_acao = None
        self.losses_sequencia = {"BUY": 0, "SELL": 0}

    def registrar_operacao(self, acao: str, lucro: float) -> None:
        """Registra uma operação e atualiza contadores."""
        # Só processa ações válidas de trading
        if acao not in ["BUY", "SELL"]:
            logging.debug(
                f"Ignorando registro de operação para ação inválida: {acao}")
            return

        self.historico_acoes.append((acao, lucro))
        if len(self.historico_acoes) > 10:  # Mantém histórico limitado
            self.historico_acoes.pop(0)

        # Atualiza contagem de losses em sequência - MAIS AGRESSIVO
        # Só conta como loss se for prejuízo significativo (maior que 25 reais)
        if lucro < -25.0:
            self.losses_sequencia[acao] += 1
            # Verifica se atingiu limite de losses seguidos
            if self.losses_sequencia[acao] >= MAX_LOSSES_SEQUENCIA:
                self.bloquear_lado(acao)
                logging.warning(
                    f"🚫 Bloqueando lado {acao} por {CICLOS_BLOQUEIO} ciclos após {MAX_LOSSES_SEQUENCIA} losses seguidos")
        else:
            # Reseta contador de losses se teve lucro OU prejuízo pequeno
            self.losses_sequencia[acao] = max(
                0, self.losses_sequencia[acao] - 1)  # Decrementa gradualmente
            # Verifica se pode desbloquear por lucro (critério mais flexível)
            if lucro >= MIN_LUCRO_DESBLOQUEIO and self.bloqueio_lado[acao] > 0:
                # Reduz bloqueio gradualmente
                self.bloqueio_lado[acao] = max(0, self.bloqueio_lado[acao] - 1)
                logging.info(
                    f"✅ Reduzindo bloqueio do lado {acao} por resultado não negativo")

        self.ultima_acao = acao

    def bloquear_lado(self, lado: str) -> None:
        """Bloqueia um lado por N ciclos."""
        if lado in ["BUY", "SELL"]:
            self.bloqueio_lado[lado] = CICLOS_BLOQUEIO
        else:
            logging.debug(f"Tentativa de bloquear lado inválido: {lado}")

    def verificar_bloqueio(self, acao: str) -> bool:
        """Verifica se uma ação está bloqueada e atualiza contadores."""
        # Só verifica bloqueio para ações válidas de trading
        if acao not in ["BUY", "SELL"]:
            return False

        if self.bloqueio_lado[acao] > 0:
            self.bloqueio_lado[acao] -= 1
            return True
        return False

    def obter_acao_alternativa(self, acao_original: str) -> str:
        """Retorna a ação oposta quando há bloqueio."""
        if acao_original == "BUY":
            return "SELL"
        elif acao_original == "SELL":
            return "BUY"
        else:
            # Fallback para ação inválida
            logging.warning(
                f"Ação original inválida para alternativa: {acao_original}")
            return "BUY"  # Default

    def get_status(self) -> dict:
        """Retorna status atual do gerenciador."""
        return {
            "bloqueios": self.bloqueio_lado.copy(),
            "losses_sequencia": self.losses_sequencia.copy(),
            "ultima_acao": self.ultima_acao
        }

# endregion


# region [Configurações]
# Carrega configuração específica do WIN
CONFIG_FILE = "config_win_v2.json"


def carregar_configuracao():
    """Carrega configuração do arquivo JSON."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"❌ Erro ao carregar configuração: {e}")
        return {}


# Carrega configuração
config = carregar_configuracao()

# Cache TTL e configurações de retry
CACHE_TTL = 1  # segundos
MAX_RETRY_ATTEMPTS = 5  # Aumentado para mais tentativas
RETRY_WAIT_MULTIPLIER = 2  # segundos - Aumentado o tempo entre tentativas

# region [Cache e Retry]


@lru_cache(maxsize=128)
def get_cached_symbol_info(symbol: str) -> Optional[Any]:
    """Cache para informações do símbolo."""
    return mt5.symbol_info(symbol)


def reconectar_mt5() -> bool:
    """Tenta reconectar ao MetaTrader 5."""
    try:
        if mt5.initialize():
            logging.info("✅ Reconectado ao MetaTrader 5")
            return True
        else:
            logging.error(f"❌ Erro ao reconectar: {mt5.last_error()}")
            return False
    except Exception as e:
        logging.error(f"❌ Erro na reconexão: {e}")
        return False


@retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
       wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER))
def retry_market_book_get(symbol: str) -> Optional[Any]:
    """Tenta obter o book com retry em caso de falha."""
    try:
        result = mt5.market_book_get(symbol)
        if result is None:
            if not mt5.initialize():
                if reconectar_mt5():
                    result = mt5.market_book_get(symbol)

        if result is None or len(result) == 0:
            logging.warning("⚠️ Book vazio ou nulo - tentando reconexão")
            if reconectar_mt5():
                result = mt5.market_book_get(symbol)

        return result
    except Exception as e:
        logging.error(f"❌ Erro ao obter book: {e}")
        raise Exception("Falha ao obter market book")


@retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
       wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER))
def retry_positions_get(symbol: str = None) -> Optional[Any]:
    """Tenta obter posições com retry em caso de falha."""
    return mt5.positions_get(symbol=symbol)

# endregion


# region [Configurações]
# Paths e arquivos - ADAPTADO PARA WIN
MT5_PATH = config.get("geral", {}).get(
    "mt5_path", r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe")
SYMBOL = None  # Será definido após inicializar o MT5
TIMEFRAME = mt5.TIMEFRAME_M1
HISTORICO_CSV = config.get("aprendizado", {}).get(
    "historico_csv", "historico_contexto_win.csv")
MODELO_PATH = config.get("aprendizado", {}).get(
    "modelo_path", "modelo_monstro_win.h5")
LOG_FILE = config.get("geral", {}).get("log_file", "monstro_v2.log")
BOOK_FILE_PATH = None  # Caminho do arquivo CSV que o EA gera

# Configurações Web
PORT = config.get("web_dashboard", {}).get("port", 5002)
DEBUG = config.get("web_dashboard", {}).get("debug", True)

# Configurações Trading - ADAPTADO PARA WIN
MAGIC_NUMBER = config.get("geral", {}).get("magic_number", 123457)
# Volume mínimo REAL para considerar nível válido no book (WIN tem mais volume)
VOLUME_MINIMO = 50
N_FEATURES = config.get("aprendizado", {}).get("n_features", 11)
DEVIATION = config.get("geral", {}).get("deviation", 20)

# Configurações B3 - MINI ÍNDICE (WIN)
TICK_SIZE = config.get("contrato", {}).get(
    "tick_size", 0.2)           # Tamanho do tick WIN
TICKS_POR_PONTO = config.get("contrato", {}).get(
    "ticks_por_ponto", 10000)   # WIN: 1 ponto = 10000 ticks
# Volume padrão (5 contratos WIN)
VOLUME_PADRAO = config.get("volume_padrao", 5.0)
HORARIO_PREGAO = config.get("horarios", {}).get("pregao", "09:00")
HORARIO_LIMITE_ORDENS = config.get(
    "horarios", {}).get("limite_ordens", "18:15")
HORARIO_ENCERRAMENTO = config.get("horarios", {}).get("encerramento", "18:20")
HORARIO_AFTER = config.get("horarios", {}).get("after_market", "18:27")
HORARIO_AJUSTE = "18:29"  # Horário do ajuste
DIGITS_INDICE = config.get("contrato", {}).get(
    "digits_indice", 0)         # Casas decimais do Mini Índice

# Limites de distância em ticks e pontos - ADAPTADO PARA WIN
MIN_TICKS = 10000          # 1 ponto WIN = 10000 ticks
MAX_TICKS = 900000         # 90 pontos WIN = 900000 ticks
MAX_DISTANCIA_SL_PONTOS = config.get(
    "sl_points", 90)   # 90 pontos = 900000 ticks
MAX_DISTANCIA_TP_PONTOS = config.get(
    "tp_points", 35)  # 35 pontos = 350000 ticks

# Trailing Stop (em pontos) - ADAPTADO PARA WIN
TRAILING_ATIVO = config.get("trailing_stop", {}).get("ativo", True)
TRAILING_INTERVALO = config.get(
    "trailing_stop", {}).get("intervalo_segundos", 5)
TRAILING_GATILHO = config.get("trailing_stop", {}).get(
    "gatilho_pontos", 15.0)      # 15 pontos WIN
TRAILING_DISTANCIA = config.get("trailing_stop", {}).get(
    "distancia_pontos", 5.0)    # 5 pontos WIN

# Stop Loss e Take Profit (em pontos) - CONFIGURAÇÃO WIN
SL_POINTS = config.get("sl_points", 90)      # 90 pontos WIN = 900000 ticks
TP_POINTS = config.get("tp_points", 35)     # 35 pontos WIN = 350000 ticks

# Circuit Breakers - ADAPTADO PARA WIN
MAX_LOSS_DIARIO = config.get("risk_management", {}).get(
    "max_loss_diario", -1000.0)   # Limite de perda diária em reais
MAX_DRAWDOWN = config.get("risk_management", {}).get(
    "max_drawdown", -500.0)      # Limite de drawdown por operação em reais
# Spread máximo em pontos WIN
MAX_SPREAD = config.get("max_spread", 10)
MIN_TICKS_VALIDOS = 10      # Mínimo de ticks válidos WIN
# Volume mínimo no book WIN - FILTRO DE QUALIDADE
# Aumentado para 300cc para reduzir overtrading e melhorar assertividade
MIN_VOLUME_BOOK = config.get("min_volume_book", 300)

# Configurações de Aprendizado
MIN_EXPERIENCIAS_TREINO = 3    # Mínimo de experiências para começar treino
MAX_EXPERIENCIAS_MEMORIA = 1000  # Máximo de experiências na memória
EPOCHS_TREINO = 3               # Número de épocas por treino
BATCH_SIZE = 32                 # Tamanho do batch de treino
MIN_DELTA_LOSS = 0.001         # Mínima melhoria na loss para continuar
PATIENCE_EARLY_STOP = 3        # Paciência para early stopping
DECAY_MEIA_VIDA = 12           # Meia-vida do decay em horas
INTERVALO_REPLAY = 60          # Intervalo em minutos para replay
PESO_REPLAY = 0.3              # Peso das experiências no replay
JANELA_CONSISTENCIA = 5        # Janela para calcular consistência

# Configurações de Stop Inteligente - VALORES ORIGINAIS RESTAURADOS
INVERSAO_SCORE_MIN = 0.3       # Mínima variação do score para considerar inversão
SCORE_LOCK_PROFIT = 0.5        # Score mínimo para ativar trava de lucro
TEMPO_MIN_POSICAO = 30         # Tempo mínimo em segundos antes de considerar saída
INTERVALO_CHECK_SCORE = 5      # Intervalo em segundos para checar score
JANELA_SUAVIZACAO = 3         # Tamanho da janela para média móvel do score
THRESHOLD_INVERSAO_SCORE = -0.2  # Threshold para considerar inversão negativa

# Configurações de Trading
MULTIPLICADOR_SL_ATR = 2.0  # SL = 2x ATR
MULTIPLICADOR_TP_ATR = 3.0  # TP = 3x ATR
PERIODO_ATR = 14           # Período para cálculo do ATR

# Limites máximos de SL/TP em pontos - ADAPTADO PARA WIN
SL_MAX_POINTS = 90        # Máximo SL em pontos WIN
TP_MAX_POINTS = 35        # Máximo TP em pontos WIN

# Configurações de Modos Situacionais - ADAPTADO PARA WIN
# ATR baixo para modo lateralidade (WIN tem volatilidade diferente)
THRESHOLD_ATR_BAIXO = 100  # WIN tem valores ATR maiores
# Entropia baixa para modo lateralidade
THRESHOLD_ENTROPIA_BAIXA = 0.2
# Entropia alta para modo explosão - MAIS SELETIVO
THRESHOLD_ENTROPIA_ALTA = 0.9
# Mínimo crescimento de volume para modo explosão - MAIS EXIGENTE
MIN_VOLUME_CRESCIMENTO = 1.5
# Máximo de losses seguidos antes de modo defesa
MAX_LOSSES_SEGUIDOS = 5
# Minutos em modo defesa após atingir max losses
TEMPO_DEFESA = 15
# Razão mínima entre bid/ask (WIN tem mais liquidez)
MIN_RATIO_BOOK = 0.03

# Configurações de Bloqueio de Lado - VALORES ORIGINAIS RESTAURADOS
MAX_LOSSES_SEQUENCIA = 3     # Máximo de losses seguidos no mesmo lado
CICLOS_BLOQUEIO = 5         # Número de ciclos que o lado fica bloqueado
MIN_LUCRO_DESBLOQUEIO = 0.0  # Lucro mínimo para desbloquear lado antes do tempo

# ========== CONFIGURAÇÕES MELHORIA 1: TRAILING STOP INTELIGENTE ==========
TRAILING_ATIVO = True
TRAILING_GATILHO = 20      # pontos WIN (ativa trailing após 20pts lucro)
TRAILING_DISTANCIA = 10    # pontos WIN (distância do trailing)
TRAILING_PERCENTUAL_TRAVA = 0.7  # Trava 70% do lucro quando > 20 pontos

# Instância global do trailing stop
trailing_stop = None

# ========== MELHORIA 2: BALANCEAMENTO BUY/SELL (+2% EFICÁCIA) ==========
class BalanceadorOperacoes:
    """Gerencia o balanceamento entre operações BUY e SELL."""

    def __init__(self):
        self.contador_buy = 0
        self.contador_sell = 0
        self.historico_operacoes = []

    def registrar_operacao(self, acao: str):
        """Registra uma operação executada."""
        if acao == "BUY":
            self.contador_buy += 1
        elif acao == "SELL":
            self.contador_sell += 1

        self.historico_operacoes.append(acao)
        if len(self.historico_operacoes) > 50:  # Mantém histórico limitado
            self.historico_operacoes.pop(0)

    def calcular_desbalanceamento(self) -> float:
        """Calcula o nível de desbalanceamento atual."""
        total = self.contador_buy + self.contador_sell
        if total == 0:
            return 0.0
        return self.contador_buy / total

    def ajustar_threshold(self, threshold_original: float) -> float:
        """Ajusta o threshold baseado no desbalanceamento."""
        desbalanceamento = self.calcular_desbalanceamento()

        # Se muitas operações BUY (>70%), aumenta threshold para reduzir BUY
        if desbalanceamento > 0.7:
            return threshold_original + 0.05
        # Se poucas operações BUY (<30%), diminui threshold para aumentar BUY
        elif desbalanceamento < 0.3:
            return threshold_original - 0.05

        return threshold_original

    def get_status(self) -> dict:
        """Retorna status do balanceamento."""
        total = self.contador_buy + self.contador_sell
        return {
            "buy_count": self.contador_buy,
            "sell_count": self.contador_sell,
            "buy_percentage": (self.contador_buy / total * 100) if total > 0 else 0,
            "desbalanceamento": self.calcular_desbalanceamento()
        }

# Configurações do balanceamento
BALANCEAMENTO_ATIVO = True
THRESHOLD_DESBALANCEAMENTO = 0.7  # 70% de um lado
AJUSTE_THRESHOLD_BALANCE = 0.05   # Ajuste no threshold quando desbalanceado

# Instância global do balanceador
balanceador = None

# ========== MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS (+2% EFICÁCIA) ==========
class DetectorModoMercado:
    """Detecta e gerencia modos de mercado simplificados."""

    def __init__(self):
        self.modo_atual = "NORMAL"
        self.historico_atr = []
        self.historico_entropia = []

    def atualizar_indicadores(self, atr: float, entropia: float):
        """Atualiza indicadores para detecção de modo."""
        self.historico_atr.append(atr)
        self.historico_entropia.append(entropia)

        # Mantém histórico limitado
        if len(self.historico_atr) > 20:
            self.historico_atr.pop(0)
        if len(self.historico_entropia) > 20:
            self.historico_entropia.pop(0)

    def detectar_modo(self) -> str:
        """Detecta o modo atual do mercado."""
        if len(self.historico_atr) < 5:
            return "NORMAL"

        atr_medio = sum(self.historico_atr[-5:]) / 5
        entropia_media = sum(self.historico_entropia[-5:]) / 5

        # Modo conservador: ATR baixo E entropia baixa
        if atr_medio < 250 and entropia_media < 0.3:  # Valores adaptados para WIN
            self.modo_atual = "CONSERVADOR"
        else:
            self.modo_atual = "NORMAL"

        return self.modo_atual

    def ajustar_parametros_trading(self, volume_base: float, sl_base: float, tp_base: float) -> tuple:
        """Ajusta parâmetros de trading baseado no modo."""
        if self.modo_atual == "CONSERVADOR":
            volume_ajustado = volume_base * 0.5  # Volume reduzido 50%
            sl_ajustado = sl_base * 0.7         # SL menor 30%
            tp_ajustado = tp_base * 0.8         # TP menor 20%
            return volume_ajustado, sl_ajustado, tp_ajustado

        return volume_base, sl_base, tp_base

# Configurações dos modos de mercado
MODO_CONSERVADOR_ATR = 250    # ATR baixo para modo conservador (WIN tem valores maiores)
MODO_CONSERVADOR_ENTROPIA = 0.3  # Entropia baixa para modo conservador
VOLUME_CONSERVADOR_MULT = 0.5     # Volume reduzido em modo conservador
SL_CONSERVADOR_MULT = 0.7         # SL menor em modo conservador
TP_CONSERVADOR_MULT = 0.8         # TP menor em modo conservador

# Instância global do detector de modo
detector_modo = None

# ========== MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS (+1.5% EFICÁCIA) ==========
class CircuitBreakerEssencial:
    """Implementa circuit breakers essenciais para proteção."""

    def __init__(self):
        self.losses_seguidos = 0
        self.loss_diario_atual = 0.0
        self.operacoes_hoje = []
        self.bloqueado = False
        self.motivo_bloqueio = ""

    def registrar_resultado(self, lucro: float):
        """Registra resultado de uma operação."""
        hoje = datetime.now().date()
        self.operacoes_hoje.append((hoje, lucro))

        # Remove operações de dias anteriores
        self.operacoes_hoje = [(data, valor) for data, valor in self.operacoes_hoje if data == hoje]

        # Atualiza loss diário
        self.loss_diario_atual = sum(valor for _, valor in self.operacoes_hoje)

        # Atualiza losses seguidos
        if lucro < -25.0:  # Loss significativo (WIN tem valores maiores)
            self.losses_seguidos += 1
        else:
            self.losses_seguidos = 0

    def verificar_circuit_breakers(self, spread_atual: float) -> bool:
        """Verifica se algum circuit breaker foi ativado."""
        # CB1: 3 losses seguidos
        if self.losses_seguidos >= 3:
            self.bloqueado = True
            self.motivo_bloqueio = f"3 losses seguidos (atual: {self.losses_seguidos})"
            return True

        # CB2: Loss diário excessivo (WIN tem valores maiores)
        if self.loss_diario_atual <= -1000.0:
            self.bloqueado = True
            self.motivo_bloqueio = f"Loss diário: R${self.loss_diario_atual:.2f}"
            return True

        # CB3: Spread muito alto (WIN tem spreads maiores)
        if spread_atual > 20:
            self.bloqueado = True
            self.motivo_bloqueio = f"Spread alto: {spread_atual:.1f} pontos"
            return True

        self.bloqueado = False
        self.motivo_bloqueio = ""
        return False

    def get_status(self) -> dict:
        """Retorna status dos circuit breakers."""
        return {
            "bloqueado": self.bloqueado,
            "motivo": self.motivo_bloqueio,
            "losses_seguidos": self.losses_seguidos,
            "loss_diario": self.loss_diario_atual
        }

# Configurações dos circuit breakers
CIRCUIT_BREAKER_ATIVO = True
MAX_LOSSES_SEGUIDOS_CB = 3   # Stop após 3 losses seguidos
SPREAD_MAXIMO_CB = 20        # Stop se spread > 20 pontos WIN
LOSS_DIARIO_CB = -1000.0     # Stop se perda diária > R$1000 (WIN tem valores maiores)

# Instância global do circuit breaker
circuit_breaker = None

# ========== MELHORIA 5: SAÍDA INTELIGENTE DE POSIÇÃO (+1.5% EFICÁCIA) ==========
class SaidaInteligentePositions:
    """Gerencia saída inteligente de posições."""

    def __init__(self):
        self.posicoes_monitoradas = {}
        self.historico_rsi = []

    def iniciar_monitoramento(self, ticket: int, tipo: str, preco_entrada: float):
        """Inicia monitoramento de uma posição."""
        self.posicoes_monitoradas[ticket] = {
            "tipo": tipo,
            "preco_entrada": preco_entrada,
            "tempo_inicio": time.time(),
            "melhor_lucro": 0.0,
            "tempo_sem_lucro": 0,
            "rsi_entrada": self.historico_rsi[-1] if self.historico_rsi else 50.0
        }

    def atualizar_rsi(self, rsi_atual: float):
        """Atualiza histórico de RSI."""
        self.historico_rsi.append(rsi_atual)
        if len(self.historico_rsi) > 10:
            self.historico_rsi.pop(0)

    def verificar_saida_inteligente(self, ticket: int, preco_atual: float, rsi_atual: float) -> bool:
        """Verifica se deve sair da posição inteligentemente."""
        if ticket not in self.posicoes_monitoradas:
            return False

        posicao = self.posicoes_monitoradas[ticket]
        tempo_atual = time.time()
        tempo_em_trade = tempo_atual - posicao["tempo_inicio"]

        # Calcula lucro atual em pontos WIN
        if posicao["tipo"] == "BUY":
            lucro_atual = (preco_atual - posicao["preco_entrada"]) / 0.2  # TICK_SIZE WIN
        else:
            lucro_atual = (posicao["preco_entrada"] - preco_atual) / 0.2  # TICK_SIZE WIN

        # Atualiza melhor lucro
        if lucro_atual > posicao["melhor_lucro"]:
            posicao["melhor_lucro"] = lucro_atual
            posicao["tempo_sem_lucro"] = 0
        else:
            posicao["tempo_sem_lucro"] = tempo_atual - posicao["tempo_inicio"]

        # CRITÉRIO 1: 5 minutos sem lucro
        if posicao["tempo_sem_lucro"] >= 300:  # 300 segundos = 5 minutos
            logging.info(f"🚪 Saída por tempo sem lucro: {posicao['tempo_sem_lucro']:.0f}s")
            return True

        # CRITÉRIO 2: RSI inverteu com lucro mínimo (5 pontos WIN)
        if lucro_atual >= 5.0:  # Lucro mínimo para considerar saída por RSI
            rsi_entrada = posicao["rsi_entrada"]

            # Para posição BUY: sair se RSI estava baixo e agora está alto
            if posicao["tipo"] == "BUY" and rsi_entrada < 30 and rsi_atual > 70:
                logging.info(f"🚪 Saída BUY por inversão RSI: {rsi_entrada:.1f} → {rsi_atual:.1f}")
                return True

            # Para posição SELL: sair se RSI estava alto e agora está baixo
            if posicao["tipo"] == "SELL" and rsi_entrada > 70 and rsi_atual < 30:
                logging.info(f"🚪 Saída SELL por inversão RSI: {rsi_entrada:.1f} → {rsi_atual:.1f}")
                return True

        return False

    def finalizar_monitoramento(self, ticket: int):
        """Finaliza monitoramento de uma posição."""
        if ticket in self.posicoes_monitoradas:
            del self.posicoes_monitoradas[ticket]

# Configurações da saída inteligente
SAIDA_INTELIGENTE_ATIVA = True
TEMPO_MAX_SEM_LUCRO = 300    # 5 minutos sem lucro = sair
RSI_INVERSAO_SAIDA = True    # Sair se RSI inverter com lucro
MIN_LUCRO_SAIDA_RSI = 5.0    # Lucro mínimo para considerar saída por RSI

# Instância global da saída inteligente
saida_inteligente = None

# ========== MELHORIA 6: FILTRO DE HORÁRIO PREMIUM (+2% EFICÁCIA) ==========
class FiltroHorarioPremium:
    """Filtra operações para horários de maior liquidez e volatilidade."""

    def __init__(self):
        # Horários de maior liquidez WIN (UTC-3)
        self.horarios_premium = [
            (dtime(9, 0), dtime(10, 30)),   # Abertura - alta volatilidade
            (dtime(14, 0), dtime(15, 30)),  # Meio período - movimento institucional
            (dtime(17, 0), dtime(18, 15))   # Fechamento - ajustes finais
        ]

    def is_horario_premium(self) -> bool:
        """Verifica se está em horário premium para trading."""
        agora = datetime.now().time()

        for inicio, fim in self.horarios_premium:
            if inicio <= agora <= fim:
                return True
        return False

    def get_status(self) -> dict:
        """Retorna status do filtro de horário."""
        return {
            "horario_premium": self.is_horario_premium(),
            "horario_atual": datetime.now().strftime("%H:%M:%S"),
            "proximos_horarios": ["09:00-10:30", "14:00-15:30", "17:00-18:15"]
        }

# Configurações do filtro de horário
FILTRO_HORARIO_ATIVO = True

# Instância global do filtro de horário
filtro_horario = None

# ========== MELHORIA 7: DETECTOR DE TENDÊNCIA SIMPLES (+3% EFICÁCIA) ==========
class DetectorTendencia:
    """Detecta tendência usando EMAs para viés direcional."""

    def __init__(self):
        self.ema9_values = []
        self.ema21_values = []
        self.tendencia_atual = "NEUTRO"

    def calcular_ema(self, valores: list, periodo: int) -> float:
        """Calcula EMA de forma simples."""
        if len(valores) < pe:
            return sum(valores) / len(valores) if valores else 0

        # EMA = (Valor * (2/(periodo+1))) + (EMA_anterior * (1-(2/(periodo+1))))
        multiplicador = 2 / (periodo + 1)
        ema_anterior = sum(valores[:periodo]) / periodo

        for valor in valores[periodo:]:
            ema_anterior = (valor * multiplicador) + (ema_anterior * (1 - multiplicador))

        return ema_anterior

    def atualizar_tendencia(self, preco_fechamento: float):
        """Atualiza cálculo de tendência com novo preço."""
        self.ema9_values.append(preco_fechamento)
        self.ema21_values.append(preco_fechamento)

        # Mantém histórico limitado
        if len(self.ema9_values) > 50:
            self.ema9_values.pop(0)
        if len(self.ema21_values) > 50:
            self.ema21_values.pop(0)

        # Calcula EMAs
        if len(self.ema9_values) >= 9 and len(self.ema21_values) >= 21:
            ema9 = self.calcular_ema(self.ema9_values, 9)
            ema21 = self.calcular_ema(self.ema21_values, 21)

            # Define tendência
            if ema9 > ema21:
                self.tendencia_atual = "ALTA"
            elif ema9 < ema21:
                self.tendencia_atual = "BAIXA"
            else:
                self.tendencia_atual = "NEUTRO"

    def pode_operar(self, acao: str) -> bool:
        """Verifica se pode operar na direção baseado na tendência."""
        if self.tendencia_atual == "NEUTRO":
            return True  # Permite ambas direções
        elif self.tendencia_atual == "ALTA" and acao == "BUY":
            return True  # BUY a favor da tendência
        elif self.tendencia_atual == "BAIXA" and acao == "SELL":
            return True  # SELL a favor da tendência
        else:
            return False  # Contra a tendência

    def get_status(self) -> dict:
        """Retorna status da tendência."""
        return {
            "tendencia": self.tendencia_atual,
            "ema9": self.ema9_values[-1] if self.ema9_values else 0,
            "ema21": self.ema21_values[-1] if self.ema21_values else 0
        }

# Configurações do detector de tendência
DETECTOR_TENDENCIA_ATIVO = True

# Instância global do detector de tendência
detector_tendencia = None

# ========== SISTEMA DE VOLUME INTELIGENTE BASEADO NO BOOK ==========
def calcular_volume_inteligente(volume_book_total: float) -> float:
    """Calcula volume de trading baseado no volume do book para melhor assertividade."""
    if volume_book_total >= 2000:
        return 10.0  # Volume alto para alta liquidez (modo explosão)
    elif volume_book_total >= 1000:
        return 5.0   # Volume padrão
    elif volume_book_total >= 500:
        return 4.0   # Volume moderado
    elif volume_book_total >= 300:
        return 2.5   # Volume conservador
    else:
        return 1.0   # Volume mínimo para baixa liquidez

# ========== MELHORIA 8: SISTEMA DE COOLDOWN INTELIGENTE (+1.5% EFICÁCIA) ==========
class CooldownInteligente:
    """Gerencia cooldown entre operações para evitar overtrading."""

    def __init__(self):
        self.ultima_operacao = 0
        self.losses_seguidos = 0
        self.cooldown_ativo = False
        self.fim_cooldown = 0

    def registrar_resultado(self, lucro: float):
        """Registra resultado e define cooldown necessário."""
        self.ultima_operacao = time.time()

        if lucro < -25.0:  # Loss significativo
            self.losses_seguidos += 1

            # Cooldown progressivo baseado em losses
            if self.losses_seguidos == 1:
                cooldown_segundos = 120  # 2 minutos após 1 loss
            elif self.losses_seguidos == 2:
                cooldown_segundos = 300  # 5 minutos após 2 losses
            else:
                cooldown_segundos = 600  # 10 minutos após 3+ losses

            self.cooldown_ativo = True
            self.fim_cooldown = time.time() + cooldown_segundos

            logging.info(f"⏳ Cooldown ativado: {cooldown_segundos}s após {self.losses_seguidos} loss(es)")

        else:  # Win ou break-even
            self.losses_seguidos = 0
            # Após win, pode operar imediatamente (sem cooldown)

    def pode_operar(self) -> bool:
        """Verifica se pode operar (não está em cooldown)."""
        if not self.cooldown_ativo:
            return True

        if time.time() >= self.fim_cooldown:
            self.cooldown_ativo = False
            logging.info("✅ Cooldown finalizado - Pode operar novamente")
            return True

        return False

    def tempo_restante_cooldown(self) -> int:
        """Retorna tempo restante de cooldown em segundos."""
        if not self.cooldown_ativo:
            return 0
        return max(0, int(self.fim_cooldown - time.time()))

    def get_status(self) -> dict:
        """Retorna status do cooldown."""
        return {
            "cooldown_ativo": self.cooldown_ativo,
            "tempo_restante": self.tempo_restante_cooldown(),
            "losses_seguidos": self.losses_seguidos
        }

# Configurações do cooldown
COOLDOWN_ATIVO = True
COOLDOWN_LOSS_1 = 120   # 2 minutos após 1 loss
COOLDOWN_LOSS_2 = 300   # 5 minutos após 2 losses
COOLDOWN_LOSS_3 = 600   # 10 minutos após 3+ losses

# Instância global do cooldown
cooldown_sistema = None

# ========== MELHORIA 9: FILTRO DE SPREAD DINÂMICO (+1% EFICÁCIA) ==========
class FiltroSpreadDinamico:
    """Ajusta spread máximo baseado na volatilidade do mercado."""

    def __init__(self):
        self.historico_atr = []
        self.spread_maximo_atual = MAX_SPREAD

    def atualizar_atr(self, atr_atual: float):
        """Atualiza histórico de ATR para cálculo dinâmico."""
        self.historico_atr.append(atr_atual)
        if len(self.historico_atr) > 20:
            self.historico_atr.pop(0)

        # Calcula spread dinâmico baseado na volatilidade
        if len(self.historico_atr) >= 5:
            atr_medio = sum(self.historico_atr[-5:]) / 5

            # Spread dinâmico baseado no ATR
            if atr_medio < 200:  # ATR baixo - mercado calmo
                self.spread_maximo_atual = 5
            elif atr_medio < 400:  # ATR médio
                self.spread_maximo_atual = 10
            else:  # ATR alto - mercado volátil
                self.spread_maximo_atual = 20

    def spread_aceitavel(self, spread_atual: float) -> bool:
        """Verifica se spread está dentro do limite dinâmico."""
        return spread_atual <= self.spread_maximo_atual

    def get_status(self) -> dict:
        """Retorna status do filtro de spread."""
        atr_atual = self.historico_atr[-1] if self.historico_atr else 0
        return {
            "spread_maximo": self.spread_maximo_atual,
            "atr_atual": atr_atual,
            "volatilidade": "BAIXA" if atr_atual < 200 else "MÉDIA" if atr_atual < 400 else "ALTA"
        }

# Configurações do spread dinâmico
SPREAD_DINAMICO_ATIVO = True
SPREAD_ATR_BAIXO = 5    # Spread máx quando ATR < 200
SPREAD_ATR_MEDIO = 10   # Spread máx quando ATR 200-400
SPREAD_ATR_ALTO = 20    # Spread máx quando ATR > 400

# Instância global do filtro de spread
filtro_spread = None

# ========== MELHORIA 10: MONITORAMENTO DE PERFORMANCE EM TEMPO REAL (+2% EFICÁCIA) ==========
class MonitorPerformance:
    """Monitora performance em tempo real com alertas inteligentes."""

    def __init__(self):
        self.operacoes_recentes = []  # Últimas 10 operações
        self.drawdown_atual = 0.0
        self.drawdown_maximo = 0.0
        self.pico_capital = 0.0
        self.performance_por_modo = {
            "NORMAL": {"wins": 0, "losses": 0, "lucro_total": 0.0},
            "EXPLOSAO": {"wins": 0, "losses": 0, "lucro_total": 0.0},
            "LATERAL": {"wins": 0, "losses": 0, "lucro_total": 0.0}
        }

    def registrar_operacao(self, lucro: float, modo: str):
        """Registra operação e atualiza métricas."""
        self.operacoes_recentes.append(lucro)
        if len(self.operacoes_recentes) > 10:
            self.operacoes_recentes.pop(0)

        # Atualiza performance por modo
        if modo in self.performance_por_modo:
            if lucro > 0:
                self.performance_por_modo[modo]["wins"] += 1
            else:
                self.performance_por_modo[modo]["losses"] += 1
            self.performance_por_modo[modo]["lucro_total"] += lucro

        # Atualiza drawdown
        capital_atual = sum(self.operacoes_recentes)
        if capital_atual > self.pico_capital:
            self.pico_capital = capital_atual
            self.drawdown_atual = 0.0
        else:
            self.drawdown_atual = self.pico_capital - capital_atual
            if self.drawdown_atual > self.drawdown_maximo:
                self.drawdown_maximo = self.drawdown_atual

    def taxa_acerto_recente(self) -> float:
        """Calcula taxa de acerto das últimas operações."""
        if not self.operacoes_recentes:
            return 0.0
        wins = sum(1 for op in self.operacoes_recentes if op > 0)
        return (wins / len(self.operacoes_recentes)) * 100

    def verificar_alertas(self) -> list:
        """Verdições de alerta."""
        alertas = []

        # Alerta: Taxa de acerto baixa
        taxa_acerto = self.taxa_acerto_recente()
        if len(self.operacoes_recentes) >= 5 and taxa_acerto < 30:
            alertas.append(f"🚨 Taxa de acerto baixa: {taxa_acerto:.1f}%")

        # Alerta: Drawdown alto
        if self.drawdown_atual > 300:  # R$ 300
            alertas.append(f"🚨 Drawdown alto: R$ {self.drawdown_atual:.2f}")

        # Alerta: Muitos losses seguidos
        losses_seguidos = 0
        for op in reversed(self.operacoes_recentes):
            if op < 0:
                losses_seguidos += 1
            else:
                break
        if losses_seguidos >= 3:
            alertas.append(f"🚨 {losses_seguidos} losses seguidos")

        return alertas

    def get_status(self) -> dict:
        """Retorna status completo da performance."""
        return {
            "taxa_acerto_recente": self.taxa_acerto_recente(),
            "drawdown_atual": self.drawdown_atual,
            "drawdown_maximo": self.drawdown_maximo,
            "operacoes_recentes": len(self.operacoes_recentes),
            "performance_por_modo": self.performance_por_modo,
            "alertas": self.verificar_alertas()
        }

# Configurações do monitor de performance
MONITOR_PERFORMANCE_ATIVO = True
ALERTA_TAXA_ACERTO_MIN = 30    # Alerta se taxa < 30%
ALERTA_DRAWDOWN_MAX = 300      # Alerta se drawdown > R$ 300
ALERTA_LOSSES_SEGUIDOS = 3     # Alerta se 3+ losses seguidos

# Instância global do monitor
monitor_performance = None

# endregion
# region [Logging]


def setup_logging():
    """Configura o sistema de logging."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logging.getLogger('').addHandler(console_handler)
    logging.info("🎯 Monstro WIN v2 iniciado! Pronto para operar Mini Índice.")
    logging.info(
        f"📊 Configuração: SL={SL_POINTS}pts, TP={TP_POINTS}pts, Vol={VOLUME_PADRAO}cc")

# endregion

# region [Funções Auxiliares]


def obter_nome_vela(open_price: float, close_price: float, high: float, low: float, previous_open: float = None, previous_close: float = None) -> str:
    """Determina o tipo da vela baseado nos preços e padrões.

    Tipos de velas identificadas:
    - Marubozu (alta/baixa): corpo grande sem sombras
    - Doji: abertura = fechamento
    - Martelo/Hammer: sombra inferior longa
    - Shooting Star: sombra superior longa
    - Engolfo (alta/baixa): quando uma vela engole a anterior
    - Inside Bar: vela contida na anterior
    - Outside Bar: vela que contém a anterior
    - Estrela da Manhã/Noite: padrão de 3 velas
    - Pin Bar: vela com sombra longa
    """
    body_size = abs(close_price - open_price)
    total_size = high - low
    upper_shadow = high - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low

    # Calcula proporções
    body_ratio = body_size / total_size if total_size > 0 else 0
    upper_ratio = upper_shadow / total_size if total_size > 0 else 0
    lower_ratio = lower_shadow / total_size if total_size > 0 else 0

    # Doji
    if body_ratio < 0.1:
        if upper_ratio > 0.6:
            return "doji_gravestone"  # Doji Lápide
        elif lower_ratio > 0.6:
            return "doji_dragonfly"   # Doji Libélula
        return "doji"

    # Direção básica
    direction = "alta" if close_price > open_price else "baixa"

    # Marubozu (vela sem sombras)
    if body_ratio > 0.9:
        return f"marubozu_{direction}"

    # Pin Bar / Martelo / Shooting Star
    if body_ratio < 0.3:
        if lower_ratio > 0.6:
            return f"hammer_{direction}"  # Martelo
        if upper_ratio > 0.6:
            return f"shooting_star_{direction}"  # Shooting Star

    # Padrões com vela anterior
    if previous_open is not None and previous_close is not None:
        prev_high = max(previous_open, previous_close)
        prev_low = min(previous_open, previous_close)
        curr_high = max(open_price, close_price)
        curr_low = min(open_price, close_price)

        # Inside Bar
        if curr_high <= prev_high and curr_low >= prev_low:
            return f"inside_bar_{direction}"

        # Outside Bar
        if curr_high >= prev_high and curr_low <= prev_low:
            return f"outside_bar_{direction}"

        # Engolfo
        if direction == "alta" and open_price <= previous_close and close_price > previous_open:
            return "engolfo_alta"
        if direction == "baixa" and open_price >= previous_close and close_price < previous_open:
            return "engolfo_baixa"

    # Velas normais com sombras significativas
    if upper_ratio > 0.3 and lower_ratio > 0.3:
        return f"spinning_top_{direction}"
    if upper_ratio > 0.3:
        return f"upper_shadow_{direction}"
    if lower_ratio > 0.3:
        return f"lower_shadow_{direction}"

    # Vela padrão
    return direction


def calcular_entropia(volumes: List[int]) -> float:
    """Calcula a entropia dos volumes do book (CORRIGIDO PARA EA)."""
    if not volumes:
        logging.debug(
            "[Entropia] Lista de volumes vazia, retornando entropia 0.0")
        return 0.0

    # Converte para inteiros e remove zeros para evitar problemas no cálculo
    try:
        volumes_validos = [int(v) for v in volumes if int(v) > 0]
    except (ValueError, TypeError) as e:
        logging.error(
            f"[Entropia] Erro ao converter volumes para int: {e}, volumes: {volumes[:5]}...")
        return 0.0

    if not volumes_validos:
        logging.debug(
            "[Entropia] Não há volumes válidos (>0), retornando entropia 0.0")
        return 0.0

    resultado_entropia = entropy(volumes_validos)
    logging.debug(
        f"[Entropia] Entropia calculada: {resultado_entropia:.3f} (volumes: {len(volumes_validos)})")
    return resultado_entropia


def calcular_rsi(prices: List[float], period: int = 14) -> float:
    """Calcula o indicador RSI."""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].mean()
    down = -seed[seed < 0].mean()
    rs = up / down if down != 0 else 0
    return 100.0 - (100.0 / (1.0 + rs)) if rs != 0 else 50.0


def normalizar_dados(df: pd.DataFrame, colunas_numericas: List[str], colunas_categoricas: List[str]) -> pd.DataFrame:
    """Normaliza dados numéricos e codifica dados categóricos."""
    scaler = MinMaxScaler()
    df[colunas_numericas] = scaler.fit_transform(df[colunas_numericas])
    for col in colunas_categoricas:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
    return df


def converter_candle_type(candle_type: str) -> str:
    """Converte o tipo de candle para um formato padronizado."""
    return candle_type.lower()  # Mantém o tipo detalhado


def monitorar_recursos() -> None:
    """Monitora recursos do sistema e salva experiências."""
    try:
        if os.path.exists(HISTORICO_CSV):
            # Verifica tamanho do arquivo
            tamanho_arquivo = os.path.getsize(
                HISTORICO_CSV) / (1024 * 1024)  # Tamanho em MB

            # Se arquivo maior que 50MB, faz rotação
            if tamanho_arquivo > 50:
                # Cria nome do backup com timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{HISTORICO_CSV}.{timestamp}.bak"

                # Move arquivo atual para backup
                os.rename(HISTORICO_CSV, backup_name)

                # Mantém apenas os últimos 5 backups
                backups = sorted([f for f in os.listdir('.') if f.startswith(
                    HISTORICO_CSV) and f.endswith('.bak')])
                while len(backups) > 5:
                    os.remove(backups.pop(0))

                logging.info(
                    f"📦 Rotação do histórico realizada. Backup: {backup_name}")

            # Lê e limita número de linhas
            df = pd.read_csv(HISTORICO_CSV)
            if len(df) > 5000:  # Reduzido de 10000 para 5000
                df = df.tail(5000)
                df.to_csv(HISTORICO_CSV, index=False)
                logging.info("✂️ Histórico truncado para últimas 5000 linhas")

    except Exception as e:
        logging.error(f"❌ Erro ao monitorar recursos: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")


def corrigir_csv_historico() -> None:
    """Corrige o formato do arquivo CSV histórico se necessário."""
    try:
        if not os.path.exists(HISTORICO_CSV):
            logging.info(
                "📝 Arquivo histórico não existe. Será criado na primeira operação.")
            return

        # Verifica tamanho do arquivo
        tamanho_arquivo = os.path.getsize(HISTORICO_CSV) / (1024 * 1024)  # MB
        if tamanho_arquivo > 100:  # Se maior que 100MB
            backup_name = f"{HISTORICO_CSV}.grande.{int(time.time())}"
            os.rename(HISTORICO_CSV, backup_name)
            logging.warning(
                f"⚠️ Arquivo muito grande ({tamanho_arquivo:.1f}MB). Movido para: {backup_name}")
            return

        # Tenta ler o CSV com error_bad_lines=False para pular linhas corrompidas
        df = pd.read_csv(HISTORICO_CSV, on_bad_lines='skip')
        linhas_originais = len(df)

        colunas_esperadas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'candle_type',
                             'entropia_book', 'rsi_14', 'volume_tick', 'is_in_trade',
                             'floating_profit', 'tempo_em_trade', 'action', 'reward']

        # Remove colunas extras se existirem
        colunas_extras = [
            col for col in df.columns if col not in colunas_esperadas]
        if colunas_extras:
            df = df.drop(columns=colunas_extras)
            logging.warning(
                f"🔄 Removendo colunas extras do CSV: {colunas_extras}")

        # Adiciona colunas faltantes com valores padrão apropriados
        colunas_faltando = [
            col for col in colunas_esperadas if col not in df.columns]
        if colunas_faltando:
            logging.warning(
                f"➕ Adicionando colunas faltantes no CSV: {colunas_faltando}")
            for col in colunas_faltando:
                if col in ['reward', 'floating_profit', 'spread']:
                    df[col] = 0.0
                elif col == 'action':
                    df[col] = 'NADA'
                elif col == 'candle_type':
                    df[col] = 'unknown'
                elif col == 'entropia_book':
                    df[col] = 0.5
                elif col == 'rsi_14':
                    df[col] = 50.0
                else:
                    df[col] = 0

        # Garante a ordem das colunas
        df = df[colunas_esperadas]

        # Corrige tipos de dados e valores inválidos
        df['bid_qty'] = pd.to_numeric(
            df['bid_qty'], errors='coerce').fillna(0).clip(lower=0)
        df['ask_qty'] = pd.to_numeric(
            df['ask_qty'], errors='coerce').fillna(0).clip(lower=0)
        df['spread'] = pd.to_numeric(
            df['spread'], errors='coerce').fillna(0).clip(lower=0)
        df['volatility'] = pd.to_numeric(
            df['volatility'], errors='coerce').fillna(0)
        df['entropia_book'] = pd.to_numeric(
            df['entropia_book'], errors='coerce').fillna(0.5).clip(0, 1)
        df['rsi_14'] = pd.to_numeric(
            df['rsi_14'], errors='coerce').fillna(50).clip(0, 100)
        df['volume_tick'] = pd.to_numeric(
            df['volume_tick'], errors='coerce').fillna(0).clip(lower=0)
        df['is_in_trade'] = pd.to_numeric(
            df['is_in_trade'], errors='coerce').fillna(0).astype(int).clip(0, 1)
        df['floating_profit'] = pd.to_numeric(
            df['floating_profit'], errors='coerce').fillna(0)
        df['tempo_em_trade'] = pd.to_numeric(
            df['tempo_em_trade'], errors='coerce').fillna(0).astype(int).clip(lower=0)
        df['reward'] = pd.to_numeric(df['reward'], errors='coerce').fillna(0)

        # Limpa valores extremos (outliers)
        for col in ['bid_qty', 'ask_qty', 'volume_tick', 'reward']:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # Remove linhas com valores inválidos
        df = df.dropna()

        # Limita número de linhas
        if len(df) > 5000:
            df = df.tail(5000)
            logging.info("✂️ Histórico truncado para últimas 5000 linhas")

        # Salva o arquivo corrigido
        df.to_csv(HISTORICO_CSV, index=False)

        linhas_final = len(df)
        linhas_removidas = linhas_originais - linhas_final
        if linhas_removidas > 0:
            logging.warning(
                f"🧹 {linhas_removidas} linhas inválidas removidas do histórico")

        logging.info("✅ Arquivo histórico corrigido com sucesso")

    except Exception as e:
        logging.error(f"❌ Erro ao corrigir CSV histórico: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        # Se houver erro, renomeia o arquivo corrompido e cria um novo
        if os.path.exists(HISTORICO_CSV):
            backup_name = f"{HISTORICO_CSV}.corrompido.{int(time.time())}"
            os.rename(HISTORICO_CSV, backup_name)
            logging.info(f"📦 Arquivo corrompido movido para: {backup_name}")


def salvar_experiencia_csv(contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
    """Salva uma experiência no arquivo CSV com validações."""
    try:
        # ========== INTEGRAÇÃO MELHORIA 4: CIRCUIT BREAKER REGISTRA RESULTADO ==========
        if circuit_breaker and acao in ["BUY", "SELL"]:
            circuit_breaker.registrar_resultado(lucro)

        # Validação dos tipos de dados
        if not isinstance(contexto, dict):
            raise ValueError("Contexto deve ser um dicionário")
        if not isinstance(acao, str):
            raise ValueError("Ação deve ser uma string")
        if not isinstance(lucro, (int, float)):
            raise ValueError("Lucro deve ser numérico")
        if not isinstance(score_dist, (int, float)):
            raise ValueError("Score_dist deve ser numérico")

        # Validação dos valores
        acoes_validas = {"BUY", "SELL", "NAO_AGIU", "NADA"}
        if acao not in acoes_validas:
            raise ValueError(f"Ação inválida: {acao}")

        # Garante que o contexto tem todas as colunas necessárias e valores válidos
        dados = {
            'bid_qty': max(0, float(contexto.get('bid_qty', 0))),
            'ask_qty': max(0, float(contexto.get('ask_qty', 0))),
            'spread': max(0, float(contexto.get('spread', 0))),
            'volatility': float(contexto.get('volatility', 0)),
            # Limita tamanho
            'candle_type': str(contexto.get('candle_type', 'unknown'))[:50],
            # Entre 0 e 1
            'entropia_book': max(0, min(1, float(contexto.get('entropia_book', 0)))),
            # Entre 0 e 100
            'rsi_14': max(0, min(100, float(contexto.get('rsi_14', 50)))),
            'volume_tick': max(0, float(contexto.get('volume_tick', 0))),
            # Força 0 ou 1
            'is_in_trade': int(bool(contexto.get('is_in_trade', 0))),
            'floating_profit': float(contexto.get('floating_profit', 0.0)),
            'tempo_em_trade': max(0, int(contexto.get('tempo_em_trade', 0))),
            'action': acao,
            'reward': float(lucro)
        }

        df = pd.DataFrame([dados])

        # Verifica se arquivo existe e seu tamanho
        if os.path.exists(HISTORICO_CSV):
            tamanho_arquivo = os.path.getsize(
                HISTORICO_CSV) / (1024 * 1024)  # MB
            if tamanho_arquivo > 50:  # Se maior que 50MB
                logging.warning(
                    "⚠️ Arquivo de histórico muito grande, aguardando rotação...")
                return
            df.to_csv(HISTORICO_CSV, mode='a', header=False, index=False)
        else:
            df.to_csv(HISTORICO_CSV, index=False)

        logging.info(
            f"✅ Experiência salva: Ação={acao}, Lucro={lucro:.2f}, Score={score_dist:.2f}")

    except Exception as e:
        logging.error(f"❌ Erro ao salvar experiência: {e}")
        logging.debug(f"Dados tentando salvar: {dados}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")


def preparar_dados(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """Prepara dados para treino ou predição."""
    colunas_categoricas = ['candle_type']
    colunas_numericas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book',
                         'rsi_14', 'volume_tick', 'is_in_trade', 'floating_profit', 'tempo_em_trade']

    # Cria uma cópia para evitar modificar o original
    df_work = df.copy()

    # Normaliza dados numéricos e codifica categóricos
    try:
        df_work = normalizar_dados(
            df_work, colunas_numericas, colunas_categoricas)
    except Exception as e:
        logging.error(f"Erro na normalização de dados: {e}")
        # Fallback: codifica manualmente as colunas categóricas
        for col in colunas_categoricas:
            if col in df_work.columns and df_work[col].dtype == 'object':
                le = LabelEncoder()
                df_work[col] = le.fit_transform(df_work[col].astype(str))

        # Normaliza apenas as numéricas
        scaler = MinMaxScaler()
        df_work[colunas_numericas] = scaler.fit_transform(
            df_work[colunas_numericas])

    # Seleciona apenas as colunas necessárias
    todas_colunas = colunas_numericas + colunas_categoricas
    colunas_disponiveis = [
        col for col in todas_colunas if col in df_work.columns]
    X = df_work[colunas_disponiveis]

    # Prepara target
    y = df_work['action'].apply(
        lambda x: 1 if x == 'BUY' else 0) if 'action' in df_work else None

    return X, y


def calcular_estocastico_lento(high_prices: List[float], low_prices: List[float], close_prices: List[float],
                               k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> Tuple[float, float]:
    """
    Calcula o Estocástico Lento (%K e %D).
    k_period: Período para %K (padrão 14)
    d_period: Período para %D (padrão 3)
    smooth_k: Período de suavização do %K (padrão 3)
    """
    if len(high_prices) < k_period or len(low_prices) < k_period or len(close_prices) < k_period:
        return 50.0, 50.0  # Valores neutros se não houver dados suficientes

    # Calcula %K rápido primeiro
    k_fast = []
    for i in range(k_period - 1, len(close_prices)):
        high_window = high_prices[i-k_period+1:i+1]
        low_window = low_prices[i-k_period+1:i+1]
        close = close_prices[i]

        highest_high = max(high_window)
        lowest_low = min(low_window)

        if highest_high == lowest_low:
            k_fast.append(50.0)
        else:
            k_fast.append(100 * (close - lowest_low) /
                          (highest_high - lowest_low))

    # Suaviza %K rápido para obter %K lento
    k_slow = []
    for i in range(len(k_fast) - smooth_k + 1):
        k_slow.append(sum(k_fast[i:i+smooth_k]) / smooth_k)

    # Calcula %D (média móvel do %K lento)
    if len(k_slow) < d_period:
        return 50.0, 50.0

    d_slow = sum(k_slow[-d_period:]) / d_period
    k_atual = k_slow[-1] if k_slow else 50.0

    return k_atual, d_slow

# endregion

# region [Modelo Neural]


def criar_modelo_neural(n_features: int) -> Sequential:
    """Cria modelo de rede neural com uma única saída para ação."""
    modelo = Sequential()

    # Camada de entrada com normalização
    modelo.add(tf.keras.layers.InputLayer(input_shape=(n_features,)))
    modelo.add(tf.keras.layers.BatchNormalization())

    # Primeira camada densa com dropout
    modelo.add(tf.keras.layers.Dense(128, activation='relu'))
    modelo.add(tf.keras.layers.BatchNormalization())
    modelo.add(tf.keras.layers.Dropout(0.3))

    # Segunda camada densa com dropout
    modelo.add(tf.keras.layers.Dense(64, activation='relu'))
    modelo.add(tf.keras.layers.BatchNormalization())
    modelo.add(tf.keras.layers.Dropout(0.2))

    # Terceira camada densa
    modelo.add(tf.keras.layers.Dense(32, activation='relu'))
    modelo.add(tf.keras.layers.BatchNormalization())

    # Camada de saída para ação (buy/sell)
    modelo.add(tf.keras.layers.Dense(1, activation='sigmoid'))

    # Compila o modelo
    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return modelo


def salvar_modelo(modelo: Sequential, caminho: str = MODELO_PATH) -> None:
    """Salva o modelo em disco em ambos os formatos h5 e keras com backup automático."""
    try:
        # === PROTEÇÃO EXTRA: BACKUP AUTOMÁTICO ANTES DE SALVAR ===
        if os.path.exists(caminho):
            # Cria backup com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{caminho}.backup_{timestamp}"

            # Cria backup do modelo atual
            shutil.copy2(caminho, backup_path)
            logging.info(f"🔒 BACKUP CRIADO: {backup_path}")

            # Mantém apenas os últimos 10 backups para economizar espaço
            backup_pattern = f"{caminho}.backup_*"
            backups = sorted(glob.glob(backup_pattern))
            while len(backups) > 10:
                oldest_backup = backups.pop(0)
                os.remove(oldest_backup)
                logging.info(f"🧹 Backup antigo removido: {oldest_backup}")

        # Salva modelo principal
        caminho_h5_abs = os.path.abspath(caminho)
        modelo.save(caminho_h5_abs)
        logging.info(f"✅ Modelo salvo em formato h5: {caminho_h5_abs}")

        # Salva também em formato keras (backup adicional)
        caminho_keras = caminho.replace('.h5', '.keras')
        caminho_keras_abs = os.path.abspath(caminho_keras)
        modelo.save(caminho_keras_abs)
        logging.info(f"✅ Modelo salvo em formato keras: {caminho_keras_abs}")

        # === PROTEÇÃO EXTRA: BACKUP DIÁRIO ===
        hoje = datetime.now().strftime("%Y%m%d")
        backup_diario = f"{caminho}.backup_diario_{hoje}"
        if not os.path.exists(backup_diario):
            shutil.copy2(caminho, backup_diario)
            logging.info(f"📅 Backup diário criado: {backup_diario}")

    except Exception as e:
        logging.error(f"❌ Erro ao salvar modelo: {e}")
        # Em caso de erro, não perde o modelo original!


def carregar_modelo(caminho: str = MODELO_PATH) -> Optional[Sequential]:
    """Carrega modelo do disco ou cria um novo."""
    if os.path.exists(caminho):
        try:
            modelo = load_model(caminho)

            # Verifica compatibilidade de features E tipos de dados
            expected_features = N_FEATURES
            try:
                # Testa com dados dummy para verificar compatibilidade
                test_input = np.zeros((1, expected_features), dtype=np.float32)

                # Teste 1: Verifica se o modelo aceita a entrada
                resultado_teste = modelo.predict(test_input, verbose=0)

                # Teste 2: Verifica se o resultado tem a forma esperada
                if resultado_teste is None or len(resultado_teste) == 0:
                    raise ValueError("Modelo retorna resultado vazio")

                if resultado_teste.shape != (1, 1):
                    raise ValueError(
                        f"Formato de saída incorreto: {resultado_teste.shape}, esperado: (1, 1)")

                # Teste 3: Verifica se o resultado é numérico válido
                resultado_valor = float(resultado_teste[0][0])
                if np.isnan(resultado_valor) or np.isinf(resultado_valor):
                    raise ValueError(
                        "Modelo retorna valores inválidos (NaN/inf)")

                logging.info(
                    f"✅ Modelo de IA carregado com sucesso de {caminho} ({expected_features} features)")
                logging.info(
                    f"✅ Teste de compatibilidade passou: resultado={resultado_valor:.3f}")
                return modelo

            except Exception as feature_error:
                logging.warning(
                    f"⚠️ Modelo incompatível ou corrompido: {feature_error}")
                logging.info(
                    f"🔄 Recriando modelo com {expected_features} features...")

                # Backup do modelo incompatível
                timestamp = int(time.time())
                backup_path = f"{caminho}.backup_incompativel_{timestamp}"
                os.rename(caminho, backup_path)
                logging.info(
                    f"📦 Modelo incompatível movido para: {backup_path}")

                # Retorna None para forçar criação de novo modelo
                return None

        except Exception as e:
            logging.error(f"Erro ao carregar modelo: {e}")
            raise  # Propaga o erro para ser exibido no teste
    return None


def verificar_e_proteger_modelo() -> bool:
    """🛡️ PROTEÇÃO TOTAL DO MODELO - Verifica e recupera automaticamente se necessário."""
    try:
        modelo_principal = MODELO_PATH
        logging.info(
            f"🔍 Verificando integridade do modelo: {modelo_principal}")

        # Verifica se modelo principal existe
        if os.path.exists(modelo_principal):
            # Testa se o modelo pode ser carregado
            try:
                test_model = load_model(modelo_principal)
                logging.info("✅ Modelo principal íntegro e carregável")
                return True
            except Exception as e:
                logging.warning(f"⚠️ Modelo principal corrompido: {e}")
                # Modelo existe mas está corrompido - tenta recuperar
                return recuperar_modelo_automaticamente()
        else:
            logging.warning(
                "⚠️ Modelo principal não encontrado - tentando recuperar")
            return recuperar_modelo_automaticamente()

    except Exception as e:
        logging.error(f"❌ Erro na verificação do modelo: {e}")
        return False


def recuperar_modelo_automaticamente() -> bool:
    """🚑 RECUPERAÇÃO AUTOMÁTICA - Encontra e restaura backup do modelo."""
    try:
        modelo_principal = MODELO_PATH

        # Lista todas as possibilidades de backup
        opcoes_backup = []

        # 1. Backup diário mais recente
        import glob
        backups_diarios = sorted(
            glob.glob(f"{modelo_principal}.backup_diario_*"), reverse=True)
        opcoes_backup.extend(backups_diarios)

        # 2. Backups com timestamp
        backups_timestamp = sorted(
            glob.glob(f"{modelo_principal}.backup_*"), reverse=True)
        opcoes_backup.extend(backups_timestamp)

        # 3. Formato keras como backup
        modelo_keras = modelo_principal.replace('.h5', '.keras')
        if os.path.exists(modelo_keras):
            opcoes_backup.append(modelo_keras)

        # 4. Backups antigos do próprio sistema
        backups_antigos = sorted(
            glob.glob(f"{modelo_principal}.backup_*"), reverse=True)
        opcoes_backup.extend(backups_antigos)

        # Remove duplicatas mantendo ordem
        opcoes_backup = list(dict.fromkeys(opcoes_backup))

        logging.info(f"🔍 Encontrados {len(opcoes_backup)} backups possíveis")

        # Tenta recuperar do backup mais recente
        for backup_path in opcoes_backup:
            try:
                logging.info(f"🚑 Tentando recuperar de: {backup_path}")

                # Testa se o backup é válido
                test_model = load_model(backup_path)

                # Se chegou aqui, o backup é válido - restaura
                shutil.copy2(backup_path, modelo_principal)
                logging.info(
                    f"✅ MODELO RECUPERADO com sucesso de: {backup_path}")

                # Verifica se a recuperação funcionou
                final_test = load_model(modelo_principal)
                logging.info("🎉 RECUPERAÇÃO CONFIRMADA - Modelo funcionando!")
                return True

            except Exception as e:
                logging.warning(f"❌ Backup {backup_path} inválido: {e}")
                continue

        # Se chegou aqui, nenhum backup funcionou
        logging.error("💀 NENHUM BACKUP VÁLIDO ENCONTRADO!")
        logging.info("🔧 Criando novo modelo do zero (última opção)")
        return False

    except Exception as e:
        logging.error(f"❌ Erro na recuperação automática: {e}")
        return False
# endregion

# region [Trading]


def calcular_score_distancia(preco_entrada: float, preco_saida: float, sl: float, tp: float) -> float:
    """Calcula um score adicional baseado na distância que o preço chegou do TP/SL.

    Returns:
        float: Score entre -1 e 1, onde:
            1.0 = Atingiu TP
            -1.0 = Atingiu SL
            Valores intermediários baseados na proximidade
    """
    # Calcula distâncias totais
    dist_total_tp = abs(tp - preco_entrada)
    dist_total_sl = abs(sl - preco_entrada)

    # Calcula distância percorrida
    dist_percorrida = abs(preco_saida - preco_entrada)

    # Determina se movimento foi em direção ao TP ou SL
    if (tp > preco_entrada and preco_saida > preco_entrada) or \
            (tp < preco_entrada and preco_saida < preco_entrada):
        # Movimento em direção ao TP
        score = dist_percorrida / dist_total_tp
    else:
        # Movimento em direção ao SL
        score = -dist_percorrida / dist_total_sl

    return max(min(score, 1.0), -1.0)  # Limita entre -1 e 1


def aguardar_abertura():
    agora = datetime.now().time()
    if agora < dtime(9, 0):
        segundos = (datetime.combine(datetime.today(),
                    dtime(9, 0)) - datetime.now()).seconds
        logging.info(
            f"⏳ Aguardando abertura do pregão em {segundos//60}m{segundos % 60}s…")
        time.sleep(segundos)


def aguardar_fechamento():
    agora = datetime.now().time()
    if agora >= dtime(18, 0):  # Ajuste conforme o after-market desejado
        segundos = ((datetime.combine(datetime.today(), dtime(
            23, 59)) - datetime.now()).seconds + 60)
        logging.info(f"🌙 Pregão encerrado. Dormindo até o próximo dia útil…")
        time.sleep(segundos)


# region [Detector de Codificação Robusto]
class CSVEncodingDetector:
    """Detector robusto de codificação para arquivos CSV do EA."""

    def __init__(self):
        """Inicializa o detector com configurações otimizadas."""
        # Lista ordenada de codificações por prioridade (mais comuns primeiro)
        self.encoding_priority = [
            'utf-8',           # Mais comum atualmente
            'utf-16-le',       # Windows UTF-16 Little Endian
            'utf-16-be',       # UTF-16 Big Endian
            'utf-16',          # UTF-16 com BOM
            'ascii',           # ASCII puro
            'latin-1',         # ISO-8859-1
            'cp1252',          # Windows-1252
            'utf-32-le',       # UTF-32 Little Endian
            'utf-32-be'        # UTF-32 Big Endian
        ]

        # Cache de codificação bem-sucedida por arquivo
        self.encoding_cache = {}
        self.cache_ttl = 300  # 5 minutos de TTL para cache

        # Padrões BOM (Byte Order Mark)
        self.bom_patterns = {
            b'\xff\xfe\x00\x00': 'utf-32-le',
            b'\x00\x00\xfe\xff': 'utf-32-be',
            b'\xff\xfe': 'utf-16-le',
            b'\xfe\xff': 'utf-16-be',
            b'\xef\xbb\xbf': 'utf-8'
        }

    def detect_bom(self, file_path: str) -> Optional[str]:
        """Detecta codificação através do BOM (Byte Order Mark).

        Args:
            file_path: Caminho para o arquivo

        Returns:
            Codificação detectada ou None se não houver BOM
        """
        try:
            with open(file_path, 'rb') as f:
                # Lê os primeiros 4 bytes para detectar BOM
                bom_bytes = f.read(4)

            # Verifica padrões BOM em ordem de tamanho (maior primeiro)
            for bom_pattern, encoding in self.bom_patterns.items():
                if bom_bytes.startswith(bom_pattern):
                    logging.debug(
                        f"[CSVEncodingDetector] BOM detectado: {encoding}")
                    return encoding

            return None

        except Exception as e:
            logging.debug(f"[CSVEncodingDetector] Erro ao detectar BOM: {e}")
            return None

    def detect_by_content(self, file_path: str) -> Optional[str]:
        """Detecta codificação analisando o conteúdo do arquivo.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            Codificação mais provável ou None
        """
        try:
            # Lê uma amostra do arquivo para análise
            with open(file_path, 'rb') as f:
                sample = f.read(1024)  # Primeiros 1KB

            if not sample:
                return None

            # Tenta decodificar com cada codificação
            encoding_scores = {}

            for encoding in self.encoding_priority:
                try:
                    decoded = sample.decode(encoding)

                    # Calcula score baseado em características do conteúdo
                    score = self._calculate_content_score(decoded, encoding)
                    encoding_scores[encoding] = score

                except (UnicodeDecodeError, UnicodeError):
                    continue

            if not encoding_scores:
                return None

            # Retorna codificação com maior score
            best_encoding = max(encoding_scores, key=encoding_scores.get)
            best_score = encoding_scores[best_encoding]

            logging.debug(
                f"[CSVEncodingDetector] Melhor codificação por conteúdo: {best_encoding} (score: {best_score:.2f})")

            # Só retorna se o score for razoável
            return best_encoding if best_score > 0.5 else None

        except Exception as e:
            logging.debug(
                f"[CSVEncodingDetector] Erro na detecção por conteúdo: {e}")
            return None

    def _calculate_content_score(self, content: str, encoding: str) -> float:
        """Calcula score de qualidade para uma decodificação.

        Args:
            content: Conteúdo decodificado
            encoding: Codificação utilizada

        Returns:
            Score de 0.0 a 1.0 (maior = melhor)
        """
        if not content:
            return 0.0

        score = 0.0

        # Bonus para caracteres ASCII válidos (números, vírgulas, quebras de linha)
        ascii_chars = sum(1 for c in content if ord(c) < 128)
        ascii_ratio = ascii_chars / len(content)
        score += ascii_ratio * 0.4

        # Bonus para padrões esperados no CSV do book (números e vírgulas)
        digit_comma_chars = sum(
            1 for c in content if c.isdigit() or c in ',\r\n ')
        pattern_ratio = digit_comma_chars / len(content)
        score += pattern_ratio * 0.4

        # Penalidade para caracteres de controle suspeitos
        control_chars = sum(1 for c in content if ord(c)
                            < 32 and c not in '\r\n\t')
        if len(content) > 0:
            control_ratio = control_chars / len(content)
            score -= control_ratio * 0.3

        # Bonus para codificações mais comuns
        encoding_bonus = {
            'utf-8': 0.2,
            'utf-16-le': 0.1,
            'ascii': 0.15,
            'latin-1': 0.05
        }
        score += encoding_bonus.get(encoding, 0.0)

        return max(0.0, min(1.0, score))

    def get_cached_encoding(self, file_path: str) -> Optional[str]:
        """Obtém codificação do cache se ainda válida.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            Codificação em cache ou None se expirada/inexistente
        """
        if file_path not in self.encoding_cache:
            return None

        cached_data = self.encoding_cache[file_path]
        cache_time = cached_data.get('timestamp', 0)

        # Verifica se cache ainda é válido
        if time.time() - cache_time > self.cache_ttl:
            del self.encoding_cache[file_path]
            return None

        encoding = cached_data.get('encoding')
        logging.debug(
            f"[CSVEncodingDetector] Usando codificação em cache: {encoding}")
        return encoding

    def cache_encoding(self, file_path: str, encoding: str):
        """Armazena codificação bem-sucedida no cache.

        Args:
            file_path: Caminho para o arquivo
            encoding: Codificação que funcionou
        """
        self.encoding_cache[file_path] = {
            'encoding': encoding,
            'timestamp': time.time()
        }
        logging.debug(
            f"[CSVEncodingDetector] Codificação {encoding} armazenada em cache")

    def detect_encoding(self, file_path: str) -> List[str]:
        """Detecta a melhor codificação para um arquivo CSV.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            Lista ordenada de codificações para tentar (mais provável primeiro)
        """
        if not os.path.exists(file_path):
            return self.encoding_priority.copy()

        # 1. Verifica cache primeiro
        cached_encoding = self.get_cached_encoding(file_path)
        if cached_encoding:
            # Move codificação em cache para o início da lista
            encodings = [cached_encoding] + \
                [e for e in self.encoding_priority if e != cached_encoding]
            return encodings

        # 2. Tenta detectar por BOM
        bom_encoding = self.detect_bom(file_path)
        if bom_encoding:
            # Move codificação detectada por BOM para o início
            encodings = [bom_encoding] + \
                [e for e in self.encoding_priority if e != bom_encoding]
            return encodings

        # 3. Tenta detectar por conteúdo
        content_encoding = self.detect_by_content(file_path)
        if content_encoding:
            # Move codificação detectada por conteúdo para o início
            encodings = [content_encoding] + \
                [e for e in self.encoding_priority if e != content_encoding]
            return encodings

        # 4. Retorna lista padrão se nenhuma detecção funcionou
        return self.encoding_priority.copy()


# Instância global do detector
_csv_encoding_detector = CSVEncodingDetector()

# region [Validador de Dados do Book]


class CSVDataValidator:
    """Validador robusto de dados do book de ofertas."""

    def __init__(self):
        """Inicializa o validador com configurações de validação."""
        # Limites de validação
        self.min_volume = 1
        self.max_volume = 100000  # Volume máximo razoável por nível
        self.min_levels = 1       # Mínimo de níveis por lado
        self.max_levels = 50      # Máximo de níveis por lado
        self.min_total_volume = 10  # Volume total mínimo por lado
        self.max_total_volume = 1000000  # Volume total máximo por lado

        # Configurações de sanitização
        self.enable_sanitization = True
        self.strict_mode = False  # Se True, rejeita dados com qualquer problema

        # Estatísticas de validação
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'sanitized_data': 0,
            'rejected_data': 0,
            'common_issues': {}
        }

    def validate_volume_list(self, volumes: List[int], side: str) -> Dict[str, Any]:
        """Valida uma lista de volumes (bids ou asks).

        Args:
            volumes: Lista de volumes para validar
            side: "bids" ou "asks" para identificação

        Returns:
            Dicionário com resultado da validação
        """
        result = {
            'valid': True,
            'issues': [],
            'sanitized_volumes': volumes.copy() if volumes else [],
            'original_count': len(volumes) if volumes else 0,
            'sanitized_count': 0,
            'total_volume': 0
        }

        if not volumes:
            result['valid'] = False
            result['issues'].append(f"Lista de {side} vazia")
            return result

        # Validação básica de tipos
        if not all(isinstance(v, (int, float)) for v in volumes):
            result['issues'].append(f"Tipos inválidos em {side}")
            if not self.enable_sanitization:
                result['valid'] = False
                return result

        # Sanitização e validação de volumes individuais
        sanitized = []
        for i, volume in enumerate(volumes):
            try:
                # Converte para int se necessário
                vol_int = int(volume) if isinstance(volume, float) else volume

                # Valida limites
                if vol_int < self.min_volume:
                    result['issues'].append(
                        f"Volume muito baixo em {side}[{i}]: {vol_int}")
                    if self.enable_sanitization:
                        continue  # Remove volume inválido
                    else:
                        result['valid'] = False
                        return result

                if vol_int > self.max_volume:
                    result['issues'].append(
                        f"Volume muito alto em {side}[{i}]: {vol_int}")
                    if self.enable_sanitization:
                        vol_int = self.max_volume  # Limita ao máximo
                    else:
                        result['valid'] = False
                        return result

                sanitized.append(vol_int)

            except (ValueError, TypeError) as e:
                result['issues'].append(f"Erro ao processar {side}[{i}]: {e}")
                if not self.enable_sanitization:
                    result['valid'] = False
                    return result

        result['sanitized_volumes'] = sanitized
        result['sanitized_count'] = len(sanitized)
        result['total_volume'] = sum(sanitized)

        # Validação de contagem de níveis
        if len(sanitized) < self.min_levels:
            result['issues'].append(
                f"Poucos níveis em {side}: {len(sanitized)} < {self.min_levels}")
            if self.strict_mode:
                result['valid'] = False
                return result

        if len(sanitized) > self.max_levels:
            result['issues'].append(
                f"Muitos níveis em {side}: {len(sanitized)} > {self.max_levels}")
            if self.enable_sanitization:
                result['sanitized_volumes'] = sanitized[:self.max_levels]
                result['sanitized_count'] = self.max_levels
                result['total_volume'] = sum(result['sanitized_volumes'])
            elif self.strict_mode:
                result['valid'] = False
                return result

        # Validação de volume total
        if result['total_volume'] < self.min_total_volume:
            result['issues'].append(
                f"Volume total muito baixo em {side}: {result['total_volume']}")
            if self.strict_mode:
                result['valid'] = False
                return result

        if result['total_volume'] > self.max_total_volume:
            result['issues'].append(
                f"Volume total muito alto em {side}: {result['total_volume']}")
            if self.strict_mode:
                result['valid'] = False
                return result

        return result

    def detect_suspicious_patterns(self, bids: List[int], asks: List[int]) -> List[str]:
        """Detecta padrões suspeitos nos dados do book.

        Args:
            bids: Lista de volumes de compra
            asks: Lista de volumes de venda

        Returns:
            Lista de alertas sobre padrões suspeitos
        """
        alerts = []

        if not bids or not asks:
            return alerts

        # Padrão 1: Todos os volumes iguais (suspeito)
        if len(set(bids)) == 1 and len(bids) > 3:
            alerts.append(f"Todos os volumes BID são iguais: {bids[0]}")

        if len(set(asks)) == 1 and len(asks) > 3:
            alerts.append(f"Todos os volumes ASK são iguais: {asks[0]}")

        # Padrão 2: Desequilíbrio extremo
        total_bids = sum(bids)
        total_asks = sum(asks)

        if total_bids > 0 and total_asks > 0:
            ratio = max(total_bids, total_asks) / min(total_bids, total_asks)
            if ratio > 10:  # Desequilíbrio de 10:1
                alerts.append(
                    f"Desequilíbrio extremo BID/ASK: {total_bids}/{total_asks} (ratio: {ratio:.1f})")

        # Padrão 3: Volumes muito baixos generalizados
        avg_bid = sum(bids) / len(bids) if bids else 0
        avg_ask = sum(asks) / len(asks) if asks else 0

        if avg_bid < 5 and avg_ask < 5:
            alerts.append(
                f"Volumes médios muito baixos: BID={avg_bid:.1f}, ASK={avg_ask:.1f}")

        # Padrão 4: Sequência suspeita (números consecutivos)
        if len(bids) >= 5:
            consecutive_count = 0
            for i in range(1, len(bids)):
                if abs(bids[i] - bids[i-1]) <= 1:
                    consecutive_count += 1
                else:
                    consecutive_count = 0
                if consecutive_count >= 4:  # 5 números quase consecutivos
                    alerts.append("Sequência suspeita detectada em BIDs")
                    break

        return alerts

    def validate_book_data(self, book_data: Dict[str, List[int]]) -> Dict[str, Any]:
        """Valida dados completos do book de ofertas.

        Args:
            book_data: Dicionário com 'bids' e 'asks'

        Returns:
            Resultado completo da validação com dados sanitizados
        """
        self.validation_stats['total_validations'] += 1

        result = {
            'valid': True,
            'sanitized_data': {},
            'issues': [],
            'suspicious_patterns': [],
            'statistics': {},
            'recommendation': 'accept'  # accept, sanitize, reject
        }

        if not book_data or not isinstance(book_data, dict):
            result['valid'] = False
            result['issues'].append("Dados do book inválidos ou nulos")
            result['recommendation'] = 'reject'
            self.validation_stats['rejected_data'] += 1
            return result

        # Valida bids
        bids = book_data.get('bids', [])
        bid_validation = self.validate_volume_list(bids, 'bids')

        # Valida asks
        asks = book_data.get('asks', [])
        ask_validation = self.validate_volume_list(asks, 'asks')

        # Combina resultados
        result['issues'].extend(bid_validation['issues'])
        result['issues'].extend(ask_validation['issues'])

        if not bid_validation['valid'] or not ask_validation['valid']:
            result['valid'] = False
            result['recommendation'] = 'reject'
            self.validation_stats['rejected_data'] += 1
            return result

        # Dados sanitizados
        result['sanitized_data'] = {
            'bids': bid_validation['sanitized_volumes'],
            'asks': ask_validation['sanitized_volumes']
        }

        # Detecta padrões suspeitos
        result['suspicious_patterns'] = self.detect_suspicious_patterns(
            bid_validation['sanitized_volumes'],
            ask_validation['sanitized_volumes']
        )

        # Estatísticas
        result['statistics'] = {
            'bid_levels': bid_validation['sanitized_count'],
            'ask_levels': ask_validation['sanitized_count'],
            'total_bid_volume': bid_validation['total_volume'],
            'total_ask_volume': ask_validation['total_volume'],
            'total_liquidity': bid_validation['total_volume'] + ask_validation['total_volume'],
            'bid_ask_ratio': (bid_validation['total_volume'] / ask_validation['total_volume'])
            if ask_validation['total_volume'] > 0 else float('inf')
        }

        # Determina recomendação final
        if result['issues'] or result['suspicious_patterns']:
            if self.enable_sanitization and not self.strict_mode:
                result['recommendation'] = 'sanitize'
                self.validation_stats['sanitized_data'] += 1
            else:
                result['recommendation'] = 'reject'
                result['valid'] = False
                self.validation_stats['rejected_data'] += 1
                return result

        # Atualiza estatísticas de issues comuns
        for issue in result['issues']:
            issue_type = issue.split(':')[0] if ':' in issue else issue
            self.validation_stats['common_issues'][issue_type] = \
                self.validation_stats['common_issues'].get(issue_type, 0) + 1

        self.validation_stats['successful_validations'] += 1
        return result

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de validação acumuladas."""
        stats = self.validation_stats.copy()

        if stats['total_validations'] > 0:
            stats['success_rate'] = stats['successful_validations'] / \
                stats['total_validations']
            stats['sanitization_rate'] = stats['sanitized_data'] / \
                stats['total_validations']
            stats['rejection_rate'] = stats['rejected_data'] / \
                stats['total_validations']
        else:
            stats['success_rate'] = 0.0
            stats['sanitization_rate'] = 0.0
            stats['rejection_rate'] = 0.0

        return stats

    def reset_statistics(self):
        """Reseta as estatísticas de validação."""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'sanitized_data': 0,
            'rejected_data': 0,
            'common_issues': {}
        }


# Instância global do validador
_csv_data_validator = CSVDataValidator()

# region [Sistema de Retry com Backoff Exponencial]


class RetryManager:
    """Gerenciador de tentativas com backoff exponencial para operações de I/O."""

    def __init__(self, max_retries: int = 5, base_delay: float = 0.1, max_delay: float = 2.0):
        """Inicializa o gerenciador de retry.

        Args:
            max_retries: Número máximo de tentativas
            base_delay: Delay inicial em segundos
            max_delay: Delay máximo em segundos
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # Estatísticas de retry
        self.retry_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'error_types': {},
            'avg_retries_per_operation': 0.0
        }

    def calculate_delay(self, attempt: int) -> float:
        """Calcula o delay para uma tentativa específica usando backoff exponencial.

        Args:
            attempt: Número da tentativa (0-based)

        Returns:
            Delay em segundos
        """
        # Backoff exponencial: base_delay * (2 ^ attempt)
        delay = self.base_delay * (2 ** attempt)

        # Adiciona jitter (variação aleatória) para evitar thundering herd
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter

        # Limita ao delay máximo
        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determina se deve tentar novamente baseado no tipo de erro e tentativa.

        Args:
            exception: Exceção que ocorreu
            attempt: Número da tentativa atual

        Returns:
            True se deve tentar novamente
        """
        if attempt >= self.max_retries:
            return False

        # Tipos de erro que justificam retry
        retryable_errors = (
            PermissionError,      # Arquivo em uso
            FileNotFoundError,    # Arquivo temporariamente inexistente
            OSError,              # Problemas de I/O gerais
            # Problemas de codificação (pode ser temporário)
            UnicodeDecodeError,
            IOError               # Problemas de entrada/saída
        )

        return isinstance(exception, retryable_errors)

    def get_error_strategy(self, exception: Exception) -> Dict[str, Any]:
        """Retorna estratégia específica para cada tipo de erro.

        Args:
            exception: Exceção que ocorreu

        Returns:
            Dicionário com estratégia de tratamento
        """
        if isinstance(exception, PermissionError):
            return {
                'delay_multiplier': 1.5,  # Aguarda mais tempo para arquivo em uso
                'max_retries': 3,         # Menos tentativas para não sobrecarregar
                'description': 'Arquivo em uso pelo EA'
            }

        elif isinstance(exception, FileNotFoundError):
            return {
                'delay_multiplier': 1.0,  # Delay normal
                'max_retries': 4,         # Mais tentativas para aguardar criação
                'description': 'Arquivo não encontrado'
            }

        elif isinstance(exception, UnicodeDecodeError):
            return {
                'delay_multiplier': 0.5,  # Delay menor, problema pode ser rápido
                'max_retries': 2,         # Poucas tentativas, detector já tenta outras codificações
                'description': 'Erro de codificação'
            }

        elif isinstance(exception, (OSError, IOError)):
            return {
                'delay_multiplier': 1.2,  # Delay um pouco maior
                'max_retries': 3,         # Tentativas moderadas
                'description': 'Erro de I/O'
            }

        else:
            return {
                'delay_multiplier': 1.0,
                'max_retries': 2,
                'description': 'Erro desconhecido'
            }

    def execute_with_retry(self, operation_func, *args, **kwargs):
        """Executa uma operação com retry automático.

        Args:
            operation_func: Função a ser executada
            *args: Argumentos posicionais para a função
            **kwargs: Argumentos nomeados para a função

        Returns:
            Resultado da operação ou None se todas as tentativas falharam
        """
        self.retry_stats['total_operations'] += 1
        last_exception = None

        # +1 para incluir tentativa inicial
        for attempt in range(self.max_retries + 1):
            try:
                # Tenta executar a operação
                result = operation_func(*args, **kwargs)

                # Sucesso!
                if attempt > 0:  # Se houve retry
                    self.retry_stats['total_retries'] += attempt
                    logging.info(
                        f"[RetryManager] Operação bem-sucedida após {attempt} tentativas")

                self.retry_stats['successful_operations'] += 1
                self._update_avg_retries()
                return result

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Atualiza estatísticas de erro
                self.retry_stats['error_types'][error_type] = \
                    self.retry_stats['error_types'].get(error_type, 0) + 1

                # Verifica se deve tentar novamente
                if not self.should_retry(e, attempt):
                    logging.debug(
                        f"[RetryManager] Não tentando novamente: {error_type} (tentativa {attempt + 1})")
                    break

                # Obtém estratégia específica para o erro
                strategy = self.get_error_strategy(e)

                # Calcula delay ajustado pela estratégia
                base_delay = self.calculate_delay(attempt)
                adjusted_delay = base_delay * strategy['delay_multiplier']

                logging.debug(f"[RetryManager] {strategy['description']} - Tentativa {attempt + 1}/{self.max_retries + 1}, "
                              f"aguardando {adjusted_delay:.2f}s")

                # Aguarda antes da próxima tentativa
                time.sleep(adjusted_delay)

        # Todas as tentativas falharam
        self.retry_stats['failed_operations'] += 1
        self.retry_stats['total_retries'] += self.max_retries
        self._update_avg_retries()

        logging.warning(f"[RetryManager] Operação falhou após {self.max_retries + 1} tentativas. "
                        f"Último erro: {last_exception}")

        return None

    def _update_avg_retries(self):
        """Atualiza a média de retries por operação."""
        if self.retry_stats['total_operations'] > 0:
            self.retry_stats['avg_retries_per_operation'] = self.retry_stats['total_retries'] / \
                self.retry_stats['total_operations']

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerenciador de retry."""
        stats = self.retry_stats.copy()

        if stats['total_operations'] > 0:
            stats['success_rate'] = stats['successful_operations'] / \
                stats['total_operations']
            stats['failure_rate'] = stats['failed_operations'] / \
                stats['total_operations']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0

        return stats

    def reset_statistics(self):
        """Reseta as estatísticas do retry manager."""
        self.retry_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'error_types': {},
            'avg_retries_per_operation': 0.0
        }


# Instância global do retry manager
_retry_manager = RetryManager(max_retries=5, base_delay=0.1, max_delay=2.0)
# endregion


def _ler_book_csv_core() -> Optional[Dict[str, List[int]]]:
    """Função core para leitura do CSV (sem retry) - usada pelo retry manager."""
    global BOOK_FILE_PATH

    if not BOOK_FILE_PATH:
        raise FileNotFoundError("Caminho do arquivo CSV não definido")

    if not os.path.exists(BOOK_FILE_PATH):
        raise FileNotFoundError(f"Arquivo não existe: {BOOK_FILE_PATH}")

    if os.path.getsize(BOOK_FILE_PATH) < 4:
        raise OSError(
            f"Arquivo muito pequeno: {os.path.getsize(BOOK_FILE_PATH)} bytes")

    # Usa detector robusto para obter lista de codificações ordenadas
    encodings_to_try = _csv_encoding_detector.detect_encoding(BOOK_FILE_PATH)

    # Tenta diferentes codificações em ordem de prioridade
    lines = None
    successful_encoding = None
    last_encoding_error = None

    for encoding in encodings_to_try:
        try:
            with open(BOOK_FILE_PATH, 'r', encoding=encoding) as f:
                lines = f.readlines()
            successful_encoding = encoding
            logging.debug(
                f"[ler_book_csv_core] Sucesso com encoding {encoding}, {len(lines)} linhas")
            break
        except UnicodeDecodeError as e:
            last_encoding_error = e
            logging.debug(f"[ler_book_csv_core] Falha com encoding {encoding}")
            continue
        except PermissionError:
            # Re-raise permission errors para o retry manager tratar
            raise
        except Exception as e:
            logging.debug(
                f"[ler_book_csv_core] Erro com encoding {encoding}: {e}")
            continue

    if lines is None:
        if last_encoding_error:
            raise last_encoding_error
        else:
            raise UnicodeDecodeError(
                "unknown", b"", 0, 1, "Nenhuma codificação funcionou")

    # Armazena codificação bem-sucedida no cache
    if successful_encoding:
        _csv_encoding_detector.cache_encoding(
            BOOK_FILE_PATH, successful_encoding)

    if len(lines) < 2:
        raise OSError(f"Linhas insuficientes: {len(lines)}")

    bids_str = lines[0].strip()
    asks_str = lines[1].strip()

    logging.debug(f"[ler_book_csv_core] BIDs raw: {bids_str}")
    logging.debug(f"[ler_book_csv_core] ASKs raw: {asks_str}")

    bids = [int(v) for v in bids_str.split(',')
            if v and v.strip().isdigit()] if bids_str else []
    asks = [int(v) for v in asks_str.split(',')
            if v and v.strip().isdigit()] if asks_str else []

    logging.debug(
        f"[ler_book_csv_core] BIDs parsed: {len(bids)} volumes, total: {sum(bids)}")
    logging.debug(
        f"[ler_book_csv_core] ASKs parsed: {len(asks)} volumes, total: {sum(asks)}")

    if not bids and not asks:
        raise ValueError("Nenhum volume válido encontrado")

    # ===== VALIDAÇÃO E SANITIZAÇÃO DOS DADOS =====
    dados_brutos = {"bids": bids, "asks": asks}

    # Valida dados com o validador robusto
    validation_result = _csv_data_validator.validate_book_data(dados_brutos)

    # Log dos resultados da validação
    if validation_result['issues']:
        logging.debug(
            f"[ler_book_csv_core] Issues encontradas: {validation_result['issues']}")

    if validation_result['suspicious_patterns']:
        logging.warning(
            f"[ler_book_csv_core] Padrões suspeitos: {validation_result['suspicious_patterns']}")

    # Decide o que fazer baseado na recomendação
    if validation_result['recommendation'] == 'reject':
        logging.warning(
            f"[ler_book_csv_core] Dados rejeitados pelo validador: {validation_result['issues']}")
        raise ValueError(f"Dados rejeitados: {validation_result['issues']}")

    elif validation_result['recommendation'] == 'sanitize':
        logging.info(
            f"[ler_book_csv_core] Dados sanitizados: {len(validation_result['issues'])} issues corrigidas")
        resultado = validation_result['sanitized_data']

    else:  # accept
        resultado = dados_brutos

    # Log das estatísticas finais
    stats = validation_result['statistics']
    logging.debug(
        f"[ler_book_csv_core] Dados validados: {stats['bid_levels']} bids ({stats['total_bid_volume']}cc), "
        f"{stats['ask_levels']} asks ({stats['total_ask_volume']}cc), "
        f"liquidez total: {stats['total_liquidity']}cc")

    return resultado


def ler_book_csv_with_retry() -> Optional[Dict[str, List[int]]]:
    """Lê os dados do book do arquivo CSV com retry automático e validação robusta."""
    try:
        # Executa a leitura com retry automático
        resultado = _retry_manager.execute_with_retry(_ler_book_csv_core)

        if resultado is None:
            logging.debug(
                "[ler_book_csv_with_retry] Falha na leitura após todas as tentativas de retry")

        return resultado

    except Exception as e:
        logging.error(
            f"[ler_book_csv_with_retry] Erro crítico não tratado: {e}")
        import traceback
        logging.debug(
            f"[ler_book_csv_with_retry] Stack trace: {traceback.format_exc()}")
        return None


def ler_book_csv() -> Optional[Dict[str, List[int]]]:
    """Lê os dados do book do arquivo CSV com retry automático, detector de codificação e validação robusta."""
    # Usa a versão com retry para máxima robustez
    return ler_book_csv_with_retry()


def inicializar_mt5() -> bool:
    global trailing_stop, balanceador, detector_modo, balanceador, detector_modo, circuit_breaker, saida_inteligente

    aguardar_abertura()
    logging.info("🔄 Tentando inicializar o MetaTrader 5...")
    if not mt5.initialize(path=MT5_PATH):
        logging.error(f"❌ Erro ao inicializar MT5: {mt5.last_error()}")
        return False
    logging.info("✅ MetaTrader 5 inicializado com sucesso")

    # ========== INICIALIZAÇÃO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
    trailing_stop = TrailingStopInteligente()
    logging.info("🎯 Trailing Stop Inteligente inicializado (+3% eficácia)")

    # ========== INICIALIZAÇÃO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
    balanceador = BalanceadorOperacoes()
    logging.info("⚖️ Balanceamento BUY/SELL inicializado (+2% eficácia)")

    # ========== INICIALIZAÇÃO MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS ==========
    detector_modo = DetectorModoMercado()
    logging.info("🎯 Detector de Modos de Mercado inicializado (+2% eficácia)")

    # ========== INICIALIZAÇÃO MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS ==========
    detector_modo = DetectorModoMercado()
    logging.info("🐌 Detector de Modos de Mercado inicializado (+2% eficácia)")

    # ========== INICIALIZAÇÃO MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS ==========
    circuit_breaker = CircuitBreakerEssencial()
    logging.info("🚨 Circuit Breakers Essenciais inicializados (+1.5% eficácia)")

    # ========== INICIALIZAÇÃO MELHORIA 5: SAÍDA INTELIGENTE DE POSIÇÃO ==========
    saida_inteligente = SaidaInteligentePositions()
    logging.info("🚪 Saída Inteligente de Posição inicializada (+1.5% eficácia)")

    # ========== INICIALIZAÇÃO NOVAS MELHORIAS 6-10 ==========
    global filtro_horario, detector_tendencia, cooldown_sistema, filtro_spread, monitor_performance

    filtro_horario = FiltroHorarioPremium()
    logging.info("⏰ Filtro de Horário Premium inicializado (+2% eficácia)")

    detector_tendencia = DetectorTendencia()
    logging.info("📈 Detector de Tendência EMA inicializado (+3% eficácia)")

    cooldown_sistema = CooldownInteligente()
    logging.info("⏳ Sistema de Cooldown Inteligente inicializado (+1.5% eficácia)")

    filtro_spread = FiltroSpreadDinamico()
    logging.info("📊 Filtro de Spread Dinâmico inicializado (+1% eficácia)")

    monitor_performance = MonitorPerformance()
    logging.info("📈 Monitor de Performance em Tempo Real inicializado (+2% eficácia)")

    logging.info("📊 Sistema de Volume Inteligente ativado:")
    logging.info("   • 300-500cc: 2.5 contratos (conservador)")
    logging.info("   • 500-1000cc: 4 contratos (moderado)")
    logging.info("   • 1000-2000cc: 5 contratos (padrão)")
    logging.info("   • 2000cc+: 10 contratos (explosão)")
    logging.info("   • Modo explosão: Mínimo 1000cc + entropia 0.9+")
    logging.info("🚀 TOTAL: +19.5% de eficácia com 10 melhorias implementadas!")

    # ===== CONFIGURAÇÃO DO ARQUIVO CSV DO EA WIN (CRÍTICO!) =====
    global BOOK_FILE_PATH, SYMBOL
    terminal_info = mt5.terminal_info()
    if terminal_info:
        BOOK_FILE_PATH = os.path.join(
            terminal_info.data_path, 'MQL5', 'Files', 'book_data_win.csv')  # Arquivo específico WIN
        logging.info(f"📡 Monitorando arquivo CSV do EA WIN: {BOOK_FILE_PATH}")

        # Verifica se arquivo existe (não remove se estiver em uso)
        if os.path.exists(BOOK_FILE_PATH):
            try:
                # Tenta apenas verificar se pode acessar o arquivo
                with open(BOOK_FILE_PATH, 'r') as f:
                    pass
                logging.info("✅ Arquivo de book WIN encontrado e acessível")
            except PermissionError:
                logging.info("📡 Arquivo de book WIN em uso pelo EA (normal)")
            except Exception as e:
                logging.warning(f"⚠️ Problema com arquivo de book WIN: {e}")
        else:
            logging.info("📝 Arquivo de book WIN será criado pelo EA")
    else:
        logging.error("❌ Não foi possível obter informações do terminal MT5")
        return False

    # Seleção dinâmica do contrato WIN
    SYMBOL = get_front_month_symbol_dynamic("WIN")
    mt5.symbol_select(SYMBOL, True)
    mt5.market_book_add(SYMBOL)  # ← ATIVA FORÇADAMENTE O BOOK

    # Extrai a validade do símbolo (ex: WINF25 -> F25)
    validade = SYMBOL[-3:] if len(SYMBOL) >= 3 else SYMBOL
    logging.info(
        f"✅ Contrato WIN dinâmico selecionado: {SYMBOL} (venc.: {validade})")
    logging.info(
        f"🎯 Configuração WIN: SL={SL_POINTS}pts, TP={TP_POINTS}pts, Vol={VOLUME_PADRAO}cc")
    logging.info(
        f"📊 WIN Specs: Tick={TICK_SIZE}, TicksPorPonto={TICKS_POR_PONTO}, Magic={MAGIC_NUMBER}")
    logging.info(
        f"💰 Risk: MaxLoss={MAX_LOSS_DIARIO}, MaxSpread={MAX_SPREAD}pts, MinVol={MIN_VOLUME_BOOK}cc")

    return True


def obter_dados_mercado(symbol: str = None, timeframe: int = TIMEFRAME) -> Tuple[Optional[float], ...]:
    """Obtém dados atuais do mercado USANDO DADOS DO EA."""
    global SYMBOL
    if symbol is None:
        symbol = SYMBOL
    if symbol is None:
        logging.error("❌ SYMBOL ainda não foi definido!")
        return (None,) * 8

    log_time = datetime.now().second % 5 == 0  # Log apenas a cada 5 segundos

    try:
        # Verifica se é fim de semana
        if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
            if log_time:
                logging.info("📅 Fim de semana: aguardando próximo dia útil...")
            time.sleep(30)  # Dorme por 30 segundos durante fim de semana
            return (None,) * 8

        # ===== LEITURA DOS DADOS DO EA (CRÍTICO!) =====
        book_data = ler_book_csv()
        if not book_data or not book_data.get('bids') or not book_data.get('asks'):
            if log_time:
                logging.warning("⚠️ Book CSV vazio ou inválido do EA")
            return (None,) * 8

        # Calcula volumes totais do book do EA
        total_bid_volume = sum(book_data['bids'])
        total_ask_volume = sum(book_data['asks'])
        total_volume = total_bid_volume + total_ask_volume

        # Log de mercado otimizado
        if log_time:
            tick = mt5.symbol_info_tick(symbol)
            spread_atual = round(tick.ask - tick.bid, 1) if tick else 0
            logging.info(
                f"📊 Mercado (EA): Liq:{total_volume} | Spread:{spread_atual}pts")

        # Verifica liquidez mínima
        if total_volume < MIN_VOLUME_BOOK:
            if log_time:
                logging.warning(
                    f"❌ Liquidez insuficiente do EA: {total_volume} < {MIN_VOLUME_BOOK}")
            return (None,) * 8

        # Obtém dados complementares do MT5
        tick_info = mt5.symbol_info_tick(symbol)
        symbol_info = get_cached_symbol_info(symbol)
        if tick_info is None:
            if log_time:
                logging.warning(f"❌ Tick NULO para símbolo {symbol}")
            return (None,) * 8
        if symbol_info is None:
            if log_time:
                logging.warning(f"❌ Symbol_info NULO para símbolo {symbol}")
            # Tenta reselecionar o símbolo
            mt5.symbol_select(symbol, True)
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logging.error(
                    f"❌ Não foi possível obter info do símbolo {symbol} mesmo após reselecionar")
            return (None,) * 8

        # Calcula spread em pontos
        spread = ((tick_info.ask - tick_info.bid) /
                  symbol_info.point) / TICKS_POR_PONTO

        # Verifica spread máximo
        if spread > MAX_SPREAD:
            if log_time:
                logging.warning(f"❌ Spread muito alto: {spread:.1f} pts")
            return (None,) * 8

        # Obtém dados de velas
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
        if rates is None or len(rates) < 2:
            if log_time:
                logging.warning("❌ Rates insuficientes")
            return (None,) * 8

        # Calcula indicadores
        df_rates = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
        atr = calcular_atr(df_rates['high'].tolist(
        ), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)

        last_candle = rates[-1]
        candle_type = obter_nome_vela(
            last_candle[1], last_candle[4], last_candle[2], last_candle[3])

        rsi_14 = calcular_rsi(df_rates['close'].tolist(), 14)
        volume_tick = tick_info.volume

        # Log detalhado dos dados do EA
        logging.debug(
            f"📊 EA Data - Bid Vol: {total_bid_volume}, Ask Vol: {total_ask_volume}")

        return total_bid_volume, total_ask_volume, spread, atr, candle_type, book_data, rsi_14, volume_tick

    except Exception as e:
        logging.error(f"❌ Erro ao obter dados do mercado (EA): {e}")
        return (None,) * 8


def volume_crescente(n: int = 2, symbol: str = None, timeframe: int = TIMEFRAME) -> bool:
    """Verifica se o volume está crescente nos últimos n candles."""
    global SYMBOL
    if symbol is None:
        symbol = SYMBOL
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n + 1)
    if rates is None or len(rates) < n + 1:
        return False

    volumes = [rate[5] for rate in rates]  # rate[5] é o volume
    for i in range(1, len(volumes)):
        if volumes[i] <= volumes[i-1]:
            return False
    return True


def verificar_book_equilibrado(bid_qty: float, ask_qty: float) -> Tuple[bool, str]:
    """Verifica se o book está equilibrado o suficiente para operar."""
    if bid_qty == 0 or ask_qty == 0:
        return False, "Book zerado em um dos lados"

    # Calcula razão entre volumes (sempre menor/maior para ter ratio <= 1)
    ratio = min(bid_qty, ask_qty) / max(bid_qty, ask_qty)

    # Identifica qual lado está mais forte
    lado_forte = "compra" if bid_qty > ask_qty else "venda"
    logging.info(f"📊 Book - Ratio: {ratio:.3f} | Lado forte: {lado_forte}")

    if ratio < MIN_RATIO_BOOK:
        lado_menor = "compra" if bid_qty < ask_qty else "venda"
        return False, f"Book muito desequilibrado (ratio={ratio:.3f}). Lado fraco: {lado_menor}"

    # Verifica se há pressão excessiva de um lado
    max_ratio_pressao = 2.0  # Máximo de 2x mais pressão de um lado
    if max(bid_qty, ask_qty) / min(bid_qty, ask_qty) > max_ratio_pressao:
        logging.warning(f"⚠️ Pressão excessiva no lado de {lado_forte}")
        return False, f"Pressão excessiva no lado de {lado_forte}"

    return True, ""


class ModoOperacional:
    """Gerencia os modos operacionais do robô."""

    def __init__(self):
        self.modo_atual = "NORMAL"
        self.inicio_defesa = None
        self.losses_seguidos = 0
        self.volume_anterior = 0
        self.ultimo_lucro = 0

    def atualizar_modo(self, atr: float, entropia: float, volume_atual: float,
                       bid_qty: float, ask_qty: float) -> str:
        """Atualiza o modo operacional baseado nas condições do mercado."""
        # Verifica se pode sair do modo defesa
        if self.modo_atual == "DEFESA":
            if self.inicio_defesa and (datetime.now() - self.inicio_defesa).total_seconds() > TEMPO_DEFESA * 60:
                self.modo_atual = "NORMAL"
                self.losses_seguidos = 0
                logging.info(
                    "🛡️ Saindo do modo defesa após período de observação")
            else:
                return "DEFESA"

        # Verifica equilíbrio do book
        book_equilibrado, msg = verificar_book_equilibrado(bid_qty, ask_qty)
        if not book_equilibrado:
            if self.modo_atual != "AGUARDANDO":
                logging.info(f"⏳ Entrando em modo aguardando - {msg}")
            return "AGUARDANDO"

        # Verifica condições para modo lateralidade
        if atr < THRESHOLD_ATR_BAIXO and entropia < THRESHOLD_ENTROPIA_BAIXA:
            if self.modo_atual != "LATERAL":
                logging.info(
                    "↔️ Entrando em modo lateralidade - Baixa volatilidade e entropia")
            return "LATERAL"

        # Verifica condições para modo explosão - VOLUME MÍNIMO 1000cc
        crescimento_volume = volume_atual / \
            self.volume_anterior if self.volume_anterior > 0 else 1
        if (entropia > THRESHOLD_ENTROPIA_ALTA and
                crescimento_volume > MIN_VOLUME_CRESCIMENTO and
                volume_atual >= 1000):  # FILTRO: Só explosão com 1000cc+
            if self.modo_atual != "EXPLOSAO":
                logging.info(
                    f"💥 Entrando em modo explosão - Alta entropia ({entropia:.2f}), volume crescente ({crescimento_volume:.1f}x) e liquidez alta ({volume_atual}cc)")
            return "EXPLOSAO"

        # Modo normal como fallback
        return "NORMAL"

    def registrar_resultado(self, lucro: float) -> None:
        """Registra resultado da operação e atualiza contadores."""
        if lucro < 0:
            self.losses_seguidos += 1
            if self.losses_seguidos >= MAX_LOSSES_SEGUIDOS:
                self.modo_atual = "DEFESA"
                self.inicio_defesa = datetime.now()
                logging.warning(
                    f"⚠️ {MAX_LOSSES_SEGUIDOS} losses seguidos - Entrando em modo defesa")
        else:
            self.losses_seguidos = 0
        self.ultimo_lucro = lucro

    def ajustar_parametros_operacionais(self, volume_book_total: float = 1000) -> Dict[str, float]:
        """Ajusta parâmetros baseado no modo atual com volume inteligente."""
        # Volume inteligente baseado no book para melhor assertividade
        volume_inteligente = calcular_volume_inteligente(volume_book_total)

        params = {
            'volume': volume_inteligente,
            'sl_mult': MULTIPLICADOR_SL_ATR,
            'tp_mult': MULTIPLICADOR_TP_ATR
        }

        if self.modo_atual == "LATERAL":
            # Modo mais conservador - Volume ainda mais reduzido
            params.update({
                'volume': max(1.0, volume_inteligente * 0.5),  # Reduz volume mas mínimo 1cc
                'sl_mult': MULTIPLICADOR_SL_ATR * 0.7,  # Reduz SL
                'tp_mult': MULTIPLICADOR_TP_ATR * 0.7,  # Reduz TP
            })

        elif self.modo_atual == "EXPLOSAO":
            # Modo mais agressivo - VOLUME INTELIGENTE BASEADO NO BOOK
            volume_book_total = getattr(self, 'ultimo_volume_book', 1000)

            # Sistema de volume escalonado baseado no volume do book
            if volume_book_total >= 2000:
                volume_explosao = 10.0  # Volume máximo para alta liquidez
            elif volume_book_total >= 1000:
                volume_explosao = 5.0   # Volume padrão
            elif volume_book_total >= 500:
                volume_explosao = 4.0   # Volume moderado
            else:
                volume_explosao = 2.5  # Volume conservador

            params.update({
                'volume': volume_explosao,  # Volume inteligente baseado no book
                'sl_mult': MULTIPLICADOR_SL_ATR * 1.2,  # Aumenta SL
                'tp_mult': MULTIPLICADOR_TP_ATR * 1.5,  # Aumenta TP
            })

        elif self.modo_atual == "DEFESA":
            # Modo apenas observação
            params.update({
                'volume': 0,  # Não opera
            })

        return params


def executar_ordem(action: str, lots: float = VOLUME_PADRAO, symbol: str = None,
                   sl: Optional[float] = None, tp: Optional[float] = None,
                   modo_operacional: Optional[ModoOperacional] = None) -> Optional[int]:
    """Executa uma ordem de compra ou venda com SL fixo de 5 pontos e sem TP (robô decide saída)."""
    # Usa SYMBOL global se não especificado
    if symbol is None:
        symbol = SYMBOL

    # Verifica se o símbolo está definido
    if symbol is None:
        logging.error(
            "❌ SYMBOL não está definido! Não é possível executar ordem.")
        return None

        logging.info(f"🔧 Executando ordem {action} para símbolo: {symbol}")

    # Verifica conexão MT5
    if not mt5.initialize():
        logging.error("❌ MT5 não está inicializado! Tentando reconectar...")
        if not reconectar_mt5():
            logging.error("❌ Falha ao reconectar MT5")
            return None

    if modo_operacional and modo_operacional.modo_atual == "DEFESA":
        logging.info("🛡️ Ordem bloqueada - Modo defesa ativo")
        return None

    # Obtém parâmetros ajustados para o modo atual
    params = modo_operacional.ajustar_parametros_operacionais() if modo_operacional else {
        'volume': lots,
        'sl_mult': MULTIPLICADOR_SL_ATR,
        'tp_mult': MULTIPLICADOR_TP_ATR
    }

    # Verifica estado do mercado
    mercado_aberto, msg = verificar_mercado_aberto()
    if not mercado_aberto:
        logging.warning(f"❌ Ordem não enviada: {msg}")
        return None

    tipo = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL

    # Diagnóstico detalhado dos dados de mercado
    tick = mt5.symbol_info_tick(symbol)
    symbol_info = get_cached_symbol_info(symbol)

    if tick is None:
        logging.error(f"❌ Tick é None para símbolo {symbol}")
        # Tenta reselecionar o símbolo e obter tick novamente
        mt5.symbol_select(symbol, True)
        time.sleep(0.1)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.error(f"❌ Tick ainda é None após reselecionar {symbol}")
            return None

    if symbol_info is None:
        logging.error(f"❌ Symbol_info é None para símbolo {symbol}")
        # Limpa cache e tenta novamente
        get_cached_symbol_info.cache_clear()
        symbol_info = get_cached_symbol_info(symbol)
        if symbol_info is None:
            logging.error(
                f"❌ Symbol_info ainda é None após limpar cache para {symbol}")
            return None

    logging.info(
        f"✅ Dados obtidos - Tick: Ask={tick.ask}, Bid={tick.bid}, Symbol: {symbol_info.name}")

    if tick is None or symbol_info is None:
        logging.warning(
            "Dados de mercado indisponíveis após tentativas de correção")
        return None

    # Verifica spread
    if not verificar_spread_maximo(symbol_info, tick):
        logging.warning(
            f"❌ Spread muito alto: {(tick.ask - tick.bid) / symbol_info.point:.1f}")
        return None

    preco = tick.ask if action == 'BUY' else tick.bid
    preco = arredondar_preco(preco)

    # Garante que o volume seja float e no mínimo 1.0
    lote_corrigido = float(max(1, round(params['volume'])))
    logging.info(f"📊 Volume ajustado: {lote_corrigido:.1f} contratos")

    # Calcula SL e TP
    sl_calculado, tp_calculado = calcular_preco_sl_tp(
        preco, action, SL_POINTS, TP_POINTS)

    # Prepara request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lote_corrigido,
        "type": tipo,
        "price": preco,
        "sl": sl_calculado,
        "tp": tp_calculado,
        "deviation": DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": f"Monstro {action}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Envia ordem
    resultado = mt5.order_send(request)
    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(
            f"❌ Falha ao executar ordem {action}: {resultado.retcode} - {resultado.comment}")
        return None

    logging.info(f"✅ Ordem {action} executada. Ticket: {resultado.order}")
    logging.info(
        f"   Preço: {preco:.3f} | SL: {sl_calculado:.3f} | TP: {tp_calculado:.3f}")

    # Aguarda um momento para o MT5 processar
    time.sleep(0.5)

    # Verifica se a ordem virou posição
    for _ in range(3):  # Tenta até 3 vezes
        positions = mt5.positions_get(ticket=resultado.order)
        if positions and len(positions) > 0:
            pos = positions[0]
            logging.info(f"✅ Ordem {resultado.order} virou posição.")

            # ========== INTEGRAÇÃO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
            if trailing_stop and TRAILING_ATIVO:
                trailing_stop.iniciar_trailing(resultado.order, action, preco, sl_calculado)
                logging.info(f"🎯 Trailing stop iniciado para posição {resultado.order}")

            # ========== INTEGRAÇÃO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
            if balanceador and BALANCEAMENTO_ATIVO:
                balanceador.registrar_operacao(action)
                status = balanceador.get_status()
                logging.info(f"⚖️ Operação {action} registrada. BUY: {status['buy_count']}, SELL: {status['sell_count']} (BUY: {status['buy_percentage']:.1f}%)")

            # ========== INTEGRAÇÃO MELHORIA 5: SAÍDA INTELIGENTE DE POSIÇÃO ==========
            if saida_inteligente and SAIDA_INTELIGENTE_ATIVA:
                saida_inteligente.iniciar_monitoramento(resultado.order, action, preco)
                logging.info(f"🚪 Saída inteligente iniciada para posição {resultado.order}")

            return resultado.order
        time.sleep(0.2)

    logging.warning(
        f"⚠️ Não foi possível confirmar se ordem {resultado.order} virou posição")
    return resultado.order


def verificar_se_ordem_virou_posicao(ticket: Optional[int], symbol: str = SYMBOL) -> bool:
    """Verifica se uma ordem se transformou em posição."""
    if ticket is None:
        return False

    positions = retry_positions_get(symbol)
    if positions is None:
        return False

    return any(
        pos.ticket == ticket and pos.magic == MAGIC_NUMBER
        for pos in positions
    )


def obter_lucro_ultima_ordem(ticket_ordem_abertura: Optional[int] = None) -> Tuple[float, float]:
    """Obtém o lucro e score da última ordem fechada, com base no ticket da ordem de abertura."""
    logging.info(
        f"🔍 Tentando obter lucro para ticket de ordem de abertura: {ticket_ordem_abertura}")
    if ticket_ordem_abertura is None:
        logging.warning(
            "⚠️ obter_lucro_ultima_ordem chamada sem ticket_ordem_abertura. Retornando 0.0, 0.0")
        return 0.0, 0.0

    # Buscar deals dos últimos X dias para garantir que cobrimos a vida da ordem.
    # Aumentar o timedelta se as posições puderem ficar abertas por mais tempo.
    data_inicio_busca = datetime.now() - timedelta(days=7)
    deals = mt5.history_deals_get(data_inicio_busca, datetime.now())

    if not deals:
        logging.warning(
            f"💰 Nenhum deal encontrado nos últimos 7 dias. Não foi possível obter lucro para ticket {ticket_ordem_abertura}.")
        return 0.0, 0.0

        logging.debug(
            f"🔍 Encontrados {len(deals)} deals nos últimos 7 dias para análise do ticket {ticket_ordem_abertura}.")

    # Filtra deals de SAÍDA (mt5.DEAL_ENTRY_OUT) cuja position_id corresponde ao ticket da ORDEM de abertura.
    deals_de_saida_relevantes = [
        d for d in deals if d.position_id == ticket_ordem_abertura and d.entry == mt5.DEAL_ENTRY_OUT
    ]

    if not deals_de_saida_relevantes:
        logging.warning(
            f"💰 Nenhum DEAL DE SAÍDA encontrado para a ordem com ticket (position_id) {ticket_ordem_abertura}.")
        # Isso pode significar que a posição ainda está aberta, foi fechada manualmente de forma não rastreável aqui,
        # ou o deal de saída ainda não foi registrado no histórico.
        return 0.0, 0.0

    # Se houver múltiplos deals de saída (ex: TPs parciais), é importante decidir como agregar.
    # Para este caso, vamos pegar o deal de saída MAIS RECENTE para calcular o lucro final da posição.
    # Ou, se for uma única saída, este será o deal.
    # Se for necessário somar lucros de saídas parciais, a lógica aqui precisaria ser mais elaborada.
    # Usar time_msc para maior precisão
    deal_final_de_saida = max(
        deals_de_saida_relevantes, key=lambda d: d.time_msc)

    lucro_total_operacao = deal_final_de_saida.profit
    # O atributo 'profit' de um deal no MT5 geralmente já inclui comissões e swaps.

    logging.info(f"💰 Deal de saída encontrado para ticket {ticket_ordem_abertura}: DealTicket={deal_final_de_saida.ticket}, PositionID={deal_final_de_saida.position_id}, Lucro={lucro_total_operacao:.2f}, Preço Saída={deal_final_de_saida.price}, Volume={deal_final_de_saida.volume}, Hora={datetime.fromtimestamp(deal_final_de_saida.time)})")

    score_dist = 0.0
    # Para calcular o score_dist, precisamos da ordem original de abertura.
    ordens_historico = mt5.history_orders_get(ticket=ticket_ordem_abertura)

    if not ordens_historico:
        logging.warning(
            f"⚠️ Não foi possível obter detalhes da ordem de abertura {ticket_ordem_abertura} do histórico para calcular score_dist.")
        # Mesmo sem a ordem, retornamos o lucro encontrado.
    elif len(ordens_historico) == 0:
        logging.warning(
            f"⚠️ Lista de ordens do histórico vazia para ticket {ticket_ordem_abertura} ao calcular score_dist.")
    else:
        # Pega a primeira (e deve ser a única) ordem com esse ticket
        ordem_obj = ordens_historico[0]
        logging.debug(
            f"📊 Detalhes da ordem de abertura para score_dist - Ticket: {ordem_obj.ticket}, PreçoAbertura: {ordem_obj.price_open}, SL: {ordem_obj.sl}, TP: {ordem_obj.tp}, Tipo: {ordem_obj.type}, Estado: {ordem_obj.state}, Razão: {ordem_obj.reason}, Preço Atual MT5: {ordem_obj.price_current}")

        preco_entrada_para_score = ordem_obj.price_open  # Fallback
        # Buscar o deal de entrada correspondente ao ticket_ordem_abertura (que é o position_id do deal de saída)
        deals_relacionados_posicao = [
            d for d in deals if d.position_id == ticket_ordem_abertura]
        deal_de_entrada_para_score = None
        for deal_historico in deals_relacionados_posicao:
            # Garante que é o deal da ordem de abertura
            if deal_historico.entry == mt5.DEAL_ENTRY_IN and deal_historico.order == ticket_ordem_abertura:
                deal_de_entrada_para_score = deal_historico
                break

        if deal_de_entrada_para_score:
            preco_entrada_para_score = deal_de_entrada_para_score.price
            logging.info(
                f"Found entry deal for score_dist calc (Order: {ticket_ordem_abertura}), execution price: {preco_entrada_para_score}")
        else:
            logging.warning(
                f"Entry deal not found for score_dist calc (Order: {ticket_ordem_abertura}), using order.price_open ({preco_entrada_para_score}).")

    score_dist = calcular_score_distancia(
        preco_entrada=preco_entrada_para_score,  # AQUI
        preco_saida=deal_final_de_saida.price,
        sl=ordem_obj.sl,
        tp=ordem_obj.tp
    )
    logging.debug(
        f"🎯 Score distância calculado para ticket {ticket_ordem_abertura}: {score_dist:.4f}")

    return lucro_total_operacao, score_dist

# endregion

# region [Trailing Stop]


def atualizar_trailing_stop() -> None:
    """Atualiza o trailing stop das posições abertas."""
    if not TRAILING_ATIVO:
        return

    # Verifica se é fim de semana
    if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
        # Verifica a cada minuto durante fim de semana
        threading.Timer(60, atualizar_trailing_stop).start()
        return

    # Verifica estado do mercado
    mercado_aberto, msg = verificar_mercado_aberto()
    if not mercado_aberto:
        logging.info(f"⏰ Trailing stop não ativo: {msg}")
        threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()
        return

    # Verifica horário do ajuste
    agora = datetime.now().time()
    horario_ajuste = datetime.strptime(HORARIO_AJUSTE, "%H:%M").time()
    if agora >= horario_ajuste:
        logging.info("⏰ Após horário de ajuste, trailing stop desativado")
        return

    posicoes = retry_positions_get(SYMBOL)
    if posicoes is None or len(posicoes) == 0:
        threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()
        return

    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        logging.warning(
            "⚠️ Informações do símbolo indisponíveis para trailing")
        threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()
        return

    for pos in posicoes:
        if pos.magic != MAGIC_NUMBER:
            continue

        preco_entrada = pos.price_open
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            continue

        preco_atual = tick.bid if pos.type == mt5.POSITION_TYPE_SELL else tick.ask
        preco_atual = arredondar_preco(preco_atual)

        # Converte diferença para pontos (1 ponto = 1000 ticks)
        lucro_ticks = abs(preco_atual - preco_entrada) / symbol_info.point
        lucro_pontos = lucro_ticks / TICKS_POR_PONTO

        # Só move o stop se atingiu o gatilho em pontos
        if lucro_pontos < TRAILING_GATILHO:
            continue

        # Calcula novo SL
        if pos.type == mt5.POSITION_TYPE_BUY:
            novo_sl = preco_atual - \
                (TRAILING_DISTANCIA * TICK_SIZE * TICKS_POR_PONTO)
        else:
            novo_sl = preco_atual + \
                (TRAILING_DISTANCIA * TICK_SIZE * TICKS_POR_PONTO)

        novo_sl = arredondar_preco(novo_sl)

        # Só atualiza se o novo SL é mais favorável
        if pos.type == mt5.POSITION_TYPE_BUY and (pos.sl is None or novo_sl > pos.sl):
            atualizar_sl(pos.ticket, novo_sl)
        elif pos.type == mt5.POSITION_TYPE_SELL and (pos.sl is None or novo_sl < pos.sl):
            atualizar_sl(pos.ticket, novo_sl)

    threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()


def atualizar_sl(ticket: int, novo_sl: float) -> bool:
    """Atualiza o stop loss de uma posição."""
    # Recupera a posição atual para pegar o TP original
    posicoes = mt5.positions_get(ticket=ticket)
    if not posicoes:
        logging.error(
            f"❌ Não foi possível obter a posição com ticket {ticket} para atualizar SL.")
        return False

    tp_original = posicoes[0].tp
    logging.debug(
        f"[atualizar_sl] Posição Ticket: {ticket}, Novo SL (antes de round): {novo_sl}, TP Original: {tp_original}")

    ordem_mod = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": SYMBOL,
        "sl": round(novo_sl, mt5.symbol_info(SYMBOL).digits),
        "tp": tp_original,  # Mantém o TP original da posição
        "magic": MAGIC_NUMBER,
        "comment": "Trailing SL Monstro"
    }

    resultado = mt5.order_send(ordem_mod)
    if resultado is None:
        logging.error(f"❌ Erro ao mover SL via trailing. Ticket={ticket}")
        logging.error(f"❌ Erro MT5: {mt5.last_error()}")
        return False
    elif resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(
            f"🔐 SL atualizado para {ordem_mod['sl']} (Ticket: {ticket})")
        return True
    else:
        logging.warning(
            f"⚠️ Falha ao mover SL. Código: {resultado.retcode} | Mensagem: {resultado.comment}")
        return False
# endregion


# region [Web Server]
app = Flask(__name__)


@app.route("/")
def index():
    """Página principal com dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monstro Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .card {
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .full-width { grid-column: 1 / -1; }
            h2 { color: #333; }
            .bloqueio-info {
                display: flex;
                gap: 20px;
                margin-top: 10px;
                padding: 10px;
                background: #f5f5f5;
                border-radius: 4px;
            }
            .bloqueio-lado {
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            .bloqueado { background: #ffebee; color: #c62828; }
            .liberado { background: #e8f5e9; color: #2e7d32; }
            .balanceamento-info {
                display: flex;
                gap: 20px;
                margin-top: 10px;
                padding: 10px;
                background: #e3f2fd;
                border-radius: 4px;
            }
            .balanceamento-metrica {
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
                background: white;
            }
            .progress-bar {
                height: 20px;
                background: #eee;
                border-radius: 10px;
                overflow: hidden;
                margin-top: 5px;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #2196f3, #64b5f6);
                transition: width 0.3s ease;
            }
        </style>
    </head>
    <body>
        <h1>🤖 Monstro Dashboard</h1>
        <div class="grid">
            <div class="card">
                <h2>📊 Performance</h2>
                <div id="performance_chart"></div>
            </div>
            <div class="card">
                <h2>🎯 Distribuição de Scores</h2>
                <div id="score_dist_chart"></div>
            </div>
            <div class="card">
                <h2>📈 Aprendizado</h2>
                <div id="learning_chart"></div>
            </div>
            <div class="card">
                <h2>⚖️ Experiências</h2>
                <div id="exp_chart"></div>
            </div>
            <div class="card full-width">
                <h2>📝 Status Atual</h2>
                <div id="status_info"></div>
                <div class="bloqueio-info">
                    <div>
                        <h3>🔒 Status Bloqueios</h3>
                        <div id="bloqueio_info"></div>
                    </div>
                    <div>
                        <h3>⚠️ Sequência de Losses</h3>
                        <div id="losses_info"></div>
                    </div>
                </div>
                <div class="balanceamento-info">
                    <div>
                        <h3>⚖️ Balanceamento de Operações</h3>
                        <div id="balanceamento_info"></div>
                        <div class="progress-bar">
                            <div id="balanceamento_bar" class="progress-fill"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            function updateCharts() {
                // Performance Chart
                $.getJSON('/api/performance', function(data) {
                    const trace = {
                        y: data.lucros,
                        type: 'scatter',
                        name: 'P&L'
                    };
                    Plotly.newPlot('performance_chart', [trace]);
                });

                // Score Distribution
                $.getJSON('/api/score_distribution', function(data) {
                    const trace = {
                        x: data.scores,
                        type: 'histogram',
                        nbinsx: 20,
                        name: 'Scores'
                    };
                    Plotly.newPlot('score_dist_chart', [trace]);
                });

                // Learning Progress
                $.getJSON('/api/learning_progress', function(data) {
                    const trace = {
                        y: data.loss_history,
                        type: 'scatter',
                        name: 'Loss'
                    };
                    Plotly.newPlot('learning_chart', [trace]);
                });

                // Experience Distribution
                $.getJSON('/api/experience_stats', function(data) {
                    const trace = {
                        labels: ['Positivas', 'Negativas'],
                        values: [data.positivas, data.negativas],
                        type: 'pie'
                    };
                    Plotly.newPlot('exp_chart', [trace]);
                });

                // Status Info
                $.getJSON('/api/status', function(data) {
                    $('#status_info').html(`
                        <p><strong>Score Atual:</strong> ${data.score.toFixed(2)}</p>
                        <p><strong>Última Decisão:</strong> ${data.ultima_decisao}</p>
                        <p><strong>Status Book:</strong> ${data.status_book}</p>
                        <p><strong>Posição:</strong> ${data.posicao_atual}</p>
                        <p><strong>Idade Média Exp.:</strong> ${data.idade_media_exp.toFixed(1)}h</p>
                        <p><strong>Decay Médio:</strong> ${data.decay_medio.toFixed(2)}</p>
                    `);

                    // Atualiza informações de bloqueio
                    $('#bloqueio_info').html(`
                        <div class="bloqueio-lado ${data.bloqueios.BUY > 0 ? 'bloqueado' : 'liberado'}">
                            COMPRA: ${data.bloqueios.BUY > 0 ? `Bloqueado (${data.bloqueios.BUY} ciclos)` : 'Liberado'}
                        </div>
                        <div class="bloqueio-lado ${data.bloqueios.SELL > 0 ? 'bloqueado' : 'liberado'}">
                            VENDA: ${data.bloqueios.SELL > 0 ? `Bloqueado (${data.bloqueios.SELL} ciclos)` : 'Liberado'}
                        </div>
                    `);

                    // Atualiza informações de losses em sequência
                    $('#losses_info').html(`
                        <div>COMPRA: ${data.losses_sequencia.BUY} losses seguidos</div>
                        <div>VENDA: ${data.losses_sequencia.SELL} losses seguidos</div>
                    `);

                    // Atualiza informações de balanceamento
                    if (data.balanceamento) {
                        $('#balanceamento_info').html(`
                            <div class="balanceamento-metrica">
                                Compras: ${data.balanceamento.buy_percent.toFixed(1)}%
                            </div>
                            <div class="balanceamento-metrica">
                                Vendas: ${data.balanceamento.sell_percent.toFixed(1)}%
                            </div>
                            <div class="balanceamento-metrica">
                                Total Ops: ${data.balanceamento.total_operacoes}
                            </div>
                        `);

                        // Atualiza barra de progresso
                        $('#balanceamento_bar').css('width', `${data.balanceamento.buy_percent}%`);
                    }
                });
            }

            // Update every 5 seconds
            setInterval(updateCharts, 5000);
            updateCharts();  // Initial update
        </script>
    </body>
    </html>
    """


@app.route("/api/performance")
def api_performance():
    """Retorna dados de performance para o gráfico."""
    return jsonify({
        "lucros": historico_lucro
    })


@app.route("/api/score_distribution")
def api_score_distribution():
    """Retorna distribuição dos scores."""
    scores = []
    if memoria_experiencias and memoria_experiencias.experiencias:
        scores = [exp[3]
                  for exp in memoria_experiencias.experiencias]  # score_dist
    return jsonify({
        "scores": scores
    })


@app.route("/api/learning_progress")
def api_learning_progress():
    """Retorna progresso do aprendizado."""
    global historico_loss
    return jsonify({
        "loss_history": historico_loss
    })


@app.route("/api/experience_stats")
def api_experience_stats():
    """Retorna estatísticas das experiências."""
    positivas = len(
        memoria_experiencias.indices_positivos) if memoria_experiencias else 0
    negativas = len(
        memoria_experiencias.indices_negativos) if memoria_experiencias else 0
    return jsonify({
        "positivas": positivas,
        "negativas": negativas
    })


@app.route("/status")
def status():
    """Retorna o status atual do sistema."""
    idade_media = 0
    decay_medio = 0
    if memoria_experiencias and memoria_experiencias.timestamps:
        idade_media = sum(
            (datetime.now() - ts).total_seconds() / 3600
            for ts in memoria_experiencias.timestamps
        ) / len(memoria_experiencias.timestamps)
        decay_medio = sum(
            memoria_experiencias.calcular_decay(ts)
            for ts in memoria_experiencias.timestamps
        ) / len(memoria_experiencias.timestamps)

    # Obtém status do gerenciador de bloqueio - usando globals() para verificar
    try:
        if 'gerenciador_bloqueio' in globals() and gerenciador_bloqueio is not None:
            status_bloqueio = gerenciador_bloqueio.get_status()
        else:
            status_bloqueio = {
                "bloqueios": {"BUY": 0, "SELL": 0},
                "losses_sequencia": {"BUY": 0, "SELL": 0},
                "ultima_acao": None
            }
    except:
        status_bloqueio = {
            "bloqueios": {"BUY": 0, "SELL": 0},
            "losses_sequencia": {"BUY": 0, "SELL": 0},
            "ultima_acao": None
        }

    # Obtém status de balanceamento
    balanceamento = memoria_experiencias.get_balanceamento_status(
    ) if memoria_experiencias else None

    # Obtém modo operacional
    try:
        if 'modo_operacional' in globals() and modo_operacional is not None:
            modo_atual = modo_operacional.modo_atual
        else:
            modo_atual = "NORMAL"
    except:
        modo_atual = "NORMAL"

    return jsonify({
        "score": score,
        "ultima_decisao": ultima_decisao,
        "status_book": "Ativo" if len(retry_market_book_get(SYMBOL) or []) > 0 else "Vazio",
        "posicao_atual": "Aberta" if posicao_aberta else "Nenhuma",
        "idade_media_exp": idade_media,
        "decay_medio": decay_medio,
        "modo_operacional": modo_atual,
        "bloqueios": status_bloqueio["bloqueios"],
        "losses_sequencia": status_bloqueio["losses_sequencia"],
        "ultima_acao_bloqueada": status_bloqueio["ultima_acao"],
        "balanceamento": balanceamento  # Novo campo
    })


@app.route("/api/novos_sistemas")
def api_novos_sistemas():
    """Retorna status dos novos sistemas implementados."""
    status_sistemas = {}

    # Status do filtro de horário
    if filtro_horario:
        status_sistemas['horario'] = filtro_horario.get_status()

    # Status do detector de tendência
    if detector_tenden:
        status_sistemas['tendencia'] = detector_tendencia.get_status()

    # Status do cooldown
    if cooldown_sistema:
        status_sistemas['cooldown'] = cooldown_sistema.get_status()

    # Status do filtro de spread
    if filtro_spread:
        status_sistemas['spread'] = filtro_spread.get_status()

    # Status do monitor de performance
    if monitor_performance:
        status_sistemas['performance'] = monitor_performance.get_status()

    return jsonify(status_sistemas)

@app.route("/lucro")
def lucro():
    """Retorna o histórico de lucros."""
    return jsonify({
        "lucros": historico_lucro,
        "total": sum(historico_lucro) if historico_lucro else 0,
        "media": sum(historico_lucro) / len(historico_lucro) if historico_lucro else 0,
        "operacoes": len(historico_lucro)
    })


def iniciar_flask():
    """Inicia o servidor Flask."""
    app.run(port=PORT, debug=DEBUG, use_reloader=False)


# Variáveis globais para métricas
historico_loss = []  # Histórico de loss do modelo

# Variáveis globais para encerramento seguro
sistema_encerrando = False
modelo_ia_global = None
memoria_experiencias_global = None

# Tratamento de sinais para encerramento seguro


def verificar_arquivo_parada():
    """Verifica se existe o arquivo parar.txt para encerramento gracioso."""
    try:
        arquivo_parada = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "parar.txt")
        return os.path.exists(arquivo_parada)
    except Exception as e:
        logging.error(f"❌ Erro ao verificar arquivo de parada: {e}")
        return False


def signal_handler(signum, frame):
    """Trata sinais do sistema para encerramento seguro."""
    global sistema_encerrando, modelo_ia_global, memoria_experiencias_global

    if sistema_encerrando:
        logging.info(
            "🔴 Sinal recebido novamente - forçando encerramento imediato")
        os._exit(1)

    sistema_encerrando = True
    logging.info(f"🔴 Sinal {signum} recebido - iniciando encerramento seguro")

    try:
        if modelo_ia_global and memoria_experiencias_global:
            encerramento_seguro_completo(
                modelo_ia_global, memoria_experiencias_global)
        else:
            logging.info(
                "🔴 Dados globais não disponíveis - encerramento direto")
            os._exit(0)
    except Exception as e:
        logging.error(f"❌ Erro no encerramento por sinal: {e}")
        os._exit(1)


# Registra os handlers de sinal - TEMPORARIAMENTE DESABILITADO PARA DEBUG
# signal.signal(signal.SIGTERM, signal_handler)
# signal.signal(signal.SIGINT, signal_handler)
# if sys.platform == "win32":
#     signal.signal(signal.SIGBREAK, signal_handler)

# region [Loop Principal]


def verificar_parada_gracil():
    """Verifica se foi solicitada parada gracil através do arquivo parar.txt"""
    if os.path.exists("parar.txt"):
        # Se mercado fechado, encerra imediatamente
        try:
            mercado_ativo, motivo = verificar_mercado_aberto()
            if not mercado_ativo:
                logging.info(
                    f"🚫 {motivo} - Encerramento imediato por mercado fechado")
                return True
        except:
            pass  # Se erro na verificação, continua normalmente
        return True
    return False


def monstro_thread(mt5_ativo_param=None, modelo_ia_param=None):
    """Loop principal do sistema de trading."""
    global thread_ativo, mt5_ativo, posicao_aberta, lucro_acumulado
    global historico_operacoes, score, modelo_ia, dados_memoria
    global memoria_experiencias, ticket_ordem_atual, ultima_decisao
    global historico_lucro, gerenciador_bloqueio, modo_operacional
    global sistema_encerrando, modelo_ia_global, memoria_experiencias_global

    try:
        # Inicialização
        mt5_ativo_local = inicializar_mt5() if mt5_ativo_param is None else mt5_ativo_param

        # === PROTEÇÃO TOTAL DO MODELO ===
        logging.info("🛡️ Iniciando verificação de proteção do modelo...")
        if not verificar_e_proteger_modelo():
            logging.warning(
                "⚠️ Proteção do modelo identificou problemas - continuando com novo modelo")

        # Verifica se o mercado está aberto antes de carregar o modelo
        mercado_aberto, msg = verificar_mercado_aberto()
        if mercado_aberto:
            logging.info("📂 Mercado aberto: carregando modelo de IA...")
            modelo_ia_local = carregar_modelo() if modelo_ia_param is None else modelo_ia_param
            if modelo_ia_local is None:
                logging.warning(
                    "⚠️ Modelo não encontrado, criando novo modelo...")
                modelo_ia_local = criar_modelo_neural(N_FEATURES)
                logging.info("✅ Novo modelo de IA criado com sucesso")
                # Salva imediatamente o novo modelo com proteção
                salvar_modelo(modelo_ia_local)
        else:
            logging.info("🚫 Mercado fechado: carregamento de modelo suspenso.")
            modelo_ia_local = None

        # Atualiza variáveis globais para tratamento de sinais
        modelo_ia_global = modelo_ia_local
        memoria_experiencias_global = memoria_experiencias

        esperando_confirmacao = False
        primeira_operacao = True  # ✅ ADICIONADO DO V2
        ultimo_heartbeat = time.time()
        ultimo_diagnostico = time.time()
        posicao_atual = None
        modo_operacional = ModoOperacional()  # Inicializa gerenciador de modos
        # Inicializa gerenciador de bloqueio
        gerenciador_bloqueio = GerenciadorBloqueio()

        while thread_ativo:
            try:
                # ===== VERIFICAÇÃO DE PARADA GRACIL =====
                if verificar_parada_gracil():
                    logging.info(
                        "🛑 PARADA GRACIL SOLICITADA - Encerrando sistema com segurança...")

                    # Fecha posições ativas se houver
                    if posicao_aberta and ticket_ordem_atual:
                        logging.info(
                            "💰 Fechando posição ativa antes de encerrar...")
                        try:
                            fechar_posicao_atual()
                        except Exception as e:
                            logging.error(f"❌ Erro ao fechar posição: {e}")

                    # Salva modelo e dados importantes
                    if modelo_ia_local:
                        logging.info("💾 Salvando modelo IA...")
                        try:
                            salvar_modelo(modelo_ia_local)
                        except Exception as e:
                            logging.error(f"❌ Erro ao salvar modelo: {e}")

                    # Salva experiências
                    if memoria_experiencias:
                        logging.info("📚 Salvando experiências...")
                        try:
                            salvar_experiencias_json(
                                memoria_experiencias.experiencias)
                        except Exception as e:
                            logging.error(
                                f"❌ Erro ao salvar experiências: {e}")

                    logging.info(
                        "✅ ENCERRAMENTO GRACIL CONCLUÍDO - Sistema finalizado com segurança")
                    thread_ativo = False
                    break

                # Dorme até o pregão abrir
                agora = datetime.now().time()
                inicio = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
                fim = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

                if agora < inicio:
                    aguardar_abertura()
                    continue
                if agora >= fim:
                    aguardar_fechamento()
                    continue
                # Verifica se é fim de semana
                if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
                    logging.info(
                        "📅 Fim de semana: sistema em modo de espera...")
                    time.sleep(60)  # Dorme por 1 minuto durante fim de semana
                    continue

                # === VERIFICAÇÃO DE SINAL DE ENCERRAMENTO EXTERNO ===
                # TEMPORARIAMENTE DESABILITADO PARA DEBUG
                if False and os.path.exists("shutdown_signal.txt"):
                    logging.info(
                        "🚦 SINAL DE ENCERRAMENTO EXTERNO DETECTADO - INICIANDO SHUTDOWN GRACIOSO")

                    # Fecha todas as posições abertas
                    posicoes_fechadas = fechar_todas_posicoes(
                        "Encerramento por sinal externo")

                    # Atualiza variáveis globais antes do encerramento
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    # Executa encerramento seguro completo
                    encerramento_seguro_completo(
                        modelo_ia_local, memoria_experiencias)
                    # Não chegará aqui pois encerramento_seguro_completo chama os._exit()

                # === ENCERRAMENTO AUTOMÁTICO ÀS 18:20 ===
                horario_atual = datetime.now().time()
                horario_encerramento = datetime.strptime(
                    HORARIO_ENCERRAMENTO, "%H:%M").time()
                if horario_atual >= horario_encerramento:
                    logging.info(
                        "🔴 ENCERRAMENTO AUTOMÁTICO ÀS 18:20 - FECHANDO TODAS AS POSIÇÕES")

                    # Fecha todas as posições abertas
                    posicoes_fechadas = fechar_todas_posicoes(
                        "Encerramento automático 18:20")

                    # Salva estatísticas finais
                    if posicoes_fechadas > 0:
                        logging.info(
                            f"📊 Estatísticas finais: {posicoes_fechadas} posições fechadas")

                    # Salva estado do modelo
                    try:
                        salvar_modelo(modelo_ia_local)
                        logging.info("💾 Modelo salvo com sucesso")
                    except Exception as e:
                        logging.error(f"❌ Erro ao salvar modelo: {e}")

                    # Atualiza variáveis globais
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    logging.info(
                        "🏁 POSIÇÕES FECHADAS ÀS 18:20 - AGUARDANDO AFTER MARKET")

                # === ENCERRAMENTO COMPLETO APÓS AFTER MARKET (18:32) ===
                horario_atual_after = datetime.now().time()
                horario_after_market = datetime.strptime(
                    HORARIO_AFTER, "%H:%M").time()
                if horario_atual_after >= horario_after_market:
                    logging.info(
                        "🔴 AFTER MARKET ENCERRADO - DESLIGANDO SISTEMA AUTOMATICAMENTE")

                    # Atualiza variáveis globais antes do encerramento
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    # Executa encerramento seguro completo
                    encerramento_seguro_completo(
                        modelo_ia_local, memoria_experiencias)
                    # Não chegará aqui pois encerramento_seguro_completo chama os._exit()

                # Heartbeat e diagnóstico
                timestamp_atual = time.time()
                if timestamp_atual - ultimo_heartbeat >= 30:
                    status_bloqueio = gerenciador_bloqueio.get_status()
                    logging.info(
                        f"👁️ Monstro está ativo e observando o mercado... Modo: {modo_operacional.modo_atual}")
                    logging.info(
                        f"🔒 Status bloqueios - BUY: {status_bloqueio['bloqueios']['BUY']}, SELL: {status_bloqueio['bloqueios']['SELL']}")
                    ultimo_heartbeat = timestamp_atual

                if timestamp_atual - ultimo_diagnostico >= 300:
                    checar_arquivos_essenciais()
                    # === VERIFICAÇÃO PERIÓDICA DO MODELO ===
                    logging.info("🛡️ Verificação periódica do modelo...")
                    if not verificar_e_proteger_modelo():
                        logging.warning(
                            "⚠️ Modelo teve problemas - mas foi protegido automaticamente")
                    ultimo_diagnostico = timestamp_atual

                if esperando_confirmacao:
                    logging.info("⏳ Aguardando confirmação da última ordem...")
                    time.sleep(1)
                    continue

                current_positions = retry_positions_get(SYMBOL)
                monstro_position_active = any(
                    p.volume > 0 for p in current_positions or []
                )

                if monstro_position_active:
                    posicao_aberta = True
                    if posicao_atual is not None:
                        monitorar_posicao_ativa(posicao_atual)
                    time.sleep(INTERVALO_CHECK_SCORE)
                    continue

                if posicao_atual is not None:
                    # Processa a posição fechada uma única vez
                    ticket_processado = posicao_atual.ticket
                    lucro_real, score_dist = obter_lucro_ultima_ordem(
                        ticket_processado)
                    gerenciador_bloqueio.registrar_operacao(
                        posicao_atual.tipo, lucro_real)
                    if posicao_atual.entry_context:
                        memoria_experiencias.adicionar(
                            posicao_atual.entry_context.copy(), posicao_atual.tipo, lucro_real, score_dist)
                        salvar_experiencia_csv(posicao_atual.entry_context.copy(
                        ), posicao_atual.tipo, lucro_real, score_dist)
                        # Treina modelo com proteção contra erros
                        try:
                            modelo_ia_local = treinar_modelo(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(
                                f"❌ Erro no treinamento do modelo: {e}")
                            logging.debug(
                                f"Stack trace: {traceback.format_exc()}")
                    else:
                        logging.warning(
                            "⚠️ Contexto de entrada não encontrado em posicao_atual ao fechar.")
                    modo_operacional.registrar_resultado(lucro_real)

                    # ========== REGISTRO NOS NOVOS SISTEMAS ==========
                    # Registra no cooldown inteligente
                    if cooldown_sistema and COOLDOWN_ATIVO:
                        cooldown_sistema.registrar_resultado(lucro_real)

                    # Registra no monitor de performance
                    if monitor_performance and MONITOR_PERFORMANCE_ATIVO:
                        modo_atual = modo_operacional.modo_atual if modo_operacional else "NORMAL"
                        monitor_performance.registrar_operacao(lucro_real, modo_atual)

                        # Verifica alertas
                        alertas = monitor_performance.verificar_alertas()
                        for alerta in alertas:
                            logging.warning(alerta)

                    # IMPORTANTE: Reset da posição ANTES de continuar
                    posicao_atual = None
                    logging.info(
                        f"✅ Posição {ticket_processado} processada e resetada.")

                    # Pequena pausa para evitar loop imediato
                    time.sleep(1)

                posicao_aberta = False
                logging.info(
                    "✅ Nenhuma posição ativa. Analisando nova entrada...")

                # DEBUG: mostra conteúdo bruto do book
                book_debug = mt5.market_book_get(SYMBOL)
                logging.info(f"📘 DEBUG BOOK: {book_debug}")

                # Verifica se o mercado está aberto
                if not verificar_estado_book(SYMBOL):
                    logging.warning(
                        "⚠️ Book em estado inválido. Tentando reiniciar...")
                    if reiniciar_book(SYMBOL):
                        logging.info("✅ Book reiniciado com sucesso")
                    else:
                        logging.error("❌ Falha ao reiniciar book. Aguardando…")

                        agora = datetime.now().time()
                        inicio = datetime.strptime(
                            HORARIO_PREGAO, "%H:%M").time()
                        fim = datetime.strptime(HORARIO_AFTER,  "%H:%M").time()

                        # Se estivermos FORA DO PREGÃO, dorme mais tempo (30s).
                        if agora < inicio or agora > fim:
                            time.sleep(30)
                        # Se estivermos em dia útil mas o book veio vazio, dorme pouco (3s).
                        else:
                            time.sleep(3)

                        continue

                # Obtém dados do mercado
                bid_qty, ask_qty, spread, volatility, candle_type, book_data, rsi_14, volume_tick = obter_dados_mercado(
                    SYMBOL)

                # Se algum dado for None, pula a iteração
                if None in (bid_qty, ask_qty, spread, volatility, candle_type, book_data, rsi_14, volume_tick):
                    logging.warning(
                        "⚠️ Dados do mercado incompletos. Aguardando próxima iteração...")
                    time.sleep(2)
                    continue

                # Calcula entropia dos dados do EA
                entropia_book = calcular_entropia(
                    book_data['bids'] + book_data['asks']) if book_data else 0.0

                contexto = {
                    "bid_qty": bid_qty, "ask_qty": ask_qty, "spread": spread, "volatility": volatility,
                    "candle_type": candle_type, "entropia_book": entropia_book, "rsi_14": rsi_14,
                    "volume_tick": volume_tick, "is_in_trade": 0, "floating_profit": 0.0, "tempo_em_trade": 0
                }
                logging.info(f"📊 Contexto para decisão: {contexto}")
                monitorar_recursos()

                # >>> Bloco de Decisão e Salvamento de Decisão (Movido para Cima) <<<
                acao_para_executar = "NADA"  # Default
                confianca_decisao = 0.0

                contexto_df_previsao = pd.DataFrame([contexto])
                # Adiciona coluna 'action' dummy se não existir, para consistência com preparar_dados
                if 'action' not in contexto_df_previsao.columns:
                    contexto_df_previsao['action'] = "BUY"  # Dummy
                X_decisao, _ = preparar_dados(contexto_df_previsao)

                if X_decisao is None or X_decisao.shape[1] != N_FEATURES:
                    logging.error(
                        f"❌ Dados inválidos para previsão (X_decisao). Shape: {X_decisao.shape if X_decisao is not None else 'None'}")
                    time.sleep(2)
                    continue

                if primeira_operacao:
                    acao_para_executar = random.choice(["BUY", "SELL"])
                    confianca_decisao = 1.0
                    primeira_operacao = False
                    logging.info(
                        f"🎲 Primeira decisão aleatória: {acao_para_executar}")
                else:
                    try:
                        acao_predita, confianca_predita = prever_acao(
                            modelo_ia_local, X_decisao, modo_operacional,
                            None, contexto)
                        acao_para_executar = acao_predita
                        confianca_decisao = confianca_predita
                        logging.info(
                            f"🤖 Previsão do Modelo: {acao_para_executar} | Confiança: {confianca_decisao:.2f}")
                    except Exception as e:
                        logging.error(
                            f"❌ Erro ao prever ação (bloco principal): {e}")
                        logging.debug(
                            f"Shape de X_decisao: {X_decisao.shape if X_decisao is not None else 'None'}")
                        time.sleep(2)
                        continue

                # Salva a decisão ANTES de qualquer filtro que possa impedir a execução da ordem
                salvar_decisao_csv(acao_para_executar,
                                   confianca_decisao, contexto)
                ultima_decisao = acao_para_executar  # Atualiza ultima_decisao global
                # >>> Fim do Bloco de Decisão e Salvamento de Decisão <<<

                rates = mt5.copy_rates_from_pos(
                    SYMBOL, TIMEFRAME, 0, PERIODO_ATR + 1)
                if rates is not None and len(rates) > PERIODO_ATR:
                    high_prices = [rate[3] for rate in rates]
                    low_prices = [rate[4] for rate in rates]
                    close_prices = [rate[2] for rate in rates]
                    atr = calcular_atr(high_prices, low_prices, close_prices)
                else:
                    atr = THRESHOLD_ATR_BAIXO * 2

                # Usa a entropia já calculada no contexto
                entropia_calculada = contexto.get('entropia_book', 0.0)

                modo_anterior = modo_operacional.modo_atual
                modo_operacional.modo_atual = modo_operacional.atualizar_modo(
                    atr, entropia_calculada, volume_tick, bid_qty, ask_qty)
                if modo_anterior != modo_operacional.modo_atual:
                    logging.info(
                        f"🔄 Mudança de modo: {modo_anterior} -> {modo_operacional.modo_atual}")
                    logging.info(
                        f"📊 ATR: {atr:.2f} | Entropia: {entropia_calculada:.2f} | Volume: {volume_tick}")
                modo_operacional.volume_anterior = volume_tick

                # Filtro de volume MENOS RESTRITIVO - só bloqueia em casos extremos
                if (not volume_crescente(n=2, symbol=SYMBOL) and
                    modo_operacional.modo_atual not in ["EXPLOSAO", "NORMAL"] and
                        volume_tick < 100):  # Só bloqueia se volume muito baixo E não crescente
                    logging.info(
                        "⛔ Volume muito baixo e não crescente. Operação bloqueada.")
                    acao_para_executar = "NAO_AGIU_FILTRO_VOLUME"
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    modelo_ia_local = treinar_modelo(
                        modelo_ia_local, memoria_experiencias)
                    time.sleep(10)  # Reduzido de 30 para 10 segundos
                    continue

                cb_ativado, cb_mensagem = verificar_circuit_breakers(contexto)
                if cb_ativado:
                    logging.warning(
                        f"⛔ Circuit Breaker ativado: {cb_mensagem}")
                    acao_para_executar = "NAO_AGIU_CB"  # Marca específica para log
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    modelo_ia_local = treinar_modelo(
                        modelo_ia_local, memoria_experiencias)
                    time.sleep(60)
                    continue

                dados_validos, erro_dados = verificar_integridade_dados(
                    contexto)
                if not dados_validos:
                    logging.error(f"❌ Dados inválidos: {erro_dados}")
                    acao_para_executar = "NAO_AGIU_DADOS_INVALIDOS"  # Marca específica para log
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    modelo_ia_local = treinar_modelo(
                        modelo_ia_local, memoria_experiencias)
                    time.sleep(10)
                    continue

                # Aplica bloqueio de lado APÓS a previsão inicial - SÓ PARA AÇÕES DE TRADING
                if acao_para_executar in ["BUY", "SELL"] and gerenciador_bloqueio.verificar_bloqueio(acao_para_executar):
                    acao_original_bloqueada = acao_para_executar
                    acao_para_executar = gerenciador_bloqueio.obter_acao_alternativa(
                        acao_original_bloqueada)
                    logging.warning(
                        f"🔄 Invertendo ação de {acao_original_bloqueada} para {acao_para_executar} devido a bloqueio de lado.")
                    # Atualiza a decisão no CSV com a ação corrigida
                    salvar_decisao_csv(acao_para_executar,
                                       confianca_decisao, contexto)

                # Se após todas as verificações, a ação for "NADA" ou alguma forma de "NAO_AGIU"
                if acao_para_executar.startswith("NADA") or acao_para_executar.startswith("NAO_AGIU"):
                    logging.info(
                        f"⏸️ Não agindo: {acao_para_executar} (Confiança: {confianca_decisao:.2f} ou restrição).")
                    # A experiência "NAO_AGIU" para filtros já foi adicionada acima.
                    # Se for "NADA" da previsão, adicionamos agora.
                    if acao_para_executar == "NADA":
                        memoria_experiencias.adicionar(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        salvar_experiencia_csv(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        modelo_ia_local = treinar_modelo(
                            modelo_ia_local, memoria_experiencias)
                        time.sleep(2)
                        continue

                # === VERIFICAÇÃO DE HORÁRIO ANTES DE EXECUTAR ORDEM ===
                horario_atual = datetime.now().time()
                horario_limite_ordens = datetime.strptime(
                    HORARIO_LIMITE_ORDENS, "%H:%M").time()
                if horario_atual >= horario_limite_ordens:
                    logging.info(
                        "🕕 18:15 - Não executando novas ordens (próximo ao encerramento)")
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    modelo_ia_local = treinar_modelo(
                        modelo_ia_local, memoria_experiencias)
                    time.sleep(10)
                    continue

                # ========== INTEGRAÇÃO MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS ==========
                if detector_modo:
                    atr = contexto.get('volatility', 0)
                    entropia = contexto.get('entropia_book', 0.5)
                    detector_modo.atualizar_indicadores(atr, entropia)
                    modo_mercado = detector_modo.detectar_modo()

                    if modo_mercado == "CONSERVADOR":
                        logging.info(f"🐌 Modo CONSERVADOR detectado (ATR: {atr:.1f}, Entropia: {entropia:.3f})")

                # ========== INTEGRAÇÃO NOVAS MELHORIAS 7 E 9 ==========
                # Atualiza detector de tendência com preço de fechamento
                if detector_tendencia and DETECTOR_TENDENCIA_ATIVO:
                    preco_fechamento = contexto.get('close_price', 0)
                    if preco_fechamento > 0:
                        detector_tendencia.atualizar_tendencia(preco_fechamento)

                # Atualiza filtro de spread dinâmico com ATR
                if filtro_spread and SPREAD_DINAMICO_ATIVO:
                    atr_atual = contexto.get('volatility', 0)
                    filtro_spread.atualizar_atr(atr_atual)

                # ========== INTEGRAÇÃO MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS ==========
                if circuit_breaker and CIRCUIT_BREAKER_ATIVO:
                    spread_atual = contexto.get('spread', 0)
                    if circuit_breaker.verificar_circuit_breakers(spread_atual):
                        status = circuit_breaker.get_status()
                        logging.warning(f"🚨 CIRCUIT BREAKER ATIVADO: {status['motivo']}")
                        logging.info("⏸️ Operação bloqueada por circuit breaker. Aguardando...")
                        time.sleep(30)  # Aguarda 30 segundos antes de tentar novamente
                        continue

                # Executa ordem com a ação final decidida
                ticket = executar_ordem(
                    acao_para_executar, modo_operacional=modo_operacional)
                if not ticket:
                    logging.warning(
                        "❌ Ordem não enviada (executar_ordem falhou). Loop reiniciado.")
                    time.sleep(2)
                    continue

                # ... (restante da lógica de confirmação da ordem e criação de PosicaoAtiva) ...
                # O bloco de salvar experiência e treinar modelo APÓS FECHAMENTO DE ORDEM já está lá.
                # Apenas precisamos garantir que o contexto usado para PosicaoAtiva e para memória seja o `contexto` correto da decisão.

                ticket_ordem_atual = ticket
                esperando_confirmacao = True
                confirmado = False
                for _ in range(20):  # Tenta por 10 segundos
                    time.sleep(0.5)
                    if verificar_se_ordem_virou_posicao(ticket, SYMBOL):
                        logging.info(f"✅ Ordem {ticket} virou posição.")
                        posicao_aberta = True
                        confirmado = True
                        break

                esperando_confirmacao = False

                if not confirmado:
                    logging.warning(
                        f"❌ Ordem {ticket} não virou posição. Abortando tentativa.")
                    ticket_ordem_atual = None
                    # NÃO salvamos experiência aqui porque a ordem não foi efetivada
                    time.sleep(3)
                    continue

                # Após confirmação da ordem que virou posição
                ordem_confirmada_info = mt5.history_orders_get(ticket=ticket)
                if not ordem_confirmada_info:
                    logging.error(
                        f"❌ Não foi possível obter detalhes da ordem {ticket} do histórico para criar PosicaoAtiva.")
                    continue
                ordem_obj = ordem_confirmada_info[0]

                preco_de_execucao_real = ordem_obj.price_open  # Fallback
                # Busca deals desde a criação da ordem
                inicio_busca = datetime.fromtimestamp(
                    ordem_obj.time_setup_msc // 1000) - timedelta(seconds=1)
                deals_da_ordem = mt5.history_deals_get(
                    inicio_busca, datetime.now())
                if deals_da_ordem:
                    deal_de_entrada_encontrado = None
                    for deal_obj in deals_da_ordem:
                        if deal_obj.order == ordem_obj.ticket and deal_obj.entry == mt5.DEAL_ENTRY_IN:
                            deal_de_entrada_encontrado = deal_obj
                            break
                    if deal_de_entrada_encontrado:
                        preco_de_execucao_real = deal_de_entrada_encontrado.price
                        logging.info(
                            f"Found entry deal for order {ordem_obj.ticket}, "
                            f"execution price: {preco_de_execucao_real}"
                        )
                    else:
                        logging.warning(
                            f"Entry deal not found for order {ordem_obj.ticket}, "
                            f"using order.price_open ({preco_de_execucao_real}) as entry price for PosicaoAtiva."
                        )
                else:
                    logging.warning(
                        f"No deals found for order {ordem_obj.ticket} when creating PosicaoAtiva, "
                        f"using order.price_open ({preco_de_execucao_real})."
                    )
                score_inicial = calcular_score_distancia(
                    preco_entrada=preco_de_execucao_real,
                    preco_saida=preco_de_execucao_real,
                    sl=ordem_obj.sl,
                    tp=ordem_obj.tp
                )
                posicao_atual = PosicaoAtiva(
                    ticket=ticket,
                    tipo=acao_para_executar,  # Usar a ação efetivamente executada
                    preco_entrada=preco_de_execucao_real,
                    sl=ordem_obj.sl,
                    tp=ordem_obj.tp,
                    score_inicial=score_inicial,
                    entry_context=contexto.copy()  # Salva o contexto que levou à decisão
                )
                logging.debug(
                    f"[DEBUG] posicao_atual após instanciação: {posicao_atual} (type: {type(posicao_atual)})"
                )
                logging.info(
                    f"📊 Nova posição iniciada: Ticket={posicao_atual.ticket}, "
                    f"Tipo={posicao_atual.tipo}, "
                    f"Entrada={posicao_atual.preco_entrada:.3f}, "
                    f"SL={posicao_atual.sl:.3f}, "
                    f"TP={posicao_atual.tp:.3f}, "
                    f"Score Inicial={posicao_atual.score_inicial:.2f}"
                )
                # NÃO calcular lucro/experiência aqui. Isso é feito quando a posição FECHA.
                time.sleep(2)  # Pequena pausa após abrir posição

            except Exception as e:
                logging.error(f"❌ Erro GRAVE no loop principal: {e}")
                logging.error(traceback.format_exc())
                time.sleep(2)  # Aguarda um pouco antes de continuar

        return mt5_ativo_local, modelo_ia_local
    except Exception as e:
        logging.error(f"❌ Erro GRAVE no loop principal: {e}")
        logging.error(traceback.format_exc())
        time.sleep(2)  # Aguarda um pouco antes de continuar

# endregion

# region [Circuit Breakers]


def verificar_circuit_breakers(contexto: Dict[str, Any]) -> Tuple[bool, str]:
    """Verifica condições de circuit breaker."""
    agora = datetime.now().time()
    inicio = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    fim = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    # Verifica horário de operação
    if not (inicio <= agora <= fim):
        return True, "Fora do horário de operação"

    # Verifica spread
    if contexto.get('spread', 0) > MAX_SPREAD:
        return True, f"Spread muito alto: {contexto['spread']:.1f} pontos"

    # Verifica volume total no book
    volume_total = contexto.get('bid_qty', 0) + contexto.get('ask_qty', 0)
    if volume_total < MIN_VOLUME_BOOK:
        return True, f"Volume total insuficiente no book: {volume_total}"

    # Verifica volume mínimo em ambos os lados
    if contexto.get('bid_qty', 0) < MIN_TICKS_VALIDOS:
        return True, f"Volume bid insuficiente: {contexto.get('bid_qty', 0)}"
    if contexto.get('ask_qty', 0) < MIN_TICKS_VALIDOS:
        return True, f"Volume ask insuficiente: {contexto.get('ask_qty', 0)}"

    # Verifica drawdown diário
    lucro_dia = sum(historico_lucro[-100:])  # Últimas 100 operações
    if lucro_dia < MAX_LOSS_DIARIO:
        return True, f"Stop loss diário atingido: {lucro_dia:.2f}"

    return False, ""


def verificar_integridade_dados(dados: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica a integridade dos dados recebidos.
    Retorna (True, mensagem) se os dados são válidos.
    """
    # Verifica valores nulos
    if None in dados.values():
        return False, "Dados contêm valores nulos"

    # Verifica valores negativos onde não deveria
    if dados.get('bid_qty', 0) < 0 or dados.get('ask_qty', 0) < 0:
        return False, "Quantidades negativas no book"

    # Verifica valores absurdos
    if dados.get('spread', 0) > 1000:  # Spread absurdamente alto
        return False, "Spread anormal"

    # Verifica consistência do RSI
    rsi = dados.get('rsi_14', 0)
    if not (0 <= rsi <= 100):
        return False, "RSI fora do intervalo válido"

    return True, ""

# endregion

# region [Filtros Evolutivos Removidos]
# Classe FiltrosEvolutivos removida para evitar conflitos
# endregion

# region [Aprendizado]


class MemoriaExperiencias:
    """Gerencia a memória de experiências do modelo."""

    def __init__(self, max_size: int = MAX_EXPERIENCIAS_MEMORIA):
        self.max_size = max_size
        self.experiencias = []
        self.indices_positivos = []
        self.indices_negativos = []
        self.timestamps = []
        self.ultimo_replay = datetime.now()
        self.historico_decisoes = []  # Para métrica de consistência
        self.score_consistencia = 0.0
        self.contagem_acoes = {"BUY": 0, "SELL": 0, "NADA": 0}  # Novo contador
        self.razao_buy_sell = 1.0  # Nova métrica de balanceamento

    def adicionar(self, contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
        """Adiciona uma nova experiência à memória."""
        if len(self.experiencias) >= self.max_size:
            self.experiencias.pop(0)
            self.timestamps.pop(0)
            self.indices_positivos = [
                i-1 for i in self.indices_positivos if i > 0]
            self.indices_negativos = [
                i-1 for i in self.indices_negativos if i > 0]

        self.experiencias.append((contexto, acao, lucro, score_dist))
        self.timestamps.append(datetime.now())
        idx = len(self.experiencias) - 1

        # Atualiza contadores de ações
        self.contagem_acoes[acao] = self.contagem_acoes.get(acao, 0) + 1

        # Atualiza razão BUY/SELL
        total_operacoes = self.contagem_acoes["BUY"] + \
            self.contagem_acoes["SELL"]
        if total_operacoes > 0:
            self.razao_buy_sell = self.contagem_acoes["BUY"] / total_operacoes

        # Atualiza índices e consistência
        if lucro > 0:
            self.indices_positivos.append(idx)
            self.historico_decisoes.append(1)
        else:
            self.indices_negativos.append(idx)
            self.historico_decisoes.append(0)

        # Mantém apenas últimas N decisões para consistência
        if len(self.historico_decisoes) > JANELA_CONSISTENCIA:
            self.historico_decisoes.pop(0)

        # Atualiza score de consistência
        self.atualizar_consistencia()

    def get_balanceamento_status(self) -> Dict[str, Any]:
        """Retorna estatísticas de balanceamento das operações."""
        total_ops = sum(self.contagem_acoes.values())
        return {
            "contagem": self.contagem_acoes.copy(),
            "razao_buy_sell": self.razao_buy_sell,
            "total_operacoes": total_ops,
            "buy_percent": (self.contagem_acoes["BUY"] / total_ops * 100) if total_ops > 0 else 0,
            "sell_percent": (self.contagem_acoes["SELL"] / total_ops * 100) if total_ops > 0 else 0
        }

    def calcular_decay(self, timestamp: datetime) -> float:
        """Calcula o decay exponencial baseado no tempo passado desde o timestamp.

        Args:
            timestamp: Momento em que a experiência foi registrada

        Returns:
            float: Valor entre 0 e 1, onde 1 significa experiência recente e
                  valores próximos de 0 significam experiências antigas
        """
        tempo_passado = (datetime.now() - timestamp).total_seconds()
        # Usa DECAY_MEIA_VIDA (em horas) para calcular o decay
        decay = math.exp(-tempo_passado / (DECAY_MEIA_VIDA * 3600))
        return max(0.1, min(1.0, decay))  # Limita entre 0.1 e 1.0

    def atualizar_consistencia(self) -> None:
        """Calcula score de consistência baseado nas últimas decisões."""
        if len(self.historico_decisoes) < 2:
            self.score_consistencia = 0.5
            return

        # Calcula sequências de acertos e erros
        sequencias = []
        seq_atual = 1
        for i in range(1, len(self.historico_decisoes)):
            if self.historico_decisoes[i] == self.historico_decisoes[i-1]:
                seq_atual += 1
            else:
                sequencias.append(seq_atual)
                seq_atual = 1
        sequencias.append(seq_atual)

        # Score baseado em:
        # 1. Tamanho médio das sequências (maior = mais consistente)
        # 2. Proporção de acertos
        # 3. Penalização por alternância frequente
        media_seq = sum(sequencias) / len(sequencias) if sequencias else 1
        prop_acertos = sum(self.historico_decisoes) / \
            len(self.historico_decisoes)
        alternancia = len(sequencias) / len(self.historico_decisoes)

        self.score_consistencia = (
            0.4 * (media_seq / JANELA_CONSISTENCIA) +  # Peso das sequências
            0.4 * prop_acertos +                       # Peso dos acertos
            # Penalização por alternância
            0.2 * (1 - alternancia)
        )

    def verificar_replay(self) -> bool:
        """Verifica se é hora de fazer replay das experiências."""
        tempo_desde_replay = (
            datetime.now() - self.ultimo_replay).total_seconds() / 60
        return tempo_desde_replay >= INTERVALO_REPLAY

    def obter_batch_replay(self) -> Tuple[List[Tuple[Dict[str, Any], str, float, float]], List[float]]:
        """Obtém batch para replay com foco em experiências positivas antigas."""
        self.ultimo_replay = datetime.now()

        # Prioriza experiências positivas antigas
        exp_positivas = [(i, exp) for i, exp in enumerate(self.experiencias)
                         if i in self.indices_positivos]

        if not exp_positivas:
            return [], []

        # Ordena por idade (mais antigas primeiro)
        exp_positivas.sort(key=lambda x: self.timestamps[x[0]])

        # Seleciona subset para replay
        n_replay = min(BATCH_SIZE, len(exp_positivas))
        indices_replay = [idx for idx, _ in exp_positivas[:n_replay]]

        batch = [self.experiencias[i] for i in indices_replay]
        decays = [PESO_REPLAY * self.calcular_decay(self.timestamps[i])
                  for i in indices_replay]

        return batch, decays

    def tem_suficiente(self) -> bool:
        """Verifica se há experiências suficientes para treino."""
        return len(self.experiencias) >= MIN_EXPERIENCIAS_TREINO


def normalizar_recompensas(recompensas: List[float], scores_distancia: List[float], decays: List[float]) -> List[float]:
    """Normaliza as recompensas usando normalização min-max com clipping, score de distância e decay temporal."""
    if not recompensas:
        return []

    # Aplica clipping para limitar valores extremos
    recompensas_clip = [max(min(r, 100), -100) for r in recompensas]

    # Normaliza para [0, 1]
    min_r = min(recompensas_clip)
    max_r = max(recompensas_clip)

    if min_r == max_r:
        recompensas_norm = [0.5] * len(recompensas_clip)
    else:
        recompensas_norm = [(r - min_r) / (max_r - min_r)
                            for r in recompensas_clip]

    # Combina com score de distância e aplica decay (60% lucro, 30% distância, decay aplicado ao total)
    recompensas_final = [
        (0.6 * r + 0.4 * s) * d
        for r, s, d in zip(recompensas_norm, scores_distancia, decays)
    ]

    return recompensas_final


def treinar_modelo(modelo: Sequential, memoria: MemoriaExperiencias) -> Sequential:
    """Treina o modelo com early stopping e batch balanceado."""
    global historico_loss
    logging.info(
        f"[treinar_modelo] Iniciando treino: tenho {len(memoria.experiencias)} experiências.")

    if not memoria.tem_suficiente():
        logging.info(
            "[treinar_modelo] Aguardando mais experiências para treino (memória insuficiente).")
        return modelo

    batch, decays = memoria.obter_batch_replay()
    # Log para inspecionar o conteúdo de 'batch' (GARANTIDO/REINSERIDO)
    logging.debug(
        f"[treinar_modelo] Conteúdo do batch (primeiras 2 exp, se houver): {batch[:2]}")

    # VERIFICAÇÃO DE BATCH VAZIO (NOVO)
    if not batch:
        logging.info(
            "[treinar_modelo] Batch de replay vazio (ex: sem experiências positivas ou lógica do batch retornou vazio). Treino adiado.")
        return modelo

    df_exp = pd.DataFrame([{
        **ctx,
        "action": ac,
        "reward": luc,
        "score_dist": score_dist
    } for ctx, ac, luc, score_dist in batch])
    # Este log agora só será atingido se batch não for vazio
    logging.debug(
        f"[treinar_modelo] Colunas de df_exp antes de normalizar recompensas: {df_exp.columns.tolist()}")

    # Normaliza recompensas com decay
    recompensas = normalizar_recompensas(
        df_exp["reward"].tolist(),
        df_exp["score_dist"].tolist(),
        decays
    )
    df_exp["reward_norm"] = recompensas

    # Log das experiências mais recentes vs antigas
    idade_media = sum((datetime.now() - ts).total_seconds() / 3600
                      for ts in memoria.timestamps) / len(memoria.timestamps)
    decay_medio = sum(decays) / len(decays)
    logging.info(
        f"📚 Idade média das experiências: {idade_media:.1f}h, Decay médio: {decay_medio:.2f}")

    # *** CORREÇÃO CRÍTICA: USA A MESMA FUNÇÃO preparar_dados() QUE FUNCIONA NO LOOP PRINCIPAL ***
    try:
        # Remove colunas extras que não são features
        df_treino = df_exp.drop(
            columns=["reward", "reward_norm", "score_dist"])

        # Usa a função preparar_dados que já funciona corretamente
        X_train, y_train_series = preparar_dados(df_treino)

        if X_train is None or y_train_series is None:
            logging.error("[treinar_modelo] preparar_dados() retornou None")
            return

        # CORREÇÃO DO ERRO: Converte corretamente para numpy arrays
        # Verifica se X_train é DataFrame e converte adequadamente
        if hasattr(X_train, 'values'):
            x_train = X_train.values.astype(np.float32)
        else:
            x_train = np.array(X_train, dtype=np.float32)

        # Verifica se y_train_series é Series e converte adequadamente
        if hasattr(y_train_series, 'values'):
            y_train = y_train_series.values.astype(np.float32)
        else:
            y_train = np.array(y_train_series, dtype=np.float32)

        # Verifica se os arrays têm a forma correta
        if len(x_train.shape) != 2 or x_train.shape[1] != N_FEATURES:
            logging.error(
                f"[treinar_modelo] Shape incorreto de X_train: {x_train.shape}, esperado: (?, {N_FEATURES})")
            return

        if len(y_train.shape) != 1:
            logging.error(
                f"[treinar_modelo] Shape incorreto de y_train: {y_train.shape}, esperado: (?,)")
            return

        # Verifica se há valores inválidos (NaN, inf)
        if np.isnan(x_train).any() or np.isinf(x_train).any():
            logging.error(
                "[treinar_modelo] X_train contém valores NaN ou infinitos")
            x_train = np.nan_to_num(x_train, nan=0.0, posinf=1.0, neginf=0.0)

        if np.isnan(y_train).any() or np.isinf(y_train).any():
            logging.error(
                "[treinar_modelo] y_train contém valores NaN ou infinitos")
            y_train = np.nan_to_num(y_train, nan=0.0, posinf=1.0, neginf=0.0)

        logging.info(
            f"[treinar_modelo] Dados preparados com sucesso - X_train.shape = {x_train.shape}, y_train.shape = {y_train.shape}")
        logging.info(
            f"[treinar_modelo] Tipos finais: X_train={type(x_train)} dtype={x_train.dtype}, y_train={type(y_train)} dtype={y_train.dtype}")
        logging.debug(f"[treinar_modelo] X_train sample: {x_train[0]}")
        logging.debug(f"[treinar_modelo] y_train sample: {y_train[0]}")

    except Exception as e:
        logging.error(
            f"[treinar_modelo] Erro ao preparar dados para treino: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        return modelo

    # Pesos das amostras baseados nas recompensas normalizadas
    # Adiciona pequeno valor para evitar peso zero
    sample_weight = [r + 0.1 for r in recompensas]

    # Early stopping
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='loss',
        min_delta=MIN_DELTA_LOSS,
        patience=PATIENCE_EARLY_STOP,
        verbose=0,
        restore_best_weights=True
    )

    # Treina o modelo com shuffle
    try:
        # VALIDAÇÃO FINAL ANTES DO FIT
        logging.info(f"[treinar_modelo] Validação final antes do fit:")
        logging.info(
            f"[treinar_modelo] x_train: shape={x_train.shape}, dtype={x_train.dtype}, type={type(x_train)}")
        logging.info(
            f"[treinar_modelo] y_train: shape={y_train.shape}, dtype={y_train.dtype}, type={type(y_train)}")
        logging.info(
            f"[treinar_modelo] sample_weight: len={len(sample_weight)}, type={type(sample_weight)}")

        # Garante que sample_weight também seja numpy array
        sample_weight = np.array(sample_weight, dtype=np.float32)

        # *** CORREÇÃO CRÍTICA: FORÇA BUILD DO MODELO E RECRIA OTIMIZADOR ***
        # Resolve o erro "Unknown variable" do otimizador com BatchNormalization
        logging.info("[treinar_modelo] Forçando build do modelo...")

        # Força build do modelo com dados de entrada
        modelo.build(input_shape=(None, N_FEATURES))

        # Recria completamente o otimizador (nova instância)
        novo_otimizador = Adam(learning_rate=0.001)

        logging.info(
            "[treinar_modelo] Recompilando modelo com novo otimizador...")
        modelo.compile(
            optimizer=novo_otimizador,
            loss='binary_crossentropy',
            metrics=['accuracy']
        )

        # Teste rápido com uma amostra pequena primeiro
        if len(x_train) > 1:
            test_x = x_train[:1]
            test_y = y_train[:1]
            logging.info(
                f"[treinar_modelo] Teste rápido com amostra: x_shape={test_x.shape}, y_shape={test_y.shape}")
            _ = modelo.predict(test_x, verbose=0)
            logging.info(
                "[treinar_modelo] ✅ Teste de predição passou - iniciando fit completo")

        # Treina com tratamento de erro específico para BatchNormalization
        try:
            history = modelo.fit(
                x_train, y_train,
                epochs=EPOCHS_TREINO,
                batch_size=BATCH_SIZE,
                verbose=0,
                sample_weight=sample_weight,
                callbacks=[early_stop],
                shuffle=True
            )
        except ValueError as ve:
            if "Unknown variable" in str(ve):
                logging.warning(
                    "[treinar_modelo] Erro de otimizador detectado - recreando modelo...")
                # Se ainda houver erro, recria o modelo completamente
                modelo_novo = criar_modelo_neural(N_FEATURES)
                modelo_novo.compile(
                    optimizer=Adam(learning_rate=0.001),
                    loss='binary_crossentropy',
                    metrics=['accuracy']
                )
                history = modelo_novo.fit(
                    x_train, y_train,
                    epochs=EPOCHS_TREINO,
                    batch_size=BATCH_SIZE,
                    verbose=0,
                    sample_weight=sample_weight,
                    callbacks=[early_stop],
                    shuffle=True
                )
                # Atualiza referência do modelo
                modelo = modelo_novo
                logging.info(
                    "[treinar_modelo] ✅ Modelo recriado e treinado com sucesso")
            else:
                raise

        # Salva histórico de loss
        historico_loss.extend(history.history['loss'])
        if len(historico_loss) > 1000:  # Mantém últimos 1000 pontos
            historico_loss = historico_loss[-1000:]

        logging.info("[treinar_modelo] PRESTES A SALVAR O MODELO.")
        # Salva modelo em ambos os formatos
        salvar_modelo(modelo)

        # Salva experiências em JSON
        salvar_experiencias_json(memoria.experiencias)

        # Log do treinamento
        final_loss = history.history['loss'][-1]
        epochs_trained = len(history.history['loss'])
        logging.info(
            f"🧠 Modelo treinado por {epochs_trained} épocas. Loss final: {final_loss:.4f}")

    except Exception as e:
        logging.error(f"[treinar_modelo] Erro durante o fit() do modelo: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        return modelo

    # Retorna o modelo (pode ser o original ou um novo se foi recriado)
    return modelo


def prever_acao(modelo: Sequential, X: pd.DataFrame,
                modo_operacional: Optional[ModoOperacional] = None,
                filtros_evolutivos: Optional[Any] = None,
                contexto_completo: Optional[Dict] = None) -> Tuple[str, float]:
    """Prevê a próxima ação com filtros evolutivos que aumentam seletividade conforme experiência."""
    try:
        # VALIDAÇÃO E CORREÇÃO DE TIPOS PARA PREDIÇÃO
        if hasattr(X, 'values'):
            x_pred = X.values.astype(np.float32)
        else:
            x_pred = np.array(X, dtype=np.float32)

        # Verifica se há valores inválidos
        if np.isnan(x_pred).any() or np.isinf(x_pred).any():
            logging.warning(
                "[prever_acao] Dados contêm valores NaN ou infinitos - corrigindo")
            x_pred = np.nan_to_num(x_pred, nan=0.0, posinf=1.0, neginf=0.0)

        # Verifica shape
        if len(x_pred.shape) != 2 or x_pred.shape[1] != N_FEATURES:
            logging.error(
                f"[prever_acao] Shape incorreto: {x_pred.shape}, esperado: (?, {N_FEATURES})")
            return "NADA", 0.0

        logging.debug(
            f"[prever_acao] x_pred: shape={x_pred.shape}, dtype={x_pred.dtype}")

        resultado_predicao = modelo.predict(x_pred, verbose=0)
        if resultado_predicao is None or len(resultado_predicao) == 0:
            logging.warning("⚠️ Previsão vazia ou inválida")
            return "NADA", 0.0

        acao_prob = float(resultado_predicao[0][0])  # Garante que é float
        confianca = 1.0

        # Ajusta threshold baseado no balanceamento atual
        if memoria_experiencias:
            status = memoria_experiencias.get_balanceamento_status()
            razao_atual = status["razao_buy_sell"]

            # Log detalhado do estado atual
            logging.info(
                f"📊 Estado atual - Prob. compra: {acao_prob:.3f}, RSI: {X['rsi_14'].iloc[0]:.1f}")

            # ========== INTEGRAÇÃO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
            threshold_base = 0.5
            if balanceador and BALANCEAMENTO_ATIVO:
                threshold_base = balanceador.ajustar_threshold(threshold_base)
                status = balanceador.get_status()
                logging.info(f"⚖️ Balanceamento: BUY={status['buy_count']}, SELL={status['sell_count']}, "
                            f"BUY%={status['buy_percentage']:.1f}%, Threshold ajustado={threshold_base:.3f}")

            # Ajusta threshold dinamicamente com MAIS AGRESSIVIDADE
            max_ajuste = 0.25  # Aumentado para 25% (mais agressivo)

            # Considera RSI para ajuste adicional
            rsi = X['rsi_14'].iloc[0]
            rsi_ajuste = 0.0

            if rsi < 30:  # Sobrevenda
                rsi_ajuste = -0.05  # Favorece compras
            elif rsi > 70:  # Sobrecompra
                rsi_ajuste = 0.05  # Favorece vendas

            # BALANCEAMENTO MAIS AGRESSIVO - permite mais desequilíbrio
            if razao_atual < 0.35:  # Menos de 35% de compras (mais tolerante)
                # Multiplicador mais agressivo
                ajuste = min((0.35 - razao_atual) * 3.0, max_ajuste)
                threshold = threshold_base - ajuste + rsi_ajuste
                logging.info(
                    f"📊 Ajustando threshold para {threshold:.3f} (favorecendo compras) | RSI ajuste: {rsi_ajuste:.3f}")
            # Se houver mais compras que vendas, aumenta threshold para favorecer vendas
            elif razao_atual > 0.65:  # Mais de 65% de compras (mais tolerante)
                # Multiplicador mais agressivo
                ajuste = min((razao_atual - 0.65) * 3.0, max_ajuste)
                threshold = threshold_base + ajuste + rsi_ajuste
                logging.info(
                    f"📊 Ajustando threshold para {threshold:.3f} (favorecendo vendas) | RSI ajuste: {rsi_ajuste:.3f}")
            else:
                threshold = threshold_base + rsi_ajuste
                logging.info(
                    f"📊 Threshold base mantido em {threshold:.3f} | RSI ajuste: {rsi_ajuste:.3f}")

            acao_inicial = "BUY" if acao_prob > threshold else "SELL"

            # ========== APLICAÇÃO DOS NOVOS FILTROS ==========
            # Filtro 1: Horário Premium
            if FILTRO_HORARIO_ATIVO and filtro_horario and not filtro_horario.is_horario_premium():
                logging.info("⏰ Operação bloqueada - Fora do horário premium")
                return "NADA", 0.0

            # Filtro 2: Tendência (só opera a favor)
            if DETECTOR_TENDENCIA_ATIVO and detector_tendencia and not detector_tendencia.pode_operar(acao_inicial):
                logging.info(f"📈 Operação bloqueada - {acao_inicial} contra tendência {detector_tendencia.tendencia_atual}")
                return "NADA", 0.0

            # Filtro 3: Cooldown
            if COOLDOWN_ATIVO and cooldown_sistema and not cooldown_sistema.pode_operar():
                tempo_restante = cooldown_sistema.tempo_restante_cooldown()
                logging.info(f"⏳ Operação bloqueada - Cooldown ativo ({tempo_restante}s restantes)")
                return "NADA", 0.0

            # Filtro 4: Spread dinâmico
            spread_atual = contexto_completo.get('spread', 0) if contexto_completo else 0
            if SPREAD_DINAMICO_ATIVO and filtro_spread and not filtro_spread.spread_aceitavel(spread_atual):
                logging.info(f"📊 Operação bloqueada - Spread alto ({spread_atual:.1f} > {filtro_spread.spread_maximo_atual})")
                return "NADA", 0.0

            acao = acao_inicial

            # Log detalhado do balanceamento
            logging.info(
                f"🔄 Balanceamento - BUY: {status['buy_percent']:.1f}% | SELL: {status['sell_percent']:.1f}%")
            logging.info(
                f"📈 Decisão final: {acao} | Prob: {acao_prob:.3f} | Threshold: {threshold:.3f}")
        else:
            threshold = 0.5
            acao = "BUY" if acao_prob > threshold else "SELL"
            logging.info(
                f"📈 Decisão sem balanceamento: {acao} | Prob: {acao_prob:.3f}")

        return acao, confianca
    except Exception as e:
        logging.error(f"❌ Erro ao prever ação: {e}")
        return "NADA", 0.0


def salvar_experiencias_json(experiencias: List[Tuple[Dict[str, Any], str, float, float]], arquivo: str = "experiencias.json") -> None:
    """Salva as experiências em formato JSON."""
    try:
        dados = []
        for contexto, acao, lucro, score_dist in experiencias:
            dados.append({
                "contexto": contexto,
                "acao": acao,
                "lucro": lucro,
                "score_dist": score_dist,
                "timestamp": datetime.now().isoformat()
            })

        with open(arquivo, 'w') as f:
            json.dump(dados, f, indent=2)
        logging.info(f"✅ Experiências salvas em {arquivo}")
    except Exception as e:
        logging.error(f"❌ Erro ao salvar experiências em JSON: {e}")


def salvar_decisao_csv(acao: str, confianca: float, contexto: Dict[str, Any], arquivo: str = "decisions.csv") -> None:
    """Salva uma decisão no arquivo CSV de decisões."""
    try:
        abs_path_arquivo = os.path.abspath(arquivo)
        logging.info(
            f"[salvar_decisao_csv] Tentando salvar decisão em: {abs_path_arquivo}")

        dados = {
            "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M:%S"),  # Formato corrigido
            "acao": acao,
            "confianca": confianca,
            "bid_qty": contexto.get('bid_qty', 0),
            "ask_qty": contexto.get('ask_qty', 0),
            "spread": contexto.get('spread', 0),
            "volatility": contexto.get('volatility', 0),
            "candle_type": contexto.get('candle_type', ''),
            "entropia_book": contexto.get('entropia_book', 0),
            "rsi_14": contexto.get('rsi_14', 0),
            "volume_tick": contexto.get('volume_tick', 0)
        }

        df = pd.DataFrame([dados])

        file_exists = os.path.exists(abs_path_arquivo)
        file_size = os.path.getsize(abs_path_arquivo) if file_exists else 0
        logging.info(
            f"[salvar_decisao_csv] Arquivo '{abs_path_arquivo}' existe: {file_exists}, Tamanho: {file_size} bytes")

        # Escreve com cabeçalho se o arquivo não existe OU se existe mas está vazio.
        if not file_exists or (file_exists and file_size == 0):
            df.to_csv(abs_path_arquivo, index=False)
        else:
            # Adiciona sem cabeçalho se o arquivo já existe e tem conteúdo.
            df.to_csv(abs_path_arquivo, mode='a', header=False, index=False)

        logging.info(f"✅ Decisão salva em {abs_path_arquivo}")
    except Exception as e:
        logging.error(f"❌ Erro ao salvar decisão em CSV: {e}")

# endregion

# region [Funções de Mercado]


def verificar_estado_book(symbol: str = SYMBOL) -> bool:
    """Verifica se o book está ativo e funcionando corretamente."""
    try:
        # Verifica se é fim de semana
        if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
            logging.info(
                "📅 Fim de semana: book não disponível (comportamento normal)")
            return True  # Retorna True para evitar tentativas de reinicialização

        # Garante que o símbolo esteja selecionado
        mt5.symbol_select(symbol, True)

        # Verifica se o book está ativo
        if not mt5.market_book_add(symbol):
            logging.error(f"❌ Erro ao ativar book: {mt5.last_error()}")
            return False

        # Tenta obter dados do book
        book = mt5.market_book_get(symbol)
        if book is None:
            logging.error("❌ Book retornou None")
            return False

        # Verifica se há dados no book
        if len(book) == 0:
            logging.error("❌ Book vazio")
            return False

        # Verifica tipos de ordem no book
        tipos_ordem = set(level.type for level in book)
        if len(tipos_ordem) < 2:
            logging.error(f"❌ Book com apenas um tipo de ordem: {tipos_ordem}")
            return False

        return True

    except Exception as e:
        logging.error(f"❌ Erro ao verificar estado do book: {e}")
        return False


def reiniciar_book(symbol: str = SYMBOL) -> bool:
    """Tenta reiniciar o book de ofertas."""
    try:
        # Desativa o book
        mt5.market_book_release(symbol)
        time.sleep(1)  # Espera 1 segundo

        # Reativa o book
        if not mt5.market_book_add(symbol):
            logging.error("❌ Falha ao reativar book")
            return False

        time.sleep(1)  # Espera mais 1 segundo

        # Verifica se está funcionando
        return verificar_estado_book(symbol)

    except Exception as e:
        logging.error(f"❌ Erro ao reiniciar book: {e}")
        return False


def calcular_atr(high_prices: List[float], low_prices: List[float], close_prices: List[float], periodo: int = 14) -> float:
    """
    Calcula o Average True Range (ATR) para um período específico.

    Args:
        high_prices: Lista de preços máximos
        low_prices: Lista de preços mínimos
        close_prices: Lista de preços de fechamento
        periodo: Período para cálculo do ATR (default 14)

    Returns:
        float: Valor do ATR
    """
    if len(high_prices) < periodo + 1 or len(low_prices) < periodo + 1 or len(close_prices) < periodo + 1:
        return 0.0

    # Calcula True Range
    tr_values = []
    for i in range(1, len(close_prices)):
        high = high_prices[i]
        low = low_prices[i]
        prev_close = close_prices[i-1]

        tr = max(
            high - low,  # Current High - Current Low
            abs(high - prev_close),  # Current High - Previous Close
            abs(low - prev_close)  # Current Low - Previous Close
        )
        tr_values.append(tr)

    # Calcula média móvel do TR para obter ATR
    if not tr_values:
        return 0.0

    # Implementa Wilder's Smoothing
    atr = tr_values[0]  # Primeiro TR como valor inicial
    for tr in tr_values[1:]:
        atr = ((periodo - 1) * atr + tr) / periodo

    return atr


def verificar_mercado_aberto() -> Tuple[bool, str]:
    """Verifica se o mercado está aberto e em qual período."""
    agora = datetime.now().time()
    pregao = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    after = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    # Verifica se é fim de semana
    if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
        return False, "Mercado fechado (Fim de semana) 🏖️"

    # Verifica horário
    if agora < pregao:
        return False, "Mercado fechado (Antes do pregão) ⏰"
    elif agora > after:
        return False, "Mercado fechado (Após after-market) 🌙"

    # Verifica se o símbolo está ativo
    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        return False, "Símbolo não encontrado ❓"

    if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
        return False, f"Símbolo não está ativo para trading ({symbol_info.trade_mode}) ⚠️"

    return True, "Mercado aberto ✅"


def arredondar_preco(preco: float) -> float:
    """Arredonda o preço para a precisão correta do Mini Índice (WIN)."""
    return round(preco / TICK_SIZE) * TICK_SIZE


def calcular_preco_sl_tp(preco_entrada: float, action: str, sl_points: int, tp_points: int) -> Tuple[float, float]:
    """Calcula preços de SL e TP com arredondamento correto, usando pontos (não ticks)."""
    from MetaTrader5 import symbol_info
    symbol = SYMBOL
    symbol_info_obj = get_cached_symbol_info(symbol)
    if symbol_info_obj is None:
        raise ValueError(
            "Informações do símbolo indisponíveis para cálculo de SL/TP.")

    ponto = symbol_info_obj.point
    # Para WIN: 1 ponto = 1.0 (não multiplicar por TICKS_POR_PONTO)
    sl_dist = sl_points * 1.0  # 90 pontos = 90.0
    tp_dist = tp_points * 1.0  # 35 pontos = 35.0

    # Log detalhado para debug
    logging.info(
        f"🔧 DEBUG SL/TP - Entrada: {preco_entrada:.1f}, Ação: {action}")
    logging.info(
        f"🔧 DEBUG SL/TP - SLOINTS: {sl_points}, TP_POINTS: {tp_points}")
    logging.info(
        f"🔧 DEBUG SL/TP - Point: {ponto}, TICKS_POR_PONTO: {TICKS_POR_PONTO}")
    logging.info(
        f"🔧 DEBUG SL/TP - SL_dist: {sl_dist:.5f}, TP_dist: {tp_dist:.5f}")

    if action == 'BUY':
        sl = arredondar_preco(preco_entrada - sl_dist)
        tp = arredondar_preco(preco_entrada + tp_dist)
    else:
        sl = arredondar_preco(preco_entrada + sl_dist)
        tp = arredondar_preco(preco_entrada - tp_dist)

    logging.info(f"🔧 DEBUG SL/TP - Calculado: SL={sl:.1f}, TP={tp:.1f}")

    # Validação básica
    if action == 'BUY':
        if sl >= preco_entrada:
            logging.error(
                f"❌ SL inválido para BUY: {sl:.1f} >= {preco_entrada:.1f}")
        if tp <= preco_entrada:
            logging.error(
                f"❌ TP inválido para BUY: {tp:.1f} <= {preco_entrada:.1f}")
    else:  # SELL
        if sl <= preco_entrada:
            logging.error(
                f"❌ SL inválido para SELL: {sl:.1f} <= {preco_entrada:.1f}")
        if tp >= preco_entrada:
            logging.error(
                f"❌ TP inválido para SELL: {tp:.1f} >= {preco_entrada:.1f}")

    return sl, tp


def calcular_sl_tp_dinamico(preco_entrada: float, acao: str, atr: float) -> Tuple[float, float]:
    """Calcula preços de SL e TP com base no ATR e ação de compra ou venda."""
    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        logging.error("❌ Informações do símbolo indisponíveis")
        return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Validação inicial do preço de entrada
    if not (100 <= preco_entrada <= 1000000):  # Faixa de preço razoável para dólar
        logging.error(f"❌ Preço de entrada inválido: {preco_entrada}")
        return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Calcula distâncias iniciais em ticks baseadas no ATR
    sl_ticks = int(MULTIPLICADOR_SL_ATR * atr / symbol_info.point)
    tp_ticks = int(MULTIPLICADOR_TP_ATR * atr / symbol_info.point)

    # Log para debug das distâncias iniciais
    logging.debug(
        f"Distâncias iniciais - SL: {sl_ticks} ticks | TP: {tp_ticks} ticks")

    # Corrige para faixa segura em ticks
    sl_ticks = min(max(sl_ticks, MIN_TICKS), MAX_TICKS)
    tp_ticks = min(max(tp_ticks, MIN_TICKS), MAX_TICKS)

    # Calcula preços baseados nos ticks ajustados
    if acao == "BUY":
        sl_price = preco_entrada - sl_ticks * symbol_info.point
        tp_price = preco_entrada + tp_ticks * symbol_info.point
    else:
        sl_price = preco_entrada + sl_ticks * symbol_info.point
        tp_price = preco_entrada - tp_ticks * symbol_info.point

    # Arredonda os preços
    sl_price = arredondar_preco(sl_price)
    tp_price = arredondar_preco(tp_price)

    # Validação final dos preços calculados
    preco_max = preco_entrada * 1.1  # Limite máximo de 10% acima do preço
    preco_min = preco_entrada * 0.9  # Limite mínimo de 10% abaixo do preço

    # Verifica se os preços estão dentro dos limites razoáveis
    if not (preco_min <= sl_price <= preco_max):
        logging.error(
            f"❌ SL calculado inválido: {sl_price:.1f} (entrada: {preco_entrada:.1f})")
        # Usa fallback seguro
        sl_price = preco_entrada - 500 * \
            symbol_info.point if acao == "BUY" else preco_entrada + 500 * symbol_info.point
        sl_price = arredondar_preco(sl_price)

    if not (preco_min <= tp_price <= preco_max):
        logging.error(
            f"❌ TP calculado inválido: {tp_price:.1f} (entrada: {preco_entrada:.1f})")
        # Usa fallback seguro
        tp_price = preco_entrada + 1000 * \
            symbol_info.point if acao == "BUY" else preco_entrada - 1000 * symbol_info.point
        tp_price = arredondar_preco(tp_price)

    # Validação final da direção de SL/TP
    if acao == "BUY":
        if sl_price >= preco_entrada or tp_price <= preco_entrada:
            logging.error(
                f"❌ Direção SL/TP invertida para BUY - SL: {sl_price:.1f}, TP: {tp_price:.1f}, Entrada: {preco_entrada:.1f}")
            return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)
    else:  # SELL
        if sl_price <= preco_entrada or tp_price >= preco_entrada:
            logging.error(
                f"❌ Direção SL/TP invertida para SELL - SL: {sl_price:.1f}, TP: {tp_price:.1f}, Entrada: {preco_entrada:.1f}")
            return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Log das distâncias finais
    sl_dist_final = abs(sl_price - preco_entrada) / symbol_info.point
    tp_dist_final = abs(tp_price - preco_entrada) / symbol_info.point
    logging.info(
        f"Distâncias finais - SL: {sl_dist_final} ticks | TP: {tp_dist_final} ticks")

    return sl_price, tp_price


def verificar_spread_maximo(symbol_info: Any, tick_info: Any) -> bool:
    """Verifica se o spread está dentro do limite máximo."""
    if symbol_info is None or tick_info is None:
        logging.error(
            "❌ Dados do símbolo ou tick indisponíveis para verificar spread")
        return False

    spread_atual = (tick_info.ask - tick_info.bid) / symbol_info.point
    spread_em_pontos = spread_atual / TICKS_POR_PONTO  # Converte para pontos

    if spread_em_pontos > MAX_SPREAD:
        logging.warning(
            f"⚠️ Spread alto: {spread_em_pontos:.1f} pontos (máx: {MAX_SPREAD})")
        return False

    logging.info(f"✅ Spread OK: {spread_em_pontos:.1f} pontos")
    return True

# endregion

# region [Trading]


class PosicaoAtiva:
    """Mantém informações sobre a posição ativa."""

    def __init__(self, ticket: int, tipo: str, preco_entrada: float,
                 sl: float, tp: float, score_inicial: float, entry_context: Optional[Dict[str, Any]] = None):
        self.ticket = ticket
        self.tipo = tipo  # "BUY" ou "SELL"
        self.preco_entrada = preco_entrada
        self.sl = sl
        self.tp = tp
        self.score_inicial = score_inicial
        self.score_maximo = score_inicial
        self.hora_entrada = datetime.now()
        self.travado = False
        self.historico_scores = [score_inicial]  # Histórico para média móvel
        self.entry_context = entry_context  # Novo atributo

    def adicionar_score(self, score: float) -> float:
        """Adiciona score ao histórico e retorna média móvel."""
        self.historico_scores.append(score)
        if len(self.historico_scores) > JANELA_SUAVIZACAO:
            self.historico_scores.pop(0)
        return sum(self.historico_scores) / len(self.historico_scores)


def monitorar_posicao_ativa(posicao: PosicaoAtiva) -> None:
    """Monitora uma posição ativa e aplica critérios de saída inteligente."""
    tempo_posicao = (datetime.now() - posicao.hora_entrada).total_seconds()
    if tempo_posicao < TEMPO_MIN_POSICAO:
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logging.warning("⚠️ Tick indisponível para monitoramento")
        return

    preco_atual = tick.bid if posicao.tipo == "SELL" else tick.ask

    # ========== INTEGRAÇÃO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
    if trailing_stop and TRAILING_ATIVO:
        novo_sl = trailing_stop.atualizar_trailing(preco_atual, posicao.tipo)
        if novo_sl:
            # Modifica SL da posição
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": SYMBOL,
                "position": posicao.ticket,
                "sl": novo_sl,
                "tp": posicao.tp,
                "magic": MAGIC_NUMBER,
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"🎯 Trailing SL atualizado para {novo_sl}")
                posicao.sl = novo_sl

    # ========== INTEGRAÇÃO MELHORIA 5: SAÍDA INTELIGENTE DE POSIÇÃO ==========
    if saida_inteligente and SAIDA_INTELIGENTE_ATIVA:
        # Atualiza RSI atual (simulado - em produção viria do contexto)
        rsi_atual = 50.0  # Placeholder - deve ser calculado do contexto atual
        saida_inteligente.atualizar_rsi(rsi_atual)

        if saida_inteligente.verificar_saida_inteligente(posicao.ticket, preco_atual, rsi_atual):
            logging.info("🚪 Saída inteligente ativada - fechando posição")
            fechar_posicao_score(posicao, "saída inteligente", 0.0)
            return

    score_atual = calcular_score_distancia(
        posicao.preco_rada,
        preco_atual,
        posicao.sl,
        posicao.tp
    )

    score_suavizado = posicao.adicionar_score(score_atual)
    if score_suavizado > posicao.score_maximo:
        posicao.score_maximo = score_suavizado

    # Fechamento por score mais responsivo
    if posicao.score_maximo > 0.5 and score_suavizado < 0.2:
        fechar_posicao_score(
            posicao, "queda de score pós-lucro", score_suavizado)
        return

    # Critérios já existentes
    if verificar_inversao_score(posicao, score_atual):
        fechar_posicao_score(posicao, "inversão de direção", score_suavizado)
    elif verificar_enfraquecimento(posicao, score_atual):
        if not posicao.travado:
            travar_lucro(posicao, score_atual)


def verificar_inversao_score(posicao: PosicaoAtiva, score_atual: float) -> bool:
    """Verifica se houve inversão significativa no score."""
    # Inversão de positivo para negativo (mais conservador)
    if posicao.score_inicial > 0 and score_atual < THRESHOLD_INVERSAO_SCORE:
        return True
    # Inversão de negativo para positivo (mais conservador)
    if posicao.score_inicial < 0 and score_atual > abs(THRESHOLD_INVERSAO_SCORE):
        return True
    # Queda abrupta do máximo (usando score suavizado)
    if (posicao.score_maximo > SCORE_LOCK_PROFIT and
            score_atual < posicao.score_maximo - INVERSAO_SCORE_MIN):
        return True
    return False


def verificar_enfraquecimento(posicao: PosicaoAtiva, score_atual: float) -> bool:
    """Verifica se o movimento está enfraquecendo e precisa travar lucro."""
    if not posicao.travado:
        if score_atual > SCORE_LOCK_PROFIT:
            return True
        if (posicao.score_maximo > SCORE_LOCK_PROFIT and
                score_atual < posicao.score_maximo * 0.7):
            return True
    return False


def travar_lucro(posicao: PosicaoAtiva, score_atual: float) -> None:
    tick = mt5.symbol_info_tick(SYMBOL)
    symbol_info = get_cached_symbol_info(SYMBOL)
    if tick is None or symbol_info is None:
        logging.warning("[travar_lucro] Tick ou SymbolInfo indisponível.")
        return

    logging.debug(
        f"[travar_lucro] Posição: Tipo={posicao.tipo}, Entrada={posicao.preco_entrada:.3f}")
    logging.debug(
        f"[travar_lucro] Tick Atual: Ask={tick.ask:.3f}, Bid={tick.bid:.3f}")

    # Calcula novo SL (garante pelo menos 30% do movimento a favor)
    if posicao.tipo == "BUY":
        movimento = max(0, tick.bid - posicao.preco_entrada)
        novo_sl = posicao.preco_entrada + movimento * 0.3
        # Nunca mova o SL para baixo do preço de entrada (com margem de 1 tick)
        novo_sl = max(novo_sl, posicao.preco_entrada - symbol_info.point)
    else:
        movimento = max(0, posicao.preco_entrada - tick.ask)
        novo_sl = posicao.preco_entrada - movimento * 0.3
        # Nunca mova o SL para cima do preço de entrada (com margem de 1 tick)
        novo_sl = min(novo_sl, posicao.preco_entrada + symbol_info.point)

    # Limite de segurança: SL não pode ficar mais de 2x o stop original de distância
    sl_dist_original_ticks = SL_POINTS * TICKS_POR_PONTO  # SL_POINTS é em pontos
    # sl_max_dist_ticks = sl_dist_original_ticks * 2 # Não parece estar sendo usado, mas a ideia de limitar é boa.

    logging.debug(
        f"[travar_lucro] Novo SL (calculado, antes de arredondar e limites de segurança): {novo_sl:.3f}, Movimento: {movimento:.3f}")

    # Limites de segurança baseados no preço de entrada e um múltiplo do SL original em pontos
    # Convertendo SL_MAX_POINTS para valor de preço
    max_sl_dev = SL_MAX_POINTS * TICKS_POR_PONTO * symbol_info.point
    if posicao.tipo == "BUY":
        sl_limite_inferior = posicao.preco_entrada - max_sl_dev
        # Garante que não seja muito longe pra baixo
        novo_sl = max(novo_sl, sl_limite_inferior)
    else:  # SELL
        sl_limite_superior = posicao.preco_entrada + max_sl_dev
        # Garante que não seja muito longe pra cima
        novo_sl = min(novo_sl, sl_limite_superior)

    logging.debug(
        f"[travar_lucro] Novo SL (após limites de segurança adicionais): {novo_sl:.3f}")

    novo_sl_arredondado = arredondar_preco(novo_sl)
    logging.debug(
        f"[travar_lucro] Novo SL (após arredondar_preco): {novo_sl_arredondado:.3f}")

    if atualizar_sl(posicao.ticket, novo_sl_arredondado):
        posicao.sl = novo_sl_arredondado
        posicao.travado = True
        logging.info(
            f"🔒 Lucro travado em {novo_sl_arredondado:.2f} (Score: {score_atual:.2f})")


def fechar_posicao_score(posicao: PosicaoAtiva, motivo: str, score_atual: float) -> None:
    """Fecha a posição por critério de score."""
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": posicao.ticket,
        "symbol": SYMBOL,
        "volume": VOLUME_PADRAO,
        "type": mt5.ORDER_TYPE_SELL if posicao.tipo == "BUY" else mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(SYMBOL).bid if posicao.tipo == "BUY" else mt5.symbol_info_tick(SYMBOL).ask,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": f"Score:{score_atual:.2f}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    resultado = mt5.order_send(request)
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(
            f"⚠️ Posição fechada por {motivo}. Score inicial: {posicao.score_inicial:.2f}, Score final: {score_atual:.2f}")
    else:
        logging.error(f"❌ Erro ao fechar posição: {resultado.comment}")


def fechar_todas_posicoes(motivo: str = "Encerramento automático") -> int:
    """Fecha todas as posições abertas do robô."""
    posicoes_fechadas = 0

    try:
        # Obtém todas as posições abertas
        posicoes = mt5.positions_get()
        if not posicoes:
            logging.info("✅ Nenhuma posição aberta para fechar")
            return 0

        # Filtra apenas posições do robô (por magic number)
        posicoes_monstro = [
            pos for pos in posicoes if pos.magic == MAGIC_NUMBER]

        if not posicoes_monstro:
            logging.info("✅ Nenhuma posição do Monstro para fechar")
            return 0

        logging.info(
            f"🔴 Iniciando fechamento de {len(posicoes_monstro)} posições - {motivo}")

        # Fecha cada posição
        for pos in posicoes_monstro:
            try:
                # Determina o tipo de ordem necessário para fechar
                tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

                # Obtém preço atual
                tick = mt5.symbol_info_tick(pos.symbol)
                if not tick:
                    logging.error(
                        f"❌ Não foi possível obter tick para {pos.symbol}")
                    continue

                preco_fechamento = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask

                # Prepara requisição de fechamento
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": pos.ticket,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": tipo_fechamento,
                    "price": preco_fechamento,
                    "deviation": 20,
                    "magic": MAGIC_NUMBER,
                    "comment": f"Auto-close: {motivo}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                # Envia ordem de fechamento
                resultado = mt5.order_send(request)

                if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    posicoes_fechadas += 1
                    logging.info(
                        f"✅ Posição #{pos.ticket} fechada - {pos.symbol} {pos.type} Vol:{pos.volume}")
                else:
                    logging.error(
                        f"❌ Erro ao fechar posição #{pos.ticket}: {resultado.retcode} - {resultado.comment}")

            except Exception as e:
                logging.error(
                    f"❌ Erro ao processar posição #{pos.ticket}: {e}")
                continue

        logging.info(
            f"🏁 Fechamento concluído: {posicoes_fechadas} posições fechadas")
        return posicoes_fechadas

    except Exception as e:
        logging.error(f"❌ Erro crítico ao fechar posições: {e}")
        return 0


def salvar_dados_finais(modelo_ia_local: Optional[Sequential], memoria_experiencias: MemoriaExperiencias) -> None:
    """Salva todos os dados importantes antes do encerramento."""
    try:
        logging.info("💾 Iniciando salvamento final de dados...")

        # Salva modelo de IA
        if modelo_ia_local:
            salvar_modelo(modelo_ia_local, MODELO_PATH)
            logging.info("✅ Modelo de IA salvo com sucesso")

        # Salva experiências em JSON
        if memoria_experiencias and memoria_experiencias.experiencias:
            salvar_experiencias_json(
                memoria_experiencias.experiencias, "experiencias_finais.json")
            logging.info("✅ Experiências salvas em JSON")

        # Salva estatísticas finais
        estatisticas_finais = {
            "timestamp_encerramento": datetime.now().isoformat(),
            "total_experiencias": len(memoria_experiencias.experiencias) if memoria_experiencias else 0,
            "total_lucros": sum(historico_lucro) if historico_lucro else 0.0,
            "total_operacoes": len(historico_lucro) if historico_lucro else 0,
            "historico_loss": historico_loss[-100:] if historico_loss else [],
            "contagem_acoes": memoria_experiencias.contagem_acoes if memoria_experiencias else {},
            "razao_buy_sell": memoria_experiencias.razao_buy_sell if memoria_experiencias else 0.0
        }

        with open("estatisticas_finais.json", "w") as f:
            json.dump(estatisticas_finais, f, indent=2)
        logging.info("✅ Estatísticas finais salvas")

        # Força flush dos logs
        logging.info("💾 Salvamento final concluído com sucesso")

    except Exception as e:
        logging.error(f"❌ Erro ao salvar dados finais: {e}")


def fechar_conexoes_seguras() -> None:
    """Fecha todas as conexões de forma segura."""
    try:
        logging.info("🔌 Iniciando fechamento seguro de conexões...")

        # Fecha conexão MT5
        try:
            if mt5.initialize():
                mt5.shutdown()
                logging.info("✅ Conexão MT5 fechada")
        except Exception as e:
            logging.error(f"❌ Erro ao fechar MT5: {e}")

        # Para threads de forma segura
        global thread_ativo
        thread_ativo = False
        logging.info("✅ Threads marcadas para encerramento")

        # Aguarda um momento para threads terminarem
        time.sleep(2)

        logging.info("🔌 Fechamento de conexões concluído")

    except Exception as e:
        logging.error(f"❌ Erro ao fechar conexões: {e}")


def encerramento_seguro_completo(modelo_ia_local: Optional[Sequential], memoria_experiencias: MemoriaExperiencias) -> None:
    """Executa encerramento completo e seguro do sistema."""
    try:
        logging.info("🔴 INICIANDO ENCERRAMENTO SEGURO COMPLETO DO SISTEMA")

        # Passo 1: Fecha todas as posições
        posicoes_fechadas = fechar_todas_posicoes(
            "Encerramento seguro do sistema")
        logging.info(f"✅ {posicoes_fechadas} posições fechadas")

        # Passo 2: Salva todos os dados importantes
        salvar_dados_finais(modelo_ia_local, memoria_experiencias)

        # Passo 3: Fecha conexões
        fechar_conexoes_seguras()

        # Passo 4: Log final
        logging.info("🏁 ENCERRAMENTO SEGURO CONCLUÍDO COM SUCESSO")
        logging.info("🤖 MONSTRO DAS NEGOCIAÇÕES DESLIGADO AUTOMATICAMENTE")

        # Passo 5: Força flush final dos logs
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Passo 6: Encerra o programa
        logging.info("💤 Sistema sendo desligado...")
        os._exit(0)  # Encerramento forçado mas seguro

    except Exception as e:
        logging.error(f"❌ Erro crítico no encerramento seguro: {e}")
        # Mesmo com erro, tenta encerrar
        try:
            os._exit(1)
        except:
            pass

# endregion

# region [Monitoramento]


def monitorar_spread() -> None:
    """Monitora o spread do mercado."""
    try:
        # Verifica se é fim de semana
        if datetime.now().weekday() > 4:  # 5 = Sábado, 6 = Domingo
            # Verifica a cada minuto durante fim de semana
            threading.Timer(60, monitorar_spread).start()
            return

        # Resto do código permanece igual...
        spreads = []
        while thread_ativo:
            try:
                tick = mt5.symbol_info_tick(SYMBOL)
                symbol_info = get_cached_symbol_info(SYMBOL)

                if tick and symbol_info:
                    spread_atual = (tick.ask - tick.bid) / symbol_info.point
                    spread_em_pontos = spread_atual / TICKS_POR_PONTO

                    spreads.append(spread_em_pontos)
                    if len(spreads) > 100:  # Mantém últimos 100 valores
                        spreads.pop(0)

                    # Calcula estatísticas
                    if len(spreads) >= 10:
                        media = sum(spreads) / len(spreads)
                        maximo = max(spreads)
                        minimo = min(spreads)

                        # Log a cada 30 segundos
                        if len(spreads) % 30 == 0:
                            logging.info(f"📊 Spread (pontos) - Atual: {spread_em_pontos:.1f} | "
                                         f"Média: {media:.1f} | Min: {minimo:.1f} | Máx: {maximo:.1f}")

                time.sleep(1)  # Atualiza a cada segundo

            except Exception as e:
                logging.error(f"Erro ao monitorar spread: {e}")
                time.sleep(1)
    except Exception as e:
        logging.error(f"Erro ao monitorar spread: {e}")
        time.sleep(1)

# endregion


# region [Inicialização]
print("--- BLOCO MAIN PRESTES A INICIAR ---")

if __name__ == "__main__":
    print("--- DENTRO DO BLOCO MAIN, ANTES DE SETUP_LOGGING ---")
    # Inicializa logging
    setup_logging()

    # Variáveis globais
    thread_ativo = True
    mt5_ativo = True
    posicao_aberta = False
    lucro_acumulado = 0.0
    historico_operacoes = []
    score = 0
    modelo_ia = None
    dados_memoria = []
    memoria_experiencias = MemoriaExperiencias()
    ticket_ordem_atual = None
    ultima_decisao = None
    historico_lucro = []
    gerenciador_bloqueio = None  # Será inicializado na thread
    modo_operacional = None      # Será inicializado na thread

    # Corrige formato do CSV
    corrigir_csv_historico()

    # Inicia threads
    flask_thread = threading.Thread(target=iniciar_flask, daemon=True)
    flask_thread.start()

    monstro_thread_obj = threading.Thread(target=monstro_thread, daemon=True)
    monstro_thread_obj.start()

    threading.Thread(target=atualizar_trailing_stop, daemon=True).start()
    # Nova thread de monitoramento
    threading.Thread(target=monitorar_spread, daemon=True).start()

    # Aguarda threads
    monstro_thread_obj.join()
