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
PRE = {
    "Williams %R veto": r"WILLIAMS %R VETO",
    "VETO TOTAL (nenhum lado viavel)": r"VETO TOTAL",
    "Multi-TF veto (M5/M15/M30)": r"MULTI-TF VETO",
    "Sentinela veto": r"SENTINELA VETO",
    "MR veto (mean reversion)": r"MR VETO",
    "FORCA BUY/SELL (so um lado viavel)": r"FORCA (BUY|SELL)",
    "Tendencia veto total": r"TENDENCIA VETO TOTAL",
    "C10 score baixo (aprendizado)": r"C10: Score \d+/11 < 2",
    "Spread alto": r"Spread alto",
    "Aprendizado forcado": r"APRENDIZADO FORCADO",
}

# ---- ETAPA B: depois do CSV, com BUY/SELL ainda na mao ----
POS = {
    "Volume muito baixo": r"Volume muito baixo",
    "Circuit Breaker CB1": r"Circuit Breaker ativado",
    "Circuit Breaker CB2": r"CIRCUIT BREAKER ATIVADO",
    "Dados invalidos": r"Dados inv.lidos",
    "Bloqueio de lado (inversao)": r"Invertindo a..o de",
    "Horario limite de ordens": r"limite de ordens \(pr",
    "Veto seguir os bigs": r"VETO SEGUIR OS BIGS",
    "Piso de confianca": r"PISO DE CONFIAN.A",
    "GATE ROMPIMENTO (Faixa 1)": r"GATE ROMPIMENTO",
    ">>> ORDEM EXECUTADA": r"Ordem (BUY|SELL) executada",
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
    sn = re.findall(r"SNIPER %R INICIA", txt, re.I)
    gt = re.findall(r"GATE ROMPIMENTO", txt, re.I)
    core = re.findall(r"processada e resetada", txt, re.I)
    return a, b, len(sn), len(gt), len(core), txt


def horas(txt, pat):
    out = []
    for l in txt.splitlines():
        if re.search(pat, l, re.I):
            m = RE_HORA.match(l)
            if m:
                out.append(m.group(2) + ":" + m.group(3))
    return out


def main():
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
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
