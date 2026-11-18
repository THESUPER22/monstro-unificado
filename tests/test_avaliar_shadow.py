#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_avaliar_shadow.py  (P1 #2, ROADMAP 23.54.3)

Testes do avaliador pre-registrado do shadow de SL/TP. O ultimo teste congela o
SHA-256 do script: mudar o avaliador depois de ver resultado quebra a suite,
que e exatamente a regra combinada.
"""
import hashlib
import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from avaliar_shadow_sltp import (CUSTO_PTS, avaliar, bootstrap_por_dia,  # noqa: E402
                                 carregar, holm, liquido_pts, p_unilateral,
                                 simular, sl_tp, status_coleta)

DIA = "2026-11-18"
T0 = "2026-11-18T10:00:00"


def _sinal(sinal="BUY", path=None, operado=True, dia=DIA, sl=8.0, tp=8.0,
           atr=10.0):
    return {"ts": T0, "dia": dia, "sinal": sinal, "operado": operado,
            "sl_pts": sl, "tp_pts": tp, "atr": atr,
            "path": path or [[T0, 100.0, 100.0]]}


def _p(hora, bid, ask):
    return [f"2026-11-18T{hora}", bid, ask]


# --------------------------------------------------------------- variantes --
def test_sl_tp_das_quatro_variantes():
    s = _sinal(sl=8.0, tp=0.0, atr=10.0)
    assert sl_tp("A0", s) == (8.0, 0.0)
    assert sl_tp("B", s) == (15.0, 30.0)
    assert sl_tp("C", s) == (8.0, 8.0)
    assert sl_tp("D", s) == (8.0, 12.0)


def test_variante_b_tem_piso_de_3_pontos():
    assert sl_tp("B", _sinal(atr=1.0)) == (3.0, 3.0)


# --------------------------------------------------------------- simulacao --
def test_entrada_paga_meio_ponto_contra():
    r = simular(_sinal(path=[_p("10:00:00", 100.0, 100.0)]), "C")
    assert r["entrada"] == 100.5
    r = simular(_sinal("SELL", path=[_p("10:00:00", 100.0, 100.2)]), "C")
    assert r["entrada"] == 99.5


def test_numerico_vira_datetime_utc():
    """Epoch = relogio do servidor, lido como UTC (nao como fuso da maquina)."""
    from datetime import datetime, timezone
    from avaliar_shadow_sltp import _quando
    dt = _quando(1794936902)      # 17/11 17:35:02 UTC (deal do fecho)
    assert dt == datetime(2026, 11, 17, 17, 35, 2, tzinfo=timezone.utc)
    assert dt.tzinfo == timezone.utc
    # string sem fuso tambem e UTC; com Z/+00:00 idem
    assert _quando("2026-11-17T20:35:00").hour == 20
    assert _quando("2026-11-17T20:35:00Z").hour == 20
    assert _quando("2026-11-17T17:35:00-03:00").hour == 20


def test_tp_so_conta_apos_ultrapassar_1_tick():
    # entrada 100.5, TP 8 => nivel 108.5; bid 108.9 NAO basta
    s = _sinal(path=[_p("10:00:00", 100.0, 100.0),
                     _p("10:01:00", 108.9, 109.0),
                     _p("10:02:00", 105.0, 105.1)])
    r = simular(s, "C")
    assert r["motivo"] == "fim_dados"
    # bid 109.0 (1 tick acima do nivel) fecha no nivel, sem otimismo
    s["path"][1] = _p("10:01:00", 109.0, 109.1)
    r = simular(s, "C")
    assert r["motivo"] == "tp"
    assert r["saida"] == 108.5
    assert r["bruto_pts"] == 8.0


def test_sl_leva_1_tick_de_slippage():
    s = _sinal(path=[_p("10:00:00", 100.0, 100.0),
                     _p("10:01:00", 92.5, 92.6)])
    r = simular(s, "C")
    assert r["motivo"] == "sl"
    assert r["saida"] == 92.0        # min(92.5, 92.5) - 0.5
    assert r["bruto_pts"] == -8.5


def test_sl_com_gap_piora_a_partir_do_preco():
    # BUY SL 8 => nivel 92.5; o preco abre em 90.0: piora 1 tick de 90.0
    s = _sinal(path=[_p("10:00:00", 100.0, 100.0),
                     _p("10:01:00", 90.0, 90.1)])
    r = simular(s, "C")
    assert r["motivo"] == "sl"
    assert r["saida"] == 89.5        # min(90.0, 92.5) - 0.5
    assert r["bruto_pts"] == -11.0
    # SELL: entrada 99.5, SL 8 => nivel 107.5; gap para 110.0
    s = _sinal("SELL", path=[_p("10:00:00", 100.0, 100.0),
                             _p("10:01:00", 110.0, 110.0)])
    r = simular(s, "C")
    assert r["motivo"] == "sl"
    assert r["saida"] == 110.5       # max(110.0, 107.5) + 0.5
    assert r["bruto_pts"] == -11.0


def test_saida_pelo_lado_certo_do_book():
    # SELL sai no ask; entrada 99.5, TP 8 => 91.5
    s = _sinal("SELL", path=[_p("10:00:00", 100.0, 100.1),
                             _p("10:01:00", 91.0, 91.0)])
    r = simular(s, "C")
    assert r["motivo"] == "tp"
    assert r["saida"] == 91.5
    assert r["bruto_pts"] == 8.0


def test_fechamento_20_35_utc_tem_prioridade():
    # 17:35 BRT = 20:35 UTC; o fecho vence TP/SL no mesmo ponto
    s = _sinal(path=[_p("20:34:59", 100.0, 100.0),
                     _p("20:35:00", 150.0, 150.1)])
    r = simular(s, "C")
    assert r["motivo"] == "fechamento"
    assert r["saida"] == 150.0


def test_fechamento_e_em_america_sao_paulo_nao_em_utc():
    """10:00 BRT (13:00 UTC) NAO pode ser tratado como 17:35."""
    s = _sinal(path=[["2026-11-18T10:00:00-03:00", 100.0, 100.0],
                     ["2026-11-18T10:01:00-03:00", 100.1, 100.1]])
    assert simular(s, "A0")["motivo"] == "fim_dados"

    s2 = _sinal(path=[["2026-11-18T17:34:59-03:00", 100.0, 100.0],
                      ["2026-11-18T17:35:00-03:00", 100.1, 100.1]])
    assert simular(s2, "A0")["motivo"] == "fechamento"


def test_path_das_1730_brt_fecha_as_1735_brt():
    """Sinal das 17:30 BRT so fecha quando o path chega as 17:35 BRT."""
    antes = _sinal(path=[["2026-11-18T17:30:00-03:00", 100.0, 100.0],
                         ["2026-11-18T17:34:59-03:00", 100.0, 100.0]])
    assert simular(antes, "A0")["motivo"] == "fim_dados"

    depois = _sinal(path=[["2026-11-18T17:30:00-03:00", 100.0, 100.0],
                          ["2026-11-18T17:34:59-03:00", 100.0, 100.0],
                          ["2026-11-18T17:35:00-03:00", 100.0, 100.0]])
    assert simular(depois, "A0")["motivo"] == "fechamento"


def test_quando_brt_do_resultado_mostra_o_fuso():
    """O resultado mostra o horario de saida no fuso do pregao (nao em UTC)."""
    s = _sinal(path=[["2026-11-18T20:34:00+00:00", 100.0, 100.0],
                     ["2026-11-18T20:35:00+00:00", 100.0, 100.0]])
    r = simular(s, "A0")
    assert r["motivo"] == "fechamento"
    assert r["quando_brt"] == "2026-11-18T17:35:00-03:00"


def test_janela_brt_do_relatorio_usa_sao_paulo():
    from avaliar_shadow_sltp import _janela_brt

    janela = _janela_brt([_sinal(), {"ts": "2026-11-18T20:35:00+00:00"}])
    assert janela == ("2026-11-18T07:00:00-03:00",
                      "2026-11-18T17:35:00-03:00")


def test_liquido_desconta_slippage_e_custo():
    assert abs(liquido_pts(8.0, 0.0) - (8.0 - CUSTO_PTS)) < 1e-9
    assert abs(liquido_pts(8.0, 0.5) - (8.0 - 1.0 - CUSTO_PTS)) < 1e-9
    assert abs(CUSTO_PTS - 0.12) < 1e-9


# ------------------------------------------------------------ estatistica ---
def test_bootstrap_por_dia_e_reproduzivel():
    diffs = {"2026-11-17": [1.0, 2.0], "2026-11-18": [3.0],
             "2026-11-19": [0.5, 0.5, 0.5]}
    a = bootstrap_por_dia(diffs)
    b = bootstrap_por_dia(diffs)
    assert a == b
    assert a["media"] == sum(sum(v) for v in diffs.values()) / 6
    assert a["li"] <= a["media"] <= a["ls"]
    assert a["n_dias"] == 3


def test_p_unilateral_negativo_da_p_alto():
    assert p_unilateral({"d1": [-5.0, -4.0], "d2": [-6.0]}) > 0.5


def test_holm_ordena_e_limita():
    ajustado = holm({"B": 0.01, "C": 0.04, "D": 0.03})
    assert ajustado["B"] == 0.03          # 3 * 0.01
    assert ajustado["D"] == 0.06          # 2 * 0.03
    assert ajustado["C"] == 0.06          # max(anterior, 1 * 0.04)
    assert all(0 <= p <= 1 for p in ajustado.values())


def test_status_coleta_congelado():
    assert status_coleta(199, 15) == "coletando"
    assert status_coleta(200, 14) == "coletando"
    assert status_coleta(200, 15) == "decidir"
    assert status_coleta(10, 39) == "coletando"
    assert status_coleta(10, 40) == "inconclusivo"


# ------------------------------------------------------------------ avaliar -
def test_avaliar_usa_so_os_operados_na_decisao():
    sinais = [_sinal(path=[_p("10:00:00", 100.0, 100.0),
                           _p("10:01:00", 105.0, 105.1)], operado=True),
              _sinal(path=[_p("10:00:00", 100.0, 100.0),
                           _p("10:01:00", 90.0, 90.1)], operado=False)]
    r = avaliar(sinais)
    assert r["n_pareados"] == 1
    assert r["resumo"]["A0"]["n"] == 1
    assert r["status_coleta"] == "coletando"
    assert r["promovidas"] == []


def test_nao_promove_sem_os_200_sinais():
    sinais = []
    for i in range(20):
        dia = f"2026-11-{10 + i:02d}"
        sinais.append(_sinal(dia=dia, path=[_p("10:00:00", 100.0, 100.0),
                                            _p("10:01:00", 120.0, 120.1)]))
    r = avaliar(sinais)
    assert r["n_pareados"] == 20
    assert r["n_pregoes"] == 20
    assert r["status_coleta"] == "coletando"
    assert r["promovidas"] == []


# ------------------------------------------------------------------- dados --
def test_carregar_jsonl_e_json():
    with tempfile.TemporaryDirectory() as d:
        p1 = os.path.join(d, "a.jsonl")
        with open(p1, "w", encoding="utf-8") as f:
            f.write(json.dumps(_sinal()) + "\n" + json.dumps(_sinal("SELL")) + "\n")
        assert len(carregar(p1)) == 2
        p2 = os.path.join(d, "b.json")
        with open(p2, "w", encoding="utf-8") as f:
            json.dump([_sinal()], f)
        assert len(carregar(p2)) == 1


def test_tp_zero_significa_sem_tp():
    """A0 de producao tem TP=0 (saida dinamica): nao pode virar TP de 0 pt."""
    s = _sinal(sl=8.0, tp=0.0, path=[_p("10:00:00", 100.0, 100.0),
                                      _p("10:01:00", 101.5, 101.6),
                                      _p("10:02:00", 103.0, 103.1)])
    r = simular(s, "A0")
    assert r["motivo"] == "fim_dados"
    assert r["saida"] == 103.0


# ------------------------------------------------------------ calibracao ---
def test_calibracao_ok_quando_sim_e_real_proximos():
    s = _sinal(path=[_p("10:00:00", 100.0, 100.0),
                     _p("10:01:00", 109.0, 109.1)])
    s["ticket"] = 111
    sim = simular(s, "A0")["bruto_pts"] - 2 * 0.5 - CUSTO_PTS
    r = avaliar([s], reais={"111": sim})
    assert r["calibracao"]["n"] == 1
    assert abs(r["calibracao"]["media"]) < 1e-9
    assert r["calibracao"]["ok"] is True


def test_calibracao_invalida_quando_desvio_passa_de_meio_ponto():
    s = _sinal(path=[_p("10:00:00", 100.0, 100.0),
                     _p("10:01:00", 109.0, 109.1)])
    s["ticket"] = 222
    r = avaliar([s], reais={"222": 0.0})   # sim pos, real zero => desvio grande
    assert r["calibracao"]["ok"] is False
    assert "invalido" in r["calibracao"]["motivo"]
    assert r["promovidas"] == []


def test_sem_dados_reais_nao_valida_simulador():
    s = _sinal(path=[_p("10:00:00", 100.0, 100.0)])
    r = avaliar([s])
    assert r["calibracao"]["ok"] is False
    assert r["calibracao"]["n"] == 0


def test_carregar_reais_json_e_jsonl():
    from avaliar_shadow_sltp import _carregar_reais
    with tempfile.TemporaryDirectory() as d:
        p1 = os.path.join(d, "r.json")
        with open(p1, "w", encoding="utf-8") as f:
            json.dump({"111": 1.5, "222": -2.0}, f)
        assert _carregar_reais(p1) == {"111": 1.5, "222": -2.0}
        p2 = os.path.join(d, "r.jsonl")
        with open(p2, "w", encoding="utf-8") as f:
            f.write('{"ticket": 333, "pnl_pts": 4.0}\n')
        assert _carregar_reais(p2) == {"333": 4.0}


def test_criterio_absoluto_entra_na_promocao():
    """200 sinais/15 dias: B vence A0 e tem IC absoluto > 0 => promove."""
    sinais = []
    for i in range(200):
        dia = f"2026-11-{10 + (i % 15):02d}"
        path = [_p("10:00:00", 100.0, 100.0),
                _p("10:01:00", 107.0, 107.1),   # B (atr=2) faz TP 6
                _p("10:02:00", 99.0, 99.1)]     # A0 (tp=0) sai no fim
        s = _sinal(dia=dia, sl=8.0, tp=0.0, atr=2.0, path=path)
        s["ticket"] = i
        sinais.append(s)
    sim_a0 = -2.62  # entrada 100.5, saida 99.0 (-1.5), menos 1.12 de custos
    reais = {str(i): sim_a0 for i in range(200)}
    r = avaliar(sinais, reais=reais)
    assert r["status_coleta"] == "decidir"
    assert r["calibracao"]["ok"] is True
    assert r["resumo"]["B"]["absoluto"]["li"] > 0
    assert r["resumo"]["B"]["diff_vs_A0"]["media"] >= 0.5
    assert r["resumo"]["B"]["promover"] is True
    assert "B" in r["promovidas"]
    # C/D empatam com A0 no path (sem TP): nao promovem
    assert r["resumo"]["C"]["promover"] is False


# ------------------------------------------------------- congelamento hash ---
def test_hash_do_avaliador_congelado_no_roadmap():
    """Mudar o avaliador depois do pre-registro invalida a coleta."""
    script = os.path.join(BASE, "avaliar_shadow_sltp.py")
    with open(script, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    roadmap = os.path.join(BASE, "ROADMAP_MONSTRO_OFICIAL_UNIFICADO.md")
    with open(roadmap, encoding="utf-8") as f:
        texto = f.read()
    inicio = texto.index("### 23.54.3")
    fim = texto.index("### 23.54.4", inicio)
    secao = texto[inicio:fim]
    assert f"`{sha}`" in secao, (
        "SHA-256 do avaliador mudou; atualizar o ROADMAP invalida a coleta "
        f"(hash atual: {sha})")


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
