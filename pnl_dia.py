# -*- coding: utf-8 -*-
"""P&L diario a partir dos deals do MT5 (P0 17/11 #3).

Fonte unica de verdade: o extrato da corretora (``history_deals_get``), nao o
historico em memoria (``historico_lucro[-100:]``) nem o parse do log.

Soma o **fluxo de caixa** do dia: ``profit + commission + swap + fee`` de
TODOS os deals do dia. Deal de entrada tem ``profit = 0`` mas pode ter
comissao, entao filtrar so as saidas subestimaria o custo.

Convencao de tempo do MT5: ``deal.time`` e o relogio do SERVIDOR codificado
como epoch "UTC" (``utcfromtimestamp`` devolve a hora do servidor). Validado
em 17/11: o deal 1882256502 (ultimo fechamento) da 17:35:02, o mesmo horario
do log do robo. Por isso o filtro de dia usa ``fromtimestamp(ts, UTC).date()``.

Modulo puro (sem MT5), testavel em ``tests/test_pnl_dia.py``.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable, Optional, Tuple


def _campo(deal, nome: str, padrao=0.0):
    """Le ``nome`` de um dict ou de um objeto do MT5, tolerando None."""
    valor = deal.get(nome, padrao) if isinstance(deal, dict) else getattr(deal, nome, padrao)
    return padrao if valor is None else valor


def data_do_deal(ts) -> date:
    """Data do servidor de um ``deal.time`` (epoch codificado como UTC)."""
    return datetime.fromtimestamp(float(ts), timezone.utc).date()


def pnl_de_deals(deals: Iterable,
                 dia,
                 magics: Optional[Iterable[int]] = None) -> Tuple[float, int]:
    """Soma o resultado liquido (cash flow) dos deals de ``dia``.

    Parametros:
      deals: iterable de objetos MT5 ou dicts com
             ``time/profit/commission/swap/fee/magic``.
      dia: ``datetime.date`` ou ``"AAAA-MM-DD"`` (dia do servidor).
      magics: colecao de magics a incluir; ``None`` = todos.

    Retorna ``(total, n_deals)``; total arredondado a 2 casas.
    """
    if isinstance(dia, str):
        dia = datetime.strptime(dia, "%Y-%m-%d").date()
    alvo = set(int(m) for m in magics) if magics is not None else None

    total = 0.0
    n = 0
    for deal in deals or ():
        if alvo is not None and int(_campo(deal, "magic", -1)) not in alvo:
            continue
        if data_do_deal(_campo(deal, "time")) != dia:
            continue
        total += (float(_campo(deal, "profit"))
                  + float(_campo(deal, "commission"))
                  + float(_campo(deal, "swap"))
                  + float(_campo(deal, "fee")))
        n += 1
    return round(total, 2), n
