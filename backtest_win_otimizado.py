import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import itertools

def rodar_backtest_otimizado():
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

    print(f"Puxando dados historicos de M1 para {symbol}...")

    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=90)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)
    
    if rates is None or len(rates) == 0:
        print("Nenhum dado historico encontrado.")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    dias = df.index.normalize().unique()
    valor_ponto = 0.20
    custo_por_trade = 1.20  # custo real: R$0,60 entrada + R$0,60 saida por contrato

    # === FASE 1: Otimizar JANELA DE HORARIO (1 cc) ===
    entradas = [(17, 50), (17, 52), (17, 54), (17, 56), (17, 58)]
    saidas = [(18, 10), (18, 13), (18, 15), (18, 18), (18, 20)]

    print("\n" + "="*70)
    print("FASE 1: OTIMIZACAO DA JANELA (1 contrato)")
    print("="*70)
    print(f"{'Entrada':<10} {'Saida':<10} {'Trades':<8} {'Win%':<8} {'Pts Total':<12} {'R$ Liquido':<14} {'Sharpe':<8}")
    print("-"*70)

    melhor_sharpe = -999
    melhor_janela = None
    resultados_janela = {}

    for (eh, em), (sh, sm) in itertools.product(entradas, saidas):
        if eh > sh or (eh == sh and em >= sm):
            continue
        
        trades = []
        for dia in dias:
            h_entrada = dia + timedelta(hours=eh, minutes=em)
            h_saida = dia + timedelta(hours=sh, minutes=sm)
            try:
                preco_entrada = df.loc[h_entrada]['open']
                sub_df = df.loc[h_entrada:h_saida]
                if sub_df.empty:
                    continue
                preco_saida = sub_df.iloc[-1]['close']
                pts = preco_saida - preco_entrada
                trades.append(pts)
            except (KeyError, KeyError):
                continue

        if len(trades) < 10:
            continue

        import numpy as np
        trades_arr = np.array(trades)
        wins = (trades_arr > 0).sum()
        total_pts = trades_arr.sum()
        media = trades_arr.mean()
        desvio = trades_arr.std() if trades_arr.std() > 0 else 1
        sharpe = (media / desvio) * (252 ** 0.5)  # anualizado
        custo_total = len(trades) * custo_por_trade  # R$1,20 por contrato por trade (já inclui entrada+saída)
        r_liquido = total_pts * valor_ponto - custo_total

        label = f"{eh}:{em:02d} -> {sh}:{sm:02d}"
        resultados_janela[label] = {
            'trades': len(trades), 'win_pct': wins/len(trades)*100,
            'pts': total_pts, 'r_liq': r_liquido, 'sharpe': sharpe,
            'media': media, 'desvio': desvio
        }

        print(f"{label:<20} {len(trades):<8} {wins/len(trades)*100:.1f}%   {total_pts:>6.0f} pts   R${r_liquido:>8.2f}   {sharpe:>6.2f}")

        if sharpe > melhor_sharpe:
            melhor_sharpe = sharpe
            melhor_janela = label

    print(f"\n>>> MELHOR JANELA: {melhor_janela} (Sharpe={melhor_sharpe:.2f})")

    # === FASE 2: OTIMIZAR NUMERO DE CONTRATOS na melhor janela ===
    print("\n" + "="*70)
    print("FASE 2: NUMERO IDEAL DE CONTRATOS")
    print("="*70)

    if melhor_janela:
        partes = melhor_janela.split(" -> ")
        eh, em = map(int, partes[0].split(":"))
        sh, sm = map(int, partes[1].split(":"))

        trades = []
        for dia in dias:
            h_entrada = dia + timedelta(hours=eh, minutes=em)
            h_saida = dia + timedelta(hours=sh, minutes=sm)
            try:
                preco_entrada = df.loc[h_entrada]['open']
                sub_df = df.loc[h_entrada:h_saida]
                if sub_df.empty:
                    continue
                preco_saida = sub_df.iloc[-1]['close']
                pts = preco_saida - preco_entrada
                trades.append(pts)
            except (KeyError, KeyError):
                continue

        import numpy as np
        trades_arr = np.array(trades)

        contratos_teste = [2]

        print(f"Janela: {melhor_janela} | Trades: {len(trades_arr)}")
        print(f"{'Contratos':<12} {'R$ Liquido':<14} {'R$/dia':<12} {'MaxDD R$':<14} {'Risco 5%':<14}")
        print("-"*66)

        for cc in contratos_teste:
            lucros = trades_arr * valor_ponto * cc
            custo_por_trade_cc = custo_por_trade * cc  # R$1,20 por contrato por trade (já inclui entrada+saída)
            liquidos = lucros - custo_por_trade_cc  # desconta custo de CADA trade
            total_liq = liquidos.sum()
            media_dia = total_liq / len(trades_arr)
            
            # Max Drawdown em R$
            acumulado = np.cumsum(liquidos)
            picos = np.maximum.accumulate(acumulado)
            drawdowns = picos - acumulado
            max_dd = drawdowns.max()

            # Risco de 5% do capital (supondo R$100k)
            capital = 100000
            risco_5pct = capital * 0.05

            print(f"{cc:>4}cc      R${total_liq:>10.2f}   R${media_dia:>7.2f}   -R${max_dd:>9.2f}   {'OK' if max_dd < risco_5pct else 'ALTO'}")

    # === FASE 3: TABELA COMPLETA COM TODAS AS JANELAS (mais dados) ===
    print("\n" + "="*70)
    print("FASE 3: RANKING COMPLETO DAS 15 MELHORES JANELAS")
    print("="*70)

    sorted_janelas = sorted(resultados_janela.items(), key=lambda x: x[1]['sharpe'], reverse=True)

    print(f"{'#':<4} {'Janela':<22} {'Trades':<8} {'Win%':<8} {'Pts':<10} {'R$ Liq':<12} {'Sharpe':<8} {'Media':<8}")
    print("-"*80)

    for i, (janela, dados) in enumerate(sorted_janelas[:15], 1):
        print(f"{i:<4} {janela:<22} {dados['trades']:<8} {dados['win_pct']:.1f}%  {dados['pts']:>6.0f}pts  R${dados['r_liq']:>8.2f}  {dados['sharpe']:>6.2f}  {dados['media']:>5.1f}pts")

    mt5.shutdown()

if __name__ == "__main__":
    rodar_backtest_otimizado()
