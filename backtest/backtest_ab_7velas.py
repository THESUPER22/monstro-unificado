#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest A/B - Estrategia 7 Velas no WDO (M15) com dados reais MT5 (M1).
Comparacao justa: mesmos dias, mesmos dados; SL/TP por primeiro toque.

Modelo A (Monstro atual): majority 9 velas M15 + Gatekeeper Dual (CVD + VWAP) + SL8/TP10.
Modelo B (Disclaimer varejo): 7 velas consecutivas mesma cor + RSI(14) extremo + fechamento
                              fora da banda de Bollinger(20,2) + stop atras do pavio.
"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from time import time as _time

SYMBOL = "WDO@"          # contínuo do Mini Impulso; troque para 'WDOV26' se usar contrato mensal
NUM_CANDLES = 200000     # M1 (352 dias uteis de pregao 2025-04 -> 2026-08)
PREGAO_INICIO = "09:00"
PREGAO_FIM = "17:30"
VLP_5CC = 50.0

SL_A = 8.0
TP_A = 10.0


def rsi_series(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1 / period, adjust=False).mean()
    al = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def bollinger(close, period=20, dev=2.0):
    mid = close.rolling(period).mean()
    sd = close.rolling(period).std()
    return mid + dev * sd, mid - dev * sd


def init_mt5():
    if not mt5.initialize():
        print("[ERRO] MT5:", mt5.last_error())
        return False
    mt5.symbol_select(SYMBOL, True)
    return True


def load_m1():
    t0 = _time()
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, NUM_CANDLES)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"sem dados M1: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['hm'] = df['time'].dt.strftime('%H:%M')
    df = df[(df['hm'] >= PREGAO_INICIO) & (df['hm'] <= PREGAO_FIM)].copy()
    df['date'] = df['time'].dt.date
    # proxy de agressao (delta por volume)
    df['dir'] = np.where(df['close'] >= df['open'], 1, -1)
    df['candle_delta'] = df['real_volume'] * df['dir']
    df['delta_15'] = df['candle_delta'].rolling(15, min_periods=1).sum()
    # vwap diaria
    df['typical'] = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = df['typical'] * df['real_volume']
    df['cum_pv'] = df.groupby('date')['pv'].cumsum()
    df['cum_vol'] = df.groupby('date')['real_volume'].cumsum()
    df['vwap'] = df['cum_pv'] / df['cum_vol']
    print(f"[OK] {len(df)} candles M1 carregados em {_time()-t0:.1f}s")
    return df


def build_m15(df):
    """Agrega M1 em velas M15 alinhadas por relogio dentro de cada dia."""
    d = df.set_index('time')
    g = d.groupby([d.index.date, d.index.floor('15min')])
    m = pd.DataFrame({
        'open': g['open'].first(),
        'high': g['high'].max(),
        'low': g['low'].min(),
        'close': g['close'].last(),
        'vol': g['real_volume'].sum(),
        'delta': g['candle_delta'].sum(),
    })
    m.index = m.index.set_names(['data', 't15'])
    return m.sort_index()


def simular_primeiro_toque(df_dia_m1, sinal, preco_ent, sl, tp, inicio_dt, stop_entrada=None):
    """First-touch SL/TP. Se stop_entrada dado (stop order), exige que o mercado
    toque esse preco primeiro para o trade entrar; se nao tocar, retorna 'NAO'.
    Posicao aberta no fim do dia e marcada a mercado no ultimo close."""
    fut = df_dia_m1[df_dia_m1['time'] > inicio_dt].sort_values('time')
    entrou = stop_entrada is None
    for _, c in fut.iterrows():
        if not entrou:
            if sinal == 'BUY':
                if c['high'] >= stop_entrada:
                    entrou = True
                    preco_ent = stop_entrada
                elif c['low'] < stop_entrada - 1.0:
                    return 'NAO'
            else:
                if c['low'] <= stop_entrada:
                    entrou = True
                    preco_ent = stop_entrada
                elif c['high'] > stop_entrada + 1.0:
                    return 'NAO'
            if not entrou:
                continue
        if sinal == 'BUY':
            if c['high'] >= preco_ent + tp:
                return tp
            if c['low'] <= preco_ent - sl:
                return -sl
        else:
            if c['low'] <= preco_ent - tp:
                return tp
            if c['high'] >= preco_ent + sl:
                return -sl
    # fim do dia: mark-to-market no ultimo close
    if fut.empty or not entrou:
        return None
    ultimo = float(fut['close'].iloc[-1])
    pnl = (ultimo - preco_ent) if sinal == 'BUY' else (preco_ent - ultimo)
    return pnl


def main():
    if not init_mt5():
        return
    df_m1 = load_m1()
    m15 = build_m15(df_m1)
    datas = sorted(set(x[0] for x in m15.index))
    print(f"Janela: {datas[0]} a {datas[-1]} | {len(datas)} dias uteis")

    # RSI/Bollinger na serie M15 contínua (por data ordenada)
    closes = m15['close'].reset_index(drop=True)
    ub, lb = bollinger(closes, 20, 2.0)
    rsi = rsi_series(closes, 14)
    m15 = m15.copy()
    m15['ub'] = ub.values
    m15['lb'] = lb.values
    m15['rsi'] = rsi.values
    m15['seq'] = np.arange(len(m15))

    resultados = []

    for d in datas:
        dia = m15.xs(d, level='data')
        df_dia_m1 = df_m1[df_m1['date'] == d]

        # ---------------- MODELO A ----------------
        if len(dia) >= 10:
            velas9 = dia.iloc[:9]
            vela_entrada = dia.iloc[9]  # 8a vela M15 = 11:15 (bucket 09:00+9*15)
            ups = int((velas9['close'] > velas9['open']).sum())
            downs = int((velas9['close'] < velas9['open']).sum())
            sinal = 'BUY' if ups > downs else 'SELL'
            preco_ent = float(vela_entrada['open'])
            inicio_dt = vela_entrada.name
            # Gatekeeper: delta acumulada + vwap no candle de entrada
            candle_entrada = df_dia_m1[df_dia_m1['hm'] == '11:15']
            if len(candle_entrada) > 0:
                ce = candle_entrada.iloc[0]
                cvd = ce['delta_15']
                gate_cvd = (cvd > 0 and sinal == 'BUY') or (cvd < 0 and sinal == 'SELL')
                gate_vwap = (ce['close'] > ce['vwap']) if sinal == 'BUY' else (ce['close'] < ce['vwap'])
                executar = gate_cvd and gate_vwap
                pts = simular_primeiro_toque(df_dia_m1, sinal, preco_ent, SL_A, TP_A, inicio_dt) if executar else None
                resultados.append(dict(modelo='A', data=d, sinal=sinal,
                                       executar=bool(executar), pts=pts))

        # ---------------- MODELO B ----------------
        # Janelas estendidas do disclaimer: 10:15-12:30 e 14:00-16:30
        # Avalia apos CADA vela da janela: 7 velas consecutivas da mesma cor
        # (intra-dia) + RSI extremo + fechamento fora da banda.
        jan_b = [("10:15", "12:30"), ("14:00", "16:30")]
        idx_dia = dia.index
        times_dia = [t.strftime("%H:%M") for t in idx_dia]
        for h_inicio, h_fim in jan_b:
            sinal_emitido = False
            for j, tstr in enumerate(times_dia):
                if sinal_emitido:
                    break  # 1 sinal por janela/dia
                if not (h_inicio <= tstr <= h_fim):
                    continue
                if j < 7:
                    continue
                bloco = dia.iloc[j-6:j+1]  # 7 velas terminando na atual
                if len(bloco) < 7:
                    continue
                cores = [1 if c > o else 0 for c, o in
                         zip(bloco['close'], bloco['open'])]
                if not all(c == cores[0] for c in cores):
                    continue
                cor = cores[0]
                fech7 = float(bloco['close'].iloc[-1])
                rsi7 = float(bloco['rsi'].iloc[-1])
                ub7 = float(bloco['ub'].iloc[-1])
                lb7 = float(bloco['lb'].iloc[-1])
                if np.isnan(rsi7) or np.isnan(ub7):
                    continue
                sinal_b = 'BUY' if cor == 1 else 'SELL'  # momentum continuacao
                if sinal_b == 'BUY':
                    filtro = fech7 > ub7 and rsi7 > 70  # 7 verdes + overbought forte
                    stop_entrada = float(bloco['high'].max()) + 0.5  # BUY STOP acima
                    sl_lvl = float(bloco['low'].min()) - 1.0         # SL abaixo do range
                else:
                    filtro = fech7 < lb7 and rsi7 < 30  # 7 vermelhas + oversold forte
                    stop_entrada = float(bloco['low'].min()) - 0.5  # SELL STOP abaixo
                    sl_lvl = float(bloco['high'].max()) + 1.0       # SL acima do range
                preco_ent = stop_entrada
                stop_b = abs(preco_ent - sl_lvl)
                tp_b = stop_b  # alvo = 1:1 com o stop
                sinal_emitido = True
                if j + 1 >= len(dia):
                    continue
                inicio_dt = dia.index[j + 1]
                pts_b = None
                if filtro:
                    pts_b = simular_primeiro_toque(df_dia_m1, sinal_b, preco_ent,
                                                   stop_b, tp_b, inicio_dt,
                                                   stop_entrada=stop_entrada)
                resultados.append(dict(modelo='B', data=d, sinal=sinal_b,
                                       executar=bool(filtro), pts=pts_b))

    dfr = pd.DataFrame(resultados)
    print("\n" + "=" * 70)
    for modelo, nome in [('A', 'MODELO A - Monstro (majority 9v + Gatekeeper Dual + SL8/TP10)'),
                         ('B', 'MODELO B - Varejo (7 velas mesma cor + RSI + Bollinger)')]:
        sub = dfr[dfr['modelo'] == modelo]
        execs = sub[sub['executar']]
        print(f"\n--- {nome} | {modelo} ---")
        print(f"Sinais: {len(sub)} | Executados: {len(execs)} | Filtrados(gate): {len(sub)-len(execs)}")
        if execs.empty:
            print("  (nenhum trade executado)")
            continue
        # Modelo B usa stop-order: pts 'NAO' = stop de entrada nunca disparou
        if execs['pts'].isin(['NAO']).any():
            naodisp = int((execs['pts'] == 'NAO').sum())
            execs = execs[execs['pts'] != 'NAO']
            print(f"  stop de entrada NAO disparou (trade nao ocorreu): {naodisp}")
        if execs.empty:
            print("  (nenhum trade de fato entrou)")
            continue
        wins = int((execs['pts'] > 0).sum())
        losses = int((execs['pts'] < 0).sum())
        sem_encosto = int(execs['pts'].isna().sum())
        ptsv = execs['pts'].dropna()
        pnl = float(ptsv.sum()) * VLP_5CC
        gp = float(ptsv[ptsv > 0].sum()) * VLP_5CC
        gl = float(abs(ptsv[ptsv < 0].sum())) * VLP_5CC
        pf = gp / gl if gl > 0 else float('inf')
        cum = ptsv.cumsum()
        mdd = float((cum.cummax() - cum).max()) * VLP_5CC
        wr = wins / (wins + losses) * 100 if (wins + losses) else 0
        print(f"Executados: {len(execs)} | Wins: {wins} | Loss: {losses} | sem-encosto: {sem_encosto}")
        print(f"WR (com encosto): {wr:.1f}%")
        print(f"PnL 5CC: R$ {pnl:,.0f} | PF: {pf:.2f} | MaxDD: R$ {mdd:,.0f}")
    mt5.shutdown()
    print("\n[Fim]")


if __name__ == '__main__':
    main()