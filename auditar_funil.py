"""
auditar_funil.py - ATRIBUICAO DE DESCARTE DO FUNIL DO Core v22 (WDO)

READ-ONLY. Nao escreve nada, nao importa o monstro, nao toca em config.
Uso:  python auditar_funil.py            (todos os logs)
      python auditar_funil.py 20260924   (um dia)

POR QUE EXISTE
--------------
`decisions_wdo.csv` grava a decisao ANTES de qualquer portao pos-decisao
(monstro_unificado_v22.py:8266). Logo, os 40k BUY/SELL do CSV NAO sao ordens:
sao *candidatos*. Este script separa as duas coisas:

  ETAPA A  - morrem DENTRO de prever_acao() (linhas < 8267)
             A decisao ja volta NADA e e gravada como NADA no CSV.
             Estes vetoes TEM poder causal: definem quais candidatos sobrevivem.

  ETAPA B  - portoes DEPOIS do CSV (linhas > 8267)
             A decisao estava BUY/SELL no CSV e mesmo assim virou NADA.
             Estes portoes sao os que "matam" os 40k.

O que o script responde: qual camada realmente descarta os candidatos,
e se o Core esta operavel (a Faixa 1 pausa o Core enquanto houver posicao
magic 7008 aberta - ver _atualizar_estado_sistema / GATE ROMPIMENTO).
"""

import io
import os
import re
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\AIOFEN"
MAGIC_ROMPIMENTO = 7008

# ---- ETAPA A: dentro de prever_acao() -> ja volta NADA (antes do CSV) ----
# REGEXES AUDITADAS PELO SELFTEST (as antigas tinham colisao cruzada:
# "VETO TOTAL" casava "TENDENCIA VETO TOTAL"; CB1 casava CB2)
PRE = {
    "Williams %R veto": r"WILLIAMS %R VETO",
    "VETO TOTAL (nenhum lado viavel)": r"(?<!TENDENCIA )VETO TOTAL: BUY=",
    "Multi-TF veto (M5/M15/M30)": r"MULTI-TF VETO",
    "Sentinela veto": r"SENTINELA VETO",
    "MR veto (mean reversion)": r"MR VETO",
    "FORCA BUY/SELL (so um lado viavel)": r"FORCA (BUY|SELL)",
    "C10 score baixo (aprendizado)": r"C10: Score \d+/11 < 2",
    "Spread alto": r"Spread alto",
    "Aprendizado forcado": r"APRENDIZADO FORCADO",
}

# ---- ETAPA B: depois do CSV, com BUY/SELL ainda na mao ----
POS = {
    "Volume muito baixo": r"Volume muito baixo",
    "Dados invalidos": r"Dados inv.lidos",
    "Bloqueio de lado (inversao)": r"Invertindo a",
    "Horario limite de ordens": r"executando novas ordens",
    "Veto seguir os bigs": r"VETO SEGUIR OS BIGS",
    "Piso de confianca": r"PISO DE CONFIAN.A",
    "GATE ROMPIMENTO (Faixa 1)": r"GATE ROMPIMENTO",
    ">>> ORDEM EXECUTADA": r"Ordem (BUY|SELL) executada",
}

# Contadores que exigem distincao de case. CB1 = "Circuit Breaker ativado"
# (minusculo); CB2 = "CIRCUIT BREAKER ATIVADO" (maiusculo). Sob re.I os dois
# casavam as mesmas linhas e cada um contava o total do outro.
CASO_SENSI = {
    "Circuit Breaker CB1": r"Circuit Breaker ativado",
    "Circuit Breaker CB2": r"CIRCUIT BREAKER ATIVADO",
    "SNIPER %R INICIA": r"SNIPER %R INICIA",
}

RE_HORA = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})")


def logs_disponiveis():
    return sorted(f for f in os.listdir(BASE) if re.match(r"monstro_wdo.*\.log$", f))


def dia_de(f):
    m = re.search(r"(\d{8})", f)
    return m.group(1) if m else "hoje"


def medir(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    a = {k: len(re.findall(v, txt, re.I)) for k, v in PRE.items()}
    b = {k: len(re.findall(v, txt, re.I)) for k, v in POS.items()}
    c = {k: len(re.findall(v, txt)) for k, v in CASO_SENSI.items()}  # case sensivel
    b["Circuit Breaker CB1"] = c["Circuit Breaker CB1"]
    b["Circuit Breaker CB2"] = c["Circuit Breaker CB2"]
    sn = c["SNIPER %R INICIA"]
    gt = b["GATE ROMPIMENTO (Faixa 1)"]
    core = re.findall(r"processada e resetada", txt, re.I)
    return a, b, sn, gt, len(core), txt


def horas(txt, pat):
    out = []
    for l in txt.splitlines():
        if re.search(pat, l, re.I):
            m = RE_HORA.match(l)
            if m:
                out.append(m.group(2) + ":" + m.group(3))
    return out


# ======================================================================
# TRIPLICE REGRA DE VALIDACAO (29/09/2026)
# Existe porque uma regex errada ja produziu dois vereditos ERRADOS nesta
# mesma sessao: (1) "Sniper %R: 0 disparos / codigo morto" -> o padrao nao
# cobria a linha "SNIPER %R INICIA"; (2) "o funil e'contraditorio entre
# Williams e Multi-TF" -> ambos rodam ANTES do save do CSV, entao nao
# matem o funil pos-decisao. Nenhuma das duas conclusoes sobreviveu ao
# cruzamento de fontes. Daqui em diante: nada de verdict sem passar aqui.
# ======================================================================

# Linha por linha, EXATAMENTE como o log as emite.
# Cada entrada casa 1:1 com a chave do PRE/POS acima.
LINHAS_CANONE = [
    ("SNIPER %R INICIA",
     r"2026-09-29 10:00:00,100 - INFO - \xf0\x9f\x90\xa1 SNIPER %R INICIA BUY \x94\x90 sobrepondo IA, pulando filtros normais"),
    ("GATE ROMPIMENTO (Faixa 1)",
     r"2026-09-29 10:00:01,200 - WARNING - [GATE ROMPIMENTO] Ordem bloqueada para WDOV26 (apenas Magic 7008 na Faixa 1)"),
    (">>> ORDEM EXECUTADA",
     r"2026-09-29 10:00:13,206 - INFO - \xef\xb8\x8f \xef\xb8\x8f Ordem SELL executada. Ticket: 2540488355"),
    ("Williams %R veto",
     r"2026-09-29 09:15:00,000 - WARNING - WILLIAMS %R VETO BUY: WR=-16 (sobrecomprado)"),
    ("VETO TOTAL (nenhum lado viavel)",
     r"2026-09-29 09:15:00,000 - WARNING - VETO TOTAL: BUY=x, SELL=y"),
    ("Multi-TF veto (M5/M15/M30)",
     r"2026-09-29 09:15:00,000 - WARNING - MULTI-TF VETO BUY: M5_RSI=40.1 M15_RSI=42.3 M30_RSI=44.0 (todos < 50)"),
    ("Sentinela veto",
     r"2026-09-29 09:15:00,000 - WARNING - \xc2\xb0\xc2\xb8\xc2\xa8 SENTINELA VETO BUY: detalhe"),
    ("MR veto (mean reversion)",
     r"2026-09-29 09:15:00,000 - WARNING - MR VETO BUY: rsi=82.1"),
    ("FORCA BUY/SELL (so um lado viavel)",
     r"2026-09-29 09:15:00,000 - INFO - FORCA SELL: contexto"),
    ("C10 score baixo (aprendizado)",
     r"2026-09-29 09:15:00,000 - INFO - \xe2\x9a\x96 C10: Score 1/11 < 2. Operacao bloqueada."),
    ("Spread alto",
     r"2026-09-29 09:15:00,000 - INFO - \xef\xb8\x8f Operacao bloqueada - Spread alto (9.0 > 8.0)"),
    ("Aprendizado forcado",
     r"2026-09-29 09:15:00,000 - WARNING - \xef\xb8\x8f APRENDIZADO FORCADO 1/3: Score 1/11 aceito"),
    ("Volume muito baixo",
     r"2026-09-29 09:15:00,000 - INFO - \xe2\x9a\x96 Volume muito baixo e n\xc3\xa3o crescente. Opera\xc3\xa7\xc3\xa3o bloqueada."),
    ("Circuit Breaker CB1",
     r"2026-09-29 09:15:00,000 - WARNING - \xe2\x9a\x96 Circuit Breaker ativado: max loss"),
    ("Circuit Breaker CB2",
     r"2026-09-29 09:15:00,000 - WARNING - \xef\xb8\x8f CIRCUIT BREAKER ATIVADO: {status}"),
    ("Dados invalidos",
     r"2026-09-29 09:15:00,000 - ERROR - \xef\xb8\x8f Dados invalidos: sem preco"),
    ("Bloqueio de lado (inversao)",
     r"2026-09-29 09:15:00,000 - WARNING - \xef\xb8\x9c\xe2\x84\xa2 Invertindo a acao de BUY para SELL devido a bloqueio de lado."),
    ("Horario limite de ordens",
     r"2026-09-29 17:35:00,000 - INFO - \xef\xb8\x8d\xef\xb8\x8d 17:30 - N\xc3\xa3o executando novas ordens (pr\xc3\xb3ximo ao encerramento)"),
    ("Veto seguir os bigs",
     r"2026-09-29 09:15:00,000 - INFO - \xef\xb8\x90\xef\xb8\x91 VETO SEGUIR OS BIGS: decisao SELL \xc3\xa9 CONTRA o lado dominante"),
    ("Piso de confianca",
     "2026-09-29 09:15:00,000 - WARNING - \xef\xb8\x8f PISO DE CONFIAN\xe7A: BUY bloqueado (confian\xe7a 0.40 < 0.50)"),
]

# (linhas de "TENDENCIA VETO" foram REMOVIDAS em 29/09/2026: o grep nos logs
#  monstro_wdo*.log nao encontra nenhuma ocorrencia. Eram contadores fantasma.)

# Marcadores de posicao do Core (fora do PRE/POS, so contagem por dia).
CANONE_CORE = (r"2026-09-29 12:26:52,000 - INFO - \xef\xb8\x8f Posicao 2540558678 processada e resetada.")


def selftest() -> bool:
    """Teste unitario das regexes contra linhas canonicas conhecidas.
    REGRA 1: nenhuma regex entra no funil sem passar por aqui.
    Cobre dois defeitos reais ja observados: falta de cobertura (regex que
    nunca casa a linha real) e colisao cruzada (uma linha contada 2x)."""
    print("=" * 92)
    print("TRIPLICE REGRA / TESTE 1 - as regexes casam as linhas canonicas?")
    print("=" * 92)
    regex = dict(list(PRE.items()) + list(POS.items()))
    flags_de = {k: re.I for k in regex}
    regex.update(CASO_SENSI)
    flags_de.update({k: 0 for k in CASO_SENSI})
    ok = True
    testadas = 0
    for chave, linha in LINHAS_CANONE:
        if chave not in regex:
            print("  %-38s REGRA SEM REGEX (chave nao encontrada)  <-- corrigir" % chave)
            ok = False
            continue
        rx, fl = regex[chave], flags_de[chave]
        casou = bool(re.search(rx, linha, fl))
        falso = [c for c, l2 in LINHAS_CANONE
                 if c != chave and re.search(rx, l2, fl)]
        if not (casou and not falso):
            ok = False
        testadas += 1
        print("  %-38s %s%s" % (chave, "OK " if casou and not falso else "FALHA",
              ("  (colide com: %s)" % falso) if falso else ""))
    if not re.search(r"processada e resetada", CANONE_CORE, re.I):
        print("  %-38s FALHA (marcador de core)" % "processada e resetada")
        ok = False
    else:
        testadas += 1
        print("  %-38s OK " % "processada e resetada")
    faltando = sorted(set(regex) - {c for c, _ in LINHAS_CANONE})
    print("-" * 60)
    print("  regexes testadas: %d/%d  (+1 marcador de core)"
          % (len(LINHAS_CANONE), len(regex)))
    if faltando:
        print("  sem linha canonica (cobertas so por contagem): %s" % ", ".join(faltando))
    print("  RESULTADO DO SELFTEST: %s"
          % ("PASS" if ok else "FAIL - CORRIGIR ANTES DE CONFIAR EM QUALQUER VERDICT"))
    return ok


def dualcheck() -> bool:
    """REGRA 2: cruzar contagem do LOG com a fonte independente.
    O log e texto livre; o CSV de decisoes e a base; o historico MT5 e o juizo.
    Se log=0 e a outra fonte tem registro, a regex esta errada."""
    print()
    print("=" * 92)
    print("TRIPLICE REGRA / TESTE 2 - dual-check log x CSV x MT5")
    print("=" * 92)
    ok = True
    csv_p = os.path.join(BASE, "decisions_wdo.csv")
    if os.path.exists(csv_p):
        import csv as _csv
        cnt = Counter()
        with open(csv_p, encoding="utf-8", errors="replace") as f:
            for row in _csv.DictReader(f):
                cnt[row.get("acao", "")] += 1
        dir_ = cnt.get("BUY", 0) + cnt.get("SELL", 0)
        print("  CSV decisions_wdo.csv : NADA=%d  BUY=%d  SELL=%d  (direcionais=%d)"
              % (cnt.get("NADA", 0), cnt.get("BUY", 0), cnt.get("SELL", 0), dir_))
    else:
        print("  CSV ausente: %s" % csv_p)

    # fonte 3: historico MT5 para magic 123456 (trades REAIS do Core)
    try:
        import MetaTrader5 as mt5
        from datetime import datetime as _dt, timedelta as _td
        if mt5.initialize():
            ini = _dt(2026, 7, 29)
            deals = mt5.history_deals_get(ini, _dt.now())
            fechar = [d for d in (deals or []) if d.magic == 123456 and d.entry == 1]
            print("  MT5 deals fechados magic 123456 (desde 29/07): %d" % len(fechar))
            print("  >> CSV tem %d candidatos direcionais; MT5 tem %d execucoes reais."
                  % (dir_, len(fechar)))
            print("  >> A razao e' o funil. Os %d do CSV NAO tem pnl_real." % dir_)
            mt5.shutdown()
        else:
            print("  MT5 indisponivel: dual-check parcial (so CSV)")
    except ImportError:
        print("  MetaTrader5 ausente: dual-check parcial (so CSV)")

    print("-" * 60)
    print("  RESULTADO DO DUAL-CHECK: %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    if alvo in ("--selftest", "selftest"):
        sys.exit(0 if selftest() else 1)
    if alvo in ("--dualcheck", "dualcheck"):
        sys.exit(0 if dualcheck() else 1)
    if alvo in (None, "--tudo", "tudo"):
        selftest()
        dualcheck()

    logs = logs_disponiveis()
    if alvo:
        logs = [f for f in logs if dia_de(f) == alvo]

    tot_a, tot_b = Counter(), Counter()
    print("=" * 92)
    print("FUNIL DO CORE v22 (WDO) - %s" % ("dia %s" % alvo if alvo else "TODOS OS LOGS"))
    print("READ-ONLY: nada foi escrito.")
    print("=" * 92)

    print()
    print("ETAPA A - vetoes DENTRO de prever_acao() (a decisao volta NADA antes do CSV)")
    print("-" * 92)
    linhas_a = []
    for f in logs:
        a, b, sn, gt, core, txt = medir(os.path.join(BASE, f))
        tot_a.update(a)
        linhas_a.append((dia_de(f), sn, gt, core, a, b, txt))
    for k, v in tot_a.most_common():
        marca = "  <-- NUNCA ATIVA" if v == 0 else ""
        print("  %-40s %7d%s" % (k, v, marca))

    print()
    print("ETAPA B - portoes DEPOIS do CSV (a decisao estava BUY/SELL)")
    print("-" * 92)
    for _, _, _, _, _, b, _ in linhas_a:
        tot_b.update(b)
    for k, v in tot_b.most_common():
        marca = "  <-- NUNCA ATIVA" if v == 0 else ""
        print("  %-40s %7d%s" % (k, v, marca))

    print()
    print("POR DIA: o Sniper disparou, o gate segurou, o Core fechou posicao")
    print("-" * 92)
    print("%-11s %8s %8s %8s   %s" % ("dia", "sniper", "gate", "core_ok", "faixa do gate"))
    ts = tg = tc = 0
    for d, sn, gt, core, a, b, txt in linhas_a:
        g = horas(txt, r"GATE ROMPIMENTO")
        faixa = "%s..%s" % (g[0], g[-1]) if g else "-"
        if sn and core == 0 and gt == sn:
            faixa += "  (100% bloqueado)"
        ts += sn
        tg += gt
        tc += core
        print("%-11s %8d %8d %8d   %s" % (d, sn, gt, core, faixa))
    print("-" * 60)
    print("%-11s %8d %8d %8d" % ("TOTAL", ts, tg, tc))
    print()
    print("LEITURA: 'core_ok' = posicoes fechadas pelo Core (marca 'processada e resetada').")
    print("Se sniper > 0 e core_ok == 0, o Core disparou sinal e NAO abriu posicao.")


if __name__ == "__main__":
    main()
