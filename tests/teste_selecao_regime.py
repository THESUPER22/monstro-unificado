#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_selecao_regime.py  (Sessao 19)

Testes do modulo selecao_estrategia_regime.py (design, sem MT5).
Roda direto (python tests\teste_selecao_regime.py) ou via pytest.
"""
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from selecao_estrategia_regime import (  # noqa: E402
    MODOS_VALIDOS, SelecionadorRegime, RastreadorPerformanceRegime,
    validar_config, PERFIL_POR_REGIME,
)

FALHAS = []


def checar(nome, condicao, detalhe=""):
    status = "PASS" if condicao else "FAIL"
    print(f"[{status}] {nome}" + (f" - {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(f"{nome}: {detalhe}")


def test_config_valida():
    sel = SelecionadorRegime()  # dispara validar_config() no __init__
    checar("Config valida (6 modos, sem typos)", True)


def test_todos_modos_tem_perfil():
    sel = SelecionadorRegime()
    ok = all(m in PERFIL_POR_REGIME for m in MODOS_VALIDOS)
    checar("Todos os modos tem perfil definido", ok)


def test_defesa_e_aguardando_bloqueiam():
    sel = SelecionadorRegime()
    checar("DEFESA nao opera", not sel.permitido_operar("DEFESA"))
    checar("AGUARDANDO nao opera", not sel.permitido_operar("AGUARDANDO"))
    checar("NORMAL opera", sel.permitido_operar("NORMAL"))


def test_lateral_foca_mean_reversion():
    sel = SelecionadorRegime()
    ativas = sel.estrategias_ativas("LATERAL")
    checar("LATERAL tem williams_r", "williams_r" in ativas)
    checar("LATERAL tem rsi_mean_reversion", "rsi_mean_reversion" in ativas)
    checar("LATERAL NAO tem sniper_supermo", "sniper_supermo" not in ativas)
    checar("LATERAL desliga filtro_tendencia", not sel.filtro_bloqueia("filtro_tendencia", "LATERAL", 999, 1.0))


def test_explosao_foca_momentum():
    sel = SelecionadorRegime()
    ativas = sel.estrategias_ativas("EXPLOSAO")
    checar("EXPLOSAO tem sniper_supermo", "sniper_supermo" in ativas)
    checar("EXPLOSAO NAO tem williams_r", "williams_r" not in ativas)
    checar("EXPLOSAO NAO tem rsi_mean_reversion", "rsi_mean_reversion" not in ativas)


def test_parametros_por_regime():
    sel = SelecionadorRegime()
    p_defesa = sel.parametros("DEFESA", 1.0, 8.0, 0.0)
    checar("DEFESA zera volume", p_defesa["volume"] == 0.0)
    p_lateral = sel.parametros("LATERAL", 1.0, 8.0, 0.0)
    checar("LATERAL reduz volume 50%", p_lateral["volume"] == 0.5)
    p_explosao = sel.parametros("EXPLOSAO", 1.0, 8.0, 10.0)
    checar("EXPLOSAO aumenta volume 50%", p_explosao["volume"] == 1.5)
    checar("EXPLOSAO SL maior", p_explosao["sl"] == 9.6)


def test_filtro_ativado_por_peso():
    sel = SelecionadorRegime()
    # peso 1.0 (padrao): valor >= limiar -> bloqueia
    checar("Filtro padrao bloqueia acima do limiar", sel.filtro_bloqueia("filtro_entropia", "NORMAL", 3.0, 2.5))
    # peso 0.0 (desligado): nunca bloqueia
    checar("Filtro desligado nunca bloqueia", not sel.filtro_bloqueia("filtro_tendencia", "LATERAL", 0.1, 1.0))


def test_rastreador_win_rate():
    r = RastreadorPerformanceRegime()
    r.registrar_trade("LATERAL", "rsi_mean_reversion", 12.0)
    r.registrar_trade("LATERAL", "rsi_mean_reversion", -8.0)
    r.registrar_trade("LATERAL", "rsi_mean_reversion", 4.0)
    est = r.estatisticas_por_modo()
    lateral = est["LATERAL"]
    checar("win_rate = 2/3", abs(lateral["win_rate"] - 2 / 3) < 0.001, f"={lateral['win_rate']}")
    checar("avg_profit = 8/3", abs(lateral["avg_profit"] - 8 / 3) < 0.01, f"={lateral['avg_profit']}")
    checar("total = 8.0", lateral["total"] == 8.0, f"={lateral['total']}")


def test_rastreador_melhor_estrategia():
    r = RastreadorPerformanceRegime()
    r.registrar_trade("LATERAL", "rsi_mean_reversion", 1.0)
    r.registrar_trade("LATERAL", "williams_r", 5.0)
    melhores = r.melhor_estrategia_por_regime()
    checar("Melhor estrategia LATERAL = williams_r", melhores.get("LATERAL") == "williams_r")


def test_rastreador_persistencia():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        caminho = tmp.name
    try:
        r1 = RastreadorPerformanceRegime(caminho_json=caminho)
        r1.registrar_trade("NORMAL", "williams_r", 3.0)
        r2 = RastreadorPerformanceRegime(caminho_json=caminho)
        checar("Persistencia: trade recuperado", len(r2.trades) == 1 and r2.trades[0].lucro == 3.0)
    finally:
        os.remove(caminho)


def test_validar_config_rejeita_erro():
    config_errada = dict(PERFIL_POR_REGIME)
    config_errada["NORMAL"]["filtros"]["estrategia_que_nao_existe"] = 1.0
    try:
        validar_config(config_errada)
        checar("validar_config rejeita estrategia desconhecida", False)
    except ValueError:
        checar("validar_config rejeita estrategia desconhecida", True)


def main():
    print("=" * 60)
    print("TESTES SELECAO ESTRATEGIA POR REGIME (Sessao 19, sem MT5)")
    print("=" * 60)
    for fn in sorted(globals()):
        if fn.startswith("test_"):
            globals()[fn]()
    print("-" * 60)
    if FALHAS:
        print(f"RESULTADO: {len(FALHAS)} FALHA(S)")
        for f in FALHAS:
            print(f"  X {f}")
        sys.exit(1)
    print("RESULTADO: TODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    main()
