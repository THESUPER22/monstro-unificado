import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\AIOFEN")
from selecao_estrategia_regime import SelecionadorRegime

BARRAS = r"C:\AIOFEN\barras_1min_wdo.csv"
REGIME_DIA = r"C:\AIOFEN\regime_por_dia_wdo.csv"
OUT = r"C:\AIOFEN\relatorio_validacao_regime.txt"

JANELA = 30
ATR_PERIODO = 14
ALPHA = 1.0 / ATR_PERIODO


def std_ret_por_dia(g):
    return g.rolling(JANELA).std().shift(-JANELA)


def main():
    df = pd.read_csv(BARRAS)
    df["data"] = df["datetime"].str[:10]
    df["ret"] = np.log(df["close"] / df["close"].shift(1))
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum((df["high"] - df["close"].shift(1)).abs(), (df["low"] - df["close"].shift(1)).abs()),
    )
    df["atr14"] = df["tr"].ewm(alpha=ALPHA, adjust=False).mean().shift(1)
    df["vol_proxy"] = df["ret"].rolling(JANELA).std().shift(1)
    df["vol_tick30"] = df["tick_volume"].rolling(JANELA).sum().shift(1)
    df["vol_tick5"] = df["tick_volume"].rolling(5).sum().shift(1)
    df["growth"] = df["vol_tick5"] / df["vol_tick5"].shift(5)
    df["forward_vol"] = df.groupby("data")["ret"].transform(std_ret_por_dia)
    df["fwd_hi"] = df.groupby("data")["high"].transform(lambda g: g.rolling(JANELA).max().shift(-JANELA))
    df["fwd_lo"] = df.groupby("data")["low"].transform(lambda g: g.rolling(JANELA).min().shift(-JANELA))
    df["fwd_range"] = df["fwd_hi"] - df["fwd_lo"]

    preco_medio = df["close"].mean()
    df["vol_proxy_pts"] = df["vol_proxy"] * preco_medio
    df["forward_vol_pts"] = df["forward_vol"] * preco_medio

    datas = sorted(df["data"].unique())
    corte = datas[len(datas) // 2]
    treino = df[df["data"] < corte].dropna(subset=["vol_proxy_pts", "forward_vol_pts"])
    teste = df[df["data"] >= corte].dropna(subset=["vol_proxy_pts", "forward_vol_pts"])
    t_data = datas[: len(datas) // 2]
    e_data = datas[len(datas) // 2:]

    atr_th = treino["atr14"].quantile(0.30)
    vol_low_th = treino["vol_proxy_pts"].quantile(0.50)
    vol_cc_th = treino["vol_tick30"].quantile(0.75)
    realized_th = treino["forward_vol_pts"].quantile(0.80)

    def classificar_com(g, vol_high_q, vol_tick_q, growth_th):
        vp = g["vol_proxy_pts"]
        vol_high_th = treino["vol_proxy_pts"].quantile(vol_high_q)
        vol_tick_gate = treino["vol_tick30"].quantile(vol_tick_q)
        resultado = np.where((g["atr14"] < atr_th) & (vp < vol_low_th), "LATERAL", "NORMAL")
        resultado = resultado.astype("<U9")
        explosao = (vp > vol_high_th) & (g["growth"] > growth_th) & (g["vol_tick30"] >= vol_tick_gate)
        resultado[explosao.values] = "EXPLOSAO"
        return pd.Series(resultado, index=g.index)

    candidatos = [(q, tq, gr) for q in (0.80, 0.85, 0.90) for tq in (0.50, 0.60, 0.75) for gr in (1.1, 1.2)]
    melhor = None
    melhor_diff = math.inf
    for combo in candidatos:
        share = float((classificar_com(treino, *combo) == "EXPLOSAO").mean())
        if share <= 0:
            continue
        d = abs(share - 0.05)
        if d < melhor_diff:
            melhor_diff = d
            melhor = (combo, share)
    vol_high_q, vol_tick_q, growth_th = melhor[0]
    vol_high_th = treino["vol_proxy_pts"].quantile(vol_high_q)
    vol_tick_gate = treino["vol_tick30"].quantile(vol_tick_q)
    share_treino = melhor[1]
    teste = teste.copy()
    teste["modo_pred"] = classificar_com(teste, vol_high_q, vol_tick_q, growth_th)
    teste["realizada"] = np.where(teste["forward_vol_pts"] >= realized_th, "EXPLOSAO_REAL", "NAO")

    corr = teste[["vol_proxy_pts", "forward_vol_pts"]].corr(method="spearman").iloc[0, 1]

    pred_exp = teste["modo_pred"] == "EXPLOSAO"
    real_exp = teste["realizada"] == "EXPLOSAO_REAL"
    tp = int((pred_exp & real_exp).sum())
    fp = int((pred_exp & ~real_exp).sum())
    fn = int((~pred_exp & real_exp).sum())
    tn = int((~pred_exp & ~real_exp).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    baseline = float(real_exp.mean())

    linhas = []
    linhas.append("=" * 68)
    linhas.append("VALIDACAO DO SELECIONADOR REGIME — CAUSAL, FORA DA AMOSTRA")
    linhas.append("=" * 68)
    linhas.append(f"Treino: {len(t_data)} dias ({t_data[0]} a {t_data[-1]})")
    linhas.append(f"Teste : {len(e_data)} dias ({e_data[0]} a {e_data[-1]})")
    linhas.append(f"Barras 1min: treino={len(treino)} | teste={len(teste)}")
    linhas.append("")
    linhas.append("AVISO METODOLOGICO (honesto):")
    linhas.append("  - Detector de producao usa ATR + ENTROPIA DE BOOK + volume. Entropia de book")
    linhas.append("    nao existe neste CSV (so trades). Usado PROXY de preco: desvio padrao do retorno")
    linhas.append("    1min nos ultimos 30 min (vol_proxy).")
    linhas.append("  - AGUARDANDO (book desequilibrado) e DEFESA (sequencia de losses) NAO foram")
    linhas.append("    modelados: nao sao detectaveis por dados de preco.")
    linhas.append("  - Limiares ajustados SOMENTE no treino; todos os numeros abaixo sao do TESTE")
    linhas.append("    (segundo semestre), classificados barra a barra sem olhar o futuro.")
    linhas.append("")
    linhas.append("LIMIARES (treino):")
    linhas.append(f"  atr_baixo      = {atr_th:.2f} pts")
    linhas.append(f"  vol_lateral    = < {vol_low_th:.2f} pts (P50)")
    linhas.append(f"  vol_explosao   = > {vol_high_th:.2f} pts (P{int(vol_high_q*100)})")
    linhas.append(f"  volume_min     = {vol_tick_gate:,.0f} cc (P{int(vol_tick_q*100)}, 30min)")
    linhas.append(f"  crescimento    = > {growth_th}x (5min -> 5min)")
    linhas.append(f"  share EXPLOSAO no treino = {share_treino:.1%} (buscou ~5%)")
    linhas.append(f"  realizada(exp) = forward_vol >= {realized_th:.2f} pts (P80)")
    linhas.append("")
    linhas.append("1) PODER PREDITIVO DO SINAL (proxy -> volatilidade futura)")
    linhas.append(f"  Spearman(vol_proxy, forward_vol) no TESTE = {corr:+.3f}")
    linhas.append("")
    linhas.append("2) DETECCAO DE EXPLOSAO — matriz (TESTE)")
    linhas.append(f"  {'':14}{'EXP real':>9}{'nao real':>9}")
    linhas.append(f"  {'previsto EXP':<14}{tp:>9}{fp:>9}")
    linhas.append(f"  {'previsto nao':<14}{fn:>9}{tn:>9}")
    linhas.append("")
    linhas.append(f"  Precisao (dos que avisou, quantos foram mesmo): {precision:.1%}  (baseline aleatorio: {baseline:.1%})")
    linhas.append(f"  Revocacao (dos que ocorreram, quantos avisou):    {recall:.1%}")
    linhas.append(f"  Falsos positivos: {fp} ({fpr:.1%} das nao-explosoes)")
    linhas.append(f"  Lift de precisao vs aleatorio: {precision / baseline:.2f}x" if baseline > 0 else "  Lift: n/a")
    linhas.append("")
    linhas.append("3) MONOTONICIDADE — o modo previsto anda junto com o que realizou (TESTE)")
    linhas.append(f"  {'modo':<10}{'n':>7}{'fwd vol med':>12}{'fwd range max med':>18}")
    for modo in ["LATERAL", "NORMAL", "EXPLOSAO"]:
        g = teste[teste["modo_pred"] == modo]
        if len(g) == 0:
            continue
        fwd_range = g["fwd_range"].mean()
        linhas.append(
            f"  {modo:<10}{len(g):>7}{g['forward_vol_pts'].mean():>12.2f}{fwd_range:>18.1f}"
        )
    linhas.append("")
    linhas.append("4) O QUE O SelecionadorRegime FAZ COM CADA MODO (modulo real da Sessao 19)")
    sel = SelecionadorRegime()
    for modo in ["LATERAL", "NORMAL", "EXPLOSAO"]:
        p = sel.selecionar_perfil(modo)
        linhas.append(
            f"  {modo:<10} opera={str(sel.permitido_operar(modo)):<5} "
            f"volx{p['volume_mult']:.1f} slx{p['sl_mult']:.1f} tpx{p['tp_mult']:.1f} "
            f"score_min={p['score_minimo']} -> {', '.join(p['estrategias_ativas'])}"
        )
    linhas.append("")
    linhas.append("5) CONCORDANCIA DIARIA — modo dominante previsto vs regime_por_dia_wdo.csv")
    try:
        rdiario = pd.read_csv(REGIME_DIA)
        dom_pred = teste[teste["modo_pred"] != "NAO"].groupby("data")["modo_pred"].apply(
            lambda s: s.mode().iloc[0])
        mapa = {"LATERAL": "LATERAL", "NORMAL": "LATERAL", "EXPLOSAO": "EXPLOSAO"}
        acordos = 0
        total = 0
        for d, pred in dom_pred.items():
            linha = rdiario[rdiario["date"] == d]
            if linha.empty:
                continue
            real = linha["regime"].iloc[0]
            total += 1
            if (mapa.get(pred, "NAO") == "EXPLOSAO" and real in ("EXPLOSAO", "EXTREMO")) or (
                mapa.get(pred, "NAO") == "LATERAL" and real == "LATERAL"):
                acordos += 1
        linhas.append(f"  Dias no teste com ambos: {total}")
        linhas.append(f"  Concordancia (explosivo vs lateral): {acordos}/{total} = {acordos / total:.0%}" if total else "  n/a")
    except Exception as e:
        linhas.append(f"  (nao foi possivel ler regime_por_dia: {e})")
    linhas.append("")
    linhas.append("CONCLUSAO OPERACIONAL:")
    linhas.append("  - Se precisao/lift forem altos: o modo EXPLOSAO avisado vale risco maior.")
    linhas.append("  - Se fpr alto: EXPLOSAO via proxy nao deve subir volume antes de confirmacao.")
    linhas.append("  - LATERAL/NORMAL separando fwd_vol: a escala de risco por modo esta correta.")

    texto = "\n".join(linhas)
    print(texto)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(texto)


if __name__ == "__main__":
    main()
