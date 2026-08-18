import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def rodar_backtest_2min():
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

    print(f"Puxando 250 dias uteis (Alvo 200 pts / Tempo Max 2 min)...")

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
        h_0900 = dia_atual + timedelta(hours=9, minutes=0)
        h_0901 = dia_atual + timedelta(hours=9, minutes=1)
        h_0902 = dia_atual + timedelta(hours=9, minutes=2)

        try:
            candle_0900 = df.loc[h_0900]
            open_0900 = candle_0900['open']
            close_0900 = candle_0900['close']
            high_0900 = candle_0900['high']
            low_0900 = candle_0900['low']
            
            corpo = close_0900 - open_0900
            
            if abs(corpo) < 80.0:
                continue

            direcao = "BUY" if corpo > 0 else "SELL"
            preco_entrada = df.loc[h_0901]['open']
            
            sl_preco = low_0900 if direcao == "BUY" else high_0900
            
            tp_pontos = 200.0
            tp_preco = preco_entrada + tp_pontos if direcao == "BUY" else preco_entrada - tp_pontos

            sub_df = df.loc[h_0901:h_0902]
            if sub_df.empty:
                continue

            preco_saida = sub_df.iloc[-1]['close']
            motivo = "TEMPO_2MIN"

            for _, row in sub_df.iterrows():
                if direcao == "BUY":
                    if row['low'] <= sl_preco:
                        preco_saida = sl_preco
                        motivo = "STOP_LOSS"
                        break
                    elif row['high'] >= tp_preco:
                        preco_saida = tp_preco
                        motivo = "TAKE_PROFIT"
                        break
                elif direcao == "SELL":
                    if row['high'] >= sl_preco:
                        preco_saida = sl_preco
                        motivo = "STOP_LOSS"
                        break
                    elif row['low'] <= tp_preco:
                        preco_saida = tp_preco
                        motivo = "TAKE_PROFIT"
                        break

            pts = (preco_saida - preco_entrada) if direcao == "BUY" else (preco_entrada - preco_saida)
            lucro_r = (pts * valor_ponto_win * contratos) - custo_total_trade

            resultados.append({
                'data': dia_atual.strftime('%Y-%m-%d'),
                'tipo': direcao,
                'motivo': motivo,
                'pts': round(pts, 0),
                'lucro_r': round(lucro_r, 2),
                'win': 1 if pts > 0 else 0
            })

        except KeyError:
            continue

    mt5.shutdown()

    if not resultados:
        print("Nenhum trade atendeu aos criterios.")
        return

    res_df = pd.DataFrame(resultados)
    total_trades = len(res_df)
    wins = res_df['win'].sum()
    win_rate = (wins / total_trades) * 100
    saldo_r = res_df['lucro_r'].sum()

    tp_count = (res_df['motivo'] == "TAKE_PROFIT").sum()
    sl_count = (res_df['motivo'] == "STOP_LOSS").sum()
    tempo_count = (res_df['motivo'] == "TEMPO_2MIN").sum()

    print("\n==================================================")
    print(f"BACKTEST MODELO C (ALVO 200 PTS / MAX 2 MIN)")
    print("==================================================")
    print(f" Total de Trades:       {total_trades}")
    print(f" Win Rate:              {win_rate:.1f}% ({wins}W / {total_trades - wins}L)")
    print(f" Saldo Liquido (R$):    R$ {saldo_r:.2f}")
    print("--------------------------------------------------")
    print(f" Detalhamento de Saidas:")
    print(f"   Alvo 200 pts atingido:  {tp_count}")
    print(f"   Stop Loss atingido:     {sl_count}")
    print(f"   Saida por Tempo (2m):   {tempo_count}")
    print("==================================================\n")

if __name__ == "__main__":
    rodar_backtest_2min()
