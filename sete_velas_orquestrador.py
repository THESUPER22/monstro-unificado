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
# ---- Gestao de posicao (TP parcial 1:1 + breakeven) ----
LOTE_TP1_DEFAULT = 3.0      # contratos realizados no TP1; restante segue para o alvo final
VARIANTES_BASE = {
    7: dict(entrada=10.75, sl=SL_DEFAULT, tp=TP_DEFAULT),
    9: dict(entrada=11.25, sl=SL_DEFAULT, tp=TP_DEFAULT),
}
STATE_PATH = r'C:\AIOFEN\logs\sete_velas_state.json'
TRADES_PATH = r'C:\AIOFEN\logs\sete_velas_trades.csv'


def _carregar_cfg():
    """Flags de ativacao por variante vindas do config.json (V7/V9)."""
    p = _parametros_sv()
    return {
        7: bool(p.get('V7_1045_ATIVO', True)),
        9: bool(p.get('V9_1115_ATIVO', True)),
    }


def _parametros_sv():
    """Dict completo da secao sete_velas do config.json (parametros unificados)."""
    try:
        with open(r'C:\AIOFEN\config.json', encoding='utf-8') as f:
            return json.load(f).get('sete_velas', {}) or {}
    except Exception:
        return {}


def _variantes():
    """VARIANTES dinamicas: entradas fixas (7->10:45, 9->11:15), SL/TP/lote do config."""
    p = _parametros_sv()
    sl = float(p.get('sl', SL_DEFAULT))
    tp = float(p.get('tp', TP_DEFAULT))
    lote = float(p.get('lote', LOTE))
    return {
        7: dict(entrada=10.75, sl=sl, tp=tp, lote=lote),
        9: dict(entrada=11.25, sl=sl, tp=tp, lote=lote),
    }


def _na_janela():
    p = _parametros_sv()
    ini = float(p.get('hora_inicio', JANELA_INICIO_HORA))
    fim = float(p.get('hora_fim', JANELA_FIM_HORA))
    a = _agora_brt()
    h = a.hour + a.minute / 60.0
    return ini <= h < fim


def _agora_brt():
    return brt_agora()


def _dia_macro():
    """Trava macro: True se hoje a janela do 7 Velas deve ser blindada.
    - Payroll (Non-Farm Payrolls) : primeira sexta-feira do mes (automatico).
    - Datas manuais (FOMC/Copom)  : lista em config['sete_velas']['datas_bloqueadas'].
    Na hipotese de dia macro, nenhuma posicao eh aberta (VETADO_MACRO)."""
    try:
        p = _parametros_sv()
        datas_bloqueadas = p.get('datas_bloqueadas') or []
        a = _agora_brt()
        hoje = a.date()
        # Datas manuais (FOMC/Copom)
        if hoje in datas_bloqueadas:
            return True
        # Payroll: primeira sexta do mes (a.weekday()==4 -> sexta)
        if a.weekday() == 4:
            if a.day <= 7:
                return True
        return False
    except Exception:
        return False


def _gestao():
    """Dict de gerenciamento de posicao vindo do config (tp1/breakeven)."""
    p = _parametros_sv()
    sl = float(p.get('sl', SL_DEFAULT))
    tp = float(p.get('tp', TP_DEFAULT))
    return {
        'ativo': bool(p.get('gestao_tp_parcial', True)),
        'tp1_dist': float(p.get('tp1_dist', sl)),      # distancia do TP1 (1:1 = SL)
        'lote_tp1': float(p.get('lote_tp1', LOTE_TP1_DEFAULT)),
        'tp_final_dist': float(p.get('tp_final_dist', tp)),
        'rear_tp': bool(p.get('rear_tp', False)),
    }


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


class Orquestrador7Velas:
    def __init__(self, fn_executar, symbol='WDOU26', ativo=True):
        self.fn_executar = fn_executar
        self.symbol = symbol
        self.ativo = ativo
        self.ticket_aberto = None
        self.variante_entrando = None
        self.tp1_feito = False     # 3 CC ja realizados + BE aplicado?
        self._tp1_nivel = None
        self._be_nivel = None

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

    def _executar(self, action, sl, tp, lote, magic):
        try:
            ticket = self.fn_executar(
                action, lots=lote, symbol=self.symbol,
                sl=sl, tp=tp, magic_override=magic,
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
        cfg = _variantes()[variante]
        p = _parametros_sv()
        # Trava macro (Payroll/FOMC/Copom): nao abrir posicao, registrar veto
        if _dia_macro():
            print(f"[7VELAS V{variante}] DIA MACRO (Payroll/FOMC) -> VETADO_MACRO",
                  flush=True)
            return dict(
                dia=_agora_brt().date().isoformat(), variante=variante,
                hora_entrada=f"{int(cfg['entrada']):02d}:{int(round((cfg['entrada'] % 1) * 60)):02d}",
                sinal='NENHUM', ups=0, downs=0, cvd=0, cvd_confluente=False,
                entrada='', saida='', pts='', motivo='VETADO_MACRO',
                ticket=None)
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
            rec['ticket'] = None
            print(f"[7VELAS V{variante}] {sinal} {ups}-{downs} cvd={cvd:.1f} "
                  f"VETADO-CVD @ {preco:.1f}", flush=True)
            return rec
        # Executa
        ticket = self._executar(sinal, cfg['sl'], cfg['tp'], cfg['lote'], int(p.get('magic', MAGIC_SETE_VELAS)))
        rec['ticket'] = ticket
        if ticket is None:
            rec['motivo'] = 'ERRO_EXECUCAO'
        else:
            rec['saida'] = 'ABERTA'
            rec['pts'] = ''
            # Prepara gestao de TP parcial 1:1 + breakeven
            g = _gestao()
            self.tp1_feito = False
            self._tp1_nivel = (preco + g['tp1_dist']) if sinal == 'BUY' else (preco - g['tp1_dist'])
            self._be_nivel = preco
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
            self.tp1_feito = False

    def _fechar_parcial(self, ticket, volume_parcial, symbol=None, direction=None, magic=7007):
        """Fecha volume_parcial lotes de uma posicao aberta (TP parcial)."""
        try:
            pos = mt5.positions_get(ticket=ticket)
            if not pos:
                return False
            pos = pos[0]
            sym = pos.symbol
            tick = mt5.symbol_info_tick(sym)
            if tick is None:
                return False
            tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            preco = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": sym,
                "volume": float(volume_parcial),
                "type": tipo_fechamento,
                "position": int(pos.ticket),
                "price": preco,
                "deviation": 20,
                "magic": magic,
                "comment": f"7Velas TP1 parcial {volume_parcial}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(request)
            if res is None:
                print(f"[7VELAS] TP1 parcial order_send None: {mt5.last_error()}", flush=True)
                return False
            if res.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"[7VELAS] TP1 parcial rejeitada retcode={res.retcode} {res.comment}", flush=True)
                return False
            print(f"[7VELAS] TP1 parcial de {volume_parcial} CC realizado (ticket {ticket})", flush=True)
            return True
        except Exception as e:
            print(f"[7VELAS] ERRO TP1 parcial: {e}", flush=True)
            return False

    def _mover_sl(self, ticket, novo_sl):
        """Move o Stop Loss de uma posicao aberta (ex.: para breakeven)."""
        try:
            pos = mt5.positions_get(ticket=ticket)
            if not pos:
                return False
            pos = pos[0]
            sym_info = mt5.symbol_info(pos.symbol)
            if sym_info is None:
                return False
            novo_sl = round(float(novo_sl), 1)
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": pos.symbol,
                "position": int(pos.ticket),
                "sl": novo_sl,
                "tp": pos.tp,
                "deviation": 20,
                "magic": int(pos.magic),
            }
            res = mt5.order_send(request)
            if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"[7VELAS] mover SL falhou retcode={res.retcode if res else 'None'}", flush=True)
                return False
            print(f"[7VELAS] SL movido p/ breakeven {novo_sl} (ticket {ticket})", flush=True)
            return True
        except Exception as e:
            print(f"[7VELAS] ERRO mover SL: {e}", flush=True)
            return False

    def gerenciar_posicao(self):
        """TP parcial 1:1 + breakeven: ao atingir +tp1_dist, realiza lote_tp1 CC e
        move SL dos restantes (original tp1 + SL remanescente) para breakeven."""
        if self.ticket_aberto is None or self.tp1_feito:
            return
        g = _gestao()
        if not g['ativo']:
            return
        try:
            pos = mt5.positions_get(ticket=self.ticket_aberto)
            if not pos:
                # posicao ja fechada (SL/TP 10pts ou manual)
                self.ticket_aberto = None
                self.tp1_feito = False
                return
            pos = pos[0]
            preco_ent = float(pos.price_open)
            if pos.type == mt5.POSITION_TYPE_BUY:
                atingiu_tp1 = pos.price_current >= self._tp1_nivel
            else:
                atingiu_tp1 = pos.price_current <= self._tp1_nivel
            if not atingiu_tp1:
                return
            # Realiza parcial
            lote_total = float(pos.volume)
            lote_tp1 = min(g['lote_tp1'], lote_total)
            lote_restante = lote_total - lote_tp1
            if lote_restante <= 0:
                # Nada a manter: deixa o TP original do MT5 encerrar tudo
                self.tp1_feito = True
                return
            ok = self._fechar_parcial(self.ticket_aberto, lote_tp1, magic=int(pos.magic))
            if ok:
                # Move SL dos restantes para breakeven (entrada)
                self._mover_sl(self.ticket_aberto, preco_ent)
                self.tp1_feito = True
                print(f"[7VELAS] TP1 OK: {lote_tp1} CC realizados, BE nos {lote_restante:.2f} CC", flush=True)
        except Exception as e:
            print(f"[7VELAS] ERRO gerenciar_posicao: {e}", flush=True)

    def orquestrar(self):
        """Gancho chamado a cada iteração do loop principal do monstro."""
        if not self.ativo:
            return
        a = _agora_brt()
        if a.weekday() >= 5:
            return
        # Gestao de TP parcial 1:1 + breakeven (executa a cada iteracao)
        try:
            self.gerenciar_posicao()
        except Exception:
            pass
        if not _na_janela():
            # Fora da janela: fecha posição pendente e reseta
            if self.ticket_aberto is not None:
                self.fechar_janela()
            return
        # Dentro da janela: verificar se já executou alguma variante hoje
        vars_ativas = _carregar_cfg()
        state = _carregar_state()
        for variante in (7, 9):
            if not vars_ativas.get(variante, False):
                continue
            chave = f"{a.date().isoformat()}_{variante}"
            if chave in state and state[chave].get('ticket'):
                self.ticket_aberto = state[chave].get('ticket')
        # Gatilhos de entrada
        for variante, cfg in _variantes().items():
            if not vars_ativas.get(variante, False):
                continue
            chave = f"{a.date().isoformat()}_{variante}"
            h = cfg['entrada']
            hora_entrada_dt = a.replace(hour=int(h), minute=int(round((h % 1) * 60)), second=0, microsecond=0)
            if a >= hora_entrada_dt and chave not in state:
                self.variante_entrando = variante
                rec = self.avaliar(variante)
                # Idempotencia: registra trade uma unica vez e grava state em
                # QUALQUER resultado (executado, vetado CVD ou erro)
                if rec is None:
                    rec = dict(dia=a.date().isoformat(), variante=variante,
                               hora_entrada=cfg['entrada'], sinal='', ups=0, downs=0,
                               cvd=0, cvd_confluente=False, entrada=0,
                               saida='', pts='', motivo='SEM_DADOS')
                self._registrar_trade(rec)
                state[chave] = {
                    'ticket': rec.get('ticket'),
                    'sinal': rec.get('sinal', ''), 'entrada': rec.get('entrada', 0),
                    'saida': rec.get('saida', ''), 'pts': rec.get('pts', ''),
                    'motivo': rec.get('motivo', '')}
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