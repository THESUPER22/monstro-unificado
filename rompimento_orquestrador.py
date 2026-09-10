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
)

ROOT = r"C:\AIOFEN"
LOG_DIR = os.path.join(ROOT, "logs", "rompimento")
LOG_FILE = os.path.join(LOG_DIR, "rompimento.log")
STATE_JSON = os.path.join(LOG_DIR, "rompimento_state.json")
TRADES_CSV = os.path.join(LOG_DIR, "rompimento_trades.csv")
HEADER_TRADES = ["dia", "side", "entrada", "sl", "tp", "saida", "pts", "obs"]

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


def dfasagem_min(mt5mod, symbol):
    """Defasagem (min) da ultima M5 em relacao a hora real (fuso-independente)."""
    r = mt5mod.copy_rates_from_pos(symbol, mt5mod.TIMEFRAME_M5, 0, 1)
    if r is None or len(r) == 0:
        return 10 ** 9
    return (time.time() - int(r[0]["time"])) / 60.0


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
                bars=trigb, fim=(fim.hour * 3600 + fim.minute * 60))


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


def resolve(t, side, idx, e, sl_mode, tp_k):
    """SL conferido antes do TP (intrabarra); EOD no ultimo bar da sessao."""
    bars = t["bars"]
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
    for b in bars[idx:]:
        if side == "C":
            if b[3] <= sl_lvl:
                return -sl_dist, "SL"
            if tp is not None and b[2] >= tp:
                return tp - e, "TP"
        else:
            if b[2] >= sl_lvl:
                return -sl_dist, "SL"
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


def _rewrite_csv_drop_day(p, header, dia):
    rows = []
    if os.path.exists(p) and os.path.getsize(p) > 0:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("dia") != dia:
                    rows.append(r)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _registrar_trade(rec):
    _rewrite_csv_drop_day(TRADES_CSV, HEADER_TRADES, rec["dia"])
    with open(TRADES_CSV, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER_TRADES)
        if os.path.getsize(TRADES_CSV) == 0:
            w.writeheader()
        w.writerow({c: rec.get(c, "") for c in HEADER_TRADES})


# ---------------- ORQUESTRADOR ----------------
class OrquestradorRompimento:
    def __init__(self, fn_executar, symbol="WDO$", ativo=True, mt5mod=None,
                 clock=None, bars_fn=None, tick_fn=None):
        self.fn_executar = fn_executar
        self.symbol = symbol
        self.ativo = ativo
        self.cfg = _carga_cfg()
        self.mt5 = mt5mod or mt5
        self.clock = clock or (lambda: datetime.now())
        self.bars_fn = bars_fn   # (mt5mod, symbol, data) -> barras do dia
        self.tick_fn = tick_fn   # () -> preco ou None

    # -- helpers --
    def _pos_aberta(self, ticket):
        try:
            pos = self.mt5.positions_get(ticket=ticket)
            return pos[0] if pos else None
        except Exception:
            return None

    def _fresco(self):
        stale = dfasagem_min(self.mt5, self.symbol)
        return stale <= float(self.cfg["stale_max_min"]), stale

    def _exit_deal(self, ticket):
        try:
            deals = self.mt5.history_deals_get(position=ticket)
        except Exception:
            return None
        if not deals:
            return None
        outs = [d for d in deals if d["entry"] == self.mt5.DEAL_ENTRY_OUT]
        if not outs:
            return None
        return float(outs[-1]["price"])

    def _fechar_market(self, ticket):
        try:
            self.mt5.position_close(ticket)
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
        if st.get("dia") == dia and st.get("final"):
            return

        # ---- fase gatilho (10:00-11:06): sem posicao, pode abrir ----
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
                st = self._cria_estado(dia)
            self._abrir(st, t, tr)
            if st.get("final"):
                return

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
                    saida=None, pts=None, obs=None)

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
        st.update(dict(side=side, entry=entry, sl_lvl=sl_lvl,
                       tp_lvl=self._alvo_tp(entry, side, tp_dist),
                       ticket=ticket, final=False, saida="ABERTA", pts=None))
        _salvar_state(st)
        log("[ROMPIMENTO] %s %s (lote %s) entrada=%s SL~%s TP=%s ticket=%s" %
            (action, self.symbol, cfg["lote"], entry, sl_lvl,
             st["tp_lvl"], ticket))

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
        self._grava_final(st)

    def _grava_final(self, st):
        rec = dict(dia=st["dia"], side=st.get("side"), entrada=st.get("entry"),
                   sl=st.get("sl_lvl"), tp=st.get("tp_lvl"),
                   saida=st.get("saida"), pts=st.get("pts"),
                   obs=st.get("obs") or (st.get("saida") or ""))
        _registrar_trade(rec)
        log("[ROMPIMENTO] REGISTRO %s side=%s saida=%s pts=%s obs=%s" %
            (rec["dia"], rec["side"], rec["saida"], rec["pts"], rec["obs"]))


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
            pts, saida = resolve(t, tr[0], tr[1], tr[2], cfg["sl_mode"], cfg.get("tp_k"))
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
    print("TOTAL trades=%d (sl_mode=%s tp_k=%s janela=%dmin, sem noturnos)" %
          (tot, cfg["sl_mode"], cfg.get("tp_k"), int(cfg["janela_min"])))
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