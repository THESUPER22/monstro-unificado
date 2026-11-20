# -*- coding: utf-8 -*-
"""robustez_fecho_helpers.py — helpers do fecho (C1..C4) usados pelo robo.

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
  2. O bloco das 17:35 usa `posicoes_restantes` para so logar sucesso se
     realmente nao houver posicao aberta (`None` = estado desconhecido).
  3. O shutdown gracioso nao encerra enquanto `posicoes_restantes` nao for
     `[]` confirmado; `None` mantem o processo vivo.
  4. `agente_monstro_core.gerar_relatorio_diario` usa `contar_deals_reais_hoje`.
"""
from __future__ import annotations

import os as _os
import time as _time

TETO_BACKOFF_S = 30.0
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
    """Posições abertas cujo magic pertence ao robô.

    ``None`` = estado DESCONHECIDO (``positions_get()`` falhou ou levantou).
    Não confundir com ``[]`` (leitura OK, nenhuma posição): a C3 usa essa
    diferença para não gravar ``parado.ok`` sem confirmar que está flat.
    """
    try:
        pos = mt5.positions_get()
    except Exception:  # noqa: BLE001
        return None
    if pos is None:
        return None
    magics = set(magics)
    return [p for p in pos if p.magic in magics]


def posicoes_restantes(mt5, magics):
    """Tickets de posições do robô ainda abertas.

    ``[]`` == flat confirmado; ``None`` == estado desconhecido.
    """
    pos = posicoes_do_robo(mt5, magics)
    if pos is None:
        return None
    return [p.ticket for p in pos]


def _espera_com_teto(base_s, expoente, teto_s=TETO_BACKOFF_S):
    """Backoff exponencial com TETO de 30 s (23.60.11 item 3).

    Sem teto, 2**(tent-1) cresce sem limite; o teto garante que o operador
    nunca fica mais de 30 s sem nova leitura/batimento.
    """
    return min(float(base_s) * (2 ** max(0, int(expoente))), float(teto_s))


def posicoes_restantes_com_retry(mt5, magics, *, log, reconnect=None,
                                 tentativas=4, backoff_s=2.0,
                                 teto_backoff_s=TETO_BACKOFF_S,
                                 sleep=_time.sleep):
    """Lê as posições insistindo quando ``positions_get()`` devolve ``None``.

    Entre as tentativas chama ``reconnect()`` (em produção,
    ``reconectar_mt5`` -> ``mt5.initialize()``) e dorme com backoff
    exponencial limitado a ``teto_backoff_s`` (30 s). Devolve ``None`` só se
    TODAS as tentativas falharem.
    """
    for tent in range(1, tentativas + 1):
        restantes = posicoes_restantes(mt5, magics)
        if restantes is not None:
            return restantes
        if tent >= tentativas:
            break
        log.warning("[fecho] positions_get() None (tent %d/%d) - estado "
                    "desconhecido; reinicializando MT5", tent, tentativas)
        if reconnect is not None:
            try:
                reconnect()
            except Exception as e:  # noqa: BLE001
                log.warning("[fecho] reconnect falhou: %s", e)
        espera = _espera_com_teto(backoff_s, tent - 1, teto_backoff_s)
        sleep(espera)
    log.critical("[fecho] positions_get() None apos %d tentativas - estado "
                 "desconhecido", tentativas)
    return None


def restantes_ate_saber(mt5, magics, *, log, reconnect=None,
                        tentativas=4, backoff_s=2.0, pausa_s=30.0,
                        teto_backoff_s=TETO_BACKOFF_S,
                        sleep=_time.sleep, max_ciclos=None):
    """Repete a leitura até o estado ser conhecido.

    Em produção ``max_ciclos=None``: NUNCA devolve ``None``. A C3 usa isso
    para não gravar ``parado.ok`` nem agendar ``os._exit`` enquanto o MT5
    não confirmar flat. ``max_ciclos`` existe só para teste.

    23.60.11 item 3: pausa com teto de 30 s e um CRITICAL de BATIMENTO por
    ciclo, provando que o loop principal continua vivo (não travou, não
    encerrou) enquanto o estado é desconhecido.
    """
    ciclos = 0
    while True:
        restantes = posicoes_restantes_com_retry(
            mt5, magics, log=log, reconnect=reconnect,
            tentativas=tentativas, backoff_s=backoff_s,
            teto_backoff_s=teto_backoff_s, sleep=sleep)
        if restantes is not None:
            return restantes
        ciclos += 1
        if max_ciclos is not None and ciclos >= max_ciclos:
            return None
        pausa = min(float(pausa_s), float(teto_backoff_s))
        log.critical("[fecho][BATIMENTO] loop principal VIVO - ciclo %d sem "
                     "estado das posicoes; nova leitura em %.0fs", ciclos, pausa)
        sleep(pausa)


def confirmar_flat_para_encerrar(mt5, magics, *, log, reconnect=None,
                                 fechar=None, tentativas=4, backoff_s=2.0,
                                 pausa_s=30.0, teto_backoff_s=TETO_BACKOFF_S,
                                 sleep=_time.sleep, max_ciclos=None):
    """Fluxo da trava de shutdown (C3): ler, fechar, reler.

    Devolve ``[]`` somente com flat CONFIRMADO. Em produção
    (``max_ciclos=None``) nunca devolve ``None``: o processo fica vivo até
    o MT5 responder. ``max_ciclos``/``fechar`` existem para teste.
    """
    restantes = restantes_ate_saber(
        mt5, magics, log=log, reconnect=reconnect, tentativas=tentativas,
        backoff_s=backoff_s, pausa_s=pausa_s,
        teto_backoff_s=teto_backoff_s, sleep=sleep,
        max_ciclos=max_ciclos)
    if restantes:
        log.critical("SHUTDOWN BLOQUEADO: posicoes abertas %s - tentando fechar",
                     restantes)
        if fechar is not None:
            fechar()
        restantes = restantes_ate_saber(
            mt5, magics, log=log, reconnect=reconnect, tentativas=tentativas,
            backoff_s=backoff_s, pausa_s=pausa_s,
            teto_backoff_s=teto_backoff_s, sleep=sleep,
            max_ciclos=max_ciclos)
    return restantes


def remover_sinal_parada(restantes, caminho_parar, *, log, remover=None):
    """Consome ``parar.txt`` SOMENTE quando ``restantes == []`` (flat confirmado).

    Motivo medido (23.60.11 item 1): o C3 removia o sinal antes da trava C3;
    com ``positions_get() -> None`` o ``continue`` voltava ao loop e
    ``verificar_parada_gracil()`` não encontrava mais o arquivo, então o
    encerramento não repetia. Agora o sinal sobrevive a qualquer ciclo
    desconhecido e só é apagado depois do flat confirmado.

    Devolve True se removeu, False se manteve o sinal.
    """
    if restantes != []:
        log.info("[fecho] parar.txt MANTIDO: estado das posicoes nao e flat "
                 "confirmado (restantes=%r)", restantes)
        return False
    apagar = remover or _os.remove
    try:
        apagar(caminho_parar)
    except OSError:
        pass
    log.info("parar.txt consumido e removido.")
    return True


def ticket_aberto(mt5, ticket):
    """True = aberto, False = fechado, None = estado DESCONHECIDO.

    Antes, ``positions_get() or []`` transformava falha de leitura em
    "fechado" e o fecho podia se declarar concluído sem confirmar nada.
    """
    try:
        pos = mt5.positions_get()
    except Exception:  # noqa: BLE001
        return None
    if pos is None:
        return None
    return any(p.ticket == ticket for p in pos)


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
        aberto = ticket_aberto(mt5, ticket)
        if aberto is False:
            log.info("[fecho] #%s já não existe (fechada)", ticket)
            return True
        if aberto is None:
            log.warning("[fecho] #%s estado desconhecido (tent %d/%d) - "
                        "reconectando", ticket, tent, tentativas)
            reconnect()
            sleep(backoff_s)
            continue

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

        saida = ticket_aberto(mt5, ticket)
        if saida is False:
            log.info("[fecho] #%s saiu após tentativa %d", ticket, tent)
            return True
        if saida is None:
            log.warning("[fecho] #%s estado desconhecido após tentativa %d",
                        ticket, tent)
            reconnect()
            sleep(backoff_s)
            continue

        if sem_conexao or tent < tentativas:
            reconnect()
            sleep(backoff_s)

    fechou = ticket_aberto(mt5, ticket)
    if fechou is None:
        log.critical("[fecho] #%s estado desconhecido após %d tentativas - "
                     "fecho NAO confirmado", ticket, tentativas)
        return False
    if fechou:
        log.critical("[fecho] #%s NÃO fechou após %d tentativas",
                     ticket, tentativas)
        return False
    return True


def fechar_todas_robusto(mt5, magics, *, reconnect, log, deviation=50,
                         tentativas=5, backoff_s=5.0, sleep=_time.sleep):
    """Fecha todas as posições do robô. Retorna `(fechadas, restantes)`.

    ``restantes`` pode ser ``None`` (estado desconhecido): o chamador NÃO
    pode tratar isso como flat.
    """
    alvos = posicoes_do_robo(mt5, magics)
    if alvos is None:
        log.warning("[fecho] positions_get() None - estado desconhecido; "
                    "nao da para fechar")
        return 0, None
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


class SalvamentoUnico:
    """Cada chave e executada no maximo UMA vez por encerramento (C3).

    O parar.txt agora sobrevive a trava de flat; se ela bloquear, o loop
    reexecuta o bloco de salvamento. Sem este guarda o modelo (~28 s em
    19/11) e as experiencias eram regravados a cada tentativa.
    """

    def __init__(self, log):
        self.log = log
        self._feitos = set()

    def executar(self, chave, acao):
        """True se executou agora; False se ja estava feita. Erros propagam."""
        if chave in self._feitos:
            self.log.info("[C3] '%s' ja salvo neste encerramento - pulando", chave)
            return False
        acao()
        self._feitos.add(chave)
        self.log.info("[C3] '%s' salvo uma unica vez neste encerramento", chave)
        return True
