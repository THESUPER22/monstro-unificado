#!/usr/bin/env python3
"""
Backtest - SETE VELAS INVERTIDO (WIN - M15 / M5) + FILTROS
Regras base (confirmadas em 09/09/2026):
  1. Timeframe M15. As 6 primeiras velas do dia = 09:00..10:15 BRT.
  2. Entrada: 10:30:00 cravado, abertura da 7a vela (M5 10:30 open), a mercado.
  3. Direcao INVERTIDA: maioria verde -> VENDA; maioria vermelha -> COMPRA.
     Vela doji (open==close) = neutra. Empate (ups==dns) = sem trade.
  4. Stop Loss: 300 pontos. Alvo: extremidade oposta matinal (09:00..10:15).
  5. Filtro rompido: entrada ja alem do alvo = sem trade.
  Checagem M5, SL conferido primeiro (conservador), EOD 17:55 BRT.
Filtros testados:
  R400/R500 : range matinal (max-min das 6 velas) >= 400 / 500 pts
  EMA200    : MME(200) nas closes M15 ate a vela 10:15 (sem lookahead);
              acima do EMA as 10:30 -> so BUY permitido; abaixo -> so SELL.
"""
import csv
import os
import sys
from datetime import datetime, time, timedelta
from collections import defaultdict

DATA_M5 = r"C:\AIOFEN\backtest\dados_mt5\WIN_GANHO26_M5.csv"
OUT_DIR = r"C:\AIOFEN\backtest\resultados"
os.makedirs(OUT_DIR, exist_ok=True)

INI = time(9, 0)
FIM = time(17, 55)
ENTRY_H = time(10, 30)
SL_PT = 300.0
MIN_BARRAS_DIA = 100
VALOR_PONTO = 0.20
CUSTO = 0.75


def agregar_m15(bars_m5):
    out = {}
    for b in bars_m5:
        key15 = (b["hh"].hour, (b["hh"].minute // 15) * 15)
        if key15 not in out:
            out[key15] = {"h": key15, "o": b["o"], "hi": b["lo"], "lo": b["hi"], "c": b["c"]}
        c = out[key15]
        c["hi"] = max(c["hi"], b["hi"])
        c["lo"] = min(c["lo"], b["lo"])
        c["c"] = b["c"]
    return out


def ema_serie(vals, n=200):
    """SMA expandido ate n barras, depois EMA classico. Retorna lista."""
    out = []
    s = 0.0
    a = 2.0 / (n + 1)
    for i, v in enumerate(vals):
        if i < n:
            s += v
            out.append(s / (i + 1))
        else:
            out.append(v * a + out[-1] * (1 - a))
    return out


def main(csv_path=None, rotulo="WIN"):
    DATA_M5 = csv_path or r"C:\AIOFEN\backtest\dados_mt5\WIN_GANHO26_M5.csv"
    dias = defaultdict(list)
    first_close_ts = {}
    with open(DATA_M5, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dt = datetime.fromtimestamp(int(r["time"])) + timedelta(hours=3)
            hh = dt.time()
            if hh < INI or hh > FIM:
                continue
            dias[dt.date()].append({
                "t": int(r["time"]), "hh": hh,
                "o": float(r["open"]), "hi": float(r["high"]),
                "lo": float(r["low"]), "c": float(r["close"]),
            })

    # ---- serie M15 global (todas as closes) para EMA200 ----
    serie_dt = defaultdict(list)   # dia -> lista ordenada de M15 bars
    for d in sorted(dias):
        bars = sorted(dias[d], key=lambda b: b["t"])
        if len(bars) < MIN_BARRAS_DIA:
            continue
        m15 = agregar_m15(bars)
        serie_dt[d] = [m15[k] for k in sorted(m15)]
    closes = []
    pos_map = {}  # (dia, hkey) -> idx na serie
    idx = 0
    for d in sorted(serie_dt):
        for c in serie_dt[d]:
            pos_map[(d, c["h"])] = idx
            closes.append(c["c"])
            idx += 1
    emas = ema_serie(closes, 200)

    # ---- candidatos ----
    cands = []
    n_skip_data = n_skip_tie = n_skip_broken = 0
    n_dias = 0
    for d in sorted(dias):
        bars = sorted(dias[d], key=lambda b: b["t"])
        if len(bars) < MIN_BARRAS_DIA:
            n_skip_data += 1
            continue
        n_dias += 1
        m15 = agregar_m15(bars)
        chave = {(k[0], k[1]): c for k, c in m15.items()}
        seis_key = [(9, 0), (9, 15), (9, 30), (9, 45), (10, 0), (10, 15)]
        if not all(k in chave for k in seis_key) or (10, 30) not in chave:
            n_skip_data += 1
            continue
        six = [chave[k] for k in seis_key]
        ent = chave[(10, 30)]
        ups = sum(1 for c in six if c["c"] > c["o"])
        dns = sum(1 for c in six if c["c"] < c["o"])
        if ups == dns:
            n_skip_tie += 1
            continue
        dire = "SELL" if ups > dns else "BUY"
        entrada = ent["o"]
        alvo = max(c["hi"] for c in six) if dire == "BUY" else min(c["lo"] for c in six)
        if (dire == "BUY" and entrada >= alvo) or (dire == "SELL" and entrada <= alvo):
            n_skip_broken += 1
            continue

        pts = None
        saida = None
        for m5 in bars:
            if m5["hh"] < ENTRY_H:
                continue
            if dire == "BUY":
                if m5["lo"] <= entrada - SL_PT:
                    pts, saida = -SL_PT, "SL"
                    break
                if m5["hi"] >= alvo:
                    pts, saida = alvo - entrada, "TP"
                    break
            else:
                if m5["hi"] >= entrada + SL_PT:
                    pts, saida = -SL_PT, "SL"
                    break
                if m5["lo"] <= alvo:
                    pts, saida = entrada - alvo, "TP"
                    break
        else:
            fec = bars[-1]["c"]
            pts = (fec - entrada) if dire == "BUY" else (entrada - fec)
            saida = "EOD"

        # ---- variante CLASSICA (espelho): verde->BUY / vermelho->SELL, TP=+300, SL=extremo matinal ----
        dir_c = "BUY" if dire == "SELL" else "SELL"
        sl_c = min(c["lo"] for c in six) if dir_c == "BUY" else max(c["hi"] for c in six)
        pts_c = None
        saida_c = None
        for m5 in bars:
            if m5["hh"] < ENTRY_H:
                continue
            if dir_c == "BUY":
                if m5["hi"] >= entrada + SL_PT:
                    pts_c, saida_c = SL_PT, "TP"
                    break
                if m5["lo"] <= sl_c:
                    pts_c, saida_c = -(entrada - sl_c), "SL"
                    break
            else:
                if m5["lo"] <= entrada - SL_PT:
                    pts_c, saida_c = SL_PT, "TP"
                    break
                if m5["hi"] >= sl_c:
                    pts_c, saida_c = -(sl_c - entrada), "SL"
                    break
        else:
            fec = bars[-1]["c"]
            pts_c = (fec - entrada) if dir_c == "BUY" else (entrada - fec)
            saida_c = "EOD"

        rng = max(c["hi"] for c in six) - min(c["lo"] for c in six)
        ema_v = emas[pos_map[(d, (10, 15))]]
        cands.append({
            "dia": d, "dir": dire, "ups": ups, "dns": dns,
            "entrada": entrada, "alvo": alvo, "pts": round(pts, 1), "saida": saida,
            "pts_c": round(pts_c, 1), "saida_c": saida_c,
            "range": rng, "ema": ema_v, "acima_ema": entrada >= ema_v,
        })

    def filtro(combo):
        r = list(cands)
        if combo == "CLASSIC":
            return r  # usa pts_c (construcao no relatorio)
        if "R1500" in combo and "R2000" not in combo and "R2500" not in combo:
            r = [t for t in r if t["range"] >= 1500]
        if "R2000" in combo and "R2500" not in combo:
            r = [t for t in r if t["range"] >= 2000]
        if "R2500" in combo:
            r = [t for t in r if t["range"] >= 2500]
        if "EMAONLY" in combo:
            r = [t for t in r if t["acima_ema"]]
        if "EMA12" in combo:
            r = [t for t in r if (t["dir"] == "BUY" and t["acima_ema"]) or (t["dir"] == "SELL" and not t["acima_ema"])]
        return r

    def metricas(ts, col="pts"):
        n = len(ts)
        if n == 0:
            return None
        wins = [t for t in ts if t[col] > 0]
        los = [t for t in ts if t[col] <= 0]
        gw = sum(t[col] for t in wins)
        gl = abs(sum(t[col] for t in los))
        eq = 0.0
        pico = 0.0
        mdd = 0.0
        seq = 0
        streak = 0
        for t in ts:
            eq += t[col]
            pico = max(pico, eq)
            mdd = min(mdd, eq - pico)
            seq = seq + 1 if t[col] <= 0 else 0
            streak = max(streak, seq)
        net = sum(t[col] for t in ts)
        return {
            "n": n, "w": len(wins), "l": len(los),
            "wr": len(wins) / n * 100,
            "gw": gw or 0, "gl": gl or 0,
            "pf": gw / gl if gl else float("inf"),
            "net": net,
            "payoff": (gw / len(wins)) / (gl / len(los)) if wins and los and gl else 0,
            "avg_win": gw / len(wins) if wins else 0,
            "avg_loss": gl / len(los) if los else 0,
            "mdd": mdd,
            "streak": streak,
            "mai_win": max(t[col] for t in ts),
        }

    combos = ["BASE", "R1500", "R2500", "EMAONLY", "EMA12", "EMAONLY+R2000", "EMAONLY+R2500", "CLASSIC"]

    def pts_of(cb, t):
        return t["pts_c"] if cb == "CLASSIC" else t["pts"]
    print("=" * 100)
    print("SETE VELAS INVERTIDO + FILTROS | %s | M15 | %s a %s" % (rotulo, cands[0]["dia"], cands[-1]["dia"]))
    print("Dias validos: %d | sem dados: %d | empate: %d | rompido: %d" % (n_dias, n_skip_data, n_skip_tie, n_skip_broken))
    print("=" * 100)

    resultados = {}
    for cb in combos:
        ts = filtro(cb)
        m = metricas(ts, "pts_c" if cb == "CLASSIC" else "pts")
        resultados[cb] = (ts, m)
        if m is None:
            print(f"[{cb:9s}] sem trades")
            continue
        netr = m["net"] * VALOR_PONTO
        netl = netr - m["n"] * CUSTO
        print(f"[{cb:9s}] n={m['n']:3d}  WR={m['wr']:5.1f}%  ({m['w']}W/{m['l']}L)  "
              f"PW={m['payoff']:5.2f}  PF={m['pf']:5.2f}  avg_win={m['avg_win']:+7.0f}  "
              f"MAXwin={m['mai_win']:+6.0f}")
        print(f"           net={m['net']:+8.0f} pts (R$ {netr:+8.2f} brut / R$ {netl:+8.2f} liq p/ 1cc)  "
              f"MaxDD={m['mdd']:+8.0f} pts (R$ {m['mdd']*VALOR_PONTO:+.2f})  streak={m['streak']}L")

    print("-" * 100)
    for cb in combos:
        ts, m = resultados[cb]
        if m is None:
            continue
        netr = sum(pts_of(cb, t) for t in ts) * VALOR_PONTO
        netl = netr - len(ts) * CUSTO
        print(f"[{cb:9s}] R$ liquido 1cc (custo R${CUSTO:.2f}): {netl:+.2f}   |  R$ p/ ponto de lucro bruto: {netr:+.2f}")

    # checagem do espelho: BASE (pts) + CLASSIC (pts_c) devem zerar trade a trade
    dif = max(abs(t["pts"] + t["pts_c"]) for t in cands)
    print(f"\nESPELHO verificado: max |BASE.pts + CLASSIC.pts_c| por trade = {dif} pts (deve ser 0)")
    print(f"BASE+CLASSIC by construction: cada dia = espelho exato (SL/TP trocados + direcao invertida).")

    # mes a mes da base vs melhor PF
    def por_mes(ts, col="pts"):
        mm = defaultdict(lambda: [0, 0.0, 0])
        for t in ts:
            mk = t["dia"].strftime("%Y-%m")
            mm[mk][0] += 1
            mm[mk][1] += t[col]
            if t[col] > 0:
                mm[mk][2] += 1
        return mm

    melhor = max([c for c in combos if c != "CLASSIC"], key=lambda cb: (resultados[cb][1]["pf"] if resultados[cb][1] else 0))
    print("-" * 100)
    print("POR MES - BASE:")
    for mk in sorted(por_mes(resultados["BASE"][0])):
        n, pts, w = por_mes(resultados["BASE"][0])[mk]
        print(f"  {mk}: n={n:3d} WR={w/n*100 if n else 0:5.1f}%  pts={pts:+8.1f}  R$1cc={pts*VALOR_PONTO:+9.2f}")
    print(f"\nPOR MES - MELHOR COMBO [{melhor}] (PF {resultados[melhor][1]['pf']:.2f}):")
    for mk in sorted(por_mes(resultados[melhor][0])):
        n, pts, w = por_mes(resultados[melhor][0])[mk]
        print(f"  {mk}: n={n:3d} WR={w/n*100 if n else 0:5.1f}%  pts={pts:+8.1f}  R$1cc={pts*VALOR_PONTO:+9.2f}")
    print(f"\nPOR MES - CLASSICO (espelho):")
    pmc = por_mes(resultados["CLASSIC"][0], "pts_c")
    for mk in sorted(pmc):
        n, pts, w = pmc[mk]
        print(f"  {mk}: n={n:3d} WR={w/n*100 if n else 0:5.1f}%  pts={pts:+8.1f}  R$1cc={pts*VALOR_PONTO:+9.2f}")

    # salvar trades de cada combo
    for cb in combos:
        ts, _ = resultados[cb]
        p = os.path.join(OUT_DIR, f"sete_velas_invertido_{rotulo}_{cb}.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["dia", "direcao", "ups", "dns", "entrada", "alvo", "range", "ema", "acima_ema", "pts", "saida", "pts_c", "saida_c"])
            for t in ts:
                w.writerow([t["dia"].isoformat(), t["dir"], t["ups"], t["dns"], round(t["entrada"], 1),
                            round(t["alvo"], 1), round(t["range"], 1), round(t["ema"], 1),
                            1 if t["acima_ema"] else 0, round(t["pts"], 1), t["saida"],
                            round(t["pts_c"], 1), t["saida_c"]])
    print(f"\nCSVs salvos em {OUT_DIR} (sete_velas_invertido_{rotulo}_*.csv)")


if __name__ == "__main__":
    csv_p = sys.argv[1] if len(sys.argv) > 1 else None
    rotl = sys.argv[2] if len(sys.argv) > 2 else "WIN"
    main(csv_p, rotl)