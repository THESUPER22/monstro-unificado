# -*- coding: utf-8 -*-
"""Watchdog x encerramento gracioso (18/11/2026).

Cenario medido: o robo gravou `parado.ok` as 17:35:58 e saiu. O watchdog
rodava a cada 15 min (09:05-17:20, PT15M no agendador) e, sem processo,
reiniciava o robo - anulando o encerramento. Nenhum processo real e
tocado: `pids_robo`, `start_robot` e `start_mt5` sao injetados.
"""
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402

AGORA = datetime(2026, 11, 18, 17, 37, 0)


def _preparar(tmp_path, parado_em=None, inicio_em=None):
    (tmp_path / "logs").mkdir(exist_ok=True)
    if parado_em is not None:
        p = tmp_path / "parado.ok"
        p.write_text("ok", encoding="utf-8")
        ts = parado_em.timestamp()
        os.utime(p, (ts, ts))
    if inicio_em is not None:
        m = tmp_path / "logs" / "robo_inicio.txt"
        m.write_text("marcador", encoding="utf-8")
        ts = inicio_em.timestamp()
        os.utime(m, (ts, ts))
    return tmp_path


def _watchdog(monkeypatch, base, chamadas):
    monkeypatch.setattr(ag, "BASE_DIR", str(base))
    monkeypatch.setattr(ag, "_agora_local", lambda: AGORA)
    monkeypatch.setattr(ag, "dentro_do_expediente", lambda: True)
    monkeypatch.setattr(ag, "verificar_kill_switch", lambda: False)
    monkeypatch.setattr(ag, "kill_switch_ja_ativado", lambda: False)
    monkeypatch.setattr(ag, "pids_robo", lambda: [])
    monkeypatch.setattr(ag, "em_backoff", lambda: False)
    monkeypatch.setattr(ag, "start_mt5", lambda: chamadas.append("mt5"))
    monkeypatch.setattr(ag, "start_robot", lambda: chamadas.append("robo"))
    monkeypatch.setattr(ag, "health_check", lambda t: (True, "OK"))
    monkeypatch.setattr(ag, "_backoff_salvar", lambda ts: None)


def test_1737_com_parado_ok_nao_reinicia(monkeypatch, tmp_path):
    _preparar(tmp_path, parado_em=datetime(2026, 11, 18, 17, 35, 58))
    chamadas = []
    _watchdog(monkeypatch, tmp_path, chamadas)
    ag.run_watchdog()
    assert chamadas == []
    assert ag.robo_encerrou_graciosamente(
        str(tmp_path), agora=AGORA) is True


def test_robo_morto_sem_parado_ok_reinicia(monkeypatch, tmp_path):
    _preparar(tmp_path)
    chamadas = []
    _watchdog(monkeypatch, tmp_path, chamadas)
    ag.run_watchdog()
    assert chamadas == ["mt5", "robo"]


def test_parado_ok_de_outro_dia_nao_bloqueia(monkeypatch, tmp_path):
    _preparar(tmp_path, parado_em=datetime(2026, 11, 17, 17, 35, 0))
    assert ag.robo_encerrou_graciosamente(
        str(tmp_path), agora=AGORA) is False


def test_parado_ok_mais_antigo_que_o_start_nao_bloqueia(monkeypatch, tmp_path):
    _preparar(tmp_path, parado_em=datetime(2026, 11, 18, 17, 0, 0),
              inicio_em=datetime(2026, 11, 18, 17, 20, 0))
    # Este teste so testa a comparacao de mtimes: nao pode depender de um
    # processo real do robo vivo (create_time de hoje venceria o parado.ok).
    monkeypatch.setattr(ag, "pids_robo", lambda: [])
    assert ag.robo_encerrou_graciosamente(
        str(tmp_path), agora=AGORA) is False


def test_parado_ok_mais_novo_que_o_start_bloqueia(monkeypatch, tmp_path):
    _preparar(tmp_path, parado_em=datetime(2026, 11, 18, 17, 35, 58),
              inicio_em=datetime(2026, 11, 18, 9, 0, 0))
    # Sem esta injecao, pids_robo() le processos REAIS: se o robo estiver
    # vivo, create_time() de hoje > mtime de 18/11 e o teste falha so por
    # causa do estado da maquina (flake medido em 19/11).
    monkeypatch.setattr(ag, "pids_robo", lambda: [])
    assert ag.robo_encerrou_graciosamente(
        str(tmp_path), agora=AGORA) is True


def test_start_robot_apaga_parado_ok_e_grava_marcador(monkeypatch, tmp_path):
    _preparar(tmp_path, parado_em=datetime(2026, 11, 18, 17, 35, 58))
    monkeypatch.setattr(ag, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    monkeypatch.setattr(ag, "MARCADOR_INICIO",
                        str(tmp_path / "logs" / "robo_inicio.txt"))
    monkeypatch.setattr(ag, "P", {"python_venv": "python.exe",
                                  "robo_script": "x.py"})
    monkeypatch.setattr(ag, "_agora_local", lambda: AGORA)

    class PopenFalso:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(ag.subprocess, "Popen", PopenFalso)
    ag.start_robot()
    assert not os.path.exists(str(tmp_path / "parado.ok"))
    marcador = tmp_path / "logs" / "robo_inicio.txt"
    assert marcador.exists()
    assert marcador.read_text(encoding="utf-8").startswith("2026-11-18T17:37")
