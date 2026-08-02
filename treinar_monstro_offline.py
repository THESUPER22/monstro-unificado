#!/usr/bin/env python3
"""
TREINAMENTO OFFLINE DO MONSTRO WDO
Gera dados sintéticos realistas de WDO, calcula as 22 features (18 originais + 4 PTAX),
cria labels BUY/SELL/NAO_AGIU, e treina o modelo Keras.

Uso: python treinar_monstro_offline.py [--samples N] [--output path]

O modelo salva em modelo_monstro_wdo.h5 (padrão) ou no caminho especificado.
"""

import os
import sys
import json
import random
import argparse
import warnings
import io
import time
warnings.filterwarnings('ignore')

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, InputLayer, BatchNormalization, Dropout, GaussianNoise
from tensorflow.keras.regularizers import l2
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# ============================================================
# CONFIGURAÇÃO
# ============================================================
TICK_SIZE = 0.5
PRECO_BASE = 5090.0
N_FEATURES = 22
COLUNAS_NUMERICAS = [
    'bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book',
    'rsi_14', 'volume_tick', 'is_in_trade', 'floating_profit', 'tempo_em_trade',
    'preco_maior_escora_bid', 'volume_maior_escora_bid', 'distancia_maior_escora_bid',
    'preco_maior_escora_ask', 'volume_maior_escora_ask', 'distancia_maior_escora_ask',
    'liquidez_top5_bid', 'liquidez_top5_ask',
    'dolar_casado', 'em_janela_ptax', 'minutos_para_ptax', 'dia_ptax'
]


# ============================================================
# GERAÇÃO DE DADOS SINTÉTICOS REALISTAS
# ============================================================

def gerar_precos_wdo(n_bars: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Gera séries de preço sintéticas realistas para WDO."""
    rng = np.random.RandomState(seed)
    
    preco = PRECO_BASE
    precos = []
    
    for _ in range(n_bars):
        # Movimento browniano com mean-reversion e volatilidade variável
        vol = rng.uniform(0.3, 2.5)
        drift = -0.0001 * (preco - PRECO_BASE)  # mean-reversion suave
        retorno = drift + vol * rng.randn() * TICK_SIZE
        
        preco = max(PRECO_BASE - 30, min(PRECO_BASE + 30, preco + retorno))
        preco = round(preco / TICK_SIZE) * TICK_SIZE
        
        # OHLC sintético
        high = preco + abs(rng.randn() * TICK_SIZE)
        low = preco - abs(rng.randn() * TICK_SIZE)
        open_p = preco + rng.randn() * TICK_SIZE * 0.5
        
        high = round(high / TICK_SIZE) * TICK_SIZE
        low = round(low / TICK_SIZE) * TICK_SIZE
        open_p = round(open_p / TICK_SIZE) * TICK_SIZE
        
        precos.append({
            'open': open_p,
            'high': max(high, preco, open_p),
            'low': min(low, preco, open_p),
            'close': preco,
            'vol_base': vol
        })
    
    return pd.DataFrame(precos)


def calcular_rsi(prices: list, period: int = 14) -> float:
    """Calcula RSI."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period if sum(gains) > 0 else 0.001
    avg_loss = sum(losses) / period if sum(losses) > 0 else 0.001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calcular_entropia(volumes: list) -> float:
    """Calcula entropia de Shannon dos volumes."""
    validos = [int(v) for v in volumes if int(v) > 0]
    if len(validos) < 2:
        return 0.0
    return float(scipy_entropy(validos))


def gerar_book_sintetico(preco: float, vol: float, rng: np.random.RandomState) -> dict:
    """Gera book de ofertas sintético realista."""
    n_levels = 5
    
    # Pressão de compra/venda (correlacionada com vol e preço)
    pressao = rng.uniform(-0.3, 0.3)  # -1=todo vende, +1=todo compra
    
    # Bids (compradores)
    bids = []
    for i in range(n_levels):
        p = preco - (i + 1) * TICK_SIZE
        v = int(max(50, rng.exponential(500) * (1 + pressao) * (1 + vol * 0.1)))
        bids.append({'price': round(p, 1), 'volume': v})
    
    # Asks (vendedores)
    asks = []
    for i in range(n_levels):
        p = preco + (i + 1) * TICK_SIZE
        v = int(max(50, rng.exponential(500) * (1 - pressao) * (1 + vol * 0.1)))
        asks.append({'price': round(p, 1), 'volume': v})
    
    bid_qty = sum(b['volume'] for b in bids)
    ask_qty = sum(a['volume'] for a in asks)
    
    return {
        'bids': bids,
        'asks': asks,
        'bid_qty': bid_qty,
        'ask_qty': ask_qty,
        'spread': asks[0]['price'] - bids[0]['price'],
    }


def gerar_features(df_precos: pd.DataFrame, n_samples: int = 5000) -> pd.DataFrame:
    """Gera 22 features (18 originais + 4 PTAX) a partir dos preços sintéticos."""
    rng = np.random.RandomState(42)
    rows = []
    
    precos_historico = []
    ptax_base = 5.85  # PTAX base em R$/USD
    
    for idx, row in df_precos.iterrows():
        preco = row['close']
        vol = row['vol_base']
        precos_historico.append(preco)
        
        # Book sintético
        book = gerar_book_sintetico(preco, vol, rng)
        
        # RSI
        rsi = calcular_rsi(precos_historico[-20:])
        
        # Entropia
        volumes_bid = [b['volume'] for b in book['bids']]
        volumes_ask = [a['volume'] for a in book['asks']]
        entropia = calcular_entropia(volumes_bid + volumes_ask)
        
        # Volatilidade (ATR simplificado)
        if len(precos_historico) >= 15:
            volatility = np.std(precos_historico[-15:])
        else:
            volatility = abs(rng.randn() * 2)
        
        # Candle type
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
        volume_tick = int(max(1, rng.exponential(3) + vol * 2))
        
        # Escora bid/ask (maior ofertante)
        maior_escora_bid = max(book['bids'], key=lambda x: x['volume'])
        maior_escora_ask = max(book['asks'], key=lambda x: x['volume'])
        
        # Liquidez top5
        liquidez_top5_bid = sum(b['volume'] for b in book['bids'][:5])
        liquidez_top5_ask = sum(a['volume'] for a in book['asks'][:5])
        
        # PTAX sintético (correlacionado com o preço WDO)
        ptax = ptax_base + (preco - PRECO_BASE) / 1000 * rng.uniform(-0.5, 0.5)
        ptax = round(ptax, 4)
        dolar_casado = round((preco / 1000 - ptax) * 1000, 2)
        
        # Janela PTAX (aleatório: ~40% das amostras em janela)
        em_janela = 1.0 if rng.random() < 0.4 else 0.0
        mins_rest = float(rng.randint(0, 60)) if em_janela else float(rng.randint(1, 240))
        dia_ptax = 1.0 if rng.random() < 0.03 else 0.0  # ~3% das amostras
        
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
            'dolar_casado': dolar_casado,
            'em_janela_ptax': em_janela,
            'minutos_para_ptax': mins_rest,
            'dia_ptax': dia_ptax,
        })
    
    return pd.DataFrame(rows)


def gerar_labels(df: pd.DataFrame, lookahead: int = 10, threshold: float = 2.0) -> pd.Series:
    """
    Gera labels BUY/SELL/NAO_AGIU baseado no resultado futuro.
    BUY se preço subiu >= threshold nos próximos 'lookahead' bars.
    SELL se preço caiu >= threshold nos próximos 'lookahead' bars.
    NAO_AGIU caso contrário.
    """
    n = len(df)
    labels = []
    
    precos = []
    for i in range(n):
        # Reconstrói preço a partir das features
        bid = df.iloc[i]['bid_qty']
        ask = df.iloc[i]['ask_qty']
        # Preço médio aproximado
        preco_ref = PRECO_BASE + (bid - ask) / max(bid + ask, 1) * 5
        precos.append(preco_ref)
    
    for i in range(n):
        if i + lookahead >= n:
            labels.append('NAO_AGIU')
            continue
        
        preco_atual = precos[i]
        preco_futuro = precos[i + lookahead]
        variacao = preco_futuro - preco_atual
        
        if variacao >= threshold:
            labels.append('BUY')
        elif variacao <= -threshold:
            labels.append('SELL')
        else:
            labels.append('NAO_AGIU')
    
    return pd.Series(labels)


def calcular_recompensa(labels: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Calcula recompensa para cada amostra."""
    rewards = []
    for i, label in enumerate(labels):
        if label == 'BUY':
            rewards.append(random.uniform(15, 50))  # Lucro potencial
        elif label == 'SELL':
            rewards.append(random.uniform(15, 50))
        else:
            rewards.append(random.uniform(-5, 5))  # NAO_AGIU
    return pd.Series(rewards)


# ============================================================
# MODELO KERAS (mesma arquitetura do monstro)
# ============================================================

def criar_modelo(n_features: int = N_FEATURES) -> Sequential:
    """Cria modelo com L2 leve + BatchNorm + Dropout moderado + GaussianNoise."""
    l2_reg = l2(0.001)
    modelo = Sequential()
    modelo.add(InputLayer(input_shape=(n_features,)))
    modelo.add(GaussianNoise(0.01))
    modelo.add(BatchNormalization())

    modelo.add(Dense(128, activation='relu', kernel_regularizer=l2_reg))
    modelo.add(BatchNormalization())
    modelo.add(Dropout(0.2))

    modelo.add(Dense(64, activation='relu', kernel_regularizer=l2_reg))
    modelo.add(BatchNormalization())
    modelo.add(Dropout(0.2))

    modelo.add(Dense(32, activation='relu', kernel_regularizer=l2_reg))
    modelo.add(BatchNormalization())
    modelo.add(Dropout(0.2))

    modelo.add(Dense(1, activation='sigmoid', kernel_regularizer=l2_reg))

    modelo.compile(
        optimizer=Adam(learning_rate=0.0005),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return modelo


# ============================================================
# PREPARAÇÃO DOS DADOS (compatível com monstro)
# ============================================================

def preparar_dados_treino(df: pd.DataFrame):
    """Normaliza e prepara X, y para treino (compatível com preparar_dados do monstro)."""
    from sklearn.preprocessing import MinMaxScaler, LabelEncoder
    
    df_work = df.copy()
    
    # Remove candle_type (não usado pelo modelo)
    if 'candle_type' in df_work.columns:
        df_work = df_work.drop(columns=['candle_type'])
    
    # Remove colunas que não são features
    for col in ['action', 'reward', 'score_dist']:
        if col in df_work.columns:
            df_work = df_work.drop(columns=[col])
    
    # Normaliza
    scaler = MinMaxScaler()
    colunas = [c for c in df_work.columns if c in COLUNAS_NUMERICAS]
    df_work[colunas] = scaler.fit_transform(df_work[colunas])
    
    X = df_work[colunas].values.astype(np.float32)
    
    return X, scaler, colunas


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Treina modelo Monstro WDO offline')
    parser.add_argument('--samples', type=int, default=5000, help='Número de amostras sintéticas')
    parser.add_argument('--output', type=str, default='modelo_monstro_wdo.h5', help='Caminho do modelo de saída')
    parser.add_argument('--epochs', type=int, default=100, help='Máximo de épocas')
    parser.add_argument('--seed', type=int, default=42, help='Seed aleatória')
    args = parser.parse_args()
    
    print(f"{'='*60}")
    print(f"  TREINAMENTO OFFLINE - MONSTRO WDO")
    print(f"  Amostras: {args.samples} | Épocas: {args.epochs}")
    print(f"{'='*60}")
    
    # 1. Gerar dados sintéticos
    print("\n[1/5] Gerando preços sintéticos WDO...")
    df_precos = gerar_precos_wdo(n_bars=args.samples + 100, seed=args.seed)
    print(f"  ✅ {len(df_precos)} barras geradas")
    
    # 2. Gerar features
    print("\n[2/5] Calculando 22 features (18 originais + 4 PTAX)...")
    df_features = gerar_features(df_precos, n_samples=args.samples)
    print(f"  ✅ {len(df_features)} amostras com {len(COLUNAS_NUMERICAS)} features (N_FEATURES={N_FEATURES})")
    
    # 3. Gerar labels
    print("\n[3/5] Gerando labels BUY/SELL/NAO_AGIU...")
    labels = gerar_labels(df_features, lookahead=10, threshold=1.5)
    df_features['action'] = labels
    df_features['reward'] = calcular_recompensa(labels, df_features)
    
    n_buy = (labels == 'BUY').sum()
    n_sell = (labels == 'SELL').sum()
    n_nao = (labels == 'NAO_AGIU').sum()
    print(f"  ✅ BUY: {n_buy} | SELL: {n_sell} | NAO_AGIU: {n_nao}")
    print(f"     Proporção BUY/SELL: {(n_buy+n_sell)/len(labels)*100:.1f}%")
    
    # Filtra apenas BUY e SELL para treino (NAO_AGIU é ruído)
    df_treino = df_features[df_features['action'].isin(['BUY', 'SELL'])].copy()
    print(f"  📊 Amostras para treino: {len(df_treino)}")
    
    if len(df_treino) < 50:
        print("  ❌ Poucas amostras BUY/SELL! Aumente --samples.")
        sys.exit(1)
    
    # 4. Preparar dados com TIMESERIES SPLIT (sem shuffle)
    print("\n[4/5] Normalizando features com TimeSeriesSplit...")
    X, scaler, colunas = preparar_dados_treino(df_treino)

    # Labels: BUY=1, SELL=0
    y = (df_treino['action'] == 'BUY').astype(np.float32).values

    # TimeSeriesSplit: primeiros 80% treino, últimos 20% validação
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    print(f"  ✅ X shape: {X.shape} | Diviso temporal: {len(X_train)} treino, {len(X_val)} val")
    print(f"     Treino - BUY(1): {int(y_train.sum())} | SELL(0): {int(len(y_train)-y_train.sum())}")
    print(f"     Val    - BUY(1): {int(y_val.sum())} | SELL(0): {int(len(y_val)-y_val.sum())}")

    # SMOTE no treino
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)
        print(f"  ✅ SMOTE aplicado. Treino final: {len(X_train)} amostras balanceadas.")
    except Exception as e:
        print(f"  ⚠️ SMOTE não disponível: {e}")

    # Ruído gaussiano nas features para evitar overfitting
    noise_std = 0.015
    X_train_noisy = X_train + np.random.normal(0, noise_std, X_train.shape).astype(np.float32)
    X_train_noisy = np.clip(X_train_noisy, 0.0, 1.0)
    print(f"  ✅ Ruído gaussiano (std={noise_std}) adicionado às features de treino")

    # Label smoothing: BUY=0.9, SELL=0.1 (em vez de 1.0/0.0)
    smoothing = 0.1
    y_train_smooth = y_train * (1.0 - smoothing) + (1.0 - y_train) * smoothing
    print(f"  ✅ Label smoothing (alpha={smoothing}) aplicado: BUY={1.0-smoothing}, SELL={smoothing}")

    # 5. Treinar modelo Keras
    print("\n[5/5] Treinando modelo Keras...")
    modelo = criar_modelo(N_FEATURES)
    modelo.summary()

    # Callback para log detalhado por época
    class EpochLogger(tf.keras.callbacks.Callback):
        def __init__(self, n_total_epochs):
            super().__init__()
            self.start_time = time.time()
            self.n_total = n_total_epochs
        def on_epoch_end(self, epoch, logs=None):
            elapsed = time.time() - self.start_time
            l = logs.get('loss', 0)
            a = logs.get('accuracy', 0)
            vl = logs.get('val_loss', 0)
            va = logs.get('val_accuracy', 0)
            gap = a - va
            print(f"  ⏱ {epoch+1:3d}/{self.n_total} | loss={l:.4f} acc={a:.4f} | val_loss={vl:.4f} val_acc={va:.4f} | gap={gap:.4f} | {elapsed:.0f}s")
        def on_train_end(self, logs=None):
            total = time.time() - self.start_time
            print(f"  🕒 Treino concluído em {total:.0f}s")

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6),
        EpochLogger(args.epochs),
    ]

    history = modelo.fit(
        X_train_noisy, y_train_smooth,
        epochs=args.epochs,
        batch_size=32,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        shuffle=False,  # Temporal: NÃO embaralhar
        verbose=0  # verbose 0 porque temos o callback custom
    )
    
    # Salvar history em JSON para análise posterior
    history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history_treino.json')
    with open(history_path, 'w') as f:
        json.dump(history.history, f, indent=2, default=str)
    # Salvar params do treino
    params_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history_treino_params.json')
    with open(params_path, 'w') as f:
        json.dump({
            'n_amostras': args.samples,
            'n_features': N_FEATURES,
            'n_treino': int(len(X_train)),
            'n_val': int(len(X_val)),
            'max_epochs': args.epochs,
            'smote': 'sim' if 'smote' in dir() else 'nao',
            'split_temporal': f'{split_idx} treino + {len(X)-split_idx} val',
            'seed': args.seed,
        }, f, indent=2)
    print(f"  ✅ History salvo: {history_path}")
    print(f"  ✅ Params salvo: {params_path}")
    
    # Métricas finais
    loss_final = history.history['loss'][-1]
    acc_final = history.history['accuracy'][-1]
    val_loss = history.history['val_loss'][-1]
    val_acc = history.history['val_accuracy'][-1]
    best_epoch = np.argmin(history.history['val_loss']) + 1
    
    print(f"\n{'='*60}")
    print(f"  RESULTADO DO TREINO")
    print(f"{'='*60}")
    print(f"  Loss:     {loss_final:.4f} (val: {val_loss:.4f})")
    print(f"  Accuracy: {acc_final:.4f} (val: {val_acc:.4f})")
    print(f"  Gap:      {(acc_final - val_acc)*100:.2f}%")
    print(f"  Melhor época (val_loss): {best_epoch}")
    print(f"  Épocas:   {len(history.history['loss'])}")
    
    # Salvar modelo
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    modelo.save(output_path)
    tamanho = os.path.getsize(output_path)
    print(f"\n  ✅ Modelo salvo: {output_path}")
    print(f"     Tamanho: {tamanho:,} bytes ({tamanho/1024:.1f} KB)")
    
    # Salvar scaler para referência
    scaler_path = output_path.replace('.h5', '_scaler.json')
    scaler_info = {
        'min': scaler.data_min_.tolist(),
        'max': scaler.data_max_.tolist(),
        'feature_names': colunas
    }
    with open(scaler_path, 'w') as f:
        json.dump(scaler_info, f)
    print(f"  ✅ Scaler salvo: {scaler_path}")
    
    # Teste rápido com dados de validação temporal
    print(f"\n{'='*60}")
    print(f"  TESTE RÁPIDO DE PREDIÇÃO (validação temporal)")
    print(f"{'='*60}")
    
    idx_test = np.random.choice(len(X_val), min(5, len(X_val)), replace=False)
    X_test = X_val[idx_test]
    preds = modelo.predict(X_test, verbose=0).flatten()
    reais = y_val[idx_test]
    
    for i, (pred, real) in enumerate(zip(preds, reais)):
        acao_prev = "BUY" if pred > 0.5 else "SELL"
        acao_real = "BUY" if real == 1 else "SELL"
        ok = "✅" if acao_prev == acao_real else "❌"
        print(f"  Amostra {i+1}: pred={pred:.4f} ({acao_prev}) real={acao_real} {ok}")
    
    print(f"\n{'='*60}")
    print(f"  PRONTO! Reinicie o robô para carregar o modelo.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
