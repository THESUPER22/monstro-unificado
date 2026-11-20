# -*- coding: utf-8 -*-
"""Guarda do fecho do agente (23.60.11 item 2).

Sem parado.ok do dia E sem flat confirmado no MT5, o agente NAO pode
force-killar o robo nem fechar o terminal. Nenhum processo real e tocado:
MT5, pids_robo, parar_gracioso e parar_forcado sao injetados.
"""
import inspect
import os
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402


class LogFalso:
    def __init__(self):
        self.criticos = []

    def critical(self, msg, *args):
        self.criticos.append(msg % args if args else msg)

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def _mt5_falso(monkeypatch, leitura):
    """Modulo MetaTrader5 falso: positions_get() devolve `leitura`."""
    modulo = types.ModuleType("MetaTrader5")
    modulo.initialize = lambda: True
    modulo.shutdown = lambda: None
    modulo.positions_get = lambda: leitura
    monkeypatch.setitem(sys.modules, "MetaTrader5", modulo)
    monkeypatch.setattr(ag, "carregar_config_robo",
                        lambda: {"geral": {"magic_number": 123456},
                                 "rompimento": {"magic": 7008}})


def test_parado_ok_de_outra_data_nao_vale(monkeypatch, tmp_path):
    alvo = tmp_path / "parado.ok"
    alvo.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(ag, "PARADO_OK", str(alvo))
    antigo = (datetime.now() - timedelta(days=1)).timestamp()
    os.utime(alvo, (antigo, antigo))
    assert ag._parado_ok_do_dia() is False
    agora = datetime.now().timestamp()
    os.utime(alvo, (agora, agora))
    assert ag._parado_ok_do_dia() is True


def test_parado_ok_ausente_nao_vale(monkeypatch, tmp_path):
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    assert ag._parado_ok_do_dia() is False


def test_parado_ok_do_dia_basta_sem_ler_mt5(monkeypatch):
    monkeypatch.setattr(ag, "_parado_ok_do_dia", lambda: True)

    def explode():
        raise AssertionError("nao deveria ler MT5 com parado.ok do dia")

    monkeypatch.setitem(sys.modules, "MetaTrader5", explode)
    assert ag.flat_confirmado_para_fecho() is True


def test_flat_confirmado_com_positions_get_vazio(monkeypatch):
    monkeypatch.setattr(ag, "_parado_ok_do_dia", lambda: False)
    _mt5_falso(monkeypatch, ())
    assert ag.flat_confirmado_para_fecho() is True


def test_positions_none_nao_passa_por_zero(monkeypatch):
    monkeypatch.setattr(ag, "_parado_ok_do_dia", lambda: False)
    _mt5_falso(monkeypatch, None)          # leitura falhou
    log = LogFalso()
    monkeypatch.setattr(ag, "log", log)
    assert ag.flat_confirmado_para_fecho() is False
    assert any("NAO confirmado" in m for m in log.criticos)


def test_posicao_aberta_nao_e_flat(monkeypatch):
    monkeypatch.setattr(ag, "_parado_ok_do_dia", lambda: False)
    pos = SimpleNamespace(ticket=1, magic=123456)
    _mt5_falso(monkeypatch, (pos,))
    assert ag.flat_confirmado_para_fecho() is False


def test_mt5_sem_initialize_nao_e_flat(monkeypatch):
    monkeypatch.setattr(ag, "_parado_ok_do_dia", lambda: False)
    modulo = types.ModuleType("MetaTrader5")
    modulo.initialize = lambda: False
    modulo.shutdown = lambda: None
    monkeypatch.setitem(sys.modules, "MetaTrader5", modulo)
    assert ag.flat_confirmado_para_fecho() is False


def _preparar_parar_robo(monkeypatch, gracioso, flat):
    chamadas = []
    monkeypatch.setattr(ag, "pids_robo", lambda: [123])
    monkeypatch.setattr(ag, "parar_gracioso", lambda timeout: gracioso)
    monkeypatch.setattr(ag, "flat_confirmado_para_fecho", lambda: flat)
    monkeypatch.setattr(ag, "parar_forcado",
                        lambda: chamadas.append("kill") or True)
    log = LogFalso()
    monkeypatch.setattr(ag, "log", log)
    return chamadas, log


def test_parar_robo_sem_flat_nao_mata(monkeypatch):
    chamadas, log = _preparar_parar_robo(monkeypatch, gracioso=False, flat=False)
    assert ag.parar_robo() is False
    assert chamadas == []
    assert any("force kill" in m and "BLOQUEADOS" in m for m in log.criticos)


def test_parar_robo_com_flat_mata(monkeypatch):
    chamadas, _ = _preparar_parar_robo(monkeypatch, gracioso=False, flat=True)
    assert ag.parar_robo() is True
    assert chamadas == ["kill"]


def test_parar_robo_gracioso_nao_mata(monkeypatch):
    chamadas, _ = _preparar_parar_robo(monkeypatch, gracioso=True, flat=False)
    assert ag.parar_robo() is True
    assert chamadas == []


def test_fecho_do_agente_nao_fecha_mt5():
    src = inspect.getsource(ag.run_fecho)
    assert "stop_mt5(" not in src
    assert '_etapa_fecho("parar robo"' in src


def test_run_fecho_marca_falha_quando_parar_robo_retorna_false(monkeypatch):
    """'todas as etapas concluidas sem erro' nao pode mentir (aceite 19/11)."""
    monkeypatch.setattr(ag, "sinalizar_parada_robo", lambda: None)
    monkeypatch.setattr(ag, "verificar_mudanca_codigo", lambda: None)
    monkeypatch.setattr(ag, "ultimo_commit_robo", lambda: None)
    monkeypatch.setattr(ag, "gerar_relatorio_diario", lambda *a: None)
    monkeypatch.setattr(ag, "resumo_fluxo_dia", lambda: None)
    # nao pode gerar plano/relatorio reais: sao artefatos do fecho de 19/11
    monkeypatch.setattr(ag, "gerar_plano_dia_seguinte", lambda: None)
    monkeypatch.setattr(ag, "git_commit_dia", lambda: None)
    monkeypatch.setattr(ag, "CFG", {})
    monkeypatch.setattr(ag, "parar_coletor_herman", lambda: None)
    monkeypatch.setattr(ag, "parar_robo", lambda: False)
    log = LogFalso()
    monkeypatch.setattr(ag, "log", log)
    ag.run_fecho()
    assert "parar robo (flat nao confirmado)" in ag._FALHAS_FECHO
    assert any("robo NAO foi parado" in m for m in log.criticos)
    ag._FALHAS_FECHO.clear()
