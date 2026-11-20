# -*- coding: utf-8 -*-
"""Parada e pausa com PID inexistente.

O processo pode morrer entre `pids_robo()` e `psutil.Process(pid)`.
`NoSuchProcess` nao pode derrubar watchdog, fecho ou pausa.
"""
import logging
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402

PID_MORTO = 999999


def _pids_que_some(vezes_com_pid):
    chamadas = {"n": 0}

    def pids():
        chamadas["n"] += 1
        return [PID_MORTO] if chamadas["n"] <= vezes_com_pid else []

    return pids


def test_parar_forcado_pid_inexistente_nao_quebra(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(ag, "pids_robo", _pids_que_some(1))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    (tmp_path / "parar.txt").write_text("PARAR", encoding="utf-8")

    with caplog.at_level(logging.INFO):
        ok = ag.parar_forcado()

    assert ok is True
    assert not (tmp_path / "parar.txt").exists()
    assert f"falha kill {PID_MORTO}" in caplog.text
    assert "parada forcada: ok" in caplog.text


def test_parar_robo_pid_inexistente_cai_para_forcado(monkeypatch, tmp_path, caplog):
    # 3 leituras: parar_robo, diagnostico do timeout e parar_forcado.
    monkeypatch.setattr(ag, "pids_robo", _pids_que_some(3))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    monkeypatch.setitem(ag.R, "graceful_timeout_s", 0)
    monkeypatch.setitem(ag.R, "handshake_parado_ok", True)

    with caplog.at_level(logging.WARNING):
        ok = ag.parar_robo()

    assert ok is True
    assert f"falha kill {PID_MORTO}" in caplog.text
    assert not (tmp_path / "parar.txt").exists()


def test_run_pausa_pid_inexistente_nao_reinicia(monkeypatch, caplog):
    chamadas = []
    monkeypatch.setattr(ag, "dentro_da_janela_autonomia", lambda: True)
    monkeypatch.setattr(ag, "parse_decisions", lambda: {})
    monkeypatch.setattr(ag, "parse_vetos_log", lambda: ({}, {}))
    monkeypatch.setattr(ag, "decidir",
                        lambda stats, counts, last: (None, "sem ajuste"))
    monkeypatch.setattr(ag, "pids_robo", lambda: [PID_MORTO])
    monkeypatch.setattr(ag, "start_mt5", lambda: chamadas.append("mt5"))
    monkeypatch.setattr(ag, "start_robot", lambda: chamadas.append("robo"))
    monkeypatch.setattr(ag, "health_check", lambda t: (True, "OK"))

    with caplog.at_level(logging.INFO):
        ag.run_pausa()

    assert chamadas == []
    assert "robo segue rodando" in caplog.text
