# -*- coding: utf-8 -*-
"""Log do agente por variavel de ambiente (isolamento da suite).

O import do `agente_monstro_core` chama `logging.basicConfig(filename=...)`.
Sem `MONSTRO_AGENTE_LOG`, a suite escrevia no `agente_autonomo.log` real.
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_conftest_aponta_para_arquivo_temporario():
    import agente_monstro_core as ag

    assert ag.LOG_AGENTE == os.environ["MONSTRO_AGENTE_LOG"]
    assert "monstro_agente_teste_" in ag.LOG_AGENTE
    assert not ag.LOG_AGENTE.lower().endswith("agente_autonomo.log")


def test_env_var_controla_o_log_no_import(tmp_path):
    alvo = tmp_path / "agente_de_teste.log"
    env = dict(os.environ, MONSTRO_AGENTE_LOG=str(alvo),
               PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, "-c",
         "import agente_monstro_core as a; print(a.LOG_AGENTE)"],
        cwd=BASE, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-1] == str(alvo)


def test_fonte_le_a_variavel_de_ambiente():
    with open(os.path.join(BASE, "agente_monstro_core.py"),
              encoding="utf-8") as f:
        fonte = f.read()
    assert 'os.environ.get(' in fonte
    assert '"MONSTRO_AGENTE_LOG"' in fonte
