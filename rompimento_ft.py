# -*- coding: utf-8 -*-
"""Rompimento da Primeira Hora - ROBO DE PAPEL (forward test) | WIN$
Lógica idêntica ao backtest (C:\\AIOFEN\\backtest\\backtest_rompimento_1hora.py):
  caixa 09:00-10:00 (velas M5 hora 9), gatilho 10:00-11:00 (prioridade 60min),
  fill = abertura da barra gatilho, SL conferido ANTES do TP, EOD 17:55.
NUNCA envia ordem. Apenas registra o que acertaria em papel (banca fictícia).
Uso:
  python rompimento_ft.py              -> roda o dia em papel (agendado pelo Windows)
  python rompimento_ft.py --selftest C:\AIOFEN\backtest\dados_mt5\baixa_tudo\filtrados\WING2026_M5.csv
                                      -> valida a maquina de estados contra o historico (1:1 com o backtest)
"""
import csv, json, os, sys, time
from datetime import datetime, timedelta, time as dtime

BT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest")
if BT_DIR not in sys.path:
    sys.path.insert(0, BT_DIR)
from backtest_rompimento_1hora import load, build_days, prep, trig, resolve

# ---------------- CONFIG DA ESTRATEGIA (mesmos parametros do MELHOR combo) ----------------
SYMBOL = "WIN$"
SL_MODE = "lo_half"
TP_K = 2.0
WINDOW_MIN = 60
PV = 0.20          # R$ por ponto (WIN$: tick 1.0 -> R$0.20) - igual ao backtest
CUSTO = 0.75       # R$ por trade (mesmo do backtest)
BANCO_INICIAL = 1500.0
MAGIC = 0          # inexistente: papel nao abre posicao real

# ---------------- TIMES (BRT) ----------------
TIME_EOD_FINAL = dtime(18, 0, 30)   # espera a vela 17:55 fechar (fecha 18:00) para EOD igual ao backtest
TIME_NO_TRADE = dtime(11, 6)        # sem gatilho ate 11:06 -> dia sem trade

ROOT = r"C:\AIOFEN"
LOG_DIR = os.path.join(ROOT, "logs", "rompimento_ft")
LOG_FILE = os.path.join(LOG_DIR, "rompimento_ft.log")
TRADES_CSV = os.path.join(LOG_DIR, "trades.csv")
EQUITY_CSV = os.path.join(LOG_DIR, "equity.csv")
STATE_JSON = os.path.join(LOG_DIR, "state.json")
HEADER_TRADES = ["dia", "side", "entrada", "sl", "tp", "saida", "pts", "custo", "nav_antes", "nav_depois", "obs"]
HEADER_EQUITY = ["datahora", "dia", "nav", "pts_dia", "obs"]

os.makedirs(LOG_DIR, exist_ok=True)

_OFFSET = 0


def log(msg):
    line = "%s | %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def brt(ts):
    return datetime.fromtimestamp(ts + _OFFSET)


def short_s(var):
    return "-" if var is None else str(round(var, 1))


# ---------------- MT5 ----------------
def connect(max_wait_s=900):
    global _OFFSET
    import MetaTrader5 as mt5
    t0 = time.time()
    while not mt5.initialize():
        if time.time() - t0 > max_wait_s:
            return False
        time.sleep(5)
    _OFFSET = detect_offset(mt5)
    log("MT5 conectado (expiracao=%s)".replace("expiracao=%s", "offset=%d s") % _OFFSET)
    return True


def detect_offset(mt5):
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 200)
    if rates is None or len(rates) == 0:
        return 0
    amb = [i for i in [-21600, -10800, 0, 10800, 21600]]
    best = (0, -1)
    for off in amb:
        horas = [datetime.fromtimestamp(int(r["time"]) + off).hour
                 for r in rates[-50:]
                 if datetime.fromtimestamp(int(r["time"]) + off).weekday() < 5]
        sess = sum(1 for h in horas if 9 <= h <= 18)
        if sess > best[1]:
            best = (off, sess)
    return best[0]


def fetch_today_bars(mt5, hoje, now):
    """velas M5 de hoje ja fechadas (b[0] + 5min <= now), em ordem cronologica"""
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 1200)
    if rates is None:
        return []
    out = []
    for r in rates:
        dt = brt(int(r["time"]))
        if dt.date() != hoje:
            continue
        if dt + timedelta(minutes=5) > now:
            continue
        out.append((dt, float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]), int(r["tick_volume"])))
    return out


# ---------------- NUCLEO (state machine pura; identica em live e selftest) ----------------
def make_state(dia, nav=BANCO_INICIAL):
    return dict(dia=dia.isoformat(), nav=round(nav, 2), side=None, idx=None, entry=None,
                sl_lvl=None, tp_lvl=None, pts=None, saida=None, final=False)


def prep_safe(bars):
    """prep() do backtest tolerante a dia incompleto (trigb vazia antes das 10:00)"""
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
    """um passo. retorna (novo state, mudou_final). cfg: {sl_mode, tp_k, window_min}"""
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
    # EOD valido quando: (a) sessao quase completa (vela 17:55 fechada) apos 18:00, ou
    # (b) sessao curta/encerrada (sem barra fechada nova ha 30 min apos a tarde)
    lb = max((b[0] + timedelta(minutes=5) for b in bars), default=None)
    sessao_completa = now.time() >= cfg["eod_final"] and any(b[0].time() >= dtime(17, 50) for b in bars)
    sessao_curta = (lb is not None and now.time() >= dtime(13, 0)
                    and now - lb >= timedelta(minutes=30))
    if sessao_completa or sessao_curta:
        st["pts"] = pts
        st["saida"] = "EOD"
        st["final"] = True
        return st, True
    return st, False


def aplicar_resultado(st):
    pf = st["pts"] - CUSTO if st["pts"] is not None else 0.0
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


def append_csv(p, row, header=HEADER_TRADES):
    novo = not os.path.exists(p) or os.path.getsize(p) == 0
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if novo:
            w.writeheader()
        w.writerow(row)


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
    if prev and prev.get("dia") == hoje.isoformat():
        # ja rodou hoje? verifica se o pid ainda existe
        pid = prev.get("pid")
        if pid:
            ok = False
            try:
                import ctypes
                PRO_QUERY = (0x0000, 0x0400)  # PROCESS_QUERY_LIMITED_INFORMATION
                h = ctypes.windll.kernel32.OpenProcess(PRO_QUERY[1], False, pid)
                if h:
                    ok = True
                    ctypes.windll.kernel32.CloseHandle(h)
            except Exception:
                ok = False
            if ok:
                log("ja rodando (pid=%s)" % pid)
                mt5.shutdown()
                return
    st = make_state(hoje)
    st["pid"] = os.getpid()
    st["started"] = datetime.now().isoformat()
    save_state(st)
    cfg = dict(sl_mode=SL_MODE, tp_k=TP_K, window_min=WINDOW_MIN,
               no_trade_at=TIME_NO_TRADE, eod_final=TIME_EOD_FINAL)
    log("INICIO papel | %s | banco=R$%.2f | caixa 09-10h | SL=%s TP=%sx janela=%dmin" %
        (SYMBOL, BANCO_INICIAL, SL_MODE, TP_K, WINDOW_MIN))
    cycle = 0
    while True:
        now = datetime.now()
        if now.weekday() >= 5:
            log("virou fim de semana - encerrando")
            break
        if now.date() != hoje:
            log("mudou o dia - encerrando")
            break
        bars = fetch_today_bars(mt5, hoje, now)
        st2, changed = run_step(st, bars, now, cfg)
        if st2["final"] and not st.get("final"):
            pf = aplicar_resultado(st2)
            row = {
                "dia": hoje.isoformat(), "side": st2["side"], "entrada": short_s(st2["entry"]),
                "sl": short_s(st2["sl_lvl"]), "tp": short_s(st2["tp_lvl"]),
                "saida": st2["saida"], "pts": st2["pts"], "custo": CUSTO,
                "nav_antes": "%.2f" % (st2["nav"] - pf if st2["pts"] is not None else st2["nav"]),
                "nav_depois": "%.2f" % st2["nav"], "obs": st2.get("obs", ""),
            }
            append_csv(TRADES_CSV, row)
            linha_eq = dict(datahora=datetime.now().isoformat(), dia=hoje.isoformat(),
                            nav="%.2f" % st2["nav"], pts_dia=short_s(st2["pts"]), obs=st2["saida"])
            append_csv(EQUITY_CSV, linha_eq, HEADER_EQUITY)
            log("=> RESULTADO %s | side=%s entrada=%s saida=%s pts=%s | NAV=R$%.2f" %
                (hoje, st2["side"], short_s(st2["entry"]), st2["saida"], short_s(st2["pts"]), st2["nav"]))
            save_state(st2)
        elif st2 != st:
            save_state(st2)
        st = st2
        if st["final"]:
            log("FIM do dia (estado final=%s)" % st["saida"])
            save_state(st)
            break
        if now.time() >= dtime(18, 30):
            log("tempo maximo atingido (18:30) - encerrando")
            save_state(st)
            break
        cycle += 1
        time.sleep(20 if cycle % 5 else 30)
    mt5.shutdown()


# ---------------- SELFTEST (replay historico 1:1) ----------------
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
            fail += 1
            fails.append((d, ref, got, "presenca divergente"))
        elif ref[0] != got[0] or ref[1] != got[1] or ref[2] != got[2]:
            fail += 1
            fails.append((d, ref, got, ""))
        else:
            ok += 1
    print("SELFTEST: dias=%d OK=%d FALHA=%d" % (len(days), ok, fail))
    for d, ref, got, obs in fails[:20]:
        print("  FALHA %s | ref=%s got=%s %s" % (d, ref, got, obs))
    return fail == 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest(sys.argv[2]) else 1)
    elif len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        p = os.path.join(BT_DIR, "dados_mt5", "baixa_tudo", "filtrados", "WING2026_M5.csv")
        sys.exit(0 if selftest(p) else 1)
    live()