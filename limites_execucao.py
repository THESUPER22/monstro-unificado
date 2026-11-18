# -*- coding: utf-8 -*-
"""Tetos de execucao (P0 17/11 #2): exposicao em contratos e frequencia.

Rede de seguranca, NAO estrategia. O comportamento normal e 1 contrato por
vez e Sniper com cooldown de 120 s; estes limites so devem disparar em loop
anomalo (bug que reenvia ordem, dois caminhos abrindo ao mesmo tempo, ordem
duplicada apos timeout). Ao estourar, ``executar_ordem`` bloqueia a ordem e
dispara o kill-switch (``parar.txt``) do proprio robo.

A conta e netting: ``positions_get`` devolve no maximo 1 posicao, por isso o
teto e medido em CONTRATOS (soma do volume aberto + volume da nova ordem) e
nao em numero de posicoes.

Modulo puro (sem MT5/TensorFlow), testavel em
``tests/test_limites_execucao.py``.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

LIMITES_PADRAO = {
    "max_contratos": 2,
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


def volume_aberto(posicoes) -> float:
    """Soma o volume das posicoes abertas.

    ``posicoes is None`` significa que a leitura do MT5 falhou: levanta
    ``ValueError`` para o chamador bloquear a ordem (fail-closed). Uma
    sequencia vazia (``()``) e exposicao zero, que e o caso normal.
    """
    if posicoes is None:
        raise ValueError("posicoes=None: leitura da exposicao indisponivel")

    total = 0.0
    for p in posicoes:
        vol = getattr(p, "volume", None)
        if vol is None and isinstance(p, dict):
            vol = p.get("volume")
        if vol is None:
            raise ValueError(f"posicao sem volume: {p!r}")
        total += float(vol)
    return total


def avaliar_limite(volume_aberto_atual: float,
                   volume_novo: float,
                   timestamps: Iterable[float],
                   agora: float,
                   janela_s: float,
                   max_contratos: float,
                   max_ordens: int) -> Tuple[bool, str]:
    """Decide se a proxima ordem deve ser bloqueada.

    Retorna ``(bloqueado, motivo)``. Puro: nao toca MT5 nem relogio.
    A checagem de exposicao vem primeiro (estado, nao fluxo). O teto e
    estourado somente quando a soma ULTRAPASSA ``max_contratos`` (igual passa:
    1 aberto + 1 novo com max 2 e permitido).
    """
    if max_contratos <= 0:
        raise ValueError(f"max_contratos deve ser > 0 (recebido {max_contratos!r})")
    if max_ordens <= 0:
        raise ValueError(f"max_ordens deve ser > 0 (recebido {max_ordens!r})")
    if volume_aberto_atual < 0:
        raise ValueError(
            f"volume_aberto_atual deve ser >= 0 (recebido {volume_aberto_atual!r})")
    if volume_novo < 0:
        raise ValueError(f"volume_novo deve ser >= 0 (recebido {volume_novo!r})")

    total = volume_aberto_atual + volume_novo
    if total > max_contratos:
        return True, (f"exposicao: {volume_aberto_atual:g} aberto + "
                      f"{volume_novo:g} novo = {total:g} contratos "
                      f"(max {max_contratos:g})")

    na_janela = podar_janela(timestamps, agora, janela_s)
    if len(na_janela) >= max_ordens:
        return True, (f"frequencia: {len(na_janela)} ordens em {janela_s:g}s "
                      f"(max {max_ordens})")

    return False, ""
