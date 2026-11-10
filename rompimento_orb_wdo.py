# -*- coding: utf-8 -*-
"""rompimento_orb_wdo.py — ORB (Opening Range Breakout) no WDO, PAPER / READ-ONLY.

Espelha a metodologia do estudo `backtest_orb_wdo.py`:
  caixa  = 09:00-10:00 BRT (primeira hora)
  gatilho= 10:30-11:00 BRT (rompimento do high/low da caixa)  <- janela pos-EUA
  saida  = EOD (ultima barra do dia, ~17:55)
  custo  = R$ 1,20 por contrato (0,60 entrada + 0,60 saida); 1 ponto = R$ 10,00

Decisao do Mestre (23.21.5): rodar as TRES saidas EM PARALELO no paper, custo
zero, para escolher o vencedor com dado real em 20-30 sessoes:
  1. stop_caixa  = lado oposto da caixa (~R$ 339 de risco)  -> maior WR
  2. stop_half   = 0,5x caixa a partir da entrada (~R$ 170)  -> melhor total
  3. stop_fixed5 = 5 pontos fixos (R$ 50)                    -> stop do Herman

NUNCA envia ordem. Nao importa order_send / order_check. Apenas le barras M5
do terminal (copy_rates_from_pos) e registra o que teria acontecido.

Filtros sao REGISTRADOS por dia (nao bloqueiam o paper): vies da 1a hora,
alinhamento EMA20/50 e caixa <= 2x mediana de 20 sessoes. Depois o `--resumo`
compara as 3 saidas com/sem cada filtro.

CLI:
  python rompimento_orb_wdo.py                       -> roda o dia em papel (agendado)
  python rompimento_orb_wdo.py --reconcilia-hoje AAAA-MM-DD
  python rompimento_orb_wdo.py --resumo              -> estatisticas do CSV
"""
import csv
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta, time as dtime

# ---------------- CONFIG (metodologia do backtest_orb_wdo.py) ----------------
SYMBOL = "WDO$"
RS_PER_POINT = 10.0
COST_RS = 1.20            # 0,60 entrada + 0,60 saida, por contrato
BOX_START, BOX_END = "09:00", "10:00"
TRIG_START, TRIG_END = "10:30", "11:00"
EOD_HM = "17:55"

# ---------------- TIMES (BRT) ----------------
TIME_NO_TRADE = dtime(11, 6)      # janela fecha 11:00; depois disso, sem gatilho = S/TRADE
TIME_EOD_FINAL = dtime(18, 5)     # ultima M5 (17:55) fecha 18:00
TIME_RECON = dtime(18, 20)
TIME_STOP = dtime(18, 30)
STALE_MAX_MIN = 12                # feed defasado acima disso nao decide

ROOT = r"C:\AIOFEN"
LOG_DIR = os.path.join(ROOT, "logs", "rompimento_orb_wdo")
LOG_FILE = os.path.join(LOG_DIR, "orb_wdo.log")
TRADES_CSV = os.path.join(LOG_DIR, "trades_orb_wdo.csv")
STATE_JSON = os.path.join(LOG_DIR, "state.json")

HEADER = [
    "dia", "side", "box_high", "box_low", "box_range", "box_bias",
    "ema_align", "cap_ok", "entry", "entry_ts",
    "stop_caixa", "stop_half", "stop_fixed5",
    "exit_caixa", "pts_caixa", "exit_half", "pts_half",
    "exit_fixed5", "pts_fixed5", "mfe_pts", "mae_pts", "obs",
]

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
    return datetime.fromtimestamp(int(ts) + _SHIFT)


# ---------------- MT5 (somente leitura) ----------------
def connect(max_wait_s=900):
    import MetaTrader5 as mt5
    t0 = time.time()
    while not mt5.initialize():
        if time.time() - t0 > max_wait_s:
            return False
        time.sleep(5)
    detect_shift(mt5)
    log("MT5 conectado | offset=%d s | simbolo=%s" % (_SHIFT, SYMBOL))
    return True


def detect_shift(mt5, n=3000):
    """Escolhe o deslocamento (s) que coloca mais barras na sessao 9-18h."""
    global _SHIFT
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, n)
    if rates is None or len(rates) < 300:
        return _SHIFT
    best = (_SHIFT, -1)
    for cand in (-25200, -21600, -18000, -14400, -10800, -7200, -3600,
                 0, 3600, 7200, 10800, 14400, 18000, 21600):
        cnt = 0
        for r in rates[-1500:]:
            dt = datetime.fromtimestamp(int(r["time"]) + cand)
            if 9 <= dt.hour <= 17 and dt.weekday() < 5:
                cnt += 1
        if cnt > best[1]:
            best = (cand, cnt)
    _SHIFT = best[0]
    return _SHIFT


def fetch_bars(mt5, n=4000):
    """Barras M5 (em ordem) interpretadas no horario local. Read-only."""
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, n)
    if rates is None:
        return []
    out = []
    for r in rates:
        out.append({
            "dt": brt(r["time"]),
            "o": float(r["open"]),
            "h": float(r["high"]),
            "l": float(r["low"]),
            "c": float(r["close"]),
            "v": int(r["tick_volume"]),
        })
    out.sort(key=lambda b: b["dt"])
    return out


def feed_lag_min(mt5):
    """Defasagem (min) da ultima barra M5 em relacao a hora real."""
    r = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 1)
    if r is None or len(r) == 0:
        return 10 ** 9
    return (time.time() - (int(r[0]["time"]) + _SHIFT)) / 60.0


# ---------------- NUCLEO (identico em live e reconciliacao) ----------------
def ema_series(vals, span):
    k = 2.0 / (span + 1.0)
    out = []
    e = None
    for v in vals:
        e = v if e is None else v * k + e * (1.0 - k)
        out.append(e)
    return out


def day_bars_of(bars, dia):
    """Barras do dia dentro da sessao 09:00-18:00 (mesmo filtro do backtest).

    O WDO$ traz barras de after-market (ex.: 18:05-18:25); ignora-las e'
    essencial para o EOD bater com o estudo.
    """
    out = []
    for b in bars:
        if b["dt"].date() != dia:
            continue
        hm = b["dt"].strftime("%H:%M")
        if "09:00" <= hm <= "18:00":
            out.append(b)
    return out


def _hm(b):
    return b["dt"].strftime("%H:%M")


def build_box(day_bars):
    box = [b for b in day_bars if BOX_START <= _hm(b) < BOX_END]
    if len(box) < 8:
        return None
    high = max(b["h"] for b in box)
    low = min(b["l"] for b in box)
    return {
        "high": high,
        "low": low,
        "range": high - low,
        "open": box[0]["o"],
        "close": box[-1]["c"],
        "last_dt": box[-1]["dt"],
        "n": len(box),
    }


def prior_range_median(bars, hoje, n_days=20):
    """Mediana do tamanho da caixa nas ultimas `n_days` sessoes anteriores."""
    by_day = {}
    for b in bars:
        d = b["dt"].date()
        if d >= hoje:
            continue
        by_day.setdefault(d, []).append(b)
    ranges = []
    for d in sorted(by_day)[-n_days:]:
        bx = build_box(by_day[d])
        if bx is not None:
            ranges.append(bx["range"])
    return statistics.median(ranges) if ranges else None


def attach_emas(bars, box):
    """EMA20/EMA50 no fechamento da ultima barra da caixa."""
    closes = [b["c"] for b in bars]
    e20 = ema_series(closes, 20)
    e50 = ema_series(closes, 50)
    idx = None
    for i, b in enumerate(bars):
        if b["dt"] == box["last_dt"]:
            idx = i
            break
    if idx is None:
        return None, None
    return e20[idx], e50[idx]


def entry_signal(day_bars, box):
    """(side, entry, entry_dt, ambiguous) do rompimento na janela 10:30-11:00."""
    for b in day_bars:
        if not (TRIG_START <= _hm(b) < TRIG_END):
            continue
        up = b["h"] > box["high"]
        dn = b["l"] < box["low"]
        if up and dn:
            return None, None, None, True       # barra ambigua: pula o dia
        if up:
            return "BUY", box["high"], b["dt"], False
        if dn:
            return "SELL", box["low"], b["dt"], False
    return None, None, None, False


def simulate(day_bars, side, entry, entry_dt, stop, eod_close):
    """Simula UMA saida a partir da barra de entrada. Stop antes de EOD.

    Modela gap atraves do stop: se a barra (posterior a entrada) ABRE alem do
    stop, o fill e' o open (pior que o stop). Na barra de entrada nao ha gap.
    """
    mfe = mae = 0.0
    first = True
    for b in day_bars:
        if b["dt"] < entry_dt:
            continue
        hi, lo, op = b["h"], b["l"], b["o"]
        gap = (not first) and (
            (side == "BUY" and op < stop) or (side == "SELL" and op > stop)
        )
        first = False
        if side == "BUY":
            mfe = max(mfe, hi - entry)
            mae = min(mae, lo - entry)
            if lo <= stop:
                fill = op if gap else stop
                return {"pnl": fill - entry, "exit": "SL", "mfe": mfe, "mae": mae}
        else:
            mfe = max(mfe, entry - lo)
            mae = min(mae, entry - hi)
            if hi >= stop:
                fill = op if gap else stop
                return {"pnl": entry - fill, "exit": "SL", "mfe": mfe, "mae": mae}
    pnl = (eod_close - entry) if side == "BUY" else (entry - eod_close)
    return {"pnl": pnl, "exit": "EOD", "mfe": mfe, "mae": mae}


def path_mfe_mae(day_bars, side, entry, entry_dt):
    mfe = mae = 0.0
    for b in day_bars:
        if b["dt"] < entry_dt:
            continue
        if side == "BUY":
            mfe = max(mfe, b["h"] - entry)
            mae = min(mae, b["l"] - entry)
        else:
            mfe = max(mfe, entry - b["l"])
            mae = min(mae, entry - b["h"])
    return mfe, mae


def evaluate_day(bars, dia, obs=""):
    """Avalia o dia inteiro (ou o que houver) e devolve a linha do CSV.

    Retorna (row, estado). row=None quando nao ha caixa suficiente.
    """
    day_bars = day_bars_of(bars, dia)
    box = build_box(day_bars)
    if box is None:
        return None, {"dia": dia.isoformat(), "final": False, "obs": "caixa incompleta"}
    e20, e50 = attach_emas(bars, box)
    med = prior_range_median(bars, dia)

    side, entry, entry_dt, ambiguous = entry_signal(day_bars, box)
    if side is None:
        st = {
            "dia": dia.isoformat(), "final": False, "side": None,
            "ambiguous": bool(ambiguous),
            "obs": "barra ambigua" if ambiguous else "sem gatilho na janela",
        }
        return None, st

    # filtros (registrados, nao bloqueiam)
    bias = "UP" if box["close"] > box["open"] else ("DOWN" if box["close"] < box["open"] else "FLAT")
    if side == "BUY":
        vies = bias == "UP"
        ema_align = (e20 is not None and e50 is not None and e20 > e50)
    else:
        vies = bias == "DOWN"
        ema_align = (e20 is not None and e50 is not None and e20 < e50)
    cap_ok = (med is not None and box["range"] <= 2.0 * med)

    stops = {
        "caixa": box["low"] if side == "BUY" else box["high"],
        "half": entry - 0.5 * box["range"] if side == "BUY" else entry + 0.5 * box["range"],
        "fixed5": entry - 5.0 if side == "BUY" else entry + 5.0,
    }
    eod_close = day_bars[-1]["c"]
    res = {k: simulate(day_bars, side, entry, entry_dt, s, eod_close)
           for k, s in stops.items()}
    mfe, mae = path_mfe_mae(day_bars, side, entry, entry_dt)

    row = {
        "dia": dia.isoformat(),
        "side": side,
        "box_high": round(box["high"], 2),
        "box_low": round(box["low"], 2),
        "box_range": round(box["range"], 2),
        "box_bias": bias,
        "ema_align": int(bool(ema_align)),
        "cap_ok": int(bool(cap_ok)),
        "entry": round(entry, 2),
        "entry_ts": entry_dt.strftime("%H:%M"),
        "stop_caixa": round(stops["caixa"], 2),
        "stop_half": round(stops["half"], 2),
        "stop_fixed5": round(stops["fixed5"], 2),
        "exit_caixa": res["caixa"]["exit"],
        "pts_caixa": round(res["caixa"]["pnl"], 2),
        "exit_half": res["half"]["exit"],
        "pts_half": round(res["half"]["pnl"], 2),
        "exit_fixed5": res["fixed5"]["exit"],
        "pts_fixed5": round(res["fixed5"]["pnl"], 2),
        "mfe_pts": round(mfe, 2),
        "mae_pts": round(mae, 2),
        "obs": obs or ("vies=%d ema=%d cap=%d" % (int(vies), int(bool(ema_align)), int(bool(cap_ok)))),
    }
    st = {
        "dia": dia.isoformat(), "final": False, "side": side,
        "entry": round(entry, 2), "entry_ts": entry_dt.strftime("%H:%M"),
        "stops": {k: round(v, 2) for k, v in stops.items()},
        "resultados": {k: {"exit": res[k]["exit"], "pts": round(res[k]["pnl"], 2)}
                       for k in res},
        "obs": row["obs"],
    }
    return row, st


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
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_JSON)


def _drop_day(path, dia):
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("dia") != dia]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HEADER})


def registrar(row):
    """Grava a unica linha do dia no CSV (idempotente)."""
    _drop_day(TRADES_CSV, row["dia"])
    with open(TRADES_CSV, "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=HEADER).writerow(row)
    log("=> [REGISTRO %s] %s entrada=%s | caixa %s/%s pts | half %s/%s | f5 %s/%s | %s" % (
        row["dia"], row["side"], row["entry"],
        row["exit_caixa"], row["pts_caixa"], row["exit_half"], row["pts_half"],
        row["exit_fixed5"], row["pts_fixed5"], row["obs"]))


def dia_completo(bars, dia, now):
    day_bars = day_bars_of(bars, dia)
    if not day_bars:
        return False
    if now.time() < TIME_EOD_FINAL:
        return False
    return any(_hm(b) >= EOD_HM for b in day_bars)


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
        log("dia %s ja finalizado - encerrando" % hoje)
        mt5.shutdown()
        return
    st = {"dia": hoje.isoformat(), "final": False, "fase": "inicio", "obs": None}
    save_state(st)
    log("INICIO paper ORB WDO | caixa %s-%s | gatilho %s-%s | 3 saidas em paralelo" %
        (BOX_START, BOX_END, TRIG_START, TRIG_END))
    registrado = False
    ultimo_aviso = None
    while True:
        now = datetime.now()
        if now.weekday() >= 5 or now.date() != hoje:
            log("fora do dia - encerrando")
            break
        frag = feed_lag_min(mt5)
        fresh = frag <= STALE_MAX_MIN
        bars = fetch_bars(mt5)
        if fresh and bars:
            row, st = evaluate_day(bars, hoje)
            if now.time() < dtime(10, 5):
                st["fase"] = "aguardando caixa 09-10h"
            elif now.time() < dtime(11, 6):
                st["fase"] = "janela de gatilho 10:30-11:00" if st.get("side") else "aguardando gatilho"
            elif not st.get("side"):
                st["fase"] = "sem trade"
                st["final"] = True          # janela fechou sem gatilho
            else:
                st["fase"] = "em trade"
            save_state(st)
            if row is not None and now.time() >= TIME_EOD_FINAL:
                registrar(row)
                registrado = True
                st["final"] = True
                save_state(st)
                break
        else:
            if ultimo_aviso is None or (now - ultimo_aviso).total_seconds() > 60:
                log("feed defasado %.0f min - sem decisao (aguardando dados)" %
                    (frag if frag < 10 ** 6 else -1))
                ultimo_aviso = now
        if now.time() >= TIME_RECON:
            break
        time.sleep(20)

    # reconciliacao autoritativa com barras completas
    bars = fetch_bars(mt5)
    if dia_completo(bars, hoje, datetime.now()):
        row, st = evaluate_day(bars, hoje, obs="REC")
        if row is not None:
            registrar(row)
            registrado = True
        st["final"] = True
        save_state(st)
    elif not registrado:
        log("dados incompletos no fim do dia - SEM registro (rode --reconcilia-hoje %s)" % hoje)
    log("FIM do dia %s (registrado=%s | %s)" % (hoje, registrado, st.get("fase")))
    mt5.shutdown()


# ---------------- RECONCILIA MANUAL ----------------
def reconcilia_hoje(dia_str):
    import MetaTrader5 as mt5
    dia = datetime.strptime(dia_str, "%Y-%m-%d").date()
    if not connect():
        print("FALHA conectar MT5")
        return 1
    bars = fetch_bars(mt5)
    ref = datetime.now()
    if dia < ref.date():
        ref = datetime.combine(dia, dtime(18, 10))   # dia passado: ja' fechado
    if not dia_completo(bars, dia, ref):
        print("ATENCAO: dados de %s incompletos/defasados - SEM registro." % dia)
        mt5.shutdown()
        return 2
    row, st = evaluate_day(bars, dia, obs="REC")
    if row is None:
        print("dia %s: %s" % (dia, st.get("obs")))
        st["final"] = True
        save_state(st)
        mt5.shutdown()
        return 0
    registrar(row)
    st["final"] = True
    save_state(st)
    print("registrado: %s" % row)
    mt5.shutdown()
    return 0


# ---------------- RESUMO ----------------
def _stats(pts_list):
    if not pts_list:
        return None
    pnl = [p * RS_PER_POINT - COST_RS for p in pts_list]
    wins = [x for x in pnl if x > 0]
    loss = [x for x in pnl if x <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(loss))
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    eq = 0.0
    peak = 0.0
    maxdd = 0.0
    for x in pnl:
        eq += x
        peak = max(peak, eq)
        maxdd = min(maxdd, eq - peak)
    return {
        "n": len(pnl),
        "wr": 100.0 * len(wins) / len(pnl),
        "exp": sum(pnl) / len(pnl),
        "pf": pf,
        "total": sum(pnl),
        "maxdd": maxdd,
    }


def resumo():
    if not os.path.exists(TRADES_CSV):
        print("sem CSV ainda: %s" % TRADES_CSV)
        return 0
    with open(TRADES_CSV, encoding="utf-8", newline="") as f:
        todas = list(csv.DictReader(f))
    rows = [r for r in todas if r.get("side")]
    if not rows:
        print("sem trades registrados")
        return 0
    print("sessoes com trade: %d (de %d linhas no CSV)" % (len(rows), len(todas)))
    variants = (("stop_caixa", "pts_caixa"), ("stop_half", "pts_half"),
                ("stop_fixed5", "pts_fixed5"))
    filtros = (
        ("TODOS", lambda r: True),
        ("+ vies 1a hora", lambda r: r.get("box_bias") in ("UP", "DOWN") and (
            (r.get("side") == "BUY" and r.get("box_bias") == "UP") or
            (r.get("side") == "SELL" and r.get("box_bias") == "DOWN"))),
        ("+ EMA alinhada", lambda r: r.get("ema_align") == "1"),
        ("+ caixa <=2x", lambda r: r.get("cap_ok") == "1"),
        ("+ vies + EMA + caixa", lambda r: (
            r.get("ema_align") == "1" and r.get("cap_ok") == "1" and (
                (r.get("side") == "BUY" and r.get("box_bias") == "UP") or
                (r.get("side") == "SELL" and r.get("box_bias") == "DOWN")))),
    )
    for fname, cond in filtros:
        sub = [r for r in rows if cond(r)]
        if not sub:
            continue
        print("\n[%s] n=%d" % (fname, len(sub)))
        print("  %-12s %5s %7s %9s %6s %11s %10s" %
              ("saida", "n", "win%", "exp_R$", "PF", "total_R$", "maxDD_R$"))
        for key, col in variants:
            try:
                pts = [float(r[col]) for r in sub]
            except (KeyError, ValueError):
                continue
            s = _stats(pts)
            if s is None:
                continue
            print("  %-12s %5d %7.1f %9.2f %6.2f %11.0f %10.0f" %
                  (key, s["n"], s["wr"], s["exp"], s["pf"], s["total"], s["maxdd"]))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--reconcilia-hoje":
        sys.exit(reconcilia_hoje(sys.argv[2]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "--resumo":
        sys.exit(resumo())
    live()
