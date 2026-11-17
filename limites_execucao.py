# -*- coding: utf-8 -*-
"""Tetos de execucao (P0 17/11 #2): exposicao e frequencia de ordens.

Rede de seguranca, NAO estrategia. O comportamento normal e 1 posicao por vez
e Sniper com cooldown de 120 s; estes limites so devem disparar em loop
anomalo (bug que reenvia ordem, dois caminhos abrindo ao mesmo tempo, ordem
duplicada apos timeout). Ao estourar, ``executar_ordem`` bloqueia a ordem e
dispara o kill-switch (``parar.txt``) do proprio robo.

Modulo puro (sem MT5/TensorFlow), testavel em
``tests/test_limites_execucao.py``.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

LIMITES_PADRAO = {
    "max_posicoes": 2,
    "max_ordens_por_janela": 3,
    "janela_ordens_s": 60,
}


def podar_janela(timestamps: Iterable[float], agora: float, janela_s: float) -> List[float]:
    """Mantem so os envios com idade < ``janela_s`` (ordem preservada).

    Borda: um envio com exatamente ``janela_s`` de idade ja sai da janela
    (comparacao estrita), para que a janela volte a liberar no tempo certo.
    """
    if janela_s <= 0:
        raise ValueError(f"janela_s deve ser > 0 (recebido {janela_s!r})")
    return [t for t in timestamps if agora - t < janela_s]


def avaliar_limite(posicoes_abertas: int,
                   timestamps: Iterable[float],
                   agora: float,
                   janela_s: float,
                   max_posicoes: int,
                   max_ordens: int) -> Tuple[bool, str]:
    """Decide se a proxima ordem deve ser bloqueada.

    Retorna ``(bloqueado, motivo)``. Puro: nao toca MT5 nem relogio.
    A checagem de exposicao vem primeiro (estado, nao fluxo).
    """
    if max_posicoes <= 0:
        raise ValueError(f"max_posicoes deve ser > 0 (recebido {max_posicoes!r})")
    if max_ordens <= 0:
        raise ValueError(f"max_ordens deve ser > 0 (recebido {max_ordens!r})")

    if posicoes_abertas >= max_posicoes:
        return True, (f"exposicao: {posicoes_abertas} posicoes abertas "
                      f"(max {max_posicoes})")

    na_janela = podar_janela(timestamps, agora, janela_s)
    if len(na_janela) >= max_ordens:
        return True, (f"frequencia: {len(na_janela)} ordens em {janela_s:g}s "
                      f"(max {max_ordens})")

    return False, ""
