# -*- coding: utf-8 -*-
"""Testes do aceite pos-pregao (read-only)."""
import os
import subprocess
import sys
from datetime import date, datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from aceite_pos_pregao import (coletar, commits_do_fecho,  # noqa: E402
                               contar_10016, contar_teto,
                               encerrou_graciosamente, permitido,
                               resolver_log, soma_deals, ultimo_pnl_mt5)

DIA = date(2026, 11, 18)
T = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc).timestamp()

LOG_OK = (
    "2026-11-18 10:00:00,000 - INFO - ordem ok\n"
    "2026-11-18 10:05:00,000 - INFO - [pnl_dia] MT5: 3 deals, liquido +11.74 (magics [123457, 7008])\n"
    "2026-11-18 17:35:00,000 - INFO - [pnl_dia] MT5: 3 deals, liquido +11.74 (magics [123457, 7008])\n"
)
AGENTE_OK = "2026-11-18 17:35:39 - INFO - robo encerrou graciosamente\n"

DEALS = [
    {"time": T, "profit": 10.0, "commission": 0.0, "swap": 0.0,
     "fee": 0.0, "magic": 123457, "entry": 1},
    {"time": T, "profit": 2.34, "commission": 0.0, "swap": 0.0,
     "fee": 0.0, "magic": 123457, "entry": 1},
    {"time": T, "profit": 0.0, "commission": -0.60, "swap": 0.0,
     "fee": 0.0, "magic": 123457, "entry": 0},
]


def test_conta_linhas_10016_e_teto():
    txt = ("retcode 10016\noutra linha 10016 10016\n"
           "TETO DE EXECUCAO ESTOURADO\n")
    assert contar_10016(txt) == 2
    assert contar_teto(txt) == 1


def test_ultimo_pnl_pega_o_mais_recente_com_magics_e_horario():
    p = ultimo_pnl_mt5(LOG_OK)
    assert p == {"deals": 3, "liquido": 11.74, "magics": [123457, 7008],
                 "quando": datetime(2026, 11, 18, 17, 35, 0, 0)}
    assert ultimo_pnl_mt5("nada") is None


def test_encerrou_so_no_dia_certo():
    assert encerrou_graciosamente(AGENTE_OK, DIA) is True
    assert encerrou_graciosamente(AGENTE_OK, date(2026, 11, 19)) is False


def test_soma_saidas_ignora_comissao_de_entrada():
    saidas, n_saidas = soma_deals(DEALS, DIA, [123457], apenas_saida=True)
    todos, n_todos = soma_deals(DEALS, DIA, [123457], apenas_saida=False)
    assert (saidas, n_saidas) == (12.34, 2)
    assert (todos, n_todos) == (11.74, 3)


def test_soma_deals_respeita_o_horario_do_snapshot():
    """`ate` e o que corrige o item 3: snapshot nao e o dia inteiro."""
    antes = datetime(2026, 11, 18, 9, 0)
    depois = datetime(2026, 11, 18, 11, 0)
    assert soma_deals(DEALS, DIA, [123457], ate=antes) == (0.0, 0)
    assert soma_deals(DEALS, DIA, [123457], ate=depois) == (11.74, 3)


def test_permitido_usa_whitelist():
    padroes = ["ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md",
               "logs/fluxo_resumo_*.json"]
    assert permitido("ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md", padroes)
    assert permitido("logs\\fluxo_resumo_20261118.json", padroes)
    assert not permitido("monstro_unificado_v22.py", padroes)


def test_coletar_ok_quando_os_5_numeros_batem(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, deals=DEALS, log_texto=LOG_OK,
                agente_texto=AGENTE_OK,
                commit_info={"commits": 1, "arquivos": ["ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md"],
                             "extras": [], "ok": True})
    assert r["retcode_10016"] == 0
    assert r["teto_estourado"] == 0
    assert r["pnl_igual_log"] is True
    assert r["pnl_igual_saidas"] is False
    assert r["pnl_igual_todos"] is True
    assert r["parado_ok"] is True and r["encerrou_graciosamente"] is True
    assert r["ok"] is True


def test_coletar_falha_com_10016_ou_commit_fora_da_whitelist(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    log = LOG_OK + "2026-11-18 11:00:00 - ERROR - retcode 10016\n"
    r = coletar(str(tmp_path), DIA, deals=DEALS, log_texto=log,
                agente_texto=AGENTE_OK,
                commit_info={"commits": 1, "arquivos": ["monstro_unificado_v22.py"],
                             "extras": ["monstro_unificado_v22.py"], "ok": False})
    assert r["retcode_10016"] == 1
    assert r["ok"] is False


# ------------------------------------------------- log do dia (rotacao) -----
def test_resolver_log_prefere_o_datado(tmp_path):
    datado = tmp_path / "monstro_wdo_20261118.log"
    datado.write_text("x", encoding="utf-8")
    (tmp_path / "monstro_wdo.log").write_text("y", encoding="utf-8")
    caminho, motivo = resolver_log(str(tmp_path), DIA)
    assert caminho == str(datado) and motivo == "datado"


def test_resolver_log_usa_o_atual_da_sessao_do_dia(tmp_path):
    atual = tmp_path / "monstro_wdo.log"
    atual.write_text("x", encoding="utf-8")
    mtime = datetime(2026, 11, 18, 12, 0).timestamp()
    os.utime(atual, (mtime, mtime))
    caminho, motivo = resolver_log(str(tmp_path), DIA)
    assert caminho == str(atual) and "ainda nao rotacionado" in motivo


def test_resolver_log_nao_usa_atual_de_outro_dia(tmp_path):
    atual = tmp_path / "monstro_wdo.log"
    atual.write_text("x", encoding="utf-8")
    mtime = datetime(2026, 11, 17, 12, 0).timestamp()
    os.utime(atual, (mtime, mtime))
    caminho, motivo = resolver_log(str(tmp_path), DIA)
    assert caminho == ""
    assert "2026-11-17" in motivo


def test_coletar_sem_log_nao_passa_nem_zera_10016(tmp_path):
    """Sem log nao existe '0 x 10016': o aceite nao pode passar."""
    r = coletar(str(tmp_path), DIA, deals=DEALS, agente_texto=AGENTE_OK,
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})
    assert r["log_encontrado"] is False
    assert r["log_usado"] == ""
    assert r["ok"] is False


def test_coletar_18_11_snapshot_vale_so_ate_o_horario_da_linha(tmp_path):
    """Reproduz o defeito medido em 18/11.

    Ultimo [pnl_dia] as 16:58:32 com +5,00 (30 deals). Depois fecharam mais
    dois deals: entrada 17:02:47 e saida 17:23:14 (+65,00). O dia terminou
    em +70,00. O snapshot de 16:58 continua valido; comparar com o dia
    inteiro e que estava errado.
    """
    log = ("2026-11-18 16:58:32,530 - INFO - [pnl_dia] MT5: 30 deals, "
           "liquido +5.00 (magics [7008, 123456])\n")
    deals = [{"time": T, "profit": 5.0 / 30, "commission": 0.0,
              "swap": 0.0, "fee": 0.0, "magic": 123456, "entry": 1}
             for _ in range(30)]
    deals.append({"time": datetime(2026, 11, 18, 17, 2, 47,
                                   tzinfo=timezone.utc).timestamp(),
                  "profit": 0.0, "commission": 0.0, "swap": 0.0,
                  "fee": 0.0, "magic": 123456, "entry": 0})
    deals.append({"time": datetime(2026, 11, 18, 17, 23, 14,
                                   tzinfo=timezone.utc).timestamp(),
                  "profit": 65.0, "commission": 0.0, "swap": 0.0,
                  "fee": 0.0, "magic": 123456, "entry": 1})
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, deals=deals, log_texto=log,
                agente_texto=AGENTE_OK,
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})
    assert r["pnl_log"]["liquido"] == 5.0
    assert r["pnl_soma_ate_log"] == 5.0
    assert r["pnl_igual_log"] is True
    assert r["pnl_soma_todos"] == 70.0
    assert r["pnl_igual_todos"] is False
    assert r["ok"] is True


def test_watchdog_nao_conta_como_encerramento_do_agente():
    """A linha do watchdog observa o parado.ok; nao e o fecho concluido."""
    txt = ("2026-11-18 17:37:00,000 - INFO - watchdog: robo encerrou "
           "graciosamente (parado.ok) - sem reinicio\n")
    assert encerrou_graciosamente(txt, DIA) is False


def test_encerramento_do_agente_conta():
    assert encerrou_graciosamente(AGENTE_OK, DIA) is True
    assert encerrou_graciosamente(AGENTE_OK, date(2026, 11, 17)) is False


def _repo_com_dois_commits(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (["init", "-q"],
                ["config", "user.email", "t@t"],
                ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(repo), *cmd], check=True)
    (repo / "a.txt").write_text("a", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm",
                    "trabalho manual da noite"], check=True)
    (repo / "b.txt").write_text("b", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "b.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm",
                    f"fecho autonomo {date.today():%Y-%m-%d} (agente Fase 1)"],
                   check=True)
    return repo


def test_commits_do_fecho_filtra_pela_mensagem(tmp_path):
    """18/11: a janela 17:30-23:59 pegava commit manual (4 commits/8 arquivos)."""
    repo = _repo_com_dois_commits(tmp_path)
    shas = commits_do_fecho(str(repo), date.today())
    assert len(shas) == 1
    assunto = subprocess.run(
        ["git", "-C", str(repo), "show", "-s", "--pretty=%s", shas[0]],
        capture_output=True, text=True, encoding="utf-8").stdout.strip()
    assert assunto.startswith(f"fecho autonomo {date.today():%Y-%m-%d}")


def test_commits_do_fecho_de_outro_dia_nao_entra(tmp_path):
    repo = _repo_com_dois_commits(tmp_path)
    assert commits_do_fecho(str(repo), date(2026, 11, 17)) == []
