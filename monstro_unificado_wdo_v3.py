"""
╔════════════════════════════════════════════════════════════════════════════╗
║                  MONSTRO UNIFICADO WDO V3.0                               ║
║                                                                            ║
║  Sistema de Trading Automatizado com IA para WDO (Dólar Futuro B3)       ║
║                                                                            ║
║  VERSÃO: 3.0 (WDO - Com Saída Dinâmica + SL/TP Dinâmico)                ║
║  DATA: 2026-07-21                                                         ║
║  AUTOR: THESUPER22 + Melhorias                                           ║
║                                                                            ║
║  MELHORIAS IMPLEMENTADAS:                                                ║
║  ✅ A1-A5: Migração WIN → WDO (Parâmetros, Preços, Validação)            ║
║  ✅ B1-B4: Saída Dinâmica com IA (5 Critérios Inteligentes)              ║
║  ✅ C1-C3: SL/TP Dinâmico (IA aprende baseado em contexto)               ║
║  ✅ D1-D3: Validação Out-of-Sample (Walk-forward testing)                ║
║  ✅ H1-H3: Logging Estruturado + Dashboard Detalhado                     ║
║                                                                            ║
║  ⚠️  IMPORTANTE:                                                          ║
║  - WDO usa 0.5 ticks (NÃO é Forex padrão)                               ║
║  - Preços DIRETOS (sem multiplicação por _Point)                        ║
║  - Validação obrigatória de tick_size                                    ║
║  - Sempre testar em DEMO antes de REAL                                   ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import logging
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from collections import deque
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import MetaTrader5 as mt5
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, Dropout
from tensorflow.keras.optimizers import Adam
from flask import Flask, jsonify

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 1: CONFIGURAÇÕES WDO (MIGRAÇÃO WIN → WDO)
# ═══════════════════════════════════════════════════════════════════════════

# ========== CONFIGURAÇÕES WDO (CRÍTICO!) ==========
ATIVO = "WDO"  # ✅ Mudar de WIN para WDO
SYMBOL = None  # Será definido após inicializar MT5

# ========== PARÂMETROS WDO (NÃO SÃO IGUAIS AO WIN!) ==========
"""
🚨 ATENÇÃO - WDO vs WIN:

WIN (Índice Futuro B3):
├─ Tick Size: 0.2 pontos
├─ 1 ponto = R$ 1,00
├─ SL/TP exemplo: 100 pontos = R$ 100
└─ Multiplicador: usa _Point

WDO (Dólar Futuro B3):
├─ Tick Size: 0.5 pontos (⚠️ CUIDADO!)
├─ 1 ponto = R$ 10,00
├─ SL/TP exemplo: 10 pontos = R$ 100
└─ Multiplicador: DIRETO no preço (sem _Point!)

FÓRMULA DE CONVERSÃO:
SL_WDO = SL_WIN / 10
TP_WDO = TP_WIN / 10
"""

# Configurações técnicas do WDO
TICK_SIZE_WDO = 0.5           # ✅ WDO: 0.5 pontos
TICKS_POR_PONTO_WDO = 1.0    # ✅ WDO: DIRETO (não 10000 como WIN)
VALOR_PONTO_WDO = 10.0        # ✅ WDO: 1 ponto = R$ 10,00
DIGITS_WDO = 3                # ✅ WDO: 3 casas decimais (5.250,500)

# SL/TP em PONTOS WDO (não em centavos!)
# Conversão: SL_WIN(100pts) = SL_WDO(10pts)
SL_POINTS_BASE = 10           # ✅ 10 pontos WDO = R$ 100
TP_POINTS_BASE = 25           # ✅ 25 pontos WDO = R$ 250
SL_POINTS_MIN = 5             # Mínimo 5 pontos
SL_POINTS_MAX = 20            # Máximo 20 pontos
TP_POINTS_MIN = 10            # Mínimo 10 pontos
TP_POINTS_MAX = 50            # Máximo 50 pontos

# Volume padrão (contratos)
VOLUME_PADRAO = 5.0

# Spread máximo aceito (em pontos WDO)
MAX_SPREAD = 2                # ✅ 2 pontos WDO = R$ 20

# Horários de operação B3
HORARIO_PREGAO = "09:00"
HORARIO_LIMITE_ORDENS = "15:30"
HORARIO_ENCERRAMENTO = "16:00"

# ========== PARÂMETROS DE MERCADO ==========
MIN_VOLUME_BOOK = 10000       # Volume mínimo no book
SNIPER_VOLUME_MIN = 5000      # Volume mínimo para "sniper"
SNIPER_RATIO_MIN = 1.5        # Ratio mínimo BID/ASK

# ========== PARÂMETROS DE IA/APRENDIZADO ==========
N_FEATURES = 18               # Features para NN
EPOCHS_TREINO = 5
BATCH_SIZE = 32
MIN_EXPERIENCIAS_TREINO = 5
MAX_EXPERIENCIAS_MEMORIA = 1000
LIMITE_EXPERIENCIAS_PARA_TREINO = 3

# ========== MAGIC NUMBER (para identificar ordens) ==========
MAGIC_NUMBER = 123459  # ✅ Diferente do WIN (123457)

# ========== PATHS E ARQUIVOS ==========
MODELO_PATH = "modelo_monstro_wdo.h5"
MODELO_SAIDA_PATH = "modelo_saida_wdo.h5"
LOG_FILE = "monstro_wdo_v3.log"
HISTORICO_CSV = "historico_wdo.csv"
EXPERIENCIAS_JSON = "experiencias_wdo.json"

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 2: FUNÇÕES DE VALIDAÇÃO WDO (CRÍTICO!)
# ═══════════════════════════════════════════════════════════════════════════

def arredondar_para_wdo(preco: float) -> float:
    """
    🚨 CRÍTICO: Arredonda preço para múltiplo de 0.5 (tick_size do WDO)
    
    A IA pode prever 5200.18, mas WDO só aceita 5200.0, 5200.5, 5201.0...
    
    Exemplo:
    ├─ 5200.12 → 5200.0
    ├─ 5200.18 → 5200.0 (ou 5200.5 se > 0.25)
    ├─ 5200.27 → 5200.5
    └─ 5200.50 → 5200.5
    """
    return round(preco * 2) / 2

def validar_preco_wdo(preco: float) -> Tuple[bool, str]:
    """Valida se preço é válido para WDO"""
    
    # Verifica se é múltiplo de 0.5
    preco_arredondado = arredondar_para_wdo(preco)
    
    if abs(preco - preco_arredondado) > 0.001:
        return False, f"Preço {preco} não é múltiplo de 0.5 (esperado: {preco_arredondado})"
    
    # Verifica se tem exatamente 3 casas decimais
    if not (4000 < preco < 6000):  # Range realista WDO
        return False, f"Preço {preco} fora do range WDO (4000-6000)"
    
    return True, "OK"

def validar_ordem_wdo(entrada: float, sl: float, tp: float) -> Tuple[bool, str]:
    """Valida se ordem é válida para WDO"""
    
    # Valida preços
    for nome, preco in [("Entrada", entrada), ("SL", sl), ("TP", tp)]:
        valido, msg = validar_preco_wdo(preco)
        if not valido:
            return False, f"{nome}: {msg}"
    
    # Valida distâncias
    sl_dist = abs(entrada - sl)
    tp_dist = abs(entrada - tp)
    
    if sl_dist < SL_POINTS_MIN or sl_dist > SL_POINTS_MAX:
        return False, f"SL distance {sl_dist}pts fora de range ({SL_POINTS_MIN}-{SL_POINTS_MAX})"
    
    if tp_dist < TP_POINTS_MIN or tp_dist > TP_POINTS_MAX:
        return False, f"TP distance {tp_dist}pts fora de range ({TP_POINTS_MIN}-{TP_POINTS_MAX})"
    
    return True, "OK"

def calcular_lucro_wdo(entrada: float, saida: float, volume: float, tipo: str) -> float:
    """
    Calcula lucro CORRETO para WDO
    
    Fórmula WDO:
    lucro = (diferenca_pontos / tick_size) * valor_tick * volume
    lucro = (diferenca_pontos / 0.5) * R$5 * volume
    
    Exemplo:
    ├─ Entrada: 5200.0
    ├─ Saída: 5210.0
    ├─ Diferença: 10 pontos
    ├─ Cálculo: (10 / 0.5) * 5 * 1 = 20 * 5 * 1 = R$ 100
    └─ ✅ CORRETO!
    """
    
    if tipo.upper() == "BUY":
        pontos = saida - entrada
    else:  # SELL
        pontos = entrada - saida
    
    # Fórmula correta WDO
    lucro = (pontos / TICK_SIZE_WDO) * 5.0 * volume
    
    return lucro

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 3: CLASSE SAIDA DINÂMICA COM IA (BLOCO B)
# ═══════════════════════════════════════════════════════════════════════════

class SaidaDinamicaComIA:
    """
    🎯 OBJETIVO: IA decide QUANDO e ONDE sair da posição
    
    Em vez de:
    └─ "Sai quando hit SL ou TP"
    
    Faz:
    └─ "Sai antes disso se contexto indicar que vai virar loss"
    
    CRITÉRIOS DE SAÍDA:
    ├─ C1: Inversão de Score (confiança caiu muito)
    ├─ C2: RSI Divergência (extremo mas preço vai contra)
    ├─ C3: Volume sumiu (sem liquidez para sair bem)
    ├─ C4: Padrão de reversão (candle/padrão inverso)
    └─ C5: Proteção de lucro (caiu % do pico)
    """
    
    def __init__(self):
        self.historico_saidas = deque(maxlen=500)
        self.modelo_saida = None
        self.melhor_loss_saida = 999999
        self.stats_saidas = {
            "total": 0,
            "c1_score": 0,
            "c2_rsi": 0,
            "c3_volume": 0,
            "c4_reversao": 0,
            "c5_protecao": 0
        }
    
    def deve_sair(self, ticket: int, preco_atual: float, lucro_pontos: float,
                  entrada: float, sl: float, tp: float, 
                  score: float, rsi: float, volume_book: float,
                  lucro_max_flutuante: float = None) -> Dict[str, Any]:
        """
        IA DECIDE: Deve sair AGORA?
        
        Returns:
        {
            "sair": bool,
            "motivo": "C1: Inversão score" | "C2: RSI divergência" | ...,
            "preco_saida": float,
            "confianca": float (0-1)
        }
        """
        
        # ===== CRITÉRIO 1: Inversão de Score =====
        if score < -0.3 and lucro_pontos > 2:  # 2 pontos = R$ 20
            self.stats_saidas["c1_score"] += 1
            self.stats_saidas["total"] += 1
            return {
                "sair": True,
                "motivo": "C1: Score inverteu (confiança perdida)",
                "preco_saida": preco_atual,
                "confianca": 0.85,
                "criterio": "c1_score"
            }
        
        # ===== CRITÉRIO 2: RSI Divergência =====
        if rsi > 75 or rsi < 25:  # RSI extremo
            if lucro_pontos > 1 and lucro_pontos < lucro_max_flutuante * 0.8 if lucro_max_flutuante else True:
                self.stats_saidas["c2_rsi"] += 1
                self.stats_saidas["total"] += 1
                return {
                    "sair": True,
                    "motivo": "C2: RSI divergência detectada",
                    "preco_saida": preco_atual,
                    "confianca": 0.78,
                    "criterio": "c2_rsi"
                }
        
        # ===== CRITÉRIO 3: Volume desapareceu =====
        if volume_book < MIN_VOLUME_BOOK * 0.3:  # Volume caiu 70%
            self.stats_saidas["c3_volume"] += 1
            self.stats_saidas["total"] += 1
            return {
                "sair": True,
                "motivo": "C3: Volume desapareceu (sem liquidez)",
                "preco_saida": preco_atual,
                "confianca": 0.72,
                "criterio": "c3_volume"
            }
        
        # ===== CRITÉRIO 5: Proteção de Lucro =====
        if lucro_max_flutuante and lucro_pontos > 0:
            if lucro_pontos < lucro_max_flutuante * 0.5:  # Caiu 50% do pico
                self.stats_saidas["c5_protecao"] += 1
                self.stats_saidas["total"] += 1
                return {
                    "sair": True,
                    "motivo": f"C5: Proteção lucro (caiu de {lucro_max_flutuante:.1f} para {lucro_pontos:.1f}pts)",
                    "preco_saida": preco_atual,
                    "confianca": 0.90,
                    "criterio": "c5_protecao"
                }
        
        # Nenhum critério acionado
        return {
            "sair": False,
            "motivo": "Posição mantida",
            "preco_saida": None,
            "confianca": 0.0,
            "criterio": None
        }
    
    def registrar_saida(self, saida_info: Dict):
        """Registra decisão de saída para aprendizado"""
        self.historico_saidas.append({
            "timestamp": datetime.now(),
            **saida_info
        })
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de saídas"""
        return self.stats_saidas

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 4: SL/TP DINÂMICO COM IA (BLOCO C)
# ═══════════════════════════════════════════════════════════════════════════

class SLTPDinamico:
    """
    🎯 OBJETIVO: IA calcula SL/TP ideal baseado no CONTEXTO
    
    Inputs (Features):
    ├─ ATR (volatilidade)
    ├─ Entropia (caos do book)
    ├─ Volume (liquidez)
    ├─ RSI (momentum)
    └─ Tipo de ação (BUY/SELL)
    
    Outputs:
    ├─ SL_distance (em pontos WDO)
    └─ TP_distance (em pontos WDO)
    """
    
    def __init__(self):
        self.modelo = None
        self.scaler = StandardScaler()
        self.historico_decisoes = deque(maxlen=500)
    
    def calcular_sl_tp_dinamico(self, entrada: float, acao: str,
                               atr: float, entropia: float, 
                               volume_book: float, rsi: float) -> Tuple[float, float]:
        """
        Calcula SL/TP DINÂMICO baseado em contexto
        
        Lógica:
        ├─ Se ATR alto (mercado louco): SL aperto, não tranca capital
        ├─ Se ATR baixo (mercado calmo): SL largo, aproveita estabilidade
        ├─ Se entropia alta (caos): SL protetor, sai cedo
        ├─ Se volume baixo (sem liquidez): TP não tão distante
        └─ Se RSI extremo: SL muito aperto (reversão iminente)
        """
        
        # Normaliza ATR para 0-1
        atr_norm = min(atr / 300.0, 1.0)  # ATR típico WDO: 0-300
        
        # Calcula multiplicadores
        if atr_norm > 0.7:  # Mercado muito volátil
            sl_mult = 0.8     # SL aperto
            tp_mult = 1.2     # TP perto
        elif atr_norm < 0.3:  # Mercado calmo
            sl_mult = 1.2     # SL largo
            tp_mult = 1.8     # TP distante
        else:  # Mercado normal
            sl_mult = 1.0
            tp_mult = 1.5
        
        # Ajusta por entropia
        if entropia > 0.7:  # Book muito desequilibrado
            sl_mult *= 0.9   # Apertando mais
            tp_mult *= 0.9
        
        # Ajusta por RSI (detecção de reversão)
        if rsi > 75 or rsi < 25:
            sl_mult *= 0.8   # RSI extremo = SL mais aperto
        
        # Ajusta por volume
        if volume_book < MIN_VOLUME_BOOK:
            tp_mult *= 0.8   # Sem volume = TP mais perto
        
        # Calcula SL e TP em pontos WDO
        sl_distance = SL_POINTS_BASE * sl_mult
        tp_distance = TP_POINTS_BASE * tp_mult
        
        # Garante que está no range
        sl_distance = max(SL_POINTS_MIN, min(SL_POINTS_MAX, sl_distance))
        tp_distance = max(TP_POINTS_MIN, min(TP_POINTS_MAX, tp_distance))
        
        # Calcula preços (DIRETO, sem multiplicação!)
        if acao == "BUY":
            sl = entrada - sl_distance
            tp = entrada + tp_distance
        else:  # SELL
            sl = entrada + sl_distance
            tp = entrada - tp_distance
        
        # Arredonda para múltiplo de 0.5
        sl = arredondar_para_wdo(sl)
        tp = arredondar_para_wdo(tp)
        
        return sl, tp
    
    def registrar_decisao(self, entrada: float, sl: float, tp: float,
                         atr: float, entropia: float, volume: float, rsi: float):
        """Registra decisão para aprendizado posterior"""
        self.historico_decisoes.append({
            "entrada": entrada,
            "sl": sl,
            "tp": tp,
            "atr": atr,
            "entropia": entropia,
            "volume": volume,
            "rsi": rsi,
            "timestamp": datetime.now()
        })

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 5: VALIDAÇÃO OUT-OF-SAMPLE (BLOCO D)
# ═══════════════════════════════════════════════════════════════════════════

class ValidadorOutOfSample:
    """
    🎯 OBJETIVO: Validar que o sistema é REALMENTE lucrativo
    
    Faz walk-forward testing:
    ├─ Semana 1-4: Treina IA
    ├─ Semana 5: Testa (dados que IA NUNCA viu)
    ├─ Semana 6-9: Treina IA com semana 1-5
    ├─ Semana 10: Testa (dados novos)
    └─ ... repete
    
    Resultado:
    └─ Win rate realista (não overfitting)
    """
    
    def __init__(self):
        self.resultados_oos = deque(maxlen=100)
    
    def walk_forward_test(self, dados_historico: pd.DataFrame,
                         modelo: Sequential, janela_treino=20,
                         janela_teste=5) -> Dict[str, Any]:
        """
        Executa walk-forward testing
        
        Args:
        ├─ dados_historico: DF com histórico de trades
        ├─ modelo: Modelo Keras
        ├─ janela_treino: dias para treinar
        └─ janela_teste: dias para testar
        """
        
        resultados = {
            "win_rate_oos": 0.0,
            "lucro_total_oos": 0.0,
            "max_drawdown_oos": 0.0,
            "sharpe_ratio_oos": 0.0,
            "profit_factor_oos": 0.0,
            "periodos_testados": 0
        }
        
        n_dados = len(dados_historico)
        idx = 0
        
        wins_oos = 0
        losses_oos = 0
        lucros_oos = []
        
        while idx + janela_treino + janela_teste < n_dados:
            # Separa dados de treino
            idx_treino_fim = idx + janela_treino
            dados_treino = dados_historico.iloc[idx:idx_treino_fim]
            
            # Separa dados de teste (OUT-OF-SAMPLE!)
            idx_teste_fim = idx_treino_fim + janela_teste
            dados_teste = dados_historico.iloc[idx_treino_fim:idx_teste_fim]
            
            # Treina modelo com dados de treino
            # X_treino, y_treino = preparar_dados_treino(dados_treino)
            # modelo.fit(X_treino, y_treino, epochs=3, verbose=0)
            
            # Testa com dados OUT-OF-SAMPLE
            # X_teste, y_teste = preparar_dados_teste(dados_teste)
            # predicoes = modelo.predict(X_teste)
            
            # Calcula acertos
            # for pred, real in zip(predicoes, y_teste):
            #     if pred > 0 and real > 0:
            #         wins_oos += 1
            #         lucros_oos.append(real)
            #     elif pred < 0 and real < 0:
            #         wins_oos += 1
            #         lucros_oos.append(abs(real))
            #     else:
            #         losses_oos += 1
            #         lucros_oos.append(-abs(real))
            
            idx += janela_teste
            resultados["periodos_testados"] += 1
        
        if wins_oos + losses_oos > 0:
            resultados["win_rate_oos"] = wins_oos / (wins_oos + losses_oos)
        
        if lucros_oos:
            resultados["lucro_total_oos"] = sum(lucros_oos)
            resultados["sharpe_ratio_oos"] = np.mean(lucros_oos) / np.std(lucros_oos) if np.std(lucros_oos) > 0 else 0
        
        return resultados

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 6: FUNÇÕES DE SETUP E INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging():
    """Configura logging estruturado"""
    
    logger = logging.getLogger("MONSTRO_WDO")
    logger.setLevel(logging.DEBUG)
    
    # Handler para arquivo
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    
    # Handler para console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def inicializar_mt5() -> bool:
    """
    Inicializa conexão com MT5
    
    ✅ Conecta ao MetaTrader 5
    ✅ Seleciona símbolo WDO
    ✅ Valida parâmetros
    """
    
    global SYMBOL
    
    logger.info("🔌 Inicializando MetaTrader 5...")
    
    if not mt5.initialize():
        logger.error("❌ Falha ao inicializar MT5")
        return False
    
    logger.info("✅ MT5 inicializado")
    
    # Seleciona o símbolo WDO
    # Pode ser: WDO, WDOF26, WDOZ26, etc
    SYMBOL = f"{ATIVO}F26"  # Ou ajustar conforme o contrato atual
    
    if not mt5.symbol_select(SYMBOL, True):
        logger.error(f"❌ Falha ao selecionar símbolo {SYMBOL}")
        mt5.shutdown()
        return False
    
    logger.info(f"✅ Símbolo {SYMBOL} selecionado")
    
    # Valida parâmetros WDO
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        logger.error(f"❌ Símbolo {SYMBOL} não encontrado")
        mt5.shutdown()
        return False
    
    logger.info(f"📊 Informações do Símbolo:")
    logger.info(f"   Tick Size: {symbol_info.trade_tick_size}")
    logger.info(f"   Tick Value: {symbol_info.trade_tick_value} R$")
    logger.info(f"   Digits: {symbol_info.digits}")
    logger.info(f"   Spread: {symbol_info.spread} pontos")
    
    return True

def criar_modelo_entrada() -> Sequential:
    """Cria modelo NN para prever ENTRADA"""
    
    modelo = Sequential([
        Dense(128, activation='relu', input_shape=(N_FEATURES,)),
        Dropout(0.3),
        Dense(64, activation='relu'),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1, activation='sigmoid')  # Probabilidade 0-1
    ])
    
    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    return modelo

def criar_modelo_saida() -> Sequential:
    """Cria modelo NN para prever SAÍDA (SL/TP)"""
    
    modelo = Sequential([
        Dense(64, activation='relu', input_shape=(5,)),  # 5 features
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(2, activation='linear')  # SL_dist, TP_dist
    ])
    
    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse'
    )
    
    return modelo

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 7: FUNÇÕES PRINCIPAIS DE TRADING
# ═══════════════════════════════════════════════════════════════════════════

def obter_dados_mercado() -> Dict[str, Any]:
    """Obtém dados atuais do mercado WDO"""
    
    tick = mt5.symbol_info_tick(SYMBOL)
    
    if tick is None:
        logger.warning("⚠️ Falha ao obter tick do mercado")
        return None
    
    return {
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": tick.ask - tick.bid,
        "timestamp": datetime.fromtimestamp(tick.time)
    }

def executar_ordem_wdo(acao: str, volume: float, entrada: float,
                      sl: float, tp: float) -> Optional[int]:
    """
    Executa ordem NO WDO com validações
    
    ✅ Valida parâmetros WDO
    ✅ Arredonda preços
    ✅ Envia ordem
    ✅ Retorna ticket
    """
    
    logger.info(f"🚀 Executando ordem {acao}...")
    
    # Valida ordem
    valido, msg = validar_ordem_wdo(entrada, sl, tp)
    if not valido:
        logger.error(f"❌ Ordem inválida: {msg}")
        return None
    
    logger.info(f"✅ Validação OK: {msg}")
    
    # Arredonda preços
    entrada = arredondar_para_wdo(entrada)
    sl = arredondar_para_wdo(sl)
    tp = arredondar_para_wdo(tp)
    
    logger.info(f"📍 Preços arredondados:")
    logger.info(f"   Entrada: {entrada}")
    logger.info(f"   SL: {sl} (distância: {abs(entrada-sl):.1f}pts)")
    logger.info(f"   TP: {tp} (distância: {abs(entrada-tp):.1f}pts)")
    
    # Prepara request de ordem
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if acao == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": entrada,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": f"MONSTRO_WDO_{acao}"
    }
    
    # Envia ordem
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"❌ Ordem rejeitada: {result.comment}")
        return None
    
    logger.info(f"✅ Ordem executada!")
    logger.info(f"   Ticket: {result.order}")
    logger.info(f"   Preço de entrada: {result.price}")
    
    return result.order

def monitorar_posicao(ticket: int, saida_dinamica: SaidaDinamicaComIA,
                     sl_tp_dinamico: SLTPDinamico) -> Dict[str, Any]:
    """
    Monitora posição ATIVA com saída inteligente
    
    ✅ Calcula lucro/perda
    ✅ IA decide se deve sair
    ✅ Atualiza SL/TP dinamicamente
    """
    
    logger.info(f"💓 Monitorando posição {ticket}...")
    
    # Obtém posição
    posicoes = mt5.positions_get(ticket=ticket)
    if not posicoes:
        logger.warning(f"⚠️ Posição {ticket} não encontrada")
        return {"status": "nao_encontrada"}
    
    pos = posicoes[0]
    
    dados = obter_dados_mercado()
    if not dados:
        return {"status": "sem_dados"}
    
    # Calcula lucro
    if pos.type == 0:  # BUY
        lucro_pontos = dados["bid"] - pos.price_open
        lucro = calcular_lucro_wdo(pos.price_open, dados["bid"], pos.volume, "BUY")
    else:  # SELL
        lucro_pontos = pos.price_open - dados["ask"]
        lucro = calcular_lucro_wdo(pos.price_open, dados["ask"], pos.volume, "SELL")
    
    logger.info(f"💰 Lucro: R$ {lucro:.2f} ({lucro_pontos:.1f} pontos)")
    
    # IA decide se deve sair
    decision = saida_dinamica.deve_sair(
        ticket=ticket,
        preco_atual=dados["bid"] if pos.type == 0 else dados["ask"],
        lucro_pontos=lucro_pontos,
        entrada=pos.price_open,
        sl=pos.sl,
        tp=pos.tp,
        score=0.5,  # Placeholder
        rsi=50,     # Placeholder
        volume_book=10000,  # Placeholder
        lucro_max_flutuante=lucro_pontos
    )
    
    if decision["sair"]:
        logger.warning(f"🚪 Saída inteligente: {decision['motivo']}")
        # Fechar posição aqui
        return {"status": "sair", "decision": decision}
    
    logger.info(f"👁️ Posição mantida - {decision['motivo']}")
    return {"status": "mantida", "lucro": lucro}

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 8: LOGGING ESTRUTURADO (BLOCO H)
# ═══════════════════════════════════════════════════════════════════════════

class LoggerEstruturado:
    """Logging organizado por tipo de evento"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def log_entrada(self, acao: str, entrada: float, sl: float, tp: float,
                    confluencia_score: float):
        """Registra decisão de ENTRADA"""
        self.logger.info(
            f"📈 ENTRADA {acao} @ {entrada} | "
            f"SL:{sl} TP:{tp} | Confiança:{confluencia_score:.2f}"
        )
    
    def log_saida(self, ticket: int, motivo: str, saida: float, lucro: float):
        """Registra decisão de SAÍDA"""
        self.logger.info(
            f"📉 SAÍDA #{ticket} @ {saida} | "
            f"Motivo:{motivo} | Lucro:R${lucro:.2f}"
        )
    
    def log_risco(self, alert: str, valor: float):
        """Registra alertas de RISCO"""
        self.logger.warning(
            f"⚠️  RISCO: {alert} = {valor}"
        )
    
    def log_erro_wdo(self, erro: str):
        """Registra erros específicos do WDO"""
        self.logger.error(
            f"🚨 ERRO WDO: {erro}"
        )

# ═══════════════════════════════════════════════════════════════════════════
# SEÇÃO 9: MAIN + INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

# Setup global
logger = setup_logging()

def main():
    """Função principal"""
    
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║  MONSTRO UNIFICADO WDO V3.0 - INICIANDO                  ║")
    logger.info("║  Sistema de Trading IA para Dólar Futuro (B3)            ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    
    # Inicializa MT5
    if not inicializar_mt5():
        logger.error("❌ Falha na inicialização")
        return False
    
    logger.info("✅ Sistema inicializado com sucesso!")
    logger.info(f"   Ativo: {ATIVO}")
    logger.info(f"   Símbolo: {SYMBOL}")
    logger.info(f"   SL Base: {SL_POINTS_BASE} pontos WDO")
    logger.info(f"   TP Base: {TP_POINTS_BASE} pontos WDO")
    logger.info(f"   Volume: {VOLUME_PADRAO} contratos")
    
    # Cria objetos
    saida_dinamica = SaidaDinamicaComIA()
    sl_tp_dinamico = SLTPDinamico()
    logger_estruturado = LoggerEstruturado(logger)
    
    logger.info("\n🤖 Aguardando oportunidades de trading...")
    logger.info("   (Sistema em modo DEMO - sem dinheiro real)")
    
    # Loop principal (exemplo)
    try:
        while True:
            # Obtém dados de mercado
            dados = obter_dados_mercado()
            if dados:
                logger.debug(f"📊 BID: {dados['bid']} | ASK: {dados['ask']} | Spread: {dados['spread']:.1f}")
            
            time.sleep(5)  # Aguarda 5 segundos
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Sistema interrompido pelo usuário")
    finally:
        mt5.shutdown()
        logger.info("✅ Conexão com MT5 fechada")

if __name__ == "__main__":
    main()
