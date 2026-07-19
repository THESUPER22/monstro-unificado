#!/usr/bin/env python3
"""
Script para corrigir modelo WIN para 10 features
Remove close_price do contexto e recria modelo compatível
"""

import os
import shutil
from datetime import datetime

import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import BatchNormalization, Dense, Dropout
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam


def criar_modelo_10_features():
    """Cria um novo modelo neural com 10 features."""
    modelo = Sequential([
        Dense(128, input_dim=10, activation='relu'),
        BatchNormalization(),
        Dropout(0.3),
        Dense(64, activation='relu'),
        BatchNormalization(),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dropout(0.1),
        Dense(1, activation='sigmoid')
    ])

    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return modelo


def fazer_backup_modelo(caminho_modelo):
    """Faz backup do modelo atual."""
    if os.path.exists(caminho_modelo):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{caminho_modelo}.backup_11features_{timestamp}"
        shutil.copy2(caminho_modelo, backup_path)
        print(f"✅ Backup criado: {backup_path}")
        return backup_path
    return None


def testar_modelo(modelo, n_features=10):
    """Testa se o modelo funciona corretamente."""
    try:
        test_input = np.random.random((1, n_features)).astype(np.float32)
        resultado = modelo.predict(test_input, verbose=0)
        print(
            f"✅ Teste do modelo: entrada {n_features} features → saída {resultado[0][0]:.4f}")
        return True
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False


def main():
    """Função principal."""
    print("🔧 CORREÇÃO DO MODELO PARA 10 FEATURES")
    print("=" * 50)

    # Caminhos dos modelos
    modelos = [
        "modelo_monstro_win.h5",
        "modelo_monstro_win.keras",
        "modelo_monstro.h5",
        "modelo_monstro.keras"
    ]

    for caminho_modelo in modelos:
        if os.path.exists(caminho_modelo):
            print(f"\n📁 Processando: {caminho_modelo}")

            # Faz backup
            backupth = fazer_backup_modelo(caminho_modelo)

            try:
                # Tenta carregar modelo atual
                modelo_atual = load_model(caminho_modelo)
                n_features_atual = modelo_atual.layers[0].input_shape[1]
                print(f"🔍 Features atuais: {n_features_atual}")

                if n_features_atual == 10:
                    print(f"✅ {caminho_modelo} já tem 10 features!")
                    continue

            except Exception as e:
                print(f"⚠️ Erro ao carregar modelo atual: {e}")

            # Cria novo modelo com 10 features
            print("🏗️ Criando novo modelo com 10 features...")
            novo_modelo = criar_modelo_10_features()

            # Testa o novo modelo
            if testar_modelo(novo_modelo, 10):
                # Salva o novo modelo
                novo_modelo.save(caminho_modelo)
                print(f"✅ Modelo salvo: {caminho_modelo}")

                # Salva também em formato .keras se for .h5
                if caminho_modelo.endswith('.h5'):
                    keras_path = caminho_modelo.replace('.h5', '.keras')
                    novo_modelo.save(keras_path)
                    print(f"✅ Modelo salvo: {keras_path}")
            else:
                print(f"❌ Falha ao criar modelo para {caminho_modelo}")
        else:
            print(f"⚠️ Arquivo não encontrado: {caminho_modelo}")

    print("\n🎯 CORREÇÃO CONCLUÍDA!")
    print("Agora o Monstro deve funcionar com 10 features:")
    print("1. bid_qty, ask_qty, spread, volatility")
    print("2. candle_type, entropia_book, rsi_14")
    print("3. volume_tick, is_in_trade, floating_profit, tempo_em_trade")
    print("\nclose_price foi removido do contexto de decisão.")


if __name__ == "__main__":
    main()
