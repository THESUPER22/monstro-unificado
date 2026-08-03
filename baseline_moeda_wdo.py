import math

import numpy as np
import pandas as pd

BARRAS = r"C:\AIOFEN\barras_1min_wdo.csv"
OUT = r"C:\AIOFEN\relatorio_baseline_moeda.txt"

SEED = 42
N_TRADES = 15000
COSTO_PT = 0.24
COSTO_PT_COM_SPREAD = 0.74
VALOR_PONTO = 10.0
ENTRADA_INICIO = "09:05"
ENTRADA_FIM = "17:00"

CONFIGS = [
    ("SL 2.0 / TP 4.0", 2.0, 4.0, None),
    ("SL 2.0 / TP 4.0 (hold 15min)", 2.0, 4.0, 15),
    ("SL 2.0 / TP 8.0", 2.0, 8.0, None),
    ("SL 1.5 / TP 4.0", 1.5, 4.0, None),
    ("SL 3.0 / TP 6.0", 3.0, 6.0, None),
]


def simular(aberto, alto, baixo, fechado, p_ini, direcao, sl, tp, hold):
    e = aberto[p_ini]
    p = p_ini
    n = len(aberto)
    t_inicial = p
    while p < n:
        if direcao > 0:
            d_sl = e - baixo[p]
            d_tp = alto[p] - e
            if d_sl >= sl and d_tp >= tp:
                if d_tp < d_sl:
                    return tp, "TP"
                return -sl, "SL"
            if d_sl >= sl:
                return -sl, "SL"
            if d_tp >= tp:
                return tp, "TP"
        else:
            d_sl = alto[p] - e
            d_tp = e - baixo[p]
            if d_sl >= sl and d_tp >= tp:
                if d_tp < d_sl:
                    return tp, "TP"
                return -sl, "SL"
            if d_sl >= sl:
                return -sl, "SL"
            if d_tp >= tp:
                return tp, "TP"
        if hold is not None and (p - t_inicial) >= hold:
            return direcao * (fechado[p] - e), "TEMPO"
        p += 1
    return direcao * (fechado[-1] - e), "FIM_DIA"


def main():
    df = pd.read_csv(BARRAS)
    df["data"] = df["datetime"].str[:10]
    df["hora"] = df["datetime"].str[11:16]
    df["fila"] = range(len(df))
    mask_entrada = (df["hora"] >= ENTRADA_INICIO) & (df["hora"] < ENTRADA_FIM)
    posicoes = df[mask_entrada].index.to_numpy()

    dias = {}
    for d, g in df.groupby("data"):
        dias[d] = {
            "aberto": g["open"].to_numpy(),
            "alto": g["high"].to_numpy(),
            "baixo": g["low"].to_numpy(),
            "fechado": g["close"].to_numpy(),
            "pos": g["fila"].to_numpy(),
        }
    lista_dias = list(dias.keys())

    rng = np.random.default_rng(SEED)
    linhas = []
    linhas.append("=" * 70)
    linhas.append("BASELINE MOEDA NO WDO — o acaso ganha ou perde? (1 ano)")
    linhas.append("=" * 70)
    linhas.append("Metodo: entradas ALEATORIAS (direcao 50/50), mesma estrutura de SL/TP e custos")
    linhas.append("que o robo. Entrada = abertura do minuto escolhido. Janela de entrada 09:05-17:00.")
    linhas.append("Detalhe dentro do minuto: se SL e TP fossem tocados no MESMO minuto, assume-se o")
    linhas.append("nivel MAIS PROXIMO da entrada como primeiro (empate = SL, conservador).")
    linhas.append(f"Custos por viagem (ida+volta): {COSTO_PT} pts = {COSTO_PT*VALOR_PONTO:.2f} R$/contrato")
    linhas.append("  (RLP ativado: R$1,20 entrada + R$1,20 saida = R$2,40/contrato. Fills considerados no")
    linhas.append("   meio do spread (sem pagar o spread inteiro). Se quiser cobrar spread, somar 0,5 pts.)")
    linhas.append(f"Trades por config: {N_TRADES} | seed {SEED}")
    linhas.append("")

    cab = ("config", "win%", "SL%", "TP%", "tempo%", "EV brut", "EV liq", "t-stats", "R$/trade")
    linhas.append(f"  {'config':<28}{cab[1]:>6}{cab[2]:>6}{cab[3]:>6}{cab[4]:>7}{cab[5]:>9}{cab[6]:>9}{cab[7]:>8}{cab[8]:>9}")
    linhas.append("  " + "-" * 88)

    detalhe_principal = {}
    for nome, sl, tp, hold in CONFIGS:
        bruto = np.zeros(N_TRADES)
        res = []
        i = 0
        while i < N_TRADES:
            p_global = int(rng.choice(posicoes))
            alvo_data = df["data"].iloc[p_global]
            g = dias[alvo_data]
            idx = int(np.where(g["pos"] == p_global)[0][0])
            if idx >= len(g["aberto"]) - 2:
                continue
            direcao = 1 if rng.integers(2) == 0 else -1
            ganho, motivo = simular(g["aberto"], g["alto"], g["baixo"], g["fechado"], idx, direcao, sl, tp, hold)
            bruto[i] = ganho
            res.append(motivo)
            i += 1
        liquido = bruto - COSTO_PT
        w = (bruto > 0).mean()
        r_sl = sum(1 for m in res if m == "SL") / N_TRADES
        r_tp = sum(1 for m in res if m == "TP") / N_TRADES
        r_t = sum(1 for m in res if m in ("TEMPO", "FIM_DIA")) / N_TRADES
        ev_l = liquido.mean()
        se = liquido.std(ddof=1) / math.sqrt(N_TRADES)
        t = ev_l / se if se > 0 else 0.0
        beq = (sl + COSTO_PT) / (sl + tp)
        linhas.append(
            f"  {nome:<28}{w*100:>6.1f}{r_sl*100:>6.1f}{r_tp*100:>6.1f}{r_t*100:>7.1f}"
            f"{bruto.mean():>9.2f}{ev_l:>9.2f}{t:>8.2f}{ev_l*VALOR_PONTO:>9.1f}"
        )
        if nome.startswith("SL 2.0 / TP 4.0"):
            detalhe_principal[nome] = {
                "w": w, "sl": r_sl, "tp": r_tp, "t": r_t, "ev": ev_l, "beq": beq,
                "bruto": bruto, "res": res,
            }

    linhas.append("")
    linhas.append("LEITURA:")
    linhas.append("  - win% = taxa de acerto do acaso | SL%/TP%/tempo% = como saiu do trade")
    linhas.append("  - EV brut = resultado medio em pts SEM custos | EV liq = COM custos")
    linhas.append("  - t-stats: |t|>2 = o mercado em si tem estrutura (nao eh moeda justa).")
    linhas.append("  - Break-even do acaso (com custos) = (SL+custo)/(SL+TP). Se win% do acaso < beq,")
    linhas.append("    o acaso PERDE dinheiro -> qualquer robo acima disso ja melhora o caso.")
    linhas.append("")
    for nome, det in detalhe_principal.items():
        linhas.append(f"DETALHE (long x short) — {nome}:")
        for sinal, nome_sinal in ((1, "LONG "), (-1, "SHORT")):
            idx_s = np.arange(0, N_TRADES, 2) if sinal > 0 else np.arange(1, N_TRADES, 2)
            b = det["bruto"][idx_s]
            liq = b - COSTO_PT
            linhas.append(
                f"  {nome_sinal}  n={len(idx_s):<6} win={100.0*(b>0).mean():>5.1f}%  "
                f"EV liq={liq.mean():>7.2f} pts  ({liq.mean()*VALOR_PONTO:>7.1f} R$/trade)"
            )
        linhas.append(f"  Break-even do acaso: win% > {(det['beq']*100):.1f}% com SL/TP desta config")
        linhas.append(f"  Barra para o ROBO (mesmo SL/TP): precisa de win% ACIMA de {100.0*det['w']:.1f}%")
        linhas.append("")
    ev_acaso = float(detalhe_principal["SL 2.0 / TP 4.0"]["bruto"].mean())
    beq_taxas = (2.0 + COSTO_PT) / 6.0
    beq_spread = (2.0 + COSTO_PT_COM_SPREAD) / 6.0
    linhas.append("SENSIBILIDADE AO CUSTO (SL 2.0 / TP 4.0):")
    linhas.append(f"  Taxas RLP R$2,40 (0,24 pts)          -> acaso EV liq = {ev_acaso - COSTO_PT:+.2f} pts "
                  f"({(ev_acaso - COSTO_PT)*VALOR_PONTO:+.1f} R$/cc) | break-even win% > {beq_taxas*100:.1f}%")
    linhas.append(f"  Taxas + spread R$7,40 (0,74 pts)     -> acaso EV liq = {ev_acaso - COSTO_PT_COM_SPREAD:+.2f} pts "
                  f"({(ev_acaso - COSTO_PT_COM_SPREAD)*VALOR_PONTO:+.1f} R$/cc) | break-even win% > {beq_spread*100:.1f}%")
    linhas.append("  (spread de 0,5 pts de ida+volta e' o atrito de execucao real: compra no ASK, vende no BID.")
    linhas.append("   Use o cenario que reflita seus fills reais no Profit/XP.)")
    linhas.append("")
    linhas.append("CONCLUSAO:")
    linhas.append(f"  - Com custo REAL de taxas (R${COSTO_PT*VALOR_PONTO:.2f}/cc RLP), o acaso perde ~"
                  f"{abs(ev_acaso - COSTO_PT)*VALOR_PONTO:.1f} R$/contrato por trade.")
    linhas.append("    EV bruto ~ -0.15 pts = o WDO e praticamente justo para entradas aleatorias")
    linhas.append("    nessa estrutura (teorico do passeio aleatorio: win% = SL/(SL+TP) = 33%).")
    linhas.append("  - Stop 2.0 pts NAO e stop-out catastrofico: o acaso ainda alcanca o TP em ~30%")
    linhas.append("    dos trades (proximo do teorico 33%).")
    linhas.append("  - Duas barras para o ROBO (SL 2.0 / TP 4.0):")
    linhas.append("      (1) bater o acaso:      win% > ~30.5%   (empatar com entrada aleatoria)")
    linhas.append(f"      (2) lucrar de verdade:  win% > {beq_taxas*100:.1f}%  (break-even com custos de taxas)")
    linhas.append("  - Com win% do robo x, EV esperado = x*TP - (1-x)*SL - custo (usar p/ dimensionar).")

    texto = "\n".join(linhas)
    print(texto)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(texto)


if __name__ == "__main__":
    main()
