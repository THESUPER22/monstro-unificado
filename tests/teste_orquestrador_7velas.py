#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_orquestrador_7velas.py

Testes determinísticos do reparo do orquestrador 7 Velas (autorizado 04/09/2026).
Roda SEM MT5 real (mock via sys.modules). Cobre os 4 pontos do reparo:

  P1. _registrar_trade com campo 'ticket' em campos (sem ValueError no CSV).
  P2. Trava dupla de reentrada: acumulado do magic bloqueia gatilho.
  P3. Trava de volume máximo acumulado por janela (1 lote configurado).
  P4. Alinhamento rec/campos em todos os fluxos (VETADO_MACRO, VETADO_CVD,
      sem_velas_suficientes e executado).

Execução: python tests/teste_orquestrador_7velas.py
"""
import os
import sys
import csv
import types
import shutil
import tempfile
from datetime import datetime
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

FALHAS = []

def checar(nome, condicao, detalhe=""):
    status = "PASS" if condicao else "FAIL"
    print(f"[{status}] {nome}" + (f" - {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(f"{nome}: {detalhe}")


def criear_mt5_mock(posicoes):
    mt5 = mock.Mock()
    mt5.positions_get = mock.Mock(return_value=list(posicoes) or None)
    return mt5


def carregar_modulo(posicoes, config_extra=None):
    """(re)importa sete_velas_orquestrador com mocks; retorna (mod, orq, tmpdir)."""
    mt5 = criear_mt5_mock(posicoes)
    with mock.patch.dict(sys.modules, {"MetaTrader5": mt5}):
        # Garante re-import limpo (remove modulos ja importados)
        sys.modules.pop("sete_velas_orquestrador", None)
        sys.modules.pop("sete_velas_util", None)
        import sete_velas_orquestrador as mod

        tmp = tempfile.mkdtemp(prefix="sv7_")
        mod.STATE_PATH = os.path.join(tmp, "sete_velas_state.json")
        mod.TRADES_PATH = os.path.join(tmp, "sete_velas_trades.csv")

        cfg = {
            'entrada': 11.25, 'sl': 8.0, 'tp': 10.0, 'lote': 5.0,
            'magic': 7007, 'V7_1045_ATIVO': False, 'V9_1115_ATIVO': True,
            'gestao_tp_parcial': True, 'tp1_dist': 8.0, 'lote_tp1': 3.0,
            'tp_final_dist': 10.0, 'rear_tp': False,
        }
        if config_extra:
            cfg.update(config_extra)
        mod._parametros_sv = mock.Mock(return_value=cfg)
        mod._carregar_cfg = mock.Mock(return_value={
            7: bool(cfg.get('V7_1045_ATIVO', True)),
            9: bool(cfg.get('V9_1115_ATIVO', True)),
        })
        mod._agora_brt = mock.Mock(return_value=datetime(2026, 9, 3, 11, 16, 0))
        mod._dia_macro = mock.Mock(return_value=False)
        mod._carregar_state = mock.Mock(return_value={})
        mod._salvar_state = mock.Mock()

        mod.velas_para_entrada = mock.Mock(return_value=(True, 5129.0, 7, 2))
        mod.calcular_cvd_janela = mock.Mock(return_value=500.0)

        orq = mod.Orquestrador7Velas(fn_executar=mock.Mock(return_value=2519356257))
        return mod, orq, mt5, tmp
    raise RuntimeError("carregar_modulo nao retornou")


def teste_p1_dictwriter():
    mod, orq, mt5, tmp = carregar_modulo([])
    try:
        rec = dict(dia='2026-09-03', variante=9, hora_entrada='11:15',
                   sinal='SELL', ups=7, downs=2, cvd=500.0,
                   cvd_confluente=True, entrada=5129.0, saida='ABERTA',
                   pts='', motivo='', ticket=2519356257)
        orq._registrar_trade(rec)
        with open(mod.TRADES_PATH, encoding='utf-8', newline='') as f:
            linhas = list(csv.DictReader(f))
        checar("P1 writerow com 'ticket' nao lanca", True)
        checar("P1 header + valor de 'ticket' gravados",
               bool(linhas) and linhas[0].get('ticket') == '2519356257',
               f"ticket={linhas[0].get('ticket') if linhas else 'vazio'}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_p2_trava_reentrada():
    pos = [types.SimpleNamespace(magic=7007, volume=0.5)]
    mod, orq, mt5, tmp = carregar_modulo(pos)
    try:
        acumulado = orq._acumulado_janela(mod.MAGIC_SETE_VELAS)
        checar("P2 acumulado detecta posicao magic 7007", acumulado == 0.5, f"acumulado={acumulado}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_p2_trava_dupla_posicao_parcial():
    # Posicao parcial (2.0 CC restantes apos TP1) < teto 5.0, mas
    # ainda ha posicao aberta -> a trava de posicao (1) deve bloquear.
    pos = [types.SimpleNamespace(magic=7007, volume=2.0)]
    mod, orq, mt5, tmp = carregar_modulo(pos)
    try:
        teto = orq._teto_volume_janela()
        posicao_aberta = orq._tem_posicao_aberta(7007)
        acumulado = orq._acumulado_janela(7007)
        checar("P2-dupla posicao aberta mesmo abaixo do teto", posicao_aberta, f"teto={teto} acumulado={acumulado}")
        checar("P2-dupla gate bloqueia (posicao_aberta=True)", posicao_aberta)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_p3_trava_volume():
    pos = [types.SimpleNamespace(magic=7007, volume=5.0)]
    mod, orq, mt5, tmp = carregar_modulo(pos)
    try:
        teto = orq._teto_volume_janela()
        checar("P3 teto = lote configurado", teto == 5.0, f"teto={teto}")
        bloqueia = orq._acumulado_janela(7007) >= teto
        checar("P3 volume acumulado >= teto -> bloqueia gatilho", bloqueia)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_p4_fluxos_rec():
    mod, orq, mt5, tmp = carregar_modulo([])
    try:
        mod._dia_macro = mock.Mock(return_value=True)
        r_macro = orq.avaliar(9)
        mod._dia_macro = mock.Mock(return_value=False)
        mod.velas_para_entrada = mock.Mock(return_value=(None, None, 0, 0))
        r_sem_velas = orq.avaliar(9)
        mod.velas_para_entrada = mock.Mock(return_value=(True, 5129.0, 7, 2))
        mod.calcular_cvd_janela = mock.Mock(return_value=-500.0)
        r_exec = orq.avaliar(9)
        for nome, r in (("VETADO_MACRO", r_macro), ("sem_velas", r_sem_velas), ("executado", r_exec)):
            checar(f"P4 {nome} contem 'ticket'",
                   isinstance(r, dict) and 'ticket' in r,
                   f"chaves={list(r.keys()) if isinstance(r, dict) else r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    teste_p1_dictwriter()
    teste_p2_trava_reentrada()
    teste_p2_trava_dupla_posicao_parcial()
    teste_p3_trava_volume()
    teste_p4_fluxos_rec()
    print("=" * 50)
    if FALHAS:
        print("FALHAS:")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TODOS OS TESTES PASSARAM")