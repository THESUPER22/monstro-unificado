# -*- coding: utf-8 -*-
"""Kill-switch por deals do MT5 (23.61/23.62).

Nenhum processo e morto: MT5, config, log e funcoes de parada sao injetados.
A linha corrompida de 19/11 esta aqui de proposito: o parser antigo
(``Deal de sa.da ... Lucro=``) nao a reconhecia e o kill-switch dizia 0.00.
"""
import logging
import os
import sys
import types

import pytest
from datetime import date, datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import agente_monstro_core as ag  # noqa: E402

@pytest.fixture(autouse=True)
def _parar_isolado(tmp_path, monkeypatch):
    """NENHUM teste deste modulo pode tocar o parar.txt real do repo."""
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))


DIA_19 = date(2026, 11, 19)
# Copiada de monstro_wdo.log:1179 (19/11/2026). O "i" de "saida" virou
# U+FFFD + literal "\x83" + soft hyphen; por isso o regex antigo falhava.
LINHA_REAL_19_11 = (
    "2026-11-19 09:35:27,098 - INFO - Deal de sa\ufffd\\x83\xadda "
    "encontrado para ticket 2597390578: DealTicket=1883493264, "
    "PositionID=2597390578, Lucro=-85.00, Pre\ufffd\\x83§o "
    "Sa\ufffd\\x83\xadda=5895.0, Volume=1.0, Hora=2026-11-19 06:35:25"
)


def _deal(valor, quando=None, magic=123456):
    base = quando or datetime.now()
    ts = base.replace(tzinfo=timezone.utc).timestamp()
    return {"time": ts, "profit": valor, "commission": 0.0,
            "swap": 0.0, "fee": 0.0, "magic": magic, "entry": 1}


def _deal_em(valor, hora):
    return _deal(valor, quando=datetime(2026, 11, 19, *hora))


def _mt5_falso(monkeypatch, deals, initialize=True):
    modulo = types.ModuleType("MetaTrader5")
    modulo.initialize = lambda: initialize
    modulo.shutdown = lambda: None
    modulo.history_deals_get = lambda ini, fim: deals
    monkeypatch.setitem(sys.modules, "MetaTrader5", modulo)
    monkeypatch.setattr(ag, "carregar_config_robo",
                        lambda: {"geral": {"magic_number": 123456},
                                 "rompimento": {"magic": 7008}})


def _log_com_pnl(tmp_path, monkeypatch, liquido, linha_extra="", hora="17:36:04,008"):
    hoje = datetime.now().strftime("%Y-%m-%d")
    caminho = tmp_path / "monstro_wdo.log"
    caminho.write_text(
        f"{hoje} {hora} - INFO - [pnl_dia] MT5: 54 deals, "
        f"liquido {liquido:.2f} (magics [7008, 123456])\n{linha_extra}\n",
        encoding="utf-8")
    monkeypatch.setattr(ag, "LOG_ROBO", str(caminho))


# --------------------------------------------------------------- regressao --
def test_parser_de_log_de_deals_foi_removido():
    assert not hasattr(ag, "RE_DEAL_SAIDA")


def test_linha_real_19_11_com_i_corrompido_nao_e_a_fonte(tmp_path, monkeypatch):
    """Mesmo com a linha REAL no log, o P&L vem dos deals, nao do Lucro=."""
    _log_com_pnl(tmp_path, monkeypatch, -1025.0, LINHA_REAL_19_11)
    _mt5_falso(monkeypatch, [_deal(-1025.0)])
    assert ag.calcular_loss_acumulado_hoje() == -1025.0


def test_leitura_falha_e_desconhecido_nunca_zero(tmp_path, monkeypatch, caplog):
    _log_com_pnl(tmp_path, monkeypatch, -1025.0)
    _mt5_falso(monkeypatch, [], initialize=False)
    with caplog.at_level(logging.ERROR):
        assert ag.calcular_loss_acumulado_hoje() is None
    assert "estado desconhecido" in caplog.text


def test_history_deals_none_e_desconhecido(tmp_path, monkeypatch, caplog):
    _log_com_pnl(tmp_path, monkeypatch, -1025.0)
    modulo = types.ModuleType("MetaTrader5")
    modulo.initialize = lambda: True
    modulo.shutdown = lambda: None
    modulo.history_deals_get = lambda ini, fim: None
    monkeypatch.setitem(sys.modules, "MetaTrader5", modulo)
    monkeypatch.setattr(ag, "carregar_config_robo",
                        lambda: {"geral": {"magic_number": 123456}})
    with caplog.at_level(logging.ERROR):
        assert ag.calcular_loss_acumulado_hoje() is None
    assert "history_deals_get() None" in caplog.text


# ------------------------------------- novo contrato: min() + so alerta -----
def test_calcular_loss_usa_o_pior_valor_entre_deals_e_snapshot():
    snapshot = {"liquido": -260.0, "quando": datetime(2026, 11, 19, 12, 45),
                "deals": 24}
    deals = [_deal_em(-260.0, (12, 45, 0))]
    r = ag.calcular_loss_com_deals(
        deals, DIA_19, {123456}, snapshot=snapshot,
        agora=datetime(2026, 11, 19, 12, 50))
    assert r["pnl_deals"] == -260.0 and r["acao"] == -260.0
    assert r["pnl_ate_snapshot"] == -260.0 and r["divergencia"] == 0.0


def test_trade_fechado_entre_log_e_checagem_nao_desliga_nivel_1():
    """Perda nova depois do snapshot piora o valor: N1 continua acionando."""
    snapshot = {"liquido": -260.0, "quando": datetime(2026, 11, 19, 12, 45),
                "deals": 24}
    deals = [_deal_em(-260.0, (12, 45, 0)), _deal_em(-20.0, (12, 47, 30))]
    r = ag.calcular_loss_com_deals(
        deals, DIA_19, {123456}, snapshot=snapshot,
        agora=datetime(2026, 11, 19, 12, 50))
    assert r["pnl_deals"] == -280.0
    assert r["acao"] == -280.0 <= -250  # nivel 1
    assert r["divergencia"] == 0.0


def test_trade_lucro_depois_do_snapshot_tambem_nao_desliga_nivel_1():
    """Mesmo melhorando os deals, o snapshot (pior valor) continua valendo."""
    snapshot = {"liquido": -260.0, "quando": datetime(2026, 11, 19, 12, 45),
                "deals": 24}
    deals = [_deal_em(-260.0, (12, 45, 0)), _deal_em(50.0, (12, 47, 30))]
    r = ag.calcular_loss_com_deals(
        deals, DIA_19, {123456}, snapshot=snapshot,
        agora=datetime(2026, 11, 19, 12, 50))
    assert r["pnl_deals"] == -210.0
    assert r["acao"] == -260.0 <= -250  # nivel 1


def test_comparacao_usa_deals_ate_a_linha_e_so_alerta(tmp_path, monkeypatch, caplog):
    """Divergencia de R$ 925 gera WARNING, NAO 'kill-switch cego'."""
    _log_com_pnl(tmp_path, monkeypatch, -1025.0)
    _mt5_falso(monkeypatch, [_deal(-100.0)])
    with caplog.at_level(logging.WARNING):
        assert ag.calcular_loss_acumulado_hoje() == -1025.0
    assert "SO ALERTA" in caplog.text
    assert "cego" not in caplog.text


def test_sem_snapshot_e_zero_deals_e_0_valido(tmp_path, monkeypatch, caplog):
    (tmp_path / "monstro_wdo.log").write_text("sem snapshot\n", encoding="utf-8")
    monkeypatch.setattr(ag, "LOG_ROBO", str(tmp_path / "monstro_wdo.log"))
    _mt5_falso(monkeypatch, [])
    with caplog.at_level(logging.INFO):
        assert ag.calcular_loss_acumulado_hoje() == 0.0
    assert "0.00 valido" in caplog.text
    assert "cego" not in caplog.text


def test_estado_desconhecido_nao_cria_parar_nem_loga_ok(monkeypatch, tmp_path,
                                                       caplog):
    monkeypatch.setattr(ag, "CFG", {"kill_switch": {
        "ativo": True, "limite_1": -250, "limite_2": -400}})
    monkeypatch.setattr(ag, "kill_switch_ja_ativado", lambda: False)
    monkeypatch.setattr(ag, "calcular_loss_acumulado_hoje", lambda: None)
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    chamadas = []
    monkeypatch.setattr(ag, "nivel2_parar_com_flat",
                        lambda: chamadas.append("n2") or False)
    with caplog.at_level(logging.INFO):
        assert ag.verificar_kill_switch() is False
    assert chamadas == []
    assert not (tmp_path / "parar.txt").exists()
    assert "estado desconhecido" in caplog.text
    assert "sem acao" in caplog.text
    assert " - ok" not in caplog.text


def test_linha_padrao_aparece_mesmo_quando_nivel_1_aciona(tmp_path, monkeypatch,
                                                          caplog):
    _log_com_pnl(tmp_path, monkeypatch, -260.0)
    _mt5_falso(monkeypatch, [_deal(-260.0)])
    monkeypatch.setattr(ag, "CFG", {"kill_switch": {
        "ativo": True, "limite_1": -250, "limite_2": -400}})
    monkeypatch.setattr(ag, "kill_switch_ja_ativado", lambda: False)
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    with caplog.at_level(logging.INFO):
        assert ag.verificar_kill_switch() is False
    assert "kill-switch: loss hoje -260.00" in caplog.text
    assert "NIVEL 1" in caplog.text
    assert (tmp_path / "parar.txt").exists()


def test_deals_validados_acionam_nivel_2_na_ordem_segura(tmp_path, monkeypatch):
    _log_com_pnl(tmp_path, monkeypatch, -1025.0, LINHA_REAL_19_11)
    _mt5_falso(monkeypatch, [_deal(-1025.0)])
    monkeypatch.setattr(ag, "CFG", {"kill_switch": {
        "ativo": True, "limite_1": -250, "limite_2": -400}})
    monkeypatch.setattr(ag, "kill_switch_ja_ativado", lambda: False)
    chamadas = []
    monkeypatch.setattr(ag, "marcar_kill_switch_ativado",
                        lambda: chamadas.append("marcar"))
    monkeypatch.setattr(ag, "_criar_parar_txt",
                        lambda motivo: chamadas.append("parar_txt") or True)
    monkeypatch.setattr(ag, "fechar_posicoes_kill_switch",
                        lambda: chamadas.append("fechar") or (1, []))
    monkeypatch.setattr(ag, "parar_robo",
                        lambda: chamadas.append("parar") or True)
    monkeypatch.setattr(ag, "flat_confirmado_para_fecho",
                        lambda: chamadas.append("flat") or True)
    monkeypatch.setattr(ag, "stop_mt5", lambda: chamadas.append("mt5"))
    assert ag.verificar_kill_switch() is True
    assert chamadas == ["parar_txt", "fechar", "parar", "flat", "mt5", "marcar"]


def test_nivel2_sem_flat_nao_marca_o_dia_e_pode_tentar_de_novo(tmp_path,
                                                              monkeypatch,
                                                              caplog):
    _log_com_pnl(tmp_path, monkeypatch, -1025.0)
    _mt5_falso(monkeypatch, [_deal(-1025.0)])
    monkeypatch.setattr(ag, "CFG", {"kill_switch": {
        "ativo": True, "limite_1": -250, "limite_2": -400}})
    monkeypatch.setattr(ag, "kill_switch_ja_ativado", lambda: False)
    marcou = []
    monkeypatch.setattr(ag, "marcar_kill_switch_ativado",
                        lambda: marcou.append(True))
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    monkeypatch.setattr(ag, "nivel2_parar_com_flat", lambda: False)
    with caplog.at_level(logging.CRITICAL):
        assert ag.verificar_kill_switch() is False
    assert marcou == []
    sinal = tmp_path / "parar.txt"
    assert sinal.exists(), "N2 falho nao pode deixar o robo sem N1"
    assert "KILL-SWITCH LOSS DIARIO: -1025.00" in sinal.read_text(encoding="utf-8")


def test_n2_bem_sucedido_tambem_cria_parar_txt(tmp_path, monkeypatch):
    _log_com_pnl(tmp_path, monkeypatch, -1025.0)
    _mt5_falso(monkeypatch, [_deal(-1025.0)])
    monkeypatch.setattr(ag, "CFG", {"kill_switch": {
        "ativo": True, "limite_1": -250, "limite_2": -400}})
    monkeypatch.setattr(ag, "kill_switch_ja_ativado", lambda: False)
    monkeypatch.setattr(ag, "nivel2_parar_com_flat", lambda: True)
    monkeypatch.setattr(ag, "marcar_kill_switch_ativado", lambda: None)
    monkeypatch.setattr(ag, "PARAR", str(tmp_path / "parar.txt"))
    assert ag.verificar_kill_switch() is True
    assert (tmp_path / "parar.txt").exists()


def test_script_de_realidade_usa_resolver_log():
    caminho = os.path.join(BASE, "tools", "teste_realidade_kill_switch.py")
    with open(caminho, encoding="utf-8") as f:
        src = f.read()
    assert "from aceite_pos_pregao import resolver_log" in src
    assert "resolver_log(BASE, DIA)" in src
    assert "LOG_ROBO_19" not in src


def test_sinal_parar_existente_nao_e_reescrito(tmp_path, monkeypatch, caplog):
    sinal = tmp_path / "parar.txt"
    sinal.write_text("sinal manual do operador", encoding="utf-8")
    monkeypatch.setattr(ag, "PARAR", str(sinal))
    with caplog.at_level(logging.INFO):
        assert ag._criar_parar_txt("KILL-SWITCH LOSS DIARIO: -1025.00") is True
    assert sinal.read_text(encoding="utf-8") == "sinal manual do operador"
    assert "nao reescrito" in caplog.text
