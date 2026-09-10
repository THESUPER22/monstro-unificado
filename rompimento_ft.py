# -*- coding: utf-8 -*-
"""Rompimento da Primeira Hora - ROBO DE PAPEL (forward test) | WIN$
Logica identica ao backtest (C:\\AIOFEN\\backtest\\backtest_rompimento_1hora.py):
  caixa 09:00-10:00 (velas M5 hora 9), gatilho 10:00-11:00 (janela 60min),
  fill = abertura da barra gatilho, SL conferido ANTES do TP, EOD 17:55.
NUNCA envia ordem. Apenas registra o que acertaria em papel (banca ficticia).

Robustez:
  - Offset de fuso detectado automaticamente por dia (o terminal pode alternar
    entre servidores/conta cujo relogio nao e BRT).
  - Trava de frescor: decisoes so sao tomadas com ultima vela M5 a <=12 min da
    hora real; caso contrario o dia fica "aguardando dados".
  - Reconci liacao ao fim do dia (18:50 BRT): avalia o dia com as barras COMPLETAS
    (identico ao backtest) e grava a linha autoritativa do dia (1 linha/dia).

CLI:
  python rompimento_ft.py                          -> roda o dia em papel (agendado)
  python rompimento_ft.py --reconcilia-hoje AAAA-MM-DD -> avalia o dia completo e grava a linha
  python rompimento_ft.py --selftest [csv]         -> valida a maquina de estados contra o historico
"""
import csv, json, os, sys, time
from datetime import datetime, timedelta, time as dtime
from collections import defaultdict

BT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest")
if BT_DIR not in sys.path:
    sys.path.insert(0, BT_DIR)
from backtest_rompimento_1hora import load, build_days, prep, trig, resolve

# ---------------- CONFIG DA ESTRATEGIA (parametros do MELHOR combo) ----------------
SYMBOL = "WIN$"
SL_MODE = "lo_half"
TP_K = 2.0
WINDOW_MIN = 60
PV = 0.20          # R$ por ponto (WIN$ tick 1.0 -> R$0.20); igual ao backtest
CUSTO = 0.75       # R$ por trade
BANCO_INICIAL = 1500.0

# ---------------- TIMES (BRT) ----------------
TIME_NO_TRADE = dtime(11, 6)        # sem gatilho ate 11:06 (janela fecha 11:00) -> dia sem trade
TIME_EOD_FINAL = dtime(18, 0, 30)   # aguarda a vela 17:55 fechar (fecha 18:00) p/ EOD identico ao backtest
TIME_RECON = dtime(18, 50)          # fim do dia: reconcilia com barras completas
TIME_STOP = dtime(18, 55)
STALE_MAX_MIN = 12                  # feed defasado acima disso nao decide

ROOT = r"C:\AIOFEN"
LOG_DIR = os.path.join(ROOT, "logs", "rompimento_ft")
LOG_FILE = os.path.join(LOG_DIR, "rompimento_ft.log")
TRADES_CSV = os.path.join(LOG_DIR, "trades.csv")
EQUITY_CSV = os.path.join(LOG_DIR, "equity.csv")
STATE_JSON = os.path.join(LOG_DIR, "state.json")
HEADER_TRADES = ["dia", "side", "entrada", "sl", "tp", "saida", "pts", "custo", "nav_antes", "nav_depois", "obs"]
HEADER_EQUITY = ["datahora", "dia", "nav", "pts_dia", "obs"]

os.makedirs(LOG_DIR, exist_ok=True)

_SHIFT = 0


def log(msg):
    line = "%s | %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def brt(ts):
    return datetime.fromtimestamp(ts + _SHIFT)


def short_s(var):
    return "-" if var is None else str(round(var, 0))


# ---------------- MT5 ----------------
def connect(max_wait_s=900):
    import MetaTrader5 as mt5
    t0 = time.time()
    while not mt5.initialize():
        if time.time() - t0 > max_wait_s:
            return False
        time.sleep(5)
    detect_shift(mt5)
    log("MT5 conectado | offset=%d s" % _SHIFT)
    return True


def detect_shift(mt5, n=3000):
    """escolhe o deslocamento (s) que coloca mais barras historicas no horario de sessao (9-18h)."""
    global _SHIFT
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, n)
    if rates is None or len(rates) < 300:
        return _SHIFT
    best = (_SHIFT, -1)
    for cand in (-25200, -21600, -18000, -14400, -10800, -7200, -3600, 0, 3600, 7200, 10800, 14400, 18000, 21600):
        cnt = 0
        for r in rates[-1500:]:
            dt = datetime.fromtimestamp(int(r["time"]) + cand)
            if 9 <= dt.hour <= 17 and dt.weekday() < 5:
                cnt += 1
        if cnt > best[1]:
            best = (cand, cnt)
    _SHIFT = best[0]
    return _SHIFT


def fetch_bars(mt5, hoje):
    """velas M5 fechadas do dia (em ordem), interpretadas com o offset atual"""
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 1500)
    if rates is None:
        return []
    out = []
    for r in rates:
        dt = brt(int(r["time"]))
        if dt.date() != hoje:
            continue
        out.append((dt, float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]), int(r["tick_volume"])))
    out.sort(key=lambda b: b[0])
    return out


def batch_avail(mt5, hoje, now):
    """barras fechadas do dia (b[0] + 5min <= now) para decisoes intraday"""
    return [b for b in fetch_bars(mt5, hoje) if b[0] + timedelta(minutes=5) <= now]


def feed_lag_min(mt5):
    """defasagem (min) da ultima vela M5 em relacao a hora real. fuso-independente."""
    r = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 1)
    if r is None or len(r) == 0:
        return 10 ** 9
    last_epoch = int(r[0]["time"])
    return (time.time() - last_epoch) / 60.0


# ---------------- NUCLEO (identical in live/selftest/reconcile) ----------------
def last_nav():
    if os.path.exists(EQUITY_CSV):
        try:
            with open(EQUITY_CSV, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if rows and rows[-1].get("nav"):
                return float(rows[-1]["nav"])
        except Exception:
            pass
    return BANCO_INICIAL


def make_state(dia, nav=None):
    if nav is None:
        nav = last_nav()
    return dict(dia=dia.isoformat(), nav=round(nav, 2), side=None, idx=None, entry=None,
                sl_lvl=None, tp_lvl=None, pts=None, saida=None, final=False, obs=None)


def prep_safe(bars):
    if not bars:
        return None
    try:
        t = prep(bars)
    except Exception:
        return None
    if t is None or not t["bars"]:
        return None
    return t


def run_step(st, bars, now, cfg):
    """um passo. retorna (novo state, mudou_final)"""
    st = dict(st)
    if st["final"]:
        return st, False
    t = prep_safe(bars)
    if t is None:
        if now.time() >= cfg["no_trade_at"]:
            st["final"] = True
            st["saida"] = "S/TRADE"
            st["obs"] = "sem dados/box"
        return st, False
    if st["side"] is None:
        tr = trig(t, cfg["window_min"])
        if tr is None:
            if now.time() >= cfg["no_trade_at"]:
                st["final"] = True
                st["saida"] = "S/TRADE"
                st["obs"] = "sem gatilho na janela"
            return st, False
        side, idx, entry = tr
        st.update(dict(side=side, idx=idx, entry=entry))
        if side == "C":
            st["sl_lvl"] = t["lo"] - 0.5 * t["rr"]
            st["tp_lvl"] = entry + cfg["tp_k"] * t["rr"] if cfg["tp_k"] else None
        else:
            st["sl_lvl"] = t["hi"] + 0.5 * t["rr"]
            st["tp_lvl"] = entry - cfg["tp_k"] * t["rr"] if cfg["tp_k"] else None
    pts, saida = resolve(t, st["side"], st["idx"], st["entry"], cfg["sl_mode"], cfg["tp_k"])
    if saida != "EOD":
        st["pts"] = pts
        st["saida"] = saida
        st["final"] = True
        return st, True
    lb = max((b[0] + timedelta(minutes=5) for b in bars), default=None)
    sessao_completa = now.time() >= cfg["eod_final"] and any(b[0].time() >= dtime(17, 50) for b in bars)
    sessao_curta = (cfg.get("fresh", True) and lb is not None and now.time() >= dtime(13, 0)
                    and now - lb >= timedelta(minutes=30))
    if sessao_completa or sessao_curta:
        st["pts"] = pts
        st["saida"] = "EOD"
        st["final"] = True
        return st, True
    return st, False


def apply_stop_custos(st):
    pf = (st["pts"] * PV - CUSTO) if st["pts"] is not None else 0.0
    st["nav"] = round(st["nav"] + pf, 2)
    return pf


# ---------------- PERSISTENCIA ----------------
def load_state():
    if os.path.exists(STATE_JSON):
        try:
            with open(STATE_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_state(st):
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp, STATE_JSON)


def _rewrite_csv_drop_day(p, header, dia):
    """reescreve CSV removendo as linhas do dia (garante 1 linha/dia)"""
    rows = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            rd = csv.DictReader(f)
            rows = [r for r in rd if r.get("dia") != dia]
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


# ---------------- REGISTRO AUTORITATIVO DO DIA ----------------
def registrar_dia(st, obs):
    """grava a unica linha do dia em trades.csv e equity.csv a partir do estado final."""
    dia = st["dia"]
    nav_antes = st["nav"]
    pf = (st["pts"] * PV - CUSTO) if st["pts"] is not None else 0.0
    st["nav"] = round(st["nav"] + pf, 2)
    _rewrite_csv_drop_day(TRADES_CSV, HEADER_TRADES, dia)
    _rewrite_csv_drop_day(EQUITY_CSV, HEADER_EQUITY, dia)
    row = {
        "dia": dia, "side": st["side"], "entrada": short_s(st["entry"]),
        "sl": short_s(st["sl_lvl"]), "tp": short_s(st["tp_lvl"]),
        "saida": st["saida"], "pts": st["pts"], "custo": CUSTO,
        "nav_antes": "%.2f" % nav_antes, "nav_depois": "%.2f" % st["nav"],
        "obs": (st.get("obs") or obs or st["saida"]),
    }
    with open(TRADES_CSV, "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=HEADER_TRADES).writerow(row)
    linha_eq = dict(datahora=datetime.now().isoformat(), dia=dia, nav="%.2f" % st["nav"],
                    pts_dia=short_s(st["pts"]), obs=row["obs"])
    with open(EQUITY_CSV, "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=HEADER_EQUITY).writerow(linha_eq)
    log("=> [REGISTRO %s] side=%s entrada=%s saida=%s pts=%s obs=%s | NAV=R$%.2f" %
        (dia, st["side"], short_s(st["entry"]), st["saida"], short_s(st["pts"]), row["obs"], st["nav"]))


def dia_completo(mt5, dia, bars):
    """o dia tem barras suficientes pra ser considerado 'final'? (usado a noite/reconciliacao)"""
    lb = bars[-1] if bars else None
    if lb is None:
        return False
    now = datetime.now()
    if now.time() < dtime(18, 5):
        return False
    lb_end = lb[0] + timedelta(minutes=5)
    if lb[0].time() >= dtime(17, 45) or now - lb_end >= timedelta(hours=6):
        return True
    return feed_lag_min(mt5) <= STALE_MAX_MIN


def reconciliar(mt5, dia, bars=None):
    """avalia o dia completo (barras finais) -> estado final autoritativo == backtest"""
    if bars is None:
        bars = fetch_bars(mt5, dia)
    st = make_state(dia)
    if not bars:
        st["final"] = True
        st["saida"] = "SEM_DADOS"
        st["obs"] = "nenhuma barra do dia"
        return st
    cfg = dict(sl_mode=SL_MODE, tp_k=TP_K, window_min=WINDOW_MIN,
               no_trade_at=TIME_NO_TRADE, eod_final=TIME_EOD_FINAL, fresh=True)
    now = datetime(dia.year, dia.month, dia.day, 19, 0)
    st, ch = run_step(st, bars, now, cfg)
    if not st["final"]:
        st["final"] = True
        st["saida"] = st["saida"] or "S/TRADE"
        st["obs"] = st.get("obs") or "reconciliado sem final"
    return st


# ---------------- LIVE ----------------
def live():
    import MetaTrader5 as mt5
    if datetime.now().weekday() >= 5:
        print("fim de semana - nao opera")
        return
    if not connect():
        log("FALHA conectar MT5")
        return
    hoje = datetime.now().date()
    prev = load_state()
    if prev and prev.get("dia") == hoje.isoformat() and prev.get("final"):
        log("dia %s ja finalizado (state) - encerrando" % hoje)
        mt5.shutdown()
        return
    st = make_state(hoje)
    st["pid"] = os.getpid()
    st["started"] = datetime.now().isoformat()
    cfg = dict(sl_mode=SL_MODE, tp_k=TP_K, window_min=WINDOW_MIN,
               no_trade_at=TIME_NO_TRADE, eod_final=TIME_EOD_FINAL, fresh=False)
    save_state(st)
    log("INICIO papel | %s | banco=R$%.2f | caixa 09-10h | SL=%s TP=%sx janela=%dmin" %
        (SYMBOL, BANCO_INICIAL, SL_MODE, TP_K, WINDOW_MIN))
    registrado = False
    ultimo_aviso = None
    while True:
        now = datetime.now()
        if now.weekday() >= 5 or now.date() != hoje:
            log("fora do dia - encerrando")
            break
        frag = feed_lag_min(mt5)
        fresh = frag <= STALE_MAX_MIN
        bars = batch_avail(mt5, hoje, now)
        if fresh and bars:
            cfg["fresh"] = True
            st, changed = run_step(st, bars, now, cfg)
            if st["final"]:
                registrar_dia(st, "")
                registrado = True
                save_state(st)
                break
        else:
            if ultimo_aviso is None or (now - ultimo_aviso).total_seconds() > 60:
                log("feed defasado %.0f min - sem decisao (aguardando dados frescos)" %
                    (frag if frag < 10 ** 6 else -1))
                ultimo_aviso = now
        save_state(st)
        if now.time() >= TIME_RECON:
            break
        time.sleep(20)
    # reconciliacao autoritativa ao final
    if dia_completo(mt5, hoje, fetch_bars(mt5, hoje)):
        st = reconciliar(mt5, hoje)
        registrar_dia(st, "REC")
        registrado = True
    elif not registrado:
        log("dados incompletos/defasados no fim do dia - SEM registro (rode --reconcilia-hoje %s depois)" % hoje)
    save_state(st)
    log("FIM do dia %s (registrado=%s | %s %s)" % (hoje, registrado, st["saida"], short_s(st["pts"])))
    mt5.shutdown()


# ---------------- RECONCILIA MANUAL ----------------
def reconcilia_hoje(dia_str):
    import MetaTrader5 as mt5
    dia = datetime.strptime(dia_str, "%Y-%m-%d").date()
    if not connect():
        print("FALHA conectar MT5")
        return 1
    bars = fetch_bars(mt5, dia)
    print("barras do dia %s: %d | ultima: %s" % (dia, len(bars),
                                                 bars[-1][0].strftime("%H:%M") if bars else "-"))
    if not dia_completo(mt5, dia, bars):
        print("ATENCAO: dados do dia ainda incompletos/defasados - SEM registro.")
        print("Rode de novo depois do preg~ao (18:05+) ou quando o feed sincronizar.")
        mt5.shutdown()
        return 2
    st = reconciliar(mt5, dia, bars)
    registrar_dia(st, "REC")
    save_state(st)
    print("registrado: %s" % st)
    mt5.shutdown()
    return 0


# ---------------- SELFTEST ----------------
def selftest(path):
    cfg = dict(sl_mode=SL_MODE, tp_k=TP_K, window_min=WINDOW_MIN,
               no_trade_at=TIME_NO_TRADE, eod_final=TIME_EOD_FINAL)
    days = build_days(load(path))
    ok = fail = 0
    fails = []
    for d in sorted(days):
        bars_all = days[d]
        ref = None
        t = prep_safe(bars_all)
        if t is not None:
            tr = trig(t, WINDOW_MIN)
            if tr is not None:
                pts, saida = resolve(t, tr[0], tr[1], tr[2], SL_MODE, TP_K)
                ref = (tr[0], round(pts, 6), saida)
        st = make_state(d)
        now = datetime(d.year, d.month, d.day, 8, 58)
        fim = datetime(d.year, d.month, d.day, 18, 6)
        while now <= fim:
            avail = [b for b in bars_all if b[0] + timedelta(minutes=5) <= now]
            st, changed = run_step(st, avail, now, cfg)
            if st["final"]:
                break
            now += timedelta(minutes=1)
        if st["final"] and st["side"] is not None:
            got = (st["side"], round(st["pts"], 6), st["saida"])
        else:
            got = None
        if ref is None and got is None:
            ok += 1
        elif ref is None or got is None:
            fail += 1; fails.append((d, ref, got, "presenca divergente"))
        elif ref[0] != got[0] or ref[1] != got[1] or ref[2] != got[2]:
            fail += 1; fails.append((d, ref, got, ""))
        else:
            ok += 1
    print("SELFTEST: dias=%d OK=%d FALHA=%d" % (len(days), ok, fail))
    for d, ref, got, obs in fails[:20]:
        print("  FALHA %s | ref=%s got=%s %s" % (d, ref, got, obs))
    return fail == 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        p = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(
            BT_DIR, "dados_mt5", "baixa_tudo", "filtrados", "WING2026_M5.csv")
        sys.exit(0 if selftest(p) else 1)
    elif len(sys.argv) >= 3 and sys.argv[1] == "--reconcilia-hoje":
        sys.exit(reconcilia_hoje(sys.argv[2]))
    live()