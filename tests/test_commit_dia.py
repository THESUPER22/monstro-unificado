#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_commit_dia.py  (P1 17/11 #3)

Testes do modulo commit_dia.py: selecao por whitelist/dia e o commit restrito.
O ultimo bloco cria um repo git descartavel, reproduz o bug real de 17/11
(`git add` sem `-f` em arquivo coberto pelo .gitignore -> exit 1) e prova que o
fix commita sem publicar o historico.

Roda direto (python tests\\test_commit_dia.py) ou via pytest.
"""
import contextlib
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from commit_dia import (STATUS_ADD_FALHOU, STATUS_COMMIT_FALHOU,  # noqa: E402
                        STATUS_COMMITADO, STATUS_DRY_RUN, STATUS_NADA_NOVO,
                        STATUS_NADA_PRESENTE, STATUS_OK, caminhos_permitidos,
                        executar_commit, mensagem_fecho, selecionar_arquivos)

ONTEM = datetime.now() - timedelta(days=1)
VELHO = datetime.now() - timedelta(days=3)
RECENTE = datetime.now() - timedelta(hours=3)


def _tocar(caminho, conteudo="x", quando=None):
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    if quando is not None:
        ts = quando.timestamp()
        os.utime(caminho, (ts, ts))
    return caminho


def _git(base, *args):
    return subprocess.run(["git", "-C", str(base)] + list(args),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


@contextlib.contextmanager
def repo_temporario(arquivos=None, gitignore="relatorio_*.txt\nplano_*.txt\nlogs/\n"):
    """Repo git isolado; `arquivos` = {caminho_relativo: (conteudo, quando)}."""
    chaves = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
              "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")
    antigo = {k: os.environ.get(k) for k in chaves}
    os.environ.update({
        "GIT_AUTHOR_NAME": "teste", "GIT_AUTHOR_EMAIL": "teste@teste",
        "GIT_COMMITTER_NAME": "teste", "GIT_COMMITTER_EMAIL": "teste@teste",
    })
    try:
        with tempfile.TemporaryDirectory() as d:
            _git(d, "-c", "init.defaultBranch=main", "init", "-q")
            if gitignore is not None:
                _tocar(os.path.join(d, ".gitignore"), gitignore)
            for rel, valor in (arquivos or {}).items():
                conteudo, quando = valor if isinstance(valor, tuple) else (valor, None)
                _tocar(os.path.join(d, rel.replace("/", os.sep)), conteudo, quando)
            yield d
    finally:
        for k, v in antigo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _arquivos_no_head(base):
    return sorted(_git(base, "ls-tree", "-r", "--name-only", "HEAD").stdout.split())


# ------------------------------------------------------- selecionar_arquivos -
def test_seleciona_apenas_os_padroes():
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "relatorio_diario_20261117.txt"))
        _tocar(os.path.join(d, "plano_20261117.txt"))
        _tocar(os.path.join(d, "segredo.py"))
        _tocar(os.path.join(d, "relatorio_diario_20261117.txt.bak"))
        r = selecionar_arquivos(["relatorio_diario_*.txt", "plano_*.txt"], d)
        assert r == ["plano_20261117.txt", "relatorio_diario_20261117.txt"], r


def test_ignora_diretorio_que_casa_com_o_padrao():
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "logs", "fluxo_resumo_2026-11-17.json"), "{}")
        r = selecionar_arquivos(["logs", "logs/fluxo_resumo_*.json"], d)
        assert r == ["logs/fluxo_resumo_2026-11-17.json"], r


def test_janela_horas_filtra_pelo_mtime():
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "relatorio_diario_20260804.txt"), "velho", VELHO)
        _tocar(os.path.join(d, "relatorio_diario_20261117.txt"), "novo")
        r = selecionar_arquivos(["relatorio_diario_*.txt"], d)
        assert r == ["relatorio_diario_20261117.txt"], r


def test_janela_padrao_recupera_o_fecho_de_ontem():
    """26 h: o fecho de ontem 17:35 ainda entra no fecho de hoje 17:35."""
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "relatorio_diario_20261116.txt"), "ontem", ONTEM)
        r = selecionar_arquivos(["relatorio_diario_*.txt"], d)
        assert r == ["relatorio_diario_20261116.txt"], r


def test_janela_none_traz_o_historico():
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "relatorio_diario_20260804.txt"), "velho", VELHO)
        _tocar(os.path.join(d, "relatorio_diario_20261117.txt"), "novo", RECENTE)
        r = selecionar_arquivos(["relatorio_diario_*.txt"], d, janela_horas=None)
        assert r == ["relatorio_diario_20260804.txt",
                     "relatorio_diario_20261117.txt"], r


def test_padroes_sobrepostos_nao_duplicam():
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "relatorio_diario_20261117.txt"))
        r = selecionar_arquivos(["relatorio_*.txt", "relatorio_diario_*.txt",
                                 "relatorio_diario_20261117.txt"], d)
        assert r == ["relatorio_diario_20261117.txt"], r


def test_padrao_com_subpasta_usa_barra_normal():
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "logs", "fluxo_resumo_2026-11-17.json"), "{}")
        r = selecionar_arquivos(["logs/fluxo_resumo_*.json"], d)
        assert r == ["logs/fluxo_resumo_2026-11-17.json"], r
        assert os.sep not in r[0]


def test_padroes_vazios_ou_sem_arquivo():
    with tempfile.TemporaryDirectory() as d:
        assert selecionar_arquivos([], d) == []
        assert selecionar_arquivos(["nao_existe_*.txt"], d) == []


def test_agora_move_a_janela():
    """`agora` desloca a janela: com agora=VELHO, o arquivo de VELHO entra."""
    with tempfile.TemporaryDirectory() as d:
        _tocar(os.path.join(d, "relatorio_diario_20260804.txt"), "velho", VELHO)
        r = selecionar_arquivos(["relatorio_diario_*.txt"], d, agora=VELHO)
        assert r == ["relatorio_diario_20260804.txt"], r
        r2 = selecionar_arquivos(["relatorio_diario_*.txt"], d)
        assert r2 == [], r2


# ------------------------------------------------------------ mensagem_fecho -
def test_mensagem_fecho_usa_a_data():
    assert mensagem_fecho(datetime(2026, 11, 17, 17, 35)) == \
        "fecho autonomo 2026-11-17 (agente Fase 1)"


# ------------------------------------------------------- executar_commit ----
def test_bug_de_17_11_add_normal_falha_em_arquivo_ignorado():
    """Prova a causa raiz: `git add` sem -f retorna 1 em caminho do .gitignore."""
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        add = _git(d, "add", "--", "relatorio_diario_20261117.txt")
        assert add.returncode != 0, "git add deveria recusar arquivo ignorado"
        assert "ignored" in (add.stderr or "").lower()


def test_executar_commit_vence_o_gitignore():
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje",
                          "plano_20261117.txt": "plano"}) as d:
        r = executar_commit(d, ["relatorio_diario_*.txt", "plano_*.txt"],
                             "teste", add_forcado=True)
        assert r["status"] == STATUS_COMMITADO, r
        assert sorted(r["arquivos"]) == ["plano_20261117.txt",
                                         "relatorio_diario_20261117.txt"]
        assert _arquivos_no_head(d) == ["plano_20261117.txt",
                                        "relatorio_diario_20261117.txt"]
        pendente = _git(d, "status", "--porcelain").stdout
        assert "relatorio_diario" not in pendente and "plano_" not in pendente


def test_sem_add_forcado_falha_com_status_explicito():
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        r = executar_commit(d, ["relatorio_diario_*.txt"], "teste",
                             add_forcado=False)
        assert r["status"] == STATUS_ADD_FALHOU, r
        assert "ignored" in r["detalhe"].lower()
        assert _git(d, "ls-files").stdout.strip() == ""


def test_nao_publica_historico_do_disco():
    """71 relatorios antigos no disco: so o recente entra."""
    arquivos = {f"relatorio_diario_2026{i:02d}01.txt": ("velho", VELHO)
                for i in range(1, 13)}
    arquivos["relatorio_diario_20261117.txt"] = "hoje"
    with repo_temporario(arquivos) as d:
        r = executar_commit(d, ["relatorio_diario_*.txt"], "teste")
        assert r["status"] == STATUS_COMMITADO, r
        assert r["arquivos"] == ["relatorio_diario_20261117.txt"], r
        assert _arquivos_no_head(d) == ["relatorio_diario_20261117.txt"]


def test_nao_toca_em_arquivo_fora_da_whitelist():
    with repo_temporario({"codigo.py": "v1",
                          "relatorio_diario_20261117.txt": "hoje"}) as d:
        _git(d, "add", "-f", "--", "codigo.py", ".gitignore")
        _git(d, "commit", "-q", "-m", "base")
        _tocar(os.path.join(d, "codigo.py"), "v2")   # mudanca humana, fora da whitelist
        r = executar_commit(d, ["relatorio_diario_*.txt"], "teste")
        assert r["status"] == STATUS_COMMITADO, r
        assert _arquivos_no_head(d) == [".gitignore", "codigo.py",
                                        "relatorio_diario_20261117.txt"]
        # o codigo.py do HEAD continua v1 e a mudanca segue pendente
        assert _git(d, "show", "HEAD:codigo.py").stdout == "v1"
        assert " M codigo.py" in _git(d, "status", "--porcelain").stdout


def test_segunda_execucao_e_nada_novo():
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        assert executar_commit(d, ["relatorio_diario_*.txt"], "t1")["status"] \
            == STATUS_COMMITADO
        r2 = executar_commit(d, ["relatorio_diario_*.txt"], "t2")
        assert r2["status"] == STATUS_NADA_NOVO, r2
        assert _git(d, "rev-list", "--count", "HEAD").stdout.strip() == "1"


def test_whitelist_vazia_nao_faz_nada():
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        r = executar_commit(d, [], "teste")
        assert r["status"] == STATUS_NADA_PRESENTE, r
        assert _git(d, "rev-list", "--count", "HEAD").returncode != 0   # sem commit


def test_repo_sem_arquivo_permitido_nao_commita():
    with repo_temporario({"codigo.py": "v1"}) as d:
        r = executar_commit(d, ["relatorio_diario_*.txt"], "teste")
        assert r["status"] == STATUS_NADA_PRESENTE, r


def test_repo_inexistente_nao_levanta():
    r = executar_commit(os.path.join(tempfile.gettempdir(), "nao_existe_xyz"),
                         ["relatorio_*.txt"], "teste")
    assert r["status"] in (STATUS_NADA_PRESENTE, STATUS_ADD_FALHOU,
                           STATUS_COMMIT_FALHOU), r


# --------------------------------------------------- caminhos_permitidos ---
def test_caminhos_permitidos_e_puro():
    """2.3: a checagem so le o disco; nao chama git nem cria commit."""
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        r = caminhos_permitidos(["relatorio_diario_*.txt"], d)
        assert r["status"] == STATUS_OK, r
        assert r["arquivos"] == ["relatorio_diario_20261117.txt"], r
        assert _git(d, "rev-list", "--count", "HEAD").returncode != 0
        assert _git(d, "ls-files").stdout.strip() == ""
        assert _git(d, "diff", "--cached", "--quiet").returncode == 0
        # arquivo ignorado nao aparece nem como untracked: nada mudou no git
        assert "relatorio_diario" not in _git(d, "status", "--porcelain").stdout


def test_caminhos_permitidos_whitelist_vazia():
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        r = caminhos_permitidos([], d)
        assert r["status"] == STATUS_NADA_PRESENTE, r


def test_caminhos_permitidos_respeita_janela():
    with repo_temporario({"relatorio_diario_20261117.txt": ("hoje", VELHO)}) as d:
        assert caminhos_permitidos(["relatorio_diario_*.txt"], d)["status"] \
            == STATUS_NADA_PRESENTE
        assert caminhos_permitidos(["relatorio_diario_*.txt"], d,
                                   janela_horas=None)["status"] == STATUS_OK


# --------------------------------------------------------------- dry_run ----
def test_dry_run_nao_toca_no_indice():
    """2.3: dry_run devolve a lista e deixa o repo exatamente como estava."""
    with repo_temporario({"relatorio_diario_20261117.txt": "hoje"}) as d:
        antes = _git(d, "status", "--porcelain").stdout
        r = executar_commit(d, ["relatorio_diario_*.txt"], "teste",
                            dry_run=True)
        assert r["status"] == STATUS_DRY_RUN, r
        assert r["arquivos"] == ["relatorio_diario_20261117.txt"], r
        assert _git(d, "status", "--porcelain").stdout == antes
        assert _git(d, "rev-list", "--count", "HEAD").returncode != 0
        assert _git(d, "ls-files").stdout.strip() == ""


def test_dry_run_sem_arquivo_mantem_nada_presente():
    with repo_temporario({"codigo.py": "v1"}) as d:
        r = executar_commit(d, ["relatorio_diario_*.txt"], "teste",
                            dry_run=True)
        assert r["status"] == STATUS_NADA_PRESENTE, r


# ------------------------------------------------------------- integracao ----
def test_agente_usa_o_modulo_e_nao_add_sem_f():
    caminho = os.path.join(BASE, "agente_monstro_core.py")
    with open(caminho, encoding="utf-8", errors="replace") as f:
        fonte = f.read()
    assert "from commit_dia import STATUS_SENSIVEL, executar_commit, mensagem_fecho" in fonte
    assert "executar_commit(" in fonte
    assert 'dry_run=cfg.get("dry_run", False)' in fonte
    assert "verificar_sensivel=cfg.get(\"verificar_sensivel\", True)" in fonte
    # o add manual (sem -f) saiu do agente
    assert '"add", "--"' not in fonte
    assert '"git", "-C", BASE_DIR, "add"' not in fonte


def test_config_tem_as_flags_do_patch():
    import json
    with open(os.path.join(BASE, "agente_config.json"), encoding="utf-8-sig") as f:
        cfg = json.load(f)["git"]
    assert cfg["add_forcado"] is True
    assert cfg["janela_horas"] == 26
    assert cfg["dry_run"] is False  # 2.3: desligado em producao
    for padrao in ("relatorio_diario_*.txt", "plano_*.txt",
                   "logs/fluxo_resumo_*.json",
                   "ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md",
                   "relatorio_metricas_*.txt"):
        assert padrao in cfg["caminhos_permitidos"], padrao


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"[PASS] {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"[FAIL] {nome} - {e}")
    print(f"\n{'OK' if not falhas else 'FALHAS'}: {falhas}")
    sys.exit(1 if falhas else 0)
