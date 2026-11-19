# -*- coding: utf-8 -*-
"""start_all.bat: o aborto do guard precisa propagar o codigo de saida.

Antes era `exit /b 0`: o Agendador mostrava sucesso mesmo quando o start
foi cancelado (robo vivo, erro interno ou psutil ausente).
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _linhas():
    with open(os.path.join(BASE, "start_all.bat"), encoding="utf-8") as f:
        return f.read().splitlines()


def _bloco_aborto():
    linhas = _linhas()
    i = next(k for k, l in enumerate(linhas)
             if l.startswith('if not "%RC%"=="0" ('))
    j = next(k for k in range(i, len(linhas)) if linhas[k].strip() == ")")
    return linhas[i:j + 1]


def test_aborto_propaga_rc_do_guard():
    bloco = "\n".join(_bloco_aborto())
    assert "exit /b %RC%" in bloco
    assert "exit /b 0" not in bloco


def test_aborto_nao_apaga_parado_ok():
    bloco = "\n".join(_bloco_aborto())
    assert "del /f /q parado.ok" not in bloco


def test_rc_e_capturado_fora_do_bloco():
    linhas = _linhas()
    i = next(k for k, l in enumerate(linhas)
             if l.startswith('if not "%RC%"=="0" ('))
    assert any(l.strip() == 'set "RC=%errorlevel%"' for l in linhas[:i])
