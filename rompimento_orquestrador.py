# -*- coding: utf-8 -*-
"""
Orquestrador Rompimento da Primeira Hora (WDO) - modo de producao.
Substitui a Estrategia das Sete Velas (removida em 10/09/2026) como Faixa 1
do monstro_unificado_v22.py.

Estrategia (paridade com backtest/backtest_rompimento_1hora.py, combo WDO$):
  - caixa 09:00-10:00 BRT (velas M5 da hora 9) -> hi/lo/rr(=hi-lo)
  - gatilho 10:00-11:00 (janela 60min): primeira vela M5 FECHADA que rompe o
    hi da caixa => BUY; low => SELL; fill = entrada a mercado no momento em
    que a vela gatilho fecha (backtest: abertura da vela gatilho - desvio
    documentado)
  - SL = extremidade oposta da caixa (sl_mode 'lo'), TP = tp_k * rr
  - EOD: posicao ainda aberta ao fim da sessao diurna = fechada a mercado em
    hora_eod (padrao 17:30 BRT). NAO usa barras noturnas (hora>=18).

Robustez (aprendizada com o feed do terminal XP nos dias 09-10/09/2026):
  - offset de fuso detectado por dia (histograma 9-17h nas M5 recentes);
  - trava de frescor: decisoes so com a ultima M5 a <= stale_max_min min;
  - registro idempotente por dia (logs/rompimento_state.json + CSV).

Hooks de teste: bars_fn/tick_fn permitem injetar dados determinísticos.

CLI (sem robô): referencia estatística sobre o historico.
  python rompimento_orquestrador.py --selftest [csv]
"""
import csv
import json
import os
import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5

# ---------------- CONFIG (padroes; sobrepostos por config.json) ----------------
CFG_PATH = r"C:\AIOFEN\config.json"
DEFAULT_CFG = dict(
    ativo=True, lote=5.0, sl_mode="lo", tp_k=1.5, janela_min=60,
    magic=7008, hora_inicio=9.0, hora_fim=11.0, hora_eod="17:30",
    stale_max_min=12, no_night_bars=True,
    # Ajuste do SL da Faixa 1 (correcao 5):
    # SL_efetivo = max(sl_piso, min(SL_da_caixa, sl_atr_factor * ATR14_da_manha)).
    # Dias calmos (ATR baixo) deixam de gerar SLs desproporcionais de 23-27 pts;
    # o piso anti-ruido evita stops por oscilacao de ticks.
    sl_atr_factor=2.5, sl_piso=8.0,
    # Sub-Trader do Corpo de 1H (item 6): entrada no rompimento do CORPO do
    # candle 09:00-10:00, saida nos PAVIOS. Fecha antes/Faixa 1 ira esperar.
    # sub_rr_min: filtro estrutural de R/R minimo na entrada (calibracao
    # backtest 264 pregoes, 29/09/2026). 1.0 => so opera R/R>=1:1.
    sub_ativo=True, sub_rr_min=1.0,
)

ROOT = r"C:\AIOFEN"
LOG_DIR = os.path.join(ROOT, "logs", "rompimento")
LOG_FILE = os.path.join(LOG_DIR, "rompimento.log")
STATE_JSON = os.path.join(LOG_DIR, "rompimento_state.json")
TRADES_CSV = os.path.join(LOG_DIR, "rompimento_trades.csv")
# D3 (05/10): ticket/modulo/lucro_rs allow the unified memory to resolve the real
# book snapshot (by ticket) and the reward in R$ (from the MT5 deals).
HEADER_TRADES = ["dia", "side", "entrada", "sl", "tp", "saida", "pts", "obs",
                 "ticket", "modulo", "lucro_rs"]

os.makedirs(LOG_DIR, exist_ok=True)

_SHIFT = 0  # offset de fuso (s) aplicado aos epochs das barras


def _carga_cfg():
    """Dict da secao 'rompimento' do config.json (parametros unificados)."""
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        return dict(DEFAULT_CFG, **(cfg.get("rompimento") or {}))
    except Exception:
        return dict(DEFAULT_CFG)


def log(msg):
    linha = "%s | %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass
    print(linha, flush=True)


def _dia_str(dt):
    return dt.date().isoformat()


def _hora_float(dt):
    return dt.hour + dt.minute / 60.0


# ---------------- FUSO / FRESCOR / BARRAS ----------------
def detectar_shift(mt5mod, symbol, n=3000):
    """Escolhe o deslocamento (s) que coloca mais M5 na sessao diurna 9-17h."""
    global _SHIFT
    rates = mt5mod.copy_rates_from_pos(symbol, mt5mod.TIMEFRAME_M5, 0, n)
    if rates is None or len(rates) < 300:
        return _SHIFT
    melhor = (_SHIFT, -1)
    for cand in (-25200, -21600, -18000, -14400, -10800, -7200, -3600, 0,
                 3600, 7200, 10800, 14400, 18000, 21600):
        cnt = 0
        for r in rates[-1500:]:
            dt = datetime.fromtimestamp(int(r["time"]) + cand)
            if 9 <= dt.hour <= 17 and dt.weekday() < 5:
                cnt += 1
        if cnt > melhor[1]:
            melhor = (cand, cnt)
    _SHIFT = melhor[0]
    return _SHIFT


_OFFSET_MEDICAO = None  # offset (s) do fuso-servidor usado so p/ MEDIR frescor


def _offset_medicao(mt5mod, symbol):
    """Deslocamento (s) que o servidor aplica aos epochs (ex.: XPMT5-DEMO grava a
    hora BRT como se fosse UTC => +10800). Detecta uma vez e cacheia.
    Normaliza APENAS a medida de frescor; nao altera as janelas de decisao
    ('_SHIFT' continua intocado = calibrado). Retorna 0 se nao conseguir medir."""
    global _OFFSET_MEDICAO
    if _OFFSET_MEDICAO is not None:
        return _OFFSET_MEDICAO
    _OFFSET_MEDICAO = 0
    try:
        rates = mt5mod.copy_rates_from_pos(symbol, mt5mod.TIMEFRAME_M5, 0, 3000)
        if rates is not None and len(rates) >= 300:
            melhor = (0, -1)
            for cand in (-25200, -21600, -18000, -14400, -10800, -7200, -3600, 0,
                         3600, 7200, 10800, 14400, 18000, 21600):
                cnt = 0
                for r in rates[-1500:]:
                    dt = datetime.fromtimestamp(int(r["time"]) + cand)
                    if 9 <= dt.hour <= 17 and dt.weekday() < 5:
                        cnt += 1
                if cnt > melhor[1]:
                    melhor = (cand, cnt)
            _OFFSET_MEDICAO = melhor[0]
    except Exception:
        pass
    return _OFFSET_MEDICAO


def dfasagem_min(mt5mod, symbol):
    """Defasagem (min) da ultima M5 em relacao a hora real. Remove o offset de
    fuso do servidor (senao o XPMT5-DEMO acusa ~180 min fixas em feed saudavel)."""
    r = mt5mod.copy_rates_from_pos(symbol, mt5mod.TIMEFRAME_M5, 0, 1)
    if r is None or len(r) == 0:
        return 10 ** 9
    return (time.time() - (int(r[0]["time"]) + _offset_medicao(mt5mod, symbol))) / 60.0


def barras_do_dia(mt5mod, symbol, hoje, no_night=True):
    """M5 do dia (interpretadas com offset), sem barras noturnas (hora>=18)."""
    rates = mt5mod.copy_rates_from_pos(symbol, mt5mod.TIMEFRAME_M5, 0, 1500)
    if rates is None:
        return []
    out = []
    for r in rates:
        dt = datetime.fromtimestamp(int(r["time"]) + _SHIFT)
        if dt.date() != hoje:
            continue
        if no_night and dt.hour >= 18:
            continue
        out.append((dt, float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]), int(r["tick_volume"])))
    out.sort(key=lambda b: b[0])
    return out


def barras_fechadas(bars, agora):
    """Somente barras cuja vela ja fechou (barra + 5min <= agora)."""
    return [b for b in bars if b[0] + timedelta(minutes=5) <= agora]


# ---------------- ATR E NIVEL CRU DE 1H ----------------
def _atr14(bars, periodo=14):
    """ATR de Wilder sobre barras (dt,o,h,l,c,v). Retorna 0 se dados insuficientes."""
    trs = []
    prev_c = None
    for _dt, op, hi, lo, cl, _v in bars:
        if prev_c is None:
            prev_c = cl
            continue
        trs.append(max(hi - lo, abs(hi - prev_c), abs(lo - prev_c)))
        prev_c = cl
    if not trs:
        return 0.0
    p = min(periodo, len(trs))
    atr = trs[0]
    for tr in trs[1:]:
        atr = ((p - 1) * atr + tr) / p
    return atr


def _nivel_corpo_pavio(candle):
    """Do candle 1H (dt,o,h,l,c,v) extrai os niveis do Sub-Trader:
    Corpo_Topo=max(abertura,fechamento), Corpo_Fundo=min(abertura,fechamento),
    Pavio_Topo=maxima, Pavio_Fundo=minima. Retorna dict ou None."""
    try:
        op, hi, lo, cl = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    except Exception:
        return None
    corpo_topo = max(op, cl)
    corpo_fundo = min(op, cl)
    pavio_topo = hi
    pavio_fundo = lo
    if pavio_topo <= pavio_fundo or corpo_topo <= corpo_fundo:
        return None
    return dict(corpo_topo=corpo_topo, corpo_fundo=corpo_fundo,
                pavio_topo=pavio_topo, pavio_fundo=pavio_fundo)


def _agrega_h1(bars9):
    """Agrega as M5 da hora 9 em um candle 1H (open 1a, high=max, low=min,
    close ultima, vol soma). Retorna tupla (dt,o,h,l,c,v) ou None.
    Exige as 12 M5 da hora (09:00-09:55) para o candle estar fechado."""
    if not bars9:
        return None
    horas = {b[0].minute for b in bars9}
    if len(horas) < 12:
        return None  # candle 1H ainda nao fechou
    o = bars9[0][1]
    h = max(b[2] for b in bars9)
    lo = min(b[3] for b in bars9)
    cl = bars9[-1][4]
    v = sum(b[5] for b in bars9)
    return (bars9[0][0].replace(minute=0, second=0), o, h, lo, cl, v)


# ---------------- NUCLEO (identico ao backtest) ----------------
def prep(bars):
    """Caixa 09:00-10:00. Retorna dict(hi, lo, rr, mvol, bars, fim) ou None."""
    morning = [b for b in bars if b[0].hour == 9]
    if not morning:
        return None
    hi = max(b[2] for b in morning)
    lo = min(b[3] for b in morning)
    rr = hi - lo
    if rr <= 0:
        return None
    trigb = [b for b in bars if b[0].hour >= 10]
    if not trigb:
        return None
    fim = trigb[-1][0]
    return dict(hi=hi, lo=lo, rr=rr, mvol=sum(b[5] for b in morning),
                bars=trigb, fim=(fim.hour * 3600 + fim.minute * 60),
                atr=_atr14(morning))


def trig(t, window_min):
    """(side, idx, entry) na janela apos 10:00; None se nada rompeu."""
    bars = t["bars"]
    lim = 10 * 3600 + (window_min * 60 if window_min else t["fim"])
    for i, b in enumerate(bars):
        secs = b[0].hour * 3600 + b[0].minute * 60
        if secs > lim:
            break
        if b[2] >= t["hi"]:
            return "C", i, b[1]
        if b[3] <= t["lo"]:
            return "V", i, b[1]
    return None


def resolve(t, side, idx, e, sl_mode, tp_k, sl_atr_factor=0.0, sl_piso=0.0):
    """SL conferido antes do TP (intrabarra); EOD no ultimo bar da sessao.

    Aplica o MESMO ajuste da correcao 5 da producao:
    sl_dist_efetivo = max(sl_piso, min(SL_da_caixa, sl_atr_factor * ATR_manha)).
    Paridade backtest <> orquestrador."""
    bars = t["bars"]
    atr = float(t.get("atr") or 0.0)
    if side == "C":
        sl_lvl = {"mid": (t["hi"] + t["lo"]) / 2, "lo": t["lo"],
                  "lo_half": t["lo"] - 0.5 * t["rr"]}[sl_mode]
        sl_dist = e - sl_lvl
        tp = e + tp_k * t["rr"] if tp_k else None
    else:
        sms = {"mid": "mid", "lo": "hi", "lo_half": "hi_half"}[sl_mode]
        sl_lvl = {"mid": (t["hi"] + t["lo"]) / 2, "hi": t["hi"],
                  "hi_half": t["hi"] + 0.5 * t["rr"]}[sms]
        sl_dist = sl_lvl - e
        tp = e - tp_k * t["rr"] if tp_k else None
    sl_ef = sl_dist
    if atr > 0 and sl_atr_factor > 0:
        sl_ef = max(sl_piso, min(sl_dist, sl_atr_factor * atr))
    for b in bars[idx:]:
        if side == "C":
            if b[3] <= e - sl_ef:
                return -sl_ef, "SL"
            if tp is not None and b[2] >= tp:
                return tp - e, "TP"
        else:
            if b[2] >= e + sl_ef:
                return -sl_ef, "SL"
            if tp is not None and b[3] <= tp:
                return e - tp, "TP"
    fec = bars[-1][4]
    pts = (fec - e) if side == "C" else (e - fec)
    return pts, "EOD"


def prep_safe(bars):
    if not bars:
        return None
    try:
        t = prep(bars)
    except Exception:
        return None
    return t if t is not None and t["bars"] else None


# ---------------- PERSISTENCIA ----------------
def _carregar_state():
    if os.path.exists(STATE_JSON):
        try:
            with open(STATE_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _salvar_state(state):
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, STATE_JSON)


def _rewrite_csv_drop_day(p, header, dia, modulo=None):
    """Remove a linha do dia. Quando modulo e informado, so remove a linha do
    mesmo modulo (um sub NAO pode apagar o registro da Faixa 1 do mesmo dia)."""
    rows = []
    if os.path.exists(p) and os.path.getsize(p) > 0:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("dia") != dia:
                    rows.append(r)
                elif modulo and (r.get("modulo") or "faixa1") != modulo:
                    rows.append(r)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _registrar_trade(rec):
    _rewrite_csv_drop_day(TRADES_CSV, HEADER_TRADES, rec["dia"],
                          rec.get("modulo") or None)
    with open(TRADES_CSV, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER_TRADES)
        if os.path.getsize(TRADES_CSV) == 0:
            w.writeheader()
        w.writerow({c: rec.get(c, "") for c in HEADER_TRADES})


# ---------------- ORQUESTRADOR ----------------
class OrquestradorRompimento:
    def __init__(self, fn_executar, symbol="WDO$", ativo=True, mt5mod=None,
                 clock=None, bars_fn=None, tick_fn=None, fresco_fn=None,
                 mem_entrada=None, mem_saida=None):
        self.fn_executar = fn_executar
        self.symbol = symbol
        self.ativo = ativo
        self.cfg = _carga_cfg()
        self.mt5 = mt5mod or mt5
        try:
            detectar_shift(self.mt5, self.symbol)
        except Exception:
            pass  # sem dados suficientes -> _SHIFT permanece 0 (janela calibrada)
        self.clock = clock or (lambda: datetime.now())
        self.bars_fn = bars_fn   # (mt5mod, symbol, data) -> barras do dia
        self.tick_fn = tick_fn   # () -> preco ou None
        self.fresco_fn = fresco_fn  # () -> bool (override do frescor p/ teste)
        # Memoria unificada (05/10): injetados pelo monstro para evitar
        # dependencia circular entre os dois modulos.
        self.mem_entrada = mem_entrada  # (ticket, modulo, side) -> fixa snapshot
        self.mem_saida = mem_saida      # (ticket, lucro_rs, side, saida) -> grava

    def _mem_fixar(self, ticket, modulo, side):
        """D1: fixa o snapshot real do book no instante da entrada."""
        if self.mem_entrada is None or not ticket:
            return
        try:
            self.mem_entrada(ticket, self.symbol, modulo, side)
        except Exception as e:
            log("[ROMPIMENTO] MEM entrada falhou (%s): %s" % (ticket, e))

    def _mem_gravar(self, ticket, side, saida):
        """D1+D2+D3: grava a operacao com contexto real e reward em R$."""
        if self.mem_saida is None or not ticket:
            return
        try:
            self.mem_saida(ticket, self._lucro_real_rs(ticket), side, saida)
        except Exception as e:
            log("[ROMPIMENTO] MEM saida falhou (%s): %s" % (ticket, e))

    # -- helpers --
    def _pos_aberta(self, ticket):
        try:
            pos = self.mt5.positions_get(ticket=ticket)
            return pos[0] if pos else None
        except Exception:
            return None

    def _fresco(self):
        if self.fresco_fn is not None:
            return self.fresco_fn(), 0.0
        stale = dfasagem_min(self.mt5, self.symbol)
        return stale <= float(self.cfg["stale_max_min"]), stale

    def _exit_deal(self, ticket):
        try:
            deals = self.mt5.history_deals_get(position=ticket)
        except Exception:
            return None
        if not deals:
            return None
        outs = [d for d in deals if d.entry == self.mt5.DEAL_ENTRY_OUT]
        if not outs:
            return None
        return float(outs[-1].price)

    def _lucro_real_rs(self, ticket):
        """D2: resolve o resultado financeiro REAL em R$ a partir dos deals.

        O orquestrador so conhecia 'pts' (pontos de preco), que nao e compativel
        com a coluna 'reward' do historico_contexto_wdo.csv -- que o Core grava
        em R$. Misturar as duas escalas contaminava o alvo do treino. A fonte
        autoritativa e o proprio MT5 (profit + commission + swap dos deals de
        saida). Retorna None quando o deal ainda nao existe, para o chamador
        nao gravar um chute.
        """
        if not ticket:
            return None
        try:
            deals = self.mt5.history_deals_get(position=int(ticket))
        except Exception:
            return None
        if not deals:
            return None
        total = 0.0
        achou = False
        for d in deals:
            if d.entry != self.mt5.DEAL_ENTRY_OUT:
                continue
            achou = True
            total += float(getattr(d, "profit", 0.0) or 0.0)
            total += float(getattr(d, "commission", 0.0) or 0.0)
            total += float(getattr(d, "swap", 0.0) or 0.0)
        return round(total, 2) if achou else None

    def _fechar_market(self, ticket):
        """Fecha a posicao do rompimento por ordem inversa (TRADE_ACTION_DEAL).

        mt5.position_close NAO existe na API do MetaTrader5 Python (AttributeError
        registrado 31x entre 18-28/09/2026, o que deixava o estado em ABERTA). O
        fechamento correto envia um DEAL na direcao oposta apontando o ticket."""
        try:
            pos = self._pos_aberta(ticket)
            if pos is None:
                return True  # ja nao existe; deal de saida lancara a finalizacao
            tipo = (self.mt5.ORDER_TYPE_SELL if pos.type == self.mt5.POSITION_TYPE_BUY
                    else self.mt5.ORDER_TYPE_BUY)
            tick = self.mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                log("[ROMPIMENTO] sem tick para fechar %s" % ticket)
                return False
            preco = tick.bid if pos.type == self.mt5.POSITION_TYPE_BUY else tick.ask
            req = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "position": int(ticket),
                "symbol": pos.symbol,
                "volume": float(pos.volume),
                "type": tipo,
                "price": float(preco),
                "deviation": 20,
                "magic": int(self.cfg.get("magic") or 7008),
                "comment": "Rompimento1H close EOD",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            res = self.mt5.order_send(req)
            if res is None or res.retcode != self.mt5.TRADE_RETCODE_DONE:
                log("[ROMPIMENTO] ERRO ao fechar %s: retcode=%s %s" %
                    (ticket, None if res is None else res.retcode,
                     None if res is None else res.comment))
                return False
        except Exception as e:
            log("[ROMPIMENTO] ERRO ao fechar %s: %s" % (ticket, e))
            return False
        for _ in range(6):
            time.sleep(0.4)
            if self._exit_deal(ticket) is not None or self._pos_aberta(ticket) is None:
                return True
        return True

    # -- maquina --
    def orquestrar(self):
        if not self.ativo or not self.cfg.get("ativo"):
            return
        a = self.clock()
        if a.weekday() >= 5:
            return
        dia = _dia_str(a)
        h = _hora_float(a)
        if h < 10.0:
            return
        st = _carregar_state()
        if st.get("dia") and st.get("dia") != dia:
            # dia anterior: limpa o ciclo (ticket/saida/final) para liberar a
            # janela operacional do novo pregão (correção B - caso ABERTA presa)
            st = {}
        if st.get("dia") == dia and st.get("final"):
            return

        # ---- AGENDA do dia: niveis do candle 1H da manha (Sub-Trader) ----
        sub_cfg = st.get("sub") or {}
        if not sub_cfg.get("final") and not st.get("ticket"):
            self._sub_gerenciar(st, a, dia)

        # ---- fase gatilho (10:00-11:06): sem posicao, pode abrir ----
        # (apenas se o Sub-Trader NAO estiver pendente/bloqueando;
        # se ja FINALIZOU, o gatilho da Faixa 1 fica liberado imediatamente)
        sub = st.get("sub") or {}
        if sub.get("ticket") and not sub.get("final"):
            return  # sub aberto: bloqueia Faixa 1
        self._fase_gatilho(st, a, dia)

        # ---- gestao de posicao: SL/TP no servidor; EOD fecha a mercado ----
        st = _carregar_state()
        if not st.get("ticket"):
            return
        pos = self._pos_aberta(st["ticket"])
        if pos is None:
            exit_p = self._exit_deal(st["ticket"])
            if exit_p is None:
                if self._hora_eod_excedida(a):
                    st["final"] = True
                    st["saida"] = "FECHADA"
                    st["pts"] = ""
                    st["obs"] = "fechamento sem preco de saida disponivel"
                    self._grava_final(st)
                    _salvar_state(st)
                else:
                    log("[ROMPIMENTO] aguardando confirmacao de fechamento (ticket %s)" % st["ticket"])
                return
            self._finaliza(st, exit_p, self._classifica_saida(st, exit_p), "posicao fechada no servidor")
            return
        if self._hora_eod_excedida(a):
            if self._fechar_market(st["ticket"]):
                exit_p = self._exit_deal(st["ticket"])
                if exit_p is None:
                    exit_p = self._coleta_price()
                if exit_p is None:
                    st["final"] = True
                    st["saida"] = "EOD"
                    st["pts"] = ""
                    st["obs"] = "EOD (preco de saida indisponivel)"
                    _salvar_state(st)
                    return
                self._finaliza(st, exit_p, "EOD", "EOD")

    def _sub_gerenciar(self, st, a, dia):
        """Sub-Trader do Corpo de 1H (item 6).

        Niveis no fechamento do candle 09:00-10:00 (ja em 10:00): entrada a
        mercado no rompimento do CORPO (Corpo_Topo para BUY / Corpo_Fundo para
        SELL), saida dinamica na direcao do PAVIO (BUY: TP=Pavio_Topo, SL=
        Pavio_Fundo; SELL: TP=Pavio_Fundo, SL=Pavio_Topo). Enquanto o sub-trade
        estiver aberto, a Faixa 1 Raiz fica BLOQUEADA; ao encerrar, libera o
        gatilho de rompimento do Pavio_Topo/Fundo imediatamente.
        """
        if not self.cfg.get("sub_ativo"):
            return
        sub = st.get("sub") or {}
        if sub.get("final"):
            return

        # ---- gestao de posicao do sub-trade (se aberto) ----
        if sub.get("ticket"):
            pos = self._pos_aberta(sub["ticket"])
            if pos is None:
                exit_p = self._exit_deal(sub["ticket"])
                if exit_p is None:
                    if self._hora_eod_excedida(a):
                        sub["final"] = True
                        sub["saida"] = "FECHADA"
                        sub["pts"] = ""
                        sub["obs"] = "sub fechado sem preco de saida"
                        st["sub"] = sub
                        _salvar_state(st)
                        self._grava_final_sub(st)
                    else:
                        log("[ROMPIMENTO] sub: aguardando confirmacao (ticket %s)" % sub["ticket"])
                    return
                dirv = 1 if sub["side"] == "C" else -1
                try:
                    sub["pts"] = round(dirv * (float(exit_p) - float(sub["entry"])), 3)
                except Exception:
                    sub["pts"] = ""
                sub["saida"] = self._classifica_saida(sub, exit_p) or "FECHADA"
                sub["obs"] = "sub fechado no servidor"
                sub["final"] = True
                st["sub"] = sub
                _salvar_state(st)
                self._grava_final_sub(st)
                log("[ROMPIMENTO] SUB %s saida=%s pts=%s (libera Faixa 1)" %
                    (sub["side"], sub["saida"], sub["pts"]))
                return
            if self._hora_eod_excedida(a):
                if self._fechar_market(sub["ticket"]):
                    exit_p = self._exit_deal(sub["ticket"])
                    if exit_p is None:
                        exit_p = self._coleta_price()
                    if exit_p is None:
                        sub["final"] = True; sub["saida"] = "EOD"; sub["pts"] = ""
                    else:
                        dirv = 1 if sub["side"] == "C" else -1
                        try:
                            sub["pts"] = round(dirv * (float(exit_p) - float(sub["entry"])), 3)
                        except Exception:
                            sub["pts"] = ""
                        sub["saida"] = "EOD"; sub["obs"] = "sub EOD"
                        sub["final"] = True
                    st["sub"] = sub
                    _salvar_state(st)
                    self._grava_final_sub(st)
                return
            return  # sub aberto: bloqueia Faixa 1

        # ---- entrada do sub-trade (rompimento do CORPO do candle 1H) ----
        if not self._fresco()[0]:
            return
        cand1h = None
        bars9 = [b for b in barras_fechadas(self._barras_dia(a.date()), a)
                 if b[0].hour == 9]
        h1 = _agrega_h1(bars9)
        if h1:
            cand1h = h1
        if cand1h is None:
            return
        niv = _nivel_corpo_pavio(cand1h)
        if niv is None:
            return
        # so opera no rompimento do corpo DENTRO da janela 10:00-11:06
        if self._janela_fechada(a):
            return
        tick = self.mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return
        preco_bid, preco_ask = float(tick.bid), float(tick.ask)
        # gatilho: preco rompe o Corpo (saiu do corpo na direcao do pavio)
        if preco_ask >= niv["corpo_topo"]:
            side, entry = "C", preco_ask
            tp_lvl, sl_lvl = niv["pavio_topo"], niv["pavio_fundo"]
        elif preco_bid <= niv["corpo_fundo"]:
            side, entry = "V", preco_bid
            tp_lvl, sl_lvl = niv["pavio_fundo"], niv["pavio_topo"]
        else:
            return
        # folga minima para o pavio (senao o sub-trade sofre com tick a tick)
        dist_tp = abs(tp_lvl - entry)
        dist_sl = abs(entry - sl_lvl)
        if dist_tp <= 0.3 or dist_sl <= 0.3:
            log("[ROMPIMENTO] sub: pavio colado no corpo - sem folga (tp=%.2f sl=%.2f)" %
                (dist_tp, dist_sl))
            return
        # Filtro estrutural de R/R (calibracao backtest 264 pregoes): o desenho
        # original (TP=Pavio a favor / SL=Pavio oposto) tem R/R medio 0,39 e
        # expectancy NEGATIVA (-1,00 pt/trade) apesar do winrate 67%. O filtro
        # rejeita rompimentos cuja relacao risco/retorno inicial fica abaixo de
        # sub_rr_min (default 1.0): so opera quando o pavio a favor sera >= o
        # pavio oposto. Variaveis D (R/R>=1): E=+2,36 pts, P(E>0)=88,6%.
        rr_min = float(self.cfg.get("sub_rr_min", 1.0))
        if rr_min > 0 and (dist_tp / dist_sl) < rr_min:
            log("[ROMPIMENTO] sub: R/R desfavoravel %.2f < %.2f (tp=%.2f sl=%.2f) - sem entrada" %
                (dist_tp / dist_sl, rr_min, dist_tp, dist_sl))
            return
        action = "BUY" if side == "C" else "SELL"
        cfg = self.cfg
        try:
            ticket = self.fn_executar(
                action, lots=cfg["lote"], symbol=self.symbol,
                sl=round(dist_sl, 3), tp=round(dist_tp, 3),
                magic_override=int(cfg["magic"]), comment="Rompimento1H SUB %s" % side)
        except Exception as e:
            log("[ROMPIMENTO] sub ERRO ao executar %s: %s" % (action, e))
            return
        if ticket is None:
            log("[ROMPIMENTO] sub ordem rejeitada/nao enviada (%s)" % action)
            return
        entry = None
        for _ in range(4):
            time.sleep(0.3)
            pos = self._pos_aberta(ticket)
            if pos is not None:
                entry = float(pos.price_open)
                break
        if entry is None:
            entry = preco_bid if side == "V" else preco_ask
        sub = dict(side=side, entry=entry, sl_lvl=sl_lvl, tp_lvl=tp_lvl,
                   ticket=ticket, final=False, saida="ABERTA", pts=None,
                   obs=None, nv=niv)
        st["dia"] = st.get("dia") or dia
        st["sub"] = sub
        _salvar_state(st)
        self._mem_fixar(ticket, "sub", side)
        log("[ROMPIMENTO] SUB %s %s entrada=%s SL=%s TP=%s ticket=%s (corpo_topo=%.2f corpo_fundo=%.2f pavio_topo=%.2f pavio_fundo=%.2f)" %
            (action, self.symbol, entry, sl_lvl, tp_lvl, ticket,
             niv["corpo_topo"], niv["corpo_fundo"],
             niv["pavio_topo"], niv["pavio_fundo"]))

    def _fase_gatilho(self, st, a, dia):
        """Fase gatilho da Faixa 1 (10:00-11:06): abre sem posicao."""
        if not st.get("ticket"):
            if self._janela_fechada(a):
                if st.get("dia") != dia:
                    st = self._cria_estado(dia)
                    st["final"] = True
                    st["saida"] = "S/TRADE"
                    st["obs"] = "sem gatilho na janela"
                    self._grava_final(st)
                    _salvar_state(st)
                elif not st.get("final"):
                    st["final"] = True
                    st["saida"] = st.get("saida") or "S/TRADE"
                    self._grava_final(st)
                    _salvar_state(st)
                return
            fresh, diff = self._fresco()
            if not fresh:
                log("[ROMPIMENTO] feed defasado %.0f min - sem decisao" % diff)
                return
            bars = barras_fechadas(self._barras_dia(a.date()), a)
            t = prep_safe(bars)
            if t is None:
                if a.hour >= 10 and a.minute >= 30:
                    log("[ROMPIMENTO] sem caixa 09-10h (dados incompletos) %s" % dia)
                return
            tr = trig(t, int(self.cfg["janela_min"]))
            if tr is None:
                return
            if st.get("dia") != dia:
                sub_ant = st.get("sub")
                st = self._cria_estado(dia)
                if sub_ant:
                    st["sub"] = sub_ant  # preserva registro do sub do MESMO dia
            self._abrir(st, t, tr)

    # -- auxiliares de fase --
    def _janela_fechada(self, a):
        return _hora_float(a) >= 11.0 + 0.1 or a.time() >= datetime.strptime(
            self._hora_eod_str(), "%H:%M").time()

    def _hora_eod_str(self):
        return str(self.cfg.get("hora_eod", "17:30"))

    def _hora_eod_excedida(self, a):
        eod = datetime.strptime(self._hora_eod_str(), "%H:%M").time()
        return a.time() >= eod

    def _barras_dia(self, data):
        if self.bars_fn is not None:
            return self.bars_fn(self.mt5, self.symbol, data)
        return barras_do_dia(self.mt5, self.symbol, data)

    def _coleta_price(self):
        if self.tick_fn is not None:
            return self.tick_fn()
        tick = self.mt5.symbol_info_tick(self.symbol)
        return float(tick.ask) if tick is not None else None

    def _cria_estado(self, dia):
        return dict(dia=dia, side=None, entry=None, sl_lvl=None, tp_lvl=None,
                    ticket=None, lote=float(self.cfg["lote"]), final=False,
                    saida=None, pts=None, obs=None, sub=None)

    def _classifica_saida(self, st, exit_p):
        try:
            e = float(st["entry"]); sl = float(st["sl_lvl"]); tp = float(st["tp_lvl"])
        except Exception:
            return "FECHADA"
        if st["side"] == "C":
            if exit_p <= sl:
                return "SL"
            if tp > e and exit_p >= tp:
                return "TP"
        else:
            if exit_p >= sl:
                return "SL"
            if tp < e and exit_p <= tp:
                return "TP"
        return "FECHADA"

    def _alvo_tp(self, e, side, tp_dist):
        return e + tp_dist if side == "C" else e - tp_dist

    def _abrir(self, st, t, tr):
        side, _idx, _entry_bt = tr
        action = "BUY" if side == "C" else "SELL"
        cfg = self.cfg
        sl_lvl = t["lo"] if side == "C" else t["hi"]
        e_atual = self._coleta_price()
        if e_atual is None:
            log("[ROMPIMENTO] sem tick para %s - adiando" % action)
            return
        sl_dist = max(0.0, (e_atual - sl_lvl) if side == "C" else (sl_lvl - e_atual))
        # Correcao 5: SL_efetivo = max(piso, min(SL_da_caixa, fator * ATR14 manha)).
        # ATR baixo => SL menor (sem stops desproporcionais de 23-27 pts);
        # piso garante folga anti-ruido (default 8.0 pts).
        atr = float(t.get("atr") or 0.0)
        fator = float(cfg.get("sl_atr_factor") or 0.0)
        piso = float(cfg.get("sl_piso") or 0.0)
        if atr > 0 and fator > 0:
            sl_dist = max(piso, min(sl_dist, fator * atr))
        tp_dist = cfg["tp_k"] * t["rr"] if cfg.get("tp_k") else 0.0
        try:
            ticket = self.fn_executar(
                action, lots=cfg["lote"], symbol=self.symbol,
                sl=round(sl_dist, 3), tp=round(tp_dist, 3),
                magic_override=int(cfg["magic"]), comment="Rompimento1H %s" % side)
        except Exception as e:
            log("[ROMPIMENTO] ERRO ao executar %s: %s" % (action, e))
            return
        if ticket is None:
            log("[ROMPIMENTO] ordem rejeitada/nao enviada (%s) - dia sem trade" % action)
            st["final"] = True
            st["saida"] = "S/TRADE"
            st["obs"] = "gatilho %s visto, ordem nao enviada" % action
            self._grava_final(st)
            _salvar_state(st)
            return
        entry = None
        for _ in range(4):
            time.sleep(0.3)
            pos = self._pos_aberta(ticket)
            if pos is not None:
                entry = float(pos.price_open)
                break
        if entry is None:
            entry = e_atual
        # SL_lvl efetivo ALINHADO com o sl_dist enviado a corretora (nao o da caixa)
        sl_lvl = entry - sl_dist if side == "C" else entry + sl_dist
        st.update(dict(side=side, entry=entry, sl_lvl=sl_lvl,
                       tp_lvl=self._alvo_tp(entry, side, tp_dist),
                       ticket=ticket, final=False, saida="ABERTA", pts=None))
        _salvar_state(st)
        log("[ROMPIMENTO] %s %s (lote %s) entrada=%s SL~%s TP=%s ticket=%s atr=%.2f factor=%.2f"
            % (action, self.symbol, cfg["lote"], entry, sl_lvl,
               st["tp_lvl"], ticket, atr, fator))
        self._mem_fixar(ticket, "faixa1", st.get("side"))

    def _finaliza(self, st, exit_p, saida, obs):
        dirv = 1 if st["side"] == "C" else -1
        try:
            entry = float(st["entry"])
        except Exception:
            entry = None
        st["pts"] = round(dirv * (float(exit_p) - entry), 3) if entry is not None else ""
        st["saida"] = saida
        st["obs"] = obs
        st["final"] = True
        _salvar_state(st)
        self._mem_gravar(st.get("ticket"), st.get("side"), saida)
        self._grava_final(st)

    def _grava_final(self, st):
        rec = dict(dia=st["dia"], side=st.get("side"), entrada=st.get("entry"),
                   sl=st.get("sl_lvl"), tp=st.get("tp_lvl"),
                   saida=st.get("saida"), pts=st.get("pts"),
                   obs=st.get("obs") or (st.get("saida") or ""),
                   ticket=st.get("ticket") or "", modulo="faixa1",
                   lucro_rs=self._lucro_real_rs(st.get("ticket")))
        _registrar_trade(rec)
        log("[ROMPIMENTO] REGISTRO %s side=%s saida=%s pts=%s lucro_rs=%s obs=%s" %
            (rec["dia"], rec["side"], rec["saida"], rec["pts"],
             rec["lucro_rs"], rec["obs"]))

    def _grava_final_sub(self, st):
        """D3: o Sub-Trader passa a alimentar a mesma trilha de memoria da
        Faixa 1. Sem isso o sub era um ponto cego para o dataset."""
        sub = st.get("sub") or {}
        if not sub or not sub.get("ticket"):
            return
        rec = dict(dia=st.get("dia"), side=sub.get("side"),
                   entrada=sub.get("entry"), sl=sub.get("sl_lvl"),
                   tp=sub.get("tp_lvl"), saida=sub.get("saida"),
                   pts=sub.get("pts"), obs=sub.get("obs") or "sub",
                   ticket=sub.get("ticket"), modulo="sub",
                   lucro_rs=self._lucro_real_rs(sub.get("ticket")))
        _registrar_trade(rec)
        self._mem_gravar(sub.get("ticket"), sub.get("side"), sub.get("saida"))
        log("[ROMPIMENTO] REGISTRO SUB %s side=%s saida=%s pts=%s lucro_rs=%s" %
            (rec["dia"], rec["side"], rec["saida"], rec["pts"], rec["lucro_rs"]))


# ---------------- SELFTEST (referencia estatística, sem barras noturnas) -------
def rodar_referencia(path):
    """Roda o nucleo (prep/trig/resolve) no historico e imprime stats por ano."""
    from collections import defaultdict

    def _load(p):
        rows = []
        with open(p, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                dt = datetime.fromtimestamp(int(row["time"]))
                rows.append((dt, float(row["open"]), float(row["high"]),
                             float(row["low"]), float(row["close"]),
                             int(row["tick_volume"])))
        return rows

    cfg = _carga_cfg()
    por_ano = defaultdict(list)
    for row in _load(path):
        dt = row[0]
        if dt.date().weekday() >= 5:
            continue
        por_ano[dt.year].append(row)
    tot = 0
    for ano in sorted(por_ano):
        days = defaultdict(list)
        for b in por_ano[ano]:
            if b[0].hour >= 18:
                continue  # sem noturnas
            days[b[0].date()].append(b)
        n = wr = pf = net = 0.0
        wins = guts = 0.0
        seq = max_seq = 0
        for d in sorted(days):
            t = prep_safe(days[d])
            if t is None:
                continue
            tr = trig(t, int(cfg["janela_min"]))
            if tr is None:
                continue
            pts, saida = resolve(t, tr[0], tr[1], tr[2], cfg["sl_mode"],
                                 cfg.get("tp_k"),
                                 float(cfg.get("sl_atr_factor") or 0.0),
                                 float(cfg.get("sl_piso") or 0.0))
            n += 1
            net += pts
            wins += max(pts, 0)
            guts += abs(min(pts, 0))
            if pts > 0:
                wr += 1
            seq = seq + 1 if pts <= 0 else 0
            max_seq = max(max_seq, seq)
        if n > 0:
            tot += n
            wr = wr / n * 100
            pf = wins / guts if guts else 0.0
            print("%s: n=%4.d WR=%5.1f%% PF=%5.2f net=%+8.0f maxseq=%d" %
                  (ano, n, wr, pf, net, max_seq))
    print("TOTAL trades=%d (sl_mode=%s tp_k=%s janela=%dmin, factor_atr=%s piso=%s, sem noturnos)" %
          (tot, cfg["sl_mode"], cfg.get("tp_k"), int(cfg["janela_min"]),
           cfg.get("sl_atr_factor"), cfg.get("sl_piso")))
    return tot > 0


if __name__ == "__main__":
    import sys
    sect = sys.argv[1] if len(sys.argv) > 1 else "--selftest"
    if sect == "--selftest":
        p = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(
            ROOT, "backtest", "dados_mt5", "baixa_tudo", "filtrados", "WDG2026_M5.csv")
        print("ROMPIMENTO 1a HORA | referencia (sem barras noturnas, hora>=18 fora)")
        ok = rodar_referencia(p)
        sys.exit(0 if ok else 2)
    print("Uso: rompimento_orquestrador.py --selftest [csv]")