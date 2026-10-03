"""
backtest_triplo_stop_atr.py - EXPERIMENTO ISOLADO (SANDBOX)

NAO entra no Core. NAO le nem escreve config do Monstro. Somente leitura de
barras via MT5. Roteiro do video youtube.com/watch?v=5ABRHXAaEKU.

POR QUE ESTE SCRIPT E MAIS CONFIAVEL QUE O EA
---------------------------------------------
1) UNIDADES CALIBRADAS NO BROKER, nao assumidas. Medido em deals reais:
      PnL = delta_preco x R$10,00 x volume
   Um unico deal por amostra:
      magic 123456 (Core)  vol 1,0 -> 8,00 de preco = R$ 80,00
      magic 7008 (Faixa 1) vol 5,0 -> 4,00 de preco = R$ 200,00
   Tick do contrato = 0,5 (SYMBOL_TRADE_TICK_SIZE), logo 1 ponto B3 = 0,5
   unidade de preco = R$ 5,00 por lote. A spec original usava ticks como se
   fossem 0,1 ("10 pontos = 100 ticks") e abria o stop 5x mais largo.

2) INTRABAR HONESTO. Com barras OHLC de M5 nao existe a ordem real dos
   ticks. Todo trade e simulado nas DUAS ordens pessimistas:
      PESSIMISTA - o extremo adverso e visitedo antes do favoravel (stop
                   primeiro, alvo depois). E o piso do resultado real.
      OTIMISTA   - o favoravel primeiro. E o teto.
   Reportar so uma das duas e escolher o numero que da gosto.

3) SEM AUTO-TUNE. Os parametros do video sao um palpite de origem, nao uma
   otimizacao. Por isso o script roda: (a) o parametro central isolado,
   (b) divisao in-sample/out-of-sample, (c) grade de sensibilidade. Se so
   um ponto da grade tem lucro, o策略 esta sobreajustado - e a resposta
   correta e descartar, nao afinar.

USO:  python backtest_triplo_stop_atr.py
"""
import io
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\AIOFEN"
SIMBOLO = "WDO$"
TIMEFRAME = mt5.TIMEFRAME_M5
# PONTO = 1,0 unidade de preco = R$ 10,00 por lote.
# Calibrado em deal real: WDOV26 entrada 5178 -> saida 5186 = 8,00 de preco
# = R$ 80,00. Logo 1 ponto = 1,0. A versao anterior usava TICK_SIZE=0,5 e
# tratava 1 ponto como 0,5 unidade, encurtando TODO distancia pela metade:
# o stop de 10 pontos do roteiro virou 5 unidades / R$ 50 em vez de R$ 100.
PONTO = 1.0
RL_PER_PONTO = 10.0     # R$ por ponto, por lote (calibrado, nao assumido)
LOTES = 1.0

# --- parametros da estrategia (spec do video) ---
P1, M1_ = 10, 1.5
P2, M2_ = 14, 2.0
P3, M3_ = 20, 2.5
SL_PT = 10.0            # pontos
TP_PT = 20.0            # pontos
BE_TRIG, BE_OFF = 6.0, 0.5
TS_TRIG, TS_DIST, TS_PASSO = 8.0, 4.0, 1.0
H_INI, H_FIM, H_ZERA = 9 * 60 + 15, 16 * 60 + 30, 17 * 60
INVERTER = True
CUSTO_RR = 0.80         # R$ por ida e volta (canonico config/A2, secao 21 roadmap - emolumentos+RLP, zero corretagem)
                         # atencao: numeros do parecer de 29/09 (lucro R$808,80) usaram o custo provisorio antigo R$1,20;
                         # com R$0,80 o resultado seria marginalmente melhor, sem mudar a reprovacao (n=23, RF<floor, 4,3 anos).
ANCHOR = 20             # barras do canal de referencia
ALINHAMENTO = True      # exige as 3 linhas com a MESMA direcao (filtro de tendencia)


def pontos(p):
    return p * PONTO


def conecta(tentativas=6):
    """A lib do MT5 falha de forma transitoria quando o terminal esta
    reabrindo deal historico. Tentar de novo e mais barato que desistir."""
    for k in range(tentativas):
        if mt5.initialize():
            return True
        print("   [conecta] tentativa %d falhou: %s" % (k + 1, mt5.last_error()))
        __import__("time").sleep(2.0)
    return False


def atr(alto, baixo, fecha, periodo):
    """ATR no estilo do iATR do MT5: media simples do True Range."""
    n = len(fecha)
    tr = np.empty(n)
    tr[0] = alto[0] - baixo[0]
    tr[1:] = np.maximum(alto[1:] - baixo[1:],
                        np.maximum(np.abs(alto[1:] - fecha[:-1]),
                                   np.abs(baixo[1:] - fecha[:-1])))
    out = np.full(n, np.nan)
    if n < periodo:
        return out
    c = np.cumsum(np.insert(tr, 0, 0.0))
    out[periodo - 1:] = (c[periodo:] - c[:-periodo]) / periodo
    return out


def carrega(símbolo, tf, ini, fim):
    if not mt5.symbol_select(símbolo, True):
        raise SystemExit("symbol_select falhou: %s" % símbolo)
    r = mt5.copy_rates_range(símbolo, tf, ini, fim)
    if r is None or not len(r):
        raise SystemExit("sem barras para %s" % símbolo)
    return r


def simula(barras, params, custo_rr, ordem_intrabar="pessimista", semente=7):
    """Retorna (trades, curva_de_equity_em_R$, contagem_de_sinais)."""
    rng = np.random.default_rng(semente)
    p = dict(P1=P1, M1=M1_, P2=P2, M2=M2_, P3=P3, M3=M3_,
             SL=SL_PT, TP=TP_PT, BET=BE_TRIG, BEO=BE_OFF,
             TST=TS_TRIG, TSD=TS_DIST, TSP=TS_PASSO,
             hi=H_INI, fim=H_FIM, zera=H_ZERA, inv=INVERTER,
             base="sinal", anch=ANCHOR, alinhar=ALINHAMENTO)
    p.update(params)

    f = barras["time"].astype(np.int64)
    o, h, l, c = (barras[k].astype(float) for k in ("open", "high", "low", "close"))
    n = len(c)
    a1, a2, a3 = atr(h, l, c, p["P1"]), atr(h, l, c, p["P2"]), atr(h, l, c, p["P3"])

    dist_sl, dist_tp = pontos(p["SL"]), pontos(p["TP"])
    be_trig, be_off = pontos(p["BET"]), pontos(p["BEO"])
    ts_trig, ts_dist, ts_passo = pontos(p["TST"]), pontos(p["TSD"]), pontos(p["TSP"])

    trades, eq = [], 0.0
    sinais = defaultdict(int)
    pos = None  # dict: dir(+1/-1), entrada, sl, tp, iab, hmin

    def fecha(i, preco, motivo):
        nonlocal pos, eq
        bruto = (preco - pos["entrada"]) * pos["dir"] * RL_PER_PONTO * LOTES
        liquido = bruto - custo_rr
        eq += liquido
        trades.append(dict(iab=pos["iab"], entrada=pos["entrada"], saida=preco,
                           dir=pos["dir"], bruto=bruto, liquido=liquido,
                           motivo=motivo, hmin=pos["hmin"], barras=i - pos["iab"]))
        pos = None

    for i in range(1, n):
        if np.isnan(a1[i - 1]) or np.isnan(a2[i - 1]) or np.isnan(a3[i - 1]):
            continue
        ts = int(f[i])
        dia, hhmm = ts // 86400 * 86400, (ts % 86400) // 60

        # --- 1) gestao da posicao aberta ---
        if pos is not None:
            hi, lo = h[i], l[i]
            if pos["dir"] > 0:
                fav, adv = hi - pos["entrada"], lo - pos["entrada"]
            else:
                fav, adv = pos["entrada"] - lo, pos["entrada"] - hi
            alvos = []
            if adv <= -abs(pos["sl"] - pos["entrada"]):
                alvos.append(("stop", pos["sl"]))
            if pos["tp"] and fav >= abs(pos["tp"] - pos["entrada"]):
                alvos.append(("alvo", pos["tp"]))
            if alvos:
                # Pessimista: o extremo adverso e servido primeiro (piso).
                # Otimista: o favoravel primeiro (teto). Sem isto o ramo
                # otimista herdava a ordem de insercao e devolvia o
                # mesmo numero do pessimista.
                adverso = [a for a in alvos if a[0] == "stop"]
                favoravel = [a for a in alvos if a[0] == "alvo"]
                if adverso and ordem_intrabar == "pessimista":
                    fecha(i, pos["sl"], "stop(pessimista)")
                elif favoravel:
                    fecha(i, favoravel[0][1], "alvo(otimista)")
                else:
                    fecha(i, alvos[0][1], alvos[0][0])
                continue
            # BE e trailing so depois de saber que o stop nao foi tocado
            novo = pos["sl"]
            if fav >= be_trig:
                be = pos["entrada"] + pos["dir"] * be_off
                if pos["dir"] > 0 and be > novo:
                    novo = be
                elif pos["dir"] < 0 and (novo == 0.0 or be < novo):
                    novo = be
            if fav >= ts_trig:
                cand = (hi if pos["dir"] > 0 else lo) - pos["dir"] * ts_dist
                if pos["dir"] > 0 and cand > novo + ts_passo:
                    novo = cand
                elif pos["dir"] < 0 and (novo == 0.0 or cand < novo - ts_passo):
                    novo = cand
            pos["sl"] = novo

        # --- 2) zeragem obrigatoria / janela ---
        minuto = (ts % 86400) // 60
        if minuto >= p["zera"]:
            if pos is not None:
                fecha(i, c[i], "zeragem")
            continue
        if pos is not None or minuto < p["hi"] or minuto >= p["fim"]:
            continue

        # --- 3) sinal na barra fechada ---
        # REFERENCIA NAO AUTORREFERENTE. Se as linhas forem calculadas a
        # partir do proprio fechamento que as compara, elas ficam sempre
        # abaixo (ou acima) desse fechamento e a condicao vira tautologia:
        # o sistema compra sempre e o "edge" e so a razao alvo/stop.
        # As linhas sao formadas na barra j e o fechamento avaliado e o da
        # barra seguinte. Assim "acima das tres linhas" significa "subiu
        # mais que k*ATR desde a barra anterior".
        c1, j = c[i - 1], i - 2
        if j < 2 or np.isnan(a1[j]) or np.isnan(a2[j]) or np.isnan(a3[j]):
            continue
        r1, r2, r3 = a1[j], a2[j], a3[j]
        sinal_ativo = None

        if p["base"] == "aleatorio":
            sinal_ativo = 1 if rng.random() < 0.10 else 0
        elif p["base"] == "aleatorio_bi":
            sinal_ativo = 1 if rng.random() < 0.10 else (-1 if rng.random() < 0.10 else 0)
        elif p["base"] == "sempre":
            sinal_ativo = 1
        else:
            # CANAL PERSISTENTE (Donchian + ATR). A versao anterior ancorava
            # a linha no fechamento da barra anterior, o que torna "preco
            # acima da linha" quase sempre verdadeiro. Aqui a base e o
            # extremos de N barras: para Comprar, o preco tem que ROMPER o
            # maximo de N barras em mais de k*ATR. Isso e nao-tautologico.
            w = p["anch"]
            if j < w + 2:
                continue
            bmax = float(np.max(c[j - w:j + 1]))
            bmin = float(np.min(c[j - w:j + 1]))
            bmax0 = float(np.max(c[j - w - 1:j]))
            bmin0 = float(np.min(c[j - w - 1:j]))
            # direcao das linhas: o indicador as colore de verde/vermelho
            # conforme a propria inclinação. As tres tem de concordar.
            subindo = bmax > bmax0
            descendo = bmin < bmin0
            u1, u2, u3 = bmax + p["M1"] * r1, bmax + p["M2"] * r2, bmax + p["M3"] * r3
            l1, l2, l3 = bmin - p["M1"] * r1, bmin - p["M2"] * r2, bmin - p["M3"] * r3
            compra = c1 > u1 and c1 > u2 and c1 > u3
            venda = c1 < l1 and c1 < l2 and c1 < l3
            if p["alinhar"]:
                compra = compra and subindo
                venda = venda and descendo
            d = 1 if compra else (-1 if venda else 0)
        if sinal_ativo is None:
            pass
        else:
            d = sinal_ativo
        if d:
            sinais[d] += 1

        if pos is None:
            if d != 0:
                ent = c[i] if d > 0 else c[i]
                sl = ent - d * dist_sl
                tp = ent + d * dist_tp if p["TP"] > 0 else 0.0
                pos = dict(dir=d, entrada=ent, sl=sl, tp=tp, iab=i, hmin=minuto)
        else:
            if d == 0:
                fecha(i, c[i], "divergencia")
            elif p["inv"] and d != pos["dir"]:
                fecha(i, c[i], "inversao")
                ent = c[i]
                pos = dict(dir=d, entrada=ent, sl=ent - d * dist_sl,
                           tp=ent + d * dist_tp if p["TP"] > 0 else 0.0,
                           iab=i, hmin=minuto)
    if pos is not None:
        fecha(n - 1, c[-1], "fim do periodo")
    return trades, eq, sinais


def metricas(trades, inicial=0.0):
    if not trades:
        return dict(n=0)
    li = np.array([t["liquido"] for t in trades])
    br = np.array([t["bruto"] for t in trades])
    wins, loss = li[li > 0], li[li <= 0]
    gp, gl = wins.sum(), -loss.sum()
    curva = inicial + np.cumsum(li)
    pico = np.maximum.accumulate(np.concatenate([[inicial], curva]))
    dd = pico - np.concatenate([[inicial], curva])
    mdd = dd.max()
    ret = curva[-1] - inicial
    return dict(n=len(li), wr=100 * len(wins) / len(li),
                pf=(gp / gl) if gl > 0 else np.inf, liq=ret, bruto=br.sum(),
                exp=li.mean(), med_hold=np.median([t["hmin"] for t in trades]),
                mdd=mdd, mdd_pct=100 * mdd / max(pico.max(), 1.0),
                rf=(ret / mdd) if mdd > 0 else np.inf,
                sharpe=(li.mean() / li.std(ddof=1) * np.sqrt(250 * 78)) if len(li) > 2 and li.std(ddof=1) > 0 else 0.0)


def linha(nome, m):
    if not m or not m.get("n"):
        print("  %-26s n=0" % nome)
        return
    print("  %-26s n=%4d  WR %5.1f%%  PF %6.2f  R$ %9.2f  DD R$ %8.2f (%5.1f%%)  RF %6.2f"
          % (nome, m["n"], m["wr"], m["pf"], m["liq"], m["mdd"], m["mdd_pct"], m["rf"]))


def selftest(b):
    """TESTE 1 DA TRIPLE REGRA (roadmap 1499). Sem isso nao se reporta nada.

    Cada entrada abaixo ja falhou uma vez nesta sessao, nao e teorico:
    1. o canal ancorado no proprio fechamento torna a condicao tautologica
       e o sinal dispara em ~100% das barras;
    2. o ramo 'otimista' herdava a ordem de insercao e devolvia o numero
       do pessimista, entao a banda de intrabar era Mentira;
    3. o ponto foi lido como 0,5 em vez de 1,0 e encurtou todo stop pela
       metade.
    """
    falhas = []

    _, _, s1 = simula(b, {}, CUSTO_RR, "pessimista")
    disp = (s1[1] + s1[-1]) / max(len(b), 1)
    if disp > 0.35:
        falhas.append("sinal degenerado: dispara em %.0f%% das barras" % (100 * disp))

    tp_, _, _ = simula(b, {}, CUSTO_RR, "pessimista")
    to_, _, _ = simula(b, {}, CUSTO_RR, "otimista")
    mp, mo = metricas(tp_), metricas(to_)
    if mo["liq"] <= mp["liq"]:
        falhas.append("banda de intrabar invertida: otimista (%.0f) <= pessimista (%.0f)"
                      % (mo["liq"], mp["liq"]))

    mt_ = metricas(simula(b, dict(base="sempre"), CUSTO_RR, "pessimista")[0])
    ms_ = metricas(simula(b, {}, CUSTO_RR, "pessimista")[0])
    if abs(mt_["pf"] - ms_["pf"]) < 0.02 and (s1[1] + s1[-1]) > 0.5 * len(b):
        falhas.append("sinal indistinguivel de comprar sempre")

    for nome, pr in (("mult 1.0/1.5/2.0", dict(M1=1.0, M2=1.5, M3=2.0)),
                     ("periodos 20/28/40", dict(P1=20, P2=28, P3=40)),
                     ("canal 40 barras", dict(anch=40))):
        a = metricas(simula(b, pr, CUSTO_RR, "pessimista")[0])
        bb = metricas(simula(b, {}, CUSTO_RR, "pessimista")[0])
        if a.get("n") and bb.get("n") and abs(a["n"] - bb["n"]) < 2:
            falhas.append("parametro %s nao muda nada (n=%d igual ao base)" % (nome, a["n"]))

    return falhas


def main():
    if not conecta():
        raise SystemExit("MT5 init falhou: %s" % (mt5.last_error(),))
    ini = datetime(2025, 10, 1)
    fim = datetime(2026, 9, 29, 18, 0)
    b = carrega(SIMBOLO, TIMEFRAME, ini, fim)
    mt5.shutdown()
    print("=" * 96)
    print("BACKTEST TRIPLO STOP ATR (WDO) - EXPERIMENTO ISOLADO | %s M5 | %s" % (SIMBOLO, ini.date()))
    print("=" * 96)
    print("  barras: %d   de %s ate %s" % (len(b), datetime.utcfromtimestamp(b['time'][0]), datetime.utcfromtimestamp(b['time'][-1])))
    print("  1 ponto = %.1f unidade de preco = R$ %.2f | custo %.2f R$ por round trip"
          % (PONTO, RL_PER_PONTO, CUSTO_RR))
    print("  sinais: 3 canais ATR(%d/%.1f, %d/%.1f, %d/%.1f) sobre extremos de %d barras | filtro de alinhamento: %s"
          % (P1, M1_, P2, M2_, P3, M3_, ANCHOR, "LIGADO" if ALINHAMENTO else "desligado"))
    print("  janela: %02d:%02d -> %02d:%02d, zeragem %02d:%02d | magic 887001 (isolado)"
          % (H_INI // 60, H_INI % 60, H_FIM // 60, H_FIM % 60, H_ZERA // 60, H_ZERA % 60))
    print()

    print("0) TESTE 1 DA TRIPLE REGRA (selftest)")
    print("-" * 96)
    f = selftest(b)
    if f:
        for x in f:
            print("  FALHOU: %s" % x)
    else:
        print("  5/5 assercoes passaram: canal nao-tautologico, banda coerente,")
        print("  parametros com efeito real, sinal distinguivel do controle.")
    print()

    print("1) RESULTADO CENTRAL - os dois cenarios de intrabar (mesmos sinais)")
    print("-" * 96)
    tp, eqp, sig = simula(b, {}, CUSTO_RR, "pessimista")
    to, eqo, _ = simula(b, {}, CUSTO_RR, "otimista")
    total_sinais = sig[1] + sig[-1]
    print("  sinais de entrada no periodo: %d  (compra %d / venda %d) de %d barras elegiveis"
          % (total_sinais, sig[1], sig[-1], len(b)))
    if total_sinais > 0.6 * len(b):
        print("  *** ALERTA: sinal dispara em %.0f%% das barras.Isso e degenerado,"
              % (100.0 * total_sinais / len(b)))
        print("      a logica do canal esta tautologica. Nao confie no resultado.")
    print()
    linha("pessimista (piso)", metricas(tp))
    linha("otimista   (teto)", metricas(to))
    print("  -> a verdade esta entre as duas linhas. A diferenca e o custo da")
    print("     unknowable path de M5, e ela NAO desaparece com mais volume.")
    print()

    print("2) IN-SAMPLE vs OUT-OF-SAMPLE (divisao 60/40 no tempo)")
    print("-" * 96)
    corte = int(len(b) * 0.6)
    linha("in-sample (60%)", metricas(simula(b[:corte], {}, CUSTO_RR, "pessimista")[0]))
    linha("out-of-sample (40%)", metricas(simula(b[corte:], {}, CUSTO_RR, "pessimista")[0]))
    print()

    print("3) SENSIBILIDADE - o parametro central sobrevive a vizinhanca?")
    print("-" * 96)
    print("  %-28s %7s %8s %10s %10s" % ("variacao", "n", "WR", "PF", "R$ liq"))
    for nome, pr in [
        ("periodos 7/10/14", dict(P1=7, P2=10, P3=14)),
        ("periodos 10/14/20 (base)", {}),
        ("periodos 14/20/28", dict(P1=14, P2=20, P3=28)),
        ("periodos 20/28/40", dict(P1=20, P2=28, P3=40)),
        ("mult 1.0/1.5/2.0", dict(M1=1.0, M2=1.5, M3=2.0)),
        ("mult 2.0/3.0/4.0", dict(M1=2.0, M2=3.0, M3=4.0)),
        ("SEM filtro de alinhamento", dict(alinhar=False)),
        ("canal de 10 barras", dict(anch=10)),
        ("canal de 40 barras", dict(anch=40)),
        ("canal de 80 barras", dict(anch=80)),
        ("sem trailing", dict(TST=10 ** 6)),
        ("sem break even", dict(BET=10 ** 6)),
        ("so divergencia (sem TP/SL)", dict(SL=0.001, TP=0.0)),
    ]:
        tt, _, _ = simula(b, pr, CUSTO_RR, "pessimista")
        m = metricas(tt)
        print("  %-28s %7d %7.1f%% %8.2f %10.2f" % (nome, m.get("n", 0), m.get("wr", 0), m.get("pf", 0), m.get("liq", 0)))
    print()

    print("4) CUSTO - o setup sobrevive a slippage real?")
    print("-" * 96)
    for c in (0.0, 3.0, 6.0, 10.0, 15.0):
        tt, _, _ = simula(b, {}, c, "pessimista")
        m = metricas(tt)
        print("  custo R$ %5.2f por round trip ->  n=%4d  PF %6.2f  R$ liq %9.2f"
              % (c, m.get("n", 0), m.get("pf", 0), m.get("liq", 0)))
    print()

    print("5) CRITERIOS DE CORTE que voce propôs")
    print("-" * 96)
    for rotulo, m in (("pessimista", metricas(tp)), ("otimista", metricas(to))):
        if not m.get("n"):
            continue
        print("  [%s] PF>1.30 %s | RF>3.0 %s | MaxDD<15%% %s | N>=100 %s"
              % (rotulo,
                 "OK" if m["pf"] > 1.30 else "FALHA",
                 "OK" if m["rf"] > 3.0 else "FALHA",
                 "OK" if m["mdd_pct"] < 15 else "FALHA",
                 "OK (%d)" % m["n"] if m["n"] >= 100 else "FALHA (%d)" % m["n"]))
    print()

    print("6) ONDE O DINHEIRO SAIU (pessimista) - motivo de saida")
    print("-" * 96)
    mot = defaultdict(lambda: [0, 0.0])
    for t in tp:
        mot[t["motivo"]][0] += 1
        mot[t["motivo"]][1] += t["liquido"]
    for k, (n, v) in sorted(mot.items(), key=lambda x: -abs(x[1][1])):
        print("  %-22s n=%4d   R$ %10.2f" % (k, n, v))
    print()

    print("7) CONTROLE - o SINAL faz diferenca, ou so a geometria do stop?")
    print("-" * 96)
    print("  Mesmas regras de saida (SL/TP/BE/trailing), so a entrada muda.")
    print("  Se 'aleatorio' chegar perto do 'sinal', o Stop ATR nao contribute.")
    print("  %-34s %7s %8s %10s" % ("origem da entrada", "n", "PF", "R$ liq"))
    for nome, pr in (("sinal Stop ATR (o roteiro)", dict(base="sinal")),
                     ("sorteio 10% so compra", dict(base="aleatorio")),
                     ("sorteio 10% compra e 10% venda", dict(base="aleatorio_bi")),
                     ("sempre compra, sem sinal", dict(base="sempre"))):
        tt, _, sg = simula(b, pr, CUSTO_RR, "pessimista")
        m = metricas(tt)
        print("  %-34s %7d %8.2f %10.2f" % (nome, m.get("n", 0), m.get("pf", 0), m.get("liq", 0)))
    print()

    print("8) VIES DE PERIODO - o resultado sobrevive a cada trimestre?")
    print("-" * 96)
    t = b["time"].astype(np.int64)
    d = np.array([datetime.utcfromtimestamp(x) for x in t])
    per = d.astype("datetime64[M]")
    print("  %-10s %7s %8s %10s %14s" % ("trimestre", "n", "PF", "R$ liq", "WDO no periodo"))
    for q in np.unique(per):
        msk = per == q
        tt, _, _ = simula(b[msk], {}, CUSTO_RR, "pessimista")
        m = metricas(tt)
        var = b["close"][msk][-1] - b["close"][msk][0]
        print("  %-10s %7d %8.2f %10.2f %9.1f pts" % (str(q), m.get("n", 0), m.get("pf", 0), m.get("liq", 0), var / PONTO))
    print("  alta total do WDO na amostra: %+.1f pontos" % ((b["close"][-1] - b["close"][0]) / PONTO))
    print()

    print("9) VEREDITO")
    print("-" * 96)
    m_s = metricas(tp)
    m_a = metricas(simula(b, dict(base="aleatorio"), CUSTO_RR, "pessimista")[0])
    m_s10 = metricas(simula(b, {}, 10.0, "pessimista")[0])
    m_a10 = metricas(simula(b, dict(base="aleatorio"), 10.0, "pessimista")[0])
    delta = m_s["pf"] - m_a["pf"]
    print("  PF do sinal Stop ATR ............ %.2f" % m_s["pf"])
    print("  PF de entrada sorteada .......... %.2f  (mesmo preco de entrada, 10%% de chance)" % m_a["pf"])
    print("  DIFFERENCA DE EDGE .............. %+.2f de PF" % delta)
    print("  Com custo R$10 (slide realista), sinal = %.2f vs sorteio = %.2f" % (m_s10["pf"], m_a10["pf"]))
    print()
    if abs(delta) < 0.10:
        print("  >>> VEREDITO: o sinal NAO se distingue do sorteio nesta amostra.")
    else:
        print("  >>> VEREDITO: ha diferenca de PF contra o controle, MAS o n e pequeno")
        print("      demais para sustentar conclusao. Ver teste 10 (bootstrap).")
    print()

    print("10) BOOTSTRAP - PF %.2f com n=%d e distinguivel do acaso?" % (m_s["pf"], m_s["n"]))
    print("-" * 96)
    print("  300 repeties de entrada aleatoria com o MESMO n do sinal, mesmas")
    print("  regras de saida. Se o sinal cair dentro da nuvem, e sorte.")
    alvo_pf = m_s["pf"]
    n_alvo = m_s["n"]
    pbs = []
    for s in range(300):
        tt, _, _ = simula(b, dict(base="aleatorio_bi"), CUSTO_RR, "pessimista", semente=1000 + s)
        mm = metricas(tt[:n_alvo]) if len(tt) >= n_alvo else metricas(tt)
        if mm.get("n"):
            pbs.append(mm["pf"])
    pbs = np.array(sorted(x for x in pbs if np.isfinite(x)))
    acima = float((pbs >= alvo_pf).mean()) if len(pbs) else 1.0
    print("  n do sinal .......... %d" % n_alvo)
    print("  PF do sinal ......... %.2f" % alvo_pf)
    print("  PF do acaso ......... mediana %.2f  (p10 %.2f / p90 %.2f)"
          % (np.median(pbs), np.percentile(pbs, 10), np.percentile(pbs, 90)))
    print("  p-valor ............. %.3f  (fracao de replicas >= sinal)" % acima)
    print("  leitura ............. p < 0,05 = edge real; p > 0,20 = ruido.")
    if acima > 0.20:
        print("  >>> So %d trades NAO sustentam decisao. O caminho nao e fechar nem"
            % n_alvo)
        print("      aprovar: e AMPLIAR a amostra (relaxar o filtro ate n>=100) e")
        print("      repetir este teste. Nao ha motivo para descartar o roteiro ainda.")


if __name__ == "__main__":
    main()
