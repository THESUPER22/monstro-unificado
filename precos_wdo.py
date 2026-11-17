# -*- coding: utf-8 -*-
"""Alinhamento de precos ao tick real do WDO (modulo puro).

Motivo (P0 17/11, ver 23.51.9): o trailing enviava SL arredondado por
``symbol_info.digits`` (3 casas) em vez do tick de negociacao
(``trade_tick_size`` = 0.5). Resultado: 17 de 18 rejeicoes ``10016 Invalid
stops`` de 17/11 eram precos impossiveis (5796.75, 5797.25, 5786.25...).

Fontes dos valores quebrados, todas passando por ``atualizar_sl``:
  - trailing 50% do Sniper: ``entrada + 0.5 * lucro_pts`` (L7416-7419);
  - ``TrailingStopInteligente``: ``lucro_pontos * 0.7 * TICK_SIZE`` (L149).

Este modulo NAO importa MetaTrader5, TensorFlow nem nada do robo, para poder
ser testado isoladamente (``tests/teste_precos_tick.py``).
"""
from __future__ import annotations

import math

TICK_WDO = 0.5
_EPS = 1e-9


def tick_do_simbolo(symbol_info=None, padrao: float = TICK_WDO) -> float:
    """Tick de negociacao do simbolo, com fallback seguro.

    WDOZ26: ``trade_tick_size = 0.5`` (``digits = 3`` e ``point = 0.001``
    enganam quem arredonda por casas). Aceita o objeto do MT5 ou um float;
    qualquer valor invalido cai no ``padrao``.
    """
    tick = getattr(symbol_info, "trade_tick_size", symbol_info)
    try:
        tick = float(tick)
    except (TypeError, ValueError):
        return float(padrao)
    return tick if tick > 0 else float(padrao)


def alinhar_ao_tick(preco: float, tick: float = TICK_WDO, modo: str = "nearest") -> float:
    """Alinha ``preco`` a um multiplo de ``tick``.

    modo:
      - ``"nearest"``: multiplo mais proximo (empate sobe; sem banker's rounding)
      - ``"baixo"``:   floor (para SL de BUY, nunca aproxima do preco)
      - ``"alto"``:    ceil  (para SL de SELL, nunca aproxima do preco)
    """
    if tick <= 0:
        raise ValueError(f"tick deve ser > 0 (recebido {tick!r})")
    n = float(preco) / tick
    if modo == "nearest":
        k = math.floor(n + 0.5)
    elif modo == "baixo":
        k = math.floor(n + _EPS)
    elif modo == "alto":
        k = math.ceil(n - _EPS)
    else:
        raise ValueError(f"modo invalido: {modo!r} (use nearest|baixo|alto)")
    # round(..., 10) remove ruido de ponto flutuante (ex.: 5790.999999999)
    return round(k * tick, 10)


def alinhar_sl(preco: float, lado: str, tick: float = TICK_WDO) -> float:
    """Alinha o SL ao tick no lado SEGURO: afasta do preco, nunca aproxima.

    BUY  -> SL abaixo do preco -> floor (``"baixo"``)
    SELL -> SL acima do preco  -> ceil  (``"alto"``)
    """
    lado_norm = str(lado or "").strip().upper()
    if lado_norm in ("BUY", "COMPRA"):
        return alinhar_ao_tick(preco, tick, "baixo")
    if lado_norm in ("SELL", "VENDA"):
        return alinhar_ao_tick(preco, tick, "alto")
    raise ValueError(f"lado invalido: {lado!r} (use BUY|SELL)")


def alinhar_tp(preco: float, lado: str, tick: float = TICK_WDO) -> float:
    """Alinha o TP ao tick sem encurtar o alvo.

    BUY  -> TP acima do preco -> ceil  (``"alto"``)
    SELL -> TP abaixo do preco -> floor (``"baixo"``)
    """
    lado_norm = str(lado or "").strip().upper()
    if lado_norm in ("BUY", "COMPRA"):
        return alinhar_ao_tick(preco, tick, "alto")
    if lado_norm in ("SELL", "VENDA"):
        return alinhar_ao_tick(preco, tick, "baixo")
    raise ValueError(f"lado invalido: {lado!r} (use BUY|SELL)")
