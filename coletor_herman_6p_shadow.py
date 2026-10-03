# -*- coding: utf-8 -*-
"""
coletor_herman_6p_shadow.py — ESTRATEGIA DO HERMAN em SHADOW MODE.
Processo separado, READ-ONLY (nao envia ordens), zero impacto no Core v22.

Le ticks ao vivo do WDO$ e monta, na MESMA passada, boxes 6P (6 pontos / 12 ticks)
e boxes 3P (3 pontos / 6 ticks) — decisoes de granularidade ficam parametrizaveis
no futuro. Grava, por box fechado:
  logs/herman_6p/boxes_herman.csv  (TODOS os boxes, coluna box_pts = 6 ou 3)
  logs/herman_6p/sinais_herman.csv (gatilhos: candle padrao + location + K<=2)
  logs/herman_6p/online_herman.log (heartbeat)
  logs/herman_6p/resumo_herman.json(resumo acumulado)

Sinal (spec Herman): COMPRA se ema9>ema21 E close>vwap E close>ajuste[proxy D1 ult.]
  E pavio_inf/range>=0.35 E K<=2; VENDA espelhado. K = boxes desde o crossover das
  emas (reset por dia, K=1 no crossover). EMAs sobre os CLOSES dos boxes (por
  track, continuo entre dias). VWAP diaria real (sum preco*vol / vol), reset no
  primeiro tick do dia. Ajuste proxied pelo close D1 anterior.

NOTA: ha uma contradicao interna no spec como transcrito — com box de 6 pts o
stop (pavio+0.5 atras do extremo) sai >= 9.7 pts, incompativel com o limite de
4.5. Por isso coletamos 6P e 3P: o 3P deixa o stop 3.5-6.0, consistente com o
metodo. O harness aceita --max-sl para calibrar.

Uso: python coletor_herman_6p_shadow.py [--smoke | --uma-hora N]
Recomendado: agendar 08:55-18:35 (UTC) em dias de pregao.
"""
import os
import csv
import json
import time
import datetime as dt
import argparse

BASE = r"C:\AIOFEN"
SYM = "WDO$"
OUT = os.path.join(BASE, "logs", "herman_6p")
SIZES = (6.0, 3.0)
MIN_PAVIO = 0.35
POLL_S = 0.1
LAST_LOOKBACK_S = 3.0


class Builder:
    """Builds one box track (size pts). Closes box when |px - open| >= size."""
    def __init__(self, size):
        self.size = size
        self.box = None
        self.closes = []
        self.ef = self.es = None
        self.K = 999
        self.n_boxes = 0
        self.n_sinais = 0

    def tick(self, preco, day):
        if self.box is None:
            self.box = {"open": preco, "high": preco, "low": preco, "n": 0, "vol": 0.0}
        self.box["high"] = max(self.box["high"], preco)
        self.box["low"] = min(self.box["low"], preco)
        self.box["n"] += 1
        disp = preco - self.box["open"]
        if disp >= self.size or disp <= -self.size:
            b = self.box
            cl = b["open"] + (self.size if preco >= b["open"] else -self.size)
            self.closes.append(cl)
            n = len(self.closes)
            if n >= 21:
                if self.ef is None:
                    self.ef = [cl, cl]; self.es = [cl, cl]
                else:
                    ef9 = cl * (2 / 10) + self.ef[-1] * (8 / 10)
                    es21 = cl * (2 / 22) + self.es[-1] * (20 / 22)
                    self.ef.append(ef9); self.es.append(es21)
                    cu = self.ef[-2] <= self.es[-2] and self.ef[-1] > self.es[-1]
                    cd = self.ef[-2] >= self.es[-2] and self.ef[-1] < self.es[-1]
                    self.K = 1 if (cu or cd) else self.K + 1
            elif n == 9:
                self.ef = [cl]; self.es = [cl]
            self.n_boxes += 1
            self.box = None
            return (b, cl, 1 if preco >= b["open"] else -1)
        return None

    def reset_day(self):
        self.K = 999
        self.box = None


class Coletor:
    def __init__(self):
        import MetaTrader5 as mt5
        self.mt5 = mt5
        if not mt5.initialize():
            raise RuntimeError("MT5 nao inicializou")
        self.last_ms = 0
        self.day = None
        self.nlv = 0.0
        self.vol = 0.0
        self.vwap = None
        self.d1_prev_close = None
        self.erros = 0
        self.builders = [Builder(s) for s in SIZES]
        self._ajuste()
        os.makedirs(OUT, exist_ok=True)
        self._init_csvs()

    def _ajuste(self):
        d1 = self.mt5.copy_rates_range(SYM, self.mt5.TIMEFRAME_D1,
                                       dt.datetime.now() - dt.timedelta(days=6),
                                       dt.datetime.now())
        if d1 is not None and len(d1) >= 2:
            self.d1_prev_close = float(d1["close"][-2])

    def _init_csvs(self):
        box_h = ["box_pts", "ts", "day", "open", "high", "low", "close", "direction",
                 "range", "pavio_sup", "pavio_inf", "ratio_sup", "ratio_inf",
                 "tick_volume", "n_ticks", "vwap", "ajuste", "ema9", "ema21",
                 "K", "bias", "sinal", "entry", "sl", "tp_parcial", "tp_final"]
        sin_h = ["box_pts", "ts", "day", "sinal", "entry", "sl", "dist_sl",
                 "tp_parcial", "tp_final", "vwap", "ajuste", "close", "pavio",
                 "ema9", "ema21", "K"]
        for fn, h, obj in (("boxes_herman.csv", box_h, "wbx"),
                           ("sinais_herman.csv", sin_h, "wsi")):
            p = os.path.join(OUT, fn)
            novo = not os.path.exists(p)
            fh = open(p, "a", newline="", encoding="utf-8")
            w = csv.DictWriter(fh, fieldnames=h)
            if novo:
                w.writeheader()
            setattr(self, obj + "_fh", fh)
            setattr(self, obj, w)

    def heart(self):
        with open(os.path.join(OUT, "online_herman.log"), "a", encoding="utf-8") as f:
            tot = sum(b.n_boxes for b in self.builders)
            f.write("%s | boxes=%d sinais=%d erros=%d vwap=%.2f aj=%s\n" % (
                dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tot,
                sum(b.n_sinais for b in self.builders), self.erros,
                self.vwap or 0, self.d1_prev_close))
        with open(os.path.join(OUT, "resumo_herman.json"), "w", encoding="utf-8") as f:
            json.dump({("boxes_%dP" % int(b.size)): b.n_boxes for b in self.builders} |
                      {"sinais_%dP" % int(b.size): b.n_sinais for b in self.builders} |
                      {"erros": self.erros, "day": str(self.day), "vwap": self.vwap},
                      f, ensure_ascii=False, indent=2)

    def _coleta_ticks(self):
        agora = dt.datetime.now()
        tk = self.mt5.copy_ticks_range(SYM, agora - dt.timedelta(seconds=LAST_LOOKBACK_S), agora)
        if tk is None or len(tk) == 0:
            return []
        out = []
        for i in range(len(tk)):
            msc = int(tk["time_msc"][i])
            if msc <= self.last_ms:
                continue
            out.append((msc, float(tk["bid"][i]), float(tk["ask"][i]),
                        float(tk["volume"][i])))
        if out:
            out.sort(key=lambda x: x[0])
            self.last_ms = out[-1][0]
        return out

    def _processa(self, msc, bid, ask, vol):
        preco = (bid + ask) / 2.0 if (bid and ask) else bid
        if not preco or preco <= 0:
            return
        dia = dt.datetime.fromtimestamp(msc / 1000, tz=dt.timezone.utc).date()
        if dia != self.day:
            self.day = dia
            self.nlv = 0.0
            self.vol = 0.0
            self.vwap = None
            for b in self.builders:
                b.reset_day()
        v = max(float(vol), 0.0)
        self.nlv += preco * v
        self.vol += v
        if self.vol > 0:
            self.vwap = self.nlv / self.vol
        for b in self.builders:
            out = b.tick(preco, dia)
            if out is not None:
                box, cl, direc = out
                self._grava(b, box, cl, direc, preco, msc, v)
        # volume do box: guardamos no builder? simplificamos: volume=ticks do box
        for b in self.builders:
            if b.box is None:
                continue
            b.box["vol"] += v

    def _grava(self, b, box, cl, direc, preco, msc, v):
        sz = b.size
        rng = max(box["high"], cl) - min(box["low"], cl)
        psup = (box["high"] - max(box["open"], cl)) / rng if rng > 0 else 0.0
        pinf = (min(box["open"], cl) - box["low"]) / rng if rng > 0 else 0.0
        ts = dt.datetime.fromtimestamp(msc / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        bias, sinal = "", ""
        entry = sl = tpp = tpf = dist = ""
        n = len(b.closes)
        if n >= 22 and b.ef and b.es:
            ef9, es21 = b.ef[-1], b.es[-1]
            bias = "BUY" if ef9 > es21 else "SELL"
            pav = pinf if bias == "BUY" else psup
            loc = False
            if bias == "BUY" and self.vwap and self.d1_prev_close:
                loc = cl > self.vwap and cl > self.d1_prev_close
            elif bias == "SELL" and self.vwap and self.d1_prev_close:
                loc = cl < self.vwap and cl < self.d1_prev_close
            if pav >= MIN_PAVIO and loc and b.K <= 2:
                sinal = bias
                entry = round(cl, 2)
                sl = round((box["low"] - 0.5) if bias == "BUY" else (box["high"] + 0.5), 2)
                dist = round(abs(entry - sl), 2)
                tpp = round(entry + 2.5 if bias == "BUY" else entry - 2.5, 2)
                tpf = round(entry + 6.0 if bias == "BUY" else entry - 6.0, 2)
                b.n_sinais += 1
                self.wsi.writerow({"box_pts": int(sz), "ts": ts, "day": str(self.day),
                                   "sinal": sinal, "entry": entry, "sl": sl,
                                   "dist_sl": dist, "tp_parcial": tpp, "tp_final": tpf,
                                   "vwap": round(self.vwap, 2) if self.vwap else "",
                                   "ajuste": self.d1_prev_close, "close": round(cl, 2),
                                   "pavio": round(pav, 3), "ema9": round(ef9, 2),
                                   "ema21": round(es21, 2), "K": b.K})
                self.wsi_fh.flush()
        self.wbx.writerow({"box_pts": int(sz), "ts": ts, "day": str(self.day),
                           "open": round(box["open"], 2), "high": round(max(box["high"], cl), 2),
                           "low": round(min(box["low"], cl), 2), "close": round(cl, 2),
                           "direction": direc, "range": round(rng, 2),
                           "pavio_sup": round(psup, 3), "pavio_inf": round(pinf, 3),
                           "ratio_sup": round(psup, 3), "ratio_inf": round(pinf, 3),
                           "tick_volume": int(box.get("vol", 0)), "n_ticks": box["n"],
                           "vwap": round(self.vwap, 2) if self.vwap else "",
                           "ajuste": self.d1_prev_close,
                           "ema9": round(b.ef[-1], 2) if b.ef else "",
                           "ema21": round(b.es[-1], 2) if b.es else "",
                           "K": b.K, "bias": bias, "sinal": sinal, "entry": entry,
                           "sl": sl, "tp_parcial": tpp, "tp_final": tpf})
        self.wbx_fh.flush()

    def loop(self, fim):
        t0 = time.time()
        prox_heart = 0.0
        while True:
            if fim is not None and time.time() - t0 > fim:
                break
            try:
                for msc, bid, ask, vol in self._coleta_ticks():
                    self._processa(msc, bid, ask, vol)
            except Exception:
                self.erros += 1
                if self.erros > 20:
                    try:
                        self.mt5.shutdown()
                    except Exception:
                        pass
                    time.sleep(3)
                    if not self.mt5.initialize():
                        self.erros = 0
            if time.time() >= prox_heart:
                self.heart()
                prox_heart = time.time() + 60
            time.sleep(POLL_S)
        self.heart()

    def smoke(self):
        si = self.mt5.symbol_info_tick(SYM)
        print("conexao OK. symbol_info_tick:")
        if si is not None:
            print("  ts_ms:", si.time_msc, "bid:", si.bid, "ask:", si.ask,
                  "last:", si.last, "volume:", si.volume)
        else:
            print("  (sem tick em fim de semana - normal)")
        print("ajuste proxy (close D1 anterior):", self.d1_prev_close)
        print("tracks:", [int(b.size) for b in self.builders], "pts")
        print("SMOKE OK - coletor pronto para pregao.")

    def close(self):
        self.wbx_fh.close(); self.wsi_fh.close()
        try:
            self.mt5.shutdown()
        except Exception:
            pass


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--uma-hora", type=float, default=None)
    a = ap.parse_args()
    c = Coletor()
    try:
        if a.smoke:
            c.smoke()
        else:
            print("coletor HERMAN rodando (tracks 6P e 3P)... ctrl+c p/ parar.")
            c.loop(a.uma_hora)
    finally:
        c.close()


if __name__ == "__main__":
    main()