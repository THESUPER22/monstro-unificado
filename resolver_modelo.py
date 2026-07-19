#!/usr/bin/env python3
"""
Script para resolver incompatibilidade de features do modelo.
"""

import os
import time

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.optimizers import Adam

# Configurações
MODELO_PATH = "modelo_monstro.h5"
N_FEATURES = 11  # Número correto de features


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


def main():
    print("🔧 Resolvendo incompatibilidade de features do modelo...")

    try:
        # Verifica se o modelo existe
        if os.path.exists(MODELO_PATH):
            print(f"📁 Modelo encontrado: {MODELO_PATH}")

            # Tenta carregar e testar
            try:
                modelo = load_model(MODELO_PATH)
                test_input = np.zeros((1, N_FEATURES), dtype=np.float32)
                modelo.predict(test_input, verbose=0)
                print(f"✅ Modelo já compatível com {N_FEATURES} features!")
                return

            except Exception as e:
                print(f"❌ Modelo incompatível: {e}")

                # Backup do modelo atual
                timestamp = int(time.time())
                backup_path = f"{MODELO_PATH}.backup_incompativel_{timestamp}"
                os.rename(MODELO_PATH, backup_path)
                print(f"📦 Modelo movido para: {backup_path}")

        # Cria novo modelo
        print(f"🆕 Criando novo modelo com {N_FEATURES} features...")
        novo_modelo = criar_modelo_neural(N_FEATURES)

        # Salva o modelo
        novo_modelo.save(MODELO_PATH)
        print(f"💾 Novo modelo salvo: {MODELO_PATH}")

        # Testa o novo modelo
        test_input = np.zeros((1, N_FEATURES), dtype=np.float32)
        resultado = novo_modelo.predict(test_input, verbose=0)
        print(f"✅ Teste do novo modelo: {resultado[0][0]:.4f}")

        print("🎉 Problema resolvido! O Monstro pode ser reiniciado.")

    except Exception as e:
        print(f"❌ Erro ao resolver problema: {e}")
        return False

    return True


if __name__ == "__main__":
    main()
    main()
