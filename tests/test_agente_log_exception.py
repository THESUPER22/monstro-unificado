# -*- coding: utf-8 -*-
"""Traceback do agente por modo (fecho/watchdog/pausa).

18/11/2026: o fecho morreu com UnicodeDecodeError (0x9D) -> AttributeError e
o log parou em "agente iniciado no modo: fecho". O Agendador so mostra o
codigo de saida; sem `log.exception` a causa raiz se perde.
"""
import logging
import os

import pytest

import agente_monstro_core as ag  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fonte():
    with open(os.path.join(BASE, "agente_monstro_core.py"),
              encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


FONTE = _fonte()


@pytest.mark.parametrize("nome", ["fecho", "watchdog", "pausa"])
def test_excecao_no_modo_grava_traceback_completo(caplog, nome):
    def quebra():
        raise ValueError(f"boom-{nome}")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError):
            ag._executar_modo(nome, quebra)

    texto = caplog.text
    assert f"modo '{nome}': excecao nao tratada - abortando" in texto
    assert "Traceback (most recent call last)" in texto
    assert f"ValueError: boom-{nome}" in texto


def test_main_envolve_fecho_e_propaga(monkeypatch, caplog):
    def quebra():
        raise RuntimeError("falha no fecho")

    monkeypatch.setattr(ag, "run_fecho", quebra)
    monkeypatch.setattr(ag.sys, "argv", ["agente_monstro_core.py", "fecho"])

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            ag.main()

    assert "modo 'fecho': excecao nao tratada" in caplog.text
    assert "RuntimeError: falha no fecho" in caplog.text


def test_main_envolve_watchdog(monkeypatch):
    chamadas = []
    monkeypatch.setattr(ag, "run_watchdog", lambda: chamadas.append("w"))
    monkeypatch.setitem(ag.R, "watchdog_enabled", True)
    monkeypatch.setattr(ag.sys, "argv", ["agente_monstro_core.py", "watchdog"])

    ag.main()

    assert chamadas == ["w"]


def test_main_envolve_pausa(monkeypatch):
    chamadas = []
    monkeypatch.setattr(ag, "run_pausa", lambda: chamadas.append("p"))
    monkeypatch.setattr(ag.sys, "argv", ["agente_monstro_core.py", "pausa"])

    ag.main()

    assert chamadas == ["p"]


def test_dryrun_continua_fora_do_wrapper():
    main = FONTE[FONTE.index("def main():"):]
    assert 'elif modo == "dryrun":\n        dryrun()' in main
