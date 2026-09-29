# -*- coding: utf-8 -*-
"""
Validador de geometria do Sub-Trader (Rompimento do Corpo do candle de 1H).

Por que este script existe
--------------------------
Em 29/09/2026 o Sub vendeu (ticket 2540488355) com SL a 0.50x ATR e perdeu
R$ 200. A investigacao gerou tres hipoteses sobre a "entrada correta":

  H1 - comprar no corpo quando o candle e de alta (direcao)
  H2 - o filtro de R/R >= 1.0 teria barrado o trade (filtro)
  H3 - o problema e a GEOMETRIA: stop no pavio oposto e alvo no resto do pavio

H1 foi refutada pelos dados (o candle era de BAIXA; a SELL seguia a cor).
H2 foi refutada pelo log (o R/R ja disparou 16s antes e reprovou outro sinal;
este passou com R/R 3.375).

H3 nao pode ser decidida no olho. Este script mede. Ele testa geometrias
alternativas de stop/alvo sobre as barras M5 reais do MT5 e -- o mais
importante -- testa se o melhor resultado e estatisticamente distinguivel do
acaso. Sem essa etapa, um grid de 36 combinacoes sobre poucas semanas sempre
acha um "vencedor" por ruido (overfitting).

Uso
---
    python backtest/validar_geometria_sub.py
    python backtest/validar_geometria_sub.py --bars 6000
    python backtest/validar_geometria_sub.py --min-n 30 --perm 200000

Regras metodologicas (nao mexer sem motivo)
--------------------------------------------
1. Entrada: rompimento do corpo do candle de 1H (09:00-09:59) dentro da
   janela 10:00-11:06, identica a `rompimento_orquestrador.py`.
2. Quando alvo e stop caem na MESMA barra M5, assume STOP. Backtest
   otimista demais e a forma mais facil de se enganar aqui.
3. O grid SEMPRE imprime a lista completa de configuracoes e o p-valor.
   Se o script so mostrasse a melhor linha, ele seria um gerador de
   confirmacao do dispositivo do operador.
4. Um edge so e declarado se p-valor < 0.05 E n >= --min-n. A configuracao
   que o proprio script reprova continua impressa, com o rotulo.

O que este script NAO faz
-------------------------
Nao le `historico_contexto_wdo.csv`. Aquele arquivo guarda features de book
(bid_qty, entropia_book, rsi_14...) e o reward em R$ ja realizado, para
treinar o Keras. NAO tem OHLC, corpo, pavio, entrada, stop ou alvo -- que e
justamente o que um backtest geometrico precisa. As duas fontes sao
complementares e nao substitutiveis: este script le as barras do MT5.
"""
import argparse
import random
import sys
from collections import defaultdict
from datetime import datetime, time as dtime

# ---------------------------------------------------------------- parametros
JANELA_INI = dtime(10, 0)
JANELA_FIM = dtime(11, 6)
EOD = dtime(17, 30)
HORA_CANDLE = 9
MIN_BARRAS_CANDLE = 12          # 12 x M5 = 09:00-09:59 fechado
RISCO_MINIMO = 0.2              # abaixo disso o stop e spread, nao estrutura

STOPS = (("pavio", "pavio oposto"),
         ("corpo", "corpo inteiro"),
         ("corpo50", "50% corpo"))
MULTS = (1.0, 1.5, 2.0)
WICKS = (0.0, 0.5, 1.0)
SIDES = (("C", "BUY"), ("V", "SELL"))


def carregar_barras(symbol, n):
    """Barras M5 do MT5. Read-only: nao envia ordem, nao altera estado."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 indisponivel. Instale o pacote do terminal MT5.")
        return []
    if not mt5.initialize():
        print("Falha ao conectar ao MT5:", mt5.last_error())
        return []
    raw = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, n)
    if raw is None or len(raw) == 0:
        print("Sem barras retornadas:", mt5.last_error())
        mt5.shutdown()
        return []
    barras = [(datetime.fromtimestamp(int(r["time"])), float(r["open"]),
               float(r["high"]), float(r["low"]), float(r["close"]))
              for r in raw]
    mt5.shutdown()
    barras.sort(key=lambda b: b[0])
    return barras


def agrupar_dias(barras):
    dias = defaultdict(list)
    for b in barras:
        dias[b[0].date()].append(b)
    return dias


def candle_referencia(dia, dias):
    """Candle de 1H agregado das M5 da hora 9, igual a _agrega_h1()."""
    b9 = [b for b in dias.get(dia, []) if b[0].hour == HORA_CANDLE]
    if len({b[0].minute for b in b9}) < MIN_BARRAS_CANDLE:
        return None
    o = b9[0][1]
    h = max(b[2] for b in b9)
    l = min(b[3] for b in b9)
    c = b9[-1][4]
    if h <= l or max(o, c) <= min(o, c):
        return None
    return {"o": o, "h": h, "l": l, "c": c,
            "ct": max(o, c), "cf": min(o, c), "pt": h, "pf": l}


def gatilho(dia, side, dias):
    """Primeira barra na janela 10:00-11:06 que rompe o corpo."""
    ref = candle_referencia(dia, dias)
    if ref is None:
        return None, None
    nivel = ref["ct"] if side == "C" else ref["cf"]
    for b in dias.get(dia, []):
        if not (JANELA_INI <= b[0].time() <= JANELA_FIM):
            continue
        if side == "C" and b[2] >= nivel:
            return b, ref
        if side == "V" and b[3] <= nivel:
            return b, ref
    return None, ref


def resolver(dia, entrada, stop, alvo, side, dias):
    """Caminha as barras ate alvo, stop ou EOD. Alvo e stop na mesma barra -> STOP."""
    for b in dias.get(dia, []):
        if b[0] <= entrada[0] or b[0].date() != dia:
            continue
        if side == "C":
            if b[3] <= stop:
                return "STOP", stop
            if b[2] >= alvo:
                return "ALVO", alvo
        else:
            if b[2] >= stop:
                return "STOP", stop
            if b[3] <= alvo:
                return "ALVO", alvo
        if b[0].time() > EOD:
            return "EOD", b[4]
    return "ABERTO", None


def nivel_stop(kind, ref, side):
    if kind == "pavio":
        return ref["pt"] if side == "C" else ref["pf"]
    if kind == "corpo":
        return ref["cf"] if side == "C" else ref["ct"]
    if kind == "corpo50":
        return (ref["ct"] - 0.10) if side == "C" else (ref["ct"] + 0.10)
    return None


def simular(side, stop_kind, mult, wick_min, dias):
    """Devolve a lista de resultados em pontos (ganho +, perda -)."""
    ops = []
    for dia in sorted(dias):
        ent, ref = gatilho(dia, side, dias)
        if ent is None or ref is None:
            continue
        corpo = abs(ref["ct"] - ref["cf"])
        if corpo <= 0:
            continue
        pav_fav = (ref["pt"] - ref["ct"]) if side == "C" else (ref["cf"] - ref["pf"])
        if wick_min > 0 and (pav_fav / corpo) < wick_min:
            continue
        px = ent[1]
        stop = nivel_stop(stop_kind, ref, side)
        if stop is None:
            continue
        risco = abs(px - stop)
        if risco <= RISCO_MINIMO:
            continue
        alvo = px + mult * risco if side == "C" else px - mult * risco
        res, px_sa = resolver(dia, ent, stop, alvo, side, dias)
        if res == "ABERTO":
            continue
        if res == "ALVO":
            pts = mult * risco
        elif res == "STOP":
            pts = -risco
        else:
            pts = 0.0
        ops.append({"dia": dia, "res": res, "pts": pts, "risco": risco,
                    "px": px, "pav": pav_fav, "corpo": corpo})
    return ops


def estatisticas(ops):
    n = len(ops)
    if n == 0:
        return None
    ganhos = sum(o["pts"] for o in ops if o["pts"] > 0)
    perdas = abs(sum(o["pts"] for o in ops if o["pts"] < 0))
    alvo_w = sum(1 for o in ops if o["res"] == "ALVO")
    return {
        "n": n,
        "wr": 100.0 * sum(1 for o in ops if o["pts"] > 0) / n,
        "wr_alvo": 100.0 * alvo_w / n,
        "e": sum(o["pts"] for o in ops) / n,
        "pf": (ganhos / perdas) if perdas > 0 else float("inf"),
        "g": ganhos, "p": perdas,
    }


def p_valor(ops, n_perm, seed=7):
    """
    Teste de permutacao: embaralha os resultados entre os dias, preservando a
    distribuicao de ganho/perda mas quebrando a association com o sinal.
    p = fracao de embaralhamentos com expectancy >= expectancy real.
    """
    pts = [o["pts"] for o in ops]
    n = len(pts)
    e_real = sum(pts) / n
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        s = rng.sample(pts, n)
        if sum(s) / n >= e_real:
            ge += 1
    return ge / n_perm, e_real


def tamanho_amostra(e, sd, poder=0.80, alfa=0.05):
    """n aproximado para detectar um efeito d = e/sd (regra grosseira 2.8)."""
    if sd <= 0 or e == 0:
        return None
    d = abs(e / sd)
    return int(round(2.8 / (d * d)))


def formatar_pf(v):
    return "inf" if v == float("inf") else "%.2f" % v


def main():
    ap = argparse.ArgumentParser(description="Validador de geometria do Sub-Trader")
    ap.add_argument("--symbol", default="WDOV26")
    ap.add_argument("--bars", type=int, default=3000, help="barras M5 a carregar")
    ap.add_argument("--perm", type=int, default=100000, help="permutacoes do teste")
    ap.add_argument("--min-n", type=int, default=25,
                    help="n minimo para declarar um edge")
    args = ap.parse_args()

    print("=" * 96)
    print("VALIDADOR DE GEOMETRIA DO SUB -- rompimento do corpo do candle de 1H")
    print("=" * 96)
    print("ATENCAO: este script mede. Nao altera o robo, nao envia ordem,")
    print("nao modifica config.json. Leitura de barras apenas.")
    print()

    barras = carregar_barras(args.symbol, args.bars)
    if not barras:
        return 1
    dias = agrupar_dias(barras)
    print("dados: %s -> %s | %d barras M5 | %d pregoes"
          % (barras[0][0].strftime("%d/%m %H:%M"), barras[-1][0].strftime("%d/%m %H:%M"),
             len(barras), len(dias)))
    print("atencao: %d pregoes e uma amostra PEQUENA. Graph de 36 combinacoes"
          % len(dias))
    print("         sobre poucas semanas acha vencedor por ruido. Confira o p-valor.")
    print()

    resultados = []
    print("-" * 96)
    print("%-5s %-15s %5s %4s %4s %7s %8s %8s"
          % ("side", "stop", "mult", "wick", "n", "wr%", "E(pt)", "PF"))
    print("-" * 96)
    for side, lbl_side in SIDES:
        for stop_kind, lbl_stop in STOPS:
            for mult in MULTS:
                for wick in WICKS:
                    ops = simular(side, stop_kind, mult, wick, dias)
                    st = estatisticas(ops)
                    if st is None:
                        continue
                    resultados.append((side, lbl_side, lbl_stop, mult, wick, st, ops))
                    print("%-5s %-15s %5.1f %4.1f %4d %7.0f %+8.2f %8s"
                          % (lbl_side, lbl_stop, mult, wick, st["n"], st["wr"],
                             st["e"], formatar_pf(st["pf"])))
    print("-" * 96)
    print()

    if not resultados:
        print("Nenhuma configuracao produziu operacoes. Amplie --bars.")
        return 1

    # ---- todas as configuracoes, ordenadas, para inspecao ----
    print("TODAS AS %d CONFIGURACOES, ORDENADAS POR EXPECTANCY"
          % len(resultados))
    print("(a melhor aparece primeiro de proposito: e ela que o olho quer ver)")
    print("-" * 96)
    for side, lbl_side, lbl_stop, mult, wick, st, ops in \
            sorted(resultados, key=lambda r: -r[5]["e"]):
        print("  %-5s %-15s mult=%.1f wick>=%.1f | n=%2d E=%+6.2f wr=%3.0f%% PF=%7s"
              % (lbl_side, lbl_stop, mult, wick, st["n"], st["e"], st["wr"],
                 formatar_pf(st["pf"])))
    print()

    positivas = [r for r in resultados if r[5]["e"] > 0]
    print("configuracoes com E>0: %d de %d (%.0f%%)"
          % (len(positivas), len(resultados),
             100.0 * len(positivas) / len(resultados)))
    if positivas:
        print("  (se fosse ruido puro, perto de metade passaria)")
    print()

    # ---- teste de significancia na melhor ----
    melhor = max(resultados, key=lambda r: r[5]["e"])
    side, lbl_side, lbl_stop, mult, wick, st, ops = melhor
    print("=" * 96)
    print("TESTE DE SIGNIFICANCIA DA MELHOR CONFIGURACAO")
    print("=" * 96)
    print("  %s | %s | alvo 1:%.1f | wick>=%.1f" % (lbl_side, lbl_stop, mult, wick))
    print("  n=%d  E=%+.2f pt  PF=%s" % (st["n"], st["e"], formatar_pf(st["pf"])))
    print()
    p, e_real = p_valor(ops, args.perm)
    print("  teste de permutacao (%d embaralhamentos)" % args.perm)
    print("  p-valor = %.3f" % p)
    sd = (sum((o["pts"] - e_real) ** 2 for o in ops) / (len(ops) - 1)) ** 0.5 if len(ops) > 1 else 0.0
    if sd > 0:
        print("  desvio padrao = %.2f pt | efeito d = %.2f" % (sd, e_real / sd))
    print()
    declarado = p < 0.05 and st["n"] >= args.min_n
    if declarado:
        print("  VEREDITO: p<0.05 e n>=%d -> edge ESTATISTICAMENTE SUSTENTAVEL"
              % args.min_n)
        print("  (ainda assim: valide out-of-sample antes de colocar em producao)")
    else:
        print("  VEREDITO: NAO ha edge. Reprova por %s."
              % ("p-valor %.3f >= 0.05" % p if p >= 0.05
                 else "n=%d < %d (amostra insuficiente)" % (st["n"], args.min_n)))
        print("  A expectancy desta configuracao cabe no ruido. NAO implementar.")
    n_need = tamanho_amostra(e_real, sd)
    if n_need:
        print("  Para detectar um efeito deste tamanho com 80%% de poder:")
        print("  n ~ %d operacoes (hoje: %d)." % (n_need, st["n"]))
    print()

    print("=" * 96)
    print("LISTA DE OPERACOES DA MELHOR CONFIGURACAO (inspecao manual)")
    print("=" * 96)
    for o in ops:
        print("  %s %-5s entrada %8.2f | risco %6.2f | %+8.2f pt"
              % (o["dia"], o["res"], o["px"], o["risco"], o["pts"]))
    print()
    print("=" * 96)
    print("COMO USAR QUANDO TIVER MAIS DADOS")
    print("=" * 96)
    print("  python backtest/validar_geometria_sub.py --bars 20000 --min-n 60")
    print("  Um edge so e considerado real com p<0.05 E n suficiente. A geometria")
    print("  em producao hoje (pavio + R/R>=1.0 + trava de ATR) foi mantida")
    print("  justamente porque nenhuma alternativa se sustenta no teste.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
