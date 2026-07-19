# 🎯 MONSTRO SIMPLIFICADO - SEM LÓGICA DE TEMPO
# Versão para testar operação sem bug de timestamp

# Importar apenas as funções essenciais do monstro_unificado
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Modificar apenas a função de decisão da IA para não usar tempo
def prever_acao_sem_tempo(modelo, contexto, em_posicao=False):
    """Versão simplificada sem lógica de tempo"""
    from datetime import datetime
    import pandas as pd
    import numpy as np
    from sklearn.preprocessing import LabelEncoder
    
    FEATURE_COLUMNS = ["bid_qty", "ask_qty", "spread", "volatility", "candle_type", "entropia_book", "rsi_14", "volume_tick", "is_in_trade", "floating_profit", "tempo_em_trade", "delta_bid_ask"]
    
    df = pd.DataFrame([contexto])
    
    # Força a codificação de candle_type para número
    if 'candle_type' in df.columns:
        if not np.issubdtype(df['candle_type'].dtype, np.number):
            le = LabelEncoder()
            df['candle_type'] = le.fit_transform(df['candle_type'].astype(str))
    
    # Garante que todas as features são float
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    X_pred = df[FEATURE_COLUMNS].astype(float).values
    prob_buy = modelo.predict(X_pred, verbose=0)[0][0]
    
    # 🎯 LÓGICA SIMPLIFICADA SEM TEMPO
    if em_posicao:
        lucro_atual = contexto.get('floating_profit', 0.0)
        
        # Log da decisão a cada 15 segundos
        if datetime.now().second % 15 == 0:
            trend = "📈" if prob_buy > 0.6 else "📉" if prob_buy < 0.4 else "➖"
            pnl_status = "🟢" if lucro_atual > 10 else "🔴" if lucro_atual < -10 else "🟡"
            print(f"🧠 IA {trend}: Prob={prob_buy:.3f} | {pnl_status}P&L=R${lucro_atual:.2f}")
        
        # 🔻 APENAS SAÍDAS POR PREJUÍZO E LUCRO (sem tempo)
        if lucro_atual <= -40.0:  # Prejuízo crítico
            print(f"🚨 IA DECISÃO: SAIR POR PREJUÍZO CRÍTICO! P&L: R${lucro_atual:.2f}")
            return "FECHAR"
            
        if lucro_atual >= 50.0 and prob_buy < 0.4:  # Lucro alto + perda confiança
            print(f"💰 IA DECISÃO: REALIZAR LUCRO ALTO! P&L: R${lucro_atual:.2f}")
            return "FECHAR"
                
        if lucro_atual >= 25.0 and prob_buy < 0.2:  # Lucro moderado + sinal contrário
            print(f"💰 IA DECISÃO: LUCRO + SINAL CONTRÁRIO FORTE! P&L: R${lucro_atual:.2f}")
            return "FECHAR"
        
        # REMOVER COMPLETAMENTE A LÓGICA DE TEMPO
        return "MANTER"
    else:
        # Lógica original para entrada
        if prob_buy > 0.5:
            return "BUY"
        else:
            return "SELL"

if __name__ == "__main__":
    print("🎯 MONSTRO SEM TEMPO - Pronto para substituir a função no código principal")
    print("📋 Para usar: substitua 'prever_acao' por 'prever_acao_sem_tempo' no monstro_unificado.py") 