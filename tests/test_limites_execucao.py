#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_limites_execucao.py  (P0 17/11 #2)

Testes do modulo limites_execucao.py (puro, sem MT5/TensorFlow).
Roda direto (python tests\\test_limites_execucao.py) ou via pytest.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from limites_execucao import avaliar_limite, podar_janela  # noqa: E402

AGORA = 1_000_000.0
JANELA = 60.0
MAX_POS = 2
MAX_ORDENS = 3


# ------------------------------------------------------------- podar_janela -
def test_podar_janela_remove_antigos():
    ts = [AGORA - 120, AGORA - 61, AGORA - 59, AGORA - 1]
    assert podar_janela(ts, AGORA, JANELA) == [AGORA - 59, AGORA - 1]


def test_podar_janela_borda_sai():
    # exatamente 60 s de idade ja nao conta (libera no tempo certo)
    assert podar_janela([AGORA - 60], AGORA, JANELA) == []
    assert podar_janela([AGORA - 59.999], AGORA, JANELA) == [AGORA - 59.999]


def test_podar_janela_preserva_ordem_e_nao_muta():
    ts = [3.0, 1.0, 2.0]
    original = list(ts)
    assert podar_janela(ts, 4.0, 10.0) == [3.0, 1.0, 2.0]
    assert ts == original


def test_podar_janela_invalida():
    for ruim in (0, -1):
        try:
            podar_janela([], AGORA, ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"janela {ruim!r} deveria levantar ValueError")


# ---------------------------------------------------------- avaliar_limite -
def test_dentro_dos_limites_libera():
    bloqueado, motivo = avaliar_limite(
        1, [AGORA - 30], AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is False
    assert motivo == ""


def test_exposicao_no_limite_bloqueia():
    bloqueado, motivo = avaliar_limite(
        MAX_POS, [], AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is True
    assert "exposicao" in motivo
    assert f"max {MAX_POS}" in motivo


def test_exposicao_acima_do_limite_bloqueia():
    bloqueado, motivo = avaliar_limite(
        5, [], AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is True
    assert "5 posicoes" in motivo


def test_frequencia_no_limite_bloqueia():
    ts = [AGORA - 50, AGORA - 30, AGORA - 10]
    bloqueado, motivo = avaliar_limite(
        0, ts, AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is True
    assert "frequencia" in motivo
    assert "3 ordens" in motivo


def test_frequencia_abaixo_do_limite_libera():
    ts = [AGORA - 50, AGORA - 30]
    bloqueado, _ = avaliar_limite(
        0, ts, AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is False


def test_ordens_antigas_nao_contam():
    # 3 ordens, mas todas fora da janela: nao bloqueia
    ts = [AGORA - 300, AGORA - 200, AGORA - 100]
    bloqueado, _ = avaliar_limite(
        0, ts, AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is False


def test_exposicao_tem_prioridade_sobre_frequencia():
    ts = [AGORA - 5, AGORA - 4, AGORA - 3]
    bloqueado, motivo = avaliar_limite(
        MAX_POS, ts, AGORA, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is True
    assert "exposicao" in motivo


def test_limites_invalidos():
    for kwargs in ({"max_posicoes": 0}, {"max_ordens": 0}):
        base = dict(posicoes_abertas=0, timestamps=[], agora=AGORA,
                    janela_s=JANELA, max_posicoes=MAX_POS, max_ordens=MAX_ORDENS)
        base.update(kwargs)
        try:
            avaliar_limite(**base)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{kwargs} deveria levantar ValueError")


def test_simulacao_rajada_de_ordens():
    """3 ordens liberadas; a 4a em <60 s bloqueia; 60 s depois libera."""
    ts = []
    liberadas = 0
    for i in range(5):
        agora = AGORA + i  # rajada de 1 s
        bloqueado, _ = avaliar_limite(0, ts, agora, JANELA, MAX_POS, MAX_ORDENS)
        if not bloqueado:
            ts.append(agora)
            liberadas += 1
    assert liberadas == MAX_ORDENS
    # depois da janela, volta a liberar
    bloqueado, _ = avaliar_limite(0, ts, AGORA + 61, JANELA, MAX_POS, MAX_ORDENS)
    assert bloqueado is False


# ------------------------------------------------------------- integracao ---
def test_robo_aplica_teto_em_executar_ordem():
    """Guard de regressao: o teto tem de ser checado dentro de executar_ordem."""
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        fonte = f.read()
    assert "from limites_execucao import avaliar_limite, podar_janela" in fonte
    assert "def executar_ordem(" in fonte
    inicio = fonte.index("def executar_ordem(")
    fim = fonte.index("\ndef ", inicio + 1)
    corpo = fonte[inicio:fim]
    assert "avaliar_limite(" in corpo
    assert "_caminho_dados(\"parar.txt\")" in corpo


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
