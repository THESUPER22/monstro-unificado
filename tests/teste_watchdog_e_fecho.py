#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_watchdog_e_fecho.py

Testes deterministicos dos Patches A + B (v22.2-protected), autorizados em
05/09/2026 pelo Mestre para aplicacao no feriado de 07/09/2026.
Roda SEM MT5 real (mock via sys.modules), no padrao de teste_orquestrador_7velas.

  PA1. watchdog_dll_decidir: tick estagnado >10s dispara durante o expediente.
  PA2. watchdog_dll_decidir: fora do expediente nunca dispara.
  PA3. executar_resgate_dll: tick congelado -> hard_reset_mt5 acionado + reset.
  PA4. executar_resgate_dll: tick recente -> nenhum resgate.
  PA5. horario_expediente: janela HORARIO_PREGAO..HORARIO_AFTER respeitada.
  PB1. varrear_deal_fecho: DEAL_ENTRY_OUT atrasado e detectado.
  PB2. rechecagem_fecho_sincrona: deal confirmado na 2a tentativa captura PnL.
  PB3. rechecagem_fecho_sincrona: nunca confirma -> False, sem registro.

Execucao: python tests/teste_watchdog_e_fecho.py
"""
import os
import sys
from datetime import time as dtime
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

FALHAS = []


def checar(nome, condicao, detalhe=""):
    status = "PASS" if condicao else "FAIL"
    print(f"[{status}] {nome}" + (f" - {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(f"{nome}: {detalhe}")


# ===== Importa o modulo com MetaTrader5 mockado (sem conexao) =====
mt5_obj = mock.Mock()
mt5_obj.DEAL_ENTRY_OUT = 5  # constante simplificada p/ teste
with mock.patch.dict(sys.modules, {"MetaTrader5": mt5_obj}):
    import monstro_unificado_v22 as mod
    mod.mt5 = mt5_obj


def deal_fake(ticket, profit, entry=None):
    if entry is None:
        entry = mod.mt5.DEAL_ENTRY_OUT
    return mock.Mock(position_id=ticket, entry=entry, profit=profit,
                     __class__=mock.Mock)


def teste_pa1_dispara_em_expediente():
    r = mod.watchdog_dll_decidir(agora=100.0, ultimo_tick=80.0,
                                 em_expediente=True, timeout=10.0)
    checar("PA1 tick estagnado >10s em expediente dispara", r is True, f"got={r}")


def teste_pa2_fora_do_expediente():
    r = mod.watchdog_dll_decidir(agora=100.0, ultimo_tick=80.0,
                                 em_expediente=False, timeout=10.0)
    checar("PA2 fora do expediente nunca dispara", r is False, f"got={r}")
    r2 = mod.watchdog_dll_decidir(agora=100.0, ultimo_tick=99.5,
                                  em_expediente=True, timeout=10.0)
    checar("PA2 tick recente nao dispara", r2 is False, f"got={r2}")


def teste_pa3_resgate_acionado():
    with mock.patch.object(mod, "horario_expediente", return_value=True), \
         mock.patch.object(mod, "hard_reset_mt5", return_value=True) as hr:
        estado = {"ultimo_tick": 80.0}
        ativou = mod.executar_resgate_dll(estado, agora=100.0)
        checar("PA3 resgate acionado com tick congelado", ativou is True,
               f"got={ativou}")
        checar("PA3 hard_reset_mt5 chamado", hr.called, f"n={hr.call_count}")
        checar("PA3 estado resetado (evita cascata)",
               estado["ultimo_tick"] == 100.0,
               f"ultimo_tick={estado.get('ultimo_tick')}")


def teste_pa4_sem_resgate():
    with mock.patch.object(mod, "horario_expediente", return_value=True), \
         mock.patch.object(mod, "hard_reset_mt5") as hr:
        estado = {"ultimo_tick": 95.0}
        ativou = mod.executar_resgate_dll(estado, agora=100.0)
        checar("PA4 tick recente nao aciona resgate", ativou is False,
               f"got={ativou}")
        checar("PA4 hard_reset_mt5 NAO chamado", not hr.called,
               f"n={hr.call_count}")


def teste_pa5_horario_expediente():
    casos = (
        ("antes do pregao", dtime(8, 59), False),
        ("abertura exata", dtime(9, 0), True),
        ("meio do dia", dtime(13, 24), True),
        ("encerramento exato", dtime(17, 40), True),
        ("apos o encerramento", dtime(17, 41), False),
    )
    for nome, hora, esperado in casos:
        r = mod.horario_expediente(hora)
        checar(f"PA5 {nome}", r is esperado, f"hora={hora} got={r}")


def teste_pb1_varredura_deal():
    deal = deal_fake(2520776665, profit=-25.0)
    mod.mt5.history_deals_get = mock.Mock(return_value=[deal])
    d = mod.varrear_deal_fecho(2520776665, janela=90)
    checar("PB1 DEAL_ENTRY_OUT atrasado detectado", d is deal,
           f"got={d}")
    mod.mt5.history_deals_get = mock.Mock(return_value=[])
    d2 = mod.varrear_deal_fecho(2520776665, janela=90)
    checar("PB1 sem deal -> None", d2 is None, f"got={d2}")


def teste_pb2_confirmacao_na_segunda_tentativa():
    deal = deal_fake(2520776665, profit=12.5)
    varredor = mock.Mock(side_effect=[None, deal])
    registrar = mock.Mock()
    ok = mod.rechecagem_fecho_sincrona(
        2520776665, varredor=varredor, registrar=registrar, intervalos=(0, 0))
    checar("PB2 re-checagem confirma na 2a tentativa", ok is True, f"got={ok}")
    checar("PB2 PnL registrado no deal atrasado",
           registrar.call_args == mock.call(2520776665, deal),
           f"calls={registrar.call_args_list}")


def teste_pb3_nunca_confirma():
    varredor = mock.Mock(return_value=None)
    registrar = mock.Mock()
    ok = mod.rechecagem_fecho_sincrona(
        2520776665, varredor=varredor, registrar=registrar, intervalos=(0, 0))
    checar("PB3 sem confirmacao -> False", ok is False, f"got={ok}")
    checar("PB3 registrar nao chamado", not registrar.called,
           f"n={registrar.call_count}")


if __name__ == "__main__":
    teste_pa1_dispara_em_expediente()
    teste_pa2_fora_do_expediente()
    teste_pa3_resgate_acionado()
    teste_pa4_sem_resgate()
    teste_pa5_horario_expediente()
    teste_pb1_varredura_deal()
    teste_pb2_confirmacao_na_segunda_tentativa()
    teste_pb3_nunca_confirma()
    print("=" * 50)
    if FALHAS:
        print("FALHAS:")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TODOS OS TESTES PASSARAM")