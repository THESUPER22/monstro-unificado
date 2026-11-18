#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_pnl_dia.py  (P0 17/11 #3)

Testes do modulo pnl_dia.py (puro, sem MT5/TensorFlow).
Roda direto (python tests\\test_pnl_dia.py) ou via pytest.
"""
import calendar
import os
import sys
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from pnl_dia import data_do_deal, pnl_de_deals  # noqa: E402

DIA = "2026-11-17"
MAGIC_ROBO = 123456
MAGIC_ROMP = 7008
MAGIC_ESTRANHO = 999999


def ts(ano, mes, dia, hora=0, minuto=0, seg=0):
    """Epoch no mesmo formato do MT5 (hora do servidor codificada como UTC)."""
    return calendar.timegm((ano, mes, dia, hora, minuto, seg, 0, 0, 0))


def deal(hora, profit=0.0, comm=0.0, swap=0.0, fee=0.0, magic=MAGIC_ROBO,
         dia=17, mes=11, ano=2026, entry=1):
    return {"time": ts(ano, mes, dia, hora), "profit": profit,
            "commission": comm, "swap": swap, "fee": fee,
            "magic": magic, "entry": entry}


# ------------------------------------------------------------ data_do_deal --
def test_data_do_deal_usa_hora_do_servidor():
    # 17:35:02 no servidor == horario do log do robo em 17/11
    assert data_do_deal(ts(2026, 11, 17, 17, 35, 2)).isoformat() == "2026-11-17"
    assert data_do_deal(ts(2026, 11, 18, 0, 0, 0)).isoformat() == "2026-11-18"


# --------------------------------------------------------------- somatorio --
def test_soma_saidas_e_entradas_do_dia():
    deals = [
        deal(9, entry=0),                 # entrada: profit 0
        deal(10, profit=100.0, entry=1),
        deal(11, entry=0),
        deal(12, profit=-50.0, entry=1),
    ]
    total, n = pnl_de_deals(deals, DIA)
    assert (total, n) == (50.0, 4)


def test_inclui_comissao_swap_e_fee():
    deals = [
        deal(9, comm=-0.6, entry=0),      # entrada so com comissao
        deal(10, profit=10.0, comm=-0.6, swap=-0.1, fee=-0.2, entry=1),
    ]
    total, n = pnl_de_deals(deals, DIA)
    assert n == 2
    assert total == round(-0.6 + 10.0 - 0.6 - 0.1 - 0.2, 2)


def test_ignora_outros_dias():
    deals = [
        deal(10, profit=100.0, dia=16),
        deal(10, profit=25.0, dia=17),
        deal(10, profit=999.0, dia=18),
    ]
    total, n = pnl_de_deals(deals, DIA)
    assert (total, n) == (25.0, 1)


def test_bordas_do_dia():
    deals = [
        deal(0, profit=1.0),                                  # 00:00:00 entra
        deal(23, profit=2.0),                                 # 23:00 entra
        {"time": ts(2026, 11, 16, 23, 59, 59), "profit": 500.0, "magic": MAGIC_ROBO},
    ]
    total, n = pnl_de_deals(deals, DIA)
    assert (total, n) == (3.0, 2)


def test_filtro_por_magic():
    deals = [
        deal(10, profit=100.0, magic=MAGIC_ROBO),
        deal(10, profit=10.0, magic=MAGIC_ROMP),
        deal(10, profit=999.0, magic=MAGIC_ESTRANHO),
    ]
    total, n = pnl_de_deals(deals, DIA, magics=[MAGIC_ROBO, MAGIC_ROMP])
    assert (total, n) == (110.0, 2)
    # None = todos (inclui o estranho)
    total_todos, n_todos = pnl_de_deals(deals, DIA, magics=None)
    assert (total_todos, n_todos) == (1109.0, 3)


def test_magic_ausente_nao_quebra():
    deals = [{"time": ts(2026, 11, 17, 10), "profit": 5.0}]
    total, n = pnl_de_deals(deals, DIA, magics=[MAGIC_ROBO])
    assert (total, n) == (0.0, 0)      # sem magic != robo
    total_todos, n_todos = pnl_de_deals(deals, DIA, magics=None)
    assert (total_todos, n_todos) == (5.0, 1)


def test_dia_vazio():
    assert pnl_de_deals([], DIA) == (0.0, 0)
    assert pnl_de_deals(None, DIA) == (0.0, 0)


def test_aceita_date_e_string():
    deals = [deal(10, profit=7.5)]
    from datetime import date
    assert pnl_de_deals(deals, date(2026, 11, 17)) == (7.5, 1)
    assert pnl_de_deals(deals, "2026-11-17") == (7.5, 1)


def test_campos_none_e_objetos():
    # objetos do MT5 (atributos) + campos None
    d1 = SimpleNamespace(time=ts(2026, 11, 17, 10), profit=None,
                         commission=-0.6, swap=None, fee=None, magic=MAGIC_ROBO)
    d2 = SimpleNamespace(time=ts(2026, 11, 17, 11), profit=10.0,
                         commission=None, swap=0.0, fee=None, magic=MAGIC_ROBO)
    total, n = pnl_de_deals([d1, d2], DIA, magics=[MAGIC_ROBO])
    assert (total, n) == (9.4, 2)


def test_arredonda_duas_casas():
    deals = [deal(10, profit=0.1), deal(11, profit=0.2)]
    total, _ = pnl_de_deals(deals, DIA)
    assert total == 0.3


def test_estrutura_do_dia_17_11():
    """Estrutura real de 17/11: 34 deals = 17 entradas + 17 saidas.

    As entradas tem profit=0 (e comissao 0 na demo); o total e a soma das
    saidas. Os valores individuais aqui sao sinteticos - so a estrutura e a
    regra de soma sao verificadas.
    """
    saidas = [40.0] * 9 + [45.0] * 8  # 9 TP + 8 outras, soma 720
    deals = [deal(10, entry=0) for _ in range(17)]
    deals += [deal(11, profit=p, entry=1) for p in saidas]
    total, n = pnl_de_deals(deals, DIA, magics=[MAGIC_ROBO])
    assert n == 34
    assert total == 720.0


# ------------------------------------------------------------- integracao ---
def test_robo_usa_deals_como_fonte_primaria():
    """Guard: a fonte primaria e pnl_dia_mt5; a memoria vira fallback."""
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        fonte = f.read()
    assert "from pnl_dia import pnl_de_deals" in fonte
    assert "def pnl_dia_mt5(" in fonte
    assert "lucro_dia = pnl_dia_mt5()" in fonte
    assert "if lucro_dia is None:" in fonte


def _fonte():
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        return f.read()


def test_fallback_global_usa_memoria_do_breaker():
    """2.2: se o MT5 falhar, o fallback e circuit_breaker.loss_diario_atual."""
    fonte = _fonte()
    assert "historico_lucro[-100:]" not in fonte
    assert ("lucro_dia = circuit_breaker.loss_diario_atual if circuit_breaker"
            in fonte)
    assert 'if _log_periodico("pnl_dia_fallback", 3600):' in fonte


def test_breaker_da_classe_usa_pnl_do_mt5_e_max_loss():
    """2.2: CircuitBreakerEssencial le o P&L dos deals, nao so a memoria."""
    fonte = _fonte()
    ini = fonte.index("class CircuitBreakerEssencial")
    fim = fonte.index("LOSS_DIARIO_CB =", ini)  # fim do bloco da classe
    corpo = fonte[ini:fim]
    assert "pnl_dia_mt5()" in corpo
    assert "MAX_LOSS_DIARIO" in corpo
    assert "-1000.0" not in corpo  # limite nao pode voltar a ser literal
    assert "self.loss_diario_atual" in corpo  # fallback continua existindo
    assert 'if _log_periodico("cb_loss_fallback", 3600):' in corpo


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"[PASS] {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"[FAIL] {nome} - {e}")
    print(f"\n{'OK' if not falhas else 'FALHAS'}: {falhas}")
    sys.exit(1 if falhas else 0)
