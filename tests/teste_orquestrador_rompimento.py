#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_orquestrador_rompimento.py

Testes deterministicos e OFF-LINE do Orquestrador Rompimento da 1a Hora
(rompimento_orquestrador.py). Roda SEM MT5 real (mock via sys.modules),
no padrao de teste_watchdog_e_fecho.py.

  RG1. gatilho BUY: caixa 09-10h rompida => abre posicao C lote 5, SL/TP.
  RG2. gatilho SELL: low rompido => abre posicao V.
  RG3. EOD: posicao aberta fecha a mercado em hora_eod 17:30.
  RG4. sem gatilho apos 11:06 => S/TRADE final registrado.
  RG5. ordem rejeitada (fn_executar=None) => S/TRADE "ordem nao enviada".
  RG6. idempotencia: segunda chamada do dia nao duplica registro.
  RG7. SL antes do TP intrabarra (resolve): empata => SL vence.
  RG8. prep sem caixa de 09h => None (dados incompletos).
  RG9. dfasagem_min real: ultima M5 recente => fresco; antiga => defasado.

  MEMORIA UNIFICADA (05/10):
  RG12. D2: reward vem dos deals do MT5 (profit+commission) em R$, nunca de pts.
  RG13. D3: registro carrega modulo/ticket/lucro_rs.
  RG14. D3: sub e Faixa 1 no mesmo dia nao se apagam.
  RG15. D1: snapshot fixado na entrada, memoria gravada na saida.
  RG16. D3: sub alimenta a memoria unificada.

Execucao: python tests/teste_orquestrador_rompimento.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

FALHAS = []


def checar(nome, condicao, detalhe=""):
    status = "PASS" if condicao else "FAIL"
    print("[%s] %s%s" % (status, nome, (" - %s" % detalhe) if detalhe else ""))
    if not condicao:
        FALHAS.append("%s: %s" % (nome, detalhe))


# ===== Importa o modulo com MetaTrader5 mockado (sem conexao) =====
with mock.patch.dict(sys.modules, {"MetaTrader5": mock.Mock()}):
    import rompimento_orquestrador as mod

_DFASAGEM_ORIG = mod.dfasagem_min


class _Pos:
    def __init__(self, ticket, price_open):
        self.ticket = ticket
        self.price_open = price_open


class _Deal:
    """Emula o TradeDeal do MT5 (namedtuple): atributo .entry/.price, mas SEM
    indexacao por string (d['entry'] levanta TypeError - bug real corrigido)."""
    def __init__(self, entry, price, profit=0.0, commission=0.0, swap=0.0):
        self.entry = entry
        self.price = price
        self.profit = profit
        self.commission = commission
        self.swap = swap
    def __getitem__(self, key):
        raise TypeError("tuple indices must be integers or slices, not str")


class FakeMT5:
    """MT5 fake para posicoes/deals. Barras/ticks injetados via hooks."""

    TIMEFRAME_M5 = 5
    DEAL_ENTRY_OUT = 1

    def __init__(self):
        self.positions = {}
        self.deals = {}
        self.fechamentos = []
        self.liquida = 0.0
        self.tick_preco = 0.0

    def symbol_info_tick(self, symbol):
        return mock.Mock(bid=self.tick_preco, ask=self.tick_preco)

    def positions_get(self, ticket=None):
        if ticket is not None:
            p = self.positions.get(ticket)
            return [p] if p is not None else None
        return (list(self.positions.values()) or None)

    def history_deals_get(self, position=None):
        if position is None:
            return None
        return self.deals.get(position)

    def position_close(self, ticket):
        if ticket in self.positions:
            del self.positions[ticket]
            self.fechamentos.append(ticket)
            self.deals.setdefault(ticket, []).append(_Deal(self.DEAL_ENTRY_OUT, self.liquida))
        return True


DIA = datetime(2026, 8, 24)  # segunda-feira (dia util)

CFG_FIXO = {
    "rompimento": {
        "ativo": True, "lote": 5.0, "sl_mode": "lo", "tp_k": 1.5,
        "janela_min": 60, "magic": 7008, "hora_inicio": 9.0,
        "hora_fim": 11.0, "hora_eod": "17:30", "stale_max_min": 12,
    }
}


def montar_fixture(bars, clock_pontos, tick_holder, fn_executar=None, fake=None,
                  mem_entrada=None, mem_saida=None):
    """Monta um OrquestradorRompimento com dados/mt5/relogio injetados."""
    import json as _json
    tmp = tempfile.mkdtemp(prefix="romp_test_")
    cfg = os.path.join(tmp, "config.json")
    with open(cfg, "w", encoding="utf-8") as f:
        _json.dump(CFG_FIXO, f)
    mod.CFG_PATH = cfg
    mod.LOG_FILE = os.path.join(tmp, "rompimento.log")
    mod.STATE_JSON = os.path.join(tmp, "rompimento_state.json")
    mod.TRADES_CSV = os.path.join(tmp, "rompimento_trades.csv")

    f = fake or FakeMT5()

    def bars_fn(mt5mod, symbol, data):
        dia = data if isinstance(data, datetime) else datetime.combine(data, datetime.min.time())
        return [b for b in bars if b[0].date() == dia.date()]

    relogio = mock.Mock(side_effect=clock_pontos)

    def ordem(action, lots, symbol, sl, tp, magic_override, comment):
        if fn_executar is None:
            t = 1001 if action == "BUY" else 2001
            f.positions[t] = _Pos(t, float(tick_holder["preco"]))
            return t
        return fn_executar(action, lots, symbol, sl, tp, magic_override, comment)

    sabe_preco = mock.Mock(side_effect=lambda: float(tick_holder["preco"]))

    orq = mod.OrquestradorRompimento(
        fn_executar=ordem, symbol="WDO$", ativo=True, mt5mod=f,
        clock=relogio, bars_fn=bars_fn, tick_fn=sabe_preco,
        mem_entrada=mem_entrada, mem_saida=mem_saida)
    mod.dfasagem_min = mock.Mock(return_value=1.0)
    return orq, tmp, f, sabe_preco


def gerar_barras(hi=100.0, lo=98.0, preco_abre=99.8, rompe="cima", sem_gatilho=False):
    """Barras da sessao 09:00-11:30 do DIA. Vela 10:00 rompe hi/lo."""
    bars = []
    t = datetime.combine(DIA.date(), datetime.min.time())
    # hora 9 = caixa
    for m in range(0, 60, 5):
        dt = t.replace(hour=9, minute=m)
        o = h = l = c = 99.0
        if m == 30:
            o = 98.6; h = hi; l = 98.2; c = 99.4   # vela que define o hi
        elif m == 45:
            o = 99.2; h = 99.5; l = lo; c = 98.8   # vela que define o lo
        bars.append((dt, o, h, l, c, 200))
    # hora 10 = gatilho
    for m in (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55):
        dt = t.replace(hour=10, minute=m)
        if sem_gatilho:
            o = h = l = c = 99.5
        elif rompe == "cima" and m == 0:
            o = preco_abre; h = 100.7; l = 99.6; c = 100.5
        elif rompe == "baixo" and m == 0:
            o = preco_abre; h = 99.4; l = 97.6; c = 97.9
        else:
            o = h = l = c = 99.5
        bars.append((dt, o, h, l, c, 200))
    # hora 11 avulsa (para trig() ter onde verificar)
    dt = t.replace(hour=11, minute=0)
    bars.append((dt, 99.5, 99.6, 99.4, 99.5, 200))
    return bars


def _ler_csv(tmp):
    rows = []
    if os.path.exists(os.path.join(tmp, "rompimento_trades.csv")):
        import csv
        with open(os.path.join(tmp, "rompimento_trades.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows


def gerar_barras_sub(pavio_topo, pavio_fundo):
    """Barras p/ Sub-Trader: candle 1H da hora 9 com corpo (open=100, close=101)
    e pavios controlados. Pavio_Topo/Maxima = pavio_topo (v 09:30),
    Pavio_Fundo/Minima = pavio_fundo (v 09:45). Retorna (bars, cl=[10:00]).
    Entrada BUY esperada: corpo_topo=101, corpo_fundo=100; com tick 101.5:
      dist_tp = pavio_topo - 101.5 ; dist_sl = 101.5 - pavio_fundo
    """
    t = datetime.combine(DIA.date(), datetime.min.time())
    bars = []
    minutos = [m for m in range(0, 60, 5)]
    for m in minutos:
        dt = t.replace(hour=9, minute=m)
        if m == 30:
            bars.append((dt, 100.0, pavio_topo, 100.0, 100.0, 200))
        elif m == 45:
            bars.append((dt, 100.0, 100.0, pavio_fundo, 100.0, 200))
        elif m == 55:
            bars.append((dt, 101.0, 101.0, 101.0, 101.0, 200))
        else:
            bars.append((dt, 100.0, 100.0, 100.0, 100.0, 200))
    dt = t.replace(hour=10, minute=0)
    bars.append((dt, 100.5, 101.0, 100.0, 100.5, 200))  # dentro do corpo: sem gatilho Faixa 1
    return bars


# ---------------------------------------------------------------------------
def test_gatilho_buy():
    bars = gerar_barras(rompe="cima")
    tick = {"preco": 100.2}
    orq, tmp, _f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick)
    orq.orquestrar()
    st = mod._carregar_state()

    checar("RG1 abre BUY", st.get("side") == "C" and st.get("ticket") == 1001)
    checar("RG1 entrada = tick", abs(st["entry"] - 100.2) < 1e-9)
    checar("RG1 SL = lo caixa", abs(st["sl_lvl"] - 100.0 * 0 + 98.0) < 1e-9 or abs(st["sl_lvl"] - 98.0) < 1e-9)
    checar("RG1 TP = 1.5x rr", abs(st["tp_lvl"] - (100.2 + 1.5 * (100.0 - 98.0))) < 1e-9)
    checar("RG1 nao finalizado", st.get("final") is False)


def test_gatilho_sell():
    bars = gerar_barras(rompe="baixo", preco_abre=97.8)
    tick = {"preco": 97.8}
    orq, tmp, _f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick)
    orq.orquestrar()
    st = mod._carregar_state()
    checar("RG2 abre SELL", st.get("side") == "V" and st.get("ticket") == 2001)
    checar("RG2 SL = hi caixa", abs(st["sl_lvl"] - 100.0) < 1e-9)
    checar("RG2 TP abaixo", st["tp_lvl"] < 97.8)


def test_eod_fecha_market():
    bars = gerar_barras(rompe="cima")
    tick = {"preco": 100.2}
    orq, tmp, _f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6), DIA.replace(hour=17, minute=31)], tick)
    orq.orquestrar()  # abre
    _f.liquida = 102.0  # preco de saida no EOD
    orq.orquestrar()  # segunda chamada: hora 17:31 -> EOD
    st = mod._carregar_state()
    rows = _ler_csv(tmp)
    checar("RG3 final EOD", st.get("final") is True and st.get("saida") == "EOD")
    checar("RG3 pts fechados", st.get("pts") is not None and abs(st["pts"] - 1.8) < 1e-9)
    checar("RG3 registro unico no CSV",
           len(rows) == 1 and rows[0]["saida"] == "EOD" and rows[0]["dia"] == "2026-08-24")


def test_sem_gatilho():
    bars = gerar_barras(sem_gatilho=True)
    tick = {"preco": 99.5}
    orq, tmp, _f, _ = montar_fixture(bars, [DIA.replace(hour=11, minute=7)], tick)
    orq.orquestrar()
    st = mod._carregar_state()
    rows = _ler_csv(tmp)
    checar("RG4 S/TRADE final", st.get("final") is True and st.get("saida") == "S/TRADE")
    checar("RG4 registro S/TRADE", len(rows) == 1 and rows[0]["saida"] == "S/TRADE")


def test_sub_rr_rejeita():
    """RG10: rompimento com R/R<1.0 (pavio a favor curto x oposto longo)
    e REJEITADO pelo filtro estrutural -> nenhum ticket de sub aberto."""
    bars = gerar_barras_sub(pavio_topo=102.0, pavio_fundo=96.0)
    tick = {"preco": 101.5}
    orq, tmp, f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick)
    f.tick_preco = 101.5  # ask rompe corpo_topo=101 => BUY candidato
    orq.orquestrar()
    st = mod._carregar_state()
    sub = st.get("sub") or {}
    checar("RG10 R/R<1 rejeitado (sem ticket sub)",
           sub.get("ticket") is None and not sub.get("final"))
    checar("RG10 Faixa 1 nao abriu", st.get("ticket") is None)


def test_sub_rr_aceita():
    """RG11: rompimento com R/R>=1.0 (pavio a favor >= oposto) e ACEITO ->
    sub abre BUY e bloqueia a Faixa 1."""
    bars = gerar_barras_sub(pavio_topo=103.5, pavio_fundo=99.5)
    # dist_tp = 103.5-101.5 = 2.0 ; dist_sl = 101.5-99.5 = 2.0 => R/R = 1.0
    tick = {"preco": 101.5}
    orq, tmp, f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick)
    f.tick_preco = 101.5
    orq.orquestrar()
    st = mod._carregar_state()
    sub = st.get("sub") or {}
    checar("RG11 R/R>=1 abre BUY sub", sub.get("side") == "C" and sub.get("ticket") == 1001)
    checar("RG11 sub ainda aberto (bloqueia Faixa 1)",
           sub.get("final") is False and st.get("ticket") is None)
    rows = _ler_csv(tmp)
    checar("RG11 sem registro Faixa 1", len(rows) == 0)


def test_ordem_rejeitada():
    bars = gerar_barras(rompe="cima")
    tick = {"preco": 100.2}
    orq, tmp, _f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick,
                              fn_executar=lambda *a, **k: None)
    orq.orquestrar()
    st = mod._carregar_state()
    rows = _ler_csv(tmp)
    checar("RG5 rejeitada -> S/TRADE final", st.get("final") is True and st.get("saida") == "S/TRADE")
    checar("RG5 obs registrado", len(rows) == 1 and "nao enviada" in rows[0].get("obs", ""))


def test_idempotencia():
    bars = gerar_barras(sem_gatilho=True)
    tick = {"preco": 99.5}
    orq, tmp, _f, _ = montar_fixture(bars, [DIA.replace(hour=11, minute=7)] * 3, tick)
    for _ in range(3):
        orq.orquestrar()
    rows = _ler_csv(tmp)
    checar("RG6 idempotente (1 registro)", len(rows) == 1)


def test_sl_antes_do_tp():
    t = {"hi": 100.0, "lo": 98.0, "rr": 2.0,
         "bars": [(DIA.replace(hour=10, minute=5), 100.1, 103.3, 97.9, 100.0, 100)],  # TP e SL na MESMA vela
         "fim": 10 * 3600 + 60 * 60}
    pts, saida = mod.resolve(t, "C", 0, 100.2, "lo", 1.5)
    checar("RG7 SL vence intrabarra", saida == "SL" and abs(abs(pts) - 2.2) < 1e-9)


def test_prep_incompleto():
    bars = [(DIA.replace(hour=10, minute=0), 99, 99.5, 98.5, 99, 100)]  # sem caixa 09h
    checar("RG8 prep sem caixa=9h", mod.prep_safe(bars) is None)


def test_dfasagem_min():
    try:
        import numpy  # noqa: F401  (nao instalado no runner CI)
    except ImportError:
        print("[SKIP] RG9 (numpy indisponivel)")
        return
    agora = datetime.now()
    f = FakeMT5()

    def rates(ocs, base_t):
        import numpy as np
        arr = np.zeros(len(ocs), dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"),
                                        ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")])
        for i, (o, h, l, c) in enumerate(ocs):
            arr[i]["time"] = int((base_t + timedelta(seconds=300 * i)).timestamp())
            arr[i]["open"], arr[i]["high"], arr[i]["low"], arr[i]["close"] = o, h, l, c
        return arr

    f.copy_rates_from_pos = mock.Mock(return_value=rates([(99, 99, 99, 99)], agora - timedelta(minutes=2)))
    checar("RG9 barra 2min = fresco", _DFASAGEM_ORIG(f, "WDO$") <= 12.0)

    f2 = FakeMT5()
    f2.copy_rates_from_pos = mock.Mock(return_value=rates([(99, 99, 99, 99)], agora - timedelta(minutes=40)))
    checar("RG9 barra 40min = defasado", _DFASAGEM_ORIG(f2, "WDO$") > 12.0)


# =========================================================================
# MEMORIA UNIFICADA (05/10) - D1 contexto real, D2 reward em R$, D3 sub
# =========================================================================
def test_lucro_real_rs_dos_deals():
    """D2: o reward sai dos deals do MT5 (R$), nunca de 'pts'."""
    bars = gerar_barras(rompe="cima")
    tick = {"preco": 100.2}
    orq, tmp, f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick)
    f.deals[1001] = [_Deal(f.DEAL_ENTRY_OUT, 100.9, profit=-80.0, commission=-4.0, swap=0.0)]
    checar("RG12 lucro real = profit+commission",
           orq._lucro_real_rs(1001) == -84.0, str(orq._lucro_real_rs(1001)))
    checar("RG12 sem deal => None", orq._lucro_real_rs(9999) is None)
    checar("RG12 sem ticket => None", orq._lucro_real_rs(None) is None)


def test_csv_tem_modulo_e_lucro_rs():
    """D3: o registro carrega modulo/lucro_rs/ticket na trilha unificada."""
    bars = gerar_barras(rompe="cima")
    tick = {"preco": 100.2}
    orq, tmp, f, _ = montar_fixture(bars, [DIA.replace(hour=10, minute=6)], tick)
    f.deals[1001] = [_Deal(f.DEAL_ENTRY_OUT, 100.9, profit=40.0)]
    orq.orquestrar()
    st = mod._carregar_state()
    orq._finaliza(st, 100.9, "TP", "teste")
    rows = _ler_csv(tmp)
    checar("RG13 modulo=faixa1", len(rows) == 1 and rows[0].get("modulo") == "faixa1")
    checar("RG13 ticket gravado", rows[0].get("ticket") == "1001")
    checar("RG13 lucro_rs em R$", rows[0].get("lucro_rs") == "40.0")


def test_faixa1_e_sub_nao_se_apagam():
    """D3: o sub NAO pode apagar o registro da Faixa 1 no mesmo dia."""
    _registrar = mod._registrar_trade
    try:
        mod.HEADER_TRADES = ["dia", "side", "entrada", "sl", "tp", "saida", "pts",
                             "obs", "ticket", "modulo", "lucro_rs"]
        mod.TRADES_CSV = os.path.join(tempfile.mkdtemp(prefix="mem_test_"), "t.csv")
        mod._registrar_trade(dict(dia="2026-08-24", side="C", entrada=1, sl=0,
                                  tp=0, saida="TP", pts=5, obs="", ticket=1,
                                  modulo="faixa1", lucro_rs=50.0))
        mod._registrar_trade(dict(dia="2026-08-24", side="V", entrada=1, sl=0,
                                  tp=0, saida="TP", pts=3, obs="", ticket=2,
                                  modulo="sub", lucro_rs=30.0))
        with open(mod.TRADES_CSV, encoding="utf-8") as f:
            import csv as _c
            rows = list(_c.DictReader(f))
        checar("RG14 dois registros no mesmo dia", len(rows) == 2, str(len(rows)))
        checar("RG14 faixa1 preservada",
               any(r["modulo"] == "faixa1" for r in rows))
        checar("RG14 sub preservado",
               any(r["modulo"] == "sub" for r in rows))
    finally:
        mod._registrar_trade = _registrar


def test_memoria_callbacks_disparam():
    """D1: o snapshot e fixado na entrada e o registro ocorre na saida."""
    barras = gerar_barras(rompe="cima")
    tick = {"preco": 100.2}
    fixados, gravados = [], []

    def mem_entrada(ticket, symbol, modulo, side=None):
        fixados.append((ticket, modulo))

    def mem_saida(ticket, lucro_rs, side=None, saida=None):
        gravados.append((ticket, lucro_rs, side, saida))

    import json as _json
    tmp = tempfile.mkdtemp(prefix="mem_cb_")
    cfg = os.path.join(tmp, "config.json")
    _json.dump(CFG_FIXO, open(cfg, "w", encoding="utf-8"))
    mod.CFG_PATH = cfg
    mod.LOG_FILE = os.path.join(tmp, "r.log")
    mod.STATE_JSON = os.path.join(tmp, "s.json")
    mod.TRADES_CSV = os.path.join(tmp, "t.csv")

    f = FakeMT5()

    def bars_fn(mt5mod, symbol, data):
        dia = data if isinstance(data, datetime) else datetime.combine(data, datetime.min.time())
        return [b for b in barras if b[0].date() == dia.date()]

    def ordem(action, lots, symbol, sl, tp, magic_override, comment):
        t = 1001 if action == "BUY" else 2001
        f.positions[t] = _Pos(t, float(tick["preco"]))
        return t

    orq = mod.OrquestradorRompimento(
        fn_executar=ordem, symbol="WDO$", ativo=True, mt5mod=f,
        clock=mock.Mock(return_value=DIA.replace(hour=10, minute=6)),
        bars_fn=bars_fn, tick_fn=lambda: 100.2,
        mem_entrada=mem_entrada, mem_saida=mem_saida)
    mod.dfasagem_min = mock.Mock(return_value=1.0)
    orq.orquestrar()
    f.positions.pop(1001, None)
    f.deals[1001] = [_Deal(f.DEAL_ENTRY_OUT, 100.9, profit=40.0)]
    st = mod._carregar_state()
    orq._finaliza(st, 100.9, "TP", "teste")
    checar("RG15 snapshot fixado na entrada", fixados and fixados[0][1] == "faixa1", str(fixados))
    checar("RG15 memoria gravada na saida", gravados and gravados[0][1] == 40.0, str(gravados))


def test_sub_grava_na_memoria():
    """D3: o sub tambem alimenta a memoria unificada."""
    gravados = []
    f = FakeMT5()
    orq, tmp, _f, _ = montar_fixture(
        gerar_barras(), [DIA.replace(hour=10, minute=6)], {"preco": 100.2},
        fake=f, mem_entrada=lambda *a: None,
        mem_saida=lambda t, l, s=None, d=None: gravados.append((t, l, s)))
    st = orq._cria_estado("2026-08-24")
    st["dia"] = "2026-08-24"
    f.deals[555] = [_Deal(f.DEAL_ENTRY_OUT, 100.9, profit=25.0)]
    st["sub"] = dict(side="C", entry=100.0, sl_lvl=99.0, tp_lvl=102.0,
                     ticket=555, final=True, saida="TP", pts=0.9, obs="sub")
    orq._grava_final_sub(st)
    rows = _ler_csv(tmp)
    checar("RG16 sub gravado no CSV", len(rows) == 1 and rows[0].get("modulo") == "sub")
    checar("RG16 sub enviou memoria", gravados and gravados[0][1] == 25.0, str(gravados))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_gatilho_buy()
    test_gatilho_sell()
    test_eod_fecha_market()
    test_sem_gatilho()
    test_sub_rr_rejeita()
    test_sub_rr_aceita()
    test_ordem_rejeitada()
    test_idempotencia()
    test_sl_antes_do_tp()
    test_prep_incompleto()
    test_dfasagem_min()
    test_lucro_real_rs_dos_deals()
    test_csv_tem_modulo_e_lucro_rs()
    test_faixa1_e_sub_nao_se_apagam()
    test_memoria_callbacks_disparam()
    test_sub_grava_na_memoria()
    print("\n%d falha(s)" % len(FALHAS))
    sys.exit(1 if FALHAS else 0)