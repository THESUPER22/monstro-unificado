# -*- coding: utf-8 -*-
"""Placebo historico (P0 17/11 #4, rev. 2.4).

``test_indentation_error`` nunca testou nada: um bloco ``try`` valido nao
levanta ``IndentationError`` (esse erro e de compilacao, nao de execucao), entao
o teste caia sempre no ``else: assert False``. Ele ficou marcado como
``xfail(strict=True)``: a suite fica verde e, se um dia o corpo passar a
passar de verdade, o pytest falha avisando que o xfail virou obsoleto.
"""
import pytest


@pytest.mark.xfail(strict=True,
                   reason="placebo: IndentationError nao ocorre em runtime")
def test_indentation_error():
    try:
        # Bloco valido: nunca levanta IndentationError em tempo de execucao.
        colunas_numericas = ['bid_qty', 'ask_qty', 'spread', 'volatility', 'entropia_book']
    except IndentationError:
        assert True
    else:
        assert False
