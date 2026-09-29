#===== MONSTRO DAS NEGOCIAÇÕES V2 - CIRURGIA COMPLETA ==========
# IMPLEMENTAÇÃO COMPLETA DAS 3 FASES:
# FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR + LIMITE DIÁRIO REAL
# FASE 2: REPLAY DE EXPERIÊNCIAS ATIVO + VETO MATEMÁTICO
# FASE 3: APRENDIZADO COM WINS E LOSSES + EXPECTATIVA MATEMÁTICA

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam

# ========== CONFIGURAÇÕES GLOBAIS ==========
N_FEATURES = 18
HISTORICO_CSV = "historico_contexto_win.csv"
EXPERIENCIAS_JSON = "experiencias.json"
DECISIONS_CSV = "decisions.csv"

# Configurações de trading
MAX_LOSS_DIARIO = -1000.0  # Limite diário em -1000 como solicitado
SL_POINTS = 90
TP_POINTS = 35
VOLUME_PADRAO = 5.0

# Configurações de aprendizado
MIN_EXPERIENCIAS_TREINO = 3
EPOCHS_TREINO = 3
BATCH_SIZE = 32
contador_experiencias_novas = 0
LIMITE_EXPERIENCIAS_PARA_TREINO = 3

# ========== FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR ==========
class BloqueadorContexto:
    """Sistema de bloqueio de contextos perdedores baseado em experiências passadas."""

    def __init__(self):
        self.contextos_bloqueados = {}
        self.max_losses_contexto = 3
        self.tempo_bloqueio = 3600  # 1 hora

    def _hash_contexto(self, contexto: dict) -> str:
        """Cria hash único do contexto para identificação."""
        hora = datetime.now().hour
        faixa_horario = f"{hora//2*2:02d}-{(hora//2*2)+1:02d}"

        volatilidade_faixa = "baixa" if contexto.get('volatility', 0) < 50 else "alta"
        rsi_faixa = "baixo" if contexto.get('rsi_14', 50) < 40 else "alto" if contexto.get('rsi_14', 50) > 60 else "neutro"
        candle_type = contexto.get('candle_type', 'unknown')

        bid_qty = contexto.get('bid_qty', 0)
        ask_qty = contexto.get('ask_qty', 0)
        ratio = bid_qty / (ask_qty + 1)
        book_pressure = "compra" if ratio > 1.5 else "venda" if ratio < 0.7 else "neutro"

        return f"{faixa_horario}_{volatilidade_faixa}_{rsi_faixa}_{candle_type}_{book_pressure}"

    def registrar_loss(self, contexto: dict):
        """Registra um loss em determinado contexto."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx not in self.contextos_bloqueados:
            self.contextos_bloqueados[hash_ctx] = {'losses': 0, 'bloqueado_ate': 0}

        self.contextos_bloqueados[hash_ctx]['losses'] += 1

        if self.contextos_bloqueados[hash_ctx]['losses'] >= self.max_losses_contexto:
            self.contextos_bloqueados[hash_ctx]['bloqueado_ate'] = time.time() + self.tempo_bloqueio
            logging.warning(f"🚫 CONTEXTO BLOQUEADO: {hash_ctx} - {self.max_losses_contexto} losses consecutivos")

    def contexto_bloqueado(self, contexto: dict) -> bool:
        """Verifica se contexto está bloqueado."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx not in self.contextos_bloqueados:
            return False

        ctx_data = self.contextos_bloqueados[hash_ctx]

        if ctx_data['bloqueado_ate'] > time.time():
            tempo_restante = int(ctx_data['bloqueado_ate'] - time.time())
            logging.info(f"⏳ Contexto {hash_ctx} bloqueado por mais {tempo_restante}s")
            return True

        if ctx_data['bloqueado_ate'] > 0 and ctx_data['bloqueado_ate'] <= time.time():
            self.contextos_bloqueados[hash_ctx] = {'losses': 0, 'bloqueado_ate': 0}
            logging.info(f"✅ Contexto {hash_ctx} desbloqueado")

        return False

    def registrar_win(self, contexto: dict):
        """Registra um win - reduz contador de losses do contexto."""
        hash_ctx = self._hash_contexto(contexto)

        if hash_ctx in self.contextos_bloqueados:
            self.contextos_bloqueados[hash_ctx]['losses'] = max(0, self.contextos_bloqueados[hash_ctx]['losses'] - 1)
            if self.contextos_bloqueados[hash_ctx]['losses'] == 0:
                self.contextos_bloqueados[hash_ctx]['bloqueado_ate'] = 0
                logging.info(f"✅ Contexto {hash_ctx} reabilitado após win")

# ========== FASE 2: REPLAY DE EXPERIÊNCIAS ATIVO ==========
class ReplayExperiencias:
    """Sistema de consulta ativa de experiências passadas antes de operar."""

    def __init__(self):
        self.experiencias_cache = []
        self.ultimo_carregamento = 0
        self.cache_valido_por = 300

    def carregar_experiencias(self):
        """Carrega experiências do arquivo JSON."""
        try:
            if not os.path.exists(EXPERIENCIAS_JSON):
                return []

            if time.time() - self.ultimo_carregamento < self.cache_valido_por:
                return self.experiencias_cache

            with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
                experiencias = json.load(f)

            cutoff_time = datetime.now() - timedelta(days=7)
            experiencias_recentes = []

            for exp in experiencias:
                try:
                    timestamp = datetime.fromisoformat(exp.get('timestamp', ''))
                    if timestamp > cutoff_time:
                        experiencias_recentes.append(exp)
                except:
                    continue

            self.experiencias_cache = experiencias_recentes
            self.ultimo_carregamento = time.time()

            logging.debug(f"📚 Carregadas {len(experiencias_recentes)} experiências recentes")
            return experiencias_recentes

        except Exception as e:
            logging.error(f"❌ Erro ao carregar experiências: {e}")
            return []

    def calcular_expectativa_contexto(self, contexto_atual: dict, acao_proposta: str) -> dict:
        """Calcula expectativa matemática para contexto similar."""
        experiencias = self.carregar_experiencias()

        if not experiencias:
            return {'expectativa': 0, 'trades_similares': 0, 'taxa_acerto': 0, 'lucro_medio': 0, 'perda_media': 0}

        similares = []

        for exp in experiencias:
            if exp.get('acao') != acao_proposta:
                continue

            ctx = exp.get('contexto', {})
            similar = True

            # Volatilidade similar (±20%)
            vol_atual = contexto_atual.get('volatility', 0)
            vol_exp = ctx.get('volatility', 0)
            if abs(vol_atual - vol_exp) > vol_atual * 0.2:
                similar = False

            # RSI similar (±15 pontos)
            rsi_atual = contexto_atual.get('rsi_14', 50)
            rsi_exp = ctx.get('rsi_14', 50)
            if abs(rsi_atual - rsi_exp) > 15:
                similar = False

            # Mesmo tipo de candle ou similar
            candle_atual = contexto_atual.get('candle_type', '')
            candle_exp = ctx.get('candle_type', '')
            if candle_atual != candle_exp:
                tipos_alta = ['alta', 'marubozu_alta', 'upper_shadow_alta']
                tipos_baixa = ['baixa', 'marubozu_baixa', 'lower_shadow_baixa']

                if not ((candle_atual in tipos_alta and candle_exp in tipos_alta) or
                        (candle_atual in tipos_baixa and candle_exp in tipos_baixa)):
                    similar = False

            # Pressão do book similar
            bid_atual = contexto_atual.get('bid_qty', 0)
            ask_atual = contexto_atual.get('ask_qty', 0)
            ratio_atual = bid_atual / (ask_atual + 1)

            bid_exp = ctx.get('bid_qty', 0)
            ask_exp = ctx.get('ask_qty', 0)
            ratio_exp = bid_exp / (ask_exp + 1)

            if abs(ratio_atual - ratio_exp) > 0.5:
                similar = False

            if similar:
                similares.append(exp)

        if not similares:
            return {'expectativa': 0, 'trades_similares': 0, 'taxa_acerto': 0, 'lucro_medio': 0, 'perda_media': 0}

        # Calcula estatísticas
        lucros = [exp.get('lucro', 0) for exp in similares]
        wins = [l for l in lucros if l > 0]
        losses = [l for l in lucros if l < 0]

        taxa_acerto = len(wins) / len(lucros) if lucros else 0
        lucro_medio = sum(wins) / len(wins) if wins else 0
        perda_media = abs(sum(losses) / len(losses)) if losses else 0

        # EXPECTATIVA MATEMÁTICA = (Taxa_Acerto * Lucro_Médio) - ((1 - Taxa_Acerto) * Perda_Média)
        expectativa = (taxa_acerto * lucro_medio) - ((1 - taxa_acerto) * perda_media)

        resultado = {
            'expectativa': expectativa,
            'trades_similares': len(similares),
            'taxa_acerto': taxa_acerto * 100,
            'lucro_medio': lucro_medio,
            'perda_media': perda_media
        }

        logging.info(f"📊 Expectativa {acao_proposta}: {expectativa:.2f} | Similares: {len(similares)} | Taxa: {taxa_acerto*100:.1f}%")

        return resultado

# ========== CIRCUIT BREAKER COM LIMITE DIÁRIO REAL ==========
class CircuitBreakerEssencial:
    """Circuit breaker com limite diário REAL que desliga o robô."""

    def __init__(self):
        self.losses_seguidos = 0
        self.loss_diario_atual = 0.0
        self.operacoes_hoje = []
        self.bloqueado = False
        self.motivo_bloqueio = ""
        self.inicio_dia = datetime.now().date()

    def registrar_resultado(self, lucro: float):
        """Registra resultado de uma operação."""
        hoje = datetime.now().date()

        # Reset diário
        if hoje != self.inicio_dia:
            self.loss_diario_atual = 0.0
            self.losses_seguidos = 0
            self.operacoes_hoje = []
            self.inicio_dia = hoje
            self.bloqueado = False
            logging.info("🌅 Novo dia: Circuit breakers resetados")

        self.operacoes_hoje.append((hoje, lucro))
        self.operacoes_hoje = [(data, valor) for data, valor in self.operacoes_hoje if data == hoje]

        self.loss_diario_atual = sum(valor for _, valor in self.operacoes_hoje)

        if lucro < -25.0:
            self.losses_seguidos += 1
        else:
            self.losses_seguidos = 0

        # LIMITE DIÁRIO REAL: Se atingiu -1000, DESLIGA O ROBÔ
        if self.loss_diario_atual <= MAX_LOSS_DIARIO:
            self.bloqueado = True
            self.motivo_bloqueio = f"LIMITE DIÁRIO ATINGIDO: {self.loss_diario_atual:.2f} <= {MAX_LOSS_DIARIO}"
            logging.error(f"🚨 {self.motivo_bloqueio}")
            logging.error("🛑 ROBÔ SERÁ DESLIGADO AUTOMATICAMENTE!")

            # Força encerramento do sistema
            sys.exit(f"LIMITE DIÁRIO ATINGIDO: {self.loss_diario_atual:.2f}")

    def verificar_circuit_breakers(self, spread_atual: float) -> bool:
        """Verifica se algum circuit breaker foi ativado."""
        if self.bloqueado:
            return True

        if self.losses_seguidos >= 3:
            self.bloqueado = True
            self.motivo_bloqueio = f"3 losses seguidos"
            logging.warning(f"🚨 CB ATIVADO: {self.motivo_bloqueio}")
            return True

        if spread_atual > 20:
            self.bloqueado = True
            self.motivo_bloqueio = f"Spread alto: {spread_atual:.1f} pontos"
            logging.warning(f"🚨 CB ATIVADO: {self.motivo_bloqueio}")
            return True

        return False

    def get_status(self) -> dict:
        """Retorna status dos circuit breakers."""
        return {
            "bloqueado": self.bloqueado,
            "motivo": self.motivo_bloqueio,
            "losses_seguidos": self.losses_seguidos,
            "loss_diario": self.loss_diario_atual,
            "operacoes_hoje": len(self.operacoes_hoje)
        }

# ========== INSTÂNCIAS GLOBAIS DOS NOVOS SISTEMAS ==========
bloqueador_contexto = BloqueadorContexto()
replay_experiencias = ReplayExperiencias()
circuit_breaker = CircuitBreakerEssencial()

# ========== FUNÇÃO DE DECISÃO COM VETO INTELIGENTE ==========
def prever_acao_com_veto(modelo: Sequential, contexto_completo: dict) -> Tuple[str, float]:
    """Prevê ação com sistema completo de veto inteligente."""

    # FASE 1: BLOQUEIO DE CONTEXTO PERDEDOR
    if bloqueador_contexto.contexto_bloqueado(contexto_completo):
        return "NADA", 0.0

    # FASE 2: CONSULTA EXPERIÊNCIAS PASSADAS
    expectativa_buy = replay_experiencias.calcular_expectativa_contexto(contexto_completo, "BUY")
    expectativa_sell = replay_experiencias.calcular_expectativa_contexto(contexto_completo, "SELL")

    # VETO MATEMÁTICO: Se ambas expectativas são negativas, NÃO OPERA
    if expectativa_buy['expectativa'] <= 0 and expectativa_sell['expectativa'] <= 0:
        logging.warning(f"🚫 VETO MATEMÁTICO: Expectativas negativas - BUY: {expectativa_buy['expectativa']:.2f}, SELL: {expectativa_sell['expectativa']:.2f}")
        return "NADA", 0.0

    # Se apenas uma tem expectativa positiva, força essa ação
    if expectativa_buy['expectativa'] > 0 and expectativa_sell['expectativa'] <= 0:
        if expectativa_buy['trades_similares'] >= 3:
            logging.info(f"🎯 FORÇA BUY por expectativa: {expectativa_buy['expectativa']:.2f} (similares: {expectativa_buy['trades_similares']})")
            return "BUY", expectativa_buy['expectativa'] / 100

    if expectativa_sell['expectativa'] > 0 and expectativa_buy['expectativa'] <= 0:
        if expectativa_sell['trades_similares'] >= 3:
            logging.info(f"🎯 FORÇA SELL por expectativa: {expectativa_sell['expectativa']:.2f} (similares: {expectativa_sell['trades_similares']})")
            return "SELL", expectativa_sell['expectativa'] / 100

    # Se chegou até aqui, usa IA tradicional
    try:
        # Prepara dados para IA (implementação simplificada)
        X = np.array([[
            contexto_completo.get('bid_qty', 0),
            contexto_completo.get('ask_qty', 0),
            contexto_completo.get('spread', 0),
            contexto_completo.get('volatility', 0),
            contexto_completo.get('entropia_book', 0),
            contexto_completo.get('rsi_14', 50),
            contexto_completo.get('volume_tick', 0),
            0,  # is_in_trade
            0,  # floating_profit
            0,  # tempo_em_trade
            contexto_completo.get('preco_maior_escora_bid', 0),
            contexto_completo.get('volume_maior_escora_bid', 0),
            contexto_completo.get('distancia_maior_escora_bid', 999),
            contexto_completo.get('preco_maior_escora_ask', 0),
            contexto_completo.get('volume_maior_escora_ask', 0),
            contexto_completo.get('distancia_maior_escora_ask', 999),
            contexto_completo.get('liquidez_top5_bid', 0),
            contexto_completo.get('liquidez_top5_ask', 0)
        ]], dtype=np.float32)

        resultado = modelo.predict(X, verbose=0)
        prob = float(resultado[0][0])

        if prob > 0.6:
            return "BUY", prob
        elif prob < 0.4:
            return "SELL", 1 - prob
        else:
            return "NADA", prob

    except Exception as e:
        logging.error(f"❌ Erro na IA: {e}")
        return "NADA", 0.0

# ========== FUNÇÃO DE SALVAMENTO COM CORREÇÃO C9 ==========
def salvar_experiencia_corrigida(contexto: dict, acao: str, lucro: float, score_dist: float):
    """Salva experiência com correção C9 - treina com TODAS as operações."""
    global contador_experiencias_novas

    # FASE 3: TREINA COM TODAS AS EXPERIÊNCIAS (wins E losses)
    if acao in ["BUY", "SELL"]:
        contador_experiencias_novas += 1

        # FASE 1: Registra resultado no bloqueador de contexto
        if lucro < 0:
            bloqueador_contexto.registrar_loss(contexto)
        else:
            bloqueador_contexto.registrar_win(contexto)

        # Registra no circuit breaker
        circuit_breaker.registrar_resultado(lucro)

        logging.info(f"✅ Experiência REAL salva: Ação={acao}, Lucro={lucro:.2f}, Score={score_dist:.2f} | Contador: {contador_experiencias_novas}/{LIMITE_EXPERIENCIAS_PARA_TREINO}")

    # Salva no JSON
    try:
        experiencia = {
            "contexto": contexto,
            "acao": acao,
            "lucro": lucro,
            "score_dist": score_dist,
            "timestamp": datetime.now().isoformat()
        }

        experiencias = []
        if os.path.exists(EXPERIENCIAS_JSON):
            with open(EXPERIENCIAS_JSON, 'r', encoding='utf-8') as f:
                experiencias = json.load(f)

        experiencias.aa)
)exemplo_uso(:
    "__main__"= ame__ =

if __nído!")emplo conclu.info("🏁 Ex    logging)

mulado, 0.8ao, lucro_siac, loexempa(contexto_igidorra_cienciexper   salvar_
         ]: "SELL""BUY",if acao in [
    0.0
      lse "SELL" e acao ==0.0 iflse -3Y" e== "BUacao  if .0do = 45ulao_sim  lucr      resultado
mula     # Si
    ")
   anca:.3f})fi {con(confiança:ão: {acao} ecis(f"🎯 Dg.infologgin        )
o_exemploxtlo, conteeto(modeacao_com_va = prever_, confiancacao:
         modelo
    ifcisãoesta de T
    #one
  o = Nel    mod
    ulação") simsandodo - uão encontra️ Modelo n.warning("⚠     logging   cept:
)
    exm sucesso"codo delo carregaMo✅ .info("logging
     o_win.h5')nstrmodelo_moad_model('elo = lo mod     :
     tryo real)
 ue o modelo, carreg(em produção a model# Simul

      }: 1200.0
  top5_ask'  'liquidez_0.0,
      d': 200biidez_top5_iqu      'l
  k': 25.0,scora_asmaior_eistancia_    'd
    .0, 300':askscora__maior_e'volume       151050.0,
 cora_ask': aior_espreco_m       '5.0,
 cora_bid': 2ior_esa_mastanci     'di,
   _bid': 500.0ior_escora 'volume_ma     000.0,
  51_bid': 1oraor_esc'preco_mai       0,
 : 1ck'e_tivolum      ',
  .2 45  'rsi_14':      8,
a_book': 2.'entropi
        alta',ype': 'ndle_t'ca      : 65.5,
  ity'  'volatil      d': 2.0,
   'sprea   y': 800,
      'ask_qt
    500,: 1qty'       'bid_
  {mplo =xe contexto_eexto
   ntplo de co# Exem

 IARIO}")MAX_LOSS_De diário: {🛡️ Limitg.info(f"   logginTIVO")
  Asesm wins e loscodo : Aprendizao("✅ FASE 3 logging.inf
    ATIVO") tivocias aeriênde exp: Replay SE 2"✅ FAging.info(  log   ATIVO")
 perdedor de contextoloqueio"✅ FASE 1: Bnfo(ogging.i)
    lA!"A INICIADCOMPLET- CIRURGIA 2 MONSTRO V.info("🚀     logging)

        ]

   dler()anging.StreamHlog
     gia.log'),ro_ciruronstandler('ming.FileH      loggrs=[
         handle
     s',essage) %(mme)s -- %(levelna(asctime)s format='%        ,
ng.INFOevel=loggi      lonfig(
  sicC  logging.baging
  ra lognfigu    # Co"

""a completo.ar o sistemo usde com""Exemplo :
    "uso()plo_==
def exemLO ========XEMPIPAL DE EUNÇÃO PRINC=== F=======

# cia: {e}")r experiêno ao salvaErrf"❌ r(rrog.e    loggin
     as e:oncept Excepti
    ex            indent=2)
False, nsure_ascii=ncias, f, eiedump(exper json.       as f:
    ') ng='utf-8ncodiJSON, 'w', eENCIAS_ERIh open(EXPwit

      as[-1000:]perienciias = experienc          ex 1000:
  ) >iaseriencn(exp      if lencias
   experiê000mas 1nas últiMantém ape#
                xperienci
