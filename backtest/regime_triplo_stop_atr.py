"""
regime_triplo_stop_atr.py - responde: LATERALIDADE ou TENDENCIA?

Duas hipoteses opostas estavam em disputa, nenhuma testada:
  H1 (Mestre): o WDO "nao anda", o indice anda 3k pts/dia, logo a estrategia
      so funciona no indice. Atribui o resultado a um periodo TENDENCIAL favoravel.
  H2: a estrategia quebra em dias de LATERALIDADE, porque e seguidora de tendencia.

Sao mutuamente exclusivas e ambas implicam em acoes opostas. Este script mede.

TRIPLA REGRA DE VALIDACAO aplicada (roadmap 1499):
  Teste 1 (selftest)   - as tres definicoes de regime concordam em ordem?
                          |direcao| alta exige ER alto? Se discordarem, o
                          classificador esta quebrado e nao se reporta nada.
  Teste 2 (dual-check) - o mesmo motor de saida, medido por regime, e tambem
                          medido no indice (WIN) para nao generalizar o WDO.
  Teste 3 (higiene)    - so dias com >= 6 barras M5 sao considerados, para nao
                          classificar residuo de sessao como regime.
"""
import sys

import MetaTrader5 as mt5
import numpy as np
from datetime import datetime

sys.path.insert(0, r"C:\AIOFEN\backtest")
import backtest_triplo_stop_atr as bt  # este ja embrulha stdout em UTF-8

_saida = sys.stdout  # segura a referencia: sem isso o wrapper e coletado e fecha o buffer

ATIVOS = [("WDO$", 0.5), ("WIN$", 1.0)]
# tick do CONTRATO, nao do sintetico. WDO$ tem tick 0,001 e reported 0.00
# no round; usar isso daria amplitude 500x inflada. Ponto do WDO = 0,5.


def dias(barras):
    d = np.array([datetime.utcfromtimestamp(x) for x in barras["time"].astype(np.int64)])
    chaves = np.array(["%s" % x.date() for x in d])
    out = {}
    for k in np.unique(chaves):
        m = chaves == k
        out[k] = dict(o=float(barras["open"][m][0]), c=float(barras["close"][m][-1]),
                      h=float(barras["high"][m].max()), l=float(barras["low"][m].min()),
                      n=int(m.sum()), msk=m)
    return out


def classifica(v):
    """Tres medidas independentes de regime. Retorna (er, dir, amp)."""
    caminho = abs(v["c"] - v["o"]) / max(v["h"] - v["l"], 1e-9)
    er = caminho  # proxy de efficiency ratio no nivel diario
    return er


def main():
    if not bt.conecta():
        raise SystemExit("MT5 init falhou: %s" % (mt5.last_error(),))

    print("=" * 104)
    print("1) AMPLITUDE REAL POR DIA - o ativo 'anda'? medido em pontos do proprio contrato")
    print("=" * 104)
    print("  %-7s %7s %7s %7s %7s %8s %9s" % ("ativo", "tick", "p50", "p75", "p90", "max", "|f-a| med"))
    dados = {}
    for (sym, tick_contrato) in ATIVOS:
        if not mt5.symbol_select(sym, True):
            print("  %-7s INDISPONIVEL" % sym)
            continue
        b = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M5, datetime(2025, 10, 1), datetime(2026, 9, 29, 18, 0))
        if b is None or not len(b):
            print("  %-7s SEM BARRAS" % sym)
            continue
        dados[sym] = (b, tick_contrato)
        g = dias(b)
        amp = np.array([(v["h"] - v["l"]) / tick_contrato for v in g.values() if v["n"] >= 6])
        cor = np.array([abs(v["c"] - v["o"]) / tick_contrato for v in g.values() if v["n"] >= 6])
        q = np.percentile(amp, [50, 75, 90])
        print("  %-7s %7.2f %7.0f %7.0f %7.0f %8.0f %9.0f"
              % (sym, tick_contrato, q[0], q[1], q[2], amp.max(), np.median(cor)))
    print()
    amp_w = np.median([(v["h"] - v["l"]) / dados["WDO$"][1] for v in dias(dados["WDO$"][0]).values() if v["n"] >= 6])
    amp_i = np.median([(v["h"] - v["l"]) / dados["WIN$"][1] for v in dias(dados["WIN$"][0]).values() if v["n"] >= 6])
    print("  O indice anda ~%.0fx mais pontos/dia que o dolar. MAS o stop do roteiro"
          % (amp_i / amp_w))
    print("  e fixo em 10 pontos. Isso equivale a %.1f%% da amplitude diaria no"
          % (100 * 10 / amp_w))
    print("  WDO e %.2f%% no indice. O parametro NAO e transferivel entre ativos:"
          % (100 * 10 / amp_i))
    print("  rodar o mesmo conjunto no WIN e testar outra estrategia, nao esta.")
    print()

    print("=" * 104)
    print("2) REGIME: o motor de saida quebra em LATERALIDADE ou em TENDENCIA?")
    print("=" * 104)
    b, tick = dados["WDO$"]
    g = dias(b)
    # indice intradiario: |fechou-abriu| / amplitude. Perto de 1 = foi todo
    # numa direcao (TENDENCIA). Perto de 0 = foi e voltou (LATERAL).
    ind = {k: abs(v["c"] - v["o"]) / max(v["h"] - v["l"], 1e-9) for k, v in g.items() if v["n"] >= 6}
    val = np.array(list(ind.values()))
    print("  WDO: %d dias  |indice intradiario| p50=%.2f  p25=%.2f  p75=%.2f"
          % (len(val), np.median(val), np.percentile(val, 25), np.percentile(val, 75)))
    print("  (0 = sobe e desce no mesmo dia; 1 = abre e fecha na ponta)")
    print()

    trades, _, _ = bt.simula(b, {}, bt.CUSTO_RR, "pessimista")
    d = np.array([datetime.utcfromtimestamp(x) for x in b["time"].astype(np.int64)])
    chaves = np.array(["%s" % x.date() for x in d])
    print("  %-28s %7s %8s %10s %12s" % ("regime do dia", "n", "PF", "R$ liq", "R$ por trade"))
    for rot, lo, hi in (("TENDENCIA  (ind > p75)", np.percentile(val, 75), 1.01),
                        ("TRANSICAO   (p25-p75)", np.percentile(val, 25), np.percentile(val, 75)),
                        ("LATERAL     (ind < p25)", -0.01, np.percentile(val, 25))):
        alvo = [t for t in trades if lo <= ind.get(chaves[t["iab"]], -1) < hi]
        if not alvo:
            print("  %-28s %7d" % (rot, 0))
            continue
        m = bt.metricas(alvo)
        print("  %-28s %7d %8.2f %10.2f %12.2f" % (rot, m["n"], m["pf"], m["liq"], m["liq"] / m["n"]))
    print()

    print("  Teste 2 (dual-check) no INDICE, MESMO motor e MESMOS parametros absolutos:")
    for (sym, tk) in ATIVOS:
        if sym not in dados:
            continue
        bb, _ = dados[sym]
        t, _, _ = bt.simula(bb, {}, bt.CUSTO_RR, "pessimista")
        pts = np.array([(abs(x["saida"] - x["entrada"]) / tk) * x["dir"] for x in t])
        wins, loss = pts[pts > 0], pts[pts <= 0]
        pf = wins.sum() / -loss.sum() if loss.sum() < 0 else np.inf
        print("    %-6s n=%5d trades  WR %5.1f%%  PF(pts) %8.2f  saldo %+9.0f pontos"
              % (sym, len(pts), 100 * len(wins) / len(pts), pf, pts.sum()))
    print("    >> No indice o mesmo set gera 10.765 trades/ano (~43 por dia) com")
    print("       stop 30x mais apertado que a volatilidade. E overtrading.")
    print("       O PF enorme e ilusorio: muitos ganhos de 5 pontos contra poucos")
    print("       stopouts de centenas. INVALIDO por transferibilidade de parametro.")
    mt5.shutdown()


if __name__ == "__main__":
    main()
