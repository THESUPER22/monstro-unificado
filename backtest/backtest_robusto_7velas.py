#!/usr/bin/env python3
"""
Backtest Robusto - Estratégia 7 Velas (Magic 7007) - Mini Dólar (WDO)
Validação Própria com Dados REAIS do MT5 (M1)
Comparação: ENTRADA SECA vs FILTRO DUAL (Delta 15min + VWAP)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, time
import os

# ============================================================
# CONFIGURAÇÕES
# ============================================================
SYMBOL = "WDO$"  # Ticker contínuo do Mini Dólar (ajuste conforme seu MT5)
TIMEFRAME = mt5.TIMEFRAME_M1
NUM_CANDLES = 50000  # ~35 dias úteis de M1

# Parâmetros da Estratégia
SL_PONTOS = 8.0
TP_PONTOS = 10.0
VALOR_POR_PONTO_5CC = 50.0  # 5 contratos x R$10/pontos
MAGIC = 7007

# Janelas de Entrada
JANELAS = {
    7: time(10, 45),   # V7 - 10:45 BRT
    9: time(11, 15)    # V9 - 11:15 BRT (Tiro Certo)
}

# Horário de pregão WDO (BRT)
PREGAO_INICIO = time(9, 0)
PREGAO_FIM = time(17, 30)

# Valor por ponto (5 contratos = R$ 50/pontos)
VALOR_POR_PONTO = 50.0

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def inicializar_mt5():
    """Inicializa conexão MT5"""
    if not mt5.initialize():
        print(f"[ERRO] Falha ao inicializar MT5: {mt5.last_error()}")
        return False
    print(f"[OK] MT5 inicializado - Build {mt5.version()}")
    
    if not mt5.symbol_select(SYMBOL, True):
        print(f"[ERRO] Falha ao selecionar {SYMBOL}: {mt5.last_error()}")
        return False
    print(f"[OK] Símbolo {SYMBOL} selecionado")
    return True


def extrair_dados_m1(simbolo, num_candles=50000):
    """Extrai candles M1 do MT5"""
    print(f"[INFO] Extraindo {num_candles} candles M1 de {simbolo}...")
    
    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, num_candles)
    if rates is None or len(rates) == 0:
        raise ValueError(f"Nenhum dado retornado do MT5 para {simbolo}: {mt5.last_error()}")
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['data'] = df['time'].dt.date
    df['hora_minuto'] = df['time'].dt.time
    
    # Filtra apenas horário de pregão (09:00-17:30 BRT)
    mask_pregao = (df['hora_minuto'] >= PREGAO_INICIO) & (df['hora_minuto'] <= PREGAO_FIM)
    df = df[mask_pregao].copy()
    
    print(f"[OK] {len(df)} candles M1 extraídos (pregão apenas)")
    return df


def calcular_features(df):
    """Calcula todas as features necessárias: Delta, CVD, VWAP, Delta 15min"""
    df = df.copy()
    
    # 1. Direção e Delta de agressão do candle
    df['direction'] = np.where(df['close'] >= df['open'], 1, -1)
    df['candle_delta'] = df['real_volume'] * df['direction']
    
    # 2. Delta Restrito Dinâmico (Rolling 15 minutos = 15 barras M1)
    df['delta_15min'] = df['candle_delta'].rolling(window=15, min_periods=1).sum()
    
    # 3. VWAP Diária (reset a cada dia)
    df['data'] = df['time'].dt.date
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = df['typical_price'] * df['real_volume']
    df['cum_pv'] = df.groupby('data')['pv'].cumsum()
    df['cum_vol'] = df.groupby('data')['real_volume'].cumsum()
    df['vwap'] = df['cum_pv'] / df['cum_vol']
    
    # Limpeza
    df.drop(columns=['pv', 'cum_pv', 'cum_vol', 'typical_price'], inplace=True)
    
    return df


def run_backtest():
    """Executa backtest completo"""
    print("=" * 60)
    print("BACKTEST ROBUSTO - 7 VELAS (Magic 7007) - WDO M1")
    print("Comparação: ENTRADA SECA vs FILTRO DUAL (Delta 15min + VWAP)")
    print("=" * 60)
    
    # 1. Inicializa MT5
    if not inicializar_mt5():
        return
    
    try:
        # 1. Extrai dados M1
        df_m1 = extrair_dados_m1(SYMBOL, NUM_CANDLES)
        
        # 2. Calcula features
        print("[INFO] Calculando features (Delta, CVD, VWAP, Delta 15min)...")
        df_m1 = calcular_features(df_m1)
        
        # 3. Identifica candles de gatilho (10:45 e 11:15)
        mask_1045 = df_m1['time'].dt.time == time(10, 45)
        mask_1115 = df_m1['time'].dt.time == time(11, 15)
        
        n_v7 = mask_1045.sum()
        n_v9 = mask_1115.sum()
        print(f"[INFO] Candles de gatilho: V7={n_v7} (10:45) + V9={n_v9} (11:15) = {n_v7 + n_v9}")
        
        # 4. Simula trades para ambos os modos
        trades = []
        
        # Candles de gatilho (10:45 e 11:15)
        candles_gatilho = df_m1[mask_1045 | mask_1115].copy()
        
        for idx, candle in candles_gatilho.iterrows():
            janela = 'V7' if candle['time'].time() == time(10, 45) else 'V9'
            data = candle['data']
            preco_ent = candle['close']
            delta_15 = candle['delta_15min']
            vwap = candle['vwap']
            candle_delta = candle['candle_delta']
            
            # Direção SECA (M1 apenas)
            dir_seca = 'COMPRA' if candle_delta >= 0 else 'VENDA'
            
            # Direção DUAL (Gatekeeper: Delta 15min + VWAP)
            dir_dual = None
            if delta_15 > 0 and candle['close'] > candle['vwap']:
                dir_dual = 'COMPRA'
            elif delta_15 < 0 and candle['close'] < candle['vwap']:
                dir_dual = 'VENDA'
            
            # Futuros do mesmo dia (após o candle de gatilho)
            futuros = df_m1[
                (df_m1['data'] == candle['data']) & 
                (df_m1['time'] > candle['time'])
            ].sort_values('time')
            
            if len(futuros) == 0:
                continue
            
            # Testa ambos os modos
            for modo, direcao in [('SECO', dir_seca), ('DUAL', dir_dual)]:
                if direcao is None:
                    continue
                    
                preco_ent = candle['close']
                resultado = None
                duracao = 0
                pnl_pts = 0
                
                for _, c in futuros.iterrows():
                    if c['data'] != candle['data']:
                        break
                    duracao += 1
                    
                    if direcao == 'COMPRA':
                        if c['high'] >= preco_ent + TP_PONTOS:
                            resultado = 'WIN'; pnl_pts = TP_PONTOS; break
                        elif c['low'] <= preco_ent - SL_PONTOS:
                            resultado = 'LOSS'; pnl_pts = -SL_PONTOS; break
                    else:
                        if c['low'] <= preco_ent - TP_PONTOS:
                            resultado = 'WIN'; pnl_pts = TP_PONTOS; break
                        elif c['high'] >= preco_ent + SL_PONTOS:
                            resultado = 'LOSS'; pnl_pts = -SL_PONTOS; break
                
                if resultado in ['WIN', 'LOSS']:
                    trades.append({
                        'data': candle['time'].date(),
                        'hora': candle['time'].time(),
                        'janela': 'V7' if candle['time'].time() == time(10, 45) else 'V9',
                        'modo': modo,
                        'direcao': direcao,
                        'resultado': resultado,
                        'pontos': pnl_pts,
                        'financeiro': pnl_pts * VALOR_POR_PONTO,
                        'duracao_min': duracao
                    })
        
        df_trades = pd.DataFrame(trades)
        
        # 5. Relatório
        gerar_relatorio_completo(df_trades)
        
    finally:
        mt5.shutdown()


def gerar_relatorio_completo(trades_df):
    """Gera relatório comparativo detalhado"""
    if trades_df.empty:
        print("[AVISO] Nenhum trade executado")
        return
    
    print("\n" + "=" * 80)
    print("RELATÓRIO DE BACKTEST - 7 VELAS (MAGIC 7007) - WDO M1")
    print("=" * 80)
    
    print(f"\nTotal de trades simulados: {len(trades_df)}")
    print(f"Período: {trades_df['data'].min()} a {trades_df['data'].max()}")
    print(f"Dias operados: {trades_df['data'].nunique()}")
    
    # Métricas por Janela x Modo
    for janela in ['V7', 'V9']:
        for modo in ['SECO', 'DUAL']:
            subset = trades_df[(trades_df['janela'] == janela) & (trades_df['modo'] == modo)]
            if len(subset) == 0:
                continue
            
            ops = len(subset)
            wins = (subset['resultado'] == 'WIN').sum()
            losses = (subset['resultado'] == 'LOSS').sum()
            wr = wins / ops * 100
            
            pnl = subset['financeiro'].sum()
            
            # Profit Factor
            gp = subset[subset['financeiro'] > 0]['financeiro'].sum()
            gl = abs(subset[subset['financeiro'] < 0]['financeiro'].sum())
            pf = gp / gl if gl > 0 else float('inf')
            
            # Max DD
            cum = subset['financeiro'].cumsum()
            dd = (cum.cummax() - cum).max()
            
            dur_med = subset['duracao_min'].mean()
            
            label = f"{janela} ({'10:45' if janela=='V7' else '11:15'}) | {modo}"
            print(f"\n{'='*60}")
            print(f" {janela} ({'10:45' if janela=='V7' else '11:15'}) | MODO: {modo}")
            print(f"{'='*60}")
            print(f"  Operações: {len(subset)}")
            print(f"  Win Rate: {wr:.1f}% ({wins}W / {losses}L)")
            print(f"  PnL Total: R$ {subset['financeiro'].sum():,.2f}")
            pf = subset[subset['financeiro']>0]['financeiro'].sum() / abs(subset[subset['financeiro']<0]['financeiro'].sum()) if (subset['financeiro']<0).any() else float('inf')
            print(f"  Profit Factor: {pf:.2f}")
            print(f"  Max Drawdown: R$ {dd:,.0f}")
            print(f"  Duração média: {dur_med:.1f} min")
    
    # Resumo comparativo
    print("\n" + "="*80)
    print("RESUMO COMPARATIVO: SECO vs DUAL (GATEKEEPER)")
    print("="*80)
    
    for janela in ['V7', 'V9']:
        seca = trades_df[(trades_df['janela']==janela) & (trades_df['modo']=='SECO')]
        dual = trades_df[(trades_df['janela']==janela) & (trades_df['modo']=='DUAL')]
        
        if len(seca) == 0 or len(dual) == 0:
            continue
            
        wr_seca = (seca['resultado']=='WIN').sum() / len(seca) * 100
        wr_dual = (dual['resultado']=='WIN').sum() / len(dual) * 100
        pnl_seca = seca['financeiro'].sum()
        pnl_dual = dual['financeiro'].sum()
        
        gp_s = seca[seca['financeiro']>0]['financeiro'].sum()
        gl_s = abs(seca[seca['financeiro']<0]['financeiro'].sum())
        pf_s = gp_s/gl_s if gl_s > 0 else float('inf')
        
        gp_d = dual[dual['financeiro']>0]['financeiro'].sum()
        gl_d = abs(dual[dual['financeiro']<0]['financeiro'].sum())
        pf_d = gp_d/gl_d if gl_d > 0 else float('inf')
        
        filt = len(seca) - len(dual)
        stops_ev = len(seca[seca['resultado']=='LOSS']) - len(dual[dual['resultado']=='LOSS'])
        
        print(f"\n{janela} ({'10:45' if janela=='V7' else '11:15'}):")
        print(f"  Ops:     SECO={len(seca):3d} | DUAL={len(dual):3d} | Filtrados: {len(seca)-len(dual):3d}")
        print(f"  WR:      SECO={wr_seca:5.1f}% | DUAL={wr_dual:5.1f}%")
        print(f"  PnL:     SECO=R${pnl_seca:>10,.0f} | DUAL=R${pnl_dual:>10,.0f}")
        print(f"  PF:      SECO={pf_s:.2f} | DUAL={pf_d:.2f}")
        print(f"  Filtrados: {len(seca)-len(dual)} sinais | Stops evitados: {len(seca[seca['resultado']=='LOSS']) - len(dual[dual['resultado']=='LOSS'])}")


if __name__ == "__main__":
    run_backtest()