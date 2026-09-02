import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, r'C:\AIOFEN')

DATA_DIR = r'C:\AIOFEN\backtest\dados_mt5'
OUT_DIR = r'C:\AIOFEN\backtest\resultados'
os.makedirs(OUT_DIR, exist_ok=True)

ATIVOS = ['WDOU26', 'WINV26']
ARQ_ATIVO = {
    'WDOU26': r'C:\AIOFEN\backtest\dados_mt5\WDOU26_M5.csv',
    'WINV26': r'C:\AIOFEN\backtest\dados_mt5\WINV26_M5.csv',
}

MIN_BARRAS_DIA = 100  # exige sessao quase completa (114 p/ dia solido)

# Importar funcao de custo real
from sete_velas_util import calcular_custo_trade


def carregar_m5(path):
    dias = {}
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            t = int(r['time'])
            d = datetime.fromtimestamp(t).date()
            dias.setdefault(d, []).append({
                't': t,
                'o': float(r['open']),
                'h': float(r['high']),
                'l': float(r['low']),
                'c': float(r['close']),
            })
    for d in dias:
        dias[d].sort(key=lambda b: b['t'])
    return dias


def agregar_tf(barras_m5, tf=3):
    out = []
    n = len(barras_m5)
    i = 0
    while i < n:
        grp = barras_m5[i:i + tf]
        out.append({
            'o': grp[0]['o'],
            'h': max(b['h'] for b in grp),
            'l': min(b['l'] for b in grp),
            'c': grp[-1]['c'],
        })
        i += tf
    return out


def dias_validos(dias_m5):
    dias = []
    for d, bars in sorted(dias_m5.items()):
        if len(bars) < MIN_BARRAS_DIA:
            continue
        dias.append((d, bars))
    return dias


def executar(dia_bars_tf, sinal, entrada, tp, sl, ativo, inicio=7):
    if sinal == 'BUY':
        tp_nivel = entrada + tp
        sl_nivel = entrada - sl
        for v in dia_bars_tf[inicio:]:
            if v['l'] <= sl_nivel:  # stop primeiro (conservador)
                return -sl, 'SL'
            if v['h'] >= tp_nivel:
                return tp, 'TP'
        return dia_bars_tf[-1]['c'] - entrada, 'EOD'
    else:
        tp_nivel = entrada - tp
        sl_nivel = entrada + sl
        for v in dia_bars_tf[inicio:]:
            if v['h'] >= sl_nivel:
                return -sl, 'SL'
            if v['l'] <= tp_nivel:
                return tp, 'TP'
        return entrada - dia_bars_tf[-1]['c'], 'EOD'


def backtest_ativo(nome, dias, tf, n_velas, tp, sl):
    trades = []
    ativo = 'WDO' if 'WDO' in nome else 'WIN'
    for d, bars in dias:
        tf_bars = agregar_tf(bars, tf)
        if len(tf_bars) < n_velas + 2:
            continue
        ups = sum(1 for v in tf_bars[:n_velas] if v['c'] > v['o'])
        downs = n_velas - ups
        if ups == downs:
            continue
        sinal = 'BUY' if ups > downs else 'SELL'
        entrada = tf_bars[n_velas]['o']
        pb, motivo = executar(tf_bars, sinal, entrada, tp, sl, ativo, inicio=n_velas)
        custo_info = calcular_custo_trade(ativo, pb)
        trades.append({'dia': d, 'sinal': sinal, 'ups': ups,
                        'entrada': entrada, 'pts': pb, 'saida': motivo,
                        'custo_total': custo_info['custo_total'],
                        'pnl_bruto': custo_info['pnl_bruto'],
                        'pnl_liquido': custo_info['pnl_liquido']})
    return trades


def metricas(trades):
    n = len(trades)
    if n == 0:
        return None
    wins = [t for t in trades if t.get('pnl_liquido', t.get('pts', 0)) > 0]
    losses = [t for t in trades if t.get('pnl_liquido', t.get('pts', 0)) <= 0]
    gw = sum(t.get('pnl_liquido', t.get('pts', 0)) for t in wins)
    gl = sum(t.get('pnl_liquido', t.get('pts', 0)) for t in losses)
    wr = len(wins) / n
    payoff = (gw / len(wins)) if wins else 0.0
    pf = (gw / abs(gl)) if gl else float('inf')
    eq = 0.0
    pico = 0.0
    mdd = 0.0
    for t in trades:
        eq += t.get('pnl_liquido', t.get('pts', 0))
        pico = max(pico, eq)
        mdd = min(mdd, eq - pico)
    return {'n': n, 'wins': len(wins), 'losses': len(losses),
            'wr': wr, 'net': eq, 'payoff': payoff, 'pf': pf, 'mdd': mdd}


def main():
    resultados = []
    todos_trades = []  # lista de (ativo, tfn, n_velas, sl, tp, trades_list)
    for ativo in ATIVOS:
        dias = dias_validos(carregar_m5(ARQ_ATIVO[ativo]))
        print(f'== {ativo}: {len(dias)} dias validos ==', flush=True)
        if ativo == 'WDOU26':
            for n_velas in [5, 7, 9]:
                for tf, tfn in [(1, 'M5'), (3, 'M15')]:
                    for sl in [5.0, 8.0, 10.0, 15.0]:
                        for tp in [10.0, 15.0, 20.0, 25.0]:
                            tr = backtest_ativo(ativo, dias, tf, n_velas, tp, sl)
                            m = metricas(tr)
                            resultados.append((ativo, tfn, n_velas, sl, tp, m))
                            todos_trades.append((ativo, tfn, n_velas, sl, tp, tr))
        else:
            for n_velas in [5, 7, 9]:
                for tf, tfn in [(1, 'M5'), (3, 'M15')]:
                    for sl in [150.0, 250.0, 400.0, 500.0]:
                        for tp in [500.0, 750.0, 1000.0]:
                            tr = backtest_ativo(ativo, dias, tf, n_velas, tp, sl)
                            m = metricas(tr)
                            resultados.append((ativo, tfn, n_velas, sl, tp, m))
                            todos_trades.append((ativo, tfn, n_velas, sl, tp, tr))

    csv_path = os.path.join(OUT_DIR, 'sete_velas_resultados.csv')
    linhas = []
    for ativo, tfn, n_velas, sl, tp, m in resultados:
        if m is None:
            continue
        linhas.append([ativo, tfn, n_velas, sl, tp, m['n'], m['wr'], m['pf'],
                       m['net'], m['payoff'], m['mdd']])
        tag = '<<<' if m['pf'] >= 1.4 and m['n'] >= 20 else ''
        print(f"{ativo:7s} {tfn:3s} V={n_velas} SL={sl:6.1f} TP={tp:7.1f} "
              f"n={m['n']:3d} WR={m['wr']*100:5.1f}% PF={m['pf']:5.2f} "
              f"net={m['net']:+9.1f} payoff={m['payoff']:5.2f} "
              f"maxDD={m['mdd']:8.1f} {tag}", flush=True)
    if linhas:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['ativo', 'timeframe', 'n_velas', 'sl', 'tp', 'n', 'wr',
                        'pf', 'net', 'payoff', 'maxdd'])
            w.writerows(linhas)
        print(f'\nResultados salvos em {csv_path}', flush=True)
    trades_path = os.path.join(OUT_DIR, 'sete_velas_trades.csv')
    with open(trades_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ativo', 'timeframe', 'n_velas', 'sl', 'tp', 'dia',
                    'sinal', 'ups', 'entrada', 'pts', 'saida',
                    'custo_total', 'pnl_bruto', 'pnl_liquido'])
        for ativo, tfn, n_velas, sl, tp, trades in todos_trades:
            for t in trades:
                w.writerow([ativo, tfn, n_velas, sl, tp,
                           t['dia'], t['sinal'], t['ups'],
                           round(t['entrada'], 1),
                           round(t['pts'], 1), t['saida'],
                           round(t.get('custo_total', 0), 2),
                           round(t.get('pnl_bruto', 0), 2),
                           round(t.get('pnl_liquido', 0), 2)])
    print(f'Trades salvos em {trades_path} ({len(todos_trades)} trades)', flush=True)


if __name__ == '__main__':
    main()