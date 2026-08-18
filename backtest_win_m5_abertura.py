import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def rodar_backtest_m5():
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

    print(f"Puxando 250 dias uteis para Backtest do Candle M5 (09:00-09:05) em {symbol}...")

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

    for dia_atual in dias:
        h_inicio = dia_atual + timedelta(hours=9, minutes=0)
        h_fim_m5 = dia_atual + timedelta(hours=9, minutes=4)
        h_entrada = dia_atual + timedelta(hours=9, minutes=5)
        h_limite_tempo = dia_atual + timedelta(hours=9, minutes=30)

        try:
            m5_candles = df.loc[h_inicio:h_fim_m5]
            if len(m5_candles) < 5:
                continue

            open_m5 = m5_candles.iloc[0]['open']
            close_m5 = m5_candles.iloc[-1]['close']
            high_m5 = m5_candles['high'].max()
            low_m5 = m5_candles['low'].min()

            corpo = close_m5 - open_m5
            amplitude_m5 = high_m5 - low_m5

            if abs(corpo) < 100.0:
                continue

            direcao = "BUY" if corpo > 0 else "SELL"
            preco_entrada = df.loc[h_entrada]['open']

            sl_preco = (low_m5 - 20) if direcao == "BUY" else (high_m5 + 20)
            sl_pontos = abs(preco_entrada - sl_preco)

            tp_1to1 = preco_entrada + amplitude_m5 if direcao == "BUY" else preco_entrada - amplitude_m5
            tp_2to1 = preco_entrada + (amplitude_m5 * 2) if direcao == "BUY" else preco_entrada - (amplitude_m5 * 2)

            sub_df = df.loc[h_entrada:h_limite_tempo]
            if sub_df.empty:
                continue

            preco_saida_1to1 = sub_df.iloc[-1]['close']
            for _, row in sub_df.iterrows():
                if direcao == "BUY":
                    if row['low'] <= sl_preco:
                        preco_saida_1to1 = sl_preco
                        break
                    elif row['high'] >= tp_1to1:
                        preco_saida_1to1 = tp_1to1
                        break
                else:
                    if row['high'] >= sl_preco:
                        preco_saida_1to1 = sl_preco
                        break
                    elif row['low'] <= tp_1to1:
                        preco_saida_1to1 = tp_1to1
                        break

            preco_saida_2to1 = sub_df.iloc[-1]['close']
            for _, row in sub_df.iterrows():
                if direcao == "BUY":
                    if row['low'] <= sl_preco:
                        preco_saida_2to1 = sl_preco
                        break
                    elif row['high'] >= tp_2to1:
                        preco_saida_2to1 = tp_2to1
                        break
                else:
                    if row['high'] >= sl_preco:
                        preco_saida_2to1 = sl_preco
                        break
                    elif row['low'] <= tp_2to1:
                        preco_saida_2to1 = tp_2to1
                        break

            pts_1to1 = (preco_saida_1to1 - preco_entrada) if direcao == "BUY" else (preco_entrada - preco_saida_1to1)
            lucro_1to1 = (pts_1to1 * valor_ponto_win * contratos) - custo_total_trade

            pts_2to1 = (preco_saida_2to1 - preco_entrada) if direcao == "BUY" else (preco_entrada - preco_saida_2to1)
            lucro_2to1 = (pts_2to1 * valor_ponto_win * contratos) - custo_total_trade

            resultados.append({
                'data': dia_atual.strftime('%Y-%m-%d'),
                'tipo': direcao,
                'amp_m5': round(amplitude_m5, 0),
                'sl_pts': round(sl_pontos, 0),
                'lucro_1to1': round(lucro_1to1, 2),
                'lucro_2to1': round(lucro_2to1, 2),
                'win_1to1': 1 if pts_1to1 > 0 else 0,
                'win_2to1': 1 if pts_2to1 > 0 else 0
            })

        except KeyError:
            continue

    mt5.shutdown()

    if not resultados:
        print("Nenhum trade atendeu aos criterios M5.")
        return

    res_df = pd.DataFrame(resultados)
    total_trades = len(res_df)

    wins_1 = res_df['win_1to1'].sum()
    win_rate_1 = (wins_1 / total_trades) * 100
    saldo_1 = res_df['lucro_1to1'].sum()

    wins_2 = res_df['win_2to1'].sum()
    win_rate_2 = (wins_2 / total_trades) * 100
    saldo_2 = res_df['lucro_2to1'].sum()

    print("\n==================================================")
    print(f"BACKTEST ABERTURA M5 (09:00-09:05) - WIN")
    print("==================================================")
    print(f" Total de Trades Processados: {total_trades}")
    print("--------------------------------------------------")
    print(" ALVO PROJETADO 1:1 (Amplitude do M5):")
    print(f"   Win Rate:              {win_rate_1:.1f}% ({wins_1}W / {total_trades - wins_1}L)")
    print(f"   Saldo Liquido (R$):    R$ {saldo_1:.2f}")
    print("--------------------------------------------------")
    print(" ALVO PROJETADO 2:1 (2x Amplitude M5):")
    print(f"   Win Rate:              {win_rate_2:.1f}% ({wins_2}W / {total_trades - wins_2}L)")
    print(f"   Saldo Liquido (R$):    R$ {saldo_2:.2f}")
    print("==================================================\n")

if __name__ == "__main__":
    rodar_backtest_m5()
