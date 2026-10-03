# -*- coding: utf-8 -*-
"""
rotular_b1_contrafactual.py — ETAPA I (B1-a)
Rotulo contrafactual da IA primaria: tripla barreira t+12 em M5 sobre WDO$.
Especificacao: ROADMAP secoes 10.1-10.4. READ-ONLY: nao altera o Core, nao vira gate.

Cenario 1: calibra o multiplicador k da barreira superior pela concordancia
com os 242 resultados reais do MT5 (magic 123456, desde 29/07).
Cenario 2: aplica o k vencedor as ~43k decisoes direcionais congeladas ate 02/10
e responde a pergunta binaria da secao 11:
    E_teorica (IA) > E_executada (Core real) -> valor no desacoplamento (gates)
    E_teorica <= 0                            -> sem alpha a resgatar (sinal)
"""
import os
import csv
import json
import numpy as np
from datetime import datetime, timezone, timedelta

BASE = r"C:\AIOFEN"
BRT = timezone(timedelta(hours=-3))
FROZEN = datetime(2026, 10, 2, 23, 59, 59, tzinfo=BRT)  # decisoes ate 02/10 inclusive
T_BARS = 12          # t+12 = 60 min
ATR_WIN = 20         # janela ATR M5 (antes da barra da decisao)
FLOOR = 8.0          # max(1.5*ATR, 8) — regra real do Core
K_CAND = [1.0, 1.5, 2.0, 3.0]
MAGIC = 123456


def parse_ts(s):
    # formato: '2026.07.29 09:41:10' (BRT)
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S").replace(tzinfo=BRT)


def load_bars():
    import MetaTrader5 as mt5
    from datetime import datetime as DD
    if not mt5.initialize():
        raise RuntimeError("MT5 nao inicializou")
    rates = mt5.copy_rates_range("WDO$", mt5.TIMEFRAME_M5, DD(2026, 7, 26), DD(2026, 10, 3))
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError("WDO$ M5 vazio")
    t = np.ascontiguousarray(rates["time"], dtype=np.int64)
    o = rates["open"].astype(np.float64)
    h = rates["high"].astype(np.float64)
    l = rates["low"].astype(np.float64)
    c = rates["close"].astype(np.float64)
    return t, o, h, l, c


def atr_series(h, l, c, win=ATR_WIN):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    cs = np.concatenate([[0.0], np.cumsum(tr)])
    atr = np.full(len(tr), np.nan)
    atr[win - 1:] = (cs[win:] - cs[:-win]) / win
    atr[0] = atr[win - 1]
    i = np.argmax(~np.isnan(atr))
    if i > 0:
        atr[:i] = atr[i]
    return atr


def simul(entry_idx, entry_price, lower, upper, h, l, c, t12=T_BARS):
    """Retorna (label, pnl_pts, mfe, mae, rets). label: +1/-1/0 (expirado)."""
    if entry_idx + t12 > len(c):
        return None
    hi = h[entry_idx:entry_idx + t12]
    lo = l[entry_idx:entry_idx + t12]
    cl = c[entry_idx:entry_idx + t12]
    stop = entry_price - lower
    target = entry_price + upper
    hs = lo <= stop
    ht = hi >= target
    i_stop = int(np.argmax(hs)) if hs.any() else None
    i_tgt = int(np.argmax(ht)) if ht.any() else None
    pnl = float(cl[-1] - entry_price)
    if i_stop is not None or i_tgt is not None:
        cands = []
        if i_stop is not None:
            cands.append((i_stop, -lower))
        if i_tgt is not None:
            cands.append((i_tgt, +upper))
        bi, pnl = min(cands, key=lambda x: x[0])
        if i_stop is not None and i_tgt is not None and i_stop == i_tgt:
            pnl = -lower  # mesma barra: conservador, assume stop
    mfe = float(np.maximum.accumulate(hi)[-1] - entry_price)
    mae = float(entry_price - np.minimum.accumulate(lo)[-1])
    label = 1 if pnl > 0 else (-1 if pnl < 0 else 0)
    rets = cl - entry_price
    return label, pnl, mfe, mae, rets


def load_decisions():
    out = []
    with open(os.path.join(BASE, "decisions_wdo.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            a = r["acao"]
            if a not in ("BUY", "SELL"):
                continue
            ts = parse_ts(r["timestamp"])
            if ts > FROZEN:
                continue
            conf = float(r["confianca"] or 0)
            sgn = 1.0 if a == "BUY" else -1.0
            out.append((int(ts.timestamp()), sgn, conf))
    return out


def load_real_trades():
    import MetaTrader5 as mt5
    from datetime import datetime as DD
    if not mt5.initialize():
        raise RuntimeError("MT5 nao inicializou")
    deals = mt5.history_deals_get(DD(2026, 7, 28), DD(2026, 10, 3))
    trades = []
    aberta = None
    for i in range(len(deals)):
        d = deals[i]
        if d.magic != MAGIC:
            continue
        pnl = float(d.profit)
        if d.entry == 0:
            aberta = (int(d.time), float(d.price), pnl)
        elif d.entry == 1 and aberta is not None:
            ts, price, _ = aberta
            trades.append((ts, price, pnl))
            aberta = None
        elif d.entry == 2:
            trades.append((int(d.time), float(d.price), pnl))
    mt5.shutdown()
    return trades


def bar_index_for(times, ts_epoch):
    return int(np.searchsorted(times, int(ts_epoch)))


def main():
    print("== B1-a: carregando WDO$ M5 e ATR ==")
    t, o, h, l, c = load_bars()
    atr = atr_series(h, l, c)
    print("barras M5:", len(t), "| primeira:", datetime.fromtimestamp(int(t[0]), timezone.utc),
          "| ultima:", datetime.fromtimestamp(int(t[-1]), timezone.utc))

    print("== trades reais do Core (magic %d) ==" % MAGIC)
    trades = load_real_trades()
    print("trades reais emparelhados:", len(trades))
    reais_pnl = np.array([x[2] for x in trades], dtype=np.float64)
    sign_real = np.sign(reais_pnl)

    print("== CALIBRACAO k pela concordancia ==")
    best = (-1, None, None)
    calib = {}
    for k in K_CAND:
        ac = []
        match = 0
        tot = 0
        for (ets, epr, rpnl) in trades:
            # barra que CONTEM a entrada = insercao - 1 (d.time e epoch UTC, mesmo eixo das barras);
            # sim inicia na abertura da barra seguinte (mesma convencao das decisoes)
            b0 = max(bar_index_for(t, ets) - 1, 0)
            if b0 + 1 + T_BARS > len(c):
                continue
            lower = max(1.5 * float(atr[max(b0 - 1, 0)]), FLOOR)
            upper = k * lower
            sim = simul(b0 + 1, epr, lower, upper, h, l, c)
            if sim is None:
                continue
            label, spnl, _, _, _ = sim
            tot += 1
            s_sim = np.sign(spnl)
            match += int((s_sim == sign_real[0]) if False else ((s_sim == np.sign(rpnl)) if (s_sim != 0 and np.sign(rpnl) != 0) else (spnl == rpnl)))
        concord = match / tot if tot else 0
        calib[k] = {"n": tot, "concordancia": round(concord, 4)}
        print("k=%.1f : n=%d concordancia=%.1f%%" % (k, tot, 100 * concord))
        if concord > best[0]:
            best = (concord, k, tot)
    k_best = best[1]
    print(">> k vencedor: %.1f (concordancia %.1f%%)" % (k_best, 100 * best[0]))

    print("== aplicando k=%.1f as decisoes direcionais congeladas ==" % k_best)
    dec = load_decisions()
    print("decisoes direcionais ate 02/10:", len(dec))
    linhas = []
    pnls = []
    labels = []
    n_skip = 0
    tarr = t
    for (dts, sgn, conf) in dec:
        b0 = bar_index_for(tarr, dts)
        if b0 + 1 + T_BARS >= len(c):
            n_skip += 1
            continue
        lower = max(1.5 * float(atr[max(b0 - 1, 0)]), FLOOR)
        upper = k_best * lower
        sim = simul(b0 + 1, float(o[b0 + 1]), lower, upper, h, l, c)
        if sim is None:
            n_skip += 1
            continue
        label, pnl, mfe, mae, rets = sim
        linhas.append({
            "timestamp": datetime.fromtimestamp(int(dts), BRT).strftime("%Y-%m-%d %H:%M:%S"),
            "acao": "BUY" if sgn > 0 else "SELL",
            "confianca": round(conf, 4),
            "entry_price": round(float(o[b0 + 1]), 2),
            "lower_pts": round(lower, 2),
            "upper_pts": round(upper, 2),
            "label": label,
            "pnl_pts": round(pnl, 2),
            "mfe_pts": round(mfe, 2),
            "mae_pts": round(mae, 2),
        })
        pnls.append(pnl)
        labels.append(label)
    pnls = np.array(pnls)
    labels = np.array(labels)
    e_teorica_pts = float(np.mean(pnls))
    e_teorica_rs = e_teorica_pts * 10.0
    e_executada_pts = float(np.mean(reais_pnl)) if len(reais_pnl) else 0.0
    e_executada_rs = e_executada_pts * 10.0
    wr_teorica = float(np.mean(labels == 1))
    wr_exec = float(np.mean(sign_real > 0)) if len(sign_real) else 0.0

    print()
    print("== PERGUNTA BINARIA (secao 11) ==")
    print("E_teorica IA  : %+.2f pts / trade (%d decisoes) => R$ %+.2f" % (e_teorica_pts, len(pnls), e_teorica_rs))
    print("E_executada   : %+.2f pts / trade (%d trades)   => R$ %+.2f" % (e_executada_pts, len(trades), e_executada_rs))
    print("WR teorica (label +1): %.1f%% | WR executada: %.1f%% | label 0 (expirado): %.1f%%" % (
        100 * wr_teorica, 100 * wr_exec, 100 * float(np.mean(labels == 0))))
    if e_teorica_pts <= 0:
        veredito = "SEM ALPHA A RESGATAR (E_teorica <= 0): a perda e estrutural do sinal primario."
        cen = "B"
    elif abs(e_teorica_pts) < 1.0:
        veredito = "SINAL INCONCLUSIVO/DENTRO DO RUIDO (|E_teorica| < 1 pt): sem alpha comprovado a resgatar; perda concentrada na execucao mas sem base para condicionar ao gate."
        cen = "B-"
    elif e_teorica_pts > e_executada_pts:
        veredito = "VALOR NO DESACOPLAMENTO: o sinal teorico > executado -> os GATES/EXECUCAO destroem o alpha (adiar pauta p/ 09/10 e aprofundar gates)."
        cen = "A"
    else:
        veredito = "CENARIO INTERMEDIARIO: teorica > 0 porem <= executada -> sinal fraco; investigar antes de condicionar ao gate."
        cen = "A-"
    print("Cenario:", cen)
    print("Veredito:", veredito)

    with_open = os.path.join(BASE, "logs", "b1a_rotulos.csv")
    with open(with_open, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    resumo = {
        "barras_m5": int(len(t)),
        "decisoes_direcionais": len(dec),
        "rotuladas": len(linhas),
        "skipped": n_skip,
        "calibracao_k": calib,
        "k_vencedor": k_best,
        "trades_reais": len(trades),
        "E_teorica_pts": round(e_teorica_pts, 4),
        "E_teorica_RS": round(e_teorica_rs, 2),
        "E_executada_pts": round(e_executada_pts, 4),
        "E_executada_RS": round(e_executada_rs, 2),
        "WR_teorica": round(100 * wr_teorica, 2),
        "WR_executada": round(100 * wr_exec, 2),
        "label0_pct": round(100 * float(np.mean(labels == 0)), 2),
        "cenario": cen,
        "veredito": veredito,
    }
    with open(os.path.join(BASE, "logs", "b1a_resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    print()
    print("gravados: logs/b1a_rotulos.csv (%d linhas) e logs/b1a_resumo.json" % len(linhas))


if __name__ == "__main__":
    main()