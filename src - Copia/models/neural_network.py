import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import os
from config.settings import N_FEATURES, LEARNING_RATE, MODELO_PATH

class NeuralNetwork:
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
        self.label_encoder = LabelEncoder()
        self.n_features = N_FEATURES
        
    def criar_modelo(self):
        """Cria um novo modelo neural."""
        modelo = Sequential()
        modelo.add(Dense(64, input_dim=self.n_features, activation='relu'))
        modelo.add(Dense(32, activation='relu'))
        modelo.add(Dense(1, activation='sigmoid'))
        modelo.compile(
            optimizer=Adam(learning_rate=LEARNING_RATE),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        self.model = modelo
        return modelo
    
    def carregar_modelo(self):
        """Carrega um modelo existente ou cria um novo."""
        if os.path.exists(MODELO_PATH):
            self.model = load_model(MODELO_PATH)
            return True
        self.criar_modelo()
        return False
    
    def salvar_modelo(self):
        """Salva o modelo atual."""
        if self.model:
            self.model.save(MODELO_PATH)
            return True
        return False
    
    def preparar_dados(self, df):
        """Prepara os dados para treino ou predição."""
        colunas_categoricas = ['candle_type']
        colunas_numericas = ['bid_qty', 'ask_qty', 'spread', 'volatility',
                            'entropia_book', 'rsi_14', 'volume_tick',
                            'is_in_trade', 'floating_profit', 'tempo_em_trade']
        
        # Normalização de dados numéricos
        df[colunas_numericas] = self.scaler.fit_transform(df[colunas_numericas])
        
        # Encoding de dados categóricos
        for col in colunas_categoricas:
            df[col] = self.label_encoder.fit_transform(df[col])
            
        X = df[colunas_numericas + colunas_categoricas]
        y = df['action'].apply(lambda x: 1 if x == 'BUY' else 0) if 'action' in df.columns else None
        
        return X, y
    
    def prever(self, contexto):
        """Faz uma previsão com base no contexto atual."""
        if not self.model:
            self.carregar_modelo()
            
        df = pd.DataFrame([contexto])
        df['action'] = 'BUY'  # dummy para manter shape
        X, _ = self.preparar_dados(df)
        
        previsao = self.model.predict(X, verbose=0)
        return 'BUY' if previsao[0][0] > 0.5 else 'SELL'
    
    def treinar(self, experiencias):
        """Treina o modelo com novas experiências."""
        if not experiencias:
            return False
            
        df_exp = pd.DataFrame([{
            **ctx,
            "action": ac,
            "reward": luc
        } for ctx, ac, luc in experiencias])
        
        # Limita perdas muito grandes
        df_exp["reward"] = df_exp["reward"].apply(lambda x: max(x, -50))
        
        X, y = self.preparar_dados(df_exp)
        sample_weight = df_exp["reward"] + 50  # Penaliza negativo, reforça positivo
        
        self.model.fit(
            X, y,
            epochs=1,
            verbose=0,
            sample_weight=sample_weight
        )
        
        self.salvar_modelo()
        return True 