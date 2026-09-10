# -*- coding: utf-8 -*-
# Rompimento da Primeira Hora (range 09:00-10:00) | WIN M5 | 2021-2026
# Fill conservador: abertura da barra M5 gatilho. SL conferido antes do TP (intrabarra). EOD 17:55.
import csv, os
from datetime import datetime
from collections import defaultdict

VALOR = 0.20
CUSTO = 0.75


def load(p):
    rows = []
    with open(p, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            dt = datetime.fromtimestamp(int(row["time"]))
            rows.append((dt, float(row["open"]), float(row["high"]),
                         float(row["low"]), float(row["close"]), int(row["tick_volume"])))
    return rows


def build_days(rows):
    days = {}
    for row in rows:
        days.setdefault(row[0].date(), []).append(row)
    return days


def trig(t, window_min):
    """retorna (side, idx, entry) ou None; window_min=None -> dia inteiro, senao minutos apos 10:00"""
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


def prep(bars):
    morning = [b for b in bars if b[0].hour == 9]
    if not morning:
        return None
    hi = max(b[2] for b in morning); lo = min(b[3] for b in morning)
    rr = hi - lo
    if rr <= 0:
        return None
    mvol = sum(b[5] for b in morning)
    trigb = [b for b in bars if b[0].hour >= 10]
    fim = trigb[-1][0]
    return dict(hi=hi, lo=lo, rr=rr, mvol=mvol, bars=trigb, fim=(fim.hour * 3600 + fim.minute * 60))


def resolve(t, side, idx, e, sl_mode, tp_k):
    bars = t["bars"]
    if side == "C":
        sl_lvl = {"mid": (t["hi"] + t["lo"]) / 2, "lo": t["lo"], "lo_half": t["lo"] - 0.5 * t["rr"]}[sl_mode]
        sl_dist = e - sl_lvl
        tp = e + tp_k * t["rr"] if tp_k else None
    else:
        sms = {"mid": "mid", "lo": "hi", "lo_half": "hi_half"}[sl_mode]
        sl_lvl = {"mid": (t["hi"] + t["lo"]) / 2, "hi": t["hi"], "hi_half": t["hi"] + 0.5 * t["rr"]}[sms]
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


def stats(pnls):
    ts = sorted(pnls)
    if not ts:
        return None
    n = len(ts)
    wins = [p for _, p in ts if p > 0]
    los = [p for _, p in ts if p <= 0]
    gw = sum(wins); gl = abs(sum(los))
    eq = 0.0; pico = 0.0; mdd = 0.0; seq = 0; streak = 0
    for _, p in ts:
        eq += p; pico = max(pico, eq); mdd = min(mdd, eq - pico)
        seq = seq + 1 if p <= 0 else 0; streak = max(streak, seq)
    net = sum(p for _, p in ts)
    wr = len(wins) / n * 100 if n else 0
    pf = gw / gl if gl else (float("inf") if gw else 0)
    return dict(n=n, wr=wr, pf=pf, net=net, mdd=mdd, streak=streak, gw=gw, gl=gl)


def main(files):
    combos = [(sm, tk, wm) for sm in ["mid", "lo", "lo_half"]
              for tk in [1.5, 2.0, 3.0, 4.0, None]
              for wm in [30, 60]]
    res = {}
    preps = {}
    trades_by_year = {}
    for ano, p in files:
        days = build_days(load(p))
        per = defaultdict(list)
        pp = {}
        for d in sorted(days):
            t = prep(days[d])
            if t is None:
                continue
            pp[d] = t
            tr = trig(t, None)
            if tr is None:
                continue
            rec = dict(dia=d, side=tr[0], hi=t["hi"], lo=t["lo"], rr=t["rr"], mvol=t["mvol"])
            for (sm, tk, wm) in combos:
                r = trig(t, wm)
                if r is None:
                    continue
                pts, saida = resolve(t, r[0], r[1], r[2], sm, tk)
                per[(sm, tk, wm)].append((d, pts))
                if (sm, tk, wm) == ("lo", 2.0, 60):
                    rec["pts"] = pts; rec["saida"] = saida
            trades_by_year.setdefault(ano, []).append(rec)
        res[ano] = per
        preps[ano] = pp
    # ------- tabela combinada 2022-26 -------
    combs_all = [(sm, tk, wm) for sm in ["mid", "lo", "lo_half"]
                 for tk in [1.5, 2.0, 3.0, 4.0, None] for wm in [30, 60]]
    anos_ok = [a for a, _ in files if a != 2021]
    rows = []
    for cb in combs_all:
        tot = [(d, p) for a in anos_ok for d, p in res[a][cb]]
        s = stats(tot)
        if s is None:
            continue
        rows.append((cb, s, tot))
    rows.sort(key=lambda x: -x[1]["net"])
    print("=" * 100)
    print("ROMPIMENTO 1a HORA | combinado 2022-2026 | fill=abertura do gatilho | custo R$0.75 | 1cc")
    print(f"{'SL':<8}{'TP':<8}{'jane':<6}{'n':>5}{'WR':>6}{'PF':>5}{'net':>8}{'R$':>9}{'MaxDD':>8}")
    for cb, s, tot in rows[:15]:
        sm, tk, wm = cb
        netl = s["net"] * VALOR - s["n"] * CUSTO
        print(f"{sm:<8}{str(tk):<8}{wm:<6}{s['n']:>5}{s['wr']:>6.1f}{s['pf']:>5.2f}"
              f"{s['net']:>8.0f}{netl:>9.2f}{s['mdd']*VALOR:>8.0f}")
    print("-" * 100)
    best = rows[0]
    print("MELHOR: SL=%s TP=%s janela=%s | PF=%.2f WR=%.1f%%" % (best[0][0], best[0][1], best[0][2], best[1]["pf"], best[1]["wr"]))
    for ano in [a for a, _ in files]:
        s = stats([(x, y) for x, y in res[ano][best[0]]])
        if s:
            netl = s["net"] * VALOR - s["n"] * CUSTO
            print(f"  {ano}: n={s['n']:>4} WR={s['wr']:5.1f}% PF={s['pf']:5.2f} net={s['net']:+7.0f} R$1cc={netl:+8.2f} MaxDD={s['mdd']*VALOR:+7.0f}")
    # baseline classico: SL=lo/hi, TP=EOD, janela 30min
    base = ("lo", None, 30)
    print("-" * 100)
    print("BASELINE classico (SL=extremidade oposta, sem TP=EOD, gatilho 30min):")
    for ano in [a for a, _ in files]:
        s = stats(res[ano][base])
        if s:
            netl = s["net"] * VALOR - s["n"] * CUSTO
            print(f"  {ano}: n={s['n']:>4} WR={s['wr']:5.1f}% PF={s['pf']:5.2f} net={s['net']:+7.0f} R$1cc={netl:+8.2f}")
    # volume: estratificar o melhor combo por tercil de vol matinal (proxy tick_volume) 2022-26
    print("-" * 100)
    print(f"VOLUME matinal (proxy tick_volume 09:00-10:00) - melhor combo {best[0]}: tercis 2022-26")
    sm, tk, wm = best[0]
    vols = [t["mvol"] for a in anos_ok for t in preps[a].values()]
    vs = sorted(vols)
    q33 = vs[len(vs) // 3]; q66 = vs[2 * len(vs) // 3]
    bucket = defaultdict(list)
    for a in anos_ok:
        for d in preps[a]:
            t = preps[a][d]
            tr = trig(t, wm)
            if tr is None:
                continue
            pts, saida = resolve(t, tr[0], tr[1], tr[2], sm, tk)
            b = "baixo" if t["mvol"] < q33 else ("alto" if t["mvol"] >= q66 else "medio")
            if t["mvol"] is not None:
                bucket[b].append((d, pts))
    for b in ["baixo", "medio", "alto"]:
        s = stats(bucket[b])
        if s:
            netl = s["net"] * VALOR - s["n"] * CUSTO
            print(f"  {b:>5}: n={s['n']:>4} WR={s['wr']:5.1f}% PF={s['pf']:5.2f} net={s['net']:+7.0f} R$1cc={netl:+8.2f}")


if __name__ == "__main__":
    DATA = r"C:\AIOFEN\backtest\dados_mt5\baixa_tudo\filtrados"
    files = [(ano, os.path.join(DATA, f"WING{ano}_M5.csv"))
             for ano in [2021, 2022, 2023, 2024, 2025, 2026]
             if os.path.exists(os.path.join(DATA, f"WING{ano}_M5.csv"))]
    main(files)