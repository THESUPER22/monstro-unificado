"""
Orquestrador da Estratégia das Sete Velas (WDO) — modo de produção.
Integra-se ao monstro_unificado_v22.py via callback de execução de ordens.

Fluxo:
  1. A cada iteração do loop principal do monstro, chama orquestrar().
  2. Se na janela 09:00–11:30 BRT e SETE_VELAS_ATIVO, avalia o sinal
     na hora da variante (7→10:45, 9→11:15) usando majority M15 + CVD.
  3. Se confluente, executa ordem com magic=7007, lote=5, SL/TP fixos.
  4. No fechamento da janela (11:30) fecha posição se ainda aberta.
  5. Estado idempotente persistido em logs/sete_velas_state.json.
"""
import json, os, time, csv
from datetime import datetime, timedelta

import MetaTrader5 as mt5

from sete_velas_util import (
    brt_agora, epoch_para_brt, brt_para_epoch,
    velas_para_entrada, calcular_cvd_janela, majority,
)

MAGIC_SETE_VELAS = 7007
JANELA_INICIO_HORA = 9.0
JANELA_FIM_HORA = 11.5
LOTE = 5.0
SL_DEFAULT = 8.0
TP_DEFAULT = 10.0
VARIANTES = {
    7: dict(entrada=10.75, sl=SL_DEFAULT, tp=TP_DEFAULT),
    9: dict(entrada=11.25, sl=SL_DEFAULT, tp=TP_DEFAULT),
}
STATE_PATH = r'C:\AIOFEN\logs\sete_velas_state.json'
TRADES_PATH = r'C:\AIOFEN\logs\sete_velas_trades.csv'


def _agora_brt():
    return brt_agora()


def _carregar_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _salvar_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def _chave_dia(variante):
    return f"{_agora_brt().date().isoformat()}_{variante}"


def _na_janela():
    a = _agora_brt()
    h = a.hour + a.minute / 60.0
    return JANELA_INICIO_HORA <= h < JANELA_FIM_HORA


class Orquestrador7Velas:
    def __init__(self, fn_executar, symbol='WDOU26', ativo=True):
        self.fn_executar = fn_executar
        self.symbol = symbol
        self.ativo = ativo
        self.ticket_aberto = None
        self.variante_entrando = None

    def _registrar_trade(self, rec):
        os.makedirs(os.path.dirname(TRADES_PATH), exist_ok=True)
        campos = ['dia', 'variante', 'hora_entrada', 'sinal', 'ups', 'downs',
                  'cvd', 'cvd_confluente', 'entrada', 'saida', 'pts', 'motivo']
        file_exists = os.path.exists(TRADES_PATH)
        with open(TRADES_PATH, 'a', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=campos)
            if not file_exists:
                w.writeheader()
            w.writerow(rec)

    def _executar(self, action, sl, tp):
        try:
            ticket = self.fn_executar(
                action, lots=LOTE, symbol=self.symbol,
                sl=sl, tp=tp, magic_override=MAGIC_SETE_VELAS,
                comment=f"7Velas V{self.variante_entrando}")
        except Exception as e:
            print(f"[7VELAS] ERRO ao executar {action}: {e}", flush=True)
            return None
        if ticket is None:
            return None
        self.ticket_aberto = ticket
        return ticket

    def avaliar(self, variante):
        """Avalia sinal e executa se confluente. Retorna dict de resultado."""
        cfg = VARIANTES[variante]
        entrada_dt = _agora_brt().replace(hour=int(cfg['entrada']), minute=int(round((cfg['entrada'] % 1) * 60)), second=0, microsecond=0)
        prox, preco, ups, downs = velas_para_entrada(self.symbol, variante, entrada_dt)
        if prox is None or preco is None:
            return dict(ok=False, motivo='sem_velas_suficientes')
        cvd = calcular_cvd_janela(self.symbol, _agora_brt().replace(hour=9, minute=0), entrada_dt)
        cvd_confluente = (ups > downs and cvd > 0) or (downs > ups and cvd < 0)
        sinal = 'BUY' if ups > downs else 'SELL'
        rec = dict(
            dia=_agora_brt().date().isoformat(),
            variante=variante,
            hora_entrada=f"{int(cfg['entrada']):02d}:{int(round((cfg['entrada'] % 1) * 60)):02d}",
            sinal=sinal, ups=ups, downs=downs,
            cvd=round(cvd, 1), cvd_confluente=cvd_confluente,
            entrada=round(preco, 3), saida='', pts='', motivo='')
        if not cvd_confluente:
            rec['motivo'] = 'VETADO_CVD'
            self._registrar_trade(rec)
            print(f"[7VELAS V{variante}] {sinal} {ups}-{downs} cvd={cvd:.1f} "
                  f"VETADO-CVD @ {preco:.1f}", flush=True)
            return rec
        # Executa
        ticket = self._executar(sinal, cfg['sl'], cfg['tp'])
        if ticket is None:
            rec['motivo'] = 'ERRO_EXECUCAO'
        else:
            rec['saida'] = 'ABERTA'
            rec['pts'] = ''
        self._registrar_trade(rec)
        print(f"[7VELAS V{variante}] {sinal} {ups}-{downs} cvd={cvd:.1f} "
              f"CONF {cvd_confluente} @ {preco:.1f} ticket={ticket}", flush=True)
        return rec

    def fechar_janela(self):
        """Fecha posição da 7 Velas ao fim da janela (11:30)."""
        if self.ticket_aberto is not None:
            try:
                mt5.position_close(self.ticket_aberto)
                print(f"[7VELAS] Posição {self.ticket_aberto} fechada ao fim da janela", flush=True)
            except Exception as e:
                print(f"[7VELAS] ERRO ao fechar {self.ticket_aberto}: {e}", flush=True)
            self.ticket_aberto = None
            self.variante_entrando = None

    def orquestrar(self):
        """Gancho chamado a cada iteração do loop principal do monstro."""
        if not self.ativo:
            return
        a = _agora_brt()
        if a.weekday() >= 5:
            return
        if not _na_janela():
            # Fora da janela: fecha posição pendente e reseta
            if self.ticket_aberto is not None:
                self.fechar_janela()
            return
        # Dentro da janela: verificar se já executou alguma variante hoje
        state = _carregar_state()
        for variante in (7, 9):
            chave = f"{a.date().isoformat()}_{variante}"
            if chave in state and state[chave].get('ticket'):
                self.ticket_aberto = state[chave].get('ticket')
        # Gatilhos de entrada
        for variante, cfg in VARIANTES.items():
            chave = f"{a.date().isoformat()}_{variante}"
            h = cfg['entrada']
            hora_entrada_dt = a.replace(hour=int(h), minute=int(round((h % 1) * 60)), second=0, microsecond=0)
            if a >= hora_entrada_dt and chave not in state:
                self.variante_entrando = variante
                rec = self.avaliar(variante)
                if rec and rec.get('ticket'):
                    state[chave] = {
                        'ticket': rec.get('ticket'),
                        'sinal': rec['sinal'], 'entrada': rec['entrada'],
                        'saida': 'ABERTA', 'pts': ''}
                    _salvar_state(state)
        # Fim da janela: fecha tudo e reseta state
        h = a.hour + a.minute / 60.0
        if h >= JANELA_FIM_HORA and self.ticket_aberto is not None:
            self.fechar_janela()
            state = _carregar_state()
            for variante in (7, 9):
                chave = f"{a.date().isoformat()}_{variante}"
                if chave in state:
                    state[chave]['saida'] = 'FECHADA_JANELA'
            _salvar_state(state)
        elif h >= JANELA_FIM_HORA:
            # Garantir que todos os estados do dia estejam marcados como fechados
            state = _carregar_state()
            modificou = False
            for chave, val in state.items():
                if chave.startswith(a.date().isoformat()) and val.get('saida') in ('ABERTA', ''):
                    val['saida'] = 'FECHADA_JANELA'
                    modificou = True
            if modificou:
                _salvar_state(state)