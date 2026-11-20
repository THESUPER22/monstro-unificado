# -*- coding: utf-8 -*-
"""C3: modelo/experiencias salvos uma unica vez por encerramento (23.62 item 4)."""
import logging
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from patches.robustez_fecho_helpers import SalvamentoUnico  # noqa: E402


def test_cada_chave_executa_uma_unica_vez(caplog):
    guarda = SalvamentoUnico(logging.getLogger())
    chamadas = []
    with caplog.at_level(logging.INFO):
        assert guarda.executar("modelo", lambda: chamadas.append("modelo")) is True
        assert guarda.executar("modelo", lambda: chamadas.append("modelo")) is False
        assert guarda.executar("experiencias",
                               lambda: chamadas.append("experiencias")) is True
        assert guarda.executar("experiencias",
                               lambda: chamadas.append("experiencias")) is False
    assert chamadas == ["modelo", "experiencias"]
    assert "salvo uma unica vez" in caplog.text
    assert "pulando" in caplog.text


def test_falha_nao_marca_como_feito():
    guarda = SalvamentoUnico(logging.getLogger())

    def quebra():
        raise RuntimeError("disco cheio")

    try:
        guarda.executar("modelo", quebra)
    except RuntimeError:
        pass
    # Erro propaga e a chave continua elegivel para nova tentativa.
    assert guarda.executar("modelo", lambda: None) is True


def test_robo_usa_a_guarda_no_bloco_c3():
    caminho = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(caminho, encoding="latin-1") as f:
        src = f.read()
    assert "SalvamentoUnico" in src
    assert '_SALVAMENTO_FINAL.executar(\n                                "modelo"' in src
    assert '"experiencias"' in src
