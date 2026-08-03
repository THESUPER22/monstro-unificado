# âœ… MONSTRO UNIFICADO V22 - COMPLETO E FUNCIONAL COM MELHORIAS
# Inclui: IA contÃ­nua com Keras, entropia do book, painel web, score,
# logs e aprendizado real
#
# ðŸš€ MELHORIAS IMPLEMENTADAS (+10% EFICÃCIA TOTAL):
# âœ… 1. TRAILING STOP INTELIGENTE (+3% eficÃ¡cia)
# âœ… 2. BALANCEAMENTO BUY/SELL (+2% eficÃ¡cia)
# âœ… 3. MODOS DE MERCADO SIMPLIFICADOS (+2% eficÃ¡cia)
# âœ… 4. CIRCUIT BREAKERS ESSENCIAIS (+1.5% eficÃ¡cia)
# âœ… 5. SAÃDA INTELIGENTE DE POSIÃ‡ÃƒO (+1.5% eficÃ¡cia)

import collections
import glob
import json
# region [Imports]
# Bibliotecas padrÃ£o
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

# Silencia logs verbosos do TensorFlow (C++). PRECISA ser definido ANTES de importar o TF.
# '3' = sÃ³ FATAL (esconde a mensagem repetida "NodeDef ... use_unbounded_threadpool").
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
import warnings

# Warnings benignos e repetitivos das libs (sklearn feature names, TF eager) â€” nÃ£o afetam o robÃ´.
warnings.filterwarnings('ignore', category=UserWarning)
# Deep Learning
import tensorflow as tf
from flask import Flask, jsonify, request
from scipy.stats import entropy
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from tenacity import retry, stop_after_attempt, wait_exponential
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam

import sentinela_fluxo
from dashboard_routes import dashboard_bp, register_main_module
from diagnostico_monstro import checar_arquivos_essenciais

# Reduz warnings do TensorFlow
tf.config.experimental.enable_op_determinism()
# CORREÃ‡ÃƒO CRÃTICA (C6): Adiciona semente global para resolver o erro de determinismo e permitir o treinamento.
tf.random.set_seed(42)

# TF_CPP_MIN_LOG_LEVEL jÃ¡ definido ANTES do import (acima). ReforÃ§a o logger Python do TF.
tf.get_logger().setLevel('ERROR')
# (Book nativo: a correÃ§Ã£o de timestamp do CSV do EA foi removida â€” nÃ£o hÃ¡ mais CSV)


# ===== CONTROLE DE APRENDIZADO FORÃ‡ADO =====
CONTADOR_OPERACOES_REJEITADAS = 0
LIMITE_REJEICOES_PARA_APRENDIZADO = 20  # Restaurado para 20 (fim do modo aprendizado temporÃ¡rio)
MODO_APRENDIZADO_FORCADO = False
# Limite diÃ¡rio de operaÃ§Ãµes forÃ§adas â€” evita contaminar modelo com trades ruins
FORCADOS_HOJE = 0
FORCADOS_DATA = None
MAX_FORCADOS_DIA = 3  # MÃ¡ximo 3 operaÃ§Ãµes forÃ§adas por dia

# ===== CLASSES PARA MELHORIAS IMPLEMENTADAS =====


class VolumeAdaptativo:
    """ðŸ“Š Calcula um volume mÃ­nimo para operar de forma adaptativa."""

    def __init__(self, janela_minutos=15, percentual_da_media=0.8):
        self.janela_segundos = janela_minutos * 60
        self.percentual_da_media = percentual_da_media
        # Deque armazena (timestamp, volume)
        self.historico_volumes = collections.deque()
        self.volume_minimo_adaptativo = 500  # Valor inicial padrÃ£o (WDO)

    def adicionar_volume_atual(self, volume_total: float):
        """Adiciona o volume total do book ao histÃ³rico."""
        agora = time.time()
        self.historico_volumes.append((agora, volume_total))
        self._limpar_historico_antigo(agora)
        self._calcular_novo_minimo()

    def _limpar_historico_antigo(self, timestamp_atual):
        """Remove dados mais antigos que a janela de tempo definida."""
        while self.historico_volumes:
            if timestamp_atual - self.historico_volumes[0][0] > self.janela_segundos:
                self.historico_volumes.popleft()
            else:
                break

    def _calcular_novo_minimo(self):
        """Calcula o novo volume mÃ­nimo com base na mÃ©dia do histÃ³rico."""
        if not self.historico_volumes:
            return

        volumes_na_janela = [vol for ts, vol in self.historico_volumes]
        media_volume = sum(volumes_na_janela) / len(volumes_na_janela)

        # O novo mÃ­nimo Ã© um percentual da mÃ©dia
        self.volume_minimo_adaptativo = media_volume * self.percentual_da_media

        # Garante um piso mÃ­nimo para nÃ£o operar com volume muito baixo
        piso_absoluto = 500
        self.volume_minimo_adaptativo = max(
            self.volume_minimo_adaptativo, piso_absoluto)

    def pode_operar(self, volume_atual: float) -> bool:
        """Verifica se o volume atual atende ao mÃ­nimo adaptativo."""
        return volume_atual >= self.volume_minimo_adaptativo


# ConfiguraÃ§Ã£o TensorFlow
tf.config.run_functions_eagerly(True)

# endregion

# ========== MELHORIA 1: TRAILING STOP INTELIGENTE (+3% EFICÃCIA) ==========


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
        """Inicia o trailing stop para uma posiÃ§Ã£o."""
        self.posicao_ativa = ticket
        self.preco_entrada = preco_entrada
        self.melhor_preco = preco_entrada
        self.trailing_ativo = False
        self.lucro_travado = False
        self.sl_original = sl_original

    def atualizar_trailing(self, preco_atual: float, tipo_posicao: str) -> Optional[float]:
        """Atualiza o trailing stop e retorna novo SL se necessÃ¡rio."""
        if not self.posicao_ativa:
            return None

        lucro_pontos = 0.0
        if tipo_posicao == "BUY":
            lucro_pontos = (preco_atual - self.preco_entrada) / \
                TICK_SIZE  # TICK_SIZE WDO
            if preco_atual > self.melhor_preco:
                self.melhor_preco = preco_atual
        else:  # SELL
            lucro_pontos = (self.preco_entrada - preco_atual) / \
                TICK_SIZE  # TICK_SIZE WDO
            if preco_atual < self.melhor_preco:
                self.melhor_preco = preco_atual

        # Ativa trailing apÃ³s atingir gatilho (20 pontos WDO)
        if lucro_pontos >= 20 and not self.trailing_ativo:
            self.trailing_ativo = True
            logging.info(
                f"ðŸŽ¯ Trailing stop ativado! Lucro: {lucro_pontos:.1f} pontos")

        # Trava 70% do lucro quando > 20 pontos
        if lucro_pontos >= 20 and not self.lucro_travado:
            self.lucro_travado = True
            if tipo_posicao == "BUY":
                novo_sl = self.preco_entrada + (lucro_pontos * 0.7 * TICK_SIZE)
            else:
                novo_sl = self.preco_entrada - (lucro_pontos * 0.7 * TICK_SIZE)
            logging.info(f"ðŸ”’ Lucro travado em 70%! Novo SL: {novo_sl}")
            return novo_sl

        # Trailing normal (10 pontos de distÃ¢ncia)
        if self.trailing_ativo:
            if tipo_posicao == "BUY":
                novo_sl = self.melhor_preco - (10 * TICK_SIZE)  # 10 pontos WDO
                if novo_sl > self.sl_original:
                    return novo_sl
            else:
                novo_sl = self.melhor_preco + (10 * TICK_SIZE)  # 10 pontos WDO
                if novo_sl < self.sl_original:
                    return novo_sl

        return None

    def finalizar_trailing(self):
        """Finaliza o trailing stop."""
        self.posicao_ativa = None
        self.trailing_ativo = False
        self.lucro_travado = False

# endregion


# region [ConfiguraÃ§Ãµes de Bloqueio]
MAX_LOSSES_SEQUENCIA = 3     # MÃ¡ximo de losses seguidos no mesmo lado
CICLOS_BLOQUEIO = 5         # NÃºmero de ciclos que o lado fica bloqueado
MIN_LUCRO_DESBLOQUEIO = 0.0  # Lucro mÃ­nimo para desbloquear lado antes do tempo
# endregion

# region [SeleÃ§Ã£o DinÃ¢mica do Contrato]


def get_front_month_symbol_dynamic(prefix="WDO") -> str:
    """Busca no MT5 todos os contratos prefixados por WDO, filtra por trade_mode FULL
       e retorna aquele com expiraÃ§Ã£o mais prÃ³xima no futuro."""
    symbols = mt5.symbols_get()  # lista de todos sÃ­mbolos do terminal
    agora_ts = datetime.now().timestamp()
    candidatas = []
    for s in symbols:
        if re.fullmatch(rf"{prefix}[A-Z]\d{{2}}", s.name) and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            exp_ts = getattr(s, 'expiration_time', None)
            if exp_ts and exp_ts > agora_ts:
                candidatas.append(s)
    if not candidatas:
        logging.error(
            f"âŒ Nenhum contrato mensal {prefix}* ativo encontrado. Usando {prefix}$ como fallback.")
        return f"{prefix}$"
    # escolhe o que vence primeiro
    front = min(candidatas, key=lambda s: s.expiration_time)
    logging.info(
        f"âœ… Contrato dinÃ¢mico selecionado: {front.name} (venc.: {datetime.fromtimestamp(front.expiration_time)})")
    return front.name
# endregion

# region [Classes]


class GerenciadorBloqueio:
    """Gerencia o bloqueio de lados apÃ³s sequÃªncia de prejuÃ­zos."""

    def __init__(self):
        self.historico_acoes = []  # Lista de tuplas (acao, lucro)
        # Ciclos restantes de bloqueio
        self.bloqueio_lado = {"BUY": 0, "SELL": 0}
        self.ultima_acao = None
        self.losses_sequencia = {"BUY": 0, "SELL": 0}

    def registrar_operacao(self, acao: str, lucro: float) -> None:
        """Registra uma operaÃ§Ã£o e atualiza contadores."""
        # SÃ³ processa aÃ§Ãµes vÃ¡lidas de trading
        if acao not in ["BUY", "SELL"]:
            logging.debug(
                f"Ignorando registro de operaÃ§Ã£o para aÃ§Ã£o invÃ¡lida: {acao}")
            return

        self.historico_acoes.append((acao, lucro))
        if len(self.historico_acoes) > 10:  # MantÃ©m histÃ³rico limitado
            self.historico_acoes.pop(0)

        # Atualiza contagem de losses em sequÃªncia - MAIS AGRESSIVO
        # SÃ³ conta como loss se for prejuÃ­zo significativo (maior que 25 reais)
        if acao in ["BUY", "SELL"] and lucro < -25.0:
            self.losses_sequencia[acao] += 1
            # Verifica se atingiu limite de losses seguidos
            if self.losses_sequencia[acao] >= MAX_LOSSES_SEQUENCIA:
                self.bloquear_lado(acao)
                logging.warning(
                    f"ðŸš« Bloqueando lado {acao} por {CICLOS_BLOQUEIO} ciclos apÃ³s {MAX_LOSSES_SEQUENCIA} losses seguidos")
        else:
            # Reseta contador de losses se teve lucro OU prejuÃ­zo pequeno
            self.losses_sequencia[acao] = max(
                0, self.losses_sequencia[acao] - 1)  # Decrementa gradualmente
            # Verifica se pode desbloquear por lucro (critÃ©rio mais flexÃ­vel)
            if lucro >= MIN_LUCRO_DESBLOQUEIO and self.bloqueio_lado[acao] > 0:
                # Reduz bloqueio gradualmente
                self.bloqueio_lado[acao] = max(0, self.bloqueio_lado[acao] - 1)
                logging.info(
                    f"âœ… Reduzindo bloqueio do lado {acao} por resultado nÃ£o negativo")

        self.ultima_acao = acao

    def bloquear_lado(self, lado: str) -> None:
        """Bloqueia um lado por N ciclos."""
        if lado in ["BUY", "SELL"]:
            self.bloqueio_lado[lado] = CICLOS_BLOQUEIO
        else:
            logging.debug(f"Tentativa de bloquear lado invÃ¡lido: {lado}")

    def verificar_bloqueio(self, acao: str) -> bool:
        """Verifica se uma aÃ§Ã£o estÃ¡ bloqueada e atualiza contadores."""
        # SÃ³ verifica bloqueio para aÃ§Ãµes vÃ¡lidas de trading
        if acao not in ["BUY", "SELL"]:
            return False

        if self.bloqueio_lado[acao] > 0:
            self.bloqueio_lado[acao] -= 1
            return True
        return False

    def obter_acao_alternativa(self, acao_original: str) -> str:
        """Retorna a aÃ§Ã£o oposta quando hÃ¡ bloqueio."""
        if acao_original == "BUY":
            return "SELL"
        elif acao_original == "SELL":
            return "BUY"
        else:
            # Fallback para aÃ§Ã£o invÃ¡lida
            logging.warning(
                f"AÃ§Ã£o original invÃ¡lida para alternativa: {acao_original}")
            return "BUY"  # Default

    def get_status(self) -> dict:
        """Retorna status atual do gerenciador."""
        return {
            "bloqueios": self.bloqueio_lado.copy(),
            "losses_sequencia": self.losses_sequencia.copy(),
            "ultima_acao": self.ultima_acao
        }

# endregion


# region [ConfiguraÃ§Ãµes]
# ---- RESOLUÃ‡ÃƒO DE CAMINHOS (corrige PyInstaller vs script) ----
def _caminho_base():
    """Retorna o diretÃ³rio base para escrita de arquivos de dados.
       Prioriza o diretÃ³rio do script (C:\AIOFEN) mesmo no PyInstaller,
       onde o executÃ¡vel estÃ¡ em dist\MonstroDashboard\."""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            # Sobe de _internal para o diretorio do projeto
            pai = os.path.dirname(os.path.dirname(sys._MEIPASS))
            if os.path.basename(pai) == 'dist':
                pai = os.path.dirname(pai)
            if pai and os.path.isdir(pai) and os.path.exists(os.path.join(pai, 'monstro_unificado_v22.py')):
                return pai
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _caminho_dados(nome):
    """Retorna caminho absoluto para um arquivo de dados."""
    return os.path.join(_caminho_base(), nome)

# Carrega configuraÃ§Ã£o especÃ­fica do WDO
CONFIG_FILE = _caminho_dados("config.json")


def carregar_configuracao():
    """Carrega configuraÃ§Ã£o do arquivo JSON."""
    try:
        # utf-8-sig: tolera BOM (um BOM aqui fazia json.load falhar e o robo
        # rodava inteiro nos defaults: SL=5/TP=10/Magic=123457 em vez do config real)
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"âŒ Erro ao carregar configuraÃ§Ã£o: {e}")
        return {}


# Carrega configuraÃ§Ã£o
config = carregar_configuracao()

# Cache TTL e configuraÃ§Ãµes de retry
CACHE_TTL = 1  # segundos
MAX_RETRY_ATTEMPTS = 5  # Aumentado para mais tentativas
RETRY_WAIT_MULTIPLIER = 2  # segundos - Aumentado o tempo entre tentativas

# region [Cache e Retry]


@lru_cache(maxsize=128)
def get_cached_symbol_info(symbol: str) -> Optional[Any]:
    """Cache para informaÃ§Ãµes do sÃ­mbolo."""
    return mt5.symbol_info(symbol)


def reconectar_mt5() -> bool:
    """Tenta reconectar ao MetaTrader 5."""
    try:
        if mt5.initialize():
            logging.info("âœ… Reconectado ao MetaTrader 5")
            return True
        else:
            logging.error(f"âŒ Erro ao reconectar: {mt5.last_error()}")
            return False
    except Exception as e:
        logging.error(f"âŒ Erro na reconexÃ£o: {e}")
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
            logging.warning("âš ï¸ Book vazio ou nulo - tentando reconexÃ£o")
            if reconectar_mt5():
                result = mt5.market_book_get(symbol)

        return result
    except Exception as e:
        logging.error(f"âŒ Erro ao obter book: {e}")
        raise Exception("Falha ao obter market book")


@retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
       wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER))
def retry_positions_get(symbol: str = None) -> Optional[Any]:
    """Tenta obter posiÃ§Ãµes com retry em caso de falha."""
    return mt5.positions_get(symbol=symbol)

# endregion


# region [ConfiguraÃ§Ãµes]
# Paths e arquivos - ADAPTADO PARA WDO
MT5_PATH = config.get("geral", {}).get(
    "mt5_path", r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe")
SYMBOL = None  # SerÃ¡ definido apÃ³s inicializar o MT5
SYMBOL_DOL = None  # DÃ³lar Cheio (DOL) â€” referÃªncia de fluxo institucional
TIMEFRAME = mt5.TIMEFRAME_M1

HISTORICO_CSV = config.get("aprendizado", {}).get(
    "historico_csv", _caminho_dados("historico_contexto_wdo.csv"))
MODELO_PATH = config.get("aprendizado", {}).get(
    "modelo_path", _caminho_dados("modelo_monstro_wdo.h5"))
LOG_FILE = _caminho_dados("monstro_wdo.log")

# ConfiguraÃ§Ãµes Web
PORT = config.get("web_dashboard", {}).get("port", 5002)
DEBUG = config.get("web_dashboard", {}).get("debug", True)

# ConfiguraÃ§Ãµes Trading - ADAPTADO PARA WDO
MAGIC_NUMBER = config.get("geral", {}).get("magic_number", 123457)
# Volume mÃ­nimo REAL para considerar nÃ­vel vÃ¡lido no book (WDO tem menos volume)
VOLUME_MINIMO = 50
# Atualizado para 22 features (10 originais + 8 profundidade + 4 ptax/payroll)
N_FEATURES = 22
DEVIATION = config.get("geral", {}).get("deviation", 20)

# ConfiguraÃ§Ãµes B3 - MINI DÃ“LAR (WDO)
TICK_SIZE = config.get("contrato", {}).get(
    "tick_size", 0.5)           # Tamanho do tick WDO
TICKS_POR_PONTO = config.get("contrato", {}).get(
    "ticks_por_ponto", 1000)    # WDO: 1 ponto = 1000 ticks
# Volume padrÃ£o (1 contrato WDO)
VOLUME_PADRAO = config.get("volume_padrao", 1.0)
HORARIO_PREGAO = config.get("horarios", {}).get("pregao", "09:00")
HORARIO_LIMITE_ORDENS = config.get(
    "horarios", {}).get("limite_ordens", "17:30")
HORARIO_ENCERRAMENTO = config.get("horarios", {}).get("encerramento", "17:35")
HORARIO_AFTER = config.get("horarios", {}).get("after_market", "17:40")
HORARIO_AJUSTE = "23:59"  # HorÃ¡rio do ajuste (ajustado para testes)
DIGITS_INDICE = config.get("contrato", {}).get(
    "digits_indice", 0)         # Casas decimais do Mini Ãndice

# Limites de distÃ¢ncia em ticks e pontos - ADAPTADO PARA WDO
MIN_TICKS = 500             # 1 ponto WDO = 500 ticks
MAX_TICKS = 5000            # 10 pontos WDO = 5000 ticks (TP dinÃ¢mico)
MAX_DISTANCIA_SL_PONTOS = config.get(
    "sl_points", 5)      # 5 pontos WDO
MAX_DISTANCIA_TP_PONTOS = config.get(
    "tp_points", 10)     # 10 pontos WDO (TP dinÃ¢mico)

# Trailing Stop (em pontos) - ADAPTADO PARA WDO
TRAILING_ATIVO = config.get("trailing_stop", {}).get("ativo", True)
TRAILING_INTERVALO = config.get(
    "trailing_stop", {}).get("intervalo_segundos", 5)
# NOTA: TRAILING_GATILHO e TRAILING_DISTANCIA sÃ£o definidos em linha ~964 (apÃ³s melhorias)
# Os valores do config.json sÃ£o sobrescritos pelos valores ajustados manualmente

# Stop Loss e Take Profit (em pontos) - CONFIGURAÃ‡ÃƒO WDO (REFATORADO)
# 5 pontos WDO = 5000 ticks (SL como rede de seguranÃ§a)
SL_POINTS = config.get("sl_points", 5)
# 10 pontos WDO = 10000 ticks (TP dinÃ¢mico - Keras decide saÃ­da)
TP_POINTS = config.get("tp_points", 10)

# ========================================================================
# ðŸŽ¯ FILTRO SNIPER DE ELITE (BOOK NATIVO MT5) - AJUSTE FÃCIL AQUI
# ------------------------------------------------------------------------
# Estes 2 valores controlam quando o robÃ´ "acorda" para operar.
# Migrados do EA MQL5 para o Python (arquitetura nativa, sem CSV/EA).
#   SNIPER_VOLUME_MIN : volume TOTAL somado (bid+ask) nos 10 nÃ­veis do book
#                       necessÃ¡rio para o robÃ´ considerar operar (big players).
#   SNIPER_RATIO_MIN  : desequilÃ­brio mÃ­nimo entre os lados (um lado precisa
#                       ter pelo menos este mÃºltiplo do volume do outro).
# Basta alterar os nÃºmeros abaixo e reiniciar o robÃ´ â€” sem recompilar EA.
# AJUSTADO PARA WDO (Mini DÃ³lar): thresholds 3-5x menores que WIN (Mini Ãndice)
# ========================================================================
SNIPER_VOLUME_MIN = config.get("sniper_volume_min", 800)
SNIPER_RATIO_MIN = config.get("sniper_ratio_min", 1.5)  # Restaurado para 1.5 (fim do modo aprendizado temporÃ¡rio)

# ========================================================================
# ðŸ”‡ CONTROLE DE VERBOSIDADE DOS LOGS (NÃƒO afeta a velocidade/decisÃ£o do robÃ´!)
# O robÃ´ monitora e decide sempre no ritmo mÃ¡ximo (1-5s). Isto controla apenas
# a FREQUÃŠNCIA de ESCRITA no arquivo de log, para ficar legÃ­vel (~60 linhas/hora
# em standby). Dicts mutÃ¡veis = nÃ£o precisam de 'global' nas funÃ§Ãµes.
# ========================================================================
_veto_estado = {'ultimo_log': 0.0}
VETO_LOG_INTERVALO_S = 60   # loga o veto no mÃ¡ximo 1x a cada 60s
_log_estado = {'ultimo_pulso': 0.0, 'ultimo_heartbeat': 0.0}
PULSO_LOG_INTERVALO_S = 60      # pulso de mercado (ðŸ“Š) 1x a cada 60s em standby
HEARTBEAT_LOG_INTERVALO_S = 15  # heartbeat da posiÃ§Ã£o (ðŸ’“) 1x a cada 15s operando
_throttle_estado = {}


def _log_periodico(chave: str, intervalo_s: float) -> bool:
    """Retorna True no mÃ¡ximo 1x a cada intervalo_s para a 'chave'. Controla apenas
    a FREQUÃŠNCIA de logs â€” NÃƒO altera o processamento/decisÃ£o do robÃ´."""
    agora = time.time()
    if agora - _throttle_estado.get(chave, 0.0) >= intervalo_s:
        _throttle_estado[chave] = agora
        return True
    return False

# Circuit Breakers - ADAPTADO PARA WDO
MAX_LOSS_DIARIO = config.get("risk_management", {}).get(
    "max_loss_diario", -500.0)   # Limite de perda diÃ¡ria em reais
MAX_DRAWDOWN = config.get("risk_management", {}).get(
    "max_drawdown", -250.0)      # Limite de drawdown por operaÃ§Ã£o em reais
# Spread mÃ¡ximo em pontos WDO
MAX_SPREAD = config.get("max_spread", 5)
MIN_TICKS_VALIDOS = 10      # MÃ­nimo de ticks vÃ¡lidos WDO
# Volume mÃ­nimo no book WDO - FILTRO ULTRA SELETIVO
# Aumentado para 200cc para SEGUIR BIG PLAYERS - mÃ¡xima acertividade
MIN_VOLUME_BOOK = config.get("min_volume_book", 200)

# ConfiguraÃ§Ãµes de Aprendizado
MIN_EXPERIENCIAS_TREINO = 3    # MÃ­nimo de experiÃªncias para comeÃ§ar treino
MAX_EXPERIENCIAS_MEMORIA = 1000  # MÃ¡ximo de experiÃªncias na memÃ³ria
EPOCHS_TREINO = 3               # NÃºmero de Ã©pocas por treino
BATCH_SIZE = 32                 # Tamanho do batch de treino
MIN_DELTA_LOSS = 0.001         # MÃ­nima melhoria na loss para continuar
PATIENCE_EARLY_STOP = 3        # PaciÃªncia para early stopping
DECAY_MEIA_VIDA = 12           # Meia-vida do decay em horas
INTERVALO_REPLAY = 60          # Intervalo em minutos para replay
PESO_REPLAY = 0.3              # Peso das experiÃªncias no replay
JANELA_CONSISTENCIA = 5        # Janela para calcular consistÃªncia

# Arquivos de dados (HISTORICO_CSV jÃ¡ definido acima via config)
EXPERIENCIAS_JSON = _caminho_dados("experiencias_wdo.json")
DECISIONS_CSV = _caminho_dados("decisions_wdo.csv")
MULTITF_CSV = _caminho_dados("historico_multitf.csv")

# ========== FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR ==========


class BloqueadorContexto:
    """Sistema de bloqueio de contextos perdedores baseado em experiÃªncias passadas."""

    def __init__(self):
        # {hash_coeado_ate''losses': count, 'bloqueado_ate': timestamp}}
        self.contextos_bloqueados = {}
        self.max_losses_contexto = 3  # MÃ¡ximo de losses no mesmo contexto
        self.tempo_bloqueio = 3600  # 1 hora de bloqueio

    def _hash_contexto(self, contexto: dict) -> str:
        """Cria hash Ãºnico do contexto para identificaÃ§Ã£o."""
        # Agrupa por faixas para criar contextos similares
        hora = datetime.now().hour
        faixa_horario = f"{hora//2*2:02d}-{(hora//2*2)+1:02d}"  # Faixas de 2h

        volatilidade_faixa = "baixa" if contexto.get(
            'volatility', 0) < 50 else "alta"
        rsi_faixa = "baixo" if contexto.get(
            'rsi_14', 50) < 40 else "alto" if contexto.get('rsi_14', 50) > 60 else "neutro"
        candle_type = contexto.get('candle_type', 'unknown')

        # PressÃ£o do book
        bid_qty = contexto.get('bid_qty', 0)
        ask_qty = contexto.get('ask_qty', 0)
        ratio = bid_qty / (ask_qty + 1)  # +1 para evitar divisÃ£o por zero
        book_pressure = "compra" if ratio > 1.5 else "venda" if ratio < 0.7 else "neutro"

        return f"{faixa_horario}_{volatilidade_faixa}_{rsi_faixa}_{candle_type}_{book_pressure}"

    def registrar_loss(self, contexto: dict):
        """Registra um loss em determinado contexto."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx not in self.contextos_bloqueados:
            self.contextos_bloqueados[hash_ctx] = {
                'losses': 0, 'bloqueado_ate': 0}

        self.contextos_bloqueados[hash_ctx]['losses'] += 1

        # Se atingiu limite, bloqueia por tempo determinado
        if self.contextos_bloqueados[hash_ctx]['losses'] >= self.max_losses_contexto:
            self.contextos_bloqueados[hash_ctx]['bloqueado_ate'] = time.time(
            ) + self.tempo_bloqueio
            logging.warning(
                f"ðŸš« CONTEXTO BLOQUEADO: {hash_ctx} - {self.max_losses_contexto} losses consecutivos")

    def contexto_bloqueado(self, contexto: dict) -> bool:
        """Verifica se contexto estÃ¡ bloqueado."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx not in self.contextos_bloqueados:
            return False

        ctx_data = self.contextos_bloqueados[hash_ctx]

        # Verifica se ainda estÃ¡ no perÃ­odo de bloqueio
        if ctx_data['bloqueado_ate'] > time.time():
            tempo_restante = int(ctx_data['bloqueado_ate'] - time.time())
            logging.info(
                f"â³ Contexto {hash_ctx} bloqueado por mais {tempo_restante}s")
            return True

        # Se passou o tempo, reseta o contador
        if ctx_data['bloqueado_ate'] > 0 and ctx_data['bloqueado_ate'] <= time.time():
            self.contextos_bloqueados[hash_ctx] = {
                'losses': 0, 'bloqueado_ate': 0}
            logging.info(f"âœ… Contexto {hash_ctx} desbloqueado")

        return False

    def registrar_win(self, contexto: dict):
        """Registra um win - reduz contador de losses do contexto."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx in self.contextos_bloqueados:
            self.contextos_bloqueados[hash_ctx]['losses'] = max(
                0, self.contextos_bloqueados[hash_ctx]['losses'] - 1)
            if self.contextos_bloqueados[hash_ctx]['losses'] == 0:
                self.contextos_bloqueados[hash_ctx]['bloqueado_ate'] = 0
                logging.info(f"âœ… Contexto {hash_ctx} reabilitado apÃ³s win")

# ========== FASE 2: REPLAY DE EXPERIÃŠNCIAS ATIVO ==========


class ReplayExperiencias:
    """Sistema de consulta ativa de experiÃªncias passadas antes de operar."""

    def __init__(self):
        self.experiencias_cache = []
        self.ultimo_carregamento = 0
        self.cache_valido_por = 300  # 5 minutos

    def carregar_experiencias(self):
        """Carrega experiÃªncias do arquivo JSON."""
        try:
            if not os.path.exists(EXPERIENCIAS_JSON):
                return []

            # Verifica se precisa recarregar cache
            if time.time() - self.ultimo_carregamento < self.cache_valido_por:
                return self.experiencias_cache

            with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
                experiencias = json.load(f)

            # Filtra apenas experiÃªncias dos Ãºltimos 7 dias
            cutoff_time = datetime.now() - timedelta(days=7)
            experiencias_recentes = []

            for exp in experiencias:
                try:
                    timestamp = datetime.fromisoformat(
                        exp.get('timestamp', ''))
                    if timestamp > cutoff_time:
                        experiencias_recentes.append(exp)
                except:
                    continue

            self.experiencias_cache = experiencias_recentes
            self.ultimo_carregamento = time.time()

            logging.debug(
                f"ðŸ“š Carregadas {len(experiencias_recentes)} experiÃªncias recentes")
            return experiencias_recentes

        except Exception as e:
            logging.error(f"âŒ Erro ao carregar experiÃªncias: {e}")
            return []

    def calcular_expectativa_contexto(self, contexto_atual: dict, acao_proposta: str) -> dict:
        """Calcula expectativa matemÃ¡tica para contexto similar."""
        experiencias = self.carregar_experiencias()

        if not experiencias:
            return {'expectativa': 0, 'trades_similares': 0, 'taxa_acerto': 0, 'lucro_medio': 0, 'perda_media': 0}

        # Busca experiÃªncias similares com critÃ©rios relaxados
        similares = []

        for exp in experiencias:
            if exp.get('acao') != acao_proposta:
                continue

            ctx = exp.get('contexto', {})
            similar = True

            # Volatilidade similar (Â±40% â€” relaxado de 20%)
            vol_atual = contexto_atual.get('volatility', 0)
            vol_exp = ctx.get('volatility', 0)
            if vol_atual > 0 and abs(vol_atual - vol_exp) > vol_atual * 0.4:
                similar = False

            # RSI similar (Â±25 pontos â€” relaxado de 15)
            rsi_atual = contexto_atual.get('rsi_14', 50)
            rsi_exp = ctx.get('rsi_14', 50)
            if abs(rsi_atual - rsi_exp) > 25:
                similar = False

            # Candle: agrupa em alta/baixa/neutro (mais permissivo)
            candle_atual = contexto_atual.get('candle_type', '')
            candle_exp = ctx.get('candle_type', '')
            if candle_atual != candle_exp:
                tipos_alta = ['alta', 'marubozu_alta', 'upper_shadow_alta',
                              'lower_shadow_alta', 'hammer_alta']
                tipos_baixa = ['baixa', 'marubozu_baixa', 'lower_shadow_baixa',
                               'upper_shadow_baixa', 'hammer_baixa', 'shooting_star_baixa',
                               'shooting_star_alta']
                tipos_neutro = ['doji', 'doji_gravestone', 'doji_dragonfly',
                                'spinning_top_alta', 'spinning_top_baixa']

                def grupo(c):
                    if c in tipos_alta:
                        return 'alta'
                    if c in tipos_baixa:
                        return 'baixa'
                    return 'neutro'

                if grupo(candle_atual) != grupo(candle_exp):
                    similar = False

            if similar:
                similares.append(exp)

        if not similares:
            return {'expectativa': 0, 'trades_similares': 0, 'taxa_acerto': 0, 'lucro_medio': 0, 'perda_media': 0}

        # Calcula estatÃ­sticas
        lucros = [exp.get('lucro', 0) for exp in similares]
        wins = [l for l in lucros if l > 0]
        losses = [l for l in lucros if l < 0]

        taxa_acerto = len(wins) / len(lucros) if lucros else 0
        lucro_medio = sum(wins) / len(wins) if wins else 0
        perda_media = abs(sum(losses) / len(losses)) if losses else 0

        # Expectativa matemÃ¡tica
        expectativa = (taxa_acerto * lucro_medio) - \
            ((1 - taxa_acerto) * perda_media)

        resultado = {
            'expectativa': expectativa,
            'trades_similares': len(similares),
            'taxa_acerto': taxa_acerto * 100,
            'lucro_medio': lucro_medio,
            'perda_media': perda_media
        }

        logging.debug(
            f"ðŸ“Š Expectativa {acao_proposta}: {expectativa:.2f} | Similares: {len(similares)} | Taxa: {taxa_acerto*100:.1f}%")

        return resultado


# ========== INSTÃ‚NCIAS GLOBAIS â€” definidas aqui para ficarem disponÃ­veis em todo o mÃ³dulo ==========
bloqueador_contexto = BloqueadorContexto()
replay_experiencias = ReplayExperiencias()

# ========== SISTEMA DE VETO SIMPLES E DIRETO (BASEADO NA SUGESTÃƒO DA IA) ==========


def carregar_experiencias_simples():
    """Carrega experiÃªncias do JSON de forma simples."""
    if not os.path.exists(EXPERIENCIAS_JSON):
        return []
    try:
        with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def contexto_similar_simples(exp_contexto, contexto_atual):
    """Verifica se contextos sÃ£o similares usando critÃ©rios simples."""
    # Faixa horÃ¡ria (2h)
    hora_atual = datetime.now().hour
    faixa_atual = f"{hora_atual//2*2:02d}-{(hora_atual//2*2)+1:02d}"

    # Volatilidade
    vol_atual = "baixa" if contexto_atual.get('volatility', 0) < 50 else "alta"
    vol_exp = "baixa" if exp_contexto.get('volatility', 0) < 50 else "alta"

    # RSI
    rsi_atual = contexto_atual.get('rsi_14', 50)
    rsi_exp = exp_contexto.get('rsi_14', 50)
    rsi_similar = abs(rsi_atual - rsi_exp) <= 20  # Â±20 pontos

    # Candle type
    candle_atual = contexto_atual.get('candle_type', '')
    candle_exp = exp_contexto.get('candle_type', '')

    return vol_atual == vol_exp and rsi_similar and candle_atual == candle_exp


def calcular_expectativa_simples(experiencias):
    """Calcula expectativa matemÃ¡tica simples."""
    if len(experiencias) < 5:  # MÃ­nimo de dados
        return None

    ganhos = [e['lucro'] for e in experiencias if e['lucro'] > 0]
    perdas = [e['lucro'] for e in experiencias if e['lucro'] < 0]

    if not ganhos or not perdas:
        return None

    winrate = len(ganhos) / len(experiencias)
    avg_gain = sum(ganhos) / len(ganhos)
    avg_loss = abs(sum(perdas) / len(perdas))

    expectativa = (winrate * avg_gain) - ((1 - winrate) * avg_loss)
    return expectativa


def deve_operar_contexto(contexto_atual, acao_proposta, expectativa_minima=0):
    """VETO SIMPLES: Verifica se deve operar baseado no histÃ³rico."""
    experiencias = carregar_experiencias_simples()

    # Busca experiÃªncias similares com a mesma aÃ§Ã£o
    similares = []
    for exp in experiencias:
        if (exp.get('acao') == acao_proposta and
                contexto_similar_simples(exp.get('contexto', {}), contexto_atual)):
            similares.append(exp)

    expectativa = calcular_expectativa_simples(similares)

    if expectativa is None:
        return True, "Sem histÃ³rico suficiente"

    if expectativa <= expectativa_minima:
        return False, f"Expectativa negativa: {expectativa:.2f} (similares: {len(similares)})"

    return True, f"Expectativa positiva: {expectativa:.2f} (similares: {len(similares)})"


# Alias para compatibilidade â€” prever_acao chama deve_operar_contexto_simples
deve_operar_contexto_simples = deve_operar_contexto


# ConfiguraÃ§Ãµes de Stop Inteligente - VALORES ORIGINAIS RESTAURADOS
INVERSAO_SCORE_MIN = 0.3       # MÃ­nima variaÃ§Ã£o do score para considerar inversÃ£o
SCORE_LOCK_PROFIT = 0.5        # Score mÃ­nimo para ativar trava de lucro
TEMPO_MIN_POSICAO = 30         # Tempo mÃ­nimo em segundos antes de considerar saÃ­da
INTERVALO_CHECK_SCORE = 5      # Intervalo em segundos para checar score
JANELA_SUAVIZACAO = 3         # Tamanho da janela para mÃ©dia mÃ³vel do score
THRESHOLD_INVERSAO_SCORE = -0.2  # Threshold para considerar inversÃ£o negativa

# ConfiguraÃ§Ãµes de Trading
MULTIPLICADOR_SL_ATR = 2.0  # SL = 2x ATR
MULTIPLICADOR_TP_ATR = 3.0  # TP = 3x ATR
PERIODO_ATR = 14           # PerÃ­odo para cÃ¡lculo do ATR

# Limites mÃ¡ximos de SL/TP em pontos - ADAPTADO PARA WDO
SL_MAX_POINTS = 5         # MÃ¡ximo SL em pontos WDO
TP_MAX_POINTS = 0         # SEM TP â€” saÃ­da dinÃ¢mica por Keras+Book

# ConfiguraÃ§Ãµes de Modos Situacionais - ADAPTADO PARA WDO
# ATR mÃ­nimo para operar â€” WDO opera com ATR 2-10 pontos (tick=0.5)
# Abaixo de 1.5 = mercado completamente lateral, sem oportunidade
THRESHOLD_ATR_BAIXO = 1.5
# Entropia mÃ­nima para operar â€” escala REAL (entropy log natural) 2.69-2.97
# FIX (01/08/2026): era 0.6 em escala [0,1], mas entropia real Ã© 2.7-3.0 -> modo lateral nunca ativava
THRESHOLD_ENTROPIA_BAIXA = 2.75
# Entropia alta para modo explosÃ£o - ULTRA SELETIVO (era 0.7, escala [0,1] -> explosÃ£o sempre ativa)
THRESHOLD_ENTROPIA_ALTA = 2.85
# MÃ­nimo crescimento de volume para modo explosÃ£o - MAIS EXIGENTE
MIN_VOLUME_CRESCIMENTO = 1.5
# MÃ¡ximo de losses seguidos antes de modo defesa
MAX_LOSSES_SEGUIDOS = 3   # Era 5 - reduzido para reagir mais rÃ¡pido
# Minutos em modo defesa apÃ³s atingir max losses
TEMPO_DEFESA = 10         # Era 15 - reduzido para nÃ£o travar demais
# RazÃ£o mÃ­nima entre bid/ask (WDO tem menos liquidez)
MIN_RATIO_BOOK = 0.03

# ConfiguraÃ§Ãµes de Bloqueio de Lado - VALORES ORIGINAIS RESTAURADOS
MAX_LOSSES_SEQUENCIA = 3     # MÃ¡ximo de losses seguidos no mesmo lado
CICLOS_BLOQUEIO = 5         # NÃºmero de ciclos que o lado fica bloqueado
MIN_LUCRO_DESBLOQUEIO = 0.0  # Lucro mÃ­nimo para desbloquear lado antes do tempo

# ========== CONFIGURAÃ‡Ã•ES MELHORIA 1: TRAILING STOP INTELIGENTE ==========
TRAILING_ATIVO = True
# pontos WDO â€” sÃ³ ativa apÃ³s lucro real (AJUSTE FINO: era 80, agora 5 para WDO)
TRAILING_GATILHO = 5
# pontos WDO â€” respira sem violinar (AJUSTE FINO: era 40, agora 2 para WDO)
TRAILING_DISTANCIA = 2
TRAILING_PERCENTUAL_TRAVA = 0.7  # Trava 70% do lucro quando > 5 pontos

# InstÃ¢ncia global do trailing stop
trailing_stop = None

# ========== MELHORIA 2: BALANCEAMENTO BUY/SELL (+2% EFICÃCIA) ==========


class BalanceadorOperacoes:
    """Gerencia o balanceamento entre operaÃ§Ãµes BUY e SELL."""

    def __init__(self):
        self.contador_buy = 0
        self.contador_sell = 0
        self.historico_operacoes = []

    def registrar_operacao(self, acao: str):
        """Registra uma operaÃ§Ã£o executada."""
        if acao == "BUY":
            self.contador_buy += 1
        elif acao == "SELL":
            self.contador_sell += 1

        self.historico_operacoes.append(acao)
        if len(self.historico_operacoes) > 50:  # MantÃ©m histÃ³rico limitado
            self.historico_operacoes.pop(0)

    def calcular_desbalanceamento(self) -> float:
        """Calcula o nÃ­vel de desbalanceamento atual."""
        total = self.contador_buy + self.contador_sell
        if total == 0:
            return 0.0
        return self.contador_buy / total

    def ajustar_threshold(self, threshold_original: float) -> float:
        """Ajusta o threshold baseado no desbalanceamento de forma mais agressiva."""
        desbalanceamento = self.calcular_desbalanceamento()
        total = self.contador_buy + self.contador_sell

        # NÃ£o ajusta se tiver poucas operaÃ§Ãµes
        if total < 5:
            return threshold_original

        # BALANCEAMENTO ULTRA AGRESSIVO
        # Se muito desbalanceado (>85%), ajuste extremo
        if desbalanceamento > 0.85:
            ajuste = 0.3  # Ajuste muito agressivo
            logging.info(
                f"ðŸš¨ Desbalanceamento crÃ­tico BUY: {desbalanceamento:.1%} - Ajuste extremo +{ajuste}")
            # Pode ir atÃ© 1.5 (quase impossÃ­vel BUY)
            return min(1.5, threshold_original + ajuste)
        elif desbalanceamento < 0.15:
            ajuste = -0.3  # Ajuste muito agressivo
            logging.info(
                f"ðŸš¨ Desbalanceamento crÃ­tico SELL: {desbalanceamento:.1%} - Ajuste extremo {ajuste}")
            # Pode ir atÃ© -0.5 (quase sempre BUY)
            return max(-0.5, threshold_original + ajuste)

        # Balanceamento agressivo normal
        elif desbalanceamento > 0.7:
            ajuste = 0.15  # Mais agressivo que antes
            return min(1.2, threshold_original + ajuste)
        elif desbalanceamento < 0.3:
            ajuste = -0.15  # Mais agressivo que antes
            return max(0.0, threshold_original + ajuste)

        return threshold_original

    def deve_forcar_operacao(self) -> tuple[bool, str]:
        """Verifica se deve forÃ§ar uma operaÃ§Ã£o especÃ­fica devido ao desbalanceamento extremo."""
        desbalanceamento = self.calcular_desbalanceamento()
        total = self.contador_buy + self.contador_sell

        if total < 10:  # Precisa de pelo menos 10 operaÃ§Ãµes para forÃ§ar
            return False, ""

        if desbalanceamento > 0.85:  # Mais de 85% BUY
            return True, "SELL"
        elif desbalanceamento < 0.15:  # Menos de 15% BUY (85% SELL)
            return True, "BUY"

        return False, ""

    def get_status(self) -> dict:
        """Retorna status do balanceamento."""
        total = self.contador_buy + self.contador_sell
        buy_pct = (self.contador_buy / total * 100) if total > 0 else 0
        sell_pct = (self.contador_sell / total * 100) if total > 0 else 0
        deve_forcar, acao_forcada = self.deve_forcar_operacao()

        return {
            "buy_count": self.contador_buy,
            "sell_count": self.contador_sell,
            "buy_percentage": buy_pct,
            "sell_percentage": sell_pct,
            "desbalanceamento": self.calcular_desbalanceamento(),
            "deve_forcar": deve_forcar,
            "acao_forcada": acao_forcada
        }


# ConfiguraÃ§Ãµes do balanceamento
BALANCEAMENTO_ATIVO = False  # DESATIVADO: causava deadlock (forÃ§a BUY com threshold=2.0 impossÃ­vel)
THRESHOLD_DESBALANCEAMENTO = 0.7  # 70% de um lado
AJUSTE_THRESHOLD_BALANCE = 0.05   # Ajuste no threshold quando desbalanceado

# InstÃ¢ncia global do balanceador
balanceador = None

# ========== MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS (+2% EFICÃCIA) ==========


class DetectorModoMercado:
    """Detecta e gerencia modos de mercado simplificados."""

    def __init__(self):
        self.modo_atual = "NORMAL"
        self.historico_atr = []
        self.historico_entropia = []

    def atualizar_indicadores(self, atr: float, entropia: float):
        """Atualiza indicadores para detecÃ§Ã£o de modo."""
        self.historico_atr.append(atr)
        self.historico_entropia.append(entropia)

        # MantÃ©m histÃ³rico limitado
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
        # WDO: ATR tÃ­pico 2-10 pontos. Abaixo de 2.0 = conservador.
        # FIX (01/08/2026): entropia em escala real (2.69-2.97), era 0.3 em [0,1] -> nunca ativava
        if atr_medio < 2.0 and entropia_media < 2.75:
            self.modo_atual = "CONSERVADOR"
        else:
            self.modo_atual = "NORMAL"

        return self.modo_atual

    def ajustar_parametros_trading(self, volume_base: float, sl_base: float, tp_base: float) -> tuple:
        """Ajusta parÃ¢metros de trading baseado no modo."""
        if self.modo_atual == "CONSERVADOR":
            volume_ajustado = volume_base * 0.5  # Volume reduzido 50%
            sl_ajustado = sl_base * 0.7         # SL menor 30%
            tp_ajustado = tp_base * 0.8         # TP menor 20%
            return volume_ajustado, sl_ajustado, tp_ajustado

        return volume_base, sl_base, tp_base


# ConfiguraÃ§Ãµes dos modos de mercado
# ATR mÃ­nimo para modo conservador (WDO: ATR tÃ­pico 2-10 pontos)
MODO_CONSERVADOR_ATR = 2.0
MODO_CONSERVADOR_ENTROPIA = 0.3  # Entropia baixa para modo conservador
VOLUME_CONSERVADOR_MULT = 0.5     # Volume reduzido em modo conservador
SL_CONSERVADOR_MULT = 0.7         # SL menor em modo conservador
TP_CONSERVADOR_MULT = 0.8         # TP menor em modo conservador

# InstÃ¢ncia global do detector de modo
detector_modo = None

# ========== MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS (+1.5% EFICÃCIA) ==========


class CircuitBreakerEssencial:
    """Implementa circuit breakers essenciais para proteÃ§Ã£o."""

    def __init__(self):
        self.losses_seguidos = 0
        self.loss_diario_atual = 0.0
        self.operacoes_hoje = []
        self.bloqueado = False
        self.motivo_bloqueio = ""

    def registrar_resultado(self, lucro: float):
        """Registra resultado de uma operaÃ§Ã£o."""
        hoje = datetime.now().date()
        self.operacoes_hoje.append((hoje, lucro))

        # Remove operaÃ§Ãµes de dias anteriores
        self.operacoes_hoje = [(data, valor) for data,
                               valor in self.operacoes_hoje if data == hoje]

        # Atualiza loss diÃ¡rio
        self.loss_diario_atual = sum(valor for _, valor in self.operacoes_hoje)

        # Atualiza losses seguidos
        if lucro < -25.0:  # Loss significativo (WDO)
            self.losses_seguidos += 1
        else:
            self.losses_seguidos = 0

        # LIMITE DIÃRIO REAL: Se atingiu -1000, DESLIGA O ROBÃ”
        if self.loss_diario_atual <= MAX_LOSS_DIARIO:
            self.bloqueado = True
            self.motivo_bloqueio = f"LIMITE DIÃRIO ATINGIDO: {self.loss_diario_atual:.2f} <= {MAX_LOSS_DIARIO}"
            logging.error(f"ðŸš¨ {self.motivo_bloqueio}")
            logging.error("ðŸ›‘ ROBÃ” SERÃ DESLIGADO AUTOMATICAMENTE!")

            # FIX (01/08/2026): era sys.exit() dentro de thread daemon -> so matava a thread,
            # dashboard e demais threads continuavam vivas (processo parecia ativo). Agora cria
            # parar.txt (caminho absoluto), que o loop principal detecta via verificar_parada_gracil
            # e executa o shutdown coordenado (fecha posicoes, salva modelo/experiencias, os._exit).
            try:
                with open(_caminho_dados("parar.txt"), 'w', encoding='utf-8') as f:
                    f.write(f"LIMITE DIARIO ATINGIDO: {self.loss_diario_atual:.2f}")
                logging.info("âœ… parar.txt criado - encerramento coordenado sera executado pelo loop principal")
            except Exception as e:
                logging.error(f"âŒ Erro ao criar parar.txt: {e}")

    def verificar_circuit_breakers(self, spread_atual: float) -> bool:
        """Verifica se algum circuit breaker foi ativado."""
        # CB1: 3 losses seguidos - TEMPORARIAMENTE DESABILITADO (30/07/2025)
        # MOTIVO: Permitir mais operaÃ§Ãµes para treinamento da IA
        # REATIVAR EM: 06/08/2025 (apÃ³s 1 semana de dados)
        # if self.losses_seguidos >= 3:
        #     self.bloqueado = True
        #     self.motivo_bloqueio = f"3 losses seguidos (atual: {self.losses_seguidos})"
        #     return True

        # CB2: Loss diÃ¡rio excessivo (WDO)
        if self.loss_diario_atual <= -1000.0:
            self.bloqueado = True
            self.motivo_bloqueio = f"Loss diÃ¡rio: R${self.loss_diario_atual:.2f}"
            return True

        # CB3: Spread muito alto (WDO)
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


# ConfiguraÃ§Ãµes dos circuit breakers
CIRCUIT_BREAKER_ATIVO = True
# Stop apÃ³s 3 losses seguidos - TEMPORARIAMENTE DESABILITADO
MAX_LOSSES_SEGUIDOS_CB = 3
SPREAD_MAXIMO_CB = 20        # Stop se spread > 20 pontos WDO
# Stop se perda diÃ¡ria > R$1000 (WDO)
LOSS_DIARIO_CB = -1000.0

# InstÃ¢ncia global do circuit breaker
circuit_breaker = None

# InstÃ¢ncia global do sistema de confluÃªncia
sistema_confluencia = None
confluencia_info_atual = None

# ========== NOVA MELHORIA: SISTEMA DE CONFLUÃŠNCIA (+4% EFICÃCIA) ==========


class SistemaConfluencia:
    """Sistema que sÃ³ opera quando mÃºltiplos sinais concordam - MÃXIMA EFICÃCIA."""

    def __init__(self):
        self.historico_confluencias = []
        self.stats_por_confluencia = {}

    def verificar_confluencia(self, contexto: Dict[str, Any], probabilidade_ia: float, acao_ia: str) -> Dict[str, Any]:
        """Verifica confluÃªncia de mÃºltiplos sinais tÃ©cnicos."""
        sinais_buy = []
        sinais_sell = []
        score_confluencia = 0

        # ===== SINAL 1: INTELIGÃŠNCIA ARTIFICIAL (Peso: 30) ==========
        if probabilidade_ia > 0.75:
            sinais_buy.append("IA_FORTE")
            score_confluencia += 30
        elif probabilidade_ia > 0.6:
            sinais_buy.append("IA_MEDIA")
            score_confluencia += 20
        elif probabilidade_ia < 0.25:
            sinais_sell.append("IA_FORTE")
            score_confluencia += 30
        elif probabilidade_ia < 0.4:
            sinais_sell.append("IA_MEDIA")
            score_confluencia += 20

        # ========== SINAL 2: BOOK DE OFERTAS DESEQUILIBRADO (Peso: 25) ==========
        bid_qty = contexto.get('bid_qty', 0)
        ask_qty = contexto.get('ask_qty', 0)

        if bid_qty > 0 and ask_qty > 0:
            ratio_book = bid_qty / ask_qty

            # LÃ“GICA CORRIGIDA: SEGUIR BIG PLAYERS NA MESMA DIREÃ‡ÃƒO
            if ratio_book > 1.3:  # Muito mais compradores (bid_qty > ask_qty)
                # BUY (big players comprando â†’ entrar junto na compra)
                sinais_buy.append("BOOK_DESEQUILIBRIO")
                score_confluencia += 25
            elif ratio_book > 1.15:  # Moderadamente mais compradores
                # BUY (pressÃ£o de compra moderada)
                sinais_buy.append("BOOK_LEVE")
                score_confluencia += 15
            # Muito mais vendedores (ask_qty > bid_qty)
            elif ratio_book < 0.77:
                # SELL (big players vendendo â†’ entrar junto na venda)
                sinais_sell.append("BOOK_DESEQUILIBRIO")
                score_confluencia += 25
            elif ratio_book < 0.87:  # Moderadamente mais vendedores
                # SELL (pressÃ£o de venda moderada)
                sinais_sell.append("BOOK_LEVE")
                score_confluencia += 15

        # ========== SINAL 3: RSI + ENTROPIA (Peso: 20) ==========
        rsi = contexto.get('rsi_14', 50)
        entropia = contexto.get('entropia_book', 1.0)

        # RSI oversold + alta entropia = sinal de compra
        if rsi < 35 and entropia > 2.0:
            sinais_buy.append("RSI_ENTROPIA")
            score_confluencia += 20
        elif rsi < 40 and entropia > 1.8:
            sinais_buy.append("RSI_ENTROPIA_LEVE")
            score_confluencia += 12

        # RSI overbought + alta entropia = sinal de venda
        if rsi > 65 and entropia > 2.0:
            sinais_sell.append("RSI_ENTROPIA")
            score_confluencia += 20
        elif rsi > 60 and entropia > 1.8:
            sinais_sell.append("RSI_ENTROPIA_LEVE")
            score_confluencia += 12

        # ========== SINAL 4: PADRÃƒO DE CANDLESTICK (Peso: 15) ==========
        candle_type = contexto.get('candle_type', '')

        # PadrÃµes de reversÃ£o de baixa (sinal de compra)
        padroes_compra = ['hammer_baixa', 'doji_baixa',
                          'spinning_top_baixa', 'lower_shadow_baixa']
        if candle_type in padroes_compra:
            sinais_buy.append("CANDLE_REVERSAO")
            score_confluencia += 15

        # PadrÃµes de reversÃ£o de alta (sinal de venda)
        padroes_venda = ['shooting_star_alta', 'doji_alta',
                         'spinning_top_alta', 'upper_shadow_alta']
        if candle_type in padroes_venda:
            sinais_sell.append("CANDLE_REVERSAO")
            score_confluencia += 15

        # PadrÃµes de continuaÃ§Ã£o
        if candle_type in ['marubozu_alta', 'alta'] and acao_ia == "BUY":
            sinais_buy.append("CANDLE_CONTINUACAO")
            score_confluencia += 10
        elif candle_type in ['marubozu_baixa', 'baixa'] and acao_ia == "SELL":
            sinais_sell.append("CANDLE_CONTINUACAO")
            score_confluencia += 10

        # ========== SINAL 5: VOLUME E VOLATILIDADE (Peso: 10) ==========
        volume_tick = contexto.get('volume_tick', 0)
        volatilidade = contexto.get('volatility', 0)

        # Volume alto + volatilidade alta = movimento forte
        if volume_tick > 20 and volatilidade > 60:
            if acao_ia == "BUY":
                sinais_buy.append("VOLUME_VOLATILIDADE")
            else:
                sinais_sell.append("VOLUME_VOLATILIDADE")
            score_confluencia += 10
        elif volume_tick > 10 and volatilidade > 50:
            if acao_ia == "BUY":
                sinais_buy.append("VOLUME_VOLATILIDADE_LEVE")
            else:
                sinais_sell.append("VOLUME_VOLATILIDADE_LEVE")
            score_confluencia += 5

        # ========== DECISÃƒO FINAL DE CONFLUÃŠNCIA (REFATORADO) ==========
        total_sinais_buy = len(sinais_buy)
        total_sinais_sell = len(sinais_sell)

        # ðŸŽ¯ REGRA 1: IA COM ALTA CONFIANÃ‡A (>80%) NÃƒO PODE SER INVERTIDA
        # NOTA: probabilidade_ia=0.0 (modelo nÃ£o treinado) NÃƒO Ã© confianÃ§a alta
        ia_confianca_alta = (probabilidade_ia > 0.8 or probabilidade_ia < 0.2) and probabilidade_ia != 0.0

        if ia_confianca_alta:
            # IA tem alta confianÃ§a - ConfluÃªncia sÃ³ pode CONFIRMAR, nÃ£o inverter
            if probabilidade_ia > 0.8:
                acao_confluencia = "BUY"
                confianca_confluencia = min(
                    probabilidade_ia + (score_confluencia / 200.0), 1.0)
                logging.debug(
                    f"ðŸ”’ IA ALTA CONFIANÃ‡A (BUY): {probabilidade_ia:.2f} - ConfluÃªncia nÃ£o pode inverter")
            else:  # probabilidade_ia < 0.2
                acao_confluencia = "SELL"
                confianca_confluencia = min(
                    (1 - probabilidade_ia) + (score_confluencia / 200.0), 1.0)
                logging.debug(
                    f"ðŸ”’ IA ALTA CONFIANÃ‡A (SELL): {1-probabilidade_ia:.2f} - ConfluÃªncia nÃ£o pode inverter")
        else:
            # ðŸŽ¯ REGRA 2: CONFLUÃŠNCIA EXIGE MÃNIMO 2 SINAIS TÃ‰CNICOS PARA VALIDAR ENTRADA
            if total_sinais_buy >= 2 and total_sinais_buy > total_sinais_sell:
                acao_confluencia = "BUY"
                confianca_confluencia = min(score_confluencia / 100.0, 1.0)
            elif total_sinais_sell >= 2 and total_sinais_sell > total_sinais_buy:
                acao_confluencia = "SELL"
                confianca_confluencia = min(score_confluencia / 100.0, 1.0)
            else:
                # FALLBACK: Menos de 2 sinais tÃ©cnicos - NÃƒO OPERAR
                acao_confluencia = "NADA"
                confianca_confluencia = 0.0
                logging.warning(
                    f"âš ï¸ CONFLUÃŠNCIA INSUFICIENTE: BUY={total_sinais_buy}, SELL={total_sinais_sell} (mÃ­nimo 2 sinais)")

        # Registra estatÃ­sticas
        confluencia_key = f"{total_sinais_buy}B_{total_sinais_sell}S"
        if confluencia_key not in self.stats_por_confluencia:
            self.stats_por_confluencia[confluencia_key] = {
                "total": 0, "acertos": 0}

        resultado = {
            "acao": acao_confluencia,
            "confianca": confianca_confluencia,
            "score": score_confluencia,
            "sinais_buy": sinais_buy,
            "sinais_sell": sinais_sell,
            "total_sinais_buy": total_sinais_buy,
            "total_sinais_sell": total_sinais_sell,
            "detalhes": f"BUY:{total_sinais_buy} SELL:{total_sinais_sell} Score:{score_confluencia}"
        }

        return resultado

    def registrar_resultado_confluencia(self, confluencia_info: Dict, lucro: float):
        """Registra resultado de uma operaÃ§Ã£o baseada em confluÃªncia."""
        if confluencia_info["acao"] in ["BUY", "SELL"]:
            key = f"{confluencia_info['total_sinais_buy']}B_{confluencia_info['total_sinais_sell']}S"

            if key in self.stats_por_confluencia:
                self.stats_por_confluencia[key]["total"] += 1
                if lucro > 0.0:  # CORREÃ‡ÃƒO C9: Conta apenas experiÃªncias lucrativas
                    self.stats_por_confluencia[key]["acertos"] += 1

    def get_stats_confluencia(self) -> Dict:
        """Retorna estatÃ­sticas de performance por tipo de confluÃªncia."""
        stats = {}
        for key, data in self.stats_por_confluencia.items():
            if data["total"] > 0:
                taxa_acerto = data["acertos"] / data["total"]
                stats[key] = {
                    "total_ops": data["total"],
                    "acertos": data["acertos"],
                    "taxa_acerto": taxa_acerto
                }
        return stats


# ========== MELHORIA 5: SAÃDA INTELIGENTE DE POSIÃ‡ÃƒO (+1.5% EFICÃCIA) ==========


class SaidaInteligentePositions:
    """Gerencia saÃ­da inteligente de posiÃ§Ãµes."""

    def __init__(self):
        self.posicoes_monitoradas = {}
        self.historico_rsi = []

    def iniciar_monitoramento(self, ticket: int, tipo: str, preco_entrada: float):
        """Inicia monitoramento de uma posiÃ§Ã£o."""
        self.posicoes_monitoradas[ticket] = {
            "tipo": tipo,
            "preco_entrada": preco_entrada,
            "tempo_inicio": time.time(),
            "melhor_lucro": 0.0,
            "tempo_sem_lucro": 0,
            "rsi_entrada": self.historico_rsi[-1] if self.historico_rsi else 50.0
        }

    def atualizar_rsi(self, rsi_atual: float):
        """Atualiza histÃ³rico de RSI."""
        self.historico_rsi.append(rsi_atual)
        if len(self.historico_rsi) > 10:
            self.historico_rsi.pop(0)

    def verificar_saida_inteligente(self, ticket: int, preco_atual: float, rsi_atual: float) -> bool:
        """Verifica se deve sair da posiÃ§Ã£o inteligentemente."""
        if ticket not in self.posicoes_monitoradas:
            return False

        posicao = self.posicoes_monitoradas[ticket]
        tempo_atual = time.time()
        tempo_em_trade = tempo_atual - posicao["tempo_inicio"]

        # Calcula lucro atual em pontos WDO
        if posicao["tipo"] == "BUY":
            # TICK_SIZE WDO
            lucro_atual = (preco_atual - posicao["preco_entrada"]) / TICK_SIZE
        else:
            lucro_atual = (posicao["preco_entrada"] -
                           preco_atual) / TICK_SIZE  # TICK_SIZE WDO

        # Atualiza melhor lucro
        if lucro_atual > posicao["melhor_lucro"]:
            posicao["melhor_lucro"] = lucro_atual
            posicao["tempo_sem_lucro"] = 0
        else:
            posicao["tempo_sem_lucro"] = tempo_atual - posicao["tempo_inicio"]

        # CRITÃ‰RIO 1: 5 minutos sem lucro
        if posicao["tempo_sem_lucro"] >= 300:  # 300 segundos = 5 minutos
            logging.info(
                f"ðŸšª SaÃ­da por tempo sem lucro: {posicao['tempo_sem_lucro']:.0f}s")
            return True

        # CRITÃ‰RIO 2: RSI inverteu com lucro mÃ­nimo (5 pontos WDO)
        if lucro_atual >= 5.0:  # Lucro mÃ­nimo para considerar saÃ­da por RSI
            rsi_entrada = posicao["rsi_entrada"]

            # Para posiÃ§Ã£o BUY: sair se RSI estava baixo e agora estÃ¡ alto
            if posicao["tipo"] == "BUY" and rsi_entrada < 30 and rsi_atual > 70:
                logging.info(
                    f"ðŸšª SaÃ­da BUY por inversÃ£o RSI: {rsi_entrada:.1f} â†’ {rsi_atual:.1f}")
                return True

            # Para posiÃ§Ã£o SELL: sair se RSI estava alto e agora estÃ¡ baixo
            if posicao["tipo"] == "SELL" and rsi_entrada > 70 and rsi_atual < 30:
                logging.info(
                    f"ðŸšª SaÃ­da SELL por inversÃ£o RSI: {rsi_entrada:.1f} â†’ {rsi_atual:.1f}")
                return True

        return False

    def finalizar_monitoramento(self, ticket: int):
        """Finaliza monitoramento de uma posiÃ§Ã£o."""
        if ticket in self.posicoes_monitoradas:
            del self.posicoes_monitoradas[ticket]


# ConfiguraÃ§Ãµes da saÃ­da inteligente
SAIDA_INTELIGENTE_ATIVA = True
TEMPO_MAX_SEM_LUCRO = 300    # 5 minutos sem lucro = sair
RSI_INVERSAO_SAIDA = True    # Sair se RSI inverter com lucro
MIN_LUCRO_SAIDA_RSI = 5.0    # Lucro mÃ­nimo para considerar saÃ­da por RSI

# InstÃ¢ncia global da saÃ­da inteligente
saida_inteligente = None

# ========== MELHORIA 6: FILTRO DE HORÃRIO PREMIUM (+2% EFICÃCIA) ==========


class FiltroHorarioPremium:
    """Filtra operaÃ§Ãµes para horÃ¡rios de maior liquidez e volatilidade."""

    def __init__(self):
        # HorÃ¡rios de maior liquidez WDO (UTC-3)
        self.horarios_premium = [
            (dtime(9, 0), dtime(12, 30)),   # Abertura - alta volatilidade
            # Meio perÃ­odo - movimento institucional
            (dtime(14, 0), dtime(15, 30)),
            (dtime(17, 0), dtime(17, 30))   # Fechamento - ajustes finais
        ]

    def is_horario_premium(self) -> bool:
        """Verifica se estÃ¡ em horÃ¡rio premium para trading."""
        agora = datetime.now().time()

        for inicio, fim in self.horarios_premium:
            if inicio <= agora <= fim:
                return True
        return False

    def get_status(self) -> dict:
        """Retorna status do filtro de horÃ¡rio."""
        return {
            "horario_premium": self.is_horario_premium(),
            "horario_atual": datetime.now().strftime("%H:%M:%S"),
            "proximos_horarios": ["09:15-12:30", "14:30-17:15"]
        }


# ConfiguraÃ§Ãµes do filtro de horÃ¡rio
# Desativado temporariamente para operar em todos os horÃ¡rios
FILTRO_HORARIO_ATIVO = False

# InstÃ¢ncia global do filtro de horÃ¡rio
filtro_horario = None

# ========== SCALER GLOBAL PARA NORMALIZAÃ‡ÃƒO CONSISTENTE ==========
scaler_global = None

# ForÃ§a recriaÃ§Ã£o do scaler para compatibilidade com 22 features


def resetar_scaler_global():
    """ForÃ§a recriaÃ§Ã£o do scaler global para evitar problemas de compatibilidade."""
    global scaler_global
    scaler_global = None
    logging.info(
        f"ðŸ”„ Scaler global resetado para compatibilidade com {N_FEATURES} features")


def forcar_recreacao_scaler():
    """Tenta carregar scaler salvo pelo treinamento offline; se nÃ£o existir, cria com dummy."""
    global scaler_global
    import json as json_mod

    import numpy as np
    from sklearn.preprocessing import MinMaxScaler

    scaler_path = MODELO_PATH.replace('.h5', '_scaler.json')
    if os.path.exists(scaler_path):
        try:
            with open(scaler_path, 'r') as f:
                scaler_info = json_mod.load(f)
            scaler_global = MinMaxScaler()
            mins = np.array(scaler_info['min']).reshape(1, -1)
            maxs = np.array(scaler_info['max']).reshape(1, -1)
            # Estende range em 20% para evitar clipping excessivo em dados reais
            ranges = maxs - mins
            ranges = np.where(ranges == 0, 1.0, ranges)
            mins_ext = mins - ranges * 0.2
            maxs_ext = maxs + ranges * 0.2
            scaler_global.fit(np.vstack([mins_ext, maxs_ext]))
            logging.info(
                f"âœ… Scaler carregado do treinamento offline: {scaler_path}")
            return
        except Exception as e:
            logging.warning(
                f"âš ï¸ Erro ao carregar scaler salvo ({e}), criando com dummy")

    dados_dummy = np.random.random((5, N_FEATURES))
    scaler_global = MinMaxScaler()
    scaler_global.fit(dados_dummy)
    logging.info(
        f"ðŸ”§ Scaler global recriado com {N_FEATURES} features usando dados dummy")

# ========== MELHORIA 7: DETECTOR DE TENDÃŠNCIA SIMPLES (+3% EFICÃCIA) ==========


class DetectorTendencia:
    """Detecta tendÃªncia usando EMAs para viÃ©s direcional."""

    def __init__(self):
        self.ema9_values = []
        self.ema21_values = []
        self.tendencia_atual = "NEUTRO"

    def calcular_ema(self, valores: list, periodo: int) -> float:
        """Calcula EMA de forma simples."""
        if len(valores) < periodo:
            return sum(valores) / len(valores) if valores else 0

        # EMA = (Valor * (2/(periodo+1))) + (EMA_anterior * (1-(2/(periodo+1))))
        multiplicador = 2 / (periodo + 1)
        ema_anterior = sum(valores[:periodo]) / periodo

        for valor in valores[periodo:]:
            ema_anterior = (valor * multiplicador) + \
                (ema_anterior * (1 - multiplicador))

        return ema_anterior

    def atualizar_tendencia(self, preco_fechamento: float):
        """Atualiza cÃ¡lculo de tendÃªncia com novo preÃ§o."""
        self.ema9_values.append(preco_fechamento)
        self.ema21_values.append(preco_fechamento)

        # MantÃ©m histÃ³rico limitado
        if len(self.ema9_values) > 50:
            self.ema9_values.pop(0)
        if len(self.ema21_values) > 50:
            self.ema21_values.pop(0)

        # Calcula EMAs
        if len(self.ema9_values) >= 9 and len(self.ema21_values) >= 21:
            ema9 = self.calcular_ema(self.ema9_values, 9)
            ema21 = self.calcular_ema(self.ema21_values, 21)

            # Define tendÃªncia
            if ema9 > ema21:
                self.tendencia_atual = "ALTA"
            elif ema9 < ema21:
                self.tendencia_atual = "BAIXA"
            else:
                self.tendencia_atual = "NEUTRO"

    def pode_operar(self, acao: str) -> bool:
        """Verifica se pode operar na direÃ§Ã£o baseado na tendÃªncia."""
        if self.tendencia_atual == "NEUTRO":
            return True  # Permite ambas direÃ§Ãµes
        elif self.tendencia_atual == "ALTA" and acao == "BUY":
            return True  # BUY a favor da tendÃªncia
        elif self.tendencia_atual == "BAIXA" and acao == "SELL":
            return True  # SELL a favor da tendÃªncia
        else:
            return False  # Contra a tendÃªncia

    def get_status(self) -> dict:
        """Retorna status da tendÃªncia."""
        return {
            "tendencia": self.tendencia_atual,
            "ema9": self.ema9_values[-1] if self.ema9_values else 0,
            "ema21": self.ema21_values[-1] if self.ema21_values else 0
        }


# ConfiguraÃ§Ãµes do detector de tendÃªncia
DETECTOR_TENDENCIA_ATIVO = True

# InstÃ¢ncia global do detector de tendÃªncia
detector_tendencia = None

# ========== SISTEMA DE VOLUME INTELIGENTE BASEADO NO BOOK ==========


def calcular_volume_inteligente(volume_book_total: float) -> float:
    """Calcula volume adaptativo baseado na liquidez do book (ajustado para WDO).
    WDO: 1 contrato padrÃ£o. SÃ³ aumenta se liquidez MUITO alta."""
    if volume_book_total >= 5000:   # LIQUIDEZ EXTREMA
        return 2.0   # No mÃ¡ximo 2 contratos
    elif volume_book_total >= 3000: # ALTA LIQUIDEZ WDO
        return 1.5
    else:  # NORMAL
        return 1.0   # PadrÃ£o: 1 contrato

# ========== MELHORIA 8: SISTEMA DE COOLDOWN INTELIGENTE (+1.5% EFICÃCIA) ==========


class CooldownInteligente:
    """Gerencia cooldown entre operaÃ§Ãµes para evitar overtrading."""

    def __init__(self):
        self.ultima_operacao = 0
        self.losses_seguidos = 0
        self.cooldown_ativo = False
        self.fim_cooldown = 0

    def registrar_resultado(self, lucro: float):
        """Registra resultado e define cooldown necessÃ¡rio."""
        self.ultima_operacao = time.time()

        if lucro <= -25.0:  # Loss significativo (<= R$25)
            self.losses_seguidos += 1

            # âœ… TRAVA PÃ“S-LOSS: mÃ­nimo 180s independente de qualquer sinal "premium"
            if self.losses_seguidos == 1:
                # 5 min apÃ³s 1 loss (>= 180s obrigatÃ³rio)
                cooldown_segundos = 300
            elif self.losses_seguidos == 2:
                cooldown_segundos = 600   # 10 min apÃ³s 2 losses
            else:
                cooldown_segundos = 900   # 15 min apÃ³s 3+ losses

            # Garantia: nunca menos de 180s apÃ³s qualquer loss
            cooldown_segundos = max(cooldown_segundos, 180)

            self.cooldown_ativo = True
            self.fim_cooldown = time.time() + cooldown_segundos

            logging.warning(
                f"ðŸ”’ TRAVA PÃ“S-LOSS: {cooldown_segundos}s bloqueado apÃ³s {self.losses_seguidos} loss(es) | "
                f"Nenhum sinal pode ultrapassar esta trava!")

        else:  # Win ou break-even
            self.losses_seguidos = 0
            # COOLDOWN GERAL: 4 minutos entre TODAS as operaÃ§Ãµes (mesmo apÃ³s win)
            cooldown_segundos = 240  # 4 minutos para reduzir overtrading
            self.cooldown_ativo = True
            self.fim_cooldown = time.time() + cooldown_segundos
            logging.info(
                f"â³ Cooldown geral ativado: {cooldown_segundos}s para reduzir overtrading")

    def pode_operar(self) -> bool:
        """Verifica se pode operar (nÃ£o estÃ¡ em cooldown)."""
        if not self.cooldown_ativo:
            return True

        if time.time() >= self.fim_cooldown:
            self.cooldown_ativo = False
            logging.info("âœ… Cooldown finalizado - Pode operar novamente")
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


# ConfiguraÃ§Ãµes do cooldown
# âœ… REATIVADO (23/07/2026): trade entrou 2s apÃ³s prejuÃ­zo â€” precisa de trava.
# Cooldown: 5min apÃ³s 1 loss, 10min apÃ³s 2 losses, 15min apÃ³s 3+ losses.
# MÃ­nimo 180s apÃ³s qualquer loss.
COOLDOWN_ATIVO = False  # DESATIVADO por solicitaÃ§Ã£o do operador â€” cooldown sÃ³ atrasava reentrada
COOLDOWN_LOSS_1 = 300   # 5 minutos apÃ³s 1 loss
COOLDOWN_LOSS_2 = 600   # 10 minutos apÃ³s 2 losses
COOLDOWN_LOSS_3 = 900   # 15 minutos apÃ³s 3+ losses

# InstÃ¢ncia global do cooldown
cooldown_sistema = None

# ========== MELHORIA 9: FILTRO DE SPREAD DINÃ‚MICO (+1% EFICÃCIA) ==========


class FiltroSpreadDinamico:
    """Ajusta spread mÃ¡ximo baseado na volatilidade do mercado."""

    def __init__(self):
        self.historico_atr = []
        self.spread_maximo_atual = MAX_SPREAD

    def atualizar_atr(self, atr_atual: float):
        """Atualiza histÃ³rico de ATR para cÃ¡lculo dinÃ¢mico."""
        self.historico_atr.append(atr_atual)
        if len(self.historico_atr) > 20:
            self.historico_atr.pop(0)

        # Calcula spread dinÃ¢mico baseado na volatilidade
        if len(self.historico_atr) >= 5:
            atr_medio = sum(self.historico_atr[-5:]) / 5

            # Spread dinÃ¢mico baseado no ATR
            if atr_medio < 200:  # ATR baixo - mercado calmo
                self.spread_maximo_atual = 5
            elif atr_medio < 400:  # ATR mÃ©dio
                self.spread_maximo_atual = 10
            else:  # ATR alto - mercado volÃ¡til
                self.spread_maximo_atual = 20

    def spread_aceitavel(self, spread_atual: float) -> bool:
        """Verifica se spread estÃ¡ dentro do limite dinÃ¢mico."""
        return spread_atual <= self.spread_maximo_atual

    def get_status(self) -> dict:
        """Retorna status do filtro de spread."""
        atr_atual = self.historico_atr[-1] if self.historico_atr else 0
        return {
            "spread_maximo": self.spread_maximo_atual,
            "atr_atual": atr_atual,
            "volatilidade": "BAIXA" if atr_atual < 200 else "MÃ‰DIA" if atr_atual < 400 else "ALTA"
        }


# ConfiguraÃ§Ãµes do spread dinÃ¢mico
SPREAD_DINAMICO_ATIVO = True
SPREAD_ATR_BAIXO = 5    # Spread mÃ¡x quando ATR < 200
SPREAD_ATR_MEDIO = 10   # Spread mÃ¡x quando ATR 200-400
SPREAD_ATR_ALTO = 20    # Spread mÃ¡x quando ATR > 400

# InstÃ¢ncia global do filtro de spread
filtro_spread = None

# ========== MELHORIA 10: MONITORAMENTO DE PERFORMANCE EM TEMPO REAL (+2% EFICÃCIA) ==========


class MonitorPerformance:
    """Monitora performance em tempo real com alertas inteligentes."""

    def __init__(self):
        self.operacoes_recentes = []  # Ãšltimas 10 operaÃ§Ãµes
        self.drawdown_atual = 0.0
        self.drawdown_maximo = 0.0
        self.pico_capital = 0.0
        self.performance_por_modo = {
            "NORMAL": {"wins": 0, "losses": 0, "lucro_total": 0.0},
            "EXPLOSAO": {"wins": 0, "losses": 0, "lucro_total": 0.0},
            "LATERAL": {"wins": 0, "losses": 0, "lucro_total": 0.0}
        }

    def registrar_operacao(self, lucro: float, modo: str):
        """Registra operaÃ§Ã£o e atualiza mÃ©tricas."""
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
        """Calcula taxa de acerto das Ãºltimas operaÃ§Ãµes."""
        if not self.operacoes_recentes:
            return 0.0
        wins = sum(1 for op in self.operacoes_recentes if op > 0)
        return (wins / len(self.operacoes_recentes)) * 100

    def verificar_alertas(self) -> list:
        """VerdiÃ§Ãµes de alerta."""
        alertas = []

        # Alerta: Taxa de acerto baixa
        taxa_acerto = self.taxa_acerto_recente()
        if len(self.operacoes_recentes) >= 5 and taxa_acerto < 30:
            alertas.append(f"ðŸš¨ Taxa de acerto baixa: {taxa_acerto:.1f}%")

        return alertas


# ========== NOVAS CLASSES IMPLEMENTADAS (IMPLEMENTE.TXT) ==========


class GerenciadorDeSaida:
    """
    Unifica e gerencia todas as lÃ³gicas de saÃ­da de uma posiÃ§Ã£o:
    - Trailing Stop Inteligente
    - Timeout sem evoluÃ§Ã£o
    - ProteÃ§Ã£o de lucro (Drawdown do Pico)
    - SaÃ­da por estagnaÃ§Ã£o
    - SaÃ­da por inversÃ£o de RSI
    """

    def __init__(self, config_saida: dict):
        self.config = config_saida
        self.posicao_monitorada = None
        self.preco_entrada = 0.0
        self.melhor_preco = 0.0
        self.lucro_maximo_pontos = 0.0
        self.tempo_inicio = None
        self.tipo_posicao = ""  # "BUY" ou "SELL"

    def iniciar_monitoramento(self, posicao_mt5):
        """Inicia o monitoramento de uma nova posiÃ§Ã£o."""
        self.posicao_monitorada = posicao_mt5.ticket
        self.preco_entrada = posicao_mt5.price_open
        self.melhor_preco = self.preco_entrada
        self.lucro_maximo_pontos = 0.0
        self.tempo_inicio = time.time()
        self.tipo_posicao = "BUY" if posicao_mt5.type == mt5.POSITION_TYPE_BUY else "SELL"
        logging.info(
            f"ðŸ›¡ï¸ Gerenciador de SaÃ­da ATIVADO para posiÃ§Ã£o #{self.posicao_monitorada}")

    def finalizar_monitoramento(self):
        """Reseta o estado do gerenciador."""
        self.posicao_monitorada = None
        logging.info("ðŸ›¡ï¸ Gerenciador de SaÃ­da DESATIVADO.")

    def verificar_condicoes_saida(self, preco_atual: float, rsi_atual: float) -> Tuple[bool, str, Optional[float]]:
        """
        Verifica todas as regras de saÃ­da e retorna uma decisÃ£o.
        Retorna: (deve_sair, motivo, novo_sl_se_aplicavel)
        """
        if not self.posicao_monitorada:
            return False, "", None

        # --- CÃ¡lculos Iniciais ---
        tempo_em_posicao = time.time() - self.tempo_inicio
        lucro_em_pontos = 0.0
        # CORREÃ‡ÃƒO: lucro em PONTOS REAIS (nÃ£o ticks)
        # 1 ponto WDO = 10 ticks (preÃ§o muda de 0.5 em 0.5)
        # DiferenÃ§a de preÃ§o / 1.0 = pontos reais

        if self.tipo_posicao == "BUY":
            # PONTOS REAIS (nÃ£o divide por tick)
            lucro_em_pontos = (preco_atual - self.preco_entrada)
            if preco_atual > self.melhor_preco:
                self.melhor_preco = preco_atual
        else:  # SELL
            lucro_em_pontos = (self.preco_entrada -
                               preco_atual)  # PONTOS REAIS
            if preco_atual < self.melhor_preco:
                self.melhor_preco = preco_atual

        self.lucro_maximo_pontos = max(
            self.lucro_maximo_pontos, lucro_em_pontos)

        # --- VerificaÃ§Ã£o das Regras de SAÃDA (Ordem de Prioridade) ---

        # âŒ REGRA 1 (Timeout) e REGRA 3 (EstagnaÃ§Ã£o) DESATIVADAS (17/07/2026,
        # decisÃ£o do mestre super): com entrada Sniper (ratio 2.0) + veto "seguir os
        # bigs", a posiÃ§Ã£o deve respirar atÃ© o alvo natural. Quem tira do trade agora Ã©:
        #   â€¢ SL fixo de 5pts (proteÃ§Ã£o WDO)
        #   â€¢ TP dinÃ¢mico (Keras decide saÃ­da)
        #   â€¢ Trailing Stop (REGRA 4, abaixo)
        #   â€¢ InversÃ£o de fluxo (big players viram contra â†’ sai no loop principal)
        # Timers arbitrÃ¡rios de tempo NÃƒO fecham mais a posiÃ§Ã£o.

        # REGRA 2: ProteÃ§Ã£o de lucro â€” sÃ³ ativa apÃ³s 10pts (WDO sem TP)
        # Com TP=0, precisa de mais espaÃ§o: trailing gatilho Ã© 80pts, entÃ£o
        # proteÃ§Ã£o sÃ³ corta se pico > 10pts E caiu > 50% do pico.
        # AlÃ©m disso, sÃ³ ativa apÃ³s 30s para evitar falsos positivos no inÃ­cio.
        if tempo_em_posicao > 30 and self.lucro_maximo_pontos > 10 and \
           lucro_em_pontos < self.lucro_maximo_pontos * 0.50:
            return True, f"C12: ProteÃ§Ã£o de Lucro (caiu de {self.lucro_maximo_pontos:.1f}pts - 50% do pico, TP=0)", None

        # --- VerificaÃ§Ã£o das Regras de AJUSTE (Trailing Stop) ---

        # REGRA 4: Trailing Stop (C12 - Mais agressivo)
        # Ativa Trailing mais cedo (15pts) e mantÃ©m distÃ¢ncia de 5pts (era 10pts)
        # REGRA 4: Trailing Stop â€” usa config calibrado para TP=250pts
        # Gatilho: 80pts | DistÃ¢ncia: 40pts (em PONTOS REAIS de preÃ§o)
        # REGRA 4: Trailing Stop â€” usa preÃ§o ATUAL para garantir SL vÃ¡lido
        # (melhor_preco pode estar acima do preÃ§o atual, gerando SL acima do bid â†’ MT5 rejeita)
        if lucro_em_pontos >= self.config['trailing_gatilho_pts']:
            novo_sl = 0.0
            distancia_trailing_preco = self.config['trailing_distancia_pts']

            if self.tipo_posicao == "BUY":
                # SL fica ABAIXO do preÃ§o atual (nunca acima do bid)
                novo_sl = preco_atual - distancia_trailing_preco
            else:  # SELL
                # SL fica ACIMA do preÃ§o atual (nunca abaixo do ask)
                novo_sl = preco_atual + distancia_trailing_preco

            # VALIDAÃ‡ÃƒO CRÃTICA: Garantir que o novo SL Ã© uma melhoria real
            posicao_mt5_info = mt5.positions_get(
                ticket=self.posicao_monitorada)

            if posicao_mt5_info and len(posicao_mt5_info) > 0:
                sl_atual = posicao_mt5_info[0].sl

                # Para BUY, SL deve ser maior que o atual (subindo)
                if self.tipo_posicao == "BUY" and novo_sl > sl_atual:
                    logging.info(
                        f"ðŸ”§ DecisÃ£o de Ajuste BUY: Novo SL {novo_sl:.2f} (Melhoria de {sl_atual:.2f})")
                    return False, "Ajuste de Trailing Stop", novo_sl

                # Para SELL, SL deve ser menor que o atual (descendo)
                elif self.tipo_posicao == "SELL" and novo_sl < sl_atual:
                    logging.info(
                        f"ðŸ”§ DecisÃ£o de Ajuste SELL: Novo SL {novo_sl:.2f} (Melhoria de {sl_atual:.2f})")
                    return False, "Ajuste de Trailing Stop", novo_sl

                else:
                    logging.debug(
                        f"ðŸ”§ Trailing Stop nÃ£o aplicado: {novo_sl:.2f} nÃ£o Ã© melhoria do atual {sl_atual:.2f}")

            # Se nÃ£o conseguiu validar ou nÃ£o Ã© melhoria, nÃ£o ajusta
            return False, "Manter PosiÃ§Ã£o", None

        return False, "Manter PosiÃ§Ã£o", None


class VolumeAdaptativo:
    """Calcula um volume mÃ­nimo para operar de forma adaptativa."""

    def __init__(self, janela_minutos=15, percentual_da_media=0.8):
        self.janela_segundos = janela_minutos * 60
        self.percentual_da_media = percentual_da_media
        # Deque armazena (timestamp, volume)
        self.historico_volumes = collections.deque()
        self.volume_minimo_adaptativo = 500  # Valor inicial padrÃ£o (WDO)

    def adicionar_volume_atual(self, volume_total: float):
        """Adiciona o volume total do book ao histÃ³rico."""
        agora = time.time()
        self.historico_volumes.append((agora, volume_total))
        self._limpar_historico_antigo(agora)
        self._calcular_novo_minimo()

    def _limpar_historico_antigo(self, timestamp_atual):
        """Remove dados mais antigos que a janela de tempo definida."""
        while self.historico_volumes:
            if timestamp_atual - self.historico_volumes[0][0] > self.janela_segundos:
                self.historico_volumes.popleft()
            else:
                break

    def _calcular_novo_minimo(self):
        """Calcula o novo volume mÃ­nimo com base na mÃ©dia do histÃ³rico."""
        if not self.historico_volumes:
            return

        volumes_na_janela = [vol for ts, vol in self.historico_volumes]
        media_volume = sum(volumes_na_janela) / len(volumes_na_janela)

        # O novo mÃ­nimo Ã© um percentual da mÃ©dia
        self.volume_minimo_adaptativo = media_volume * self.percentual_da_media

        # Garante um piso mÃ­nimo para nÃ£o operar com volume muito baixo
        piso_absoluto = 500
        self.volume_minimo_adaptativo = max(
            self.volume_minimo_adaptativo, piso_absoluto)

    def pode_operar(self, volume_atual: float) -> bool:
        """Verifica se o volume atual ae ao mÃ­nimo adaptativo."""
        return volume_atual >= self.volume_minimo_adaptativo

        # Alerta: Drawdown alto
        if self.drawdown_atual > 300:  # R$ 300
            alertas.append(f"ðŸš¨ Drawdown alto: R$ {self.drawdown_atual:.2f}")

        # Alerta: Muitos losses seguidos
        losses_seguidos = 0
        for op in reversed(self.operacoes_recentes):
            if op < 0:
                losses_seguidos += 1
            else:
                break
        if losses_seguidos >= 3:
            alertas.append(f"ðŸš¨ {losses_seguidos} losses seguidos")

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


# ConfiguraÃ§Ãµes do monitor de performance
MONITOR_PERFORMANCE_ATIVO = True
ALERTA_TAXA_ACERTO_MIN = 30    # Alerta se taxa < 30%
ALERTA_DRAWDOWN_MAX = 300      # Alerta se drawdown > R$ 300
ALERTA_LOSSES_SEGUIDOS = 3     # Alerta se 3+ losses seguidos

# InstÃ¢ncia global do monitor
monitor_performance = None

# endregion
# region [Logging]


def setup_logging():
    """Configura o sistema de logging.

    LÃ³gica de rotaÃ§Ã£o:
    - Se o log NÃƒO existe ou foi modificado em outro dia â†’ SOBRESCREVE (nova sessÃ£o)
    - Se o log existe e foi modificado HOJE â†’ APPEND (reiniciando durante o mercado)

    NÃ­vel INFO: mostra o que importa (mercado ao vivo, Sniper, decisÃµes, heartbeat
    da posiÃ§Ã£o, trailing, erros) e elimina o spam de DEBUG (ex.: 'Nenhuma posiÃ§Ã£o
    ativa', 'EA Data', logs internos de bibliotecas). Para depurar, trocar para DEBUG.
    """
    hoje = datetime.now().date()
    log_existe_hoje = False

    if os.path.exists(LOG_FILE):
        modificacao = datetime.fromtimestamp(os.path.getmtime(LOG_FILE)).date()
        log_existe_hoje = (modificacao == hoje)

    # Se o log Ã© de hoje (reiniciando durante o mercado) â†’ append
    # Se o log nÃ£o existe ou Ã© de ontem/antes â†’ sobrescreve (nova sessÃ£o)
    filemode = 'a' if log_existe_hoje else 'w'
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode=filemode,
        # force=True: remove handlers pre-existentes (ex.: StreamHandler(stderr=None)
        # injetado no modo PyInstaller console=False) e garante a criacao do FileHandler.
        force=True
    )

    # Filtra warning repetitivo do Keras sobre compiled metrics
    class KerasWarningFilter(logging.Filter):
        def filter(self, record):
            return 'compiled metrics have yet to be built' not in record.getMessage()
    logging.getLogger().addFilter(KerasWarningFilter())

    if log_existe_hoje:
        logging.info("ðŸŽ¯ Monstro WDO v2 REINICIADO (log de hoje preservado)")
    else:
        logging.info("ðŸŽ¯ Monstro WDO v2 iniciado! Nova sessÃ£o (log anterior sobrescrito)")
    logging.info(
        f"ðŸ“Š ConfiguraÃ§Ã£o: SL={SL_POINTS}pts, TP={TP_POINTS}pts, Vol={VOLUME_PADRAO}cc")


# ========== PA1: TRAVA DE HORÃRIO - IMPLEMENTAÃ‡ÃƒO DO PLANO DE AÃ‡ÃƒO ==========

def horario_permitido() -> bool:
    """
    âœ… PA1: Janelas de operaÃ§Ã£o baseadas em liquidez e volatilidade do WDO:
    - 09:15-12:30  Abertura dos futuros (pÃ³s-volatilidade inicial)
    - 14:30-17:15  Retomada institucional (ajustes finais)
    NOTA: SniperSupermo ignora esta verificaÃ§Ã£o (pode operar 09:00-17:30).
    """
    agora = datetime.now().time()
    if dtime(9, 15) <= agora <= dtime(12, 30):
        return True
    if dtime(14, 30) <= agora <= dtime(17, 15):
        return True
    return False


def segundos_ate_proxima_janela() -> int:
    """Calcula quantos segundos faltam para a prÃ³xima janela de operaÃ§Ã£o."""
    agora = datetime.now()
    hoje = agora.date()

    janelas = [dtime(9, 15), dtime(14, 30)]

    for janela in janelas:
        proximo = datetime.combine(hoje, janela)
        if proximo > agora:
            return int((proximo - agora).total_seconds())

    # Todas as janelas de hoje passaram â€” prÃ³xima Ã© 09:15 do prÃ³ximo dia Ãºtil
    amanha = hoje + timedelta(days=1)
    while amanha.weekday() > 4:  # pula fim de semana
        amanha += timedelta(days=1)

    proximo = datetime.combine(amanha, dtime(9, 15))
    return int((proximo - agora).total_seconds())


# ========== PTAX: COLETA E INDICADORES ==========

import html.parser
import urllib.request

_ptax_cache = {"valor": 0.0, "data": None, "hora_coleta": 0}

class _PTAXParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self._dentro_td = False
        self._valores = []
    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self._dentro_td = True
    def handle_endtag(self, tag):
        if tag == "td":
            self._dentro_td = False
    def handle_data(self, data):
        if self._dentro_td:
            data = data.strip().replace(",", ".")
            try:
                self._valores.append(float(data))
            except ValueError:
                pass

def coletar_ptax() -> float:
    """Coleta PTAX venda do site do BCB. Retorna 0.0 se falhar."""
    try:
        req = urllib.request.Request(
            "https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html_bytes = resp.read()
        parser = _PTAXParser()
        parser.feed(html_bytes.decode("utf-8", errors="ignore"))
        if len(parser._valores) >= 2:
            return parser._valores[1]  # taxa venda
    except Exception:
        pass
    return 0.0

def atualizar_ptax():
    """Tenta coletar PTAX uma vez por dia. Usa cache."""
    hoje = datetime.now().date()
    if _ptax_cache["data"] == hoje and _ptax_cache["valor"] > 0:
        return _ptax_cache["valor"]
    valor = coletar_ptax()
    if valor > 0:
        _ptax_cache["valor"] = valor
        _ptax_cache["data"] = hoje
        _ptax_cache["hora_coleta"] = time.time()
        logging.info(f"ðŸ“ˆ PTAX atualizada: R$ {valor:.4f}")
    return valor

def ultimo_dia_util_mes(data: datetime = None) -> bool:
    """Retorna True se 'data' Ã© o Ãºltimo dia Ãºtil do mÃªs."""
    if data is None:
        data = datetime.now()
    prox = data + timedelta(days=1)
    while prox.weekday() > 4:
        prox += timedelta(days=1)
    return prox.month != data.month

def em_janela_ptax() -> Tuple[bool, int]:
    """Retorna (dentro_da_janela, minutos_para_proxima_janela)."""
    agora = datetime.now()
    h, m = agora.hour, agora.minute
    minutos = h * 60 + m
    # Janelas PTAX: 10:00-10:10, 11:00-11:10, 12:00-12:10, 13:00-13:10
    janelas = [(600, 610), (660, 670), (720, 730), (780, 790)]
    for inicio, fim in janelas:
        if inicio <= minutos <= fim:
            return True, 0
    # Minutos atÃ© prÃ³xima janela
    for inicio, _ in janelas:
        if minutos < inicio:
            return False, inicio - minutos
    return False, 60  # Se passou das 13:10, prÃ³ximo dia

def eh_horario_payroll() -> bool:
    """Retorna True se estamos dentro da janela de fuga do payroll (9:25-9:35 BRT)."""
    agora = datetime.now()
    if agora.weekday() != 4:  # Sexta
        return False
    h, m = agora.hour, agora.minute
    # Payroll: primeira sexta do mÃªs, 9:30 BRT. Fugir 9:25-9:35
    if h == 9 and 25 <= m <= 35:
        return True
    return False

def verificar_sniper_bloqueado() -> Tuple[bool, str]:
    """Retorna (bloqueado, motivo) para o sniper."""
    if ultimo_dia_util_mes():
        return True, "DIA_PTAX"
    if eh_horario_payroll():
        return True, "PAYROLL"
    return False, ""


# ========== PA3: RESET DE MEMÃ“RIA DA IA - IMPLEMENTAÃ‡ÃƒO DO PLANO DE AÃ‡ÃƒO ==========

def resetar_memoria_ia():
    """
    âœ… PA3: RESET DE IA: Limpa memÃ³ria de experiÃªncias para comeÃ§ar aprendizado do zero
    com as novas correÃ§Ãµes conforme plano de aÃ§Ã£o.
    """
    arquivos_para_limpar = [
        "experiencias_wdo.json",
        "historico_contexto_wdo.csv",
        "decisions_wdo.csv",
        "memoria.pkl"
    ]

    arquivos_limpos = 0

    for arquivo in arquivos_para_limpar:
        try:
            if os.path.exists(arquivo):
                # Faz backup antes de limpar
                backup_name = f"{arquivo}.backup_reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(arquivo, backup_name)

                # Limpa o arquivo
                if arquivo.endswith('.json'):
                    with open(arquivo, 'w') as f:
                        json.dump([], f)
                elif arquivo.endswith('.csv'):
                    # MantÃ©m apenas o cabeÃ§alho se existir
                    if os.path.getsize(arquivo) > 0:
                        df = pd.read_csv(arquivo, nrows=0)  # SÃ³ cabeÃ§alho
                        df.to_csv(arquivo, index=False)
                elif arquivo.endswith('.pkl'):
                    os.remove(arquivo)

                arquivos_limpos += 1
                logging.info(
                    f"âœ… RESET: {arquivo} limpo (backup: {backup_name})")
            else:
                logging.info(f"âš ï¸ RESET: {arquivo} nÃ£o existe")

        except Exception as e:
            logging.error(f"âŒ RESET: Erro ao limpar {arquivo}: {e}")

    logging.info(
        f"ðŸ”„ RESET DE MEMÃ“RIA COMPLETO: {arquivos_limpos} arquivos processados")
    logging.info("ðŸŽ¯ IA comeÃ§arÃ¡ aprendizado do zero com novas correÃ§Ãµes!")

# endregion

# region [FunÃ§Ãµes Auxiliares]


def analisar_profundidade_book(book_data: Dict, preco_referencia: float) -> Dict:
    """
    Analisa a profundidade do book e extrai features sobre escoras e liquidez.

    Args:
        book_data: Dados book no formato JSON {"bids": [...], "asks": [...]}
        preco_referencia: PreÃ§o atual de referÃªncia para calcular distÃ¢ncias

    Returns:
        Dict com 8 novas features de profundidade do book
    """
    features = {
        'preco_maior_escora_bid': 0.0,
        'volume_maior_escora_bid': 0.0,
        'distancia_maior_escora_bid': 999.0,
        'preco_maior_escora_ask': 0.0,
        'volume_maior_escora_ask': 0.0,
        'distancia_maior_escora_ask': 999.0,
        'liquidez_top5_bid': 0.0,
        'liquidez_top5_ask': 0.0
    }

    if not book_data:
        return features

    try:
        # Analisa o lado da compra (bids)
        if book_data.get("bids") and len(book_data["bids"]) > 0:
            df_bids = pd.DataFrame(book_data["bids"])
            if not df_bids.empty and 'volume' in df_bids.columns:
                # Encontra a maior escora (maior volume)
                idx_maior_bid = df_bids['volume'].idxmax()
                maior_escora_bid = df_bids.loc[idx_maior_bid]

                features['preco_maior_escora_bid'] = float(
                    maior_escora_bid.get('price', 0.0))
                features['volume_maior_escora_bid'] = float(
                    maior_escora_bid.get('volume', 0.0))

                # Calcula distÃ¢ncia apenas se temos preÃ§o vÃ¡lido
                if features['preco_maior_escora_bid'] > 0 and preco_referencia > 0:
                    features['distancia_maior_escora_bid'] = abs(
                        preco_referencia - features['preco_maior_escora_bid'])

                # Liquidez dos top 5 nÃ­veis
                features['liquidez_top5_bid'] = float(
                    df_bids.head(5)['volume'].sum())

        # Analisa o lado da venda (asks)
        if book_data.get("asks") and len(book_data["asks"]) > 0:
            df_asks = pd.DataFrame(book_data["asks"])
            if not df_asks.empty and 'volume' in df_asks.columns:
                # Encontra a maior escora (maior volume)
                idx_maior_ask = df_asks['volume'].idxmax()
                maior_escora_ask = df_asks.loc[idx_maior_ask]

                features['preco_maior_escora_ask'] = float(
                    maior_escora_ask.get('price', 0.0))
                features['volume_maior_escora_ask'] = float(
                    maior_escora_ask.get('volume', 0.0))

                # Calcula distÃ¢ncia apenas se temos preÃ§o vÃ¡lido
                if features['preco_maior_escora_ask'] > 0 and preco_referencia > 0:
                    features['distancia_maior_escora_ask'] = abs(
                        features['preco_maior_escora_ask'] - preco_referencia)

                # Liquidez dos top 5 nÃ­veis
                features['liquidez_top5_ask'] = float(
                    df_asks.head(5)['volume'].sum())

    except Exception as e:
        logging.warning(f"âš ï¸ Erro ao analisar profundidade do book: {e}")
        # Retorna features zeradas em caso de erro

    return features


def obter_nome_vela(open_price: float, close_price: float, high: float, low: float, previous_open: float = None, previous_close: float = None) -> str:
    """Determina o tipo da vela baseado nos preÃ§os e padrÃµes.

    Tipos de velas identificadas:
    - Marubozu (alta/baixa): corpo grande sem sombras
    - Doji: abertura = fechamento
    - Martelo/Hammer: sombra inferior longa
    - Shooting Star: sombra superior longa
    - Engolfo (alta/baixa): quando uma vela engole a anterior
    - Inside Bar: vela contida na anterior
    - Outside Bar: vela que contÃ©m a anterior
    - Estrela da ManhÃ£/Noite: padrÃ£o de 3 velas
    - Pin Bar: vela com sombra longa
    """
    body_size = abs(close_price - open_price)
    total_size = high - low
    upper_shadow = high - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low

    # Calcula proporÃ§Ãµes
    body_ratio = body_size / total_size if total_size > 0 else 0
    upper_ratio = upper_shadow / total_size if total_size > 0 else 0
    lower_ratio = lower_shadow / total_size if total_size > 0 else 0

    # Doji
    if body_ratio < 0.1:
        if upper_ratio > 0.6:
            return "doji_gravestone"  # Doji LÃ¡pide
        elif lower_ratio > 0.6:
            return "doji_dragonfly"   # Doji LibÃ©lula
        return "doji"

    # DireÃ§Ã£o bÃ¡sica
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

    # PadrÃµes com vela anterior
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

    # Vela padrÃ£o
    return direction


def calcular_entropia(volumes: List[int]) -> float:
    """Calcula a entropia dos volumes do book (CORRIGIDO PARA EA)."""
    if not volumes:
        logging.debug(
            "[Entropia] Lista de volumes vazia, retornando entropia 0.0")
        return 0.0

    # Converte para inteiros e remove zeros para evitar problemas no cÃ¡lculo
    try:
        volumes_validos = [int(v) for v in volumes if int(v) > 0]
    except (ValueError, TypeError) as e:
        logging.error(
            f"[Entropia] Erro ao converter volumes para int: {e}, volumes: {volumes[:5]}...")
        return 0.0

    if not volumes_validos:
        logging.debug(
            "[Entropia] NÃ£o hÃ¡ volumes vÃ¡lidos (>0), retornando entropia 0.0")
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


def calcular_williams_r(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calcula Williams %R (Larry Williams oscillator)."""
    if len(highs) < period or len(lows) < period or len(closes) < period:
        return -50.0
    highest_high = max(highs[-period:])
    lowest_low = min(lows[-period:])
    if highest_high == lowest_low:
        return -50.0
    return -100.0 * (highest_high - closes[-1]) / (highest_high - lowest_low)


def detectar_divergencia_wr(precos: List[float], wr_values: List[float], janela: int = 200) -> str:
    """Detecta divergÃªncia bull/bear entre preÃ§o e Williams %R usando thresholds em ticks (WDO TICK_SIZE=0.5)."""
    if len(precos) < janela or len(wr_values) < janela:
        return "NEUTRO"
    TICK_SIZE = 0.5
    precos_janela = precos[-janela:]
    wr_janela = wr_values[-janela:]
    min_preco_ant = min(precos_janela[:-1])
    max_preco_ant = max(precos_janela[:-1])
    min_wr_ant = min(wr_janela[:-1])
    max_wr_ant = max(wr_janela[:-1])
    # Bullish divergence: price makes lower low, %R makes higher low
    if precos_janela[-1] <= min_preco_ant - 2 * TICK_SIZE:
        if wr_janela[-1] >= min_wr_ant + 5:
            return "DIVERGENCIA_BULL"
    # Bearish divergence: price makes higher high, %R makes lower high
    if precos_janela[-1] >= max_preco_ant + 2 * TICK_SIZE:
        if wr_janela[-1] <= max_wr_ant - 5:
            return "DIVERGENCIA_BEAR"
    return "NEUTRO"


class MonitorWilliamsR:
    """Monitora Williams %R em tempo real, detecta zonas e divergÃªncias, salva histÃ³rico CSV."""

    def __init__(self, arquivo_csv: str = None, period: int = 14, janela_div: int = 200):
        self.arquivo_csv = arquivo_csv or _caminho_dados("williams_r_historico.csv")
        self.period = period
        self.janela_div = janela_div
        self.historico_precos: List[float] = []
        self.historico_highs: List[float] = []
        self.historico_lows: List[float] = []
        self.historico_wr: List[float] = []
        self.ultimo_log_zona = ""
        self.ultima_divergencia = ""
        self._csv_header_escrito = False

    def alimentar(self, preco: float, high: float, low: float, wr: float) -> dict:
        self.historico_precos.append(preco)
        self.historico_highs.append(high)
        self.historico_lows.append(low)
        self.historico_wr.append(wr)
        max_hist = max(self.janela_div * 3, 1000)
        if len(self.historico_precos) > max_hist:
            self.historico_precos = self.historico_precos[-max_hist:]
            self.historico_highs = self.historico_highs[-max_hist:]
            self.historico_lows = self.historico_lows[-max_hist:]
            self.historico_wr = self.historico_wr[-max_hist:]

        zona = "NEUTRO"
        if wr < -80:
            zona = "SOBREVENDIDO"
        elif wr > -20:
            zona = "SOBRECOMPRADO"

        divergencia = detectar_divergencia_wr(
            self.historico_precos, self.historico_wr, janela=self.janela_div)

        resultado = {
            'wr': wr,
            'zona': zona,
            'divergencia': divergencia,
        }

        # Log zona only when it changes
        if zona != self.ultimo_log_zona and zona != "NEUTRO":
            logging.info(f"ðŸ“Š WILLIAMS %R: {wr:.1f} ({zona})")
            self.ultimo_log_zona = zona

        # Log divergencia only when detected
        if divergencia != "NEUTRO" and divergencia != self.ultima_divergencia:
            logging.info(f"ðŸ” WILLIAMS %R DIVERGENCIA: {divergencia} (WR={wr:.1f}, Preco={preco:.1f})")
            self.ultima_divergencia = divergencia

        self._salvar_csv(preco, high, low, wr, zona, divergencia)
        return resultado

    def _salvar_csv(self, preco: float, high: float, low: float, wr: float, zona: str, divergencia: str):
        try:
            escrever = not self._csv_header_escrito
            with open(self.arquivo_csv, 'a', newline='') as f:
                if escrever:
                    if f.tell() == 0:
                        f.write("timestamp,preco,high,low,wr,zona,divergencia\n")
                    self._csv_header_escrito = True
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{preco:.1f},{high:.1f},{low:.1f},{wr:.1f},{zona},{divergencia}\n")
        except Exception as e:
            logging.debug(f"[WilliamsR] Erro ao salvar CSV: {e}")


williams_r_monitor = MonitorWilliamsR()


# ========== SNIPER SUPERMO (entrada cirÃºrgica com confluÃªncia TOTAL) ==========
SNIPER_SUPERMO_ATIVO = False
SNIPER_SUPERMO_VOLUME = 5.0
SNIPER_SUPERMO_CSV = _caminho_dados("sniper_supermo_historico.csv")


class SniperSupermo:
    """Modo de operaÃ§Ã£o de alta convicÃ§Ã£o. SÃ³ entra quando TODOS os filtros se alinham.

    CondiÃ§Ãµes verificadas:
      1. DOL confianÃ§a > 0.7 + lado alinhado com direÃ§Ã£o
      2. Williams %R em zona extrema (< -85 ou > -15) OU divergÃªncia
      3. RSI em zona (< 25 ou > 75)
      4. ATR > 2.0
      5. Entropia > 2.75 (livro com direÃ§Ã£o, escala real)
      6. HorÃ¡rio: 09:30-11:00 ou 14:45-16:00
      7. Sniper ratio > 2.0 (desequilÃ­brio forte)
    """

    def __init__(self):
        self._csv_header_escrito = False
        self.ultimo_log = 0
        self.cooldown_ate: float = 0
        self.cooldown_segundos = 0  # Sem cooldown â€” sniper Ã© raro, pode re-ativar

    def verificar(self, contexto: dict, acao_sugerida: str) -> dict:
        """Retorna {'ativo': bool, 'direcao': str, 'score': int, 'detalhes': list}."""
        agora = time.time()
        if agora < self.cooldown_ate:
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['cooldown']}

        if not contexto:
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['sem_contexto']}

        # Bloqueio por PTAX day ou payroll (sniper 5cc = risco alto)
        if contexto.get('sniper_bloqueado', 0):
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['BLOQ_PTAX/PAYROLL']}

        score = 0
        detalhes = []
        direcao_sugerida = "NADA"

        # 1. DOL confianÃ§a > 0.7 + lado
        dol_lado = contexto.get('dol_lado', 'NEUTRO')
        dol_conf = contexto.get('dol_confianca', 0)
        dol_presente = contexto.get('dol_presente', 0)
        if dol_presente and dol_lado != 'NEUTRO' and dol_conf > 0.7:
            score += 2
            detalhes.append(f"DOL={dol_lado}({dol_conf:.2f})")
            if dol_lado == 'BUY':
                direcao_sugerida = 'BUY'
            else:
                direcao_sugerida = 'SELL'

        # 2. Sniper ratio > 2.0
        bid_qty = float(contexto.get('bid_qty', 0))
        ask_qty = float(contexto.get('ask_qty', 0))
        if bid_qty > 0 and ask_qty > 0:
            ratio = max(bid_qty, ask_qty) / min(bid_qty, ask_qty)
            if ratio > 2.0:
                score += 1
                detalhes.append(f"SNIPER={ratio:.1f}x")
                lado_book = "BUY" if bid_qty > ask_qty else "SELL"
                if direcao_sugerida == "NADA":
                    direcao_sugerida = lado_book

        # 3. Williams %R em zona extrema ou divergÃªncia
        williams_r = float(contexto.get('williams_r', -50))
        wr_div = contexto.get('wr_divergencia', 'NEUTRO')
        if williams_r < -85:
            score += 2
            detalhes.append(f"%R={williams_r:.0f}(SEV)")  # SobreVendido
            if direcao_sugerida == "NADA":
                direcao_sugerida = "BUY"
        elif williams_r > -15:
            score += 2
            detalhes.append(f"%R={williams_r:.0f}(SEC)")  # SobreComprado
            if direcao_sugerida == "NADA":
                direcao_sugerida = "SELL"
        elif wr_div != "NEUTRO":
            score += 1
            detalhes.append(f"%R_DIV={wr_div}")
            if "BULL" in wr_div and direcao_sugerida == "NADA":
                direcao_sugerida = "BUY"
            elif "BEAR" in wr_div and direcao_sugerida == "NADA":
                direcao_sugerida = "SELL"

        # 4. RSI em zona extrema (usando raw do contexto)
        rsi_raw = float(contexto.get('rsi_14', 50))
        if rsi_raw < 25:
            score += 1
            detalhes.append(f"RSI={rsi_raw:.0f}(SEV)")
        elif rsi_raw > 75:
            score += 1
            detalhes.append(f"RSI={rsi_raw:.0f}(SEC)")

        # 5. ATR > 2.0
        atr = float(contexto.get('volatility', 0))
        if atr > 2.0:
            score += 1
            detalhes.append(f"ATR={atr:.1f}")

        # 6. Entropia > 2.75 (escala real, era 0.3 em [0,1] -> sempre verdadeira)
        entropia = float(contexto.get('entropia_book', 0))
        if entropia > 2.75:
            score += 1
            detalhes.append(f"ENT={entropia:.2f}")

        # 7. HorÃ¡rio (checagem global jÃ¡ feita em horario_permitido, mas pontua)
        agora_h = datetime.now().hour
        agora_m = datetime.now().minute
        score += 1
        detalhes.append(f"HR={agora_h:02d}:{agora_m:02d}")

        ativo = score >= 7 and direcao_sugerida != "NADA"

        if ativo:
            # Verifica se a direÃ§Ã£o sugerida Ã© coerente com DOL
            if dol_presente and dol_lado != 'NEUTRO' and direcao_sugerida != dol_lado:
                ativo = False
                detalhes.append("DOL_CONTRARIA")

        resultado = {
            'ativo': ativo,
            'direcao': direcao_sugerida if ativo else 'NADA',
            'score': score,
            'detalhes': detalhes
        }

        if ativo and agora - self.ultimo_log > 30:
            banner = (
                f"\n{'='*60}\n"
                f"ðŸ”´âš¡ðŸ”´âš¡ðŸ”´ SNIPER SUPERMO ATIVADO âš¡ðŸ”´âš¡ðŸ”´âš¡\n"
                f"DIREÃ‡ÃƒO: {direcao_sugerida} | SCORE: {score}/10\n"
                f"CONDIÃ‡Ã•ES: {' | '.join(detalhes)}\n"
                f"{'='*60}"
            )
            logging.info(banner)
            self.ultimo_log = agora
            self._salvar_csv(contexto, direcao_sugerida, score, detalhes)

        return resultado

    def _salvar_csv(self, contexto: dict, direcao: str, score: int, detalhes: list):
        try:
            escrever = not self._csv_header_escrito
            with open(SNIPER_SUPERMO_CSV, 'a', newline='') as f:
                if escrever:
                    if f.tell() == 0:
                        f.write("timestamp,direcao,score,detalhes,preco,williams_r,wr_div,rsi_14,dol_lado,dol_conf,atr,entropia\n")
                    self._csv_header_escrito = True
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                preco = contexto.get('preco', 0)
                wr = contexto.get('williams_r', -50)
                wr_div = contexto.get('wr_divergencia', 'NEUTRO')
                rsi = contexto.get('rsi_14', 50)
                dol_lado = contexto.get('dol_lado', 'NEUTRO')
                dol_conf = contexto.get('dol_confianca', 0)
                atr = contexto.get('volatility', 0)
                ent = contexto.get('entropia_book', 0)
                det_str = '|'.join(detalhes)
                f.write(f"{ts},{direcao},{score},{det_str},{preco},{wr},{wr_div},{rsi},{dol_lado},{dol_conf},{atr},{ent}\n")
        except Exception as e:
            logging.debug(f"[SniperSupermo] Erro CSV: {e}")

    def ativar_cooldown(self):
        self.cooldown_ate = time.time() + self.cooldown_segundos
        logging.info(f"â³ SNIPER SUPERMO cooldown: {self.cooldown_segundos}s")


sniper_supermo = SniperSupermo()


def normalizar_dados(df: pd.DataFrame, colunas_numericas: List[str], colunas_categoricas: List[str], treino: bool = True) -> pd.DataFrame:
    """Normaliza dados numÃ©ricos e codifica dados categÃ³ricos."""
    global scaler_global
    from sklearn.utils.validation import check_is_fitted

    if treino:
        # Durante treino, cria/ajusta o scaler
        scaler_global = MinMaxScaler()
        df[colunas_numericas] = scaler_global.fit_transform(
            df[colunas_numericas])
        logging.debug(
            f"[normalizar_dados] Scaler ajustado para treino com {len(df)} amostras")
    else:
        # Durante prediÃ§Ã£o â€” verifica se scaler estÃ¡ fitted
        scaler_precisa_fit = False
        if scaler_global is None:
            scaler_precisa_fit = True
        else:
            try:
                check_is_fitted(scaler_global)
            except Exception:
                scaler_precisa_fit = True

        if scaler_precisa_fit:
            # Scaler nÃ£o fitted â€” faz fit com os dados atuais como fallback
            logging.warning(
                "[normalizar_dados] âš ï¸ Scaler nÃ£o fitted â€” fazendo fit com dados atuais como fallback")
            scaler_global = MinMaxScaler()
            df[colunas_numericas] = scaler_global.fit_transform(
                df[colunas_numericas])
        else:
            df[colunas_numericas] = scaler_global.transform(
                df[colunas_numericas])
            antes = df[colunas_numericas].values.copy()
            df[colunas_numericas] = df[colunas_numericas].clip(0.0, 1.0)
            n_clip = int((df[colunas_numericas].values != antes).sum())
            if n_clip > 0:
                logging.warning(f"[normalizar_dados] ⚠️ {n_clip} valores fora de [0,1] foram clipped")
            logging.debug(f"[normalizar_dados] Scaler aplicado para prediÃ§Ã£o")

    for col in colunas_categoricas:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
    return df


def converter_candle_type(candle_type: str) -> str:
    """Converte o tipo de candle para um formato padronizado."""
    return candle_type.lower()  # MantÃ©m o tipo detalhado


def monitorar_recursos() -> None:
    """Monitora recursos do sistema e salva experiÃªncias."""
    try:
        if os.path.exists(HISTORICO_CSV):
            # Verifica tamanho do arquivo
            tamanho_arquivo = os.path.getsize(
                HISTORICO_CSV) / (1024 * 1024)  # Tamanho em MB

            # Se arquivo maior que 50MB, faz rotaÃ§Ã£o
            if tamanho_arquivo > 50:
                # Cria nome do backup com timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{HISTORICO_CSV}.{timestamp}.bak"

                # Move arquivo atual para backup
                os.rename(HISTORICO_CSV, backup_name)

                # MantÃ©m apenas os Ãºltimos 5 backups
                backups = sorted([f for f in os.listdir('.') if f.startswith(
                    HISTORICO_CSV) and f.endswith('.bak')])
                while len(backups) > 5:
                    os.remove(backups.pop(0))

                logging.info(
                    f"ðŸ“¦ RotaÃ§Ã£o do histÃ³rico realizada. Backup: {backup_name}")

            # LÃª e limita nÃºmero de linhas com tratamento de erro
            try:
                df = pd.read_csv(HISTORICO_CSV)
                if len(df) > 5000:  # Reduzido de 10000 para 5000
                    df = df.tail(5000)
                    df.to_csv(HISTORICO_CSV, index=False)
                    logging.debug(
                        "âœ‚ï¸ HistÃ³rico truncado para Ãºltimas 5000 linhas")
            except pd.errors.ParserError as e:
                logging.warning(f"âš ï¸ CSV histÃ³rico corrompido: {e}")
                logging.info("ðŸ”§ Recriando arquivo CSV histÃ³rico...")
                # Cria cabeÃ§alho com o esquema atual (22 features + reward)
                colunas_padrao = ['bid_qty', 'ask_qty', 'spread', 'volatility',
                                  'candle_type', 'entropia_book', 'rsi_14', 'volume_tick',
                                  'is_in_trade', 'floating_profit', 'tempo_em_trade',
                                  'preco_maior_escora_bid', 'volume_maior_escora_bid',
                                  'distancia_maior_escora_bid', 'preco_maior_escora_ask',
                                  'volume_maior_escora_ask', 'distancia_maior_escora_ask',
                                  'liquidez_top5_bid', 'liquidez_top5_ask',
                                  'dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax',
                                  'action', 'reward']
                df_novo = pd.DataFrame(columns=colunas_padrao)
                df_novo.to_csv(HISTORICO_CSV, index=False)
                logging.info("âœ… CSV histÃ³rico recriado com sucesso")

    except Exception as e:
        logging.error(f"âŒ Erro ao monitorar recursos: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")


def corrigir_csv_historico() -> None:
    """Corrige o formato do arquivo CSV histÃ³rico se necessÃ¡rio."""
    try:
        if not os.path.exists(HISTORICO_CSV):
            logging.info(
                "ðŸ“ Arquivo histÃ³rico nÃ£o existe. SerÃ¡ criado na primeira operaÃ§Ã£o.")
            return

        # Verifica tamanho do arquivo
        tamanho_arquivo = os.path.getsize(HISTORICO_CSV) / (1024 * 1024)  # MB
        if tamanho_arquivo > 100:  # Se maior que 100MB
            backup_name = f"{HISTORICO_CSV}.grande.{int(time.time())}"
            os.rename(HISTORICO_CSV, backup_name)
            logging.warning(
                f"âš ï¸ Arquivo muito grande ({tamanho_arquivo:.1f}MB). Movido para: {backup_name}")
            return

        # Tenta ler o CSV com error_bad_lines=False para pular linhas corrompidas
        df = pd.read_csv(HISTORICO_CSV, on_bad_lines='skip')
        linhas_originais = len(df)

        colunas_esperadas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'candle_type',
                             'entropia_book', 'rsi_14', 'volume_tick', 'is_in_trade',
                             'floating_profit', 'tempo_em_trade',
                             'preco_maior_escora_bid', 'volume_maior_escora_bid',
                             'distancia_maior_escora_bid', 'preco_maior_escora_ask',
                             'volume_maior_escora_ask', 'distancia_maior_escora_ask',
                             'liquidez_top5_bid', 'liquidez_top5_ask',
                             'action', 'reward']

        # Remove colunas extras se existirem
        colunas_extras = [
            col for col in df.columns if col not in colunas_esperadas]
        if colunas_extras:
            df = df.drop(columns=colunas_extras)
            logging.warning(
                f"ðŸ”„ Removendo colunas extras do CSV: {colunas_extras}")

        # Adiciona colunas faltantes com valores padrÃ£o apropriados
        colunas_faltando = [
            col for col in colunas_esperadas if col not in df.columns]
        if colunas_faltando:
            logging.warning(
                f"âž• Adicionando colunas faltantes no CSV: {colunas_faltando}")
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

        # Corrige tipos de dados e valores invÃ¡lidos
        df['bid_qty'] = pd.to_numeric(
            df['bid_qty'], errors='coerce').fillna(0).clip(lower=0)
        df['ask_qty'] = pd.to_numeric(
            df['ask_qty'], errors='coerce').fillna(0).clip(lower=0)
        df['spread'] = pd.to_numeric(
            df['spread'], errors='coerce').fillna(0).clip(lower=0)
        df['volatility'] = pd.to_numeric(
            df['volatility'], errors='coerce').fillna(0)
        df['entropia_book'] = pd.to_numeric(
            df['entropia_book'], errors='coerce').fillna(0.5).clip(lower=0)
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

        # Limpa valores extremos (outliers) APENAS de features de volume.
        # âš ï¸ NÃƒO clipar 'reward'! Como a maioria das linhas Ã© NAO_AGIU (reward=0),
        # os quartis ficam [0,0] e o clip zeraria TODAS as recompensas reais â€”
        # apagando o aprendizado da IA a cada reinÃ­cio. Reward Ã© sinal, nÃ£o feature.
        for col in ['bid_qty', 'ask_qty', 'volume_tick']:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # Remove linhas com valores invÃ¡lidos
        df = df.dropna()

        # Limita nÃºmero de linhas
        if len(df) > 5000:
            df = df.tail(5000)
            logging.debug("âœ‚ï¸ HistÃ³rico truncado para Ãºltimas 5000 linhas")

        # Salva o arquivo corrigido
        df.to_csv(HISTORICO_CSV, index=False)

        linhas_final = len(df)
        linhas_removidas = linhas_originais - linhas_final
        if linhas_removidas > 0:
            logging.warning(
                f"ðŸ§¹ {linhas_removidas} linhas invÃ¡lidas removidas do histÃ³rico")

        logging.info("âœ… Arquivo histÃ³rico corrigido com sucesso")

    except Exception as e:
        logging.error(f"âŒ Erro ao corrigir CSV histÃ³rico: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        # Se houver erro, renomeia o arquivo corrompido e cria um novo
        if os.path.exists(HISTORICO_CSV):
            backup_name = f"{HISTORICO_CSV}.corrompido.{int(time.time())}"
            os.rename(HISTORICO_CSV, backup_name)
            logging.info(f"ðŸ“¦ Arquivo corrompido movido para: {backup_name}")


def salvar_experiencia_csv(contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
    """Salva uma experiÃªncia no arquivo CSV com validaÃ§Ãµes."""
    try:
        # RESET MODO APRENDIZADO FORÃ‡ADO apÃ³s operaÃ§Ã£o real
        global MODO_APRENDIZADO_FORCADO
        if acao in ["BUY", "SELL"] and MODO_APRENDIZADO_FORCADO:
            MODO_APRENDIZADO_FORCADO = False
            logging.info(
                "ðŸŽ“ MODO APRENDIZADO FORÃ‡ADO DESATIVADO - OperaÃ§Ã£o real executada")

        # ========== INTEGRAÃ‡ÃƒO MELHORIA 4: CIRCUIT BREAKER REGISTRA RESULTADO ==========
        if circuit_breaker and acao in ["BUY", "SELL"]:
            circuit_breaker.registrar_resultado(lucro)

        # ValidaÃ§Ã£o dos tipos de dados
        if not isinstance(contexto, dict):
            raise ValueError("Contexto deve ser um dicionÃ¡rio")
        if not isinstance(acao, str):
            raise ValueError("AÃ§Ã£o deve ser uma string")
        if not isinstance(lucro, (int, float)):
            raise ValueError("Lucro deve ser numÃ©rico")
        if not isinstance(score_dist, (int, float)):
            raise ValueError("Score_dist deve ser numÃ©rico")

        # ValidaÃ§Ã£o dos valores
        acoes_validas = {"BUY", "SELL", "NAO_AGIU", "NADA"}
        if acao not in acoes_validas:
            raise ValueError(f"AÃ§Ã£o invÃ¡lida: {acao}")

        # Garante que o contexto tem todas as colunas necessÃ¡rias e valores vÃ¡lidos
        dados = {
            'bid_qty': max(0, float(contexto.get('bid_qty', 0))),
            'ask_qty': max(0, float(contexto.get('ask_qty', 0))),
            'spread': max(0, float(contexto.get('spread', 0))),
            'volatility': float(contexto.get('volatility', 0)),
            # Limita tamanho
            'candle_type': str(contexto.get('candle_type', 'unknown'))[:50],
            # Entre 0 e 1
            'entropia_book': max(0, float(contexto.get('entropia_book', 0))),
            # Entre 0 e 100
            'rsi_14': max(0, min(100, float(contexto.get('rsi_14', 50)))),
            'volume_tick': max(0, float(contexto.get('volume_tick', 0))),
            # ForÃ§a 0 ou 1
            'is_in_trade': int(bool(contexto.get('is_in_trade', 0))),
            'floating_profit': float(contexto.get('floating_profit', 0.0)),
            'tempo_em_trade': max(0, int(contexto.get('tempo_em_trade', 0))),
            # Novas features de profundidade do book
            'preco_maior_escora_bid': float(contexto.get('preco_maior_escora_bid', 0.0)),
            'volume_maior_escora_bid': max(0, float(contexto.get('volume_maior_escora_bid', 0.0))),
            'distancia_maior_escora_bid': max(0, float(contexto.get('distancia_maior_escora_bid', 999.0))),
            'preco_maior_escora_ask': float(contexto.get('preco_maior_escora_ask', 0.0)),
            'volume_maior_escora_ask': max(0, float(contexto.get('volume_maior_escora_ask', 0.0))),
            'distancia_maior_escora_ask': max(0, float(contexto.get('distancia_maior_escora_ask', 999.0))),
            'liquidez_top5_bid': max(0, float(contexto.get('liquidez_top5_bid', 0.0))),
            'liquidez_top5_ask': max(0, float(contexto.get('liquidez_top5_ask', 0.0))),
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
                    "âš ï¸ Arquivo de histÃ³rico muito grande, aguardando rotaÃ§Ã£o...")
                return
            df.to_csv(HISTORICO_CSV, mode='a', header=False, index=False)
        else:
            df.to_csv(HISTORICO_CSV, index=False)

        # CORREÃ‡ÃƒO C9: FASE 3 - TREINA COM TODAS AS EXPERIÃŠNCIAS (wins E losses)
        global contador_experiencias_novas
        if acao in ["BUY", "SELL"]:  # Conta TODAS as operaÃ§Ãµes reais, nÃ£o sÃ³ lucrativas
            contador_experiencias_novas += 1

            # FASE 1: Registra resultado no bloqueador de contexto
            if lucro < 0:
                bloqueador_contexto.registrar_loss(contexto)
            else:
                bloqueador_contexto.registrar_win(contexto)

            logging.info(
                f"âœ… ExperiÃªncia REAL salva: AÃ§Ã£o={acao}, Lucro={lucro:.2f}, Score={score_dist:.2f} | Contador: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO}")
        else:
            logging.debug(
                f"âœ… ExperiÃªncia salva: AÃ§Ã£o={acao}, Lucro={lucro:.2f}, Score={score_dist:.2f}")

    except Exception as e:
        logging.error(f"âŒ Erro ao salvar experiÃªncia: {e}")
        logging.debug(f"Dados tentando salvar: {dados}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")


def preparar_dados(df: pd.DataFrame, treino: bool = False) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """Prepara dados para treino ou prediÃ§Ã£o."""
    colunas_categoricas = [
    ]  # Removido candle_type para compatibilidade com modelo (10 features)
    colunas_numericas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book',
                         'rsi_14', 'volume_tick', 'is_in_trade', 'floating_profit', 'tempo_em_trade',
                         'preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
                         'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
                         'liquidez_top5_bid', 'liquidez_top5_ask',
                         'dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax']

    # Cria uma cÃ³pia para evitar modificar o original
    df_work = df.copy()

    # Adiciona colunas faltantes com valor 0 (compatibilidade com experiÃªncias antigas)
    colunas_book_novas = ['preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
                          'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
                          'liquidez_top5_bid', 'liquidez_top5_ask',
                          'dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax']
    for col in colunas_book_novas:
        if col not in df_work.columns:
            df_work[col] = 0.0

    # Normaliza dados numÃ©ricos e codifica categÃ³ricos
    try:
        df_work = normalizar_dados(
            df_work, colunas_numericas, colunas_categoricas, treino=treino)
    except Exception as e:
        logging.error(f"Erro na normalizaÃ§Ã£o de dados: {e}")
        # Fallback: codifica manualmente as colunas categÃ³ricas
        for col in colunas_categoricas:
            if col in df_work.columns and df_work[col].dtype == 'object':
                le = LabelEncoder()
                df_work[col] = le.fit_transform(df_work[col].astype(str))

        # Normaliza apenas as numÃ©ricas usando scaler global
        global scaler_global
        if treino or scaler_global is None:
            scaler_global = MinMaxScaler()
            df_work[colunas_numericas] = scaler_global.fit_transform(
                df_work[colunas_numericas])
        else:
            df_work[colunas_numericas] = scaler_global.transform(
                df_work[colunas_numericas])

    # Seleciona apenas as colunas necessÃ¡rias
    todas_colunas = colunas_numericas + colunas_categoricas
    colunas_disponiveis = [
        col for col in todas_colunas if col in df_work.columns]

    # Debug para identificar problema
    logging.debug(
        f"[preparar_dados] Colunas no DataFrame: {list(df_work.columns)}")
    logging.debug(f"[preparar_dados] Colunas esperadas: {todas_colunas}")
    logging.debug(
        f"[preparar_dados] Colunas disponÃ­veis: {colunas_disponiveis}")

    X = df_work[colunas_disponiveis]
    logging.debug(f"[preparar_dados] Shape final X: {X.shape}")

    # Prepara target
    y = df_work['action'].apply(
        lambda x: 1 if x == 'BUY' else 0) if 'action' in df_work else None

    return X, y


def calcular_estocastico_lento(high_prices: List[float], low_prices: List[float], close_prices: List[float],
                               k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> Tuple[float, float]:
    """
    Calcula o EstocÃ¡stico Lento (%K e %D).
    k_period: PerÃ­odo para %K (padrÃ£o 14)
    d_period: PerÃ­odo para %D (padrÃ£o 3)
    smooth_k: PerÃ­odo de suavizaÃ§Ã£o do %K (padrÃ£o 3)
    """
    if len(high_prices) < k_period or len(low_prices) < k_period or len(close_prices) < k_period:
        return 50.0, 50.0  # Valores neutros se nÃ£o houver dados suficientes

    # Calcula %K rÃ¡pido primeiro
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

    # Suaviza %K rÃ¡pido para obter %K lento
    k_slow = []
    for i in range(len(k_fast) - smooth_k + 1):
        k_slow.append(sum(k_fast[i:i+smooth_k]) / smooth_k)

    # Calcula %D (mÃ©dia mÃ³vel do %K lento)
    if len(k_slow) < d_period:
        return 50.0, 50.0

    d_slow = sum(k_slow[-d_period:]) / d_period
    k_atual = k_slow[-1] if k_slow else 50.0

    return k_atual, d_slow

# endregion

# region [Modelo Neural]


def criar_modelo_neural(n_features: int) -> Sequential:
    """Cria modelo de rede neural com L2 + BatchNorm + Dropout."""
    l2_reg = tf.keras.regularizers.l2(0.001)
    modelo = Sequential()

    modelo.add(tf.keras.layers.InputLayer(input_shape=(n_features,)))
    modelo.add(tf.keras.layers.BatchNormalization())

    modelo.add(tf.keras.layers.Dense(128, activation='relu', kernel_regularizer=l2_reg))
    modelo.add(tf.keras.layers.BatchNormalization())
    modelo.add(tf.keras.layers.Dropout(0.3))

    modelo.add(tf.keras.layers.Dense(64, activation='relu', kernel_regularizer=l2_reg))
    modelo.add(tf.keras.layers.BatchNormalization())
    modelo.add(tf.keras.layers.Dropout(0.2))

    modelo.add(tf.keras.layers.Dense(32, activation='relu', kernel_regularizer=l2_reg))
    modelo.add(tf.keras.layers.BatchNormalization())

    modelo.add(tf.keras.layers.Dense(1, activation='sigmoid', kernel_regularizer=l2_reg))

    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return modelo


def salvar_modelo(modelo: Sequential, caminho: str = MODELO_PATH) -> None:
    """Salva o modelo em disco (h5 + keras) com backup diÃ¡rio Ãºnico (sobrescreve).

    ATOMICIDADE: grava primeiro em arquivo temporÃ¡rio e usa os.replace()
    para a troca final. Assim o modelo principal nunca fica corrompido se
    o processo for morto no meio do save.
    """
    try:
        caminho_h5_abs = os.path.abspath(caminho)
        print(f"[SALVAR_MODELO] Iniciando save: {caminho_h5_abs}")

        # === BACKUP DIÃRIO: MÃX 1 POR DIA, SOBRESCREVENDO ===
        hoje = datetime.now().strftime("%Y%m%d")
        backup_diario = f"{caminho}.backup_{hoje}"
        if os.path.exists(caminho):
            shutil.copy2(caminho, backup_diario)
            logging.info(f"ðŸ“¦ Backup diÃ¡rio sobrescrito: {backup_diario}")

        # Remove backups antigos (timestamps) se existirem de versÃµes anteriores
        backup_pattern = f"{caminho}.backup_*"
        for antigo in glob.glob(backup_pattern):
            if antigo != backup_diario:
                try:
                    os.remove(antigo)
                except Exception:
                    pass

        # === SAVE ATÃ”MICO: temp + os.replace (evita corrupÃ§Ã£o em crash) ===
        caminho_keras = caminho.replace('.h5', '.keras')
        # ⚠️ FIX (01/08/2026): TF só aceita extensões .h5 ou .keras — .tmp_atomic causava
        # "Invalid filepath extension" silencioso. Usar _tmp.h5 / _tmp.keras (extensão válida).
        tmp_h5 = caminho.replace('.h5', '_tmp.h5')
        tmp_keras = caminho_keras.replace('.keras', '_tmp.keras')

        modelo.save(tmp_h5)
        if os.path.exists(tmp_keras):
            try:
                os.remove(tmp_keras)
            except Exception:
                pass
        modelo.save(tmp_keras)
        os.replace(tmp_h5, caminho_h5_abs)
        os.replace(tmp_keras, os.path.abspath(caminho_keras))

        tamanho = os.path.getsize(caminho_h5_abs)
        tamanho_k = os.path.getsize(os.path.abspath(caminho_keras))
        print(f"[SALVAR_MODELO] H5 salvo: {tamanho} bytes | Keras: {tamanho_k} bytes")
        logging.info(f"Modelo H5 salvo: {tamanho} bytes")

    except Exception as e:
        print(f"[SALVAR_MODELO] ERRO: {type(e).__name__}: {e}")
        logging.error(f"Erro ao salvar modelo: {type(e).__name__}: {e}")


def carregar_modelo(caminho: str = MODELO_PATH) -> Optional[Sequential]:
    """Carrega o modelo Keras ou cria um novo se nÃ£o existir ou estiver corrompido."""
    try:
        if os.path.exists(caminho):
            # Tenta carregar o modelo existente
            modelo = load_model(caminho)

            # Verifica compatibilidade bÃ¡sica
            expected_features = N_FEATURES
            test_input = np.zeros((1, expected_features), dtype=np.float32)
            modelo.predict(test_input, verbose=0)

            logging.info(f"âœ… Modelo de IA carregado com sucesso de {caminho}")
            return modelo
        else:
            logging.info(
                "ðŸ“‚ Modelo nÃ£o encontrado. Criando um novo cÃ©rebro do zero...")
            return criar_modelo_neural(N_FEATURES)
    except Exception as e:
        logging.error(
            f"âš ï¸ Erro ao carregar modelo ({e}). Resetando para evitar travamento...")
        # Se o arquivo estiver corrompido, removemos para criar um novo
        if os.path.exists(caminho):
            try:
                # Backup do corrompido antes de deletar
                os.rename(caminho, f"{caminho}.corrompido_{int(time.time())}")
            except:
                try:
                    os.remove(caminho)
                except:
                    pass
        return criar_modelo_neural(N_FEATURES)


def verificar_e_proteger_modelo() -> bool:
    """PROTEÃ‡ÃƒO TOTAL DO MODELO - Verifica e recupera automaticamente se necessÃ¡rio."""
    try:
        modelo_principal = MODELO_PATH
        logging.info(
            f"ðŸ” Verificando integridade do modelo: {modelo_principal}")

        # Verifica se modelo principal existe
        if os.path.exists(modelo_principal):
            # Testa se o modelo pode ser carregado
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    test_model = load_model(modelo_principal)
                logging.debug("âœ… Modelo principal Ã­ntegro e carregÃ¡vel")
                return True
            except Exception as e:
                logging.warning(f"âš ï¸ Modelo principal corrompido: {e}")
                # Modelo existe mas estÃ¡ corrompido - tenta recuperar
                return recuperar_modelo_automaticamente()
        else:
            logging.warning(
                "âš ï¸ Modelo principal nÃ£o encontrado - tentando recuperar")
            return recuperar_modelo_automaticamente()

    except Exception as e:
        logging.error(f"âŒ Erro na verificaÃ§Ã£o do modelo: {e}")
        return False


def recuperar_modelo_automaticamente() -> bool:
    """ðŸš‘ RECUPERAÃ‡ÃƒO AUTOMÃTICA - Encontra e restaura backup do modelo."""
    try:
        modelo_principal = MODELO_PATH

        # Lista todas as possibilidades de backup
        opcoes_backup = []

        # 1. Backup diÃ¡rio mais recente
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

        # 4. Backups antigos do prÃ³prio sistema
        backups_antigos = sorted(
            glob.glob(f"{modelo_principal}.backup_*"), reverse=True)
        opcoes_backup.extend(backups_antigos)

        # Remove duplicatas mantendo ordem
        opcoes_backup = list(dict.fromkeys(opcoes_backup))

        logging.info(f"ðŸ” Encontrados {len(opcoes_backup)} backups possÃ­veis")

        # Tenta recuperar do backup mais recente
        for backup_path in opcoes_backup:
            try:
                logging.info(f"ðŸš‘ Tentando recuperar de: {backup_path}")

                # Testa se o backup Ã© vÃ¡lido
                test_model = load_model(backup_path)

                # Se chegou aqui, o backup Ã© vÃ¡lido - restaura
                shutil.copy2(backup_path, modelo_principal)
                logging.info(
                    f"âœ… MODELO RECUPERADO com sucesso de: {backup_path}")

                # Verifica se a recuperaÃ§Ã£o funcionou
                final_test = load_model(modelo_principal)
                logging.info("ðŸŽ‰ RECUPERAÃ‡ÃƒO CONFIRMADA - Modelo funcionando!")
                return True

            except Exception as e:
                logging.warning(f"âŒ Backup {backup_path} invÃ¡lido: {e}")
                continue

        # Se chegou aqui, nenhum backup funcionou
        logging.error("ðŸ’€ NENHUM BACKUP VÃLIDO ENCONTRADO!")
        logging.info("ðŸ”§ Criando novo modelo do zero (Ãºltima opÃ§Ã£o)")
        return False

    except Exception as e:
        logging.error(f"âŒ Erro na recuperaÃ§Ã£o automÃ¡tica: {e}")
        return False
# endregion

# region [Trading]


def calcular_score_distancia(preco_entrada: float, preco_saida: float, sl: float, tp: float) -> float:
    """Calcula um score adicional baseado na distÃ¢ncia que o preÃ§o chegou do TP/SL.

    Returns:
        float: Score entre -1 e 1, onde:
            1.0 = Atingiu TP
            -1.0 = Atingiu SL
            Valores intermediÃ¡rios baseados na proximidade
            Com TP=0: score baseado apenas na distÃ¢ncia do SL (saÃ­da dinÃ¢mica)
    """
    # Calcula distÃ¢ncias totais
    dist_total_sl = abs(sl - preco_entrada)
    if dist_total_sl == 0:
        dist_total_sl = 1.0  # Evita divisÃ£o por zero

    # Calcula distÃ¢ncia percorrida
    dist_percorrida = preco_saida - preco_entrada

    # Com TP=0 (saÃ­da dinÃ¢mica): score baseado na direÃ§Ã£o e magnitude
    if tp == 0 or abs(tp - preco_entrada) < 0.01:
        # Sem TP definido: score proporcional ao lucro/prejuÃ­zo em relaÃ§Ã£o ao SL
        # Lucro positivo â†’ score positivo; PrejuÃ­zo â†’ score negativo
        score = dist_percorrida / dist_total_sl
        return max(min(score, 1.0), -1.0)

    dist_total_tp = abs(tp - preco_entrada)
    if dist_total_tp == 0:
        dist_total_tp = 1.0

    # Com TP definido: lÃ³gica original
    if ((tp > preco_entrada and preco_saida > preco_entrada) or
            (tp < preco_entrada and preco_saida < preco_entrada)):
        score = dist_percorrida / dist_total_tp
    else:
        score = -dist_percorrida / dist_total_sl

    return max(min(score, 1.0), -1.0)


def aguardar_abertura():
    agora = datetime.now().time()
    if agora < dtime(9, 0):
        segundos = (datetime.combine(datetime.today(),
                                     dtime(9, 0)) - datetime.now()).seconds
        logging.info(
            f"â³ Aguardando abertura do pregÃ£o em {segundos//60}m{segundos % 60}sâ€¦")
        while segundos > 0 and not verificar_parada_gracil():
            time.sleep(min(60, segundos))
            segundos -= 60


def aguardar_fechamento():
    agora = datetime.now().time()
    if agora >= dtime(17, 35):  # ApÃ³s encerramento automÃ¡tico
        segundos = ((datetime.combine(datetime.today(), dtime(
            23, 59)) - datetime.now()).seconds + 60)
        logging.info(f"ðŸŒ™ PregÃ£o encerrado. Dormindo atÃ© o prÃ³ximo dia Ãºtilâ€¦")
        while segundos > 0 and not verificar_parada_gracil():
            time.sleep(min(60, segundos))
            segundos -= 60


# region [Detector de CodificaÃ§Ã£o Robusto]
class CSVEncodingDetector:
    """Detector robusto de codificaÃ§Ã£o para arquivos CSV do EA."""

    def __init__(self):
        """Inicializa o detector com configuraÃ§Ãµes otimizadas."""
        # Lista ordenada de codificaÃ§Ãµes por prioridade (mais comuns primeiro)
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

        # Cache de codificaÃ§Ã£o bem-sucedida por arquivo
        self.encoding_cache = {}
        self.cache_ttl = 300  # 5 minutos de TTL para cache

        # PadrÃµes BOM (Byte Order Mark)
        self.bom_patterns = {
            b'\xff\xfe\x00\x00': 'utf-32-le',
            b'\x00\x00\xfe\xff': 'utf-32-be',
            b'\xff\xfe': 'utf-16-le',
            b'\xfe\xff': 'utf-16-be',
            b'\xef\xbb\xbf': 'utf-8'
        }

    def detect_bom(self, file_path: str) -> Optional[str]:
        """Detecta codificaÃ§Ã£o atravÃ©s do BOM (Byte Order Mark).

        Args:
            file_path: Caminho para o arquivo

        Returns:
            CodificaÃ§Ã£o detectada ou None se nÃ£o houver BOM
        """
        try:
            with open(file_path, 'rb') as f:
                # LÃª os primeiros 4 bytes para detectar BOM
                bom_bytes = f.read(4)

            # Verifica padrÃµes BOM em ordem de tamanho (maior primeiro)
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
        """Detecta codificaÃ§Ã£o analisando o conteÃºdo do arquivo.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            CodificaÃ§Ã£o mais provÃ¡vel ou None
        """
        try:
            # LÃª uma amostra do arquivo para anÃ¡lise
            with open(file_path, 'rb') as f:
                sample = f.read(1024)  # Primeiros 1KB

            if not sample:
                return None

            # Tenta decodificar com cada codificaÃ§Ã£o
            encoding_scores = {}

            for encoding in self.encoding_priority:
                try:
                    decoded = sample.decode(encoding)

                    # Calcula score baseado em caracterÃ­sticas do conteÃºdo
                    score = self._calculate_content_score(decoded, encoding)
                    encoding_scores[encoding] = score

                except (UnicodeDecodeError, UnicodeError):
                    continue

            if not encoding_scores:
                return None

            # Retorna codificaÃ§Ã£o com maior score
            best_encoding = max(encoding_scores, key=encoding_scores.get)
            best_score = encoding_scores[best_encoding]

            logging.debug(
                f"[CSVEncodingDetector] Melhor codificaÃ§Ã£o por conteÃºdo: {best_encoding} (score: {best_score:.2f})")

            # SÃ³ retorna se o score for razoÃ¡vel
            return best_encoding if best_score > 0.5 else None

        except Exception as e:
            logging.debug(
                f"[CSVEncodingDetector] Erro na detecÃ§Ã£o por conteÃºdo: {e}")
            return None

    def _calculate_content_score(self, content: str, encoding: str) -> float:
        """Calcula score de qualidade para uma decodificaÃ§Ã£o.

        Args:
            content: ConteÃºdo decodificado
            encoding: CodificaÃ§Ã£o utilizada

        Returns:
            Score de 0.0 a 1.0 (maior = melhor)
        """
        if not content:
            return 0.0

        score = 0.0

        # Bonus para caracteres ASCII vÃ¡lidos (nÃºmeros, vÃ­rgulas, quebras de linha)
        ascii_chars = sum(1 for c in content if ord(c) < 128)
        ascii_ratio = ascii_chars / len(content)
        score += ascii_ratio * 0.4

        # Bonus para padrÃµes esperados no CSV do book (nÃºmeros e vÃ­rgulas)
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

        # Bonus para codificaÃ§Ãµes mais comuns
        encoding_bonus = {
            'utf-8': 0.2,
            'utf-16-le': 0.1,
            'ascii': 0.15,
            'latin-1': 0.05
        }
        score += encoding_bonus.get(encoding, 0.0)

        return max(0.0, min(1.0, score))

    def get_cached_encoding(self, file_path: str) -> Optional[str]:
        """ObtÃ©m codificaÃ§Ã£o do cache se ainda vÃ¡lida.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            CodificaÃ§Ã£o em cache ou None se expirada/inexistente
        """
        if file_path not in self.encoding_cache:
            return None

        cached_data = self.encoding_cache[file_path]
        cache_time = cached_data.get('timestamp', 0)

        # Verifica se cache ainda Ã© vÃ¡lido
        if time.time() - cache_time > self.cache_ttl:
            del self.encoding_cache[file_path]
            return None

        encoding = cached_data.get('encoding')
        logging.debug(
            f"[CSVEncodingDetector] Usando codificaÃ§Ã£o em cache: {encoding}")
        return encoding

    def cache_encoding(self, file_path: str, encoding: str):
        """Armazena codificaÃ§Ã£o bem-sucedida no cache.

        Args:
            file_path: Caminho para o arquivo
            encoding: CodificaÃ§Ã£o que funcionou
        """
        self.encoding_cache[file_path] = {
            'encoding': encoding,
            'timestamp': time.time()
        }
        logging.debug(
            f"[CSVEncodingDetector] CodificaÃ§Ã£o {encoding} armazenada em cache")

    def detect_encoding(self, file_path: str) -> List[str]:
        """Detecta a melhor codificaÃ§Ã£o para um arquivo CSV.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            Lista ordenada de codificaÃ§Ãµes para tentar (mais provÃ¡vel primeiro)
        """
        if not os.path.exists(file_path):
            return self.encoding_priority.copy()

        # 1. Verifica cache primeiro
        cached_encoding = self.get_cached_encoding(file_path)
        if cached_encoding:
            # Move codificaÃ§Ã£o em cache para o inÃ­cio da lista
            encodings = [cached_encoding] + \
                [e for e in self.encoding_priority if e != cached_encoding]
            return encodings

        # 2. Tenta detectar por BOM
        bom_encoding = self.detect_bom(file_path)
        if bom_encoding:
            # Move codificaÃ§Ã£o detectada por BOM para o inÃ­cio
            encodings = [bom_encoding] + \
                [e for e in self.encoding_priority if e != bom_encoding]
            return encodings

        # 3. Tenta detectar por conteÃºdo
        content_encoding = self.detect_by_content(file_path)
        if content_encoding:
            # Move codificaÃ§Ã£o detectada por conteÃºdo para o inÃ­cio
            encodings = [content_encoding] + \
                [e for e in self.encoding_priority if e != content_encoding]
            return encodings

        # 4. Retorna lista padrÃ£o se nenhuma detecÃ§Ã£o funcionou
        return self.encoding_priority.copy()


# InstÃ¢ncia global do detector
_csv_encoding_detector = CSVEncodingDetector()

# region [Validador de Dados do Book]


class CSVDataValidator:
    """Validador robusto de dados do book de ofertas."""

    def __init__(self):
        """Inicializa o validador com configuraÃ§Ãµes de validaÃ§Ã£o."""
        # Limites de validaÃ§Ã£o
        self.min_volume = 1
        self.max_volume = 100000  # Volume mÃ¡ximo razoÃ¡vel por nÃ­vel
        self.min_levels = 1       # MÃ­nimo de nÃ­veis por lado
        self.max_levels = 50      # MÃ¡ximo de nÃ­veis por lado
        self.min_total_volume = 10  # Volume total mÃ­nimo por lado
        self.max_total_volume = 1000000  # Volume total mÃ¡ximo por lado

        # ConfiguraÃ§Ãµes de sanitizaÃ§Ã£o
        self.enable_sanitization = True
        self.strict_mode = False  # Se True, rejeita dados com qualquer problema

        # EstatÃ­sticas de validaÃ§Ã£o
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
            side: "bids" ou "asks" para identificaÃ§Ã£o

        Returns:
            DicionÃ¡rio com resultado da validaÃ§Ã£o
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

        # ValidaÃ§Ã£o bÃ¡sica de tipos
        if not all(isinstance(v, (int, float)) for v in volumes):
            result['issues'].append(f"Tipos invÃ¡lidos em {side}")
            if not self.enable_sanitization:
                result['valid'] = False
                return result

        # SanitizaÃ§Ã£o e validaÃ§Ã£o de volumes individuais
        sanitized = []
        for i, volume in enumerate(volumes):
            try:
                # Converte para int se necessÃ¡rio
                vol_int = int(volume) if isinstance(volume, float) else volume

                # Valida limites
                if vol_int < self.min_volume:
                    result['issues'].append(
                        f"Volume muito baixo em {side}[{i}]: {vol_int}")
                    if self.enable_sanitization:
                        continue  # Remove volume invÃ¡lido
                    else:
                        result['valid'] = False
                        return result

                if vol_int > self.max_volume:
                    result['issues'].append(
                        f"Volume muito alto em {side}[{i}]: {vol_int}")
                    if self.enable_sanitization:
                        vol_int = self.max_volume  # Limita ao mÃ¡ximo
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

        # ValidaÃ§Ã£o de contagem de nÃ­veis
        if len(sanitized) < self.min_levels:
            result['issues'].append(
                f"Poucos nÃ­veis em {side}: {len(sanitized)} < {self.min_levels}")
            if self.strict_mode:
                result['valid'] = False
                return result

        if len(sanitized) > self.max_levels:
            result['issues'].append(
                f"Muitos nÃ­veis em {side}: {len(sanitized)} > {self.max_levels}")
            if self.enable_sanitization:
                result['sanitized_volumes'] = sanitized[:self.max_levels]
                result['sanitized_count'] = self.max_levels
                result['total_volume'] = sum(result['sanitized_volumes'])
            elif self.strict_mode:
                result['valid'] = False
                return result

        # ValidaÃ§Ã£o de volume total
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
        """Detecta padrÃµes suspeitos nos dados do book.

        Args:
            bids: Lista de volumes de compra
            asks: Lista de volumes de venda

        Returns:
            Lista de alertas sobre padrÃµes suspeitos
        """
        alerts = []

        if not bids or not asks:
            return alerts

        # PadrÃ£o 1: Todos os volumes iguais (suspeito)
        if len(set(bids)) == 1 and len(bids) > 3:
            alerts.append(f"Todos os volumes BID sÃ£o iguais: {bids[0]}")

        if len(set(asks)) == 1 and len(asks) > 3:
            alerts.append(f"Todos os volumes ASK sÃ£o iguais: {asks[0]}")

        # PadrÃ£o 2: DesequilÃ­brio extremo
        total_bids = sum(bids)
        total_asks = sum(asks)

        if total_bids > 0 and total_asks > 0:
            ratio = max(total_bids, total_asks) / min(total_bids, total_asks)
            if ratio > 10:  # DesequilÃ­brio de 10:1
                alerts.append(
                    f"DesequilÃ­brio extremo BID/ASK: {total_bids}/{total_asks} (ratio: {ratio:.1f})")

        # PadrÃ£o 3: Volumes muito baixos generalizados
        avg_bid = sum(bids) / len(bids) if bids else 0
        avg_ask = sum(asks) / len(asks) if asks else 0

        if avg_bid < 5 and avg_ask < 5:
            alerts.append(
                f"Volumes mÃ©dios muito baixos: BID={avg_bid:.1f}, ASK={avg_ask:.1f}")

        # PadrÃ£o 4: SequÃªncia suspeita (nÃºmeros consecutivos)
        if len(bids) >= 5:
            consecutive_count = 0
            for i in range(1, len(bids)):
                if abs(bids[i] - bids[i-1]) <= 1:
                    consecutive_count += 1
                else:
                    consecutive_count = 0
                if consecutive_count >= 4:  # 5 nÃºmeros quase consecutivos
                    alerts.append("SequÃªncia suspeita detectada em BIDs")
                    break

        return alerts

    def validate_book_data(self, book_data: Dict[str, List[int]]) -> Dict[str, Any]:
        """Valida dados completos do book de ofertas.

        Args:
            book_data: DicionÃ¡rio com 'bids' e 'asks'

        Returns:
            Resultado completo da validaÃ§Ã£o com dados sanitizados
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
            result['issues'].append("Dados do book invÃ¡lidos ou nulos")
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

        # Detecta padrÃµes suspeitos
        result['suspicious_patterns'] = self.detect_suspicious_patterns(
            bid_validation['sanitized_volumes'],
            ask_validation['sanitized_volumes']
        )

        # EstatÃ­sticas
        result['statistics'] = {
            'bid_levels': bid_validation['sanitized_count'],
            'ask_levels': ask_validation['sanitized_count'],
            'total_bid_volume': bid_validation['total_volume'],
            'total_ask_volume': ask_validation['total_volume'],
            'total_liquidity': bid_validation['total_volume'] + ask_validation['total_volume'],
            'bid_ask_ratio': (bid_validation['total_volume'] / ask_validation['total_volume'])
            if ask_validation['total_volume'] > 0 else float('inf')
        }

        # Determina recomendaÃ§Ã£o final
        if result['issues'] or result['suspicious_patterns']:
            if self.enable_sanitization and not self.strict_mode:
                result['recommendation'] = 'sanitize'
                self.validation_stats['sanitized_data'] += 1
            else:
                result['recommendation'] = 'reject'
                result['valid'] = False
                self.validation_stats['rejected_data'] += 1
                return result

        # Atualiza estatÃ­sticas de issues comuns
        for issue in result['issues']:
            issue_type = issue.split(':')[0] if ':' in issue else issue
            self.validation_stats['common_issues'][issue_type] = self.validation_stats['common_issues'].get(
                issue_type, 0) + 1

        self.validation_stats['successful_validations'] += 1
        return result

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Retorna estatÃ­sticas de validaÃ§Ã£o acumuladas."""
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
        """Reseta as estatÃ­sticas de validaÃ§Ã£o."""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'sanitized_data': 0,
            'rejected_data': 0,
            'common_issues': {}
        }


# InstÃ¢ncia global do validador
_csv_data_validator = CSVDataValidator()

# region [Sistema de Retry com Backoff Exponencial]


class RetryManager:
    """Gerenciador de tentativas com backoff exponencial para operaÃ§Ãµes de I/O."""

    def __init__(self, max_retries: int = 5, base_delay: float = 0.1, max_delay: float = 2.0):
        """Inicializa o gerenciador de retry.

        Args:
            max_retries: NÃºmero mÃ¡ximo de tentativas
            base_delay: Delay inicial em segundos
            max_delay: Delay mÃ¡ximo em segundos
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # EstatÃ­sticas de retry
        self.retry_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'error_types': {},
            'avg_retries_per_operation': 0.0
        }

    def calculate_delay(self, attempt: int) -> float:
        """Calcula o delay para uma tentativa especÃ­fica usando backoff exponencial.

        Args:
            attempt: NÃºmero da tentativa (0-based)

        Returns:
            Delay em segundos
        """
        # Backoff exponencial: base_delay * (2 ^ attempt)
        delay = self.base_delay * (2 ** attempt)

        # Adiciona jitter (variaÃ§Ã£o aleatÃ³ria) para evitar thundering herd
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter

        # Limita ao delay mÃ¡ximo
        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determina se deve tentar novamente baseado no tipo de erro e tentativa.

        Args:
            exception: ExceÃ§Ã£o que ocorreu
            attempt: NÃºmero da tentativa atual

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
            # Problemas de codificaÃ§Ã£o (pode ser temporÃ¡rio)
            UnicodeDecodeError,
            IOError               # Problemas de entrada/saÃ­da
        )

        return isinstance(exception, retryable_errors)

    def get_error_strategy(self, exception: Exception) -> Dict[str, Any]:
        """Retorna estratÃ©gia especÃ­fica para cada tipo de erro.

        Args:
            exception: ExceÃ§Ã£o que ocorreu

        Returns:
            DicionÃ¡rio com estratÃ©gia de tratamento
        """
        if isinstance(exception, PermissionError):
            return {
                'delay_multiplier': 1.5,  # Aguarda mais tempo para arquivo em uso
                'max_retries': 3,         # Menos tentativas para nÃ£o sobrecarregar
                'description': 'Arquivo em uso pelo EA'
            }

        elif isinstance(exception, FileNotFoundError):
            return {
                'delay_multiplier': 1.0,  # Delay normal
                'max_retries': 4,         # Mais tentativas para aguardar criaÃ§Ã£o
                'description': 'Arquivo nÃ£o encontrado'
            }

        elif isinstance(exception, UnicodeDecodeError):
            return {
                'delay_multiplier': 0.5,  # Delay menor, problema pode ser rÃ¡pido
                'max_retries': 2,         # Poucas tentativas, detector jÃ¡ tenta outras codificaÃ§Ãµes
                'description': 'Erro de codificaÃ§Ã£o'
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
        """Executa uma operaÃ§Ã£o com retry automÃ¡tico.

        Args:
            operation_func: FunÃ§Ã£o a ser executada
            *args: Argumentos posicionais para a funÃ§Ã£o
            **kwargs: Argumentos nomeados para a funÃ§Ã£o

        Returns:
            Resultado da operaÃ§Ã£o ou None se todas as tentativas falharam
        """
        self.retry_stats['total_operations'] += 1
        last_exception = None

        # +1 para incluir tentativa inicial
        for attempt in range(self.max_retries + 1):
            try:
                # Tenta executar a operaÃ§Ã£o
                result = operation_func(*args, **kwargs)

                # Sucesso!
                if attempt > 0:  # Se houve retry
                    self.retry_stats['total_retries'] += attempt
                    logging.info(
                        f"[RetryManager] OperaÃ§Ã£o bem-sucedida apÃ³s {attempt} tentativas")

                self.retry_stats['successful_operations'] += 1
                self._update_avg_retries()
                return result

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Atualiza estatÃ­sticas de erro
                self.retry_stats['error_types'][error_type] = self.retry_stats['error_types'].get(
                    error_type, 0) + 1

                # Verifica se deve tentar novamente
                if not self.should_retry(e, attempt):
                    logging.debug(
                        f"[RetryManager] NÃ£o tentando novamente: {error_type} (tentativa {attempt + 1})")
                    break

                # ObtÃ©m estratÃ©gia especÃ­fica para o erro
                strategy = self.get_error_strategy(e)

                # Calcula delay ajustado pela estratÃ©gia
                base_delay = self.calculate_delay(attempt)
                adjusted_delay = base_delay * strategy['delay_multiplier']

                logging.debug(f"[RetryManager] {strategy['description']} - Tentativa {attempt + 1}/{self.max_retries + 1}, "
                              f"aguardando {adjusted_delay:.2f}s")

                # Aguarda antes da prÃ³xima tentativa
                time.sleep(adjusted_delay)

        # Todas as tentativas falharam
        self.retry_stats['failed_operations'] += 1
        self.retry_stats['total_retries'] += self.max_retries
        self._update_avg_retries()

        logging.warning(f"[RetryManager] OperaÃ§Ã£o falhou apÃ³s {self.max_retries + 1} tentativas. "
                        f"Ãšltimo erro: {last_exception}")

        return None

    def _update_avg_retries(self):
        """Atualiza a mÃ©dia de retries por operaÃ§Ã£o."""
        if self.retry_stats['total_operations'] > 0:
            self.retry_stats['avg_retries_per_operation'] = self.retry_stats['total_retries'] / \
                self.retry_stats['total_operations']

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatÃ­sticas do gerenciador de retry."""
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
        """Reseta as estatÃ­sticas do retry manager."""
        self.retry_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'error_types': {},
            'avg_retries_per_operation': 0.0
        }


# InstÃ¢ncia global do retry manager
_retry_manager = RetryManager(max_retries=5, base_delay=0.1, max_delay=2.0)
# endregion


def ler_book_nativo() -> Optional[Dict[str, Any]]:
    """
    ========================================================================
    ðŸ“¡ LEITURA NATIVA DO BOOK (Depth of Market) DIRETO DO METATRADER 5
    ------------------------------------------------------------------------
    Substitui a antiga leitura do arquivo book_data_wdo.csv gerado pelo EA.
    Os dados vÃªm da memÃ³ria do terminal via mt5.market_book_get(SYMBOL),
    eliminando latÃªncia de escrita/leitura em disco e "dados congelados".

    A subscriÃ§Ã£o Ã© feita uma Ãºnica vez com mt5.market_book_add(SYMBOL) na
    inicializaÃ§Ã£o (funÃ§Ã£o inicializar_mt5) e cancelada com
    mt5.market_book_release(SYMBOL) no encerramento.

    Estrutura BookInfo retornada pelo MT5 (ver documentaÃ§Ã£o oficial):
        type=1 -> ordem de VENDA  (ASK, preÃ§os acima do mercado)
        type=2 -> ordem de COMPRA (BID, preÃ§os abaixo do mercado)
        type=3 -> venda a mercado / type=4 -> compra a mercado
    Convertemos para o MESMO formato dict que o resto do cÃ³digo jÃ¡ usa:
        {
          'bids': [{'price': p, 'volume': v}, ...],  # ordenado do melhor p/ pior
          'asks': [{'price': p, 'volume': v}, ...],
          'total_bid_volume': int,
          'total_ask_volume': int,
          'symbol': SYMBOL,
          'relevancia': True
        }
    Retorna None se o book estiver vazio (mercado fechado / sem dados).
    ========================================================================
    """
    global SYMBOL

    if not SYMBOL:
        return None

    try:
        items = mt5.market_book_get(SYMBOL)
    except Exception as e:
        logging.debug(f"[ler_book_nativo] Erro ao obter book nativo: {e}")
        return None

    if not items:
        # Book vazio: normalmente mercado fechado ou terminal ainda sincronizando
        return None

    bids: List[Dict[str, float]] = []
    asks: List[Dict[str, float]] = []

    for it in items:
        # it pode ser BookInfo (namedtuple) â€” acessa por atributo
        tipo = getattr(it, 'type', None)
        preco = getattr(it, 'price', 0.0)
        # volume_dbl Ã© mais preciso; cai para volume se nÃ£o existir
        vol = getattr(it, 'volume_dbl', None)
        if vol is None or vol == 0:
            vol = getattr(it, 'volume', 0)

        if vol <= 0:
            continue

        registro = {'price': float(preco), 'volume': float(vol)}

        # type 2/4 = COMPRA (BID) | type 1/3 = VENDA (ASK)
        if tipo in (2, 4):
            bids.append(registro)
        elif tipo in (1, 3):
            asks.append(registro)

    if not bids or not asks:
        return None

    # Ordena: melhor BID = maior preÃ§o primeiro | melhor ASK = menor preÃ§o primeiro
    bids.sort(key=lambda x: x['price'], reverse=True)
    asks.sort(key=lambda x: x['price'])

    total_bid_volume = sum(b['volume'] for b in bids)
    total_ask_volume = sum(a['volume'] for a in asks)

    # Timestamp = relÃ³gio LOCAL (mesma base de timestamp_inicializacao = time.time()).
    # âš ï¸ NÃƒO usar tick.time do MT5 aqui: ele vem no fuso do servidor da corretora
    # (nÃ£o Ã© POSIX/UTC local) e a TRAVA o interpretaria como "dado antigo", bloqueando
    # TODAS as operaÃ§Ãµes. O book nativo Ã© sempre AO VIVO (se o mercado fecha, o
    # market_book_get retorna vazio e jÃ¡ saÃ­mos com None acima), entÃ£o o problema de
    # "dado velho de sessÃ£o anterior" â€” que era exclusivo do CSV/EA â€” nÃ£o existe aqui.
    ts_now = time.time()

    return {
        'symbol': SYMBOL,
        'bids': bids,
        'asks': asks,
        'total_bid_volume': total_bid_volume,
        'total_ask_volume': total_ask_volume,
        'timestamp': ts_now,
        'relevancia': True,
    }


# ========================================================================
# ðŸ“¡ LEITURA DO BOOK DO DÃ“LAR CHEIO (DOL) â€” REFERÃŠNCIA INSTITUCIONAL
# ------------------------------------------------------------------------
# O DOL Ã© onde os grandes players (bancos, fundos) operam de verdade.
# O WDO Ã© replicado por HFTs que espelham o DOL com milissegundos de
# atraso. Ler o DOL permite antecipar movimentos do WDO.
# ========================================================================

def ler_book_dol() -> Optional[Dict[str, Any]]:
    """LÃª o book do DÃ³lar Cheio (DOL) â€” mesmo formato de ler_book_nativo."""
    global SYMBOL_DOL
    if not SYMBOL_DOL:
        return None
    try:
        items = mt5.market_book_get(SYMBOL_DOL)
    except Exception:
        return None
    if not items:
        return None

    bids: List[Dict[str, float]] = []
    asks: List[Dict[str, float]] = []

    for it in items:
        tipo = getattr(it, 'type', None)
        preco = getattr(it, 'price', 0.0)
        vol = getattr(it, 'volume_dbl', None)
        if vol is None or vol == 0:
            vol = getattr(it, 'volume', 0)
        if vol <= 0:
            continue
        registro = {'price': float(preco), 'volume': float(vol)}
        if tipo == 2:  # BID
            bids.append(registro)
        elif tipo == 1:  # ASK
            asks.append(registro)

    if not bids and not asks:
        return None

    bids.sort(key=lambda x: x['price'], reverse=True)
    asks.sort(key=lambda x: x['price'])

    total_bid = sum(b['volume'] for b in bids)
    total_ask = sum(a['volume'] for a in asks)

    return {
        'symbol': SYMBOL_DOL,
        'bids': bids,
        'asks': asks,
        'total_bid_volume': total_bid,
        'total_ask_volume': total_ask,
        'timestamp': time.time(),
        'relevancia': True,
    }


def analisar_sinal_dol(book_dol: Optional[Dict]) -> Dict[str, Any]:
    """
    Analisa o book do DOL e retorna sinais de fluxo institucional.
    Retorna dict com:
      - ratio: desequilÃ­brio bid/ask (>1 = mais compras, <1 = mais vendas)
      - lado: "BUY", "SELL" ou "NEUTRO"
      - confianca: 0.0 a 1.0 (baseado no desequilÃ­brio)
      - volume_total: volume total do book DOL
      - presente: True se DOL estÃ¡ disponÃ­vel
    """
    resultado = {
        'presente': False,
        'ratio': 1.0,
        'lado': 'NEUTRO',
        'confianca': 0.0,
        'volume_total': 0,
        'maior_escora_bid': 0,
        'maior_escora_ask': 0,
    }

    if not book_dol or not book_dol.get('bids') or not book_dol.get('asks'):
        return resultado

    resultado['presente'] = True
    total_bid = book_dol.get('total_bid_volume', 0)
    total_ask = book_dol.get('total_ask_volume', 0)
    resultado['volume_total'] = total_bid + total_ask

    if total_bid <= 0 or total_ask <= 0:
        return resultado

    ratio = max(total_bid, total_ask) / min(total_bid, total_ask)
    resultado['ratio'] = ratio

    # Maior escora (ordem grande) de cada lado
    bids = book_dol.get('bids', [])
    asks = book_dol.get('asks', [])
    resultado['maior_escora_bid'] = max((b['volume'] for b in bids), default=0)
    resultado['maior_escora_ask'] = max((a['volume'] for a in asks), default=0)

    # Determina lado e confianÃ§a
    if total_bid > total_ask:
        resultado['lado'] = 'BUY'
        # ConfianÃ§a: quanto maior o ratio, mais confianÃ§a (mÃ¡x 1.0 em ratio 3.0+)
        resultado['confianca'] = min(ratio / 3.0, 1.0)
    elif total_ask > total_bid:
        resultado['lado'] = 'SELL'
        resultado['confianca'] = min(ratio / 3.0, 1.0)
    else:
        resultado['lado'] = 'NEUTRO'

    return resultado# ========================================================================
# ðŸ—‘ï¸ LEITURA VIA CSV/EA REMOVIDA (MUDANÃ‡A 1 â€” ARQUITETURA NATIVA)
# As antigas funÃ§Ãµes _ler_book_csv_core / ler_book_csv_with_retry / ler_book_csv
# foram eliminadas. Toda a leitura do book agora Ã© nativa via ler_book_nativo()
# (mt5.market_book_get). NÃ£o hÃ¡ mais dependÃªncia do EA MQL5 nem de arquivos CSV.
# ========================================================================


def inicializar_mt5() -> bool:
    global trailing_stop, balanceador, detector_modo, balanceador, detector_modo, circuit_breaker, saida_inteligente, sistema_confluencia

    aguardar_abertura()
    logging.info("ðŸ”„ Tentando inicializar o MetaTrader 5...")
    if not mt5.initialize(path=MT5_PATH):
        logging.error(f"âŒ Erro ao inicializar MT5: {mt5.last_error()}")
        return False
    logging.info("âœ… MetaTrader 5 inicializado com sucesso")

    # ===== INICIALIZAÃ‡ÃƒO DOS SUBSISTEMAS (silenciosa â€” sem propaganda) =====
    global filtro_horario, detector_tendencia, cooldown_sistema, filtro_spread, monitor_performance

    trailing_stop = TrailingStopInteligente()
    balanceador = BalanceadorOperacoes()
    detector_modo = DetectorModoMercado()
    circuit_breaker = CircuitBreakerEssencial()
    saida_inteligente = SaidaInteligentePositions()
    sistema_confluencia = SistemaConfluencia()
    filtro_horario = FiltroHorarioPremium()
    detector_tendencia = DetectorTendencia()
    cooldown_sistema = CooldownInteligente()
    filtro_spread = FiltroSpreadDinamico()
    monitor_performance = MonitorPerformance()
    logging.info(
        "ðŸ§© Subsistemas ativos: Trailing | Balanceamento | Modos | CircuitBreaker | "
        "SaÃ­daInteligente | ConfluÃªncia | HorÃ¡rio | TendÃªncia | Cooldown | Spread | Performance")

    # ===== ARQUITETURA NATIVA: BOOK DIRETO DO MT5 (SEM EA / SEM CSV) =====
    global SYMBOL
    terminal_info = mt5.terminal_info()
    if not terminal_info:
        logging.error("âŒ NÃ£o foi possÃ­vel obter informaÃ§Ãµes do terminal MT5")
        return False
    logging.info(
        "ðŸ“¡ Fonte de dados: BOOK NATIVO (mt5.market_book_get) â€” EA/CSV eliminados")

    # SeleÃ§Ã£o dinÃ¢mica do contrato WDO
    SYMBOL = get_front_month_symbol_dynamic("WDO")
    mt5.symbol_select(SYMBOL, True)

    # Subscreve o book (Depth of Market) do contrato na memÃ³ria do terminal.
    # A partir daqui ler_book_nativo() recebe atualizaÃ§Ãµes em tempo real.
    if mt5.market_book_add(SYMBOL):
        logging.info(f"[BOOK] Book nativo ATIVADO para {SYMBOL} (Depth of Market)")
    else:
        logging.warning(
            f"âš ï¸ market_book_add falhou para {SYMBOL}: {mt5.last_error()} "
            f"(o book pode ainda assim responder â€” seguindo)")

    # Extrai a validade do sÃ­mbolo (ex: WDOQ26 -> Q26)
    validade = SYMBOL[-3:] if len(SYMBOL) >= 3 else SYMBOL
    logging.info(
        f"âœ… Contrato WDO dinÃ¢mico selecionado: {SYMBOL} (venc.: {validade})")

    # ===== DÃ“LAR CHEIO (DOL) â€” REFERÃŠNCIA DE FLUXO INSTITUCIONAL =====
    global SYMBOL_DOL
    SYMBOL_DOL = get_front_month_symbol_dynamic("DOL")
    if SYMBOL_DOL:
        mt5.symbol_select(SYMBOL_DOL, True)
        if mt5.market_book_add(SYMBOL_DOL):
            logging.info(
                f"[BOOK DOL] Book nativo ATIVADO para {SYMBOL_DOL} (referÃªncia institucional)")
        else:
            logging.warning(
                f"âš ï¸ market_book_add falhou para DOL {SYMBOL_DOL}: {mt5.last_error()}")
    else:
        logging.warning(
            "âš ï¸ DOL nÃ£o encontrado â€” operando sem referÃªncia institucional")

    logging.info(
        f"ðŸŽ¯ ConfiguraÃ§Ã£o WDO: SL={SL_POINTS}pts, TP={TP_POINTS}pts, Vol={VOLUME_PADRAO}cc")
    logging.info(
        f"ðŸ“Š WDO Specs: Tick={TICK_SIZE}, TicksPorPonto={TICKS_POR_PONTO}, Magic={MAGIC_NUMBER}")
    logging.info(
        f"ðŸ’° Risk: MaxLoss={MAX_LOSS_DIARIO}, MaxSpread={MAX_SPREAD}pts, MinVol={MIN_VOLUME_BOOK}cc")

    return True


def obter_dados_mercado(symbol: str = None, timeframe: int = TIMEFRAME) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[str], Optional[Dict], Optional[float], Optional[int], Optional[float], Optional[float]]:
    """ObtÃ©m dados atuais do mercado USANDO O BOOK NATIVO DO MT5."""
    global SYMBOL
    if not hasattr(obter_dados_mercado, '_log_counter'):
        obter_dados_mercado._log_counter = 0
    if symbol is None:
        symbol = SYMBOL
    if symbol is None:
        logging.error("âŒ SYMBOL ainda nÃ£o foi definido!")
        return (None,) * 10

    # Pulso de standby: loga no mÃ¡ximo 1x a cada 60s (sÃ³ "sinal de vida" + mercado).
    # NÃƒO afeta o robÃ´ â€” ele continua lendo o book e decidindo a cada ciclo.
    log_time = _log_periodico('pulso_mercado', PULSO_LOG_INTERVALO_S)

    # Inicializa todas as variÃ¡veis com valores padrÃ£o para evitar erros
    close_price = 0.0
    total_bid_volume = 0.0
    total_ask_volume = 0.0
    spread = 0.0
    atr = 0.0
    candle_type = "doji"
    book_data = {}
    rsi_14 = 50.0
    volume_tick = 0

    try:
        # Verifica se Ã© fim de semana
        if datetime.now().weekday() > 4:  # 5 = SÃ¡bado, 6 = Domingo
            if log_time:
                logging.info("ðŸ“… Fim de semana: aguardando prÃ³ximo dia Ãºtil...")
            time.sleep(30)  # Dorme por 30 segundos durante fim de semana
            return (None,) * 10

        # ===== LEITURA NATIVA DO BOOK (DIRETO DO MT5, SEM EA/CSV) =====
        book_data = ler_book_nativo()
        if not book_data or not book_data.get('bids') or not book_data.get('asks'):
            if log_time:
                # âœ… MODO SNIPER: log reduzido â€” standby silencioso aguardando sinal institucional
                logging.debug(
                    "ðŸ˜´ Standby: Aguardando book nativo com liquidez do MT5...")
            # Dorme 1s sem sinal (book nativo Ã© rÃ¡pido, nÃ£o precisa 2s)
            time.sleep(1)
            return (None,) * 10

        # Calcula volumes totais do book do EA
        # CORREÃ‡ÃƒO: book_data agora contÃ©m dicionÃ¡rios com price/volume
        if isinstance(book_data['bids'][0], dict):
            # Formato JSON: [{"price": X, "volume": Y}, ...]
            total_bid_volume = sum(item['volume']
                                   for item in book_data['bids'])
            total_ask_volume = sum(item['volume']
                                   for item in book_data['asks'])
        else:
            # Formato legado: [volume1, volume2, ...]
            total_bid_volume = sum(book_data['bids'])
            total_ask_volume = sum(book_data['asks'])

        total_volume = total_bid_volume + total_ask_volume

        # Log de mercado â€” informaÃ§Ã£o REAL e Ãºtil: preÃ§o ao vivo, spread,
        # volumes BID/ASK, desequilÃ­brio e lado dominante do fluxo.
        if log_time:
            tick = mt5.symbol_info_tick(symbol)
            spread_atual = round(tick.ask - tick.bid, 1) if tick else 0
            preco_vivo = (tick.last if (tick and tick.last) else (
                tick.bid if tick else 0))
            if total_bid_volume > 0 and total_ask_volume > 0:
                ratio_book = max(total_bid_volume, total_ask_volume) / \
                    min(total_bid_volume, total_ask_volume)
            else:
                ratio_book = 0.0
            lado = "ðŸŸ¢COMPRA" if total_bid_volume > total_ask_volume else "ðŸ”´VENDA"
            obter_dados_mercado._log_counter += 1
            if obter_dados_mercado._log_counter % 5 == 1:
                logging.info(
                    f"ðŸ“Š {symbol} | PreÃ§o: {preco_vivo:.0f} | Spread: {spread_atual}pts | "
                    f"BID: {total_bid_volume:.0f} / ASK: {total_ask_volume:.0f} | "
                    f"DesequilÃ­brio: {ratio_book:.2f}x {lado}")

        # Verifica liquidez mÃ­nima
        if total_volume < MIN_VOLUME_BOOK:
            if log_time:
                logging.warning(
                    f"âŒ Liquidez insuficiente: {total_volume} < {MIN_VOLUME_BOOK}")
            return (None,) * 10

        # ObtÃ©m dados complementares do MT5
        tick_info = mt5.symbol_info_tick(symbol)
        symbol_info = get_cached_symbol_info(symbol)
        if tick_info is None:
            if log_time:
                logging.warning(f"âŒ Tick NULO para sÃ­mbolo {symbol}")
            return (None,) * 10
        if symbol_info is None:
            if log_time:
                logging.warning(f"âŒ Symbol_info NULO para sÃ­mbolo {symbol}")
            # Tenta reselecionar o sÃ­mbolo
            mt5.symbol_select(symbol, True)
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logging.error(
                    f"âŒ NÃ£o foi possÃ­vel obter info do sÃ­mbolo {symbol} mesmo apÃ³s reselecionar")
            return (None,) * 10

        # Calcula spread em pontos
        spread = ((tick_info.ask - tick_info.bid) /
                  symbol_info.point) / TICKS_POR_PONTO

        # Verifica spread mÃ¡ximo
        if spread > MAX_SPREAD:
            if log_time:
                logging.warning(f"âŒ Spread muito alto: {spread:.1f} pts")
            return (None,) * 10

        # ObtÃ©m dados de velas
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
        if rates is None or len(rates) < 2:
            if log_time:
                logging.warning("âŒ Rates insuficientes")
            return (None,) * 10

        # ObtÃ©m dados bÃ¡sicos primeiro (antes de cÃ¡lculos que podem falhar)
        last_candle = rates[-1]
        close_price = float(last_candle[4])  # close price da Ãºltima vela
        volume_tick = int(tick_info.volume)

        # Calcula indicadores
        df_rates = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])

        # Calcula ATR com tratamento de erro
        try:
            atr = calcular_atr(df_rates['high'].tolist(
            ), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)
        except Exception as e:
            logging.warning(f"âš ï¸ Erro no cÃ¡lculo ATR: {e}")
            atr = 50.0  # Valor padrÃ£o

        # Calcula tipo de vela com tratamento de
        try:
            candle_type = obter_nome_vela(
                last_candle[1], last_candle[4], last_candle[2], last_candle[3])
        except Exception as e:
            logging.warning(f"âš ï¸ Erro no tipo de vela: {e}")
            candle_type = "doji"

        # Calcula RSI com tratamento de erro
        try:
            rsi_14 = calcular_rsi(df_rates['close'].tolist(), 14)
        except Exception as e:
            logging.warning(f"âš ï¸ Erro no cÃ¡lculo RSI: {e}")
            rsi_14 = 50.0  # Valor padrÃ£o

        # Calcula Williams %R (Larry Williams) com tratamento de erro
        try:
            williams_r = calcular_williams_r(
                df_rates['high'].tolist(), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)
        except Exception as e:
            logging.warning(f"âš ï¸ Erro no cÃ¡lculo Williams %R: {e}")
            williams_r = -50.0  # Valor padrÃ£o

        # Log detalhado dos dados do EA
        if log_time:
            logging.debug(
                f"ðŸ“Š EA Data - Bid Vol: {total_bid_volume}, Ask Vol: {total_ask_volume}")

        return total_bid_volume, total_ask_volume, spread, atr, candle_type, book_data, rsi_14, volume_tick, close_price, williams_r

    except Exception as e:
        logging.error(f"âŒ Erro ao obter dados do mercado (EA): {e}")
        return (None,) * 10


def volume_crescente(n: int = 2, symbol: str = None, timeframe: int = TIMEFRAME) -> bool:
    """Verifica se o volume estÃ¡ crescente nos Ãºltimos n candles."""
    global SYMBOL
    if symbol is None:
        symbol = SYMBOL
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n + 1)
    if rates is None or len(rates) < n + 1:
        return False

    volumes = [rate[5] for rate in rates]  # rate[5] Ã© o volume
    for i in range(1, len(volumes)):
        if volumes[i] <= volumes[i-1]:
            return False
    return True


def obter_dados_multitf(symbol: str = None) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[int], Optional[int], Optional[int]]:
    """Coleta indicadores de M5, M15, M30 em paralelo sem interromper o loop M1."""
    global SYMBOL
    if symbol is None:
        symbol = SYMBOL
    if symbol is None:
        return (None,) * 15

    try:
        # M5
        rates5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 100)
        if rates5 is None or len(rates5) < 14:
            return (None,) * 15
        df5 = pd.DataFrame(rates5, columns=['time','open','high','low','close','tick_volume','spread','real_volume'])
        rsi5 = calcular_rsi(df5['close'].tolist(), 14)
        atr5 = calcular_atr(df5['high'].tolist(), df5['low'].tolist(), df5['close'].tolist(), 14)
        wr5 = calcular_williams_r(df5['high'].tolist(), df5['low'].tolist(), df5['close'].tolist(), 14)
        close5 = float(rates5[-1][4])
        vol5 = int(rates5[-1][5])

        # M15
        rates15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        if rates15 is None or len(rates15) < 14:
            return (None,) * 15
        df15 = pd.DataFrame(rates15, columns=['time','open','high','low','close','tick_volume','spread','real_volume'])
        rsi15 = calcular_rsi(df15['close'].tolist(), 14)
        atr15 = calcular_atr(df15['high'].tolist(), df15['low'].tolist(), df15['close'].tolist(), 14)
        wr15 = calcular_williams_r(df15['high'].tolist(), df15['low'].tolist(), df15['close'].tolist(), 14)
        close15 = float(rates15[-1][4])
        vol15 = int(rates15[-1][5])

        # M30
        rates30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 100)
        if rates30 is None or len(rates30) < 14:
            return (None,) * 15
        df30 = pd.DataFrame(rates30, columns=['time','open','high','low','close','tick_volume','spread','real_volume'])
        rsi30 = calcular_rsi(df30['close'].tolist(), 14)
        atr30 = calcular_atr(df30['high'].tolist(), df30['low'].tolist(), df30['close'].tolist(), 14)
        wr30 = calcular_williams_r(df30['high'].tolist(), df30['low'].tolist(), df30['close'].tolist(), 14)
        close30 = float(rates30[-1][4])
        vol30 = int(rates30[-1][5])

        return rsi5, atr5, wr5, close5, vol5, rsi15, atr15, wr15, close15, vol15, rsi30, atr30, wr30, close30, vol30

    except Exception as e:
        logging.error(f"[MultiTF] Erro ao coletar dados: {e}")
        return (None,) * 15


def salvar_dados_multitf_csv(dados: Dict[str, Any], arquivo: str = None) -> None:
    """Salva snapshot multi-timeframe no CSV."""
    if arquivo is None:
        arquivo = MULTITF_CSV
    try:
        abs_path = os.path.abspath(arquivo)
        df = pd.DataFrame([dados])
        file_exists = os.path.exists(abs_path)
        file_size = os.path.getsize(abs_path) if file_exists else 0
        if not file_exists or (file_exists and file_size == 0):
            df.to_csv(abs_path, index=False)
        else:
            df.to_csv(abs_path, mode='a', header=False, index=False)
    except Exception as e:
        logging.debug(f"[MultiTF] Erro ao salvar CSV: {e}")


def verificar_book_equilibrado(bid_qty: float, ask_qty: float) -> Tuple[bool, str]:
    """Verifica se o book estÃ¡ equilibrado o suficiente para operar."""
    if bid_qty == 0 or ask_qty == 0:
        return False, "Book zerado em um dos lados"

    # Calcula razÃ£o entre volumes (sempre menor/maior para ter ratio <= 1)
    ratio = min(bid_qty, ask_qty) / max(bid_qty, ask_qty)

    # Identifica qual lado estÃ¡ mais forte
    lado_forte = "compra" if bid_qty > ask_qty else "venda"
    logging.debug(f"ðŸ“Š Book - Ratio: {ratio:.3f} | Lado forte: {lado_forte}")

    if ratio < MIN_RATIO_BOOK:
        lado_menor = "compra" if bid_qty < ask_qty else "venda"
        return False, f"Book muito desequilibrado (ratio={ratio:.3f}). Lado fraco: {lado_menor}"

    # CORREÃ‡ÃƒO: PressÃ£o forte indica BIG PLAYERS - SEGUIR, nÃ£o bloquear!
    max_ratio_pressao = 10.0  # Permite atÃ© 10:1 (big players massivos)
    if max(bid_qty, ask_qty) / min(bid_qty, ask_qty) > max_ratio_pressao:
        logging.warning(
            f"âš ï¸ PressÃ£o EXTREMA no lado de {lado_forte} - PossÃ­vel manipulaÃ§Ã£o")
        return False, f"PressÃ£o EXTREMA no lado de {lado_forte}"
    elif max(bid_qty, ask_qty) / min(bid_qty, ask_qty) > 3.0:
        logging.info(
            f"ðŸ‹ BIG PLAYERS detectados no lado de {lado_forte} - OPORTUNIDADE!")

    return True, ""


class ModoOperacional:
    """Gerencia os modos operacionais do robÃ´."""

    def __init__(self):
        self.modo_atual = "NORMAL"
        self.inicio_defesa = None
        self.losses_seguidos = 0
        self.volume_anterior = 0
        self.ultimo_lucro = 0

    def atualizar_modo(self, atr: float, entropia: float, volume_atual: float,
                       bid_qty: float, ask_qty: float) -> str:
        """Atualiza o modo operacional baseado nas condiÃ§Ãµes do mercado."""
        # Verifica se pode sair do modo defesa
        if self.modo_atual == "DEFESA":
            if self.inicio_defesa and (datetime.now() - self.inicio_defesa).total_seconds() > TEMPO_DEFESA * 60:
                self.modo_atual = "NORMAL"
                self.losses_seguidos = 0
                logging.info(
                    "ðŸ›¡ï¸ Saindo do modo defesa apÃ³s perÃ­odo de observaÃ§Ã£o")
            else:
                return "DEFESA"

        # Verifica equilÃ­brio do book
        book_equilibrado, msg = verificar_book_equilibrado(bid_qty, ask_qty)
        if not book_equilibrado:
            if self.modo_atual != "AGUARDANDO":
                logging.info(f"â³ Entrando em modo aguardando - {msg}")
            return "AGUARDANDO"

        # Verifica condiÃ§Ãµes para modo lateralidade
        if atr < THRESHOLD_ATR_BAIXO and entropia < THRESHOLD_ENTROPIA_BAIXA:
            if self.modo_atual != "LATERAL":
                logging.info(
                    "â†”ï¸ Entrando em modo lateralidade - Baixa volatilidade e entropia")
            return "LATERAL"

        # Verifica condiÃ§Ãµes para modo explosÃ£o - VOLUME MÃNIMO 1000cc
        crescimento_volume = volume_atual / \
            self.volume_anterior if self.volume_anterior > 0 else 1
        if (entropia > THRESHOLD_ENTROPIA_ALTA and
                crescimento_volume > MIN_VOLUME_CRESCIMENTO and
                volume_atual >= 1000):  # FILTRO: SÃ³ explosÃ£o com 1000cc+
            if self.modo_atual != "EXPLOSAO":
                logging.info(
                    f"ðŸ’¥ Entrando em modo explosÃ£o - Alta entropia ({entropia:.2f}), volume crescente ({crescimento_volume:.1f}x) e liquidez alta ({volume_atual}cc)")
            return "EXPLOSAO"

        # Modo normal como fallback
        return "NORMAL"

    def registrar_resultado(self, lucro: float) -> None:
        """Registra resultado da operaÃ§Ã£o e atualiza contadores."""
        if lucro < 0:
            self.losses_seguidos += 1
            if self.losses_seguidos >= MAX_LOSSES_SEGUIDOS:
                self.modo_atual = "DEFESA"
                self.inicio_defesa = datetime.now()
                logging.warning(
                    f"âš ï¸ {MAX_LOSSES_SEGUIDOS} losses seguidos - Entrando em modo defesa")
        else:
            self.losses_seguidos = 0
        self.ultimo_lucro = lucro

    def ajustar_parametros_operacionais(self, volume_book_total: float = 1000) -> Dict[str, float]:
        """Ajusta parÃ¢metros baseado no modo atual com volume inteligente."""
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
                # Reduz volume mas mÃ­nimo 1cc
                'volume': max(1.0, volume_inteligente * 0.5),
                'sl_mult': MULTIPLICADOR_SL_ATR * 0.7,  # Reduz SL
                'tp_mult': MULTIPLICADOR_TP_ATR * 0.7,  # Reduz TP
            })

        elif self.modo_atual == "EXPLOSAO":
            # Modo mais agressivo - mas WDO: mÃ¡ximo 2 contratos
            volume_book_total = getattr(self, 'ultimo_volume_book', 1000)

            # Volume adaptativo para WDO (conservador)
            if volume_book_total >= 5000:   # LIQUIDEZ EXTREMA
                volume_explosao = 2.0
            elif volume_book_total >= 3000: # ALTA LIQUIDEZ
                volume_explosao = 1.5
            else:
                volume_explosao = 1.0

            params.update({
                'volume': volume_explosao,  # Volume inteligente baseado no book
                'sl_mult': MULTIPLICADOR_SL_ATR * 1.2,  # Aumenta SL
                'tp_mult': MULTIPLICADOR_TP_ATR * 1.5,  # Aumenta TP
            })

        elif self.modo_atual == "DEFESA":
            # Modo apenas observaÃ§Ã£o
            params.update({
                'volume': 0,  # NÃ£o opera
            })

        return params


def executar_ordem(action: str, lots: float = VOLUME_PADRAO, symbol: str = None,
                   sl: Optional[float] = None, tp: Optional[float] = None,
                   modo_operacional: Optional[ModoOperacional] = None,
                   sniper: bool = False) -> Optional[int]:
    """Executa uma ordem de compra ou venda com SL fixo de 5 pontos e sem TP (robÃ´ decide saÃ­da)."""

    # ========== âœ… PA1: VERIFICAÃ‡ÃƒO DE HORÃRIO OBRIGATÃ“RIA ==========
    # SniperSupermo pula esta verificaÃ§Ã£o (opera 09:00-17:30)
    if not sniper and not horario_permitido():
        horario_atual = datetime.now().strftime("%H:%M")
        logging.warning(
            f"ðŸš« PA1 ORDEM BLOQUEADA POR HORÃRIO: {horario_atual} - SÃ³ executa 09:15-12:30 e 14:30-17:15")
        return None

    # Usa SYMBOL global se nÃ£o especificado
    if symbol is None:
        symbol = SYMBOL

    # Verifica se o sÃ­mbolo estÃ¡ definido
    if symbol is None:
        logging.error(
            "âŒ SYMBOL nÃ£o estÃ¡ definido! NÃ£o Ã© possÃ­vel executar ordem.")
        return None

        logging.info(f"ðŸ”§ Executando ordem {action} para sÃ­mbolo: {symbol}")

    # Verifica conexÃ£o MT5
    if not mt5.initialize():
        logging.error("âŒ MT5 nÃ£o estÃ¡ inicializado! Tentando reconectar...")
        if not reconectar_mt5():
            logging.error("âŒ Falha ao reconectar MT5")
            return None

    if modo_operacional and modo_operacional.modo_atual == "DEFESA":
        logging.info("ðŸ›¡ï¸ Ordem bloqueada - Modo defesa ativo")
        return None

    # ObtÃ©m parÃ¢metros ajustados para o modo atual
    params = modo_operacional.ajustar_parametros_operacionais() if modo_operacional else {
        'volume': lots,
        'sl_mult': MULTIPLICADOR_SL_ATR,
        'tp_mult': MULTIPLICADOR_TP_ATR
    }
    # Override de volume para SniperSupermo (lots diferente do padrÃ£o)
    if abs(lots - VOLUME_PADRAO) > 0.001:
        params['volume'] = lots

    # Verifica estado do mercado
    mercado_aberto, msg = verificar_mercado_aberto()
    if not mercado_aberto:
        logging.warning(f"âŒ Ordem nÃ£o enviada: {msg}")
        return None

    tipo = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL

    # DiagnÃ³stico detalhado dos dados de mercado
    tick = mt5.symbol_info_tick(symbol)
    symbol_info = get_cached_symbol_info(symbol)

    if tick is None:
        logging.error(f"âŒ Tick Ã© None para sÃ­mbolo {symbol}")
        # Tenta reselecionar o sÃ­mbolo e obter tick novamente
        mt5.symbol_select(symbol, True)
        time.sleep(0.1)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.error(f"âŒ Tick ainda Ã© None apÃ³s reselecionar {symbol}")
            return None

    if symbol_info is None:
        logging.error(f"âŒ Symbol_info Ã© None para sÃ­mbolo {symbol}")
        # Limpa cache e tenta novamente
        get_cached_symbol_info.cache_clear()
        symbol_info = get_cached_symbol_info(symbol)
        if symbol_info is None:
            logging.error(
                f"âŒ Symbol_info ainda Ã© None apÃ³s limpar cache para {symbol}")
            return None

    logging.info(
        f"âœ… Dados obtidos - Tick: Ask={tick.ask}, Bid={tick.bid}, Symbol: {symbol_info.name}")

    if tick is None or symbol_info is None:
        logging.warning(
            "Dados de mercado indisponÃ­veis apÃ³s tentativas de correÃ§Ã£o")
        return None

    # Verifica spread
    if not verificar_spread_maximo(symbol_info, tick):
        logging.warning(
            f"âŒ Spread muito alto: {(tick.ask - tick.bid) / symbol_info.point:.1f}")
        return None

    preco = tick.ask if action == 'BUY' else tick.bid
    preco = arredondar_preco(preco)

    # Garante que o volume seja float e no mÃ­nimo 1.0
    lote_corrigido = float(max(1, round(params['volume'])))
    logging.info(f"ðŸ“Š Volume ajustado: {lote_corrigido:.1f} contratos")

    # ========== WDO: SL=5 (seguranÃ§a), TP=0 (saÃ­da dinÃ¢mica por Keras+Book) ==========
    sl_points_dinamico = SL_POINTS  # 5 pontos WDO (mÃ¡ximo)
    tp_points_dinamico = TP_POINTS  # 0 = SEM TP â€” GerenciadorDeSaida decide
    logging.info(
        f"ðŸ›¡ï¸ WDO CONFIG: SL={sl_points_dinamico}pts, TP={tp_points_dinamico} (saÃ­da dinÃ¢mica)")

    # Calcula SL e TP com valores dinÃ¢micos
    sl_calculado, tp_calculado = calcular_preco_sl_tp(
        preco, action, sl_points_dinamico, tp_points_dinamico)
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

    # ðŸ”§ CORREÃ‡ÃƒO CRÃTICA 3: Verificar se resultado nÃ£o Ã© None
    if resultado is None:
        logging.error(
            "âŒ Erro crÃ­tico: mt5.order_send retornou None (falha de conexÃ£o)")
        return None

    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(
            f"âŒ Falha ao executar ordem {action}: {resultado.retcode} - {resultado.comment}")
        return None

    logging.info(f"âœ… Ordem {action} executada. Ticket: {resultado.order}")
    logging.info(
        f"   PreÃ§o: {preco:.3f} | SL: {sl_calculado:.3f} | TP: {'SEM TP (saÃ­da dinÃ¢mica)' if tp_calculado == 0 else f'{tp_calculado:.3f}'}")

    # Aguarda um momento para o MT5 processar
    time.sleep(0.5)

    # Verifica se a ordem virou posiÃ§Ã£o
    for _ in range(3):  # Tenta atÃ© 3 vezes
        positions = mt5.positions_get(ticket=resultado.order)
        if positions and len(positions) > 0:
            pos = positions[0]
            logging.info(f"âœ… Ordem {resultado.order} virou posiÃ§Ã£o.")

            # ========== INTEGRAÃ‡ÃƒO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
            if trailing_stop and TRAILING_ATIVO:
                trailing_stop.iniciar_trailing(
                    resultado.order, action, preco, sl_calculado)
                logging.info(
                    f"ðŸŽ¯ Trailing stop iniciado para posiÃ§Ã£o {resultado.order}")

            # ========== INTEGRAÃ‡ÃƒO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
            if balanceador and BALANCEAMENTO_ATIVO:
                balanceador.registrar_operacao(action)
                status = balanceador.get_status()
                logging.info(
                    f"âš–ï¸ OperaÃ§Ã£o {action} registrada. BUY: {status['buy_count']}, SELL: {status['sell_count']} (BUY: {status['buy_percentage']:.1f}%)")

            # SAÃDA INTELIGENTE ANTIGA DESATIVADA â€” usa GerenciadorDeSaida no loop principal
            # (evita conflito entre dois sistemas de saÃ­da simultÃ¢neos)

            # ========== INTEGRAÃ‡ÃƒO PASSO 2: GERENCIADOR DE SAÃDA UNIFICADO ==========
            # ATIVA O GERENCIADOR DE SAÃDA (precisa ser passado como parÃ¢metro global)
            # gerenciador_saida.iniciar_monitoramento(pos)

            return resultado.order
        time.sleep(0.2)

    logging.warning(
        f"âš ï¸ NÃ£o foi possÃ­vel confirmar se ordem {resultado.order} virou posiÃ§Ã£o")
    return resultado.order


def verificar_se_ordem_virou_posicao(ticket: Optional[int], symbol: str = SYMBOL) -> bool:
    """Verifica se uma ordem se transformou em posiÃ§Ã£o."""
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
    """ObtÃ©m o lucro e score da Ãºltima ordem fechada, com base no ticket da ordem de abertura."""
    logging.info(
        f"ðŸ” Tentando obter lucro para ticket de ordem de abertura: {ticket_ordem_abertura}")
    if ticket_ordem_abertura is None:
        logging.warning(
            "âš ï¸ obter_lucro_ultima_ordem chamada sem ticket_ordem_abertura. Retornando 0.0, 0.0")
        return 0.0, 0.0

    # Buscar deals dos Ãºltimos X dias para garantir que cobrimos a vida da ordem.
    # Aumentar o timedelta se as posiÃ§Ãµes puderem ficar abertas por mais tempo.
    data_inicio_busca = datetime.now() - timedelta(days=7)
    deals = mt5.history_deals_get(data_inicio_busca, datetime.now())

    if not deals:
        logging.warning(
            f"ðŸ’° Nenhum deal encontrado nos Ãºltimos 7 dias. NÃ£o foi possÃ­vel obter lucro para ticket {ticket_ordem_abertura}.")
        return 0.0, 0.0

        logging.debug(
            f"ðŸ” Encontrados {len(deals)} deals nos Ãºltimos 7 dias para anÃ¡lise do ticket {ticket_ordem_abertura}.")

    # Filtra deals de SAÃDA (mt5.DEAL_ENTRY_OUT) cuja position_id corresponde ao ticket da ORDEM de abertura.
    deals_de_saida_relevantes = [
        d for d in deals if d.position_id == ticket_ordem_abertura and d.entry == mt5.DEAL_ENTRY_OUT
    ]

    if not deals_de_saida_relevantes:
        logging.warning(
            f"ðŸ’° Nenhum DEAL DE SAÃDA encontrado para a ordem com ticket (position_id) {ticket_ordem_abertura}.")
        # Isso pode significar que a posiÃ§Ã£o ainda estÃ¡ aberta, foi fechada manualmente de forma nÃ£o rastreÃ¡vel aqui,
        # ou o deal de saÃ­da ainda nÃ£o foi registrado no histÃ³rico.
        return 0.0, 0.0

    # Se houver mÃºltiplos deals de saÃ­da (ex: TPs parciais), Ã© importante decidir como agregar.
    # Para este caso, vamos pegar o deal de saÃ­da MAIS RECENTE para calcular o lucro final da posiÃ§Ã£o.
    # Ou, se for uma Ãºnica saÃ­da, este serÃ¡ o deal.
    # Se for necessÃ¡rio somar lucros de saÃ­das parciais, a lÃ³gica aqui precisaria ser mais elaborada.
    # Usar time_msc para maior precisÃ£o
    deal_final_de_saida = max(
        deals_de_saida_relevantes, key=lambda d: d.time_msc)

    lucro_total_operacao = deal_final_de_saida.profit
    # O atributo 'profit' de um deal no MT5 geralmente jÃ¡ inclui comissÃµes e swaps.

    logging.info(f"ðŸ’° Deal de saÃ­da encontrado para ticket {ticket_ordem_abertura}: DealTicket={deal_final_de_saida.ticket}, PositionID={deal_final_de_saida.position_id}, Lucro={lucro_total_operacao:.2f}, PreÃ§o SaÃ­da={deal_final_de_saida.price}, Volume={deal_final_de_saida.volume}, Hora={datetime.fromtimestamp(deal_final_de_saida.time)})")

    score_dist = 0.0
    # Para calcular o score_dist, precisamos da ordem original de abertura.
    ordens_historico = mt5.history_orders_get(ticket=ticket_ordem_abertura)

    if not ordens_historico:
        logging.warning(
            f"âš ï¸ NÃ£o foi possÃ­vel obter detalhes da ordem de abertura {ticket_ordem_abertura} do histÃ³rico para calcular score_dist.")
        # Mesmo sem a ordem, retornamos o lucro encontrado.
    elif len(ordens_historico) == 0:
        logging.warning(
            f"âš ï¸ Lista de ordens do histÃ³rico vazia para ticket {ticket_ordem_abertura} ao calcular score_dist.")
    else:
        # Pega a primeira (e deve ser a Ãºnica) ordem com esse ticket
        ordem_obj = ordens_historico[0]
        logging.debug(
            f"ðŸ“Š Detalhes da ordem de abertura para score_dist - Ticket: {ordem_obj.ticket}, PreÃ§oAbertura: {ordem_obj.price_open}, SL: {ordem_obj.sl}, TP: {ordem_obj.tp}, Tipo: {ordem_obj.type}, Estado: {ordem_obj.state}, RazÃ£o: {ordem_obj.reason}, PreÃ§o Atual MT5: {ordem_obj.price_current}")

        preco_entrada_para_score = ordem_obj.price_open  # Fallback
        # Buscar o deal de entrada correspondente ao ticket_ordem_abertura (que Ã© o position_id do deal de saÃ­da)
        deals_relacionados_posicao = [
            d for d in deals if d.position_id == ticket_ordem_abertura]
        deal_de_entrada_para_score = None
        for deal_historico in deals_relacionados_posicao:
            # Garante que Ã© o deal da ordem de abertura
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
        f"ðŸŽ¯ Score distÃ¢ncia calculado para ticket {ticket_ordem_abertura}: {score_dist:.4f}")

    # ========== AJUSTE FINO: PENALIDADE POR "MORTE SÃšBITA" ==========
    # Se o trade foi Loss e durou menos de 15 segundos, penalizamos severamente a IA
    # Isso ensina o modelo a evitar entradas em falsos rompimentos e ruÃ­dos de mercado
    if deal_de_entrada_para_score:
        tempo_trade_segundos = (
            deal_final_de_saida.time_msc - deal_de_entrada_para_score.time_msc) / 1000.0

        if lucro_total_operacao < 0 and tempo_trade_segundos < 15:
            score_dist = -1.5  # Penalidade severa para "Morte SÃºbita"
            logging.warning(
                f"âš ï¸ MORTE SÃšBITA DETECTADA: Trade durou {tempo_trade_segundos:.1f}s com prejuÃ­zo de R${lucro_total_operacao:.2f} | Penalizando IA com score -1.5")
        elif lucro_total_operacao < 0 and tempo_trade_segundos < 30:
            # Penalidade mÃ©dia para stops muito rÃ¡pidos
            score_dist = min(score_dist * 1.5, -1.0)
            logging.warning(
                f"âš ï¸ STOP RÃPIDO: Trade durou {tempo_trade_segundos:.1f}s com prejuÃ­zo | Score penalizado: {score_dist:.2f}")

    return lucro_total_operacao, score_dist

# endregion

# region [Trailing Stop]


def atualizar_trailing_stop() -> None:
    """Atualiza o trailing stop das posiÃ§Ãµes abertas."""
    if not TRAILING_ATIVO:
        return

    # Verifica se Ã© fim de semana
    if datetime.now().weekday() > 4:  # 5 = SÃ¡bado, 6 = Domingo
        # Verifica a cada minuto durante fim de semana
        threading.Timer(60, atualizar_trailing_stop).start()
        return

    # Verifica estado do mercado
    mercado_aberto, msg = verificar_mercado_aberto()
    if not mercado_aberto:
        if not hasattr(atualizar_trailing_stop, '_ultimo_log_fechado'):
            atualizar_trailing_stop._ultimo_log_fechado = 0
        if time.time() - atualizar_trailing_stop._ultimo_log_fechado >= 300:
            logging.debug(f"Trailing stop inativo: mercado fechado")
            atualizar_trailing_stop._ultimo_log_fechado = time.time()
        threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()
        return

    # Verifica horÃ¡rio do ajuste
    agora = datetime.now().time()
    horario_ajuste = datetime.strptime(HORARIO_AJUSTE, "%H:%M").time()
    if agora >= horario_ajuste:
        logging.info("â° ApÃ³s horÃ¡rio de ajuste, trailing stop desativado")
        return

    posicoes = retry_positions_get(SYMBOL)
    if posicoes is None or len(posicoes) == 0:
        threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()
        return

    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        logging.warning(
            "âš ï¸ InformaÃ§Ãµes do sÃ­mbolo indisponÃ­veis para trailing")
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

        # Converte diferenÃ§a para pontos (1 ponto = 1000 ticks)
        lucro_ticks = abs(preco_atual - preco_entrada) / symbol_info.point
        lucro_pontos = lucro_ticks / TICKS_POR_PONTO

        # SÃ³ move o stop se atingiu o gatilho em pontos
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

        # SÃ³ atualiza se o novo SL Ã© mais favorÃ¡vel
        if pos.type == mt5.POSITION_TYPE_BUY and (pos.sl is None or novo_sl > pos.sl):
            atualizar_sl(pos.ticket, novo_sl)
        elif pos.type == mt5.POSITION_TYPE_SELL and (pos.sl is None or novo_sl < pos.sl):
            atualizar_sl(pos.ticket, novo_sl)

    threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()


def atualizar_sl(ticket: int, novo_sl: float, eh_breakeen_forcado: bool = False) -> bool:
    """Atualiza o stop loss de uma posiÃ§Ã£o com validaÃ§Ã£o de distÃ¢ncia mÃ­nima.
    eh_breakeen_forcado=True: pula TODAS as validaÃ§Ãµes (usado por INVERSÃƒO DE FLUXO)."""
    # Recupera a posiÃ§Ã£o atual para pegar o TP original
    posicoes = mt5.positions_get(ticket=ticket)
    if not posicoes:
        logging.error(
            f"âŒ NÃ£o foi possÃ­vel obter a posiÃ§Ã£o com ticket {ticket} para atualizar SL.")
        return False

    posicao = posicoes[0]
    tp_original = posicao.tp

    # CORREÃ‡ÃƒO CRÃTICA: ValidaÃ§Ã£o de distÃ¢ncia mÃ­nima obrigatÃ³ria
    symbol_info = mt5.symbol_info(SYMBOL)
    if not symbol_info:
        logging.error(f"âŒ Erro ao obter informaÃ§Ãµes do sÃ­mbolo {SYMBOL}")
        return False

    # Obter preÃ§o atual e freeze level
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        logging.error(f"âŒ Erro ao obter tick atual do {SYMBOL}")
        return False

    # Inicializa freeze_level com valor padrÃ£o ANTES de qualquer uso
    freeze_level = symbol_info.trade_freeze_level if symbol_info else 0
    if freeze_level == 0:
        freeze_level = 1  # WDO: 1pt mÃ­nimo (freeze_level real do MT5)
    distancia_minima = freeze_level  # Sem multiplicador â€” precisa ser mÃ­nimo real, nÃ£o conservador

    # Breakeen: SL no preÃ§o de entrada â€” SEM validaÃ§Ã£o de distÃ¢ncia mÃ­nima
    eh_breakeen = abs(novo_sl - posicao.price_open) < 2.0  # tolerÃ¢ncia de 2 ticks

    if eh_breakeen_forcado:
        logging.info(
            f"\U0001f510 Breakeen FORCADO (SL={novo_sl:.2f} ~ entrada={posicao.price_open:.2f}) \u2014 sem validacao")
    elif not eh_breakeen:
        # Validar distÃ¢ncia mÃ­nima baseada no tipo de posiÃ§Ã£o
        if posicao.type == mt5.POSITION_TYPE_BUY:
            preco_referencia = tick.bid
            distancia_atual = preco_referencia - novo_sl  # BUY: SL fica abaixo do bid
            if distancia_atual < distancia_minima:
                novo_sl_corrigido = preco_referencia - distancia_minima
                # SAFETY: Se correÃ§Ã£o piora SL, nÃ£o mover â€” esperar prÃ³ximo tick
                if posicao.sl != 0 and novo_sl_corrigido <= posicao.sl:
                    logging.debug(
                        f"ðŸ”„ Trailing BUY: correÃ§Ã£o ({novo_sl_corrigido:.2f}) pior que atual ({posicao.sl:.2f}). Aguardando preÃ§o.")
                    return False
                logging.warning(
                    f"âš ï¸ SL BUY muito prÃ³ximo! Corrigido: {novo_sl:.2f} â†’ {novo_sl_corrigido:.2f}")
                novo_sl = novo_sl_corrigido
        else:  # SELL
            preco_referencia = tick.ask
            distancia_atual = novo_sl - preco_referencia  # SELL: SL fica acima do ask
            if distancia_atual < distancia_minima:
                novo_sl_corrigido = preco_referencia + distancia_minima
                # SAFETY: Se correÃ§Ã£o piora SL, nÃ£o mover â€” esperar prÃ³ximo tick
                if posicao.sl != 0 and novo_sl_corrigido >= posicao.sl:
                    logging.debug(
                        f"ðŸ”„ Trailing SELL: correÃ§Ã£o ({novo_sl_corrigido:.2f}) pior que atual ({posicao.sl:.2f}). Aguardando preÃ§o.")
                    return False
                logging.warning(
                    f"âš ï¸ SL SELL muito prÃ³ximo! Corrigido: {novo_sl:.2f} â†’ {novo_sl_corrigido:.2f}")
                novo_sl = novo_sl_corrigido
    else:
        logging.debug(
            f"[atualizar_sl] Breakeen detectado (SL={novo_sl:.2f} â‰ˆ entrada={posicao.price_open:.2f}) â€” sem validaÃ§Ã£o de distÃ¢ncia")

    # Verificar se o novo SL Ã© realmente uma melhoria
    if posicao.sl != 0:  # Se jÃ¡ tem SL definido
        if posicao.type == mt5.POSITION_TYPE_BUY and novo_sl <= posicao.sl:
            logging.debug(
                f"ðŸ”„ SL BUY nÃ£o Ã© melhoria: {novo_sl:.2f} <= {posicao.sl:.2f}")
            return False
        elif posicao.type == mt5.POSITION_TYPE_SELL and novo_sl >= posicao.sl:
            logging.debug(
                f"ðŸ”„ SL SELL nÃ£o Ã© melhoria: {novo_sl:.2f} >= {posicao.sl:.2f}")
            return False

    logging.debug(
        f"[atualizar_sl] Ticket: {ticket}, Novo SL: {novo_sl:.2f}, TP: {tp_original:.2f}, Freeze: {freeze_level}")

    ordem_mod = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": SYMBOL,
        "sl": round(novo_sl, symbol_info.digits),
        "tp": tp_original,  # MantÃ©m o TP original da posiÃ§Ã£o
        "magic": MAGIC_NUMBER,
        "comment": "Trailing SL Monstro"
    }

    resultado = mt5.order_send(ordem_mod)
    if resultado is None:
        logging.error(f"âŒ Erro ao mover SL via trailing. Ticket={ticket}")
        logging.error(f"âŒ Erro MT5: {mt5.last_error()}")
        return False
    elif resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(
            f"ðŸ” SL atualizado com sucesso! {posicao.sl:.2f} â†’ {ordem_mod['sl']:.2f} (Ticket: {ticket})")
        return True
    else:
        logging.error(
            f"âŒ FALHA ao mover SL! CÃ³digo: {resultado.retcode} | Msg: {resultado.comment} | SL: {novo_sl:.2f}")
        logging.error(
            f"âŒ Detalhes: Freeze={freeze_level}, DistÃ¢ncia mÃ­n={distancia_minima:.5f}")
        return False
# endregion


# region [Web Server]
def _caminho_recurso(path):
    if hasattr(sys, '_MEIPASS'):
        full = os.path.join(sys._MEIPASS, path)
        if os.path.exists(full):
            return full
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, path)
app = Flask(__name__, template_folder=_caminho_recurso('templates'))
app.register_blueprint(dashboard_bp)

from flask import abort, send_from_directory


@app.route('/static/<path:nome>')
def _static(nome):
    base = _caminho_recurso('.')
    caminho = os.path.join(base, nome)
    if not os.path.exists(caminho):
        base = os.path.abspath('.')
    return send_from_directory(base, nome)

# Rota antiga redireciona para o novo dashboard
@app.route("/old")
def index_old():
    """PÃ¡gina antiga com dashboard."""
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
        <h1>ðŸ¤– Monstro Dashboard</h1>
        <div class="grid">
            <div class="card">
                <h2>ðŸ“Š Performance</h2>
                <div id="performance_chart"></div>
            </div>
            <div class="card">
                <h2>ðŸŽ¯ DistribuiÃ§Ã£o de Scores</h2>
                <div id="score_dist_chart"></div>
            </div>
            <div class="card">
                <h2>ðŸ“ˆ Aprendizado</h2>
                <div id="learning_chart"></div>
            </div>
            <div class="card">
                <h2>âš–ï¸ ExperiÃªncias</h2>
                <div id="exp_chart"></div>
            </div>
            <div class="card full-width">
                <h2>ðŸ“ Status Atual</h2>
                <div id="status_info"></div>
                <div class="bloqueio-info">
                    <div>
                        <h3>ðŸ”’ Status Bloqueios</h3>
                        <div id="bloqueio_info"></div>
                    </div>
                    <div>
                        <h3>âš ï¸ SequÃªncia de Losses</h3>
                        <div id="losses_info"></div>
                    </div>
                </div>
                <div class="balanceamento-info">
                    <div>
                        <h3>âš–ï¸ Balanceamento de OperaÃ§Ãµes</h3>
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
                        <p><strong>Ãšltima DecisÃ£o:</strong> ${data.ultima_decisao}</p>
                        <p><strong>Status Book:</strong> ${data.status_book}</p>
                        <p><strong>PosiÃ§Ã£o:</strong> ${data.posicao_atual}</p>
                        <p><strong>Idade MÃ©dia Exp.:</strong> ${data.idade_media_exp.toFixed(1)}h</p>
                        <p><strong>Decay MÃ©dio:</strong> ${data.decay_medio.toFixed(2)}</p>
                    `);

                    // Atualiza informaÃ§Ãµes de bloqueio
                    $('#bloqueio_info').html(`
                        <div class="bloqueio-lado ${data.bloqueios.BUY > 0 ? 'bloqueado' : 'liberado'}">
                            COMPRA: ${data.bloqueios.BUY > 0 ? `Bloqueado (${data.bloqueios.BUY} ciclos)` : 'Liberado'}
                        </div>
                        <div class="bloqueio-lado ${data.bloqueios.SELL > 0 ? 'bloqueado' : 'liberado'}">
                            VENDA: ${data.bloqueios.SELL > 0 ? `Bloqueado (${data.bloqueios.SELL} ciclos)` : 'Liberado'}
                        </div>
                    `);

                    // Atualiza informaÃ§Ãµes de losses em sequÃªncia
                    $('#losses_info').html(`
                        <div>COMPRA: ${data.losses_sequencia.BUY} losses seguidos</div>
                        <div>VENDA: ${data.losses_sequencia.SELL} losses seguidos</div>
                    `);

                    // Atualiza informaÃ§Ãµes de balanceamento
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
    """Retorna dados de performance para o grÃ¡fico."""
    return jsonify({
        "lucros": historico_lucro
    })


@app.route("/api/score_distribution")
def api_score_distribution():
    """Retorna distribuiÃ§Ã£o dos scores."""
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
    """Retorna estatÃ­sticas das experiÃªncias."""
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
    global memoria_experiencias
    idade_media = 0
    decay_medio = 0
    mem_exp = globals().get('memoria_experiencias')
    if mem_exp and mem_exp.timestamps:
        idade_media = sum(
            (datetime.now() - ts).total_seconds() / 3600
            for ts in mem_exp.timestamps
        ) / len(mem_exp.timestamps)
        decay_medio = sum(
            mem_exp.calcular_decay(ts)
            for ts in mem_exp.timestamps
        ) / len(mem_exp.timestamps)

    # ObtÃ©m status do gerenciador de bloqueio - usando globals() para verificar
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

    # ObtÃ©m status de balanceamento
    balanceamento = mem_exp.get_balanceamento_status(
    ) if mem_exp else None

    # ObtÃ©m modo operacional
    try:
        if 'modo_operacional' in globals() and modo_operacional is not None:
            modo_atual = modo_operacional.modo_atual
        else:
            modo_atual = "NORMAL"
    except:
        modo_atual = "NORMAL"

    # Safe globals for status endpoint (Flask runs in separate thread)
    score = globals().get('score', 0)
    ultima_decisao = globals().get('ultima_decisao', None)
    posicao_aberta = globals().get('posicao_aberta', False)
    ptax_valor = globals().get('ptax_valor', 0.0)
    dolar_casado = globals().get('dolar_casado', 0.0)
    sniper_bloqueado = globals().get('sniper_bloqueado', False)
    sniper_bloqueio_motivo = globals().get('sniper_bloqueio_motivo', '')
    payroll_ativado = globals().get('payroll_ativado', False)
    SYMBOL = globals().get('SYMBOL', 'WDOQ26')

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
        "balanceamento": balanceamento,
        "ptax": ptax_valor,
        "dolar_casado": dolar_casado,
        "sniper_bloqueado": sniper_bloqueado,
        "sniper_bloqueio_motivo": sniper_bloqueio_motivo,
        "payroll_ativado": payroll_ativado
    })


@app.route("/api/novos_sistemas")
def api_novos_sistemas():
    """Retorna status dos novos sistemas implementados."""
    status_sistemas = {}

    # Status do filtro de horÃ¡rio
    if filtro_horario:
        status_sistemas['horario'] = filtro_horario.get_status()

    # Status do detector de tendÃªncia
    if detector_tendencia:
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

    # Status PTAX + Payroll
    em_janela, mins_rest = em_janela_ptax()
    status_sistemas['ptax'] = {
        'valor': ptax_valor,
        'dolar_casado': dolar_casado,
        'em_janela': em_janela,
        'minutos_restantes': mins_rest,
        'dia_ptax': ultimo_dia_util_mes(),
        'payroll_ativado': payroll_ativado,
        'sniper_bloqueado': sniper_bloqueado,
        'motivo_bloqueio': sniper_bloqueio_motivo
    }

    return jsonify(status_sistemas)


@app.route("/lucro")
def lucro():
    """Retorna o histÃ³rico de lucros."""
    return jsonify({
        "lucros": historico_lucro,
        "total": sum(historico_lucro) if historico_lucro else 0,
        "media": sum(historico_lucro) / len(historico_lucro) if historico_lucro else 0,
        "operacoes": len(historico_lucro)
    })


@app.route("/api/data_files")
def api_data_files():
    """Retorna status dos arquivos de dados e modelos do robÃ´."""
    import csv
    diretorio = _caminho_base()
    arquivos = [
        "modelo_monstro_wdo.keras",
        "modelo_monstro_wdo.h5",
        "decisions_wdo.csv",
        "experiencias_wdo.json",
        "williams_r_historico.csv",
        "historico_contexto_wdo.csv",
        "sniper_supermo_historico.csv",
        "historico_multitf.csv",
    ]
    resultado = []
    for nome in arquivos:
        caminho = os.path.join(diretorio, nome)
        info = {"nome": nome, "presente": os.path.exists(caminho)}
        if info["presente"]:
            stat = os.stat(caminho)
            info["tamanho_kb"] = round(stat.st_size / 1024, 1)
            info["modificado"] = datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S")
            info["modificado_data"] = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m")
            # Contagem de linhas para CSVs
            if nome.endswith(".csv"):
                try:
                    with open(caminho, encoding="utf-8", errors="ignore") as f:
                        info["linhas"] = sum(1 for _ in f) - 1  # menos cabeÃ§alho
                except Exception:
                    info["linhas"] = 0
            elif nome.endswith(".json"):
                try:
                    with open(caminho, encoding="utf-8") as f:
                        info["linhas"] = len(json.load(f))
                except Exception:
                    info["linhas"] = 0
        resultado.append(info)
    return jsonify(arquivos=resultado)


def iniciar_flask():
    """Inicia o servidor Flask."""
    # Suprime logs de requests HTTP (GET/POST 200) — só loga erros
    flask_log = logging.getLogger('werkzeug')
    flask_log.setLevel(logging.WARNING)
    app.logger.setLevel(logging.WARNING)
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG, use_reloader=False)


def atualizar_sentinela():
    """Mantém o Sentinela de Fluxo aquecido em background (cache de 60s)."""
    global sentinela_cenario, sentinela_detalhe, sentinela_score, sentinela_ultima_atualizacao
    while True:
        try:
            _sf = sentinela_fluxo.classificar()
            sentinela_cenario = _sf['cenario']
            sentinela_detalhe = _sf['detalhe']
            sentinela_score = _sf['score']
            sentinela_ultima_atualizacao = _sf['atualizado']
            if _sf['cenario'] != 'NEUTRO':
                logging.info(f"ðŸ›¡ SENTINELA: {_sf['cenario']} | {_sf['detalhe']}")
        except Exception:
            pass
        time.sleep(60)


# VariÃ¡veis globais para mÃ©tricas
historico_loss = []  # HistÃ³rico de loss do modelo

# Controle de treinamento inteligente
contador_experiencias_novas = 0
# ðŸš¨ CORREÃ‡ÃƒO C3: Treina a cada 3 experiÃªncias novas (era 10) - APRENDIZADO ACELERADO
LIMITE_EXPERIENCIAS_PARA_TREINO = 3

# Dashboard V2 â€” VariÃ¡veis de estado para o dashboard
spread_atual = 0.0
atr_atual = 0.0
rsi_atual = 50.0

# PTAX globals
ptax_valor = 0.0
dolar_casado = 0.0
sniper_bloqueado = False
sniper_bloqueio_motivo = ""
payroll_ativado = False

# SENTINELA DE FLUXO globals (camada macroeconômica de veto)
SENTINELA_ATIVO = True  # False desativa o veto macro totalmente
sentinela_cenario = "NEUTRO"
sentinela_detalhe = "Inicializando..."
sentinela_score = 0
sentinela_ultima_atualizacao = ""

# ========== SANITY CHECK: DETECTOR DE DADOS CONGELADOS ==========
_ultimo_bid_qty = None
_ultimo_ask_qty = None
_timestamp_ultimo_dado_novo = None
TEMPO_MAX_DADOS_CONGELADOS = 300  # 5 minutos sem mudanÃ§a = alerta


def verificar_dados_congelados(bid_qty: float, ask_qty: float) -> bool:
    """
    Verifica se os dados do book estÃ£o congelados.
    Retorna True se os dados estÃ£o congelados (problema no EA MQL5).
    """
    global _ultimo_bid_qty, _ultimo_ask_qty, _timestamp_ultimo_dado_novo

    agora = time.time()

    # Inicializa na primeira chamada
    if _timestamp_ultimo_dado_novo is None:
        _ultimo_bid_qty = bid_qty
        _ultimo_ask_qty = ask_qty
        _timestamp_ultimo_dado_novo = agora
        return False

    # Verifica se os dados mudaram
    if bid_qty != _ultimo_bid_qty or ask_qty != _ultimo_ask_qty:
        _ultimo_bid_qty = bid_qty
        _ultimo_ask_qty = ask_qty
        _timestamp_ultimo_dado_novo = agora
        return False

    # Dados nÃ£o mudaram â€” verifica hÃ¡ quanto tempo
    tempo_congelado = agora - _timestamp_ultimo_dado_novo
    if tempo_congelado > TEMPO_MAX_DADOS_CONGELADOS:
        logging.warning(
            f"ðŸ§Š DADOS CONGELADOS: bid_qty={bid_qty}, ask_qty={ask_qty} "
            f"sem mudanÃ§a hÃ¡ {tempo_congelado/60:.1f} minutos! "
            f"Verifique o EA MQL5 â€” OnBookEvent pode nÃ£o estar disparando.")
        return True

    return False


# VariÃ¡veis globais para encerramento seguro
sistema_encerrando = False
modelo_ia_global = None
memoria_experiencias_global = None

# Tratamento de sinais para encerramento seguro


def verificar_arquivo_parada():
    """Verifica se existe o arquivo parar.txt para encerramento gracioso."""
    try:
        arquivo_parada = _caminho_dados("parar.txt")
        return os.path.exists(arquivo_parada)
    except Exception as e:
        logging.error(f"âŒ Erro ao verificar arquivo de parada: {e}")
        return False


def signal_handler(signum, frame):
    """Trata sinais do sistema para encerramento seguro."""
    global sistema_encerrando, modelo_ia_global, memoria_experiencias_global

    if sistema_encerrando:
        logging.info(
            "ðŸ”´ Sinal recebido novamente - forÃ§ando encerramento imediato")
        os._exit(1)

    sistema_encerrando = True
    logging.info(f"ðŸ”´ Sinal {signum} recebido - iniciando encerramento seguro")

    try:
        if modelo_ia_global and memoria_experiencias_global:
            encerramento_seguro_completo(
                modelo_ia_global, memoria_experiencias_global)
        else:
            logging.info(
                "ðŸ”´ Dados globais nÃ£o disponÃ­veis - encerramento direto")
            os._exit(0)
    except Exception as e:
        logging.error(f"âŒ Erro no encerramento por sinal: {e}")
        os._exit(1)


# Registra os handlers de sinal - TEMPORARIAMENTE DESABILITADO PARA DEBUG
# signal.signal(signal.SIGTERM, signal_handler)
# signal.signal(signal.SIGINT, signal_handler)
# if sys.platform == "win32":
#     signal.signal(signal.SIGBREAK, signal_handler)

# region [Loop Principal]


def verificar_parada_gracil():
    """Verifica se foi solicitada parada gracil atravÃ©s do arquivo parar.txt"""
    if os.path.exists(_caminho_dados("parar.txt")):
        # Se mercado fechado, encerra imediatamente
        try:
            mercado_ativo, motivo = verificar_mercado_aberto()
            if not mercado_ativo:
                logging.info(
                    f"ðŸš« {motivo} - Encerramento imediato por mercado fechado")
                return True
        except:
            pass  # Se erro na verificaÃ§Ã£o, continua normalmente
        return True
    return False


def monstro_thread(mt5_ativo_param=None, modelo_ia_param=None):
    """Loop principal do sistema de trading."""
    global thread_ativo, mt5_ativo, posicao_aberta, lucro_acumulado
    global historico_operacoes, score, modelo_ia, dados_memoria
    global memoria_experiencias, ticket_ordem_atual, ultima_decisao
    global historico_lucro, gerenciador_bloqueio, modo_operacional
    global sistema_encerrando, modelo_ia_global, memoria_experiencias_global
    global confluencia_info_atual, posicao_atual
    global SNIPER_SUPERMO_ATIVO

    try:
        # InicializaÃ§Ã£o
        mt5_ativo_local = inicializar_mt5() if mt5_ativo_param is None else mt5_ativo_param

        # === PROTEÃ‡ÃƒO TOTAL DO MODELO ===
        logging.info("ðŸ›¡ï¸ Iniciando verificaÃ§Ã£o de proteÃ§Ã£o do modelo...")
        if not verificar_e_proteger_modelo():
            logging.warning(
                "âš ï¸ ProteÃ§Ã£o do modelo identificou problemas - continuando com novo modelo")

        # Verifica se o mercado estÃ¡ aberto antes de carregar o modelo
        mercado_aberto, msg = verificar_mercado_aberto()
        if mercado_aberto:
            logging.info("Mercado aberto: carregando modelo de IA...")
            modelo_ia_local = carregar_modelo() if modelo_ia_param is None else modelo_ia_param
            print(f"[STARTUP] modelo_ia_local is None: {modelo_ia_local is None}")
            if modelo_ia_local is None:
                logging.warning("Modelo nao encontrado, criando novo modelo...")
                modelo_ia_local = criar_modelo_neural(N_FEATURES)
                logging.info("Novo modelo de IA criado com sucesso")
            print(f"[STARTUP] Chamando salvar_modelo...")
            salvar_modelo(modelo_ia_local)
            print(f"[STARTUP] salvar_modelo concluido")
        else:
            logging.info("ðŸš« Mercado fechado: carregamento de modelo suspenso.")
            modelo_ia_local = None

        # Atualiza variÃ¡veis globais para tratamento de sinais
        modelo_ia_global = modelo_ia_local
        memoria_experiencias_global = memoria_experiencias

        esperando_confirmacao = False
        ultimo_heartbeat = time.time()
        ultimo_diagnostico = time.time()

        # ========== TRAVA DE TIMESTAMP: SÃ³ opera com dados POSTERIORES Ã  inicializaÃ§Ã£o ==========
        # Guarda o momento exato da inicializaÃ§Ã£o. O robÃ´ sÃ³ vai operar quando o EA
        # enviar um timestamp POSTERIOR a este momento. Evita operar com dados velhos
        # que ficaram no arquivo book_data_wdo.csv de sessÃµes anteriores.
        timestamp_inicializacao = time.time()
        ultimo_timestamp_ea_processado = None  # Nenhum dado processado ainda
        logging.info(
            f"ðŸ”’ TRAVA TIMESTAMP: SÃ³ operarÃ¡ com dados posteriores a {datetime.now().strftime('%H:%M:%S')}")
        posicao_atual = None
        modo_operacional = ModoOperacional()  # Inicializa gerenciador de modos

        # --- INICIALIZAÃ‡ÃƒO DAS NOVAS MELHORIAS (PASSO 2 COMPLETO) ---

        # 1. Gerenciador de SaÃ­da Unificado â€” recalibrado para R/R 1:2
        config_saida = {
            'timeout_sem_evolucao_s': 180,       # 3 minutos â€” mais paciÃªncia
            'lucro_minimo_evolucao_pts': 5,      # 5 pontos mÃ­nimo de evoluÃ§Ã£o
            # SÃ³ protege apÃ³s 40pts de lucro (>50% do TP)
            'pico_minimo_protecao_pts': 40,
            'percentual_perda_pico': 0.35,       # Sai se perder 35% do pico
            'tempo_max_estagnacao_s': 240,       # 4 minutos de estagnaÃ§Ã£o
            'lucro_max_estagnacao_pts': 20,      # Lucro "pequeno" = menos de 20pts
            # Trailing sÃ³ ativa apÃ³s 3pts de lucro (WDO â€” mais sensÃ­vel)
            'trailing_gatilho_pts': 3,
            # 2pts de distÃ¢ncia â€” respira sem violinar (WDO)
            'trailing_distancia_pts': 2
        }
        gerenciador_saida = GerenciadorDeSaida(config_saida)
        logging.info("âœ… Gerenciador de SaÃ­da Unificado INICIALIZADO.")

        # 2. Volume MÃ­nimo Adaptativo (REDUZIDO PARA APRENDIZADO)
        volume_adaptativo = VolumeAdaptativo(
            janela_minutos=15, percentual_da_media=0.5)  # Reduzido de 0.8 para 0.5
        logging.info("âœ… Gerenciador de Volume Adaptativo INICIALIZADO.")

        # Inicializa gerenciador de bloqueio
        gerenciador_bloqueio = GerenciadorBloqueio()

        # CONTADOR DE REJEIÃ‡Ã•ES PARA MODO EMERGÃŠNCIA
        contador_rejeicoes_consecutivas = 0
        LIMITE_REJEICOES_EMERGENCIA = 30

        # Garante contexto inicializado antes do loop (evita NameError na sincronizaÃ§Ã£o)
        contexto: dict = {}

        while thread_ativo:
            try:
                # ===== VERIFICAÃ‡ÃƒO DE SEGURANÃ‡A DA VARIÃVEL POSICAO_ATUAL =====
                # Garante que posicao_atual sempre exista (inicializada como None se necessÃ¡rio)
                if 'posicao_atual' not in locals() and 'posicao_atual' not in globals():
                    posicao_atual = None
                    logging.debug(
                        "ðŸ”§ posicao_atual inicializada como None por seguranÃ§a")

                # ===== VERIFICAÃ‡ÃƒO DE PARADA GRACIL =====
                if verificar_parada_gracil():
                    logging.info(
                        "ðŸ›‘ PARADA GRACIL SOLICITADA - Encerrando sistema com seguranÃ§a...")
                    # Consome o sinal: remove parar.txt para nao bloquear a proxima inicializacao
                    try:
                        os.remove(_caminho_dados("parar.txt"))
                        logging.info("ðŸ§¹ parar.txt consumido e removido.")
                    except Exception:
                        pass

                    # Fecha posiÃ§Ãµes ativas se houver
                    if posicao_aberta and ticket_ordem_atual:
                        logging.info(
                            "ðŸ’° Fechando posiÃ§Ã£o ativa antes de encerrar...")
                        try:
                            fechar_posicao_atual()
                        except Exception as e:
                            logging.error(f"âŒ Erro ao fechar posiÃ§Ã£o: {e}")

                    # Salva modelo e dados importantes
                    if modelo_ia_local:
                        logging.info("ðŸ’¾ Salvando modelo IA...")
                        try:
                            salvar_modelo(modelo_ia_local)
                        except Exception as e:
                            logging.error(f"âŒ Erro ao salvar modelo: {e}")

                    # Salva experiÃªncias
                    if memoria_experiencias:
                        logging.info("ðŸ“š Salvando experiÃªncias...")
                        try:
                            salvar_experiencias_json(
                                memoria_experiencias.experiencias)
                        except Exception as e:
                            logging.error(
                                f"âŒ Erro ao salvar experiÃªncias: {e}")

                    logging.info(
                        "âœ… ENCERRAMENTO GRACIL CONCLUÃDO - Sistema finalizado com seguranÃ§a")
                    thread_ativo = False
                    break

                # Dorme atÃ© o pregÃ£o abrir
                agora = datetime.now().time()
                inicio = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
                fim = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

                if agora < inicio:
                    aguardar_abertura()
                    continue
                if agora >= fim:
                    aguardar_fechamento()
                    continue
                # Verifica se Ã© fim de semana
                if datetime.now().weekday() > 4:  # 5 = SÃ¡bado, 6 = Domingo
                    logging.info(
                        "ðŸ“… Fim de semana: sistema em modo de espera...")
                    time.sleep(60)  # Dorme por 1 minuto durante fim de semana
                    continue

                # === VERIFICAÃ‡ÃƒO DE SINAL DE ENCERRAMENTO EXTERNO ===
                # TEMPORARIAMENTE DESABILITADO PARA DEBUG
                if False and os.path.exists("shutdown_signal.txt"):
                    logging.info(
                        "ðŸš¦ SINAL DE ENCERRAMENTO EXTERNO DETECTADO - INICIANDO SHUTDOWN GRACIOSO")

                    # Fecha todas as posiÃ§Ãµes abertas
                    posicoes_fechadas = fechar_todas_posicoes(
                        "Encerramento por sinal externo")

                    # Atualiza variÃ¡veis globais antes do encerramento
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    # Executa encerramento seguro completo
                    encerramento_seguro_completo(
                        modelo_ia_local, memoria_experiencias)
                    # NÃ£o chegarÃ¡ aqui pois encerramento_seguro_completo chama os._exit()

                # === ENCERRAMENTO AUTOMÃTICO Ã€S 17:35 ===
                horario_atual = datetime.now().time()
                horario_encerramento = datetime.strptime(
                    HORARIO_ENCERRAMENTO, "%H:%M").time()
                if horario_atual >= horario_encerramento:
                    logging.info(
                        f"ðŸ”´ ENCERRAMENTO AUTOMÃTICO Ã€S {HORARIO_ENCERRAMENTO} - FECHANDO TODAS AS POSIÃ‡Ã•ES")

                    # Fecha todas as posiÃ§Ãµes abertas
                    posicoes_fechadas = fechar_todas_posicoes(
                        "Encerramento automÃ¡tico 17:35")

                    # Salva estatÃ­sticas finais
                    if posicoes_fechadas > 0:
                        logging.info(
                            f"ðŸ“Š EstatÃ­sticas finais: {posicoes_fechadas} posiÃ§Ãµes fechadas")

                    # Salva estado do modelo
                    try:
                        salvar_modelo(modelo_ia_local)
                        logging.info("ðŸ’¾ Modelo salvo com sucesso")
                    except Exception as e:
                        logging.error(f"âŒ Erro ao salvar modelo: {e}")

                    # Atualiza variÃ¡veis globais
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    logging.info(
                        f"ðŸ POSIÃ‡Ã•ES FECHADAS Ã€S {HORARIO_ENCERRAMENTO} - AGUARDANDO AFTER MARKET")

                # === ENCERRAMENTO COMPLETO APÃ“S AFTER MARKET (17:40) ===
                horario_atual_after = datetime.now().time()
                horario_after_market = datetime.strptime(
                    HORARIO_AFTER, "%H:%M").time()
                if horario_atual_after >= horario_after_market:
                    logging.info(
                        "ðŸ”´ AFTER MARKET ENCERRADO - DESLIGANDO SISTEMA AUTOMATICAMENTE")

                    # Atualiza variÃ¡veis globais antes do encerramento
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    # Executa encerramento seguro completo
                    encerramento_seguro_completo(
                        modelo_ia_local, memoria_experiencias)
                    # NÃ£o chegarÃ¡ aqui pois encerramento_seguro_completo chama os._exit()

                # Heartbeat e diagnÃ³stico - sÃ³ loga se estiver em horÃ¡rio de operaÃ§Ã£o
                timestamp_atual = time.time()
                if timestamp_atual - ultimo_heartbeat >= 300:  # 5min (o pulso de 60s jÃ¡ mostra vida)
                    if horario_permitido():
                        # Dentro do horÃ¡rio: 1 linha a cada 5min
                        status_bloqueio = gerenciador_bloqueio.get_status()
                        logging.info(
                            f"ðŸ‘ï¸ Monstro ativo | Modo: {modo_operacional.modo_atual}")
                        # Status de bloqueios sÃ³ interessa quando hÃ¡ algum bloqueio ativo
                        _bloq_buy = status_bloqueio['bloqueios']['BUY']
                        _bloq_sell = status_bloqueio['bloqueios']['SELL']
                        if _bloq_buy or _bloq_sell:
                            logging.info(
                                f"ðŸ”’ Status bloqueios - BUY: {_bloq_buy}, SELL: {_bloq_sell}")
                    else:
                        # Fora do horÃ¡rio: log silencioso a cada 10 minutos
                        if timestamp_atual - ultimo_heartbeat >= 600:
                            agora_str = datetime.now().strftime("%H:%M")
                            logging.info(
                                f"ðŸ˜´ Fora do horÃ¡rio ({agora_str}) - aguardando prÃ³xima janela")
                    ultimo_heartbeat = timestamp_atual

                if timestamp_atual - ultimo_diagnostico >= 300:
                    checar_arquivos_essenciais()
                    # === VERIFICAÃ‡ÃƒO PERIÃ“DICA DO MODELO (roda igual; log em debug) ===
                    logging.debug("ðŸ›¡ï¸ VerificaÃ§Ã£o periÃ³dica do modelo...")
                    if not verificar_e_proteger_modelo():
                        logging.warning(
                            "âš ï¸ Modelo teve problemas - mas foi protegido automaticamente")
                    ultimo_diagnostico = timestamp_atual

                if esperando_confirmacao:
                    logging.info("â³ Aguardando confirmaÃ§Ã£o da Ãºltima ordem...")
                    time.sleep(1)
                    continue

                current_positions = retry_positions_get(SYMBOL)
                monstro_position_active = any(
                    p.volume > 0 for p in current_positions or []
                )

                # ===== SINCRONIZAÃ‡ÃƒO AUTOMÃTICA DA POSIÃ‡ÃƒO ATUAL =====
                # Se existe uma posiÃ§Ã£o no MT5, mas nossa variÃ¡vel estÃ¡ vazia, sincronize!
                posicao_ativa_no_mt5 = next(
                    (p for p in current_positions if p.magic == MAGIC_NUMBER), None) if current_positions else None

                if posicao_ativa_no_mt5 and posicao_atual is None:
                    try:
                        logging.info(
                            f"ðŸ”„ Sincronizando com posiÃ§Ã£o ativa encontrada no MT5: #{posicao_ativa_no_mt5.ticket}")
                        _ctx_recover = contexto.copy() if 'contexto' in dir() and contexto else {}
                        posicao_atual = PosicaoAtiva(
                            ticket=posicao_ativa_no_mt5.ticket,
                            tipo="BUY" if posicao_ativa_no_mt5.type == mt5.POSITION_TYPE_BUY else "SELL",
                            preco_entrada=posicao_ativa_no_mt5.price_open,
                            sl=posicao_ativa_no_mt5.sl,
                            tp=posicao_ativa_no_mt5.tp,
                            score_inicial=0.0,  # NÃ£o temos o contexto original, entÃ£o usamos um valor neutro
                            entry_context=_ctx_recover  # Salva contexto atual para nÃ£o perder o registro no CSV
                        )
                        # Inicia o monitoramento do gerenciador de saÃ­da para esta posiÃ§Ã£o
                        gerenciador_saida.iniciar_monitoramento(
                            posicao_ativa_no_mt5)
                        posicao_aberta = True
                        logging.info(
                            f"âœ… SincronizaÃ§Ã£o concluÃ­da - PosiÃ§Ã£o {posicao_atual.tipo} de {posicao_atual.preco_entrada:.2f}")
                    except Exception as e:
                        logging.error(
                            f"âŒ Erro na sincronizaÃ§Ã£o de posiÃ§Ã£o: {e}")
                        posicao_atual = None
                # ==========================================

                if monstro_position_active:
                    posicao_aberta = True

                    # VERIFICAÃ‡ÃƒO ADICIONAL DE SEGURANÃ‡A
                    if posicao_atual is None:
                        logging.warning(
                            "âš ï¸ PosiÃ§Ã£o ativa no MT5 mas posicao_atual Ã© None. Tentando ressincronizar...")
                        # Tenta ressincronizar uma vez mais
                        if posicao_ativa_no_mt5:
                            try:
                                _ctx_recover2 = contexto.copy() if 'contexto' in dir() and contexto else {}
                                posicao_atual = PosicaoAtiva(
                                    ticket=posicao_ativa_no_mt5.ticket,
                                    tipo="BUY" if posicao_ativa_no_mt5.type == mt5.POSITION_TYPE_BUY else "SELL",
                                    preco_entrada=posicao_ativa_no_mt5.price_open,
                                    sl=posicao_ativa_no_mt5.sl,
                                    tp=posicao_ativa_no_mt5.tp,
                                    score_inicial=0.0,
                                    entry_context=_ctx_recover2
                                )
                                gerenciador_saida.iniciar_monitoramento(
                                    posicao_ativa_no_mt5)
                                logging.info(
                                    "âœ… RessincronizaÃ§Ã£o de emergÃªncia concluÃ­da")
                            except Exception as e:
                                logging.error(
                                    f"âŒ Falha na ressincronizaÃ§Ã£o: {e}")

                    # SUBSTITUI A LÃ“GICA ANTIGA PELA NOVA (PASSO 2)
                    # OBTÃ‰M DADOS ATUAIS
                    tick = mt5.symbol_info_tick(SYMBOL)
                    # Obtenha o RSI atual aqui tambÃ©m, se a regra for usada

                    if tick and posicao_atual is not None:
                        preco_atual = tick.bid if gerenciador_saida.tipo_posicao == "SELL" else tick.ask

                        # ========== ï¿½ HEARTBEAT DA POSIÃ‡ÃƒO (monitor ao vivo a cada ~5s) ==========
                        # Loga a cada iteraÃ§Ã£o â€” o loop jÃ¡ Ã© pausado em
                        # INTERVALO_CHECK_SCORE (5s), entÃ£o o heartbeat sai confiÃ¡vel.
                        # (Antes usava 'segundo % 5 == 0', que ficava fora de fase com o
                        #  sleep de 5s e fazia o lucro flutuante sumir por minutos.)
                        if True:
                            try:
                                _pos = mt5.positions_get(
                                    ticket=posicao_atual.ticket)
                                _lucro_rs = _pos[0].profit if (
                                    _pos and len(_pos) > 0) else 0.0
                                if gerenciador_saida.tipo_posicao == "SELL":
                                    _pts = posicao_atual.preco_entrada - preco_atual
                                else:
                                    _pts = preco_atual - posicao_atual.preco_entrada
                                _emoji = "ðŸŸ¢" if _lucro_rs >= 0 else "ðŸ”´"
                                logging.info(
                                    f"ðŸ’“ {_emoji} {gerenciador_saida.tipo_posicao} {SYMBOL} | "
                                    f"Entrada: {posicao_atual.preco_entrada:.0f} â†’ Atual: {preco_atual:.0f} | "
                                    f"{_pts:+.0f} pts | Flutuante: R$ {_lucro_rs:+.2f} | "
                                    f"SL: {_pos[0].sl:.0f} TP: {_pos[0].tp:.0f}" if (_pos and len(_pos) > 0) else "")
                            except Exception:
                                pass

                        # ========== ï¿½ðŸ”„ SAÃDA POR INVERSÃƒO DE FLUXO (BIG PLAYERS INVERTERAM) ==========
                        # Book nativo (tempo real). Se o fluxo vira contra a posiÃ§Ã£o
                        # (ratio >= SNIPER_RATIO_MIN), reage em 2 NÃVEIS:
                        #   â€¢ Em PREJUÃZO  -> SAI IMEDIATO (corta a perda, big players viraram)
                        #   â€¢ Em LUCRO/zero -> move SL para breakeven (protege e deixa correr)
                        try:
                            book_fluxo = ler_book_nativo()
                            if book_fluxo and posicao_atual:
                                bid_total = book_fluxo.get(
                                    'total_bid_volume', 0)
                                ask_total = book_fluxo.get(
                                    'total_ask_volume', 0)

                                if bid_total > 0 and ask_total > 0:
                                    # Para SELL: inversÃ£o = BID domina (compradores fortes)
                                    # Para BUY: inversÃ£o = ASK domina (vendedores fortes)
                                    fluxo_inverteu = False
                                    ratio_inversao = 0.0

                                    if gerenciador_saida.tipo_posicao == "SELL" and bid_total > ask_total:
                                        ratio_inversao = bid_total / ask_total
                                        if ratio_inversao >= SNIPER_RATIO_MIN:
                                            fluxo_inverteu = True
                                    elif gerenciador_saida.tipo_posicao == "BUY" and ask_total > bid_total:
                                        ratio_inversao = ask_total / bid_total
                                        if ratio_inversao >= SNIPER_RATIO_MIN:
                                            fluxo_inverteu = True

                                    if fluxo_inverteu:
                                        # LÃª o lucro flutuante REAL da posiÃ§Ã£o direto do MT5
                                        posicoes_check = mt5.positions_get(
                                            ticket=posicao_atual.ticket)
                                        lucro_flutuante = posicoes_check[0].profit if (
                                            posicoes_check and len(posicoes_check) > 0) else 0.0

                                        # Converte lucro em R$ para pontos (1pt = R$10 no WDO)
                                        lucro_pontos_inv = lucro_flutuante / 10.0

                                        if lucro_pontos_inv < -2.0:
                                            # NÃVEL 1 â€” PREJUÃZO GRAVE + fluxo contra: SAI IMEDIATO
                                            logging.warning(
                                                f"ðŸ”„ðŸš¨ INVERSÃƒO DE FLUXO CONTRA POSIÃ‡ÃƒO EM PREJUÃZO! "
                                                f"Ratio contrÃ¡rio: {ratio_inversao:.2f} | Lucro: {lucro_pontos_inv:+.1f}pts (R${lucro_flutuante:.2f}) | "
                                                f"Big Players viraram â€” SAINDO IMEDIATAMENTE para cortar a perda!")
                                            fechar_posicao_atual(
                                                motivo=f"InversÃ£o de fluxo em prejuÃ­zo (ratio {ratio_inversao:.2f})")
                                            posicao_atual = None
                                            posicao_aberta = False
                                        elif lucro_pontos_inv >= -2.0 and posicoes_check and len(posicoes_check) > 0:
                                            # NÃVEL 2 â€” PREJUÃZO LEVE/LUCRO/ZERO + fluxo contra: breakeen
                                            sl_breakeven = posicao_atual.preco_entrada
                                            sl_atual = posicoes_check[0].sl
                                            melhoria = (gerenciador_saida.tipo_posicao == "SELL" and sl_breakeven < sl_atual) or \
                                                       (gerenciador_saida.tipo_posicao ==
                                                        "BUY" and sl_breakeven > sl_atual)
                                            if melhoria:
                                                logging.warning(
                                                    f"ðŸ”„ INVERSÃƒO DE FLUXO (lucro {lucro_pontos_inv:+.1f}pts)! Ratio contrÃ¡rio: {ratio_inversao:.2f} | "
                                                    f"SL movido para breakeen ({sl_breakeven:.2f}) â€” protegendo!")
                                                # FIX: ForÃ§ar breakeen sem validaÃ§Ã£o de distÃ¢ncia
                                                atualizar_sl(
                                                    posicao_atual.ticket, sl_breakeven, eh_breakeen_forcado=True)
                        except Exception as e:
                            logging.debug(
                                f"[InversÃ£o Fluxo] Erro na verificaÃ§Ã£o: {e}")

                        # ========== âš¡ SNIPER SUPERMO: TRAILING ESPECÃFICO ==========
                        # 1. SL inicial 5pts da entrada (jÃ¡ Ã© o padrÃ£o)
                        # 2. Lucro >= 2.5pts â†’ move SL para breakeven (entrada)
                        # 3. Depois do breakeven: trailing 1pt/1pt (SL = preco - 1pt)
                        if SNIPER_SUPERMO_ATIVO and posicao_atual is not None:
                            try:
                                _pos_mt5 = mt5.positions_get(ticket=posicao_atual.ticket)
                                if _pos_mt5 and len(_pos_mt5) > 0:
                                    _sl_atual = _pos_mt5[0].sl
                                    _lucro_pts = (
                                        preco_atual - posicao_atual.preco_entrada
                                    ) if gerenciador_saida.tipo_posicao == "BUY" else (
                                        posicao_atual.preco_entrada - preco_atual
                                    )
                                    _entrada = posicao_atual.preco_entrada
                                    _is_buy = gerenciador_saida.tipo_posicao == "BUY"
                                    _ja_breakeven = (
                                        _sl_atual >= _entrada if _is_buy else _sl_atual <= _entrada
                                    )
                                    if _lucro_pts >= 2.5:
                                        if not _ja_breakeven:
                                            # Passo 1: breakeven garantido
                                            if atualizar_sl(posicao_atual.ticket, _entrada, eh_breakeen_forcado=True):
                                                logging.info(
                                                    f"âš¡ SNIPER: lucro {_lucro_pts:.0f}pts â†’ breakeven")
                                        else:
                                            # Passo 2: trailing 1pt atrÃ¡s do preÃ§o
                                            _sl_1pt = preco_atual - 1.0 if _is_buy else preco_atual + 1.0
                                            _melhoria = _sl_1pt > _sl_atual if _is_buy else _sl_1pt < _sl_atual
                                            if _melhoria:
                                                if atualizar_sl(posicao_atual.ticket, _sl_1pt, eh_breakeen_forcado=True):
                                                    logging.debug(
                                                        f"âš¡ SNIPER: trailing â†’ {_sl_1pt:.0f}")
                            except Exception:
                                pass

                        # CHAMA O GERENCIADOR UNIFICADO
                        deve_sair, motivo, novo_sl = gerenciador_saida.verificar_condicoes_saida(
                            preco_atual, rsi_atual=50)  # Passe o RSI real

                        if deve_sair:
                            logging.info(f"ðŸšª DecisÃ£o de SaÃ­da: {motivo}")
                            # Verificar se posiÃ§Ã£o ainda existe antes de tentar fechar
                            # (pode ter sido fechada pelo TP/SL do MT5 entre o check e o fechamento)
                            ticket_para_verificar = posicao_atual.ticket if posicao_atual else None
                            posicoes_mt5 = mt5.positions_get(
                                symbol=SYMBOL) if ticket_para_verificar else None
                            posicao_ainda_aberta = any(
                                p.ticket == ticket_para_verificar
                                for p in (posicoes_mt5 or [])
                            ) if ticket_para_verificar else False

                            if not posicao_ainda_aberta:
                                logging.info(
                                    f"âœ… PosiÃ§Ã£o {ticket_para_verificar} jÃ¡ foi fechada pelo MT5 (TP/SL). Sem aÃ§Ã£o necessÃ¡ria.")
                                gerenciador_saida.finalizar_monitoramento()
                            else:
                                # PosiÃ§Ã£o ainda aberta â€” tenta fechar com atÃ© 3 tentativas
                                fechou = False
                                for tentativa in range(3):
                                    if posicao_atual is not None:
                                        resultado_fechamento = fechar_posicao_atual(
                                            motivo)
                                    else:
                                        resultado_fechamento = fechar_todas_posicoes(
                                            motivo)

                                    if resultado_fechamento is not False and resultado_fechamento is not None:
                                        fechou = True
                                        break
                                    else:
                                        logging.warning(
                                            f"âš ï¸ Tentativa {tentativa+1}/3 de fechar falhou. Aguardando 1s...")
                                        time.sleep(1)
                                        if not mt5.initialize():
                                            reconectar_mt5()

                                if not fechou:
                                    logging.error(
                                        f"âŒ FALHA AO FECHAR POSIÃ‡ÃƒO apÃ³s 3 tentativas! PosiÃ§Ã£o pode estar aberta.")

                                gerenciador_saida.finalizar_monitoramento()
                        elif novo_sl:
                            # FIX: Se SL jÃ¡ estÃ¡ em breakeen, sÃ³ ignora se o novo SL NÃƒO Ã© uma melhoria
                            sl_ja_em_breakeen = False
                            novo_e_melhoria = False
                            if posicao_atual is not None:
                                pos_check = mt5.positions_get(ticket=posicao_atual.ticket)
                                if pos_check and len(pos_check) > 0:
                                    sl_atual_pos = pos_check[0].sl
                                    entrada_pos = pos_check[0].price_open
                                    tipo_pos = pos_check[0].type
                                    if tipo_pos == mt5.POSITION_TYPE_BUY:
                                        sl_ja_em_breakeen = sl_atual_pos >= entrada_pos
                                        novo_e_melhoria = novo_sl > sl_atual_pos
                                    elif tipo_pos == mt5.POSITION_TYPE_SELL:
                                        sl_ja_em_breakeen = sl_atual_pos <= entrada_pos
                                        novo_e_melhoria = novo_sl < sl_atual_pos
                            if sl_ja_em_breakeen and not novo_e_melhoria:
                                logging.debug(
                                    f"ðŸ”’ SL jÃ¡ em breakeen e novo SL nÃ£o Ã© melhoria - ignorado (novo={novo_sl:.2f} vs atual={sl_atual_pos:.2f})")
                            else:
                                logging.info(
                                    f"ðŸ”§ DecisÃ£o de Ajuste: Novo SL {novo_sl:.2f}")
                                if posicao_atual is not None:
                                    atualizar_sl(posicao_atual.ticket, novo_sl)
                    elif not tick:
                        logging.warning(
                            "âš ï¸ Tick indisponÃ­vel para monitoramento de posiÃ§Ã£o")
                    elif posicao_atual is None:
                        logging.warning(
                            "âš ï¸ posicao_atual ainda Ã© None apÃ³s tentativas de sincronizaÃ§Ã£o. Usando fallback.")
                        # Como Ãºltimo recurso, fecha todas as posiÃ§Ãµes
                        fechar_todas_posicoes("Fallback - posicao_atual None")
                        gerenciador_saida.finalizar_monitoramento()

                    time.sleep(INTERVALO_CHECK_SCORE)
                    continue

                if posicao_atual is not None:
                    # Processa a posiÃ§Ã£o fechada uma Ãºnica vez
                    ticket_processado = posicao_atual.ticket
                    lucro_real, score_dist = obter_lucro_ultima_ordem(
                        ticket_processado)
                    gerenciador_bloqueio.registrar_operacao(
                        posicao_atual.tipo, lucro_real)
                    if posicao_atual.entry_context is not None:
                        memoria_experiencias.adicionar(
                            posicao_atual.entry_context.copy(), posicao_atual.tipo, lucro_real, score_dist)
                        salvar_experiencia_csv(posicao_atual.entry_context.copy(
                        ), posicao_atual.tipo, lucro_real, score_dist)

                        # ========== REGISTRO RESULTADO CONFLUÃŠNCIA ==========
                        if sistema_confluencia and confluencia_info_atual:
                            sistema_confluencia.registrar_resultado_confluencia(
                                confluencia_info_atual, lucro_real)
                            logging.info(
                                f"ðŸŽ¯ Resultado confluÃªncia registrado: Lucro={lucro_real:.2f}")

                        # Treina modelo com proteÃ§Ã£o contra erros (apenas quando necessÃ¡rio)
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(
                                f"âŒ Erro no treinamento do modelo: {e}")
                            logging.debug(
                                f"Stack trace: {traceback.format_exc()}")
                    else:
                        logging.warning(
                            "âš ï¸ Contexto de entrada nÃ£o encontrado em posicao_atual ao fechar.")
                    modo_operacional.registrar_resultado(lucro_real)
                    historico_lucro.append(lucro_real)

                    # ========== REGISTRO NOS NOVOS SISTEMAS ==========
                    # Registra no cooldown inteligente
                    if cooldown_sistema and COOLDOWN_ATIVO:
                        cooldown_sistema.registrar_resultado(lucro_real)

                    # Registra no monitor de performance
                    if monitor_performance and MONITOR_PERFORMANCE_ATIVO:
                        modo_atual = modo_operacional.modo_atual if modo_operacional else "NORMAL"
                        monitor_performance.registrar_operacao(
                            lucro_real, modo_atual)

                        # Verifica alertas
                        alertas = monitor_performance.verificar_alertas()
                        for alerta in alertas:
                            logging.warning(alerta)

                    # IMPORTANTE: Reset da posiÃ§Ã£o ANTES de continuar
                    # DESATIVA O GERENCIADOR DE SAÃDA (PASSO 2)
                    gerenciador_saida.finalizar_monitoramento()

                    posicao_atual = None
                    logging.info(
                        f"âœ… PosiÃ§Ã£o {ticket_processado} processada e resetada.")

                    # Pequena pausa para evitar loop imediato
                    time.sleep(1)

                posicao_aberta = False
                SNIPER_SUPERMO_ATIVO = False  # Reset apÃ³s fechamento
                # Rebaixado para debug: o log de mercado (a cada 5s) e o standby Sniper
                # (a cada 10s) jÃ¡ mostram que o robÃ´ estÃ¡ vivo e analisando â€” evita spam.
                logging.debug(
                    "Nenhuma posiÃ§Ã£o ativa. Analisando nova entrada...")

                # Verifica se o mercado estÃ¡ aberto (DESABILITADO para mercado fechado)
                # if not verificar_estado_book(SYMBOL):
                #     logging.warning(
                #         "âš ï¸ Book em estado invÃ¡lido. Tentando reiniciar...")
                #     if reiniciar_book(SYMBOL):
                #         logging.info("âœ… Book reiniciado com sucesso")
                #     else:
                #         logging.error("âŒ Falha ao reiniciar book. Aguardandoâ€¦")

                # VerificaÃ§Ã£o simplificada para mercado fechado
                agora = datetime.now().time()
                inicio_pregao = datetime.strptime("09:00", "%H:%M").time()
                fim_pregao = datetime.strptime("17:40", "%H:%M").time()

                if agora < inicio_pregao or agora > fim_pregao:
                    logging.info(
                        f"ðŸ• Mercado fechado ({agora.strftime('%H:%M')}): modo simulaÃ§Ã£o ativo")
                    time.sleep(30)
                    continue

                # ========== HIBERNAÃ‡ÃƒO 12:30-14:30 (REDUZIDA - SNIPER CONTINUA ATIVO) ==========
                inicio_hibernacao = dtime(12, 30)
                fim_hibernacao = dtime(14, 30)

                if inicio_hibernacao <= agora < fim_hibernacao:
                    # Treina uma vez ao entrar na hibernaÃ§Ã£o (exatamente Ã s 12h)
                    if agora.hour == 12 and agora.minute == 30:
                        logging.info(
                            "ðŸ§  TREINO DO MEIO-DIA: Iniciando treino antes da hibernaÃ§Ã£o...")
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                            logging.info(
                                "âœ… TREINO DO MEIO-DIA CONCLUÃDO. HibernaÃ§Ã£o reduzida â€” sniper ativo.")
                        except Exception as e:
                            logging.error(f"âŒ Erro no treino do meio-dia: {e}")

                    # HibernaÃ§Ã£o reduzida: loop normal mas modo normal bloqueado
                    # SniperSupermo pode operar mesmo em hibernaÃ§Ã£o
                    logging.debug(
                        "ðŸ˜´ HibernaÃ§Ã£o 12:30-14:30 (sniper ativo, modo normal bloqueado por horÃ¡rio)")
                    time.sleep(5)
                    continue

                # ========== TREINO DAS 17:30 ANTES DE ENCERRAR ==========
                inicio_treino_tarde = dtime(17, 30)
                fim_treino_tarde = dtime(17, 31)  # Janela de 1 minuto

                if inicio_treino_tarde <= agora < fim_treino_tarde:
                    logging.info(
                        "ðŸ§  TREINO DA TARDE: Iniciando treino antes do encerramento...")
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                        logging.info(
                            "âœ… TREINO DA TARDE CONCLUÃDO. Aguardando encerramento Ã s 17:35...")
                    except Exception as e:
                        logging.error(f"âŒ Erro no treino da tarde: {e}")
                    time.sleep(60)  # Evita re-treinar no mesmo minuto
                    continue

                # ===== FORA DA JANELA PA1 (ex.: apÃ³s 17:15) â€” NÃƒO opera, sÃ³ aguarda =====
                # "Bloquear operaÃ§Ãµes Ã s 17:15" = nem processa decisÃ£o/salva/treina Ã  toa.
                # Evita churn de CPU/disco e spam de log fora de 09:15-12:30 / 14:30-17:15.
                # (SÃ³ entra aqui quando NÃƒO hÃ¡ posiÃ§Ã£o â€” posiÃ§Ãµes abertas seguem monitoradas.)
                if not horario_permitido():
                    if _log_periodico('fora_pa1', 300):
                        logging.info(
                            f"ðŸš« Fora do horÃ¡rio PA1 ({datetime.now().strftime('%H:%M')}) â€” "
                             f"aguardando prÃ³xima janela (09:15-12:30 / 14:30-17:15)")
                    time.sleep(30)
                    continue

                # ObtÃ©m dados do mercado
                bid_qty, ask_qty, spread, volatility, candle_type, book_data, rsi_14, volume_tick, close_price, williams_r = obter_dados_mercado(
                    SYMBOL)

                # Se algum dado for None, pula a iteraÃ§Ã£o
                if None in (bid_qty, ask_qty, spread, volatility, candle_type, book_data, rsi_14, volume_tick, close_price, williams_r):
                    logging.warning(
                        "âš ï¸ Dados do mercado incompletos. Aguardando prÃ³xima iteraÃ§Ã£o...")
                    time.sleep(2)
                    continue

                # ========== TRAVA DE TIMESTAMP: Ignora dados anteriores Ã  inicializaÃ§Ã£o ==========
                # O EA Sniper grava "timestamp" no JSON. Verificamos se o dado Ã© POSTERIOR
                # Ã  inicializaÃ§Ã£o do robÃ´. Dados antigos do arquivo sÃ£o ignorados.
                if book_data and isinstance(book_data, dict):
                    timestamp_ea = book_data.get('timestamp', '')
                    # Tenta extrair timestamp do EA (formato: "2026.07.15 17:01:01")
                    try:
                        if isinstance(timestamp_ea, str) and len(timestamp_ea) > 10:
                            dt_ea = datetime.strptime(
                                timestamp_ea, "%Y.%m.%d %H:%M:%S")
                            timestamp_ea_epoch = dt_ea.timestamp()
                        elif isinstance(timestamp_ea, (int, float)):
                            timestamp_ea_epoch = float(timestamp_ea)
                        else:
                            timestamp_ea_epoch = 0

                        # Verifica se Ã© dado POSTERIOR Ã  inicializaÃ§Ã£o
                        if timestamp_ea_epoch > 0 and timestamp_ea_epoch < timestamp_inicializacao:
                            # Dado antigo â€” EA nÃ£o atualizou desde que o robÃ´ iniciou
                            if ultimo_timestamp_ea_processado is None:
                                logging.warning(
                                    f"ðŸ”’ TRAVA TIMESTAMP: Ignorando dado antigo do EA "
                                    f"(timestamp EA: {timestamp_ea} | "
                                    f"RobÃ´ iniciou: {datetime.fromtimestamp(timestamp_inicializacao).strftime('%H:%M:%S')})")
                                ultimo_timestamp_ea_processado = "aguardando"
                            time.sleep(2)
                            continue
                        else:
                            # Dado novo! Pode operar
                            if ultimo_timestamp_ea_processado == "aguardando":
                                logging.info(
                                    f"âœ… TRAVA TIMESTAMP LIBERADA: Dado novo recebido do EA (timestamp: {timestamp_ea})")
                            ultimo_timestamp_ea_processado = timestamp_ea
                    except (ValueError, TypeError):
                        # Se nÃ£o consegue parsear timestamp, aceita o dado (compatibilidade)
                        pass

                # ========== ðŸ“¡ LEITURA DO BOOK DOL (FLUXO INSTITUCIONAL) ==========
                # O DOL Ã© o mercado "real" onde grandes players operam.
                # O WDO Ã© espelhado por HFTs com ~0.5-2s de atraso.
                # Ler o DOL permite antecipar movimentos do WDO.
                book_dol_data = ler_book_dol()
                sinal_dol = analisar_sinal_dol(book_dol_data)

                # Log periÃ³dico do sinal DOL (1x a cada 2min)
                if sinal_dol['presente'] and _log_periodico('dol', 120):
                    logging.info(
                        f"ðŸ“Š DOL {SYMBOL_DOL}: ratio={sinal_dol['ratio']:.2f} "
                        f"lado={sinal_dol['lado']} conf={sinal_dol['confianca']:.2f} "
                        f"vol={sinal_dol['volume_total']:.0f}")

                # ========== ðŸŽ¯ FILTRO SNIPER DE ELITE (BOOK NATIVO) ==========
                # O robÃ´ sÃ³ "acorda" para buscar entrada quando hÃ¡ volume institucional
                # no book (>= SNIPER_VOLUME_MIN) E desequilÃ­brio claro entre os lados
                # (ratio >= SNIPER_RATIO_MIN). Ambos ajustÃ¡veis no topo do arquivo.
                # Caso contrÃ¡rio: standby silencioso aguardando os Big Players.
                sniper_bid = book_data.get('total_bid_volume', 0) if isinstance(
                    book_data, dict) else 0
                sniper_ask = book_data.get('total_ask_volume', 0) if isinstance(
                    book_data, dict) else 0
                sniper_total = sniper_bid + sniper_ask
                sniper_ratio = 0.0
                if sniper_bid > 0 and sniper_ask > 0:
                    sniper_ratio = max(sniper_bid, sniper_ask) / \
                        min(sniper_bid, sniper_ask)

                if sniper_total < SNIPER_VOLUME_MIN or sniper_ratio < SNIPER_RATIO_MIN:
                    if _log_periodico('standby', 300):  # 1x a cada 5min (pulso jÃ¡ mostra vida)
                        logging.info(
                            f"ðŸ˜´ Standby: Aguardando Big Players... "
                            f"(Vol {sniper_total:.0f}/{SNIPER_VOLUME_MIN} | "
                            f"Ratio {sniper_ratio:.2f}/{SNIPER_RATIO_MIN})")
                    time.sleep(1)
                    continue

                # --- NOVA LÃ“GICA DE ANÃLISE DE PROFUNDIDADE ---
                tick_info = mt5.symbol_info_tick(SYMBOL)
                preco_atual_ref = (
                    tick_info.bid + tick_info.ask) / 2 if tick_info else 0

                features_profundidade = analisar_profundidade_book(
                    book_data, preco_atual_ref)
                # --- FIM DA NOVA LÃ“GICA ---

                # Calcula entropia dos dados do EA (compatibilidade com formato legado)
                if isinstance(book_data.get('bids', []), list) and len(book_data['bids']) > 0:
                    if isinstance(book_data['bids'][0], dict):
                        # Novo formato JSON: extrai apenas os volumes para entropia
                        volumes_bid = [item['volume']
                                       for item in book_data['bids']]
                        volumes_ask = [item['volume']
                                       for item in book_data['asks']]
                        entropia_book = calcular_entropia(
                            volumes_bid + volumes_ask)
                    else:
                        # Formato legado: usa diretamente
                        entropia_book = calcular_entropia(
                            book_data['bids'] + book_data['asks'])
                else:
                    entropia_book = 0.0

                # ========== FEATURES 16-18: DADOS REAIS DA POSIÃ‡ÃƒO ==========
                # Quando em trade, preenche com dados reais para Keras aprender a gerenciar
                _is_in_trade = 1 if (monstro_position_active and posicao_atual) else 0
                _floating_profit = 0.0
                _tempo_em_trade = 0

                if _is_in_trade and posicao_atual and tick_info:
                    preco_ref = tick_info.bid if posicao_atual.tipo == "SELL" else tick_info.ask
                    if posicao_atual.tipo == "SELL":
                        _floating_profit = posicao_atual.preco_entrada - preco_ref
                    else:
                        _floating_profit = preco_ref - posicao_atual.preco_entrada
                    _tempo_em_trade = int((datetime.now() - posicao_atual.hora_entrada).total_seconds())

                # Williams %R monitor (log only, nÃ£o bloqueia)
                wr_result = williams_r_monitor.alimentar(
                    preco=close_price, high=close_price, low=close_price, wr=williams_r
                )

                # PTAX + payroll update
                ptax_bruto = atualizar_ptax()
                preco_wdo = preco_atual_ref / 1000.0 if preco_atual_ref else 0
                dolar_casado = (preco_wdo - ptax_bruto) * 1000 if ptax_bruto > 0 else 0
                em_janela, mins_rest = em_janela_ptax()
                dia_ptax = 1 if ultimo_dia_util_mes() else 0
                sniper_blq, sniper_mot = verificar_sniper_bloqueado()
                sniper_bloqueado = sniper_blq
                sniper_bloqueio_motivo = sniper_mot
                payroll_ativado = eh_horario_payroll()

                contexto = {
                    "bid_qty": bid_qty, "ask_qty": ask_qty, "spread": spread, "volatility": volatility,
                    "candle_type": candle_type, "entropia_book": entropia_book, "rsi_14": rsi_14,
                    "volume_tick": volume_tick, "is_in_trade": _is_in_trade,
                    "floating_profit": _floating_profit, "tempo_em_trade": _tempo_em_trade,
                    "preco": preco_atual_ref,
                    # Williams %R (monitoring only)
                    "williams_r": williams_r,
                    "wr_zona": wr_result['zona'],
                    "wr_divergencia": wr_result['divergencia'],
                    # Sinal DOL: desequilÃ­brio do book do dÃ³lar cheio (referÃªncia institucional)
                    "dol_ratio": sinal_dol.get('ratio', 1.0),
                    "dol_lado": sinal_dol.get('lado', 'NEUTRO'),
                    "dol_confianca": sinal_dol.get('confianca', 0.0),
                    "dol_presente": 1 if sinal_dol.get('presente', False) else 0,
                    # PTAX + PAYROLL
                    "ptax": ptax_bruto,
                    "dolar_casado": dolar_casado,
                    "em_janela_ptax": 1 if em_janela else 0,
                    "minutos_para_ptax": mins_rest,
                    "dia_ptax": dia_ptax,
                    "payroll_ativado": 1 if payroll_ativado else 0,
                    "sniper_bloqueado": 1 if sniper_blq else 0,
                    **features_profundidade  # Adiciona todas as novas features de uma vez!
                }
                # ========== COLETA MULTI-TIMEFRAME (M5/M15/M30) ==========
                # Coleta silenciosa para histÃ³rico sem interferir na decisÃ£o M1.
                mtf_result = obter_dados_multitf(SYMBOL)
                if None not in mtf_result:
                    rsi5, atr5, wr5, close5, vol5, rsi15, atr15, wr15, close15, vol15, rsi30, atr30, wr30, close30, vol30 = mtf_result
                    dados_mtf = {
                        "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                        "rsi_5": round(rsi5, 2), "atr_5": round(atr5, 2), "wr_5": round(wr5, 2), "close_5": round(close5, 2), "vol_5": vol5,
                        "rsi_15": round(rsi15, 2), "atr_15": round(atr15, 2), "wr_15": round(wr15, 2), "close_15": round(close15, 2), "vol_15": vol15,
                        "rsi_30": round(rsi30, 2), "atr_30": round(atr30, 2), "wr_30": round(wr30, 2), "close_30": round(close30, 2), "vol_30": vol30,
                    }
                    salvar_dados_multitf_csv(dados_mtf)
                    # Injeta no contexto para veto Multi-TF em prever_acao()
                    contexto.update({
                        "m5_rsi": round(rsi5, 2), "m5_atr": round(atr5, 2), "m5_wr": round(wr5, 2),
                        "m15_rsi": round(rsi15, 2), "m15_atr": round(atr15, 2), "m15_wr": round(wr15, 2),
                        "m30_rsi": round(rsi30, 2), "m30_atr": round(atr30, 2), "m30_wr": round(wr30, 2),
                    })
                    if _log_periodico('multitf', 300):
                        logging.info(
                            f"[MultiTF] M5 RSI={rsi5:.1f} ATR={atr5:.1f} WR={wr5:.1f} | "
                            f"M15 RSI={rsi15:.1f} ATR={atr15:.1f} WR={wr15:.1f} | "
                            f"M30 RSI={rsi30:.1f} ATR={atr30:.1f} WR={wr30:.1f}")
                # close_price separado para detector de tendÃªncia (nÃ£o vai para IA)
                close_price_para_tendencia = close_price

                # Dashboard V2 â€” Atualiza variÃ¡veis de estado para o dashboard
                spread_atual = spread
                atr_atual = volatility
                rsi_atual = rsi_14

                # ATUALIZA E VERIFICA O VOLUME ADAPTATIVO (PASSO 2)
                volume_total_book = contexto.get(
                    'bid_qty', 0) + contexto.get('ask_qty', 0)
                volume_adaptativo.adicionar_volume_atual(volume_total_book)

                # MODO EMERGÃŠNCIA: ForÃ§a operaÃ§Ã£o apÃ³s muitas rejeiÃ§Ãµes
                if not volume_adaptativo.pode_operar(volume_total_book):
                    contador_rejeicoes_consecutivas += 1

                    if contador_rejeicoes_consecutivas >= LIMITE_REJEICOES_EMERGENCIA:
                        # âœ… PA1: MESMO NO MODO EMERGÃŠNCIA, RESPEITA HORÃRIO
                        if not horario_permitido():
                            horario_atual = datetime.now().strftime("%H:%M")
                            logging.warning(
                                f"ðŸš« PA1 MODO EMERGÃŠNCIA BLOQUEADO POR HORÃRIO: {horario_atual}")
                            time.sleep(2)
                            continue

                        logging.warning(
                            f"ðŸš¨ MODO EMERGÃŠNCIA ATIVADO! {contador_rejeicoes_consecutivas} rejeiÃ§Ãµes consecutivas - FORÃ‡ANDO OPERAÃ‡ÃƒO!")
                        contador_rejeicoes_consecutivas = 0
                        # Continua para forÃ§ar operaÃ§Ã£o mesmo com volume baixo
                    else:
                        logging.info(
                            f"ðŸš« OperaÃ§Ã£o bloqueada: Volume atual ({volume_total_book:.0f}) < MÃ­nimo Adaptativo ({volume_adaptativo.volume_minimo_adaptativo:.0f}) - RejeiÃ§Ãµes: {contador_rejeicoes_consecutivas}/{LIMITE_REJEICOES_EMERGENCIA}")
                        time.sleep(2)
                        continue  # Pula para a prÃ³xima iteraÃ§Ã£o do loop
                else:
                    # Reset contador quando volume Ã© adequado
                    contador_rejeicoes_consecutivas = 0

                logging.debug(f"ðŸ“Š Contexto para decisÃ£o: {contexto}")

                # ========== SANITY CHECK: DADOS CONGELADOS ==========
                if verificar_dados_congelados(
                    contexto.get('bid_qty', 0),
                    contexto.get('ask_qty', 0)
                ):
                    # Dados congelados â€” nÃ£o opera mas continua monitorando
                    time.sleep(10)
                    continue

                monitorar_recursos()

                # >>> Bloco de DecisÃ£o e Salvamento de DecisÃ£o (Movido para Cima) <<<
                acao_para_executar = "NADA"  # Default
                confianca_decisao = 0.0

                # Garante que o scaler estÃ¡ limpo do JSON (treino online nÃ£o corrompe)
                forcar_recreacao_scaler()

                contexto_df_previsao = pd.DataFrame([contexto])
                # Adiciona coluna 'action' dummy se nÃ£o existir, para consistÃªncia com preparar_dados
                if 'action' not in contexto_df_previsao.columns:
                    contexto_df_previsao['action'] = "BUY"  # Dummy
                X_decisao, _ = preparar_dados(
                    contexto_df_previsao, treino=False)

                if X_decisao is None or X_decisao.shape[1] != N_FEATURES:
                    logging.error(
                        f"âŒ Dados invÃ¡lidos para previsÃ£o (X_decisao). Shape: {X_decisao.shape if X_decisao is not None else 'None'}")
                    time.sleep(2)
                    continue

                # âœ… REMOVIDA A PRIMEIRA OPERAÃ‡ÃƒO ALEATÃ“RIA
                # Motivo: entrava sem anÃ¡lise (antes da IA ter contexto) e causava
                # conflito de fechamento entre C12 e TP do MT5 (order_send None)
                # Agora a IA decide desde o primeiro ciclo normalmente
                try:
                    acao_predita, confianca_predita = prever_acao(
                        modelo_ia_local, X_decisao, modo_operacional,
                        None, contexto)

                    # ========== INTEGRAÃ‡ÃƒO SISTEMA DE CONFLUÃŠNCIA ==========
                    # Short-circuit: se prever_acao jÃ¡ retornou NADA (cooldown P0, horÃ¡rio, veto),
                    # nÃ£o recalcula IA/ConfluÃªncia â€” economiza CPU e evita logs confusos
                    if acao_predita == "NADA" and confianca_predita == 0.0:
                        acao_para_executar = "NADA"
                        confianca_decisao = 0.0
                    elif sistema_confluencia:
                        # Obter probabilidade bruta da IA para confluÃªncia
                        # X_decisao jÃ¡ foi normalizado pela funÃ§Ã£o preparar_dados
                        x_pred = X_decisao.values.astype(np.float32)
                        prob_bruta = modelo_ia_local.predict(
                            x_pred, verbose=0)[0][0]

                        # Verificar confluÃªncia de sinais
                        confluencia_info = sistema_confluencia.verificar_confluencia(
                            contexto, prob_bruta, acao_predita)

                        # Armazenar para uso posterior
                        confluencia_info_atual = confluencia_info

                        # Log detalhado da confluÃªncia (DEBUG â€” repetia a cada decisÃ£o)
                        logging.debug(
                            f"ðŸŽ¯ CONFLUÃŠNCIA: {confluencia_info['detalhes']} | Score: {confluencia_info['score']}")
                        logging.debug(
                            f"ðŸŽ¯ Sinais BUY: {confluencia_info['sinais_buy']}")
                        logging.debug(
                            f"ðŸŽ¯ Sinais SELL: {confluencia_info['sinais_sell']}")

                        # ========== REFATORADO: NOVA LÃ“GICA DE DECISÃƒO ==========
                        # ðŸŽ¯ REGRA 1: IA com confianÃ§a > 80% NÃƒO pode ser invertida pela confluÃªncia
                        # ðŸŽ¯ REGRA 2: ConfluÃªncia precisa de mÃ­nimo 2 sinais tÃ©cnicos

                        # Verifica se VETO MATEMÃTICO estÃ¡ ativo
                        veto_ativo = getattr(
                            prever_acao, '_ultimo_veto', False)

                        # Verifica confianÃ§a alta da IA
                        # NOTA: prob_bruta=0.0 (modelo nÃ£o treinado) NÃƒO Ã© confianÃ§a alta
                        ia_confianca_alta = (prob_bruta > 0.8 or prob_bruta < 0.2) and prob_bruta != 0.0

                        if veto_ativo:
                            # VETO MATEMÃTICO ativo - nada sobrescreve
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                            logging.warning(
                                f"ðŸš« CONFLUÃŠNCIA BLOQUEADA: Veto matemÃ¡tico ativo - hierarquia respeitada")

                        elif ia_confianca_alta:
                            # IA com confianÃ§a > 80% - ConfluÃªncia NÃƒO pode inverter
                            if confluencia_info['acao'] == acao_predita:
                                # ConfluÃªncia confirma IA de alta confianÃ§a
                                acao_para_executar = acao_predita
                                # BÃ´nus por confirmaÃ§Ã£o
                                confianca_decisao = min(
                                    prob_bruta * 1.15, 1.0)
                                logging.debug(
                                    f"ðŸ”’ IA ALTA CONFIANÃ‡A CONFIRMADA: {acao_predita} | ConfianÃ§a: {confianca_decisao:.2f}")
                            elif confluencia_info['acao'] == "NADA":
                                # ConfluÃªncia sem sinais suficientes - respeita IA de alta confianÃ§a
                                acao_para_executar = acao_predita
                                confianca_decisao = prob_bruta
                                logging.debug(
                                    f"ðŸ”’ IA ALTA CONFIANÃ‡A MANTIDA: {acao_predita} (ConfluÃªncia insuficiente)")
                            else:
                                # ConfluÃªncia tenta inverter - BLOQUEADA
                                acao_para_executar = acao_predita
                                confianca_decisao = prob_bruta * 0.9  # Penalidade leve por divergÃªncia
                                logging.warning(
                                    f"ðŸ”’ INVERSÃƒO BLOQUEADA: IA={acao_predita} (conf:{prob_bruta:.2f}) PREVALECE sobre ConfluÃªncia={confluencia_info['acao']}")

                        elif confluencia_info['acao'] != "NADA":
                            # ConfluÃªncia com sinais suficientes (â‰¥2) e IA sem alta confianÃ§a
                            if confluencia_info['acao'] != acao_predita:
                                # ConfluÃªncia sobrescreve IA de baixa/mÃ©dia confianÃ§a
                                logging.warning(
                                    f"ðŸŽ¯ CONFLUÃŠNCIA SOBRESCREVE: IA={acao_predita} (conf:{prob_bruta:.2f}) â†’ CONFLUÃŠNCIA={confluencia_info['acao']}")
                                acao_para_executar = confluencia_info['acao']
                                confianca_decisao = confluencia_info['confianca']
                            else:
                                # ConfluÃªncia confirma IA
                                acao_para_executar = acao_predita
                                base_confianca = confianca_predita if confianca_predita > 0.0 else confluencia_info[
                                    'confianca']
                                confianca_decisao = min(
                                    base_confianca * 1.2, 1.0)
                                logging.info(
                                    f"ðŸŽ¯ CONFLUÃŠNCIA CONFIRMA: {acao_predita} | ConfianÃ§a aumentada: {confianca_decisao:.2f}")
                        else:
                            # ConfluÃªncia sem sinais suficientes (<2)
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                            logging.info(
                                f"ðŸŽ¯ CONFLUÃŠNCIA BLOQUEIA: Menos de 2 sinais tÃ©cnicos (mÃ­nimo exigido)")
                    else:
                        # sistema_confluencia nÃ£o inicializado â€” usa aÃ§Ã£o direta da IA
                        acao_para_executar = acao_predita
                        confianca_decisao = confianca_predita

                    # ========== ðŸ“¡ VETO/CONFIRMAÃ‡ÃƒO PELO DOL ==========
                    # O DOL Ã© o mercado "real" â€” se ele contradiz a decisÃ£o,
                    # Ã© um sinal forte de que o WDO pode nÃ£o seguir.
                    # Regra: DOL com confianÃ§a > 0.6 e lado oposto = VETO
                    # (exceto se IA tem confianÃ§a > 80%)
                    if (sinal_dol['presente']
                            and acao_para_executar != "NADA"
                            and sinal_dol['lado'] != 'NEUTRO'
                            and sinal_dol['confianca'] > 0.6):
                        dol_contra = (
                            (acao_para_executar == "BUY" and sinal_dol['lado'] == 'SELL')
                            or (acao_para_executar == "SELL" and sinal_dol['lado'] == 'BUY')
                        )
                        dol_confirma = (
                            (acao_para_executar == "BUY" and sinal_dol['lado'] == 'BUY')
                            or (acao_para_executar == "SELL" and sinal_dol['lado'] == 'SELL')
                        )

                        if dol_contra and not ia_confianca_alta:
                            # DOL contradiz E IA nÃ£o tem confianÃ§a alta â†’ VETO
                            logging.warning(
                                f"ðŸ“ŠðŸš« DOL VETA: IA/ConfluÃªncia={acao_para_executar} "
                                f"mas DOL={sinal_dol['lado']} "
                                f"(ratio={sinal_dol['ratio']:.2f}, conf={sinal_dol['confianca']:.2f})")
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                        elif dol_contra and ia_confianca_alta:
                            # DOL contradiz MAS IA tem confianÃ§a alta â†’ penalidade
                            confianca_decisao *= 0.85
                            logging.warning(
                                f"ðŸ“Šâš ï¸ DOL CONTRARIA IA: {acao_para_executar} "
                                f"(DOL={sinal_dol['lado']}, ratio={sinal_dol['ratio']:.2f}) "
                                f"â†’ confianÃ§a reduzida: {confianca_decisao:.2f}")
                        elif dol_confirma:
                            # DOL confirma â†’ bÃ´nus de confianÃ§a
                            confianca_decisao = min(confianca_decisao * 1.1, 1.0)
                            logging.debug(
                                f"ðŸ“Šâœ… DOL CONFIRMA: {acao_para_executar} "
                                f"(ratio={sinal_dol['ratio']:.2f}) "
                                f"â†’ confianÃ§a: {confianca_decisao:.2f}")

                    # ========== NOVOS FILTROS PÓS-DOL (não-SNIPER) ==========
                    # 1. DOL confiança ≥ DOL_CONF_MIN + alinhado obrigatório para entradas não-sniper
                    # 2. Book ratio ≥ BOOK_RATIO_MIN para qualquer trade direcional
                    # AJUSTE DIAGNÓSTICO (03/08): portão exigia DOL ratio≥1.5 + WDO ratio≥1.5 + alinhado
                    # (tripla coincidência rara) → 0 trades com mercado operável. Relaxado p/ destravar amostra.
                    DOL_CONF_MIN = 0.4    # era 0.5 (DOL ratio ≥1.5); 0.4 = DOL ratio ≥1.2
                    BOOK_RATIO_MIN = 1.3  # era 1.5 (passava ~20% do dia); 1.3 passa ~60%
                    if not SNIPER_SUPERMO_ATIVO and acao_para_executar != "NADA":
                        dol_conf = sinal_dol.get('confianca', 0) if sinal_dol.get('presente') else 0
                        dol_lado = sinal_dol.get('lado', 'NEUTRO') if sinal_dol.get('presente') else 'NEUTRO'
                        bid_qty_atual = contexto.get('bid_qty', 0)
                        ask_qty_atual = contexto.get('ask_qty', 0)
                        book_ratio = max(bid_qty_atual, ask_qty_atual) / max(1, min(bid_qty_atual, ask_qty_atual))

                        dol_ok = (dol_conf >= DOL_CONF_MIN and dol_lado != 'NEUTRO' and dol_lado == acao_para_executar)
                        ratio_ok = book_ratio >= BOOK_RATIO_MIN

                        if not dol_ok:
                            logging.warning(
                                f"⛔ VETO DOL: conf={dol_conf:.2f} lado={dol_lado} ≠ {acao_para_executar} (mín 0.5 + alinhado)")
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                        elif not ratio_ok:
                            logging.warning(
                                f"⛔ VETO BOOK RATIO: {book_ratio:.2f}x < 1.5x (bid={bid_qty_atual:.0f} ask={ask_qty_atual:.0f})")
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0

                    logging.debug(
                        f"ðŸ¤– DecisÃ£o Final: {acao_para_executar} | ConfianÃ§a: {confianca_decisao:.2f}")
                except Exception as e:
                    logging.error(
                        f"âŒ Erro ao prever aÃ§Ã£o (bloco principal): {e}")
                    logging.debug(
                        f"Shape de X_decisao: {X_decisao.shape if X_decisao is not None else 'None'}")
                    time.sleep(2)
                    continue

                # Salva a decisÃ£o ANTES de qualquer filtro que possa impedir a execuÃ§Ã£o da ordem
                salvar_decisao_csv(acao_para_executar,
                                   confianca_decisao, contexto)
                ultima_decisao = acao_para_executar  # Atualiza ultima_decisao global
                # >>> Fim do Bloco de DecisÃ£o e Salvamento de DecisÃ£o <<<

                # ========== âš¡ SNIPER SUPERMO CHECK ==========
                # Se TODAS as condiÃ§Ãµes de alta convicÃ§Ã£o forem atendidas,
                # sobrepÃµe a aÃ§Ã£o e pula filtros normais (volume, big players)
                sniper_result = sniper_supermo.verificar(contexto, acao_para_executar)
                sniper_ativo = sniper_result['ativo'] and sniper_result['direcao'] == acao_para_executar
                if sniper_ativo:
                    SNIPER_SUPERMO_ATIVO = True
                    logging.info(
                        f"âš¡ SNIPER SUPERMO CONFIRMA {acao_para_executar} â€” pulando filtros normais, volume=5cc")
                else:
                    SNIPER_SUPERMO_ATIVO = False

                rates = mt5.copy_rates_from_pos(
                    SYMBOL, TIMEFRAME, 0, PERIODO_ATR + 1)
                if rates is not None and len(rates) > PERIODO_ATR:
                    high_prices = [rate[3] for rate in rates]
                    low_prices = [rate[4] for rate in rates]
                    close_prices = [rate[2] for rate in rates]
                    atr = calcular_atr(high_prices, low_prices,
                                       close_prices, PERIODO_ATR)
                else:
                    atr = THRESHOLD_ATR_BAIXO * 2

                # Usa a entropia jÃ¡ calculada no contexto
                entropia_calculada = contexto.get('entropia_book', 0.0)

                modo_anterior = modo_operacional.modo_atual
                modo_operacional.modo_atual = modo_operacional.atualizar_modo(
                    atr, entropia_calculada, volume_tick, bid_qty, ask_qty)
                if modo_anterior != modo_operacional.modo_atual:
                    logging.info(
                        f"ðŸ”„ MudanÃ§a de modo: {modo_anterior} -> {modo_operacional.modo_atual}")
                    logging.info(
                        f"ðŸ“Š ATR: {atr:.2f} | Entropia: {entropia_calculada:.2f} | Volume: {volume_tick}")
                modo_operacional.volume_anterior = volume_tick

                # Filtro de volume MENOS RESTRITIVO - sÃ³ bloqueia em casos extremos
                # (pulado se SNIPER SUPERMO estiver ativo)
                if not SNIPER_SUPERMO_ATIVO and (
                    not volume_crescente(n=2, symbol=SYMBOL) and
                    modo_operacional.modo_atual not in ["EXPLOSAO", "NORMAL"] and
                        volume_tick < 100):  # SÃ³ bloqueia se volume muito baixo E nÃ£o crescente
                    logging.info(
                        "â›” Volume muito baixo e nÃ£o crescente. OperaÃ§Ã£o bloqueada.")
                    acao_para_executar = "NAO_AGIU_FILTRO_VOLUME"
                    # Salva experiÃªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                    except Exception as e:
                        logging.error(f"âŒ Erro no treinamento: {e}")
                    time.sleep(10)
                    continue

                cb_ativado, cb_mensagem = verificar_circuit_breakers(contexto)
                if cb_ativado:
                    logging.warning(
                        f"â›” Circuit Breaker ativado: {cb_mensagem}")
                    acao_para_executar = "NAO_AGIU_CB"
                    # Salva experiÃªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                    except Exception as e:
                        logging.error(f"âŒ Erro no treinamento: {e}")
                    time.sleep(60)
                    continue

                dados_validos, erro_dados = verificar_integridade_dados(
                    contexto)
                if not dados_validos:
                    logging.error(f"âŒ Dados invÃ¡lidos: {erro_dados}")
                    acao_para_executar = "NAO_AGIU_DADOS_INVALIDOS"
                    # Salva experiÃªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                    except Exception as e:
                        logging.error(f"âŒ Erro no treinamento: {e}")
                    time.sleep(10)
                    continue

                # Aplica bloqueio de lado APÃ“S a previsÃ£o inicial - SÃ“ PARA AÃ‡Ã•ES DE TRADING
                if acao_para_executar in ["BUY", "SELL"] and gerenciador_bloqueio.verificar_bloqueio(acao_para_executar):
                    acao_original_bloqueada = acao_para_executar
                    acao_para_executar = gerenciador_bloqueio.obter_acao_alternativa(
                        acao_original_bloqueada)
                    logging.warning(
                        f"ðŸ”„ Invertendo aÃ§Ã£o de {acao_original_bloqueada} para {acao_para_executar} devido a bloqueio de lado.")
                    # Atualiza a decisÃ£o no CSV com a aÃ§Ã£o corrigida
                    salvar_decisao_csv(acao_para_executar,
                                       confianca_decisao, contexto)

                # Se apÃ³s todas as verificaÃ§Ãµes, a aÃ§Ã£o for "NADA" ou alguma forma de "NAO_AGIU"
                if acao_para_executar.startswith("NADA") or acao_para_executar.startswith("NAO_AGIU"):
                    if _log_periodico('nao_agindo', 300):
                        logging.debug(
                            f"NÃ£o agindo: {acao_para_executar} (ConfianÃ§a: {confianca_decisao:.2f} ou restriÃ§Ã£o).")
                    # Salva experiÃªncia e treina como no arquivo principal (apenas para NADA da previsÃ£o)
                    if acao_para_executar == "NADA":
                        memoria_experiencias.adicionar(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        salvar_experiencia_csv(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        # Treina apenas dentro do horÃ¡rio de pregÃ£o (evita treino desperdiÃ§ado pÃ³s-17:30)
                        if agora < dtime(17, 30):
                            try:
                                modelo_ia_local = treinar_modelo_inteligente(
                                    modelo_ia_local, memoria_experiencias)
                            except Exception as e:
                                logging.error(f"âŒ Erro no treinamento: {e}")
                        time.sleep(2)
                        continue

                # === VERIFICAÃ‡ÃƒO DE HORÃRIO ANTES DE EXECUTAR ORDEM ===
                horario_atual = datetime.now().time()
                horario_limite_ordens = datetime.strptime(
                    HORARIO_LIMITE_ORDENS, "%H:%M").time()
                if horario_atual >= horario_limite_ordens:
                    logging.info(
                        f"ðŸ•• {HORARIO_LIMITE_ORDENS} - NÃ£o executando novas ordens (prÃ³ximo ao encerramento)")
                    # Salva experiÃªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    # Treina apenas dentro do horÃ¡rio de pregÃ£o (evita treino desperdiÃ§ado pÃ³s-17:30)
                    if agora < dtime(17, 30):
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(f"âŒ Erro no treinamento: {e}")
                            time.sleep(10)
                    continue

                # ========== INTEGRAÃ‡ÃƒO MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS ==========
                if detector_modo:
                    atr = contexto.get('volatility', 0)
                    entropia = contexto.get('entropia_book', 0.5)
                    detector_modo.atualizar_indicadores(atr, entropia)
                    modo_mercado = detector_modo.detectar_modo()

                    if modo_mercado == "CONSERVADOR":
                        logging.info(
                            f"ðŸŒ Modo CONSERVADOR detectado (ATR: {atr:.1f}, Entropia: {entropia:.3f})")

                # ========== INTEGRAÃ‡ÃƒO NOVAS MELHORIAS 7 E 9 ==========
                # Atualiza detector de tendÃªncia com preÃ§o de fechamento
                if detector_tendencia and DETECTOR_TENDENCIA_ATIVO:
                    if close_price_para_tendencia > 0:
                        detector_tendencia.atualizar_tendencia(
                            close_price_para_tendencia)
                        status_tendencia = detector_tendencia.get_status()
                        logging.debug(
                            f"ðŸ“ˆ TendÃªncia atualizada: {status_tendencia['tendencia']} | Close: {close_price_para_tendencia}")
                    else:
                        logging.warning(
                            "âš ï¸ Close price nÃ£o disponÃ­vel para detector de tendÃªncia")

                # Atualiza filtro de spread dinÃ¢mico com ATR
                if filtro_spread and SPREAD_DINAMICO_ATIVO:
                    atr_atual = contexto.get('volatility', 0)
                    filtro_spread.atualizar_atr(atr_atual)

                # ========== INTEGRAÃ‡ÃƒO MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS ==========
                if circuit_breaker and CIRCUIT_BREAKER_ATIVO:
                    spread_atual = contexto.get('spread', 0)
                    if circuit_breaker.verificar_circuit_breakers(spread_atual):
                        status = circuit_breaker.get_status()
                        logging.warning(
                            f"ðŸš¨ CIRCUIT BREAKER ATIVADO: {status['motivo']}")
                        logging.info(
                            "â¸ï¸ OperaÃ§Ã£o bloqueada por circuit breaker. Aguardando...")
                        # Salva experiÃªncia e treina como no arquivo principal
                        memoria_experiencias.adicionar(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        salvar_experiencia_csv(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(f"âŒ Erro no treinamento: {e}")
                        # Aguarda 30 segundos antes de tentar novamente
                        time.sleep(30)
                        continue

                # ========== ðŸ‹ DIRETRIZ: SEGUIR OS BIG PLAYERS ==========
                # A IA decide, mas NUNCA operamos CONTRA o lado dominante do book.
                # Se os bigs estÃ£o comprando (BID > ASK) nÃ£o vendemos; se estÃ£o
                # vendendo (ASK > BID) nÃ£o compramos. "NÃ£o brigar com a fita."
                # (O Sniper jÃ¡ garante que o lado dominante tem >= 2x â€” desequilÃ­brio real.)
                # (Pulado se SNIPER SUPERMO estiver ativo â€” jÃ¡ verificou alinhamento total)
                if not SNIPER_SUPERMO_ATIVO and acao_para_executar in ["BUY", "SELL"]:
                    _bid_dom = float(contexto.get('bid_qty', 0))
                    _ask_dom = float(contexto.get('ask_qty', 0))
                    lado_dominante = "BUY" if _bid_dom > _ask_dom else (
                        "SELL" if _ask_dom > _bid_dom else None)
                    if lado_dominante and acao_para_executar != lado_dominante:
                        # Log do veto com THROTTLE (1x a cada VETO_LOG_INTERVALO_S) para
                        # nÃ£o inundar o arquivo quando o desequilÃ­brio contra persiste.
                        if time.time() - _veto_estado['ultimo_log'] >= VETO_LOG_INTERVALO_S:
                            logging.info(
                                f"ðŸ‹ VETO SEGUIR OS BIGS: decisÃ£o {acao_para_executar} Ã© CONTRA o lado dominante "
                                f"({lado_dominante} | BID {_bid_dom:.0f} x ASK {_ask_dom:.0f}) â€” nÃ£o brigo com a fita.")
                            _veto_estado['ultimo_log'] = time.time()
                        # NÃƒO grava experiÃªncia aqui (gravava a cada 1s = flood de NAO_AGIU
                        # na memÃ³ria e no disco). O veto Ã© uma REGRA fixa, nÃ£o aprendizado.
                        time.sleep(5)  # re-checa a cada 5s (nÃ£o precisa 1s p/ nÃ£o brigar)
                        continue

                # Executa ordem com a aÃ§Ã£o final decidida
                # Se SNIPER SUPERMO ativo, usa volume maior (5cc) e SL=5pts
                _volume_exec = SNIPER_SUPERMO_VOLUME if SNIPER_SUPERMO_ATIVO else VOLUME_PADRAO
                ticket = executar_ordem(
                    acao_para_executar, lots=_volume_exec, modo_operacional=modo_operacional,
                    sniper=SNIPER_SUPERMO_ATIVO)
                if SNIPER_SUPERMO_ATIVO:
                    logging.info(f"âš¡ SNIPER SUPERMO: ordem enviada com {_volume_exec}cc")
                    sniper_supermo.ativar_cooldown()
                if not ticket:
                    logging.warning(
                        "âŒ Ordem nÃ£o enviada (executar_ordem falhou). Loop reiniciado.")
                    time.sleep(2)
                    continue

                # ... (restante da lÃ³gica de confirmaÃ§Ã£o da ordem e criaÃ§Ã£o de PosicaoAtiva) ...
                # O bloco de salvar experiÃªncia e treinar modelo APÃ“S FECHAMENTO DE ORDEM jÃ¡ estÃ¡ lÃ¡.
                # Apenas precisamos garantir que o contexto usado para PosicaoAtiva e para memÃ³ria seja o `contexto` correto da decisÃ£o.

                ticket_ordem_atual = ticket
                esperando_confirmacao = True
                confirmado = False
                for _ in range(20):  # Tenta por 10 segundos
                    time.sleep(0.5)
                    if verificar_se_ordem_virou_posicao(ticket, SYMBOL):
                        logging.info(f"âœ… Ordem {ticket} virou posiÃ§Ã£o.")
                        posicao_aberta = True
                        confirmado = True
                        break

                esperando_confirmacao = False

                if not confirmado:
                    logging.warning(
                        f"âŒ Ordem {ticket} nÃ£o virou posiÃ§Ã£o. Abortando tentativa.")
                    ticket_ordem_atual = None
                    # NÃƒO salvamos experiÃªncia aqui porque a ordem nÃ£o foi efetivada
                    time.sleep(3)
                    continue

                # ApÃ³s confirmaÃ§Ã£o da ordem que virou posiÃ§Ã£o
                ordem_confirmada_info = mt5.history_orders_get(ticket=ticket)
                if not ordem_confirmada_info:
                    logging.error(
                        f"âŒ NÃ£o foi possÃ­vel obter detalhes da ordem {ticket} do histÃ³rico para criar PosicaoAtiva.")
                    continue
                ordem_obj = ordem_confirmada_info[0]

                preco_de_execucao_real = ordem_obj.price_open  # Fallback
                # Busca deals desde a criaÃ§Ã£o da ordem
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
                    tipo=acao_para_executar,  # Usar a aÃ§Ã£o efetivamente executada
                    preco_entrada=preco_de_execucao_real,
                    sl=ordem_obj.sl,
                    tp=ordem_obj.tp,
                    score_inicial=score_inicial,
                    entry_context=contexto.copy()  # Salva o contexto que levou Ã  decisÃ£o
                )

                # ATIVA O GERENCIADOR DE SAÃDA (PASSO 2)
                posicao_obj_mt5 = mt5.positions_get(ticket=ticket)[0]
                gerenciador_saida.iniciar_monitoramento(posicao_obj_mt5)

                logging.debug(
                    f"[DEBUG] posicao_atual apÃ³s instanciaÃ§Ã£o: {posicao_atual} (type: {type(posicao_atual)})"
                )
                logging.info(
                    f"ðŸ“Š Nova posiÃ§Ã£o iniciada: Ticket={posicao_atual.ticket}, "
                    f"Tipo={posicao_atual.tipo}, "
                    f"Entrada={posicao_atual.preco_entrada:.3f}, "
                    f"SL={posicao_atual.sl:.3f}, "
                    f"TP={posicao_atual.tp:.3f}, "
                    f"Score Inicial={posicao_atual.score_inicial:.2f}"
                )
                # NÃƒO calcular lucro/experiÃªncia aqui. Isso Ã© feito quando a posiÃ§Ã£o FECHA.
                time.sleep(2)  # Pequena pausa apÃ³s abrir posiÃ§Ã£o

            except Exception as e:
                logging.error(f"âŒ Erro GRAVE no loop principal: {e}")
                logging.error(traceback.format_exc())
                time.sleep(2)  # Aguarda um pouco antes de continuar

        return mt5_ativo_local, modelo_ia_local
    except Exception as e:
        logging.error(f"âŒ Erro GRAVE no loop principal: {e}")
        logging.error(traceback.format_exc())
        time.sleep(2)  # Aguarda um pouco antes de continuar

# endregion

# region [Circuit Breakers]


def verificar_circuit_breakers(contexto: Dict[str, Any]) -> Tuple[bool, str]:
    """Verifica condiÃ§Ãµes de circuit breaker."""
    agora = datetime.now().time()
    inicio = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    fim = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    # Verifica horÃ¡rio de operaÃ§Ã£o
    if not (inicio <= agora <= fim):
        return True, "Fora do horÃ¡rio de operaÃ§Ã£o"

    # Verifica spread
    if contexto.get('spread', 0) > MAX_SPREAD:
        return True, f"Spread muito alto: {contexto['spread']:.1f} pontos"

    # Verifica volume total no book
    volume_total = contexto.get('bid_qty', 0) + contexto.get('ask_qty', 0)
    if volume_total < MIN_VOLUME_BOOK:
        return True, f"Volume total insuficiente no book: {volume_total}"

    # Verifica volume mÃ­nimo em ambos os lados
    if contexto.get('bid_qty', 0) < MIN_TICKS_VALIDOS:
        return True, f"Volume bid insuficiente: {contexto.get('bid_qty', 0)}"
    if contexto.get('ask_qty', 0) < MIN_TICKS_VALIDOS:
        return True, f"Volume ask insuficiente: {contexto.get('ask_qty', 0)}"

    # Verifica drawdown diÃ¡rio
    lucro_dia = sum(historico_lucro[-100:])  # Ãšltimas 100 operaÃ§Ãµes
    if lucro_dia < MAX_LOSS_DIARIO:
        return True, f"Stop loss diÃ¡rio atingido: {lucro_dia:.2f}"

    return False, ""


def verificar_integridade_dados(dados: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica a integridade dos dados recebidos.
    Retorna (True, mensagem) se os dados sÃ£o vÃ¡lidos.
    """
    # Verifica valores nulos
    if None in dados.values():
        return False, "Dados contÃªm valores nulos"

    # Verifica valores negativos onde nÃ£o deveria
    if dados.get('bid_qty', 0) < 0 or dados.get('ask_qty', 0) < 0:
        return False, "Quantidades negativas no book"

    # Verifica valores absurdos
    if dados.get('spread', 0) > 1000:  # Spread absurdamente alto
        return False, "Spread anormal"

    # Verifica consistÃªncia do RSI
    rsi = dados.get('rsi_14', 0)
    if not (0 <= rsi <= 100):
        return False, "RSI fora do intervalo vÃ¡lido"

    return True, ""

# endregion

# region [Filtros Evolutivos Removidos]
# Classe FiltrosEvolutivos removida para evitar conflitos
# endregion

# region [Aprendizado]


class MemoriaExperiencias:
    """Gerencia a memÃ³ria de experiÃªncias do modelo."""

    def __init__(self, max_size: int = MAX_EXPERIENCIAS_MEMORIA):
        self.max_size = max_size
        self.experiencias = []
        self.indices_positivos = []
        self.indices_negativos = []
        self.timestamps = []
        self.ultimo_replay = datetime.now()
        self.historico_decisoes = []  # Para mÃ©trica de consistÃªncia
        self.score_consistencia = 0.0
        self.contagem_acoes = {"BUY": 0, "SELL": 0,
                               "NADA": 0, "NAO_AGIU": 0}  # Novo contador
        self.razao_buy_sell = 0.5  # Neutro atÃ© ter operaÃ§Ãµes reais (era 1.0 = forÃ§ava SELL)

        # CORREÃ‡ÃƒO CRÃTICA: Carrega experiÃªncias na inicializaÃ§Ã£o
        self.carregar_experiencias_do_csv()

    def adicionar(self, contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
        """Adiciona uma nova experiÃªncia Ã  memÃ³ria."""
        self._adicionar_direto(contexto, acao, lucro, score_dist)

        # MantÃ©m apenas Ãºltimas N decisÃµes para consistÃªncia
        if len(self.historico_decisoes) > JANELA_CONSISTENCIA:
            self.historico_decisoes.pop(0)

        # Atualiza score de consistÃªncia
        self.atualizar_consistencia()

    def get_balanceamento_status(self) -> Dict[str, Any]:
        """Retorna estatÃ­sticas de balanceamento das operaÃ§Ãµes."""
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
            timestamp: Momento em que a experiÃªncia foi registrada

        Returns:
            float: Valor entre 0 e 1, onde 1 significa experiÃªncia recente e
                  valores prÃ³ximos de 0 significam experiÃªncias antigas
        """
        tempo_passado = (datetime.now() - timestamp).total_seconds()
        # Usa DECAY_MEIA_VIDA (em horas) para calcular o decay
        decay = math.exp(-tempo_passado / (DECAY_MEIA_VIDA * 3600))
        return max(0.1, min(1.0, decay))  # Limita entre 0.1 e 1.0

    def atualizar_consistencia(self) -> None:
        """Calcula score de consistÃªncia baseado nas Ãºltimas decisÃµes."""
        if len(self.historico_decisoes) < 2:
            self.score_consistencia = 0.5
            return

        # Calcula sequÃªncias de acertos e erros
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
        # 1. Tamanho mÃ©dio das sequÃªncias (maior = mais consistente)
        # 2. ProporÃ§Ã£o de acertos
        # 3. PenalizaÃ§Ã£o por alternÃ¢ncia frequente
        media_seq = sum(sequencias) / len(sequencias) if sequencias else 1
        prop_acertos = sum(self.historico_decisoes) / \
            len(self.historico_decisoes)
        alternancia = len(sequencias) / len(self.historico_decisoes)

        self.score_consistencia = (
            0.4 * (media_seq / JANELA_CONSISTENCIA) +  # Peso das sequÃªncias
            0.4 * prop_acertos +                       # Peso dos acertos
            # PenalizaÃ§Ã£o por alternÃ¢ncia
            0.2 * (1 - alternancia)
        )

    def verificar_replay(self) -> bool:
        """Verifica se Ã© hora de fazer replay das experiÃªncias."""
        tempo_desde_replay = (
            datetime.now() - self.ultimo_replay).total_seconds() / 60
        return tempo_desde_replay >= INTERVALO_REPLAY

    def obter_batch_replay(self) -> Tuple[List[Tuple[Dict[str, Any], str, float, float]], List[float]]:
        """ObtÃ©m batch para replay â€” inclui TODAS as experiÃªncias reais para aprendizado completo."""
        self.ultimo_replay = datetime.now()

        # âœ… CORREÃ‡ÃƒO: Inclui TODAS as experiÃªncias reais (BUY/SELL), nÃ£o apenas positivas
        # A IA precisa aprender tanto com acertos quanto com erros
        # Prioriza positivas mas inclui negativas com peso menor
        exp_reais = [(i, exp) for i, exp in enumerate(self.experiencias)
                     # Filtra apenas operaÃ§Ãµes reais
                     if exp[1] in ['BUY', 'SELL']]

        if not exp_reais:
            # Fallback: tenta positivas de qualquer tipo (incluindo NAO_AGIU corretos)
            exp_reais = [(i, exp) for i, exp in enumerate(self.experiencias)
                         if i in self.indices_positivos]

        if not exp_reais:
            return [], []

        # Ordena por idade (mais antigas primeiro para replay)
        exp_reais.sort(key=lambda x: self.timestamps[x[0]])

        # Seleciona subset para replay
        n_replay = min(BATCH_SIZE, len(exp_reais))
        indices_replay = [idx for idx, _ in exp_reais[:n_replay]]

        batch = [self.experiencias[i] for i in indices_replay]
        decays = [PESO_REPLAY * self.calcular_decay(self.timestamps[i])
                  for i in indices_replay]

        return batch, decays

    def tem_suficiente(self) -> bool:
        """Verifica se hÃ¡ experiÃªncias suficientes para treino."""
        return len(self.experiencias) >= MIN_EXPERIENCIAS_TREINO

    def carregar_experiencias_do_csv(self) -> None:
        """CORREÃ‡ÃƒO CRÃTICA: Carrega experiÃªncias do arquivo CSV na inicializaÃ§Ã£o."""
        try:
            if not os.path.exists(HISTORICO_CSV):
                logging.info(
                    f"ðŸ“š Arquivo {HISTORICO_CSV} nÃ£o existe. Iniciando com memÃ³ria vazia.")
                return

            import pandas as pd
            df = pd.read_csv(HISTORICO_CSV, on_bad_lines='skip')

            # CARREGAMENTO EQUILIBRADO: WINS + LOSSES (modelo precisa aprender com erros)
            experiencias_reais = df[df['action'].isin(['BUY', 'SELL'])].copy()
            experiencias_nao_agiu = df[df['action'] == 'NAO_AGIU'].copy()

            # Separa wins e losses
            wins = experiencias_reais[experiencias_reais['reward'] > 0].copy()
            losses = experiencias_reais[experiencias_reais['reward'] <= 0].copy()

            # Carrega TODAS as wins + losses balanceado (ratio 2:1 wins:losses)
            max_wins = min(200, len(wins))
            max_losses = min(100, len(losses))
            wins_recentes = wins.tail(max_wins) if max_wins > 0 else wins
            losses_recentes = losses.tail(max_losses) if max_losses > 0 else losses

            logging.info(
                f"ðŸ“š CARREGAMENTO EQUILIBRADO: {max_wins} WINS + {max_losses} LOSSES (de {len(wins)}W/{len(losses)}L)")

            # Carrega NAO_AGIU proporcionalmente
            max_nao_agiu = min(200, len(experiencias_nao_agiu))
            nao_agiu_recentes = experiencias_nao_agiu.tail(max_nao_agiu)

            # Combina: wins + losses + nao_agiu
            experiencias_recentes = pd.concat(
                [wins_recentes, losses_recentes, nao_agiu_recentes], ignore_index=True)

            logging.info(
                f"ðŸ“š âœ… TOTAL: {len(wins_recentes)} WINS + {len(losses_recentes)} LOSSES + {len(nao_agiu_recentes)} NAO_AGIU")

            if len(experiencias_recentes) == 0:
                logging.info("ðŸ“š Nenhuma experiÃªncia encontrada no CSV.")
                return

            carregadas = 0
            for _, row in experiencias_recentes.iterrows():
                try:
                    # ReconstrÃ³i o contexto com TODAS as 22 features
                    contexto = {
                        'bid_qty': float(row.get('bid_qty', 0)),
                        'ask_qty': float(row.get('ask_qty', 0)),
                        'spread': float(row.get('spread', 0)),
                        'volatility': float(row.get('volatility', 0)),
                        'candle_type': str(row.get('candle_type', 'doji')),
                        'entropia_book': float(row.get('entropia_book', 0)),
                        'rsi_14': float(row.get('rsi_14', 50)),
                        'volume_tick': float(row.get('volume_tick', 0)),
                        'is_in_trade': int(row.get('is_in_trade', 0)),
                        'floating_profit': float(row.get('floating_profit', 0)),
                        'tempo_em_trade': int(row.get('tempo_em_trade', 0)),
                        'preco_maior_escora_bid': float(row.get('preco_maior_escora_bid', 0)),
                        'volume_maior_escora_bid': float(row.get('volume_maior_escora_bid', 0)),
                        'distancia_maior_escora_bid': float(row.get('distancia_maior_escora_bid', 0)),
                        'preco_maior_escora_ask': float(row.get('preco_maior_escora_ask', 0)),
                        'volume_maior_escora_ask': float(row.get('volume_maior_escora_ask', 0)),
                        'distancia_maior_escora_ask': float(row.get('distancia_maior_escora_ask', 0)),
                        'liquidez_top5_bid': float(row.get('liquidez_top5_bid', 0)),
                        'liquidez_top5_ask': float(row.get('liquidez_top5_ask', 0)),
                        'dolar_casado': float(row.get('dolar_casado', 0)),
                        'em_janela_ptax': float(row.get('em_janela_ptax', 0)),
                        'minutos_para_ptax': float(row.get('minutos_para_ptax', 0)),
                        'dia_ptax': float(row.get('dia_ptax', 0))
                    }

                    acao = str(row['action'])  # CSV usa 'action', nÃ£o 'acao'
                    lucro = float(row['reward'])
                    # Para NAO_AGIU, usa score neutro; para BUY/SELL usa reward
                    if acao == 'NAO_AGIU':
                        score_dist = 0.1  # Score neutro positivo para nÃ£o agir quando correto
                    else:
                        score_dist = float(row.get('reward', 0))

                    # Adiciona Ã  memÃ³ria (sem chamar carregar_experiencias_do_csv novamente)
                    self._adicionar_direto(contexto, acao, lucro, score_dist)
                    carregadas += 1

                except Exception as e:
                    logging.debug(f"Erro ao carregar experiÃªncia: {e}")
                    continue

            logging.info(
                f"ðŸ“š âœ… CORREÃ‡ÃƒO APLICADA: {carregadas} experiÃªncias carregadas do CSV!")
            logging.info(
                f"ðŸ“Š ExperiÃªncias positivas: {len(self.indices_positivos)}")
            logging.info(
                f"ðŸ“Š ExperiÃªncias negativas: {len(self.indices_negativos)}")

            # CORREÃ‡ÃƒO CRÃTICA: Ajusta contador global para evitar perda de progresso
            global contador_experiencias_novas
            experiencias_reais_carregadas = len(
                [exp for exp in self.experiencias if exp[1] in ['BUY', 'SELL']])
            contador_experiencias_novas = experiencias_reais_carregadas % LIMITE_EXPERIENCIAS_PARA_TREINO
            logging.info(
                f"ðŸ”„ CONTADOR AJUSTADO: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO} (baseado em {experiencias_reais_carregadas} operaÃ§Ãµes reais)")

            # Log da razÃ£o BUY/SELL apÃ³s carregamento completo
            total_ops = self.contagem_acoes.get(
                "BUY", 0) + self.contagem_acoes.get("SELL", 0)
            if total_ops > 0:
                logging.info(
                    f"ðŸ“Š RazÃ£o BUY/SELL final: {self.razao_buy_sell:.3f} ({self.contagem_acoes.get('BUY', 0)}/{total_ops})")

        except Exception as e:
            logging.warning(
                f"âš ï¸ CSV histÃ³rico com formato antigo ('{e}') â€” serÃ¡ corrigido automaticamente na inicializaÃ§Ã£o")

    def _adicionar_direto(self, contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
        """Adiciona experiÃªncia diretamente sem chamar carregar_experiencias_do_csv."""
        if len(self.experiencias) >= self.max_size:
            self.experiencias.pop(0)
            self.timestamps.pop(0)
            self.indices_positivos = [
                i-1 for i in self.indices_positivos if i > 0]
            self.indices_negativos = [
                i-1 for i in self.indices_negativos if i > 0]

        # Adiciona nova experiÃªncia
        experiencia = (contexto, acao, lucro, score_dist)
        self.experiencias.append(experiencia)
        self.timestamps.append(datetime.now())
        idx = len(self.experiencias) - 1

        # CORREÃ‡ÃƒO: Considera score_dist para NAO_AGIU e lucro para operaÃ§Ãµes reais
        if acao == 'NAO_AGIU':
            # NAO_AGIU com score positivo = decisÃ£o correta de nÃ£o operar
            if score_dist > 0:
                self.indices_positivos.append(idx)
                self.historico_decisoes.append(1)
            else:
                self.indices_negativos.append(idx)
                self.historico_decisoes.append(0)
        else:
            # BUY/SELL: usa lucro real
            if lucro > 0:
                self.indices_positivos.append(idx)
                self.historico_decisoes.append(1)
            else:
                self.indices_negativos.append(idx)
                self.historico_decisoes.append(0)
        # Atualiza contagem de aÃ§Ãµes
        if acao in self.contagem_acoes:
            self.contagem_acoes[acao] += 1
        else:
            # Adiciona nova aÃ§Ã£o se nÃ£o existir
            self.contagem_acoes[acao] = 1

        # CORREÃ‡ÃƒO CRÃTICA: Atualiza razao_buy_sell (SEM LOG para evitar spam)
        total_operacoes = self.contagem_acoes["BUY"] + \
            self.contagem_acoes["SELL"]
        if total_operacoes > 0:
            self.razao_buy_sell = self.contagem_acoes["BUY"] / total_operacoes


def normalizar_recompensas(recompensas: List[float], scores_distancia: List[float], decays: List[float]) -> List[float]:
    """Normaliza recompensas preservando sinal: losses = negativo, wins = positivo.

    Usa divisÃ£o por 100 (apÃ³s clipping) para mapear [-100,+100] â†’ [-1,+1].
    Losses recebem puniÃ§Ã£o (negativo), wins recebem bÃ´nus (positivo).
    """
    if not recompensas:
        return []

    # Clipping para limitar extremos
    recompensas_clip = [max(min(r, 100), -100) for r in recompensas]

    # Preserva SINAL: losses ficam negativos, wins ficam positivos
    recompensas_norm = [r / 100.0 for r in recompensas_clip]

    # Combina: 95% lucro + 5% score, aplicando decay temporal
    recompensas_final = [
        (0.95 * r + 0.05 * s) * d
        for r, s, d in zip(recompensas_norm, scores_distancia, decays)
    ]

    return recompensas_final


def deve_treinar_modelo() -> bool:
    """Verifica se deve treinar o modelo baseado no contador de experiÃªncias."""
    global contador_experiencias_novas, MODO_APRENDIZADO_FORCADO

    # APRENDIZADO ACELERADO: Treina mais frequentemente quando em modo forÃ§ado
    if MODO_APRENDIZADO_FORCADO and contador_experiencias_novas >= 3:
        logging.info(
            "ðŸš€ APRENDIZADO ACELERADO: Treinando com apenas 3 experiÃªncias")
        return True

    # MODO TESTE DESATIVADO â€” causava loop de spam a cada 2s (colunas faltantes no CSV)
    # if ciclos_sem_operacao % 10 == 0 and contador_experiencias_novas == 0:
    #     logging.info("ðŸ§ª MODO TESTE: ForÃ§ando treinamento mesmo sem operaÃ§Ãµes novas")
    #     return True

    return contador_experiencias_novas >= LIMITE_EXPERIENCIAS_PARA_TREINO


def treinar_modelo_inteligente(modelo: Sequential, memoria: MemoriaExperiencias) -> Sequential:
    """Treina o modelo apenas quando necessÃ¡rio."""
    global contador_experiencias_novas

    if not deve_treinar_modelo():
        logging.debug(
            f"ðŸ§  Treinamento adiado. ExperiÃªncias: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO}")
        return modelo

    # Reset contador
    contador_experiencias_novas = 0
    logging.info(
        f"ðŸ§  Iniciando treinamento apÃ³s {LIMITE_EXPERIENCIAS_PARA_TREINO} experiÃªncias novas")

    return treinar_modelo(modelo, memoria)


def _modelo_tem_l2(modelo):
    """Verifica se o modelo jÃ¡ tem regularizaÃ§Ã£o L2 nas camadas Dense."""
    for camada in modelo.layers:
        if isinstance(camada, tf.keras.layers.Dense):
            reg = getattr(camada, 'kernel_regularizer', None)
            if reg is None:
                return False
    return True


def _migrar_modelo_l2(modelo_antigo, n_features):
    """Cria novo modelo com L2 e copia os pesos do modelo antigo."""
    modelo_novo = criar_modelo_neural(n_features)
    # Copia pesos camada por camada (ignora BatchNormalization stats que podem ter shape diferente)
    for i, camada in enumerate(modelo_novo.layers):
        if i < len(modelo_antigo.layers):
            try:
                camada.set_weights(modelo_antigo.layers[i].get_weights())
            except Exception:
                pass
    logging.info("âœ… Modelo migrado para arquitetura com L2 regularization.")
    return modelo_novo


def treinar_modelo(modelo: Sequential, memoria: MemoriaExperiencias) -> Sequential:
    """
    Treina o modelo com: L2 regularization, TimeSeriesSplit, SMOTE,
    early stopping e batch balanceado.
    """
    global historico_loss
    logging.info(
        f"[treinar_modelo] Iniciando treino. Tenho {len(memoria.experiencias)} experiÃªncias.")

    if not memoria.tem_suficiente():
        logging.info(
            "[treinar_modelo] Aguardando mais experiÃªncias para treino.")
        return modelo

    try:
        # 0. Migrar para L2 se necessÃ¡rio (garante que modelo tenha regularizaÃ§Ã£o)
        if not _modelo_tem_l2(modelo):
            modelo = _migrar_modelo_l2(modelo, N_FEATURES)

        # 1. Obter o batch de experiÃªncias
        batch, decays = memoria.obter_batch_replay()
        if not batch:
            logging.info(
                "[treinar_modelo] Batch de replay vazio. Treino adiado.")
            return modelo

        df_exp = pd.DataFrame([{
            **ctx, "action": ac, "reward": luc, "score_dist": score_dist
        } for ctx, ac, luc, score_dist in batch])

        recompensas = normalizar_recompensas(
            df_exp["reward"].tolist(), df_exp["score_dist"].tolist(), decays
        )
        df_exp["reward_norm"] = recompensas

        # 2. Preparar os dados (X e y)
        df_treino = df_exp.drop(
            columns=["reward", "reward_norm", "score_dist"])
        X, y = preparar_dados(df_treino, treino=False)

        # Remove NaN/inf e alinha recompensas com dados vÃ¡lidos
        if X is not None and y is not None and len(X) > 0:
            mask_valid = np.isfinite(X.values if hasattr(X, 'values') else X).all(axis=1)
            X = X[mask_valid].reset_index(drop=True)
            y = y[mask_valid].reset_index(drop=True)
            recompensas = [recompensas[i] for i in range(len(recompensas)) if i < len(mask_valid) and mask_valid[i]]

        if X is None or y is None or len(X) < 4:
            logging.warning(
                f"[treinar_modelo] Dados insuficientes: {len(X) if X is not None else 0} amostras vÃ¡lidas (mÃ­nimo 4).")
            return modelo

        # Converte para numpy arrays
        if hasattr(X, 'values'):
            X = X.values.astype(np.float32)
        else:
            X = np.array(X, dtype=np.float32)
        if hasattr(y, 'values'):
            y = y.values.astype(np.float32)
        else:
            y = np.array(y, dtype=np.float32)

        # 3. TIMESERIES SPLIT (sem shuffle) â€” Ãºltimos 20% viram validaÃ§Ã£o
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        if len(X_train) < 2 or len(X_val) < 2:
            # Fallback: shuffle split se dados demais pequenos
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42)
        logging.info(
            f"Dados divididos (temporal): {len(X_train)} treino, {len(X_val)} val.")

        # 4. SMOTE (balanceamento de classes) apenas no treino
        smote_aplicado = False
        try:
            from imblearn.over_sampling import SMOTE
            smote = SMOTE(random_state=42)
            X_train, y_train = smote.fit_resample(X_train, y_train)
            smote_aplicado = True
            logging.info(f"âœ… SMOTE aplicado. Treino final: {len(X_train)} amostras.")
        except Exception as e:
            logging.debug(f"SMOTE nÃ£o disponÃ­vel: {e}")

        # 5. SALVAR PESOS DO MODELO ATUAL ANTES DE TREINAR
        modelo_temp_path = MODELO_PATH + ".temp_treino"
        try:
            modelo.save(modelo_temp_path)
        except Exception:
            modelo_temp_path = None

        loss_antiga, acc_antiga = modelo.evaluate(X_val, y_val, verbose=0)
        logging.info(
            f"Performance do Modelo ANTIGO na validaÃ§Ã£o: Loss={loss_antiga:.4f}, AcurÃ¡cia={acc_antiga:.4f}")

        # 6. TREINAR
        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=PATIENCE_EARLY_STOP, restore_best_weights=True)

        sample_weight = np.array(
            [abs(r) * 2.0 + 0.1 if r < 0 else abs(r) * 0.5 + 0.1 for r in recompensas[:len(X_train)]],
            dtype=np.float32)
        # Ajusta tamanho do sample_weight se SMOTE aumentou o dataset
        if smote_aplicado and len(sample_weight) < len(X_train):
            sample_weight = np.ones(len(X_train), dtype=np.float32)

        novo_otimizador = Adam(learning_rate=0.001)
        modelo.compile(optimizer=novo_otimizador,
                       loss='binary_crossentropy', metrics=['accuracy'])

        history = modelo.fit(
            X_train, y_train,
            epochs=EPOCHS_TREINO,
            batch_size=BATCH_SIZE,
            verbose=0,
            validation_data=(X_val, y_val),
            callbacks=[early_stop],
            sample_weight=sample_weight,
            shuffle=False  # Temporal: NÃƒO embaralhar
        )

        # 7. COMPARAR E DECIDIR SE SALVA
        loss_nova, acc_nova = modelo.evaluate(X_val, y_val, verbose=0)
        logging.info(
            f"Performance do Modelo NOVO na validaÃ§Ã£o: Loss={loss_nova:.4f}, AcurÃ¡cia={acc_nova:.4f}")

        melhoria_minima = loss_antiga * 0.01
        if loss_nova < (loss_antiga - melhoria_minima):
            logging.info(
                f"âœ… MELHORIA REAL: Loss {loss_antiga:.4f} â†’ {loss_nova:.4f}. Salvando.")
            salvar_modelo(modelo)
            historico_loss.extend(history.history['val_loss'])
            if modelo_temp_path and os.path.exists(modelo_temp_path):
                try:
                    os.remove(modelo_temp_path)
                except Exception:
                    pass
        else:
            logging.warning(
                f"âŒ SEM MELHORIA ({loss_antiga:.4f} â†’ {loss_nova:.4f}). Restaurando anterior.")
            if modelo_temp_path and os.path.exists(modelo_temp_path):
                try:
                    modelo = carregar_modelo(modelo_temp_path)
                    os.remove(modelo_temp_path)
                except Exception as e:
                    logging.error(f"âŒ Erro ao restaurar: {e}")
                    modelo = carregar_modelo(MODELO_PATH)

        salvar_experiencias_json(memoria.experiencias)
        final_loss = history.history['loss'][-1]
        epochs_trained = len(history.history['loss'])
        logging.info(
            f"ðŸ§  Modelo treinado por {epochs_trained} Ã©pocas. Loss final: {final_loss:.4f}")

    except Exception as e:
        logging.error(f"[treinar_modelo] Erro durante o fit(): {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        return modelo

    # Restaura scaler global do JSON apÃ³s treino (evita corromper escala)
    forcar_recreacao_scaler()

    return modelo


def filtros_alta_acertividade(contexto_completo: Dict) -> Tuple[bool, str]:
    """
    ðŸŽ¯ FILTROS DE MÃXIMA ACERTIVIDADE - SÃ“ OPERA EM SETUPS PREMIUM
    Reduz operaÃ§Ãµes mas aumenta drasticamente a taxa de acerto
    """
    if not contexto_completo:
        return False, "Contexto nÃ£o fornecido"

    # FILTRO 1: Volume ALTO (big players) - AJUSTADO PARA WDO
    volume_total = contexto_completo.get(
        'bid_qty', 0) + contexto_completo.get('ask_qty', 0)
    if volume_total < MIN_VOLUME_BOOK:  # 400cc mÃ­nimo (era 800)
        return False, f"Volume insuficiente: {volume_total} < {MIN_VOLUME_BOOK}"

    # FILTRO 2: Entropia â€” desequilÃ­brio do book
    # FIX (01/08/2026): escala real 2.69-2.97, era 0.2 em [0,1] -> nunca bloqueava
    entropia = contexto_completo.get('entropia_book', 0)
    if entropia < 2.60:
        return False, f"Book equilibrado demais: entropia {entropia:.3f} < 2.60"

    # FILTRO 3: ATR MÃNIMO (volatilidade real)
    # WDO: ATR tÃ­pico 2-10 pontos (tick=0.5). Abaixo de 1.5 = lateral total.
    atr = contexto_completo.get('volatility', 0)  # ATR estÃ¡ como 'volatility'
    if atr < 1.5:
        return False, f"Mercado lateral demais: ATR {atr:.1f} < 1.5"

    # FILTRO 4: RSI confirmando direÃ§Ã£o (FLEXIBILIZADO PARA APRENDIZADO)
    rsi = contexto_completo.get('rsi_14', 50)
    # REMOVIDO: Filtro RSI neutro estava impedindo 80% das operaÃ§Ãµes
    # if 35 <= rsi <= 65:  # RSI neutro - evita
    #     return False, f"RSI neutro: {rsi:.1f} (evitando zona 35-65)"

    # FILTRO 5: Spread controlado
    spread = contexto_completo.get('spread', 0)
    if spread > 10:  # Spread muito alto
        return False, f"Spread muito alto: {spread:.1f} > 10"

    # FILTRO 6: Score de qualidade do setup
    score_qualidade = 0

    # PontuaÃ§Ã£o por volume (peso 3)
    if volume_total >= 1500:
        score_qualidade += 3
    elif volume_total >= 1200:
        score_qualidade += 2
    elif volume_total >= 800:
        score_qualidade += 1

    # PontuaÃ§Ã£o por entropia (peso 3) - escala real (2.69-2.97), era 0.7/0.6/0.5
    if entropia >= 2.85:
        score_qualidade += 3
    elif entropia >= 2.80:
        score_qualidade += 2
    elif entropia >= 2.75:
        score_qualidade += 1

    # PontuaÃ§Ã£o por ATR (peso 3) â€” WDO: ATR tÃ­pico 2-10 pontos
    if atr >= 8:
        score_qualidade += 3
    elif atr >= 5:
        score_qualidade += 2
    elif atr >= 3:
        score_qualidade += 1

    # PontuaÃ§Ã£o por RSI extremo (peso 2)
    if rsi <= 25 or rsi >= 75:
        score_qualidade += 2
    elif rsi <= 30 or rsi >= 70:
        score_qualidade += 1

    # SISTEMA DE APRENDIZADO FORÃ‡ADO - Permite operaÃ§Ãµes para gerar experiÃªncias
    global CONTADOR_OPERACOES_REJEITADAS, MODO_APRENDIZADO_FORCADO
    global FORCADOS_HOJE, FORCADOS_DATA

    if score_qualidade < 2:
        CONTADOR_OPERACOES_REJEITADAS += 1

        if CONTADOR_OPERACOES_REJEITADAS >= LIMITE_REJEICOES_PARA_APRENDIZADO:
            # âœ… PA1: MESMO NO MODO FORÃ‡ADO, RESPEITA HORÃRIO
            if not horario_permitido():
                horario_atual = datetime.now().strftime("%H:%M")
                logging.warning(
                    f"ðŸš« PA1 APRENDIZADO FORÃ‡ADO BLOQUEADO POR HORÃRIO: {horario_atual}")
                return False, f"Aprendizado forÃ§ado bloqueado por horÃ¡rio: {horario_atual}"

            # LIMITE DIÃRIO: mÃ¡ximo 3 operaÃ§Ãµes forÃ§adas por dia
            hoje = datetime.now().date()
            if FORCADOS_DATA != hoje:
                FORCADOS_HOJE = 0
                FORCADOS_DATA = hoje

            if FORCADOS_HOJE >= MAX_FORCADOS_DIA:
                logging.warning(
                    f"ðŸš« LIMITE DIÃRIO DE FORÃ‡ADOS ATINGIDO: {FORCADOS_HOJE}/{MAX_FORCADOS_DIA}. Bloqueando.")
                CONTADOR_OPERACOES_REJEITADAS = 0
                return False, f"Limite diÃ¡rio de aprendizado forÃ§ado atingido ({MAX_FORCADOS_DIA}/dia)"

            CONTADOR_OPERACOES_REJEITADAS = 0
            FORCADOS_HOJE += 1
            MODO_APRENDIZADO_FORCADO = True
            logging.warning(
                f"ðŸŽ“ APRENDIZADO FORÃ‡ADO {FORCADOS_HOJE}/{MAX_FORCADOS_DIA}: Score {score_qualidade}/11 aceito")
            return True, f"Aprendizado forÃ§ado {FORCADOS_HOJE}/{MAX_FORCADOS_DIA} (score {score_qualidade}/11)"

        logging.info(
            f"âŒ C10: Score {score_qualidade}/11 < 2. OperaÃ§Ã£o bloqueada. RejeiÃ§Ãµes: {CONTADOR_OPERACOES_REJEITADAS}/{LIMITE_REJEICOES_PARA_APRENDIZADO}")
        return False, f"Setup de baixa qualidade: score {score_qualidade}/11 < 2 (RejeiÃ§Ãµes: {CONTADOR_OPERACOES_REJEITADAS}/{LIMITE_REJEICOES_PARA_APRENDIZADO})"

    # Reset contador quando o setup Ã© bom
    CONTADOR_OPERACOES_REJEITADAS = 0

    # Setup aprovado
    logging.info(
        f"âœ… C10: SETUP APROVADO! Score: {score_qualidade}/11 | Vol: {volume_total} | Entropia: {entropia:.3f} | ATR: {atr:.1f} | RSI: {rsi:.1f}")
    return True, f"C10: Setup aprovado (score {score_qualidade}/11)"


def prever_acao(modelo: Sequential, X: pd.DataFrame,
                modo_operacional: Optional[ModoOperacional] = None,
                filtros_evolutivos: Optional[Any] = None,
                contexto_completo: Optional[Dict] = None) -> Tuple[str, float]:
    """PrevÃª a prÃ³xima aÃ§Ã£o com VETO SIMPLES E DIRETO baseado na sugestÃ£o da IA."""
    # Inicializa flag de veto (False = sem veto ativo)
    prever_acao._ultimo_veto = False
    try:
        # ========== âœ… PRIORIDADE 0: COOLDOWN â€” NADA PASSA ANTES DISSO ==========
        # Regra Sniper: Se cooldown ativo, retorna NADA imediatamente sem ler book ou consultar IA
        if COOLDOWN_ATIVO and cooldown_sistema and not cooldown_sistema.pode_operar():
            tempo_restante = cooldown_sistema.tempo_restante_cooldown()
            logging.info(
                f"ðŸ›‘ [P0] COOLDOWN ATIVO ({tempo_restante}s restantes) â€” Bloqueio total, aguardando...")
            return "NADA", 0.0

        # ========== âœ… PA1: TRAVA DE HORÃRIO - PRIORIDADE MÃXIMA ==========
        if not horario_permitido():
            # Log com throttle (1x a cada 300s) â€” fora do horÃ¡rio PA1 isso repetiria
            # a cada ciclo e inundaria o log.
            if _log_periodico('pa1_bloqueado', 300):
                horario_atual = datetime.now().strftime("%H:%M")
                logging.info(
                    f"ðŸš« PA1 HORÃRIO BLOQUEADO: {horario_atual} - SÃ³ opera 09:15-12:30 e 14:30-17:15")
            return "NADA", 0.0

        # ========== SENTINELA DE FLUXO (gatekeeper macro) - classifica 1x ==========
        # Fail-open: qualquer erro/indisponibilidade => NEUTRO => sem veto.
        _sf_veto_buy = False
        _sf_veto_sell = False
        _sf_detalhe = ""
        if SENTINELA_ATIVO:
            try:
                global sentinela_cenario, sentinela_detalhe, sentinela_score, sentinela_ultima_atualizacao
                _sf = sentinela_fluxo.classificar()
                sentinela_cenario = _sf['cenario']
                sentinela_detalhe = _sf['detalhe']
                sentinela_score = _sf['score']
                sentinela_ultima_atualizacao = _sf['atualizado']
                _sf_detalhe = _sf['detalhe']
                if _sf['cenario'] == 'RISK_OFF':
                    _sf_veto_sell = True  # so BUY liberado
                elif _sf['cenario'] == 'RISK_ON':
                    _sf_veto_buy = True  # so SELL liberado
            except Exception as _e:
                logging.debug(f"Sentinela de fluxo indisponível (fail-open): {_e}")

# ========== VETO SIMPLES + WILLIAMS %R ==========
        if contexto_completo:
            pode_buy, motivo_buy = deve_operar_contexto_simples(
                contexto_completo, "BUY")
            pode_sell, motivo_sell = deve_operar_contexto_simples(
                contexto_completo, "SELL")

            # WILLIAMS %R: TRAVA DE SOBRECOMPRA/SOBREVENDIDO
            wr_val = contexto_completo.get('williams_r', -50)
            if pode_buy and wr_val > -20:
                logging.warning(f"WILLIAMS %R VETO BUY: WR={wr_val:.0f} (sobrecomprado)")
                pode_buy = False
            if pode_sell and wr_val < -80:
                logging.warning(f"WILLIAMS %R VETO SELL: WR={wr_val:.0f} (sobrevendido)")
                pode_sell = False
            # WILLIAMS %R: VETO BUY EM SOBREVENDA EXTREMA (continuaÃ§Ã£o de queda, nÃ£o fundo)
            # THRESHOLD -80: simÃ©trico ao veto SELL (WR < -80 = sobrevenda agressiva)
            if pode_buy and wr_val < -80:
                logging.warning(f"WILLIAMS %R VETO BUY (continuaÃ§Ã£o): WR={wr_val:.0f} (< -80, sobrevenda agressiva)")
                pode_buy = False

            # MULTI-TF VETO: nÃ£o comprar contra 3 timeframes bearish
            m5_rsi = contexto_completo.get('m5_rsi', 50)
            m15_rsi = contexto_completo.get('m15_rsi', 50)
            m30_rsi = contexto_completo.get('m30_rsi', 50)
            if pode_buy and m5_rsi < 50 and m15_rsi < 50 and m30_rsi < 50:
                logging.warning(f"MULTI-TF VETO BUY: M5_RSI={m5_rsi:.1f} M15_RSI={m15_rsi:.1f} M30_RSI={m30_rsi:.1f} (todos < 50)")
                pode_buy = False

            # Se ambas negativas, nao opera
            if not pode_buy and not pode_sell:
                logging.warning(f"VETO TOTAL: BUY={motivo_buy}, SELL={motivo_sell}")
                return "NADA", 0.0

            # Se so uma viavel, forca essa (com proteÃ§Ã£o Multi-TF)
            if pode_buy and not pode_sell:
                # NÃ£o forÃ§ar BUY se Multi-TF mostra bearish (todos < 50)
                if m5_rsi < 50 and m15_rsi < 50 and m30_rsi < 50:
                    logging.warning(f"FORÃ‡A BUY BLOQUEADO: Multi-TF bearish (M5={m5_rsi:.0f} M15={m15_rsi:.0f} M30={m30_rsi:.0f})")
                    return "NADA", 0.0
                if _sf_veto_buy:
                    logging.warning(f"ðŸš« SENTINELA VETO BUY: {_sf_detalhe}")
                    prever_acao._ultimo_veto = True
                    return "NADA", 0.0
                logging.info(f"FORCA BUY: {motivo_buy}")
                return "BUY", 0.8
            if pode_sell and not pode_buy:
                # NÃ£o forÃ§ar SELL se Multi-TF mostra bullish (todos > 50)
                if m5_rsi > 50 and m15_rsi > 50 and m30_rsi > 50:
                    logging.warning(f"FORÃ‡A SELL BLOQUEADO: Multi-TF bullish (M5={m5_rsi:.0f} M15={m15_rsi:.0f} M30={m30_rsi:.0f})")
                    return "NADA", 0.0
                if _sf_veto_sell:
                    logging.warning(f"ðŸš« SENTINELA VETO SELL: {_sf_detalhe}")
                    prever_acao._ultimo_veto = True
                    return "NADA", 0.0
                logging.info(f"FORCA SELL: {motivo_sell}")
                return "SELL", 0.8

# ========== FILTRO DE TENDÃŠNCIA (SMA-50 + MOMENTUM) ==========
        # Bloqueia operaÃ§Ãµes contra a tendÃªncia para evitar comprar em queda
        # Avalia UMA VEZ (avaliar_tendencia registra preÃ§o e calcula tudo)
        _tendencia_veto_buy = False
        _tendencia_veto_sell = False
        preco_atual_tend = None
        if contexto_completo:
            preco_atual_tend = contexto_completo.get('preco', 0) or contexto_completo.get('preco_maior_escora_bid', 0)
        if preco_atual_tend and preco_atual_tend > 0:
            _tendencia_result = filtro_tendencia.avaliar_tendencia(preco_atual_tend)
            _tendencia_veto_buy = _tendencia_result['veto_buy']
            _tendencia_veto_sell = _tendencia_result['veto_sell']

            if _tendencia_veto_buy and _tendencia_veto_sell:
                logging.warning(f"ðŸš« TENDÃŠNCIA VETO TOTAL: {_tendencia_result['motivo']}")
                return "NADA", 0.0
            if _tendencia_veto_buy:
                logging.info(f"ðŸš« TENDÃŠNCIA BLOQUEIA BUY: {_tendencia_result['motivo']}")
            if _tendencia_veto_sell:
                logging.info(f"ðŸš« TENDÃŠNCIA BLOQUEIA SELL: {_tendencia_result['motivo']}")

        # ========== FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR ==========
        if contexto_completo:
            if bloqueador_contexto.contexto_bloqueado(contexto_completo):
                return "NADA", 0.0

        # ========== FASE 2: CONSULTA EXPERIÃŠNCIAS PASSADAS ==========
        if contexto_completo:
            expectativa_buy = replay_experiencias.calcular_expectativa_contexto(
                contexto_completo, "BUY")
            expectativa_sell = replay_experiencias.calcular_expectativa_contexto(
                contexto_completo, "SELL")

            tem_dados_buy = expectativa_buy['trades_similares'] >= 5
            tem_dados_sell = expectativa_sell['trades_similares'] >= 5

            # VETO MATEMÃTICO: SÃ³ veta se tiver dados suficientes E expectativa NEGATIVA REAL
            # Sem dados (0.00) = NEUTRO = deixa passar para IA/ConfluÃªncia decidirem
            if tem_dados_buy and tem_dados_sell:
                if expectativa_buy['expectativa'] < 0 and expectativa_sell['expectativa'] < 0:
                    logging.warning(
                        f"ðŸš« VETO MATEMÃTICO (prova real): BUY={expectativa_buy['expectativa']:.2f} "
                        f"({expectativa_buy['trades_similares']} trades), "
                        f"SELL={expectativa_sell['expectativa']:.2f} "
                        f"({expectativa_sell['trades_similares']} trades)")
                    # HIERARQUIA: Veto negativo - nada mais sobrescreve
                    prever_acao._ultimo_veto = True
                    return "NADA", 0.0

            # Se uma direÃ§Ã£o tem dados positivos e a outra nÃ£o tem dados ou Ã© negativa
            if tem_dados_buy and expectativa_buy['expectativa'] > 0:
                if not tem_dados_sell or expectativa_sell['expectativa'] <= 0:
                    if _sf_veto_buy:
                        logging.warning(f"ðŸš« SENTINELA VETO BUY: {_sf_detalhe}")
                        prever_acao._ultimo_veto = True
                        return "NADA", 0.0
                    logging.info(
                        f"ðŸŽ¯ FORÃ‡A BUY por expectativa positiva: {expectativa_buy['expectativa']:.2f} "
                        f"({expectativa_buy['trades_similares']} trades)")
                    prever_acao._ultimo_veto = False
                    return "BUY", min(0.9, expectativa_buy['expectativa'] / 100)

            if tem_dados_sell and expectativa_sell['expectativa'] > 0:
                if not tem_dados_buy or expectativa_buy['expectativa'] <= 0:
                    if _sf_veto_sell:
                        logging.warning(f"ðŸš« SENTINELA VETO SELL: {_sf_detalhe}")
                        prever_acao._ultimo_veto = True
                        return "NADA", 0.0
                    logging.info(
                        f"ðŸŽ¯ FORÃ‡A SELL por expectativa positiva: {expectativa_sell['expectativa']:.2f} "
                        f"({expectativa_sell['trades_similares']} trades)")
                    prever_acao._ultimo_veto = False
                    return "SELL", min(0.9, expectativa_sell['expectativa'] / 100)

            # Sem dados suficientes em nenhuma direÃ§Ã£o: log neutro e deixa passar
            if not tem_dados_buy and not tem_dados_sell:
                logging.debug(
                    f"ðŸ“Š Sem histÃ³rico suficiente (BUY:{expectativa_buy['trades_similares']}, "
                    f"SELL:{expectativa_sell['trades_similares']}) - IA decide normalmente")

            # Dados mistos ou inconclusivos: NÃƒO forÃ§a direÃ§Ã£o â€” deixa IA decidir
            prever_acao._ultimo_veto = False

        # ========== APLICAÃ‡ÃƒO DOS FILTROS DE ALTA ACERTIVIDADE ==========
        if contexto_completo:
            pode_operar, motivo = filtros_alta_acertividade(contexto_completo)
            if not pode_operar:
                if not hasattr(prever_acao, '_ultimo_log_bloqueio'):
                    prever_acao._ultimo_log_bloqueio = 0
                if time.time() - prever_acao._ultimo_log_bloqueio >= 60:
                    logging.info(f"BLOQUEIO: {motivo}")
                    prever_acao._ultimo_log_bloqueio = time.time()
                return "NADA", 0.0

        # VALIDAÃ‡ÃƒO E CORREÃ‡ÃƒO DE TIPOS PARA PREDIÃ‡ÃƒO
        if hasattr(X, 'values'):
            x_pred = X.values.astype(np.float32)
        else:
            x_pred = np.array(X, dtype=np.float32)

        # Verifica se hÃ¡ valores invÃ¡lidos
        if np.isnan(x_pred).any() or np.isinf(x_pred).any():
            logging.warning(
                "[prever_acao] Dados contÃªm valores NaN ou infinitos - corrigindo")
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
            logging.warning("âš ï¸ PrevisÃ£o vazia ou invÃ¡lida")
            return "NADA", 0.0

        acao_prob = float(resultado_predicao[0][0])  # Garante que Ã© float
        confianca = 1.0

        # Log detalhado da prediÃ§Ã£o para diagnÃ³stico
        logging.debug(
            f"[prever_acao] Resultado bruto da prediÃ§Ã£o: {resultado_predicao[0][0]}")
        logging.debug(f"[prever_acao] Probabilidade processada: {acao_prob}")

        # Se a probabilidade estÃ¡ muito baixa (prÃ³xima de 0), pode indicar problema no modelo
        if acao_prob < 0.001:
            logging.warning(
                f"âš ï¸ Probabilidade muito baixa: {acao_prob:.6f} - Modelo pode precisar de retreino")
            # ForÃ§a uma decisÃ£o baseada em RSI como fallback
            if 'rsi_14' in X.columns:
                rsi_val_scaled = X['rsi_14'].iloc[0]
                # X jÃ¡ estÃ¡ escalado pelo scaler: rsi_14 min=1.0, max=100.0
                rsi_val_real = rsi_val_scaled * 99.0 + 1.0
                if rsi_val_real < 30:  # Sobrevenda - favorece compra
                    acao_prob = 0.7
                    logging.info(
                        f"ðŸ”„ Fallback RSI: RSI={rsi_val_real:.1f} (raw) < 30, forÃ§ando BUY (prob={acao_prob})")
                elif rsi_val_real > 70:  # Sobrecompra - favorece venda
                    acao_prob = 0.3
                    logging.info(
                        f"ðŸ”„ Fallback RSI: RSI={rsi_val_real:.1f} (raw) > 70, forÃ§ando SELL (prob={acao_prob})")
                else:
                    # RSI neutro - usa desequilÃ­brio do book para direÃ§Ã£o
                    bid_dom = float(contexto_completo.get('bid_qty', 0)) if contexto_completo else 0
                    ask_dom = float(contexto_completo.get('ask_qty', 0)) if contexto_completo else 0
                    if bid_dom > ask_dom:
                        acao_prob = 0.6  # Mais compradores â†’ favorece BUY
                        logging.info(
                            f"ðŸ”„ Fallback Book: BID {bid_dom:.0f} > ASK {ask_dom:.0f}, favorecendo BUY")
                    elif ask_dom > bid_dom:
                        acao_prob = 0.4  # Mais vendedores â†’ favorece SELL
                        logging.info(
                            f"ðŸ”„ Fallback Book: ASK {ask_dom:.0f} > BID {bid_dom:.0f}, favorecendo SELL")
                    else:
                        acao_prob = 0.5  # Equilibrado â†’ neutro
                        logging.info(
                            f"ðŸ”„ Fallback Book: BID=ASK={bid_dom:.0f}, neutro")

        # Ajusta threshold baseado no balanceamento atual
        if memoria_experiencias:
            status = memoria_experiencias.get_balanceamento_status()
            razao_atual = status["razao_buy_sell"]

            # Log detalhado do estado atual
            logging.info(
                f"ðŸ“Š Estado atual - Prob. compra: {acao_prob:.3f}, RSI: {X['rsi_14'].iloc[0]:.1f}")

            # ========== INTEGRAÃ‡ÃƒO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
            threshold_base = 0.5
            acao_forcada_balanceador = None

            if balanceador and BALANCEAMENTO_ATIVO:
                threshold_base = balanceador.ajustar_threshold(threshold_base)
                status = balanceador.get_status()
                logging.info(f"âš–ï¸ Balanceamento: BUY={status['buy_count']}, SELL={status['sell_count']}, "
                             f"BUY%={status['buy_percentage']:.1f}%, Threshold ajustado={threshold_base:.3f}")

                # Verifica se deve forÃ§ar operaÃ§Ã£o pelo balanceador
                if status['deve_forcar']:
                    acao_forcada_balanceador = status['acao_forcada']
                    logging.info(
                        f"ðŸš¨ BALANCEADOR FORÃ‡A: {acao_forcada_balanceador} devido a desbalanceamento extremo")

            # Ajusta threshold dinamicamente com MAIS AGRESSIVIDADE
            max_ajuste = 0.25  # Aumentado para 25% (mais agressivo)

            # Considera RSI para ajuste adicional
            rsi = X['rsi_14'].iloc[0]
            rsi_ajuste = 0.0

            if rsi < 30:  # Sobrevenda
                rsi_ajuste = -0.05  # Favorece compras
            elif rsi > 70:  # Sobrecompra
                rsi_ajuste = 0.05  # Favorece vendas

            # Filtro de ConfianÃ§a MÃ­nima (confidence gap 0.15) â€” zona neutra
            CONFIDENCE_GAP = 0.15
            confianca = abs(acao_prob - 0.5)
            if confianca < CONFIDENCE_GAP:
                logging.info(
                    f"â¸ï¸ Sinal NEUTRO (confianÃ§a {confianca:.3f} < {CONFIDENCE_GAP}) | Prob: {acao_prob:.3f} | Ignorado")
                return "NADA", 0.0

            # DecisÃ£o baseada na probabilidade (sem forÃ§ar lado)
            threshold = threshold_base + rsi_ajuste
            acao_inicial = "BUY" if acao_prob > threshold else "SELL"
            logging.info(
                f"ðŸ“Š DecisÃ£o por probabilidade: {acao_inicial} | Prob: {acao_prob:.3f} | ConfianÃ§a: {confianca:.3f} | Threshold: {threshold:.3f}")

            # ========== ESTRATÃ‰GIA ESCALONADA POR QUALIDADE DO SETUP ==========
            if contexto_completo:
                volume_total = contexto_completo.get(
                    'bid_qty', 0) + contexto_completo.get('ask_qty', 0)
                entropia = contexto_completo.get('entropia_book', 0)
                atr = contexto_completo.get('volatility', 0)

                # Calcula score de qualidade novamente para definir estratÃ©gia
                score_qualidade = 0
                if volume_total >= 1500:
                    score_qualidade += 3
                elif volume_total >= 1200:
                    score_qualidade += 2
                elif volume_total >= 800:
                    score_qualidade += 1

                if entropia >= 2.85:
                    score_qualidade += 3
                elif entropia >= 2.80:
                    score_qualidade += 2
                elif entropia >= 2.75:
                    score_qualidade += 1

                if atr >= 8:
                    score_qualidade += 3
                elif atr >= 5:
                    score_qualidade += 2
                elif atr >= 3:
                    score_qualidade += 1

                # Define parÃ¢metros baseado na qualidade do setup
                if score_qualidade >= 8:  # Setup ULTRA PREMIUM
                    confianca = 0.95
                    logging.info(
                        f"ðŸ† SETUP ULTRA PREMIUM (score {score_qualidade}/11) - ConfianÃ§a mÃ¡xima!")
                elif score_qualidade >= 6:  # Setup PREMIUM
                    confianca = 0.85
                    logging.info(
                        f"â­ SETUP PREMIUM (score {score_qualidade}/11) - Alta confianÃ§a")
                else:  # Setup BOM (jÃ¡ passou nos filtros)
                    confianca = 0.75
                    logging.info(
                        f"âœ… SETUP BOM (score {score_qualidade}/11) - ConfianÃ§a moderada")

            # ========== APLICAÃ‡ÃƒO DOS FILTROS ADICIONAIS ==========
            # Filtro 1: HorÃ¡rio Premium
            if FILTRO_HORARIO_ATIVO and filtro_horario and not filtro_horario.is_horario_premium():
                logging.info("â° OperaÃ§Ã£o bloqueada - Fora do horÃ¡rio premium")
                return "NADA", 0.0

            # Filtro 2: TendÃªncia em CONSENSO (sÃ³ bloqueia se AMBOS detectores concordarem)
            if DETECTOR_TENDENCIA_ATIVO and detector_tendencia:
                _ema_bloqueia_buy = detector_tendencia.tendencia_atual == "BAIXA" and acao_inicial == "BUY"
                _ema_bloqueia_sell = detector_tendencia.tendencia_atual == "ALTA" and acao_inicial == "SELL"
                _sma_bloqueia_buy = _tendencia_veto_buy and acao_inicial == "BUY"
                _sma_bloqueia_sell = _tendencia_veto_sell and acao_inicial == "SELL"
                if (_ema_bloqueia_buy and _sma_bloqueia_buy) or (_ema_bloqueia_sell and _sma_bloqueia_sell):
                    logging.info(
                        f"ðŸ“ˆ CONSENSO DE TENDÃŠNCIA: {acao_inicial} bloqueado "
                        f"(EMA={detector_tendencia.tendencia_atual}, SMA={_tendencia_result['motivo']})")
                    return "NADA", 0.0

            # Filtro 3: Cooldown â€” jÃ¡ verificado na Prioridade 0, mantido aqui como seguranÃ§a de redundÃ¢ncia
            # (nÃ£o gera log duplicado pois Prioridade 0 jÃ¡ bloqueou antes de chegar aqui)

            # Filtro 4: Spread dinÃ¢mico
            spread_atual = contexto_completo.get(
                'spread', 0) if contexto_completo else 0
            if SPREAD_DINAMICO_ATIVO and filtro_spread and not filtro_spread.spread_aceitavel(spread_atual):
                logging.info(
                    f"ðŸ“Š OperaÃ§Ã£o bloqueada - Spread alto ({spread_atual:.1f} >{filtro_spread.spread_maximo_atual})")
                return "NADA", 0.0

            # DECISÃƒO FINAL: Considera ambos os sistemas de balanceamento
            if acao_forcada_balanceador:
                acao = acao_forcada_balanceador
                logging.info(
                    f"ðŸŽ¯ DECISÃƒO FINAL FORÃ‡ADA pelo balanceador: {acao}")
            else:
                acao = acao_inicial
                logging.info(f"ðŸŽ¯ DECISÃƒO FINAL normal: {acao}")

            # ========== VETO DE TENDÃŠNCIA (pÃ³s-decisÃ£o) ==========
            # Se o modelo escolheu BUY mas tendÃªncia Ã© de baixa â†’ bloqueia
            # EXCETO se RSI estiver em zona extrema (mean reversion)
            if acao == "BUY" and _tendencia_veto_buy:
                rsi_override = rsi * 99.0 + 1.0
                if rsi_override < 25.0:
                    logging.info(f"ðŸ“Š RSI={rsi_override:.1f} (sobrevendido) sobrepÃµe veto de tendÃªncia - BUY liberado")
                else:
                    logging.warning(f"ðŸš« TENDÃŠNCIA VETO pÃ³s-decisÃ£o: BUY bloqueado (mercado em queda, RSI={rsi_override:.1f})")
                    return "NADA", 0.0
            if acao == "SELL" and _tendencia_veto_sell:
                rsi_override = rsi * 99.0 + 1.0
                if rsi_override > 75.0:
                    logging.info(f"ðŸ“Š RSI={rsi_override:.1f} (sobrecomprado) sobrepÃµe veto de tendÃªncia - SELL liberado")
                else:
                    logging.warning(f"ðŸš« TENDÃŠNCIA VETO pÃ³s-decisÃ£o: SELL bloqueado (mercado em alta, RSI={rsi_override:.1f})")
                    return "NADA", 0.0

            # ========== FILTRO MEAN REVERSION (RSI + Z-Score + ADX) ==========
            rsi_real = rsi * 99.0 + 1.0  # Desescala RSI do scaler
            preco_atual_tend = contexto_completo.get('preco', 0) if contexto_completo else 0
            if preco_atual_tend and preco_atual_tend > 0 and rsi_real > 0:
                mr_result = filtro_mean_reversion.avaliar(
                    preco_atual=preco_atual_tend,
                    rsi_real=rsi_real,
                    ema_atual=preco_atual_tend,  # Usando preÃ§o como proxy da EMA
                    ema_anterior=preco_atual_tend
                )
                if mr_result['veto_buy'] and acao == "BUY":
                    logging.warning(
                        f"ðŸš« MR VETO BUY: RSI={rsi_real:.1f}({mr_result['rsi_zona']}) | "
                        f"Z={mr_result['zscore']:+.2f} | ADX={mr_result['adx']:.1f}({mr_result['estado']})")
                    return "NADA", 0.0
                if mr_result['veto_sell'] and acao == "SELL":
                    logging.warning(
                        f"ðŸš« MR VETO SELL: RSI={rsi_real:.1f}({mr_result['rsi_zona']}) | "
                        f"Z={mr_result['zscore']:+.2f} | ADX={mr_result['adx']:.1f}({mr_result['estado']})")
                    return "NADA", 0.0

            # Log detalhado do balanceamento
            if balanceador and BALANCEAMENTO_ATIVO:
                status_bal = balanceador.get_status()
                logging.info(
                    f"ðŸ”„ Balanceamento - BUY: {status_bal['buy_percentage']:.1f}% | SELL: {status_bal['sell_percentage']:.1f}%")
            else:
                mem_status = memoria_experiencias.get_balanceamento_status()
                logging.info(
                    f"ðŸ”„ Balanceamento - BUY: {mem_status['buy_percent']:.1f}% | SELL: {mem_status['sell_percent']:.1f}%")
            # Log detalhado da decisÃ£o final
            if acao_forcada_balanceador:
                logging.info(
                    f"ðŸ“ˆ DecisÃ£o FORÃ‡ADA: {acao} | Prob original: {acao_prob:.3f} | Threshold: {threshold:.3f} | IGNORADO por balanceamento")
            else:
                logging.info(
                    f"ðŸ“ˆ DecisÃ£o normal: {acao} | Prob: {acao_prob:.3f} | Threshold: {threshold:.3f}")
        else:
            threshold = 0.5
            acao = "BUY" if acao_prob > threshold else "SELL"
            logging.info(
                f"ðŸ“ˆ DecisÃ£o sem balanceamento: {acao} | Prob: {acao_prob:.3f}")

        # ========== VETO DE TENDÃŠNCIA (pÃ³s-decisÃ£o, fora do balanceador) ==========
        if acao == "BUY" and _tendencia_veto_buy:
            rsi_over = rsi * 99.0 + 1.0
            if rsi_over < 25.0:
                logging.info(f"ðŸ“Š RSI={rsi_over:.1f} (sobrevendido) sobrepÃµe veto de tendÃªncia - BUY liberado")
            else:
                logging.warning(f"ðŸš« TENDÃŠNCIA VETO pÃ³s-decisÃ£o: BUY bloqueado (mercado em queda, RSI={rsi_over:.1f})")
                return "NADA", 0.0
        if acao == "SELL" and _tendencia_veto_sell:
            rsi_over = rsi * 99.0 + 1.0
            if rsi_over > 75.0:
                logging.info(f"ðŸ“Š RSI={rsi_over:.1f} (sobrecomprado) sobrepÃµe veto de tendÃªncia - SELL liberado")
            else:
                logging.warning(f"ðŸš« TENDÃŠNCIA VETO pÃ³s-decisÃ£o: SELL bloqueado (mercado em alta, RSI={rsi_over:.1f})")
                return "NADA", 0.0

        # ========== FILTRO MEAN REVERSION (pÃ³s-decisÃ£o, fora do balanceador) ==========
        rsi_real_fallback = rsi * 99.0 + 1.0
        preco_atual_tend_fb = contexto_completo.get('preco', 0) if contexto_completo else 0
        if preco_atual_tend_fb and preco_atual_tend_fb > 0 and rsi_real_fallback > 0:
            mr_fb = filtro_mean_reversion.avaliar(
                preco_atual=preco_atual_tend_fb,
                rsi_real=rsi_real_fallback,
                ema_atual=preco_atual_tend_fb,
                ema_anterior=preco_atual_tend_fb
            )
            if mr_fb['veto_buy'] and acao == "BUY":
                logging.warning(
                    f"ðŸš« MR VETO BUY: RSI={rsi_real_fallback:.1f}({mr_fb['rsi_zona']}) | "
                    f"Z={mr_fb['zscore']:+.2f} | ADX={mr_fb['adx']:.1f}({mr_fb['estado']})")
                return "NADA", 0.0
            if mr_fb['veto_sell'] and acao == "SELL":
                logging.warning(
                    f"ðŸš« MR VETO SELL: RSI={rsi_real_fallback:.1f}({mr_fb['rsi_zona']}) | "
                    f"Z={mr_fb['zscore']:+.2f} | ADX={mr_fb['adx']:.1f}({mr_fb['estado']})")
                return "NADA", 0.0

        # ========== SENTINELA DE FLUXO (gatekeeper macro) - veto final ==========
        if _sf_veto_sell and acao == 'SELL':
            logging.warning(f"ðŸš« SENTINELA VETO SELL: {_sf_detalhe}")
            prever_acao._ultimo_veto = True
            return "NADA", 0.0
        if _sf_veto_buy and acao == 'BUY':
            logging.warning(f"ðŸš« SENTINELA VETO BUY: {_sf_detalhe}")
            prever_acao._ultimo_veto = True
            return "NADA", 0.0

        return acao, confianca
    except Exception as e:
        logging.error(f"âŒ Erro ao prever aÃ§Ã£o: {e}")
        return "NADA", 0.0


def salvar_experiencias_json(experiencias: List[Tuple[Dict[str, Any], str, float, float]], arquivo: str = "experiencias_wdo.json") -> None:
    """
    âœ… PA2: FILTRO DE MEMÃ“RIA: Salva as experiÃªncias em formato JSON.
    SÃ³ salva experiÃªncias com lucro > 0 conforme plano de aÃ§Ã£o.
    """
    try:
        dados = []
        experiencias_positivas = 0
        experiencias_totais = len(experiencias)

        for contexto, acao, lucro, score_dist in experiencias:
            # âœ… PA2: FILTRO DE MEMÃ“RIA: SÃ³ salva se lucro > 0
            if lucro > 0:
                dados.append({
                    "contexto": contexto,
                    "acao": acao,
                    "lucro": lucro,
                    "score_dist": score_dist,
                    "timestamp": datetime.now().isoformat()
                })
                experiencias_positivas += 1

        with open(arquivo, 'w') as f:
            json.dump(dados, f, indent=2)

        logging.info(
            f"âœ… PA2 FILTRO DE MEMÃ“RIA: {experiencias_positivas}/{experiencias_totais} experiÃªncias positivas salvas em {arquivo}")

    except Exception as e:
        logging.error(f"âŒ Erro ao salvar experiÃªncias em JSON: {e}")


def salvar_decisao_csv(acao: str, confianca: float, contexto: Dict[str, Any], arquivo: str = None) -> None:
    if arquivo is None:
        arquivo = DECISIONS_CSV
    """Salva uma decisÃ£o no arquivo CSV de decisÃµes."""
    try:
        abs_path_arquivo = os.path.abspath(arquivo)
        logging.debug(
            f"[salvar_decisao_csv] Tentando salvar decisÃ£o em: {abs_path_arquivo}")

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
        logging.debug(
            f"[salvar_decisao_csv] Arquivo '{abs_path_arquivo}' existe: {file_exists}, Tamanho: {file_size} bytes")

        # Escreve com cabeÃ§alho se o arquivo nÃ£o existe OU se existe mas estÃ¡ vazio.
        if not file_exists or (file_exists and file_size == 0):
            df.to_csv(abs_path_arquivo, index=False)
        else:
            # Adiciona sem cabeÃ§alho se o arquivo jÃ¡ existe e tem conteÃºdo.
            df.to_csv(abs_path_arquivo, mode='a', header=False, index=False)

        logging.debug(f"âœ… DecisÃ£o salva em {abs_path_arquivo}")
    except Exception as e:
        logging.error(f"âŒ Erro ao salvar decisÃ£o em CSV: {e}")

# endregion

# region [FunÃ§Ãµes de Mercado]


def verificar_estado_book(symbol: str = SYMBOL) -> bool:
    """Verifica se o book estÃ¡ ativo e funcionando corretamente."""
    try:
        # Verifica se Ã© fim de semana
        if datetime.now().weekday() > 4:  # 5 = SÃ¡bado, 6 = Domingo
            logging.info(
                "ðŸ“… Fim de semana: book nÃ£o disponÃ­vel (comportamento normal)")
            return True  # Retorna True para evitar tentativas de reinicializaÃ§Ã£o

        # Verifica se Ã© horÃ¡rio de mercado fechado (fora do pregÃ£o)
        agora = datetime.now().time()
        inicio_pregao = datetime.strptime("09:00", "%H:%M").time()
        fim_pregao = datetime.strptime("17:40", "%H:%M").time()

        if agora < inicio_pregao or agora > fim_pregao:
            logging.info(
                f"ðŸ• Mercado fechado ({agora.strftime('%H:%M')}): book nativo indisponÃ­vel (normal)")
            # Fora do pregÃ£o o book nativo fica vazio â€” retorna True para nÃ£o
            # disparar reinicializaÃ§Ãµes desnecessÃ¡rias do book.
            return True

        # Garante que o sÃ­mbolo esteja selecionado
        mt5.symbol_select(symbol)

        # Verifica se o sÃ­mbolo estÃ¡ ativo
        if not mt5.symbol_info(symbol):
            logging.error(f"âŒ SÃ­mbolo {symbol} nÃ£o encontrado")
            return False

        # Tenta obter dados do book
        book = mt5.market_book_get(symbol)

        if book is None:
            return False

        if len(book) == 0:
            logging.error("âŒ Book vazio")
            return False

        # Verifica tipos no book
        tipos_ordem = set(level.type for level in book)
        if len(tipos_ordem) < 2:
            logging.error("Book incompleto: tipos insuficientes")
            return False

    except Exception as e:
        logging.error(f"âŒ Erro ao verificar book: {e}")
        return False


def reiniciar_book(symbol: str = SYMBOL) -> bool:
    """Tenta reiniciar o book de ofertas."""
    try:
        # Desativa o book
        mt5.market_book_release(symbol)
        time.sleep(1)  # Espera 1 segundo

        # Reativa o book
        if not mt5.market_book_add(symbol):
            logging.error("âŒ Falha ao reativar book")
            return False

        time.sleep(1)  # Espera mais 1 segundo

        # Verifica se estÃ¡ funcionando
        return verificar_estado_book(symbol)

    except Exception as e:
        logging.error(f"âŒ Erro ao reiniciar book: {e}")
        return False


def calcular_atr(high_prices: List[float], low_prices: List[float], close_prices: List[float], periodo: int = 14) -> float:
    """
    Calcula o Average True Range (ATR) para um perÃ­odo especÃ­fico.

    Args:
        high_prices: Lista de preÃ§os mÃ¡ximos
        low_prices: Lista de preÃ§os mÃ­nimos
        close_prices: Lista de preÃ§os de fechamento
        periodo: PerÃ­odo para cÃ¡lculo do ATR (default 14)

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

    # Calcula mÃ©dia mÃ³vel do TR para obter ATR
    if not tr_values:
        return 0.0

    # Implementa Wilder's Smoothing
    atr = tr_values[0]  # Primeiro TR como valor inicial
    for tr in tr_values[1:]:
        atr = ((periodo - 1) * atr + tr) / periodo

    return atr


def verificar_mercado_aberto() -> Tuple[bool, str]:
    """Verifica se o mercado estÃ¡ aberto e em qual perÃ­odo."""
    agora = datetime.now().time()
    pregao = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    after = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    # Verifica se Ã© fim de semana
    if datetime.now().weekday() > 4:  # 5 = SÃ¡bado, 6 = Domingo
        return False, "Mercado fechado (Fim de semana) ðŸ–ï¸"

    # Verifica horÃ¡rio
    if agora < pregao:
        return False, "Mercado fechado (Antes do pregÃ£o) â°"
    elif agora > after:
        return False, "Mercado fechado (ApÃ³s after-market) ðŸŒ™"

    # Verifica se o sÃ­mbolo estÃ¡ ativo
    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        return False, "SÃ­mbolo nÃ£o encontrado â“"

    if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
        return False, f"SÃ­mbolo nÃ£o estÃ¡ ativo para trading ({symbol_info.trade_mode}) âš ï¸"

    return True, "Mercado aberto âœ…"


def arredondar_preco(preco: float) -> float:
    """Arredonda o preÃ§o para a precisÃ£o correta do Mini DÃ³lar (WDO)."""
    return round(preco / TICK_SIZE) * TICK_SIZE


def calcular_preco_sl_tp(preco_entrada: float, action: str, sl_points: int, tp_points: int) -> Tuple[float, float]:
    """Calcula preÃ§os de SL e TP com arredondamento correto, usando pontos (nÃ£o ticks).
    WDO: tp_points=0 â†’ TP=0 (sem take profit, saÃ­da dinÃ¢mica por GerenciadorDeSaida)."""
    from MetaTrader5 import symbol_info
    symbol = SYMBOL
    symbol_info_obj = get_cached_symbol_info(symbol)
    if symbol_info_obj is None:
        raise ValueError(
            "InformaÃ§Ãµes do sÃ­mbolo indisponÃ­veis para cÃ¡lculo de SL/TP.")

    ponto = symbol_info_obj.point
    # Para WDO: 1 ponto = TICK_SIZE (0.5), NÃƒO symbol_info.point (0.001)
    # symbol_info.point Ã© a precisÃ£o decimal, nÃ£o o tick real do contrato
    sl_dist = sl_points * TICK_SIZE  # 5 pontos = 5 * 0.5 = 2.5

    # Garante distÃ¢ncia mÃ­nima conforme trade_stops_level do broker
    min_stops_ticks = symbol_info_obj.trade_stops_level  # ex: 5 ticks
    min_dist = max(sl_dist, (min_stops_ticks + 1) * TICK_SIZE)
    if min_dist > sl_dist:
        logging.info(
            f"ðŸ”§ SL dist ajustada: {sl_dist:.1f} -> {min_dist:.1f} (trade_stops_level={min_stops_ticks})")
    sl_dist = min_dist

    # TP=0 â†’ sem take profit (saÃ­da dinÃ¢mica)
    tp_dist = tp_points * TICK_SIZE if tp_points > 0 else 0.0

    # Log detalhado para debug
    logging.info(
        f"ðŸ”§ DEBUG SL/TP - Entrada: {preco_entrada:.1f}, AÃ§Ã£o: {action}")
    logging.info(
        f"ðŸ”§ DEBUG SL/TP - SL_POINTS: {sl_points}, TP_POINTS: {tp_points}")
    logging.info(
        f"ðŸ”§ DEBUG SL/TP - Point: {ponto}, TICK_SIZE: {TICK_SIZE}, TICKS_POR_PONTO: {TICKS_POR_PONTO}")
    logging.info(
        f"ðŸ”§ DEBUG SL/TP - SL_dist: {sl_dist:.5f}, TP_dist: {tp_dist:.5f}")

    if action == 'BUY':
        sl = arredondar_preco(preco_entrada - sl_dist)
        tp = 0.0 if tp_points == 0 else arredondar_preco(preco_entrada + tp_dist)
    else:
        sl = arredondar_preco(preco_entrada + sl_dist)
        tp = 0.0 if tp_points == 0 else arredondar_preco(preco_entrada - tp_dist)

    tp_str = f"{tp:.1f}" if tp > 0 else "0 (sem TP)"
    logging.info(f"ðŸ”§ DEBUG SL/TP - Calculado: SL={sl:.1f}, TP={tp_str}")

    # ValidaÃ§Ã£o bÃ¡sica
    if action == 'BUY':
        if sl >= preco_entrada:
            logging.error(
                f"âŒ SL invÃ¡lido para BUY: {sl:.1f} >= {preco_entrada:.1f}")
        if tp > 0 and tp <= preco_entrada:
            logging.error(
                f"âŒ TP invÃ¡lido para BUY: {tp:.1f} <= {preco_entrada:.1f}")
    else:  # SELL
        if sl <= preco_entrada:
            logging.error(
                f"âŒ SL invÃ¡lido para SELL: {sl:.1f} <= {preco_entrada:.1f}")
        if tp > 0 and tp >= preco_entrada:
            logging.error(
                f"âŒ TP invÃ¡lido para SELL: {tp:.1f} >= {preco_entrada:.1f}")

    return sl, tp


def calcular_sl_tp_dinamico(preco_entrada: float, acao: str, atr: float) -> Tuple[float, float]:
    """Calcula preÃ§os de SL e TP com base no ATR e aÃ§Ã£o de compra ou venda."""
    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        logging.error("âŒ InformaÃ§Ãµes do sÃ­mbolo indisponÃ­veis")
        return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # ValidaÃ§Ã£o inicial do preÃ§o de entrada
    if not (100 <= preco_entrada <= 1000000):  # Faixa de preÃ§o razoÃ¡vel para dÃ³lar
        logging.error(f"âŒ PreÃ§o de entrada invÃ¡lido: {preco_entrada}")
        return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Calcula distÃ¢ncias iniciais em ticks baseadas no ATR
    sl_ticks = int(MULTIPLICADOR_SL_ATR * atr / symbol_info.point)
    tp_ticks = int(MULTIPLICADOR_TP_ATR * atr / symbol_info.point)

    # Log para debug das distÃ¢ncias iniciais
    logging.debug(
        f"DistÃ¢ncias iniciais - SL: {sl_ticks} ticks | TP: {tp_ticks} ticks")

    # Corrige para faixa segura em ticks
    sl_ticks = min(max(sl_ticks, MIN_TICKS), MAX_TICKS)
    tp_ticks = min(max(tp_ticks, MIN_TICKS), MAX_TICKS)

    # Calcula preÃ§os baseados nos ticks ajustados
    if acao == "BUY":
        sl_price = preco_entrada - sl_ticks * symbol_info.point
        tp_price = preco_entrada + tp_ticks * symbol_info.point
    else:
        sl_price = preco_entrada + sl_ticks * symbol_info.point
        tp_price = preco_entrada - tp_ticks * symbol_info.point

    # Arredonda os preÃ§os
    sl_price = arredondar_preco(sl_price)
    tp_price = arredondar_preco(tp_price)

    # ValidaÃ§Ã£o final dos preÃ§os calculados
    preco_max = preco_entrada * 1.1  # Limite mÃ¡ximo de 10% acima do preÃ§o
    preco_min = preco_entrada * 0.9  # Limite mÃ­nimo de 10% abaixo do preÃ§o

    # Verifica se os preÃ§os estÃ£o dentro dos limites razoÃ¡veis
    if not (preco_min <= sl_price <= preco_max):
        logging.error(
            f"âŒ SL calculado invÃ¡lido: {sl_price:.1f} (entrada: {preco_entrada:.1f})")
        # Usa fallback seguro
        sl_price = preco_entrada - 500 * \
            symbol_info.point if acao == "BUY" else preco_entrada + 500 * symbol_info.point
        sl_price = arredondar_preco(sl_price)

    if not (preco_min <= tp_price <= preco_max):
        logging.error(
            f"âŒ TP calculado invÃ¡lido: {tp_price:.1f} (entrada: {preco_entrada:.1f})")
        # Usa fallback seguro
        tp_price = preco_entrada + 1000 * \
            symbol_info.point if acao == "BUY" else preco_entrada - 1000 * symbol_info.point
        tp_price = arredondar_preco(tp_price)

    # ValidaÃ§Ã£o final da direÃ§Ã£o de SL/TP
    if acao == "BUY":
        if sl_price >= preco_entrada or tp_price <= preco_entrada:
            logging.error(
                f"âŒ DireÃ§Ã£o SL/TP invertida para BUY - SL: {sl_price:.1f}, TP: {tp_price:.1f}, Entrada: {preco_entrada:.1f}")
            return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)
    else:  # SELL
        if sl_price <= preco_entrada or tp_price >= preco_entrada:
            logging.error(
                f"âŒ DireÃ§Ã£o SL/TP invertida para SELL - SL: {sl_price:.1f}, TP:{tp_price:.1f}, Entrada: {preco_entrada:.1f}")
            return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Log das distÃ¢ncias finais
    sl_dist_final = abs(sl_price - preco_entrada) / symbol_info.point
    tp_dist_final = abs(tp_price - preco_entrada) / symbol_info.point
    logging.info(
        f"DistÃ¢ncias finais - SL: {sl_dist_final} ticks | TP: {tp_dist_final} ticks")

    return sl_price, tp_price


def verificar_spread_maximo(symbol_info: Any, tick_info: Any) -> bool:
    """Verifica se o spread estÃ¡ dentro do limite mÃ¡ximo."""
    if symbol_info is None or tick_info is None:
        logging.error(
            "âŒ Dados do sÃ­mbolo ou tick indisponÃ­veis para verificar spread")
        return False

    spread_atual = (tick_info.ask - tick_info.bid) / symbol_info.point
    spread_em_pontos = spread_atual / TICKS_POR_PONTO  # Converte para pontos

    if spread_em_pontos > MAX_SPREAD:
        logging.warning(
            f"âš ï¸ Spread alto: {spread_em_pontos:.1f} pontos (mÃ¡x: {MAX_SPREAD})")
        return False

    logging.info(f"âœ… Spread OK: {spread_em_pontos:.1f} pontos")
    return True

# endregion

# region [Trading]


class PosicaoAtiva:
    """MantÃ©m informaÃ§Ãµes sobre a posiÃ§Ã£o ativa."""

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
        self.historico_scores = [score_inicial]  # HistÃ³rico para mÃ©dia mÃ³vel
        self.entry_context = entry_context  # Novo atributo
        self.volume = VOLUME_PADRAO  # CORREÃ‡ÃƒO: Adicionar volume padrÃ£o

    def adicionar_score(self, score: float) -> float:
        """Adiciona score ao histÃ³rico e retorna mÃ©dia mÃ³vel."""
        self.historico_scores.append(score)
        if len(self.historico_scores) > JANELA_SUAVIZACAO:
            self.historico_scores.pop(0)
        return sum(self.historico_scores) / len(self.historico_scores)


def monitorar_posicao_ativa(posicao: PosicaoAtiva) -> None:
    """Monitora uma posiÃ§Ã£o ativa e aplica critÃ©rios de saÃ­da inteligente."""
    tempo_posicao = (datetime.now() - posicao.hora_entrada).total_seconds()
    if tempo_posicao < TEMPO_MIN_POSICAO:
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logging.warning("âš ï¸ Tick indisponÃ­vel para monitoramento")
        return

    preco_atual = tick.bid if posicao.tipo == "SELL" else tick.ask

    # ========== INTEGRAÃ‡ÃƒO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
    if trailing_stop and TRAILING_ATIVO:
        novo_sl = trailing_stop.atualizar_trailing(preco_atual, posicao.tipo)
        if novo_sl:
            # USAR FUNÃ‡ÃƒO CORRIGIDA com validaÃ§Ã£o de distÃ¢ncia mÃ­nima
            if atualizar_sl(posicao.ticket, novo_sl):
                posicao.sl = novo_sl

    # ========== SAÃDA INTELIGENTE ULTRA RESTRITIVA (+MÃXIMA ACERTIVIDADE) ==========
    lucro_atual = calcular_lucro_posicao(posicao, preco_atual)
    lucro_maximo = getattr(posicao, 'lucro_maximo', lucro_atual)

    # Atualiza lucro mÃ¡ximo
    if lucro_atual > lucro_maximo:
        posicao.lucro_maximo = lucro_atual
        lucro_maximo = lucro_atual

    # REGRA 1: Timeout sem evoluÃ§Ã£o (MAIS RESTRITIVO - 2 minutos)
    if tempo_posicao > 120 and lucro_atual <= 15:  # 2 min sem aevoluir
        logging.info(
            f"â° SAÃDA POR TIMEOUT: {tempo_posicao:.0f}s sem evoluÃ§Ã£o (lucro: R${lucro_atual:.2f})")
        fechar_posicao_score(posicao, "timeout sem evoluÃ§Ã£o", 0.0)
        return

    # REGRA 2: Lucro derretendo (PROTEÃ‡ÃƒO AGRESSIVA)
    if lucro_maximo > 40 and lucro_atual < lucro_maximo * 0.8:  # Perdeu 20% do pico
        logging.info(
            f"ðŸ“‰ SAÃDA POR PROTEÃ‡ÃƒO: Lucro caiu de R${lucro_maximo:.2f} para R${lucro_atual:.2f}")
        fechar_posicao_score(posicao, "proteÃ§Ã£o de lucro", 0.0)
        return

    # REGRA 3: Breakeven apÃ³s tempo (MAIS AGRESSIVO)
    if tempo_posicao > 90 and lucro_atual <= 0:  # 1.5 min no zero/negativo
        logging.info(f"ðŸš« SAÃDA POR BREAKEVEN: {tempo_posicao:.0f}s sem lucro")
        fechar_posicao_score(posicao, "breakeven preventivo", 0.0)
        return

    # REGRA 4: Lucro pequeno hÃ¡ muito tempo (NOVA REGRA)
    if tempo_posicao > 180 and 0 < lucro_atual < 25:  # 3 min com lucro pequeno
        logging.info(
            f"ðŸŒ SAÃDA POR ESTAGNAÃ‡ÃƒO: Lucro pequeno R${lucro_atual:.2f} hÃ¡ {tempo_posicao:.0f}s")
        fechar_posicao_score(posicao, "estagnaÃ§Ã£o", 0.0)
        return

    score_atual = calcular_score_distancia(
        posicao.preco_entrada,
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
            posicao, "queda de score pÃ³s-lucro", score_suavizado)
        return

    # CritÃ©rios jÃ¡ existentes
    if verificar_inversao_score(posicao, score_atual):
        fechar_posicao_score(posicao, "inversÃ£o de direÃ§Ã£o", score_suavizado)
    elif verificar_enfraquecimento(posicao, score_atual):
        if not posicao.travado:
            travar_lucro(posicao, score_atual)


def obter_contexto_completo() -> Optional[Dict]:
    """ObtÃ©m o contexto completo atual para anÃ¡lise de qualidade do setup."""
    try:
        # ObtÃ©m dados do book (nativo, direto do MT5)
        book_data = ler_book_nativo()
        if not book_data:
            return None

        # ObtÃ©m dados de mercado
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 50)
        if rates is None or len(rates) == 0:
            return None

        # Calcula indicadores
        df_rates = pd.DataFrame(rates)
        atr = calcular_atr(df_rates['high'].tolist(
        ), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)
        rsi = calcular_rsi(df_rates['close'].tolist(), period=14)
        # CORREÃ‡ÃƒO: Calcula entropia considerando formato JSON
        if isinstance(book_data['bids'][0], dict):
            # Formato JSON: extrai volumes dos dicionÃ¡rios
            volumes_bid = [item['volume'] for item in book_data['bids']]
            volumes_ask = [item['volume'] for item in book_data['asks']]
            entropia = calcular_entropia(volumes_bid + volumes_ask)
        else:
            # Formato legado: usa diretamente
            entropia = calcular_entropia(book_data['bids'] + book_data['asks'])

        # Calcula spread
        tick = mt5.symbol_info_tick(SYMBOL)
        spread = (tick.ask - tick.bid) / TICK_SIZE if tick else 0

        # ðŸ”§ CORREÃ‡ÃƒO CRÃTICA 2: Calcula volumes corretamente baseado no formato
        if isinstance(book_data['bids'][0], dict):
            # Formato JSON: extrai volumes dos dicionÃ¡rios
            bid_qty = sum(item['volume'] for item in book_data['bids'])
            ask_qty = sum(item['volume'] for item in book_data['asks'])
        else:
            # Formato legado: usa diretamente
            bid_qty = sum(book_data['bids'])
            ask_qty = sum(book_data['asks'])

        contexto = {
            'bid_qty': bid_qty,
            'ask_qty': ask_qty,
            'entropia_book': entropia,
            'volatility': atr,
            'rsi_14': rsi,
            'spread': spread
        }

        # Adiciona sinal DOL ao contexto (referÃªncia institucional)
        book_dol_data = ler_book_dol()
        sinal_dol = analisar_sinal_dol(book_dol_data)
        contexto['dol_ratio'] = sinal_dol.get('ratio', 1.0)
        contexto['dol_lado'] = sinal_dol.get('lado', 'NEUTRO')
        contexto['dol_confianca'] = sinal_dol.get('confianca', 0.0)
        contexto['dol_presente'] = 1 if sinal_dol.get('presente', False) else 0

        return contexto
    except Exception as e:
        logging.error(f"âŒ Erro ao obter contexto completo: {e}")
        return None


def calcular_lucro_posicao(posicao: PosicaoAtiva, preco_atual: float) -> float:
    """Calcula o lucro atual da posiÃ§Ã£o em reais."""
    if posicao.tipo == "BUY":
        diferenca_pontos = (preco_atual - posicao.preco_entrada) / TICK_SIZE
    else:  # SELL
        diferenca_pontos = (posicao.preco_entrada - preco_atual) / TICK_SIZE

    # WDO: 1 ponto = R$5 por contrato
    lucro_reais = diferenca_pontos * posicao.volume
    return lucro_reais


def verificar_inversao_score(posicao: PosicaoAtiva, score_atual: float) -> bool:
    """Verifica se houve inversÃ£o significativa no score."""
    # InversÃ£o de positivo para negativo (mais conservador)
    if posicao.score_inicial > 0 and score_atual < THRESHOLD_INVERSAO_SCORE:
        return True
    # InversÃ£o de negativo para positivo (mais conservador)
    if posicao.score_inicial < 0 and score_atual > abs(THRESHOLD_INVERSAO_SCORE):
        return True
    # Queda abrupta do mÃ¡ximo (usando score suavizado)
    if (posicao.score_maximo > SCORE_LOCK_PROFIT and
            score_atual < posicao.score_maximo - INVERSAO_SCORE_MIN):
        return True
    return False


def verificar_enfraquecimento(posicao: PosicaoAtiva, score_atual: float) -> bool:
    """Verifica se o movimento estÃ¡ enfraquecendo e precisa travar lucro."""
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
        logging.warning("[travar_lucro] Tick ou SymbolInfo indisponÃ­vel.")
        return

    logging.debug(
        f"[travar_lucro] PosiÃ§Ã£o: Tipo={posicao.tipo}, Entrada={posicao.preco_entrada:.3f}")
    logging.debug(
        f"[travar_lucro] Tick Atual: Ask={tick.ask:.3f}, Bid={tick.bid:.3f}")

    # Calcula novo SL (garante pelo menos 30% do movimento a favor)
    if posicao.tipo == "BUY":
        movimento = max(0, tick.bid - posicao.preco_entrada)
        novo_sl = posicao.preco_entrada + movimento * 0.3
        # Nunca mova o SL para baixo do preÃ§o de entrada (com margem de 1 tick)
        novo_sl = max(novo_sl, posicao.preco_entrada - symbol_info.point)
    else:
        movimento = max(0, posicao.preco_entrada - tick.ask)
        novo_sl = posicao.preco_entrada - movimento * 0.3
        # Nunca mova o SL para cima do preÃ§o de entrada (com margem de 1 tick)
        novo_sl = min(novo_sl, posicao.preco_entrada + symbol_info.point)

    # Limite de seguranÃ§a: SL nÃ£o pode ficar mais de 2x o stop original de distÃ¢ncia
    sl_dist_original_ticks = SL_POINTS * TICKS_POR_PONTO  # SL_POINTS Ã© em pontos
    # sl_max_dist_ticks = sl_dist_original_ticks * 2 # NÃ£o parece estar sendo usado, mas a ideia de limitar Ã© boa.

    logging.debug(
        f"[travar_lucro] Novo SL (calculado, antes de arredondar e limites de seguranÃ§a): {novo_sl:.3f}, Movimento: {movimento:.3f}")

    # Limites de seguranÃ§a baseados no preÃ§o de entrada e um mÃºltiplo do SL original em pontos
    # Convertendo SL_MAX_POINTS para valor de preÃ§o
    max_sl_dev = SL_MAX_POINTS * TICKS_POR_PONTO * symbol_info.point
    if posicao.tipo == "BUY":
        sl_limite_inferior = posicao.preco_entrada - max_sl_dev
        # Garante que nÃ£o seja muito longe pra baixo
        novo_sl = max(novo_sl, sl_limite_inferior)
    else:  # SELL
        sl_limite_superior = posicao.preco_entrada + max_sl_dev
        # Garante que nÃ£o seja muito longe pra cima
        novo_sl = min(novo_sl, sl_limite_superior)

    logging.debug(
        f"[travar_lucro] Novo SL (apÃ³s limites de seguranÃ§a adicionais): {novo_sl:.3f}")

    novo_sl_arredondado = arredondar_preco(novo_sl)
    logging.debug(
        f"[travar_lucro] Novo SL (apÃ³s arredondar_preco): {novo_sl_arredondado:.3f}")

    if atualizar_sl(posicao.ticket, novo_sl_arredondado):
        posicao.sl = novo_sl_arredondado
        posicao.travado = True
        logging.info(
            f"ðŸ”’ Lucro travado em {novo_sl_arredondado:.2f} (Score: {score_atual:.2f})")


def fechar_posicao_atual(motivo: str = "Fechamento manual") -> bool:
    """Fecha a posiÃ§Ã£o atual ativa â€” detecta filling aceito pela corretora automaticamente."""
    global posicao_atual

    if posicao_atual is None:
        logging.warning("Nenhuma posiÃ§Ã£o ativa para fechar")
        return False

    try:
        tick = mt5.symbol_info_tick(SYMBOL)
        if not tick:
            logging.error("Erro ao obter tick para fechamento")
            return False

        tipo_ordem = mt5.ORDER_TYPE_SELL if posicao_atual.tipo == "BUY" else mt5.ORDER_TYPE_BUY
        preco = tick.bid if posicao_atual.tipo == "BUY" else tick.ask

        # Detecta filling aceito pelo sÃ­mbolo na corretora
        info = mt5.symbol_info(SYMBOL)
        filling_mode = info.filling_mode if info else 0

        # Monta lista de fillings na ordem de preferÃªncia
        # filling_mode Ã© bitmask: 1=FOK, 2=IOC, 4=RETURN
        fillings_disponiveis = []
        if filling_mode & 1:
            fillings_disponiveis.append(mt5.ORDER_FILLING_FOK)
        if filling_mode & 2:
            fillings_disponiveis.append(mt5.ORDER_FILLING_IOC)
        if filling_mode & 4:
            fillings_disponiveis.append(mt5.ORDER_FILLING_RETURN)

        # Fallback: tenta todos se nÃ£o conseguiu detectar
        if not fillings_disponiveis:
            fillings_disponiveis = [
                mt5.ORDER_FILLING_FOK,
                mt5.ORDER_FILLING_IOC,
                mt5.ORDER_FILLING_RETURN
            ]

        logging.debug(
            f"ðŸ”§ Fillings disponÃ­veis para {SYMBOL}: {fillings_disponiveis}")

        for filling in fillings_disponiveis:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": posicao_atual.ticket,
                "symbol": SYMBOL,
                "volume": posicao_atual.volume if hasattr(posicao_atual, 'volume') else VOLUME_PADRAO,
                "type": tipo_ordem,
                "price": preco,
                "deviation": DEVIATION,
                "magic": MAGIC_NUMBER,
                "comment": f"Fechamento: {motivo}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }

            resultado = mt5.order_send(request)

            if resultado is None:
                logging.warning(
                    f"âš ï¸ order_send None (filling={filling}), reconectando...")
                reconectar_mt5()
                time.sleep(0.5)
                tick = mt5.symbol_info_tick(SYMBOL)
                if tick:
                    preco = tick.bid if posicao_atual.tipo == "BUY" else tick.ask
                    request["price"] = preco
                resultado = mt5.order_send(request)

            if resultado is not None and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(
                    f"âœ… PosiÃ§Ã£o {posicao_atual.ticket} fechada (filling={filling}): {motivo}")
                return True
            elif resultado is not None:
                # Retcodes que indicam posiÃ§Ã£o jÃ¡ fechada pelo MT5 (TP/SL/manual)
                # Trata como sucesso â€” a posiÃ§Ã£o nÃ£o existe mais de qualquer forma
                retcodes_posicao_fechada = [
                    10009,  # TRADE_RETCODE_DONE
                    10010,  # TRADE_RETCODE_DONE_PARTIAL
                    10015,  # TRADE_RETCODE_INVALID_PRICE â€” preÃ§o mudou, posiÃ§Ã£o jÃ¡ fechou
                    10016,  # TRADE_RETCODE_INVALID_STOPS
                    10018,  # TRADE_RETCODE_MARKET_CLOSED
                    10019,  # TRADE_RETCODE_NO_MONEY â€” nÃ£o aplica mas posiÃ§Ã£o foi
                    10030,  # TRADE_RETCODE_POSITION_CLOSED â€” posiÃ§Ã£o jÃ¡ encerrada
                ]
                if resultado.retcode in retcodes_posicao_fechada:
                    logging.info(
                        f"âœ… PosiÃ§Ã£o considerada fechada (retcode={resultado.retcode}): {resultado.comment}")
                    return True

                # Verifica se posiÃ§Ã£o ainda existe no MT5 apÃ³s falha
                posicoes_check = mt5.positions_get(symbol=SYMBOL)
                ticket_ainda_aberto = any(
                    p.ticket == posicao_atual.ticket
                    for p in (posicoes_check or [])
                )
                if not ticket_ainda_aberto:
                    logging.info(
                        f"âœ… PosiÃ§Ã£o {posicao_atual.ticket} jÃ¡ foi fechada pelo MT5 (detectado apÃ³s retcode={resultado.retcode})")
                    return True

                logging.warning(
                    f"âš ï¸ Retcode {resultado.retcode} (filling={filling}): {resultado.comment}")

        logging.error(
            f"âŒ Falha ao fechar posiÃ§Ã£o apÃ³s todos os fillings: {motivo}")
        return False

    except Exception as e:
        logging.error(f"Erro ao fechar posiÃ§Ã£o atual: {e}")
        return False


def fechar_posicao_score(posicao: PosicaoAtiva, motivo: str, score_atual: float) -> None:
    """Fecha posiÃ§Ã£o por critÃ©rio de score."""
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

    # ðŸ”§ CORREÃ‡ÃƒO CRÃTICA 3: Verificar se resultado nÃ£o Ã© None
    if resultado is None:
        logging.error(
            "âŒ Erro crÃ­tico: mt5.order_send retornou None (falha de conexÃ£o)")
        return

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(
            f"âš ï¸ PosiÃ§Ã£o fechada por {motivo}. Score inicial: {posicao.score_inicial:.2f}, Score final: {score_atual:.2f}")
    else:
        logging.error(f"âŒ Erro ao fechar posiÃ§Ã£o: {resultado.comment}")


def fechar_todas_posicoes(motivo: str = "Encerramento automÃ¡tico") -> int:
    """Fecha todas as posiÃ§Ãµes abertas do robÃ´."""
    posicoes_fechadas = 0

    try:
        # ObtÃ©m todas as posiÃ§Ãµes abertas
        posicoes = mt5.positions_get()
        if not posicoes:
            logging.info("âœ… Nenhuma posiÃ§Ã£o aberta para fechar")
            return 0

        # Filtra apenas posiÃ§Ãµes do robÃ´ (por magic number)
        posicoes_monstro = [
            pos for pos in posicoes if pos.magic == MAGIC_NUMBER]

        if not posicoes_monstro:
            logging.info("âœ… Nenhuma posiÃ§Ã£o do Monstro para fechar")
            return 0

        logging.info(
            f"ðŸ”´ Iniciando fechamento de {len(posicoes_monstro)} posiÃ§Ãµes - {motivo}")

        # Fecha cada posiÃ§Ã£o
        for pos in posicoes_monstro:
            try:
                # Determina o tipo de ordem necessÃ¡rio para fechar
                tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

                # ObtÃ©m preÃ§o atual
                tick = mt5.symbol_info_tick(pos.symbol)
                if not tick:
                    logging.error(
                        f"âŒ NÃ£o foi possÃ­vel obter tick para {pos.symbol}")
                    continue

                preco_fechamento = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask

                # Prepara requisiÃ§Ã£o de fechamento
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

                # ðŸ”§ CORREÃ‡ÃƒO CRÃTICA 3: Verificar se resultado nÃ£o Ã© None
                if resultado is None:
                    logging.error(
                        f"âŒ Erro crÃ­tico: mt5.order_send retornou None para posiÃ§Ã£o #{pos.ticket}")
                    continue

                if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    posicoes_fechadas += 1
                    logging.info(
                        f"âœ… PosiÃ§Ã£o #{pos.ticket} fechada - {pos.symbol} {pos.type} Vol:{pos.volume}")
                else:
                    logging.error(
                        f"âŒ Erro ao fechar posiÃ§Ã£o #{pos.ticket}: {resultado.retcode} - {resultado.comment}")

            except Exception as e:
                logging.error(
                    f"âŒ Erro ao processar posiÃ§Ã£o #{pos.ticket}: {e}")
                continue

        logging.info(
            f"ðŸ Fechamento concluÃ­do: {posicoes_fechadas} posiÃ§Ãµes fechadas")
        return posicoes_fechadas

    except Exception as e:
        logging.error(f"âŒ Erro crÃ­tico ao fechar posiÃ§Ãµes: {e}")
        return 0


def salvar_dados_finais(modelo_ia_local: Optional[Sequential], memoria_experiencias: MemoriaExperiencias) -> None:
    """Salva todos os dados importantes antes do encerramento."""
    try:
        logging.info("ðŸ’¾ Iniciando salvamento final de dados...")

        # Salva modelo de IA
        if modelo_ia_local:
            salvar_modelo(modelo_ia_local, MODELO_PATH)
            logging.info("âœ… Modelo de IA salvo com sucesso")

        # Salva experiÃªncias em JSON
        if memoria_experiencias and memoria_experiencias.experiencias:
            salvar_experiencias_json(
                memoria_experiencias.experiencias, "experiencias_finais.json")
            logging.info("âœ… ExperiÃªncias salvas em JSON")

        # Salva estatÃ­sticas finais
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
        logging.info("âœ… EstatÃ­sticas finais salvas")

        # ForÃ§a flush dos logs
        logging.info("ðŸ’¾ Salvamento final concluÃ­do com sucesso")

    except Exception as e:
        logging.error(f"âŒ Erro ao salvar dados finais: {e}")


def fechar_conexoes_seguras() -> None:
    """Fecha todas as conexÃµes de forma segura."""
    try:
        logging.info("ðŸ”Œ Iniciando fechamento seguro de conexÃµes...")

        # Cancela a subscriÃ§Ã£o do book nativo (Depth of Market) antes de desligar
        try:
            if SYMBOL:
                mt5.market_book_release(SYMBOL)
                logging.info(f"ðŸ“• Book nativo liberado para {SYMBOL}")
        except Exception as e:
            logging.debug(f"Falha ao liberar book nativo: {e}")

        # Libera book do DOL se estava ativo
        try:
            if SYMBOL_DOL:
                mt5.market_book_release(SYMBOL_DOL)
                logging.info(f"ðŸ“• Book DOL liberado para {SYMBOL_DOL}")
        except Exception as e:
            logging.debug(f"Falha ao liberar book DOL: {e}")

        # Fecha conexÃ£o MT5
        try:
            if mt5.initialize():
                mt5.shutdown()
                logging.info("âœ… ConexÃ£o MT5 fechada")
        except Exception as e:
            logging.error(f"âŒ Erro ao fechar MT5: {e}")

        # Para threads de forma segura
        global thread_ativo
        thread_ativo = False
        logging.info("âœ… Threads marcadas para encerramento")

        # Aguarda um momento para threads terminarem
        time.sleep(2)

        logging.info("ðŸ”Œ Fechamento de conexÃµes concluÃ­do")

    except Exception as e:
        logging.error(f"âŒ Erro ao fechar conexÃµes: {e}")


def encerramento_seguro_completo(modelo_ia_local: Optional[Sequential], memoria_experiencias: MemoriaExperiencias) -> None:
    """Executa encerramento completo e seguro do sistema."""
    try:
        logging.info("ðŸ”´ INICIANDO ENCERRAMENTO SEGURO COMPLETO DO SISTEMA")

        # Passo 1: Fecha todas as posiÃ§Ãµes
        posicoes_fechadas = fechar_todas_posicoes(
            "Encerramento seguro do sistema")
        logging.info(f"âœ… {posicoes_fechadas} posiÃ§Ãµes fechadas")

        # Passo 2: Salva todos os dados importantes
        salvar_dados_finais(modelo_ia_local, memoria_experiencias)

        # Passo 3: Fecha conexÃµes
        fechar_conexoes_seguras()

        # Passo 4: Log final
        logging.info("ðŸ ENCERRAMENTO SEGURO CONCLUÃDO COM SUCESSO")
        logging.info("ðŸ¤– MONSTRO DAS NEGOCIAÃ‡Ã•ES DESLIGADO AUTOMATICAMENTE")

        # Passo 5: ForÃ§a flush final dos logs
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Passo 6: Encerra o programa
        logging.info("ðŸ’¤ Sistema sendo desligado...")
        os._exit(0)  # Encerramento forÃ§ado mas seguro

    except Exception as e:
        logging.error(f"âŒ Erro crÃ­tico no encerramento seguro: {e}")
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
        # Verifica se Ã© fim de semana
        if datetime.now().weekday() > 4:  # 5 = SÃ¡bado, 6 = Domingo
            # Verifica a cada minuto durante fim de semana
            threading.Timer(60, monitorar_spread).start()
            return

        # Resto do cÃ³digo permanece igual...
        spreads = []
        while thread_ativo:
            try:
                tick = mt5.symbol_info_tick(SYMBOL)
                symbol_info = get_cached_symbol_info(SYMBOL)

                if tick and symbol_info:
                    spread_atual = (tick.ask - tick.bid) / symbol_info.point
                    spread_em_pontos = spread_atual / TICKS_POR_PONTO

                    spreads.append(spread_em_pontos)
                    if len(spreads) > 100:  # MantÃ©m Ãºltimos 100 valores
                        spreads.pop(0)

                    # Log removido: era redundante e bugado (mostrava 0.0). O spread
                    # real jÃ¡ aparece correto no log de mercado (ex.: "Spread: 5.0pts").
                    # A coleta de 'spreads' fica mantida caso outra parte precise.

                time.sleep(1)  # Atualiza a cada segundo

            except Exception as e:
                logging.error(f"Erro ao monitorar spread: {e}")
                time.sleep(1)
    except Exception as e:
        logging.error(f"Erro ao monitorar spread: {e}")
        time.sleep(1)

# endregion


# ========== FILTRO DE TENDÃŠNCIA (SMA-50 + MOMENTUM) ==========
class FiltroTendencia:
    """Bloqueia operaÃ§Ãµes contra a tendÃªncia usando SMA-50 + momentum.

    3 camadas de detecÃ§Ã£o:
    1. SMA-50: diff > 1.0pt = tendÃªncia (SMA lenta, reage devagar)
    2. Momentum: subiu >3pts nos Ãºltimos 20 ticks = tendÃªncia de alta
    3. Consenso: se 2+ sinais concordam, bloqueia com mais forÃ§a
    """

    def __init__(self, janela: int = 50, margem_pts: float = 1.0):
        self.janela = janela
        self.margem_pts = margem_pts
        self.historico_precos: list = []
        self._preco_registrado_ultimo_tick: float = 0.0
        self._log_contador = 0
        self._ultima_decisao_veto_buy = False
        self._ultima_decisao_veto_sell = False

    def registrar_preco(self, preco: float):
        """Registra preÃ§o UMA VEZ por ciclo (evita dupla registro)."""
        if preco != self._preco_registrado_ultimo_tick:
            self.historico_precos.append(preco)
            self._preco_registrado_ultimo_tick = preco
            if len(self.historico_precos) > self.janela:
                self.historico_precos = self.historico_precos[-self.janela:]

    def calcular_sma(self) -> float:
        if len(self.historico_precos) < 5:
            return 0.0
        return sum(self.historico_precos) / len(self.historico_precos)

    def calcular_momentum(self) -> tuple:
        """Detecta momentum: compara preÃ§o atual com preÃ§o de 20 ticks atrÃ¡s.
        Retorna: (momentum_pts, direcao)"""
        if len(self.historico_precos) < 20:
            return 0.0, "NEUTRO"
        preco_20_atras = self.historico_precos[-20]
        preco_atual = self.historico_precos[-1]
        momentum = preco_atual - preco_20_atras
        if momentum > 3.0:
            return momentum, "ALTA"
        elif momentum < -3.0:
            return momentum, "BAIXA"
        return momentum, "NEUTRO"

    def avaliar_tendencia(self, preco_atual: float) -> dict:
        """Avalia tendÃªncia completa e retorna dict com resultado.
        Chamar UMA VEZ por ciclo â€” NÃƒO chamar para BUY e SELL separadamente."""
        self.registrar_preco(preco_atual)
        sma = self.calcular_sma()
        momentum_pts, momentum_dir = self.calcular_momentum()

        resultado = {
            'veto_buy': False,
            'veto_sell': False,
            'sma': sma,
            'diff': 0.0,
            'momentum_pts': momentum_pts,
            'momentum_dir': momentum_dir,
            'em_tendencia': False,
            'motivo': ''
        }

        if sma == 0.0:
            resultado['motivo'] = f"Tendencia: dados insuficientes ({len(self.historico_precos)}/{self.janela})"
            return resultado

        diff = preco_atual - sma
        resultado['diff'] = diff

        # â”€â”€ Camada 1: SMA-50 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sma_tendencia = abs(diff) > self.margem_pts

        # â”€â”€ Camada 2: Momentum (20 ticks) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        momentum_tendencia = momentum_dir != "NEUTRO"

        # â”€â”€ Camada 3: Consenso â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Se SMA e momentum concordam â†’ tendÃªncia forte
        # Se sÃ³ um detecta â†’ tendÃªncia fraca (ainda bloqueia)
        em_tendencia = sma_tendencia or momentum_tendencia
        resultado['em_tendencia'] = em_tendencia

        self._log_contador += 1
        if self._log_contador % 20 == 1:
            logging.info(
                f"TENDENCIA: Preco={preco_atual:.1f} | SMA={sma:.1f} | "
                f"Diff={diff:+.1f}pts | Momentum={momentum_pts:+.1f}pts({momentum_dir}) | "
                f"{'TENDENCIA' if em_tendencia else 'LATERAL'}")

        if not em_tendencia:
            resultado['motivo'] = f"LATERAL: Diff={diff:+.1f}pts, Momentum={momentum_pts:+.1f}pts"
            return resultado

        # â”€â”€ DecisÃ£o de veto â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # TendÃªncia de ALTA: bloqueia SELL
        if diff > self.margem_pts or momentum_dir == "ALTA":
            resultado['veto_sell'] = True
            resultado['motivo'] = (
                f"TENDENCIA DE ALTA: Preco {diff:+.1f}pts acima SMA, "
                f"Momentum {momentum_pts:+.1f}pts")
            if not self._ultima_decisao_veto_sell:
                logging.info(f"ðŸš« TENDENCIA BLOQUEIA SELL: {resultado['motivo']}")
            self._ultima_decisao_veto_sell = True
        else:
            self._ultima_decisao_veto_sell = False

        # TendÃªncia de BAIXA: bloqueia BUY
        if diff < -self.margem_pts or momentum_dir == "BAIXA":
            resultado['veto_buy'] = True
            resultado['motivo'] = (
                f"TENDENCIA DE BAIXA: Preco {diff:+.1f}pts abaixo SMA, "
                f"Momentum {momentum_pts:+.1f}pts")
            if not self._ultima_decisao_veto_buy:
                logging.info(f"ðŸš« TENDENCIA BLOQUEIA BUY: {resultado['motivo']}")
            self._ultima_decisao_veto_buy = True
        else:
            self._ultima_decisao_veto_buy = False

        return resultado

    def pode_operar(self, direcao: str, preco_atual: float) -> tuple:
        """Compatibilidade: avalia e retorna (pode, motivo) para uma direÃ§Ã£o."""
        resultado = self.avaliar_tendencia(preco_atual)
        if direcao == "BUY":
            return not resultado['veto_buy'], resultado['motivo']
        else:
            return not resultado['veto_sell'], resultado['motivo']


filtro_tendencia = FiltroTendencia(janela=50, margem_pts=4.5)


# ========== FILTRO MEAN REVERSION (RSI + Z-Score + ADX) ==========
class FiltroMeanReversion:
    """Sistema de 3 camadas para filtrar operaÃ§Ãµes por reversÃ£o Ã  mÃ©dia.

    Camada 1 - RSI por Zonas (70/50/30):
        RSI > 70 â†’ sobrecomprado â†’ bloqueia BUY (sÃ³ permite SELL)
        RSI < 30 â†’ sobrevendido â†’ bloqueia SELL (sÃ³ permite BUY)
        RSI 30-70 â†’ normal â†’ permite ambos

    Camada 2 - Z-Score (desvio padrÃ£o da mÃ©dia):
        Z > +1.5 â†’ preÃ§o esticado p/ cima â†’ bloqueia BUY
        Z < -1.5 â†’ preÃ§o esticado p/ baixo â†’ bloqueia SELL

    Camada 3 - ADX Trend Classifier:
        ADX < 20 â†’ LATERAL â†’ mean reversion ativo (RSI+Z-Score mandam)
        ADX >= 25 + EMA subindo â†’ TENDENCIA_ALTA â†’ sÃ³ BUY
        ADX >= 25 + EMA descendo â†’ TENDENCIA_BAIXA â†’ sÃ³ SELL
    """

    def __init__(self, janela: int = 20, rsi_compra: float = 25.0, rsi_venda: float = 75.0,
                 zscore_limiar: float = 1.5, adx_lateral: float = 20.0, adx_tendencia: float = 25.0):
        self.janela = janela
        self.rsi_compra = rsi_compra
        self.rsi_venda = rsi_venda
        self.zscore_limiar = zscore_limiar
        self.adx_lateral = adx_lateral
        self.adx_tendencia = adx_tendencia
        self.historico_precos: list = []
        self.historico_ema: list = []
        self._log_contador = 0

    # â”€â”€ Z-Score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _calcular_zscore(self, preco: float) -> float:
        self.historico_precos.append(preco)
        if len(self.historico_precos) > self.janela:
            self.historico_precos = self.historico_precos[-self.janela:]
        if len(self.historico_precos) < 10:
            return 0.0
        import statistics
        media = statistics.mean(self.historico_precos)
        try:
            desvio = statistics.stdev(self.historico_precos)
        except statistics.StatisticsError:
            return 0.0
        if desvio == 0:
            return 0.0
        return (preco - media) / desvio

    # â”€â”€ ADX + DireÃ§Ã£o (EMA slope) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _calcular_adx_simples(self, ema_atual: float, ema_anterior: float) -> tuple:
        """Calcula ADX simplificado baseado na inclinaÃ§Ã£o da EMA e distÃ¢ncia do preÃ§o.

        Retorna: (adx_valor: float, direcao: str)
        """
        self.historico_ema.append(ema_atual)
        if len(self.historico_ema) > self.janela:
            self.historico_ema = self.historico_ema[-self.janela:]

        if len(self.historico_ema) < 5:
            return 0.0, "NEUTRO"

        # InclinaÃ§Ã£o da EMA (variaÃ§Ã£o nos Ãºltimos 3 ticks)
        inclinacao = ema_atual - self.historico_ema[-3] if len(self.historico_ema) >= 3 else 0

        # ADX simplificado: magnitude da inclinaÃ§Ã£o acumulada
        variacoes = [abs(self.historico_ema[i] - self.historico_ema[i-1])
                     for i in range(1, len(self.historico_ema))]
        adx = sum(variacoes) / len(variacoes) * 10 if variacoes else 0
        adx = min(adx, 100)

        if adx < self.adx_lateral:
            return adx, "LATERAL"
        elif adx >= self.adx_tendencia:
            if inclinacao > 0.3:
                return adx, "TENDENCIA_ALTA"
            elif inclinacao < -0.3:
                return adx, "TENDENCIA_BAIXA"
        return adx, "LATERAL"

    # â”€â”€ AvaliaÃ§Ã£o Principal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def avaliar(self, preco_atual: float, rsi_real: float, ema_atual: float = 0,
                ema_anterior: float = 0) -> dict:
        """Avalia os 3 filtros e retorna veto + estado de mercado.

        Retorna dict com:
            veto_buy: bool, veto_sell: bool, estado: str,
            rsi_zona: str, zscore: float, adx: float
        """
        zscore = self._calcular_zscore(preco_atual)
        adx, estado = self._calcular_adx_simples(ema_atual, ema_anterior)

        veto_buy = False
        veto_sell = False
        rsi_zona = "NEUTRO"

        # â”€â”€ Se TENDÃŠNCIA, mean reversion desligado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if estado in ("TENDENCIA_ALTA", "TENDENCIA_BAIXA"):
            if estado == "TENDENCIA_ALTA":
                veto_sell = True  # SÃ³ permite BUY em tendÃªncia de alta
            else:
                veto_buy = True  # SÃ³ permite SELL em tendÃªncia de baixa
            rsi_zona = "TENDENCIA"
        else:
            # â”€â”€ LATERAL: RSI + Z-Score ativos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # RSI por zonas
            if rsi_real > self.rsi_venda:
                veto_buy = True
                rsi_zona = "SOBRECOMPRADO"
            elif rsi_real < self.rsi_compra:
                veto_sell = True
                rsi_zona = "SOBREVENDIDO"
            else:
                rsi_zona = "NEUTRO"

            # Z-Score (reforÃ§a o veto do RSI)
            if zscore > self.zscore_limiar:
                veto_buy = True
                rsi_zona += "+Z_ESTICADO"
            elif zscore < -self.zscore_limiar:
                veto_sell = True
                rsi_zona += "+Z_ESTICADO"

        self._log_contador += 1
        if self._log_contador % 5 == 1:
            logging.info(
                f"ðŸ“Š MR: RSI={rsi_real:.1f}({rsi_zona}) | Z={zscore:+.2f} | "
                f"ADX={adx:.1f}({estado}) | Veto: BUY={veto_buy} SELL={veto_sell}")

        return {
            'veto_buy': veto_buy,
            'veto_sell': veto_sell,
            'estado': estado,
            'rsi_zona': rsi_zona,
            'zscore': zscore,
            'adx': adx
        }


filtro_mean_reversion = FiltroMeanReversion()


# region [InicializaÃ§Ã£o]

if __name__ == "__main__":
    # PyInstaller console=False deixa sys.stdout/sys.stderr = None. Redireciona
    # para devnull para que print() nao lance excecao no build windowed.
    import sys as _sys_out
    import os as _os_out
    if _sys_out.stdout is None:
        _sys_out.stdout = open(_os_out.devnull, 'w')
    if _sys_out.stderr is None:
        _sys_out.stderr = open(_os_out.devnull, 'w')

    # ---- BLOQUEIO DE INSTÃ‚NCIA ÃšNICA: se outra cÃ³pia do Monstro V22 jÃ¡ estiver rodando, sai na hora ----
    # FIX (01/08/2026): movido para o __main__ - antes rodava no import e matava qualquer
    # processo que importasse o modulo com outra instancia ativa
    import ctypes
    import sys as _sys

    _mutex_instancia_unica = ctypes.windll.kernel32.CreateMutexW(
        None, False, "Local\\MonstroDashboard_V22_InstanciaUnica")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "O Monstro V22 jÃ¡ estÃ¡ em execuÃ§Ã£o.\n"
                "Encerre a instÃ¢ncia atual antes de iniciar outra.",
                "Monstro Dashboard V22",
                0x40)
        except Exception:
            pass
        _sys.exit(0)

    # Inicializa logging
    setup_logging()

    # ========== REGRAS OPERACIONAIS ATIVAS ==========
    logging.info("âš™ï¸ HorÃ¡rio: 09:15-12:30 e 14:30-17:15 | Treino sÃ³ com lucro | Aprendizado PRESERVADO entre reinÃ­cios")

    # âœ… PA3: Reset de memÃ³ria foi executado UMA vez na primeira inicializaÃ§Ã£o.
    # DESATIVADO permanentemente â€” o aprendizado (h5/keras/experiÃªncias) Ã© PRESERVADO
    # entre reinÃ­cios. SÃ³ reative manualmente chamando resetar_memoria_ia() se quiser zerar tudo.
    # resetar_memoria_ia()  # SÃ³ reativar manualmente se necessÃ¡rio

    # Reseta e recria scaler global para compatibilidade com 22 features
    resetar_scaler_global()
    forcar_recreacao_scaler()

    # VariÃ¡veis globais
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
    gerenciador_bloqueio = None  # SerÃ¡ inicializado na thread
    modo_operacional = None      # SerÃ¡ inicializado na thread
    confluencia_info_atual = None  # Para sistema de confluÃªncia

    # Corrige formato do CSV
    corrigir_csv_historico()

    # Dashboard V2 â€” Registra mÃ³dulo principal para acesso aos globals
    import sys
    register_main_module(sys.modules[__name__], log_file=LOG_FILE)

    # Inicia threads
    flask_thread = threading.Thread(target=iniciar_flask, daemon=True)
    flask_thread.start()

    monstro_thread_obj = threading.Thread(target=monstro_thread, daemon=True)
    monstro_thread_obj.start()

    threading.Thread(target=atualizar_trailing_stop, daemon=True).start()
    # Nova thread de monitoramento
    threading.Thread(target=monitorar_spread, daemon=True).start()
    # Sentinela de Fluxo (gatekeeper macro) em background
    threading.Thread(target=atualizar_sentinela, daemon=True).start()

    # Aguarda Flask ficar pronto antes de abrir a janela
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/status', timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    # Janela Desktop (PyWebView) â€” substitui o join, roda na thread principal
    try:
        import webview
        _janela = webview.create_window(
            title='Monstro Dashboard V2',
            url=f'http://127.0.0.1:{PORT}',
            width=1280,
            height=800,
            resizable=True,
            min_size=(1024, 600)
        )

        def _maximizar_janela():
            try:
                _janela.maximize()
            except Exception:
                pass

        webview.start(_maximizar_janela)
        # Limpeza ao fechar a janela
        logging.info("Janela Desktop fechada. Encerrando threads...")
        thread_ativo = False
        mt5_ativo = False
        try:
            import MetaTrader5 as mt5
            mt5.shutdown()
        except Exception:
            pass
        logging.info("RobÃ´ encerrado pela janela Desktop.")
    except Exception as e:
        logging.error(f"PyWebView nao disponivel ou falhou: {e}. Rodando sem janela desktop.")
        # Fallback: mantÃ©m o join original se pywebview falhar
        monstro_thread_obj.join()


# ======================================
# Fim do arquivo - Monstro das NegociaÃ§Ãµes v2

# ========== SISTEMA DE VETO SIMPLES E DIRETO (BASEADO NA SUGESTÃƒO DA IA) ==========


def carregar_experiencias_simples():
    """Carrega experiÃªncias do JSON de forma simples."""
    if not os.path.exists(EXPERIENCIAS_JSON):
        return []
    try:
        with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def contexto_similar_simples(exp_contexto, contexto_atual):
    """Verifica se contextos sÃ£o similares usando critÃ©rios simples."""
    # Volatilidade
    vol_atual = "baixa" if contexto_atual.get('volatility', 0) < 50 else "alta"
    vol_exp = "baixa" if exp_contexto.get('volatility', 0) < 50 else "alta"

    # RSI
    rsi_atual = contexto_atual.get('rsi_14', 50)
    rsi_exp = exp_contexto.get('rsi_14', 50)
    rsi_similar = abs(rsi_atual - rsi_exp) <= 20  # Â±20 pontos

    # Candle type
    candle_atual = contexto_atual.get('candle_type', '')
    candle_exp = exp_contexto.get('candle_type', '')

    return vol_atual == vol_exp and rsi_similar and candle_atual == candle_exp


def calcular_expectativa_simples(experiencias):
    """Calcula expectativa matemÃ¡tica simples."""
    if len(experiencias) < 5:  # MÃ­nimo de dados
        return None

    ganhos = [e['lucro'] for e in experiencias if e['lucro'] > 0]
    perdas = [e['lucro'] for e in experiencias if e['lucro'] < 0]

    if not ganhos or not perdas:
        return None

    winrate = len(ganhos) / len(experiencias)
    avg_gain = sum(ganhos) / len(ganhos)
    avg_loss = abs(sum(perdas) / len(perdas))

    expectativa = (winrate * avg_gain) - ((1 - winrate) * avg_loss)
    return expectativa


def deve_operar_contexto_simples(contexto_atual, acao_proposta, expectativa_minima=0):
    """VETO SIMPLES: Verifica se deve operar baseado no histÃ³rico."""
    experiencias = carregar_experiencias_simples()

    # Busca experiÃªncias similares com a mesma aÃ§Ã£o
    similares = []
    for exp in experiencias:
        if (exp.get('acao') == acao_proposta and
                contexto_similar_simples(exp.get('contexto', {}), contexto_atual)):
            similares.append(exp)

    expectativa = calcular_expectativa_simples(similares)

    if expectativa is None:
        return True, "Sem histÃ³rico suficiente"

    if expectativa <= expectativa_minima:
        return False, f"Expectativa negativa: {expectativa:.2f} (similares: {len(similares)})"

    return True, f"Expectativa positiva: {expectativa:.2f} (similares: {len(similares)})"


# ========== INSTÃ‚NCIAS GLOBAIS DOS NOVOS SISTEMAS ==========
# (bloqueador_contexto e replay_experiencias jÃ¡ instanciados acima, apÃ³s as classes)
# ========== LIMITE DE INSISTÃŠNCIA POR CONTEXTO (SUGESTÃƒO DA IA) ==========


class LimitadorInsistencia:
    """Limita operaÃ§Ãµes no mesmo contexto no mesmo dia."""

    def __init__(self):
        self.operacoes_por_contexto = {}  # {hash_contexto: [timestamps]}
        self.max_operacoes_contexto_dia = 2  # MÃ¡ximo 2 operaÃ§Ãµes por contexto por dia

    def _hash_contexto_dia(self, contexto: dict) -> str:
        """Cria hash do contexto + data."""
        hoje = datetime.now().date()
        hora = datetime.now().hour
        faixa_horario = f"{hora//2*2:02d}-{(hora//2*2)+1:02d}"

        vol_faixa = "baixa" if contexto.get('volatility', 0) < 50 else "alta"
        rsi_faixa = "baixo" if contexto.get(
            'rsi_14', 50) < 40 else "alto" if contexto.get('rsi_14', 50) > 60 else "neutro"
        candle = contexto.get('candle_type', 'unknown')

        return f"{hoje}_{faixa_horario}_{vol_faixa}_{rsi_faixa}_{candle}"

    def pode_operar(self, contexto: dict) -> bool:
        """Verifica se pode operar neste contexto hoje."""
        hash_ctx = self._hash_contexto_dia(contexto)

        if hash_ctx not in self.operacoes_por_contexto:
            return True

        # Conta operaÃ§Ãµes hoje neste contexto
        hoje = datetime.now().date()
        ops_hoje = [ts for ts in self.operacoes_por_contexto[hash_ctx]
                    if ts.date() == hoje]

        if len(ops_hoje) >= self.max_operacoes_contexto_dia:
            logging.warning(
                f"ðŸš« LIMITE CONTEXTO: JÃ¡ operou {len(ops_hoje)}x hoje em {hash_ctx}")
            return False

        return True

    def registrar_operacao(self, contexto: dict):
        """Registra uma operaÃ§Ã£o neste contexto."""
        hash_ctx = self._hash_contexto_dia(contexto)

        if hash_ctx not in self.operacoes_por_contexto:
            self.operacoes_por_contexto[hash_ctx] = []

        self.operacoes_por_contexto[hash_ctx].append(datetime.now())

        # Limpa operaÃ§Ãµes antigas (mais de 7 dias)
        cutoff = datetime.now() - timedelta(days=7)
        self.operacoes_por_contexto[hash_ctx] = [
            ts for ts in self.operacoes_por_contexto[hash_ctx]
            if ts > cutoff
        ]


# InstÃ¢ncia global do limitador
limitador_insistencia = LimitadorInsistencia()

