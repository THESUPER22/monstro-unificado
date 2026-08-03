import math
import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HISTORICO = r"C:\AIOFEN\historico_contexto_wdo.csv"
DECISIONS = r"C:\AIOFEN\decisions_wdo.csv"
OUT = r"C:\AIOFEN\relatorio_apuracao_diaria.txt"

COSTO_PT = 0.24
VALOR_PONTO = 10.0
BARRAS = (30.5, 37.3, 45.7)
LIFT_META_BASE = 1.22
LIFT_META_ALTA = 1.47
DIAS_PISO = 30
Z = 1.96


def wilson(win, n):
    if n == 0:
        return 0.0, 0.0, 0.0
    p = win / n
    d = 1 + Z * Z / n
    centro = (p + Z * Z / (2 * n)) / d
    margem = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return p, max(0.0, centro - margem), min(1.0, centro + margem)


def main():
    linhas = []
    out = linhas.append
    out("=" * 72)
    out("APURACAO DIARIA WDO - acompanhamento do robo vs baseline (Sessao 20)")
    out("=" * 72)

    if not os.path.exists(HISTORICO):
        out(f"ERRO: {HISTORICO} nao encontrado. O robo ainda nao gravou historico.")
        _finalizar(linhas)
        return

    df = pd.read_csv(HISTORICO, on_bad_lines="skip")
    trades = df[df["reward"].astype(float).fillna(0.0) != 0].copy()
    trades["reward"] = trades["reward"].astype(float)

    n = len(trades)
    out(f"Fonte: {HISTORICO}")
    out(f"  registros brutos      : {len(df)} (rota para ultimas 5000 linhas no v22)")
    out(f"  trades concluidos     : {n}  (reward != 0; linhas com reward==0 = entradas/flutuantes descartadas)")
    if n == 0:
        out("Amostra ainda sem trades concluidos. Rode de novo apos o primeiro pregão com trades.")
        _finalizar(linhas)
        return

    rewards = trades["reward"].to_numpy()
    wins = int((rewards > 0).sum())
    losses = int((rewards < 0).sum())
    win_rate = wins / n * 100.0
    p, lb, ub = wilson(wins, n)

    gros = rewards[rewards > 0].sum()
    gros_l = -rewards[rewards < 0].sum()
    pf = gros / gros_l if gros_l > 0 else float("inf")
    avg_win = gros / wins if wins > 0 else 0.0
    avg_loss = rewards[rewards < 0].mean() if losses > 0 else 0.0
    ev_bruto = rewards.mean()
    ev_liq = ev_bruto - COSTO_PT
    pl_bruto = rewards.sum()
    pl_liq = pl_bruto - n * COSTO_PT

    out("")
    out("--- TRADES (P&L bruto em pts) ---")
    out(f"  wins {wins} | losses {losses} | win% {win_rate:.2f}%  (IC95 Wilson: {lb*100:.1f}% a {ub*100:.1f}%)")
    out(f"  avg win {avg_win:+.2f} pts | avg loss {avg_loss:+.2f} pts | payoff {avg_win/abs(avg_loss):.2f}")
    out(f"  profit factor {pf:.2f}  (lucro bruto {gros:+.1f} / prejuizo bruto {-gros_l:+.1f})")
    out(f"  EV bruto {ev_bruto:+.3f} pts | EV liq (taxas R${COSTO_PT*VALOR_PONTO:.2f}/cc) {ev_liq:+.3f} pts")
    out(f"  P&L bruto {pl_bruto:+.1f} pts | P&L liquido {pl_liq:+.1f} pts = R$ {pl_liq*VALOR_PONTO:+.2f}")

    out("")
    out("--- LONG x SHORT ---")
    for sinal, nome in ((1, "LONG "), (-1, "SHORT")):
        r = rewards[trades["action"] == ("BUY" if sinal > 0 else "SELL")]
        if len(r) == 0:
            out(f"  {nome}  sem trades")
            continue
        w = int((r > 0).sum())
        out(f"  {nome}  n={len(r):<5} win% {w/len(r)*100:5.1f}  EV liq {r.mean()-COSTO_PT:+7.2f} pts")

    out("")
    out("--- COMPARACAO TRIPLA vs BASELINE (SL 2.0 / TP 4.0) ---")
    nomes = ("bater o acaso", "pagar taxas RLP (R$2,40/cc)", "pagar spread cheio (R$7,40/cc)")
    for barra, nome in zip(BARRAS, nomes):
        status = "APROVADO" if win_rate > barra else "NAO ATINGIU"
        out(f"  win% > {barra:>5.1f}%  -> {status:<11}  ({nome})")

    lift = win_rate / BARRAS[0] if BARRAS[0] else 0.0
    out(f"  lift vs acaso  = win%/{BARRAS[0]:.1f}% = {lift:.2f}x  (meta {LIFT_META_BASE:.2f}x, exigente {LIFT_META_ALTA:.2f}x)")
    if lift >= LIFT_META_ALTA:
        out("  status lift    = EXIGENTE (edge forte)")
    elif lift >= LIFT_META_BASE:
        out("  status lift    = BASE (edge consistente)")
    else:
        out("  status lift    = ABAIXO (nao prova edge)")

    out("")
    out("--- MATURACAO DA AMOSTRA ---")
    dias = 0
    dias_operando = 0
    ultima_data = "N/A"
    if os.path.exists(DECISIONS):
        d = pd.read_csv(DECISIONS, on_bad_lines="skip")
        if "timestamp" in d.columns and len(d):
            ts = pd.to_datetime(d["timestamp"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
            datas = ts.dropna().dt.date
            dias = datas.nunique()
            ultima_data = str(max(datas))
            if "acao" in d.columns:
                dias_operando = d.loc[ts.notna() & d["acao"].isin(["BUY", "SELL"]), "timestamp"].pipe(
                    lambda s: pd.to_datetime(s, format="%Y.%m.%d %H:%M:%S", errors="coerce")
                ).dropna().dt.date.nunique()
    out(f"  dias com registro de decisao: {dias}   (ultima: {ultima_data})")
    out(f"  dias com entrada BUY/SELL   : {dias_operando}")
    out(f"  piso de significancia       : {DIAS_PISO} dias")
    if dias >= DIAS_PISO:
        out("  -> AMOSTRA ATINGIDA. Comparacao contra a baseline valida.")
    else:
        out(f"  -> Faltam {max(0, DIAS_PISO - dias)} dias de coleta. Win% ainda pode mudar (n={n}).")

    out("")
    out("--- VEREDICTO ---")
    if dias < DIAS_PISO:
        out(f"  AMOSTRA EM COLETA ({dias}/{DIAS_PISO} dias). Nao mexer no config do v22 (Item 3 travado).")
    elif win_rate > BARRAS[1]:
        out(f"  APROVADO para calibrar o v22 (Item 3): win% {win_rate:.1f}% > {BARRAS[1]:.1f}% pagou as taxas RLP.")
        out("  Regra: so ajustar config.json com respaldo (>=30 dias, reward != 0) e conferir avancos no ROADMAP.")
    elif win_rate > BARRAS[0]:
        out(f"  EM EDGE: vence o acaso ({win_rate:.1f}% > {BARRAS[0]:.1f}%) mas ainda nao paga as taxas ({BARRAS[1]:.1f}%).")
        out("  Nao calibrar. Investigar onde o lucro esta vazando (avg loss, saidas por fluxo, spread).")
    else:
        out(f"  ABAIXO DO ACASO ({win_rate:.1f}% <= {BARRAS[0]:.1f}%). V2 nao provou edge real no WDO.")
        out("  Manter coleta, nao calibrar. Dados WIN sao laboratorio, NAO usados aqui (decisao Sessao 20).")

    out("")
    out("--- CAVEATS (leia antes de decidir) ---")
    out("  1. historico_contexto_wdo.csv NAO tem timestamp: a contagem de dias vem de decisions_wdo.csv")
    out("     (dias em que o robo rodou/decidiu). Dias com trade fechado podem ser menos.")
    out("  2. O v22 trunca o historico em 5000 linhas: trades muito antigos podem nao estar mais no CSV.")
    out("     Backup os CSVs periodicamente (ex.: backup_auto diario) para preservar a amostra completa.")
    out("  3. Barras 30,5/37,3/45,7 assumem estrutura SL 2.0 / TP 4.0 da baseline. O v22 sai por fluxo/")
    out("     breakeven/trailing, entao as barras sao aproximacao conservadora da estrutura real dos trades.")
    out("  4. Fills no meio do spread (RLP). Se a execucao real pagar o spread inteiro, use a barra de 45,7%.")

    _finalizar(linhas)


def _finalizar(linhas):
    texto = "\n".join(linhas)
    print(texto)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(texto)
    print(f"\nRelatorio salvo em: {OUT}")


if __name__ == "__main__":
    main()
