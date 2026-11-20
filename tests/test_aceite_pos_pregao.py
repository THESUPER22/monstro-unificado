# -*- coding: utf-8 -*-
"""Testes do aceite pos-pregao (read-only)."""
import os
import subprocess
import sys
from datetime import date, datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from aceite_pos_pregao import (coletar, commits_do_fecho,  # noqa: E402
                               contar_10016, contar_posicoes_abertas,
                               contar_teto, encerrou_graciosamente, imprimir,
                               permitido, resolver_log, soma_deals,
                               ultimo_kill_switch, ultimo_pnl_mt5)

DIA = date(2026, 11, 18)
T = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc).timestamp()

LOG_OK = (
    "2026-11-18 10:00:00,000 - INFO - ordem ok\n"
    "2026-11-18 10:05:00,000 - INFO - [pnl_dia] MT5: 3 deals, liquido +11.74 (magics [123457, 7008])\n"
    "2026-11-18 17:35:00,000 - INFO - [pnl_dia] MT5: 3 deals, liquido +11.74 (magics [123457, 7008])\n"
)
AGENTE_OK = (
    "2026-11-18 17:35:30,000 - INFO - kill-switch: loss hoje +11.74 "
    "(limites -250/-400) - ok\n"
    "2026-11-18 17:35:39 - INFO - robo encerrou graciosamente\n"
)
AGENTE_5 = (
    "2026-11-18 16:58:32,000 - INFO - kill-switch: loss hoje +5.00 "
    "(limites -250/-400) - ok\n"
    "2026-11-18 17:35:39 - INFO - robo encerrou graciosamente\n"
)

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


def test_coletar_ok_quando_os_6_numeros_batem(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, deals=DEALS, log_texto=LOG_OK,
                agente_texto=AGENTE_OK, posicoes=[],
                commit_info={"commits": 1, "arquivos": ["ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md"],
                             "extras": [], "ok": True})
    assert r["retcode_10016"] == 0
    assert r["teto_estourado"] == 0
    assert r["pnl_igual_log"] is True
    assert r["pnl_igual_saidas"] is False
    assert r["pnl_igual_todos"] is True
    assert r["parado_ok"] is True and r["encerrou_graciosamente"] is True
    assert r["posicoes_abertas"] == 0 and r["posicoes_ok"] is True
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
                agente_texto=AGENTE_5, posicoes=[],
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


# ---------------------------------------- item 6: posicoes apos o fecho ---
def _ok_kwargs(posicoes):
    return dict(deals=DEALS, log_texto=LOG_OK, agente_texto=AGENTE_OK,
                posicoes=posicoes,
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})


def test_item6_conta_so_magics_do_robo():
    assert contar_posicoes_abertas([{"magic": 123457}], [123457, 7008]) == 1
    assert contar_posicoes_abertas([{"magic": 999}], [123457, 7008]) == 0
    assert contar_posicoes_abertas([], [123457, 7008]) == 0


def test_item6_sem_magics_nao_vira_zero():
    assert contar_posicoes_abertas([], None) is None
    assert contar_posicoes_abertas([{"magic": 123457}], []) is None


def test_item6_posicao_aberta_reprova(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA,
                **_ok_kwargs([{"magic": 123457, "ticket": 1}]))
    assert r["posicoes_abertas"] == 1
    assert r["posicoes_ok"] is False
    assert r["ok"] is False


def test_item6_leitura_falhou_nao_passa_por_zero(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, **_ok_kwargs(None))
    assert r["posicoes_abertas"] is None
    assert r["posicoes_ok"] is False
    assert r["ok"] is False


def test_item6_sem_mt5_e_nao_verificado(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, deals=[], log_texto=LOG_OK,
                agente_texto=AGENTE_OK,
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})
    assert r["posicoes_abertas"] is None
    assert r["ok"] is False


def test_imprimir_mostra_o_item6(tmp_path, capsys):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    imprimir(coletar(str(tmp_path), DIA, **_ok_kwargs([])))
    saida = capsys.readouterr().out
    assert "posicoes abertas apos o fecho: 0" in saida

    imprimir(coletar(str(tmp_path), DIA, **_ok_kwargs(None)))
    saida = capsys.readouterr().out
    assert "posicoes abertas apos o fecho: NAO VERIFICADO" in saida
    assert "FALHOU" in saida


def test_item6_modo_mt5_le_as_posicoes(tmp_path, monkeypatch):
    """Sem `deals` fornecidos, o item 6 consulta o MT5 (nao fica sem ler)."""
    import aceite_pos_pregao as ap

    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(ap, "_deals_mt5", lambda dia: DEALS)
    monkeypatch.setattr(ap, "_posicoes_mt5",
                        lambda magics: chamadas.append(magics) or [])
    r = ap.coletar(str(tmp_path), DIA, log_texto=LOG_OK,
                   agente_texto=AGENTE_OK,
                   commit_info={"commits": 1, "arquivos": [], "extras": [],
                                "ok": True})
    assert chamadas == [[123457, 7008]]
    assert r["posicoes_abertas"] == 0
    assert r["ok"] is True


# ------------------------------------------ item 7: kill-switch x [pnl_dia] --
def _ok_kwargs_agente(agente_texto):
    return dict(deals=DEALS, log_texto=LOG_OK, agente_texto=agente_texto,
                posicoes=[],
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})


def test_ultimo_kill_switch_ignora_outro_dia_e_pega_o_mais_recente():
    txt = (
        "2026-11-17 17:35:30,000 - INFO - kill-switch: loss hoje -900.00 - ok\n"
        "2026-11-18 17:34:00,000 - INFO - kill-switch: loss hoje +1.00 - ok\n"
        "2026-11-18 17:35:30,000 - INFO - kill-switch: loss hoje +11.74 - ok\n"
    )
    ks = ultimo_kill_switch(txt, DIA)
    assert ks == {"loss": 11.74,
                  "quando": datetime(2026, 11, 18, 17, 35, 30)}
    assert ultimo_kill_switch(txt, date(2026, 11, 17))["loss"] == -900.0


def test_item7_kill_switch_igual_pnl_passa(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, **_ok_kwargs_agente(AGENTE_OK))
    assert r["kill_switch_ok"] is True
    assert r["kill_switch_zero_com_deals"] is False
    assert r["ok"] is True


def test_item7_divergencia_maior_que_um_reprova(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    agente = AGENTE_OK.replace("+11.74", "+9.00")
    r = coletar(str(tmp_path), DIA, **_ok_kwargs_agente(agente))
    assert r["kill_switch_igual_pnl"] is False
    assert r["kill_switch_ok"] is False
    assert r["ok"] is False


def test_item7_zero_com_deals_no_dia_reprova(tmp_path):
    """Defeito medido em 19/11: 0.00 no log enquanto havia 54 deals."""
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    agente = AGENTE_OK.replace("+11.74", "0.00")
    r = coletar(str(tmp_path), DIA, **_ok_kwargs_agente(agente))
    assert r["kill_switch"]["loss"] == 0.0
    assert r["kill_switch_zero_com_deals"] is True
    assert r["kill_switch_ok"] is False
    assert r["ok"] is False


def test_item7_zero_com_saidas_zeradas_nao_reprova(tmp_path):
    """Dia que fecha em 0 com trades nao e o defeito '0.00 as cegas'."""
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    log = ("2026-11-18 17:36:04,008 - INFO - [pnl_dia] MT5: 2 deals, "
           "liquido 0.00 (magics [123457])\n")
    agente = ("2026-11-18 17:35:30,000 - INFO - kill-switch: loss hoje 0.00 "
              "(limites -250/-400) - ok\n"
              "2026-11-18 17:35:39 - INFO - robo encerrou graciosamente\n")
    deals = [
        {"time": T, "profit": 0.0, "commission": 0.0, "swap": 0.0,
         "fee": 0.0, "magic": 123457, "entry": 0},
        {"time": T, "profit": 0.0, "commission": 0.0, "swap": 0.0,
         "fee": 0.0, "magic": 123457, "entry": 1},
    ]
    r = coletar(str(tmp_path), DIA, deals=deals, log_texto=log,
                agente_texto=agente, posicoes=[],
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})
    assert r["kill_switch_deals_ate"] == 2
    assert r["kill_switch_saidas_com_resultado_ate"] == 0
    assert r["kill_switch_zero_com_deals"] is False
    assert r["kill_switch_ok"] is True
    assert r["ok"] is True


def test_item7_kill_switch_ausente_reprova(tmp_path):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    agente = "2026-11-18 17:35:39 - INFO - robo encerrou graciosamente\n"
    r = coletar(str(tmp_path), DIA, **_ok_kwargs_agente(agente))
    assert r["kill_switch"] is None
    assert r["kill_switch_ok"] is False
    assert r["ok"] is False


def test_item7_compara_com_deals_ate_a_linha_do_kill_switch(tmp_path):
    """Trade fechado depois do kill-switch nao pode reprovar o item 7."""
    ks = ("2026-11-18 12:50:02,000 - INFO - kill-switch: loss hoje -260.00 "
          "(limites -250/-400) - ok\n"
          "2026-11-18 17:35:39 - INFO - robo encerrou graciosamente\n")
    log = ("2026-11-18 17:36:04,008 - INFO - [pnl_dia] MT5: 54 deals, "
           "liquido -1025.00 (magics [123457, 7008])\n")
    cedo = datetime(2026, 11, 18, 12, 45, tzinfo=timezone.utc).timestamp()
    tarde = datetime(2026, 11, 18, 17, 20, tzinfo=timezone.utc).timestamp()
    deals = [{"time": cedo, "profit": -260.0, "commission": 0.0, "swap": 0.0,
              "fee": 0.0, "magic": 123457, "entry": 1},
             {"time": tarde, "profit": -765.0, "commission": 0.0, "swap": 0.0,
              "fee": 0.0, "magic": 123457, "entry": 1}]
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    r = coletar(str(tmp_path), DIA, deals=deals, log_texto=log,
                agente_texto=ks, posicoes=[],
                commit_info={"commits": 1, "arquivos": [], "extras": [],
                             "ok": True})
    assert r["kill_switch_soma_ate"] == -260.0
    assert r["kill_switch_deals_ate"] == 1
    assert r["kill_switch_ok"] is True
    assert r["ok"] is True


def test_imprimir_mostra_o_item7(tmp_path, capsys):
    (tmp_path / "parado.ok").write_text("ok", encoding="utf-8")
    imprimir(coletar(str(tmp_path), DIA, **_ok_kwargs_agente(AGENTE_OK)))
    assert "kill-switch: loss hoje:        +11.74" in capsys.readouterr().out

    agente = AGENTE_OK.replace("+11.74", "0.00")
    imprimir(coletar(str(tmp_path), DIA, **_ok_kwargs_agente(agente)))
    saida = capsys.readouterr().out
    assert "0.00 COM SAIDA COM RESULTADO - FALHOU" in saida
    assert "VEREDITO: FALHOU" in saida
