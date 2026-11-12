# -*- coding: utf-8 -*-
"""teste_fecho_demo.py - teste REAL e controlado do fecho C1/C2 em DEMO.

Uso:
    python patches\\teste_fecho_demo.py --check
    python patches\\teste_fecho_demo.py --run WDOZ26

Regras de seguranca:
- So roda em conta DEMO (aborta se nao for).
- Aborta se houver QUALQUER posicao dos magics do robo (123456/7008).
- Usa magic de teste 999999 (fora de MAGICS_ROBO).
- Abre 1 contrato (volume_min) a mercado, sem SL/TP, e fecha pelo helper.
- Se o helper falhar, tenta fecho direto de emergencia; se ainda assim
  sobrar posicao, imprime o ticket e sai com codigo 2.
- Nao toca em lógica de trade, config ou arquivos do robo.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

BASE = r"C:\AIOFEN"
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import MetaTrader5 as mt5  # noqa: E402
from patches.robustez_fecho_helpers import (  # noqa: E402
    fechar_todas_robusto,
    fillings_disponiveis,
    posicoes_do_robo,
    posicoes_restantes,
)

MAGIC_TESTE = 999999
MAGICS_ROBO = {123456, 7008}
LOG_PATH = os.path.join(BASE, "logs", "teste_fecho_demo.log")


def _log():
    lg = logging.getLogger("teste_fecho")
    lg.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    lg.addHandler(sh)
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    lg.addHandler(fh)
    return lg


def conectar(log):
    if not mt5.initialize():
        log.error("MT5 initialize falhou: %s", mt5.last_error())
        return False
    acc = mt5.account_info()
    if acc is None:
        log.error("account_info None")
        return False
    log.info("conta=%s server=%s trade_mode=%s (0=demo)",
             acc.login, acc.server, acc.trade_mode)
    if acc.trade_mode != 0:
        log.error("ABORTADO: conta nao e DEMO (trade_mode=%s)", acc.trade_mode)
        return False
    return True


def check(log):
    acc = mt5.account_info()
    log.info("=== CHECK (read-only) ===")
    log.info("posicoes abertas: %d", len(mt5.positions_get() or []))
    robo = posicoes_do_robo(mt5, MAGICS_ROBO)
    log.info("posicoes do robo (123456/7008): %d", len(robo))
    for p in (mt5.positions_get() or []):
        log.info("  #%s %s magic=%s vol=%s", p.ticket, p.symbol, p.magic, p.volume)
    for sym in ("WDOZ26", "WINZ26", "DOLZ26"):
        i = mt5.symbol_info(sym)
        t = mt5.symbol_info_tick(sym)
        log.info("%s: vis=%s trade_mode=%s vol_min=%s point=%s filling=%s "
                 "bid=%s ask=%s", sym, getattr(i, "visible", None),
                 getattr(i, "trade_mode", None), getattr(i, "volume_min", None),
                 getattr(i, "point", None), getattr(i, "filling_mode", None),
                 t.bid if t else None, t.ask if t else None)
    return 0


def abrir_teste(log, symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        log.error("simbolo %s nao existe", symbol)
        return None
    if not info.visible and not mt5.symbol_select(symbol, True):
        log.error("nao consegui selecionar %s", symbol)
        return None
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        log.error("sem tick para %s", symbol)
        return None
    volume = float(info.volume_min)
    for filling in fillings_disponiveis(mt5, symbol):
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 50,
            "magic": MAGIC_TESTE,
            "comment": "TESTE_FECHO_C1C4",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        r = mt5.order_send(req)
        log.info("abertura: filling=%s retcode=%s comment=%s",
                 filling, getattr(r, "retcode", None), getattr(r, "comment", ""))
        if r is not None and r.retcode in (10009, 10010):
            for _ in range(20):
                time.sleep(0.5)
                alvo = [p for p in (mt5.positions_get() or [])
                        if p.magic == MAGIC_TESTE and p.symbol == symbol]
                if alvo:
                    p = alvo[0]
                    log.info("posicao de teste aberta: #%s %s vol=%s",
                             p.ticket, p.symbol, p.volume)
                    return p
            log.error("ordem aceita mas posicao nao apareceu")
            return None
    log.error("abertura falhou em todos os fillings")
    return None


def fechar_emergencia(log, symbol):
    """Fallback: fecha qualquer posicao magic 999999 no simbolo."""
    for tent in range(1, 4):
        alvos = [p for p in (mt5.positions_get() or [])
                 if p.magic == MAGIC_TESTE and p.symbol == symbol]
        if not alvos:
            return True
        for p in alvos:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                time.sleep(2)
                continue
            for filling in fillings_disponiveis(mt5, symbol):
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": p.ticket,
                    "symbol": symbol,
                    "volume": p.volume,
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": tick.bid,
                    "deviation": 50,
                    "magic": MAGIC_TESTE,
                    "comment": "TESTE_FECHO_EMERG",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling,
                }
                r = mt5.order_send(req)
                log.info("emergencia #%s filling=%s retcode=%s",
                         p.ticket, filling, getattr(r, "retcode", None))
                if r is not None and r.retcode in (10009, 10010, 10030):
                    break
        time.sleep(2)
    return not [p for p in (mt5.positions_get() or [])
                if p.magic == MAGIC_TESTE and p.symbol == symbol]


def run(log, symbol):
    log.info("=== RUN REAL (demo) %s ===", symbol)
    robo = posicoes_do_robo(mt5, MAGICS_ROBO)
    if robo:
        log.error("ABORTADO: ha posicao do robo aberta: %s",
                  [p.ticket for p in robo])
        return 1
    antes = len(mt5.positions_get() or [])
    pos = abrir_teste(log, symbol)
    if pos is None:
        return 2
    log.info("posicoes antes=%d depois_abertura=%d", antes,
             len(mt5.positions_get() or []))
    fechadas, restantes = fechar_todas_robusto(
        mt5, {MAGIC_TESTE},
        reconnect=lambda: mt5.initialize(),
        log=log,
        deviation=50,
        tentativas=5,
        backoff_s=2.0,
    )
    log.info("helper: fechadas=%s restantes=%s", fechadas, restantes)
    if restantes:
        log.error("helper NAO confirmou; tentando fecho de emergencia")
        ok = fechar_emergencia(log, symbol)
        restantes = posicoes_restantes(mt5, {MAGIC_TESTE})
        log.info("emergencia ok=%s restantes=%s", ok, restantes)
    if restantes:
        log.critical("FALHA: posicao de teste segue aberta: %s", restantes)
        return 2
    log.info("PASS: fecho confirmado por positions_get (flat, magic %s)",
             MAGIC_TESTE)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", metavar="SIMBOLO")
    args = ap.parse_args()
    log = _log()
    if not conectar(log):
        return 3
    try:
        if args.check:
            return check(log)
        if args.run:
            return run(log, args.run)
        log.info("use --check ou --run SIMBOLO")
        return 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
