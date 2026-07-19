# ✅ MONSTRO UNIFICADO - VERSÃO VEREDITO FINAL DO MESTRE
# Foco: Implementação do logging de diagnóstico detalhado para um veredito final.

# region [Imports e Config]
import logging, os, time, threading, random, json, traceback, shutil, pickle, csv
from datetime import datetime, timedelta, time as dtime
from typing import Optional, List, Dict, Any
from functools import lru_cache
import numpy as np
import pandas as pd
from scipy.stats import entropy
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import tensorflow as tf
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, Input
import MetaTrader5 as mt5
from flask import Flask, jsonify
import matplotlib.pyplot as plt
import glob

# ATIVAR EAGER EXECUTION
tf.config.run_functions_eagerly(True)
tf.data.experimental.enable_debug_mode()

# ⚡ OTIMIZAÇÕES DE PERFORMANCE CRÍTICAS
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Silenciar warnings TensorFlow
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Desabilitar oneDNN para acelerar

# ⚡ CACHE GLOBAL DE OBJETOS PESADOS
_cache_modelo = None
_cache_symbol_info = None
_cache_rates = None
_cache_timestamp = 0

def carregar_configuracao(path='config.json'):
    try:
        with open(path, 'r', encoding='utf-8') as f: config = json.load(f)
        print("✅ Configuração externa carregada com sucesso.")
        return config
    except FileNotFoundError: print(f"❌ CRÍTICO: Arquivo de configuração '{path}' não encontrado."); exit()
    except json.JSONDecodeError: print(f"❌ CRÍTICO: Erro ao decodificar o arquivo JSON '{path}'."); exit()
config = carregar_configuracao()
# (Atribuição de constantes)
MT5_PATH = config['geral']['mt5_path']; LOG_FILE = config['geral']['log_file']; MAGIC_NUMBER = config['geral']['magic_number']; DEVIATION = config['geral']['deviation']
SYMBOL_PREFIX = config['contrato']['prefixo']; TICK_SIZE = config['contrato']['tick_size']; TICKS_POR_PONTO = config['contrato']['ticks_por_ponto']; DIGITS_DOLAR = config['contrato']['digits_dolar']; SYMBOL = None
HORARIO_PREGAO = config['horarios']['pregao_inicio']; HORARIO_AFTER = config['horarios']['after_market_fim']; HORARIO_AJUSTE = config['horarios']['ajuste']
HORARIO_AUTO_ENCERRAMENTO = config['horarios']['auto_encerramento']
VOLUME_PADRAO = config['operacional']['volume_padrao']; VOLUME_MINIMO_BOOK = config['operacional']['volume_minimo_book']; PERIODO_ATR = config['operacional']['periodo_atr']
MULTIPLICADOR_SL_ATR = config['operacional']['multiplicador_sl_atr']; MULTIPLICADOR_TP_ATR = config['operacional']['multiplicador_tp_atr']
SL_MAX_POINTS = config['operacional']['sl_max_pontos']; TP_MAX_POINTS = config['operacional']['tp_max_pontos']
MAX_SPREAD = config['risk_management']['max_spread_pontos']; MAX_LOSSES_SEQUENCIA = config['risk_management']['max_losses_sequencia_lado']
CICLOS_BLOQUEIO = config['risk_management']['ciclos_bloqueio_lado']; MIN_LUCRO_DESBLOQUEIO = config['risk_management']['min_lucro_desbloqueio']
MODELO_PATH = config['aprendizado']['modelo_path']; N_FEATURES = config['aprendizado']['n_features']; MIN_EXPERIENCIAS_TREINO = config['aprendizado']['min_exp_para_treino']
GATILHO_TREINO = config['aprendizado']['gatilho_operacoes_para_treino']; MAX_EXPERIENCIAS_MEMORIA = config['aprendizado']['max_exp_memoria']
EPOCHS_TREINO = config['aprendizado']['epochs']; BATCH_SIZE = config['aprendizado']['batch_size']
MULTIPLICADOR_PUNICAO_LOSS = config['aprendizado']['multiplicador_punicao_loss']
# TRAILING STOP CONFIGURAÇÕES
TRAILING_ATIVO = config['trailing_stop']['ativo']; TRAILING_INTERVALO = config['trailing_stop']['intervalo_segundos']
TRAILING_GATILHO = config['trailing_stop']['gatilho_pontos']; TRAILING_DISTANCIA = config['trailing_stop']['distancia_pontos']
FEATURE_COLUMNS = ["bid_qty", "ask_qty", "spread", "volatility", "candle_type", "entropia_book", "rsi_14", "volume_tick", "is_in_trade", "floating_profit", "tempo_em_trade", "delta_bid_ask", "momentum_5", "momentum_reversao", "volume_intensidade"]
TIMEFRAME = mt5.TIMEFRAME_M1
BOOK_FILE_PATH = None

# 🎯 PARÂMETROS SCALPING AGRESSIVO
SCALPING_MODE = {
    "ativo": True,
    "lucro_rapido_pts": 1.5,      # 1.5 pontos = R$ 1.50
    "prejuizo_rapido_pts": 3.0,   # 3.0 pontos = R$ 3.00
    "tempo_max_segundos": 180,    # 3 minutos máximo
    "momentum_reversao": True,    # Detectar reversões por momentum
    "agressividade": 0.85         # 85% de agressividade
}

# 🎯 MODO SNIPER - PRECISÃO CIRÚRGICA OTIMIZADA 
MODO_SNIPER = {
    "ativo": True,                        # Ativar modo sniper
    "score_minimo_entrada": 6.0,          # Score 6.0/10 para entrar (vs 8.5)
    "threshold_ia_minimo": 0.75,          # 75% confiança IA (vs 85%)
    "max_trades_dia": 30,                 # Máximo 30 trades/dia (vs 20)
    "cooldown_entre_trades": 120,         # 2min entre trades (vs 3min)
    "cooldown_apos_loss": 300,            # 5min após loss (vs 10min)
    "cooldown_apos_win": 60,              # 1min após win (vs 2min)
    
    # 💰 TARGETS OTIMIZADOS
    "target_minimo_pts": 2.0,             # R$2 mínimo/trade (vs 3)
    "target_ideal_pts": 6.0,              # R$6 ideal/trade (vs 8)
    "sl_maximo_pts": 3.0,                 # SL máximo 3pts (vs 4pts)
    
    # 📊 CRITÉRIOS MAIS AGRESSIVOS
    "volume_multiplicador": 1.5,          # 1.5x volume médio (vs 2x)
    "atr_minimo": 2.0,                    # ATR >2.0 (vs 2.5)
    "spread_maximo": 1.5,                 # Spread <1.5pt (vs 1pt)
    "momentum_minimo": 1.5,               # Momentum >1.5% (vs 2%)
    
    # 🎯 BREAKOUT DETECTION
    "breakout_ativo": True,               # Detectar rompimentos
    "breakout_volume_min": 3.0,           # 3x volume em breakout
    "breakout_confirmacao": 2,            # 2 ticks confirmação
    "nivels_importantes": True,           # Aguardar níveis importantes
    
    # 🧠 CONFIRMAÇÃO TRIPLA
    "confirmacao_book": True,             # Desequilíbrio book >2:1
    "confirmacao_momentum": True,         # Momentum confirmado
    "confirmacao_volume": True,           # Volume explosivo
    
    # 📈 ESTATÍSTICAS
    "trades_realizados_hoje": 0,
    "ultimo_trade_timestamp": 0,
    "score_medio_entradas": 0.0,
    "taxa_acerto_sniper": 0.0
}

# 🎯 DETECTOR DE NÍVEIS IMPORTANTES (SUPORTE/RESISTÊNCIA)
DETECTOR_NIVEIS = {
    "ativo": True,
    "lookback_periodos": 50,              # Analisar 50 períodos
    "min_toques_nivel": 3,                # Mínimo 3 toques para ser importante
    "tolerancia_pts": 0.5,                # Tolerância 0.5pts para agrupar
    "forca_minima": 0.7,                  # Força mínima do nível
    "niveis_cache": {},                   # Cache dos níveis identificados
    "ultimo_update": 0                    # Timestamp última atualização
}
# endregion

def setup_logging():
    for handler in logging.root.handlers[:]: logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'), logging.StreamHandler()])
    # Silenciar TensorFlow
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
    logging.info("🤖 Monstro (OTIMIZADO) iniciado.")
setup_logging()

# region [Estrutura Principal]

# 🎯 SOLUÇÃO DEFINITIVA PARA TIMESTAMP - GERENCIADOR INTERNO
class GerenciadorTempo:
    def __init__(self):
        self.posicoes_tempo = {}  # {ticket: timestamp_entrada}
        
    def registrar_entrada(self, ticket: int):
        """Registra timestamp interno confiável"""
        self.posicoes_tempo[ticket] = time.time()
        logging.info(f"⏰ Timestamp interno registrado - Ticket: {ticket}")
        
    def calcular_tempo_trade(self, ticket: int) -> float:
        """Calcula tempo de trade usando timestamp interno"""
        if ticket not in self.posicoes_tempo:
            return 0.0
        tempo_decorrido = time.time() - self.posicoes_tempo[ticket]
        return tempo_decorrido / 60.0  # Retorna em minutos
        
    def remover_posicao(self, ticket: int):
        """Remove timestamp ao fechar posição"""
        if ticket in self.posicoes_tempo:
            del self.posicoes_tempo[ticket]
            logging.info(f"⏰ Timestamp removido - Ticket: {ticket}")

# 🧠 ANALISADOR DE MOMENTUM E REVERSÕES
class AnalisadorMomentum:
    def __init__(self):
        self.historico_precos = []
        self.historico_volumes = []
        
    def calcular_momentum_5_periodos(self, precos: List[float]) -> float:
        """Calcula momentum baseado em 5 períodos"""
        if len(precos) < 6:
            return 0.0
        return (precos[-1] - precos[-6]) / precos[-6] * 100
        
    def detectar_reversao_momentum(self, precos: List[float], volumes: List[int]) -> float:
        """Detecta padrões de reversão por momentum"""
        if len(precos) < 3 or len(volumes) < 3:
            return 0.0
            
        # Padrão de divergência: preço sobe, volume diminui (bearish)
        preco_trend = precos[-1] > precos[-3]
        volume_trend = volumes[-1] < volumes[-3]
        
        if preco_trend and volume_trend:  # Divergência bearish
            return -0.7
        elif not preco_trend and not volume_trend:  # Divergência bullish
            return 0.7
        else:
            return 0.0
            
    def calcular_intensidade_volume(self, volumes: List[int]) -> float:
        """Calcula intensidade relativa do volume"""
        if len(volumes) < 10:
            return 1.0
        media_vol = np.mean(volumes[-10:])
        vol_atual = volumes[-1] if volumes else media_vol
        return vol_atual / media_vol if media_vol > 0 else 1.0

# 🎯 ANALISADOR SNIPER - PRECISÃO CIRÚRGICA
class AnalisadorSniper:
    def __init__(self):
        self.niveis_importantes = {}
        self.historico_scores = []
        self.ultima_atualizacao_niveis = 0
        self.trades_dia = 0
        self.reset_diario_feito = False
        
    def reset_diario(self):
        """Reset diário das estatísticas"""
        agora = datetime.now()
        if not self.reset_diario_feito and agora.hour == 9 and agora.minute < 5:
            MODO_SNIPER["trades_realizados_hoje"] = 0
            self.trades_dia = 0
            self.reset_diario_feito = True
            logging.info("🎯 SNIPER: Reset diário executado")
        elif agora.hour > 9:
            self.reset_diario_feito = False
    
    def identificar_niveis_importantes(self, rates_data) -> Dict[str, List[float]]:
        """Identifica níveis de suporte e resistência importantes"""
        try:
            if len(rates_data) < DETECTOR_NIVEIS["lookback_periodos"]:
                return {"suportes": [], "resistencias": []}
            
            # Análise dos últimos X períodos
            highs = [r[2] for r in rates_data[-DETECTOR_NIVEIS["lookback_periodos"]:]]  # high
            lows = [r[3] for r in rates_data[-DETECTOR_NIVEIS["lookback_periodos"]:]]   # low
            
            # Agrupar preços similares (tolerância)
            tolerancia = DETECTOR_NIVEIS["tolerancia_pts"]
            
            # Encontrar resistências (topos)
            resistencias = []
            for i, high in enumerate(highs):
                toques = sum(1 for h in highs if abs(h - high) <= tolerancia)
                if toques >= DETECTOR_NIVEIS["min_toques_nivel"]:
                    resistencias.append(high)
            
            # Encontrar suportes (fundos)
            suportes = []
            for i, low in enumerate(lows):
                toques = sum(1 for l in lows if abs(l - low) <= tolerancia)
                if toques >= DETECTOR_NIVEIS["min_toques_nivel"]:
                    suportes.append(low)
            
            # Remover duplicatas e ordenar
            resistencias = sorted(list(set([round(r, 3) for r in resistencias])))
            suportes = sorted(list(set([round(s, 3) for s in suportes])))
            
            # Verificar se houve mudança significativa nos níveis
            niveis_antigos = self.niveis_importantes
            mudanca_significativa = False
            
            if not niveis_antigos or abs(len(resistencias) - len(niveis_antigos.get("resistencias", []))) > 2 or \
               abs(len(suportes) - len(niveis_antigos.get("suportes", []))) > 2:
                mudanca_significativa = True
                
            self.niveis_importantes = {"suportes": suportes, "resistencias": resistencias}
            self.ultima_atualizacao_niveis = time.time()
            
            # Log apenas se houver mudança significativa ou a cada 60 segundos
            if (resistencias or suportes) and (mudanca_significativa or time.time() % 60 < 1):
                logging.info(f"🎯 NÍVEIS IDENTIFICADOS: {len(resistencias)} resistências, {len(suportes)} suportes")
            
            return self.niveis_importantes
            
        except Exception as e:
            logging.error(f"❌ Erro identificando níveis: {e}")
            return {"suportes": [], "resistencias": []}
    
    def detectar_breakout(self, preco_atual: float, volume_atual: float, volume_medio: float, contexto: dict) -> Dict[str, Any]:
        """Detecta breakouts de níveis importantes"""
        try:
            if not MODO_SNIPER["breakout_ativo"]:
                return {"breakout": False, "direcao": None, "forca": 0.0}
            
            if not self.niveis_importantes:
                return {"breakout": False, "direcao": None, "forca": 0.0}
            
            suportes = self.niveis_importantes.get("suportes", [])
            resistencias = self.niveis_importantes.get("resistencias", [])
            
            # Volume suficiente para breakout?
            volume_ratio = volume_atual / volume_medio if volume_medio > 0 else 1.0
            if volume_ratio < MODO_SNIPER["breakout_volume_min"]:
                return {"breakout": False, "direcao": None, "forca": 0.0}
            
            # Verificar breakout de resistência (alta)
            for resistencia in resistencias:
                if preco_atual > resistencia + 0.5:  # Rompeu com folga
                    forca_breakout = min(volume_ratio / 3.0, 1.0)  # Força baseada no volume
                    logging.info(f"🚀 BREAKOUT ALTA detectado! Preço:{preco_atual:.3f} > Resistência:{resistencia:.3f} | Vol:{volume_ratio:.1f}x")
                    return {"breakout": True, "direcao": "ALTA", "forca": forca_breakout, "nivel": resistencia}
            
            # Verificar breakout de suporte (baixa)
            for suporte in suportes:
                if preco_atual < suporte - 0.5:  # Rompeu com folga
                    forca_breakout = min(volume_ratio / 3.0, 1.0)
                    logging.info(f"🔻 BREAKOUT BAIXA detectado! Preço:{preco_atual:.3f} < Suporte:{suporte:.3f} | Vol:{volume_ratio:.1f}x")
                    return {"breakout": True, "direcao": "BAIXA", "forca": forca_breakout, "nivel": suporte}
            
            return {"breakout": False, "direcao": None, "forca": 0.0}
            
        except Exception as e:
            logging.error(f"❌ Erro detectando breakout: {e}")
            return {"breakout": False, "direcao": None, "forca": 0.0}
    
    def calcular_score_setup(self, contexto: dict, breakout_info: dict, prob_ia: float) -> float:
        """Calcula score de qualidade do setup (0-10)"""
        try:
            score = 0.0
            detalhes = []
            
            # 1. SCORE IA (0-3 pontos) - MAIS FLEXÍVEL
            if prob_ia >= 0.85:
                score += 3.0
                detalhes.append("IA:Excelente(3.0)")
            elif prob_ia >= 0.75:
                score += 2.5
                detalhes.append("IA:Ótimo(2.5)")
            elif prob_ia >= 0.65:
                score += 2.0
                detalhes.append("IA:Bom(2.0)")
            elif prob_ia >= 0.50:
                score += 1.5
                detalhes.append("IA:Aceitável(1.5)")
            else:
                score += prob_ia * 3  # Mais generoso para IAs baixas
                detalhes.append(f"IA:Baixo({prob_ia*3:.1f})")
            
            # 2. VOLUME INTENSIDADE (0-2 pontos) - MAIS GENEROSO
            volume_intensidade = contexto.get('volume_intensidade', 1.0)
            if volume_intensidade >= 2.5:
                score += 2.0
                detalhes.append("Vol:Explosivo(2.0)")
            elif volume_intensidade >= 1.8:
                score += 1.5
                detalhes.append("Vol:Alto(1.5)")
            elif volume_intensidade >= 1.3:
                score += 1.0
                detalhes.append("Vol:Bom(1.0)")
            elif volume_intensidade >= 1.0:
                score += 0.7
                detalhes.append("Vol:Normal(0.7)")
            else:
                score += volume_intensidade * 0.7
                detalhes.append(f"Vol:Baixo({volume_intensidade*0.7:.1f})")
            
            # 3. MOMENTUM (0-2 pontos) - MAIS TOLERANTE
            momentum = abs(contexto.get('momentum_5', 0.0))
            if momentum >= 2.5:
                score += 2.0
                detalhes.append("Mom:Forte(2.0)")
            elif momentum >= 1.5:
                score += 1.5
                detalhes.append("Mom:Bom(1.5)")
            elif momentum >= 0.8:
                score += 1.0
                detalhes.append("Mom:Médio(1.0)")
            elif momentum >= 0.3:
                score += 0.7
                detalhes.append("Mom:Leve(0.7)")
            else:
                score += momentum * 1.0
                detalhes.append(f"Mom:Mínimo({momentum*1.0:.1f})")
            
            # 4. BREAKOUT BONUS (0-2 pontos)
            if breakout_info.get("breakout", False):
                forca = breakout_info.get("forca", 0.0)
                bonus_breakout = forca * 2.0
                score += bonus_breakout
                detalhes.append(f"Breakout:Sim({bonus_breakout:.1f})")
            else:
                detalhes.append("Breakout:Não(0.0)")
            
            # 5. QUALIDADE DO SPREAD (0-1 ponto)
            spread = contexto.get('spread', 5.0)
            if spread <= 1.0:
                score += 1.0
                detalhes.append("Spread:Ótimo(1.0)")
            elif spread <= 2.0:
                score += 0.5
                detalhes.append("Spread:Bom(0.5)")
            else:
                detalhes.append("Spread:Ruim(0.0)")
            
            # Limitando score máximo em 10
            score = min(score, 10.0)
            
            # Log do score calculado
            if score >= MODO_SNIPER["score_minimo_entrada"]:
                logging.info(f"🎯 SCORE SETUP: {score:.1f}/10 ✅ | {' | '.join(detalhes[:3])}")
            else:
                if datetime.now().second % 30 == 0:  # Log menos frequente para scores baixos
                    logging.info(f"🎯 SCORE SETUP: {score:.1f}/10 ❌ | {detalhes[0] if detalhes else 'N/A'}")
            
            return score
            
        except Exception as e:
            logging.error(f"❌ Erro calculando score: {e}")
            return 0.0
    
    def verificar_cooldown(self, resultado_ultimo_trade: Optional[float] = None) -> bool:
        """Verifica se está no período de cooldown"""
        agora = time.time()
        
        # Registrar resultado do último trade se fornecido
        if resultado_ultimo_trade is not None:
            MODO_SNIPER["ultimo_trade_timestamp"] = agora
            if resultado_ultimo_trade > 0:
                logging.info(f"🎯 SNIPER WIN: +R${resultado_ultimo_trade:.2f} | Cooldown: {MODO_SNIPER['cooldown_apos_win']}s")
            else:
                logging.warning(f"🎯 SNIPER LOSS: R${resultado_ultimo_trade:.2f} | Cooldown: {MODO_SNIPER['cooldown_apos_loss']}s")
        
        # Verificar limite diário
        if MODO_SNIPER["trades_realizados_hoje"] >= MODO_SNIPER["max_trades_dia"]:
            if datetime.now().second % 60 == 0:  # Log a cada minuto
                logging.info(f"🎯 SNIPER: Limite diário atingido ({MODO_SNIPER['max_trades_dia']} trades)")
            return False
        
        # Verificar cooldown temporal
        if MODO_SNIPER["ultimo_trade_timestamp"] > 0:
            tempo_desde_ultimo = agora - MODO_SNIPER["ultimo_trade_timestamp"]
            cooldown_necessario = MODO_SNIPER["cooldown_entre_trades"]  # Padrão
            
            if tempo_desde_ultimo < cooldown_necessario:
                tempo_restante = cooldown_necessario - tempo_desde_ultimo
                if int(tempo_restante) % 30 == 0:  # Log a cada 30s
                    logging.info(f"🎯 SNIPER COOLDOWN: {tempo_restante:.0f}s restantes")
                return False
        
        return True
    
    def analisar_confirmacao_tripla(self, contexto: dict, prob_ia: float) -> Dict[str, Any]:
        """Análise de confirmação tripla: Book + IA + Momentum"""
        confirmacoes = []
        score_total = 0.0
        
        try:
            # 1. CONFIRMAÇÃO BOOK (Desequilíbrio)
            bid_qty = contexto.get('bid_qty', 0)
            ask_qty = contexto.get('ask_qty', 0)
            total_book = bid_qty + ask_qty
            
            if total_book > 0:
                ratio_bid = bid_qty / total_book
                ratio_ask = ask_qty / total_book
                
                if ratio_bid >= 0.65:  # 65% BID = Pressão de alta
                    confirmacoes.append("Book:Alta")
                    score_total += 2.0
                elif ratio_ask >= 0.65:  # 65% ASK = Pressão de baixa
                    confirmacoes.append("Book:Baixa")
                    score_total += 2.0
                else:
                    confirmacoes.append("Book:Neutro")
                    score_total += 0.5
            
            # 2. CONFIRMAÇÃO IA (Confiança)
            if prob_ia >= 0.85:
                confirmacoes.append("IA:MuitoAlta" if prob_ia >= 0.9 else "IA:Alta")
                score_total += 3.0
            elif prob_ia <= 0.15:
                confirmacoes.append("IA:MuitoBaixa" if prob_ia <= 0.1 else "IA:Baixa")
                score_total += 3.0
            else:
                confirmacoes.append("IA:Indefinida")
                score_total += 0.5
            
            # 3. CONFIRMAÇÃO MOMENTUM
            momentum = contexto.get('momentum_5', 0.0)
            if abs(momentum) >= 2.5:
                direcao = "Alta" if momentum > 0 else "Baixa"
                confirmacoes.append(f"Mom:{direcao}")
                score_total += 2.0
            elif abs(momentum) >= 1.5:
                direcao = "Alta" if momentum > 0 else "Baixa"
                confirmacoes.append(f"Mom:{direcao}Fraco")
                score_total += 1.0
            else:
                confirmacoes.append("Mom:Neutro")
                score_total += 0.0
            
            # Resultado final
            confirmacao_ok = len([c for c in confirmacoes if not ("Neutro" in c or "Indefinida" in c)]) >= 2
            
            resultado = {
                "confirmado": confirmacao_ok,
                "score": score_total,
                "detalhes": confirmacoes,
                "resumo": " | ".join(confirmacoes)
            }
            
            if confirmacao_ok:
                logging.info(f"✅ CONFIRMAÇÃO TRIPLA: {resultado['resumo']} | Score: {score_total:.1f}")
            
            return resultado
            
        except Exception as e:
            logging.error(f"❌ Erro na confirmação tripla: {e}")
            return {"confirmado": False, "score": 0.0, "detalhes": [], "resumo": "Erro"}

def ler_book_csv() -> Optional[Dict[str, List[int]]]:
    global BOOK_FILE_PATH
    if not BOOK_FILE_PATH or not os.path.exists(BOOK_FILE_PATH): return None
    try:
        if os.path.getsize(BOOK_FILE_PATH) < 4: return None
        with open(BOOK_FILE_PATH, 'r', encoding='utf-16') as f:
            lines = f.readlines()
        if len(lines) < 2: return None
        bids_str = lines[0].strip(); asks_str = lines[1].strip()
        bids = [int(v) for v in bids_str.split(',') if v] if bids_str else []
        asks = [int(v) for v in asks_str.split(',') if v] if asks_str else []
        return {"bids": bids, "asks": asks}
    except Exception: return None

# [FUNÇÃO FINAL COM SOLUÇÕES DEFINITIVAS + MOMENTUM + TIMESTAMP RESOLVIDO]
def obter_dados_mercado(symbol: str, posicao_ativa=None, gerenciador_tempo=None) -> Optional[Dict[str, Any]]:
    # ⚡ OTIMIZAÇÃO: Log apenas quando necessário
    log_time = datetime.now().second % 10 == 0  # Reduzido de 5 para 10 segundos
    try:
        book_data = ler_book_csv()
        if not book_data or not book_data.get('bids') or not book_data.get('asks'):
            if log_time: logging.warning("⚠️ Book vazio ou inválido.")
            return None

        total_bid_volume = sum(book_data['bids'])
        total_ask_volume = sum(book_data['asks'])
        total_volume = total_bid_volume + total_ask_volume
        
        if total_volume < VOLUME_MINIMO_BOOK:
            if log_time: logging.warning(f"❌ Liquidez insuficiente: {total_volume} < {VOLUME_MINIMO_BOOK}")
            return None

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            if log_time: logging.warning("❌ Tick NULO.")
            return None

        spread_pontos = round(tick.ask - tick.bid, 1)
        if spread_pontos > MAX_SPREAD:
            if log_time: logging.warning(f"❌ Spread muito alto: {spread_pontos} pts")
            return None

        rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, 100)
        if rates is None or len(rates) < PERIODO_ATR + 1:
            if log_time: logging.warning("❌ Dados de rates insuficientes.")
            return None
        
        df_rates = pd.DataFrame(rates, columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
        atr = calcular_atr(df_rates['high'].tolist(), df_rates['low'].tolist(), df_rates['close'].tolist(), PERIODO_ATR)
        last_candle = rates[-1]
        
        # 🎯 CÁLCULO DE LUCRO REAL EM TEMPO REAL + TIMESTAMP RESOLVIDO
        lucro_atual_real = 0.0
        tempo_em_trade = 0.0
        is_in_trade = 0
        
        if posicao_ativa and gerenciador_tempo:
            is_in_trade = 1
            # Calcular lucro real baseado na posição atual
            preco_atual = tick.bid if posicao_ativa.type == mt5.POSITION_TYPE_BUY else tick.ask
            
            # 🎯 CORREÇÃO DEFINITIVA: 1 ponto = 1000 ticks no mini dólar
            if posicao_ativa.type == mt5.POSITION_TYPE_BUY:
                diferenca_ticks = (preco_atual - posicao_ativa.price_open) * TICKS_POR_PONTO
            else:
                diferenca_ticks = (posicao_ativa.price_open - preco_atual) * TICKS_POR_PONTO
                
            # Lucro em pontos reais
            lucro_pontos = diferenca_ticks / TICKS_POR_PONTO
            # Lucro em R$ (1 ponto = R$ 1.00 para mini dólar)
            lucro_atual_real = lucro_pontos * posicao_ativa.volume
            
            # 🎯 SOLUÇÃO DEFINITIVA: TEMPO INTERNO CONFIÁVEL
            tempo_em_trade = gerenciador_tempo.calcular_tempo_trade(posicao_ativa.ticket)
            
            # ⚡ LOG P&L OTIMIZADO - MENOS FREQUENTE
            if datetime.now().second % 6 == 0:
                status_lucro = "💰" if lucro_atual_real > 0 else "🔻" if lucro_atual_real < 0 else "➖"
                intensidade = ""
                if abs(lucro_atual_real) >= 20: 
                    intensidade = "🚨" if lucro_atual_real < 0 else "🎯"
                elif abs(lucro_atual_real) >= 10: 
                    intensidade = "⚠️" if lucro_atual_real < 0 else "✅"
                
                logging.info(f"{intensidade}{status_lucro} P&L: R${lucro_atual_real:.2f} | {lucro_pontos:.1f}pts | ⏰{tempo_em_trade:.1f}min")

        # 🧠 ANÁLISE DE MOMENTUM E REVERSÃO
        analisador = AnalisadorMomentum()
        precos = df_rates['close'].tolist()
        volumes = df_rates['tick_volume'].tolist()
        
        momentum_5 = analisador.calcular_momentum_5_periodos(precos)
        momentum_reversao = analisador.detectar_reversao_momentum(precos, volumes)
        volume_intensidade = analisador.calcular_intensidade_volume(volumes)

        # Log de mercado otimizado com momentum
        if log_time: 
            logging.info(f"📊 Mercado: Liq:{total_volume} | Spread:{spread_pontos}pts | ATR:{atr:.2f} | Mom:{momentum_5:.1f}%")
        
        return {
            "bid_qty": total_bid_volume, 
            "ask_qty": total_ask_volume, 
            "spread": spread_pontos, 
            "volatility": atr, 
            "candle_type": obter_nome_vela(last_candle[1], last_candle[4], last_candle[2], last_candle[3]), 
            "entropia_book": calcular_entropia(book_data['bids'] + book_data['asks']), 
            "rsi_14": calcular_rsi(df_rates['close'].tolist(), 14), 
            "volume_tick": tick.volume, 
            "is_in_trade": is_in_trade, 
            "floating_profit": lucro_atual_real,
            "tempo_em_trade": tempo_em_trade, 
            "atr": atr, 
            "delta_bid_ask": total_bid_volume - total_ask_volume,
            # 🧠 NOVAS FEATURES DE MOMENTUM
            "momentum_5": momentum_5,
            "momentum_reversao": momentum_reversao,
            "volume_intensidade": volume_intensidade
        }
    except Exception as e:
        logging.error(f"Erro em obter_dados_mercado: {e}"); return None

# (O resto do código é idêntico)
class GerenciadorBloqueio:
    def __init__(self): self.bloqueio_lado = {"BUY": 0, "SELL": 0}; self.losses_sequencia = {"BUY": 0, "SELL": 0}
    def registrar_operacao(self, acao, lucro):
        if acao not in ["BUY", "SELL"]: return
        if lucro < 0:
            self.losses_sequencia[acao] += 1; outro_lado = "SELL" if acao == "BUY" else "BUY"; self.losses_sequencia[outro_lado] = 0
            if self.losses_sequencia[acao] >= MAX_LOSSES_SEQUENCIA: self.bloquear_lado(acao)
        else:
            self.losses_sequencia[acao] = 0
            if lucro >= MIN_LUCRO_DESBLOQUEIO and self.bloqueio_lado.get(acao, 0) > 0: self.desbloquear_lado(acao)
    def bloquear_lado(self, lado): self.bloqueio_lado[lado] = CICLOS_BLOQUEIO; logging.warning(f"🚫 LADO {lado} BLOQUEADO.")
    def desbloquear_lado(self, lado): self.bloqueio_lado[lado] = 0; logging.info(f"✅ Lado {lado} desbloqueado.")
    def verificar_bloqueio(self, acao):
        if self.bloqueio_lado.get(acao, 0) > 0: self.bloqueio_lado[acao] -= 1; logging.warning(f"Ação {acao} bloqueada."); return True
        return False
class MemoriaExperiencias:
    def __init__(self, max_size=MAX_EXPERIENCIAS_MEMORIA): self.max_size = max_size; self.memoria = []
    def adicionar(self, exp):
        if len(self.memoria) >= self.max_size: self.memoria.pop(0)
        self.memoria.append(exp)
    def obter_batch(self, size): return random.sample(self.memoria, min(len(self.memoria), size))
    def __len__(self): return len(self.memoria)

class GerenciadorTrailingStop:
    def __init__(self):
        self.trailing_data = {}  # {ticket: {'melhor_preco': float, 'ultimo_update': datetime}}
        self.ultimo_check = datetime.now()
        logging.info(f"🎯 Trailing Stop inicializado - Ativo: {TRAILING_ATIVO}, Gatilho: {TRAILING_GATILHO}pts, Distancia: {TRAILING_DISTANCIA}pts")
    
    def processar_posicao(self, posicao, symbol_info):
        if not TRAILING_ATIVO: return False
        agora = datetime.now()
        if (agora - self.ultimo_check).seconds < TRAILING_INTERVALO: return False
        self.ultimo_check = agora
        
        ticket = posicao.ticket
        preco_atual = posicao.price_current
        
        # CORREÇÃO MINI DÓLAR: 1000 ticks = 1 ponto
        ponto_real = TICKS_POR_PONTO * symbol_info.point  # 1000 * 0.001 = 1.0 ponto real
        lucro_pontos = (preco_atual - posicao.price_open) / ponto_real
        
        if posicao.type == mt5.POSITION_TYPE_SELL:
            lucro_pontos = -lucro_pontos
        
        if lucro_pontos < TRAILING_GATILHO: return False
        
        if ticket not in self.trailing_data:
            self.trailing_data[ticket] = {'melhor_preco': preco_atual, 'ultimo_update': agora}
            logging.info(f"🎯 Trailing iniciado - Ticket: {ticket}, Lucro: {lucro_pontos:.1f}pts reais")
            return False
        
        # Atualizar melhor preço
        melhor_anterior = self.trailing_data[ticket]['melhor_preco']
        if (posicao.type == mt5.POSITION_TYPE_BUY and preco_atual > melhor_anterior) or \
           (posicao.type == mt5.POSITION_TYPE_SELL and preco_atual < melhor_anterior):
            self.trailing_data[ticket]['melhor_preco'] = preco_atual
            self.trailing_data[ticket]['ultimo_update'] = agora
            
            # Calcular novo SL - DISTÂNCIA EM PONTOS REAIS
            distancia_real = TRAILING_DISTANCIA * ponto_real  # 1.0 * 1000 ticks
            if posicao.type == mt5.POSITION_TYPE_BUY:
                novo_sl = preco_atual - distancia_real
            else:
                novo_sl = preco_atual + distancia_real
            
            # Garantir que respeita tick_size e distância mínima
            novo_sl = arredondar_preco(novo_sl)
            stops_level = symbol_info.trade_stops_level * symbol_info.point
            min_dist = max(stops_level, 2 * ponto_real)  # Mínimo 2 pontos reais
            
            if posicao.type == mt5.POSITION_TYPE_BUY:
                if (preco_atual - novo_sl) < min_dist:
                    novo_sl = preco_atual - min_dist
                    novo_sl = arredondar_preco(novo_sl)
            else:
                if (novo_sl - preco_atual) < min_dist:
                    novo_sl = preco_atual + min_dist  
                    novo_sl = arredondar_preco(novo_sl)
            
            # Atualizar SL se for melhor
            if (posicao.type == mt5.POSITION_TYPE_BUY and novo_sl > posicao.sl) or \
               (posicao.type == mt5.POSITION_TYPE_SELL and novo_sl < posicao.sl):
                
                logging.info(f"🎯 Tentando SL: Atual={preco_atual:.3f} | Novo={novo_sl:.3f} | Dist={(abs(preco_atual-novo_sl)/ponto_real):.1f}pts")
                
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": posicao.symbol,
                    "position": ticket,
                    "sl": novo_sl,
                    "tp": posicao.tp,
                    "magic": MAGIC_NUMBER
                }
                resultado = mt5.order_send(request)
                if resultado and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    logging.info(f"🎯 Trailing atualizado - Ticket: {ticket}, Novo SL: {novo_sl:.3f}")
                    return True
                else:
                    erro_desc = mt5.last_error()
                    logging.warning(f"❌ Falha trailing - Ticket: {ticket} | Erro: {resultado.retcode} | {erro_desc}")
        return False
    
    def limpar_posicao(self, ticket):
        if ticket in self.trailing_data:
            del self.trailing_data[ticket]
            logging.info(f"🎯 Trailing removido - Ticket: {ticket}")
@lru_cache(maxsize=1)
def get_cached_symbol_info(s: str) -> Optional[Any]: return mt5.symbol_info(s)
def get_front_month_symbol_dynamic(prefix=SYMBOL_PREFIX) -> str:
    symbols = mt5.symbols_get()
    if not symbols: logging.error("❌ Não foi possível obter símbolos."); return f"{prefix}$"
    now_ts = datetime.now().timestamp()
    candidates = [s for s in symbols if s.name.startswith(prefix) and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL and getattr(s, 'expiration_time', 0) > now_ts]
    if not candidates: logging.error(f"❌ Nenhum contrato futuro ativo."); return f"{prefix}$"
    front_month = min(candidates, key=lambda s: s.expiration_time)
    logging.info(f"✅ Contrato dinâmico: {front_month.name}"); return front_month.name
def calcular_entropia(volumes: List[int]) -> float:
    return entropy(volumes) if volumes else 0.0
def calcular_atr(highs, lows, closes, period):
    if len(highs) < period + 1: return 0.0
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(closes))]; return np.mean(trs[-period:]) if trs else 0.0
def obter_nome_vela(o, c, h, l):
    body, total_range = abs(c - o), h - l
    if total_range == 0: return "doji"
    is_bullish = c > o
    if body / total_range < 0.1: return "doji"
    if body / total_range > 0.9: return "marubozu_alta" if is_bullish else "marubozu_baixa"
    return "alta" if is_bullish else "baixa"
def calcular_rsi(prices, period=14):
    if len(prices) < period + 1: return 50.0
    deltas = np.diff(prices); gains = deltas[deltas >= 0]; losses = -deltas[deltas < 0]
    avg_gain = np.mean(gains[-period:]) if len(gains) >= period else 0; avg_loss = np.mean(losses[-period:]) if len(losses) >= period else 1
    if avg_loss == 0: return 100.0
    return 100 - (100 / (1 + (avg_gain / avg_loss)))
def arredondar_preco(p: float) -> float: 
    return round(p / TICK_SIZE) * TICK_SIZE if TICK_SIZE > 0 else p

def formatar_preco_dolar(preco: float) -> str:
    return f"{preco:.{DIGITS_DOLAR}f}"
def executar_ordem(action, symbol, atr):
    if action not in ["BUY", "SELL"]: return None
    tipo_ordem, tick, symbol_info = (mt5.ORDER_TYPE_BUY, mt5.symbol_info_tick(symbol), get_cached_symbol_info(symbol)) if action == 'BUY' else (mt5.ORDER_TYPE_SELL, mt5.symbol_info_tick(symbol), get_cached_symbol_info(symbol))
    if not tick or not symbol_info: return None
    preco_entrada = tick.ask if action == 'BUY' else tick.bid
    # Converte pontos REAIS para ticks MT5 - MINI DÓLAR: 1000 ticks = 1 ponto
    ponto_real = TICKS_POR_PONTO * symbol_info.point  # 1000 * 0.001 = 1.0 ponto real
    sl_min_dist = 2 * ponto_real  # 2 pontos reais mínimos
    sl_dist = max(sl_min_dist, min(atr * MULTIPLICADOR_SL_ATR, SL_MAX_POINTS * ponto_real))

    # TP EVOLUTIVO: Se multiplicador for 0, desativa TP completamente
    if MULTIPLICADOR_TP_ATR > 0 and TP_MAX_POINTS > 0:
        tp_min_dist = 1 * ponto_real  # 1 ponto real mínimo
        tp_dist = max(tp_min_dist, min(atr * MULTIPLICADOR_TP_ATR, TP_MAX_POINTS * ponto_real))
        tp_preco = (preco_entrada + tp_dist) if action == 'BUY' else (preco_entrada - tp_dist)
    else:
        tp_preco = 0.0  # TP DESATIVADO - IA decide quando sair!

    sl_preco = (preco_entrada - sl_dist) if action == 'BUY' else (preco_entrada + sl_dist)
    
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": float(VOLUME_PADRAO), "type": tipo_ordem, "price": preco_entrada, "sl": arredondar_preco(sl_preco), "tp": tp_preco, "deviation": DEVIATION, "magic": MAGIC_NUMBER, "comment": f"Monstro (Evolução IA) {action}", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_RETURN}
    resultado = mt5.order_send(request)
    if resultado is None:
        logging.error(f"❌ ERRO: mt5.order_send retornou None. Verifique a conexão com o MetaTrader 5.")
        return None

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"✅ ORDEM ENVIADA: {action} {VOLUME_PADRAO} {symbol} @ {preco_entrada:.3f} | Ticket: {resultado.order}")
        return resultado.order
    else:
        desc = mt5.last_error()
        logging.error(f"❌ ERRO AO ENVIAR ORDEM {action}: retcode={resultado.retcode}, descrição={desc}")
        return None
def obter_lucro_ultima_ordem(ticket):
    time.sleep(1.5); deals = mt5.history_deals_get(datetime.now() - timedelta(days=1), datetime.now())
    if not deals: return 0.0
    lucro = sum(d.profit + d.commission + d.swap for d in deals if d.position_id == ticket and d.entry == mt5.DEAL_ENTRY_OUT)
    if lucro != 0.0: logging.info(f"💰 Lucro apurado Ticket {ticket}: R$ {lucro:.2f}")
    else: logging.warning(f"Nenhum deal de SAÍDA lucrativo/perdedor encontrado para ticket {ticket}.")
    return lucro
def criar_modelo_neural(n_features):
    model = Sequential([Input(shape=(n_features,)), Dense(128, activation='relu'), Dropout(0.3), Dense(64, activation='relu'), Dropout(0.2), Dense(32, activation='relu'), Dense(1, activation='sigmoid')])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy']); return model

# 🎯 VERSIONAMENTO DE FEATURES E METADADOS
VERSAO_FEATURES = "2.0"  # Versão atual das features
FEATURES_METADATA = {
    "versao": VERSAO_FEATURES,
    "total_features": N_FEATURES,
    "features_list": FEATURE_COLUMNS,
    "data_criacao": None,
    "data_ultima_migracao": None,
    "historico_migracoes": []
}

def salvar_metadados_modelo(versao, total_features, features_list):
    """
    Salva metadados do modelo para controle de versão
    """
    metadata_path = MODELO_PATH.replace('.h5', '_metadata.json')
    try:
        metadata = {
            "versao": versao,
            "total_features": total_features,
            "features_list": features_list,
            "data_criacao": datetime.now().isoformat(),
            "data_ultima_migracao": datetime.now().isoformat() if versao != "1.0" else None,
            "historico_migracoes": []
        }
        
        # Se já existe metadata, preservar histórico
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_antiga = json.load(f)
                metadata["historico_migracoes"] = metadata_antiga.get("historico_migracoes", [])
                metadata["data_criacao"] = metadata_antiga.get("data_criacao", metadata["data_criacao"])
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        logging.info(f"✅ Metadados salvos: v{versao} com {total_features} features")
        
    except Exception as e:
        logging.error(f"❌ Erro ao salvar metadados: {e}")

def carregar_metadados_modelo():
    """
    Carrega metadados do modelo existente
    """
    metadata_path = MODELO_PATH.replace('.h5', '_metadata.json')
    try:
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"❌ Erro ao carregar metadados: {e}")
    return None

def salvar_modelo(modelo, fazer_backup=True, motivo="treino"):
    """
    Salvar modelo com metadados e backup inteligente
    """
    try:
        # 🎯 BACKUP INTELIGENTE - Apenas quando necessário
        if os.path.exists(MODELO_PATH) and fazer_backup:
            # Verificar se é necessário fazer backup
            if motivo == "migracao" or motivo == "novo":
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{MODELO_PATH}.backup_{motivo}_{timestamp}"
                shutil.copy(MODELO_PATH, backup_path)
                logging.info(f"📦 Backup {motivo} salvo: {backup_path}")
            elif motivo == "treino":
                # Para treino, só fazer backup se for primeira vez do dia
                agora = datetime.now()
                timestamp_hoje = agora.strftime("%Y%m%d")
                backup_treino_hoje = f"{MODELO_PATH}.backup_treino_{timestamp_hoje}"
                
                if not os.path.exists(backup_treino_hoje):
                    shutil.copy(MODELO_PATH, backup_treino_hoje)
                    logging.info(f"📦 Backup diário treino: {backup_treino_hoje}")
                # Senão, não faz backup desnecessário
            
        # Salvar modelo
        modelo.save(MODELO_PATH)
        
        # 🎯 SALVAR METADADOS INTELIGENTES
        salvar_metadados_modelo(VERSAO_FEATURES, N_FEATURES, FEATURE_COLUMNS)
        
        if motivo == "treino":
            logging.info(f"✅ Modelo atualizado pós-treino (v{VERSAO_FEATURES})")
        else:
            logging.info(f"✅ Novo modelo salvo com {N_FEATURES} features (v{VERSAO_FEATURES})")
        
    except Exception as e: 
        logging.error(f"❌ Erro ao salvar modelo: {e}")

def log_status_migracao(metadados_antigos, n_features_novas):
    """
    Log detalhado do status da migração
    """
    if metadados_antigos:
        features_antigas = metadados_antigos.get("features_list", [])
        features_novas = FEATURE_COLUMNS
        
        # Detectar features adicionadas
        features_adicionadas = [f for f in features_novas if f not in features_antigas]
        features_removidas = [f for f in features_antigas if f not in features_novas]
        
        logging.info(f"📊 ANÁLISE DE MIGRAÇÃO:")
        logging.info(f"   └─ Versão antiga: {metadados_antigos.get('versao', 'N/A')}")
        logging.info(f"   └─ Versão nova: {VERSAO_FEATURES}")
        logging.info(f"   └─ Features antigas: {len(features_antigas)}")
        logging.info(f"   └─ Features novas: {len(features_novas)}")
        
        if features_adicionadas:
            logging.info(f"   └─ ➕ Adicionadas: {features_adicionadas}")
        if features_removidas:
            logging.warning(f"   └─ ➖ Removidas: {features_removidas}")
            
        # Registrar no histórico
        historico_entrada = {
            "data": datetime.now().isoformat(),
            "versao_origem": metadados_antigos.get('versao', 'N/A'),
            "versao_destino": VERSAO_FEATURES,
            "features_adicionadas": features_adicionadas,
            "features_removidas": features_removidas
        }
        
        FEATURES_METADATA["historico_migracoes"].append(historico_entrada)

def migrar_modelo_inteligente(modelo_antigo, n_features_antigas, n_features_novas):
    """
    Migra modelo antigo preservando pesos e adicionando novas features
    """
    logging.info(f"🔄 MIGRANDO MODELO: {n_features_antigas} → {n_features_novas} features")
    
    try:
        # Extrair pesos das camadas antigas
        pesos_antigos = modelo_antigo.get_weights()
        
        # Criar novo modelo com features expandidas
        modelo_novo = criar_modelo_neural(n_features_novas)
        pesos_novos = modelo_novo.get_weights()
        
        # 🎯 MIGRAÇÃO INTELIGENTE DE PESOS
        # Camada de entrada: preservar pesos antigos + inicializar novos
        if len(pesos_antigos) >= 2 and len(pesos_novos) >= 2:
            # Pesos da primeira camada (entrada → hidden)
            pesos_entrada_antigos = pesos_antigos[0]  # Shape: (n_features_antigas, 128)
            bias_entrada_antigos = pesos_antigos[1]   # Shape: (128,)
            
            # Criar matriz expandida
            pesos_entrada_novos = pesos_novos[0]  # Shape: (n_features_novas, 128)
            bias_entrada_novos = pesos_novos[1]   # Shape: (128,)
            
            # Copiar pesos antigos preservando ordem das features
            pesos_entrada_novos[:n_features_antigas, :] = pesos_entrada_antigos
            # Bias permanece o mesmo (já treinado)
            bias_entrada_novos[:] = bias_entrada_antigos
            
            # Atualizar primeira camada
            pesos_novos[0] = pesos_entrada_novos
            pesos_novos[1] = bias_entrada_novos
            
            # 🎯 PRESERVAR TODAS AS CAMADAS OCULTAS
            for i in range(2, min(len(pesos_antigos), len(pesos_novos))):
                pesos_novos[i] = pesos_antigos[i]
            
            # Aplicar pesos migrados
            modelo_novo.set_weights(pesos_novos)
            
            logging.info(f"✅ MIGRAÇÃO COMPLETA: Preservados {n_features_antigas} pesos + {n_features_novas - n_features_antigas} novos")
            return modelo_novo
            
    except Exception as e:
        logging.error(f"❌ Erro na migração: {e}")
        logging.info("🔄 Fallback: Criando modelo novo")
        
    return criar_modelo_neural(n_features_novas)

def detectar_features_antigas_do_modelo(modelo_path):
    """
    Detecta quantas features o modelo antigo tinha
    """
    try:
        # Primeiro tentar carregar metadata (mais rápido)
        metadados = carregar_metadados_modelo()
        if metadados and metadados.get('total_features'):
            logging.info(f"🔍 Features detectadas via metadata: {metadados['total_features']}")
            return metadados['total_features']
        
        # Fallback: carregar modelo para detectar features
        modelo_temp = load_model(modelo_path)
        if modelo_temp.layers and hasattr(modelo_temp.layers[0], 'input_shape'):
            n_features = modelo_temp.layers[0].input_shape[1]
            logging.info(f"🔍 Features detectadas via modelo: {n_features}")
            del modelo_temp  # Libera memória
            return n_features
        else:
            logging.warning("⚠️ Não foi possível detectar input_shape do modelo")
            del modelo_temp
            return None
    except Exception as e:
        logging.error(f"❌ Erro detectando features: {e}")
        return None

def carregar_ou_criar_modelo(n_features):
    """
    🚀 SISTEMA INTELIGENTE: Migração automática com metadados
    """
    if os.path.exists(MODELO_PATH):
        try:
            # 🎯 CARREGAMENTO AVANÇADO COM METADADOS
            metadados_antigos = carregar_metadados_modelo()
            n_features_antigas = detectar_features_antigas_do_modelo(MODELO_PATH)
            
            logging.info(f"🔍 DETECÇÃO COMPATIBILIDADE:")
            logging.info(f"   └─ Features do modelo: {n_features_antigas}")
            logging.info(f"   └─ Features esperadas: {n_features}")
            logging.info(f"   └─ Compatível: {n_features_antigas == n_features}")
            
            if n_features_antigas == n_features:
                # Modelo 100% compatível - carregamento direto
                modelo = load_model(MODELO_PATH)
                versao_antiga = metadados_antigos.get('versao', 'N/A') if metadados_antigos else 'N/A'
                logging.info(f"✅ MODELO CARREGADO: {n_features} features compatíveis (v{versao_antiga})")
                
                # 🎯 PRESERVAR APRENDIZADO - Não recriar modelo compatível!
                # Atualizar apenas metadados se necessário (sem backup)
                if not metadados_antigos or versao_antiga != VERSAO_FEATURES:
                    salvar_metadados_modelo(VERSAO_FEATURES, N_FEATURES, FEATURE_COLUMNS)
                    logging.info("📝 Metadados atualizados (modelo preservado)")
                    
                return modelo
                
            elif n_features_antigas and n_features_antigas < n_features:
                # 🎯 MIGRAÇÃO INTELIGENTE COM ANÁLISE COMPLETA
                logging.info(f"🔄 INICIANDO MIGRAÇÃO INTELIGENTE...")
                
                # Log detalhado da migração
                log_status_migracao(metadados_antigos, n_features)
                
                # Backup do modelo antigo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{MODELO_PATH}.backup_migacao_{timestamp}"
                shutil.copy(MODELO_PATH, backup_path)
                logging.info(f"📦 Backup pré-migração: {backup_path}")
                
                # Carregar modelo antigo
                modelo_antigo = load_model(MODELO_PATH)
                
                # 🎯 MIGRAÇÃO PRESERVANDO APRENDIZADO
                modelo_migrado = migrar_modelo_inteligente(modelo_antigo, n_features_antigas, n_features)
                
                # Salvar modelo migrado COM metadados
                salvar_modelo(modelo_migrado, fazer_backup=True, motivo="migracao")
                
                features_adicionadas = n_features - n_features_antigas
                logging.info(f"🚀 MIGRAÇÃO CONCLUÍDA! Preservado aprendizado + {features_adicionadas} features novas")
                logging.info(f"   └─ Status: SUCESSO | Backup: {backup_path}")
                
                return modelo_migrado
                
            else:
                # Modelo incompatível (features reduzidas ou corrupto)
                versao_antiga = metadados_antigos.get('versao', 'N/A') if metadados_antigos else 'N/A'
                logging.warning(f"⚠️ MODELO INCOMPATÍVEL: v{versao_antiga} ({n_features_antigas}) vs v{VERSAO_FEATURES} ({n_features})")
                logging.warning("   └─ Criando modelo novo (incompatibilidade detectada)")
                
        except Exception as e: 
            logging.error(f"❌ Erro no processo de migração: {e}")
            logging.info("🔄 Fallback: Criando modelo novo")
    
    # 🎯 CRIAÇÃO DE MODELO NOVO COM METADADOS
    logging.info(f"🔄 CRIANDO MODELO NOVO: {n_features} features (v{VERSAO_FEATURES})")
    modelo_novo = criar_modelo_neural(n_features)
    salvar_modelo(modelo_novo, fazer_backup=False, motivo="novo")  # Sem backup para modelo novo
    
    return modelo_novo

def normalizar_dados(df):
    df_norm = df.copy()
    colunas_numericas = df_norm.select_dtypes(include=np.number).columns
    if not colunas_numericas.empty:
        scaler = MinMaxScaler()
        df_norm[colunas_numericas] = scaler.fit_transform(df_norm[colunas_numericas])
    if 'candle_type' in df_norm.columns:
        le = LabelEncoder()
        df_norm['candle_type'] = le.fit_transform(df_norm['candle_type'])
    print("🚨 Dados normalizados para treino:", df_norm[FEATURE_COLUMNS].head())
    return df_norm
def treinar_modelo(modelo, memoria):
    if len(memoria) < MIN_EXPERIENCIAS_TREINO:
        logging.info("🔄 Memória insuficiente para treino.")
        return
    logging.info(f"🔄 Iniciando treino com {len(memoria)} experiências.")
    try:
        # Recompile o modelo para garantir que o otimizador reconheça as variáveis atuais
        modelo.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        # Separe exemplos de BUY e SELL e monte o batch balanceado
        buys = [exp for exp in memoria.memoria if exp['action'] == 'BUY']
        sells = [exp for exp in memoria.memoria if exp['action'] == 'SELL']
        batch = random.sample(buys, min(len(buys), BATCH_SIZE//2)) + random.sample(sells, min(len(sells), BATCH_SIZE//2))
        df = pd.DataFrame([exp['contexto'] for exp in batch])
        df['action'] = [exp['action'] for exp in batch]
        df['reward'] = [exp['reward'] for exp in batch]
        df_norm = normalizar_dados(df)
        X_train = df_norm[FEATURE_COLUMNS]
        y_train = (df['action'] == 'BUY').astype(int)
        sample_weights = np.array([max(0.1, 1 + r / 10) for r in df['reward']])
        logging.info(f"Shape X_train: {X_train.shape}, y_train: {y_train.shape}, sample_weights: {sample_weights.shape}")
        logging.debug(f"Batch de experiências: {batch}")
        modelo.fit(
            X_train, y_train,
            epochs=EPOCHS_TREINO,
            batch_size=BATCH_SIZE,
            sample_weight=sample_weights,
            verbose=0
        )
        salvar_modelo(modelo, fazer_backup=True, motivo="treino")
        logging.info("✅ Modelo treinado e salvo com sucesso.")

        # Após o treino, calcule e logue métricas de performance
        rewards = df['reward']
        reward_medio = rewards.mean()
        taxa_acerto = (rewards > 0).mean() * 100  # % de trades com lucro

        logging.info(f"📈 Reward médio do batch: {reward_medio:.2f} | Taxa de acerto: {taxa_acerto:.1f}%")
        logging.info(f"Reward min: {rewards.min():.2f} | max: {rewards.max():.2f}")

        with open("historico_evolucao.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), reward_medio, taxa_acerto])
    except Exception as e:
        logging.error(f"❌ Falha no treino do modelo: {e}\n{traceback.format_exc()}")

# 🎯 IA DEFINITIVA - SCALPING AGRESSIVO + DETECÇÃO REVERSÃO + TIMESTAMP RESOLVIDO
def prever_acao(modelo, contexto, em_posicao=False):
    """IA definitiva com scalping agressivo e detecção de reversão"""
    df = pd.DataFrame([contexto])
    
    # Processamento de features
    if 'candle_type' in df.columns:
        if not np.issubdtype(df['candle_type'].dtype, np.number):
            le = LabelEncoder()
            df['candle_type'] = le.fit_transform(df['candle_type'].astype(str))
    
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    X_pred = df[FEATURE_COLUMNS].astype(float).values
    prob_buy = modelo.predict(X_pred, verbose=0)[0][0]
    
    if em_posicao:
        lucro_atual = contexto.get('floating_profit', 0.0)
        tempo_trade = contexto.get('tempo_em_trade', 0.0)
        momentum_5 = contexto.get('momentum_5', 0.0)
        momentum_reversao = contexto.get('momentum_reversao', 0.0)
        volume_intensidade = contexto.get('volume_intensidade', 1.0)
        
        # 🎯 LOG DECISÃO IA DEFINITIVA
        if datetime.now().second % 12 == 0:
            trend = "📈" if prob_buy > 0.6 else "📉" if prob_buy < 0.4 else "➖"
            pnl_status = "🟢" if lucro_atual > 5 else "🔴" if lucro_atual < -5 else "🟡"
            mom_status = "⚡" if abs(momentum_5) > 2 else "💨" if abs(momentum_5) > 1 else "😶‍🌫️"
            logging.info(f"🧠 IA DEFINITIVA {trend}: Prob={prob_buy:.3f} | {pnl_status}P&L=R${lucro_atual:.2f} | {mom_status}Mom={momentum_5:.1f}% | ⏰{tempo_trade:.1f}min")
        
        # 🎯 SCALPING AGRESSIVO - SAÍDAS RÁPIDAS
        if SCALPING_MODE["ativo"]:
            # Lucro rápido - realizar rapidamente
            if lucro_atual >= SCALPING_MODE["lucro_rapido_pts"]:
                logging.info(f"💰 SCALPING: LUCRO RÁPIDO! R${lucro_atual:.2f}")
                return "FECHAR"
                
            # Prejuízo controlado - sair rápido
            if lucro_atual <= -SCALPING_MODE["prejuizo_rapido_pts"]:
                logging.warning(f"🚨 SCALPING: PREJUÍZO CONTROLADO! R${lucro_atual:.2f}")
                return "FECHAR"
                
            # Tempo máximo em scalping
            if tempo_trade >= (SCALPING_MODE["tempo_max_segundos"] / 60.0):
                if abs(lucro_atual) < 0.5:  # Sem direção clara
                    logging.info(f"⏰ SCALPING: TEMPO MÁXIMO SEM DIREÇÃO! {tempo_trade:.1f}min")
                    return "FECHAR"
        
        # 🧠 DETECÇÃO DE REVERSÃO POR MOMENTUM
        if momentum_reversao < -0.5 and prob_buy < 0.3:  # Forte sinal de reversão bearish
            logging.warning(f"🔄 REVERSÃO DETECTADA: Mom={momentum_reversao:.2f} | Prob={prob_buy:.3f}")
            return "FECHAR"
            
        if momentum_reversao > 0.5 and prob_buy > 0.7:  # Forte sinal de reversão bullish
            logging.info(f"🔄 REVERSÃO BULLISH: Mom={momentum_reversao:.2f} | Prob={prob_buy:.3f}")
            return "FECHAR"
        
        # 🎯 SAÍDAS CLÁSSICAS (mantidas para segurança)
        if lucro_atual <= -40.0:
            logging.warning(f"🚨 STOP LOSS CRÍTICO! P&L: R${lucro_atual:.2f}")
            return "FECHAR"
            
        if lucro_atual >= 50.0 and prob_buy < 0.4:
            logging.info(f"💰 REALIZANDO LUCRO ALTO! P&L: R${lucro_atual:.2f}")
            return "FECHAR"
        
        return "MANTER"
    else:
        # Lógica de entrada com momentum
        momentum_5 = contexto.get('momentum_5', 0.0)
        volume_intensidade = contexto.get('volume_intensidade', 1.0)
        
        # Aumentar confiança com momentum positivo
        if momentum_5 > 1.0 and volume_intensidade > 1.2:
            prob_buy += 0.1  # Boost para entrada com momentum
        elif momentum_5 < -1.0 and volume_intensidade > 1.2:
            prob_buy -= 0.1  # Penalidade para entrada contra momentum
        
        if prob_buy > 0.5:
            return "BUY"
        else:
            return "SELL"

# 🎯 MODO SNIPER - IA REVOLUCIONÁRIA COM PRECISÃO CIRÚRGICA
def prever_acao_sniper(modelo, contexto, analisador_sniper, rates_data, em_posicao=False):
    """
    🎯 MODO SNIPER: Análise ultra-avançada com score de qualidade,
    breakout detection, confirmação tripla e controle rigoroso
    """
    # Reset diário automático
    analisador_sniper.reset_diario()
    
    # Verificar se MODO SNIPER está ativo
    if not MODO_SNIPER["ativo"]:
        return prever_acao(modelo, contexto, em_posicao)  # Fallback para modo normal
    
    # Processamento básico da IA
    df = pd.DataFrame([contexto])
    if 'candle_type' in df.columns:
        if not np.issubdtype(df['candle_type'].dtype, np.number):
            le = LabelEncoder()
            df['candle_type'] = le.fit_transform(df['candle_type'].astype(str))
    
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    X_pred = df[FEATURE_COLUMNS].astype(float).values
    prob_buy = modelo.predict(X_pred, verbose=0)[0][0]
    
    # 🎯 LÓGICA EM POSIÇÃO (com targets agressivos SNIPER)
    if em_posicao:
        lucro_atual = contexto.get('floating_profit', 0.0)
        tempo_trade = contexto.get('tempo_em_trade', 0.0)
        
        # 🎯 TARGETS SNIPER AGRESSIVOS
        target_minimo = MODO_SNIPER["target_minimo_pts"]
        target_ideal = MODO_SNIPER["target_ideal_pts"]
        sl_maximo = MODO_SNIPER["sl_maximo_pts"]
        
        # Log SNIPER detalhado
        if datetime.now().second % 15 == 0:
            status = "🎯" if lucro_atual >= target_minimo else "⏳" if lucro_atual >= 0 else "🚨"
            logging.info(f"{status} SNIPER P&L: R${lucro_atual:.2f} | Target: R${target_ideal:.1f} | ⏰{tempo_trade:.1f}min")
        
        # 💰 REALIZAÇÕES DE LUCRO SNIPER
        if lucro_atual >= target_ideal:
            if prob_buy < 0.3 or prob_buy > 0.7:  # IA muito definida = sair
                logging.info(f"💰 SNIPER TARGET ATINGIDO! +R${lucro_atual:.2f} | IA:{prob_buy:.3f}")
                return "FECHAR"
        
        if lucro_atual >= target_minimo and tempo_trade >= 5.0:  # 5min + lucro mínimo
            if prob_buy < 0.2 or prob_buy > 0.8:  # IA extremamente definida
                logging.info(f"💰 SNIPER LUCRO MÍNIMO + TEMPO! +R${lucro_atual:.2f}")
                return "FECHAR"
        
        # 🚨 STOP LOSS SNIPER (mais rígido)
        if lucro_atual <= -sl_maximo:
            logging.warning(f"🚨 SNIPER STOP LOSS! -R${abs(lucro_atual):.2f}")
            return "FECHAR"
        
        # 🎯 PROTEÇÃO POR REVERSÃO DE MOMENTUM
        momentum_reversao = contexto.get('momentum_reversao', 0.0)
        if abs(momentum_reversao) > 0.6:  # Reversão forte
            if (momentum_reversao < 0 and prob_buy < 0.25) or (momentum_reversao > 0 and prob_buy > 0.75):
                logging.warning(f"🔄 SNIPER REVERSÃO! Mom:{momentum_reversao:.2f}")
                return "FECHAR"
        
        return "MANTER"
    
    # 🎯 LÓGICA DE ENTRADA SNIPER (análise ultra-rigorosa)
    else:
        # 1. VERIFICAR COOLDOWN E LIMITE DIÁRIO
        if not analisador_sniper.verificar_cooldown():
            return "NADA"  # Em cooldown ou limite atingido
        
        # 🚨 MODO EMERGÊNCIA: Mercado muito volátil = critérios relaxados
        atr_atual = contexto.get('volatility', 0.0)
        volume_atual = contexto.get('volume_intensidade', 1.0)
        modo_emergencia = atr_atual > 4.0 and volume_atual > 10.0  # ATR alto + volume explosivo
        
        # 2. PRIMEIRO FILTRO: THRESHOLD IA MÍNIMO (relaxado em emergência)
        threshold_minimo = MODO_SNIPER["threshold_ia_minimo"]
        if modo_emergencia:
            threshold_minimo = max(0.65, threshold_minimo - 0.1)  # Reduz threshold em 10%
            logging.info(f"🚨 MODO EMERGÊNCIA: ATR:{atr_atual:.2f} Vol:{volume_atual:.1f}x - Threshold relaxado para {threshold_minimo:.2f}")
            
        if not (prob_buy >= threshold_minimo or prob_buy <= (1 - threshold_minimo)):
            return "NADA"  # IA não está confiante o suficiente
        
        # 3. IDENTIFICAR NÍVEIS IMPORTANTES
        niveis = analisador_sniper.identificar_niveis_importantes(rates_data)
        
        # 4. DETECTAR BREAKOUT
        tick = mt5.symbol_info_tick(SYMBOL)
        if not tick:
            return "NADA"
            
        volume_atual = contexto.get('volume_tick', 1)
        volume_medio = contexto.get('volume_intensidade', 1.0) * volume_atual if contexto.get('volume_intensidade', 1.0) > 0 else volume_atual
        breakout_info = analisador_sniper.detectar_breakout(tick.last, volume_atual, volume_medio, contexto)
        
        # 5. CALCULAR SCORE DO SETUP
        score_setup = analisador_sniper.calcular_score_setup(contexto, breakout_info, prob_buy)
        
        # 6. VERIFICAR SCORE MÍNIMO (relaxado em emergência)
        score_minimo = MODO_SNIPER["score_minimo_entrada"]
        if modo_emergencia:
            score_minimo = max(4.5, score_minimo - 1.5)  # Reduz score mínimo em emergência
            logging.info(f"🚨 EMERGÊNCIA: Score mínimo relaxado para {score_minimo:.1f}")
            
        if score_setup < score_minimo:
            if modo_emergencia:
                logging.warning(f"🚨 EMERGÊNCIA: Score {score_setup:.1f} ainda baixo mesmo relaxado!")
            return "NADA"  # Setup de baixa qualidade
        
        # 7. CONFIRMAÇÃO TRIPLA
        confirmacao = analisador_sniper.analisar_confirmacao_tripla(contexto, prob_buy)
        if not confirmacao["confirmado"]:
            return "NADA"  # Confirmação tripla falhou
        
        # 8. VERIFICAÇÕES FINAIS DE QUALIDADE
        atr = contexto.get('volatility', 0.0)
        spread = contexto.get('spread', 5.0)
        volume_intensidade = contexto.get('volume_intensidade', 1.0)
        
        # ATR mínimo (evitar lateralização)
        if atr < MODO_SNIPER["atr_minimo"]:
            # Log inteligente sobre lateralização
            if datetime.now().second % 30 == 0:  # A cada 30s
                logging.info(f"🔍 SNIPER AGUARDANDO: ATR {atr:.2f} < {MODO_SNIPER['atr_minimo']:.1f} (lateralização)")
            return "NADA"
            
        # Spread máximo
        if spread > MODO_SNIPER["spread_maximo"]:
            return "NADA"
            
        # Volume mínimo
        if volume_intensidade < MODO_SNIPER["volume_multiplicador"]:
            return "NADA"
        
        # 🎯 DECISÃO FINAL SNIPER
        # Determinar direção baseada em múltiplos fatores
        if breakout_info.get("breakout", False):
            # Entrada por breakout
            direcao_breakout = breakout_info["direcao"]
            if direcao_breakout == "ALTA" and prob_buy >= 0.85:
                acao_final = "BUY"
            elif direcao_breakout == "BAIXA" and prob_buy <= 0.15:
                acao_final = "SELL"
            else:
                return "NADA"  # Breakout e IA não concordam
        else:
            # Entrada por IA + confirmação
            if prob_buy >= MODO_SNIPER["threshold_ia_minimo"]:
                acao_final = "BUY"
            else:
                acao_final = "SELL"
        
        # 🎯 LOG ENTRADA SNIPER APROVADA
        logging.info("=" * 60)
        logging.info(f"🎯 SNIPER ENTRADA APROVADA! 🎯")
        logging.info(f"   └─ Ação: {acao_final}")
        logging.info(f"   └─ Score: {score_setup:.1f}/10")
        logging.info(f"   └─ IA: {prob_buy:.3f}")
        logging.info(f"   └─ Confirmação: {confirmacao['resumo']}")
        if breakout_info.get("breakout"):
            logging.info(f"   └─ Breakout: {breakout_info['direcao']} (força: {breakout_info['forca']:.2f})")
        logging.info(f"   └─ ATR: {atr:.2f} | Volume: {volume_intensidade:.1f}x | Spread: {spread:.1f}pts")
        logging.info("=" * 60)
        
        # Incrementar contador
        MODO_SNIPER["trades_realizados_hoje"] += 1
        
        return acao_final

def inicializar_mt5() -> bool:
    if not mt5.initialize(path=MT5_PATH): logging.error(f"Falha na inicialização do MT5: {mt5.last_error()}"); return False
    terminal_info = mt5.terminal_info()
    if not terminal_info: logging.error("Não foi possível obter informações do terminal."); return False
    global BOOK_FILE_PATH; BOOK_FILE_PATH = os.path.join(terminal_info.data_path, 'MQL5', 'Files', 'book_data.csv')
    try:
        if os.path.exists(BOOK_FILE_PATH): os.remove(BOOK_FILE_PATH); logging.info("Protocolo 'Terra Arrasada': Limpando arquivo de book antigo...")
    except Exception as e: logging.error(f"Não foi possível apagar o arquivo de book antigo: {e}")
    logging.info(f"Monitorando arquivo de comunicação CSV em: {BOOK_FILE_PATH}")
    for i in range(10):
        if os.path.exists(BOOK_FILE_PATH) and os.path.getsize(BOOK_FILE_PATH) > 4:
            logging.info(f"✅ Comunicação direta estabelecida. 'Olho' (BookExporter.mq5) operacional.")
            global SYMBOL; SYMBOL = get_front_month_symbol_dynamic()
            if not mt5.symbol_select(SYMBOL, True): logging.error("Falha ao selecionar símbolo."); return False
            return True
        logging.warning(f"Tentativa {i+1}/10: Aguardando arquivo de comunicação válido do EA...")
        time.sleep(1)
    logging.critical("❌ FALHA CRÍTICA: Arquivo CSV não encontrado/inválido. Verifique o EA V4.0."); return False

def salvar_memoria(memoria, path='memoria.pkl'):
    try:
        with open(path, 'wb') as f:
            pickle.dump(memoria.memoria, f)
        logging.info("✅ Memória de experiências salva com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro ao salvar memória: {e}")

def carregar_memoria(memoria, path='memoria.pkl'):
    try:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                memoria.memoria = pickle.load(f)
            logging.info("✅ Memória de experiências carregada com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro ao carregar memória: {e}")

def monstro_core():
    if not inicializar_mt5(): logging.error("Encerrando robô."); return
    modelo_ia = obter_modelo_cached(); memoria = MemoriaExperiencias(); carregar_memoria(memoria)
    gerenciador_risco = GerenciadorBloqueio(); trailing_stop = GerenciadorTrailingStop()
    # 🎯 NOVOS GERENCIADORES DEFINITIVOS
    gerenciador_tempo = GerenciadorTempo()
    # 🎯 INICIALIZAR ANALISADOR SNIPER
    analisador_sniper = AnalisadorSniper()
    logging.info("🎯 MODO SNIPER ATIVO - Precisão Cirúrgica Iniciada!")
    logging.info(f"   └─ Max trades/dia: {MODO_SNIPER['max_trades_dia']}")
    logging.info(f"   └─ Score mínimo: {MODO_SNIPER['score_minimo_entrada']}/10")
    logging.info(f"   └─ Target ideal: R${MODO_SNIPER['target_ideal_pts']:.1f}")
    
    # 🧹 LIMPEZA AUTOMÁTICA DE BACKUPS
    limpar_backups_antigos()
    
    # 🎯 DIAGNÓSTICO INICIAL DO SNIPER
    diagnosticar_modo_sniper()
    
    posicao_ativa = None; contexto_entrada = None; operacoes_desde_ultimo_treino = 0
    logging.info("✅ Entrando no loop principal de operacoes...")
    try:
        while True:
            try:
                agora = datetime.now()
                
                # 🌙 AUTO-ENCERRAMENTO INTELIGENTE (prioridade máxima)
                if agora.time() >= dtime.fromisoformat(HORARIO_AUTO_ENCERRAMENTO):
                    logging.info("🌙 AUTO-ENCERRAMENTO: After-market finalizado.")
                    logging.info("💾 Salvando memória final...")
                    salvar_memoria(memoria)
                    logging.info("🤖 Salvando modelo final...")
                    salvar_modelo(modelo_ia)
                    logging.info("✅ Monstro encerrado automaticamente. Até amanhã!")
                    try:
                        mt5.shutdown()
                    except:
                        pass
                    return
                
                # 🕐 VERIFICAÇÃO DE HORÁRIOS DE OPERAÇÃO
                if agora.weekday() > 4:  # Fim de semana
                    if agora.second % 60 == 0: logging.info("🏖️ Final de semana - Mercado fechado.")
                    time.sleep(1); continue
                elif agora.time() >= dtime.fromisoformat(HORARIO_AJUSTE):
                    if agora.second % 30 == 0: logging.info("🕐 Horário de ajuste - Aguardando...")
                    time.sleep(1); continue
                elif not (dtime.fromisoformat(HORARIO_PREGAO) <= agora.time() <= dtime.fromisoformat(HORARIO_AFTER)):
                    if agora.second % 60 == 0: logging.info("🌙 Mercado fechado.")
                    time.sleep(1); continue
                posicao_monstro = next((p for p in mt5.positions_get(symbol=SYMBOL) if p.magic == MAGIC_NUMBER), None)
                if not posicao_ativa and not posicao_monstro:
                    contexto_atual = obter_dados_mercado(SYMBOL, gerenciador_tempo=gerenciador_tempo)
                    if not contexto_atual: time.sleep(0.1); continue
                    
                    # 🎯 OBTER DADOS HISTÓRICOS PARA SNIPER
                    rates_data = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)
                    if rates_data is None or len(rates_data) < 50:
                        time.sleep(0.1); continue
                    
                    # 🎯 USAR MODO SNIPER PARA ANÁLISE DE ENTRADA
                    acao_sugerida = prever_acao_sniper(modelo_ia, contexto_atual, analisador_sniper, rates_data, em_posicao=False)
                    if acao_sugerida != "NADA":
                        logging.info(f"🧠 IA Sugere: {acao_sugerida} | Volatilidade: {contexto_atual.get('volatility', 0):.2f}")
                        if not gerenciador_risco.verificar_bloqueio(acao_sugerida):
                            ticket = executar_ordem(acao_sugerida, SYMBOL, contexto_atual['atr'])
                            if ticket: 
                                contexto_entrada = contexto_atual
                                # 🎯 REGISTRAR TIMESTAMP INTERNO
                                gerenciador_tempo.registrar_entrada(ticket)
                                logging.info("Aguardando confirmação..."); time.sleep(3)
                elif posicao_monstro and not posicao_ativa:
                    posicao_ativa = posicao_monstro
                    tipo_pos = "📈 COMPRA" if posicao_ativa.type == mt5.POSITION_TYPE_BUY else "📉 VENDA"
                    logging.info(f"🎯 POSIÇÃO ATIVA: {tipo_pos} | Ticket: {posicao_ativa.ticket} | Entrada: R${posicao_ativa.price_open:.3f}")
                    logging.info(f"💎 MONITORAMENTO P&L EM TEMPO REAL INICIADO! Volume: {posicao_ativa.volume}")
                elif posicao_monstro and posicao_ativa:
                    # 🎯 PROCESSAR TRAILING STOP
                    symbol_info = get_cached_symbol_info(SYMBOL)
                    if symbol_info:
                        trailing_stop.processar_posicao(posicao_monstro, symbol_info)
                    
                    # 🎯 NOVO: Consultar IA SNIPER com LUCRO REAL para decidir se fecha a posição
                    contexto_atual = obter_dados_mercado(SYMBOL, posicao_ativa=posicao_monstro, gerenciador_tempo=gerenciador_tempo)
                    if not contexto_atual: time.sleep(0.1); continue
                    
                    # 🎯 OBTER DADOS HISTÓRICOS PARA SNIPER
                    rates_data = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)
                    if rates_data is None:
                        acao_saida = prever_acao(modelo_ia, contexto_atual, em_posicao=True)  # Fallback
                    else:
                        acao_saida = prever_acao_sniper(modelo_ia, contexto_atual, analisador_sniper, rates_data, em_posicao=True)
                    if acao_saida == "FECHAR":
                        # Enviar ordem oposta para fechar
                        acao_oposta = "SELL" if posicao_ativa.type == mt5.POSITION_TYPE_BUY else "BUY"
                        ticket = executar_ordem(acao_oposta, SYMBOL, contexto_atual['atr'])
                        if ticket:
                            logging.info("🤖 IA DECIDIU SAIR DA OPERAÇÃO! Ordem de saída enviada.")
                            time.sleep(3)
                    # Se "MANTER", não faz nada, só espera o próximo ciclo
                elif not posicao_monstro and posicao_ativa:
                    logging.info(f"🎯 SNIPER - Posição {posicao_ativa.ticket} fechada.")
                    # 🎯 LIMPAR TRAILING STOP E TIMESTAMP
                    trailing_stop.limpar_posicao(posicao_ativa.ticket)
                    gerenciador_tempo.remover_posicao(posicao_ativa.ticket)
                    lucro = obter_lucro_ultima_ordem(posicao_ativa.ticket)
                    acao = "BUY" if posicao_ativa.type == mt5.POSITION_TYPE_BUY else "SELL"
                    
                    # 🎯 FEEDBACK SNIPER - Registrar resultado no cooldown
                    analisador_sniper.verificar_cooldown(lucro)
                    
                    # 🎯 ESTATÍSTICAS SNIPER
                    resultado = "WIN ✅" if lucro > 0 else "LOSS ❌"
                    trades_hoje = MODO_SNIPER["trades_realizados_hoje"]
                    restantes = MODO_SNIPER["max_trades_dia"] - trades_hoje
                    
                    logging.info("=" * 50)
                    logging.info(f"🎯 SNIPER RESULTADO: {resultado}")
                    logging.info(f"   └─ P&L: R${lucro:.2f}")
                    logging.info(f"   └─ Trades hoje: {trades_hoje}/{MODO_SNIPER['max_trades_dia']}")
                    logging.info(f"   └─ Restantes: {restantes}")
                    logging.info("=" * 50)
                    
                    gerenciador_risco.registrar_operacao(acao, lucro)
                    if contexto_entrada:
                        # 🎯 PUNIÇÃO CONFIGURÁVEL PARA ACELERAR APRENDIZADO
                        reward_ajustado = lucro * MULTIPLICADOR_PUNICAO_LOSS if lucro < 0 else lucro
                        memoria.adicionar({"contexto": contexto_entrada, "action": acao, "reward": reward_ajustado})
                        salvar_memoria(memoria)
                    
                    # 🎯 Salvar experiência de saída com contexto atualizado (incluindo lucro real)
                    contexto_saida = obter_dados_mercado(SYMBOL, posicao_ativa=None, gerenciador_tempo=gerenciador_tempo)
                    if contexto_saida:
                        reward_saida = lucro * MULTIPLICADOR_PUNICAO_LOSS if lucro < 0 else lucro
                        memoria.adicionar({"contexto": contexto_saida, "action": "FECHAR", "reward": reward_saida})
                        salvar_memoria(memoria)
                        
                        # 🎯 LOG DE APRENDIZADO EM TEMPO REAL
                        status_aprendizado = "📈 APRENDEU GANHAR" if lucro > 0 else "📉 APRENDEU PERDER"
                        logging.info(f"{status_aprendizado}: R${lucro:.2f} | Reward: {reward_saida:.2f} | Memória: {len(memoria)}")
                    
                    operacoes_desde_ultimo_treino += 1
                    if operacoes_desde_ultimo_treino >= GATILHO_TREINO:
                        try:
                            treinar_modelo(modelo_ia, memoria)
                            limpar_cache_modelo()  # ⚡ Limpa cache após retreino
                            modelo_ia = obter_modelo_cached()  # ⚡ Recarrega modelo atualizado
                        except Exception as e:
                            logging.error(f"Erro inesperado treinando IA: {e}")
                        finally:
                            operacoes_desde_ultimo_treino = 0
                    posicao_ativa, contexto_entrada = None, None
                # ⚡ SLEEP DINÂMICO - MAIS RÁPIDO QUANDO EM POSIÇÃO
                if posicao_ativa:
                    time.sleep(0.2)  # Mais rápido quando operando
                else:
                    time.sleep(0.5)  # Normal quando sem posição
            except KeyboardInterrupt:
                logging.info("Encerrando robô por KeyboardInterrupt.")
                salvar_memoria(memoria)
                exit()
            except Exception as e:
                logging.critical(f"ERRO CRÍTICO NO LOOP: {e}\n{traceback.format_exc()}")
                salvar_memoria(memoria)
                time.sleep(10)
                exit()
    finally:
        salvar_memoria(memoria)

# 🎯 DIAGNÓSTICO DO SISTEMA DE MIGRAÇÃO
def diagnosticar_sistema_migracao():
    """
    Diagnóstico completo do sistema de migração
    """
    logging.info("🔍 DIAGNÓSTICO DO SISTEMA DE MIGRAÇÃO")
    logging.info("=" * 50)
    
    # Verificar modelo atual
    if os.path.exists(MODELO_PATH):
        try:
            modelo_atual = load_model(MODELO_PATH)
            n_features_atual = modelo_atual.layers[0].input_shape[1]
            logging.info(f"✅ Modelo atual: {n_features_atual} features")
            del modelo_atual  # Libera memória
        except Exception as e:
            logging.error(f"❌ Erro ao carregar modelo atual: {e}")
            n_features_atual = "ERRO"
    else:
        logging.warning("⚠️ Nenhum modelo encontrado")
        n_features_atual = "AUSENTE"
    
    # Verificar metadados
    metadados = carregar_metadados_modelo()
    if metadados:
        logging.info(f"📋 METADADOS ENCONTRADOS:")
        logging.info(f"   └─ Versão: {metadados.get('versao', 'N/A')}")
        logging.info(f"   └─ Features: {metadados.get('total_features', 'N/A')}")
        logging.info(f"   └─ Criado em: {metadados.get('data_criacao', 'N/A')}")
        
        historico = metadados.get('historico_migracoes', [])
        if historico:
            logging.info(f"📈 HISTÓRICO DE MIGRAÇÕES ({len(historico)}):")
            for i, migração in enumerate(historico[-3:], 1):  # Últimas 3
                data = migração.get('data', 'N/A')[:19]  # Remove microssegundos
                origem = migração.get('versao_origem', 'N/A')
                destino = migração.get('versao_destino', 'N/A')
                logging.info(f"   └─ [{i}] {data}: v{origem} → v{destino}")
    else:
        logging.warning("⚠️ Nenhum metadado encontrado")
    
    # Status atual vs esperado
    logging.info(f"🎯 STATUS ATUAL:")
    logging.info(f"   └─ Features esperadas: {N_FEATURES} (v{VERSAO_FEATURES})")
    logging.info(f"   └─ Features do modelo: {n_features_atual}")
    
    if str(n_features_atual) == str(N_FEATURES):
        logging.info("✅ SISTEMA COMPATÍVEL - Nenhuma migração necessária")
    elif n_features_atual == "AUSENTE":
        logging.info("🔄 MODELO AUSENTE - Será criado na próxima execução")
    elif n_features_atual == "ERRO":
        logging.error("❌ MODELO CORROMPIDO - Será recriado na próxima execução")
    else:
        logging.info(f"🔄 MIGRAÇÃO NECESSÁRIA: {n_features_atual} → {N_FEATURES}")
    
    logging.info("=" * 50)

# 🎯 COMANDO PARA FORÇAR MIGRAÇÃO MANUAL
def forcar_migracao_manual():
    """
    Força uma migração manual do modelo (útil para testes)
    """
    logging.info("🔧 FORÇANDO MIGRAÇÃO MANUAL...")
    
    if not os.path.exists(MODELO_PATH):
        logging.error("❌ Nenhum modelo encontrado para migrar")
        return False
    
    try:
        # Backup do modelo atual
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{MODELO_PATH}.backup_manual_{timestamp}"
        shutil.copy(MODELO_PATH, backup_path)
        logging.info(f"📦 Backup manual: {backup_path}")
        
        # Carregar e analisar modelo atual
        metadados_antigos = carregar_metadados_modelo()
        n_features_antigas = detectar_features_antigas_do_modelo(MODELO_PATH)
        
        if n_features_antigas and n_features_antigas != N_FEATURES:
            # Executar migração
            modelo_antigo = load_model(MODELO_PATH)
            modelo_migrado = migrar_modelo_inteligente(modelo_antigo, n_features_antigas, N_FEATURES)
            
            # Salvar resultado
            salvar_modelo(modelo_migrado)
            
            logging.info(f"✅ MIGRAÇÃO MANUAL CONCLUÍDA: {n_features_antigas} → {N_FEATURES}")
            return True
        else:
            logging.info("ℹ️ Modelo já está atualizado - Nenhuma migração necessária")
            return False
            
    except Exception as e:
        logging.error(f"❌ Erro na migração manual: {e}")
        return False

def obter_modelo_cached():
    """Cache do modelo para evitar recarregamentos"""
    global _cache_modelo
    if _cache_modelo is None:
        _cache_modelo = carregar_ou_criar_modelo(N_FEATURES)
    return _cache_modelo

def limpar_cache_modelo():
    """Limpa cache do modelo (após retreino)"""
    global _cache_modelo
    _cache_modelo = None

# 🎯 DIAGNÓSTICO COMPLETO DO MODO SNIPER
def diagnosticar_modo_sniper():
    """
    Diagnóstico completo do sistema SNIPER
    """
    logging.info("🎯 DIAGNÓSTICO DO MODO SNIPER")
    logging.info("=" * 60)
    
    # Status geral
    status = "ATIVO ✅" if MODO_SNIPER["ativo"] else "INATIVO ❌"
    logging.info(f"📊 STATUS GERAL: {status}")
    
    if not MODO_SNIPER["ativo"]:
        logging.info("⚠️ MODO SNIPER DESATIVADO - Rodando em modo normal")
        logging.info("=" * 60)
        return
    
    # Configurações principais
    logging.info(f"🎯 CONFIGURAÇÕES PRINCIPAIS:")
    logging.info(f"   └─ Max trades/dia: {MODO_SNIPER['max_trades_dia']}")
    logging.info(f"   └─ Score mínimo: {MODO_SNIPER['score_minimo_entrada']}/10")
    logging.info(f"   └─ Threshold IA: {MODO_SNIPER['threshold_ia_minimo']*100:.0f}%")
    logging.info(f"   └─ Target ideal: R${MODO_SNIPER['target_ideal_pts']:.1f}")
    logging.info(f"   └─ Stop loss: R${MODO_SNIPER['sl_maximo_pts']:.1f}")
    
    # Estatísticas do dia
    trades_hoje = MODO_SNIPER["trades_realizados_hoje"]
    restantes = MODO_SNIPER["max_trades_dia"] - trades_hoje
    percentual_usado = (trades_hoje / MODO_SNIPER["max_trades_dia"]) * 100
    
    logging.info(f"📈 ESTATÍSTICAS DO DIA:")
    logging.info(f"   └─ Trades realizados: {trades_hoje}/{MODO_SNIPER['max_trades_dia']}")
    logging.info(f"   └─ Trades restantes: {restantes}")
    logging.info(f"   └─ Percentual usado: {percentual_usado:.1f}%")
    
    # Status do cooldown
    if MODO_SNIPER["ultimo_trade_timestamp"] > 0:
        tempo_desde_ultimo = time.time() - MODO_SNIPER["ultimo_trade_timestamp"]
        cooldown_restante = max(0, MODO_SNIPER["cooldown_entre_trades"] - tempo_desde_ultimo)
        
        logging.info(f"⏰ STATUS COOLDOWN:")
        logging.info(f"   └─ Tempo desde último: {tempo_desde_ultimo/60:.1f}min")
        logging.info(f"   └─ Cooldown restante: {cooldown_restante:.0f}s")
        
        if cooldown_restante > 0:
            logging.info(f"   └─ Status: EM COOLDOWN ⏸️")
        else:
            logging.info(f"   └─ Status: PRONTO PARA OPERAR ✅")
    else:
        logging.info(f"⏰ STATUS COOLDOWN: PRIMEIRO TRADE DO DIA")
    
    # Configurações de qualidade
    logging.info(f"🔍 CRITÉRIOS DE QUALIDADE:")
    logging.info(f"   └─ Volume mínimo: {MODO_SNIPER['volume_multiplicador']:.1f}x média")
    logging.info(f"   └─ ATR mínimo: {MODO_SNIPER['atr_minimo']:.1f}pts")
    logging.info(f"   └─ Spread máximo: {MODO_SNIPER['spread_maximo']:.1f}pts")
    logging.info(f"   └─ Momentum mínimo: {MODO_SNIPER['momentum_minimo']:.1f}%")
    
    # Breakout detection
    breakout_status = "ATIVO ✅" if MODO_SNIPER["breakout_ativo"] else "INATIVO ❌"
    logging.info(f"🚀 DETECÇÃO DE BREAKOUT: {breakout_status}")
    if MODO_SNIPER["breakout_ativo"]:
        logging.info(f"   └─ Volume mín breakout: {MODO_SNIPER['breakout_volume_min']:.1f}x")
        logging.info(f"   └─ Confirmação: {MODO_SNIPER['breakout_confirmacao']} ticks")
    
    # Confirmação tripla
    logging.info(f"✅ CONFIRMAÇÃO TRIPLA:")
    logging.info(f"   └─ Book: {'ATIVO' if MODO_SNIPER['confirmacao_book'] else 'INATIVO'}")
    logging.info(f"   └─ Momentum: {'ATIVO' if MODO_SNIPER['confirmacao_momentum'] else 'INATIVO'}")
    logging.info(f"   └─ Volume: {'ATIVO' if MODO_SNIPER['confirmacao_volume'] else 'INATIVO'}")
    
    # Cooldowns configurados
    logging.info(f"⏱️ COOLDOWNS CONFIGURADOS:")
    logging.info(f"   └─ Entre trades: {MODO_SNIPER['cooldown_entre_trades']}s")
    logging.info(f"   └─ Após WIN: {MODO_SNIPER['cooldown_apos_win']}s")
    logging.info(f"   └─ Após LOSS: {MODO_SNIPER['cooldown_apos_loss']}s")
    
    # Resumo final
    if trades_hoje >= MODO_SNIPER["max_trades_dia"]:
        logging.info("🛑 STATUS FINAL: LIMITE DIÁRIO ATINGIDO")
    elif cooldown_restante > 0 if MODO_SNIPER["ultimo_trade_timestamp"] > 0 else False:
        logging.info("⏸️ STATUS FINAL: EM COOLDOWN")
    else:
        logging.info("🎯 STATUS FINAL: PRONTO PARA SNIPER!")
    
    logging.info("=" * 60)

# 🧹 LIMPEZA INTELIGENTE DE BACKUPS
def limpar_backups_antigos(manter_dias=7, manter_por_tipo=3):
    """
    Limpa backups antigos mantendo apenas os essenciais
    """
    try:
        import glob
        from datetime import datetime, timedelta
        
        # Padrão dos arquivos de backup
        pasta_modelo = os.path.dirname(MODELO_PATH)
        if not pasta_modelo:
            pasta_modelo = "."
            
        padrao_backup = os.path.join(pasta_modelo, "modelo_monstro.h5.backup_*")
        backups = glob.glob(padrao_backup)
        
        if not backups:
            logging.info("🧹 Nenhum backup encontrado para limpeza")
            return
        
        agora = datetime.now()
        limite_tempo = agora - timedelta(days=manter_dias)
        
        # Separar backups por tipo
        backups_por_tipo = {
            "treino": [],
            "migracao": [],
            "novo": [],
            "outros": []
        }
        
        for backup in backups:
            nome = os.path.basename(backup)
            if "_treino_" in nome:
                backups_por_tipo["treino"].append(backup)
            elif "_migracao_" in nome:
                backups_por_tipo["migracao"].append(backup)
            elif "_novo_" in nome:
                backups_por_tipo["novo"].append(backup)
            else:
                backups_por_tipo["outros"].append(backup)
        
        removidos = 0
        preservados = 0
        
        # Processar cada tipo
        for tipo, lista_backups in backups_por_tipo.items():
            if not lista_backups:
                continue
                
            # Ordenar por data de modificação (mais recente primeiro)
            lista_backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            for i, backup in enumerate(lista_backups):
                try:
                    # Obter data do arquivo
                    data_arquivo = datetime.fromtimestamp(os.path.getmtime(backup))
                    
                    # Manter sempre os N mais recentes de cada tipo
                    if i < manter_por_tipo:
                        preservados += 1
                        continue
                    
                    # Remover se for muito antigo
                    if data_arquivo < limite_tempo:
                        os.remove(backup)
                        removidos += 1
                        logging.info(f"🗑️ Backup removido: {os.path.basename(backup)}")
                    else:
                        preservados += 1
                        
                except Exception as e:
                    logging.warning(f"⚠️ Erro processando backup {backup}: {e}")
        
        if removidos > 0:
            logging.info(f"🧹 LIMPEZA CONCLUÍDA: {removidos} backups removidos, {preservados} preservados")
        else:
            logging.info(f"🧹 Pasta organizada: {preservados} backups preservados")
            
    except Exception as e:
        logging.error(f"❌ Erro na limpeza de backups: {e}")

if __name__ == "__main__":
    app = Flask(__name__)
    @app.route("/status")
    def status(): return jsonify({"status": "Monstro (VEREDITO FINAL) rodando"})
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False), daemon=True).start()
    monstro_core()
# endregion
