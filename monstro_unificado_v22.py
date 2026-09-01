# Ã¢Åâ¦ MONSTRO UNIFICADO V22 - COMPLETO E FUNCIONAL COM MELHORIAS
# Inclui: IA contÃÂ­nua com Keras, entropia do book, painel web, score,
# logs e aprendizado real
#
# Ã°Å¸Å¡â¬ MELHORIAS IMPLEMENTADAS (+10% EFICÃÂCIA TOTAL):
# Ã¢Åâ¦ 1. TRAILING STOP INTELIGENTE (+3% eficÃÂ¡cia)
# Ã¢Åâ¦ 2. BALANCEAMENTO BUY/SELL (+2% eficÃÂ¡cia)
# Ã¢Åâ¦ 3. MODOS DE MERCADO SIMPLIFICADOS (+2% eficÃÂ¡cia)
# Ã¢Åâ¦ 4. CIRCUIT BREAKERS ESSENCIAIS (+1.5% eficÃÂ¡cia)
# Ã¢Åâ¦ 5. SAÃÂDA INTELIGENTE DE POSIÃâ¡ÃÆO (+1.5% eficÃÂ¡cia)

import collections
import glob
import json
# region [Imports]
# Bibliotecas padrÃÂ£o
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
# '3' = sÃÂ³ FATAL (esconde a mensagem repetida "NodeDef ... use_unbounded_threadpool").
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
import warnings

# Warnings benignos e repetitivos das libs (sklearn feature names, TF eager) Ã¢â¬â nÃÂ£o afetam o robÃÂ´.
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
from sete_velas_orquestrador import Orquestrador7Velas
from sete_velas_util import (brt_agora, epoch_para_brt, brt_para_epoch,
                           velas_m15_do_dia, majority, calcular_cvd_janela,
                           velas_para_entrada, get_hora_entrada)

# Reduz warnings do TensorFlow
tf.config.experimental.enable_op_determinism()
# CORREÃâ¡ÃÆO CRÃÂTICA (C6): Adiciona semente global para resolver o erro de determinismo e permitir o treinamento.
tf.random.set_seed(42)

# TF_CPP_MIN_LOG_LEVEL jÃÂ¡ definido ANTES do import (acima). ReforÃÂ§a o logger Python do TF.
tf.get_logger().setLevel('ERROR')
# (Book nativo: a correÃÂ§ÃÂ£o de timestamp do CSV do EA foi removida Ã¢â¬â nÃÂ£o hÃÂ¡ mais CSV)


# ===== CONTROLE DE APRENDIZADO FORÃâ¡ADO =====
CONTADOR_OPERACOES_REJEITADAS = 0
LIMITE_REJEICOES_PARA_APRENDIZADO = 20  # Restaurado para 20 (fim do modo aprendizado temporÃÂ¡rio)
MODO_APRENDIZADO_FORCADO = False
# Limite diÃÂ¡rio de operaÃÂ§ÃÂµes forÃÂ§adas Ã¢â¬â evita contaminar modelo com trades ruins
FORCADOS_HOJE = 0
FORCADOS_DATA = None
MAX_FORCADOS_DIA = 3  # MÃÂ¡ximo 3 operaÃÂ§ÃÂµes forÃÂ§adas por dia

# ===== CLASSES PARA MELHORIAS IMPLEMENTADAS =====


class VolumeAdaptativo:
    """Ã°Å¸âÅ  Calcula um volume mÃÂ­nimo para operar de forma adaptativa."""

    def __init__(self, janela_minutos=15, percentual_da_media=0.8):
        self.janela_segundos = janela_minutos * 60
        self.percentual_da_media = percentual_da_media
        # Deque armazena (timestamp, volume)
        self.historico_volumes = collections.deque()
        self.volume_minimo_adaptativo = 500  # Valor inicial padrÃÂ£o (WDO)

    def adicionar_volume_atual(self, volume_total: float):
        """Adiciona o volume total do book ao histÃÂ³rico."""
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
        """Calcula o novo volume mÃÂ­nimo com base na mÃÂ©dia do histÃÂ³rico."""
        if not self.historico_volumes:
            return

        volumes_na_janela = [vol for ts, vol in self.historico_volumes]
        media_volume = sum(volumes_na_janela) / len(volumes_na_janela)

        # O novo mÃÂ­nimo ÃÂ© um percentual da mÃÂ©dia
        self.volume_minimo_adaptativo = media_volume * self.percentual_da_media

        # Garante um piso mÃÂ­nimo para nÃÂ£o operar com volume muito baixo
        piso_absoluto = 500
        self.volume_minimo_adaptativo = max(
            self.volume_minimo_adaptativo, piso_absoluto)

    def pode_operar(self, volume_atual: float) -> bool:
        """Verifica se o volume atual atende ao mÃÂ­nimo adaptativo."""
        return volume_atual >= self.volume_minimo_adaptativo


# ConfiguraÃÂ§ÃÂ£o TensorFlow
tf.config.run_functions_eagerly(True)

# endregion

# ========== MELHORIA 1: TRAILING STOP INTELIGENTE (+3% EFICÃÂCIA) ==========


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
        """Inicia o trailing stop para uma posiÃÂ§ÃÂ£o."""
        self.posicao_ativa = ticket
        self.preco_entrada = preco_entrada
        self.melhor_preco = preco_entrada
        self.trailing_ativo = False
        self.lucro_travado = False
        self.sl_original = sl_original

    def atualizar_trailing(self, preco_atual: float, tipo_posicao: str) -> Optional[float]:
        """Atualiza o trailing stop e retorna novo SL se necessÃÂ¡rio."""
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

        # Ativa trailing apÃÂ³s atingir gatilho (20 pontos WDO)
        if lucro_pontos >= 20 and not self.trailing_ativo:
            self.trailing_ativo = True
            logging.info(
                f"Ã°Å¸Å½Â¯ Trailing stop ativado! Lucro: {lucro_pontos:.1f} pontos")

        # Trava 70% do lucro quando > 20 pontos
        if lucro_pontos >= 20 and not self.lucro_travado:
            self.lucro_travado = True
            if tipo_posicao == "BUY":
                novo_sl = self.preco_entrada + (lucro_pontos * 0.7 * TICK_SIZE)
            else:
                novo_sl = self.preco_entrada - (lucro_pontos * 0.7 * TICK_SIZE)
            logging.info(f"Ã°Å¸ââ Lucro travado em 70%! Novo SL: {novo_sl}")
            return novo_sl

        # Trailing normal (10 pontos de distÃÂ¢ncia)
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


# region [ConfiguraÃÂ§ÃÂµes de Bloqueio]
MAX_LOSSES_SEQUENCIA = 3     # MÃÂ¡ximo de losses seguidos no mesmo lado
CICLOS_BLOQUEIO = 5         # NÃÂºmero de ciclos que o lado fica bloqueado
MIN_LUCRO_DESBLOQUEIO = 0.0  # Lucro mÃÂ­nimo para desbloquear lado antes do tempo
# endregion

# region [SeleÃÂ§ÃÂ£o DinÃÂ¢mica do Contrato]


def get_front_month_symbol_dynamic(prefix="WDO") -> str:
    """Busca no MT5 todos os contratos prefixados por WDO, filtra por trade_mode FULL
       e retorna aquele com expiraÃÂ§ÃÂ£o mais prÃÂ³xima no futuro."""
    symbols = mt5.symbols_get()  # lista de todos sÃÂ­mbolos do terminal
    agora_ts = datetime.now().timestamp()
    candidatas = []
    for s in symbols:
        if re.fullmatch(rf"{prefix}[A-Z]\d{{2}}", s.name) and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            exp_ts = getattr(s, 'expiration_time', None)
            if exp_ts and exp_ts > agora_ts:
                candidatas.append(s)
    if not candidatas:
        logging.error(
            f"Ã¢ÂÅ Nenhum contrato mensal {prefix}* ativo encontrado. Usando {prefix}$ como fallback.")
        return f"{prefix}$"
    # escolhe o que vence primeiro
    front = min(candidatas, key=lambda s: s.expiration_time)
    logging.info(
        f"Ã¢Åâ¦ Contrato dinÃÂ¢mico selecionado: {front.name} (venc.: {datetime.fromtimestamp(front.expiration_time)})")
    return front.name
# endregion

# region [Classes]


class GerenciadorBloqueio:
    """Gerencia o bloqueio de lados apÃÂ³s sequÃÂªncia de prejuÃÂ­zos."""

    def __init__(self):
        self.historico_acoes = []  # Lista de tuplas (acao, lucro)
        # Ciclos restantes de bloqueio
        self.bloqueio_lado = {"BUY": 0, "SELL": 0}
        self.ultima_acao = None
        self.losses_sequencia = {"BUY": 0, "SELL": 0}

    def registrar_operacao(self, acao: str, lucro: float) -> None:
        """Registra uma operaÃÂ§ÃÂ£o e atualiza contadores."""
        # SÃÂ³ processa aÃÂ§ÃÂµes vÃÂ¡lidas de trading
        if acao not in ["BUY", "SELL"]:
            logging.debug(
                f"Ignorando registro de operaÃÂ§ÃÂ£o para aÃÂ§ÃÂ£o invÃÂ¡lida: {acao}")
            return

        self.historico_acoes.append((acao, lucro))
        if len(self.historico_acoes) > 10:  # MantÃÂ©m histÃÂ³rico limitado
            self.historico_acoes.pop(0)

        # Atualiza contagem de losses em sequÃÂªncia - MAIS AGRESSIVO
        # SÃÂ³ conta como loss se for prejuÃÂ­zo significativo (maior que 25 reais)
        if acao in ["BUY", "SELL"] and lucro < -25.0:
            self.losses_sequencia[acao] += 1
            # Verifica se atingiu limite de losses seguidos
            if self.losses_sequencia[acao] >= MAX_LOSSES_SEQUENCIA:
                self.bloquear_lado(acao)
                logging.warning(
                    f"Ã°Å¸Å¡Â« Bloqueando lado {acao} por {CICLOS_BLOQUEIO} ciclos apÃÂ³s {MAX_LOSSES_SEQUENCIA} losses seguidos")
        else:
            # Reseta contador de losses se teve lucro OU prejuÃÂ­zo pequeno
            self.losses_sequencia[acao] = max(
                0, self.losses_sequencia[acao] - 1)  # Decrementa gradualmente
            # Verifica se pode desbloquear por lucro (critÃÂ©rio mais flexÃÂ­vel)
            if lucro >= MIN_LUCRO_DESBLOQUEIO and self.bloqueio_lado[acao] > 0:
                # Reduz bloqueio gradualmente
                self.bloqueio_lado[acao] = max(0, self.bloqueio_lado[acao] - 1)
                logging.info(
                    f"Ã¢Åâ¦ Reduzindo bloqueio do lado {acao} por resultado nÃÂ£o negativo")

        self.ultima_acao = acao

    def bloquear_lado(self, lado: str) -> None:
        """Bloqueia um lado por N ciclos."""
        if lado in ["BUY", "SELL"]:
            self.bloqueio_lado[lado] = CICLOS_BLOQUEIO
        else:
            logging.debug(f"Tentativa de bloquear lado invÃÂ¡lido: {lado}")

    def verificar_bloqueio(self, acao: str) -> bool:
        """Verifica se uma aÃÂ§ÃÂ£o estÃÂ¡ bloqueada e atualiza contadores."""
        # SÃÂ³ verifica bloqueio para aÃÂ§ÃÂµes vÃÂ¡lidas de trading
        if acao not in ["BUY", "SELL"]:
            return False

        if self.bloqueio_lado[acao] > 0:
            self.bloqueio_lado[acao] -= 1
            return True
        return False

    def obter_acao_alternativa(self, acao_original: str) -> str:
        """Retorna a aÃÂ§ÃÂ£o oposta quando hÃÂ¡ bloqueio."""
        if acao_original == "BUY":
            return "SELL"
        elif acao_original == "SELL":
            return "BUY"
        else:
            # Fallback para aÃÂ§ÃÂ£o invÃÂ¡lida
            logging.warning(
                f"AÃÂ§ÃÂ£o original invÃÂ¡lida para alternativa: {acao_original}")
            return "BUY"  # Default

    def get_status(self) -> dict:
        """Retorna status atual do gerenciador."""
        return {
            "bloqueios": self.bloqueio_lado.copy(),
            "losses_sequencia": self.losses_sequencia.copy(),
            "ultima_acao": self.ultima_acao
        }

# endregion


# region [ConfiguraÃÂ§ÃÂµes]
# ---- RESOLUÃâ¡ÃÆO DE CAMINHOS (corrige PyInstaller vs script) ----
def _caminho_base():
    """Retorna o diretÃÂ³rio base para escrita de arquivos de dados (C:\\AIOFEN).
       Independente do CWD e da localizaÃÂ§ÃÂ£o do executÃÂ¡vel PyInstaller:
       prioriza o diretÃÂ³rio que CONTÃâ°M o config.json (assinatura do projeto)."""
    candidatos = [r"C:\AIOFEN"]
    if getattr(sys, 'frozen', False):
        candidatos.append(os.path.dirname(sys.executable))
        if hasattr(sys, '_MEIPASS'):
            candidatos.append(os.path.dirname(os.path.dirname(sys._MEIPASS)))
    else:
        candidatos.append(os.path.dirname(os.path.abspath(__file__)))
    candidatos.append(os.getcwd())
    for c in candidatos:
        try:
            if c and os.path.isdir(c) and os.path.exists(os.path.join(c, 'config.json')):
                return c
        except Exception:
            continue
    return candidatos[0]

def _caminho_dados(nome):
    """Retorna caminho absoluto para um arquivo de dados."""
    return os.path.join(_caminho_base(), nome)

# Carrega configuraÃÂ§ÃÂ£o especÃÂ­fica do WDO
CONFIG_FILE = _caminho_dados("config.json")


def carregar_configuracao():
    """Carrega configuraÃÂ§ÃÂ£o do arquivo JSON."""
    try:
        # utf-8-sig: tolera BOM (um BOM aqui fazia json.load falhar e o robo
        # rodava inteiro nos defaults: SL=5/TP=10/Magic=123457 em vez do config real)
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ã¢Å Erro ao carregar configuraÃÂ§ÃÂ£o: {e}")
        return {}


# Carrega configuraÃÂ§ÃÂ£o
config = carregar_configuracao()

# ========== v22.1 HOTFIX: Multi-Estrategia 7 Velas (estado global) ==========
SETE_VELAS_CFG = config.get("sete_velas", {}) if isinstance(config, dict) else {}
SETE_VELAS_ATIVO = bool(SETE_VELAS_CFG.get("ativo", False))
MAGIC_SETE_VELAS = int(SETE_VELAS_CFG.get("magic", 7007))
SETE_VELAS_INICIO_HORA = float(SETE_VELAS_CFG.get("hora_inicio", 9.0))
SETE_VELAS_FIM_HORA = float(SETE_VELAS_CFG.get("hora_fim", 11.5))
ESTADO_SISTEMA = "PADRAO_MONSTRO"


def _atualizar_estado_sistema():
    """Alterna o estado global entre SETE_VELAS_EXCLUSIVO e PADRAO_MONSTRO
    conforme janela configurada e disponibilidade da estrategia."""
    global ESTADO_SISTEMA
    try:
        if not SETE_VELAS_ATIVO:
            ESTADO_SISTEMA = "PADRAO_MONSTRO"
            return
        a = brt_agora()
        h = a.hour + a.minute / 60.0
        if a.weekday() >= 5 or not (SETE_VELAS_INICIO_HORA <= h < SETE_VELAS_FIM_HORA):
            ESTADO_SISTEMA = "PADRAO_MONSTRO"
        else:
            ESTADO_SISTEMA = "SETE_VELAS_EXCLUSIVO"
    except Exception as e:
        logging.warning(f"Falha ao atualizar ESTADO_SISTEMA: {e}")
        ESTADO_SISTEMA = "PADRAO_MONSTRO"

# Cache TTL e configuraÃÂ§ÃÂµes de retry
CACHE_TTL = 1  # segundos
MAX_RETRY_ATTEMPTS = 5  # Aumentado para mais tentativas
RETRY_WAIT_MULTIPLIER = 2  # segundos - Aumentado o tempo entre tentativas

# region [Cache e Retry]


@lru_cache(maxsize=128)
def get_cached_symbol_info(symbol: str) -> Optional[Any]:
    """Cache para informaÃÂ§ÃÂµes do sÃÂ­mbolo."""
    return mt5.symbol_info(symbol)


def reconectar_mt5() -> bool:
    """Tenta reconectar ao MetaTrader 5."""
    try:
        if mt5.initialize():
            logging.info("Ã¢Åâ¦ Reconectado ao MetaTrader 5")
            return True
        else:
            logging.error(f"Ã¢ÂÅ Erro ao reconectar: {mt5.last_error()}")
            return False
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro na reconexÃÂ£o: {e}")
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
            logging.warning("Ã¢Å¡Â Ã¯Â¸Â Book vazio ou nulo - tentando reconexÃÂ£o")
            if reconectar_mt5():
                result = mt5.market_book_get(symbol)

        return result
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao obter book: {e}")
        raise Exception("Falha ao obter market book")


@retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
       wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER))
def retry_positions_get(symbol: str = None) -> Optional[Any]:
    """Tenta obter posiÃÂ§ÃÂµes com retry em caso de falha."""
    return mt5.positions_get(symbol=symbol)

# endregion


# region [ConfiguraÃÂ§ÃÂµes]
# Paths e arquivos - ADAPTADO PARA WDO
MT5_PATH = config.get("geral", {}).get(
    "mt5_path", r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe")
SYMBOL = None  # SerÃÂ¡ definido apÃÂ³s inicializar o MT5
SYMBOL_DOL = None  # DÃÂ³lar Cheio (DOL) Ã¢â¬â referÃÂªncia de fluxo institucional
TIMEFRAME = mt5.TIMEFRAME_M1

HISTORICO_CSV = config.get("aprendizado", {}).get(
    "historico_csv", _caminho_dados("historico_contexto_wdo.csv"))


COLUNAS_CONTEXTO_OFICIAL = [
    'timestamp', 'bid_qty', 'ask_qty', 'spread', 'volatility', 'candle_type',
    'entropia_book', 'rsi_14', 'volume_tick', 'is_in_trade', 'floating_profit',
    'tempo_em_trade', 'preco_maior_escora_bid', 'volume_maior_escora_bid',
    'distancia_maior_escora_bid', 'preco_maior_escora_ask',
    'volume_maior_escora_ask', 'distancia_maior_escora_ask',
    'liquidez_top5_bid', 'liquidez_top5_ask', 'action', 'reward']


def _migrar_historico_timestamp():
    """Migracao unica de schema: arquivo antigo sem 'timestamp' vai para .bak.

    O log de contexto passou a gravar 'timestamp' como primeira coluna.
    Como o append usa header=False, um arquivo antigo geraria desalinhamento
    de colunas e perda silenciosa de linhas nos loads (on_bad_lines='skip').
    """
    try:
        if not os.path.exists(HISTORICO_CSV):
            _recriar_header_contexto()
            return
        with open(HISTORICO_CSV, encoding="utf-8-sig") as f:
            cabecalho = f.readline().strip().split(",")
        if cabecalho and cabecalho[0].strip().lower() == "timestamp":
            return
        backup = f"{HISTORICO_CSV}.sem_timestamp.bak"
        os.rename(HISTORICO_CSV, backup)
        logging.warning(
            "HISTORICO: schema antigo sem timestamp migrado para %s. "
            "Novo arquivo sera criado com timestamp.", os.path.basename(backup))
        _recriar_header_contexto()
    except Exception as e:
        logging.warning("HISTORICO: falha na migracao de schema (%s)", e)


def _recriar_header_contexto() -> None:
    """Recria o CSV de contexto com o header oficial (timestamp na 1a coluna).

    Garante que um arquivo apagado/inexistente nasca com o esquema correto,
    evitando que o append (header=False) produza um CSV sem cabecalho.
    """
    try:
        if os.path.exists(HISTORICO_CSV):
            return
        if not os.path.exists(os.path.dirname(os.path.abspath(HISTORICO_CSV))):
            os.makedirs(os.path.dirname(os.path.abspath(HISTORICO_CSV)), exist_ok=True)
        try:
            import pandas as _pd
            _pd.DataFrame(columns=COLUNAS_CONTEXTO_OFICIAL).to_csv(
                HISTORICO_CSV, index=False)
        except ImportError:
            with open(HISTORICO_CSV, "w", encoding="utf-8") as f:
                f.write(",".join(COLUNAS_CONTEXTO_OFICIAL) + "\n")
        logging.info(
            "[HISTORICO] Arquivo de contexto recriado com header oficial "
            "(%d colunas, timestamp na 1a posicao).", len(COLUNAS_CONTEXTO_OFICIAL))
    except Exception as e:
        logging.warning("HISTORICO: falha ao recriar header (%s)", e)


_migrar_historico_timestamp()

MODELO_PATH = config.get("aprendizado", {}).get(
    "modelo_path", _caminho_dados("modelo_monstro_wdo.h5"))
LOG_FILE = _caminho_dados("monstro_wdo.log")

# ========== SHADOW MODE - MODELO A (veto ML em avaliacao passiva) ==========
# Registra a probabilidade do Modelo A em cada ordem SEM bloquear execucao.
# Dados gravados em logs/modelo_a_shadow.csv para validacao futura do veto.
SHADOW_CSV = os.path.join(_caminho_base(), "logs", "modelo_a_shadow.csv")
_shadow_modelo_a = None
_shadow_scaler_a = None
_SHADOW_FEATS = [
    "estado_alta", "estado_baixa", "estado_consol", "estado_breakout",
    "estado_prev_alta", "estado_prev_baixa", "estado_prev_consol",
    "estado_prev_breakout",
    "atr_ratio", "slope", "dist_ema_atr", "corpo_atr",
    "sessao_manha", "sessao_almoco", "sessao_tarde",
    "mtf_close_5", "mtf_rsi_5", "mtf_atr_5", "mtf_wr_5", "mtf_tick_volume_5",
    "mtf_close_15", "mtf_rsi_15", "mtf_atr_15", "mtf_wr_15",
    "mtf_tick_volume_15",
    "mtf_close_30", "mtf_rsi_30", "mtf_atr_30", "mtf_wr_30",
    "mtf_tick_volume_30",
]


def _shadow_carregar_modelo():
    """Carrega o Modelo A e o scaler uma unica vez. Retorna True se pronto."""
    global _shadow_modelo_a, _shadow_scaler_a
    if _shadow_modelo_a is not None:
        return True
    try:
        from tensorflow.keras.models import load_model as _lm
        caminho_modelo = os.path.join(_caminho_base(), "modelo_a_filtro_wdo.keras")
        caminho_scaler = os.path.join(_caminho_base(), "modelo_a_scaler.json")
        if not (os.path.exists(caminho_modelo) and os.path.exists(caminho_scaler)):
            return False
        _shadow_modelo_a = _lm(caminho_modelo)
        with open(caminho_scaler, encoding="utf-8") as f:
            params = json.load(f)
        _shadow_scaler_a = (np.array(params["mean"]), np.array(params["scale"]))
        logging.info("SHADOW: Modelo A carregado para modo passivo.")
        return True
    except Exception as e:
        logging.warning(f"SHADOW: modelo A indisponivel ({e})")
        return False


def _shadow_features_atuais(symbol):
    """Replica o pipeline de treinar_modelo_a na ultima barra M5 FECHADA."""
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1800)
    if rates is None or len(rates) < 400:
        return None
    m1 = pd.DataFrame(rates)
    m1["time"] = pd.to_datetime(m1["time"], unit="s")
    m1.set_index("time", inplace=True)

    def indicadores_tf(d, regra):
        t = d.resample(regra).agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "tick_volume": "sum"}).dropna()
        delta = t["close"].diff()
        ganho = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        perda = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rs = ganho / perda.replace(0, np.nan)
        t["rsi"] = 100 - 100 / (1 + rs)
        hl = t["high"] - t["low"]
        hc = (t["high"] - t["close"].shift()).abs()
        lc = (t["low"] - t["close"].shift()).abs()
        t["atr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(
            alpha=1 / 14, adjust=False).mean()
        maior = t["high"].rolling(14).max()
        menor = t["low"].rolling(14).min()
        t["wr"] = -100 * (maior - t["close"]) / (maior - menor).replace(0, np.nan)
        return t[["close", "rsi", "atr", "wr", "tick_volume"]]

    partes = {}
    for tf, regra in [("5", "5min"), ("15", "15min"), ("30", "30min")]:
        t = indicadores_tf(m1, regra)
        for col in t.columns:
            partes[f"mtf_{col}_{tf}"] = t[col]
    grade = m1.resample("5min").close.last().index
    mtf = pd.DataFrame(partes).reindex(grade).ffill()

    d5 = m1.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

    ema = d5["close"].ewm(span=21, adjust=False).mean()
    ref = ema.shift(3)
    slope = np.where(ref != 0, (ema - ref) / ref, 0.0)
    hl = d5["high"] - d5["low"]
    hc = (d5["high"] - d5["close"].shift()).abs()
    lc = (d5["low"] - d5["close"].shift()).abs()
    atr = pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(
        span=14, adjust=False).mean()
    atr_ma = atr.ewm(span=14, adjust=False).mean()
    ratio_ref = atr_ma.shift(3)
    atr_ratio = np.where(ratio_ref > 0, atr / ratio_ref, 1.0)

    estado = np.full(len(d5), 2, dtype=int)
    estado[atr_ratio >= 1.0] = 3
    zona = (atr_ratio >= 0.6) & (atr_ratio < 1.0)
    estado[zona & (slope > 0.0003)] = 0
    estado[zona & (slope < -0.0003)] = 1

    i = len(d5) - 2  # ultima barra FECHADA
    feats = {}
    for k, nome in [(0, "alta"), (1, "baixa"), (2, "consol"), (3, "breakout")]:
        feats[f"estado_{nome}"] = float(estado[i] == k)
        feats[f"estado_prev_{nome}"] = float(estado[i - 1] == k)
    feats["atr_ratio"] = float(atr_ratio[i])
    feats["slope"] = float(slope[i])
    feats["dist_ema_atr"] = float((d5["close"].iloc[i] - ema.iloc[i]) / atr.iloc[i])
    feats["corpo_atr"] = float(
        (d5["close"].iloc[i] - d5["open"].iloc[i]) / atr.iloc[i])
    ts = d5.index[i]
    h, m = ts.hour, ts.minute
    feats["sessao_manha"] = float((h == 9 and m >= 10) or (10 <= h < 12))
    feats["sessao_almoco"] = float(12 <= h < 14)
    feats["sessao_tarde"] = float(14 <= h < 17)

    linha_mtf = mtf.iloc[i]
    for c in mtf.columns:
        feats[c] = float(linha_mtf[c]) if pd.notna(linha_mtf[c]) else 0.0

    return np.array([feats[c] for c in _SHADOW_FEATS], dtype=float)


def shadow_registrar_entrada(ticket, direcao, symbol):
    """Grava a probabilidade do Modelo A no momento da entrada (passivo)."""
    try:
        if not _shadow_carregar_modelo():
            return
        x_raw = _shadow_features_atuais(symbol)
        if x_raw is None:
            return
        mean, scale = _shadow_scaler_a
        x = ((x_raw - mean) / scale).reshape(1, -1)
        prob = float(_shadow_modelo_a.predict(x, verbose=0)[0][0])
        os.makedirs(os.path.dirname(SHADOW_CSV), exist_ok=True)
        novo = not os.path.exists(SHADOW_CSV)
        import csv as _csv
        with open(SHADOW_CSV, "a", newline="", encoding="utf-8") as f:
            w = _csv.writer(f)
            if novo:
                w.writerow(["timestamp", "ticket_mt5", "direcao",
                            "prob_modelo_a", "resultado_bruto",
                            "resultado_pontos"])
            w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ticket, direcao, f"{prob:.4f}", "", ""])
        logging.info(f"SHADOW Modelo A: ticket {ticket} {direcao} p={prob:.3f}")
    except Exception as e:
        logging.warning(f"SHADOW: falha ao registrar entrada ({e})")


def shadow_registrar_resultado(ticket, lucro):
    """Preenche o resultado da ordem na linha shadow correspondente."""
    try:
        if not os.path.exists(SHADOW_CSV):
            return
        df = pd.read_csv(SHADOW_CSV)
        if "ticket_mt5" not in df.columns:
            return
        mask = (df["ticket_mt5"] == ticket) & (
            df["resultado_bruto"].isna() | (df["resultado_bruto"] == ""))
        if not mask.any():
            return
        idx = df[mask].index[-1]
        df.loc[idx, "resultado_bruto"] = round(float(lucro), 2)
        df.to_csv(SHADOW_CSV, index=False)
        logging.info(f"SHADOW Modelo A: resultado ticket {ticket} "
                     f"lucro={lucro:.2f}")
    except Exception as e:
        logging.warning(f"SHADOW: falha ao registrar resultado ({e})")
# ========== FIM SHADOW MODE ==========


# ConfiguraÃÂ§ÃÂµes Web
PORT = config.get("web_dashboard", {}).get("port", 5002)
DEBUG = config.get("web_dashboard", {}).get("debug", True)

# ConfiguraÃÂ§ÃÂµes Trading - ADAPTADO PARA WDO
MAGIC_NUMBER = config.get("geral", {}).get("magic_number", 123457)
# Volume mÃÂ­nimo REAL para considerar nÃÂ­vel vÃÂ¡lido no book (WDO tem menos volume)
VOLUME_MINIMO = 50
# Atualizado para 22 features (10 originais + 8 profundidade + 4 ptax/payroll)
N_FEATURES = 22
DEVIATION = config.get("geral", {}).get("deviation", 20)

# ConfiguraÃÂ§ÃÂµes B3 - MINI DÃâLAR (WDO)
TICK_SIZE = config.get("contrato", {}).get(
    "tick_size", 0.5)           # Tamanho do tick WDO
TICKS_POR_PONTO = config.get("contrato", {}).get(
    "ticks_por_ponto", 1000)    # WDO: 1 ponto = 1000 ticks
# Volume padrÃÂ£o (1 contrato WDO)
VOLUME_PADRAO = config.get("volume_padrao", 1.0)
HORARIO_PREGAO = config.get("horarios", {}).get("pregao", "09:00")
HORARIO_LIMITE_ORDENS = config.get(
    "horarios", {}).get("limite_ordens", "17:30")
HORARIO_ENCERRAMENTO = config.get("horarios", {}).get("encerramento", "17:35")
HORARIO_AFTER = config.get("horarios", {}).get("after_market", "17:40")
HORARIO_AJUSTE = "23:59"  # HorÃÂ¡rio do ajuste (ajustado para testes)
DIGITS_INDICE = config.get("contrato", {}).get(
    "digits_indice", 0)         # Casas decimais do Mini ÃÂndice

# Limites de distÃÂ¢ncia em ticks e pontos - ADAPTADO PARA WDO
MIN_TICKS = 500             # 1 ponto WDO = 500 ticks
MAX_TICKS = 5000            # 10 pontos WDO = 5000 ticks (TP dinÃÂ¢mico)
MAX_DISTANCIA_SL_PONTOS = config.get(
    "sl_points", 5)      # 5 pontos WDO (FIX 07/08: era 8 -> perdas de R$80)
MAX_DISTANCIA_TP_PONTOS = config.get(
    "tp_points", 10)     # 10 pontos WDO (TP dinÃÂ¢mico)

# Trailing Stop (em pontos) - ADAPTADO PARA WDO
TRAILING_ATIVO = config.get("trailing_stop", {}).get("ativo", True)
TRAILING_INTERVALO = config.get(
    "trailing_stop", {}).get("intervalo_segundos", 5)
# NOTA: TRAILING_GATILHO e TRAILING_DISTANCIA sÃÂ£o definidos em linha ~964 (apÃÂ³s melhorias)
# Os valores do config.json sÃÂ£o sobrescritos pelos valores ajustados manualmente

# Stop Loss e Take Profit (em pontos) - CONFIGURAÃâ¡ÃÆO WDO (REFATORADO)
# 5 pontos WDO = 5000 ticks (SL como rede de seguranÃÂ§a - FIX 07/08: era 8)
SL_POINTS = config.get("sl_points", 5)
# 10 pontos WDO = 10000 ticks (TP dinÃÂ¢mico - Keras decide saÃÂ­da)
TP_POINTS = config.get("tp_points", 10)

# ========================================================================
# Ã°Å¸Å½Â¯ FILTRO SNIPER DE ELITE (BOOK NATIVO MT5) - AJUSTE FÃÂCIL AQUI
# ------------------------------------------------------------------------
# Estes 2 valores controlam quando o robÃÂ´ "acorda" para operar.
# Migrados do EA MQL5 para o Python (arquitetura nativa, sem CSV/EA).
#   SNIPER_VOLUME_MIN : volume TOTAL somado (bid+ask) nos 10 nÃÂ­veis do book
#                       necessÃÂ¡rio para o robÃÂ´ considerar operar (big players).
#   SNIPER_RATIO_MIN  : desequilÃÂ­brio mÃÂ­nimo entre os lados (um lado precisa
#                       ter pelo menos este mÃÂºltiplo do volume do outro).
# Basta alterar os nÃÂºmeros abaixo e reiniciar o robÃÂ´ Ã¢â¬â sem recompilar EA.
# AJUSTADO PARA WDO (Mini DÃÂ³lar): thresholds 3-5x menores que WIN (Mini ÃÂndice)
# ========================================================================
SNIPER_VOLUME_MIN = config.get("sniper_volume_min", 800)
SNIPER_RATIO_MIN = config.get("sniper_ratio_min", 1.5)  # Restaurado para 1.5 (fim do modo aprendizado temporÃÂ¡rio)

# ========================================================================
# Ã°Å¸ââ¡ CONTROLE DE VERBOSIDADE DOS LOGS (NÃÆO afeta a velocidade/decisÃÂ£o do robÃÂ´!)
# O robÃÂ´ monitora e decide sempre no ritmo mÃÂ¡ximo (1-5s). Isto controla apenas
# a FREQUÃÅ NCIA de ESCRITA no arquivo de log, para ficar legÃÂ­vel (~60 linhas/hora
# em standby). Dicts mutÃÂ¡veis = nÃÂ£o precisam de 'global' nas funÃÂ§ÃÂµes.
# ========================================================================
_veto_estado = {'ultimo_log': 0.0}
VETO_LOG_INTERVALO_S = 60   # loga o veto no mÃÂ¡ximo 1x a cada 60s

# Cooldown anti-espasmo da inversÃÂ£o de fluxo (FIX 07/08: era 1x/5s -> 27x FALHA 10016)
_fluxo_estado = {'ultimo_ajuste': 0.0}
FLUXO_COOLDOWN_S = 60         # no mÃÂ¡ximo 1 ajuste de SL por fluxo a cada 60s
FLUXO_TRAVA_LUCRO_PCT = 0.50  # trava 50% do lucro quando o fluxo vira (nÃÂ£o breakeven)
FLUXO_DIST_MINIMA_PTS = 2.0   # distÃÂ¢ncia mÃÂ­nima SL-preÃÂ§o para tentar ajuste (evita retcode 10016)
_log_estado = {'ultimo_pulso': 0.0, 'ultimo_heartbeat': 0.0}
PULSO_LOG_INTERVALO_S = 60      # pulso de mercado (Ã°Å¸âÅ ) 1x a cada 60s em standby
HEARTBEAT_LOG_INTERVALO_S = 15  # heartbeat da posiÃÂ§ÃÂ£o (Ã°Å¸ââ) 1x a cada 15s operando
_throttle_estado = {}


def _log_periodico(chave: str, intervalo_s: float) -> bool:
    """Retorna True no mÃÂ¡ximo 1x a cada intervalo_s para a 'chave'. Controla apenas
    a FREQUÃÅ NCIA de logs Ã¢â¬â NÃÆO altera o processamento/decisÃÂ£o do robÃÂ´."""
    agora = time.time()
    if agora - _throttle_estado.get(chave, 0.0) >= intervalo_s:
        _throttle_estado[chave] = agora
        return True
    return False

# Circuit Breakers - ADAPTADO PARA WDO
MAX_LOSS_DIARIO = config.get("risk_management", {}).get(
    "max_loss_diario", -500.0)   # Limite de perda diÃÂ¡ria em reais
MAX_DRAWDOWN = config.get("risk_management", {}).get(
    "max_drawdown", -250.0)      # Limite de drawdown por operaÃÂ§ÃÂ£o em reais
# Spread mÃÂ¡ximo em pontos WDO
MAX_SPREAD = config.get("max_spread", 5)
MIN_TICKS_VALIDOS = 10      # MÃÂ­nimo de ticks vÃÂ¡lidos WDO
# Volume mÃÂ­nimo no book WDO - FILTRO ULTRA SELETIVO
# Aumentado para 200cc para SEGUIR BIG PLAYERS - mÃÂ¡xima acertividade
MIN_VOLUME_BOOK = config.get("min_volume_book", 200)

# ConfiguraÃÂ§ÃÂµes de Aprendizado
MIN_EXPERIENCIAS_TREINO = 3    # MÃÂ­nimo de experiÃÂªncias para comeÃÂ§ar treino
MAX_EXPERIENCIAS_MEMORIA = 1000  # MÃÂ¡ximo de experiÃÂªncias na memÃÂ³ria
EPOCHS_TREINO = 3               # NÃÂºmero de ÃÂ©pocas por treino
BATCH_SIZE = 32                 # Tamanho do batch de treino
MIN_DELTA_LOSS = 0.001         # MÃÂ­nima melhoria na loss para continuar
PATIENCE_EARLY_STOP = 3        # PaciÃÂªncia para early stopping
DECAY_MEIA_VIDA = 12           # Meia-vida do decay em horas
INTERVALO_REPLAY = 60          # Intervalo em minutos para replay
PESO_REPLAY = 0.3              # Peso das experiÃÂªncias no replay
JANELA_CONSISTENCIA = 5        # Janela para calcular consistÃÂªncia

# Arquivos de dados (HISTORICO_CSV jÃÂ¡ definido acima via config)
EXPERIENCIAS_JSON = _caminho_dados("experiencias_wdo.json")
DECISIONS_CSV = _caminho_dados("decisions_wdo.csv")
MULTITF_CSV = _caminho_dados("historico_multitf.csv")

# ========== FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR ==========


class BloqueadorContexto:
    """Sistema de bloqueio de contextos perdedores baseado em experiÃÂªncias passadas."""

    def __init__(self):
        # {hash_coeado_ate''losses': count, 'bloqueado_ate': timestamp}}
        self.contextos_bloqueados = {}
        self.max_losses_contexto = 3  # MÃÂ¡ximo de losses no mesmo contexto
        self.tempo_bloqueio = 3600  # 1 hora de bloqueio

    def _hash_contexto(self, contexto: dict) -> str:
        """Cria hash ÃÂºnico do contexto para identificaÃÂ§ÃÂ£o."""
        # Agrupa por faixas para criar contextos similares
        hora = datetime.now().hour
        faixa_horario = f"{hora//2*2:02d}-{(hora//2*2)+1:02d}"  # Faixas de 2h

        volatilidade_faixa = "baixa" if contexto.get(
            'volatility', 0) < 50 else "alta"
        rsi_faixa = "baixo" if contexto.get(
            'rsi_14', 50) < 40 else "alto" if contexto.get('rsi_14', 50) > 60 else "neutro"
        candle_type = contexto.get('candle_type', 'unknown')

        # PressÃÂ£o do book
        bid_qty = contexto.get('bid_qty', 0)
        ask_qty = contexto.get('ask_qty', 0)
        ratio = bid_qty / (ask_qty + 1)  # +1 para evitar divisÃÂ£o por zero
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
                f"Ã°Å¸Å¡Â« CONTEXTO BLOQUEADO: {hash_ctx} - {self.max_losses_contexto} losses consecutivos")

    def contexto_bloqueado(self, contexto: dict) -> bool:
        """Verifica se contexto estÃÂ¡ bloqueado."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx not in self.contextos_bloqueados:
            return False

        ctx_data = self.contextos_bloqueados[hash_ctx]

        # Verifica se ainda estÃÂ¡ no perÃÂ­odo de bloqueio
        if ctx_data['bloqueado_ate'] > time.time():
            tempo_restante = int(ctx_data['bloqueado_ate'] - time.time())
            logging.info(
                f"Ã¢ÂÂ³ Contexto {hash_ctx} bloqueado por mais {tempo_restante}s")
            return True

        # Se passou o tempo, reseta o contador
        if ctx_data['bloqueado_ate'] > 0 and ctx_data['bloqueado_ate'] <= time.time():
            self.contextos_bloqueados[hash_ctx] = {
                'losses': 0, 'bloqueado_ate': 0}
            logging.info(f"Ã¢Åâ¦ Contexto {hash_ctx} desbloqueado")

        return False

    def registrar_win(self, contexto: dict):
        """Registra um win - reduz contador de losses do contexto."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx in self.contextos_bloqueados:
            self.contextos_bloqueados[hash_ctx]['losses'] = max(
                0, self.contextos_bloqueados[hash_ctx]['losses'] - 1)
            if self.contextos_bloqueados[hash_ctx]['losses'] == 0:
                self.contextos_bloqueados[hash_ctx]['bloqueado_ate'] = 0
                logging.info(f"Ã¢Åâ¦ Contexto {hash_ctx} reabilitado apÃÂ³s win")

# ========== FASE 2: REPLAY DE EXPERIÃÅ NCIAS ATIVO ==========


class ReplayExperiencias:
    """Sistema de consulta ativa de experiÃÂªncias passadas antes de operar."""

    def __init__(self):
        self.experiencias_cache = []
        self.ultimo_carregamento = 0
        self.cache_valido_por = 300  # 5 minutos

    def carregar_experiencias(self):
        """Carrega experiÃÂªncias do arquivo JSON."""
        try:
            if not os.path.exists(EXPERIENCIAS_JSON):
                return []

            # Verifica se precisa recarregar cache
            if time.time() - self.ultimo_carregamento < self.cache_valido_por:
                return self.experiencias_cache

            with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
                experiencias = json.load(f)

            # Filtra apenas experiÃÂªncias dos ÃÂºltimos 7 dias
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
                f"Ã°Å¸âÅ¡ Carregadas {len(experiencias_recentes)} experiÃÂªncias recentes")
            return experiencias_recentes

        except Exception as e:
            logging.error(f"Ã¢ÂÅ Erro ao carregar experiÃÂªncias: {e}")
            return []

    def calcular_expectativa_contexto(self, contexto_atual: dict, acao_proposta: str) -> dict:
        """Calcula expectativa matemÃÂ¡tica para contexto similar."""
        experiencias = self.carregar_experiencias()

        if not experiencias:
            return {'expectativa': 0, 'trades_similares': 0, 'taxa_acerto': 0, 'lucro_medio': 0, 'perda_media': 0}

        # Busca experiÃÂªncias similares com critÃÂ©rios relaxados
        similares = []

        for exp in experiencias:
            if exp.get('acao') != acao_proposta:
                continue

            ctx = exp.get('contexto', {})
            similar = True

            # Volatilidade similar (ÃÂ±40% Ã¢â¬â relaxado de 20%)
            vol_atual = contexto_atual.get('volatility', 0)
            vol_exp = ctx.get('volatility', 0)
            if vol_atual > 0 and abs(vol_atual - vol_exp) > vol_atual * 0.4:
                similar = False

            # RSI similar (ÃÂ±25 pontos Ã¢â¬â relaxado de 15)
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

        # Calcula estatÃÂ­sticas
        lucros = [exp.get('lucro', 0) for exp in similares]
        wins = [l for l in lucros if l > 0]
        losses = [l for l in lucros if l < 0]

        taxa_acerto = len(wins) / len(lucros) if lucros else 0
        lucro_medio = sum(wins) / len(wins) if wins else 0
        perda_media = abs(sum(losses) / len(losses)) if losses else 0

        # Expectativa matemÃÂ¡tica
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
            f"Ã°Å¸âÅ  Expectativa {acao_proposta}: {expectativa:.2f} | Similares: {len(similares)} | Taxa: {taxa_acerto*100:.1f}%")

        return resultado


# ========== INSTÃâNCIAS GLOBAIS Ã¢â¬â definidas aqui para ficarem disponÃÂ­veis em todo o mÃÂ³dulo ==========
bloqueador_contexto = BloqueadorContexto()
replay_experiencias = ReplayExperiencias()

# ========== SISTEMA DE VETO SIMPLES E DIRETO (BASEADO NA SUGESTÃÆO DA IA) ==========


def carregar_experiencias_simples():
    """Carrega experiÃÂªncias do JSON de forma simples."""
    if not os.path.exists(EXPERIENCIAS_JSON):
        return []
    try:
        with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def contexto_similar_simples(exp_contexto, contexto_atual):
    """Verifica se contextos sÃÂ£o similares usando critÃÂ©rios simples."""
    # Faixa horÃÂ¡ria (2h)
    hora_atual = datetime.now().hour
    faixa_atual = f"{hora_atual//2*2:02d}-{(hora_atual//2*2)+1:02d}"

    # Volatilidade
    vol_atual = "baixa" if contexto_atual.get('volatility', 0) < 50 else "alta"
    vol_exp = "baixa" if exp_contexto.get('volatility', 0) < 50 else "alta"

    # RSI
    rsi_atual = contexto_atual.get('rsi_14', 50)
    rsi_exp = exp_contexto.get('rsi_14', 50)
    rsi_similar = abs(rsi_atual - rsi_exp) <= 20  # ÃÂ±20 pontos

    # Candle type
    candle_atual = contexto_atual.get('candle_type', '')
    candle_exp = exp_contexto.get('candle_type', '')

    return vol_atual == vol_exp and rsi_similar and candle_atual == candle_exp


def calcular_expectativa_simples(experiencias):
    """Calcula expectativa matemÃÂ¡tica simples."""
    if len(experiencias) < 5:  # MÃÂ­nimo de dados
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
    """VETO SIMPLES: Verifica se deve operar baseado no histÃÂ³rico."""
    experiencias = carregar_experiencias_simples()

    # Busca experiÃÂªncias similares com a mesma aÃÂ§ÃÂ£o
    similares = []
    for exp in experiencias:
        if (exp.get('acao') == acao_proposta and
                contexto_similar_simples(exp.get('contexto', {}), contexto_atual)):
            similares.append(exp)

    expectativa = calcular_expectativa_simples(similares)

    if expectativa is None:
        return True, "Sem histÃÂ³rico suficiente"

    if expectativa <= expectativa_minima:
        return False, f"Expectativa negativa: {expectativa:.2f} (similares: {len(similares)})"

    return True, f"Expectativa positiva: {expectativa:.2f} (similares: {len(similares)})"


# Alias para compatibilidade Ã¢â¬â prever_acao chama deve_operar_contexto_simples
deve_operar_contexto_simples = deve_operar_contexto


# ConfiguraÃÂ§ÃÂµes de Stop Inteligente - VALORES ORIGINAIS RESTAURADOS
INVERSAO_SCORE_MIN = 0.3       # MÃÂ­nima variaÃÂ§ÃÂ£o do score para considerar inversÃÂ£o
SCORE_LOCK_PROFIT = 0.5        # Score mÃÂ­nimo para ativar trava de lucro
TEMPO_MIN_POSICAO = 30         # Tempo mÃÂ­nimo em segundos antes de considerar saÃÂ­da
INTERVALO_CHECK_SCORE = 5      # Intervalo em segundos para checar score
JANELA_SUAVIZACAO = 3         # Tamanho da janela para mÃÂ©dia mÃÂ³vel do score
THRESHOLD_INVERSAO_SCORE = -0.2  # Threshold para considerar inversÃÂ£o negativa

# ConfiguraÃÂ§ÃÂµes de Trading
MULTIPLICADOR_SL_ATR = 2.0  # SL = 2x ATR
MULTIPLICADOR_TP_ATR = 3.0  # TP = 3x ATR
PERIODO_ATR = 14           # PerÃÂ­odo para cÃÂ¡lculo do ATR

# Limites mÃÂ¡ximos de SL/TP em pontos - ADAPTADO PARA WDO
SL_MAX_POINTS = 5         # MÃÂ¡ximo SL em pontos WDO
TP_MAX_POINTS = 0         # SEM TP Ã¢â¬â saÃÂ­da dinÃÂ¢mica por Keras+Book

# ConfiguraÃÂ§ÃÂµes de Modos Situacionais - ADAPTADO PARA WDO
# ATR mÃÂ­nimo para operar Ã¢â¬â WDO opera com ATR 2-10 pontos (tick=0.5)
# Abaixo de 1.5 = mercado completamente lateral, sem oportunidade
THRESHOLD_ATR_BAIXO = 1.5
# Entropia mÃÂ­nima para operar Ã¢â¬â escala REAL (entropy log natural) 2.69-2.97
# FIX (01/08/2026): era 0.6 em escala [0,1], mas entropia real ÃÂ© 2.7-3.0 -> modo lateral nunca ativava
THRESHOLD_ENTROPIA_BAIXA = 2.75
# Entropia alta para modo explosÃÂ£o - ULTRA SELETIVO (era 0.7, escala [0,1] -> explosÃÂ£o sempre ativa)
THRESHOLD_ENTROPIA_ALTA = 2.85
# MÃÂ­nimo crescimento de volume para modo explosÃÂ£o - MAIS EXIGENTE
MIN_VOLUME_CRESCIMENTO = 1.5
# MÃÂ¡ximo de losses seguidos antes de modo defesa
MAX_LOSSES_SEGUIDOS = 3   # Era 5 - reduzido para reagir mais rÃÂ¡pido
# Minutos em modo defesa apÃÂ³s atingir max losses
TEMPO_DEFESA = 10         # Era 15 - reduzido para nÃÂ£o travar demais
# RazÃÂ£o mÃÂ­nima entre bid/ask (WDO tem menos liquidez)
MIN_RATIO_BOOK = 0.03

# ConfiguraÃÂ§ÃÂµes de Bloqueio de Lado - VALORES ORIGINAIS RESTAURADOS
MAX_LOSSES_SEQUENCIA = 3     # MÃÂ¡ximo de losses seguidos no mesmo lado
CICLOS_BLOQUEIO = 5         # NÃÂºmero de ciclos que o lado fica bloqueado
MIN_LUCRO_DESBLOQUEIO = 0.0  # Lucro mÃÂ­nimo para desbloquear lado antes do tempo

# ========== CONFIGURAÃâ¡Ãâ¢ES MELHORIA 1: TRAILING STOP INTELIGENTE ==========
TRAILING_ATIVO = True
# pontos WDO Ã¢â¬â sÃÂ³ ativa apÃÂ³s lucro real (AJUSTE FINO: era 80/5, agora 8 para WDO - AÃÂ§ÃÂ£o 1 07/08)
TRAILING_GATILHO = 8
# pontos WDO Ã¢â¬â respira sem violinar (AJUSTE FINO: era 40/2, agora 4 para WDO - AÃÂ§ÃÂ£o 1 07/08)
TRAILING_DISTANCIA = 4
TRAILING_PERCENTUAL_TRAVA = 0.7  # Trava 70% do lucro quando > 5 pontos

# AÃÂ§ÃÂ£o 2 (07/08): piso mÃÂ­nimo de confianÃÂ§a para executar ordem
# EmpÃÂ­rico (simulaÃÂ§ÃÂ£o 07/08): conf < 0.50 concentra lixo; 0.50 corta
# parte das perdas sem matar os winners (0.60 anularia todos os trades).
PISO_CONFIANCA_MINIMA = 0.50

# InstÃÂ¢ncia global do trailing stop
trailing_stop = None

# ========== MELHORIA 2: BALANCEAMENTO BUY/SELL (+2% EFICÃÂCIA) ==========


class BalanceadorOperacoes:
    """Gerencia o balanceamento entre operaÃÂ§ÃÂµes BUY e SELL."""

    def __init__(self):
        self.contador_buy = 0
        self.contador_sell = 0
        self.historico_operacoes = []

    def registrar_operacao(self, acao: str):
        """Registra uma operaÃÂ§ÃÂ£o executada."""
        if acao == "BUY":
            self.contador_buy += 1
        elif acao == "SELL":
            self.contador_sell += 1

        self.historico_operacoes.append(acao)
        if len(self.historico_operacoes) > 50:  # MantÃÂ©m histÃÂ³rico limitado
            self.historico_operacoes.pop(0)

    def calcular_desbalanceamento(self) -> float:
        """Calcula o nÃÂ­vel de desbalanceamento atual."""
        total = self.contador_buy + self.contador_sell
        if total == 0:
            return 0.0
        return self.contador_buy / total

    def ajustar_threshold(self, threshold_original: float) -> float:
        """Ajusta o threshold baseado no desbalanceamento de forma mais agressiva."""
        desbalanceamento = self.calcular_desbalanceamento()
        total = self.contador_buy + self.contador_sell

        # NÃÂ£o ajusta se tiver poucas operaÃÂ§ÃÂµes
        if total < 5:
            return threshold_original

        # BALANCEAMENTO ULTRA AGRESSIVO
        # Se muito desbalanceado (>85%), ajuste extremo
        if desbalanceamento > 0.85:
            ajuste = 0.3  # Ajuste muito agressivo
            logging.info(
                f"Ã°Å¸Å¡Â¨ Desbalanceamento crÃÂ­tico BUY: {desbalanceamento:.1%} - Ajuste extremo +{ajuste}")
            # Pode ir atÃÂ© 1.5 (quase impossÃÂ­vel BUY)
            return min(1.5, threshold_original + ajuste)
        elif desbalanceamento < 0.15:
            ajuste = -0.3  # Ajuste muito agressivo
            logging.info(
                f"Ã°Å¸Å¡Â¨ Desbalanceamento crÃÂ­tico SELL: {desbalanceamento:.1%} - Ajuste extremo {ajuste}")
            # Pode ir atÃÂ© -0.5 (quase sempre BUY)
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
        """Verifica se deve forÃÂ§ar uma operaÃÂ§ÃÂ£o especÃÂ­fica devido ao desbalanceamento extremo."""
        desbalanceamento = self.calcular_desbalanceamento()
        total = self.contador_buy + self.contador_sell

        if total < 10:  # Precisa de pelo menos 10 operaÃÂ§ÃÂµes para forÃÂ§ar
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


# ConfiguraÃÂ§ÃÂµes do balanceamento
BALANCEAMENTO_ATIVO = False  # DESATIVADO: causava deadlock (forÃÂ§a BUY com threshold=2.0 impossÃÂ­vel)
THRESHOLD_DESBALANCEAMENTO = 0.7  # 70% de um lado
AJUSTE_THRESHOLD_BALANCE = 0.05   # Ajuste no threshold quando desbalanceado

# InstÃÂ¢ncia global do balanceador
balanceador = None

# ========== MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS (+2% EFICÃÂCIA) ==========


class DetectorModoMercado:
    """Detecta e gerencia modos de mercado simplificados."""

    def __init__(self):
        self.modo_atual = "NORMAL"
        self.historico_atr = []
        self.historico_entropia = []

    def atualizar_indicadores(self, atr: float, entropia: float):
        """Atualiza indicadores para detecÃÂ§ÃÂ£o de modo."""
        self.historico_atr.append(atr)
        self.historico_entropia.append(entropia)

        # MantÃÂ©m histÃÂ³rico limitado
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
        # WDO: ATR tÃÂ­pico 2-10 pontos. Abaixo de 2.0 = conservador.
        # FIX (01/08/2026): entropia em escala real (2.69-2.97), era 0.3 em [0,1] -> nunca ativava
        if atr_medio < 2.0 and entropia_media < 2.75:
            self.modo_atual = "CONSERVADOR"
        else:
            self.modo_atual = "NORMAL"

        return self.modo_atual

    def ajustar_parametros_trading(self, volume_base: float, sl_base: float, tp_base: float) -> tuple:
        """Ajusta parÃÂ¢metros de trading baseado no modo."""
        if self.modo_atual == "CONSERVADOR":
            volume_ajustado = volume_base * 0.5  # Volume reduzido 50%
            sl_ajustado = sl_base * 0.7         # SL menor 30%
            tp_ajustado = tp_base * 0.8         # TP menor 20%
            return volume_ajustado, sl_ajustado, tp_ajustado

        return volume_base, sl_base, tp_base


# InstÃÂ¢ncia global do detector de modo
detector_modo = None

# ========== MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS (+1.5% EFICÃÂCIA) ==========


class CircuitBreakerEssencial:
    """Implementa circuit breakers essenciais para proteÃÂ§ÃÂ£o."""

    def __init__(self):
        self.losses_seguidos = 0
        self.loss_diario_atual = 0.0
        self.operacoes_hoje = []
        self.bloqueado = False
        self.motivo_bloqueio = ""

    def registrar_resultado(self, lucro: float):
        """Registra resultado de uma operaÃÂ§ÃÂ£o."""
        hoje = datetime.now().date()
        self.operacoes_hoje.append((hoje, lucro))

        # Remove operaÃÂ§ÃÂµes de dias anteriores
        self.operacoes_hoje = [(data, valor) for data,
                               valor in self.operacoes_hoje if data == hoje]

        # Atualiza loss diÃÂ¡rio
        self.loss_diario_atual = sum(valor for _, valor in self.operacoes_hoje)

        # Atualiza losses seguidos
        if lucro < -25.0:  # Loss significativo (WDO)
            self.losses_seguidos += 1
        else:
            self.losses_seguidos = 0

        # LIMITE DIÃÂRIO REAL: Se atingiu -1000, DESLIGA O ROBÃâ
        if self.loss_diario_atual <= MAX_LOSS_DIARIO:
            self.bloqueado = True
            self.motivo_bloqueio = f"LIMITE DIÃÂRIO ATINGIDO: {self.loss_diario_atual:.2f} <= {MAX_LOSS_DIARIO}"
            logging.error(f"Ã°Å¸Å¡Â¨ {self.motivo_bloqueio}")
            logging.error("Ã°Å¸âºâ ROBÃâ SERÃÂ DESLIGADO AUTOMATICAMENTE!")

            # FIX (01/08/2026): era sys.exit() dentro de thread daemon -> so matava a thread,
            # dashboard e demais threads continuavam vivas (processo parecia ativo). Agora cria
            # parar.txt (caminho absoluto), que o loop principal detecta via verificar_parada_gracil
            # e executa o shutdown coordenado (fecha posicoes, salva modelo/experiencias, os._exit).
            try:
                with open(_caminho_dados("parar.txt"), 'w', encoding='utf-8') as f:
                    f.write(f"LIMITE DIARIO ATINGIDO: {self.loss_diario_atual:.2f}")
                logging.info("Ã¢Åâ¦ parar.txt criado - encerramento coordenado sera executado pelo loop principal")
            except Exception as e:
                logging.error(f"Ã¢ÂÅ Erro ao criar parar.txt: {e}")

    def verificar_circuit_breakers(self, spread_atual: float, ignore_max_loss: bool = False) -> bool:
        """Verifica se algum circuit breaker foi ativado."""
        # CB1: 3 losses seguidos - TEMPORARIAMENTE DESABILITADO (30/07/2025)
        # MOTIVO: Permitir mais operaÃÂ§ÃÂµes para treinamento da IA
        # REATIVAR EM: 06/08/2025 (apÃÂ³s 1 semana de dados)
        # if self.losses_seguidos >= 3:
        #     self.bloqueado = True
        #     self.motivo_bloqueio = f"3 losses seguidos (atual: {self.losses_seguidos})"
        #     return True

        # CB2: Loss diÃÂ¡rio excessivo (WDO)
        if not ignore_max_loss and self.loss_diario_atual <= -1000.0:
            self.bloqueado = True
            self.motivo_bloqueio = f"Loss diÃÂ¡rio: R${self.loss_diario_atual:.2f}"
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


# ConfiguraÃÂ§ÃÂµes dos circuit breakers
CIRCUIT_BREAKER_ATIVO = True
# Stop apÃÂ³s 3 losses seguidos - TEMPORARIAMENTE DESABILITADO
MAX_LOSSES_SEGUIDOS_CB = 3
SPREAD_MAXIMO_CB = 20        # Stop se spread > 20 pontos WDO
# Stop se perda diÃÂ¡ria > R$1000 (WDO)
LOSS_DIARIO_CB = -1000.0

# InstÃÂ¢ncia global do circuit breaker
circuit_breaker = None

# InstÃÂ¢ncia global do sistema de confluÃÂªncia
sistema_confluencia = None
confluencia_info_atual = None

# ========== NOVA MELHORIA: SISTEMA DE CONFLUÃÅ NCIA (+4% EFICÃÂCIA) ==========


class SistemaConfluencia:
    """Sistema que sÃÂ³ opera quando mÃÂºltiplos sinais concordam - MÃÂXIMA EFICÃÂCIA."""

    def __init__(self):
        self.historico_confluencias = []
        self.stats_por_confluencia = {}

    def verificar_confluencia(self, contexto: Dict[str, Any], probabilidade_ia: float, acao_ia: str) -> Dict[str, Any]:
        """Verifica confluÃÂªncia de mÃÂºltiplos sinais tÃÂ©cnicos."""
        sinais_buy = []
        sinais_sell = []
        score_confluencia = 0

        # ===== SINAL 1: INTELIGÃÅ NCIA ARTIFICIAL (Peso: 30) ==========
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

            # LÃâGICA CORRIGIDA: SEGUIR BIG PLAYERS NA MESMA DIREÃâ¡ÃÆO
            if ratio_book > 1.3:  # Muito mais compradores (bid_qty > ask_qty)
                # BUY (big players comprando Ã¢â â entrar junto na compra)
                sinais_buy.append("BOOK_DESEQUILIBRIO")
                score_confluencia += 25
            elif ratio_book > 1.15:  # Moderadamente mais compradores
                # BUY (pressÃÂ£o de compra moderada)
                sinais_buy.append("BOOK_LEVE")
                score_confluencia += 15
            # Muito mais vendedores (ask_qty > bid_qty)
            elif ratio_book < 0.77:
                # SELL (big players vendendo Ã¢â â entrar junto na venda)
                sinais_sell.append("BOOK_DESEQUILIBRIO")
                score_confluencia += 25
            elif ratio_book < 0.87:  # Moderadamente mais vendedores
                # SELL (pressÃÂ£o de venda moderada)
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

        # ========== SINAL 4: PADRÃÆO DE CANDLESTICK (Peso: 15) ==========
        candle_type = contexto.get('candle_type', '')

        # PadrÃÂµes de reversÃÂ£o de baixa (sinal de compra)
        padroes_compra = ['hammer_baixa', 'doji_baixa',
                          'spinning_top_baixa', 'lower_shadow_baixa']
        if candle_type in padroes_compra:
            sinais_buy.append("CANDLE_REVERSAO")
            score_confluencia += 15

        # PadrÃÂµes de reversÃÂ£o de alta (sinal de venda)
        padroes_venda = ['shooting_star_alta', 'doji_alta',
                         'spinning_top_alta', 'upper_shadow_alta']
        if candle_type in padroes_venda:
            sinais_sell.append("CANDLE_REVERSAO")
            score_confluencia += 15

        # PadrÃÂµes de continuaÃÂ§ÃÂ£o
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

        # ========== DECISÃÆO FINAL DE CONFLUÃÅ NCIA (REFATORADO) ==========
        total_sinais_buy = len(sinais_buy)
        total_sinais_sell = len(sinais_sell)

        # Ã°Å¸Å½Â¯ REGRA 1: IA COM ALTA CONFIANÃâ¡A (>80%) NÃÆO PODE SER INVERTIDA
        # NOTA: probabilidade_ia=0.0 (modelo nÃÂ£o treinado) NÃÆO ÃÂ© confianÃÂ§a alta
        ia_confianca_alta = (probabilidade_ia > 0.8 or probabilidade_ia < 0.2) and probabilidade_ia != 0.0

        if ia_confianca_alta:
            # IA tem alta confianÃÂ§a - ConfluÃÂªncia sÃÂ³ pode CONFIRMAR, nÃÂ£o inverter
            if probabilidade_ia > 0.8:
                acao_confluencia = "BUY"
                confianca_confluencia = min(
                    probabilidade_ia + (score_confluencia / 200.0), 1.0)
                logging.debug(
                    f"Ã°Å¸ââ IA ALTA CONFIANÃâ¡A (BUY): {probabilidade_ia:.2f} - ConfluÃÂªncia nÃÂ£o pode inverter")
            else:  # probabilidade_ia < 0.2
                acao_confluencia = "SELL"
                confianca_confluencia = min(
                    (1 - probabilidade_ia) + (score_confluencia / 200.0), 1.0)
                logging.debug(
                    f"Ã°Å¸ââ IA ALTA CONFIANÃâ¡A (SELL): {1-probabilidade_ia:.2f} - ConfluÃÂªncia nÃÂ£o pode inverter")
        else:
            # Ã°Å¸Å½Â¯ REGRA 2: CONFLUÃÅ NCIA EXIGE MÃÂNIMO 2 SINAIS TÃâ°CNICOS PARA VALIDAR ENTRADA
            if total_sinais_buy >= 2 and total_sinais_buy > total_sinais_sell:
                acao_confluencia = "BUY"
                confianca_confluencia = min(score_confluencia / 100.0, 1.0)
            elif total_sinais_sell >= 2 and total_sinais_sell > total_sinais_buy:
                acao_confluencia = "SELL"
                confianca_confluencia = min(score_confluencia / 100.0, 1.0)
            else:
                # FALLBACK: Menos de 2 sinais tÃÂ©cnicos - NÃÆO OPERAR
                acao_confluencia = "NADA"
                confianca_confluencia = 0.0
                logging.warning(
                    f"Ã¢Å¡Â Ã¯Â¸Â CONFLUÃÅ NCIA INSUFICIENTE: BUY={total_sinais_buy}, SELL={total_sinais_sell} (mÃÂ­nimo 2 sinais)")

        # Registra estatÃÂ­sticas
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
        """Registra resultado de uma operaÃÂ§ÃÂ£o baseada em confluÃÂªncia."""
        if confluencia_info["acao"] in ["BUY", "SELL"]:
            key = f"{confluencia_info['total_sinais_buy']}B_{confluencia_info['total_sinais_sell']}S"

            if key in self.stats_por_confluencia:
                self.stats_por_confluencia[key]["total"] += 1
                if lucro > 0.0:  # CORREÃâ¡ÃÆO C9: Conta apenas experiÃÂªncias lucrativas
                    self.stats_por_confluencia[key]["acertos"] += 1

    def get_stats_confluencia(self) -> Dict:
        """Retorna estatÃÂ­sticas de performance por tipo de confluÃÂªncia."""
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


# ========== MELHORIA 5: SAÃÂDA INTELIGENTE DE POSIÃâ¡ÃÆO (+1.5% EFICÃÂCIA) ==========


class SaidaInteligentePositions:
    """Gerencia saÃÂ­da inteligente de posiÃÂ§ÃÂµes."""

    def __init__(self):
        self.posicoes_monitoradas = {}
        self.historico_rsi = []

    def iniciar_monitoramento(self, ticket: int, tipo: str, preco_entrada: float):
        """Inicia monitoramento de uma posiÃÂ§ÃÂ£o."""
        self.posicoes_monitoradas[ticket] = {
            "tipo": tipo,
            "preco_entrada": preco_entrada,
            "tempo_inicio": time.time(),
            "melhor_lucro": 0.0,
            "tempo_sem_lucro": 0,
            "rsi_entrada": self.historico_rsi[-1] if self.historico_rsi else 50.0
        }

    def atualizar_rsi(self, rsi_atual: float):
        """Atualiza histÃÂ³rico de RSI."""
        self.historico_rsi.append(rsi_atual)
        if len(self.historico_rsi) > 10:
            self.historico_rsi.pop(0)

    def verificar_saida_inteligente(self, ticket: int, preco_atual: float, rsi_atual: float) -> bool:
        """Verifica se deve sair da posiÃÂ§ÃÂ£o inteligentemente."""
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

        # CRITÃâ°RIO 1: 5 minutos sem lucro
        if posicao["tempo_sem_lucro"] >= 300:  # 300 segundos = 5 minutos
            logging.info(
                f"Ã°Å¸Å¡Âª SaÃÂ­da por tempo sem lucro: {posicao['tempo_sem_lucro']:.0f}s")
            return True

        # CRITÃâ°RIO 2: RSI inverteu com lucro mÃÂ­nimo (5 pontos WDO)
        if lucro_atual >= 5.0:  # Lucro mÃÂ­nimo para considerar saÃÂ­da por RSI
            rsi_entrada = posicao["rsi_entrada"]

            # Para posiÃÂ§ÃÂ£o BUY: sair se RSI estava baixo e agora estÃÂ¡ alto
            if posicao["tipo"] == "BUY" and rsi_entrada < 30 and rsi_atual > 70:
                logging.info(
                    f"Ã°Å¸Å¡Âª SaÃÂ­da BUY por inversÃÂ£o RSI: {rsi_entrada:.1f} Ã¢â â {rsi_atual:.1f}")
                return True

            # Para posiÃÂ§ÃÂ£o SELL: sair se RSI estava alto e agora estÃÂ¡ baixo
            if posicao["tipo"] == "SELL" and rsi_entrada > 70 and rsi_atual < 30:
                logging.info(
                    f"Ã°Å¸Å¡Âª SaÃÂ­da SELL por inversÃÂ£o RSI: {rsi_entrada:.1f} Ã¢â â {rsi_atual:.1f}")
                return True

        return False

    def finalizar_monitoramento(self, ticket: int):
        """Finaliza monitoramento de uma posiÃÂ§ÃÂ£o."""
        if ticket in self.posicoes_monitoradas:
            del self.posicoes_monitoradas[ticket]


# ConfiguraÃÂ§ÃÂµes da saÃÂ­da inteligente
SAIDA_INTELIGENTE_ATIVA = True
TEMPO_MAX_SEM_LUCRO = 300    # 5 minutos sem lucro = sair
RSI_INVERSAO_SAIDA = True    # Sair se RSI inverter com lucro
MIN_LUCRO_SAIDA_RSI = 5.0    # Lucro mÃÂ­nimo para considerar saÃÂ­da por RSI

# InstÃÂ¢ncia global da saÃÂ­da inteligente
saida_inteligente = None

# ========== MELHORIA 6: FILTRO DE HORÃÂRIO PREMIUM (+2% EFICÃÂCIA) ==========


class FiltroHorarioPremium:
    """Filtra operaÃÂ§ÃÂµes para horÃÂ¡rios de maior liquidez e volatilidade."""

    def __init__(self):
        # HorÃÂ¡rios de maior liquidez WDO (UTC-3)
        self.horarios_premium = [
            (dtime(9, 0), dtime(12, 30)),   # Abertura - alta volatilidade
            # Meio perÃÂ­odo - movimento institucional
            (dtime(14, 0), dtime(15, 30)),
            (dtime(17, 0), dtime(17, 30))   # Fechamento - ajustes finais
        ]

    def is_horario_premium(self) -> bool:
        """Verifica se estÃÂ¡ em horÃÂ¡rio premium para trading."""
        agora = datetime.now().time()

        for inicio, fim in self.horarios_premium:
            if inicio <= agora <= fim:
                return True
        return False

    def get_status(self) -> dict:
        """Retorna status do filtro de horÃÂ¡rio."""
        return {
            "horario_premium": self.is_horario_premium(),
            "horario_atual": datetime.now().strftime("%H:%M:%S"),
            "proximos_horarios": ["09:15-12:30", "14:30-17:15"]
        }


# ConfiguraÃÂ§ÃÂµes do filtro de horÃÂ¡rio
# Desativado temporariamente para operar em todos os horÃÂ¡rios
FILTRO_HORARIO_ATIVO = False

# InstÃÂ¢ncia global do filtro de horÃÂ¡rio
filtro_horario = None

# ========== SCALER GLOBAL PARA NORMALIZAÃâ¡ÃÆO CONSISTENTE ==========
scaler_global = None

# ForÃÂ§a recriaÃÂ§ÃÂ£o do scaler para compatibilidade com 22 features


def resetar_scaler_global():
    """ForÃÂ§a recriaÃÂ§ÃÂ£o do scaler global para evitar problemas de compatibilidade."""
    global scaler_global
    scaler_global = None
    logging.info(
        f"Ã°Å¸ââ Scaler global resetado para compatibilidade com {N_FEATURES} features")


def forcar_recreacao_scaler():
    """Tenta carregar scaler salvo pelo treinamento offline; se nÃÂ£o existir, cria com dummy."""
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
                f"Ã¢Åâ¦ Scaler carregado do treinamento offline: {scaler_path}")
            return
        except Exception as e:
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â Erro ao carregar scaler salvo ({e}), criando com dummy")

    dados_dummy = np.random.random((5, N_FEATURES))
    scaler_global = MinMaxScaler()
    scaler_global.fit(dados_dummy)
    logging.info(
        f"Ã°Å¸âÂ§ Scaler global recriado com {N_FEATURES} features usando dados dummy")

# ========== MELHORIA 7: DETECTOR DE TENDÃÅ NCIA SIMPLES (+3% EFICÃÂCIA) ==========


class DetectorTendencia:
    """Detecta tendÃÂªncia usando EMAs para viÃÂ©s direcional."""

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
        """Atualiza cÃÂ¡lculo de tendÃÂªncia com novo preÃÂ§o."""
        self.ema9_values.append(preco_fechamento)
        self.ema21_values.append(preco_fechamento)

        # MantÃÂ©m histÃÂ³rico limitado
        if len(self.ema9_values) > 50:
            self.ema9_values.pop(0)
        if len(self.ema21_values) > 50:
            self.ema21_values.pop(0)

        # Calcula EMAs
        if len(self.ema9_values) >= 9 and len(self.ema21_values) >= 21:
            ema9 = self.calcular_ema(self.ema9_values, 9)
            ema21 = self.calcular_ema(self.ema21_values, 21)

            # Define tendÃÂªncia
            if ema9 > ema21:
                self.tendencia_atual = "ALTA"
            elif ema9 < ema21:
                self.tendencia_atual = "BAIXA"
            else:
                self.tendencia_atual = "NEUTRO"

    def pode_operar(self, acao: str) -> bool:
        """Verifica se pode operar na direÃÂ§ÃÂ£o baseado na tendÃÂªncia."""
        if self.tendencia_atual == "NEUTRO":
            return True  # Permite ambas direÃÂ§ÃÂµes
        elif self.tendencia_atual == "ALTA" and acao == "BUY":
            return True  # BUY a favor da tendÃÂªncia
        elif self.tendencia_atual == "BAIXA" and acao == "SELL":
            return True  # SELL a favor da tendÃÂªncia
        else:
            return False  # Contra a tendÃÂªncia

    def get_status(self) -> dict:
        """Retorna status da tendÃÂªncia."""
        return {
            "tendencia": self.tendencia_atual,
            "ema9": self.ema9_values[-1] if self.ema9_values else 0,
            "ema21": self.ema21_values[-1] if self.ema21_values else 0
        }


# ConfiguraÃÂ§ÃÂµes do detector de tendÃÂªncia
DETECTOR_TENDENCIA_ATIVO = True

# InstÃÂ¢ncia global do detector de tendÃÂªncia
detector_tendencia = None

# ========== SISTEMA DE VOLUME INTELIGENTE BASEADO NO BOOK ==========


def calcular_volume_inteligente(volume_book_total: float) -> float:
    """Calcula volume adaptativo baseado na liquidez do book (ajustado para WDO).
    WDO: 1 contrato padrÃÂ£o. SÃÂ³ aumenta se liquidez MUITO alta."""
    if volume_book_total >= 5000:   # LIQUIDEZ EXTREMA
        return 2.0   # No mÃÂ¡ximo 2 contratos
    elif volume_book_total >= 3000: # ALTA LIQUIDEZ WDO
        return 1.5
    else:  # NORMAL
        return 1.0   # PadrÃÂ£o: 1 contrato

# ========== MELHORIA 8: SISTEMA DE COOLDOWN INTELIGENTE (+1.5% EFICÃÂCIA) ==========


class CooldownInteligente:
    """Gerencia cooldown entre operaÃÂ§ÃÂµes para evitar overtrading."""

    def __init__(self):
        self.ultima_operacao = 0
        self.losses_seguidos = 0
        self.cooldown_ativo = False
        self.fim_cooldown = 0

    def registrar_resultado(self, lucro: float):
        """Registra resultado e define cooldown necessÃÂ¡rio."""
        self.ultima_operacao = time.time()

        if lucro <= -25.0:  # Loss significativo (<= R$25)
            self.losses_seguidos += 1

            # Ã¢Åâ¦ TRAVA PÃâS-LOSS: mÃÂ­nimo 180s independente de qualquer sinal "premium"
            if self.losses_seguidos == 1:
                # 5 min apÃÂ³s 1 loss (>= 180s obrigatÃÂ³rio)
                cooldown_segundos = 300
            elif self.losses_seguidos == 2:
                cooldown_segundos = 600   # 10 min apÃÂ³s 2 losses
            else:
                cooldown_segundos = 900   # 15 min apÃÂ³s 3+ losses

            # Garantia: nunca menos de 180s apÃÂ³s qualquer loss
            cooldown_segundos = max(cooldown_segundos, 180)

            self.cooldown_ativo = True
            self.fim_cooldown = time.time() + cooldown_segundos

            logging.warning(
                f"Ã°Å¸ââ TRAVA PÃâS-LOSS: {cooldown_segundos}s bloqueado apÃÂ³s {self.losses_seguidos} loss(es) | "
                f"Nenhum sinal pode ultrapassar esta trava!")

        else:  # Win ou break-even
            self.losses_seguidos = 0
            # COOLDOWN GERAL: 4 minutos entre TODAS as operaÃÂ§ÃÂµes (mesmo apÃÂ³s win)
            cooldown_segundos = 240  # 4 minutos para reduzir overtrading
            self.cooldown_ativo = True
            self.fim_cooldown = time.time() + cooldown_segundos
            logging.info(
                f"Ã¢ÂÂ³ Cooldown geral ativado: {cooldown_segundos}s para reduzir overtrading")

    def pode_operar(self) -> bool:
        """Verifica se pode operar (nÃÂ£o estÃÂ¡ em cooldown)."""
        if not self.cooldown_ativo:
            return True

        if time.time() >= self.fim_cooldown:
            self.cooldown_ativo = False
            logging.info("Ã¢Åâ¦ Cooldown finalizado - Pode operar novamente")
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


# ConfiguraÃÂ§ÃÂµes do cooldown
# Ã¢Åâ¦ REATIVADO (23/07/2026): trade entrou 2s apÃÂ³s prejuÃÂ­zo Ã¢â¬â precisa de trava.
# Cooldown: 5min apÃÂ³s 1 loss, 10min apÃÂ³s 2 losses, 15min apÃÂ³s 3+ losses.
# MÃÂ­nimo 180s apÃÂ³s qualquer loss.
COOLDOWN_ATIVO = False  # DESATIVADO por solicitaÃÂ§ÃÂ£o do operador Ã¢â¬â cooldown sÃÂ³ atrasava reentrada
COOLDOWN_LOSS_1 = 300   # 5 minutos apÃÂ³s 1 loss
COOLDOWN_LOSS_2 = 600   # 10 minutos apÃÂ³s 2 losses
COOLDOWN_LOSS_3 = 900   # 15 minutos apÃÂ³s 3+ losses

# InstÃÂ¢ncia global do cooldown
cooldown_sistema = None

# ========== MELHORIA 9: FILTRO DE SPREAD DINÃâMICO (+1% EFICÃÂCIA) ==========


class FiltroSpreadDinamico:
    """Ajusta spread mÃÂ¡ximo baseado na volatilidade do mercado."""

    def __init__(self):
        self.historico_atr = []
        self.spread_maximo_atual = MAX_SPREAD

    def atualizar_atr(self, atr_atual: float):
        """Atualiza histÃÂ³rico de ATR para cÃÂ¡lculo dinÃÂ¢mico."""
        self.historico_atr.append(atr_atual)
        if len(self.historico_atr) > 20:
            self.historico_atr.pop(0)

        # Calcula spread dinÃÂ¢mico baseado na volatilidade
        if len(self.historico_atr) >= 5:
            atr_medio = sum(self.historico_atr[-5:]) / 5

            # Spread dinÃÂ¢mico baseado no ATR
            if atr_medio < 200:  # ATR baixo - mercado calmo
                self.spread_maximo_atual = 5
            elif atr_medio < 400:  # ATR mÃÂ©dio
                self.spread_maximo_atual = 10
            else:  # ATR alto - mercado volÃÂ¡til
                self.spread_maximo_atual = 20

    def spread_aceitavel(self, spread_atual: float) -> bool:
        """Verifica se spread estÃÂ¡ dentro do limite dinÃÂ¢mico."""
        return spread_atual <= self.spread_maximo_atual

    def get_status(self) -> dict:
        """Retorna status do filtro de spread."""
        atr_atual = self.historico_atr[-1] if self.historico_atr else 0
        return {
            "spread_maximo": self.spread_maximo_atual,
            "atr_atual": atr_atual,
            "volatilidade": "BAIXA" if atr_atual < 200 else "MÃâ°DIA" if atr_atual < 400 else "ALTA"
        }


# ConfiguraÃÂ§ÃÂµes do spread dinÃÂ¢mico
SPREAD_DINAMICO_ATIVO = True
SPREAD_ATR_BAIXO = 5    # Spread mÃÂ¡x quando ATR < 200
SPREAD_ATR_MEDIO = 10   # Spread mÃÂ¡x quando ATR 200-400
SPREAD_ATR_ALTO = 20    # Spread mÃÂ¡x quando ATR > 400

# InstÃÂ¢ncia global do filtro de spread
filtro_spread = None

# ========== MELHORIA 10: MONITORAMENTO DE PERFORMANCE EM TEMPO REAL (+2% EFICÃÂCIA) ==========


class MonitorPerformance:
    """Monitora performance em tempo real com alertas inteligentes."""

    def __init__(self):
        self.operacoes_recentes = []  # ÃÅ¡ltimas 10 operaÃÂ§ÃÂµes
        self.drawdown_atual = 0.0
        self.drawdown_maximo = 0.0
        self.pico_capital = 0.0
        self.performance_por_modo = {
            "NORMAL": {"wins": 0, "losses": 0, "lucro_total": 0.0},
            "EXPLOSAO": {"wins": 0, "losses": 0, "lucro_total": 0.0},
            "LATERAL": {"wins": 0, "losses": 0, "lucro_total": 0.0}
        }

    def registrar_operacao(self, lucro: float, modo: str):
        """Registra operaÃÂ§ÃÂ£o e atualiza mÃÂ©tricas."""
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
        """Calcula taxa de acerto das ÃÂºltimas operaÃÂ§ÃÂµes."""
        if not self.operacoes_recentes:
            return 0.0
        wins = sum(1 for op in self.operacoes_recentes if op > 0)
        return (wins / len(self.operacoes_recentes)) * 100

    def verificar_alertas(self) -> list:
        """VerdiÃÂ§ÃÂµes de alerta."""
        alertas = []

        # Alerta: Taxa de acerto baixa
        taxa_acerto = self.taxa_acerto_recente()
        if len(self.operacoes_recentes) >= 5 and taxa_acerto < 30:
            alertas.append(f"Ã°Å¸Å¡Â¨ Taxa de acerto baixa: {taxa_acerto:.1f}%")

        return alertas


# ========== NOVAS CLASSES IMPLEMENTADAS (IMPLEMENTE.TXT) ==========


class GerenciadorDeSaida:
    """
    Unifica e gerencia todas as lÃÂ³gicas de saÃÂ­da de uma posiÃÂ§ÃÂ£o:
    - Trailing Stop Inteligente
    - Timeout sem evoluÃÂ§ÃÂ£o
    - ProteÃÂ§ÃÂ£o de lucro (Drawdown do Pico)
    - SaÃÂ­da por estagnaÃÂ§ÃÂ£o
    - SaÃÂ­da por inversÃÂ£o de RSI
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
        """Inicia o monitoramento de uma nova posiÃÂ§ÃÂ£o."""
        self.posicao_monitorada = posicao_mt5.ticket
        self.preco_entrada = posicao_mt5.price_open
        self.melhor_preco = self.preco_entrada
        self.lucro_maximo_pontos = 0.0
        self.tempo_inicio = time.time()
        self.tipo_posicao = "BUY" if posicao_mt5.type == mt5.POSITION_TYPE_BUY else "SELL"
        logging.info(
            f"Ã°Å¸âºÂ¡Ã¯Â¸Â Gerenciador de SaÃÂ­da ATIVADO para posiÃÂ§ÃÂ£o #{self.posicao_monitorada}")

    def finalizar_monitoramento(self):
        """Reseta o estado do gerenciador."""
        self.posicao_monitorada = None
        logging.info("Ã°Å¸âºÂ¡Ã¯Â¸Â Gerenciador de SaÃÂ­da DESATIVADO.")

    def verificar_condicoes_saida(self, preco_atual: float, rsi_atual: float) -> Tuple[bool, str, Optional[float]]:
        """
        Verifica todas as regras de saÃÂ­da e retorna uma decisÃÂ£o.
        Retorna: (deve_sair, motivo, novo_sl_se_aplicavel)
        """
        if not self.posicao_monitorada:
            return False, "", None

        # --- CÃÂ¡lculos Iniciais ---
        tempo_em_posicao = time.time() - self.tempo_inicio
        lucro_em_pontos = 0.0
        # CORREÃâ¡ÃÆO: lucro em PONTOS REAIS (nÃÂ£o ticks)
        # 1 ponto WDO = 10 ticks (preÃÂ§o muda de 0.5 em 0.5)
        # DiferenÃÂ§a de preÃÂ§o / 1.0 = pontos reais

        if self.tipo_posicao == "BUY":
            # PONTOS REAIS (nÃÂ£o divide por tick)
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

        # --- VerificaÃÂ§ÃÂ£o das Regras de SAÃÂDA (Ordem de Prioridade) ---

        # Ã¢ÂÅ REGRA 1 (Timeout) e REGRA 3 (EstagnaÃÂ§ÃÂ£o) DESATIVADAS (17/07/2026,
        # decisÃÂ£o do mestre super): com entrada Sniper (ratio 2.0) + veto "seguir os
        # bigs", a posiÃÂ§ÃÂ£o deve respirar atÃÂ© o alvo natural. Quem tira do trade agora ÃÂ©:
        #   Ã¢â¬Â¢ SL fixo de 5pts (proteÃÂ§ÃÂ£o WDO)
        #   Ã¢â¬Â¢ TP dinÃÂ¢mico (Keras decide saÃÂ­da)
        #   Ã¢â¬Â¢ Trailing Stop (REGRA 4, abaixo)
        #   Ã¢â¬Â¢ InversÃÂ£o de fluxo (big players viram contra Ã¢â â sai no loop principal)
        # Timers arbitrÃÂ¡rios de tempo NÃÆO fecham mais a posiÃÂ§ÃÂ£o.

        # REGRA 2: ProteÃÂ§ÃÂ£o de lucro Ã¢â¬â sÃÂ³ ativa apÃÂ³s 10pts (WDO sem TP)
        # Com TP=0, precisa de mais espaÃÂ§o: trailing gatilho ÃÂ© 80pts, entÃÂ£o
        # proteÃÂ§ÃÂ£o sÃÂ³ corta se pico > 10pts E caiu > 50% do pico.
        # AlÃÂ©m disso, sÃÂ³ ativa apÃÂ³s 30s para evitar falsos positivos no inÃÂ­cio.
        if tempo_em_posicao > 30 and self.lucro_maximo_pontos > 10 and \
           lucro_em_pontos < self.lucro_maximo_pontos * 0.50:
            return True, f"C12: ProteÃÂ§ÃÂ£o de Lucro (caiu de {self.lucro_maximo_pontos:.1f}pts - 50% do pico, TP=0)", None

        # --- VerificaÃÂ§ÃÂ£o das Regras de AJUSTE (Trailing Stop) ---

        # REGRA 4: Trailing Stop (C12 - Mais agressivo)
        # Ativa Trailing mais cedo (15pts) e mantÃÂ©m distÃÂ¢ncia de 5pts (era 10pts)
        # REGRA 4: Trailing Stop Ã¢â¬â usa config calibrado para TP=250pts
        # Gatilho: 80pts | DistÃÂ¢ncia: 40pts (em PONTOS REAIS de preÃÂ§o)
        # REGRA 4: Trailing Stop Ã¢â¬â usa preÃÂ§o ATUAL para garantir SL vÃÂ¡lido
        # (melhor_preco pode estar acima do preÃÂ§o atual, gerando SL acima do bid Ã¢â â MT5 rejeita)
        if lucro_em_pontos >= self.config['trailing_gatilho_pts']:
            novo_sl = 0.0
            distancia_trailing_preco = self.config['trailing_distancia_pts']

            if self.tipo_posicao == "BUY":
                # SL fica ABAIXO do preÃÂ§o atual (nunca acima do bid)
                novo_sl = preco_atual - distancia_trailing_preco
            else:  # SELL
                # SL fica ACIMA do preÃÂ§o atual (nunca abaixo do ask)
                novo_sl = preco_atual + distancia_trailing_preco

            # VALIDAÃâ¡ÃÆO CRÃÂTICA: Garantir que o novo SL ÃÂ© uma melhoria real
            posicao_mt5_info = mt5.positions_get(
                ticket=self.posicao_monitorada)

            if posicao_mt5_info and len(posicao_mt5_info) > 0:
                sl_atual = posicao_mt5_info[0].sl

                # Para BUY, SL deve ser maior que o atual (subindo)
                if self.tipo_posicao == "BUY" and novo_sl > sl_atual:
                    logging.info(
                        f"Ã°Å¸âÂ§ DecisÃÂ£o de Ajuste BUY: Novo SL {novo_sl:.2f} (Melhoria de {sl_atual:.2f})")
                    return False, "Ajuste de Trailing Stop", novo_sl

                # Para SELL, SL deve ser menor que o atual (descendo)
                elif self.tipo_posicao == "SELL" and novo_sl < sl_atual:
                    logging.info(
                        f"Ã°Å¸âÂ§ DecisÃÂ£o de Ajuste SELL: Novo SL {novo_sl:.2f} (Melhoria de {sl_atual:.2f})")
                    return False, "Ajuste de Trailing Stop", novo_sl

                else:
                    logging.debug(
                        f"Ã°Å¸âÂ§ Trailing Stop nÃÂ£o aplicado: {novo_sl:.2f} nÃÂ£o ÃÂ© melhoria do atual {sl_atual:.2f}")

            # Se nÃÂ£o conseguiu validar ou nÃÂ£o ÃÂ© melhoria, nÃÂ£o ajusta
            return False, "Manter PosiÃÂ§ÃÂ£o", None

        return False, "Manter PosiÃÂ§ÃÂ£o", None


class VolumeAdaptativo:
    """Calcula um volume mÃÂ­nimo para operar de forma adaptativa."""

    def __init__(self, janela_minutos=15, percentual_da_media=0.8):
        self.janela_segundos = janela_minutos * 60
        self.percentual_da_media = percentual_da_media
        # Deque armazena (timestamp, volume)
        self.historico_volumes = collections.deque()
        self.volume_minimo_adaptativo = 500  # Valor inicial padrÃÂ£o (WDO)

    def adicionar_volume_atual(self, volume_total: float):
        """Adiciona o volume total do book ao histÃÂ³rico."""
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
        """Calcula o novo volume mÃÂ­nimo com base na mÃÂ©dia do histÃÂ³rico."""
        if not self.historico_volumes:
            return

        volumes_na_janela = [vol for ts, vol in self.historico_volumes]
        media_volume = sum(volumes_na_janela) / len(volumes_na_janela)

        # O novo mÃÂ­nimo ÃÂ© um percentual da mÃÂ©dia
        self.volume_minimo_adaptativo = media_volume * self.percentual_da_media

        # Garante um piso mÃÂ­nimo para nÃÂ£o operar com volume muito baixo
        piso_absoluto = 500
        self.volume_minimo_adaptativo = max(
            self.volume_minimo_adaptativo, piso_absoluto)

    def pode_operar(self, volume_atual: float) -> bool:
        """Verifica se o volume atual ae ao mÃÂ­nimo adaptativo."""
        return volume_atual >= self.volume_minimo_adaptativo

        # Alerta: Drawdown alto
        if self.drawdown_atual > 300:  # R$ 300
            alertas.append(f"Ã°Å¸Å¡Â¨ Drawdown alto: R$ {self.drawdown_atual:.2f}")

        # Alerta: Muitos losses seguidos
        losses_seguidos = 0
        for op in reversed(self.operacoes_recentes):
            if op < 0:
                losses_seguidos += 1
            else:
                break
        if losses_seguidos >= 3:
            alertas.append(f"Ã°Å¸Å¡Â¨ {losses_seguidos} losses seguidos")

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


# ConfiguraÃÂ§ÃÂµes do monitor de performance
MONITOR_PERFORMANCE_ATIVO = True
ALERTA_TAXA_ACERTO_MIN = 30    # Alerta se taxa < 30%
ALERTA_DRAWDOWN_MAX = 300      # Alerta se drawdown > R$ 300
ALERTA_LOSSES_SEGUIDOS = 3     # Alerta se 3+ losses seguidos

# InstÃÂ¢ncia global do monitor
monitor_performance = None

# endregion
# region [Logging]


def setup_logging():
    """Configura o sistema de logging.

    LÃÂ³gica de rotaÃÂ§ÃÂ£o:
    - Se o log NÃÆO existe ou foi modificado em outro dia Ã¢â â SOBRESCREVE (nova sessÃÂ£o)
    - Se o log existe e foi modificado HOJE Ã¢â â APPEND (reiniciando durante o mercado)

    NÃÂ­vel INFO: mostra o que importa (mercado ao vivo, Sniper, decisÃÂµes, heartbeat
    da posiÃÂ§ÃÂ£o, trailing, erros) e elimina o spam de DEBUG (ex.: 'Nenhuma posiÃÂ§ÃÂ£o
    ativa', 'EA Data', logs internos de bibliotecas). Para depurar, trocar para DEBUG.
    """
    hoje = datetime.now().date()
    log_existe_hoje = False

    if os.path.exists(LOG_FILE):
        modificacao = datetime.fromtimestamp(os.path.getmtime(LOG_FILE)).date()
        log_existe_hoje = (modificacao == hoje)

    # FIX 14/08 (item 5 da autopsia): rotaciona o log de dias anteriores em vez
    # de sobrescrever. Antes, o monstro_wdo.log de 11-13/08 foi perdido quando o
    # robo iniciou em 14/08 (filemode='w'), impossibilitando a auditoria dos dias.
    # Agora: log anterior vira monstro_wdo_YYYYMMDD.log e um novo e criado para
    # a sessao de hoje. O dashboard/agente continuam lendo monstro_wdo.log (hoje).
    if os.path.exists(LOG_FILE) and not log_existe_hoje:
        data_anterior = modificacao.strftime("%Y%m%d")
        log_rotacionado = f"{os.path.splitext(LOG_FILE)[0]}_{data_anterior}.log"
        try:
            os.replace(LOG_FILE, log_rotacionado)
        except Exception as e:
            logging.warning(f"â ï¸ Falha ao rotacionar log anterior ({log_rotacionado}): {e}")

    # Se o log Ã© de hoje (reiniciando durante o mercado) â append
    # Se o log nÃ£o existe ou foi rotacionado â nova sessÃ£o
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
        logging.info("Ã°Å¸Å½Â¯ Monstro WDO v2 REINICIADO (log de hoje preservado)")
    else:
        logging.info("Ã°Å¸Å½Â¯ Monstro WDO v2 iniciado! Nova sessÃÂ£o (log anterior sobrescrito)")
    logging.info(
        f"Ã°Å¸âÅ  ConfiguraÃÂ§ÃÂ£o: SL={SL_POINTS}pts, TP={TP_POINTS}pts, Vol={VOLUME_PADRAO}cc")


# ========== PA1: TRAVA DE HORÃÂRIO - IMPLEMENTAÃâ¡ÃÆO DO PLANO DE AÃâ¡ÃÆO ==========

def horario_permitido() -> bool:
    """
    Ã¢Åâ¦ PA1: Janelas de operaÃÂ§ÃÂ£o baseadas em liquidez e volatilidade do WDO:
    - 09:15-12:30  Abertura dos futuros (pÃÂ³s-volatilidade inicial)
    - 14:30-17:15  Retomada institucional (ajustes finais)
    NOTA: SniperSupermo ignora esta verificaÃÂ§ÃÂ£o (pode operar 09:00-17:30).
    """
    agora = datetime.now().time()
    if dtime(9, 15) <= agora <= dtime(12, 30):
        return True
    if dtime(14, 30) <= agora <= dtime(17, 15):
        return True
    return False


def segundos_ate_proxima_janela() -> int:
    """Calcula quantos segundos faltam para a prÃÂ³xima janela de operaÃÂ§ÃÂ£o."""
    agora = datetime.now()
    hoje = agora.date()

    janelas = [dtime(9, 15), dtime(14, 30)]

    for janela in janelas:
        proximo = datetime.combine(hoje, janela)
        if proximo > agora:
            return int((proximo - agora).total_seconds())

    # Todas as janelas de hoje passaram Ã¢â¬â prÃÂ³xima ÃÂ© 09:15 do prÃÂ³ximo dia ÃÂºtil
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
        logging.info(f"Ã°Å¸âË PTAX atualizada: R$ {valor:.4f}")
    return valor

def ultimo_dia_util_mes(data: datetime = None) -> bool:
    """Retorna True se 'data' ÃÂ© o ÃÂºltimo dia ÃÂºtil do mÃÂªs."""
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
    # Minutos atÃÂ© prÃÂ³xima janela
    for inicio, _ in janelas:
        if minutos < inicio:
            return False, inicio - minutos
    return False, 60  # Se passou das 13:10, prÃÂ³ximo dia

def eh_horario_payroll() -> bool:
    """Retorna True se estamos dentro da janela de fuga do payroll (9:25-9:35 BRT)."""
    agora = datetime.now()
    if agora.weekday() != 4:  # Sexta
        return False
    h, m = agora.hour, agora.minute
    # Payroll: primeira sexta do mÃÂªs, 9:30 BRT. Fugir 9:25-9:35
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


# ========== PA3: RESET DE MEMÃâRIA DA IA - IMPLEMENTAÃâ¡ÃÆO DO PLANO DE AÃâ¡ÃÆO ==========

def resetar_memoria_ia():
    """
    Ã¢Åâ¦ PA3: RESET DE IA: Limpa memÃÂ³ria de experiÃÂªncias para comeÃÂ§ar aprendizado do zero
    com as novas correÃÂ§ÃÂµes conforme plano de aÃÂ§ÃÂ£o.
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
                    # MantÃÂ©m apenas o cabeÃÂ§alho se existir
                    if os.path.getsize(arquivo) > 0:
                        df = pd.read_csv(arquivo, nrows=0)  # SÃÂ³ cabeÃÂ§alho
                        df.to_csv(arquivo, index=False)
                elif arquivo.endswith('.pkl'):
                    os.remove(arquivo)

                arquivos_limpos += 1
                logging.info(
                    f"Ã¢Åâ¦ RESET: {arquivo} limpo (backup: {backup_name})")
            else:
                logging.info(f"Ã¢Å¡Â Ã¯Â¸Â RESET: {arquivo} nÃÂ£o existe")

        except Exception as e:
            logging.error(f"Ã¢ÂÅ RESET: Erro ao limpar {arquivo}: {e}")

    logging.info(
        f"Ã°Å¸ââ RESET DE MEMÃâRIA COMPLETO: {arquivos_limpos} arquivos processados")
    logging.info("Ã°Å¸Å½Â¯ IA comeÃÂ§arÃÂ¡ aprendizado do zero com novas correÃÂ§ÃÂµes!")

# endregion

# region [FunÃÂ§ÃÂµes Auxiliares]


def analisar_profundidade_book(book_data: Dict, preco_referencia: float) -> Dict:
    """
    Analisa a profundidade do book e extrai features sobre escoras e liquidez.

    Args:
        book_data: Dados book no formato JSON {"bids": [...], "asks": [...]}
        preco_referencia: PreÃÂ§o atual de referÃÂªncia para calcular distÃÂ¢ncias

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

                # Calcula distÃÂ¢ncia apenas se temos preÃÂ§o vÃÂ¡lido
                if features['preco_maior_escora_bid'] > 0 and preco_referencia > 0:
                    features['distancia_maior_escora_bid'] = abs(
                        preco_referencia - features['preco_maior_escora_bid'])

                # Liquidez dos top 5 nÃÂ­veis
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

                # Calcula distÃÂ¢ncia apenas se temos preÃÂ§o vÃÂ¡lido
                if features['preco_maior_escora_ask'] > 0 and preco_referencia > 0:
                    features['distancia_maior_escora_ask'] = abs(
                        features['preco_maior_escora_ask'] - preco_referencia)

                # Liquidez dos top 5 nÃÂ­veis
                features['liquidez_top5_ask'] = float(
                    df_asks.head(5)['volume'].sum())

    except Exception as e:
        logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â Erro ao analisar profundidade do book: {e}")
        # Retorna features zeradas em caso de erro

    return features


def obter_nome_vela(open_price: float, close_price: float, high: float, low: float, previous_open: float = None, previous_close: float = None) -> str:
    """Determina o tipo da vela baseado nos preÃÂ§os e padrÃÂµes.

    Tipos de velas identificadas:
    - Marubozu (alta/baixa): corpo grande sem sombras
    - Doji: abertura = fechamento
    - Martelo/Hammer: sombra inferior longa
    - Shooting Star: sombra superior longa
    - Engolfo (alta/baixa): quando uma vela engole a anterior
    - Inside Bar: vela contida na anterior
    - Outside Bar: vela que contÃÂ©m a anterior
    - Estrela da ManhÃÂ£/Noite: padrÃÂ£o de 3 velas
    - Pin Bar: vela com sombra longa
    """
    body_size = abs(close_price - open_price)
    total_size = high - low
    upper_shadow = high - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low

    # Calcula proporÃÂ§ÃÂµes
    body_ratio = body_size / total_size if total_size > 0 else 0
    upper_ratio = upper_shadow / total_size if total_size > 0 else 0
    lower_ratio = lower_shadow / total_size if total_size > 0 else 0

    # Doji
    if body_ratio < 0.1:
        if upper_ratio > 0.6:
            return "doji_gravestone"  # Doji LÃÂ¡pide
        elif lower_ratio > 0.6:
            return "doji_dragonfly"   # Doji LibÃÂ©lula
        return "doji"

    # DireÃÂ§ÃÂ£o bÃÂ¡sica
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

    # PadrÃÂµes com vela anterior
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

    # Vela padrÃÂ£o
    return direction


def calcular_entropia(volumes: List[int]) -> float:
    """Calcula a entropia dos volumes do book (CORRIGIDO PARA EA)."""
    if not volumes:
        logging.debug(
            "[Entropia] Lista de volumes vazia, retornando entropia 0.0")
        return 0.0

    # Converte para inteiros e remove zeros para evitar problemas no cÃÂ¡lculo
    try:
        volumes_validos = [int(v) for v in volumes if int(v) > 0]
    except (ValueError, TypeError) as e:
        logging.error(
            f"[Entropia] Erro ao converter volumes para int: {e}, volumes: {volumes[:5]}...")
        return 0.0

    if not volumes_validos:
        logging.debug(
            "[Entropia] NÃÂ£o hÃÂ¡ volumes vÃÂ¡lidos (>0), retornando entropia 0.0")
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
    """Detecta divergÃÂªncia bull/bear entre preÃÂ§o e Williams %R usando thresholds em ticks (WDO TICK_SIZE=0.5)."""
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
    """Monitora Williams %R em tempo real, detecta zonas e divergÃÂªncias, salva histÃÂ³rico CSV."""

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
            logging.info(f"Ã°Å¸âÅ  WILLIAMS %R: {wr:.1f} ({zona})")
            self.ultimo_log_zona = zona

        # Log divergencia only when detected
        if divergencia != "NEUTRO" and divergencia != self.ultima_divergencia:
            logging.info(f"Ã°Å¸âÂ WILLIAMS %R DIVERGENCIA: {divergencia} (WR={wr:.1f}, Preco={preco:.1f})")
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


# ========== SNIPER %R (reversÃ£o de extremo â Larry Williams) ==========
SNIPER_SUPERMO_ATIVO = True
SNIPER_SUPERMO_VOLUME = 1.0
# Modo "sniper apenas": quando o sniper %R nÃ£o ativa, o robÃ´ NÃO opera pela IA
# principal (que sangrou -455 na semana). SÃ³ o sniper executa ordens.
SNIPER_APENAS = bool(config.get('sniper_apenas', True))
SNIPER_SUPERMO_CSV = _caminho_dados("sniper_supermo_historico.csv")


class SniperSupermo:
    """SNIPER %R (Larry Williams) â reversÃ£o de extremo, validado em backtest.

    EstratÃ©gia escolhida: variante A (ampla) do backtest de 07/08/2026 sobre
    8918 ticks reais (7 pregÃµes), com custo real de R$1,20/operaÃ§Ã£o (0,60 ida
    + 0,60 volta por contrato, RLP ativo):
      - 130 trades, Win 53,1%, Payoff 1,81, +167 R$/semana LÃQUIDO, MaxDD -7R.
      - Entrada no %R extremo (<= -80 BUY / >= -20 SELL), sem filtro horÃ¡rio,
        sem limite de trades/dia.
      - GestÃ£o no MT5: SL = 1.5xATR(14) M1, TP = 3xATR (alvo 2R), trailing 50%
        do ganho pÃ³s-1R no loop de monitoramento (fiel ao backtest).

    Diferente do sniper antigo (que exigia DOL conf>0.7 = score 7/7 e nunca
    disparava porque o DOL real ficava em 0.34-0.43), este sniper SÃ usa %R.
    """

    def __init__(self):
        self._csv_header_escrito = False
        self.ultimo_log = 0
        self.cooldown_ate: float = 0
        # FIX 15/08 (gargalo de spam): cooldown entre disparos vem do config.
        # A semana teve 373 disparos/dia no CSV com apenas ~5% de execuÃ§Ã£o
        # (spam de sinal). Cooldown de 2min forÃ§a o sniper a esperar entre
        # sinais consecutivos, filtrando ruÃ­do e processamento desperdiÃ§ado.
        self.cooldown_segundos = float(config.get('sniper_cooldown_s', 120))
        self.em_zona = 0  # 1=SOBREVENDIDO(BUY), -1=SOBRECOMPRADO(SELL), 0=fora
        self.wr_anterior = -50.0

    def verificar(self, contexto: dict, acao_sugerida: str) -> dict:
        """Retorna {'ativo': bool, 'direcao': str, 'score': int, 'detalhes': list,
        'sl_points': float, 'tp_points': float}."""
        agora = time.time()
        if agora < self.cooldown_ate:
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['cooldown']}

        if not contexto:
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['sem_contexto']}

        # Bloqueio por PTAX day ou payroll
        if contexto.get('sniper_bloqueado', 0):
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['BLOQ_PTAX/PAYROLL']}

        # JÃ¡ em posiÃ§Ã£o: nÃ£o re-entra (gestÃ£o de saÃ­da cuida do trade vigente)
        if contexto.get('is_in_trade', 0):
            return {'ativo': False, 'direcao': 'NADA', 'score': 0, 'detalhes': ['ja_em_posicao']}

        wr = float(contexto.get('williams_r', -50))
        self.wr_anterior = wr
        score = 0
        detalhes = []
        direcao = "NADA"

        # Sinal %R extremo com trava de zona: sÃ³ entra na ENTRADA da zona
        # (debounce), evitando mÃºltiplos sinais dentro do mesmo extremo.
        if wr <= -80:
            score += 2
            detalhes.append(f"%R={wr:.0f}(SEV)")
            if self.em_zona != 1:
                self.em_zona = 1
                direcao = "BUY"
                detalhes.append("BUY")
        elif wr >= -20:
            score += 2
            detalhes.append(f"%R={wr:.0f}(SEC)")
            if self.em_zona != -1:
                self.em_zona = -1
                direcao = "SELL"
                detalhes.append("SELL")
        else:
            self.em_zona = 0
            detalhes.append(f"%R={wr:.0f}(neutro)")

        # FIX 11/08: filtro contra-tendÃªncia â o dia 11/08 sangrou 8 SELL
        # seguidos numa tendÃªncia de alta forte. O sniper sÃ³ opera NA direÃ§Ã£o
        # da tendÃªncia (ou em NEUTRO). MantÃ©m a trava de zona para nÃ£o
        # re-disparar no mesmo extremo enquanto a tendÃªncia nÃ£o mudar.
        # FIX 12/08: usa os vetos do FiltroTendencia (SMA-50 + momentum) â
        # que detectou a tendÃªncia corretamente no dia 12/08 â alÃ©m do EMA9/21.
        # FIX 13/08: veto Multi-TF â o dia 13/08 vendeu 3x contra alta forte
        # com M15/M30 sobrecomprados (WR >= -20 em ambos). O %R M1 em SEC
        # num contexto de M15/M30 sobrecomprados NÃO Ã© reversÃ£o, Ã© tendÃªncia.
        # Regra: SELL bloqueado se M15 E M30 sobrecomprados; BUY se ambos
        # sobrevendidos (<= -80). SÃ³ bloqueia em consenso, preservando
        # reversÃµes legÃ­timas em mercado lateral.
        if direcao != "NADA":
            tendencia_m1 = contexto.get('tendencia_m1', 'NEUTRO')
            _veto_buy = contexto.get('tendencia_veto_buy', False)
            _veto_sell = contexto.get('tendencia_veto_sell', False)
            _motivo = contexto.get('tendencia_motivo', '')
            # Multi-TF: M15/M30 WR disponÃ­veis no contexto (L6979-6981)
            _m15_wr = contexto.get('m15_wr', None)
            _m30_wr = contexto.get('m30_wr', None)
            _veto_mt_buy = False
            _veto_mt_sell = False
            if _m15_wr is not None and _m30_wr is not None:
                if _m15_wr >= -20 and _m30_wr >= -20:
                    _veto_mt_sell = True
                if _m15_wr <= -80 and _m30_wr <= -80:
                    _veto_mt_buy = True
            if (direcao == "BUY" and (tendencia_m1 == "BAIXA" or _veto_buy or _veto_mt_buy)) or \
               (direcao == "SELL" and (tendencia_m1 == "ALTA" or _veto_sell or _veto_mt_sell)):
                if _veto_mt_sell or _veto_mt_buy:
                    detalhes.append(
                        f"multiTF M15={_m15_wr:.0f} M30={_m30_wr:.0f} bloqueia {direcao}")
                else:
                    detalhes.append(f"tendÃªncia={tendencia_m1} bloqueia {direcao} ({_motivo or 'EMA'})")
                direcao = "NADA"

        ativo = direcao != "NADA"

        # SL/TP por ATR do contexto (mesma gestÃ£o do backtest: 1.5x/3x)
        # FIX 17/08: piso mÃ­nimo de SL respeita o config (8.0 pts). Sem esse
        # floor, o ATR baixo em dias de baixa volatilidade gerava stops de
        # 3.5-4.0pts que eram atingidos por ruÃ­do natural do book (stop hunt).
        atr = float(contexto.get('volatility', 0)) or 2.0
        _sl_min = float(config.get('sl_max_pontos', 8.0))
        sl_points = max(1.5 * atr, _sl_min)
        tp_points = 3.0 * atr

        resultado = {
            'ativo': ativo,
            'direcao': direcao,
            'score': score,
            'detalhes': detalhes,
            'sl_points': sl_points,
            'tp_points': tp_points,
        }

        # Observabilidade: loga standby/score a cada 60s (o agente via texto de
        # sprint de treino antes, nÃ£o o robÃ´ real)
        if agora - self.ultimo_log > 60:
            self.ultimo_log = agora
            logging.info(
                f"SNIPER %R | wr={wr:.0f} | zona={self.em_zona} | "
                f"score={score} | {'ATIVO ' + direcao if ativo else 'standby'} | "
                f"{' | '.join(detalhes)} | SL={sl_points:.1f}pt TP={tp_points:.1f}pt")

        if ativo:
            banner = (
                f"\n{'='*60}\n"
                f"â¡ SNIPER %R ATIVADO â¡\n"
                f"DIREÃÃO: {direcao} | %R={wr:.0f}\n"
                f"CONDIÃÃES: {' | '.join(detalhes)}\n"
                f"SL={sl_points:.1f}pt (max({1.5}xATR,{_sl_min:.0f})) | TP={tp_points:.1f}pt (2R)\n"
                f"{'='*60}"
            )
            logging.info(banner)
            self._salvar_csv(contexto, direcao, score, detalhes)
            # FIX 15/08 (spam): disparou 1 sinal -> cooldown entre disparos.
            # Mesmo que a ordem falhe nos filtros posteriores, o sniper espera
            # o cooldown antes de gerar o prÃ³ximo sinal (filtra ~373 disparos/dia).
            self.cooldown_ate = time.time() + self.cooldown_segundos

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
        logging.info(f"Ã¢ÂÂ³ SNIPER SUPERMO cooldown: {self.cooldown_segundos}s")


sniper_supermo = SniperSupermo()


def normalizar_dados(df: pd.DataFrame, colunas_numericas: List[str], colunas_categoricas: List[str], treino: bool = True) -> pd.DataFrame:
    """Normaliza dados numÃÂ©ricos e codifica dados categÃÂ³ricos."""
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
        # Durante prediÃÂ§ÃÂ£o Ã¢â¬â verifica se scaler estÃÂ¡ fitted
        scaler_precisa_fit = False
        if scaler_global is None:
            scaler_precisa_fit = True
        else:
            try:
                check_is_fitted(scaler_global)
            except Exception:
                scaler_precisa_fit = True

        if scaler_precisa_fit:
            # Scaler nÃÂ£o fitted Ã¢â¬â faz fit com os dados atuais como fallback
            logging.warning(
                "[normalizar_dados] Ã¢Å¡Â Ã¯Â¸Â Scaler nÃÂ£o fitted Ã¢â¬â fazendo fit com dados atuais como fallback")
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
                logging.warning(f"[normalizar_dados] â ï¸ {n_clip} valores fora de [0,1] foram clipped")
            logging.debug(f"[normalizar_dados] Scaler aplicado para prediÃÂ§ÃÂ£o")

    for col in colunas_categoricas:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
    return df


def converter_candle_type(candle_type: str) -> str:
    """Converte o tipo de candle para um formato padronizado."""
    return candle_type.lower()  # MantÃÂ©m o tipo detalhado


def monitorar_recursos() -> None:
    """Monitora recursos do sistema e salva experiÃÂªncias."""
    try:
        if os.path.exists(HISTORICO_CSV):
            # Verifica tamanho do arquivo
            tamanho_arquivo = os.path.getsize(
                HISTORICO_CSV) / (1024 * 1024)  # Tamanho em MB

            # Se arquivo maior que 50MB, faz rotaÃÂ§ÃÂ£o
            if tamanho_arquivo > 50:
                # Cria nome do backup com timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{HISTORICO_CSV}.{timestamp}.bak"

                # Move arquivo atual para backup
                os.rename(HISTORICO_CSV, backup_name)

                # MantÃÂ©m apenas os ÃÂºltimos 5 backups
                backups = sorted([f for f in os.listdir('.') if f.startswith(
                    HISTORICO_CSV) and f.endswith('.bak')])
                while len(backups) > 5:
                    os.remove(backups.pop(0))

                logging.info(
                    f"Ã°Å¸âÂ¦ RotaÃÂ§ÃÂ£o do histÃÂ³rico realizada. Backup: {backup_name}")

            # LÃÂª e limita nÃÂºmero de linhas com tratamento de erro
            try:
                df = pd.read_csv(HISTORICO_CSV)
                if len(df) > 5000:  # Reduzido de 10000 para 5000
                    df = df.tail(5000)
                    df.to_csv(HISTORICO_CSV, index=False)
                    logging.debug(
                        "Ã¢ÅâÃ¯Â¸Â HistÃÂ³rico truncado para ÃÂºltimas 5000 linhas")
            except pd.errors.ParserError as e:
                logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â CSV histÃÂ³rico corrompido: {e}")
                logging.info("Ã°Å¸âÂ§ Recriando arquivo CSV histÃÂ³rico...")
                # Cria cabeÃÂ§alho com o esquema oficial (timestamp + features)
                colunas_padrao = COLUNAS_CONTEXTO_OFICIAL
                df_novo = pd.DataFrame(columns=colunas_padrao)
                df_novo.to_csv(HISTORICO_CSV, index=False)
                logging.info("Ã¢Åâ¦ CSV histÃÂ³rico recriado com sucesso")

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao monitorar recursos: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")


def corrigir_csv_historico() -> None:
    """Corrige o formato do arquivo CSV histÃÂ³rico se necessÃÂ¡rio."""
    try:
        if not os.path.exists(HISTORICO_CSV):
            logging.info(
                "Ã°Å¸âÂ Arquivo histÃÂ³rico nÃÂ£o existe. SerÃÂ¡ criado na primeira operaÃÂ§ÃÂ£o.")
            return

        # Verifica tamanho do arquivo
        tamanho_arquivo = os.path.getsize(HISTORICO_CSV) / (1024 * 1024)  # MB
        if tamanho_arquivo > 100:  # Se maior que 100MB
            backup_name = f"{HISTORICO_CSV}.grande.{int(time.time())}"
            os.rename(HISTORICO_CSV, backup_name)
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â Arquivo muito grande ({tamanho_arquivo:.1f}MB). Movido para: {backup_name}")
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
                f"Ã°Å¸ââ Removendo colunas extras do CSV: {colunas_extras}")

        # Adiciona colunas faltantes com valores padrÃÂ£o apropriados
        colunas_faltando = [
            col for col in colunas_esperadas if col not in df.columns]
        if colunas_faltando:
            logging.warning(
                f"Ã¢Å¾â¢ Adicionando colunas faltantes no CSV: {colunas_faltando}")
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

        # Corrige tipos de dados e valores invÃÂ¡lidos
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
        # Ã¢Å¡Â Ã¯Â¸Â NÃÆO clipar 'reward'! Como a maioria das linhas ÃÂ© NAO_AGIU (reward=0),
        # os quartis ficam [0,0] e o clip zeraria TODAS as recompensas reais Ã¢â¬â
        # apagando o aprendizado da IA a cada reinÃÂ­cio. Reward ÃÂ© sinal, nÃÂ£o feature.
        for col in ['bid_qty', 'ask_qty', 'volume_tick']:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # Remove linhas com valores invÃÂ¡lidos
        df = df.dropna()

        # Limita nÃÂºmero de linhas
        if len(df) > 5000:
            df = df.tail(5000)
            logging.debug("Ã¢ÅâÃ¯Â¸Â HistÃÂ³rico truncado para ÃÂºltimas 5000 linhas")

        # Salva o arquivo corrigido
        df.to_csv(HISTORICO_CSV, index=False)

        linhas_final = len(df)
        linhas_removidas = linhas_originais - linhas_final
        if linhas_removidas > 0:
            logging.warning(
                f"Ã°Å¸Â§Â¹ {linhas_removidas} linhas invÃÂ¡lidas removidas do histÃÂ³rico")

        logging.info("Ã¢Åâ¦ Arquivo histÃÂ³rico corrigido com sucesso")

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao corrigir CSV histÃÂ³rico: {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        # Se houver erro, renomeia o arquivo corrompido e cria um novo
        if os.path.exists(HISTORICO_CSV):
            backup_name = f"{HISTORICO_CSV}.corrompido.{int(time.time())}"
            os.rename(HISTORICO_CSV, backup_name)
            logging.info(f"Ã°Å¸âÂ¦ Arquivo corrompido movido para: {backup_name}")


def salvar_experiencia_csv(contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
    """Salva uma experiÃÂªncia no arquivo CSV com validaÃÂ§ÃÂµes."""
    try:
        # RESET MODO APRENDIZADO FORÃâ¡ADO apÃÂ³s operaÃÂ§ÃÂ£o real
        global MODO_APRENDIZADO_FORCADO
        if acao in ["BUY", "SELL"] and MODO_APRENDIZADO_FORCADO:
            MODO_APRENDIZADO_FORCADO = False
            logging.info(
                "Ã°Å¸Å½â MODO APRENDIZADO FORÃâ¡ADO DESATIVADO - OperaÃÂ§ÃÂ£o real executada")

        # ========== INTEGRAÃâ¡ÃÆO MELHORIA 4: CIRCUIT BREAKER REGISTRA RESULTADO ==========
        if circuit_breaker and acao in ["BUY", "SELL"]:
            circuit_breaker.registrar_resultado(lucro)

        # ValidaÃÂ§ÃÂ£o dos tipos de dados
        if not isinstance(contexto, dict):
            raise ValueError("Contexto deve ser um dicionÃÂ¡rio")
        if not isinstance(acao, str):
            raise ValueError("AÃÂ§ÃÂ£o deve ser uma string")
        if not isinstance(lucro, (int, float)):
            raise ValueError("Lucro deve ser numÃÂ©rico")
        if not isinstance(score_dist, (int, float)):
            raise ValueError("Score_dist deve ser numÃÂ©rico")

        # ValidaÃÂ§ÃÂ£o dos valores
        acoes_validas = {"BUY", "SELL", "NAO_AGIU", "NADA"}
        if acao not in acoes_validas:
            raise ValueError(f"AÃÂ§ÃÂ£o invÃÂ¡lida: {acao}")

        # Garante que o contexto tem todas as colunas necessÃÂ¡rias e valores vÃÂ¡lidos
        dados = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
            # ForÃÂ§a 0 ou 1
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
                    "Ã¢Å¡Â Ã¯Â¸Â Arquivo de histÃÂ³rico muito grande, aguardando rotaÃÂ§ÃÂ£o...")
                return
            df.to_csv(HISTORICO_CSV, mode='a', header=False, index=False)
        else:
            df.to_csv(HISTORICO_CSV, index=False)

        # CORREÃâ¡ÃÆO C9: FASE 3 - TREINA COM TODAS AS EXPERIÃÅ NCIAS (wins E losses)
        global contador_experiencias_novas
        if acao in ["BUY", "SELL"]:  # Conta TODAS as operaÃÂ§ÃÂµes reais, nÃÂ£o sÃÂ³ lucrativas
            contador_experiencias_novas += 1

            # FASE 1: Registra resultado no bloqueador de contexto
            if lucro < 0:
                bloqueador_contexto.registrar_loss(contexto)
            else:
                bloqueador_contexto.registrar_win(contexto)

            logging.info(
                f"Ã¢Åâ¦ ExperiÃÂªncia REAL salva: AÃÂ§ÃÂ£o={acao}, Lucro={lucro:.2f}, Score={score_dist:.2f} | Contador: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO}")
        else:
            logging.debug(
                f"Ã¢Åâ¦ ExperiÃÂªncia salva: AÃÂ§ÃÂ£o={acao}, Lucro={lucro:.2f}, Score={score_dist:.2f}")

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao salvar experiÃÂªncia: {e}")
        logging.debug(f"Dados tentando salvar: {dados}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")


def preparar_dados(df: pd.DataFrame, treino: bool = False) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """Prepara dados para treino ou prediÃÂ§ÃÂ£o."""
    colunas_categoricas = [
    ]  # Removido candle_type para compatibilidade com modelo (10 features)
    colunas_numericas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book',
                         'rsi_14', 'volume_tick', 'is_in_trade', 'floating_profit', 'tempo_em_trade',
                         'preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
                         'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
                         'liquidez_top5_bid', 'liquidez_top5_ask',
                         'dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax']

    # Cria uma cÃÂ³pia para evitar modificar o original
    df_work = df.copy()

    # Adiciona colunas faltantes com valor 0 (compatibilidade com experiÃÂªncias antigas)
    colunas_book_novas = ['preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
                          'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
                          'liquidez_top5_bid', 'liquidez_top5_ask',
                          'dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax']
    for col in colunas_book_novas:
        if col not in df_work.columns:
            df_work[col] = 0.0

    # Normaliza dados numÃÂ©ricos e codifica categÃÂ³ricos
    try:
        df_work = normalizar_dados(
            df_work, colunas_numericas, colunas_categoricas, treino=treino)
    except Exception as e:
        logging.error(f"Erro na normalizaÃÂ§ÃÂ£o de dados: {e}")
        # Fallback: codifica manualmente as colunas categÃÂ³ricas
        for col in colunas_categoricas:
            if col in df_work.columns and df_work[col].dtype == 'object':
                le = LabelEncoder()
                df_work[col] = le.fit_transform(df_work[col].astype(str))

        # Normaliza apenas as numÃÂ©ricas usando scaler global
        global scaler_global
        if treino or scaler_global is None:
            scaler_global = MinMaxScaler()
            df_work[colunas_numericas] = scaler_global.fit_transform(
                df_work[colunas_numericas])
        else:
            df_work[colunas_numericas] = scaler_global.transform(
                df_work[colunas_numericas])

    # Seleciona apenas as colunas necessÃÂ¡rias
    todas_colunas = colunas_numericas + colunas_categoricas
    colunas_disponiveis = [
        col for col in todas_colunas if col in df_work.columns]

    # Debug para identificar problema
    logging.debug(
        f"[preparar_dados] Colunas no DataFrame: {list(df_work.columns)}")
    logging.debug(f"[preparar_dados] Colunas esperadas: {todas_colunas}")
    logging.debug(
        f"[preparar_dados] Colunas disponÃÂ­veis: {colunas_disponiveis}")

    X = df_work[colunas_disponiveis]
    logging.debug(f"[preparar_dados] Shape final X: {X.shape}")

    # Prepara target
    y = df_work['action'].apply(
        lambda x: 1 if x == 'BUY' else 0) if 'action' in df_work else None

    return X, y


def calcular_estocastico_lento(high_prices: List[float], low_prices: List[float], close_prices: List[float],
                               k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> Tuple[float, float]:
    """
    Calcula o EstocÃÂ¡stico Lento (%K e %D).
    k_period: PerÃÂ­odo para %K (padrÃÂ£o 14)
    d_period: PerÃÂ­odo para %D (padrÃÂ£o 3)
    smooth_k: PerÃÂ­odo de suavizaÃÂ§ÃÂ£o do %K (padrÃÂ£o 3)
    """
    if len(high_prices) < k_period or len(low_prices) < k_period or len(close_prices) < k_period:
        return 50.0, 50.0  # Valores neutros se nÃÂ£o houver dados suficientes

    # Calcula %K rÃÂ¡pido primeiro
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

    # Suaviza %K rÃÂ¡pido para obter %K lento
    k_slow = []
    for i in range(len(k_fast) - smooth_k + 1):
        k_slow.append(sum(k_fast[i:i+smooth_k]) / smooth_k)

    # Calcula %D (mÃÂ©dia mÃÂ³vel do %K lento)
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
    """Salva o modelo em disco (h5 + keras) com backup diÃÂ¡rio ÃÂºnico (sobrescreve).

    ATOMICIDADE: grava primeiro em arquivo temporÃÂ¡rio e usa os.replace()
    para a troca final. Assim o modelo principal nunca fica corrompido se
    o processo for morto no meio do save.
    """
    try:
        caminho_h5_abs = os.path.abspath(caminho)
        print(f"[SALVAR_MODELO] Iniciando save: {caminho_h5_abs}")

        # === BACKUP DIÃÂRIO: MÃÂX 1 POR DIA, SOBRESCREVENDO ===
        hoje = datetime.now().strftime("%Y%m%d")
        backup_diario = f"{caminho}.backup_{hoje}"
        if os.path.exists(caminho):
            shutil.copy2(caminho, backup_diario)
            logging.info(f"Ã°Å¸âÂ¦ Backup diÃÂ¡rio sobrescrito: {backup_diario}")

        # Remove backups antigos (timestamps) se existirem de versÃÂµes anteriores
        backup_pattern = f"{caminho}.backup_*"
        for antigo in glob.glob(backup_pattern):
            if antigo != backup_diario:
                try:
                    os.remove(antigo)
                except Exception:
                    pass

        # === SAVE ATÃâMICO: temp + os.replace (evita corrupÃÂ§ÃÂ£o em crash) ===
        caminho_keras = caminho.replace('.h5', '.keras')
        # â ï¸ FIX (01/08/2026): TF sÃ³ aceita extensÃµes .h5 ou .keras â .tmp_atomic causava
        # "Invalid filepath extension" silencioso. Usar _tmp.h5 / _tmp.keras (extensÃ£o vÃ¡lida).
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
    """Carrega o modelo Keras ou cria um novo se nÃÂ£o existir ou estiver corrompido."""
    try:
        if os.path.exists(caminho):
            # Tenta carregar o modelo existente
            modelo = load_model(caminho)

            # Verifica compatibilidade bÃÂ¡sica
            expected_features = N_FEATURES
            test_input = np.zeros((1, expected_features), dtype=np.float32)
            modelo.predict(test_input, verbose=0)

            logging.info(f"Ã¢Åâ¦ Modelo de IA carregado com sucesso de {caminho}")
            return modelo
        else:
            logging.info(
                "Ã°Å¸ââ Modelo nÃÂ£o encontrado. Criando um novo cÃÂ©rebro do zero...")
            return criar_modelo_neural(N_FEATURES)
    except Exception as e:
        logging.error(
            f"Ã¢Å¡Â Ã¯Â¸Â Erro ao carregar modelo ({e}). Resetando para evitar travamento...")
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
    """PROTEÃâ¡ÃÆO TOTAL DO MODELO - Verifica e recupera automaticamente se necessÃÂ¡rio."""
    try:
        modelo_principal = MODELO_PATH
        logging.info(
            f"Ã°Å¸âÂ Verificando integridade do modelo: {modelo_principal}")

        # Verifica se modelo principal existe
        if os.path.exists(modelo_principal):
            # Testa se o modelo pode ser carregado
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    test_model = load_model(modelo_principal)
                logging.debug("Ã¢Åâ¦ Modelo principal ÃÂ­ntegro e carregÃÂ¡vel")
                return True
            except Exception as e:
                logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â Modelo principal corrompido: {e}")
                # Modelo existe mas estÃÂ¡ corrompido - tenta recuperar
                return recuperar_modelo_automaticamente()
        else:
            logging.warning(
                "Ã¢Å¡Â Ã¯Â¸Â Modelo principal nÃÂ£o encontrado - tentando recuperar")
            return recuperar_modelo_automaticamente()

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro na verificaÃÂ§ÃÂ£o do modelo: {e}")
        return False


def recuperar_modelo_automaticamente() -> bool:
    """Ã°Å¸Å¡â RECUPERAÃâ¡ÃÆO AUTOMÃÂTICA - Encontra e restaura backup do modelo."""
    try:
        modelo_principal = MODELO_PATH

        # Lista todas as possibilidades de backup
        opcoes_backup = []

        # 1. Backup diÃÂ¡rio mais recente
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

        # 4. Backups antigos do prÃÂ³prio sistema
        backups_antigos = sorted(
            glob.glob(f"{modelo_principal}.backup_*"), reverse=True)
        opcoes_backup.extend(backups_antigos)

        # Remove duplicatas mantendo ordem
        opcoes_backup = list(dict.fromkeys(opcoes_backup))

        logging.info(f"Ã°Å¸âÂ Encontrados {len(opcoes_backup)} backups possÃÂ­veis")

        # Tenta recuperar do backup mais recente
        for backup_path in opcoes_backup:
            try:
                logging.info(f"Ã°Å¸Å¡â Tentando recuperar de: {backup_path}")

                # Testa se o backup ÃÂ© vÃÂ¡lido
                test_model = load_model(backup_path)

                # Se chegou aqui, o backup ÃÂ© vÃÂ¡lido - restaura
                shutil.copy2(backup_path, modelo_principal)
                logging.info(
                    f"Ã¢Åâ¦ MODELO RECUPERADO com sucesso de: {backup_path}")

                # Verifica se a recuperaÃÂ§ÃÂ£o funcionou
                final_test = load_model(modelo_principal)
                logging.info("Ã°Å¸Å½â° RECUPERAÃâ¡ÃÆO CONFIRMADA - Modelo funcionando!")
                return True

            except Exception as e:
                logging.warning(f"Ã¢ÂÅ Backup {backup_path} invÃÂ¡lido: {e}")
                continue

        # Se chegou aqui, nenhum backup funcionou
        logging.error("Ã°Å¸ââ¬ NENHUM BACKUP VÃÂLIDO ENCONTRADO!")
        logging.info("Ã°Å¸âÂ§ Criando novo modelo do zero (ÃÂºltima opÃÂ§ÃÂ£o)")
        return False

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro na recuperaÃÂ§ÃÂ£o automÃÂ¡tica: {e}")
        return False
# endregion

# region [Trading]


def calcular_score_distancia(preco_entrada: float, preco_saida: float, sl: float, tp: float) -> float:
    """Calcula um score adicional baseado na distÃÂ¢ncia que o preÃÂ§o chegou do TP/SL.

    Returns:
        float: Score entre -1 e 1, onde:
            1.0 = Atingiu TP
            -1.0 = Atingiu SL
            Valores intermediÃÂ¡rios baseados na proximidade
            Com TP=0: score baseado apenas na distÃÂ¢ncia do SL (saÃÂ­da dinÃÂ¢mica)
    """
    # Calcula distÃÂ¢ncias totais
    dist_total_sl = abs(sl - preco_entrada)
    if dist_total_sl == 0:
        dist_total_sl = 1.0  # Evita divisÃÂ£o por zero

    # Calcula distÃÂ¢ncia percorrida
    dist_percorrida = preco_saida - preco_entrada

    # Com TP=0 (saÃÂ­da dinÃÂ¢mica): score baseado na direÃÂ§ÃÂ£o e magnitude
    if tp == 0 or abs(tp - preco_entrada) < 0.01:
        # Sem TP definido: score proporcional ao lucro/prejuÃÂ­zo em relaÃÂ§ÃÂ£o ao SL
        # Lucro positivo Ã¢â â score positivo; PrejuÃÂ­zo Ã¢â â score negativo
        score = dist_percorrida / dist_total_sl
        return max(min(score, 1.0), -1.0)

    dist_total_tp = abs(tp - preco_entrada)
    if dist_total_tp == 0:
        dist_total_tp = 1.0

    # Com TP definido: lÃÂ³gica original
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
            f"Ã¢ÂÂ³ Aguardando abertura do pregÃÂ£o em {segundos//60}m{segundos % 60}sÃ¢â¬Â¦")
        while segundos > 0 and not verificar_parada_gracil():
            time.sleep(min(60, segundos))
            segundos -= 60


def aguardar_fechamento():
    agora = datetime.now().time()
    if agora >= dtime(17, 35):  # ApÃÂ³s encerramento automÃÂ¡tico
        segundos = ((datetime.combine(datetime.today(), dtime(
            23, 59)) - datetime.now()).seconds + 60)
        logging.info(f"Ã°Å¸Åâ¢ PregÃÂ£o encerrado. Dormindo atÃÂ© o prÃÂ³ximo dia ÃÂºtilÃ¢â¬Â¦")
        while segundos > 0 and not verificar_parada_gracil():
            time.sleep(min(60, segundos))
            segundos -= 60


# region [Detector de CodificaÃÂ§ÃÂ£o Robusto]
class CSVEncodingDetector:
    """Detector robusto de codificaÃÂ§ÃÂ£o para arquivos CSV do EA."""

    def __init__(self):
        """Inicializa o detector com configuraÃÂ§ÃÂµes otimizadas."""
        # Lista ordenada de codificaÃÂ§ÃÂµes por prioridade (mais comuns primeiro)
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

        # Cache de codificaÃÂ§ÃÂ£o bem-sucedida por arquivo
        self.encoding_cache = {}
        self.cache_ttl = 300  # 5 minutos de TTL para cache

        # PadrÃÂµes BOM (Byte Order Mark)
        self.bom_patterns = {
            b'\xff\xfe\x00\x00': 'utf-32-le',
            b'\x00\x00\xfe\xff': 'utf-32-be',
            b'\xff\xfe': 'utf-16-le',
            b'\xfe\xff': 'utf-16-be',
            b'\xef\xbb\xbf': 'utf-8'
        }

    def detect_bom(self, file_path: str) -> Optional[str]:
        """Detecta codificaÃÂ§ÃÂ£o atravÃÂ©s do BOM (Byte Order Mark).

        Args:
            file_path: Caminho para o arquivo

        Returns:
            CodificaÃÂ§ÃÂ£o detectada ou None se nÃÂ£o houver BOM
        """
        try:
            with open(file_path, 'rb') as f:
                # LÃÂª os primeiros 4 bytes para detectar BOM
                bom_bytes = f.read(4)

            # Verifica padrÃÂµes BOM em ordem de tamanho (maior primeiro)
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
        """Detecta codificaÃÂ§ÃÂ£o analisando o conteÃÂºdo do arquivo.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            CodificaÃÂ§ÃÂ£o mais provÃÂ¡vel ou None
        """
        try:
            # LÃÂª uma amostra do arquivo para anÃÂ¡lise
            with open(file_path, 'rb') as f:
                sample = f.read(1024)  # Primeiros 1KB

            if not sample:
                return None

            # Tenta decodificar com cada codificaÃÂ§ÃÂ£o
            encoding_scores = {}

            for encoding in self.encoding_priority:
                try:
                    decoded = sample.decode(encoding)

                    # Calcula score baseado em caracterÃÂ­sticas do conteÃÂºdo
                    score = self._calculate_content_score(decoded, encoding)
                    encoding_scores[encoding] = score

                except (UnicodeDecodeError, UnicodeError):
                    continue

            if not encoding_scores:
                return None

            # Retorna codificaÃÂ§ÃÂ£o com maior score
            best_encoding = max(encoding_scores, key=encoding_scores.get)
            best_score = encoding_scores[best_encoding]

            logging.debug(
                f"[CSVEncodingDetector] Melhor codificaÃÂ§ÃÂ£o por conteÃÂºdo: {best_encoding} (score: {best_score:.2f})")

            # SÃÂ³ retorna se o score for razoÃÂ¡vel
            return best_encoding if best_score > 0.5 else None

        except Exception as e:
            logging.debug(
                f"[CSVEncodingDetector] Erro na detecÃÂ§ÃÂ£o por conteÃÂºdo: {e}")
            return None

    def _calculate_content_score(self, content: str, encoding: str) -> float:
        """Calcula score de qualidade para uma decodificaÃÂ§ÃÂ£o.

        Args:
            content: ConteÃÂºdo decodificado
            encoding: CodificaÃÂ§ÃÂ£o utilizada

        Returns:
            Score de 0.0 a 1.0 (maior = melhor)
        """
        if not content:
            return 0.0

        score = 0.0

        # Bonus para caracteres ASCII vÃÂ¡lidos (nÃÂºmeros, vÃÂ­rgulas, quebras de linha)
        ascii_chars = sum(1 for c in content if ord(c) < 128)
        ascii_ratio = ascii_chars / len(content)
        score += ascii_ratio * 0.4

        # Bonus para padrÃÂµes esperados no CSV do book (nÃÂºmeros e vÃÂ­rgulas)
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

        # Bonus para codificaÃÂ§ÃÂµes mais comuns
        encoding_bonus = {
            'utf-8': 0.2,
            'utf-16-le': 0.1,
            'ascii': 0.15,
            'latin-1': 0.05
        }
        score += encoding_bonus.get(encoding, 0.0)

        return max(0.0, min(1.0, score))

    def get_cached_encoding(self, file_path: str) -> Optional[str]:
        """ObtÃÂ©m codificaÃÂ§ÃÂ£o do cache se ainda vÃÂ¡lida.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            CodificaÃÂ§ÃÂ£o em cache ou None se expirada/inexistente
        """
        if file_path not in self.encoding_cache:
            return None

        cached_data = self.encoding_cache[file_path]
        cache_time = cached_data.get('timestamp', 0)

        # Verifica se cache ainda ÃÂ© vÃÂ¡lido
        if time.time() - cache_time > self.cache_ttl:
            del self.encoding_cache[file_path]
            return None

        encoding = cached_data.get('encoding')
        logging.debug(
            f"[CSVEncodingDetector] Usando codificaÃÂ§ÃÂ£o em cache: {encoding}")
        return encoding

    def cache_encoding(self, file_path: str, encoding: str):
        """Armazena codificaÃÂ§ÃÂ£o bem-sucedida no cache.

        Args:
            file_path: Caminho para o arquivo
            encoding: CodificaÃÂ§ÃÂ£o que funcionou
        """
        self.encoding_cache[file_path] = {
            'encoding': encoding,
            'timestamp': time.time()
        }
        logging.debug(
            f"[CSVEncodingDetector] CodificaÃÂ§ÃÂ£o {encoding} armazenada em cache")

    def detect_encoding(self, file_path: str) -> List[str]:
        """Detecta a melhor codificaÃÂ§ÃÂ£o para um arquivo CSV.

        Args:
            file_path: Caminho para o arquivo

        Returns:
            Lista ordenada de codificaÃÂ§ÃÂµes para tentar (mais provÃÂ¡vel primeiro)
        """
        if not os.path.exists(file_path):
            return self.encoding_priority.copy()

        # 1. Verifica cache primeiro
        cached_encoding = self.get_cached_encoding(file_path)
        if cached_encoding:
            # Move codificaÃÂ§ÃÂ£o em cache para o inÃÂ­cio da lista
            encodings = [cached_encoding] + \
                [e for e in self.encoding_priority if e != cached_encoding]
            return encodings

        # 2. Tenta detectar por BOM
        bom_encoding = self.detect_bom(file_path)
        if bom_encoding:
            # Move codificaÃÂ§ÃÂ£o detectada por BOM para o inÃÂ­cio
            encodings = [bom_encoding] + \
                [e for e in self.encoding_priority if e != bom_encoding]
            return encodings

        # 3. Tenta detectar por conteÃÂºdo
        content_encoding = self.detect_by_content(file_path)
        if content_encoding:
            # Move codificaÃÂ§ÃÂ£o detectada por conteÃÂºdo para o inÃÂ­cio
            encodings = [content_encoding] + \
                [e for e in self.encoding_priority if e != content_encoding]
            return encodings

        # 4. Retorna lista padrÃÂ£o se nenhuma detecÃÂ§ÃÂ£o funcionou
        return self.encoding_priority.copy()


# InstÃÂ¢ncia global do detector
_csv_encoding_detector = CSVEncodingDetector()

# region [Validador de Dados do Book]


class CSVDataValidator:
    """Validador robusto de dados do book de ofertas."""

    def __init__(self):
        """Inicializa o validador com configuraÃÂ§ÃÂµes de validaÃÂ§ÃÂ£o."""
        # Limites de validaÃÂ§ÃÂ£o
        self.min_volume = 1
        self.max_volume = 100000  # Volume mÃÂ¡ximo razoÃÂ¡vel por nÃÂ­vel
        self.min_levels = 1       # MÃÂ­nimo de nÃÂ­veis por lado
        self.max_levels = 50      # MÃÂ¡ximo de nÃÂ­veis por lado
        self.min_total_volume = 10  # Volume total mÃÂ­nimo por lado
        self.max_total_volume = 1000000  # Volume total mÃÂ¡ximo por lado

        # ConfiguraÃÂ§ÃÂµes de sanitizaÃÂ§ÃÂ£o
        self.enable_sanitization = True
        self.strict_mode = False  # Se True, rejeita dados com qualquer problema

        # EstatÃÂ­sticas de validaÃÂ§ÃÂ£o
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
            side: "bids" ou "asks" para identificaÃÂ§ÃÂ£o

        Returns:
            DicionÃÂ¡rio com resultado da validaÃÂ§ÃÂ£o
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

        # ValidaÃÂ§ÃÂ£o bÃÂ¡sica de tipos
        if not all(isinstance(v, (int, float)) for v in volumes):
            result['issues'].append(f"Tipos invÃÂ¡lidos em {side}")
            if not self.enable_sanitization:
                result['valid'] = False
                return result

        # SanitizaÃÂ§ÃÂ£o e validaÃÂ§ÃÂ£o de volumes individuais
        sanitized = []
        for i, volume in enumerate(volumes):
            try:
                # Converte para int se necessÃÂ¡rio
                vol_int = int(volume) if isinstance(volume, float) else volume

                # Valida limites
                if vol_int < self.min_volume:
                    result['issues'].append(
                        f"Volume muito baixo em {side}[{i}]: {vol_int}")
                    if self.enable_sanitization:
                        continue  # Remove volume invÃÂ¡lido
                    else:
                        result['valid'] = False
                        return result

                if vol_int > self.max_volume:
                    result['issues'].append(
                        f"Volume muito alto em {side}[{i}]: {vol_int}")
                    if self.enable_sanitization:
                        vol_int = self.max_volume  # Limita ao mÃÂ¡ximo
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

        # ValidaÃÂ§ÃÂ£o de contagem de nÃÂ­veis
        if len(sanitized) < self.min_levels:
            result['issues'].append(
                f"Poucos nÃÂ­veis em {side}: {len(sanitized)} < {self.min_levels}")
            if self.strict_mode:
                result['valid'] = False
                return result

        if len(sanitized) > self.max_levels:
            result['issues'].append(
                f"Muitos nÃÂ­veis em {side}: {len(sanitized)} > {self.max_levels}")
            if self.enable_sanitization:
                result['sanitized_volumes'] = sanitized[:self.max_levels]
                result['sanitized_count'] = self.max_levels
                result['total_volume'] = sum(result['sanitized_volumes'])
            elif self.strict_mode:
                result['valid'] = False
                return result

        # ValidaÃÂ§ÃÂ£o de volume total
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
        """Detecta padrÃÂµes suspeitos nos dados do book.

        Args:
            bids: Lista de volumes de compra
            asks: Lista de volumes de venda

        Returns:
            Lista de alertas sobre padrÃÂµes suspeitos
        """
        alerts = []

        if not bids or not asks:
            return alerts

        # PadrÃÂ£o 1: Todos os volumes iguais (suspeito)
        if len(set(bids)) == 1 and len(bids) > 3:
            alerts.append(f"Todos os volumes BID sÃÂ£o iguais: {bids[0]}")

        if len(set(asks)) == 1 and len(asks) > 3:
            alerts.append(f"Todos os volumes ASK sÃÂ£o iguais: {asks[0]}")

        # PadrÃÂ£o 2: DesequilÃÂ­brio extremo
        total_bids = sum(bids)
        total_asks = sum(asks)

        if total_bids > 0 and total_asks > 0:
            ratio = max(total_bids, total_asks) / min(total_bids, total_asks)
            if ratio > 10:  # DesequilÃÂ­brio de 10:1
                alerts.append(
                    f"DesequilÃÂ­brio extremo BID/ASK: {total_bids}/{total_asks} (ratio: {ratio:.1f})")

        # PadrÃÂ£o 3: Volumes muito baixos generalizados
        avg_bid = sum(bids) / len(bids) if bids else 0
        avg_ask = sum(asks) / len(asks) if asks else 0

        if avg_bid < 5 and avg_ask < 5:
            alerts.append(
                f"Volumes mÃÂ©dios muito baixos: BID={avg_bid:.1f}, ASK={avg_ask:.1f}")

        # PadrÃÂ£o 4: SequÃÂªncia suspeita (nÃÂºmeros consecutivos)
        if len(bids) >= 5:
            consecutive_count = 0
            for i in range(1, len(bids)):
                if abs(bids[i] - bids[i-1]) <= 1:
                    consecutive_count += 1
                else:
                    consecutive_count = 0
                if consecutive_count >= 4:  # 5 nÃÂºmeros quase consecutivos
                    alerts.append("SequÃÂªncia suspeita detectada em BIDs")
                    break

        return alerts

    def validate_book_data(self, book_data: Dict[str, List[int]]) -> Dict[str, Any]:
        """Valida dados completos do book de ofertas.

        Args:
            book_data: DicionÃÂ¡rio com 'bids' e 'asks'

        Returns:
            Resultado completo da validaÃÂ§ÃÂ£o com dados sanitizados
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
            result['issues'].append("Dados do book invÃÂ¡lidos ou nulos")
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

        # Detecta padrÃÂµes suspeitos
        result['suspicious_patterns'] = self.detect_suspicious_patterns(
            bid_validation['sanitized_volumes'],
            ask_validation['sanitized_volumes']
        )

        # EstatÃÂ­sticas
        result['statistics'] = {
            'bid_levels': bid_validation['sanitized_count'],
            'ask_levels': ask_validation['sanitized_count'],
            'total_bid_volume': bid_validation['total_volume'],
            'total_ask_volume': ask_validation['total_volume'],
            'total_liquidity': bid_validation['total_volume'] + ask_validation['total_volume'],
            'bid_ask_ratio': (bid_validation['total_volume'] / ask_validation['total_volume'])
            if ask_validation['total_volume'] > 0 else float('inf')
        }

        # Determina recomendaÃÂ§ÃÂ£o final
        if result['issues'] or result['suspicious_patterns']:
            if self.enable_sanitization and not self.strict_mode:
                result['recommendation'] = 'sanitize'
                self.validation_stats['sanitized_data'] += 1
            else:
                result['recommendation'] = 'reject'
                result['valid'] = False
                self.validation_stats['rejected_data'] += 1
                return result

        # Atualiza estatÃÂ­sticas de issues comuns
        for issue in result['issues']:
            issue_type = issue.split(':')[0] if ':' in issue else issue
            self.validation_stats['common_issues'][issue_type] = self.validation_stats['common_issues'].get(
                issue_type, 0) + 1

        self.validation_stats['successful_validations'] += 1
        return result

    def get_validation_statistics(self) -> Dict[str, Any]:
        """Retorna estatÃÂ­sticas de validaÃÂ§ÃÂ£o acumuladas."""
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
        """Reseta as estatÃÂ­sticas de validaÃÂ§ÃÂ£o."""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'sanitized_data': 0,
            'rejected_data': 0,
            'common_issues': {}
        }


# InstÃÂ¢ncia global do validador
_csv_data_validator = CSVDataValidator()

# region [Sistema de Retry com Backoff Exponencial]


class RetryManager:
    """Gerenciador de tentativas com backoff exponencial para operaÃÂ§ÃÂµes de I/O."""

    def __init__(self, max_retries: int = 5, base_delay: float = 0.1, max_delay: float = 2.0):
        """Inicializa o gerenciador de retry.

        Args:
            max_retries: NÃÂºmero mÃÂ¡ximo de tentativas
            base_delay: Delay inicial em segundos
            max_delay: Delay mÃÂ¡ximo em segundos
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # EstatÃÂ­sticas de retry
        self.retry_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'error_types': {},
            'avg_retries_per_operation': 0.0
        }

    def calculate_delay(self, attempt: int) -> float:
        """Calcula o delay para uma tentativa especÃÂ­fica usando backoff exponencial.

        Args:
            attempt: NÃÂºmero da tentativa (0-based)

        Returns:
            Delay em segundos
        """
        # Backoff exponencial: base_delay * (2 ^ attempt)
        delay = self.base_delay * (2 ** attempt)

        # Adiciona jitter (variaÃÂ§ÃÂ£o aleatÃÂ³ria) para evitar thundering herd
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter

        # Limita ao delay mÃÂ¡ximo
        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determina se deve tentar novamente baseado no tipo de erro e tentativa.

        Args:
            exception: ExceÃÂ§ÃÂ£o que ocorreu
            attempt: NÃÂºmero da tentativa atual

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
            # Problemas de codificaÃÂ§ÃÂ£o (pode ser temporÃÂ¡rio)
            UnicodeDecodeError,
            IOError               # Problemas de entrada/saÃÂ­da
        )

        return isinstance(exception, retryable_errors)

    def get_error_strategy(self, exception: Exception) -> Dict[str, Any]:
        """Retorna estratÃÂ©gia especÃÂ­fica para cada tipo de erro.

        Args:
            exception: ExceÃÂ§ÃÂ£o que ocorreu

        Returns:
            DicionÃÂ¡rio com estratÃÂ©gia de tratamento
        """
        if isinstance(exception, PermissionError):
            return {
                'delay_multiplier': 1.5,  # Aguarda mais tempo para arquivo em uso
                'max_retries': 3,         # Menos tentativas para nÃÂ£o sobrecarregar
                'description': 'Arquivo em uso pelo EA'
            }

        elif isinstance(exception, FileNotFoundError):
            return {
                'delay_multiplier': 1.0,  # Delay normal
                'max_retries': 4,         # Mais tentativas para aguardar criaÃÂ§ÃÂ£o
                'description': 'Arquivo nÃÂ£o encontrado'
            }

        elif isinstance(exception, UnicodeDecodeError):
            return {
                'delay_multiplier': 0.5,  # Delay menor, problema pode ser rÃÂ¡pido
                'max_retries': 2,         # Poucas tentativas, detector jÃÂ¡ tenta outras codificaÃÂ§ÃÂµes
                'description': 'Erro de codificaÃÂ§ÃÂ£o'
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
        """Executa uma operaÃÂ§ÃÂ£o com retry automÃÂ¡tico.

        Args:
            operation_func: FunÃÂ§ÃÂ£o a ser executada
            *args: Argumentos posicionais para a funÃÂ§ÃÂ£o
            **kwargs: Argumentos nomeados para a funÃÂ§ÃÂ£o

        Returns:
            Resultado da operaÃÂ§ÃÂ£o ou None se todas as tentativas falharam
        """
        self.retry_stats['total_operations'] += 1
        last_exception = None

        # +1 para incluir tentativa inicial
        for attempt in range(self.max_retries + 1):
            try:
                # Tenta executar a operaÃÂ§ÃÂ£o
                result = operation_func(*args, **kwargs)

                # Sucesso!
                if attempt > 0:  # Se houve retry
                    self.retry_stats['total_retries'] += attempt
                    logging.info(
                        f"[RetryManager] OperaÃÂ§ÃÂ£o bem-sucedida apÃÂ³s {attempt} tentativas")

                self.retry_stats['successful_operations'] += 1
                self._update_avg_retries()
                return result

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Atualiza estatÃÂ­sticas de erro
                self.retry_stats['error_types'][error_type] = self.retry_stats['error_types'].get(
                    error_type, 0) + 1

                # Verifica se deve tentar novamente
                if not self.should_retry(e, attempt):
                    logging.debug(
                        f"[RetryManager] NÃÂ£o tentando novamente: {error_type} (tentativa {attempt + 1})")
                    break

                # ObtÃÂ©m estratÃÂ©gia especÃÂ­fica para o erro
                strategy = self.get_error_strategy(e)

                # Calcula delay ajustado pela estratÃÂ©gia
                base_delay = self.calculate_delay(attempt)
                adjusted_delay = base_delay * strategy['delay_multiplier']

                logging.debug(f"[RetryManager] {strategy['description']} - Tentativa {attempt + 1}/{self.max_retries + 1}, "
                              f"aguardando {adjusted_delay:.2f}s")

                # Aguarda antes da prÃÂ³xima tentativa
                time.sleep(adjusted_delay)

        # Todas as tentativas falharam
        self.retry_stats['failed_operations'] += 1
        self.retry_stats['total_retries'] += self.max_retries
        self._update_avg_retries()

        logging.warning(f"[RetryManager] OperaÃÂ§ÃÂ£o falhou apÃÂ³s {self.max_retries + 1} tentativas. "
                        f"ÃÅ¡ltimo erro: {last_exception}")

        return None

    def _update_avg_retries(self):
        """Atualiza a mÃÂ©dia de retries por operaÃÂ§ÃÂ£o."""
        if self.retry_stats['total_operations'] > 0:
            self.retry_stats['avg_retries_per_operation'] = self.retry_stats['total_retries'] / \
                self.retry_stats['total_operations']

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatÃÂ­sticas do gerenciador de retry."""
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
        """Reseta as estatÃÂ­sticas do retry manager."""
        self.retry_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'error_types': {},
            'avg_retries_per_operation': 0.0
        }


# InstÃÂ¢ncia global do retry manager
_retry_manager = RetryManager(max_retries=5, base_delay=0.1, max_delay=2.0)
# endregion


def ler_book_nativo() -> Optional[Dict[str, Any]]:
    """
    ========================================================================
    Ã°Å¸âÂ¡ LEITURA NATIVA DO BOOK (Depth of Market) DIRETO DO METATRADER 5
    ------------------------------------------------------------------------
    Substitui a antiga leitura do arquivo book_data_wdo.csv gerado pelo EA.
    Os dados vÃÂªm da memÃÂ³ria do terminal via mt5.market_book_get(SYMBOL),
    eliminando latÃÂªncia de escrita/leitura em disco e "dados congelados".

    A subscriÃÂ§ÃÂ£o ÃÂ© feita uma ÃÂºnica vez com mt5.market_book_add(SYMBOL) na
    inicializaÃÂ§ÃÂ£o (funÃÂ§ÃÂ£o inicializar_mt5) e cancelada com
    mt5.market_book_release(SYMBOL) no encerramento.

    Estrutura BookInfo retornada pelo MT5 (ver documentaÃÂ§ÃÂ£o oficial):
        type=1 -> ordem de VENDA  (ASK, preÃÂ§os acima do mercado)
        type=2 -> ordem de COMPRA (BID, preÃÂ§os abaixo do mercado)
        type=3 -> venda a mercado / type=4 -> compra a mercado
    Convertemos para o MESMO formato dict que o resto do cÃÂ³digo jÃÂ¡ usa:
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
        # it pode ser BookInfo (namedtuple) Ã¢â¬â acessa por atributo
        tipo = getattr(it, 'type', None)
        preco = getattr(it, 'price', 0.0)
        # volume_dbl ÃÂ© mais preciso; cai para volume se nÃÂ£o existir
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

    # Ordena: melhor BID = maior preÃÂ§o primeiro | melhor ASK = menor preÃÂ§o primeiro
    bids.sort(key=lambda x: x['price'], reverse=True)
    asks.sort(key=lambda x: x['price'])

    total_bid_volume = sum(b['volume'] for b in bids)
    total_ask_volume = sum(a['volume'] for a in asks)

    # Timestamp = relÃÂ³gio LOCAL (mesma base de timestamp_inicializacao = time.time()).
    # Ã¢Å¡Â Ã¯Â¸Â NÃÆO usar tick.time do MT5 aqui: ele vem no fuso do servidor da corretora
    # (nÃÂ£o ÃÂ© POSIX/UTC local) e a TRAVA o interpretaria como "dado antigo", bloqueando
    # TODAS as operaÃÂ§ÃÂµes. O book nativo ÃÂ© sempre AO VIVO (se o mercado fecha, o
    # market_book_get retorna vazio e jÃÂ¡ saÃÂ­mos com None acima), entÃÂ£o o problema de
    # "dado velho de sessÃÂ£o anterior" Ã¢â¬â que era exclusivo do CSV/EA Ã¢â¬â nÃÂ£o existe aqui.
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
# Ã°Å¸âÂ¡ LEITURA DO BOOK DO DÃâLAR CHEIO (DOL) Ã¢â¬â REFERÃÅ NCIA INSTITUCIONAL
# ------------------------------------------------------------------------
# O DOL ÃÂ© onde os grandes players (bancos, fundos) operam de verdade.
# O WDO ÃÂ© replicado por HFTs que espelham o DOL com milissegundos de
# atraso. Ler o DOL permite antecipar movimentos do WDO.
# ========================================================================

def ler_book_dol() -> Optional[Dict[str, Any]]:
    """LÃÂª o book do DÃÂ³lar Cheio (DOL) Ã¢â¬â mesmo formato de ler_book_nativo."""
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
      - ratio: desequilÃÂ­brio bid/ask (>1 = mais compras, <1 = mais vendas)
      - lado: "BUY", "SELL" ou "NEUTRO"
      - confianca: 0.0 a 1.0 (baseado no desequilÃÂ­brio)
      - volume_total: volume total do book DOL
      - presente: True se DOL estÃÂ¡ disponÃÂ­vel
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

    # Determina lado e confianÃÂ§a
    if total_bid > total_ask:
        resultado['lado'] = 'BUY'
        # ConfianÃÂ§a: quanto maior o ratio, mais confianÃÂ§a (mÃÂ¡x 1.0 em ratio 3.0+)
        resultado['confianca'] = min(ratio / 3.0, 1.0)
    elif total_ask > total_bid:
        resultado['lado'] = 'SELL'
        resultado['confianca'] = min(ratio / 3.0, 1.0)
    else:
        resultado['lado'] = 'NEUTRO'

    return resultado# ========================================================================
# Ã°Å¸ââÃ¯Â¸Â LEITURA VIA CSV/EA REMOVIDA (MUDANÃâ¡A 1 Ã¢â¬â ARQUITETURA NATIVA)
# As antigas funÃÂ§ÃÂµes _ler_book_csv_core / ler_book_csv_with_retry / ler_book_csv
# foram eliminadas. Toda a leitura do book agora ÃÂ© nativa via ler_book_nativo()
# (mt5.market_book_get). NÃÂ£o hÃÂ¡ mais dependÃÂªncia do EA MQL5 nem de arquivos CSV.
# ========================================================================


def inicializar_mt5() -> bool:
    global trailing_stop, balanceador, detector_modo, balanceador, detector_modo, circuit_breaker, saida_inteligente, sistema_confluencia

    aguardar_abertura()
    logging.info("Ã°Å¸ââ Tentando inicializar o MetaTrader 5...")
    if not mt5.initialize(path=MT5_PATH):
        logging.error(f"Ã¢ÂÅ Erro ao inicializar MT5: {mt5.last_error()}")
        return False
    logging.info("Ã¢Åâ¦ MetaTrader 5 inicializado com sucesso")

    # ===== INICIALIZAÃâ¡ÃÆO DOS SUBSISTEMAS (silenciosa Ã¢â¬â sem propaganda) =====
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
        "Ã°Å¸Â§Â© Subsistemas ativos: Trailing | Balanceamento | Modos | CircuitBreaker | "
        "SaÃÂ­daInteligente | ConfluÃÂªncia | HorÃÂ¡rio | TendÃÂªncia | Cooldown | Spread | Performance")

    # ===== ARQUITETURA NATIVA: BOOK DIRETO DO MT5 (SEM EA / SEM CSV) =====
    global SYMBOL
    terminal_info = mt5.terminal_info()
    if not terminal_info:
        logging.error("Ã¢ÂÅ NÃÂ£o foi possÃÂ­vel obter informaÃÂ§ÃÂµes do terminal MT5")
        return False
    logging.info(
        "Ã°Å¸âÂ¡ Fonte de dados: BOOK NATIVO (mt5.market_book_get) Ã¢â¬â EA/CSV eliminados")

    # SeleÃÂ§ÃÂ£o dinÃÂ¢mica do contrato WDO
    SYMBOL = get_front_month_symbol_dynamic("WDO")
    mt5.symbol_select(SYMBOL, True)

    # Subscreve o book (Depth of Market) do contrato na memÃÂ³ria do terminal.
    # A partir daqui ler_book_nativo() recebe atualizaÃÂ§ÃÂµes em tempo real.
    if mt5.market_book_add(SYMBOL):
        logging.info(f"[BOOK] Book nativo ATIVADO para {SYMBOL} (Depth of Market)")
    else:
        logging.warning(
            f"Ã¢Å¡Â Ã¯Â¸Â market_book_add falhou para {SYMBOL}: {mt5.last_error()} "
            f"(o book pode ainda assim responder Ã¢â¬â seguindo)")

    # Extrai a validade do sÃÂ­mbolo (ex: WDOQ26 -> Q26)
    validade = SYMBOL[-3:] if len(SYMBOL) >= 3 else SYMBOL
    logging.info(
        f"Ã¢Åâ¦ Contrato WDO dinÃÂ¢mico selecionado: {SYMBOL} (venc.: {validade})")

    # ===== DÃâLAR CHEIO (DOL) Ã¢â¬â REFERÃÅ NCIA DE FLUXO INSTITUCIONAL =====
    global SYMBOL_DOL
    SYMBOL_DOL = get_front_month_symbol_dynamic("DOL")
    if SYMBOL_DOL:
        mt5.symbol_select(SYMBOL_DOL, True)
        if mt5.market_book_add(SYMBOL_DOL):
            logging.info(
                f"[BOOK DOL] Book nativo ATIVADO para {SYMBOL_DOL} (referÃÂªncia institucional)")
        else:
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â market_book_add falhou para DOL {SYMBOL_DOL}: {mt5.last_error()}")
    else:
        logging.warning(
            "Ã¢Å¡Â Ã¯Â¸Â DOL nÃÂ£o encontrado Ã¢â¬â operando sem referÃÂªncia institucional")

    logging.info(
        f"Ã°Å¸Å½Â¯ ConfiguraÃÂ§ÃÂ£o WDO: SL={SL_POINTS}pts, TP={TP_POINTS}pts, Vol={VOLUME_PADRAO}cc")
    logging.info(
        f"Ã°Å¸âÅ  WDO Specs: Tick={TICK_SIZE}, TicksPorPonto={TICKS_POR_PONTO}, Magic={MAGIC_NUMBER}")
    logging.info(
        f"Ã°Å¸âÂ° Risk: MaxLoss={MAX_LOSS_DIARIO}, MaxSpread={MAX_SPREAD}pts, MinVol={MIN_VOLUME_BOOK}cc")

    return True


def obter_dados_mercado(symbol: str = None, timeframe: int = TIMEFRAME) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[str], Optional[Dict], Optional[float], Optional[int], Optional[float], Optional[float]]:
    """ObtÃÂ©m dados atuais do mercado USANDO O BOOK NATIVO DO MT5."""
    global SYMBOL
    if not hasattr(obter_dados_mercado, '_log_counter'):
        obter_dados_mercado._log_counter = 0
    if symbol is None:
        symbol = SYMBOL
    if symbol is None:
        logging.error("Ã¢ÂÅ SYMBOL ainda nÃÂ£o foi definido!")
        return (None,) * 10

    # Pulso de standby: loga no mÃÂ¡ximo 1x a cada 60s (sÃÂ³ "sinal de vida" + mercado).
    # NÃÆO afeta o robÃÂ´ Ã¢â¬â ele continua lendo o book e decidindo a cada ciclo.
    log_time = _log_periodico('pulso_mercado', PULSO_LOG_INTERVALO_S)

    # Inicializa todas as variÃÂ¡veis com valores padrÃÂ£o para evitar erros
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
        # Verifica se ÃÂ© fim de semana
        if datetime.now().weekday() > 4:  # 5 = SÃÂ¡bado, 6 = Domingo
            if log_time:
                logging.info("Ã°Å¸ââ¦ Fim de semana: aguardando prÃÂ³ximo dia ÃÂºtil...")
            time.sleep(30)  # Dorme por 30 segundos durante fim de semana
            return (None,) * 10

        # ===== LEITURA NATIVA DO BOOK (DIRETO DO MT5, SEM EA/CSV) =====
        book_data = ler_book_nativo()
        if not book_data or not book_data.get('bids') or not book_data.get('asks'):
            if log_time:
                # Ã¢Åâ¦ MODO SNIPER: log reduzido Ã¢â¬â standby silencioso aguardando sinal institucional
                logging.debug(
                    "Ã°Å¸ËÂ´ Standby: Aguardando book nativo com liquidez do MT5...")
            # Dorme 1s sem sinal (book nativo ÃÂ© rÃÂ¡pido, nÃÂ£o precisa 2s)
            time.sleep(1)
            return (None,) * 10

        # Calcula volumes totais do book do EA
        # CORREÃâ¡ÃÆO: book_data agora contÃÂ©m dicionÃÂ¡rios com price/volume
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

        # Log de mercado Ã¢â¬â informaÃÂ§ÃÂ£o REAL e ÃÂºtil: preÃÂ§o ao vivo, spread,
        # volumes BID/ASK, desequilÃÂ­brio e lado dominante do fluxo.
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
            lado = "Ã°Å¸Å¸Â¢COMPRA" if total_bid_volume > total_ask_volume else "Ã°Å¸âÂ´VENDA"
            obter_dados_mercado._log_counter += 1
            if obter_dados_mercado._log_counter % 5 == 1:
                logging.info(
                    f"Ã°Å¸âÅ  {symbol} | PreÃÂ§o: {preco_vivo:.0f} | Spread: {spread_atual}pts | "
                    f"BID: {total_bid_volume:.0f} / ASK: {total_ask_volume:.0f} | "
                    f"DesequilÃÂ­brio: {ratio_book:.2f}x {lado}")

        # Verifica liquidez mÃÂ­nima
        if total_volume < MIN_VOLUME_BOOK:
            if log_time:
                logging.warning(
                    f"Ã¢ÂÅ Liquidez insuficiente: {total_volume} < {MIN_VOLUME_BOOK}")
            return (None,) * 10

        # ObtÃÂ©m dados complementares do MT5
        tick_info = mt5.symbol_info_tick(symbol)
        symbol_info = get_cached_symbol_info(symbol)
        if tick_info is None:
            if log_time:
                logging.warning(f"Ã¢ÂÅ Tick NULO para sÃÂ­mbolo {symbol}")
            return (None,) * 10
        if symbol_info is None:
            if log_time:
                logging.warning(f"Ã¢ÂÅ Symbol_info NULO para sÃÂ­mbolo {symbol}")
            # Tenta reselecionar o sÃÂ­mbolo
            mt5.symbol_select(symbol, True)
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logging.error(
                    f"Ã¢ÂÅ NÃÂ£o foi possÃÂ­vel obter info do sÃÂ­mbolo {symbol} mesmo apÃÂ³s reselecionar")
            return (None,) * 10

        # Calcula spread em pontos
        spread = ((tick_info.ask - tick_info.bid) /
                  symbol_info.point) / TICKS_POR_PONTO

        # Verifica spread mÃÂ¡ximo
        if spread > MAX_SPREAD:
            if log_time:
                logging.warning(f"Ã¢ÂÅ Spread muito alto: {spread:.1f} pts")
            return (None,) * 10

        # ObtÃÂ©m dados de velas
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
        if rates is None or len(rates) < 2:
            if log_time:
                logging.warning("Ã¢ÂÅ Rates insuficientes")
            return (None,) * 10

        # ObtÃÂ©m dados bÃÂ¡sicos primeiro (antes de cÃÂ¡lculos que podem falhar)
        last_candle = rates[-1]
        close_price = float(last_candle[4])  # close price da ÃÂºltima vela
        volume_tick = int(tick_info.volume)

        # Calcula indicadores
        df_rates = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])

        # Calcula ATR com tratamento de erro
        try:
            atr = calcular_atr(df_rates['high'].tolist(
            ), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)
        except Exception as e:
            logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â Erro no cÃÂ¡lculo ATR: {e}")
            atr = 50.0  # Valor padrÃÂ£o

        # Calcula tipo de vela com tratamento de
        try:
            candle_type = obter_nome_vela(
                last_candle[1], last_candle[4], last_candle[2], last_candle[3])
        except Exception as e:
            logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â Erro no tipo de vela: {e}")
            candle_type = "doji"

        # Calcula RSI com tratamento de erro
        try:
            rsi_14 = calcular_rsi(df_rates['close'].tolist(), 14)
        except Exception as e:
            logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â Erro no cÃÂ¡lculo RSI: {e}")
            rsi_14 = 50.0  # Valor padrÃÂ£o

        # Calcula Williams %R (Larry Williams) com tratamento de erro
        try:
            williams_r = calcular_williams_r(
                df_rates['high'].tolist(), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)
        except Exception as e:
            logging.warning(f"Ã¢Å¡Â Ã¯Â¸Â Erro no cÃÂ¡lculo Williams %R: {e}")
            williams_r = -50.0  # Valor padrÃÂ£o

        # Log detalhado dos dados do EA
        if log_time:
            logging.debug(
                f"Ã°Å¸âÅ  EA Data - Bid Vol: {total_bid_volume}, Ask Vol: {total_ask_volume}")

        return total_bid_volume, total_ask_volume, spread, atr, candle_type, book_data, rsi_14, volume_tick, close_price, williams_r

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao obter dados do mercado (EA): {e}")
        return (None,) * 10


def volume_crescente(n: int = 2, symbol: str = None, timeframe: int = TIMEFRAME) -> bool:
    """Verifica se o volume estÃÂ¡ crescente nos ÃÂºltimos n candles."""
    global SYMBOL
    if symbol is None:
        symbol = SYMBOL
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n + 1)
    if rates is None or len(rates) < n + 1:
        return False

    volumes = [rate[5] for rate in rates]  # rate[5] ÃÂ© o volume
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
    """Verifica se o book estÃÂ¡ equilibrado o suficiente para operar."""
    if bid_qty == 0 or ask_qty == 0:
        return False, "Book zerado em um dos lados"

    # Calcula razÃÂ£o entre volumes (sempre menor/maior para ter ratio <= 1)
    ratio = min(bid_qty, ask_qty) / max(bid_qty, ask_qty)

    # Identifica qual lado estÃÂ¡ mais forte
    lado_forte = "compra" if bid_qty > ask_qty else "venda"
    logging.debug(f"Ã°Å¸âÅ  Book - Ratio: {ratio:.3f} | Lado forte: {lado_forte}")

    if ratio < MIN_RATIO_BOOK:
        lado_menor = "compra" if bid_qty < ask_qty else "venda"
        return False, f"Book muito desequilibrado (ratio={ratio:.3f}). Lado fraco: {lado_menor}"

    # CORREÃâ¡ÃÆO: PressÃÂ£o forte indica BIG PLAYERS - SEGUIR, nÃÂ£o bloquear!
    max_ratio_pressao = 10.0  # Permite atÃÂ© 10:1 (big players massivos)
    if max(bid_qty, ask_qty) / min(bid_qty, ask_qty) > max_ratio_pressao:
        logging.warning(
            f"Ã¢Å¡Â Ã¯Â¸Â PressÃÂ£o EXTREMA no lado de {lado_forte} - PossÃÂ­vel manipulaÃÂ§ÃÂ£o")
        return False, f"PressÃÂ£o EXTREMA no lado de {lado_forte}"
    elif max(bid_qty, ask_qty) / min(bid_qty, ask_qty) > 3.0:
        logging.info(
            f"Ã°Å¸Ââ¹ BIG PLAYERS detectados no lado de {lado_forte} - OPORTUNIDADE!")

    return True, ""


class ModoOperacional:
    """Gerencia os modos operacionais do robÃÂ´."""

    def __init__(self):
        self.modo_atual = "NORMAL"
        self.inicio_defesa = None
        self.losses_seguidos = 0
        self.volume_anterior = 0
        self.ultimo_lucro = 0

    def atualizar_modo(self, atr: float, entropia: float, volume_atual: float,
                       bid_qty: float, ask_qty: float) -> str:
        """Atualiza o modo operacional baseado nas condiÃÂ§ÃÂµes do mercado."""
        # Verifica se pode sair do modo defesa
        if self.modo_atual == "DEFESA":
            if self.inicio_defesa and (datetime.now() - self.inicio_defesa).total_seconds() > TEMPO_DEFESA * 60:
                self.modo_atual = "NORMAL"
                self.losses_seguidos = 0
                logging.info(
                    "Ã°Å¸âºÂ¡Ã¯Â¸Â Saindo do modo defesa apÃÂ³s perÃÂ­odo de observaÃÂ§ÃÂ£o")
            else:
                return "DEFESA"

        # Verifica equilÃÂ­brio do book
        book_equilibrado, msg = verificar_book_equilibrado(bid_qty, ask_qty)
        if not book_equilibrado:
            if self.modo_atual != "AGUARDANDO":
                logging.info(f"Ã¢ÂÂ³ Entrando em modo aguardando - {msg}")
            return "AGUARDANDO"

        # Verifica condiÃÂ§ÃÂµes para modo lateralidade
        if atr < THRESHOLD_ATR_BAIXO and entropia < THRESHOLD_ENTROPIA_BAIXA:
            if self.modo_atual != "LATERAL":
                logging.info(
                    "Ã¢â âÃ¯Â¸Â Entrando em modo lateralidade - Baixa volatilidade e entropia")
            return "LATERAL"

        # Verifica condiÃÂ§ÃÂµes para modo explosÃÂ£o - VOLUME MÃÂNIMO 1000cc
        crescimento_volume = volume_atual / \
            self.volume_anterior if self.volume_anterior > 0 else 1
        if (entropia > THRESHOLD_ENTROPIA_ALTA and
                crescimento_volume > MIN_VOLUME_CRESCIMENTO and
                volume_atual >= 1000):  # FILTRO: SÃÂ³ explosÃÂ£o com 1000cc+
            if self.modo_atual != "EXPLOSAO":
                logging.info(
                    f"Ã°Å¸âÂ¥ Entrando em modo explosÃÂ£o - Alta entropia ({entropia:.2f}), volume crescente ({crescimento_volume:.1f}x) e liquidez alta ({volume_atual}cc)")
            return "EXPLOSAO"

        # Modo normal como fallback
        return "NORMAL"

    def registrar_resultado(self, lucro: float) -> None:
        """Registra resultado da operaÃÂ§ÃÂ£o e atualiza contadores."""
        if lucro < 0:
            self.losses_seguidos += 1
            if self.losses_seguidos >= MAX_LOSSES_SEGUIDOS:
                self.modo_atual = "DEFESA"
                self.inicio_defesa = datetime.now()
                logging.warning(
                    f"Ã¢Å¡Â Ã¯Â¸Â {MAX_LOSSES_SEGUIDOS} losses seguidos - Entrando em modo defesa")
        else:
            self.losses_seguidos = 0
        self.ultimo_lucro = lucro

    def ajustar_parametros_operacionais(self, volume_book_total: float = 1000) -> Dict[str, float]:
        """Ajusta parÃÂ¢metros baseado no modo atual com volume inteligente."""
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
                # Reduz volume mas mÃÂ­nimo 1cc
                'volume': max(1.0, volume_inteligente * 0.5),
                'sl_mult': MULTIPLICADOR_SL_ATR * 0.7,  # Reduz SL
                'tp_mult': MULTIPLICADOR_TP_ATR * 0.7,  # Reduz TP
            })

        elif self.modo_atual == "EXPLOSAO":
            # Modo mais agressivo - mas WDO: mÃÂ¡ximo 2 contratos
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
            # Modo apenas observaÃÂ§ÃÂ£o
            params.update({
                'volume': 0,  # NÃÂ£o opera
            })

        return params


def executar_ordem(action, lots=VOLUME_PADRAO, symbol=None, modo_operacional=None, sniper=False,
                   sl_points_override=None, tp_points_override=None,
                   magic_override=None, comment=None, shadow=True):
    """Executa uma ordem de compra ou venda com SL/TP calculados. magic_override permite Magic 7007 (7 Velas)."""

    # Gate exclusivo Faixa 1: apenas magic=7007 passa durante SETE_VELAS_EXCLUSIVO
    if ESTADO_SISTEMA == "SETE_VELAS_EXCLUSIVO" and (magic_override or MAGIC_NUMBER) != MAGIC_SETE_VELAS:
        logging.warning(f"[GATE 7 VELAS] Ordem bloqueada para {symbol or SYMBOL} (apenas Magic 7007 na Faixa 1)")
        return None

    # magic efetivo: override (7 Velas) ou padrao do robo
    magic_final = magic_override if magic_override is not None else MAGIC_NUMBER
    # SniperSupermo pula esta verificaÃÂ§ÃÂ£o (opera 09:00-17:30)
    if not sniper and not horario_permitido():
        horario_atual = datetime.now().strftime("%H:%M")
        logging.warning(
            f"Ã°Å¸Å¡Â« PA1 ORDEM BLOQUEADA POR HORÃÂRIO: {horario_atual} - SÃÂ³ executa 09:15-12:30 e 14:30-17:15")
        return None

    # Usa SYMBOL global se nÃÂ£o especificado
    if symbol is None:
        symbol = SYMBOL

    # Verifica se o sÃÂ­mbolo estÃÂ¡ definido
    if symbol is None:
        logging.error(
            "Ã¢ÂÅ SYMBOL nÃÂ£o estÃÂ¡ definido! NÃÂ£o ÃÂ© possÃÂ­vel executar ordem.")
        return None

        logging.info(f"Ã°Å¸âÂ§ Executando ordem {action} para sÃÂ­mbolo: {symbol}")

    # Verifica conexÃÂ£o MT5
    if not mt5.initialize():
        logging.error("Ã¢ÂÅ MT5 nÃÂ£o estÃÂ¡ inicializado! Tentando reconectar...")
        if not reconectar_mt5():
            logging.error("Ã¢ÂÅ Falha ao reconectar MT5")
            return None

    if modo_operacional and modo_operacional.modo_atual == "DEFESA":
        logging.info("Ã°Å¸âºÂ¡Ã¯Â¸Â Ordem bloqueada - Modo defesa ativo")
        return None

    # ObtÃÂ©m parÃÂ¢metros ajustados para o modo atual
    params = modo_operacional.ajustar_parametros_operacionais() if modo_operacional else {
        'volume': lots,
        'sl_mult': MULTIPLICADOR_SL_ATR,
        'tp_mult': MULTIPLICADOR_TP_ATR
    }
    # Override de volume para SniperSupermo (lots diferente do padrÃÂ£o)
    if abs(lots - VOLUME_PADRAO) > 0.001:
        params['volume'] = lots

    # Verifica estado do mercado
    mercado_aberto, msg = verificar_mercado_aberto()
    if not mercado_aberto:
        logging.warning(f"Ã¢ÂÅ Ordem nÃÂ£o enviada: {msg}")
        return None

    tipo = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL

    # DiagnÃÂ³stico detalhado dos dados de mercado
    tick = mt5.symbol_info_tick(symbol)
    symbol_info = get_cached_symbol_info(symbol)

    if tick is None:
        logging.error(f"Ã¢ÂÅ Tick ÃÂ© None para sÃÂ­mbolo {symbol}")
        # Tenta reselecionar o sÃÂ­mbolo e obter tick novamente
        mt5.symbol_select(symbol, True)
        time.sleep(0.1)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.error(f"Ã¢ÂÅ Tick ainda ÃÂ© None apÃÂ³s reselecionar {symbol}")
            return None

    if symbol_info is None:
        logging.error(f"Ã¢ÂÅ Symbol_info ÃÂ© None para sÃÂ­mbolo {symbol}")
        # Limpa cache e tenta novamente
        get_cached_symbol_info.cache_clear()
        symbol_info = get_cached_symbol_info(symbol)
        if symbol_info is None:
            logging.error(
                f"Ã¢ÂÅ Symbol_info ainda ÃÂ© None apÃÂ³s limpar cache para {symbol}")
            return None

    logging.info(
        f"Ã¢Åâ¦ Dados obtidos - Tick: Ask={tick.ask}, Bid={tick.bid}, Symbol: {symbol_info.name}")

    if tick is None or symbol_info is None:
        logging.warning(
            "Dados de mercado indisponÃÂ­veis apÃÂ³s tentativas de correÃÂ§ÃÂ£o")
        return None

    # Verifica spread
    if not verificar_spread_maximo(symbol_info, tick):
        logging.warning(
            f"Ã¢ÂÅ Spread muito alto: {(tick.ask - tick.bid) / symbol_info.point:.1f}")
        return None

    preco = tick.ask if action == 'BUY' else tick.bid
    preco = arredondar_preco(preco)

    # Garante que o volume seja float e no mÃÂ­nimo 1.0
    lote_corrigido = float(max(1, round(params['volume'])))
    logging.info(f"Ã°Å¸âÅ  Volume ajustado: {lote_corrigido:.1f} contratos")

    # ========== WDO: SL=5 (seguranÃÂ§a), TP=0 (saÃÂ­da dinÃÂ¢mica por Keras+Book) ==========
    # Sniper %R passa SL/TP por ATR (sl_points_override / tp_points_override)
    sl_points_dinamico = sl_points_override if sl_points_override else SL_POINTS  # 5 pontos WDO (mÃÂ¡ximo)
    tp_points_dinamico = tp_points_override if tp_points_override is not None else TP_POINTS  # 0 = SEM TP Ã¢â¬â GerenciadorDeSaida decide
    logging.info(
        f"Ã°Å¸âºÂ¡Ã¯Â¸Â WDO CONFIG: SL={sl_points_dinamico}pts, TP={tp_points_dinamico} (saÃÂ­da dinÃÂ¢mica)")

    # Calcula SL e TP com valores dinÃÂ¢micos
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
        "magic": magic_final,
        "comment": comment or f"Monstro {action}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Envia ordem
    resultado = mt5.order_send(request)

    # Ã°Å¸âÂ§ CORREÃâ¡ÃÆO CRÃÂTICA 3: Verificar se resultado nÃÂ£o ÃÂ© None
    if resultado is None:
        logging.error(
            "Ã¢ÂÅ Erro crÃÂ­tico: mt5.order_send retornou None (falha de conexÃÂ£o)")
        return None

    if resultado.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(
            f"Ã¢ÂÅ Falha ao executar ordem {action}: {resultado.retcode} - {resultado.comment}")
        return None

    logging.info(f"Ã¢Åâ¦ Ordem {action} executada. Ticket: {resultado.order}")
    logging.info(
        f"   PreÃÂ§o: {preco:.3f} | SL: {sl_calculado:.3f} | TP: {'SEM TP (saÃÂ­da dinÃÂ¢mica)' if tp_calculado == 0 else f'{tp_calculado:.3f}'}")

    # SHADOW MODE: registra prob do Modelo A sem interferir na execucao
    shadow_registrar_entrada(resultado.order, action, symbol)

    # Aguarda um momento para o MT5 processar
    time.sleep(0.5)

    # Verifica se a ordem virou posiÃÂ§ÃÂ£o
    for _ in range(3):  # Tenta atÃÂ© 3 vezes
        positions = mt5.positions_get(ticket=resultado.order)
        if positions and len(positions) > 0:
            pos = positions[0]
            logging.info(f"Ã¢Åâ¦ Ordem {resultado.order} virou posiÃÂ§ÃÂ£o.")

            # ========== INTEGRAÃâ¡ÃÆO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
            if trailing_stop and TRAILING_ATIVO:
                trailing_stop.iniciar_trailing(
                    resultado.order, action, preco, sl_calculado)
                logging.info(
                    f"Ã°Å¸Å½Â¯ Trailing stop iniciado para posiÃÂ§ÃÂ£o {resultado.order}")

            # ========== INTEGRAÃâ¡ÃÆO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
            if balanceador and BALANCEAMENTO_ATIVO:
                balanceador.registrar_operacao(action)
                status = balanceador.get_status()
                logging.info(
                    f"Ã¢Å¡âÃ¯Â¸Â OperaÃÂ§ÃÂ£o {action} registrada. BUY: {status['buy_count']}, SELL: {status['sell_count']} (BUY: {status['buy_percentage']:.1f}%)")

            # SAÃÂDA INTELIGENTE ANTIGA DESATIVADA Ã¢â¬â usa GerenciadorDeSaida no loop principal
            # (evita conflito entre dois sistemas de saÃÂ­da simultÃÂ¢neos)

            # ========== INTEGRAÃâ¡ÃÆO PASSO 2: GERENCIADOR DE SAÃÂDA UNIFICADO ==========
            # ATIVA O GERENCIADOR DE SAÃÂDA (precisa ser passado como parÃÂ¢metro global)
            # gerenciador_saida.iniciar_monitoramento(pos)

            return resultado.order
        time.sleep(0.2)

    logging.warning(
        f"Ã¢Å¡Â Ã¯Â¸Â NÃÂ£o foi possÃÂ­vel confirmar se ordem {resultado.order} virou posiÃÂ§ÃÂ£o")
    return resultado.order


def verificar_se_ordem_virou_posicao(ticket: Optional[int], symbol: str = SYMBOL) -> bool:
    """Verifica se uma ordem se transformou em posiÃÂ§ÃÂ£o."""
    if ticket is None:
        return False

    positions = retry_positions_get(symbol)
    if positions is None:
        return False

    return any(
        pos.ticket == ticket and pos.magic == MAGIC_NUMBER
        for pos in positions
    )


ARQ_PENDENTES_RECONCILIACAO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pendentes_reconciliacao.json")


def _pendentes_carregar() -> dict:
    """Carrega a fila persistente de posicoes pendentes de reconciliacao."""
    try:
        if os.path.exists(ARQ_PENDENTES_RECONCILIACAO):
            with open(ARQ_PENDENTES_RECONCILIACAO, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"[RECON] Falha ao carregar pendentes: {e}")
    return {}


def _pendentes_salvar(pendentes: dict) -> None:
    """Persiste a fila de posicoes pendentes de reconciliacao."""
    try:
        with open(ARQ_PENDENTES_RECONCILIACAO, "w", encoding="utf-8") as f:
            json.dump(pendentes, f, ensure_ascii=False, indent=1)
    except Exception as e:
        logging.warning(f"[RECON] Falha ao salvar pendentes: {e}")


def adicionar_pendente_reconciliacao(ticket: int, direcao: str, entrada: float) -> None:
    """Marca uma posicao em PENDING_RECONCILIATION ate o deal real aparecer."""
    try:
        pendentes = _pendentes_carregar()
        pendentes[str(ticket)] = {
            "direcao": direcao,
            "entrada": entrada,
            "timestamp": datetime.now().isoformat(),
        }
        _pendentes_salvar(pendentes)
        logging.warning(
            f"[RECON] Posicao #{ticket} ({direcao}) entrou em PENDING_RECONCILIATION.")
    except Exception as e:
        logging.warning(f"[RECON] Falha ao registrar pendente #{ticket}: {e}")


def buscar_deal_historico_estendido(ticket_ordem_abertura: Optional[int],
                                    tentativas: int = 5,
                                    intervalo_s: float = 1.5) -> float:
    """Reconsulta o historico de deals com retries para capturar a saida que o
    terminal ainda nao sincronizou (fix v22.1). Retorna o lucro real, 0.0 se nada."""
    if ticket_ordem_abertura is None:
        return 0.0
    for tentativa in range(tentativas):
        try:
            data_inicio = datetime.now() - timedelta(days=7)
            deals = mt5.history_deals_get(data_inicio, datetime.now())
            if deals:
                saidas = [d for d in deals
                          if d.position_id == ticket_ordem_abertura
                          and d.entry == mt5.DEAL_ENTRY_OUT]
                if saidas:
                    final = max(saidas, key=lambda d: d.time_msc)
                    lucro = final.profit
                    shadow_registrar_resultado(ticket_ordem_abertura, lucro)
                    logging.info(
                        f"[RECON] Deal de saida capturado apos retry {tentativa + 1}/"
                        f"{tentativas} para #{ticket_ordem_abertura}: Lucro={lucro:.2f}")
                    return lucro
        except Exception as e:
            logging.warning(f"[RECON] Erro na tentativa {tentativa + 1}: {e}")
        time.sleep(intervalo_s)
    logging.warning(
        f"[RECON] Nao foi possivel localizar saida de #{ticket_ordem_abertura} "
        f"apos {tentativas} tentativas.")
    return 0.0


def reconciliar_pendentes() -> None:
    """Processa a fila persistente: tenta achar o deal real e fecha o ciclo."""
    try:
        pendentes = _pendentes_carregar()
        if not pendentes:
            return
        removidos = []
        for ticket_str, info in list(pendentes.items()):
            ticket = int(ticket_str)
            d = None
            try:
                data_inicio = datetime.now() - timedelta(days=7)
                deals = mt5.history_deals_get(data_inicio, datetime.now())
                if deals:
                    saidas = [x for x in deals
                              if x.position_id == ticket
                              and x.entry == mt5.DEAL_ENTRY_OUT]
                    if saidas:
                        d = max(saidas, key=lambda x: x.time_msc)
            except Exception as e:
                logging.warning(f"[RECON] Erro ao reconciliar #{ticket}: {e}")
            if d is not None:
                shadow_registrar_resultado(ticket, d.profit)
                logging.info(
                    f"[RECON] Pendente #{ticket} reconciliado: Lucro={d.profit:.2f}")
                removidos.append(ticket_str)
        for chave in removidos:
            pendentes.pop(chave, None)
        if removidos:
            _pendentes_salvar(pendentes)
    except Exception as e:
        logging.warning(f"[RECON] Falha na reconciliacao de pendentes: {e}")


def obter_lucro_ultima_ordem(ticket_ordem_abertura: Optional[int] = None) -> Tuple[float, float]:
    """ObtÃÂ©m o lucro e score da ÃÂºltima ordem fechada, com base no ticket da ordem de abertura."""
    logging.info(
        f"Ã°Å¸âÂ Tentando obter lucro para ticket de ordem de abertura: {ticket_ordem_abertura}")
    if ticket_ordem_abertura is None:
        logging.warning(
            "Ã¢Å¡Â Ã¯Â¸Â obter_lucro_ultima_ordem chamada sem ticket_ordem_abertura. Retornando 0.0, 0.0")
        return 0.0, 0.0

    # Buscar deals dos ÃÂºltimos X dias para garantir que cobrimos a vida da ordem.
    # Aumentar o timedelta se as posiÃÂ§ÃÂµes puderem ficar abertas por mais tempo.
    data_inicio_busca = datetime.now() - timedelta(days=7)
    deals = mt5.history_deals_get(data_inicio_busca, datetime.now())

    if not deals:
        logging.warning(
            f"Ã°Å¸âÂ° Nenhum deal encontrado nos ÃÂºltimos 7 dias. NÃÂ£o foi possÃÂ­vel obter lucro para ticket {ticket_ordem_abertura}.")
        return 0.0, 0.0

        logging.debug(
            f"Ã°Å¸âÂ Encontrados {len(deals)} deals nos ÃÂºltimos 7 dias para anÃÂ¡lise do ticket {ticket_ordem_abertura}.")

    # Filtra deals de SAÃÂDA (mt5.DEAL_ENTRY_OUT) cuja position_id corresponde ao ticket da ORDEM de abertura.
    deals_de_saida_relevantes = [
        d for d in deals if d.position_id == ticket_ordem_abertura and d.entry == mt5.DEAL_ENTRY_OUT
    ]

    if not deals_de_saida_relevantes:
        logging.warning(
            f"Ã°Å¸âÂ° Nenhum DEAL DE SAÃÂDA encontrado para a ordem com ticket (position_id) {ticket_ordem_abertura}.")
        # Isso pode significar que a posiÃÂ§ÃÂ£o ainda estÃÂ¡ aberta, foi fechada manualmente de forma nÃÂ£o rastreÃÂ¡vel aqui,
        # ou o deal de saÃÂ­da ainda nÃÂ£o foi registrado no histÃÂ³rico.
        return 0.0, 0.0

    # Se houver mÃÂºltiplos deals de saÃÂ­da (ex: TPs parciais), ÃÂ© importante decidir como agregar.
    # Para este caso, vamos pegar o deal de saÃÂ­da MAIS RECENTE para calcular o lucro final da posiÃÂ§ÃÂ£o.
    # Ou, se for uma ÃÂºnica saÃÂ­da, este serÃÂ¡ o deal.
    # Se for necessÃÂ¡rio somar lucros de saÃÂ­das parciais, a lÃÂ³gica aqui precisaria ser mais elaborada.
    # Usar time_msc para maior precisÃÂ£o
    deal_final_de_saida = max(
        deals_de_saida_relevantes, key=lambda d: d.time_msc)

    lucro_total_operacao = deal_final_de_saida.profit
    # O atributo 'profit' de um deal no MT5 geralmente jÃÂ¡ inclui comissÃÂµes e swaps.

    logging.info(f"Ã°Å¸âÂ° Deal de saÃÂ­da encontrado para ticket {ticket_ordem_abertura}: DealTicket={deal_final_de_saida.ticket}, PositionID={deal_final_de_saida.position_id}, Lucro={lucro_total_operacao:.2f}, PreÃÂ§o SaÃÂ­da={deal_final_de_saida.price}, Volume={deal_final_de_saida.volume}, Hora={datetime.fromtimestamp(deal_final_de_saida.time)})")

    # SHADOW MODE: fecha o ciclo do registro passivo do Modelo A
    shadow_registrar_resultado(ticket_ordem_abertura, lucro_total_operacao)

    score_dist = 0.0
    # Para calcular o score_dist, precisamos da ordem original de abertura.
    ordens_historico = mt5.history_orders_get(ticket=ticket_ordem_abertura)

    if not ordens_historico:
        logging.warning(
            f"Ã¢Å¡Â Ã¯Â¸Â NÃÂ£o foi possÃÂ­vel obter detalhes da ordem de abertura {ticket_ordem_abertura} do histÃÂ³rico para calcular score_dist.")
        # Mesmo sem a ordem, retornamos o lucro encontrado.
    elif len(ordens_historico) == 0:
        logging.warning(
            f"Ã¢Å¡Â Ã¯Â¸Â Lista de ordens do histÃÂ³rico vazia para ticket {ticket_ordem_abertura} ao calcular score_dist.")
    else:
        # Pega a primeira (e deve ser a ÃÂºnica) ordem com esse ticket
        ordem_obj = ordens_historico[0]
        logging.debug(
            f"Ã°Å¸âÅ  Detalhes da ordem de abertura para score_dist - Ticket: {ordem_obj.ticket}, PreÃÂ§oAbertura: {ordem_obj.price_open}, SL: {ordem_obj.sl}, TP: {ordem_obj.tp}, Tipo: {ordem_obj.type}, Estado: {ordem_obj.state}, RazÃÂ£o: {ordem_obj.reason}, PreÃÂ§o Atual MT5: {ordem_obj.price_current}")

        preco_entrada_para_score = ordem_obj.price_open  # Fallback
        # Buscar o deal de entrada correspondente ao ticket_ordem_abertura (que ÃÂ© o position_id do deal de saÃÂ­da)
        deals_relacionados_posicao = [
            d for d in deals if d.position_id == ticket_ordem_abertura]
        deal_de_entrada_para_score = None
        for deal_historico in deals_relacionados_posicao:
            # Garante que ÃÂ© o deal da ordem de abertura
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
        f"Ã°Å¸Å½Â¯ Score distÃÂ¢ncia calculado para ticket {ticket_ordem_abertura}: {score_dist:.4f}")

    # ========== AJUSTE FINO: PENALIDADE POR "MORTE SÃÅ¡BITA" ==========
    # Se o trade foi Loss e durou menos de 15 segundos, penalizamos severamente a IA
    # Isso ensina o modelo a evitar entradas em falsos rompimentos e ruÃÂ­dos de mercado
    if deal_de_entrada_para_score:
        tempo_trade_segundos = (
            deal_final_de_saida.time_msc - deal_de_entrada_para_score.time_msc) / 1000.0

        if lucro_total_operacao < 0 and tempo_trade_segundos < 15:
            score_dist = -1.5  # Penalidade severa para "Morte SÃÂºbita"
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â MORTE SÃÅ¡BITA DETECTADA: Trade durou {tempo_trade_segundos:.1f}s com prejuÃÂ­zo de R${lucro_total_operacao:.2f} | Penalizando IA com score -1.5")
        elif lucro_total_operacao < 0 and tempo_trade_segundos < 30:
            # Penalidade mÃÂ©dia para stops muito rÃÂ¡pidos
            score_dist = min(score_dist * 1.5, -1.0)
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â STOP RÃÂPIDO: Trade durou {tempo_trade_segundos:.1f}s com prejuÃÂ­zo | Score penalizado: {score_dist:.2f}")

    return lucro_total_operacao, score_dist

# endregion

# region [Trailing Stop]


def atualizar_trailing_stop() -> None:
    """Atualiza o trailing stop das posiÃÂ§ÃÂµes abertas."""
    if not TRAILING_ATIVO:
        return

    # Verifica se ÃÂ© fim de semana
    if datetime.now().weekday() > 4:  # 5 = SÃÂ¡bado, 6 = Domingo
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

    # Verifica horÃÂ¡rio do ajuste
    agora = datetime.now().time()
    horario_ajuste = datetime.strptime(HORARIO_AJUSTE, "%H:%M").time()
    if agora >= horario_ajuste:
        logging.info("Ã¢ÂÂ° ApÃÂ³s horÃÂ¡rio de ajuste, trailing stop desativado")
        return

    posicoes = retry_positions_get(SYMBOL)
    if posicoes is None or len(posicoes) == 0:
        threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()
        return

    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        logging.warning(
            "Ã¢Å¡Â Ã¯Â¸Â InformaÃÂ§ÃÂµes do sÃÂ­mbolo indisponÃÂ­veis para trailing")
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

        # Converte diferenÃÂ§a para pontos (1 ponto = 1000 ticks)
        lucro_ticks = abs(preco_atual - preco_entrada) / symbol_info.point
        lucro_pontos = lucro_ticks / TICKS_POR_PONTO

        # SÃÂ³ move o stop se atingiu o gatilho em pontos
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

        # SÃÂ³ atualiza se o novo SL ÃÂ© mais favorÃÂ¡vel
        if pos.type == mt5.POSITION_TYPE_BUY and (pos.sl is None or novo_sl > pos.sl):
            atualizar_sl(pos.ticket, novo_sl)
        elif pos.type == mt5.POSITION_TYPE_SELL and (pos.sl is None or novo_sl < pos.sl):
            atualizar_sl(pos.ticket, novo_sl)

    threading.Timer(TRAILING_INTERVALO, atualizar_trailing_stop).start()


def atualizar_sl(ticket: int, novo_sl: float, eh_breakeen_forcado: bool = False) -> bool:
    """Atualiza o stop loss de uma posiÃÂ§ÃÂ£o com validaÃÂ§ÃÂ£o de distÃÂ¢ncia mÃÂ­nima.
    eh_breakeen_forcado=True: pula TODAS as validaÃÂ§ÃÂµes (usado por INVERSÃÆO DE FLUXO)."""
    # Recupera a posiÃÂ§ÃÂ£o atual para pegar o TP original
    posicoes = mt5.positions_get(ticket=ticket)
    if not posicoes:
        logging.error(
            f"Ã¢ÂÅ NÃÂ£o foi possÃÂ­vel obter a posiÃÂ§ÃÂ£o com ticket {ticket} para atualizar SL.")
        return False

    posicao = posicoes[0]
    tp_original = posicao.tp

    # CORREÃâ¡ÃÆO CRÃÂTICA: ValidaÃÂ§ÃÂ£o de distÃÂ¢ncia mÃÂ­nima obrigatÃÂ³ria
    symbol_info = mt5.symbol_info(SYMBOL)
    if not symbol_info:
        logging.error(f"Ã¢ÂÅ Erro ao obter informaÃÂ§ÃÂµes do sÃÂ­mbolo {SYMBOL}")
        return False

    # Obter preÃÂ§o atual e freeze level
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        logging.error(f"Ã¢ÂÅ Erro ao obter tick atual do {SYMBOL}")
        return False

    # Inicializa freeze_level com valor padrÃÂ£o ANTES de qualquer uso
    freeze_level = symbol_info.trade_freeze_level if symbol_info else 0
    if freeze_level == 0:
        freeze_level = 1  # WDO: 1pt mÃÂ­nimo (freeze_level real do MT5)
    distancia_minima = freeze_level  # Sem multiplicador Ã¢â¬â precisa ser mÃÂ­nimo real, nÃÂ£o conservador

    # FIX 11/08 (retcode 10016 "Invalid stops"): a validaÃÂ§ÃÂ£o de distÃÂ¢ncia mÃÂ­nima
    # ÃÂ© SEMPRE aplicada Ã¢â¬â antes, o breakeen (auto-detectado ou forÃÂ§ado) pulava a
    # validaÃÂ§ÃÂ£o e enviava SL dentro da zona de freeze da corretora (ex.: trailing
    # 50% do sniper SL=5130.75 a 0.25pt do ask). Agora o SL ÃÂ© corrigido para
    # respeitar a distÃÂ¢ncia mÃÂ­nima ou rejeitado (aguarda prÃÂ³ximo tick).
    eh_breakeen = abs(novo_sl - posicao.price_open) < 2.0  # tolerÃÂ¢ncia de 2 ticks (sÃÂ³ p/ log)
    if eh_breakeen_forcado:
        logging.info(
            f"\U0001f510 Breakeen FORCADO (SL={novo_sl:.2f} ~ entrada={posicao.price_open:.2f}) \u2014 validando distÃÂ¢ncia mesmo assim")

    # Validar distÃÂ¢ncia mÃÂ­nima baseada no tipo de posiÃÂ§ÃÂ£o
    if posicao.type == mt5.POSITION_TYPE_BUY:
        preco_referencia = tick.bid
        distancia_atual = preco_referencia - novo_sl  # BUY: SL fica abaixo do bid
        if distancia_atual < distancia_minima:
            novo_sl_corrigido = preco_referencia - distancia_minima
            # SAFETY: Se correÃÂ§ÃÂ£o piora SL, nÃÂ£o mover Ã¢â¬â esperar prÃÂ³ximo tick
            if posicao.sl != 0 and novo_sl_corrigido <= posicao.sl:
                logging.debug(
                    f"Ã°Å¸ââ Trailing BUY: correÃÂ§ÃÂ£o ({novo_sl_corrigido:.2f}) pior que atual ({posicao.sl:.2f}). Aguardando preÃÂ§o.")
                return False
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â SL BUY muito prÃÂ³ximo! Corrigido: {novo_sl:.2f} Ã¢â â {novo_sl_corrigido:.2f}")
            novo_sl = novo_sl_corrigido
    else:  # SELL
        preco_referencia = tick.ask
        distancia_atual = novo_sl - preco_referencia  # SELL: SL fica acima do ask
        if distancia_atual < distancia_minima:
            novo_sl_corrigido = preco_referencia + distancia_minima
            # SAFETY: Se correÃÂ§ÃÂ£o piora SL, nÃÂ£o mover Ã¢â¬â esperar prÃÂ³ximo tick
            if posicao.sl != 0 and novo_sl_corrigido >= posicao.sl:
                logging.debug(
                    f"Ã°Å¸ââ Trailing SELL: correÃÂ§ÃÂ£o ({novo_sl_corrigido:.2f}) pior que atual ({posicao.sl:.2f}). Aguardando preÃÂ§o.")
                return False
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â SL SELL muito prÃÂ³ximo! Corrigido: {novo_sl:.2f} Ã¢â â {novo_sl_corrigido:.2f}")
            novo_sl = novo_sl_corrigido

    # Verificar se o novo SL ÃÂ© realmente uma melhoria
    if posicao.sl != 0:  # Se jÃÂ¡ tem SL definido
        if posicao.type == mt5.POSITION_TYPE_BUY and novo_sl <= posicao.sl:
            logging.debug(
                f"Ã°Å¸ââ SL BUY nÃÂ£o ÃÂ© melhoria: {novo_sl:.2f} <= {posicao.sl:.2f}")
            return False
        elif posicao.type == mt5.POSITION_TYPE_SELL and novo_sl >= posicao.sl:
            logging.debug(
                f"Ã°Å¸ââ SL SELL nÃÂ£o ÃÂ© melhoria: {novo_sl:.2f} >= {posicao.sl:.2f}")
            return False

    # FIX 13/08 (10016 "Invalid stops"): o tick consultado no inÃÂ­cio da funÃÂ§ÃÂ£o
    # pode estar defasado â entre a validaÃÂ§ÃÂ£o e o order_send o mercado andou,
    # deixando o SL dentro da zona de freeze real. Re-obtÃÂ©m o tick FRESCO e
    # revalida a distÃÂ¢ncia mÃÂ­nima IMEDIATAMENTE antes de enviar.
    try:
        tick_fresco = mt5.symbol_info_tick(SYMBOL)
        if tick_fresco:
            if posicao.type == mt5.POSITION_TYPE_BUY:
                _dist_fresca = tick_fresco.bid - novo_sl
                if _dist_fresca < distancia_minima:
                    novo_sl = tick_fresco.bid - distancia_minima
                    # FIX 14/08: a revalidacao com tick fresco NUNCA pode piorar
                    # o SL atual (o mercado pode ter andado contra entre a 1a
                    # validacao e o order_send). Se a correcao piora, aguarda o
                    # proximo tick em vez de enviar um SL PIOR.
                    if posicao.sl != 0 and novo_sl <= posicao.sl:
                        logging.debug(
                            f"â ï¸ Revalidacao BUY piora SL ({novo_sl:.2f} <= {posicao.sl:.2f}) - aguardando proximo tick")
                        return False
                    logging.warning(
                        f"â ï¸ SL BUY revalidado (tick fresco bid={tick_fresco.bid:.2f}): novo_sl â {novo_sl:.2f}")
            else:  # SELL
                _dist_fresca = novo_sl - tick_fresco.ask
                if _dist_fresca < distancia_minima:
                    novo_sl = tick_fresco.ask + distancia_minima
                    if posicao.sl != 0 and novo_sl >= posicao.sl:
                        logging.debug(
                            f"â ï¸ Revalidacao SELL piora SL ({novo_sl:.2f} >= {posicao.sl:.2f}) - aguardando proximo tick")
                        return False
                    logging.warning(
                        f"â ï¸ SL SELL revalidado (tick fresco ask={tick_fresco.ask:.2f}): novo_sl â {novo_sl:.2f}")
    except Exception as e:
        logging.warning(f"â ï¸ Erro ao revalidar SL com tick fresco: {e}")

    logging.debug(
        f"[atualizar_sl] Ticket: {ticket}, Novo SL: {novo_sl:.2f}, TP: {tp_original:.2f}, Freeze: {freeze_level}")

    ordem_mod = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": SYMBOL,
        "sl": round(novo_sl, symbol_info.digits),
        "tp": tp_original,  # MantÃÂ©m o TP original da posiÃÂ§ÃÂ£o
        "magic": MAGIC_NUMBER,
        "comment": "Trailing SL Monstro"
    }

    resultado = mt5.order_send(ordem_mod)
    if resultado is None:
        logging.error(f"Ã¢ÂÅ Erro ao mover SL via trailing. Ticket={ticket}")
        logging.error(f"Ã¢ÂÅ Erro MT5: {mt5.last_error()}")
        return False
    elif resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(
            f"Ã°Å¸âÂ SL atualizado com sucesso! {posicao.sl:.2f} Ã¢â â {ordem_mod['sl']:.2f} (Ticket: {ticket})")
        return True
    else:
        logging.error(
            f"Ã¢ÂÅ FALHA ao mover SL! CÃÂ³digo: {resultado.retcode} | Msg: {resultado.comment} | SL: {novo_sl:.2f}")
        logging.error(
            f"Ã¢ÂÅ Detalhes: Freeze={freeze_level}, DistÃÂ¢ncia mÃÂ­n={distancia_minima:.5f}")
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
    """PÃÂ¡gina antiga com dashboard."""
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
        <h1>Ã°Å¸Â¤â Monstro Dashboard</h1>
        <div class="grid">
            <div class="card">
                <h2>Ã°Å¸âÅ  Performance</h2>
                <div id="performance_chart"></div>
            </div>
            <div class="card">
                <h2>Ã°Å¸Å½Â¯ DistribuiÃÂ§ÃÂ£o de Scores</h2>
                <div id="score_dist_chart"></div>
            </div>
            <div class="card">
                <h2>Ã°Å¸âË Aprendizado</h2>
                <div id="learning_chart"></div>
            </div>
            <div class="card">
                <h2>Ã¢Å¡âÃ¯Â¸Â ExperiÃÂªncias</h2>
                <div id="exp_chart"></div>
            </div>
            <div class="card full-width">
                <h2>Ã°Å¸âÂ Status Atual</h2>
                <div id="status_info"></div>
                <div class="bloqueio-info">
                    <div>
                        <h3>Ã°Å¸ââ Status Bloqueios</h3>
                        <div id="bloqueio_info"></div>
                    </div>
                    <div>
                        <h3>Ã¢Å¡Â Ã¯Â¸Â SequÃÂªncia de Losses</h3>
                        <div id="losses_info"></div>
                    </div>
                </div>
                <div class="balanceamento-info">
                    <div>
                        <h3>Ã¢Å¡âÃ¯Â¸Â Balanceamento de OperaÃÂ§ÃÂµes</h3>
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
                        <p><strong>ÃÅ¡ltima DecisÃÂ£o:</strong> ${data.ultima_decisao}</p>
                        <p><strong>Status Book:</strong> ${data.status_book}</p>
                        <p><strong>PosiÃÂ§ÃÂ£o:</strong> ${data.posicao_atual}</p>
                        <p><strong>Idade MÃÂ©dia Exp.:</strong> ${data.idade_media_exp.toFixed(1)}h</p>
                        <p><strong>Decay MÃÂ©dio:</strong> ${data.decay_medio.toFixed(2)}</p>
                    `);

                    // Atualiza informaÃÂ§ÃÂµes de bloqueio
                    $('#bloqueio_info').html(`
                        <div class="bloqueio-lado ${data.bloqueios.BUY > 0 ? 'bloqueado' : 'liberado'}">
                            COMPRA: ${data.bloqueios.BUY > 0 ? `Bloqueado (${data.bloqueios.BUY} ciclos)` : 'Liberado'}
                        </div>
                        <div class="bloqueio-lado ${data.bloqueios.SELL > 0 ? 'bloqueado' : 'liberado'}">
                            VENDA: ${data.bloqueios.SELL > 0 ? `Bloqueado (${data.bloqueios.SELL} ciclos)` : 'Liberado'}
                        </div>
                    `);

                    // Atualiza informaÃÂ§ÃÂµes de losses em sequÃÂªncia
                    $('#losses_info').html(`
                        <div>COMPRA: ${data.losses_sequencia.BUY} losses seguidos</div>
                        <div>VENDA: ${data.losses_sequencia.SELL} losses seguidos</div>
                    `);

                    // Atualiza informaÃÂ§ÃÂµes de balanceamento
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
    """Retorna dados de performance para o grÃÂ¡fico."""
    return jsonify({
        "lucros": historico_lucro
    })


@app.route("/api/score_distribution")
def api_score_distribution():
    """Retorna distribuiÃÂ§ÃÂ£o dos scores."""
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
    """Retorna estatÃÂ­sticas das experiÃÂªncias."""
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

    # ObtÃÂ©m status do gerenciador de bloqueio - usando globals() para verificar
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

    # ObtÃÂ©m status de balanceamento
    balanceamento = mem_exp.get_balanceamento_status(
    ) if mem_exp else None

    # ObtÃÂ©m modo operacional
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

    # Status do filtro de horÃÂ¡rio
    if filtro_horario:
        status_sistemas['horario'] = filtro_horario.get_status()

    # Status do detector de tendÃÂªncia
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
    """Retorna o histÃÂ³rico de lucros."""
    return jsonify({
        "lucros": historico_lucro,
        "total": sum(historico_lucro) if historico_lucro else 0,
        "media": sum(historico_lucro) / len(historico_lucro) if historico_lucro else 0,
        "operacoes": len(historico_lucro)
    })


@app.route("/api/data_files")
def api_data_files():
    """Retorna status dos arquivos de dados e modelos do robÃÂ´."""
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
                        info["linhas"] = sum(1 for _ in f) - 1  # menos cabeÃÂ§alho
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
    """Inicia o servidor Flask.

    Usa waitress (WSGI de producao, multi-thread) quando disponivel; o
    servidor dev do Flask trava sob concorrencia de requisicoes e foi a
    causa raiz dos travamentos da porta 5001 auditados em 17-18/08.
    """
    flask_log = logging.getLogger('werkzeug')
    flask_log.setLevel(logging.WARNING)
    app.logger.setLevel(logging.WARNING)
    try:
        from waitress import serve
        logging.info("Dashboard via waitress (producao, threads=8) na porta %s", PORT)
        serve(app, host='0.0.0.0', port=PORT, threads=8)
    except ImportError:
        logging.warning("waitress ausente - usando servidor dev do Flask")
        app.run(host='0.0.0.0', port=PORT, debug=DEBUG, use_reloader=False)


def atualizar_sentinela():
    """MantÃ©m o Sentinela de Fluxo aquecido em background (cache de 60s)."""
    global sentinela_cenario, sentinela_detalhe, sentinela_score, sentinela_ultima_atualizacao
    while True:
        try:
            _sf = sentinela_fluxo.classificar()
            sentinela_cenario = _sf['cenario']
            sentinela_detalhe = _sf['detalhe']
            sentinela_score = _sf['score']
            sentinela_ultima_atualizacao = _sf['atualizado']
            if _sf['cenario'] != 'NEUTRO':
                logging.info(f"Ã°Å¸âºÂ¡ SENTINELA: {_sf['cenario']} | {_sf['detalhe']}")
        except Exception:
            pass
        time.sleep(60)


# VariÃÂ¡veis globais para mÃÂ©tricas
historico_loss = []  # HistÃÂ³rico de loss do modelo

# Controle de treinamento inteligente
contador_experiencias_novas = 0
# Ã°Å¸Å¡Â¨ CORREÃâ¡ÃÆO C3: Treina a cada 3 experiÃÂªncias novas (era 10) - APRENDIZADO ACELERADO
LIMITE_EXPERIENCIAS_PARA_TREINO = 3

# Dashboard V2 Ã¢â¬â VariÃÂ¡veis de estado para o dashboard
spread_atual = 0.0
atr_atual = 0.0
rsi_atual = 50.0

# PTAX globals
ptax_valor = 0.0
dolar_casado = 0.0
sniper_bloqueado = False
sniper_bloqueio_motivo = ""
payroll_ativado = False

# SENTINELA DE FLUXO globals (camada macroeconÃ´mica de veto)
SENTINELA_ATIVO = True  # False desativa o veto macro totalmente
sentinela_cenario = "NEUTRO"
sentinela_detalhe = "Inicializando..."
sentinela_score = 0
sentinela_ultima_atualizacao = ""

# ========== SANITY CHECK: DETECTOR DE DADOS CONGELADOS ==========
_ultimo_bid_qty = None
_ultimo_ask_qty = None
_timestamp_ultimo_dado_novo = None
TEMPO_MAX_DADOS_CONGELADOS = 300  # 5 minutos sem mudanÃÂ§a = alerta


def verificar_dados_congelados(bid_qty: float, ask_qty: float) -> bool:
    """
    Verifica se os dados do book estÃÂ£o congelados.
    Retorna True se os dados estÃÂ£o congelados (problema no EA MQL5).
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

    # Dados nÃÂ£o mudaram Ã¢â¬â verifica hÃÂ¡ quanto tempo
    tempo_congelado = agora - _timestamp_ultimo_dado_novo
    if tempo_congelado > TEMPO_MAX_DADOS_CONGELADOS:
        logging.warning(
            f"Ã°Å¸Â§Å  DADOS CONGELADOS: bid_qty={bid_qty}, ask_qty={ask_qty} "
            f"sem mudanÃÂ§a hÃÂ¡ {tempo_congelado/60:.1f} minutos! "
            f"Verifique o EA MQL5 Ã¢â¬â OnBookEvent pode nÃÂ£o estar disparando.")
        return True

    return False


# VariÃÂ¡veis globais para encerramento seguro
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
        logging.error(f"Ã¢ÂÅ Erro ao verificar arquivo de parada: {e}")
        return False


def signal_handler(signum, frame):
    """Trata sinais do sistema para encerramento seguro."""
    global sistema_encerrando, modelo_ia_global, memoria_experiencias_global

    if sistema_encerrando:
        logging.info(
            "Ã°Å¸âÂ´ Sinal recebido novamente - forÃÂ§ando encerramento imediato")
        os._exit(1)

    sistema_encerrando = True
    logging.info(f"Ã°Å¸âÂ´ Sinal {signum} recebido - iniciando encerramento seguro")

    try:
        if modelo_ia_global and memoria_experiencias_global:
            encerramento_seguro_completo(
                modelo_ia_global, memoria_experiencias_global)
        else:
            logging.info(
                "Ã°Å¸âÂ´ Dados globais nÃÂ£o disponÃÂ­veis - encerramento direto")
            os._exit(0)
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro no encerramento por sinal: {e}")
        os._exit(1)


# Registra os handlers de sinal - TEMPORARIAMENTE DESABILITADO PARA DEBUG
# signal.signal(signal.SIGTERM, signal_handler)
# signal.signal(signal.SIGINT, signal_handler)
# if sys.platform == "win32":
#     signal.signal(signal.SIGBREAK, signal_handler)

# region [Loop Principal]


def verificar_parada_gracil():
    """Verifica se foi solicitada parada gracil atravÃÂ©s do arquivo parar.txt"""
    if os.path.exists(_caminho_dados("parar.txt")):
        # Se mercado fechado, encerra imediatamente
        try:
            mercado_ativo, motivo = verificar_mercado_aberto()
            if not mercado_ativo:
                logging.info(
                    f"Ã°Å¸Å¡Â« {motivo} - Encerramento imediato por mercado fechado")
                return True
        except:
            pass  # Se erro na verificaÃÂ§ÃÂ£o, continua normalmente
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
        # InicializaÃÂ§ÃÂ£o
        mt5_ativo_local = inicializar_mt5() if mt5_ativo_param is None else mt5_ativo_param

        # === PROTEÃâ¡ÃÆO TOTAL DO MODELO ===
        logging.info("Ã°Å¸âºÂ¡Ã¯Â¸Â Iniciando verificaÃÂ§ÃÂ£o de proteÃÂ§ÃÂ£o do modelo...")
        if not verificar_e_proteger_modelo():
            logging.warning(
                "Ã¢Å¡Â Ã¯Â¸Â ProteÃÂ§ÃÂ£o do modelo identificou problemas - continuando com novo modelo")

        # Verifica se o mercado estÃÂ¡ aberto antes de carregar o modelo
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
            logging.info("Ã°Å¸Å¡Â« Mercado fechado: carregamento de modelo suspenso.")
            modelo_ia_local = None

        # Atualiza variÃÂ¡veis globais para tratamento de sinais
        modelo_ia_global = modelo_ia_local
        memoria_experiencias_global = memoria_experiencias

        # ===== v22.1b: ORQUESTRADOR 7 VELAS (Faixa 1) =====
        global ESTADO_SISTEMA
        _orq = None
        if SETE_VELAS_ATIVO:
            def _sv_fn_executar(action, lots, symbol, sl, tp, magic_override, comment):
                return executar_ordem(
                    action=action, lots=lots, symbol=symbol,
                    modo_operacional=modo_operacional, sniper=True,
                    sl_points_override=sl, tp_points_override=tp,
                    magic_override=magic_override, comment=comment,
                    shadow=False)
            try:
                _orq = Orquestrador7Velas(
                    fn_executar=_sv_fn_executar, symbol=SYMBOL, ativo=SETE_VELAS_ATIVO)
                logging.info("[7VELAS] Orquestrador instanciado (magic %s) - Faixa 1 armada", MAGIC_SETE_VELAS)
            except Exception as e:
                logging.error(f"[7VELAS] Falha ao instanciar orquestrador: {e}")
                _orq = None


        esperando_confirmacao = False
        ultimo_heartbeat = time.time()
        ultimo_diagnostico = time.time()

        # ========== TRAVA DE TIMESTAMP: SÃÂ³ opera com dados POSTERIORES ÃÂ  inicializaÃÂ§ÃÂ£o ==========
        # Guarda o momento exato da inicializaÃÂ§ÃÂ£o. O robÃÂ´ sÃÂ³ vai operar quando o EA
        # enviar um timestamp POSTERIOR a este momento. Evita operar com dados velhos
        # que ficaram no arquivo book_data_wdo.csv de sessÃÂµes anteriores.
        timestamp_inicializacao = time.time()
        ultimo_timestamp_ea_processado = None  # Nenhum dado processado ainda
        logging.info(
            f"Ã°Å¸ââ TRAVA TIMESTAMP: SÃÂ³ operarÃÂ¡ com dados posteriores a {datetime.now().strftime('%H:%M:%S')}")
        posicao_atual = None
        modo_operacional = ModoOperacional()  # Inicializa gerenciador de modos

        # --- INICIALIZAÃâ¡ÃÆO DAS NOVAS MELHORIAS (PASSO 2 COMPLETO) ---

        # 1. Gerenciador de SaÃÂ­da Unificado Ã¢â¬â recalibrado para R/R 1:2
        config_saida = {
            'timeout_sem_evolucao_s': 180,       # 3 minutos Ã¢â¬â mais paciÃÂªncia
            'lucro_minimo_evolucao_pts': 5,      # 5 pontos mÃÂ­nimo de evoluÃÂ§ÃÂ£o
            # SÃÂ³ protege apÃÂ³s 40pts de lucro (>50% do TP)
            'pico_minimo_protecao_pts': 40,
            'percentual_perda_pico': 0.35,       # Sai se perder 35% do pico
            'tempo_max_estagnacao_s': 240,       # 4 minutos de estagnaÃÂ§ÃÂ£o
            'lucro_max_estagnacao_pts': 20,      # Lucro "pequeno" = menos de 20pts
            # Trailing sÃÂ³ ativa apÃÂ³s 8pts de lucro (AÃÂ§ÃÂ£o 1 07/08: era 3 Ã¢â¬â deixar o winner respirar)
            'trailing_gatilho_pts': 8,
            # 4pts de distÃÂ¢ncia (AÃÂ§ÃÂ£o 1 07/08: era 2 Ã¢â¬â nÃÂ£o cortar winner em +1pt)
            'trailing_distancia_pts': 4
        }
        gerenciador_saida = GerenciadorDeSaida(config_saida)
        logging.info("Ã¢Åâ¦ Gerenciador de SaÃÂ­da Unificado INICIALIZADO.")

        # 2. Volume MÃÂ­nimo Adaptativo (REDUZIDO PARA APRENDIZADO)
        volume_adaptativo = VolumeAdaptativo(
            janela_minutos=15, percentual_da_media=0.5)  # Reduzido de 0.8 para 0.5
        logging.info("Ã¢Åâ¦ Gerenciador de Volume Adaptativo INICIALIZADO.")

        # Inicializa gerenciador de bloqueio
        gerenciador_bloqueio = GerenciadorBloqueio()

        # CONTADOR DE REJEIÃâ¡Ãâ¢ES PARA MODO EMERGÃÅ NCIA
        contador_rejeicoes_consecutivas = 0
        LIMITE_REJEICOES_EMERGENCIA = 30

        # Garante contexto inicializado antes do loop (evita NameError na sincronizaÃÂ§ÃÂ£o)
        contexto: dict = {}

        while thread_ativo:
            try:
                # ===== v22.1b: estado multi-estrategia + orquestrador 7 Velas =====
                _atualizar_estado_sistema()
                if _orq is not None and ESTADO_SISTEMA == "SETE_VELAS_EXCLUSIVO":
                    try:
                        _orq.orquestrar()
                    except Exception as e:
                        logging.error(f"[7VELAS] Erro no orquestrar(): {e}")

                # ===== VERIFICAÃâ¡ÃÆO DE SEGURANÃâ¡A DA VARIÃÂVEL POSICAO_ATUAL =====
                # Garante que posicao_atual sempre exista (inicializada como None se necessÃÂ¡rio)
                if 'posicao_atual' not in locals() and 'posicao_atual' not in globals():
                    posicao_atual = None
                    logging.debug(
                        "Ã°Å¸âÂ§ posicao_atual inicializada como None por seguranÃÂ§a")

                # ===== VERIFICAÃâ¡ÃÆO DE PARADA GRACIL =====
                if verificar_parada_gracil():
                    logging.info(
                        "Ã°Å¸âºâ PARADA GRACIL SOLICITADA - Encerrando sistema com seguranÃÂ§a...")
                    # Consome o sinal: remove parar.txt para nao bloquear a proxima inicializacao
                    try:
                        os.remove(_caminho_dados("parar.txt"))
                        logging.info("Ã°Å¸Â§Â¹ parar.txt consumido e removido.")
                    except Exception:
                        pass

                    # Fecha posiÃÂ§ÃÂµes ativas se houver
                    if posicao_aberta and ticket_ordem_atual:
                        logging.info(
                            "Ã°Å¸âÂ° Fechando posiÃÂ§ÃÂ£o ativa antes de encerrar...")
                        try:
                            fechar_posicao_atual()
                        except Exception as e:
                            logging.error(f"Ã¢ÂÅ Erro ao fechar posiÃÂ§ÃÂ£o: {e}")

                    # Salva modelo e dados importantes
                    if modelo_ia_local:
                        logging.info("Ã°Å¸âÂ¾ Salvando modelo IA...")
                        try:
                            salvar_modelo(modelo_ia_local)
                        except Exception as e:
                            logging.error(f"Ã¢ÂÅ Erro ao salvar modelo: {e}")

                    # Salva experiÃÂªncias
                    if memoria_experiencias:
                        logging.info("Ã°Å¸âÅ¡ Salvando experiÃÂªncias...")
                        try:
                            salvar_experiencias_json(
                                memoria_experiencias.experiencias)
                        except Exception as e:
                            logging.error(
                                f"Ã¢ÂÅ Erro ao salvar experiÃÂªncias: {e}")

                    logging.info(
                        "Ã¢Åâ¦ ENCERRAMENTO GRACIL CONCLUÃÂDO - Sistema finalizado com seguranÃÂ§a")
                    thread_ativo = False
                    break

                # Dorme atÃÂ© o pregÃÂ£o abrir
                agora = datetime.now().time()
                inicio = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
                fim = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

                if agora < inicio:
                    aguardar_abertura()
                    continue
                if agora >= fim:
                    aguardar_fechamento()
                    continue
                # Verifica se ÃÂ© fim de semana
                if datetime.now().weekday() > 4:  # 5 = SÃÂ¡bado, 6 = Domingo
                    logging.info(
                        "Ã°Å¸ââ¦ Fim de semana: sistema em modo de espera...")
                    time.sleep(60)  # Dorme por 1 minuto durante fim de semana
                    continue

                # === VERIFICAÃâ¡ÃÆO DE SINAL DE ENCERRAMENTO EXTERNO ===
                # TEMPORARIAMENTE DESABILITADO PARA DEBUG
                if False and os.path.exists("shutdown_signal.txt"):
                    logging.info(
                        "Ã°Å¸Å¡Â¦ SINAL DE ENCERRAMENTO EXTERNO DETECTADO - INICIANDO SHUTDOWN GRACIOSO")

                    # Fecha todas as posiÃÂ§ÃÂµes abertas
                    posicoes_fechadas = fechar_todas_posicoes(
                        "Encerramento por sinal externo")

                    # Atualiza variÃÂ¡veis globais antes do encerramento
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    # Executa encerramento seguro completo
                    encerramento_seguro_completo(
                        modelo_ia_local, memoria_experiencias)
                    # NÃÂ£o chegarÃÂ¡ aqui pois encerramento_seguro_completo chama os._exit()

                # === ENCERRAMENTO AUTOMÃÂTICO Ãâ¬S 17:35 ===
                horario_atual = datetime.now().time()
                horario_encerramento = datetime.strptime(
                    HORARIO_ENCERRAMENTO, "%H:%M").time()
                if horario_atual >= horario_encerramento:
                    logging.info(
                        f"Ã°Å¸âÂ´ ENCERRAMENTO AUTOMÃÂTICO Ãâ¬S {HORARIO_ENCERRAMENTO} - FECHANDO TODAS AS POSIÃâ¡Ãâ¢ES")

                    # Fecha todas as posiÃÂ§ÃÂµes abertas
                    posicoes_fechadas = fechar_todas_posicoes(
                        "Encerramento automÃÂ¡tico 17:35")

                    # Salva estatÃÂ­sticas finais
                    if posicoes_fechadas > 0:
                        logging.info(
                            f"Ã°Å¸âÅ  EstatÃÂ­sticas finais: {posicoes_fechadas} posiÃÂ§ÃÂµes fechadas")

                    # Salva estado do modelo
                    try:
                        salvar_modelo(modelo_ia_local)
                        logging.info("Ã°Å¸âÂ¾ Modelo salvo com sucesso")
                    except Exception as e:
                        logging.error(f"Ã¢ÂÅ Erro ao salvar modelo: {e}")

                    # Atualiza variÃÂ¡veis globais
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    logging.info(
                        f"Ã°Å¸ÂÂ POSIÃâ¡Ãâ¢ES FECHADAS Ãâ¬S {HORARIO_ENCERRAMENTO} - AGUARDANDO AFTER MARKET")

                # === ENCERRAMENTO COMPLETO APÃâS AFTER MARKET (17:40) ===
                horario_atual_after = datetime.now().time()
                horario_after_market = datetime.strptime(
                    HORARIO_AFTER, "%H:%M").time()
                if horario_atual_after >= horario_after_market:
                    logging.info(
                        "Ã°Å¸âÂ´ AFTER MARKET ENCERRADO - DESLIGANDO SISTEMA AUTOMATICAMENTE")

                    # Atualiza variÃÂ¡veis globais antes do encerramento
                    modelo_ia_global = modelo_ia_local
                    memoria_experiencias_global = memoria_experiencias

                    # Executa encerramento seguro completo
                    encerramento_seguro_completo(
                        modelo_ia_local, memoria_experiencias)
                    # NÃÂ£o chegarÃÂ¡ aqui pois encerramento_seguro_completo chama os._exit()

                # Heartbeat e diagnÃÂ³stico - sÃÂ³ loga se estiver em horÃÂ¡rio de operaÃÂ§ÃÂ£o
                timestamp_atual = time.time()
                if timestamp_atual - ultimo_heartbeat >= 300:  # 5min (o pulso de 60s jÃÂ¡ mostra vida)
                    if horario_permitido():
                        # Dentro do horÃÂ¡rio: 1 linha a cada 5min
                        status_bloqueio = gerenciador_bloqueio.get_status()
                        logging.info(
                            f"Ã°Å¸âÂÃ¯Â¸Â Monstro ativo | Modo: {modo_operacional.modo_atual}")
                        # Status de bloqueios sÃÂ³ interessa quando hÃÂ¡ algum bloqueio ativo
                        _bloq_buy = status_bloqueio['bloqueios']['BUY']
                        _bloq_sell = status_bloqueio['bloqueios']['SELL']
                        if _bloq_buy or _bloq_sell:
                            logging.info(
                                f"Ã°Å¸ââ Status bloqueios - BUY: {_bloq_buy}, SELL: {_bloq_sell}")
                    else:
                        # Fora do horÃÂ¡rio: log silencioso a cada 10 minutos
                        if timestamp_atual - ultimo_heartbeat >= 600:
                            agora_str = datetime.now().strftime("%H:%M")
                            logging.info(
                                f"Ã°Å¸ËÂ´ Fora do horÃÂ¡rio ({agora_str}) - aguardando prÃÂ³xima janela")
                    ultimo_heartbeat = timestamp_atual

                if timestamp_atual - ultimo_diagnostico >= 300:
                    checar_arquivos_essenciais()
                    # === VERIFICAÃâ¡ÃÆO PERIÃâDICA DO MODELO (roda igual; log em debug) ===
                    logging.debug("Ã°Å¸âºÂ¡Ã¯Â¸Â VerificaÃÂ§ÃÂ£o periÃÂ³dica do modelo...")
                    if not verificar_e_proteger_modelo():
                        logging.warning(
                            "Ã¢Å¡Â Ã¯Â¸Â Modelo teve problemas - mas foi protegido automaticamente")
                    ultimo_diagnostico = timestamp_atual

                if esperando_confirmacao:
                    logging.info("Ã¢ÂÂ³ Aguardando confirmaÃÂ§ÃÂ£o da ÃÂºltima ordem...")
                    time.sleep(1)
                    continue

                current_positions = retry_positions_get(SYMBOL)
                monstro_position_active = any(
                    p.volume > 0 for p in current_positions or []
                )

                # ===== SINCRONIZAÃâ¡ÃÆO AUTOMÃÂTICA DA POSIÃâ¡ÃÆO ATUAL =====
                # Se existe uma posiÃÂ§ÃÂ£o no MT5, mas nossa variÃÂ¡vel estÃÂ¡ vazia, sincronize!
                posicao_ativa_no_mt5 = next(
                    (p for p in current_positions if p.magic == MAGIC_NUMBER), None) if current_positions else None

                if posicao_ativa_no_mt5 and posicao_atual is None:
                    try:
                        logging.info(
                            f"Ã°Å¸ââ Sincronizando com posiÃÂ§ÃÂ£o ativa encontrada no MT5: #{posicao_ativa_no_mt5.ticket}")
                        _ctx_recover = contexto.copy() if 'contexto' in dir() and contexto else {}
                        posicao_atual = PosicaoAtiva(
                            ticket=posicao_ativa_no_mt5.ticket,
                            tipo="BUY" if posicao_ativa_no_mt5.type == mt5.POSITION_TYPE_BUY else "SELL",
                            preco_entrada=posicao_ativa_no_mt5.price_open,
                            sl=posicao_ativa_no_mt5.sl,
                            tp=posicao_ativa_no_mt5.tp,
                            score_inicial=0.0,  # NÃÂ£o temos o contexto original, entÃÂ£o usamos um valor neutro
                            entry_context=_ctx_recover  # Salva contexto atual para nÃÂ£o perder o registro no CSV
                        )
                        # Se a posiÃÂ§ÃÂ£o sincronizada tem TP > 0, ÃÂ© do SNIPER %R
                        # (o robÃÂ´ principal sempre usa TP=0)
                        if posicao_ativa_no_mt5.tp and posicao_ativa_no_mt5.tp > 0:
                            if not isinstance(posicao_atual.entry_context, dict):
                                posicao_atual.entry_context = {}
                            posicao_atual.entry_context['sniper_wr'] = 1
                        # Inicia o monitoramento do gerenciador de saÃÂ­da para esta posiÃÂ§ÃÂ£o
                        gerenciador_saida.iniciar_monitoramento(
                            posicao_ativa_no_mt5)
                        posicao_aberta = True
                        logging.info(
                            f"Ã¢Åâ¦ SincronizaÃÂ§ÃÂ£o concluÃÂ­da - PosiÃÂ§ÃÂ£o {posicao_atual.tipo} de {posicao_atual.preco_entrada:.2f}")
                    except Exception as e:
                        logging.error(
                            f"Ã¢ÂÅ Erro na sincronizaÃÂ§ÃÂ£o de posiÃÂ§ÃÂ£o: {e}")
                        posicao_atual = None
                # ==========================================

                if monstro_position_active:
                    posicao_aberta = True

                    # VERIFICAÃâ¡ÃÆO ADICIONAL DE SEGURANÃâ¡A
                    if posicao_atual is None:
                        logging.warning(
                            "Ã¢Å¡Â Ã¯Â¸Â PosiÃÂ§ÃÂ£o ativa no MT5 mas posicao_atual ÃÂ© None. Tentando ressincronizar...")
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
                                # PosiÃÂ§ÃÂ£o com TP > 0 = SNIPER %R (robÃÂ´ principal usa TP=0)
                                if posicao_ativa_no_mt5.tp and posicao_ativa_no_mt5.tp > 0:
                                    if not isinstance(posicao_atual.entry_context, dict):
                                        posicao_atual.entry_context = {}
                                    posicao_atual.entry_context['sniper_wr'] = 1
                                gerenciador_saida.iniciar_monitoramento(
                                    posicao_ativa_no_mt5)
                                logging.info(
                                    "Ã¢Åâ¦ RessincronizaÃÂ§ÃÂ£o de emergÃÂªncia concluÃÂ­da")
                            except Exception as e:
                                logging.error(
                                    f"Ã¢ÂÅ Falha na ressincronizaÃÂ§ÃÂ£o: {e}")

                    # SUBSTITUI A LÃâGICA ANTIGA PELA NOVA (PASSO 2)
                    # OBTÃâ°M DADOS ATUAIS
                    tick = mt5.symbol_info_tick(SYMBOL)
                    # Obtenha o RSI atual aqui tambÃÂ©m, se a regra for usada

                    if tick and posicao_atual is not None:
                        preco_atual = tick.bid if gerenciador_saida.tipo_posicao == "SELL" else tick.ask

                        # ========== Ã¯Â¿Â½ HEARTBEAT DA POSIÃâ¡ÃÆO (monitor ao vivo a cada ~5s) ==========
                        # Loga a cada iteraÃÂ§ÃÂ£o Ã¢â¬â o loop jÃÂ¡ ÃÂ© pausado em
                        # INTERVALO_CHECK_SCORE (5s), entÃÂ£o o heartbeat sai confiÃÂ¡vel.
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
                                _emoji = "Ã°Å¸Å¸Â¢" if _lucro_rs >= 0 else "Ã°Å¸âÂ´"
                                logging.info(
                                    f"Ã°Å¸ââ {_emoji} {gerenciador_saida.tipo_posicao} {SYMBOL} | "
                                    f"Entrada: {posicao_atual.preco_entrada:.0f} Ã¢â â Atual: {preco_atual:.0f} | "
                                    f"{_pts:+.0f} pts | Flutuante: R$ {_lucro_rs:+.2f} | "
                                    f"SL: {_pos[0].sl:.0f} TP: {_pos[0].tp:.0f}" if (_pos and len(_pos) > 0) else "")
                            except Exception:
                                pass

                        # ========== Ã¯Â¿Â½Ã°Å¸ââ SAÃÂDA POR INVERSÃÆO DE FLUXO (BIG PLAYERS INVERTERAM) ==========
                        # Book nativo (tempo real). Se o fluxo vira contra a posiÃÂ§ÃÂ£o
                        # (ratio >= SNIPER_RATIO_MIN), reage em 2 NÃÂVEIS (FIX 07/08:
                        # gate config=2.0, breakeven substituÃÂ­do por trava de lucro):
                        #   Ã¢â¬Â¢ Em PREJUÃÂZO  -> SAI IMEDIATO (corta a perda, big players viraram)
                        #   Ã¢â¬Â¢ Em LUCRO      -> TRAVA 50% do lucro (protege e deixa correr)
                        # (PULADO para posiÃÂ§ÃÂ£o SNIPER %R Ã¢â¬â SL/TP por ATR no MT5 + trailing
                        # 50% abaixo gerenciam a saÃÂ­da, fiel ao backtest variante A)
                        try:
                            book_fluxo = ler_book_nativo()
                            _pos_eh_sniper_wr = bool(
                                (posicao_atual.entry_context or {}).get('sniper_wr', 0)
                            ) if posicao_atual else False
                            if book_fluxo and posicao_atual and not _pos_eh_sniper_wr:
                                bid_total = book_fluxo.get(
                                    'total_bid_volume', 0)
                                ask_total = book_fluxo.get(
                                    'total_ask_volume', 0)

                                if bid_total > 0 and ask_total > 0:
                                    # Para SELL: inversÃÂ£o = BID domina (compradores fortes)
                                    # Para BUY: inversÃÂ£o = ASK domina (vendedores fortes)
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
                                        # LÃÂª o lucro flutuante REAL da posiÃÂ§ÃÂ£o direto do MT5
                                        posicoes_check = mt5.positions_get(
                                            ticket=posicao_atual.ticket)
                                        lucro_flutuante = posicoes_check[0].profit if (
                                            posicoes_check and len(posicoes_check) > 0) else 0.0

                                        # Converte lucro em R$ para pontos (1pt = R$10 no WDO)
                                        lucro_pontos_inv = lucro_flutuante / 10.0

                                        if lucro_pontos_inv < -2.0:
                                            # NÃÂVEL 1 Ã¢â¬â PREJUÃÂZO GRAVE + fluxo contra: SAI IMEDIATO
                                            logging.warning(
                                                f"Ã°Å¸ââÃ°Å¸Å¡Â¨ INVERSÃÆO DE FLUXO CONTRA POSIÃâ¡ÃÆO EM PREJUÃÂZO! "
                                                f"Ratio contrÃÂ¡rio: {ratio_inversao:.2f} | Lucro: {lucro_pontos_inv:+.1f}pts (R${lucro_flutuante:.2f}) | "
                                                f"Big Players viraram Ã¢â¬â SAINDO IMEDIATAMENTE para cortar a perda!")
                                            fechar_posicao_atual(
                                                motivo=f"InversÃÂ£o de fluxo em prejuÃÂ­zo (ratio {ratio_inversao:.2f})")
                                            posicao_atual = None
                                            posicao_aberta = False
                                        elif lucro_pontos_inv >= -2.0 and posicoes_check and len(posicoes_check) > 0:
                                            # NÃÂVEL 2 Ã¢â¬â fluxo contra (FIX 07/08: breakeven era ineficaz):
                                            #   * Em LUCRO real -> TRAVA 50% do lucro (SL deixa a entrada p/ trÃÂ¡s)
                                            #   * Em zero/prejuÃÂ­zo leve -> SAI (breakeven inviÃÂ¡vel: MT5 retcode
                                            #     10016 "Invalid stops" quando o preÃÂ§o estÃÂ¡ colado na entrada)
                                            entrada_fluxo = posicao_atual.preco_entrada
                                            sl_atual = posicoes_check[0].sl
                                            preco_atual_pos = posicoes_check[0].price_current
                                            if lucro_pontos_inv > 0:
                                                # Trava 50% do lucro atual (em vez de voltar para a entrada)
                                                if gerenciador_saida.tipo_posicao == "SELL":
                                                    sl_alvo = entrada_fluxo - lucro_pontos_inv * FLUXO_TRAVA_LUCRO_PCT
                                                else:
                                                    sl_alvo = entrada_fluxo + lucro_pontos_inv * FLUXO_TRAVA_LUCRO_PCT
                                                # Respeita distÃÂ¢ncia mÃÂ­nima de stop (evita retcode 10016)
                                                dist_sl = (preco_atual_pos - sl_alvo) if gerenciador_saida.tipo_posicao == "BUY" \
                                                    else (sl_alvo - preco_atual_pos)
                                                melhoria = (gerenciador_saida.tipo_posicao == "SELL" and sl_alvo < sl_atual) or \
                                                           (gerenciador_saida.tipo_posicao == "BUY" and sl_alvo > sl_atual)
                                                cooldown_ok = (time.time() - _fluxo_estado['ultimo_ajuste']) >= FLUXO_COOLDOWN_S
                                                if melhoria and cooldown_ok and dist_sl >= FLUXO_DIST_MINIMA_PTS:
                                                    _fluxo_estado['ultimo_ajuste'] = time.time()
                                                    logging.warning(
                                                        f"Ã°Å¸ââ INVERSÃÆO DE FLUXO (lucro {lucro_pontos_inv:+.1f}pts)! Ratio contrÃÂ¡rio: {ratio_inversao:.2f} | "
                                                        f"SL travado em {sl_alvo:.2f} (trava {FLUXO_TRAVA_LUCRO_PCT*100:.0f}% do lucro) Ã¢â¬â protegendo!")
                                                    atualizar_sl(
                                                        posicao_atual.ticket, sl_alvo)
                                            else:
                                                # zero/prejuÃÂ­zo leve + fluxo MUITO contra: corta em vez de breakeven
                                                logging.warning(
                                                    f"Ã°Å¸ââ INVERSÃÆO DE FLUXO (lucro {lucro_pontos_inv:+.1f}pts)! Ratio contrÃÂ¡rio: {ratio_inversao:.2f} | "
                                                    f"SAINDO para cortar a perda (breakeven nÃÂ£o protege e nÃÂ£o ÃÂ© executÃÂ¡vel)")
                                                fechar_posicao_atual(
                                                    motivo=f"InversÃÂ£o de fluxo (ratio {ratio_inversao:.2f})")
                                                posicao_atual = None
                                                posicao_aberta = False
                        except Exception as e:
                            logging.debug(
                                f"[InversÃÂ£o Fluxo] Erro na verificaÃÂ§ÃÂ£o: {e}")

                        # ========== Ã¢Å¡Â¡ SNIPER %R: TRAILING (fiel ao backtest variante A) ==========
                        # R = SL = 1.5xATR. ApÃ³s lucro >= R, move SL para a entrada +
                        # 50% do ganho (trailing 50%), apenas melhorando o SL.
                        # O TP (2R) jÃ¡ estÃ¡ no MT5; o GerenciadorDeSaida Ã© pulado
                        # para posiÃ§Ãµes sniper (regras dele cortariam o trade %R cedo).
                        if posicao_atual is not None and bool((posicao_atual.entry_context or {}).get('sniper_wr', 0)):
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
                                    _r_sniper = float(posicao_atual.entry_context.get(
                                        'sniper_sl_points', 2.5) or 2.5)
                                    if _lucro_pts >= _r_sniper:
                                        _sl_alvo_trail = (
                                            _entrada + 0.5 * _lucro_pts if _is_buy
                                            else _entrada - 0.5 * _lucro_pts
                                        )
                                        _melhoria = (
                                            _sl_alvo_trail > _sl_atual if _is_buy
                                            else _sl_alvo_trail < _sl_atual
                                        )
                                        if _melhoria:
                                            # FIX 11/08: SEM eh_breakeen_forcado â a validaÃ§Ã£o de
                                            # distÃ¢ncia mÃ­nima no atualizar_sl evita o retcode 10016
                                            # "Invalid stops" (SL dentro da zona de freeze).
                                            if atualizar_sl(posicao_atual.ticket, _sl_alvo_trail):
                                                logging.info(
                                                    f"â¡ SNIPER %R: trailing 50% â SL {_sl_alvo_trail:.2f} (lucro {_lucro_pts:.1f}pts, R={_r_sniper:.1f})")
                            except Exception:
                                pass

                        # CHAMA O GERENCIADOR UNIFICADO (PULADO para SNIPER %R â SL/TP
                        # por ATR no MT5 + trailing acima jÃ¡ gerenciam a saÃ­da)
                        _pos_eh_sniper_wr = bool(
                            (posicao_atual.entry_context or {}).get('sniper_wr', 0)
                        ) if posicao_atual else False
                        if _pos_eh_sniper_wr:
                            deve_sair, motivo, novo_sl = False, None, None
                        else:
                            deve_sair, motivo, novo_sl = gerenciador_saida.verificar_condicoes_saida(
                                preco_atual, rsi_atual=50)  # Passe o RSI real

                        if deve_sair:
                            logging.info(f"Ã°Å¸Å¡Âª DecisÃÂ£o de SaÃÂ­da: {motivo}")
                            # Verificar se posiÃÂ§ÃÂ£o ainda existe antes de tentar fechar
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
                                    f"Ã¢Åâ¦ PosiÃÂ§ÃÂ£o {ticket_para_verificar} jÃÂ¡ foi fechada pelo MT5 (TP/SL). Sem aÃÂ§ÃÂ£o necessÃÂ¡ria.")
                                gerenciador_saida.finalizar_monitoramento()
                            else:
                                # PosiÃÂ§ÃÂ£o ainda aberta Ã¢â¬â tenta fechar com atÃÂ© 3 tentativas
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
                                            f"Ã¢Å¡Â Ã¯Â¸Â Tentativa {tentativa+1}/3 de fechar falhou. Aguardando 1s...")
                                        time.sleep(1)
                                        if not mt5.initialize():
                                            reconectar_mt5()

                                if not fechou:
                                    logging.error(
                                        f"Ã¢ÂÅ FALHA AO FECHAR POSIÃâ¡ÃÆO apÃÂ³s 3 tentativas! PosiÃÂ§ÃÂ£o pode estar aberta.")

                                gerenciador_saida.finalizar_monitoramento()
                        elif novo_sl:
                            # FIX: Se SL jÃÂ¡ estÃÂ¡ em breakeen, sÃÂ³ ignora se o novo SL NÃÆO ÃÂ© uma melhoria
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
                                    f"Ã°Å¸ââ SL jÃÂ¡ em breakeen e novo SL nÃÂ£o ÃÂ© melhoria - ignorado (novo={novo_sl:.2f} vs atual={sl_atual_pos:.2f})")
                            else:
                                logging.info(
                                    f"Ã°Å¸âÂ§ DecisÃÂ£o de Ajuste: Novo SL {novo_sl:.2f}")
                                if posicao_atual is not None:
                                    atualizar_sl(posicao_atual.ticket, novo_sl)
                    elif not tick:
                        logging.warning(
                            "Ã¢Å¡Â Ã¯Â¸Â Tick indisponÃÂ­vel para monitoramento de posiÃÂ§ÃÂ£o")
                    elif posicao_atual is None:
                        logging.warning(
                            "Ã¢Å¡Â Ã¯Â¸Â posicao_atual ainda ÃÂ© None apÃÂ³s tentativas de sincronizaÃÂ§ÃÂ£o. Usando fallback.")
                        # Como ÃÂºltimo recurso, fecha todas as posiÃÂ§ÃÂµes
                        fechar_todas_posicoes("Fallback - posicao_atual None")
                        gerenciador_saida.finalizar_monitoramento()

                    time.sleep(INTERVALO_CHECK_SCORE)
                    continue

                if posicao_atual is not None:
                    # Processa a posiÃÂ§ÃÂ£o fechada uma ÃÂºnica vez
                    ticket_processado = posicao_atual.ticket
                    lucro_real, score_dist = obter_lucro_ultima_ordem(
                        ticket_processado)
                    # PATCH v22.1 CORTE 1: Reconciliacao de saida nao sincronizada.
                    # Se o deal real nao veio no primeiro ciclo, tenta retries e,
                    # em ultimo caso, marca PENDING_RECONCILIATION (persistente)
                    # para o deal aparecer e o resultado NAO se perder (Trade #1).
                    if lucro_real == 0.0:
                        lucro_retry = buscar_deal_historico_estendido(
                            ticket_processado)
                        if lucro_retry != 0.0:
                            lucro_real = lucro_retry
                        else:
                            adicionar_pendente_reconciliacao(
                                ticket_processado, posicao_atual.tipo,
                                getattr(posicao_atual, 'preco_entrada', 0.0))
                    gerenciador_bloqueio.registrar_operacao(
                        posicao_atual.tipo, lucro_real)
                    if posicao_atual.entry_context is not None:
                        memoria_experiencias.adicionar(
                            posicao_atual.entry_context.copy(), posicao_atual.tipo, lucro_real, score_dist)
                        salvar_experiencia_csv(posicao_atual.entry_context.copy(
                        ), posicao_atual.tipo, lucro_real, score_dist)

                        # ========== REGISTRO RESULTADO CONFLUÃÅ NCIA ==========
                        if sistema_confluencia and confluencia_info_atual:
                            sistema_confluencia.registrar_resultado_confluencia(
                                confluencia_info_atual, lucro_real)
                            logging.info(
                                f"Ã°Å¸Å½Â¯ Resultado confluÃÂªncia registrado: Lucro={lucro_real:.2f}")

                        # Treina modelo com proteÃÂ§ÃÂ£o contra erros (apenas quando necessÃÂ¡rio)
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(
                                f"Ã¢ÂÅ Erro no treinamento do modelo: {e}")
                            logging.debug(
                                f"Stack trace: {traceback.format_exc()}")
                    else:
                        logging.warning(
                            "Ã¢Å¡Â Ã¯Â¸Â Contexto de entrada nÃÂ£o encontrado em posicao_atual ao fechar.")
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

                    # IMPORTANTE: Reset da posiÃÂ§ÃÂ£o ANTES de continuar
                    # DESATIVA O GERENCIADOR DE SAÃÂDA (PASSO 2)
                    gerenciador_saida.finalizar_monitoramento()

                    posicao_atual = None
                    logging.info(
                        f"Ã¢Åâ¦ PosiÃÂ§ÃÂ£o {ticket_processado} processada e resetada.")
                    # FIX 11/08: trava de zona reseta apenas quando a posiÃ§Ã£o
                    # FECHA (fiel ao backtest L178) â permite re-entrada na mesma
                    # zona, mas SEM o spam de sinal a cada 2s do loop.
                    sniper_supermo.em_zona = 0

                    # Pequena pausa para evitar loop imediato
                    time.sleep(1)

                posicao_aberta = False
                SNIPER_SUPERMO_ATIVO = False  # Reset apÃÂ³s fechamento
                # Rebaixado para debug: o log de mercado (a cada 5s) e o standby Sniper
                # (a cada 10s) jÃÂ¡ mostram que o robÃÂ´ estÃÂ¡ vivo e analisando Ã¢â¬â evita spam.
                logging.debug(
                    "Nenhuma posiÃÂ§ÃÂ£o ativa. Analisando nova entrada...")

                # Verifica se o mercado estÃÂ¡ aberto (DESABILITADO para mercado fechado)
                # if not verificar_estado_book(SYMBOL):
                #     logging.warning(
                #         "Ã¢Å¡Â Ã¯Â¸Â Book em estado invÃÂ¡lido. Tentando reiniciar...")
                #     if reiniciar_book(SYMBOL):
                #         logging.info("Ã¢Åâ¦ Book reiniciado com sucesso")
                #     else:
                #         logging.error("Ã¢ÂÅ Falha ao reiniciar book. AguardandoÃ¢â¬Â¦")

                # VerificaÃÂ§ÃÂ£o simplificada para mercado fechado
                agora = datetime.now().time()
                inicio_pregao = datetime.strptime("09:00", "%H:%M").time()
                fim_pregao = datetime.strptime("17:40", "%H:%M").time()

                if agora < inicio_pregao or agora > fim_pregao:
                    logging.info(
                        f"Ã°Å¸â¢Â Mercado fechado ({agora.strftime('%H:%M')}): modo simulaÃÂ§ÃÂ£o ativo")
                    time.sleep(30)
                    continue

                # ========== HIBERNAÃâ¡ÃÆO 12:30-14:30 (REDUZIDA - SNIPER CONTINUA ATIVO) ==========
                inicio_hibernacao = dtime(12, 30)
                fim_hibernacao = dtime(14, 30)

                if inicio_hibernacao <= agora < fim_hibernacao:
                    # Treina uma vez ao entrar na hibernaÃÂ§ÃÂ£o (exatamente ÃÂ s 12h)
                    if agora.hour == 12 and agora.minute == 30:
                        logging.info(
                            "Ã°Å¸Â§Â  TREINO DO MEIO-DIA: Iniciando treino antes da hibernaÃÂ§ÃÂ£o...")
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                            logging.info(
                                "Ã¢Åâ¦ TREINO DO MEIO-DIA CONCLUÃÂDO. HibernaÃÂ§ÃÂ£o reduzida Ã¢â¬â sniper ativo.")
                        except Exception as e:
                            logging.error(f"Ã¢ÂÅ Erro no treino do meio-dia: {e}")

                    # HibernaÃÂ§ÃÂ£o reduzida: loop normal mas modo normal bloqueado
                    # SniperSupermo pode operar mesmo em hibernaÃÂ§ÃÂ£o
                    logging.debug(
                        "Ã°Å¸ËÂ´ HibernaÃÂ§ÃÂ£o 12:30-14:30 (sniper ativo, modo normal bloqueado por horÃÂ¡rio)")
                    time.sleep(5)
                    continue

                # ========== TREINO DAS 17:30 ANTES DE ENCERRAR ==========
                inicio_treino_tarde = dtime(17, 30)
                fim_treino_tarde = dtime(17, 31)  # Janela de 1 minuto

                if inicio_treino_tarde <= agora < fim_treino_tarde:
                    logging.info(
                        "Ã°Å¸Â§Â  TREINO DA TARDE: Iniciando treino antes do encerramento...")
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                        logging.info(
                            "Ã¢Åâ¦ TREINO DA TARDE CONCLUÃÂDO. Aguardando encerramento ÃÂ s 17:35...")
                    except Exception as e:
                        logging.error(f"Ã¢ÂÅ Erro no treino da tarde: {e}")
                    time.sleep(60)  # Evita re-treinar no mesmo minuto
                    continue

                # ===== FORA DA JANELA PA1 (ex.: apÃÂ³s 17:15) Ã¢â¬â NÃÆO opera, sÃÂ³ aguarda =====
                # "Bloquear operaÃÂ§ÃÂµes ÃÂ s 17:15" = nem processa decisÃÂ£o/salva/treina ÃÂ  toa.
                # Evita churn de CPU/disco e spam de log fora de 09:15-12:30 / 14:30-17:15.
                # (SÃÂ³ entra aqui quando NÃÆO hÃÂ¡ posiÃÂ§ÃÂ£o Ã¢â¬â posiÃÂ§ÃÂµes abertas seguem monitoradas.)
                if not horario_permitido():
                    if _log_periodico('fora_pa1', 300):
                        logging.info(
                            f"Ã°Å¸Å¡Â« Fora do horÃÂ¡rio PA1 ({datetime.now().strftime('%H:%M')}) Ã¢â¬â "
                             f"aguardando prÃÂ³xima janela (09:15-12:30 / 14:30-17:15)")
                    time.sleep(30)
                    continue

                # ObtÃÂ©m dados do mercado
                bid_qty, ask_qty, spread, volatility, candle_type, book_data, rsi_14, volume_tick, close_price, williams_r = obter_dados_mercado(
                    SYMBOL)

                # Se algum dado for None, pula a iteraÃÂ§ÃÂ£o
                if None in (bid_qty, ask_qty, spread, volatility, candle_type, book_data, rsi_14, volume_tick, close_price, williams_r):
                    logging.warning(
                        "Ã¢Å¡Â Ã¯Â¸Â Dados do mercado incompletos. Aguardando prÃÂ³xima iteraÃÂ§ÃÂ£o...")
                    time.sleep(2)
                    continue

                # ========== TRAVA DE TIMESTAMP: Ignora dados anteriores ÃÂ  inicializaÃÂ§ÃÂ£o ==========
                # O EA Sniper grava "timestamp" no JSON. Verificamos se o dado ÃÂ© POSTERIOR
                # ÃÂ  inicializaÃÂ§ÃÂ£o do robÃÂ´. Dados antigos do arquivo sÃÂ£o ignorados.
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

                        # Verifica se ÃÂ© dado POSTERIOR ÃÂ  inicializaÃÂ§ÃÂ£o
                        if timestamp_ea_epoch > 0 and timestamp_ea_epoch < timestamp_inicializacao:
                            # Dado antigo Ã¢â¬â EA nÃÂ£o atualizou desde que o robÃÂ´ iniciou
                            if ultimo_timestamp_ea_processado is None:
                                logging.warning(
                                    f"Ã°Å¸ââ TRAVA TIMESTAMP: Ignorando dado antigo do EA "
                                    f"(timestamp EA: {timestamp_ea} | "
                                    f"RobÃÂ´ iniciou: {datetime.fromtimestamp(timestamp_inicializacao).strftime('%H:%M:%S')})")
                                ultimo_timestamp_ea_processado = "aguardando"
                            time.sleep(2)
                            continue
                        else:
                            # Dado novo! Pode operar
                            if ultimo_timestamp_ea_processado == "aguardando":
                                logging.info(
                                    f"Ã¢Åâ¦ TRAVA TIMESTAMP LIBERADA: Dado novo recebido do EA (timestamp: {timestamp_ea})")
                            ultimo_timestamp_ea_processado = timestamp_ea
                    except (ValueError, TypeError):
                        # Se nÃÂ£o consegue parsear timestamp, aceita o dado (compatibilidade)
                        pass

                # ========== Ã°Å¸âÂ¡ LEITURA DO BOOK DOL (FLUXO INSTITUCIONAL) ==========
                # O DOL ÃÂ© o mercado "real" onde grandes players operam.
                # O WDO ÃÂ© espelhado por HFTs com ~0.5-2s de atraso.
                # Ler o DOL permite antecipar movimentos do WDO.
                book_dol_data = ler_book_dol()
                sinal_dol = analisar_sinal_dol(book_dol_data)

                # Log periÃÂ³dico do sinal DOL (1x a cada 2min)
                if sinal_dol['presente'] and _log_periodico('dol', 120):
                    logging.info(
                        f"Ã°Å¸âÅ  DOL {SYMBOL_DOL}: ratio={sinal_dol['ratio']:.2f} "
                        f"lado={sinal_dol['lado']} conf={sinal_dol['confianca']:.2f} "
                        f"vol={sinal_dol['volume_total']:.0f}")

                # ========== Ã°Å¸Å½Â¯ FILTRO SNIPER DE ELITE (BOOK NATIVO) ==========
                # O robÃÂ´ sÃÂ³ "acorda" para buscar entrada quando hÃÂ¡ volume institucional
                # no book (>= SNIPER_VOLUME_MIN) E desequilÃÂ­brio claro entre os lados
                # (ratio >= SNIPER_RATIO_MIN). Ambos ajustÃÂ¡veis no topo do arquivo.
                # Caso contrÃÂ¡rio: standby silencioso aguardando os Big Players.
                sniper_bid = book_data.get('total_bid_volume', 0) if isinstance(
                    book_data, dict) else 0
                sniper_ask = book_data.get('total_ask_volume', 0) if isinstance(
                    book_data, dict) else 0
                sniper_total = sniper_bid + sniper_ask
                sniper_ratio = 0.0
                if sniper_bid > 0 and sniper_ask > 0:
                    sniper_ratio = max(sniper_bid, sniper_ask) / \
                        min(sniper_bid, sniper_ask)

                # Em modo SNIPER_APENAS o gate de "Big Players" Ã© PULADO: o
                # sniper %R (cÃ©rebro atual) decide SÃ pelo %R (<= -80 / >= -20),
                # fiel ao backtest variante A â sem exigÃªncia de volume/ratio de
                # book. O gate permanece ativo quando o robÃ´ normal (IA) opera.
                if not SNIPER_APENAS and (
                    sniper_total < SNIPER_VOLUME_MIN or sniper_ratio < SNIPER_RATIO_MIN):
                    if _log_periodico('standby', 300):  # 1x a cada 5min (pulso jÃÂ¡ mostra vida)
                        logging.info(
                            f"Ã°Å¸ËÂ´ Standby: Aguardando Big Players... "
                            f"(Vol {sniper_total:.0f}/{SNIPER_VOLUME_MIN} | "
                            f"Ratio {sniper_ratio:.2f}/{SNIPER_RATIO_MIN})")
                    time.sleep(1)
                    continue

                # --- NOVA LÃâGICA DE ANÃÂLISE DE PROFUNDIDADE ---
                tick_info = mt5.symbol_info_tick(SYMBOL)
                preco_atual_ref = (
                    tick_info.bid + tick_info.ask) / 2 if tick_info else 0

                features_profundidade = analisar_profundidade_book(
                    book_data, preco_atual_ref)
                # --- FIM DA NOVA LÃâGICA ---

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

                # ========== FEATURES 16-18: DADOS REAIS DA POSIÃâ¡ÃÆO ==========
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

                # Williams %R monitor (log only, nÃÂ£o bloqueia)
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
                    # Sinal DOL: desequilÃÂ­brio do book do dÃÂ³lar cheio (referÃÂªncia institucional)
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
                    # FIX 11/08: tendÃªncia EMA9/21 M1 do detector (filtro contra-tendÃªncia do sniper)
                    "tendencia_m1": detector_tendencia.tendencia_atual if (detector_tendencia and DETECTOR_TENDENCIA_ATIVO) else "NEUTRO",
                    **features_profundidade  # Adiciona todas as novas features de uma vez!
                }
                # ========== COLETA MULTI-TIMEFRAME (M5/M15/M30) ==========
                # Coleta silenciosa para histÃÂ³rico sem interferir na decisÃÂ£o M1.
                mtf_result = obter_dados_multitf(SYMBOL)
                if None not in mtf_result:
                    rsi5, atr5, wr5, close5, vol5, rsi15, atr15, wr15, close15, vol15, rsi30, atr30, wr30, close30, vol30 = mtf_result
                    dados_mtf = {
                        "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                        "rsi_5": round(rsi5, 2), "atr_5": round(atr5, 2), "wr_5": round(wr5, 2), "close_5": round(close5, 2), "vol_5": vol5,
                        "rsi_15": round(rsi15, 2), "atr_15": round(atr15, 2), "wr_15": round(wr15, 2), "close_15": round(close15, 2), "vol_15": vol15,
                        "rsi_30": round(rsi30, 2), "atr_30": round(atr30, 2), "wr_30": round(wr30, 2), "close_30": round(close30, 2), "vol_30": vol30,
                    }
                    if _log_periodico('multitf_csv', 60):
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
                # close_price separado para detector de tendÃÂªncia (nÃÂ£o vai para IA)
                close_price_para_tendencia = close_price

                # Dashboard V2 Ã¢â¬â Atualiza variÃÂ¡veis de estado para o dashboard
                spread_atual = spread
                atr_atual = volatility
                rsi_atual = rsi_14

                # ATUALIZA E VERIFICA O VOLUME ADAPTATIVO (PASSO 2)
                volume_total_book = contexto.get(
                    'bid_qty', 0) + contexto.get('ask_qty', 0)
                volume_adaptativo.adicionar_volume_atual(volume_total_book)

                # MODO EMERGÃÅ NCIA: ForÃÂ§a operaÃÂ§ÃÂ£o apÃÂ³s muitas rejeiÃÂ§ÃÂµes
                # (pulado em SNIPER_APENAS â o sniper %R nÃÂ£o usa volume adaptativo)
                if not SNIPER_APENAS and not volume_adaptativo.pode_operar(volume_total_book):
                    contador_rejeicoes_consecutivas += 1

                    if contador_rejeicoes_consecutivas >= LIMITE_REJEICOES_EMERGENCIA:
                        # Ã¢Åâ¦ PA1: MESMO NO MODO EMERGÃÅ NCIA, RESPEITA HORÃÂRIO
                        if not horario_permitido():
                            horario_atual = datetime.now().strftime("%H:%M")
                            logging.warning(
                                f"Ã°Å¸Å¡Â« PA1 MODO EMERGÃÅ NCIA BLOQUEADO POR HORÃÂRIO: {horario_atual}")
                            time.sleep(2)
                            continue

                        logging.warning(
                            f"Ã°Å¸Å¡Â¨ MODO EMERGÃÅ NCIA ATIVADO! {contador_rejeicoes_consecutivas} rejeiÃÂ§ÃÂµes consecutivas - FORÃâ¡ANDO OPERAÃâ¡ÃÆO!")
                        contador_rejeicoes_consecutivas = 0
                        # Continua para forÃÂ§ar operaÃÂ§ÃÂ£o mesmo com volume baixo
                    else:
                        logging.info(
                            f"Ã°Å¸Å¡Â« OperaÃÂ§ÃÂ£o bloqueada: Volume atual ({volume_total_book:.0f}) < MÃÂ­nimo Adaptativo ({volume_adaptativo.volume_minimo_adaptativo:.0f}) - RejeiÃÂ§ÃÂµes: {contador_rejeicoes_consecutivas}/{LIMITE_REJEICOES_EMERGENCIA}")
                        time.sleep(2)
                        continue  # Pula para a prÃÂ³xima iteraÃÂ§ÃÂ£o do loop
                else:
                    # Reset contador quando volume ÃÂ© adequado
                    contador_rejeicoes_consecutivas = 0

                logging.debug(f"Ã°Å¸âÅ  Contexto para decisÃÂ£o: {contexto}")

                # ========== SANITY CHECK: DADOS CONGELADOS ==========
                if verificar_dados_congelados(
                    contexto.get('bid_qty', 0),
                    contexto.get('ask_qty', 0)
                ):
                    # Dados congelados Ã¢â¬â nÃÂ£o opera mas continua monitorando
                    time.sleep(10)
                    continue

                monitorar_recursos()

                # PATCH v22.1 CORTE 1: processa pendentes de reconciliacao
                # (posicoes cujo deal de saida atrasou; fecha o ciclo p/ shadow)
                reconciliar_pendentes()

                # >>> Bloco de DecisÃÂ£o e Salvamento de DecisÃÂ£o (Movido para Cima) <<<
                acao_para_executar = "NADA"  # Default
                confianca_decisao = 0.0

                # Garante que o scaler estÃÂ¡ limpo do JSON (treino online nÃÂ£o corrompe)
                forcar_recreacao_scaler()

                contexto_df_previsao = pd.DataFrame([contexto])
                # Adiciona coluna 'action' dummy se nÃÂ£o existir, para consistÃÂªncia com preparar_dados
                if 'action' not in contexto_df_previsao.columns:
                    contexto_df_previsao['action'] = "BUY"  # Dummy
                X_decisao, _ = preparar_dados(
                    contexto_df_previsao, treino=False)

                if X_decisao is None or X_decisao.shape[1] != N_FEATURES:
                    logging.error(
                        f"Ã¢ÂÅ Dados invÃÂ¡lidos para previsÃÂ£o (X_decisao). Shape: {X_decisao.shape if X_decisao is not None else 'None'}")
                    time.sleep(2)
                    continue

                # Ã¢Åâ¦ REMOVIDA A PRIMEIRA OPERAÃâ¡ÃÆO ALEATÃâRIA
                # Motivo: entrava sem anÃÂ¡lise (antes da IA ter contexto) e causava
                # conflito de fechamento entre C12 e TP do MT5 (order_send None)
                # Agora a IA decide desde o primeiro ciclo normalmente
                try:
                    acao_predita, confianca_predita = prever_acao(
                        modelo_ia_local, X_decisao, modo_operacional,
                        None, contexto)

                    # ========== INTEGRAÃâ¡ÃÆO SISTEMA DE CONFLUÃÅ NCIA ==========
                    # Short-circuit: se prever_acao jÃÂ¡ retornou NADA (cooldown P0, horÃÂ¡rio, veto),
                    # nÃÂ£o recalcula IA/ConfluÃÂªncia Ã¢â¬â economiza CPU e evita logs confusos
                    if acao_predita == "NADA" and confianca_predita == 0.0:
                        acao_para_executar = "NADA"
                        confianca_decisao = 0.0
                    elif sistema_confluencia:
                        # Obter probabilidade bruta da IA para confluÃÂªncia
                        # X_decisao jÃÂ¡ foi normalizado pela funÃÂ§ÃÂ£o preparar_dados
                        x_pred = X_decisao.values.astype(np.float32)
                        prob_bruta = modelo_ia_local.predict(
                            x_pred, verbose=0)[0][0]

                        # Verificar confluÃÂªncia de sinais
                        confluencia_info = sistema_confluencia.verificar_confluencia(
                            contexto, prob_bruta, acao_predita)

                        # Armazenar para uso posterior
                        confluencia_info_atual = confluencia_info

                        # Log detalhado da confluÃÂªncia (DEBUG Ã¢â¬â repetia a cada decisÃÂ£o)
                        logging.debug(
                            f"Ã°Å¸Å½Â¯ CONFLUÃÅ NCIA: {confluencia_info['detalhes']} | Score: {confluencia_info['score']}")
                        logging.debug(
                            f"Ã°Å¸Å½Â¯ Sinais BUY: {confluencia_info['sinais_buy']}")
                        logging.debug(
                            f"Ã°Å¸Å½Â¯ Sinais SELL: {confluencia_info['sinais_sell']}")

                        # ========== REFATORADO: NOVA LÃâGICA DE DECISÃÆO ==========
                        # Ã°Å¸Å½Â¯ REGRA 1: IA com confianÃÂ§a > 80% NÃÆO pode ser invertida pela confluÃÂªncia
                        # Ã°Å¸Å½Â¯ REGRA 2: ConfluÃÂªncia precisa de mÃÂ­nimo 2 sinais tÃÂ©cnicos

                        # Verifica se VETO MATEMÃÂTICO estÃÂ¡ ativo
                        veto_ativo = getattr(
                            prever_acao, '_ultimo_veto', False)

                        # Verifica confianÃÂ§a alta da IA
                        # NOTA: prob_bruta=0.0 (modelo nÃÂ£o treinado) NÃÆO ÃÂ© confianÃÂ§a alta
                        ia_confianca_alta = (prob_bruta > 0.8 or prob_bruta < 0.2) and prob_bruta != 0.0

                        if veto_ativo:
                            # VETO MATEMÃÂTICO ativo - nada sobrescreve
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                            logging.warning(
                                f"Ã°Å¸Å¡Â« CONFLUÃÅ NCIA BLOQUEADA: Veto matemÃÂ¡tico ativo - hierarquia respeitada")

                        elif ia_confianca_alta:
                            # IA com confianÃÂ§a > 80% - ConfluÃÂªncia NÃÆO pode inverter
                            if confluencia_info['acao'] == acao_predita:
                                # ConfluÃÂªncia confirma IA de alta confianÃÂ§a
                                acao_para_executar = acao_predita
                                # BÃÂ´nus por confirmaÃÂ§ÃÂ£o
                                confianca_decisao = min(
                                    prob_bruta * 1.15, 1.0)
                                logging.debug(
                                    f"Ã°Å¸ââ IA ALTA CONFIANÃâ¡A CONFIRMADA: {acao_predita} | ConfianÃÂ§a: {confianca_decisao:.2f}")
                            elif confluencia_info['acao'] == "NADA":
                                # ConfluÃÂªncia sem sinais suficientes - respeita IA de alta confianÃÂ§a
                                acao_para_executar = acao_predita
                                confianca_decisao = prob_bruta
                                logging.debug(
                                    f"Ã°Å¸ââ IA ALTA CONFIANÃâ¡A MANTIDA: {acao_predita} (ConfluÃÂªncia insuficiente)")
                            else:
                                # ConfluÃÂªncia tenta inverter - BLOQUEADA
                                acao_para_executar = acao_predita
                                confianca_decisao = prob_bruta * 0.9  # Penalidade leve por divergÃÂªncia
                                logging.warning(
                                    f"Ã°Å¸ââ INVERSÃÆO BLOQUEADA: IA={acao_predita} (conf:{prob_bruta:.2f}) PREVALECE sobre ConfluÃÂªncia={confluencia_info['acao']}")

                        elif confluencia_info['acao'] != "NADA":
                            # ConfluÃÂªncia com sinais suficientes (Ã¢â°Â¥2) e IA sem alta confianÃÂ§a
                            if confluencia_info['acao'] != acao_predita:
                                # ConfluÃÂªncia sobrescreve IA de baixa/mÃÂ©dia confianÃÂ§a
                                logging.warning(
                                    f"Ã°Å¸Å½Â¯ CONFLUÃÅ NCIA SOBRESCREVE: IA={acao_predita} (conf:{prob_bruta:.2f}) Ã¢â â CONFLUÃÅ NCIA={confluencia_info['acao']}")
                                acao_para_executar = confluencia_info['acao']
                                confianca_decisao = confluencia_info['confianca']
                            else:
                                # ConfluÃÂªncia confirma IA
                                acao_para_executar = acao_predita
                                base_confianca = confianca_predita if confianca_predita > 0.0 else confluencia_info[
                                    'confianca']
                                confianca_decisao = min(
                                    base_confianca * 1.2, 1.0)
                                logging.info(
                                    f"Ã°Å¸Å½Â¯ CONFLUÃÅ NCIA CONFIRMA: {acao_predita} | ConfianÃÂ§a aumentada: {confianca_decisao:.2f}")
                        else:
                            # ConfluÃÂªncia sem sinais suficientes (<2)
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                            logging.info(
                                f"Ã°Å¸Å½Â¯ CONFLUÃÅ NCIA BLOQUEIA: Menos de 2 sinais tÃÂ©cnicos (mÃÂ­nimo exigido)")
                    else:
                        # sistema_confluencia nÃÂ£o inicializado Ã¢â¬â usa aÃÂ§ÃÂ£o direta da IA
                        acao_para_executar = acao_predita
                        confianca_decisao = confianca_predita

                    # ========== Ã°Å¸âÂ¡ VETO/CONFIRMAÃâ¡ÃÆO PELO DOL ==========
                    # O DOL ÃÂ© o mercado "real" Ã¢â¬â se ele contradiz a decisÃÂ£o,
                    # ÃÂ© um sinal forte de que o WDO pode nÃÂ£o seguir.
                    # Regra: DOL com confianÃÂ§a > 0.6 e lado oposto = VETO
                    # (exceto se IA tem confianÃÂ§a > 80%)
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
                            # DOL contradiz E IA nÃÂ£o tem confianÃÂ§a alta Ã¢â â VETO
                            logging.warning(
                                f"Ã°Å¸âÅ Ã°Å¸Å¡Â« DOL VETA: IA/ConfluÃÂªncia={acao_para_executar} "
                                f"mas DOL={sinal_dol['lado']} "
                                f"(ratio={sinal_dol['ratio']:.2f}, conf={sinal_dol['confianca']:.2f})")
                            acao_para_executar = "NADA"
                            confianca_decisao = 0.0
                        elif dol_contra and ia_confianca_alta:
                            # DOL contradiz MAS IA tem confianÃÂ§a alta Ã¢â â penalidade
                            confianca_decisao *= 0.85
                            logging.warning(
                                f"Ã°Å¸âÅ Ã¢Å¡Â Ã¯Â¸Â DOL CONTRARIA IA: {acao_para_executar} "
                                f"(DOL={sinal_dol['lado']}, ratio={sinal_dol['ratio']:.2f}) "
                                f"Ã¢â â confianÃÂ§a reduzida: {confianca_decisao:.2f}")
                        elif dol_confirma:
                            # DOL confirma Ã¢â â bÃÂ´nus de confianÃÂ§a
                            confianca_decisao = min(confianca_decisao * 1.1, 1.0)
                            logging.debug(
                                f"Ã°Å¸âÅ Ã¢Åâ¦ DOL CONFIRMA: {acao_para_executar} "
                                f"(ratio={sinal_dol['ratio']:.2f}) "
                                f"Ã¢â â confianÃÂ§a: {confianca_decisao:.2f}")

                    # ========== NOVOS FILTROS PÃS-DOL (nÃ£o-SNIPER) ==========
                    # 1. DOL confianÃ§a â¥ DOL_CONF_MIN + alinhado obrigatÃ³rio para entradas nÃ£o-sniper
                    # 2. Book ratio â¥ BOOK_RATIO_MIN para qualquer trade direcional
                    # Valores lidos do config.json (editaveis pelo agente autonomo, whitelist):
                    DOL_CONF_MIN = float(config.get("dol_conf_min", 0.4))
                    BOOK_RATIO_MIN = float(config.get("book_ratio_min", 1.3))
                    if not SNIPER_SUPERMO_ATIVO and acao_para_executar != "NADA":
                        dol_conf = sinal_dol.get('confianca', 0) if sinal_dol.get('presente') else 0
                        dol_lado = sinal_dol.get('lado', 'NEUTRO') if sinal_dol.get('presente') else 'NEUTRO'
                        bid_qty_atual = contexto.get('bid_qty', 0)
                        ask_qty_atual = contexto.get('ask_qty', 0)
                        book_ratio = max(bid_qty_atual, ask_qty_atual) / max(1, min(bid_qty_atual, ask_qty_atual))

                        dol_ok = (dol_conf >= DOL_CONF_MIN and dol_lado != 'NEUTRO' and dol_lado == acao_para_executar)
                        ratio_ok = book_ratio >= BOOK_RATIO_MIN

                        # MODO ADVISORY (03/08): DOL/book INFORMAM a confianca, NAO vetam mais.
                        # O veto seco zerava 100% das entradas em dia de DOL equilibrado (autopsia 03/08),
                        # autossabotando o Item 3 (0 trades -> 0 amostra -> nunca valida o robo).
                        # Protecao real MANTIDA: gate#1 (contradicao DOL forte), sentinela, WR, multi-TF,
                        # score de qualidade, CONFIDENCE_GAP, cooldown, circuit breakers, max_loss_diario.
                        if not dol_ok:
                            confianca_decisao *= 0.70
                            logging.warning(
                                f"â ï¸ DOL fraco/desalinhado (conf={dol_conf:.2f} lado={dol_lado} â  {acao_para_executar}) -> conf Ã0.70={confianca_decisao:.2f} (ADVISORY, sem veto)")
                        if not ratio_ok:
                            confianca_decisao *= 0.85
                            logging.warning(
                                f"â ï¸ Book ratio baixo ({book_ratio:.2f}x < {BOOK_RATIO_MIN}) -> conf Ã0.85={confianca_decisao:.2f} (ADVISORY, sem veto)")

                    logging.debug(
                        f"Ã°Å¸Â¤â DecisÃÂ£o Final: {acao_para_executar} | ConfianÃÂ§a: {confianca_decisao:.2f}")
                except Exception as e:
                    logging.error(
                        f"Ã¢ÂÅ Erro ao prever aÃÂ§ÃÂ£o (bloco principal): {e}")
                    logging.debug(
                        f"Shape de X_decisao: {X_decisao.shape if X_decisao is not None else 'None'}")
                    time.sleep(2)
                    continue

                # Salva a decisÃÂ£o ANTES de qualquer filtro que possa impedir a execuÃÂ§ÃÂ£o da ordem
                salvar_decisao_csv(acao_para_executar,
                                   confianca_decisao, contexto)
                ultima_decisao = acao_para_executar  # Atualiza ultima_decisao global
                # >>> Fim do Bloco de DecisÃÂ£o e Salvamento de DecisÃÂ£o <<<

                # ========== FIX 11/08: TENDENCIA FRESCA ANTES DO SNIPER ==========
                # Atualiza o detector EMA9/21 ANTES do sniper e injeta no contexto,
                # para o filtro contra-tendencia usar o valor mais recente.
                if detector_tendencia and DETECTOR_TENDENCIA_ATIVO:
                    if close_price_para_tendencia > 0:
                        detector_tendencia.atualizar_tendencia(
                            close_price_para_tendencia)
                        status_tendencia = detector_tendencia.get_status()
                        logging.debug(
                            f"ð Tendencia atualizada: {status_tendencia['tendencia']} | Close: {close_price_para_tendencia}")
                    else:
                        logging.warning(
                            "â ï¸ Close price nao disponivel para detector de tendencia")
                if contexto is not None:
                    contexto['tendencia_m1'] = (
                        detector_tendencia.tendencia_atual
                        if (detector_tendencia and DETECTOR_TENDENCIA_ATIVO) else "NEUTRO"
                    )
                    # FIX 12/08: vetos do FiltroTendencia (SMA-50 + momentum) â
                    # mesmo detector que bloqueou o dia 11/08 corretamente. O
                    # EMA9/21 ficava NEUTRO nos momentos de entrada; o SMA-50
                    # detectou a tendÃªncia o dia todo.
                    _preco_tend_sniper = (contexto.get('preco', 0)
                                          or contexto.get('preco_maior_escora_bid', 0))
                    if _preco_tend_sniper and _preco_tend_sniper > 0:
                        try:
                            _res_tend_sniper = filtro_tendencia.avaliar_tendencia(_preco_tend_sniper)
                            contexto['tendencia_veto_buy'] = _res_tend_sniper['veto_buy']
                            contexto['tendencia_veto_sell'] = _res_tend_sniper['veto_sell']
                            contexto['tendencia_motivo'] = _res_tend_sniper['motivo']
                        except Exception as e:
                            logging.error(
                                f"â ï¸ Erro ao avaliar tendÃªncia SMA-50 p/ sniper: {e}")
                            contexto['tendencia_veto_buy'] = False
                            contexto['tendencia_veto_sell'] = False

                # ========== â¡ SNIPER %R CHECK (INICIA OPERAÃÃO PRÃPRIA) ==========
                # O sniper %R Ã© o novo cÃ©rebro: quando o %R cruza a zona extrema
                # (<= -80 BUY / >= -20 SELL) ele INICIA a operaÃ§Ã£o com direÃ§Ã£o
                # prÃ³pria, sobrepondo a IA e pulando os filtros do robÃ´ normal.
                # GestÃ£o de saÃ­da: SL=1.5xATR e TP=3xATR no MT5 + trailing 50%
                # pÃ³s-1R no loop de monitoramento (fiel ao backtest variante A).
                # FIX 11/08: sniper NÃO dispara em modo DEFESA (evita 330 ordens
                # bloqueadas em loop apÃ³s 3 losses seguidos) e a trava de zona
                # (em_zona) sÃ³ reseta quando a posiÃ§Ã£o FECHA â nÃ£o a cada sinal
                # (elimina o spam de "INICIA" a cada 2s com o %R preso no extremo).
                if modo_operacional.modo_atual == "DEFESA":
                    sniper_result = {'ativo': False, 'direcao': 'NADA', 'score': 0,
                                     'detalhes': ['modo_defesa']}
                else:
                    sniper_result = sniper_supermo.verificar(contexto, acao_para_executar)
                if sniper_result['ativo']:
                    SNIPER_SUPERMO_ATIVO = True
                    acao_para_executar = sniper_result['direcao']
                    logging.info(
                        f"â¡ SNIPER %R INICIA {acao_para_executar} â sobrepondo IA, pulando filtros normais")
                else:
                    SNIPER_SUPERMO_ATIVO = False
                    # Modo "sniper apenas": sem sinal %R o robÃ´ espera â a IA
                    # principal nÃ£o executa (evita voltar a sangrar).
                    if SNIPER_APENAS:
                        acao_para_executar = "NADA"

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

                # Usa a entropia jÃÂ¡ calculada no contexto
                entropia_calculada = contexto.get('entropia_book', 0.0)

                modo_anterior = modo_operacional.modo_atual
                modo_operacional.modo_atual = modo_operacional.atualizar_modo(
                    atr, entropia_calculada, volume_tick, bid_qty, ask_qty)
                if modo_anterior != modo_operacional.modo_atual:
                    logging.info(
                        f"Ã°Å¸ââ MudanÃÂ§a de modo: {modo_anterior} -> {modo_operacional.modo_atual}")
                    logging.info(
                        f"Ã°Å¸âÅ  ATR: {atr:.2f} | Entropia: {entropia_calculada:.2f} | Volume: {volume_tick}")
                modo_operacional.volume_anterior = volume_tick

                # Filtro de volume MENOS RESTRITIVO - sÃÂ³ bloqueia em casos extremos
                # (pulado se SNIPER SUPERMO estiver ativo)
                if not SNIPER_SUPERMO_ATIVO and (
                    not volume_crescente(n=2, symbol=SYMBOL) and
                    modo_operacional.modo_atual not in ["EXPLOSAO", "NORMAL"] and
                        volume_tick < 100):  # SÃÂ³ bloqueia se volume muito baixo E nÃÂ£o crescente
                    logging.info(
                        "Ã¢âºâ Volume muito baixo e nÃÂ£o crescente. OperaÃÂ§ÃÂ£o bloqueada.")
                    acao_para_executar = "NAO_AGIU_FILTRO_VOLUME"
                    # Salva experiÃÂªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                    except Exception as e:
                        logging.error(f"Ã¢ÂÅ Erro no treinamento: {e}")
                    time.sleep(10)
                    continue

                cb_ativado, cb_mensagem = verificar_circuit_breakers(contexto)
                if cb_ativado:
                    logging.warning(
                        f"Ã¢âºâ Circuit Breaker ativado: {cb_mensagem}")
                    acao_para_executar = "NAO_AGIU_CB"
                    # Salva experiÃÂªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                    except Exception as e:
                        logging.error(f"Ã¢ÂÅ Erro no treinamento: {e}")
                    time.sleep(60)
                    continue

                dados_validos, erro_dados = verificar_integridade_dados(
                    contexto)
                if not dados_validos:
                    logging.error(f"Ã¢ÂÅ Dados invÃÂ¡lidos: {erro_dados}")
                    acao_para_executar = "NAO_AGIU_DADOS_INVALIDOS"
                    # Salva experiÃÂªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    try:
                        modelo_ia_local = treinar_modelo_inteligente(
                            modelo_ia_local, memoria_experiencias)
                    except Exception as e:
                        logging.error(f"Ã¢ÂÅ Erro no treinamento: {e}")
                    time.sleep(10)
                    continue

                # Aplica bloqueio de lado APÃâS a previsÃÂ£o inicial - SÃâ PARA AÃâ¡Ãâ¢ES DE TRADING
                # (pulado se SNIPER %R ativo: a direÃÂ§ÃÂ£o extrema do %R nÃÂ£o pode ser invertida)
                if acao_para_executar in ["BUY", "SELL"] and not SNIPER_SUPERMO_ATIVO and gerenciador_bloqueio.verificar_bloqueio(acao_para_executar):
                    acao_original_bloqueada = acao_para_executar
                    acao_para_executar = gerenciador_bloqueio.obter_acao_alternativa(
                        acao_original_bloqueada)
                    logging.warning(
                        f"Ã°Å¸ââ Invertendo aÃÂ§ÃÂ£o de {acao_original_bloqueada} para {acao_para_executar} devido a bloqueio de lado.")
                    # Atualiza a decisÃÂ£o no CSV com a aÃÂ§ÃÂ£o corrigida
                    salvar_decisao_csv(acao_para_executar,
                                       confianca_decisao, contexto)

                # Se apÃÂ³s todas as verificaÃÂ§ÃÂµes, a aÃÂ§ÃÂ£o for "NADA" ou alguma forma de "NAO_AGIU"
                if acao_para_executar.startswith("NADA") or acao_para_executar.startswith("NAO_AGIU"):
                    if _log_periodico('nao_agindo', 300):
                        logging.debug(
                            f"NÃÂ£o agindo: {acao_para_executar} (ConfianÃÂ§a: {confianca_decisao:.2f} ou restriÃÂ§ÃÂ£o).")
                    # Salva experiÃÂªncia e treina como no arquivo principal (apenas para NADA da previsÃÂ£o)
                    if acao_para_executar == "NADA":
                        memoria_experiencias.adicionar(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        salvar_experiencia_csv(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        # Treina apenas dentro do horÃÂ¡rio de pregÃÂ£o (evita treino desperdiÃÂ§ado pÃÂ³s-17:30)
                        if agora < dtime(17, 30):
                            try:
                                modelo_ia_local = treinar_modelo_inteligente(
                                    modelo_ia_local, memoria_experiencias)
                            except Exception as e:
                                logging.error(f"Ã¢ÂÅ Erro no treinamento: {e}")
                        time.sleep(2)
                        continue

                # === VERIFICAÃâ¡ÃÆO DE HORÃÂRIO ANTES DE EXECUTAR ORDEM ===
                horario_atual = datetime.now().time()
                horario_limite_ordens = datetime.strptime(
                    HORARIO_LIMITE_ORDENS, "%H:%M").time()
                if horario_atual >= horario_limite_ordens:
                    logging.info(
                        f"Ã°Å¸â¢â¢ {HORARIO_LIMITE_ORDENS} - NÃÂ£o executando novas ordens (prÃÂ³ximo ao encerramento)")
                    # Salva experiÃÂªncia e treina como no arquivo principal
                    memoria_experiencias.adicionar(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    salvar_experiencia_csv(
                        contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                    # Treina apenas dentro do horÃÂ¡rio de pregÃÂ£o (evita treino desperdiÃÂ§ado pÃÂ³s-17:30)
                    if agora < dtime(17, 30):
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(f"Ã¢ÂÅ Erro no treinamento: {e}")
                            time.sleep(10)
                    continue

                # ========== INTEGRAÃâ¡ÃÆO MELHORIA 3: MODOS DE MERCADO SIMPLIFICADOS ==========
                if detector_modo:
                    atr = contexto.get('volatility', 0)
                    entropia = contexto.get('entropia_book', 0.5)
                    detector_modo.atualizar_indicadores(atr, entropia)
                    modo_mercado = detector_modo.detectar_modo()

                    if modo_mercado == "CONSERVADOR":
                        logging.info(
                            f"Ã°Å¸ÂÅ Modo CONSERVADOR detectado (ATR: {atr:.1f}, Entropia: {entropia:.3f})")

                # ========== INTEGRAÃâ¡ÃÆO NOVAS MELHORIAS 7 E 9 ==========
                # Atualiza filtro de spread dinÃÂ¢mico com ATR
                if filtro_spread and SPREAD_DINAMICO_ATIVO:
                    atr_atual = contexto.get('volatility', 0)
                    filtro_spread.atualizar_atr(atr_atual)

                # ========== INTEGRAÃâ¡ÃÆO MELHORIA 4: CIRCUIT BREAKERS ESSENCIAIS ==========
                if circuit_breaker and CIRCUIT_BREAKER_ATIVO:
                    spread_atual = contexto.get('spread', 0)
                    _cb2_ignore = (ESTADO_SISTEMA == "SETE_VELAS_EXCLUSIVO"
                                   and bool(SETE_VELAS_CFG.get("cb2_ignore_max_loss", True)))
                    if circuit_breaker.verificar_circuit_breakers(spread_atual, ignore_max_loss=_cb2_ignore):
                        status = circuit_breaker.get_status()
                        logging.warning(
                            f"Ã°Å¸Å¡Â¨ CIRCUIT BREAKER ATIVADO: {status['motivo']}")
                        logging.info(
                            "Ã¢ÂÂ¸Ã¯Â¸Â OperaÃÂ§ÃÂ£o bloqueada por circuit breaker. Aguardando...")
                        # Salva experiÃÂªncia e treina como no arquivo principal
                        memoria_experiencias.adicionar(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        salvar_experiencia_csv(
                            contexto.copy(), "NAO_AGIU", 0.0, 0.0)
                        try:
                            modelo_ia_local = treinar_modelo_inteligente(
                                modelo_ia_local, memoria_experiencias)
                        except Exception as e:
                            logging.error(f"Ã¢ÂÅ Erro no treinamento: {e}")
                        # Aguarda 30 segundos antes de tentar novamente
                        time.sleep(30)
                        continue

                # ========== Ã°Å¸Ââ¹ DIRETRIZ: SEGUIR OS BIG PLAYERS ==========
                # A IA decide, mas NUNCA operamos CONTRA o lado dominante do book.
                # Se os bigs estÃÂ£o comprando (BID > ASK) nÃÂ£o vendemos; se estÃÂ£o
                # vendendo (ASK > BID) nÃÂ£o compramos. "NÃÂ£o brigar com a fita."
                # (O Sniper jÃÂ¡ garante que o lado dominante tem >= 2x Ã¢â¬â desequilÃÂ­brio real.)
                # (Pulado se SNIPER SUPERMO estiver ativo Ã¢â¬â jÃÂ¡ verificou alinhamento total)
                if not SNIPER_SUPERMO_ATIVO and acao_para_executar in ["BUY", "SELL"]:
                    _bid_dom = float(contexto.get('bid_qty', 0))
                    _ask_dom = float(contexto.get('ask_qty', 0))
                    lado_dominante = "BUY" if _bid_dom > _ask_dom else (
                        "SELL" if _ask_dom > _bid_dom else None)
                    if lado_dominante and acao_para_executar != lado_dominante:
                        # Log do veto com THROTTLE (1x a cada VETO_LOG_INTERVALO_S) para
                        # nÃÂ£o inundar o arquivo quando o desequilÃÂ­brio contra persiste.
                        if time.time() - _veto_estado['ultimo_log'] >= VETO_LOG_INTERVALO_S:
                            logging.info(
                                f"Ã°Å¸Ââ¹ VETO SEGUIR OS BIGS: decisÃÂ£o {acao_para_executar} ÃÂ© CONTRA o lado dominante "
                                f"({lado_dominante} | BID {_bid_dom:.0f} x ASK {_ask_dom:.0f}) Ã¢â¬â nÃÂ£o brigo com a fita.")
                            _veto_estado['ultimo_log'] = time.time()
                        # NÃÆO grava experiÃÂªncia aqui (gravava a cada 1s = flood de NAO_AGIU
                        # na memÃÂ³ria e no disco). O veto ÃÂ© uma REGRA fixa, nÃÂ£o aprendizado.
                        time.sleep(5)  # re-checa a cada 5s (nÃÂ£o precisa 1s p/ nÃÂ£o brigar)
                        continue

                # ========== PISO DE CONFIANÃâ¡A MÃÂNIMA (AÃâ¡ÃÆO 2 Ã¢â¬â ROADMAP 07/08) ==========
                # DecisÃÂµes BUY/SELL com confianÃÂ§a < 0.50 nÃÂ£o executam. PolÃÂ­tica fixa
                # (nÃÂ£o grava experiÃÂªncia, mesmo padrÃÂ£o do veto de bigs). A decisÃÂ£o
                # jÃÂ¡ foi salva no CSV (salvar_decisao_csv acima) para mÃÂ©tricas contÃÂ­nuas.
                # (Pulado se SNIPER %R ativo â o sniper tem regra prÃ³pria de entrada)
                if not SNIPER_SUPERMO_ATIVO and acao_para_executar in ["BUY", "SELL"] and confianca_decisao < PISO_CONFIANCA_MINIMA:
                    if _log_periodico('piso_confianca', 300):
                        logging.info(
                            f"Ã°Å¸Å¡Â« PISO DE CONFIANÃâ¡A: {acao_para_executar} bloqueado "
                            f"(confianÃÂ§a {confianca_decisao:.2f} < {PISO_CONFIANCA_MINIMA:.2f})")
                    time.sleep(5)
                    continue

                # Executa ordem com a aÃÂ§ÃÂ£o final decidida
                # Se SNIPER %R ativo, usa volume prÃ³prio e SL/TP por ATR (1.5x/3x)
                _volume_exec = SNIPER_SUPERMO_VOLUME if SNIPER_SUPERMO_ATIVO else VOLUME_PADRAO
                _sl_override = sniper_result.get('sl_points') if SNIPER_SUPERMO_ATIVO else None
                _tp_override = sniper_result.get('tp_points') if SNIPER_SUPERMO_ATIVO else None
                ticket = executar_ordem(
                    acao_para_executar, lots=_volume_exec, modo_operacional=modo_operacional,
                    sniper=SNIPER_SUPERMO_ATIVO,
                    sl_points_override=_sl_override, tp_points_override=_tp_override)
                if SNIPER_SUPERMO_ATIVO:
                    logging.info(f"â¡ SNIPER %R: ordem enviada com {_volume_exec}cc, SL/TP por ATR")
                    sniper_supermo.ativar_cooldown()
                if not ticket:
                    logging.warning(
                        "Ã¢ÂÅ Ordem nÃÂ£o enviada (executar_ordem falhou). Loop reiniciado.")
                    time.sleep(2)
                    continue

                # ... (restante da lÃÂ³gica de confirmaÃÂ§ÃÂ£o da ordem e criaÃÂ§ÃÂ£o de PosicaoAtiva) ...
                # O bloco de salvar experiÃÂªncia e treinar modelo APÃâS FECHAMENTO DE ORDEM jÃÂ¡ estÃÂ¡ lÃÂ¡.
                # Apenas precisamos garantir que o contexto usado para PosicaoAtiva e para memÃÂ³ria seja o `contexto` correto da decisÃÂ£o.

                ticket_ordem_atual = ticket
                esperando_confirmacao = True
                confirmado = False
                for _ in range(20):  # Tenta por 10 segundos
                    time.sleep(0.5)
                    if verificar_se_ordem_virou_posicao(ticket, SYMBOL):
                        logging.info(f"Ã¢Åâ¦ Ordem {ticket} virou posiÃÂ§ÃÂ£o.")
                        posicao_aberta = True
                        confirmado = True
                        break

                esperando_confirmacao = False

                if not confirmado:
                    logging.warning(
                        f"Ã¢ÂÅ Ordem {ticket} nÃÂ£o virou posiÃÂ§ÃÂ£o. Abortando tentativa.")
                    ticket_ordem_atual = None
                    # NÃÆO salvamos experiÃÂªncia aqui porque a ordem nÃÂ£o foi efetivada
                    time.sleep(3)
                    continue

                # ApÃÂ³s confirmaÃÂ§ÃÂ£o da ordem que virou posiÃÂ§ÃÂ£o
                ordem_confirmada_info = mt5.history_orders_get(ticket=ticket)
                if not ordem_confirmada_info:
                    logging.error(
                        f"Ã¢ÂÅ NÃÂ£o foi possÃÂ­vel obter detalhes da ordem {ticket} do histÃÂ³rico para criar PosicaoAtiva.")
                    continue
                ordem_obj = ordem_confirmada_info[0]

                preco_de_execucao_real = ordem_obj.price_open  # Fallback
                # Busca deals desde a criaÃÂ§ÃÂ£o da ordem
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
                    tipo=acao_para_executar,  # Usar a aÃÂ§ÃÂ£o efetivamente executada
                    preco_entrada=preco_de_execucao_real,
                    sl=ordem_obj.sl,
                    tp=ordem_obj.tp,
                    score_inicial=score_inicial,
                    entry_context=contexto.copy()  # Salva o contexto que levou ÃÂ  decisÃÂ£o
                )
                if SNIPER_SUPERMO_ATIVO:
                    posicao_atual.entry_context['sniper_wr'] = 1
                    posicao_atual.entry_context['sniper_sl_points'] = _sl_override
                    posicao_atual.entry_context['sniper_tp_points'] = _tp_override
                    logging.info(
                        f"â¡ PosiÃ§Ã£o SNIPER %R registrada: SL={_sl_override:.1f}pt TP={_tp_override:.1f}pt")

                # ATIVA O GERENCIADOR DE SAÃÂDA (PASSO 2)
                posicao_obj_mt5 = mt5.positions_get(ticket=ticket)[0]
                gerenciador_saida.iniciar_monitoramento(posicao_obj_mt5)

                logging.debug(
                    f"[DEBUG] posicao_atual apÃÂ³s instanciaÃÂ§ÃÂ£o: {posicao_atual} (type: {type(posicao_atual)})"
                )
                logging.info(
                    f"Ã°Å¸âÅ  Nova posiÃÂ§ÃÂ£o iniciada: Ticket={posicao_atual.ticket}, "
                    f"Tipo={posicao_atual.tipo}, "
                    f"Entrada={posicao_atual.preco_entrada:.3f}, "
                    f"SL={posicao_atual.sl:.3f}, "
                    f"TP={posicao_atual.tp:.3f}, "
                    f"Score Inicial={posicao_atual.score_inicial:.2f}"
                )
                # NÃÆO calcular lucro/experiÃÂªncia aqui. Isso ÃÂ© feito quando a posiÃÂ§ÃÂ£o FECHA.
                time.sleep(2)  # Pequena pausa apÃÂ³s abrir posiÃÂ§ÃÂ£o

            except Exception as e:
                logging.error(f"Ã¢ÂÅ Erro GRAVE no loop principal: {e}")
                logging.error(traceback.format_exc())
                time.sleep(2)  # Aguarda um pouco antes de continuar

        return mt5_ativo_local, modelo_ia_local
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro GRAVE no loop principal: {e}")
        logging.error(traceback.format_exc())
        time.sleep(2)  # Aguarda um pouco antes de continuar

# endregion

# region [Circuit Breakers]


def verificar_circuit_breakers(contexto: Dict[str, Any]) -> Tuple[bool, str]:
    """Verifica condiÃÂ§ÃÂµes de circuit breaker."""
    agora = datetime.now().time()
    inicio = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    fim = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    # Verifica horÃÂ¡rio de operaÃÂ§ÃÂ£o
    if not (inicio <= agora <= fim):
        return True, "Fora do horÃÂ¡rio de operaÃÂ§ÃÂ£o"

    # Verifica spread
    if contexto.get('spread', 0) > MAX_SPREAD:
        return True, f"Spread muito alto: {contexto['spread']:.1f} pontos"

    # Verifica volume total no book
    volume_total = contexto.get('bid_qty', 0) + contexto.get('ask_qty', 0)
    if volume_total < MIN_VOLUME_BOOK:
        return True, f"Volume total insuficiente no book: {volume_total}"

    # Verifica volume mÃÂ­nimo em ambos os lados
    if contexto.get('bid_qty', 0) < MIN_TICKS_VALIDOS:
        return True, f"Volume bid insuficiente: {contexto.get('bid_qty', 0)}"
    if contexto.get('ask_qty', 0) < MIN_TICKS_VALIDOS:
        return True, f"Volume ask insuficiente: {contexto.get('ask_qty', 0)}"

    # Verifica drawdown diÃÂ¡rio
    lucro_dia = sum(historico_lucro[-100:])  # ÃÅ¡ltimas 100 operaÃÂ§ÃÂµes
    if lucro_dia < MAX_LOSS_DIARIO:
        return True, f"Stop loss diÃÂ¡rio atingido: {lucro_dia:.2f}"

    return False, ""


def verificar_integridade_dados(dados: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica a integridade dos dados recebidos.
    Retorna (True, mensagem) se os dados sÃÂ£o vÃÂ¡lidos.
    """
    # Verifica valores nulos
    if None in dados.values():
        return False, "Dados contÃÂªm valores nulos"

    # Verifica valores negativos onde nÃÂ£o deveria
    if dados.get('bid_qty', 0) < 0 or dados.get('ask_qty', 0) < 0:
        return False, "Quantidades negativas no book"

    # Verifica valores absurdos
    if dados.get('spread', 0) > 1000:  # Spread absurdamente alto
        return False, "Spread anormal"

    # Verifica consistÃÂªncia do RSI
    rsi = dados.get('rsi_14', 0)
    if not (0 <= rsi <= 100):
        return False, "RSI fora do intervalo vÃÂ¡lido"

    return True, ""

# endregion

# region [Filtros Evolutivos Removidos]
# Classe FiltrosEvolutivos removida para evitar conflitos
# endregion

# region [Aprendizado]


class MemoriaExperiencias:
    """Gerencia a memÃÂ³ria de experiÃÂªncias do modelo."""

    def __init__(self, max_size: int = MAX_EXPERIENCIAS_MEMORIA):
        self.max_size = max_size
        self.experiencias = []
        self.indices_positivos = []
        self.indices_negativos = []
        self.timestamps = []
        self.ultimo_replay = datetime.now()
        self.historico_decisoes = []  # Para mÃÂ©trica de consistÃÂªncia
        self.score_consistencia = 0.0
        self.contagem_acoes = {"BUY": 0, "SELL": 0,
                               "NADA": 0, "NAO_AGIU": 0}  # Novo contador
        self.razao_buy_sell = 0.5  # Neutro atÃÂ© ter operaÃÂ§ÃÂµes reais (era 1.0 = forÃÂ§ava SELL)

        # CORREÃâ¡ÃÆO CRÃÂTICA: Carrega experiÃÂªncias na inicializaÃÂ§ÃÂ£o
        self.carregar_experiencias_do_csv()

    def adicionar(self, contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
        """Adiciona uma nova experiÃÂªncia ÃÂ  memÃÂ³ria."""
        self._adicionar_direto(contexto, acao, lucro, score_dist)

        # MantÃÂ©m apenas ÃÂºltimas N decisÃÂµes para consistÃÂªncia
        if len(self.historico_decisoes) > JANELA_CONSISTENCIA:
            self.historico_decisoes.pop(0)

        # Atualiza score de consistÃÂªncia
        self.atualizar_consistencia()

    def get_balanceamento_status(self) -> Dict[str, Any]:
        """Retorna estatÃÂ­sticas de balanceamento das operaÃÂ§ÃÂµes."""
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
            timestamp: Momento em que a experiÃÂªncia foi registrada

        Returns:
            float: Valor entre 0 e 1, onde 1 significa experiÃÂªncia recente e
                  valores prÃÂ³ximos de 0 significam experiÃÂªncias antigas
        """
        tempo_passado = (datetime.now() - timestamp).total_seconds()
        # Usa DECAY_MEIA_VIDA (em horas) para calcular o decay
        decay = math.exp(-tempo_passado / (DECAY_MEIA_VIDA * 3600))
        return max(0.1, min(1.0, decay))  # Limita entre 0.1 e 1.0

    def atualizar_consistencia(self) -> None:
        """Calcula score de consistÃÂªncia baseado nas ÃÂºltimas decisÃÂµes."""
        if len(self.historico_decisoes) < 2:
            self.score_consistencia = 0.5
            return

        # Calcula sequÃÂªncias de acertos e erros
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
        # 1. Tamanho mÃÂ©dio das sequÃÂªncias (maior = mais consistente)
        # 2. ProporÃÂ§ÃÂ£o de acertos
        # 3. PenalizaÃÂ§ÃÂ£o por alternÃÂ¢ncia frequente
        media_seq = sum(sequencias) / len(sequencias) if sequencias else 1
        prop_acertos = sum(self.historico_decisoes) / \
            len(self.historico_decisoes)
        alternancia = len(sequencias) / len(self.historico_decisoes)

        self.score_consistencia = (
            0.4 * (media_seq / JANELA_CONSISTENCIA) +  # Peso das sequÃÂªncias
            0.4 * prop_acertos +                       # Peso dos acertos
            # PenalizaÃÂ§ÃÂ£o por alternÃÂ¢ncia
            0.2 * (1 - alternancia)
        )

    def verificar_replay(self) -> bool:
        """Verifica se ÃÂ© hora de fazer replay das experiÃÂªncias."""
        tempo_desde_replay = (
            datetime.now() - self.ultimo_replay).total_seconds() / 60
        return tempo_desde_replay >= INTERVALO_REPLAY

    def obter_batch_replay(self) -> Tuple[List[Tuple[Dict[str, Any], str, float, float]], List[float]]:
        """ObtÃÂ©m batch para replay Ã¢â¬â inclui TODAS as experiÃÂªncias reais para aprendizado completo."""
        self.ultimo_replay = datetime.now()

        # Ã¢Åâ¦ CORREÃâ¡ÃÆO: Inclui TODAS as experiÃÂªncias reais (BUY/SELL), nÃÂ£o apenas positivas
        # A IA precisa aprender tanto com acertos quanto com erros
        # Prioriza positivas mas inclui negativas com peso menor
        exp_reais = [(i, exp) for i, exp in enumerate(self.experiencias)
                     # Filtra apenas operaÃÂ§ÃÂµes reais
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
        """Verifica se hÃÂ¡ experiÃÂªncias suficientes para treino."""
        return len(self.experiencias) >= MIN_EXPERIENCIAS_TREINO

    def carregar_experiencias_do_csv(self) -> None:
        """CORREÃâ¡ÃÆO CRÃÂTICA: Carrega experiÃÂªncias do arquivo CSV na inicializaÃÂ§ÃÂ£o."""
        try:
            if not os.path.exists(HISTORICO_CSV):
                logging.info(
                    f"Ã°Å¸âÅ¡ Arquivo {HISTORICO_CSV} nÃÂ£o existe. Iniciando com memÃÂ³ria vazia.")
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
                f"Ã°Å¸âÅ¡ CARREGAMENTO EQUILIBRADO: {max_wins} WINS + {max_losses} LOSSES (de {len(wins)}W/{len(losses)}L)")

            # Carrega NAO_AGIU proporcionalmente
            max_nao_agiu = min(200, len(experiencias_nao_agiu))
            nao_agiu_recentes = experiencias_nao_agiu.tail(max_nao_agiu)

            # Combina: wins + losses + nao_agiu
            experiencias_recentes = pd.concat(
                [wins_recentes, losses_recentes, nao_agiu_recentes], ignore_index=True)

            logging.info(
                f"Ã°Å¸âÅ¡ Ã¢Åâ¦ TOTAL: {len(wins_recentes)} WINS + {len(losses_recentes)} LOSSES + {len(nao_agiu_recentes)} NAO_AGIU")

            if len(experiencias_recentes) == 0:
                logging.info("Ã°Å¸âÅ¡ Nenhuma experiÃÂªncia encontrada no CSV.")
                return

            carregadas = 0
            for _, row in experiencias_recentes.iterrows():
                try:
                    # ReconstrÃÂ³i o contexto com TODAS as 22 features
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

                    acao = str(row['action'])  # CSV usa 'action', nÃÂ£o 'acao'
                    lucro = float(row['reward'])
                    # Para NAO_AGIU, usa score neutro; para BUY/SELL usa reward
                    if acao == 'NAO_AGIU':
                        score_dist = 0.1  # Score neutro positivo para nÃÂ£o agir quando correto
                    else:
                        score_dist = float(row.get('reward', 0))

                    # Adiciona ÃÂ  memÃÂ³ria (sem chamar carregar_experiencias_do_csv novamente)
                    self._adicionar_direto(contexto, acao, lucro, score_dist)
                    carregadas += 1

                except Exception as e:
                    logging.debug(f"Erro ao carregar experiÃÂªncia: {e}")
                    continue

            logging.info(
                f"Ã°Å¸âÅ¡ Ã¢Åâ¦ CORREÃâ¡ÃÆO APLICADA: {carregadas} experiÃÂªncias carregadas do CSV!")
            logging.info(
                f"Ã°Å¸âÅ  ExperiÃÂªncias positivas: {len(self.indices_positivos)}")
            logging.info(
                f"Ã°Å¸âÅ  ExperiÃÂªncias negativas: {len(self.indices_negativos)}")

            # CORREÃâ¡ÃÆO CRÃÂTICA: Ajusta contador global para evitar perda de progresso
            global contador_experiencias_novas
            experiencias_reais_carregadas = len(
                [exp for exp in self.experiencias if exp[1] in ['BUY', 'SELL']])
            contador_experiencias_novas = experiencias_reais_carregadas % LIMITE_EXPERIENCIAS_PARA_TREINO
            logging.info(
                f"Ã°Å¸ââ CONTADOR AJUSTADO: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO} (baseado em {experiencias_reais_carregadas} operaÃÂ§ÃÂµes reais)")

            # Log da razÃÂ£o BUY/SELL apÃÂ³s carregamento completo
            total_ops = self.contagem_acoes.get(
                "BUY", 0) + self.contagem_acoes.get("SELL", 0)
            if total_ops > 0:
                logging.info(
                    f"Ã°Å¸âÅ  RazÃÂ£o BUY/SELL final: {self.razao_buy_sell:.3f} ({self.contagem_acoes.get('BUY', 0)}/{total_ops})")

        except Exception as e:
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â CSV histÃÂ³rico com formato antigo ('{e}') Ã¢â¬â serÃÂ¡ corrigido automaticamente na inicializaÃÂ§ÃÂ£o")

    def _adicionar_direto(self, contexto: Dict[str, Any], acao: str, lucro: float, score_dist: float) -> None:
        """Adiciona experiÃÂªncia diretamente sem chamar carregar_experiencias_do_csv."""
        if len(self.experiencias) >= self.max_size:
            self.experiencias.pop(0)
            self.timestamps.pop(0)
            self.indices_positivos = [
                i-1 for i in self.indices_positivos if i > 0]
            self.indices_negativos = [
                i-1 for i in self.indices_negativos if i > 0]

        # Adiciona nova experiÃÂªncia
        experiencia = (contexto, acao, lucro, score_dist)
        self.experiencias.append(experiencia)
        self.timestamps.append(datetime.now())
        idx = len(self.experiencias) - 1

        # CORREÃâ¡ÃÆO: Considera score_dist para NAO_AGIU e lucro para operaÃÂ§ÃÂµes reais
        if acao == 'NAO_AGIU':
            # NAO_AGIU com score positivo = decisÃÂ£o correta de nÃÂ£o operar
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
        # Atualiza contagem de aÃÂ§ÃÂµes
        if acao in self.contagem_acoes:
            self.contagem_acoes[acao] += 1
        else:
            # Adiciona nova aÃÂ§ÃÂ£o se nÃÂ£o existir
            self.contagem_acoes[acao] = 1

        # CORREÃâ¡ÃÆO CRÃÂTICA: Atualiza razao_buy_sell (SEM LOG para evitar spam)
        total_operacoes = self.contagem_acoes["BUY"] + \
            self.contagem_acoes["SELL"]
        if total_operacoes > 0:
            self.razao_buy_sell = self.contagem_acoes["BUY"] / total_operacoes


def normalizar_recompensas(recompensas: List[float], scores_distancia: List[float], decays: List[float]) -> List[float]:
    """Normaliza recompensas preservando sinal: losses = negativo, wins = positivo.

    Usa divisÃÂ£o por 100 (apÃÂ³s clipping) para mapear [-100,+100] Ã¢â â [-1,+1].
    Losses recebem puniÃÂ§ÃÂ£o (negativo), wins recebem bÃÂ´nus (positivo).
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
    """Verifica se deve treinar o modelo baseado no contador de experiÃÂªncias."""
    global contador_experiencias_novas, MODO_APRENDIZADO_FORCADO

    # APRENDIZADO ACELERADO: Treina mais frequentemente quando em modo forÃÂ§ado
    if MODO_APRENDIZADO_FORCADO and contador_experiencias_novas >= 3:
        logging.info(
            "Ã°Å¸Å¡â¬ APRENDIZADO ACELERADO: Treinando com apenas 3 experiÃÂªncias")
        return True

    # MODO TESTE DESATIVADO Ã¢â¬â causava loop de spam a cada 2s (colunas faltantes no CSV)
    # if ciclos_sem_operacao % 10 == 0 and contador_experiencias_novas == 0:
    #     logging.info("Ã°Å¸Â§Âª MODO TESTE: ForÃÂ§ando treinamento mesmo sem operaÃÂ§ÃÂµes novas")
    #     return True

    return contador_experiencias_novas >= LIMITE_EXPERIENCIAS_PARA_TREINO


def treinar_modelo_inteligente(modelo: Sequential, memoria: MemoriaExperiencias) -> Sequential:
    """Treina o modelo apenas quando necessÃÂ¡rio."""
    global contador_experiencias_novas

    if not deve_treinar_modelo():
        logging.debug(
            f"Ã°Å¸Â§Â  Treinamento adiado. ExperiÃÂªncias: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO}")
        return modelo

    # Reset contador
    contador_experiencias_novas = 0
    logging.info(
        f"Ã°Å¸Â§Â  Iniciando treinamento apÃÂ³s {LIMITE_EXPERIENCIAS_PARA_TREINO} experiÃÂªncias novas")

    return treinar_modelo(modelo, memoria)


def _modelo_tem_l2(modelo):
    """Verifica se o modelo jÃÂ¡ tem regularizaÃÂ§ÃÂ£o L2 nas camadas Dense."""
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
    logging.info("Ã¢Åâ¦ Modelo migrado para arquitetura com L2 regularization.")
    return modelo_novo


def treinar_modelo(modelo: Sequential, memoria: MemoriaExperiencias) -> Sequential:
    """
    Treina o modelo com: L2 regularization, TimeSeriesSplit, SMOTE,
    early stopping e batch balanceado.
    """
    global historico_loss
    logging.info(
        f"[treinar_modelo] Iniciando treino. Tenho {len(memoria.experiencias)} experiÃÂªncias.")

    if not memoria.tem_suficiente():
        logging.info(
            "[treinar_modelo] Aguardando mais experiÃÂªncias para treino.")
        return modelo

    try:
        # 0. Migrar para L2 se necessÃÂ¡rio (garante que modelo tenha regularizaÃÂ§ÃÂ£o)
        if not _modelo_tem_l2(modelo):
            modelo = _migrar_modelo_l2(modelo, N_FEATURES)

        # 1. Obter o batch de experiÃÂªncias
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

        # Remove NaN/inf e alinha recompensas com dados vÃÂ¡lidos
        if X is not None and y is not None and len(X) > 0:
            mask_valid = np.isfinite(X.values if hasattr(X, 'values') else X).all(axis=1)
            X = X[mask_valid].reset_index(drop=True)
            y = y[mask_valid].reset_index(drop=True)
            recompensas = [recompensas[i] for i in range(len(recompensas)) if i < len(mask_valid) and mask_valid[i]]

        if X is None or y is None or len(X) < 4:
            logging.warning(
                f"[treinar_modelo] Dados insuficientes: {len(X) if X is not None else 0} amostras vÃÂ¡lidas (mÃÂ­nimo 4).")
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

        # 3. TIMESERIES SPLIT (sem shuffle) Ã¢â¬â ÃÂºltimos 20% viram validaÃÂ§ÃÂ£o
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
            logging.info(f"Ã¢Åâ¦ SMOTE aplicado. Treino final: {len(X_train)} amostras.")
        except Exception as e:
            logging.debug(f"SMOTE nÃÂ£o disponÃÂ­vel: {e}")

        # 5. SALVAR PESOS DO MODELO ATUAL ANTES DE TREINAR
        modelo_temp_path = MODELO_PATH + ".temp_treino"
        try:
            modelo.save(modelo_temp_path)
        except Exception:
            modelo_temp_path = None

        loss_antiga, acc_antiga = modelo.evaluate(X_val, y_val, verbose=0)
        logging.info(
            f"Performance do Modelo ANTIGO na validaÃÂ§ÃÂ£o: Loss={loss_antiga:.4f}, AcurÃÂ¡cia={acc_antiga:.4f}")

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
            shuffle=False  # Temporal: NÃÆO embaralhar
        )

        # 7. COMPARAR E DECIDIR SE SALVA
        loss_nova, acc_nova = modelo.evaluate(X_val, y_val, verbose=0)
        logging.info(
            f"Performance do Modelo NOVO na validaÃÂ§ÃÂ£o: Loss={loss_nova:.4f}, AcurÃÂ¡cia={acc_nova:.4f}")

        melhoria_minima = loss_antiga * 0.01
        if loss_nova < (loss_antiga - melhoria_minima):
            logging.info(
                f"Ã¢Åâ¦ MELHORIA REAL: Loss {loss_antiga:.4f} Ã¢â â {loss_nova:.4f}. Salvando.")
            salvar_modelo(modelo)
            historico_loss.extend(history.history['val_loss'])
            if modelo_temp_path and os.path.exists(modelo_temp_path):
                try:
                    os.remove(modelo_temp_path)
                except Exception:
                    pass
        else:
            logging.warning(
                f"Ã¢ÂÅ SEM MELHORIA ({loss_antiga:.4f} Ã¢â â {loss_nova:.4f}). Restaurando anterior.")
            if modelo_temp_path and os.path.exists(modelo_temp_path):
                try:
                    modelo = carregar_modelo(modelo_temp_path)
                    os.remove(modelo_temp_path)
                except Exception as e:
                    logging.error(f"Ã¢ÂÅ Erro ao restaurar: {e}")
                    modelo = carregar_modelo(MODELO_PATH)

        salvar_experiencias_json(memoria.experiencias)
        final_loss = history.history['loss'][-1]
        epochs_trained = len(history.history['loss'])
        logging.info(
            f"Ã°Å¸Â§Â  Modelo treinado por {epochs_trained} ÃÂ©pocas. Loss final: {final_loss:.4f}")

    except Exception as e:
        logging.error(f"[treinar_modelo] Erro durante o fit(): {e}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        return modelo

    # Restaura scaler global do JSON apÃÂ³s treino (evita corromper escala)
    forcar_recreacao_scaler()

    return modelo


def filtros_alta_acertividade(contexto_completo: Dict) -> Tuple[bool, str]:
    """
    Ã°Å¸Å½Â¯ FILTROS DE MÃÂXIMA ACERTIVIDADE - SÃâ OPERA EM SETUPS PREMIUM
    Reduz operaÃÂ§ÃÂµes mas aumenta drasticamente a taxa de acerto
    """
    if not contexto_completo:
        return False, "Contexto nÃÂ£o fornecido"

    # FILTRO 1: Volume ALTO (big players) - AJUSTADO PARA WDO
    volume_total = contexto_completo.get(
        'bid_qty', 0) + contexto_completo.get('ask_qty', 0)
    if volume_total < MIN_VOLUME_BOOK:  # 400cc mÃÂ­nimo (era 800)
        return False, f"Volume insuficiente: {volume_total} < {MIN_VOLUME_BOOK}"

    # FILTRO 2: Entropia Ã¢â¬â desequilÃÂ­brio do book
    # FIX (01/08/2026): escala real 2.69-2.97, era 0.2 em [0,1] -> nunca bloqueava
    entropia = contexto_completo.get('entropia_book', 0)
    if entropia < 2.60:
        return False, f"Book equilibrado demais: entropia {entropia:.3f} < 2.60"

    # FILTRO 3: ATR MÃÂNIMO (volatilidade real)
    # WDO: ATR tÃÂ­pico 2-10 pontos (tick=0.5). Abaixo de 1.5 = lateral total.
    atr = contexto_completo.get('volatility', 0)  # ATR estÃÂ¡ como 'volatility'
    if atr < 1.5:
        return False, f"Mercado lateral demais: ATR {atr:.1f} < 1.5"

    # FILTRO 4: RSI confirmando direÃÂ§ÃÂ£o (FLEXIBILIZADO PARA APRENDIZADO)
    rsi = contexto_completo.get('rsi_14', 50)
    # REMOVIDO: Filtro RSI neutro estava impedindo 80% das operaÃÂ§ÃÂµes
    # if 35 <= rsi <= 65:  # RSI neutro - evita
    #     return False, f"RSI neutro: {rsi:.1f} (evitando zona 35-65)"

    # FILTRO 5: Spread controlado
    spread = contexto_completo.get('spread', 0)
    if spread > 10:  # Spread muito alto
        return False, f"Spread muito alto: {spread:.1f} > 10"

    # FILTRO 6: Score de qualidade do setup
    score_qualidade = 0

    # PontuaÃÂ§ÃÂ£o por volume (peso 3)
    if volume_total >= 1500:
        score_qualidade += 3
    elif volume_total >= 1200:
        score_qualidade += 2
    elif volume_total >= 800:
        score_qualidade += 1

    # PontuaÃÂ§ÃÂ£o por entropia (peso 3) - escala real (2.69-2.97), era 0.7/0.6/0.5
    if entropia >= 2.85:
        score_qualidade += 3
    elif entropia >= 2.80:
        score_qualidade += 2
    elif entropia >= 2.75:
        score_qualidade += 1

    # PontuaÃÂ§ÃÂ£o por ATR (peso 3) Ã¢â¬â WDO: ATR tÃÂ­pico 2-10 pontos
    if atr >= 8:
        score_qualidade += 3
    elif atr >= 5:
        score_qualidade += 2
    elif atr >= 3:
        score_qualidade += 1

    # PontuaÃÂ§ÃÂ£o por RSI extremo (peso 2)
    if rsi <= 25 or rsi >= 75:
        score_qualidade += 2
    elif rsi <= 30 or rsi >= 70:
        score_qualidade += 1

    # SISTEMA DE APRENDIZADO FORÃâ¡ADO - Permite operaÃÂ§ÃÂµes para gerar experiÃÂªncias
    global CONTADOR_OPERACOES_REJEITADAS, MODO_APRENDIZADO_FORCADO
    global FORCADOS_HOJE, FORCADOS_DATA

    if score_qualidade < 2:
        CONTADOR_OPERACOES_REJEITADAS += 1

        if CONTADOR_OPERACOES_REJEITADAS >= LIMITE_REJEICOES_PARA_APRENDIZADO:
            # Ã¢Åâ¦ PA1: MESMO NO MODO FORÃâ¡ADO, RESPEITA HORÃÂRIO
            if not horario_permitido():
                horario_atual = datetime.now().strftime("%H:%M")
                logging.warning(
                    f"Ã°Å¸Å¡Â« PA1 APRENDIZADO FORÃâ¡ADO BLOQUEADO POR HORÃÂRIO: {horario_atual}")
                return False, f"Aprendizado forÃÂ§ado bloqueado por horÃÂ¡rio: {horario_atual}"

            # LIMITE DIÃÂRIO: mÃÂ¡ximo 3 operaÃÂ§ÃÂµes forÃÂ§adas por dia
            hoje = datetime.now().date()
            if FORCADOS_DATA != hoje:
                FORCADOS_HOJE = 0
                FORCADOS_DATA = hoje

            if FORCADOS_HOJE >= MAX_FORCADOS_DIA:
                logging.warning(
                    f"Ã°Å¸Å¡Â« LIMITE DIÃÂRIO DE FORÃâ¡ADOS ATINGIDO: {FORCADOS_HOJE}/{MAX_FORCADOS_DIA}. Bloqueando.")
                CONTADOR_OPERACOES_REJEITADAS = 0
                return False, f"Limite diÃÂ¡rio de aprendizado forÃÂ§ado atingido ({MAX_FORCADOS_DIA}/dia)"

            CONTADOR_OPERACOES_REJEITADAS = 0
            FORCADOS_HOJE += 1
            MODO_APRENDIZADO_FORCADO = True
            logging.warning(
                f"Ã°Å¸Å½â APRENDIZADO FORÃâ¡ADO {FORCADOS_HOJE}/{MAX_FORCADOS_DIA}: Score {score_qualidade}/11 aceito")
            return True, f"Aprendizado forÃÂ§ado {FORCADOS_HOJE}/{MAX_FORCADOS_DIA} (score {score_qualidade}/11)"

        logging.info(
            f"Ã¢ÂÅ C10: Score {score_qualidade}/11 < 2. OperaÃÂ§ÃÂ£o bloqueada. RejeiÃÂ§ÃÂµes: {CONTADOR_OPERACOES_REJEITADAS}/{LIMITE_REJEICOES_PARA_APRENDIZADO}")
        return False, f"Setup de baixa qualidade: score {score_qualidade}/11 < 2 (RejeiÃÂ§ÃÂµes: {CONTADOR_OPERACOES_REJEITADAS}/{LIMITE_REJEICOES_PARA_APRENDIZADO})"

    # Reset contador quando o setup ÃÂ© bom
    CONTADOR_OPERACOES_REJEITADAS = 0

    # Setup aprovado
    logging.info(
        f"Ã¢Åâ¦ C10: SETUP APROVADO! Score: {score_qualidade}/11 | Vol: {volume_total} | Entropia: {entropia:.3f} | ATR: {atr:.1f} | RSI: {rsi:.1f}")
    return True, f"C10: Setup aprovado (score {score_qualidade}/11)"


def prever_acao(modelo: Sequential, X: pd.DataFrame,
                modo_operacional: Optional[ModoOperacional] = None,
                filtros_evolutivos: Optional[Any] = None,
                contexto_completo: Optional[Dict] = None) -> Tuple[str, float]:
    """PrevÃÂª a prÃÂ³xima aÃÂ§ÃÂ£o com VETO SIMPLES E DIRETO baseado na sugestÃÂ£o da IA."""
    # Inicializa flag de veto (False = sem veto ativo)
    prever_acao._ultimo_veto = False
    try:
        # ========== Ã¢Åâ¦ PRIORIDADE 0: COOLDOWN Ã¢â¬â NADA PASSA ANTES DISSO ==========
        # Regra Sniper: Se cooldown ativo, retorna NADA imediatamente sem ler book ou consultar IA
        if COOLDOWN_ATIVO and cooldown_sistema and not cooldown_sistema.pode_operar():
            tempo_restante = cooldown_sistema.tempo_restante_cooldown()
            logging.info(
                f"Ã°Å¸âºâ [P0] COOLDOWN ATIVO ({tempo_restante}s restantes) Ã¢â¬â Bloqueio total, aguardando...")
            return "NADA", 0.0

        # ========== Ã¢Åâ¦ PA1: TRAVA DE HORÃÂRIO - PRIORIDADE MÃÂXIMA ==========
        if not horario_permitido():
            # Log com throttle (1x a cada 300s) Ã¢â¬â fora do horÃÂ¡rio PA1 isso repetiria
            # a cada ciclo e inundaria o log.
            if _log_periodico('pa1_bloqueado', 300):
                horario_atual = datetime.now().strftime("%H:%M")
                logging.info(
                    f"Ã°Å¸Å¡Â« PA1 HORÃÂRIO BLOQUEADO: {horario_atual} - SÃÂ³ opera 09:15-12:30 e 14:30-17:15")
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
                logging.debug(f"Sentinela de fluxo indisponÃ­vel (fail-open): {_e}")

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
            # WILLIAMS %R: VETO BUY EM SOBREVENDA EXTREMA (continuaÃÂ§ÃÂ£o de queda, nÃÂ£o fundo)
            # THRESHOLD -80: simÃÂ©trico ao veto SELL (WR < -80 = sobrevenda agressiva)
            if pode_buy and wr_val < -80:
                logging.warning(f"WILLIAMS %R VETO BUY (continuaÃÂ§ÃÂ£o): WR={wr_val:.0f} (< -80, sobrevenda agressiva)")
                pode_buy = False

            # MULTI-TF VETO: nÃÂ£o comprar contra 3 timeframes bearish
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

            # Se so uma viavel, forca essa (com proteÃÂ§ÃÂ£o Multi-TF)
            if pode_buy and not pode_sell:
                # NÃÂ£o forÃÂ§ar BUY se Multi-TF mostra bearish (todos < 50)
                if m5_rsi < 50 and m15_rsi < 50 and m30_rsi < 50:
                    logging.warning(f"FORÃâ¡A BUY BLOQUEADO: Multi-TF bearish (M5={m5_rsi:.0f} M15={m15_rsi:.0f} M30={m30_rsi:.0f})")
                    return "NADA", 0.0
                if _sf_veto_buy:
                    logging.warning(f"Ã°Å¸Å¡Â« SENTINELA VETO BUY: {_sf_detalhe}")
                    prever_acao._ultimo_veto = True
                    return "NADA", 0.0
                logging.info(f"FORCA BUY: {motivo_buy}")
                return "BUY", 0.8
            if pode_sell and not pode_buy:
                # NÃÂ£o forÃÂ§ar SELL se Multi-TF mostra bullish (todos > 50)
                if m5_rsi > 50 and m15_rsi > 50 and m30_rsi > 50:
                    logging.warning(f"FORÃâ¡A SELL BLOQUEADO: Multi-TF bullish (M5={m5_rsi:.0f} M15={m15_rsi:.0f} M30={m30_rsi:.0f})")
                    return "NADA", 0.0
                if _sf_veto_sell:
                    logging.warning(f"Ã°Å¸Å¡Â« SENTINELA VETO SELL: {_sf_detalhe}")
                    prever_acao._ultimo_veto = True
                    return "NADA", 0.0
                logging.info(f"FORCA SELL: {motivo_sell}")
                return "SELL", 0.8

# ========== FILTRO DE TENDÃÅ NCIA (SMA-50 + MOMENTUM) ==========
        # Bloqueia operaÃÂ§ÃÂµes contra a tendÃÂªncia para evitar comprar em queda
        # Avalia UMA VEZ (avaliar_tendencia registra preÃÂ§o e calcula tudo)
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
                logging.warning(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA VETO TOTAL: {_tendencia_result['motivo']}")
                return "NADA", 0.0
            if _tendencia_veto_buy:
                logging.info(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA BLOQUEIA BUY: {_tendencia_result['motivo']}")
            if _tendencia_veto_sell:
                logging.info(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA BLOQUEIA SELL: {_tendencia_result['motivo']}")

        # ========== FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR ==========
        if contexto_completo:
            if bloqueador_contexto.contexto_bloqueado(contexto_completo):
                return "NADA", 0.0

        # ========== FASE 2: CONSULTA EXPERIÃÅ NCIAS PASSADAS ==========
        if contexto_completo:
            expectativa_buy = replay_experiencias.calcular_expectativa_contexto(
                contexto_completo, "BUY")
            expectativa_sell = replay_experiencias.calcular_expectativa_contexto(
                contexto_completo, "SELL")

            tem_dados_buy = expectativa_buy['trades_similares'] >= 5
            tem_dados_sell = expectativa_sell['trades_similares'] >= 5

            # VETO MATEMÃÂTICO: SÃÂ³ veta se tiver dados suficientes E expectativa NEGATIVA REAL
            # Sem dados (0.00) = NEUTRO = deixa passar para IA/ConfluÃÂªncia decidirem
            if tem_dados_buy and tem_dados_sell:
                if expectativa_buy['expectativa'] < 0 and expectativa_sell['expectativa'] < 0:
                    logging.warning(
                        f"Ã°Å¸Å¡Â« VETO MATEMÃÂTICO (prova real): BUY={expectativa_buy['expectativa']:.2f} "
                        f"({expectativa_buy['trades_similares']} trades), "
                        f"SELL={expectativa_sell['expectativa']:.2f} "
                        f"({expectativa_sell['trades_similares']} trades)")
                    # HIERARQUIA: Veto negativo - nada mais sobrescreve
                    prever_acao._ultimo_veto = True
                    return "NADA", 0.0

            # Se uma direÃÂ§ÃÂ£o tem dados positivos e a outra nÃÂ£o tem dados ou ÃÂ© negativa
            if tem_dados_buy and expectativa_buy['expectativa'] > 0:
                if not tem_dados_sell or expectativa_sell['expectativa'] <= 0:
                    if _sf_veto_buy:
                        logging.warning(f"Ã°Å¸Å¡Â« SENTINELA VETO BUY: {_sf_detalhe}")
                        prever_acao._ultimo_veto = True
                        return "NADA", 0.0
                    logging.info(
                        f"Ã°Å¸Å½Â¯ FORÃâ¡A BUY por expectativa positiva: {expectativa_buy['expectativa']:.2f} "
                        f"({expectativa_buy['trades_similares']} trades)")
                    prever_acao._ultimo_veto = False
                    return "BUY", min(0.9, expectativa_buy['expectativa'] / 100)

            if tem_dados_sell and expectativa_sell['expectativa'] > 0:
                if not tem_dados_buy or expectativa_buy['expectativa'] <= 0:
                    if _sf_veto_sell:
                        logging.warning(f"Ã°Å¸Å¡Â« SENTINELA VETO SELL: {_sf_detalhe}")
                        prever_acao._ultimo_veto = True
                        return "NADA", 0.0
                    logging.info(
                        f"Ã°Å¸Å½Â¯ FORÃâ¡A SELL por expectativa positiva: {expectativa_sell['expectativa']:.2f} "
                        f"({expectativa_sell['trades_similares']} trades)")
                    prever_acao._ultimo_veto = False
                    return "SELL", min(0.9, expectativa_sell['expectativa'] / 100)

            # Sem dados suficientes em nenhuma direÃÂ§ÃÂ£o: log neutro e deixa passar
            if not tem_dados_buy and not tem_dados_sell:
                logging.debug(
                    f"Ã°Å¸âÅ  Sem histÃÂ³rico suficiente (BUY:{expectativa_buy['trades_similares']}, "
                    f"SELL:{expectativa_sell['trades_similares']}) - IA decide normalmente")

            # Dados mistos ou inconclusivos: NÃÆO forÃÂ§a direÃÂ§ÃÂ£o Ã¢â¬â deixa IA decidir
            prever_acao._ultimo_veto = False

        # ========== APLICAÃâ¡ÃÆO DOS FILTROS DE ALTA ACERTIVIDADE ==========
        if contexto_completo:
            pode_operar, motivo = filtros_alta_acertividade(contexto_completo)
            if not pode_operar:
                if not hasattr(prever_acao, '_ultimo_log_bloqueio'):
                    prever_acao._ultimo_log_bloqueio = 0
                if time.time() - prever_acao._ultimo_log_bloqueio >= 60:
                    logging.info(f"BLOQUEIO: {motivo}")
                    prever_acao._ultimo_log_bloqueio = time.time()
                return "NADA", 0.0

        # VALIDAÃâ¡ÃÆO E CORREÃâ¡ÃÆO DE TIPOS PARA PREDIÃâ¡ÃÆO
        if hasattr(X, 'values'):
            x_pred = X.values.astype(np.float32)
        else:
            x_pred = np.array(X, dtype=np.float32)

        # Verifica se hÃÂ¡ valores invÃÂ¡lidos
        if np.isnan(x_pred).any() or np.isinf(x_pred).any():
            logging.warning(
                "[prever_acao] Dados contÃÂªm valores NaN ou infinitos - corrigindo")
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
            logging.warning("Ã¢Å¡Â Ã¯Â¸Â PrevisÃÂ£o vazia ou invÃÂ¡lida")
            return "NADA", 0.0

        acao_prob = float(resultado_predicao[0][0])  # Garante que ÃÂ© float
        confianca = 1.0

        # Log detalhado da prediÃÂ§ÃÂ£o para diagnÃÂ³stico
        logging.debug(
            f"[prever_acao] Resultado bruto da prediÃÂ§ÃÂ£o: {resultado_predicao[0][0]}")
        logging.debug(f"[prever_acao] Probabilidade processada: {acao_prob}")

        # Se a probabilidade estÃÂ¡ muito baixa (prÃÂ³xima de 0), pode indicar problema no modelo
        if acao_prob < 0.001:
            logging.warning(
                f"Ã¢Å¡Â Ã¯Â¸Â Probabilidade muito baixa: {acao_prob:.6f} - Modelo pode precisar de retreino")
            # ForÃÂ§a uma decisÃÂ£o baseada em RSI como fallback
            if 'rsi_14' in X.columns:
                rsi_val_scaled = X['rsi_14'].iloc[0]
                # X jÃÂ¡ estÃÂ¡ escalado pelo scaler: rsi_14 min=1.0, max=100.0
                rsi_val_real = rsi_val_scaled * 99.0 + 1.0
                if rsi_val_real < 30:  # Sobrevenda - favorece compra
                    acao_prob = 0.7
                    logging.info(
                        f"Ã°Å¸ââ Fallback RSI: RSI={rsi_val_real:.1f} (raw) < 30, forÃÂ§ando BUY (prob={acao_prob})")
                elif rsi_val_real > 70:  # Sobrecompra - favorece venda
                    acao_prob = 0.3
                    logging.info(
                        f"Ã°Å¸ââ Fallback RSI: RSI={rsi_val_real:.1f} (raw) > 70, forÃÂ§ando SELL (prob={acao_prob})")
                else:
                    # RSI neutro - usa desequilÃÂ­brio do book para direÃÂ§ÃÂ£o
                    bid_dom = float(contexto_completo.get('bid_qty', 0)) if contexto_completo else 0
                    ask_dom = float(contexto_completo.get('ask_qty', 0)) if contexto_completo else 0
                    if bid_dom > ask_dom:
                        acao_prob = 0.6  # Mais compradores Ã¢â â favorece BUY
                        logging.info(
                            f"Ã°Å¸ââ Fallback Book: BID {bid_dom:.0f} > ASK {ask_dom:.0f}, favorecendo BUY")
                    elif ask_dom > bid_dom:
                        acao_prob = 0.4  # Mais vendedores Ã¢â â favorece SELL
                        logging.info(
                            f"Ã°Å¸ââ Fallback Book: ASK {ask_dom:.0f} > BID {bid_dom:.0f}, favorecendo SELL")
                    else:
                        acao_prob = 0.5  # Equilibrado Ã¢â â neutro
                        logging.info(
                            f"Ã°Å¸ââ Fallback Book: BID=ASK={bid_dom:.0f}, neutro")

        # Ajusta threshold baseado no balanceamento atual
        if memoria_experiencias:
            status = memoria_experiencias.get_balanceamento_status()
            razao_atual = status["razao_buy_sell"]

            # Log detalhado do estado atual
            logging.info(
                f"Ã°Å¸âÅ  Estado atual - Prob. compra: {acao_prob:.3f}, RSI: {X['rsi_14'].iloc[0]:.1f}")

            # ========== INTEGRAÃâ¡ÃÆO MELHORIA 2: BALANCEAMENTO BUY/SELL ==========
            threshold_base = 0.5
            acao_forcada_balanceador = None

            if balanceador and BALANCEAMENTO_ATIVO:
                threshold_base = balanceador.ajustar_threshold(threshold_base)
                status = balanceador.get_status()
                logging.info(f"Ã¢Å¡âÃ¯Â¸Â Balanceamento: BUY={status['buy_count']}, SELL={status['sell_count']}, "
                             f"BUY%={status['buy_percentage']:.1f}%, Threshold ajustado={threshold_base:.3f}")

                # Verifica se deve forÃÂ§ar operaÃÂ§ÃÂ£o pelo balanceador
                if status['deve_forcar']:
                    acao_forcada_balanceador = status['acao_forcada']
                    logging.info(
                        f"Ã°Å¸Å¡Â¨ BALANCEADOR FORÃâ¡A: {acao_forcada_balanceador} devido a desbalanceamento extremo")

            # Ajusta threshold dinamicamente com MAIS AGRESSIVIDADE
            max_ajuste = 0.25  # Aumentado para 25% (mais agressivo)

            # Considera RSI para ajuste adicional
            rsi = X['rsi_14'].iloc[0]
            rsi_ajuste = 0.0

            if rsi < 30:  # Sobrevenda
                rsi_ajuste = -0.05  # Favorece compras
            elif rsi > 70:  # Sobrecompra
                rsi_ajuste = 0.05  # Favorece vendas

            # Filtro de ConfianÃÂ§a MÃÂ­nima (confidence gap 0.15) Ã¢â¬â zona neutra
            CONFIDENCE_GAP = 0.15
            confianca = abs(acao_prob - 0.5)
            if confianca < CONFIDENCE_GAP:
                logging.info(
                    f"Ã¢ÂÂ¸Ã¯Â¸Â Sinal NEUTRO (confianÃÂ§a {confianca:.3f} < {CONFIDENCE_GAP}) | Prob: {acao_prob:.3f} | Ignorado")
                return "NADA", 0.0

            # DecisÃÂ£o baseada na probabilidade (sem forÃÂ§ar lado)
            threshold = threshold_base + rsi_ajuste
            acao_inicial = "BUY" if acao_prob > threshold else "SELL"
            logging.info(
                f"Ã°Å¸âÅ  DecisÃÂ£o por probabilidade: {acao_inicial} | Prob: {acao_prob:.3f} | ConfianÃÂ§a: {confianca:.3f} | Threshold: {threshold:.3f}")

            # ========== ESTRATÃâ°GIA ESCALONADA POR QUALIDADE DO SETUP ==========
            if contexto_completo:
                volume_total = contexto_completo.get(
                    'bid_qty', 0) + contexto_completo.get('ask_qty', 0)
                entropia = contexto_completo.get('entropia_book', 0)
                atr = contexto_completo.get('volatility', 0)

                # Calcula score de qualidade novamente para definir estratÃÂ©gia
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

                # Define parÃÂ¢metros baseado na qualidade do setup
                if score_qualidade >= 8:  # Setup ULTRA PREMIUM
                    confianca = 0.95
                    logging.info(
                        f"Ã°Å¸Ââ  SETUP ULTRA PREMIUM (score {score_qualidade}/11) - ConfianÃÂ§a mÃÂ¡xima!")
                elif score_qualidade >= 6:  # Setup PREMIUM
                    confianca = 0.85
                    logging.info(
                        f"Ã¢Â­Â SETUP PREMIUM (score {score_qualidade}/11) - Alta confianÃÂ§a")
                else:  # Setup BOM (jÃÂ¡ passou nos filtros)
                    confianca = 0.75
                    logging.info(
                        f"Ã¢Åâ¦ SETUP BOM (score {score_qualidade}/11) - ConfianÃÂ§a moderada")

            # ========== APLICAÃâ¡ÃÆO DOS FILTROS ADICIONAIS ==========
            # Filtro 1: HorÃÂ¡rio Premium
            if FILTRO_HORARIO_ATIVO and filtro_horario and not filtro_horario.is_horario_premium():
                logging.info("Ã¢ÂÂ° OperaÃÂ§ÃÂ£o bloqueada - Fora do horÃÂ¡rio premium")
                return "NADA", 0.0

            # Filtro 2: TendÃÂªncia em CONSENSO (sÃÂ³ bloqueia se AMBOS detectores concordarem)
            if DETECTOR_TENDENCIA_ATIVO and detector_tendencia:
                _ema_bloqueia_buy = detector_tendencia.tendencia_atual == "BAIXA" and acao_inicial == "BUY"
                _ema_bloqueia_sell = detector_tendencia.tendencia_atual == "ALTA" and acao_inicial == "SELL"
                _sma_bloqueia_buy = _tendencia_veto_buy and acao_inicial == "BUY"
                _sma_bloqueia_sell = _tendencia_veto_sell and acao_inicial == "SELL"
                if (_ema_bloqueia_buy and _sma_bloqueia_buy) or (_ema_bloqueia_sell and _sma_bloqueia_sell):
                    logging.info(
                        f"Ã°Å¸âË CONSENSO DE TENDÃÅ NCIA: {acao_inicial} bloqueado "
                        f"(EMA={detector_tendencia.tendencia_atual}, SMA={_tendencia_result['motivo']})")
                    return "NADA", 0.0

            # Filtro 3: Cooldown Ã¢â¬â jÃÂ¡ verificado na Prioridade 0, mantido aqui como seguranÃÂ§a de redundÃÂ¢ncia
            # (nÃÂ£o gera log duplicado pois Prioridade 0 jÃÂ¡ bloqueou antes de chegar aqui)

            # Filtro 4: Spread dinÃÂ¢mico
            spread_atual = contexto_completo.get(
                'spread', 0) if contexto_completo else 0
            if SPREAD_DINAMICO_ATIVO and filtro_spread and not filtro_spread.spread_aceitavel(spread_atual):
                logging.info(
                    f"Ã°Å¸âÅ  OperaÃÂ§ÃÂ£o bloqueada - Spread alto ({spread_atual:.1f} >{filtro_spread.spread_maximo_atual})")
                return "NADA", 0.0

            # DECISÃÆO FINAL: Considera ambos os sistemas de balanceamento
            if acao_forcada_balanceador:
                acao = acao_forcada_balanceador
                logging.info(
                    f"Ã°Å¸Å½Â¯ DECISÃÆO FINAL FORÃâ¡ADA pelo balanceador: {acao}")
            else:
                acao = acao_inicial
                logging.info(f"Ã°Å¸Å½Â¯ DECISÃÆO FINAL normal: {acao}")

            # ========== VETO DE TENDÃÅ NCIA (pÃÂ³s-decisÃÂ£o) ==========
            # Se o modelo escolheu BUY mas tendÃÂªncia ÃÂ© de baixa Ã¢â â bloqueia
            # EXCETO se RSI estiver em zona extrema (mean reversion)
            if acao == "BUY" and _tendencia_veto_buy:
                rsi_override = rsi * 99.0 + 1.0
                if rsi_override < 25.0:
                    logging.info(f"Ã°Å¸âÅ  RSI={rsi_override:.1f} (sobrevendido) sobrepÃÂµe veto de tendÃÂªncia - BUY liberado")
                else:
                    logging.warning(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA VETO pÃÂ³s-decisÃÂ£o: BUY bloqueado (mercado em queda, RSI={rsi_override:.1f})")
                    return "NADA", 0.0
            if acao == "SELL" and _tendencia_veto_sell:
                rsi_override = rsi * 99.0 + 1.0
                if rsi_override > 75.0:
                    logging.info(f"Ã°Å¸âÅ  RSI={rsi_override:.1f} (sobrecomprado) sobrepÃÂµe veto de tendÃÂªncia - SELL liberado")
                else:
                    logging.warning(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA VETO pÃÂ³s-decisÃÂ£o: SELL bloqueado (mercado em alta, RSI={rsi_override:.1f})")
                    return "NADA", 0.0

            # ========== FILTRO MEAN REVERSION (RSI + Z-Score + ADX) ==========
            rsi_real = rsi * 99.0 + 1.0  # Desescala RSI do scaler
            preco_atual_tend = contexto_completo.get('preco', 0) if contexto_completo else 0
            if preco_atual_tend and preco_atual_tend > 0 and rsi_real > 0:
                mr_result = filtro_mean_reversion.avaliar(
                    preco_atual=preco_atual_tend,
                    rsi_real=rsi_real,
                    ema_atual=preco_atual_tend,  # Usando preÃÂ§o como proxy da EMA
                    ema_anterior=preco_atual_tend
                )
                if mr_result['veto_buy'] and acao == "BUY":
                    logging.warning(
                        f"Ã°Å¸Å¡Â« MR VETO BUY: RSI={rsi_real:.1f}({mr_result['rsi_zona']}) | "
                        f"Z={mr_result['zscore']:+.2f} | ADX={mr_result['adx']:.1f}({mr_result['estado']})")
                    return "NADA", 0.0
                if mr_result['veto_sell'] and acao == "SELL":
                    logging.warning(
                        f"Ã°Å¸Å¡Â« MR VETO SELL: RSI={rsi_real:.1f}({mr_result['rsi_zona']}) | "
                        f"Z={mr_result['zscore']:+.2f} | ADX={mr_result['adx']:.1f}({mr_result['estado']})")
                    return "NADA", 0.0

            # Log detalhado do balanceamento
            if balanceador and BALANCEAMENTO_ATIVO:
                status_bal = balanceador.get_status()
                logging.info(
                    f"Ã°Å¸ââ Balanceamento - BUY: {status_bal['buy_percentage']:.1f}% | SELL: {status_bal['sell_percentage']:.1f}%")
            else:
                mem_status = memoria_experiencias.get_balanceamento_status()
                logging.info(
                    f"Ã°Å¸ââ Balanceamento - BUY: {mem_status['buy_percent']:.1f}% | SELL: {mem_status['sell_percent']:.1f}%")
            # Log detalhado da decisÃÂ£o final
            if acao_forcada_balanceador:
                logging.info(
                    f"Ã°Å¸âË DecisÃÂ£o FORÃâ¡ADA: {acao} | Prob original: {acao_prob:.3f} | Threshold: {threshold:.3f} | IGNORADO por balanceamento")
            else:
                logging.info(
                    f"Ã°Å¸âË DecisÃÂ£o normal: {acao} | Prob: {acao_prob:.3f} | Threshold: {threshold:.3f}")
        else:
            threshold = 0.5
            acao = "BUY" if acao_prob > threshold else "SELL"
            logging.info(
                f"Ã°Å¸âË DecisÃÂ£o sem balanceamento: {acao} | Prob: {acao_prob:.3f}")

        # ========== VETO DE TENDÃÅ NCIA (pÃÂ³s-decisÃÂ£o, fora do balanceador) ==========
        if acao == "BUY" and _tendencia_veto_buy:
            rsi_over = rsi * 99.0 + 1.0
            if rsi_over < 25.0:
                logging.info(f"Ã°Å¸âÅ  RSI={rsi_over:.1f} (sobrevendido) sobrepÃÂµe veto de tendÃÂªncia - BUY liberado")
            else:
                logging.warning(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA VETO pÃÂ³s-decisÃÂ£o: BUY bloqueado (mercado em queda, RSI={rsi_over:.1f})")
                return "NADA", 0.0
        if acao == "SELL" and _tendencia_veto_sell:
            rsi_over = rsi * 99.0 + 1.0
            if rsi_over > 75.0:
                logging.info(f"Ã°Å¸âÅ  RSI={rsi_over:.1f} (sobrecomprado) sobrepÃÂµe veto de tendÃÂªncia - SELL liberado")
            else:
                logging.warning(f"Ã°Å¸Å¡Â« TENDÃÅ NCIA VETO pÃÂ³s-decisÃÂ£o: SELL bloqueado (mercado em alta, RSI={rsi_over:.1f})")
                return "NADA", 0.0

        # ========== FILTRO MEAN REVERSION (pÃÂ³s-decisÃÂ£o, fora do balanceador) ==========
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
                    f"Ã°Å¸Å¡Â« MR VETO BUY: RSI={rsi_real_fallback:.1f}({mr_fb['rsi_zona']}) | "
                    f"Z={mr_fb['zscore']:+.2f} | ADX={mr_fb['adx']:.1f}({mr_fb['estado']})")
                return "NADA", 0.0
            if mr_fb['veto_sell'] and acao == "SELL":
                logging.warning(
                    f"Ã°Å¸Å¡Â« MR VETO SELL: RSI={rsi_real_fallback:.1f}({mr_fb['rsi_zona']}) | "
                    f"Z={mr_fb['zscore']:+.2f} | ADX={mr_fb['adx']:.1f}({mr_fb['estado']})")
                return "NADA", 0.0

        # ========== SENTINELA DE FLUXO (gatekeeper macro) - veto final ==========
        if _sf_veto_sell and acao == 'SELL':
            logging.warning(f"Ã°Å¸Å¡Â« SENTINELA VETO SELL: {_sf_detalhe}")
            prever_acao._ultimo_veto = True
            return "NADA", 0.0
        if _sf_veto_buy and acao == 'BUY':
            logging.warning(f"Ã°Å¸Å¡Â« SENTINELA VETO BUY: {_sf_detalhe}")
            prever_acao._ultimo_veto = True
            return "NADA", 0.0

        return acao, confianca
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao prever aÃÂ§ÃÂ£o: {e}")
        return "NADA", 0.0


def salvar_experiencias_json(experiencias: List[Tuple[Dict[str, Any], str, float, float]], arquivo: str = "experiencias_wdo.json") -> None:
    """
    Ã¢Åâ¦ PA2: FILTRO DE MEMÃâRIA: Salva as experiÃÂªncias em formato JSON.
    SÃÂ³ salva experiÃÂªncias com lucro > 0 conforme plano de aÃÂ§ÃÂ£o.
    """
    try:
        dados = []
        experiencias_positivas = 0
        experiencias_totais = len(experiencias)

        for contexto, acao, lucro, score_dist in experiencias:
            # Ã¢Åâ¦ PA2: FILTRO DE MEMÃâRIA: SÃÂ³ salva se lucro > 0
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
            f"Ã¢Åâ¦ PA2 FILTRO DE MEMÃâRIA: {experiencias_positivas}/{experiencias_totais} experiÃÂªncias positivas salvas em {arquivo}")

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao salvar experiÃÂªncias em JSON: {e}")


def salvar_decisao_csv(acao: str, confianca: float, contexto: Dict[str, Any], arquivo: str = None) -> None:
    if arquivo is None:
        arquivo = DECISIONS_CSV
    """Salva uma decisÃÂ£o no arquivo CSV de decisÃÂµes."""
    try:
        abs_path_arquivo = os.path.abspath(arquivo)
        logging.debug(
            f"[salvar_decisao_csv] Tentando salvar decisÃÂ£o em: {abs_path_arquivo}")

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

        # Escreve com cabeÃÂ§alho se o arquivo nÃÂ£o existe OU se existe mas estÃÂ¡ vazio.
        if not file_exists or (file_exists and file_size == 0):
            df.to_csv(abs_path_arquivo, index=False)
        else:
            # Adiciona sem cabeÃÂ§alho se o arquivo jÃÂ¡ existe e tem conteÃÂºdo.
            df.to_csv(abs_path_arquivo, mode='a', header=False, index=False)

        logging.debug(f"Ã¢Åâ¦ DecisÃÂ£o salva em {abs_path_arquivo}")
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao salvar decisÃÂ£o em CSV: {e}")

# endregion

# region [FunÃÂ§ÃÂµes de Mercado]


def verificar_estado_book(symbol: str = SYMBOL) -> bool:
    """Verifica se o book estÃÂ¡ ativo e funcionando corretamente."""
    try:
        # Verifica se ÃÂ© fim de semana
        if datetime.now().weekday() > 4:  # 5 = SÃÂ¡bado, 6 = Domingo
            logging.info(
                "Ã°Å¸ââ¦ Fim de semana: book nÃÂ£o disponÃÂ­vel (comportamento normal)")
            return True  # Retorna True para evitar tentativas de reinicializaÃÂ§ÃÂ£o

        # Verifica se ÃÂ© horÃÂ¡rio de mercado fechado (fora do pregÃÂ£o)
        agora = datetime.now().time()
        inicio_pregao = datetime.strptime("09:00", "%H:%M").time()
        fim_pregao = datetime.strptime("17:40", "%H:%M").time()

        if agora < inicio_pregao or agora > fim_pregao:
            logging.info(
                f"Ã°Å¸â¢Â Mercado fechado ({agora.strftime('%H:%M')}): book nativo indisponÃÂ­vel (normal)")
            # Fora do pregÃÂ£o o book nativo fica vazio Ã¢â¬â retorna True para nÃÂ£o
            # disparar reinicializaÃÂ§ÃÂµes desnecessÃÂ¡rias do book.
            return True

        # Garante que o sÃÂ­mbolo esteja selecionado
        mt5.symbol_select(symbol)

        # Verifica se o sÃÂ­mbolo estÃÂ¡ ativo
        if not mt5.symbol_info(symbol):
            logging.error(f"Ã¢ÂÅ SÃÂ­mbolo {symbol} nÃÂ£o encontrado")
            return False

        # Tenta obter dados do book
        book = mt5.market_book_get(symbol)

        if book is None:
            return False

        if len(book) == 0:
            logging.error("Ã¢ÂÅ Book vazio")
            return False

        # Verifica tipos no book
        tipos_ordem = set(level.type for level in book)
        if len(tipos_ordem) < 2:
            logging.error("Book incompleto: tipos insuficientes")
            return False

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao verificar book: {e}")
        return False


def reiniciar_book(symbol: str = SYMBOL) -> bool:
    """Tenta reiniciar o book de ofertas."""
    try:
        # Desativa o book
        mt5.market_book_release(symbol)
        time.sleep(1)  # Espera 1 segundo

        # Reativa o book
        if not mt5.market_book_add(symbol):
            logging.error("Ã¢ÂÅ Falha ao reativar book")
            return False

        time.sleep(1)  # Espera mais 1 segundo

        # Verifica se estÃÂ¡ funcionando
        return verificar_estado_book(symbol)

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao reiniciar book: {e}")
        return False


def calcular_atr(high_prices: List[float], low_prices: List[float], close_prices: List[float], periodo: int = 14) -> float:
    """
    Calcula o Average True Range (ATR) para um perÃÂ­odo especÃÂ­fico.

    Args:
        high_prices: Lista de preÃÂ§os mÃÂ¡ximos
        low_prices: Lista de preÃÂ§os mÃÂ­nimos
        close_prices: Lista de preÃÂ§os de fechamento
        periodo: PerÃÂ­odo para cÃÂ¡lculo do ATR (default 14)

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

    # Calcula mÃÂ©dia mÃÂ³vel do TR para obter ATR
    if not tr_values:
        return 0.0

    # Implementa Wilder's Smoothing
    atr = tr_values[0]  # Primeiro TR como valor inicial
    for tr in tr_values[1:]:
        atr = ((periodo - 1) * atr + tr) / periodo

    return atr


def verificar_mercado_aberto() -> Tuple[bool, str]:
    """Verifica se o mercado estÃÂ¡ aberto e em qual perÃÂ­odo."""
    agora = datetime.now().time()
    pregao = datetime.strptime(HORARIO_PREGAO, "%H:%M").time()
    after = datetime.strptime(HORARIO_AFTER, "%H:%M").time()

    # Verifica se ÃÂ© fim de semana
    if datetime.now().weekday() > 4:  # 5 = SÃÂ¡bado, 6 = Domingo
        return False, "Mercado fechado (Fim de semana) Ã°Å¸ÂâÃ¯Â¸Â"

    # Verifica horÃÂ¡rio
    if agora < pregao:
        return False, "Mercado fechado (Antes do pregÃÂ£o) Ã¢ÂÂ°"
    elif agora > after:
        return False, "Mercado fechado (ApÃÂ³s after-market) Ã°Å¸Åâ¢"

    # Verifica se o sÃÂ­mbolo estÃÂ¡ ativo
    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        return False, "SÃÂ­mbolo nÃÂ£o encontrado Ã¢Ââ"

    if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
        return False, f"SÃÂ­mbolo nÃÂ£o estÃÂ¡ ativo para trading ({symbol_info.trade_mode}) Ã¢Å¡Â Ã¯Â¸Â"

    return True, "Mercado aberto Ã¢Åâ¦"


def arredondar_preco(preco: float) -> float:
    """Arredonda o preÃÂ§o para a precisÃÂ£o correta do Mini DÃÂ³lar (WDO)."""
    return round(preco / TICK_SIZE) * TICK_SIZE


def calcular_preco_sl_tp(preco_entrada: float, action: str, sl_points: int, tp_points: int) -> Tuple[float, float]:
    """Calcula preÃÂ§os de SL e TP com arredondamento correto, usando pontos (nÃÂ£o ticks).
    WDO: tp_points=0 Ã¢â â TP=0 (sem take profit, saÃÂ­da dinÃÂ¢mica por GerenciadorDeSaida)."""
    from MetaTrader5 import symbol_info
    symbol = SYMBOL
    symbol_info_obj = get_cached_symbol_info(symbol)
    if symbol_info_obj is None:
        raise ValueError(
            "InformaÃÂ§ÃÂµes do sÃÂ­mbolo indisponÃÂ­veis para cÃÂ¡lculo de SL/TP.")

    ponto = symbol_info_obj.point
    # Para WDO: 1 ponto = 1.0 de distÃÂ¢ncia de preÃÂ§o (tick = 0.5)
    # Corrigido: NÃÆO multiplicar por TICK_SIZE (dava fator 2, SL apertado)
    sl_dist = float(sl_points)  # 8 pontos = 8.0

    # Garante distÃÂ¢ncia mÃÂ­nima conforme trade_stops_level do broker
    min_stops_ticks = symbol_info_obj.trade_stops_level  # ex: 5 ticks
    min_dist = max(sl_dist, (min_stops_ticks + 1) * TICK_SIZE)
    if min_dist > sl_dist:
        logging.info(
            f"Ã°Å¸âÂ§ SL dist ajustada: {sl_dist:.1f} -> {min_dist:.1f} (trade_stops_level={min_stops_ticks})")
    sl_dist = min_dist

    # TP=0 Ã¢â â sem take profit (saÃÂ­da dinÃÂ¢mica)
    tp_dist = float(tp_points) if tp_points > 0 else 0.0

    # Log detalhado para debug
    logging.info(
        f"Ã°Å¸âÂ§ DEBUG SL/TP - Entrada: {preco_entrada:.1f}, AÃÂ§ÃÂ£o: {action}")
    logging.info(
        f"Ã°Å¸âÂ§ DEBUG SL/TP - SL_POINTS: {sl_points}, TP_POINTS: {tp_points}")
    logging.info(
        f"Ã°Å¸âÂ§ DEBUG SL/TP - Point: {ponto}, TICK_SIZE: {TICK_SIZE}, TICKS_POR_PONTO: {TICKS_POR_PONTO}")
    logging.info(
        f"Ã°Å¸âÂ§ DEBUG SL/TP - SL_dist: {sl_dist:.5f}, TP_dist: {tp_dist:.5f}")

    if action == 'BUY':
        sl = arredondar_preco(preco_entrada - sl_dist)
        tp = 0.0 if tp_points == 0 else arredondar_preco(preco_entrada + tp_dist)
    else:
        sl = arredondar_preco(preco_entrada + sl_dist)
        tp = 0.0 if tp_points == 0 else arredondar_preco(preco_entrada - tp_dist)

    tp_str = f"{tp:.1f}" if tp > 0 else "0 (sem TP)"
    logging.info(f"Ã°Å¸âÂ§ DEBUG SL/TP - Calculado: SL={sl:.1f}, TP={tp_str}")

    # ValidaÃÂ§ÃÂ£o bÃÂ¡sica
    if action == 'BUY':
        if sl >= preco_entrada:
            logging.error(
                f"Ã¢ÂÅ SL invÃÂ¡lido para BUY: {sl:.1f} >= {preco_entrada:.1f}")
        if tp > 0 and tp <= preco_entrada:
            logging.error(
                f"Ã¢ÂÅ TP invÃÂ¡lido para BUY: {tp:.1f} <= {preco_entrada:.1f}")
    else:  # SELL
        if sl <= preco_entrada:
            logging.error(
                f"Ã¢ÂÅ SL invÃÂ¡lido para SELL: {sl:.1f} <= {preco_entrada:.1f}")
        if tp > 0 and tp >= preco_entrada:
            logging.error(
                f"Ã¢ÂÅ TP invÃÂ¡lido para SELL: {tp:.1f} >= {preco_entrada:.1f}")

    return sl, tp


def calcular_sl_tp_dinamico(preco_entrada: float, acao: str, atr: float) -> Tuple[float, float]:
    """Calcula preÃÂ§os de SL e TP com base no ATR e aÃÂ§ÃÂ£o de compra ou venda."""
    symbol_info = get_cached_symbol_info(SYMBOL)
    if symbol_info is None:
        logging.error("Ã¢ÂÅ InformaÃÂ§ÃÂµes do sÃÂ­mbolo indisponÃÂ­veis")
        return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # ValidaÃÂ§ÃÂ£o inicial do preÃÂ§o de entrada
    if not (100 <= preco_entrada <= 1000000):  # Faixa de preÃÂ§o razoÃÂ¡vel para dÃÂ³lar
        logging.error(f"Ã¢ÂÅ PreÃÂ§o de entrada invÃÂ¡lido: {preco_entrada}")
        return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Calcula distÃÂ¢ncias iniciais em ticks baseadas no ATR
    sl_ticks = int(MULTIPLICADOR_SL_ATR * atr / symbol_info.point)
    tp_ticks = int(MULTIPLICADOR_TP_ATR * atr / symbol_info.point)

    # Log para debug das distÃÂ¢ncias iniciais
    logging.debug(
        f"DistÃÂ¢ncias iniciais - SL: {sl_ticks} ticks | TP: {tp_ticks} ticks")

    # Corrige para faixa segura em ticks
    sl_ticks = min(max(sl_ticks, MIN_TICKS), MAX_TICKS)
    tp_ticks = min(max(tp_ticks, MIN_TICKS), MAX_TICKS)

    # Calcula preÃÂ§os baseados nos ticks ajustados
    if acao == "BUY":
        sl_price = preco_entrada - sl_ticks * symbol_info.point
        tp_price = preco_entrada + tp_ticks * symbol_info.point
    else:
        sl_price = preco_entrada + sl_ticks * symbol_info.point
        tp_price = preco_entrada - tp_ticks * symbol_info.point

    # Arredonda os preÃÂ§os
    sl_price = arredondar_preco(sl_price)
    tp_price = arredondar_preco(tp_price)

    # ValidaÃÂ§ÃÂ£o final dos preÃÂ§os calculados
    preco_max = preco_entrada * 1.1  # Limite mÃÂ¡ximo de 10% acima do preÃÂ§o
    preco_min = preco_entrada * 0.9  # Limite mÃÂ­nimo de 10% abaixo do preÃÂ§o

    # Verifica se os preÃÂ§os estÃÂ£o dentro dos limites razoÃÂ¡veis
    if not (preco_min <= sl_price <= preco_max):
        logging.error(
            f"Ã¢ÂÅ SL calculado invÃÂ¡lido: {sl_price:.1f} (entrada: {preco_entrada:.1f})")
        # Usa fallback seguro
        sl_price = preco_entrada - 500 * \
            symbol_info.point if acao == "BUY" else preco_entrada + 500 * symbol_info.point
        sl_price = arredondar_preco(sl_price)

    if not (preco_min <= tp_price <= preco_max):
        logging.error(
            f"Ã¢ÂÅ TP calculado invÃÂ¡lido: {tp_price:.1f} (entrada: {preco_entrada:.1f})")
        # Usa fallback seguro
        tp_price = preco_entrada + 1000 * \
            symbol_info.point if acao == "BUY" else preco_entrada - 1000 * symbol_info.point
        tp_price = arredondar_preco(tp_price)

    # ValidaÃÂ§ÃÂ£o final da direÃÂ§ÃÂ£o de SL/TP
    if acao == "BUY":
        if sl_price >= preco_entrada or tp_price <= preco_entrada:
            logging.error(
                f"Ã¢ÂÅ DireÃÂ§ÃÂ£o SL/TP invertida para BUY - SL: {sl_price:.1f}, TP: {tp_price:.1f}, Entrada: {preco_entrada:.1f}")
            return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)
    else:  # SELL
        if sl_price <= preco_entrada or tp_price >= preco_entrada:
            logging.error(
                f"Ã¢ÂÅ DireÃÂ§ÃÂ£o SL/TP invertida para SELL - SL: {sl_price:.1f}, TP:{tp_price:.1f}, Entrada: {preco_entrada:.1f}")
            return calcular_preco_sl_tp(preco_entrada, acao, SL_POINTS, TP_POINTS)

    # Log das distÃÂ¢ncias finais
    sl_dist_final = abs(sl_price - preco_entrada) / symbol_info.point
    tp_dist_final = abs(tp_price - preco_entrada) / symbol_info.point
    logging.info(
        f"DistÃÂ¢ncias finais - SL: {sl_dist_final} ticks | TP: {tp_dist_final} ticks")

    return sl_price, tp_price


def verificar_spread_maximo(symbol_info: Any, tick_info: Any) -> bool:
    """Verifica se o spread estÃÂ¡ dentro do limite mÃÂ¡ximo."""
    if symbol_info is None or tick_info is None:
        logging.error(
            "Ã¢ÂÅ Dados do sÃÂ­mbolo ou tick indisponÃÂ­veis para verificar spread")
        return False

    spread_atual = (tick_info.ask - tick_info.bid) / symbol_info.point
    spread_em_pontos = spread_atual / TICKS_POR_PONTO  # Converte para pontos

    if spread_em_pontos > MAX_SPREAD:
        logging.warning(
            f"Ã¢Å¡Â Ã¯Â¸Â Spread alto: {spread_em_pontos:.1f} pontos (mÃÂ¡x: {MAX_SPREAD})")
        return False

    logging.info(f"Ã¢Åâ¦ Spread OK: {spread_em_pontos:.1f} pontos")
    return True

# endregion

# region [Trading]


class PosicaoAtiva:
    """MantÃÂ©m informaÃÂ§ÃÂµes sobre a posiÃÂ§ÃÂ£o ativa."""

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
        self.historico_scores = [score_inicial]  # HistÃÂ³rico para mÃÂ©dia mÃÂ³vel
        self.entry_context = entry_context  # Novo atributo
        self.volume = VOLUME_PADRAO  # CORREÃâ¡ÃÆO: Adicionar volume padrÃÂ£o

    def adicionar_score(self, score: float) -> float:
        """Adiciona score ao histÃÂ³rico e retorna mÃÂ©dia mÃÂ³vel."""
        self.historico_scores.append(score)
        if len(self.historico_scores) > JANELA_SUAVIZACAO:
            self.historico_scores.pop(0)
        return sum(self.historico_scores) / len(self.historico_scores)


def monitorar_posicao_ativa(posicao: PosicaoAtiva) -> None:
    """Monitora uma posiÃÂ§ÃÂ£o ativa e aplica critÃÂ©rios de saÃÂ­da inteligente."""
    tempo_posicao = (datetime.now() - posicao.hora_entrada).total_seconds()
    if tempo_posicao < TEMPO_MIN_POSICAO:
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logging.warning("Ã¢Å¡Â Ã¯Â¸Â Tick indisponÃÂ­vel para monitoramento")
        return

    preco_atual = tick.bid if posicao.tipo == "SELL" else tick.ask

    # ========== INTEGRAÃâ¡ÃÆO MELHORIA 1: TRAILING STOP INTELIGENTE ==========
    if trailing_stop and TRAILING_ATIVO:
        novo_sl = trailing_stop.atualizar_trailing(preco_atual, posicao.tipo)
        if novo_sl:
            # USAR FUNÃâ¡ÃÆO CORRIGIDA com validaÃÂ§ÃÂ£o de distÃÂ¢ncia mÃÂ­nima
            if atualizar_sl(posicao.ticket, novo_sl):
                posicao.sl = novo_sl

    # ========== SAÃÂDA INTELIGENTE ULTRA RESTRITIVA (+MÃÂXIMA ACERTIVIDADE) ==========
    lucro_atual = calcular_lucro_posicao(posicao, preco_atual)
    lucro_maximo = getattr(posicao, 'lucro_maximo', lucro_atual)

    # Atualiza lucro mÃÂ¡ximo
    if lucro_atual > lucro_maximo:
        posicao.lucro_maximo = lucro_atual
        lucro_maximo = lucro_atual

    # REGRA 1: Timeout sem evoluÃÂ§ÃÂ£o (MAIS RESTRITIVO - 2 minutos)
    if tempo_posicao > 120 and lucro_atual <= 15:  # 2 min sem aevoluir
        logging.info(
            f"Ã¢ÂÂ° SAÃÂDA POR TIMEOUT: {tempo_posicao:.0f}s sem evoluÃÂ§ÃÂ£o (lucro: R${lucro_atual:.2f})")
        fechar_posicao_score(posicao, "timeout sem evoluÃÂ§ÃÂ£o", 0.0)
        return

    # REGRA 2: Lucro derretendo (PROTEÃâ¡ÃÆO AGRESSIVA)
    if lucro_maximo > 40 and lucro_atual < lucro_maximo * 0.8:  # Perdeu 20% do pico
        logging.info(
            f"Ã°Å¸ââ° SAÃÂDA POR PROTEÃâ¡ÃÆO: Lucro caiu de R${lucro_maximo:.2f} para R${lucro_atual:.2f}")
        fechar_posicao_score(posicao, "proteÃÂ§ÃÂ£o de lucro", 0.0)
        return

    # REGRA 3: Breakeven apÃÂ³s tempo (MAIS AGRESSIVO)
    if tempo_posicao > 90 and lucro_atual <= 0:  # 1.5 min no zero/negativo
        logging.info(f"Ã°Å¸Å¡Â« SAÃÂDA POR BREAKEVEN: {tempo_posicao:.0f}s sem lucro")
        fechar_posicao_score(posicao, "breakeven preventivo", 0.0)
        return

    # REGRA 4: Lucro pequeno hÃÂ¡ muito tempo (NOVA REGRA)
    if tempo_posicao > 180 and 0 < lucro_atual < 25:  # 3 min com lucro pequeno
        logging.info(
            f"Ã°Å¸ÂÅ SAÃÂDA POR ESTAGNAÃâ¡ÃÆO: Lucro pequeno R${lucro_atual:.2f} hÃÂ¡ {tempo_posicao:.0f}s")
        fechar_posicao_score(posicao, "estagnaÃÂ§ÃÂ£o", 0.0)
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
            posicao, "queda de score pÃÂ³s-lucro", score_suavizado)
        return

    # CritÃÂ©rios jÃÂ¡ existentes
    if verificar_inversao_score(posicao, score_atual):
        fechar_posicao_score(posicao, "inversÃÂ£o de direÃÂ§ÃÂ£o", score_suavizado)
    elif verificar_enfraquecimento(posicao, score_atual):
        if not posicao.travado:
            travar_lucro(posicao, score_atual)


def obter_contexto_completo() -> Optional[Dict]:
    """ObtÃÂ©m o contexto completo atual para anÃÂ¡lise de qualidade do setup."""
    try:
        # ObtÃÂ©m dados do book (nativo, direto do MT5)
        book_data = ler_book_nativo()
        if not book_data:
            return None

        # ObtÃÂ©m dados de mercado
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 50)
        if rates is None or len(rates) == 0:
            return None

        # Calcula indicadores
        df_rates = pd.DataFrame(rates)
        atr = calcular_atr(df_rates['high'].tolist(
        ), df_rates['low'].tolist(), df_rates['close'].tolist(), 14)
        rsi = calcular_rsi(df_rates['close'].tolist(), period=14)
        # CORREÃâ¡ÃÆO: Calcula entropia considerando formato JSON
        if isinstance(book_data['bids'][0], dict):
            # Formato JSON: extrai volumes dos dicionÃÂ¡rios
            volumes_bid = [item['volume'] for item in book_data['bids']]
            volumes_ask = [item['volume'] for item in book_data['asks']]
            entropia = calcular_entropia(volumes_bid + volumes_ask)
        else:
            # Formato legado: usa diretamente
            entropia = calcular_entropia(book_data['bids'] + book_data['asks'])

        # Calcula spread
        tick = mt5.symbol_info_tick(SYMBOL)
        spread = (tick.ask - tick.bid) / TICK_SIZE if tick else 0

        # Ã°Å¸âÂ§ CORREÃâ¡ÃÆO CRÃÂTICA 2: Calcula volumes corretamente baseado no formato
        if isinstance(book_data['bids'][0], dict):
            # Formato JSON: extrai volumes dos dicionÃÂ¡rios
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

        # Adiciona sinal DOL ao contexto (referÃÂªncia institucional)
        book_dol_data = ler_book_dol()
        sinal_dol = analisar_sinal_dol(book_dol_data)
        contexto['dol_ratio'] = sinal_dol.get('ratio', 1.0)
        contexto['dol_lado'] = sinal_dol.get('lado', 'NEUTRO')
        contexto['dol_confianca'] = sinal_dol.get('confianca', 0.0)
        contexto['dol_presente'] = 1 if sinal_dol.get('presente', False) else 0

        return contexto
    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao obter contexto completo: {e}")
        return None


def calcular_lucro_posicao(posicao: PosicaoAtiva, preco_atual: float) -> float:
    """Calcula o lucro atual da posiÃÂ§ÃÂ£o em reais."""
    if posicao.tipo == "BUY":
        diferenca_pontos = (preco_atual - posicao.preco_entrada) / TICK_SIZE
    else:  # SELL
        diferenca_pontos = (posicao.preco_entrada - preco_atual) / TICK_SIZE

    # WDO: 1 ponto = R$5 por contrato
    lucro_reais = diferenca_pontos * posicao.volume
    return lucro_reais


def verificar_inversao_score(posicao: PosicaoAtiva, score_atual: float) -> bool:
    """Verifica se houve inversÃÂ£o significativa no score."""
    # InversÃÂ£o de positivo para negativo (mais conservador)
    if posicao.score_inicial > 0 and score_atual < THRESHOLD_INVERSAO_SCORE:
        return True
    # InversÃÂ£o de negativo para positivo (mais conservador)
    if posicao.score_inicial < 0 and score_atual > abs(THRESHOLD_INVERSAO_SCORE):
        return True
    # Queda abrupta do mÃÂ¡ximo (usando score suavizado)
    if (posicao.score_maximo > SCORE_LOCK_PROFIT and
            score_atual < posicao.score_maximo - INVERSAO_SCORE_MIN):
        return True
    return False


def verificar_enfraquecimento(posicao: PosicaoAtiva, score_atual: float) -> bool:
    """Verifica se o movimento estÃÂ¡ enfraquecendo e precisa travar lucro."""
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
        logging.warning("[travar_lucro] Tick ou SymbolInfo indisponÃÂ­vel.")
        return

    logging.debug(
        f"[travar_lucro] PosiÃÂ§ÃÂ£o: Tipo={posicao.tipo}, Entrada={posicao.preco_entrada:.3f}")
    logging.debug(
        f"[travar_lucro] Tick Atual: Ask={tick.ask:.3f}, Bid={tick.bid:.3f}")

    # Calcula novo SL (garante pelo menos 30% do movimento a favor)
    if posicao.tipo == "BUY":
        movimento = max(0, tick.bid - posicao.preco_entrada)
        novo_sl = posicao.preco_entrada + movimento * 0.3
        # Nunca mova o SL para baixo do preÃÂ§o de entrada (com margem de 1 tick)
        novo_sl = max(novo_sl, posicao.preco_entrada - symbol_info.point)
    else:
        movimento = max(0, posicao.preco_entrada - tick.ask)
        novo_sl = posicao.preco_entrada - movimento * 0.3
        # Nunca mova o SL para cima do preÃÂ§o de entrada (com margem de 1 tick)
        novo_sl = min(novo_sl, posicao.preco_entrada + symbol_info.point)

    # Limite de seguranÃÂ§a: SL nÃÂ£o pode ficar mais de 2x o stop original de distÃÂ¢ncia
    sl_dist_original_ticks = SL_POINTS * TICKS_POR_PONTO  # SL_POINTS ÃÂ© em pontos
    # sl_max_dist_ticks = sl_dist_original_ticks * 2 # NÃÂ£o parece estar sendo usado, mas a ideia de limitar ÃÂ© boa.

    logging.debug(
        f"[travar_lucro] Novo SL (calculado, antes de arredondar e limites de seguranÃÂ§a): {novo_sl:.3f}, Movimento: {movimento:.3f}")

    # Limites de seguranÃÂ§a baseados no preÃÂ§o de entrada e um mÃÂºltiplo do SL original em pontos
    # Convertendo SL_MAX_POINTS para valor de preÃÂ§o
    max_sl_dev = SL_MAX_POINTS * TICKS_POR_PONTO * symbol_info.point
    if posicao.tipo == "BUY":
        sl_limite_inferior = posicao.preco_entrada - max_sl_dev
        # Garante que nÃÂ£o seja muito longe pra baixo
        novo_sl = max(novo_sl, sl_limite_inferior)
    else:  # SELL
        sl_limite_superior = posicao.preco_entrada + max_sl_dev
        # Garante que nÃÂ£o seja muito longe pra cima
        novo_sl = min(novo_sl, sl_limite_superior)

    logging.debug(
        f"[travar_lucro] Novo SL (apÃÂ³s limites de seguranÃÂ§a adicionais): {novo_sl:.3f}")

    novo_sl_arredondado = arredondar_preco(novo_sl)
    logging.debug(
        f"[travar_lucro] Novo SL (apÃÂ³s arredondar_preco): {novo_sl_arredondado:.3f}")

    if atualizar_sl(posicao.ticket, novo_sl_arredondado):
        posicao.sl = novo_sl_arredondado
        posicao.travado = True
        logging.info(
            f"Ã°Å¸ââ Lucro travado em {novo_sl_arredondado:.2f} (Score: {score_atual:.2f})")


def fechar_posicao_atual(motivo: str = "Fechamento manual") -> bool:
    """Fecha a posiÃÂ§ÃÂ£o atual ativa Ã¢â¬â detecta filling aceito pela corretora automaticamente."""
    global posicao_atual

    if posicao_atual is None:
        logging.warning("Nenhuma posiÃÂ§ÃÂ£o ativa para fechar")
        return False

    try:
        tick = mt5.symbol_info_tick(SYMBOL)
        if not tick:
            logging.error("Erro ao obter tick para fechamento")
            return False

        tipo_ordem = mt5.ORDER_TYPE_SELL if posicao_atual.tipo == "BUY" else mt5.ORDER_TYPE_BUY
        preco = tick.bid if posicao_atual.tipo == "BUY" else tick.ask

        # Detecta filling aceito pelo sÃÂ­mbolo na corretora
        info = mt5.symbol_info(SYMBOL)
        filling_mode = info.filling_mode if info else 0

        # Monta lista de fillings na ordem de preferÃÂªncia
        # filling_mode ÃÂ© bitmask: 1=FOK, 2=IOC, 4=RETURN
        fillings_disponiveis = []
        if filling_mode & 1:
            fillings_disponiveis.append(mt5.ORDER_FILLING_FOK)
        if filling_mode & 2:
            fillings_disponiveis.append(mt5.ORDER_FILLING_IOC)
        if filling_mode & 4:
            fillings_disponiveis.append(mt5.ORDER_FILLING_RETURN)

        # Fallback: tenta todos se nÃÂ£o conseguiu detectar
        if not fillings_disponiveis:
            fillings_disponiveis = [
                mt5.ORDER_FILLING_FOK,
                mt5.ORDER_FILLING_IOC,
                mt5.ORDER_FILLING_RETURN
            ]

        logging.debug(
            f"Ã°Å¸âÂ§ Fillings disponÃÂ­veis para {SYMBOL}: {fillings_disponiveis}")

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
                    f"Ã¢Å¡Â Ã¯Â¸Â order_send None (filling={filling}), reconectando...")
                reconectar_mt5()
                time.sleep(0.5)
                tick = mt5.symbol_info_tick(SYMBOL)
                if tick:
                    preco = tick.bid if posicao_atual.tipo == "BUY" else tick.ask
                    request["price"] = preco
                resultado = mt5.order_send(request)

            if resultado is not None and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(
                    f"Ã¢Åâ¦ PosiÃÂ§ÃÂ£o {posicao_atual.ticket} fechada (filling={filling}): {motivo}")
                return True
            elif resultado is not None:
                # Retcodes que indicam posiÃÂ§ÃÂ£o jÃÂ¡ fechada pelo MT5 (TP/SL/manual)
                # Trata como sucesso Ã¢â¬â a posiÃÂ§ÃÂ£o nÃÂ£o existe mais de qualquer forma
                retcodes_posicao_fechada = [
                    10009,  # TRADE_RETCODE_DONE
                    10010,  # TRADE_RETCODE_DONE_PARTIAL
                    10015,  # TRADE_RETCODE_INVALID_PRICE Ã¢â¬â preÃÂ§o mudou, posiÃÂ§ÃÂ£o jÃÂ¡ fechou
                    10016,  # TRADE_RETCODE_INVALID_STOPS
                    10018,  # TRADE_RETCODE_MARKET_CLOSED
                    10019,  # TRADE_RETCODE_NO_MONEY Ã¢â¬â nÃÂ£o aplica mas posiÃÂ§ÃÂ£o foi
                    10030,  # TRADE_RETCODE_POSITION_CLOSED Ã¢â¬â posiÃÂ§ÃÂ£o jÃÂ¡ encerrada
                ]
                if resultado.retcode in retcodes_posicao_fechada:
                    logging.info(
                        f"Ã¢Åâ¦ PosiÃÂ§ÃÂ£o considerada fechada (retcode={resultado.retcode}): {resultado.comment}")
                    return True

                # Verifica se posiÃÂ§ÃÂ£o ainda existe no MT5 apÃÂ³s falha
                posicoes_check = mt5.positions_get(symbol=SYMBOL)
                ticket_ainda_aberto = any(
                    p.ticket == posicao_atual.ticket
                    for p in (posicoes_check or [])
                )
                if not ticket_ainda_aberto:
                    logging.info(
                        f"Ã¢Åâ¦ PosiÃÂ§ÃÂ£o {posicao_atual.ticket} jÃÂ¡ foi fechada pelo MT5 (detectado apÃÂ³s retcode={resultado.retcode})")
                    return True

                logging.warning(
                    f"Ã¢Å¡Â Ã¯Â¸Â Retcode {resultado.retcode} (filling={filling}): {resultado.comment}")

        logging.error(
            f"Ã¢ÂÅ Falha ao fechar posiÃÂ§ÃÂ£o apÃÂ³s todos os fillings: {motivo}")
        return False

    except Exception as e:
        logging.error(f"Erro ao fechar posiÃÂ§ÃÂ£o atual: {e}")
        return False


def fechar_posicao_score(posicao: PosicaoAtiva, motivo: str, score_atual: float) -> None:
    """Fecha posiÃÂ§ÃÂ£o por critÃÂ©rio de score."""
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

    # Ã°Å¸âÂ§ CORREÃâ¡ÃÆO CRÃÂTICA 3: Verificar se resultado nÃÂ£o ÃÂ© None
    if resultado is None:
        logging.error(
            "Ã¢ÂÅ Erro crÃÂ­tico: mt5.order_send retornou None (falha de conexÃÂ£o)")
        return

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(
            f"Ã¢Å¡Â Ã¯Â¸Â PosiÃÂ§ÃÂ£o fechada por {motivo}. Score inicial: {posicao.score_inicial:.2f}, Score final: {score_atual:.2f}")
    else:
        logging.error(f"Ã¢ÂÅ Erro ao fechar posiÃÂ§ÃÂ£o: {resultado.comment}")


def fechar_todas_posicoes(motivo: str = "Encerramento automÃÂ¡tico") -> int:
    """Fecha todas as posiÃÂ§ÃÂµes abertas do robÃÂ´."""
    posicoes_fechadas = 0

    try:
        # ObtÃÂ©m todas as posiÃÂ§ÃÂµes abertas
        posicoes = mt5.positions_get()
        if not posicoes:
            logging.info("Ã¢Åâ¦ Nenhuma posiÃÂ§ÃÂ£o aberta para fechar")
            return 0

        # Filtra apenas posiÃÂ§ÃÂµes do robÃÂ´ (por magic number)
        posicoes_monstro = [
            pos for pos in posicoes if pos.magic == MAGIC_NUMBER]

        if not posicoes_monstro:
            logging.info("Ã¢Åâ¦ Nenhuma posiÃÂ§ÃÂ£o do Monstro para fechar")
            return 0

        logging.info(
            f"Ã°Å¸âÂ´ Iniciando fechamento de {len(posicoes_monstro)} posiÃÂ§ÃÂµes - {motivo}")

        # Fecha cada posiÃÂ§ÃÂ£o
        for pos in posicoes_monstro:
            try:
                # Determina o tipo de ordem necessÃÂ¡rio para fechar
                tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

                # ObtÃÂ©m preÃÂ§o atual
                tick = mt5.symbol_info_tick(pos.symbol)
                if not tick:
                    logging.error(
                        f"Ã¢ÂÅ NÃÂ£o foi possÃÂ­vel obter tick para {pos.symbol}")
                    continue

                preco_fechamento = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask

                # Prepara requisiÃÂ§ÃÂ£o de fechamento
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

                # Ã°Å¸âÂ§ CORREÃâ¡ÃÆO CRÃÂTICA 3: Verificar se resultado nÃÂ£o ÃÂ© None
                if resultado is None:
                    logging.error(
                        f"ï¿½Å Erro crÃÂ­tico: mt5.order_send retornou None para posiÃÂ§ÃÂ£o #{pos.ticket}")
                    # PATCH v22.1 CORTE 2: em alta latencia o servidor processa a
                    # ordem mesmo com retorno None (Trade #7). Varre os ultimos 60s
                    # para capturar a execucao real antes de declarar a falha.
                    try:
                        import time as _t_mod
                        _agora_ts = _t_mod.time()
                        _deals_recentes = mt5.history_deals_get(
                            _agora_ts - 60, _agora_ts + 5)
                        _deal_fecho = None
                        if _deals_recentes:
                            for _d in _deals_recentes:
                                if (_d.position_id == pos.ticket
                                        and _d.entry == mt5.DEAL_ENTRY_OUT):
                                    _deal_fecho = _d
                        if _deal_fecho is not None:
                            posicoes_fechadas += 1
                            shadow_registrar_resultado(
                                pos.ticket, _deal_fecho.profit)
                            logging.info(
                                f"ï¿½â¦ Fecho confirmado via varredura 60s: posicao "
                                f"#{pos.ticket} Lucro={_deal_fecho.profit:.2f}")
                        else:
                            logging.error(
                                f"Ã¢Åï¿½ Falha critica %s: ordem de fecho nao confirmada "
                                f"no servidor para #{pos.ticket}", motivo)
                    except Exception as e:
                        logging.error(
                            f"Ã¢Åï¿½ Erro na varredura de fechamento #{pos.ticket}: {e}")
                    continue

                if resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    posicoes_fechadas += 1
                    logging.info(
                        f"Ã¢Åâ¦ PosiÃÂ§ÃÂ£o #{pos.ticket} fechada - {pos.symbol} {pos.type} Vol:{pos.volume}")
                else:
                    logging.error(
                        f"Ã¢ÂÅ Erro ao fechar posiÃÂ§ÃÂ£o #{pos.ticket}: {resultado.retcode} - {resultado.comment}")

            except Exception as e:
                logging.error(
                    f"Ã¢ÂÅ Erro ao processar posiÃÂ§ÃÂ£o #{pos.ticket}: {e}")
                continue

        logging.info(
            f"Ã°Å¸ÂÂ Fechamento concluÃÂ­do: {posicoes_fechadas} posiÃÂ§ÃÂµes fechadas")
        return posicoes_fechadas

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro crÃÂ­tico ao fechar posiÃÂ§ÃÂµes: {e}")
        return 0


def salvar_dados_finais(modelo_ia_local: Optional[Sequential], memoria_experiencias: MemoriaExperiencias) -> None:
    """Salva todos os dados importantes antes do encerramento."""
    try:
        logging.info("Ã°Å¸âÂ¾ Iniciando salvamento final de dados...")

        # Salva modelo de IA
        if modelo_ia_local:
            salvar_modelo(modelo_ia_local, MODELO_PATH)
            logging.info("Ã¢Åâ¦ Modelo de IA salvo com sucesso")

        # Salva experiÃÂªncias em JSON
        if memoria_experiencias and memoria_experiencias.experiencias:
            salvar_experiencias_json(
                memoria_experiencias.experiencias, "experiencias_finais.json")
            logging.info("Ã¢Åâ¦ ExperiÃÂªncias salvas em JSON")

        # Salva estatÃÂ­sticas finais
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
        logging.info("Ã¢Åâ¦ EstatÃÂ­sticas finais salvas")

        # ForÃÂ§a flush dos logs
        logging.info("Ã°Å¸âÂ¾ Salvamento final concluÃÂ­do com sucesso")

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao salvar dados finais: {e}")


def fechar_conexoes_seguras() -> None:
    """Fecha todas as conexÃÂµes de forma segura."""
    try:
        logging.info("Ã°Å¸âÅ Iniciando fechamento seguro de conexÃÂµes...")

        # Cancela a subscriÃÂ§ÃÂ£o do book nativo (Depth of Market) antes de desligar
        try:
            if SYMBOL:
                mt5.market_book_release(SYMBOL)
                logging.info(f"Ã°Å¸ââ¢ Book nativo liberado para {SYMBOL}")
        except Exception as e:
            logging.debug(f"Falha ao liberar book nativo: {e}")

        # Libera book do DOL se estava ativo
        try:
            if SYMBOL_DOL:
                mt5.market_book_release(SYMBOL_DOL)
                logging.info(f"Ã°Å¸ââ¢ Book DOL liberado para {SYMBOL_DOL}")
        except Exception as e:
            logging.debug(f"Falha ao liberar book DOL: {e}")

        # Fecha conexÃÂ£o MT5
        try:
            if mt5.initialize():
                mt5.shutdown()
                logging.info("Ã¢Åâ¦ ConexÃÂ£o MT5 fechada")
        except Exception as e:
            logging.error(f"Ã¢ÂÅ Erro ao fechar MT5: {e}")

        # Para threads de forma segura
        global thread_ativo
        thread_ativo = False
        logging.info("Ã¢Åâ¦ Threads marcadas para encerramento")

        # Aguarda um momento para threads terminarem
        time.sleep(2)

        logging.info("Ã°Å¸âÅ Fechamento de conexÃÂµes concluÃÂ­do")

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro ao fechar conexÃÂµes: {e}")


def encerramento_seguro_completo(modelo_ia_local: Optional[Sequential], memoria_experiencias: MemoriaExperiencias) -> None:
    """Executa encerramento completo e seguro do sistema."""
    try:
        logging.info("Ã°Å¸âÂ´ INICIANDO ENCERRAMENTO SEGURO COMPLETO DO SISTEMA")

        # Passo 1: Fecha todas as posiÃÂ§ÃÂµes
        posicoes_fechadas = fechar_todas_posicoes(
            "Encerramento seguro do sistema")
        logging.info(f"Ã¢Åâ¦ {posicoes_fechadas} posiÃÂ§ÃÂµes fechadas")

        # Passo 2: Salva todos os dados importantes
        salvar_dados_finais(modelo_ia_local, memoria_experiencias)

        # Passo 3: Fecha conexÃÂµes
        fechar_conexoes_seguras()

        # Passo 4: Log final
        logging.info("Ã°Å¸ÂÂ ENCERRAMENTO SEGURO CONCLUÃÂDO COM SUCESSO")
        logging.info("Ã°Å¸Â¤â MONSTRO DAS NEGOCIAÃâ¡Ãâ¢ES DESLIGADO AUTOMATICAMENTE")

        # Passo 5: ForÃÂ§a flush final dos logs
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Passo 6: Encerra o programa
        logging.info("Ã°Å¸âÂ¤ Sistema sendo desligado...")
        os._exit(0)  # Encerramento forÃÂ§ado mas seguro

    except Exception as e:
        logging.error(f"Ã¢ÂÅ Erro crÃÂ­tico no encerramento seguro: {e}")
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
        # Verifica se ÃÂ© fim de semana
        if datetime.now().weekday() > 4:  # 5 = SÃÂ¡bado, 6 = Domingo
            # Verifica a cada minuto durante fim de semana
            threading.Timer(60, monitorar_spread).start()
            return

        # Resto do cÃÂ³digo permanece igual...
        spreads = []
        while thread_ativo:
            try:
                tick = mt5.symbol_info_tick(SYMBOL)
                symbol_info = get_cached_symbol_info(SYMBOL)

                if tick and symbol_info:
                    spread_atual = (tick.ask - tick.bid) / symbol_info.point
                    spread_em_pontos = spread_atual / TICKS_POR_PONTO

                    spreads.append(spread_em_pontos)
                    if len(spreads) > 100:  # MantÃÂ©m ÃÂºltimos 100 valores
                        spreads.pop(0)

                    # Log removido: era redundante e bugado (mostrava 0.0). O spread
                    # real jÃÂ¡ aparece correto no log de mercado (ex.: "Spread: 5.0pts").
                    # A coleta de 'spreads' fica mantida caso outra parte precise.

                time.sleep(1)  # Atualiza a cada segundo

            except Exception as e:
                logging.error(f"Erro ao monitorar spread: {e}")
                time.sleep(1)
    except Exception as e:
        logging.error(f"Erro ao monitorar spread: {e}")
        time.sleep(1)

# endregion


# ========== FILTRO DE TENDÃÅ NCIA (SMA-50 + MOMENTUM) ==========
class FiltroTendencia:
    """Bloqueia operaÃÂ§ÃÂµes contra a tendÃÂªncia usando SMA-50 + momentum.

    3 camadas de detecÃÂ§ÃÂ£o:
    1. SMA-50: diff > 1.0pt = tendÃÂªncia (SMA lenta, reage devagar)
    2. Momentum: subiu >3pts nos ÃÂºltimos 20 ticks = tendÃÂªncia de alta
    3. Consenso: se 2+ sinais concordam, bloqueia com mais forÃÂ§a
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
        """Registra preÃÂ§o UMA VEZ por ciclo (evita dupla registro)."""
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
        """Detecta momentum: compara preÃÂ§o atual com preÃÂ§o de 20 ticks atrÃÂ¡s.
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
        """Avalia tendÃÂªncia completa e retorna dict com resultado.
        Chamar UMA VEZ por ciclo Ã¢â¬â NÃÆO chamar para BUY e SELL separadamente."""
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

        # Ã¢ââ¬Ã¢ââ¬ Camada 1: SMA-50 Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
        sma_tendencia = abs(diff) > self.margem_pts

        # Ã¢ââ¬Ã¢ââ¬ Camada 2: Momentum (20 ticks) Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
        momentum_tendencia = momentum_dir != "NEUTRO"

        # Ã¢ââ¬Ã¢ââ¬ Camada 3: Consenso Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
        # Se SMA e momentum concordam Ã¢â â tendÃÂªncia forte
        # Se sÃÂ³ um detecta Ã¢â â tendÃÂªncia fraca (ainda bloqueia)
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

        # Ã¢ââ¬Ã¢ââ¬ DecisÃÂ£o de veto Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
        # TendÃÂªncia de ALTA: bloqueia SELL
        if diff > self.margem_pts or momentum_dir == "ALTA":
            resultado['veto_sell'] = True
            resultado['motivo'] = (
                f"TENDENCIA DE ALTA: Preco {diff:+.1f}pts acima SMA, "
                f"Momentum {momentum_pts:+.1f}pts")
            if not self._ultima_decisao_veto_sell:
                logging.info(f"Ã°Å¸Å¡Â« TENDENCIA BLOQUEIA SELL: {resultado['motivo']}")
            self._ultima_decisao_veto_sell = True
        else:
            self._ultima_decisao_veto_sell = False

        # TendÃÂªncia de BAIXA: bloqueia BUY
        if diff < -self.margem_pts or momentum_dir == "BAIXA":
            resultado['veto_buy'] = True
            resultado['motivo'] = (
                f"TENDENCIA DE BAIXA: Preco {diff:+.1f}pts abaixo SMA, "
                f"Momentum {momentum_pts:+.1f}pts")
            if not self._ultima_decisao_veto_buy:
                logging.info(f"Ã°Å¸Å¡Â« TENDENCIA BLOQUEIA BUY: {resultado['motivo']}")
            self._ultima_decisao_veto_buy = True
        else:
            self._ultima_decisao_veto_buy = False

        return resultado

    def pode_operar(self, direcao: str, preco_atual: float) -> tuple:
        """Compatibilidade: avalia e retorna (pode, motivo) para uma direÃÂ§ÃÂ£o."""
        resultado = self.avaliar_tendencia(preco_atual)
        if direcao == "BUY":
            return not resultado['veto_buy'], resultado['motivo']
        else:
            return not resultado['veto_sell'], resultado['motivo']


filtro_tendencia = FiltroTendencia(janela=50, margem_pts=4.5)


# ========== FILTRO MEAN REVERSION (RSI + Z-Score + ADX) ==========
class FiltroMeanReversion:
    """Sistema de 3 camadas para filtrar operaÃÂ§ÃÂµes por reversÃÂ£o ÃÂ  mÃÂ©dia.

    Camada 1 - RSI por Zonas (70/50/30):
        RSI > 70 Ã¢â â sobrecomprado Ã¢â â bloqueia BUY (sÃÂ³ permite SELL)
        RSI < 30 Ã¢â â sobrevendido Ã¢â â bloqueia SELL (sÃÂ³ permite BUY)
        RSI 30-70 Ã¢â â normal Ã¢â â permite ambos

    Camada 2 - Z-Score (desvio padrÃÂ£o da mÃÂ©dia):
        Z > +1.5 Ã¢â â preÃÂ§o esticado p/ cima Ã¢â â bloqueia BUY
        Z < -1.5 Ã¢â â preÃÂ§o esticado p/ baixo Ã¢â â bloqueia SELL

    Camada 3 - ADX Trend Classifier:
        ADX < 20 Ã¢â â LATERAL Ã¢â â mean reversion ativo (RSI+Z-Score mandam)
        ADX >= 25 + EMA subindo Ã¢â â TENDENCIA_ALTA Ã¢â â sÃÂ³ BUY
        ADX >= 25 + EMA descendo Ã¢â â TENDENCIA_BAIXA Ã¢â â sÃÂ³ SELL
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

    # Ã¢ââ¬Ã¢ââ¬ Z-Score Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
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

    # Ã¢ââ¬Ã¢ââ¬ ADX + DireÃÂ§ÃÂ£o (EMA slope) Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
    def _calcular_adx_simples(self, ema_atual: float, ema_anterior: float) -> tuple:
        """Calcula ADX simplificado baseado na inclinaÃÂ§ÃÂ£o da EMA e distÃÂ¢ncia do preÃÂ§o.

        Retorna: (adx_valor: float, direcao: str)
        """
        self.historico_ema.append(ema_atual)
        if len(self.historico_ema) > self.janela:
            self.historico_ema = self.historico_ema[-self.janela:]

        if len(self.historico_ema) < 5:
            return 0.0, "NEUTRO"

        # InclinaÃÂ§ÃÂ£o da EMA (variaÃÂ§ÃÂ£o nos ÃÂºltimos 3 ticks)
        inclinacao = ema_atual - self.historico_ema[-3] if len(self.historico_ema) >= 3 else 0

        # ADX simplificado: magnitude da inclinaÃÂ§ÃÂ£o acumulada
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

    # Ã¢ââ¬Ã¢ââ¬ AvaliaÃÂ§ÃÂ£o Principal Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
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

        # Ã¢ââ¬Ã¢ââ¬ Se TENDÃÅ NCIA, mean reversion desligado Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
        if estado in ("TENDENCIA_ALTA", "TENDENCIA_BAIXA"):
            if estado == "TENDENCIA_ALTA":
                veto_sell = True  # SÃÂ³ permite BUY em tendÃÂªncia de alta
            else:
                veto_buy = True  # SÃÂ³ permite SELL em tendÃÂªncia de baixa
            rsi_zona = "TENDENCIA"
        else:
            # Ã¢ââ¬Ã¢ââ¬ LATERAL: RSI + Z-Score ativos Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬Ã¢ââ¬
            # RSI por zonas
            if rsi_real > self.rsi_venda:
                veto_buy = True
                rsi_zona = "SOBRECOMPRADO"
            elif rsi_real < self.rsi_compra:
                veto_sell = True
                rsi_zona = "SOBREVENDIDO"
            else:
                rsi_zona = "NEUTRO"

            # Z-Score (reforÃÂ§a o veto do RSI)
            if zscore > self.zscore_limiar:
                veto_buy = True
                rsi_zona += "+Z_ESTICADO"
            elif zscore < -self.zscore_limiar:
                veto_sell = True
                rsi_zona += "+Z_ESTICADO"

        self._log_contador += 1
        if self._log_contador % 5 == 1:
            logging.info(
                f"Ã°Å¸âÅ  MR: RSI={rsi_real:.1f}({rsi_zona}) | Z={zscore:+.2f} | "
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


# region [InicializaÃÂ§ÃÂ£o]

if __name__ == "__main__":
    # PyInstaller console=False deixa sys.stdout/sys.stderr = None. Redireciona
    # para devnull para que print() nao lance excecao no build windowed.
    import sys as _sys_out
    import os as _os_out
    if _sys_out.stdout is None:
        _sys_out.stdout = open(_os_out.devnull, 'w')
    if _sys_out.stderr is None:
        _sys_out.stderr = open(_os_out.devnull, 'w')

    # ---- BLOQUEIO DE INSTÃâNCIA ÃÅ¡NICA: se outra cÃÂ³pia do Monstro V22 jÃÂ¡ estiver rodando, sai na hora ----
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
                "O Monstro V22 jÃÂ¡ estÃÂ¡ em execuÃÂ§ÃÂ£o.\n"
                "Encerre a instÃÂ¢ncia atual antes de iniciar outra.",
                "Monstro Dashboard V22",
                0x40)
        except Exception:
            pass
        _sys.exit(0)

    # Inicializa logging
    setup_logging()

    # ========== REGRAS OPERACIONAIS ATIVAS ==========
    logging.info("Ã¢Å¡â¢Ã¯Â¸Â HorÃÂ¡rio: 09:15-12:30 e 14:30-17:15 | Treino sÃÂ³ com lucro | Aprendizado PRESERVADO entre reinÃÂ­cios")

    # Ã¢Åâ¦ PA3: Reset de memÃÂ³ria foi executado UMA vez na primeira inicializaÃÂ§ÃÂ£o.
    # DESATIVADO permanentemente Ã¢â¬â o aprendizado (h5/keras/experiÃÂªncias) ÃÂ© PRESERVADO
    # entre reinÃÂ­cios. SÃÂ³ reative manualmente chamando resetar_memoria_ia() se quiser zerar tudo.
    # resetar_memoria_ia()  # SÃÂ³ reativar manualmente se necessÃÂ¡rio

    # Reseta e recria scaler global para compatibilidade com 22 features
    resetar_scaler_global()
    forcar_recreacao_scaler()

    # VariÃÂ¡veis globais
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
    gerenciador_bloqueio = None  # SerÃÂ¡ inicializado na thread
    modo_operacional = None      # SerÃÂ¡ inicializado na thread
    confluencia_info_atual = None  # Para sistema de confluÃÂªncia

    # Corrige formato do CSV
    corrigir_csv_historico()

    # Dashboard V2 Ã¢â¬â Registra mÃÂ³dulo principal para acesso aos globals
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
    # Janela Desktop (PyWebView) Ã¢â¬â substitui o join, roda na thread principal
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
        logging.info("RobÃÂ´ encerrado pela janela Desktop.")
    except Exception as e:
        logging.error(f"PyWebView nao disponivel ou falhou: {e}. Rodando sem janela desktop.")
        # Fallback: mantÃÂ©m o join original se pywebview falhar
        monstro_thread_obj.join()


# ======================================
# Fim do arquivo - Monstro das NegociaÃÂ§ÃÂµes v2

# ========== SISTEMA DE VETO SIMPLES E DIRETO (BASEADO NA SUGESTÃÆO DA IA) ==========


def carregar_experiencias_simples():
    """Carrega experiÃÂªncias do JSON de forma simples."""
    if not os.path.exists(EXPERIENCIAS_JSON):
        return []
    try:
        with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def contexto_similar_simples(exp_contexto, contexto_atual):
    """Verifica se contextos sÃÂ£o similares usando critÃÂ©rios simples."""
    # Volatilidade
    vol_atual = "baixa" if contexto_atual.get('volatility', 0) < 50 else "alta"
    vol_exp = "baixa" if exp_contexto.get('volatility', 0) < 50 else "alta"

    # RSI
    rsi_atual = contexto_atual.get('rsi_14', 50)
    rsi_exp = exp_contexto.get('rsi_14', 50)
    rsi_similar = abs(rsi_atual - rsi_exp) <= 20  # ÃÂ±20 pontos

    # Candle type
    candle_atual = contexto_atual.get('candle_type', '')
    candle_exp = exp_contexto.get('candle_type', '')

    return vol_atual == vol_exp and rsi_similar and candle_atual == candle_exp


def calcular_expectativa_simples(experiencias):
    """Calcula expectativa matemÃÂ¡tica simples."""
    if len(experiencias) < 5:  # MÃÂ­nimo de dados
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
    """VETO SIMPLES: Verifica se deve operar baseado no histÃÂ³rico."""
    experiencias = carregar_experiencias_simples()

    # Busca experiÃÂªncias similares com a mesma aÃÂ§ÃÂ£o
    similares = []
    for exp in experiencias:
        if (exp.get('acao') == acao_proposta and
                contexto_similar_simples(exp.get('contexto', {}), contexto_atual)):
            similares.append(exp)

    expectativa = calcular_expectativa_simples(similares)

    if expectativa is None:
        return True, "Sem histÃÂ³rico suficiente"

    if expectativa <= expectativa_minima:
        return False, f"Expectativa negativa: {expectativa:.2f} (similares: {len(similares)})"

    return True, f"Expectativa positiva: {expectativa:.2f} (similares: {len(similares)})"


# ========== INSTÃâNCIAS GLOBAIS DOS NOVOS SISTEMAS ==========
# (bloqueador_contexto e replay_experiencias jÃÂ¡ instanciados acima, apÃÂ³s as classes)
# ========== LIMITE DE INSISTÃÅ NCIA POR CONTEXTO (SUGESTÃÆO DA IA) ==========


class LimitadorInsistencia:
    """Limita operaÃÂ§ÃÂµes no mesmo contexto no mesmo dia."""

    def __init__(self):
        self.operacoes_por_contexto = {}  # {hash_contexto: [timestamps]}
        self.max_operacoes_contexto_dia = 2  # MÃÂ¡ximo 2 operaÃÂ§ÃÂµes por contexto por dia

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

        # Conta operaÃÂ§ÃÂµes hoje neste contexto
        hoje = datetime.now().date()
        ops_hoje = [ts for ts in self.operacoes_por_contexto[hash_ctx]
                    if ts.date() == hoje]

        if len(ops_hoje) >= self.max_operacoes_contexto_dia:
            logging.warning(
                f"Ã°Å¸Å¡Â« LIMITE CONTEXTO: JÃÂ¡ operou {len(ops_hoje)}x hoje em {hash_ctx}")
            return False

        return True

    def registrar_operacao(self, contexto: dict):
        """Registra uma operaÃÂ§ÃÂ£o neste contexto."""
        hash_ctx = self._hash_contexto_dia(contexto)

        if hash_ctx not in self.operacoes_por_contexto:
            self.operacoes_por_contexto[hash_ctx] = []

        self.operacoes_por_contexto[hash_ctx].append(datetime.now())

        # Limpa operaÃÂ§ÃÂµes antigas (mais de 7 dias)
        cutoff = datetime.now() - timedelta(days=7)
        self.operacoes_por_contexto[hash_ctx] = [
            ts for ts in self.operacoes_por_contexto[hash_ctx]
            if ts > cutoff
        ]


# InstÃÂ¢ncia global do limitador
limitador_insistencia = LimitadorInsistencia()

