# -*- coding: utf-8 -*-
"""Testes do aceite pos-pregao (read-only)."""
import os
import sys
from datetime import date, datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from aceite_pos_pregao import (coletar, contar_10016, contar_teto,  # noqa: E402
                               encerrou_graciosamente, permitido,
                               resolver_log, soma_deals, ultimo_pnl_mt5)

DIA = date(2026, 11, 18)
T = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc).timestamp()

LOG_OK = (
    "2026-11-18 10:00:00 - INFO - ordem ok\n"
    "2026-11-18 10:05:00 - INFO - [pnl_dia] MT5: 2 deals, liquido +10.00 (magics [123457, 7008])\n"
    "2026-11-18 17:35:00 - INFO - [pnl_dia] MT5: 3 deals, liquido +12.34 (magics [123457, 7008])\n"
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


def test_ultimo_pnl_pega_o_mais_recente_com_magics():
    p = ultimo_pnl_mt5(LOG_OK)
    assert p == {"deals": 3, "liquido": 12.34, "magics": [123457, 7008]}
    assert ultimo_pnl_mt5("nada") is None


def test_encerrou_so_no_dia_certo():
    assert encerrou_graciosamente(AGENTE_OK, DIA) is True
    assert encerrou_graciosamente(AGENTE_OK, date(2026, 11, 19)) is False


def test_soma_saidas_ignora_comissao_de_entrada():
    saidas, n_saidas = soma_deals(DEALS, DIA, [123457], apenas_saida=True)
    todos, n_todos = soma_deals(DEALS, DIA, [123457], apenas_saida=False)
    assert (saidas, n_saidas) == (12.34, 2)
    assert (todos, n_todos) == (11.74, 3)


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
    assert r["pnl_igual_saidas"] is True
    assert r["pnl_igual_todos"] is False
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
