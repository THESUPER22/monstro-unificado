# -*- coding: utf-8 -*-
"""Testes do guard do start_all.bat (robo vivo x zumbi).

`main` recebe `listar` e `matar_fn` injetados: a regra de decisao nao toca
processo real. O teste de deteccao real cria UM processo inofensivo com
"monstro_unificado_v22" no cmdline e o encerra no `finally`.
"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import start_guard as sg  # noqa: E402


def test_classificar_zumbi_e_vivo():
    z, v = sg.classificar([
        {"pid": 1, "inicio": 900.0},    # comecou ANTES do parado.ok
        {"pid": 2, "inicio": 1100.0},   # comecou DEPOIS do parado.ok
    ], 1000.0)
    assert [p["pid"] for p in z] == [1]
    assert [p["pid"] for p in v] == [2]


def test_sem_parado_ok_tudo_e_vivo():
    z, v = sg.classificar([{"pid": 1, "inicio": 900.0}], None)
    assert z == [] and [p["pid"] for p in v] == [1]


def test_parado_ok_mais_antigo_que_o_processo_nao_e_zumbi():
    """Robo reiniciado depois do parado.ok de ontem continua vivo."""
    z, v = sg.classificar([{"pid": 1, "inicio": 1100.0}], 1000.0)
    assert z == [] and len(v) == 1


def test_main_sem_processo_libera(tmp_path):
    rc = sg.main(["--base", str(tmp_path)], listar=lambda: [],
                 matar_fn=lambda pid: True)
    assert rc == sg.RC_OK
    log = (tmp_path / "logs" / "start_all.log").read_text(encoding="utf-8")
    assert "subida liberada" in log
    # marcador lido pelo watchdog: mtime = hora do start
    assert (tmp_path / "logs" / "robo_inicio.txt").exists()


def test_main_vivo_aborta_e_registra_sem_matar(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    os.utime(tmp_path / "parado.ok", (900, 900))
    chamadas = []
    rc = sg.main(["--base", str(tmp_path)],
                 listar=lambda: [{"pid": 42, "inicio": 1000.0}],
                 matar_fn=lambda pid: chamadas.append(pid) or True)
    assert rc == sg.RC_VIVO == 10
    assert chamadas == []
    log = (tmp_path / "logs" / "start_all.log").read_text(encoding="utf-8")
    assert "pid=42" in log and "ABORTADO" in log
    assert "parado.ok=" in log and "inicio=" in log
    assert not (tmp_path / "logs" / "robo_inicio.txt").exists()


def test_main_zumbi_mata_e_libera(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    os.utime(tmp_path / "parado.ok", (1000, 1000))
    chamadas = []
    rc = sg.main(["--base", str(tmp_path)],
                 listar=lambda: [{"pid": 43, "inicio": 900.0}],
                 matar_fn=lambda pid: chamadas.append(pid) or True)
    assert rc == 0
    assert chamadas == [43]
    log = (tmp_path / "logs" / "start_all.log").read_text(encoding="utf-8")
    assert "ZUMBI" in log and "encerrado" in log


def test_dry_run_mostra_a_decisao_sem_matar(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    os.utime(tmp_path / "parado.ok", (1000, 1000))
    chamadas = []
    rc = sg.main(["--base", str(tmp_path), "--dry-run"],
                 listar=lambda: [{"pid": 44, "inicio": 900.0}],
                 matar_fn=lambda pid: chamadas.append(pid) or True)
    assert rc == sg.RC_OK and chamadas == []
    log = (tmp_path / "logs" / "start_all.log").read_text(encoding="utf-8")
    assert "DRY-RUN: mataria" in log
    # dry-run nao pode marcar inicio: nada foi iniciado
    assert not (tmp_path / "logs" / "robo_inicio.txt").exists()


def test_mistura_zumbi_e_vivo_aborta_sem_matar_ninguem(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    os.utime(tmp_path / "parado.ok", (1000, 1000))
    chamadas = []
    rc = sg.main(["--base", str(tmp_path)],
                 listar=lambda: [{"pid": 1, "inicio": 900.0},
                                 {"pid": 2, "inicio": 1100.0}],
                 matar_fn=lambda pid: chamadas.append(pid) or True)
    assert rc == sg.RC_VIVO and chamadas == []


def test_erro_interno_aborta_com_codigo_11(tmp_path):
    def listar_quebrado():
        raise RuntimeError("psutil explodiu")

    rc = sg.main(["--base", str(tmp_path)], listar=listar_quebrado,
                 matar_fn=lambda pid: True)
    assert rc == sg.RC_ERRO == 11
    log = (tmp_path / "logs" / "start_all.log").read_text(encoding="utf-8")
    assert "ERRO INTERNO" in log and "RuntimeError" in log
    assert "ABORTADO" in log


def test_psutil_ausente_aborta_com_codigo_12(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "_psutil_ok", lambda: False)
    rc = sg.main(["--base", str(tmp_path)], listar=lambda: [],
                 matar_fn=lambda pid: True)
    assert rc == sg.RC_SEM_PSUTIL == 12
    log = (tmp_path / "logs" / "start_all.log").read_text(encoding="utf-8")
    assert "psutil ausente" in log


def test_detecta_processo_real_inofensivo_e_o_encerra():
    """Prova a deteccao no SO de verdade, sem tocar no robo.

    O processo e `python -c "time.sleep(60)" monstro_unificado_v22`: fica
    com o nome no cmdline, nao abre porta, nao le MT5. O `finally` mata.
    """
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)",
         "monstro_unificado_v22"])
    try:
        achado = None
        for _ in range(25):
            achados = [p for p in sg.listar_processos() if p["pid"] == proc.pid]
            if achados:
                achado = achados[0]
                break
            time.sleep(0.2)
        assert achado is not None, "processo com o nome no cmdline nao detectado"
        assert isinstance(achado["inicio"], float)
    finally:
        proc.kill()
        proc.wait(timeout=10)
    for _ in range(25):
        if not any(p["pid"] == proc.pid for p in sg.listar_processos()):
            break
        time.sleep(0.2)
    assert not any(p["pid"] == proc.pid for p in sg.listar_processos())


def test_start_all_bat_usa_o_guard():
    with open(os.path.join(BASE, "start_all.bat"), encoding="latin-1") as f:
        bat = f.read()
    assert "start_guard.py" in bat
    assert "Get-CimInstance Win32_Process" not in bat
    # mensagem por codigo + parado.ok apagado somente quando libera
    for codigo in ("10", "11", "12"):
        assert f'if "%RC%"=="{codigo}"' in bat
    assert 'set "RC=%errorlevel%"' in bat
    i_guard = bat.index("start_guard.py")
    i_del = bat.index("del /f /q parado.ok")
    assert i_guard < i_del
