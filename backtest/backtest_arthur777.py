#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Profundo — Estratégia Arthur 777 (3 EMAs + Deslocamento de Abertura)
Ativos: WIN (M15) e WDO (M15) | 5 Contratos | Custos Reais XP RLP
Cenários: A (Tendência) e B (Scalper)
"""

import os
import json
import csv
import sys
from datetime import datetime, time
from typing import List, Dict, Optional
from dataclasses import dataclass

import pandas as pd
import numpy as np

# Adicionar path do projeto
sys.path.insert(0, r'C:\AIOFEN')

# Importar função de custo real
from sete_velas_util import calcular_custo_trade, _carregar_custos

# ============================================================
# CONFIGURAÇÕES
# ============================================================

DATA_DIR = r'C:\AIOFEN\backtest\dados_mt5'
OUT_DIR = r'C:\AIOFEN\backtest\resultados'
os.makedirs(OUT_DIR, exist_ok=True)

ARQUIVOS_M5 = {
    'WDO': r'C:\AIOFEN\backtest\dados_mt5\WDOU26_M5.csv',
    'WIN': r'C:\AIOFEN\backtest\dados_mt5\WINV26_M5.csv',
}

# Carregar custos do config
_custos = _carregar_custos()

@dataclass
class Trade:
    data: str
    ativo: str
    hora_entrada: str
    tipo: str          # BUY/SELL
    entrada: float
    sl: float
    tp: float
    saida: float
    pts: float
    pnl_bruto: float
    custo: float
    pnl_liquido: float
    saida_tipo: str    # TP/SL/EOD
    duracao_min: int

class Arthur777Backtest:
    def __init__(self, ativo='WDO', cenario='A'):
        self.ativo = ativo
        self.cenario = cenario  # 'A' (Tendência) ou 'B' (Scalper)
        self.custos = _carregar_custos()
        
        # Parâmetros por cenário
        if ativo == 'WIN':
            self.sl_pts = 400 if cenario == 'A' else 400
            self.tp_pts = 1500 if cenario == 'A' else 100
            self.deslocamento_pts = 700
            self.tick_size = 0.5
            self.ticks_por_ponto = 2
            self.valor_ponto = 5.0
            self.custo_trade = 1.25
            self.slippage_pts = 1.0
        else:  # WDO
            self.sl_pts = 10 if cenario == 'A' else 10
            self.tp_pts = 35 if cenario == 'A' else 3
            self.deslocamento_pts = 15
            self.tick_size = 0.5
            self.ticks_por_ponto = 2000
            self.valor_ponto = 50.0
            self.custo_trade = 4.0
            self.slippage_pts = 0.5
            
        self.lote = 5
        self.custos_cfg = _carregar_custos().get('WDO' if ativo=='WDO' else 'WIN', {})
    
    def resample_m5_para_m15(self, df_m5: pd.DataFrame) -> pd.DataFrame:
        """Resample M5 -> M15 (3 velas M5 = 1 M15)"""
        df = df_m5.copy()
        # Se 'time' é o índice, resetar para coluna
        if df.index.name == 'time' or 'time' not in df.columns:
            df = df.reset_index()
        # Garantir que 'time' seja datetime
        if not pd.api.types.is_datetime64_any_dtype(df['time']):
            df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')
        # Resample 5min -> 15min (3 barras)
        m15 = df.resample('15min', label='right', closed='right').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'tick_volume': 'sum'
        }).dropna()
        return m15.reset_index()
    
    def calcular_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        return df
    
    def gerar_sinais(self, df: pd.DataFrame) -> pd.DataFrame:
        """Gera sinais baseados nas regras Arthur 777"""
        df = df.copy()
        
        # Abertura do dia (primeiro candle 09:00)
        df['data'] = df['time'].dt.date
        abertura_dia = df.groupby('data')['open'].first().rename('abertura_dia')
        df = df.merge(abertura_dia, left_on='data', right_index=True, how='left')
        
        # Deslocamento
        df['deslocamento_pts'] = (df['close'] - df['abertura_dia']) / self.tick_size
        
        # Filtro Tendência
        df['tendencia_alta'] = (df['close'] > df['ema9']) & (df['close'] > df['ema50']) & (df['close'] > df['ema200'])
        df['tendencia_baixa'] = (df['close'] < df['ema9']) & (df['close'] < df['ema50']) & (df['close'] < df['ema200'])
        
        # Deslocamento abertura
        if self.ativo == 'WIN':
            df['desloc_long'] = df['deslocamento_pts'] >= self.deslocamento_pts
            df['desloc_short'] = df['deslocamento_pts'] <= -self.deslocamento_pts
        else:
            df['desloc_long'] = df['deslocamento_pts'] >= self.deslocamento_pts
            df['desloc_short'] = df['deslocamento_pts'] <= -self.deslocamento_pts
        
        # Gatilho força
        df['prev_high'] = df['high'].shift(1)
        df['prev_low'] = df['low'].shift(1)
        df['gatilho_long'] = df['close'] > df['prev_high']
        df['gatilho_short'] = df['close'] < df['prev_low']
        
        # Sinais finais
        df['sinal_long'] = df['tendencia_alta'] & df['desloc_long'] & df['gatilho_long']
        df['sinal_short'] = df['tendencia_baixa'] & df['desloc_short'] & df['gatilho_short']
        
        return df
    
    def simular_trades(self, df_sinais: pd.DataFrame) -> List[Trade]:
        """Simula trades com AVANÇO DE CURSOR TEMPORAL.

        Regras aplicadas (correções de auditoria 03/09):
          1. Sobreposição eliminada: após abrir uma posição, só um novo trade é
             considerado depois que o anterior fechou (SL/TP/EOD). Isso garante
             1 posição simultânea, como no MT5 real.
          2. Fator 2 corrigido: `pts` internamente é medido em TICKS (comparado
             com tick_size). Na conversão para PnL financeiro, convertemos
             ticks -> pontos reais de preço (pts * tick_size) antes de aplicar
             valor_por_ponto.

        Implementação: usa índices posicionais (ordinal) em vez de iterar todas
        as linhas, pulando o cursor após o fechamento de cada trade.
        """
        self._trades = []
        trades = []

        dati = df_sinais.reset_index(drop=True)
        n = len(dati)
        i = 0
        while i < n:
            row = dati.iloc[i]
            if not (row['sinal_long'] or row['sinal_short']):
                i += 1
                continue

            tipo = 'BUY' if row['sinal_long'] else 'SELL'
            # Entrada na abertura da próxima barra após o sinal
            if i + 1 < n:
                entrada = dati.iloc[i + 1]['open']
                inicio_varredura = i + 1  # a própria barra de entrada pode fechar TP/SL
                # cursor começa na barra de entrada (j >= inicio_varredura)
            else:
                entrada = row['close']
                inicio_varredura = n

            if tipo == 'BUY':
                sl = entrada - self.sl_pts * self.tick_size
                tp = entrada + self.tp_pts * self.tick_size
            else:
                sl = entrada + self.sl_pts * self.tick_size
                tp = entrada - self.tp_pts * self.tick_size

            pts = 0
            saida_tipo = 'EOD'
            saida_preco = entrada
            duracao_min = 0
            cursor = 0  # índice (relativo a inicio_varredura) onde a posição fecha

            # Varredura até TP/SL ou fim do dia
            for j in range(inicio_varredura, n):
                f_row = dati.iloc[j]
                duracao_min += 15
                cursor = j

                if tipo == 'BUY':
                    if f_row['low'] <= sl:
                        pts = -self.sl_pts
                        saida_tipo = 'SL'
                        saida_preco = sl
                        break
                    if f_row['high'] >= tp:
                        pts = self.tp_pts
                        saida_tipo = 'TP'
                        saida_preco = tp
                        break
                else:
                    if f_row['high'] >= sl:
                        pts = -self.sl_pts
                        saida_tipo = 'SL'
                        saida_preco = sl
                        break
                    if f_row['low'] <= tp:
                        pts = self.tp_pts
                        saida_tipo = 'TP'
                        saida_preco = tp
                        break
            else:
                # Fim da série (ou sem fechamento) -> EOD
                saida_tipo = 'EOD'
                if tipo == 'BUY':
                    saida_preco = dati.iloc[-1]['close']
                    pts = (dati.iloc[-1]['close'] - entrada) / self.tick_size
                else:
                    saida_preco = dati.iloc[-1]['close']
                    pts = (entrada - dati.iloc[-1]['close']) / self.tick_size
                cursor = n - 1

            # Convertir ticks -> pontos de preço (CORREÇÃO FATOR 2)
            # Internamente `pts` está em ticks; PnL financeiro usa pontos reais.
            pontos = pts * self.tick_size

            # Calcular custo real com pontos (não ticks)
            if pontos != 0:
                custo_info = calcular_custo_trade(self.ativo, round(pontos, 2))
                pnl_bruto = custo_info['pnl_bruto']
                pnl_liquido = custo_info['pnl_liquido']
                custo_trade = custo_info['custo_total']
            else:
                pnl_liquido = 0.0
                pnl_bruto = 0.0
                custo_trade = 0.0

            trade = Trade(
                data=row['time'].strftime('%Y-%m-%d'),
                ativo=self.ativo,
                hora_entrada=row['time'].strftime('%H:%M'),
                tipo=tipo,
                entrada=round(entrada, 1),
                sl=round(sl, 1),
                tp=round(tp, 1),
                saida=round(saida_preco, 1),
                pts=pts,  # mantém ticks no registro para rastreabilidade
                pnl_bruto=pnl_bruto,
                custo=custo_trade,
                pnl_liquido=pnl_liquido,
                saida_tipo=saida_tipo,
                duracao_min=duracao_min
            )
            trades.append(trade)
            self._trades.append(trade)

            # AVANÇO DE CURSOR: próxima avaliação só após a barra de fechamento
            i = inicio_varredura + (cursor - inicio_varredura) + 1 if cursor >= inicio_varredura else n

        return trades
    
    def executar(self, df_m5: pd.DataFrame) -> dict:
        # Pipeline completo
        df_m15 = self.resample_m5_para_m15(df_m5)
        df_emas = self.calcular_emas(df_m15)
        df_sinais = self.gerar_sinais(df_emas)
        trades = self.simular_trades(df_sinais)
        metricas = self.calcular_metricas(trades)
        
        # Salvar trades detalhados
        self._salvar_trades(trades)
        
        return self.calcular_metricas(trades)
    
    def _salvar_trades(self, trades: List[Trade]):
        if not trades:
            return
        out_path = os.path.join(OUT_DIR, f'arthur777_trades_{self.ativo}_{self.cenario}.csv')
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['data', 'ativo', 'hora_entrada', 'tipo', 'entrada', 'sl', 'tp', 
                       'saida', 'pts', 'pnl_bruto', 'custo', 'pnl_liquido', 
                       'saida_tipo', 'duracao_min'])
            for t in self._trades:
                w.writerow([
                    t.data, t.ativo, t.hora_entrada, t.tipo,
                    t.entrada, t.sl, t.tp, t.saida, t.pts,
                    t.pnl_bruto, t.custo, t.pnl_liquido,
                    t.saida_tipo, t.duracao_min
                ])
        print(f"Trades salvos em: {OUT_DIR}/arthur777_trades_{self.ativo}_{self.cenario}.csv")
    
    def calcular_metricas(self, trades: List[Trade]) -> dict:
        if not trades:
            return {'n': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'saldo': 0, 'profit_factor': 0, 'payoff': 0, 'max_drawdown': 0}
        
        wins = [t for t in trades if t.pnl_liquido > 0]
        losses = [t for t in trades if t.pnl_liquido < 0]
        be = [t for t in trades if t.pnl_liquido == 0]
        
        n = len(trades)
        wins_n = len(wins)
        losses_n = len(losses)
        be_n = len(be)
        
        saldo = sum(t.pnl_liquido for t in trades)
        win_rate = wins_n / len(trades) * 100 if trades else 0
        
        avg_gain = sum(t.pnl_liquido for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl_liquido for t in losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(t.pnl_liquido for t in wins) / sum(t.pnl_liquido for t in losses)) if losses else float('inf')
        payoff = avg_gain / abs(avg_loss) if avg_loss != 0 else float('inf')
        
        # Drawdown
        equity = 0
        peak = 0
        max_dd = 0
        for t in trades:
            equity += t.pnl_liquido
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        
        # Sequências
        max_wins_seq = 0
        max_losses_seq = 0
        curr_w = 0
        curr_l = 0
        for t in trades:
            if t.pnl_liquido > 0:
                curr_w += 1
                curr_l = 0
                max_wins_seq = max(max_wins_seq, curr_w)
            elif t.pnl_liquido < 0:
                curr_l += 1
                curr_w = 0
                max_losses_seq = max(max_losses_seq, curr_l)
            else:
                curr_w = 0
                curr_l = 0
        
        return {
            'n': len(trades),
            'wins': wins_n,
            'losses': losses_n,
            'be': len([t for t in trades if t.pnl_liquido == 0]),
            'win_rate': win_rate,
            'saldo': sum(t.pnl_liquido for t in trades),
            'avg_gain': avg_gain,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'payoff': payoff,
            'max_drawdown': max_dd,
            'max_wins_seq': max_wins_seq,
            'max_losses_seq': max_losses_seq
        }

def carregar_m5(ativo: str) -> pd.DataFrame:
    """Carrega dados M5 do arquivo CSV"""
    arquivo = {
        'WDO': r'C:\AIOFEN\backtest\dados_mt5\WDOU26_M5.csv',
        'WIN': r'C:\AIOFEN\backtest\dados_mt5\WINV26_M5.csv',
    }[ativo]
    
    df = pd.read_csv(arquivo, encoding='utf-8-sig')
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df.set_index('time')
    return df

def main():
    print("=" * 60)
    print("BACKTEST ARTHUR 777 - 3 EMAs + Deslocamento Abertura")
    print("=" * 60)
    
    resultados = []
    
    for ativo in ['WDO', 'WIN']:
        for cenario in ['A', 'B']:
            print(f"\n=== {ativo} | Cenário {cenario} ===")
            
            # Carregar dados M5
            df_m5 = carregar_m5(ativo)
            print(f"Dados carregados: {len(df_m5)} velas M5")
            
            # Executar backtest
            bt = Arthur777Backtest(ativo=ativo, cenario=cenario)
            metricas = bt.executar(df_m5)
            
            resultados.append({
                'ativo': ativo,
                'cenario': cenario,
                **metricas
            })
            
            # Imprimir resumo
            print(f"  Trades: {metricas['n']}")
            print(f"  Win Rate: {metricas['win_rate']:.1f}%")
            print(f"  Saldo: R$ {metricas['saldo']:.2f}")
            print(f"  Profit Factor: {metricas['profit_factor']:.2f}")
            print(f"  Payoff: {metricas['payoff']:.2f}")
            print(f"  Max DD: R$ {metricas['max_drawdown']:.2f}")
    
    # Salvar resultados
    df_resultados = pd.DataFrame(resultados)
    out_path = os.path.join(r'C:\AIOFEN\backtest\resultados', 'arthur777_resultados.csv')
    df_resultados.to_csv(out_path, index=False)
    print(f"\nResultados salvos em: {out_path}")
    
    print("\n=== BACKTEST CONCLUÍDO ===")
    return resultados

if __name__ == "__main__":
    main()