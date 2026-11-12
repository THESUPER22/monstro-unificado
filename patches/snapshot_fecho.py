# -*- coding: utf-8 -*-
"""Snapshot READ-ONLY do estado de fecho (checklist 12/11/2026, secao 0.3).

Nao abre, nao fecha, nao altera nada. Apenas le posicoes e deals do MT5.
Ignora a posicao fantasma WINV25 (magic 123457).
"""
import MetaTrader5 as mt5
from datetime import datetime

MAGICS = {123456, 7008}   # Core + Faixa 1 (phantom 123457 fica de fora)

if not mt5.initialize():
    raise SystemExit("MT5 initialize falhou: %s" % (mt5.last_error(),))
try:
    pos = mt5.positions_get() or []
    robo = [p for p in pos if p.magic in MAGICS]
    print("posicoes abertas (todas): %d" % len(pos))
    print("posicoes abertas (robô):  %d" % len(robo))
    for p in pos:
        marca = "ROBO" if p.magic in MAGICS else "ignorada"
        print("  #%s %s %s vol=%s magic=%s [%s] lucro=%.2f"
              % (p.ticket, p.symbol, "BUY" if p.type == 0 else "SELL",
                 p.volume, p.magic, marca, p.profit))
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(hoje, datetime.now()) or []
    outs = [d for d in deals if d.magic in MAGICS and d.entry == mt5.DEAL_ENTRY_OUT]
    pnl = sum(d.profit + d.swap + d.commission for d in outs)
    print("deals OUT hoje (magics do robô): %d | PnL=R$ %.2f" % (len(outs), pnl))
    print("VEREDITO: %s" % ("FLAT (ok)" if not robo else "ATENCAO: posicao do robô aberta"))
finally:
    mt5.shutdown()
