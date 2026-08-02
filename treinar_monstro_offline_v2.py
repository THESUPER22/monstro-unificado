#!/usr/bin/env python3
"""
TREINAMENTO OFFLINE DO MONSTRO WDO - VERSÃO 2 REALISTA
Gera dados com dinâmica real de mercado:
- Tendências e reversões
- Volatilidade variável (clusters)
- Book com microestrutura real
- Labels baseados em movimentos reais

Uso: python treinar_monstro_offline_v2.py [--samples N] [--output path]
"""

import os
import sys
import json
import random
import argparse
import warnings
import io
warnings.filterwarnings('ignore')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, InputLayer, BatchNormalization, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# ============================================================
# CONFIGURAÇÃO
# ============================================================
TICK_SIZE = 0.5
PRECO_BASE = 5090.0
N_FEATURES = 18
COLUNAS_NUMERICAS = [
    'bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book',
    'rsi_14', 'volume_tick', 'is_in_trade', 'floating_profit', 'tempo_em_trade',
    'preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
    'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
    'liquidez_top5_bid', 'liquidez_top5_ask'
]


# ============================================================
# GERAÇÃO DE DADOS REALISTAS (V2)
# ============================================================

class MarketSimulator:
    """Simula dinâmica real de mercado com múltiplos regimes."""
    
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.preco = PRECO_BASE
        self.trend = 0.0
        self.volatility = 1.5
        self.volatility_target = 1.5
        self.range_low = PRECO_BASE - 25
        self.range_high = PRECO_BASE + 25
        self.regime = 'trending'  # trending, ranging, volatile
        self.regime_duration = 0
        self.precos = []
        
    def _update_regime(self):
        """Muda regime de mercado periodicamente."""
        self.regime_duration += 1
        
        if self.regime_duration > self.rng.randint(50, 200):
            regimes = ['trending', 'ranging', 'volatile']
            pesos = [0.4, 0.3, 0.3]
            self.regime = self.rng.choice(regimes, p=pesos)
            self.regime_duration = 0
            
            if self.regime == 'trending':
                self.trend = self.rng.choice([-1, 1]) * self.rng.uniform(0.1, 0.5)
            elif self.regime == 'ranging':
                self.trend = 0.0
                self.range_low = self.preco - self.rng.uniform(10, 30)
                self.range_high = self.preco + self.rng.uniform(10, 30)
            else:  # volatile
                self.volatility_target = self.rng.uniform(2.0, 4.0)
    
    def _update_volatility(self):
        """Volatilidade com mean-reversion (GARCH-like)."""
        mean_vol = 1.5
        self.volatility += 0.1 * (mean_vol - self.volatility)
        self.volatility += 0.05 * self.rng.randn()
        self.volatility = max(0.3, min(4.0, self.volatility))
    
    def gerar_bar(self):
        """Gera uma barra OHLCV realista."""
        self._update_regime()
        self._update_volatility()
        
        # Movimento do preço
        drift = self.trend * TICK_SIZE
        vol = self.volatility * TICK_SIZE
        
        # Mean-reversion quando em range
        if self.regime == 'ranging':
            mid = (self.range_low + self.range_high) / 2
            drift += 0.02 * (mid - self.preco)
        
        # Momentum (tendência persiste)
        if len(self.precos) > 5:
            momentum = (self.precos[-1] - self.precos[-5]) * 0.1
            drift += momentum
        
        retorno = drift + vol * self.rng.randn()
        self.preco += retorno
        self.preco = max(PRECO_BASE - 40, min(PRECO_BASE + 40, self.preco))
        self.preco = round(self.preco / TICK_SIZE) * TICK_SIZE
        
        # OHLC
        high = self.preco + abs(self.rng.randn() * vol * 0.5)
        low = self.preco - abs(self.rng.randn() * vol * 0.5)
        open_p = self.preco + self.rng.randn() * vol * 0.3
        
        high = round(max(high, self.preco, open_p) / TICK_SIZE) * TICK_SIZE
        low = round(min(low, self.preco, open_p) / TICK_SIZE) * TICK_SIZE
        open_p = round(open_p / TICK_SIZE) * TICK_SIZE
        
        # Volume (correlacionado com volatilidade)
        volume = int(max(100, self.rng.exponential(500) * (1 + self.volatility * 0.3)))
        
        self.precos.append(self.preco)
        
        return {
            'open': open_p,
            'high': high,
            'low': low,
            'close': self.preco,
            'volume': volume,
            'volatility': self.volatility
        }
    
    def gerar_precos(self, n_bars):
        """Gera série de preços realista."""
        barras = []
        for _ in range(n_bars):
            barras.append(self.gerar_bar())
        return pd.DataFrame(barras)


def gerar_book_realista(preco, vol, tendencia, rng):
    """Gera book com microestrutura real."""
    n_levels = 5
    
    # Pressão correlacionada com tendência
    pressao_base = tendencia * 0.3
    pressao = pressao_base + rng.uniform(-0.2, 0.2)
    pressao = max(-0.8, min(0.8, pressao))
    
    # Spread baseado em volatilidade
    spread_min = TICK_SIZE
    spread = spread_min + rng.exponential(0.5) * vol
    
    # Bids
    bids = []
    for i in range(n_levels):
        p = preco - (i + 1) * TICK_SIZE - spread/2
        # Volume com mean-reversion e clustering
        base_vol = 300 + rng.exponential(400)
        v = int(max(50, base_vol * (1 + pressao) * (1 + vol * 0.2)))
        
        # Adicionar "escora" occasionalmente (volume grande)
        if rng.random() < 0.15:
            v = int(v * (2 + rng.uniform(0, 3)))
        
        bids.append({'price': round(p, 1), 'volume': v})
    
    # Asks
    asks = []
    for i in range(n_levels):
        p = preco + (i + 1) * TICK_SIZE + spread/2
        base_vol = 300 + rng.exponential(400)
        v = int(max(50, base_vol * (1 - pressao) * (1 + vol * 0.2)))
        
        if rng.random() < 0.15:
            v = int(v * (2 + rng.uniform(0, 3)))
        
        asks.append({'price': round(p, 1), 'volume': v})
    
    bid_qty = sum(b['volume'] for b in bids)
    ask_qty = sum(a['volume'] for a in asks)
    
    return {
        'bids': bids,
        'asks': asks,
        'bid_qty': bid_qty,
        'ask_qty': ask_qty,
        'spread': round(spread, 2),
        'pressao': pressao
    }


def calcular_rsi(prices, period=14):
    """Calcula RSI."""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices[-period-1:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0.001
    avg_loss = np.mean(losses) if len(losses) > 0 else 0.001
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calcular_entropia(volumes):
    """Calcula entropia de Shannon."""
    validos = [int(v) for v in volumes if int(v) > 0]
    if len(validos) < 2:
        return 0.0
    return float(scipy_entropy(validos))


def gerar_features_realistas(df_precos):
    """Gera 18 features com dados realistas."""
    rng = np.random.RandomState(42)
    rows = []
    
    precos = df_precos['close'].tolist()
    volatilidades = df_precos['volatility'].tolist()
    
    for idx in range(len(df_precos)):
        preco = precos[idx]
        vol = volatilidades[idx]
        
        # Tendência (baseada nos últimos 10 preços)
        if idx >= 10:
            tendencia = (precos[idx] - precos[idx-10]) / 10
        else:
            tendencia = 0.0
        
        # Book realista
        book = gerar_book_realista(preco, vol, tendencia, rng)
        
        # RSI
        rsi = calcular_rsi(precos[max(0, idx-20):idx+1])
        
        # Entropia
        volumes_bid = [b['volume'] for b in book['bids']]
        volumes_ask = [a['volume'] for a in book['asks']]
        entropia = calcular_entropia(volumes_bid + volumes_ask)
        
        # Volatilidade (ATR real)
        if idx >= 15:
            volatility = np.std(precos[idx-15:idx+1])
        else:
            volatility = vol
        
        # Candle type
        row = df_precos.iloc[idx]
        o, h, l, c = row['open'], row['high'], row['low'], row['close']
        body = c - o
        total = h - l if h != l else 0.001
        
        if body > 0 and (h - c) / total > 0.3:
            candle = 'upper_shadow_baixa'
        elif body < 0 and (c - l) / total > 0.3:
            candle = 'lower_shadow_baixa'
        elif abs(body) / total < 0.1:
            candle = 'doji_baixa'
        else:
            candle = 'upper_shadow_baixa'
        
        # Volume tick
        volume_tick = int(max(1, row['volume'] / 100 + rng.exponential(2)))
        
        # Escora bid/ask
        maior_escora_bid = max(book['bids'], key=lambda x: x['volume'])
        maior_escora_ask = max(book['asks'], key=lambda x: x['volume'])
        
        # Liquidez top5
        liquidez_top5_bid = sum(b['volume'] for b in book['bids'][:5])
        liquidez_top5_ask = sum(a['volume'] for a in book['asks'][:5])
        
        rows.append({
            'bid_qty': float(book['bid_qty']),
            'ask_qty': float(book['ask_qty']),
            'spread': float(book['spread']),
            'volatility': float(volatility),
            'candle_type': candle,
            'entropia_book': float(entropia),
            'rsi_14': float(rsi),
            'volume_tick': float(volume_tick),
            'is_in_trade': 0.0,
            'floating_profit': 0.0,
            'tempo_em_trade': 0.0,
            'preco_maior_escora_bid': float(maior_escora_bid['price']),
            'volume_maior_escora_bid': float(maior_escora_bid['volume']),
            'distancia_maior_escora_bid': float(abs(preco - maior_escora_bid['price'])),
            'preco_maior_escora_ask': float(maior_escora_ask['price']),
            'volume_maior_escora_ask': float(maior_escora_ask['volume']),
            'distancia_maior_escora_ask': float(abs(maior_escora_ask['price'] - preco)),
            'liquidez_top5_bid': float(liquidez_top5_bid),
            'liquidez_top5_ask': float(liquidez_top5_ask),
        })
    
    return pd.DataFrame(rows)


def gerar_labels_realistas(precos, lookahead=10, threshold=2.0):
    """
    Gera labels baseados em movimentos reais de preço.
    BUY = preço subiu >= threshold em lookahead barras
    SELL = preço caiu >= threshold em lookahead barras
    NAO_AGIU = movimento menor que threshold
    """
    n = len(precos)
    labels = []
    
    for i in range(n):
        if i + lookahead >= n:
            labels.append('NAO_AGIU')
            continue
        
        preco_atual = precos[i]
        preco_futuro = precos[i + lookahead]
        variacao = preco_futuro - preco_atual
        
        # Adicionar ruído realista (slippage)
        variacao += np.random.normal(0, 0.1)
        
        if variacao >= threshold:
            labels.append('BUY')
        elif variacao <= -threshold:
            labels.append('SELL')
        else:
            labels.append('NAO_AGIU')
    
    return labels


def calcular_recompensa_realista(labels, precos, lookahead=10):
    """
    Calcula recompensa baseada no resultado real.
    Lucro/prejuízo real considerando slippage e custos.
    """
    rewards = []
    custo_operacao = 0.5  # Spread + slippage estimado
    
    for i, label in enumerate(labels):
        if i + lookahead >= len(precos):
            rewards.append(0.0)
            continue
        
        if label == 'BUY':
            lucro = (precos[i + lookahead] - precos[i]) - custo_operacao
            rewards.append(float(lucro))
        elif label == 'SELL':
            lucro = (precos[i] - precos[i + lookahead]) - custo_operacao
            rewards.append(float(lucro))
        else:
            rewards.append(0.0)
    
    return rewards


# ============================================================
# MODELO KERAS
# ============================================================

def criar_modelo(n_features=N_FEATURES):
    """Cria modelo com arquitetura otimizada."""
    modelo = Sequential()
    modelo.add(InputLayer(input_shape=(n_features,)))
    modelo.add(BatchNormalization())
    
    modelo.add(Dense(128, activation='relu'))
    modelo.add(BatchNormalization())
    modelo.add(Dropout(0.3))
    
    modelo.add(Dense(64, activation='relu'))
    modelo.add(BatchNormalization())
    modelo.add(Dropout(0.2))
    
    modelo.add(Dense(32, activation='relu'))
    modelo.add(BatchNormalization())
    
    modelo.add(Dense(1, activation='sigmoid'))
    
    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return modelo


def preparar_dados_treino(df):
    """Normaliza e prepara X, y para treino."""
    from sklearn.preprocessing import MinMaxScaler
    
    df_work = df.copy()
    
    if 'candle_type' in df_work.columns:
        df_work = df_work.drop(columns=['candle_type'])
    
    for col in ['action', 'reward', 'score_dist']:
        if col in df_work.columns:
            df_work = df_work.drop(columns=[col])
    
    scaler = MinMaxScaler()
    colunas = [c for c in df_work.columns if c in COLUNAS_NUMERICAS]
    df_work[colunas] = scaler.fit_transform(df_work[colunas])
    
    X = df_work[colunas].values.astype(np.float32)
    
    return X, scaler, colunas


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Treina modelo Monstro WDO V2 Realista')
    parser.add_argument('--samples', type=int, default=10000, help='Número de amostras')
    parser.add_argument('--output', type=str, default='modelo_monstro_wdo.h5', help='Caminho do modelo')
    parser.add_argument('--epochs', type=int, default=150, help='Máximo de épocas')
    parser.add_argument('--seed', type=int, default=42, help='Seed aleatória')
    parser.add_argument('--lookahead', type=int, default=10, help='Barras para lookahead')
    parser.add_argument('--threshold', type=float, default=2.0, help='Threshold para BUY/SELL (pontos)')
    args = parser.parse_args()
    
    print(f"{'='*60}")
    print(f"  TREINAMENTO OFFLINE V2 - MONSTRO WDO REALISTA")
    print(f"  Amostras: {args.samples} | Épocas: {args.epochs}")
    print(f"  Lookahead: {args.lookahead} | Threshold: {args.threshold}pts")
    print(f"{'='*60}")
    
    # 1. Gerar dados realistas
    print("\n[1/6] Gerando preços com dinâmica real de mercado...")
    sim = MarketSimulator(seed=args.seed)
    df_precos = sim.gerar_precos(args.samples + 200)
    print(f"  ✅ {len(df_precos)} barras geradas")
    print(f"  📊 Preço: {df_precos['close'].min():.1f} - {df_precos['close'].max():.1f}")
    print(f"  📊 Volatilidade: {df_precos['volatility'].mean():.2f}")
    
    # 2. Gerar features
    print("\n[2/6] Calculando 18 features realistas...")
    df_features = gerar_features_realistas(df_precos)
    print(f"  ✅ {len(df_features)} amostras com {len(COLUNAS_NUMERICAS)} features")
    
    # 3. Gerar labels
    print(f"\n[3/6] Gerando labels (lookahead={args.lookahead}, threshold={args.threshold}pts)...")
    precos = df_precos['close'].tolist()
    labels = gerar_labels_realistas(precos, lookahead=args.lookahead, threshold=args.threshold)
    rewards = calcular_recompensa_realista(labels, precos, lookahead=args.lookahead)
    
    df_features['action'] = labels
    df_features['reward'] = rewards
    
    n_buy = labels.count('BUY')
    n_sell = labels.count('SELL')
    n_nao = labels.count('NAO_AGIU')
    total = len(labels)
    
    print(f"  ✅ BUY: {n_buy} ({n_buy/total*100:.1f}%)")
    print(f"     SELL: {n_sell} ({n_sell/total*100:.1f}%)")
    print(f"     NAO_AGIU: {n_nao} ({n_nao/total*100:.1f}%)")
    print(f"     Proporção BUY/SELL: {(n_buy+n_sell)/total*100:.1f}%")
    
    # Filtra BUY e SELL
    df_treino = df_features[df_features['action'].isin(['BUY', 'SELL'])].copy()
    print(f"  📊 Amostras para treino: {len(df_treino)}")
    
    if len(df_treino) < 100:
        print("  ❌ Poucas amostras BUY/SELL! Aumente --samples ou diminua --threshold.")
        sys.exit(1)
    
    # 4. Preparar dados
    print("\n[4/6] Normalizando features...")
    X, scaler, colunas = preparar_dados_treino(df_treino)
    y = (df_treino['action'] == 'BUY').astype(np.float32).values
    
    print(f"  ✅ X shape: {X.shape} | y shape: {y.shape}")
    print(f"     BUY(1): {int(y.sum())} | SELL(0): {int(len(y)-y.sum())}")
    
    # 5. Treinar modelo
    print("\n[5/6] Treinando modelo Keras...")
    modelo = criar_modelo(N_FEATURES)
    modelo.summary()
    
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=20, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=8, min_lr=1e-6),
    ]
    
    history = modelo.fit(
        X, y,
        epochs=args.epochs,
        batch_size=32,
        validation_split=0.2,
        callbacks=callbacks,
        verbose=1
    )
    
    # Métricas
    loss_final = history.history['loss'][-1]
    acc_final = history.history['accuracy'][-1]
    val_loss = history.history['val_loss'][-1]
    val_acc = history.history['val_accuracy'][-1]
    
    print(f"\n{'='*60}")
    print(f"  RESULTADO DO TREINO")
    print(f"{'='*60}")
    print(f"  Loss:     {loss_final:.4f} (val: {val_loss:.4f})")
    print(f"  Accuracy: {acc_final:.4f} (val: {val_acc:.4f})")
    print(f"  Épocas:   {len(history.history['loss'])}")
    
    # 6. Salvar modelo
    print("\n[6/6] Salvando modelo...")
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    modelo.save(output_path)
    tamanho = os.path.getsize(output_path)
    print(f"  ✅ Modelo salvo: {output_path}")
    print(f"     Tamanho: {tamanho:,} bytes ({tamanho/1024:.1f} KB)")
    
    # Salvar scaler
    scaler_path = output_path.replace('.h5', '_scaler.json')
    scaler_info = {
        'min': scaler.data_min_.tolist(),
        'max': scaler.data_max_.tolist(),
        'feature_names': colunas
    }
    with open(scaler_path, 'w') as f:
        json.dump(scaler_info, f)
    print(f"  ✅ Scaler salvo: {scaler_path}")
    
    # Salvar dados de treino para referência
    dados_path = output_path.replace('.h5', '_dados_treino.csv')
    df_treino.to_csv(dados_path, index=False)
    print(f"  ✅ Dados de treino salvos: {dados_path}")
    
    # Teste
    print(f"\n{'='*60}")
    print(f"  TESTE RÁPIDO DE PREDIÇÃO")
    print(f"{'='*60}")
    
    idx_test = np.random.choice(len(X), min(10, len(X)), replace=False)
    X_test = X[idx_test]
    preds = modelo.predict(X_test, verbose=0).flatten()
    reais = y[idx_test]
    
    acertos = 0
    for i, (pred, real) in enumerate(zip(preds, reais)):
        acao_prev = "BUY" if pred > 0.5 else "SELL"
        acao_real = "BUY" if real == 1 else "SELL"
        ok = "✅" if acao_prev == acao_real else "❌"
        if acao_prev == acao_real:
            acertos += 1
        print(f"  Amostra {i+1}: pred={pred:.4f} ({acao_prev}) real={acao_real} {ok}")
    
    print(f"\n  Taxa de acerto: {acertos}/{len(preds)} = {acertos/len(preds)*100:.1f}%")
    
    print(f"\n{'='*60}")
    print(f"  PRONTO! Reinicie o robô para carregar o modelo.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
