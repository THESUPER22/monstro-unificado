# -*- coding: utf-8 -*-
"""Testes de tools/verificar_sensivel.py e do bloqueio no commit do fecho.

Arquivos falsos em repositorios descartaveis; nenhum processo real e tocado.
Os casos de falso positivo foram medidos no ROADMAP em 19/11: ``magic=123456``,
``ticket=2243200971`` e ``magic=123457`` NAO podem bloquear o fecho.
"""
import contextlib
import json
import os
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from commit_dia import (STATUS_COMMITADO, STATUS_SENSIVEL,  # noqa: E402
                        executar_commit)
from tools.verificar_sensivel import (analisar_arquivo,  # noqa: E402
                                      analisar_texto, formatar, varrer)

CONTA = "12345678"
SEGREDO = "sk-live-abc12345"


def _tipos(texto):
    return [(a["linha"], a["tipo"]) for a in analisar_texto(texto, "x.txt")]


# ------------------------------------------------------------- conta --------
def test_conta_estrita_detecta_os_formatos_reais():
    for linha in (
        "- Conta: **12345678 / XPMT5-DEMO** (demo)",
        "**Conta:** demo 12345678 / XPMT5-DEMO",
        "conta=12345678 XPMT5-DEMO",
        "foram feitas na conta 12345678 (XPMT5-DEMO)",
        "12345678 (conta demo)",
    ):
        assert _tipos(linha) == [(1, "conta")], linha


def test_conta_nao_marca_magic_ticket_medidos_no_roadmap():
    for linha in (
        "conta: `positions_get(magic=7008)`, `magic=123456`",
        "conta demo: `ticket=2243200971, magic=123457, symbol=WINV25`",
        "Conta terminou flat (so a fantasma WINV25 magic 123457)",
        "conta Netting sem numero",
    ):
        assert _tipos(linha) == [], linha


def test_conta_uma_vez_por_linha():
    assert _tipos("conta 12345678 e conta 123456789") == [(1, "conta")]


# ------------------------------------------------------------- saldo --------
def test_saldo_com_rs_detecta():
    assert _tipos("- Conta: demo, saldo R$ 838.534,21).") == [(1, "saldo")]


def test_custo_sem_palavra_saldo_nao_marca():
    for linha in ("custo R$ 0,60 entrar + R$ 0,60 sair",
                  "gate total R$ 21,20/trade",
                  "1 ponto = R$ 10,00"):
        assert _tipos(linha) == [], linha


# ----------------------------------------------------------- segredo --------
def test_segredo_com_valor_detecta():
    for linha in ('token = "abc12345"', "api_key: sk-live-999",
                  "senha=MinhaSenha1", '"password": "changeme2"'):
        assert _tipos(linha) == [(1, "segredo")], linha


def test_segredo_sem_valor_ou_placeholder_nao_marca():
    for linha in ('token = ""', 'password = os.environ["X"]',
                  "api_key: null", 'senha = "****"', "token: ${TOKEN}",
                  "password: exemplo"):
        assert _tipos(linha) == [], linha


# ------------------------------------------------------------ formato -------
def test_linha_e_tipo_corretos():
    texto = "ok\nnada\nConta: 12345678\nfim\n"
    assert analisar_texto(texto, "r.txt") == [
        {"arquivo": "r.txt", "linha": 3, "tipo": "conta"}]


def test_formatar_nao_expoe_o_valor():
    achados = analisar_texto('Conta: 12345678\napi_key: %s\n' % SEGREDO,
                             "r.txt")
    assert len(achados) == 2
    texto = " ".join(formatar(achados)) + repr(achados)
    assert CONTA not in texto and SEGREDO not in texto
    assert "r.txt:1 (conta)" in texto
    assert "r.txt:2 (segredo)" in texto


def test_binario_ignorado(tmp_path):
    p = tmp_path / "bin.dat"
    p.write_bytes(b"\x00\x01conta 12345678\n")
    assert analisar_arquivo(str(p), "bin.dat") == []


# -------------------------------------------------------------- staged ------
def _git(base, *args):
    return subprocess.run(["git", "-C", str(base)] + list(args),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


@contextlib.contextmanager
def repo_temporario(arquivos=None, gitignore="plano_*.txt\n"):
    chaves = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
              "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")
    antigo = {k: os.environ.get(k) for k in chaves}
    os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    try:
        with tempfile.TemporaryDirectory() as d:
            _git(d, "-c", "init.defaultBranch=main", "init", "-q")
            if gitignore is not None:
                _tocar(os.path.join(d, ".gitignore"), gitignore)
            for rel, conteudo in (arquivos or {}).items():
                _tocar(os.path.join(d, rel.replace("/", os.sep)), conteudo)
            yield d
    finally:
        for k, v in antigo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _tocar(caminho, conteudo):
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return caminho


def test_staged_detectado_e_desligavel():
    with repo_temporario({"plano_x.txt": "Conta: 12345678\n"}) as d:
        _git(d, "add", "-f", "--", "plano_x.txt")
        assert varrer(d, [], incluir_staged=True) == [
            {"arquivo": "plano_x.txt", "linha": 1, "tipo": "conta"}]
        assert varrer(d, [], incluir_staged=False) == []


def test_staged_le_o_blob_do_indice_nao_o_disco():
    with repo_temporario({"plano_x.txt": "api_key: %s\n" % SEGREDO}) as d:
        _git(d, "add", "-f", "--", "plano_x.txt")
        _tocar(os.path.join(d, "plano_x.txt"), "limpo\n")  # corrigido sem add
        achados = varrer(d, [], incluir_staged=True)
        assert [(a["linha"], a["tipo"]) for a in achados] == [(1, "segredo")]


# --------------------------------------------------- bloqueio do commit -----
def test_executar_commit_bloqueia_sensivel():
    with repo_temporario({"plano_20261119.txt": "Conta: 12345678\n"}) as d:
        r = executar_commit(d, ["plano_*.txt"], "teste")
        assert r["status"] == STATUS_SENSIVEL, r
        assert r["achados"] == [{"arquivo": "plano_20261119.txt",
                                 "linha": 1, "tipo": "conta"}]
        assert CONTA not in r["detalhe"]
        # nada foi para o indice nem para o historico
        assert _git(d, "ls-files").stdout.strip() == ""
        assert _git(d, "rev-list", "--count", "HEAD").returncode != 0


def test_executar_commit_limpo_commita():
    with repo_temporario({"plano_20261119.txt": "custo R$ 0,60\n"}) as d:
        r = executar_commit(d, ["plano_*.txt"], "teste")
        assert r["status"] == STATUS_COMMITADO, r
        assert _git(d, "ls-tree", "-r", "--name-only",
                    "HEAD").stdout.split() == ["plano_20261119.txt"]


def test_flag_desliga_a_varredura():
    with repo_temporario({"plano_20261119.txt": "Conta: 12345678\n"}) as d:
        r = executar_commit(d, ["plano_*.txt"], "teste",
                            verificar_sensivel=False)
        assert r["status"] == STATUS_COMMITADO, r


def test_staged_fora_da_whitelist_tambem_bloqueia():
    with repo_temporario({"codigo.py": 'token = "%s"\n' % SEGREDO,
                          "plano_20261119.txt": "limpo\n"}) as d:
        _git(d, "add", "-f", "--", "codigo.py")
        r = executar_commit(d, ["plano_*.txt"], "teste")
        assert r["status"] == STATUS_SENSIVEL, r
        assert r["achados"][0]["arquivo"] == "codigo.py"
        assert _git(d, "rev-list", "--count", "HEAD").returncode != 0


def test_dry_run_tambem_denuncia():
    with repo_temporario({"plano_20261119.txt": "Conta: 12345678\n"}) as d:
        r = executar_commit(d, ["plano_*.txt"], "teste", dry_run=True)
        assert r["status"] == STATUS_SENSIVEL, r


# --------------------------------------------------------------- config -----
def test_config_liga_a_varredura():
    with open(os.path.join(BASE, "agente_config.json"),
              encoding="utf-8-sig") as f:
        assert json.load(f)["git"]["verificar_sensivel"] is True
