import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def backtest_abertura():
    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        return

    symbol = "WIN$"
    if not mt5.symbol_select(symbol, True):
        symbol = "WINV26"
        mt5.symbol_select(symbol, True)

    print(f"Puxando dados de M1 para {symbol}...")

    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=120)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)

    if rates is None or len(rates) == 0:
        print("Nenhum dado encontrado.")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    # Puxa D1 para fechamento anterior
    rates_d1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_D1, utc_from, utc_to)
    df_d1 = pd.DataFrame(rates_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1.set_index('time', inplace=True)

    dias = df.index.normalize().unique()

    # Custo por contrato (ida+volta)
    CUSTO_CC = 1.20
    VALOR_PONTO = 0.20  # WIN: R$0,20/pt
    contratos_teste = [1, 2, 5, 10]

    # ============================================================
    # MODELO A: GAP REVERSAL (reversao ao fechamento anterior)
    # ============================================================
    # MODELO B: BREAKOUT DE ABERTURA (compra se abre acima da max anterior)
    # MODELO C: MOMENTUM DO PRIMEIRO CANDLE (compra se candle 09:00 e alto)

    modelos = {
        'A_GapReversao': {'gatilho_pts': [100, 150, 200, 300], 'saida': '09:15'},
        'B_Breakout': {'saida': '09:15'},
        'C_Momentum': {'saida': '09:15'},
    }

    print("\n" + "="*75)
    print("BACKTEST DE ABERTURA - WIN (09:00 -> 09:15)")
    print("="*75)

    # Coleta todos os trades por modelo
    resultados = {}

    # --- MODELO A: Gap Reversao ---
    print("\n--- MODELO A: GAP REVERSAO (vende gap alto, compra gap baixo) ---")
    for gap_threshold in [100, 150, 200, 300]:
        trades = []
        for dia in dias:
            try:
                # Procura fechamento anterior
                dia_anterior = dia - timedelta(days=1)
                # Pula fins de semana
                while dia_anterior.weekday() >= 5:
                    dia_anterior -= timedelta(days=1)

                # Fechamento do dia anterior (último candle antes das 09:00)
                mask_ant = (df.index.normalize() == dia_anterior) & (df.index.hour < 9)
                if mask_ant.sum() == 0:
                    continue
                fechamento_anterior = df.loc[mask_ant].iloc[-1]['close']

                # Abertura do candle 09:00
                h_0900 = dia + timedelta(hours=9)
                if h_0900 not in df.index:
                    continue
                open_0900 = df.loc[h_0900]['open']

                # Gap em pontos
                gap = open_0900 - fechamento_anterior

                # Filtro de gap extremo (>300 pts = noticia)
                if abs(gap) > 500:
                    continue

                # Determina direcao: se gap > threshold -> VENDA (reversao)
                if gap > gap_threshold:
                    entrada = 'VENDA'
                elif gap < -gap_threshold:
                    entrada = 'COMPRA'
                else:
                    continue

                # Saida as 09:15
                h_0915 = dia + timedelta(hours=9, minutes=15)
                sub = df.loc[h_0900:h_0915]
                if sub.empty:
                    continue

                if entrada == 'COMPRA':
                    preco_entrada = open_0900
                    preco_saida = sub.iloc[-1]['close']
                else:  # VENDA
                    preco_entrada = open_0900
                    preco_saida = sub.iloc[-1]['close']

                if entrada == 'COMPRA':
                    pontos = preco_saida - preco_entrada
                else:
                    pontos = preco_entrada - preco_saida

                trades.append({
                    'data': dia.strftime('%Y-%m-%d'),
                    'gap': gap,
                    'entrada': entrada,
                    'preco_ent': preco_entrada,
                    'preco_sai': preco_saida,
                    'pontos': pontos,
                })
            except Exception:
                continue

        if trades:
            tdf = pd.DataFrame(trades)
            pontos_arr = tdf['pontos'].values
            wins = (pontos_arr > 0).sum()
            total_pts = pontos_arr.sum()
            media = pontos_arr.mean()

            label = f"A_GapRev_{gap_threshold}pts"
            resultados[label] = {
                'trades': len(trades), 'pts': total_pts, 'media': media,
                'win_pct': wins/len(trades)*100, 'pontos_arr': pontos_arr
            }

            print(f"  Gap>{gap_threshold:3d}pts | {len(trades):3d} trades | "
                  f"Win {wins/len(trades)*100:.1f}% | "
                  f"Total {total_pts:+.0f}pts | Media {media:+.1f}pts")

    # --- MODELO B: Breakout de Abertura ---
    print("\n--- MODELO B: BREAKOUT (compra se abre > max anterior, vende se < min) ---")
    trades_b = []
    for dia in dias:
        try:
            dia_anterior = dia - timedelta(days=1)
            while dia_anterior.weekday() >= 5:
                dia_anterior -= timedelta(days=1)

            mask_ant = df.index.normalize() == dia_anterior
            if mask_ant.sum() == 0:
                continue

            max_anterior = df.loc[mask_ant]['high'].max()
            min_anterior = df.loc[mask_ant]['low'].min()
            fechamento_anterior = df.loc[mask_ant].iloc[-1]['close']

            h_0900 = dia + timedelta(hours=9)
            if h_0900 not in df.index:
                continue
            open_0900 = df.loc[h_0900]['open']

            # Filtro gap extremo
            gap = open_0900 - fechamento_anterior
            if abs(gap) > 500:
                continue

            # Direcao do breakout
            if open_0900 > max_anterior:
                entrada = 'COMPRA'
            elif open_0900 < min_anterior:
                entrada = 'VENDA'
            else:
                continue  # Sem breakout

            h_0915 = dia + timedelta(hours=9, minutes=15)
            sub = df.loc[h_0900:h_0915]
            if sub.empty:
                continue

            preco_saida = sub.iloc[-1]['close']

            if entrada == 'COMPRA':
                pontos = preco_saida - open_0900
            else:
                pontos = open_0900 - preco_saida

            trades_b.append({
                'data': dia.strftime('%Y-%m-%d'),
                'gap': gap,
                'entrada': entrada,
                'pontos': pontos,
            })
        except Exception:
            continue

    if trades_b:
        tdf = pd.DataFrame(trades_b)
        pontos_arr = tdf['pontos'].values
        wins = (pontos_arr > 0).sum()
        total_pts = pontos_arr.sum()
        media = pontos_arr.mean()
        resultados['B_Breakout'] = {
            'trades': len(trades_b), 'pts': total_pts, 'media': media,
            'win_pct': wins/len(trades_b)*100, 'pontos_arr': pontos_arr
        }
        print(f"  Breakout | {len(trades_b):3d} trades | "
              f"Win {wins/len(trades_b)*100:.1f}% | "
              f"Total {total_pts:+.0f}pts | Media {media:+.1f}pts")

    # --- MODELO C: Momentum do Primeiro Candle ---
    print("\n--- MODELO C: MOMENTUM (entra a favor do candle 09:00) ---")
    trades_c = []
    for dia in dias:
        try:
            h_0900 = dia + timedelta(hours=9)
            if h_0900 not in df.index:
                continue

            candle = df.loc[h_0900]
            corpo = candle['close'] - candle['open']
            amplitude = candle['high'] - candle['low']

            # Filtro de volatilidade anormal (>2.5x media 10 dias)
            dias_anteriores = [d for d in dias if d < dia][-10:]
            amplitudes = []
            for d in dias_anteriores:
                h = d + timedelta(hours=9)
                if h in df.index:
                    amplitudes.append(df.loc[h]['high'] - df.loc[h]['low'])
            if len(amplitudes) < 5:
                continue
            media_amp = np.mean(amplitudes)
            if amplitude > 2.5 * media_amp:
                continue  # Dia de noticia

            # Candle de conviccao: corpo > 50pts e sem pavio grande
            if abs(corpo) < 50:
                continue

            # Direcao: compra se candle de alta, vende se de baixa
            if corpo > 0:
                entrada = 'COMPRA'
            else:
                entrada = 'VENDA'

            h_0915 = dia + timedelta(hours=9, minutes=15)
            sub = df.loc[h_0900:h_0915]
            if sub.empty:
                continue

            preco_saida = sub.iloc[-1]['close']

            if entrada == 'COMPRA':
                pontos = preco_saida - candle['open']
            else:
                pontos = candle['open'] - preco_saida

            trades_c.append({
                'data': dia.strftime('%Y-%m-%d'),
                'corpo': corpo,
                'amplitude': amplitude,
                'entrada': entrada,
                'pontos': pontos,
            })
        except Exception:
            continue

    if trades_c:
        tdf = pd.DataFrame(trades_c)
        pontos_arr = tdf['pontos'].values
        wins = (pontos_arr > 0).sum()
        total_pts = pontos_arr.sum()
        media = pontos_arr.mean()
        resultados['C_Momentum'] = {
            'trades': len(trades_c), 'pts': total_pts, 'media': media,
            'win_pct': wins/len(trades_c)*100, 'pontos_arr': pontos_arr
        }
        print(f"  Momentum | {len(trades_c):3d} trades | "
              f"Win {wins/len(trades_c)*100:.1f}% | "
              f"Total {total_pts:+.0f}pts | Media {media:+.1f}pts")

    # ============================================================
    # TABELA RESUMO POR CONTRATO
    # ============================================================
    print("\n" + "="*75)
    print("RESUMO FINANCEIRO POR MODELO E CONTRATOS")
    print("="*75)
    print(f"{'Modelo':<18} {'Trades':<8} {'Win%':<8} {'Pts':<10} {'1cc':<12} {'2cc':<12} {'5cc':<12} {'10cc':<12}")
    print("-"*92)

    for nome, dados in resultados.items():
        trades_n = dados['trades']
        if trades_n == 0:
            continue
        row = f"{nome:<18} {trades_n:<8} {dados['win_pct']:.1f}%  {dados['pts']:>+6.0f}pts "
        for cc in contratos_teste:
            lucro_bruto = dados['pts'] * VALOR_PONTO * cc
            custo_total = trades_n * CUSTO_CC * cc
            liq = lucro_bruto - custo_total
            row += f"  R${liq:>+8.2f}"
        print(row)

    # ============================================================
    # DETALHE DOS TRADES (ultimas 10 de cada modelo)
    # ============================================================
    print("\n" + "="*75)
    print("ULTIMOS 10 TRADES POR MODELO")
    print("="*75)

    if trades:
        print("\n--- Modelo A (Gap Reversao 150pts) ---")
        key = 'A_GapRev_150pts'
        if key in resultados:
            # Recalcula para mostrar
            pass
        tdf = pd.DataFrame(trades)
        print(tdf.tail(10).to_string(index=False))

    if trades_b:
        print("\n--- Modelo B (Breakout) ---")
        tdf = pd.DataFrame(trades_b)
        print(tdf.tail(10).to_string(index=False))

    if trades_c:
        print("\n--- Modelo C (Momentum) ---")
        tdf = pd.DataFrame(trades_c)
        print(tdf.tail(10).to_string(index=False))

    mt5.shutdown()

if __name__ == "__main__":
    backtest_abertura()
