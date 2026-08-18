import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

def rodar_backtest():
    if not mt5.initialize():
        print("❌ Falha ao inicializar o MT5")
        return

    # Tenta selecionar o contrato atual do Mini Índice
    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        # Se falhar o WIN$, busca o WINV26
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

    print(f"🔍 Puxando dados históricos de M1 para {symbol}...")

    # Puxa os últimos 90 dias de candles de 1 minuto
    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=90)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)
    
    if rates is None or len(rates) == 0:
        print("❌ Nenhum dado histórico encontrado.")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    # Agrupa por dia
    dias = df.index.normalize().unique()
    
    resultados = []
    contratos = 10
    valor_ponto = 0.20  # R$ 0,20 por ponto no mini índice

    for dia in dias:
        # Define os horários do trade no dia
        h_entrada = dia + timedelta(hours=17, minutes=54)
        h_saida = dia + timedelta(hours=18, minutes=13)

        # Filtra os preços
        try:
            # Preço de abertura da compra às 17:54
            preco_entrada = df.loc[h_entrada]['open']
            
            # Preço de fechamento da zeragem às 18:13 (ou último preço disponível antes/no horário)
            sub_df = df.loc[h_entrada:h_saida]
            if sub_df.empty:
                continue
            
            preco_saida = sub_df.iloc[-1]['close']
            
            # Resultado em pontos e financeiro
            pontos = preco_saida - preco_entrada
            lucro_bruto = pontos * valor_ponto * contratos
            custo_est = 4.00  # Custo estimado de B3/corretagem para 10 minis (girar 20 ordens)
            lucro_liquido = lucro_bruto - custo_est

            resultados.append({
                'data': dia.strftime('%Y-%m-%d'),
                'entrada_1754': preco_entrada,
                'saida_1813': preco_saida,
                'pontos': pontos,
                'lucro_bruto': lucro_bruto,
                'lucro_liquido': lucro_liquido,
                'win': 1 if pontos > 0 else 0
            })
        except KeyError:
            # Dia sem candle no horário exato (ex: feriado, final de semana ou sem negócios)
            continue

    mt5.shutdown()

    if not resultados:
        print("⚠️ Nenhum trade foi executado no período filtrado.")
        return

    res_df = pd.DataFrame(resultados)

    # --- MÉTRICAS DO BACKTEST ---
    total_trades = len(res_df)
    wins = res_df['win'].sum()
    losses = total_trades - wins
    win_rate = (wins / total_trades) * 100
    saldo_pontos = res_df['pontos'].sum()
    saldo_financeiro = res_df['lucro_liquido'].sum()
    media_pontos = res_df['pontos'].mean()
    max_gain = res_df['lucro_liquido'].max()
    max_loss = res_df['lucro_liquido'].min()

    print("\n==================================================")
    print(f"📊 RESULTADO DO BACKTEST — COMPRA 10 WIN (17:54 -> 18:13)")
    print("==================================================")
    print(f" Ativo Analisado:         {symbol}")
    print(f" Período Avaliado:        {res_df['data'].min()} até {res_df['data'].max()}")
    print(f" Total de Dias/Trades:   {total_trades}")
    print(f" Vitórias (Wins):         {wins} ({win_rate:.1f}%)")
    print(f" Derrotas (Losses):       {losses}")
    print(f" Saldo Total em Pontos:   {saldo_pontos:.0f} pts")
    print(f" Saldo Líquido Total:     R$ {saldo_financeiro:.2f}")
    print(f" Média por Trade:         {media_pontos:.1f} pts (R$ {media_pontos * 2:.2f})")
    print(f" Maior Gain Único:        R$ {max_gain:.2f}")
    print(f" Maior Loss Único:        R$ {max_loss:.2f}")
    print("==================================================\n")

    # Mostra os últimos 10 dias de execução
    print("📋 Últimas 10 Sessões:")
    print(res_df[['data', 'entrada_1754', 'saida_1813', 'pontos', 'lucro_liquido']].tail(10).to_string(index=False))

if __name__ == "__main__":
    rodar_backtest()
