import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def backtest_igual(sl_tp_pontos):
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

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
        h_0903 = dia_atual + timedelta(hours=9, minutes=3)

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
            
            # SL e TP IGUAIS
            sl_preco = preco_entrada - sl_tp_pontos if direcao == "BUY" else preco_entrada + sl_tp_pontos
            tp_preco = preco_entrada + sl_tp_pontos if direcao == "BUY" else preco_entrada - sl_tp_pontos

            sub_df = df.loc[h_0901:h_0903]
            if sub_df.empty:
                continue

            preco_saida = sub_df.iloc[-1]['close']
            motivo = "TEMPO_3MIN"

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
        return None

    res_df = pd.DataFrame(resultados)
    total_trades = len(res_df)
    wins = res_df['win'].sum()
    win_rate = (wins / total_trades) * 100
    saldo_r = res_df['lucro_r'].sum()

    tp_count = (res_df['motivo'] == "TAKE_PROFIT").sum()
    sl_count = (res_df['motivo'] == "STOP_LOSS").sum()
    tempo_count = (res_df['motivo'] == "TEMPO_3MIN").sum()

    return {
        'sl_tp': sl_tp_pontos,
        'trades': total_trades,
        'win_rate': win_rate,
        'saldo_r': saldo_r,
        'tp': tp_count,
        'sl': sl_count,
        'tempo': tempo_count,
        'wins': wins,
        'losses': total_trades - wins
    }

if __name__ == "__main__":
    print("="*60)
    print("TESTE SL=TP IGUAL (200pts vs 400pts) - WIN ABERTURA")
    print("="*60)
    
    for sl_tp in [200, 400]:
        r = backtest_igual(sl_tp)
        if r:
            print(f"\n--- SL=TP = {r['sl_tp']}pts ---")
            print(f" Trades:        {r['trades']}")
            print(f" Win Rate:      {r['win_rate']:.1f}% ({r['wins']}W / {r['losses']}L)")
            print(f" Saldo R$:      R$ {r['saldo_r']:.2f}")
            print(f" Take Profit:   {r['tp']}")
            print(f" Stop Loss:     {r['sl']}")
            print(f" Saida Tempo:   {r['tempo']}")
        else:
            print(f"\n--- SL=TP = {sltp}pts: Sem trades ---")
