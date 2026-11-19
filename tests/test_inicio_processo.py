# -*- coding: utf-8 -*-
"""Inicio do processo do robo (qualquer forma de subir).

Antes, so `start_all.bat` e `start_robot()` do agente apagavam o `parado.ok`
e gravavam `logs/robo_inicio.txt`. Um start manual direto deixava o
handshake velho e o watchdog nao reiniciava apos uma queda real.
"""
import os
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fonte():
    # o robo esta em latin-1 (mojibake historico); leitura preserva os bytes
    with open(os.path.join(BASE, "monstro_unificado_v22.py"),
              encoding="latin-1") as f:
        return f.read()


FONTE = _fonte()


def _corpo():
    return FONTE[FONTE.index("def _registrar_inicio_processo"):
                 FONTE.index("CONFIG_FILE = _caminho_dados")]


def _carregar(base):
    """Executa o corpo REAL da funcao, sem importar o robo (MT5/webview)."""
    ns = {
        "os": os,
        "datetime": datetime,
        "_caminho_base": lambda: str(base),
    }
    exec(_corpo(), ns)
    return ns["_registrar_inicio_processo"]


def test_chamada_no_main_depois_do_mutex_e_antes_do_logging():
    main = FONTE[FONTE.index('if __name__ == "__main__":'):]
    i = main.index("_registrar_inicio_processo()")
    # depois do mutex: uma 2a instancia nao pode apagar o handshake do robo vivo
    assert main.index("_sys.exit(0)") < i
    # antes do logging: o start fica registrado mesmo se o logging falhar
    assert i < main.index("setup_logging()")


def test_remove_parado_ok_antigo_e_grava_marcador(tmp_path):
    parado = tmp_path / "parado.ok"
    parado.write_text("ok", encoding="utf-8")
    antes = datetime.now()

    _carregar(tmp_path)()

    assert not parado.exists()
    marcador = tmp_path / "logs" / "robo_inicio.txt"
    assert marcador.exists()
    quando = datetime.fromisoformat(marcador.read_text(encoding="utf-8"))
    assert quando >= antes.replace(microsecond=0)


def test_sem_parado_ok_nao_falha_e_grava_marcador(tmp_path):
    _carregar(tmp_path)()
    assert (tmp_path / "logs" / "robo_inicio.txt").exists()


def test_falha_ao_remover_nao_impede_o_marcador(tmp_path):
    # parado.ok como DIRETORIO: os.remove falha e o robo ainda precisa subir
    (tmp_path / "parado.ok").mkdir()
    _carregar(tmp_path)()
    assert (tmp_path / "logs" / "robo_inicio.txt").exists()


def test_marcador_sobrescreve_o_anterior(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    marcador = logs / "robo_inicio.txt"
    marcador.write_text("2026-11-17T09:00:00", encoding="utf-8")
    os.utime(marcador, (1000, 1000))

    _carregar(tmp_path)()

    assert datetime.fromisoformat(
        marcador.read_text(encoding="utf-8")).year == datetime.now().year
