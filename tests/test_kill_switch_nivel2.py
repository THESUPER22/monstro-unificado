# -*- coding: utf-8 -*-
"""Nivel 2 do kill-switch: zerar -> parar_robo -> MT5 so com flat (23.62 item 3).

Todos os efeitos sao injetados: nenhum processo e morto e nenhuma posicao real
e fechada neste teste.
"""
import logging
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402


def _instalar(monkeypatch, chamadas, fechamento, parou=True, flat=True):
    monkeypatch.setattr(ag, "fechar_posicoes_kill_switch",
                        lambda: chamadas.append("fechar") or fechamento)
    monkeypatch.setattr(ag, "parar_robo",
                        lambda: chamadas.append("parar") or parou)
    monkeypatch.setattr(ag, "flat_confirmado_para_fecho",
                        lambda: chamadas.append("flat") or flat)
    monkeypatch.setattr(ag, "stop_mt5", lambda: chamadas.append("mt5"))


def test_flat_confirmado_encerra_na_ordem_e_fechamt5(monkeypatch, caplog):
    chamadas = []
    _instalar(monkeypatch, chamadas, (2, []))
    with caplog.at_level(logging.INFO):
        assert ag.nivel2_parar_com_flat() is True
    assert chamadas == ["fechar", "parar", "flat", "mt5"]
    assert "2 posicao(oes) zeradas" in caplog.text


def test_restantes_bloqueiam_e_deixam_terminal_vivo(monkeypatch, caplog):
    chamadas = []
    _instalar(monkeypatch, chamadas, (1, [555]))
    with caplog.at_level(logging.CRITICAL):
        assert ag.nivel2_parar_com_flat() is False
    assert chamadas == ["fechar"]
    assert "CRITICAL" in caplog.text
    assert "terminal vivo" in caplog.text


def test_estado_desconhecido_bloqueia_e_deixa_terminal_vivo(monkeypatch, caplog):
    chamadas = []
    _instalar(monkeypatch, chamadas, (0, None))
    with caplog.at_level(logging.CRITICAL):
        assert ag.nivel2_parar_com_flat() is False
    assert chamadas == ["fechar"]
    assert "flat DESCONHECIDO" in caplog.text


def test_leitura_de_posicoes_falhou_bloqueia(monkeypatch, caplog):
    chamadas = []
    _instalar(monkeypatch, chamadas, None)
    with caplog.at_level(logging.CRITICAL):
        assert ag.nivel2_parar_com_flat() is False
    assert chamadas == ["fechar"]
    assert "flat DESCONHECIDO" in caplog.text


def test_parar_robo_sem_flat_bloqueia_fechamento_do_mt5(monkeypatch, caplog):
    chamadas = []
    _instalar(monkeypatch, chamadas, (1, []), parou=False)
    with caplog.at_level(logging.CRITICAL):
        assert ag.nivel2_parar_com_flat() is False
    assert chamadas == ["fechar", "parar"]
    assert "parar_robo falhou" in caplog.text


def test_flat_nao_confirmado_apos_parar_bloqueia_mt5(monkeypatch, caplog):
    chamadas = []
    _instalar(monkeypatch, chamadas, (1, []), flat=False)
    with caplog.at_level(logging.CRITICAL):
        assert ag.nivel2_parar_com_flat() is False
    assert chamadas == ["fechar", "parar", "flat"]
    assert "flat NAO confirmado" in caplog.text


def test_sem_chamar_stop_mt5_quando_bloqueia(monkeypatch, tmp_path):
    """Rede de seguranca: stop_mt5 so e alcancado no caminho confirmado."""
    monkeypatch.setattr(ag, "fechar_posicoes_kill_switch", lambda: (0, [1]))
    monkeypatch.setattr(ag, "stop_mt5",
                        lambda: (_ for _ in ()).throw(AssertionError("mt5!")))
    assert ag.nivel2_parar_com_flat() is False
    assert not os.path.exists(os.path.join(str(tmp_path), "parar.txt"))
