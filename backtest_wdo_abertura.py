import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def rodar_backtest_wdo():
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WDOV26"
    if not mt5.symbol_select(symbol, True):
        print("Simbolo WDO nao encontrado.")
        mt5.shutdown()
        return

    print(f"Puxando dados historicos de M1 para {symbol} (ultimos 240 dias)...")

    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=240)
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
    valor_ponto_wdo = 10.0
    custo_por_cc = 1.20
    custo_total_trade = contratos * custo_por_cc

    for i in range(10, len(dias)):
        dia = dias[i]
        
        h_0900 = dia + timedelta(hours=9, minutes=0)
        h_0901 = dia + timedelta(hours=9, minutes=1)
        h_0915 = dia + timedelta(hours=9, minutes=15)

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
            
            med_amp = pd.Series(amps_prev).mean() if len(amps_prev) > 0 else 10.0
            
            if amplitude_0900 > (2.5 * med_amp):
                continue

            if abs(corpo) < 4.0:
                continue

            direcao = "BUY" if corpo > 0 else "SELL"
            preco_entrada = df.loc[h_0901]['open']
            
            sl_preco = low_0900 if direcao == "BUY" else high_0900
            sl_pontos = abs(preco_entrada - sl_preco)

            sub_df = df.loc[h_0901:h_0915]
            if sub_df.empty:
                continue

            preco_saida_tempo = sub_df.iloc[-1]['close']
            
            hit_sl = False
            for _, row in sub_df.iterrows():
                if direcao == "BUY" and row['low'] <= sl_preco:
                    hit_sl = True
                    preco_saida_tempo = sl_preco
                    break
                elif direcao == "SELL" and row['high'] >= sl_preco:
                    hit_sl = True
                    preco_saida_tempo = sl_preco
                    break

            if direcao == "BUY":
                pts = preco_saida_tempo - preco_entrada
            else:
                pts = preco_entrada - preco_saida_tempo

            lucro_bruto = pts * valor_ponto_wdo * contratos
            lucro_liquido = lucro_bruto - custo_total_trade

            resultados.append({
                'data': dia.strftime('%Y-%m-%d'),
                'tipo': direcao,
                'corpo_0900': round(corpo, 2),
                'sl_pts': round(sl_pontos, 2),
                'pts': round(pts, 2),
                'lucro_liquido': round(lucro_liquido, 2),
                'win': 1 if pts > 0 else 0,
                'hit_sl': 1 if hit_sl else 0
            })

        except KeyError:
            continue

    mt5.shutdown()

    if not resultados:
        print("Nenhum trade atendeu aos criterios no periodo.")
        return

    res_df = pd.DataFrame(resultados)

    total_trades = len(res_df)
    wins = res_df['win'].sum()
    win_rate = (wins / total_trades) * 100
    saldo_pts = res_df['pts'].sum()
    saldo_r = res_df['lucro_liquido'].sum()
    media_pts = res_df['pts'].mean()
    stops = res_df['hit_sl'].sum()

    print("\n==================================================")
    print(f"BACKTEST ABERTURA WDO - MODELO C MOMENTUM (10 MINIS)")
    print("==================================================")
    print(f" Ativo Analisado:         {symbol}")
    print(f" Total de Trades:         {total_trades} (em ~240 dias)")
    print(f" Taxa de Acerto (Win %):  {win_rate:.1f}% ({wins}W / {total_trades - wins}L)")
    print(f" Total de Stops Atingidos:{stops}")
    print(f" Saldo Acumulado Pontos:  {saldo_pts:.1f} pts")
    print(f" Saldo Liquido (R$):      R$ {saldo_r:.2f} (ja descontado R$1,20/cc)")
    print(f" Media por Trade (pts):   {media_pts:.2f} pts (R$ {media_pts * 100:.2f}/trade)")
    print("==================================================\n")

    print("Ultimas 10 Execucoes no WDO:")
    print(res_df[['data', 'tipo', 'corpo_0900', 'sl_pts', 'pts', 'lucro_liquido']].tail(10).to_string(index=False))

if __name__ == "__main__":
    rodar_backtest_wdo()
