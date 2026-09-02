"""
Utilidades Teoria das Sete Velas (WDO).
Desacopladas do shadow e do monstro para reutilização pelo orquestrador.
"""
from datetime import datetime, timedelta

import MetaTrader5 as mt5

SHIFT_BRT = timedelta(hours=3)   # epoch MT5 XP + 3h = horário de Brasília


def brt_agora():
    return datetime.now()


def epoch_para_brt(epoch):
    return datetime.fromtimestamp(int(epoch)) + SHIFT_BRT


def brt_para_epoch(dt):
    return int((dt - SHIFT_BRT).timestamp())


def velas_m15_do_dia(symbol):
    """Últimas 200 barras M15 do MT5 no dia, convertidas para BRT."""
    bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
    if bars is None or len(bars) == 0:
        return []
    hoje = brt_agora().date()
    ini = brt_para_epoch(datetime(hoje.year, hoje.month, hoje.day, 0, 0))
    out = []
    for b in bars:
        t = int(b[0])
        if t >= ini:
            out.append({
                'epoch': t,
                'open': float(b[1]), 'high': float(b[2]),
                'low': float(b[3]), 'close': float(b[4]),
            })
    out.sort(key=lambda v: v['epoch'])
    return out


def majority(velas, n):
    """Retorna ('BUY' ou 'SELL') e (ups, downs) das primeiras n velas."""
    window = velas[:n]
    ups = sum(1 for v in window if v['close'] > v['open'])
    downs = len(window) - ups
    lado = 'BUY' if ups > downs else 'SELL'
    return lado, ups, downs


def calcular_cvd_janela(symbol, inicio_dt, fim_dt):
    """Agressão real por ticks (last > mid = compra, last < mid = venda)."""
    ini = brt_para_epoch(inicio_dt)
    fim = brt_para_epoch(fim_dt)
    ticks = mt5.copy_ticks_range(symbol, ini, fim, mt5.COPY_TICKS_ALL)
    cvd = 0.0
    if ticks is None or len(ticks) == 0:
        return cvd
    ultimo = None
    for t in ticks:
        epoch = int(t[0])
        if epoch <= ini:
            continue
        if ultimo is not None and epoch <= ultimo:
            continue
        bid = float(t[1]); ask = float(t[2]); last = float(t[3]); vol = float(t[4])
        if last > 0 and (ask > 0 or bid > 0):
            mid = (bid + ask) / 2.0
            if last > mid:
                cvd += vol
            elif last < mid:
                cvd -= vol
        ultimo = epoch
    return cvd


def get_hora_entrada(variante):
    """Retorna hora BRT de entrada (float) conforme variante (7 ou 9)."""
    return {7: 10.75, 9: 11.25}[variante]


def velas_para_entrada(symbol, variante, entrada_dt):
    """Retorna as velas M15 do dia até o horário de entrada e a vela de entrada."""
    velas = velas_m15_do_dia(symbol)
    if len(velas) < variante + 1:
        return None, None, 0, 0
    lado, ups, downs = majority(velas, variante)
    entrada_epoch = brt_para_epoch(entrada_dt)
    prox = [v for v in velas if v['epoch'] >= entrada_epoch]
    if not prox:
        return None, None, ups, downs
    return prox[0], prox[0]['open'], ups, downs


# ============================================================
# CUSTOS OPERACIONAIS REAIS XP NOMOS + RLP (5 CONTRATOS)
# ============================================================

def _carregar_custos():
    """Carrega custos operacionais do config.json"""
    try:
        with open(r'C:\AIOFEN\config.json', encoding='utf-8-sig') as f:
            import json
            cfg = json.load(f)
        return cfg.get('custos_operacionais', {})
    except Exception:
        return {}


def calcular_custo_trade(ativo: str, pontos: float) -> dict:
    """
    Calcula custo real de um trade no ambiente XP NOMOS + RLP (5 contratos).
    Retorna dict com pnl_bruto, custo_fixo, custo_slippage, custo_total, pnl_liquido.
    """
    custos = _carregar_custos()
    cfg = custos.get(ativo.upper(), {})
    
    valor_ponto = float(cfg.get('valor_por_ponto_5ct', 50.0 if 'WDO' in ativo.upper() else 5.0))
    custo_fixo = float(cfg.get('custo_por_trade_5ct', 4.0 if 'WDO' in ativo.upper() else 1.25))
    slippage_pts = float(cfg.get('slippage_pontos', 0.5 if 'WDO' in ativo.upper() else 1.0))
    
    pnl_bruto = pontos * valor_ponto
    custo_slippage = slippage_pts * (10.0 if 'WDO' in ativo.upper() else 1.0)  # R$/pt * pts
    custo_total = custo_fixo + custo_slippage
    pnl_liquido = pnl_bruto - custo_total
    
    return {
        'pnl_bruto': round(pnl_bruto, 2),
        'custo_fixo': round(custo_fixo, 2),
        'custo_slippage': round(custo_slippage, 2),
        'custo_total': round(custo_total, 2),
        'pnl_liquido': round(pnl_liquido, 2)
    }


def calcular_pnl_liquido_trade(ativo: str, pontos: float) -> float:
    """Wrapper simples que retorna apenas o P&L líquido do trade."""
    return calcular_custo_trade(ativo, pontos)['pnl_liquido']