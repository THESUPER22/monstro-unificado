import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def rodar_backtest_win_vespera():
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

    print(f"Puxando 250 dias uteis com filtro de Fechamento da Vespera para {symbol}...")

    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=365)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)

    if rates is None or len(rates) == 0:
        print("Nenhum dado historico encontrado.")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    dias = df.index.normalize().unique()
    resultados = []
    
    contratos = 10
    valor_ponto_win = 0.20
    custo_total_trade = contratos * 1.20

    for i in range(10, len(dias)):
        dia_atual = dias[i]
        dia_anterior = dias[i-1]
        
        df_dia_anterior = df.loc[df.index.normalize() == dia_anterior]
        if df_dia_anterior.empty:
            continue
        fechamento_vespera = df_dia_anterior.iloc[-1]['close']

        h_0900 = dia_atual + timedelta(hours=9, minutes=0)
        h_0901 = dia_atual + timedelta(hours=9, minutes=1)
        h_0915 = dia_atual + timedelta(hours=9, minutes=15)

        try:
            candle_0900 = df.loc[h_0900]
            open_0900 = candle_0900['open']
            close_0900 = candle_0900['close']
            high_0900 = candle_0900['high']
            low_0900 = candle_0900['low']
            
            corpo = close_0900 - open_0900
            amplitude_0900 = high_0900 - low_0900

            dias_anteriores = dias[i-10:i]
            amps_prev = []
            for d_prev in dias_anteriores:
                h_prev = d_prev + timedelta(hours=9, minutes=0)
                if h_prev in df.index:
                    c_prev = df.loc[h_prev]
                    amps_prev.append(c_prev['high'] - c_prev['low'])
            
            med_amp = pd.Series(amps_prev).mean() if len(amps_prev) > 0 else 150.0
            if amplitude_0900 > (2.5 * med_amp):
                continue

            if abs(corpo) < 80.0:
                continue

            direcao = None
            if corpo > 0 and close_0900 > fechamento_vespera:
                direcao = "BUY"
            elif corpo < 0 and close_0900 < fechamento_vespera:
                direcao = "SELL"
            else:
                continue

            preco_entrada = df.loc[h_0901]['open']
            
            sl_preco = low_0900 if direcao == "BUY" else high_0900
            sl_pontos = abs(preco_entrada - sl_preco)

            tp_pontos = amplitude_0900
            tp_preco = preco_entrada + tp_pontos if direcao == "BUY" else preco_entrada - tp_pontos

            sub_df = df.loc[h_0901:h_0915]
            if sub_df.empty:
                continue

            preco_saida_tempo = sub_df.iloc[-1]['close']
            hit_sl = False
            hit_tp = False
            preco_saida_alvo = preco_saida_tempo

            for _, row in sub_df.iterrows():
                if direcao == "BUY":
                    if row['low'] <= sl_preco:
                        hit_sl = True
                        preco_saida_tempo = sl_preco
                        preco_saida_alvo = sl_preco
                        break
                    elif row['high'] >= tp_preco and not hit_tp:
                        hit_tp = True
                        preco_saida_alvo = tp_preco
                elif direcao == "SELL":
                    if row['high'] >= sl_preco:
                        hit_sl = True
                        preco_saida_tempo = sl_preco
                        preco_saida_alvo = sl_preco
                        break
                    elif row['low'] <= tp_preco and not hit_tp:
                        hit_tp = True
                        preco_saida_alvo = tp_preco

            pts_tempo = (preco_saida_tempo - preco_entrada) if direcao == "BUY" else (preco_entrada - preco_saida_tempo)
            lucro_r_tempo = (pts_tempo * valor_ponto_win * contratos) - custo_total_trade

            pts_alvo = (preco_saida_alvo - preco_entrada) if direcao == "BUY" else (preco_entrada - preco_saida_alvo)
            lucro_r_alvo = (pts_alvo * valor_ponto_win * contratos) - custo_total_trade

            resultados.append({
                'data': dia_atual.strftime('%Y-%m-%d'),
                'tipo': direcao,
                'fech_vespera': fechamento_vespera,
                'close_0900': close_0900,
                'corpo_0900': round(corpo, 0),
                'pts_tempo': round(pts_tempo, 0),
                'lucro_r_tempo': round(lucro_r_tempo, 2),
                'pts_alvo': round(pts_alvo, 0),
                'lucro_r_alvo': round(lucro_r_alvo, 2),
                'win_tempo': 1 if pts_tempo > 0 else 0,
                'win_alvo': 1 if pts_alvo > 0 else 0
            })

        except KeyError:
            continue

    mt5.shutdown()

    if not resultados:
        print("Nenhum trade atendeu aos criterios com o filtro da vespera.")
        return

    res_df = pd.DataFrame(resultados)

    total_trades = len(res_df)
    
    wins_t = res_df['win_tempo'].sum()
    win_rate_t = (wins_t / total_trades) * 100
    saldo_r_t = res_df['lucro_r_tempo'].sum()

    wins_a = res_df['win_alvo'].sum()
    win_rate_a = (wins_a / total_trades) * 100
    saldo_r_a = res_df['lucro_r_alvo'].sum()

    print("\n==================================================")
    print(f"BACKTEST MODELO C + FILTRO FECHAMENTO VESPERA")
    print("==================================================")
    print(f" Total de Trades Filtrados: {total_trades}")
    print("--------------------------------------------------")
    print(" SAIDA NO TEMPO (09:15):")
    print(f"   Win Rate:              {win_rate_t:.1f}% ({wins_t}W / {total_trades - wins_t}L)")
    print(f"   Saldo Liquido (R$):    R$ {saldo_r_t:.2f}")
    print("--------------------------------------------------")
    print(" SAIDA POR ALVO FIXO (1:1):")
    print(f"   Win Rate:              {win_rate_a:.1f}% ({wins_a}W / {total_trades - wins_a}L)")
    print(f"   Saldo Liquido (R$):    R$ {saldo_r_a:.2f}")
    print("==================================================\n")

    print("Ultimas 10 Execucoes:")
    print(res_df[['data', 'tipo', 'corpo_0900', 'pts_tempo', 'lucro_r_tempo', 'pts_alvo', 'lucro_r_alvo']].tail(10).to_string(index=False))

if __name__ == "__main__":
    rodar_backtest_win_vespera()
