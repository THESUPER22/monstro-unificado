#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_metricas.py  (P1 17/11 #1)

Testes do modulo metricas.py (puro, sem MT5/TensorFlow).
Roda direto (python tests\\test_metricas.py) ou via pytest.
"""
import os
import sys
from types import SimpleNamespace

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from metricas import (Posicao, estatisticas, formatar_relatorio,  # noqa: E402
                      por_dia, resultado_por_posicao, resumo,
                      t_critico95, veredito)


def perto(a, b, tol=1e-3):
    return a is not None and b is not None and abs(a - b) <= tol


def pos(pid, rs, vol=1.0, saida=1000, magic=123456, entrada=None):
    return Posicao(position_id=pid, symbol="WDOZ26", magic=magic, volume=vol,
                   resultado_rs=rs, entrada_ts=entrada if entrada is not None else saida - 60,
                   saida_ts=saida, n_deals=2)


def deal(pid, ts, profit=0.0, entry=0, magic=123456, volume=1.0, **extra):
    d = {"position_id": pid, "time": ts, "profit": profit, "entry": entry,
         "magic": magic, "volume": volume, "symbol": "WDOZ26",
         "commission": 0.0, "swap": 0.0, "fee": 0.0}
    d.update(extra)
    return d


# ------------------------------------------------------------ t_critico95 ---
def test_t_critico_valores_conhecidos():
    assert perto(t_critico95(1), 12.706)
    assert perto(t_critico95(10), 2.228)
    assert perto(t_critico95(30), 2.042)
    assert perto(t_critico95(68), 1.9955, 0.002)   # n=69 do historico LIVE
    assert 1.960 <= t_critico95(1000) <= 1.965     # assintota 1,96


def test_t_critico_decrescente():
    valores = [t_critico95(gl) for gl in (1, 2, 5, 10, 30, 60, 120, 500)]
    assert all(a > b for a, b in zip(valores, valores[1:]))


def test_t_critico_invalido():
    for ruim in (0, -1):
        try:
            t_critico95(ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"gl={ruim} deveria levantar ValueError")


# --------------------------------------------------- resultado_por_posicao --
def test_agrupa_entrada_e_saida():
    deals = [deal(1, 100, profit=0.0, entry=0),
             deal(1, 200, profit=100.0, entry=1, commission=-0.6)]
    r = resultado_por_posicao(deals)
    assert len(r) == 1
    p = r[0]
    assert p.position_id == 1
    assert p.resultado_rs == 99.4
    assert p.n_deals == 2
    assert p.entrada_ts == 100 and p.saida_ts == 200
    assert p.volume == 1.0


def test_saidas_parciais_somam():
    deals = [deal(7, 100, entry=0, volume=2.0),
             deal(7, 200, entry=1, volume=1.0, profit=10.0),
             deal(7, 300, entry=1, volume=1.0, profit=-4.0)]
    p = resultado_por_posicao(deals)[0]
    assert p.resultado_rs == 6.0
    assert p.volume == 2.0
    assert p.n_deals == 3


def test_ignora_position_id_zero():
    deals = [deal(0, 100, profit=10000.0), deal(5, 100, profit=5.0, entry=1)]
    r = resultado_por_posicao(deals)
    assert [p.position_id for p in r] == [5]
    assert r[0].resultado_rs == 5.0


def test_filtro_por_magic():
    deals = [deal(1, 100, profit=10.0, entry=1, magic=123456),
             deal(2, 100, profit=20.0, entry=1, magic=7008),
             deal(3, 100, profit=99.0, entry=1, magic=999999)]
    assert len(resultado_por_posicao(deals, [123456])) == 1
    assert len(resultado_por_posicao(deals, [123456, 7008])) == 2
    assert len(resultado_por_posicao(deals, None)) == 3


def test_volume_fallback_quando_entrada_sem_volume():
    deals = [deal(9, 100, entry=0, volume=0.0), deal(9, 200, entry=1, volume=1.0, profit=3.0)]
    p = resultado_por_posicao(deals)[0]
    assert p.volume == 1.0
    assert perto(p.resultado_pt, 0.3)


def test_aceita_objetos_do_mt5():
    d1 = SimpleNamespace(position_id=4, time=100, profit=0.0, entry=0, magic=123456,
                         volume=1.0, symbol="WDOZ26", commission=0.0, swap=0.0, fee=0.0)
    d2 = SimpleNamespace(position_id=4, time=200, profit=50.0, entry=1, magic=123456,
                         volume=1.0, symbol="WDOZ26", commission=0.0, swap=0.0, fee=0.0)
    p = resultado_por_posicao([d1, d2])[0]
    assert p.resultado_rs == 50.0
    assert p.symbol == "WDOZ26"


def test_ordena_por_saida():
    deals = [deal(2, 300, entry=1, profit=1.0), deal(1, 100, entry=1, profit=1.0)]
    assert [p.position_id for p in resultado_por_posicao(deals)] == [1, 2]


def test_posicao_pt_normaliza_volume():
    p = pos(1, 50.0, vol=5.0)
    assert perto(p.resultado_pt, 1.0)          # 50 R$ / (10 * 5) = 1 pt


# ------------------------------------------------------------- estatisticas -
def test_estatisticas_vazia():
    e = estatisticas([])
    assert e["n"] == 0
    assert e["media"] is None and e["ic95"] == (None, None)
    assert e["fator_lucro"] is None and e["taxa_acerto"] is None


def test_estatisticas_n1():
    e = estatisticas([2.5])
    assert e["n"] == 1
    assert e["media"] == 2.5
    assert e["desvio"] == 0.0
    assert e["erro_padrao"] is None
    assert e["ic95"] == (None, None)


def test_estatisticas_serie_conhecida():
    e = estatisticas([1.0, 2.0, 3.0, 4.0])
    assert perto(e["media"], 2.5)
    assert perto(e["desvio"], 1.290994, 1e-5)
    assert perto(e["erro_padrao"], 0.645497, 1e-5)
    assert perto(e["ic95"][0], 0.4460, 1e-3)
    assert perto(e["ic95"][1], 4.5540, 1e-3)


def test_variancia_zero_ic_fechado():
    e = estatisticas([3.0, 3.0, 3.0])
    assert e["ic95"] == (3.0, 3.0)


def test_fator_lucro():
    assert perto(estatisticas([10.0, -5.0])["fator_lucro"], 2.0)
    assert estatisticas([10.0, 5.0])["fator_lucro"] == float("inf")
    assert estatisticas([-10.0, -5.0])["fator_lucro"] == 0.0


def test_drawdown_e_sequencia():
    e = estatisticas([10.0, -5.0, -5.0, -5.0, 20.0, -30.0])
    assert e["seq_perdas"] == 3
    # acumulado: 10, 5, 0, -5, 15, -15 -> pico 15, vale -15 => dd 30
    assert perto(e["drawdown"], 30.0)


def test_taxa_acerto_e_empates():
    e = estatisticas([1.0, -1.0, 0.0, 2.0])
    assert e["vitorias"] == 2 and e["derrotas"] == 1 and e["empates"] == 1
    assert perto(e["taxa_acerto"], 0.5)


# ------------------------------------------------------------------ resumo --
def test_resumo_17_11_bate_com_a_autopsia():
    """17 trades, R$ 735 brutos: liquido 714,60 e gate 374,60 (37,46 pts)."""
    posicoes = [pos(i, 735.0 / 17, saida=1000 + i) for i in range(17)]
    r = resumo(posicoes)
    assert r["n"] == 17
    assert r["total_bruto_rs"] == 735.0
    assert r["total_liquido_rs"] == 714.6
    assert r["total_gate_rs"] == 374.6
    assert perto(r["gate"]["total"], 37.46)
    assert perto(r["bruto"]["media"], 4.3235, 1e-3)
    assert perto(r["gate"]["media"], 2.2035, 1e-3)
    assert r["custo_pt"] == 0.12
    assert r["gate_pt"] == 2.12


def test_resumo_vazio():
    r = resumo([])
    assert r["n"] == 0
    assert r["total_bruto_rs"] == 0.0 and r["total_gate_rs"] == 0.0
    assert r["gate"]["ic95"] == (None, None)


def test_resumo_volume_5_custos_escalam():
    r = resumo([pos(1, 100.0, vol=5.0), pos(2, -50.0, vol=5.0)])
    # bruto 50; custo 2 x 1,20 x 5 = 12; gate 2 x 21,20 x 5 = 212
    assert r["total_bruto_rs"] == 50.0
    assert r["total_liquido_rs"] == 38.0
    assert r["total_gate_rs"] == -162.0
    # pontos por contrato: +2 e -1
    assert perto(r["bruto"]["media"], 0.5)


def test_por_dia_agrupa_e_ordena():
    # 2026-11-16 e 2026-11-17 (hora do servidor codificada como UTC)
    import calendar
    t16 = calendar.timegm((2026, 11, 16, 12, 0, 0, 0, 0, 0))
    t17 = calendar.timegm((2026, 11, 17, 12, 0, 0, 0, 0, 0))
    posicoes = [pos(1, 100.0, saida=t17), pos(2, -50.0, saida=t16),
                pos(3, 30.0, saida=t17)]
    dias = por_dia(posicoes)
    assert [d["dia"] for d in dias] == ["2026-11-16", "2026-11-17"]
    assert dias[0]["n"] == 1 and dias[0]["bruto_rs"] == -50.0
    assert dias[1]["n"] == 2 and dias[1]["bruto_rs"] == 130.0
    # gate: 130 - 2*21,20 = 87,60
    assert dias[1]["gate_rs"] == 87.6


# --------------------------------------------------------------- veredito ---
def test_veredito_tres_casos():
    assert "amostra insuficiente" in veredito({"n": 1, "ic95": (None, None)})
    assert "LUCRATIVO" in veredito({"n": 50, "ic95": (0.2, 3.0)})
    assert "PERDEDOR" in veredito({"n": 50, "ic95": (-3.0, -0.2)})
    assert "INDISTINGUIVEL" in veredito({"n": 50, "ic95": (-1.0, 2.0)})


# ------------------------------------------------------------- relatorio ----
def test_relatorio_tem_as_tres_visoes_e_veredito():
    posicoes = [pos(i, 735.0 / 17, saida=1000 + i) for i in range(17)]
    r = resumo(posicoes)
    txt = formatar_relatorio(r, por_dia(posicoes), "2026-11-03 -> 2026-11-17",
                             [123456], gerado_em="2026-11-17 21:00")
    for esperado in ("RELATORIO DE METRICAS", "bruto", "liquido", "gate",
                     "IC95", "714.60", "374.60", "LUCRATIVO"):
        assert esperado in txt, f"faltou {esperado!r} no relatorio"


def test_relatorio_vazio_nao_quebra():
    txt = formatar_relatorio(resumo([]), [], "janela vazia", None,
                             gerado_em="2026-11-17 21:00")
    assert "amostra insuficiente" in txt
    assert "INDISTINGUIVEL" not in txt


# ------------------------------------------------------------- integracao ---
def test_script_usa_o_modulo_e_salva_atomico():
    caminho = os.path.join(BASE, "relatorio_metricas.py")
    with open(caminho, encoding="utf-8") as f:
        fonte = f.read()
    assert "from metricas import" in fonte
    for nome in ("resultado_por_posicao(", "resumo(", "por_dia(",
                 "formatar_relatorio(", "salvar_texto_atomico("):
        assert nome in fonte, f"script nao usa {nome}"
    assert "history_deals_get(" in fonte


def test_whitelist_do_commit_inclui_o_relatorio():
    import json
    with open(os.path.join(BASE, "agente_config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    assert "relatorio_metricas_*.txt" in cfg["git"]["caminhos_permitidos"]


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
