# -*- coding: utf-8 -*-
"""robustez_fecho_helpers.py — PROPOSTA (NÃO aplicada ao robô).

Helpers de robustez para o fechamento de posições e para o relatório diário.
Motivação: ROADMAP 23.27 (11/11/2026) — o fecho das 17:35 falhou com
retcode 10031 ("sem conexão de rede") e a SELL `#2590873006` ficou aberta.

Princípios de projeto
---------------------
- Funções recebem o módulo `mt5` por injeção -> testáveis com um FakeMT5,
  sem terminal real.
- `reconnect`, `sleep` e `log` também são injetados.
- NENHUMA regra de entrada/saída do robô é alterada. Isto é só o fecho.

Integração (ver `patches/robustez_fecho_2026-11-11.md`):
  1. `fechar_todas_posicoes` passa a chamar `fechar_todas_robusto`.
  2. O bloco das 17:35 usa `posicoes_restantes` para só logar sucesso se
     realmente não houver posição aberta.
  3. O shutdown gracioso não encerra enquanto `posicoes_restantes` não for vazio.
  4. `agente_monstro_core.gerar_relatorio_diario` usa `contar_deals_reais_hoje`.
"""
from __future__ import annotations

import time as _time

RETCODE_DONE = 10009
RETCODE_DONE_PARTIAL = 10010
RETCODE_POSITION_CLOSED = 10030
RETCODE_NO_CONNECTION = 10031
# Retcodes em que o servidor ACEITA o fecho. Mesmo assim a confirmação final
# é SEMPRE via `positions_get()`: retcode não substitui a posição real.
# (10018 MARKET_CLOSED, 10015 INVALID_PRICE etc. NÃO significam "fechada".)
RETCODES_SUCESSO = frozenset({
    RETCODE_DONE,
    RETCODE_DONE_PARTIAL,
    RETCODE_POSITION_CLOSED,
})


def posicoes_do_robo(mt5, magics):
    """Posições abertas cujo magic pertence ao robô."""
    pos = mt5.positions_get()
    if not pos:
        return []
    magics = set(magics)
    return [p for p in pos if p.magic in magics]


def posicoes_restantes(mt5, magics):
    """Tickets de posições do robô ainda abertas. `[]` == flat."""
    return [p.ticket for p in posicoes_do_robo(mt5, magics)]


def ticket_aberto(mt5, ticket):
    return any(p.ticket == ticket for p in (mt5.positions_get() or []))


def fillings_disponiveis(mt5, symbol):
    """Fillings aceitos pelo símbolo, na ordem de preferência.

    `filling_mode` é bitmask: 1=FOK, 2=IOC, 4=RETURN.
    """
    info = mt5.symbol_info(symbol)
    fm = int(getattr(info, "filling_mode", 0) or 0) if info is not None else 0
    cands = []
    if fm & 1:
        cands.append(mt5.ORDER_FILLING_FOK)
    if fm & 2:
        cands.append(mt5.ORDER_FILLING_IOC)
    if fm & 4:
        cands.append(mt5.ORDER_FILLING_RETURN)
    if not cands:
        cands = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC,
                 mt5.ORDER_FILLING_RETURN]
    return cands


def fechar_posicao_robusto(mt5, pos, *, reconnect, log, deviation=50,
                           tentativas=5, backoff_s=5.0, sleep=_time.sleep):
    """Fecha UMA posição com reconexão + backoff + todos os fillings.

    Retorna True somente se confirmar (via `positions_get`) que o ticket saiu.
    """
    ticket = pos.ticket
    symbol = pos.symbol
    volume = pos.volume
    eh_buy = (pos.type == mt5.POSITION_TYPE_BUY)
    tipo_fechamento = mt5.ORDER_TYPE_SELL if eh_buy else mt5.ORDER_TYPE_BUY

    for tent in range(1, tentativas + 1):
        if not ticket_aberto(mt5, ticket):
            log.info("[fecho] #%s já não existe (fechada)", ticket)
            return True

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            log.warning("[fecho] #%s sem tick (tent %d/%d) - reconectando",
                        ticket, tent, tentativas)
            reconnect()
            sleep(backoff_s)
            continue

        preco = tick.bid if eh_buy else tick.ask
        sem_conexao = False
        for filling in fillings_disponiveis(mt5, symbol):
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": symbol,
                "volume": volume,
                "type": tipo_fechamento,
                "price": preco,
                "deviation": deviation,
                "magic": pos.magic,
                "comment": "fecho robusto",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            r = mt5.order_send(req)
            if r is None:
                log.warning("[fecho] #%s order_send None (filling=%s, tent %d)",
                            ticket, filling, tent)
                continue
            if r.retcode in RETCODES_SUCESSO:
                log.info("[fecho] #%s retcode %s (%s)", ticket, r.retcode,
                         getattr(r, "comment", ""))
                # NÃO retorna aqui: confirma via positions_get() logo abaixo.
                break
            if r.retcode == RETCODE_NO_CONNECTION:
                log.warning("[fecho] #%s retcode 10031 sem conexão (filling=%s)",
                            ticket, filling)
                sem_conexao = True
                break
            log.warning("[fecho] #%s retcode %s (%s, filling=%s)",
                        ticket, r.retcode, getattr(r, "comment", ""), filling)

        if not ticket_aberto(mt5, ticket):
            log.info("[fecho] #%s saiu após tentativa %d", ticket, tent)
            return True

        if sem_conexao or tent < tentativas:
            reconnect()
            sleep(backoff_s)

    fechou = not ticket_aberto(mt5, ticket)
    if not fechou:
        log.critical("[fecho] #%s NÃO fechou após %d tentativas",
                     ticket, tentativas)
    return fechou


def fechar_todas_robusto(mt5, magics, *, reconnect, log, deviation=50,
                         tentativas=5, backoff_s=5.0, sleep=_time.sleep):
    """Fecha todas as posições do robô. Retorna `(fechadas, restantes)`."""
    alvos = posicoes_do_robo(mt5, magics)
    if not alvos:
        log.info("[fecho] nenhuma posição do robô para fechar")
        return 0, []
    fechadas = 0
    for pos in alvos:
        if fechar_posicao_robusto(
                mt5, pos, reconnect=reconnect, log=log, deviation=deviation,
                tentativas=tentativas, backoff_s=backoff_s, sleep=sleep):
            fechadas += 1
    restantes = posicoes_restantes(mt5, magics)
    return fechadas, restantes


def contar_deals_reais_hoje(mt5, magics, inicio, fim):
    """Conta operações FECHADAS hoje lendo deals reais do MT5.

    `inicio`/`fim` são datetimes. Conta `DEAL_ENTRY_OUT` dos magics do robô.
    Retorna `(n, pnl_realizado)` — o PnL inclui swap e comissão.
    """
    deals = mt5.history_deals_get(inicio, fim)
    if not deals:
        return 0, 0.0
    magics = set(magics)
    n = 0
    pnl = 0.0
    for d in deals:
        if d.magic not in magics:
            continue
        if d.entry != mt5.DEAL_ENTRY_OUT:
            continue
        n += 1
        pnl += (float(d.profit) + float(getattr(d, "swap", 0.0))
                + float(getattr(d, "commission", 0.0)))
    return n, pnl
