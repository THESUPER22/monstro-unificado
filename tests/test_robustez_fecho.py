# -*- coding: utf-8 -*-
"""Testes dos helpers de robustez do fecho — PROPOSTA (ROADMAP 23.27).

Roda SEM MT5 real: um `FakeMT5` é injetado. Nenhum arquivo do robô é tocado.
Também roda direto:  python tests/test_robustez_fecho.py

Cobertura (as 4 correções propostas):
  C1. retcode 10031 -> reconecta com backoff e conclui quando o feed volta.
  C1b. falha persistente -> NÃO mente: reporta restantes e loga critical.
  C2. retcode DONE sem posição realmente fechada -> NÃO conta como sucesso.
  C3. `fechar_todas_robusto` devolve `restantes` (base da trava de shutdown).
  C4. contagem de deals reais por magic (ignora magic alheio e DEAL_ENTRY_IN).
"""
import os
import sys
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "patches"))

import robustez_fecho_helpers as rh  # noqa: E402

MAGIC_CORE = 123456
MAGIC_FAIXA1 = 7008
MAGIC_ALHEIO = 123457


# ===== dublês =====
class FakePos:
    def __init__(self, ticket, symbol="WDOZ26", volume=1.0, tipo=1,
                 magic=MAGIC_CORE):
        self.ticket = ticket
        self.symbol = symbol
        self.volume = volume
        self.type = tipo
        self.magic = magic


class FakeMT5:
    # constantes equivalentes às do MetaTrader5 real
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self, positions=None, filling_mode=7):
        self._positions = list(positions or [])
        self.filling_mode = filling_mode
        self.tick = SimpleNamespace(bid=5585.5, ask=5586.0)
        self.sent = []
        self.deals = []
        # handler(req, n) -> retcode | None. None => comportamento padrão (fecha).
        self.handler = None
        self._n = 0

    def positions_get(self, ticket=None):
        if ticket is not None:
            return tuple(p for p in self._positions if p.ticket == ticket)
        return tuple(self._positions)

    def symbol_info(self, symbol):
        return SimpleNamespace(filling_mode=self.filling_mode)

    def symbol_info_tick(self, symbol):
        return self.tick

    def order_send(self, req):
        self.sent.append(dict(req))
        self._n += 1
        if self.handler is not None:
            rc = self.handler(req, self._n)
        else:
            self.fechar(req["position"])
            rc = rh.RETCODE_DONE
        if rc is None:
            return None
        return SimpleNamespace(retcode=rc, comment="fake", deal=self._n)

    def history_deals_get(self, inicio, fim):
        return list(self.deals)

    def fechar(self, ticket):
        self._positions = [p for p in self._positions if p.ticket != ticket]


class FakeLog:
    def __init__(self):
        self.records = []

    def _add(self, level, msg, *args):
        self.records.append((level, msg % args if args else msg))

    def info(self, msg, *args):
        self._add("info", msg, *args)

    def warning(self, msg, *args):
        self._add("warning", msg, *args)

    def error(self, msg, *args):
        self._add("error", msg, *args)

    def critical(self, msg, *args):
        self._add("critical", msg, *args)

    def tem(self, level):
        return any(lvl == level for lvl, _ in self.records)


def _rodar(fake, magics, **kw):
    reconnects = []
    sleeps = []

    def reconnect():
        reconnects.append(1)
        return True

    def sleep(s):
        sleeps.append(s)

    log = FakeLog()
    fechadas, restantes = rh.fechar_todas_robusto(
        fake, magics, reconnect=reconnect, log=log, sleep=sleep, **kw)
    return fechadas, restantes, reconnects, sleeps, log


# ===== C1: fecho normal =====
def test_fecho_ok_uma_posicao():
    fake = FakeMT5([FakePos(111, tipo=1)])
    fechadas, restantes, rec, sleeps, _ = _rodar(fake, {MAGIC_CORE})
    assert fechadas == 1
    assert restantes == []
    assert len(fake.sent) == 1
    # fecha SELL com BUY e usa o ticket certo
    assert fake.sent[0]["type"] == fake.ORDER_TYPE_BUY
    assert fake.sent[0]["position"] == 111
    assert rec == [] and sleeps == []


def test_fechar_todas_sem_posicoes():
    fake = FakeMT5([])
    fechadas, restantes, rec, _, _ = _rodar(fake, {MAGIC_CORE})
    assert (fechadas, restantes, rec) == (0, [], [])
    assert fake.sent == []


def test_posicao_ja_ausente_conta_como_fechada():
    fake = FakeMT5([])
    log = FakeLog()
    ok = rh.fechar_posicao_robusto(
        fake, FakePos(999), reconnect=lambda: True, log=log,
        sleep=lambda s: None)
    assert ok is True
    assert fake.sent == []


# ===== C1: retcode 10031 com reconexão/backoff =====
def test_retcode_10031_reconecta_e_fecha():
    fake = FakeMT5([FakePos(222, tipo=1)])

    def handler(req, n):
        if n == 1:
            return rh.RETCODE_NO_CONNECTION
        fake.fechar(req["position"])
        return rh.RETCODE_DONE

    fake.handler = handler
    fechadas, restantes, rec, sleeps, _ = _rodar(fake, {MAGIC_CORE})
    assert fechadas == 1
    assert restantes == []
    assert len(rec) == 1          # reconectou antes da 2ª tentativa
    assert sleeps == [5.0]        # backoff padrão de 5 s
    assert len(fake.sent) == 2    # 10031 + fecho bem-sucedido


def test_retcode_10031_falha_persistente_reporta_restantes():
    fake = FakeMT5([FakePos(333, tipo=1)])
    fake.handler = lambda req, n: rh.RETCODE_NO_CONNECTION
    fechadas, restantes, rec, sleeps, log = _rodar(
        fake, {MAGIC_CORE}, tentativas=3, backoff_s=2.0)
    assert fechadas == 0
    assert restantes == [333]
    assert len(rec) == 3 and sleeps == [2.0, 2.0, 2.0]
    assert log.tem("critical")    # operador é avisado, não enganado


def test_order_send_none_reconecta_e_fecha():
    fake = FakeMT5([FakePos(444, tipo=0)])  # BUY fecha com SELL

    def handler(req, n):
        if n <= 3:  # todos os fillings da 1ª tentativa falham
            return None
        fake.fechar(req["position"])
        return rh.RETCODE_DONE

    fake.handler = handler
    fechadas, restantes, rec, _, _ = _rodar(fake, {MAGIC_CORE})
    assert fechadas == 1 and restantes == []
    assert len(rec) == 1
    assert fake.sent[-1]["type"] == fake.ORDER_TYPE_SELL


# ===== C2: retcode nunca substitui a confirmação =====
def test_retcode_done_sem_fechar_nao_conta_como_sucesso():
    fake = FakeMT5([FakePos(555, tipo=1)])
    fake.handler = lambda req, n: rh.RETCODE_DONE  # mente: não remove a posição
    fechadas, restantes, rec, _, log = _rodar(
        fake, {MAGIC_CORE}, tentativas=2)
    assert fechadas == 0
    assert restantes == [555]
    assert len(rec) == 1
    assert log.tem("critical")


# ===== C3: magics =====
def test_ignora_magic_alheio():
    fake = FakeMT5([
        FakePos(666, tipo=1, magic=MAGIC_CORE),
        FakePos(777, tipo=0, magic=MAGIC_ALHEIO),
    ])
    fechadas, restantes, _, _, _ = _rodar(
        fake, {MAGIC_CORE, MAGIC_FAIXA1})
    assert fechadas == 1
    assert restantes == []
    # a posição alheia continua aberta e nunca foi enviada
    assert [p.ticket for p in fake.positions_get()] == [777]
    assert all(req["position"] != 777 for req in fake.sent)


def test_posicoes_restantes_so_do_robo():
    fake = FakeMT5([
        FakePos(1, magic=MAGIC_CORE),
        FakePos(2, magic=MAGIC_FAIXA1),
        FakePos(3, magic=MAGIC_ALHEIO),
    ])
    assert rh.posicoes_restantes(fake, {MAGIC_CORE, MAGIC_FAIXA1}) == [1, 2]
    assert rh.posicoes_restantes(fake, set()) == []


# ===== fillings =====
def test_fillings_bitmask():
    assert rh.fillings_disponiveis(FakeMT5(filling_mode=2), "WDOZ26") == [
        FakeMT5.ORDER_FILLING_IOC]
    assert rh.fillings_disponiveis(FakeMT5(filling_mode=5), "WDOZ26") == [
        FakeMT5.ORDER_FILLING_FOK, FakeMT5.ORDER_FILLING_RETURN]
    assert rh.fillings_disponiveis(FakeMT5(filling_mode=0), "WDOZ26") == [
        FakeMT5.ORDER_FILLING_FOK, FakeMT5.ORDER_FILLING_IOC,
        FakeMT5.ORDER_FILLING_RETURN]


# ===== C4: relatório por deals reais =====
def _deal(magic, entry, profit, swap=0.0, commission=0.0):
    return SimpleNamespace(magic=magic, entry=entry, profit=profit,
                           swap=swap, commission=commission)


def test_contar_deals_reais_por_magic():
    fake = FakeMT5([])
    fake.deals = [
        _deal(MAGIC_CORE, fake.DEAL_ENTRY_OUT, 15.0),
        _deal(MAGIC_FAIXA1, fake.DEAL_ENTRY_OUT, -50.0, commission=-0.6),
        _deal(MAGIC_ALHEIO, fake.DEAL_ENTRY_OUT, 5.0),   # fantasma WINV25
        _deal(MAGIC_CORE, fake.DEAL_ENTRY_IN, 0.0),      # entrada não conta
    ]
    n, pnl = rh.contar_deals_reais_hoje(fake, {MAGIC_CORE, MAGIC_FAIXA1},
                                        "inicio", "fim")
    assert n == 2
    assert abs(pnl - (-35.6)) < 1e-9


def test_contar_deals_sem_historico():
    fake = FakeMT5([])
    fake.deals = []
    assert rh.contar_deals_reais_hoje(fake, {MAGIC_CORE}, 0, 1) == (0, 0.0)


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print("[PASS] " + nome)
            except AssertionError as e:
                falhas += 1
                print("[FAIL] %s -> %s" % (nome, e))
    print("=" * 50)
    if falhas:
        print("%d teste(s) falharam" % falhas)
        sys.exit(1)
    print("TODOS OS TESTES PASSARAM")
