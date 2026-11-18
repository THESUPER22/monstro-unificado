#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_limites_execucao.py  (P0 17/11 #2, rev. 2.1)

Testes do modulo limites_execucao.py (puro, sem MT5/TensorFlow).
Roda direto (python tests\\test_limites_execucao.py) ou via pytest.

Rev. 2.1: o teto passou de numero de posicoes para CONTRATOS, porque a conta
e netting (positions_get devolve no maximo 1 posicao) e o volume pode ser
1,0/1,5/2,0.
"""
import os
import sys
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from limites_execucao import (avaliar_limite, podar_janela,  # noqa: E402
                              volume_aberto)

AGORA = 1_000_000.0
JANELA = 60.0
MAX_CONTRATOS = 2
MAX_ORDENS = 3


def _pos(volume):
    return SimpleNamespace(volume=volume)


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


# ------------------------------------------------------------ volume_aberto -
def test_volume_aberto_sem_posicao_e_zero():
    # positions_get devolve () (nao None) quando nao ha posicao
    assert volume_aberto(()) == 0.0
    assert volume_aberto([]) == 0.0


def test_volume_aberto_soma_contratos():
    assert volume_aberto([_pos(1.0)]) == 1.0
    assert volume_aberto([_pos(1.5)]) == 1.5
    # defensivo: soma varias (conta netting devolve 1, mas a funcao e pura)
    assert volume_aberto([_pos(1.0), _pos(2.0)]) == 3.0


def test_volume_aberto_aceita_dict():
    assert volume_aberto([{"volume": 1.5}]) == 1.5


def test_volume_aberto_none_falha_fechado():
    try:
        volume_aberto(None)
    except ValueError as e:
        assert "None" in str(e)
    else:
        raise AssertionError("None deveria levantar ValueError (fail-closed)")


def test_volume_aberto_posicao_sem_volume_falha_fechado():
    for ruim in (SimpleNamespace(), {"ticket": 1}, SimpleNamespace(volume=None)):
        try:
            volume_aberto([ruim])
        except ValueError:
            pass
        else:
            raise AssertionError(f"{ruim!r} deveria levantar ValueError")


# ---------------------------------------------------------- avaliar_limite -
def test_dentro_dos_limites_libera():
    bloqueado, motivo = avaliar_limite(
        1.0, 1.0, [AGORA - 30], AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is False
    assert motivo == ""


def test_volume_igual_ao_teto_libera():
    # 1 aberto + 1 novo = 2 com max 2: permitido (igual nao estoura)
    bloqueado, _ = avaliar_limite(
        1.0, 1.0, [], AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is False


def test_exposicao_acima_do_teto_bloqueia():
    bloqueado, motivo = avaliar_limite(
        1.0, 2.0, [], AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is True
    assert "exposicao" in motivo
    assert "3 contratos" in motivo
    assert "max 2" in motivo


def test_exposicao_ja_estourada_bloqueia():
    # posicao aberta acima do teto (config reduzida em runtime): bloqueia
    bloqueado, motivo = avaliar_limite(
        5.0, 1.0, [], AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is True
    assert "5 aberto" in motivo


def test_frequencia_no_limite_bloqueia():
    ts = [AGORA - 50, AGORA - 30, AGORA - 10]
    bloqueado, motivo = avaliar_limite(
        0.0, 1.0, ts, AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is True
    assert "frequencia" in motivo
    assert "3 ordens" in motivo


def test_frequencia_abaixo_do_limite_libera():
    ts = [AGORA - 50, AGORA - 30]
    bloqueado, _ = avaliar_limite(
        0.0, 1.0, ts, AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is False


def test_ordens_antigas_nao_contam():
    # 3 ordens, mas todas fora da janela: nao bloqueia
    ts = [AGORA - 300, AGORA - 200, AGORA - 100]
    bloqueado, _ = avaliar_limite(
        0.0, 1.0, ts, AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is False


def test_exposicao_tem_prioridade_sobre_frequencia():
    ts = [AGORA - 5, AGORA - 4, AGORA - 3]
    bloqueado, motivo = avaliar_limite(
        1.0, 2.0, ts, AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is True
    assert "exposicao" in motivo


def test_limites_invalidos():
    for kwargs in ({"max_contratos": 0}, {"max_ordens": 0},
                   {"volume_aberto_atual": -1}, {"volume_novo": -1}):
        base = dict(volume_aberto_atual=0.0, volume_novo=1.0, timestamps=[],
                    agora=AGORA, janela_s=JANELA, max_contratos=MAX_CONTRATOS,
                    max_ordens=MAX_ORDENS)
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
        bloqueado, _ = avaliar_limite(
            0.0, 1.0, ts, agora, JANELA, MAX_CONTRATOS, MAX_ORDENS)
        if not bloqueado:
            ts.append(agora)
            liberadas += 1
    assert liberadas == MAX_ORDENS
    # depois da janela, volta a liberar
    bloqueado, _ = avaliar_limite(
        0.0, 1.0, ts, AGORA + 61, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is False


def test_simulacao_piramide_bloqueia_no_terceiro_contrato():
    """1 aberto + 1 novo = 2 (ok); o proximo 1 contrato estoura o teto."""
    aberto = 1.0
    bloqueado, _ = avaliar_limite(
        aberto, 1.0, [], AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is False
    aberto += 1.0
    bloqueado, motivo = avaliar_limite(
        aberto, 1.0, [], AGORA, JANELA, MAX_CONTRATOS, MAX_ORDENS)
    assert bloqueado is True
    assert "exposicao" in motivo


# ------------------------------------------------------------- integracao ---
def _corpo_executar_ordem():
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        fonte = f.read()
    inicio = fonte.index("def executar_ordem(")
    fim = fonte.index("\ndef ", inicio + 1)
    return fonte, fonte[inicio:fim]


def test_robo_aplica_teto_em_executar_ordem():
    """Guard de regressao: o teto tem de ser checado dentro de executar_ordem."""
    fonte, corpo = _corpo_executar_ordem()
    assert "from limites_execucao import avaliar_limite, podar_janela, volume_aberto" in fonte
    assert "avaliar_limite(" in corpo
    assert "volume_aberto(_pos)" in corpo
    assert "_caminho_dados(\"parar.txt\")" in corpo


def test_teto_roda_depois_do_volume_e_antes_do_order_send():
    """Ordem estatica (rev. 2.1): volume final -> teto -> order_send."""
    _, corpo = _corpo_executar_ordem()
    i_volume = corpo.index("lote_corrigido = float(")
    i_teto = corpo.index("avaliar_limite(")
    i_envio = corpo.index("resultado = mt5.order_send(request)")
    assert i_volume < i_teto < i_envio, (
        f"ordem errada: volume@{i_volume}, teto@{i_teto}, envio@{i_envio}")
    # o timestamp so pode ser registrado no bloco do teto (apos passar)
    assert corpo.count("_ordens_recentes.append(_agora)") == 1


def test_teto_fail_closed_em_positions_get_none():
    """positions_get None: 1 retry e, persistindo, bloqueia a ordem."""
    _, corpo = _corpo_executar_ordem()
    bloco = corpo[corpo.index("if LIMITES_EXEC_ATIVO:"):
                  corpo.index("avaliar_limite(")]
    assert bloco.count("mt5.positions_get(symbol=symbol)") == 2
    assert "time.sleep(0.2)" in bloco
    assert "except Exception as _e:" in bloco
    assert "positions_get falhou" in bloco
    assert "fail-closed" in bloco
    assert "return None" in bloco


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
