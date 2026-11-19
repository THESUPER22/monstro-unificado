# -*- coding: utf-8 -*-
"""Reproduz o crash do fecho de 18/11 e prova o isolamento das etapas.

O `git diff` do fonte tem bytes que nao existem em cp1252 (0x9D). Com
`text=True` sem encoding, a thread leitora do subprocess estourava
UnicodeDecodeError, `p.stdout` virava None e o fecho caia em
AttributeError. Nenhum processo real e tocado.
"""
import inspect
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402


def _repo_com_0x9d(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_bytes(b"linha\n\x9d\n")
    for cmd in (["init", "-q"],
                ["config", "user.email", "t@t"],
                ["config", "user.name", "t"],
                ["add", "a.py"],
                ["commit", "-qm", "base"]):
        subprocess.run(["git", "-C", str(repo), *cmd], check=True)
    (repo / "a.py").write_bytes(b"linha\n\x9d MUDOU\n")
    return repo


def test_git_diff_com_0x9d_nao_devolve_stdout_none(tmp_path):
    repo = _repo_com_0x9d(tmp_path)
    rc, diff = ag._git("diff", "HEAD", "--", "a.py", base=str(repo))
    assert rc == 0
    assert diff and "MUDOU" in diff
    # o byte 0x9D virou replacement, mas o diff chegou inteiro
    assert "\ufffd" in diff


def test_verificar_mudanca_codigo_com_0x9d_nao_derruba(monkeypatch, tmp_path):
    repo = _repo_com_0x9d(tmp_path)
    monkeypatch.setattr(ag, "BASE_DIR", str(repo))
    monkeypatch.setattr(ag, "P", {"robo_script": "a.py"})
    info = ag.verificar_mudanca_codigo()
    assert info is not None
    assert info["add"] >= 1
    assert os.path.exists(os.path.join(str(repo), info["nome"]))


def test_etapa_fecho_isola_falha_e_a_seguinte_roda():
    chamadas = []

    def falha():
        raise UnicodeDecodeError("charmap", b"\x9d", 0, 1, "x")

    def seguinte():
        chamadas.append("seguinte")
        return 7

    ag._FALHAS_FECHO.clear()
    assert ag._etapa_fecho("falha", falha) is ag._FALHOU
    assert ag._etapa_fecho("seguinte", seguinte) == 7
    assert chamadas == ["seguinte"]
    assert ag._FALHAS_FECHO == ["falha"]
    ag._FALHAS_FECHO.clear()


def test_run_fecho_resume_as_falhas_no_final():
    src = inspect.getsource(ag.run_fecho)
    assert "_FALHAS_FECHO.clear()" in src
    assert "etapa(s) com falha" in src
    # o resumo vem DEPOIS da ultima etapa (parar robo)
    assert (src.index("etapa(s) com falha")
            > src.index('_etapa_fecho("parar robo"'))


def test_run_fecho_isola_todas_as_etapas_no_fonte():
    src = inspect.getsource(ag.run_fecho)
    for etapa in ["sinalizar parada do robo",
                  "verificar mudanca de codigo",
                  "ultimo commit do robo",
                  "relatorio diario",
                  "resumo de fluxo",
                  "plano do dia seguinte",
                  "commit do dia",
                  "parar coletores herman",
                  "parar robo"]:
        assert f'_etapa_fecho("{etapa}"' in src, etapa


def test_nenhum_subprocess_text_sem_encoding_no_agente():
    """Regra permanente: todo `text=True` do agente declara o encoding."""
    import ast
    with open(os.path.join(BASE, "agente_monstro_core.py"),
              encoding="utf-8") as f:
        arvore = ast.parse(f.read())
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        if not (isinstance(no.func, ast.Attribute)
                and no.func.attr in ("run", "Popen")):
            continue
        kw = {k.arg: k.value for k in no.keywords if k.arg}
        if not (isinstance(kw.get("text"), ast.Constant)
                and kw["text"].value is True):
            continue
        assert "encoding" in kw, f"linha {no.lineno}: text=True sem encoding"
        assert "errors" in kw, f"linha {no.lineno}: text=True sem errors"
