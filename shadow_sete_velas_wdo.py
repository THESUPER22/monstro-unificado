"""
SHADOW MODE - TEORIA DAS SETE VELAS (WDO)
==========================================
Estrategia: contar a maioria de velas M15 desde a abertura da sessao (09:00 BRT);
entrada na abertura do candle seguinte apos N velas (N=7 -> 10:45 BRT; N=9 -> 11:15 BRT).
Filtro CVD: so confirma a entrada se o fluxo acumulado (comprador/vendedor) da
janela 09:00->alvo estiver confluente com a direcao majoritaria.

FUSO: o MT5 da XP devolve timestamps deslocados -3h do horario de Brasilia.
Este modulo converte: brt = epoch + 3h  (confirmado empiricamente).

Registros: logs/shadow_7velas_wdo.csv  (estado idempotente em logs/shadow_7v_state.json)
Modos:
  --simular : reprocessa dias passados (sem CVD) e escreve CSV de retrospecto
  (default) : acompanhamento ao vivo com polling e acumulo de CVD
"""
import os
import csv
import json
import time
import argparse
from datetime import datetime, timedelta, date

import MetaTrader5 as mt5

SYMBOLO = 'WDOU26'
SHIFT_BRT = timedelta(hours=3)   # epoch MT5 + 3h = horario de Brasilia
ENTRADAS = {7: 10.75, 9: 11.25}  # N velas -> horario BRT da entrada (10:45 / 11:15)
SL = 8.0
TP = 10.0
FIM_DIA_BRT = 18.60              # 18:35 - resolve pendentes
LOG_DIR = r'C:\AIOFEN\logs'
CSV_OUT = os.path.join(LOG_DIR, 'shadow_7velas_wdo.csv')
STATE_OUT = os.path.join(LOG_DIR, 'shadow_7v_state.json')


def brt_agora():
    return datetime.now()


def epoch_para_brt(epoch):
    return datetime.fromtimestamp(int(epoch)) + SHIFT_BRT


def brt_para_epoch(dt):
    return int((dt - SHIFT_BRT).timestamp())


def carregar_estado():
    if os.path.exists(STATE_OUT):
        with open(STATE_OUT, encoding='utf-8') as f:
            return json.load(f)
    return {}


def salvar_estado(estado):
    with open(STATE_OUT, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, default=str)


def carregar_log(novos=None, reset=False):
    linhas = []
    if not reset and os.path.exists(CSV_OUT):
        with open(CSV_OUT, encoding='utf-8') as f:
            linhas.extend(csv.DictReader(f))
    if novos:
        linhas.extend(novos)
    with open(CSV_OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=[
            'dia', 'n_velas', 'hora_entrada', 'sinal', 'ups_downs',
            'cvd', 'cvd_confluente', 'entrada', 'saida', 'resultado_pts',
            'observacao'])
        w.writeheader()
        w.writerows(linhas)


def velas_m15_do_dia():
    """Ultimas 200 velas M15 do MT5 convertidas para BRT."""
    bars = mt5.copy_rates_from_pos(SYMBOLO, mt5.TIMEFRAME_M15, 0, 200)
    if bars is None or len(bars) == 0:
        return []
    hoje = date.today()
    ini = brt_para_epoch(datetime(hoje.year, hoje.month, hoje.day, 0, 0))
    out = []
    for b in bars:
        t = int(b[0])
        if t >= ini:
            out.append({'epoch': t, 'open': float(b[1]), 'high': float(b[2]),
                        'low': float(b[3]), 'close': float(b[4])})
    out.sort(key=lambda v: v['epoch'])
    return out


def maioria(velas, n_velas):
    ups = sum(1 for v in velas[:n_velas] if v['close'] > v['open'])
    downs = n_velas - ups
    return ups, downs


def acumular_cvd(ultimo_epoch, cvd):
    """Agressao real por ticks: last acima do mid = compra, abaixo = venda."""
    agora = brt_agora()
    ate_epoch = brt_para_epoch(agora)
    de_epoch = ultimo_epoch
    if de_epoch is None or de_epoch == 0:
        de_epoch = ate_epoch - 900  # 15 min iniciais de pre-aquisicao
    ticks = mt5.copy_ticks_range(SYMBOLO, de_epoch, ate_epoch, mt5.COPY_TICKS_ALL)
    novo = 0.0
    if ticks is not None and len(ticks) > 0:
        for i in range(len(ticks)):
            t = int(ticks[i][0])
            if t <= de_epoch and i > 0:
                continue
            if t <= (de_epoch if i == 0 else t - 1):
                continue
            if t > de_epoch:
                bid = float(ticks[i][1])
                ask = float(ticks[i][2])
                last = float(ticks[i][3])
                vol = float(ticks[i][4])
                if last > 0 and (bid > 0 or ask > 0):
                    mid = (bid + ask) / 2
                    novo += vol if last > mid else -vol if last < mid else 0.0
    return cvd + novo, max(ultimo_epoch or 0, ate_epoch)


def simular_resultado(entrada, sinal, alvo_brt):
    """Resultado virtual: varre velas M15 do alvo ao fim do dia. SL avaliado
    antes de TP quando ambos tocados na mesma vela (conservador)."""
    dia = date.today()
    alvo_min = int(round((alvo_brt % 1) * 60))
    ini = brt_para_epoch(datetime(dia.year, dia.month, dia.day,
                                  int(alvo_brt), alvo_min))
    velas = velas_m15_do_dia()
    if sinal == 'BUY':
        tp_n, sl_n = entrada + TP, entrada - SL
    else:
        tp_n, sl_n = entrada - TP, entrada + SL
    for v in velas:
        if v['epoch'] < ini:
            continue
        if sinal == 'BUY':
            if v['low'] <= sl_n:
                return -SL, 'SL'
            if v['high'] >= tp_n:
                return TP, 'TP'
        else:
            if v['high'] >= sl_n:
                return -SL, 'SL'
            if v['low'] <= tp_n:
                return TP, 'TP'
    return 0.0, 'EOD'


def avaliar(n_velas, alvo_brt, cvd):
    agora = brt_agora()
    velas = velas_m15_do_dia()
    if len(velas) < n_velas + 1:
        return None
    ups, downs = maioria(velas, n_velas)
    if ups == downs:
        return None
    sinal = 'BUY' if ups > downs else 'SELL'
    alvo_epoch = brt_para_epoch(alvo_brt)
    prox = [v for v in velas if v['epoch'] >= alvo_epoch]
    if not prox:
        return None
    entrada = prox[0]['open']
    cvd_conf = (sinal == 'BUY' and cvd > 0) or (sinal == 'SELL' and cvd < 0)
    return {
        'dia': agora.date().isoformat(),
        'n_velas': n_velas,
        'hora_entrada': f'{int(alvo_brt):02d}:{int(round((alvo_brt % 1) * 60)):02d}',
        'sinal': sinal,
        'ups_downs': f'{ups}-{downs}',
        'cvd': round(cvd, 1),
        'cvd_confluente': cvd_conf,
        'entrada': entrada,
        'saida': 'PENDENTE',
        'resultado_pts': '',
        'observacao': '' if cvd_conf else 'VETADO-CVD',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--simular', action='store_true',
                    help='reprocessa dias passados (sem CVD)')
    ap.add_argument('--ate', default=None,
                    help='hora HH:MM (BRT) para resolver pendentes e encerrar')
    args = ap.parse_args()

    if args.simular:
        import sys
        sys.path.insert(0, r'C:\AIOFEN\backtest')
        from backtest_sete_velas import carregar_m5, dias_validos, agregar_tf
        if not mt5.initialize():
            print('MT5 indisponivel', flush=True)
            return
        mt5.symbol_select(SYMBOLO, True)
        dias = dias_validos(carregar_m5(r'C:\AIOFEN\backtest\dados_mt5\WDOU26_M5.csv'))
        novos = []
        for d, bars in dias:
            tf = [{'open': v['o'], 'high': v['h'], 'low': v['l'],
                   'close': v['c']} for v in agregar_tf(bars, 3)]
            if len(tf) < 10:
                continue
            for nvel, hora in ENTRADAS.items():
                ups, downs = maioria(tf, nvel)
                if ups == downs:
                    continue
                sinal = 'BUY' if ups > downs else 'SELL'
                entrada = tf[nvel]['open']
                if sinal == 'BUY':
                    tp_n, sl_n = entrada + TP, entrada - SL
                else:
                    tp_n, sl_n = entrada - TP, entrada + SL
                res, saida = 0.0, 'EOD'
                for v in tf[nvel:]:
                    if sinal == 'BUY':
                        if v['low'] <= sl_n:
                            res, saida = -SL, 'SL'
                            break
                        if v['high'] >= tp_n:
                            res, saida = TP, 'TP'
                            break
                    else:
                        if v['high'] >= sl_n:
                            res, saida = -SL, 'SL'
                            break
                        if v['low'] <= tp_n:
                            res, saida = TP, 'TP'
                            break
                else:
                    res = (tf[-1]['close'] - entrada) if sinal == 'BUY' else (
                        entrada - tf[-1]['close'])
                novos.append({
                    'dia': d.isoformat(), 'n_velas': nvel,
                    'hora_entrada': f'{int(hora):02d}:{int(round((hora % 1) * 60)):02d}',
                    'sinal': sinal, 'ups_downs': f'{ups}-{downs}',
                    'cvd': '', 'cvd_confluente': '',
                    'entrada': entrada, 'saida': saida,
                    'resultado_pts': round(res, 1),
                    'observacao': 'RETROSPECTIVA'})
        carregar_log(novos, reset=True)
        print('retrospectiva salva:', len(novos), 'registros', flush=True)
        return

    if not mt5.initialize():
        print('MT5 indisponivel; encerrando', flush=True)
        return
    mt5.symbol_select(SYMBOLO, True)

    estado = carregar_estado()
    hora_fim = []
    if args.ate:
        hp = args.ate.split(':')
        hora_fim = [int(hp[0]), int(hp[1])]
    cvd = float(estado.get('cvd_acumulado', 0.0))
    ultimo_epoch = int(estado.get('ultimo_epoch', 0))
    hoje = date.today().isoformat()
    print(f'SHADOW 7 VELAS | {SYMBOLO} | LIVE | {brt_agora().strftime("%H:%M:%S")} BRT'
          f'{(" | fim " + args.ate) if args.ate else ""}', flush=True)
    while True:
        agora = brt_agora()
        if agora.date().isoformat() != hoje:
            cvd = 0.0
            ultimo_epoch = 0
            hoje = agora.date().isoformat()
        cvd, ultimo_epoch = acumular_cvd(ultimo_epoch, cvd)
        estado['cvd_acumulado'] = cvd
        estado['ultimo_epoch'] = ultimo_epoch
        estado['atualizado'] = agora.isoformat()
        for nvel, hora_float in ENTRADAS.items():
            chave = f'{hoje}_v{nvel}'
            if chave not in estado and agora >= _brt(hora_float):
                r = avaliar(nvel, _brt(hora_float), cvd)
                if r:
                    estado[chave] = r
                    carregar_log([r])
                    print(f'[{agora.strftime("%H:%M:%S")}] {chave}: '
                          f'{r["sinal"]} {r["ups_downs"]} cvd={r["cvd"]} '
                          f'conf={r["cvd_confluente"]} @ {r["entrada"]} '
                          f'{r["observacao"]}', flush=True)
        if agora.hour + agora.minute / 60 >= FIM_DIA_BRT:
            mudou = False
            for chave, rec in list(estado.items()):
                if isinstance(rec, dict) and rec.get('saida') == 'PENDENTE':
                    hp = rec['hora_entrada'].split(':')
                    alvo = int(hp[0]) + int(hp[1]) / 60
                    res, saida = simular_resultado(rec['entrada'], rec['sinal'], alvo)
                    rec['saida'] = saida
                    rec['resultado_pts'] = round(res, 1)
                    mudou = True
                    print(f'  {chave}: {saida} {res:+.1f} pts', flush=True)
            if mudou:
                salvar_estado(estado)
                carregar_log()
            if hora_fim and (agora.hour > hora_fim[0] or
                             (agora.hour == hora_fim[0] and agora.minute >= hora_fim[1])):
                print(f'[SHADOW] horario limite {args.ate} atingido; encerrando', flush=True)
                return
            time.sleep(60)
        else:
            salvar_estado(estado)
            time.sleep(5)


def _brt(hora_float):
    hoje = date.today()
    return datetime(hoje.year, hoje.month, hoje.day, int(hora_float),
                    int(round((hora_float % 1) * 60)))


if __name__ == '__main__':
    main()