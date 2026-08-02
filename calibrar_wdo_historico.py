import csv
import math
import time
from collections import defaultdict

CSV_TICKS = r"C:\AIOFEN\WDO$_202507141229_2026073118299.csv"
OUT_BARRAS = r"C:\AIOFEN\barras_1min_wdo.csv"
OUT_REGIME = r"C:\AIOFEN\regime_por_dia_wdo.csv"
OUT_RELATORIO = r"C:\AIOFEN\relatorio_calibracao_wdo.txt"

VALOR_PONTO = 10.0


def percentil_hist(contagem, pct, total):
    alvo = pct * total / 100.0
    acum = 0
    for chave in sorted(contagem):
        acum += contagem[chave]
        if acum >= alvo:
            return chave
    return max(contagem) if contagem else 0.0


def percentil_lista(vals, pct):
    if not vals:
        return 0.0
    vals = sorted(vals)
    idx = int(math.ceil(pct / 100.0 * len(vals))) - 1
    idx = max(0, min(idx, len(vals) - 1))
    return vals[idx]


def rsi_wilder(closes, periodo=14):
    if len(closes) <= periodo:
        return None
    ganhos = []
    perdas = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        ganhos.append(max(d, 0.0))
        perdas.append(max(-d, 0.0))
    g = sum(ganhos[:periodo]) / periodo
    p = sum(perdas[:periodo]) / periodo
    for i in range(periodo, len(ganhos)):
        g = (g * (periodo - 1) + ganhos[i]) / periodo
        p = (p * (periodo - 1) + perdas[i]) / periodo
    if p == 0:
        return 100.0
    rs = g / p
    return 100.0 - 100.0 / (1.0 + rs)


def main():
    t0 = time.time()
    total_ticks = 0
    total_vol = 0.0
    dias = 0
    dia_atual = None
    preco_min = math.inf
    preco_max = -math.inf

    barra1 = None
    barra5 = None
    chave1_atual = None
    chave5_atual = None
    prev_last = None

    barras1 = []
    barras5 = []
    noite_por_hora = defaultdict(lambda: {"range": [], "vol": 0.0, "n": 0, "ticks": 0, "ret": []})
    ruido = defaultdict(int)
    ruido_overflow = 0
    delta_dia = 0.0

    estado_atr = None
    atr_vals = []
    rsi_vals = []

    with open(CSV_TICKS, "r", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for linha in fh:
            p = linha.rstrip("\n").split("\t")
            if len(p) < 7:
                continue
            if not p[4]:
                continue
            try:
                last = float(p[4])
                vol = float(p[5])
            except ValueError:
                continue
            total_ticks += 1
            total_vol += vol
            if last < preco_min:
                preco_min = last
            if last > preco_max:
                preco_max = last

            data = p[0]
            hora = p[1]
            if data != dia_atual:
                dia_atual = data
                dias += 1
                prev_last = None
                estado_atr = None
                fechamentos1 = []
            hh = hora[0:2]
            mm = hora[3:5]

            chave1 = data + " " + hh + ":" + mm
            chave5 = data + " " + hh + ":" + str(int(mm) // 5 * 5).zfill(2)

            if chave1 != chave1_atual:
                if barra1 is not None:
                    barras1.append(barra1)
                barra1 = {
                    "dt": chave1,
                    "o": last, "h": last, "l": last, "c": last,
                    "vol": vol, "n": 1, "delta": 0.0,
                }
                chave1_atual = chave1
            else:
                barra1["h"] = max(barra1["h"], last)
                barra1["l"] = min(barra1["l"], last)
                barra1["c"] = last
                barra1["vol"] += vol
                barra1["n"] += 1

            if chave5 != chave5_atual:
                if barra5 is not None:
                    barras5.append(barra5)
                barra5 = {
                    "dt": chave5,
                    "o": last, "h": last, "l": last, "c": last,
                    "vol": vol, "n": 1, "delta": 0.0,
                }
                chave5_atual = chave5
            else:
                barra5["h"] = max(barra5["h"], last)
                barra5["l"] = min(barra5["l"], last)
                barra5["c"] = last
                barra5["vol"] += vol
                barra5["n"] += 1

            if prev_last is not None:
                d = abs(last - prev_last)
                idx_b = int(d / 0.5)
                if idx_b <= 200:
                    ruido[idx_b] += 1
                else:
                    ruido_overflow += 1
                if last > prev_last:
                    barra1["delta"] += vol
                    barra5["delta"] += vol
                elif last < prev_last:
                    barra1["delta"] -= vol
                    barra5["delta"] -= vol
            prev_last = last

        if barra1 is not None:
            barras1.append(barra1)
        if barra5 is not None:
            barras5.append(barra5)

    for b in barras1:
        hh = b["dt"].split(" ")[1][:2]
        ch = noite_por_hora[hh]
        ch["range"].append(b["h"] - b["l"])
        ch["vol"] += b["vol"]
        ch["n"] += 1
        ch["ticks"] += b["n"]
        if b["delta"] > 0:
            delta_dia += 1
        ch["ret"].append(math.log(b["c"] / b["o"]) if b["o"] > 0 else 0.0)

    with open(OUT_BARRAS, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["datetime", "open", "high", "low", "close", "tick_volume", "n_ticks", "range_pts", "delta_vol"])
        for b in barras1:
            w.writerow([b["dt"], b["o"], b["h"], b["l"], b["c"], round(b["vol"], 1), b["n"], round(b["h"] - b["l"], 1), round(b["delta"], 1)])

    dias_regime = defaultdict(lambda: {"range": [], "n": 0})
    for b in barras1:
        d = b["dt"].split(" ")[0]
        dias_regime[d]["range"].append(b["h"] - b["l"])
        dias_regime[d]["n"] += 1

    medias_dia = []
    for d, info in dias_regime.items():
        media = sum(info["range"]) / max(len(info["range"]), 1)
        medias_dia.append((d, media, info["n"]))
    medias_dia.sort()
    ranges_dia = [m for _, m, _ in medias_dia]
    p75 = percentil_lista(ranges_dia, 75)
    p90 = percentil_lista(ranges_dia, 90)
    with open(OUT_REGIME, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "avg_range_1min_pts", "n_barras", "regime"])
        for d, m, n in medias_dia:
            if m >= p90:
                reg = "EXTREMO"
            elif m >= p75:
                reg = "EXPLOSAO"
            else:
                reg = "LATERAL"
            w.writerow([d, round(m, 2), n, reg])

    cont_reg = defaultdict(int)
    for d, m, n in medias_dia:
        if m >= p90:
            cont_reg["EXTREMO"] += 1
        elif m >= p75:
            cont_reg["EXPLOSAO"] += 1
        else:
            cont_reg["LATERAL"] += 1

    ruido_total = sum(ruido.values()) + ruido_overflow
    r_p50 = percentil_hist(ruido, 50, ruido_total) * 0.5
    r_p90 = percentil_hist(ruido, 90, ruido_total) * 0.5
    r_p99 = percentil_hist(ruido, 99, ruido_total) * 0.5
    r_p999 = percentil_hist(ruido, 99.9, ruido_total) * 0.5

    ranges1 = [b["h"] - b["l"] for b in barras1]
    ranges5 = [b["h"] - b["l"] for b in barras5]
    r1_p50 = percentil_lista(ranges1, 50)
    r1_p90 = percentil_lista(ranges1, 90)
    r1_p99 = percentil_lista(ranges1, 99)
    r5_p50 = percentil_lista(ranges5, 50)
    r5_p90 = percentil_lista(ranges5, 90)
    r5_p99 = percentil_lista(ranges5, 99)

    for b in barras1:
        d = b["dt"].split(" ")[0]
        if estado_atr is None:
            estado_atr = {"prev_c": None, "atr": None, "tr": 0.0, "n": 0}
        if estado_atr["prev_c"] is None:
            estado_atr["prev_c"] = b["c"]
            continue
        tr = max(b["h"] - b["l"], abs(b["h"] - estado_atr["prev_c"]), abs(b["l"] - estado_atr["prev_c"]))
        if estado_atr["atr"] is None:
            estado_atr["atr"] = tr
            estado_atr["n"] = 1
        else:
            estado_atr["n"] += 1
            if estado_atr["n"] >= 14:
                estado_atr["atr"] = (estado_atr["atr"] * 13 + tr) / 14
                atr_vals.append(estado_atr["atr"])
        estado_atr["prev_c"] = b["c"]

    if atr_vals:
        atr_media = sum(atr_vals) / len(atr_vals)
        atr_p50 = percentil_lista(atr_vals, 50)
        atr_p90 = percentil_lista(atr_vals, 90)
    else:
        atr_media = atr_p50 = atr_p90 = 0.0

    fech_por_dia = defaultdict(list)
    for b in barras1:
        fech_por_dia[b["dt"].split(" ")[0]].append(b["c"])
    for d, closes in fech_por_dia.items():
        rsi = rsi_wilder(closes, 14)
        if rsi is not None:
            rsi_vals.append(rsi)
    if rsi_vals:
        rsi_p10 = percentil_lista(rsi_vals, 10)
        rsi_p50 = percentil_lista(rsi_vals, 50)
        rsi_p90 = percentil_lista(rsi_vals, 90)
    else:
        rsi_p10 = rsi_p50 = rsi_p90 = 0.0

    linhas = []
    linhas.append("=" * 64)
    linhas.append("CALIBRACAO WDO — 1 ANO DE TICKS (14/07/2025 a 31/07/2026)")
    linhas.append("Arquivo: WDO$_202507141229_2026073118299.csv")
    linhas.append("=" * 64)
    linhas.append("")
    linhas.append("RESUMO GERAL")
    linhas.append(f"  Ticks processados: {total_ticks:,}".replace(",", "."))
    linhas.append(f"  Volume de tick total: {total_vol:,.0f}".replace(",", "."))
    linhas.append(f"  Dias de pregao: {dias}")
    linhas.append(f"  Preco minimo: {preco_min:.1f} | maximo: {preco_max:.1f}")
    linhas.append(f"  Tempo de processamento: {time.time() - t0:.1f}s")
    linhas.append("")
    linhas.append("1) RUIDO DE TICK — variacao de preco entre trades consecutivos (pts)")
    linhas.append(f"  P50={r_p50:.1f}  P90={r_p90:.1f}  P99={r_p99:.1f}  P99.9={r_p999:.1f}")
    linhas.append("  >> Piso de ruido. Stop abaixo de ~3x P99 tende a ser atropelado.")
    linhas.append(f"  >> STOP ANTI-RUIDO sugerido: ~{max(3.0 * r_p99, 2.0):.1f} pts")
    linhas.append("")
    linhas.append("2) ATR(14) em barras de 1 min (pts)")
    linhas.append(f"  Media={atr_media:.2f}  P50={atr_p50:.2f}  P90={atr_p90:.2f}")
    linhas.append("")
    linhas.append("3) PERFIL POR FAIXA DE HORARIO (barras de 1min)")
    linhas.append(f"  {'Hora':<6}{'range med':>10}{'P90 range':>10}{'ticks/min':>10}{'vol/hora':>12}{'std ret':>9}")
    for hh in sorted(noite_por_hora, key=int):
        ch = noite_por_hora[hh]
        if len(ch["range"]) < 100:
            continue
        rm = sum(ch["range"]) / len(ch["range"])
        rp90 = percentil_lista(ch["range"], 90)
        tpm = ch["ticks"] / max(len(ch["range"]), 1)
        std = 0.0
        if len(ch["ret"]) > 1:
            m = sum(ch["ret"]) / len(ch["ret"])
            std = math.sqrt(sum((x - m) ** 2 for x in ch["ret"]) / (len(ch["ret"]) - 1))
        linhas.append(f"  {hh + ':00':<6}{rm:>10.2f}{rp90:>10.2f}{tpm:>10.1f}{ch['vol']:>12,.0f}{std:>9.5f}".replace(",", "."))
    linhas.append("")
    linhas.append("4) ALVO/STOP ESTATISTICO (range tipico por periodo)")
    linhas.append(f"  1min: P50={r1_p50:.1f}  P90={r1_p90:.1f}  P99={r1_p99:.1f}")
    linhas.append(f"  5min: P50={r5_p50:.1f}  P90={r5_p90:.1f}  P99={r5_p99:.1f}")
    linhas.append(f"  >> Alvo tipico 5min (P50): {r5_p50:.1f} pts ({r5_p50 * VALOR_PONTO:.0f} R$/contrato)")
    linhas.append(f"  >> Alvo forte 5min (P90):  {r5_p90:.1f} pts ({r5_p90 * VALOR_PONTO:.0f} R$/contrato)")
    linhas.append(f"  >> Alvo agressivo (P99):   {r5_p99:.1f} pts ({r5_p99 * VALOR_PONTO:.0f} R$/contrato)")
    linhas.append("")
    linhas.append("5) RSI(14) em barras de 1min — distribuicao")
    linhas.append(f"  P10={rsi_p10:.1f}  P50={rsi_p50:.1f}  P90={rsi_p90:.1f}")
    linhas.append("  >> Referencia para thresholds do modelo price-only")
    linhas.append("")
    linhas.append("6) REGIME POR DIA (media de range 1min) — quantis: LATERAL < P75 <= EXPLOSAO < P90 <= EXTREMO")
    for reg, n in cont_reg.items():
        linhas.append(f"  {reg}: {n} dias ({100.0 * n / max(len(medias_dia), 1):.1f}%)")
    linhas.append("  Detalhe por dia: regime_por_dia_wdo.csv")
    linhas.append("")
    linhas.append("7) SUGESTAO PRATICA (base: 1 ano de ticks reais — sem book)")
    stop = max(3.0 * r_p99, 2.0)
    linhas.append(f"  STOP (anti-ruido):        {stop:.1f} pts ({stop * VALOR_PONTO:.0f} R$/contrato)")
    linhas.append(f"  ALVO conservador (5m P50): {r5_p50:.1f} pts ({r5_p50 * VALOR_PONTO:.0f} R$/contrato)")
    linhas.append(f"  ALVO medio (5m P90):       {r5_p90:.1f} pts ({r5_p90 * VALOR_PONTO:.0f} R$/contrato)")
    linhas.append(f"  Nao arriscar mais que:     {stop:.1f} pts — acima disso o mercado anda")
    linhas.append("")
    linhas.append("AVISO: dados de trade (LAST+VOLUME), sem BID/ASK. Nao serve para entropia_book/escora.")
    linhas.append("Arquivos gerados: barras_1min_wdo.csv, regime_por_dia_wdo.csv")

    with open(OUT_RELATORIO, "w", encoding="utf-8") as fh:
        fh.write("\n".join(linhas))
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
