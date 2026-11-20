# -*- coding: utf-8 -*-
"""Identidade do robo no fecho (23.61 item 3).

Nenhum processo real e morto: psutil.Process, pids_robo e relogio sao
substituidos. O arquivo de PID e gravado em tmp_path.
"""
import logging
import os
import sys
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402

CT = 1000.125
LINHA_CMD = "python monstro_unificado_v22.py " + ("x" * 200)


class ProcessoFalso:
    def __init__(self, pid, registro):
        self.pid = pid
        self.registro = registro

    def create_time(self):
        if self.pid == self.registro.get("ausente"):
            raise ag.psutil.NoSuchProcess(self.pid)
        return CT if self.pid == 111 else 2000.0

    def cmdline(self):
        return [LINHA_CMD]

    def children(self, recursive=True):
        return []

    def kill(self):
        self.registro.setdefault("killed", []).append(self.pid)


def _instalar_processo_falso(monkeypatch, registro):
    monkeypatch.setattr(ag.psutil, "Process",
                        lambda pid: ProcessoFalso(pid, registro))


def _tempo(monkeypatch, valores):
    sequencia = iter(valores)
    monkeypatch.setattr(ag, "time", SimpleNamespace(
        time=lambda: next(sequencia, 999.0), sleep=lambda _s: None))


def test_arquivo_de_pid_e_gravado_pelo_robo_no_start():
    fonte = os.path.join(BASE, "monstro_unificado_v22.py")
    with open(fonte, encoding="latin-1") as f:
        src = f.read()
    assert '"logs", "robo_pid.txt"' in src
    assert "os.getpid()" in src
    assert "create_time" in src


def test_ler_pid_robo_le_pid_e_create_time(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "robo_pid.txt").write_text(
        f"pid=111\ncreate_time={CT}\n", encoding="utf-8")
    assert ag.ler_pid_robo(str(tmp_path)) == (111, CT)


def test_ler_pid_robo_invalido_e_desconhecido(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "robo_pid.txt").write_text("lixo", encoding="utf-8")
    assert ag.ler_pid_robo(str(tmp_path)) is None


def test_parar_gracioso_espera_o_pid_do_arquivo(monkeypatch, tmp_path, caplog):
    registro = {}
    _instalar_processo_falso(monkeypatch, registro)
    sequencia = iter([[111, 222], [111, 222], []])
    monkeypatch.setattr(ag, "pids_robo", lambda: next(sequencia, []))
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "robo_pid.txt").write_text(
        f"pid=111\ncreate_time={CT}\n", encoding="utf-8")
    monkeypatch.setattr(ag, "PID_ROBO",
                        str(tmp_path / "logs" / "robo_pid.txt"))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    monkeypatch.setitem(ag.R, "handshake_parado_ok", False)
    _tempo(monkeypatch, [0.0, 0.0, 0.0, 0.0, 1.0])

    with caplog.at_level(logging.INFO):
        assert ag.parar_gracioso(0.5) is True
    assert "aguardando PID=111" in caplog.text
    assert "encerrou graciosamente" in caplog.text


def test_parar_gracioso_nao_sai_com_o_pid_alvo_vivo(monkeypatch, tmp_path,
                                                    caplog):
    registro = {}
    _instalar_processo_falso(monkeypatch, registro)
    monkeypatch.setattr(ag, "pids_robo", lambda: [111])
    monkeypatch.setattr(ag, "PID_ROBO", str(tmp_path / "sem_arquivo"))
    monkeypatch.setattr(ag, "ler_pid_robo", lambda: (111, CT))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    _tempo(monkeypatch, [0.0, 0.0, 0.1, 1.0])

    with caplog.at_level(logging.WARNING):
        assert ag.parar_gracioso(0.5) is False
    assert "PID=111" in caplog.text
    assert "create_time=" in caplog.text
    assert "cmdline=" in caplog.text


def test_timeout_loga_pid_create_time_e_cmdline_de_120_chars(monkeypatch,
                                                             tmp_path, caplog):
    registro = {}
    _instalar_processo_falso(monkeypatch, registro)
    monkeypatch.setattr(ag, "pids_robo", lambda: [111])
    monkeypatch.setattr(ag, "PID_ROBO", str(tmp_path / "sem_arquivo"))
    monkeypatch.setattr(ag, "ler_pid_robo", lambda: (111, CT))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    _tempo(monkeypatch, [0.0, 0.0, 0.1, 1.0])

    with caplog.at_level(logging.WARNING):
        ag.parar_gracioso(0.5)
    assert "PID=111" in caplog.text
    assert "create_time=1000.125" in caplog.text
    assert "cmdline=" in caplog.text
    assert LINHA_CMD[:120] in caplog.text
    assert "x" * 121 not in caplog.text


def test_parar_forcado_loga_diagnostico_antes_do_kill(monkeypatch, tmp_path,
                                                      caplog):
    registro = {}
    _instalar_processo_falso(monkeypatch, registro)
    pids = iter([[111], [], []])
    monkeypatch.setattr(ag, "pids_robo", lambda: next(pids, []))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    (tmp_path / "parar.txt").write_text("PARAR", encoding="utf-8")
    _tempo(monkeypatch, [0.0, 1.0])

    with caplog.at_level(logging.WARNING):
        assert ag.parar_forcado() is True
    assert registro["killed"] == [111]
    assert "parar_forcado: PID=111 create_time=1000.125 cmdline=" in caplog.text
    assert "force kill PID 111" in caplog.text
    assert "x" * 121 not in caplog.text


def test_sem_arquivo_de_pid_usa_fallback_com_aviso(monkeypatch, tmp_path,
                                                   caplog):
    monkeypatch.setattr(ag, "pids_robo", lambda: [])
    monkeypatch.setattr(ag, "PID_ROBO", str(tmp_path / "sem_arquivo"))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setitem(ag.R, "handshake_parado_ok", False)
    _tempo(monkeypatch, [0.0, 0.0, 1.0])
    with caplog.at_level(logging.WARNING):
        assert ag.parar_gracioso(0.5) is True
    assert "fallback" in caplog.text


# ------------------------- 23.62 item 2: so o alvo bloqueia o fecho ----------
def test_pendentes_ignora_fora_e_pid_reaproveitado(monkeypatch):
    monkeypatch.setattr(ag, "_estado_create_time", lambda pid: ("ausente", None))
    # alvo 111 morto + processo de fora 222: nao ha pendentes.
    assert ag._pendentes_parada((111, CT), [111, 222]) == []
    # PID 111 reaproveitado (create_time diferente) tambem nao e o alvo.
    monkeypatch.setattr(ag, "_estado_create_time", lambda pid: ("ok", 2000.0))
    assert ag._pendentes_parada((111, CT), [111]) == []
    # Sem arquivo de PID, mantem o fallback antigo.
    assert ag._pendentes_parada(None, [222]) == [222]


def test_alvo_morto_com_processo_de_fora_nao_bloqueia(monkeypatch, tmp_path,
                                                      caplog):
    registro = {}
    _instalar_processo_falso(monkeypatch, registro)
    monkeypatch.setattr(ag, "pids_robo", lambda: [222])
    monkeypatch.setattr(ag, "PID_ROBO", str(tmp_path / "sem_arquivo"))
    monkeypatch.setattr(ag, "ler_pid_robo", lambda: (111, CT))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setattr(ag, "PARADO_OK", str(tmp_path / "parado.ok"))
    monkeypatch.setitem(ag.R, "handshake_parado_ok", False)
    _tempo(monkeypatch, [0.0, 0.0, 1.0])

    with caplog.at_level(logging.INFO):
        assert ag.parar_gracioso(0.5) is True
    assert "processo de fora ignorado" in caplog.text
    assert "PID=222" in caplog.text
    assert "encerrou graciosamente" in caplog.text
