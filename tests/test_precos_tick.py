#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_precos_tick.py  (P0 17/11)

Testes do modulo precos_wdo.py (puro, sem MT5/TensorFlow).
Roda direto (python tests\\\\test_precos_tick.py) ou via pytest.

Criterio de aceite do P0 #1: nenhum preco enviado como SL pode deixar de ser
multiplo de ``trade_tick_size`` (0.5 no WDO). Os 18 valores abaixo sao os SLs
reais rejeitados com ``10016`` em 17/11 (17 de 18 nao eram multiplos de 0.5).
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from precos_wdo import (  # noqa: E402
    TICK_WDO, alinhar_ao_tick, alinhar_sl, alinhar_tp, tick_do_simbolo,
)

# Os 18 SLs realmente enviados e rejeitados em 17/11, na ordem do log
# (11 valores distintos; "FALHA ao mover SL" em monstro_wdo.log).
SLS_REJEITADOS_17_11 = [
    5792.25, 5792.0, 5787.75, 5788.75, 5789.25, 5793.75, 5788.75,
    5786.25, 5802.25, 5799.75, 5799.75, 5796.75, 5796.75, 5796.75,
    5796.75, 5797.25, 5797.25, 5797.25,
]


class _SymbolInfoFake:
    def __init__(self, tick):
        self.trade_tick_size = tick
        self.digits = 3
        self.point = 0.001


def _eh_multiplo(valor, tick=TICK_WDO):
    return abs(valor / tick - round(valor / tick)) < 1e-9


# --------------------------------------------------------------- tick ------
def test_tick_do_simbolo_usa_trade_tick_size():
    assert tick_do_simbolo(_SymbolInfoFake(0.5)) == 0.5
    assert tick_do_simbolo(_SymbolInfoFake(0.1)) == 0.1


def test_tick_do_simbolo_fallback():
    # 0.0 e None nao servem; digits/point nao devem ser usados
    assert tick_do_simbolo(_SymbolInfoFake(0.0)) == TICK_WDO
    assert tick_do_simbolo(None) == TICK_WDO
    assert tick_do_simbolo("lixo") == TICK_WDO
    assert tick_do_simbolo(_SymbolInfoFake(0.0), padrao=0.1) == 0.1


# ------------------------------------------------------------ alinhamento --
def test_alinhar_nearest():
    assert alinhar_ao_tick(5796.75, 0.5) == 5797.0
    assert alinhar_ao_tick(5796.74, 0.5) == 5796.5
    assert alinhar_ao_tick(5792.0, 0.5) == 5792.0
    # empate (.25 e .75) sobe, sem banker's rounding do round()
    assert alinhar_ao_tick(5796.25, 0.5) == 5796.5
    assert alinhar_ao_tick(5796.75, 0.5) == 5797.0


def test_alinhar_baixo_alto():
    assert alinhar_ao_tick(5796.75, 0.5, "baixo") == 5796.5
    assert alinhar_ao_tick(5796.75, 0.5, "alto") == 5797.0
    assert alinhar_ao_tick(5792.0, 0.5, "baixo") == 5792.0
    assert alinhar_ao_tick(5792.0, 0.5, "alto") == 5792.0


def test_alinhar_remove_ruido_float():
    assert alinhar_ao_tick(5790.999999999, 0.5) == 5791.0
    assert alinhar_ao_tick(5791.000000001, 0.5) == 5791.0


def test_modo_e_tick_invalidos():
    for ruim in ("", "proximo", None):
        try:
            alinhar_ao_tick(5792.0, 0.5, ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"modo {ruim!r} deveria levantar ValueError")
    for tick in (0, -0.5):
        try:
            alinhar_ao_tick(5792.0, tick)
        except ValueError:
            pass
        else:
            raise AssertionError(f"tick {tick!r} deveria levantar ValueError")


# ------------------------------------------------------------------- SL -----
def test_sl_lado_seguro():
    # BUY: floor -> nunca aproxima do preco (fica mais longe/abaixo)
    assert alinhar_sl(5796.75, "BUY") == 5796.5
    assert alinhar_sl(5796.75, "buy") == 5796.5
    assert alinhar_sl(5796.75, "COMPRA") == 5796.5
    # SELL: ceil -> nunca aproxima do preco (fica mais longe/acima)
    assert alinhar_sl(5796.75, "SELL") == 5797.0
    assert alinhar_sl(5796.75, "venda") == 5797.0
    # ja alinhado nao muda
    assert alinhar_sl(5792.0, "BUY") == 5792.0
    assert alinhar_sl(5792.0, "SELL") == 5792.0


def test_sl_nunca_aproxima_do_preco():
    for preco in SLS_REJEITADOS_17_11:
        assert alinhar_sl(preco, "BUY") <= preco
        assert alinhar_sl(preco, "SELL") >= preco


def test_todos_os_18_rejeitados_viram_tick_valido():
    """O criterio do P0: 18/18 alinhados (antes: 1/18)."""
    for preco in SLS_REJEITADOS_17_11:
        for lado in ("BUY", "SELL"):
            alvo = alinhar_sl(preco, lado)
            assert _eh_multiplo(alvo), f"{preco} ({lado}) -> {alvo} nao e tick"
    validos_antes = sum(1 for p in SLS_REJEITADOS_17_11 if _eh_multiplo(p))
    assert validos_antes == 1  # confirma o diagnostico: so 5792.0 era valido


def test_lado_invalido():
    for ruim in ("", "HOLD", None):
        try:
            alinhar_sl(5792.0, ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"lado {ruim!r} deveria levantar ValueError")


# ------------------------------------------------------------------- TP -----
def test_tp_nao_encurta_alvo():
    assert alinhar_tp(5796.75, "BUY") == 5797.0   # alvo acima
    assert alinhar_tp(5796.75, "SELL") == 5796.5  # alvo abaixo
    assert alinhar_tp(5792.0, "BUY") == 5792.0
    assert alinhar_tp(5792.0, "SELL") == 5792.0


# ------------------------------------------------------------- integracao ---
def test_robo_usa_alinhamento_no_envio_de_sl():
    """Guard de regressao: o envio em `atualizar_sl` nao pode voltar a
    arredondar so por `digits` (a causa dos 10016 de 17/11).

    Checagem estatica (sem importar o robo, que carrega TensorFlow).
    """
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        fonte = f.read()
    assert "from precos_wdo import alinhar_sl, tick_do_simbolo" in fonte
    assert "novo_sl = alinhar_sl(novo_sl, _lado, tick_do_simbolo(symbol_info))" in fonte
    assert '"sl": novo_sl if ALINHAR_SL_TICK else round(novo_sl, symbol_info.digits),' in fonte


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
