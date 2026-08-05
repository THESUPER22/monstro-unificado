# -*- coding: utf-8 -*-
"""
Autopsia automatizada de pregao.
Le monstro_wdo.log, CSVs e JSONs para gerar relatorio consolidado.
Uso: python autopsia_automatizada.py [AAAA-MM-DD] [HH:MM]
"""
import json
import csv
import re
import os
import sys
from datetime import datetime
from collections import defaultdict

BASE = r"C:\AIOFEN"
LOG_FILE = os.path.join(BASE, "monstro_wdo.log")


def data_pregao(args=None):
    """Data do pregao a analisar: sys.argv[1] ou hoje. Nunca avalia sys.argv no import."""
    args = args if args is not None else sys.argv
    return args[1] if len(args) > 1 else datetime.now().strftime("%Y-%m-%d")


def fim_manha(data):
    return f"{data} 12:30:00"


def ler_log():
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()


def extrair_trades(lines):
    """Extrai todas as operações do log usando regex."""
    trades = []
    re_abertura = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+.*?Ordem (BUY|SELL) executada\. Ticket: (\d+)"
    )
    re_posicao = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+.*?Nova posi..o iniciada: Ticket=(\d+), Tipo=(BUY|SELL), Entrada=([\d.]+), SL=([\d.]+), TP=([\d.]+)"
    )
    re_saida = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+.*?Deal de sa.da encontrado para ticket (\d+):.*?Lucro=(-?[\d.]+).*?Pre.o Sa.da=([\d.]+).*?Hora=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    )

    aberturas = {}
    posicoes = {}
    saidas = {}

    for line in lines:
        m = re_abertura.search(line)
        if m:
            ts, tipo, ticket = m.groups()
            aberturas[ticket] = {"ts": ts, "tipo": tipo}
            continue

        m = re_posicao.search(line)
        if m:
            ts, ticket, tipo, entrada, sl, tp = m.groups()
            posicoes[ticket] = {
                "ts_posicao": ts,
                "tipo": tipo,
                "entrada": float(entrada),
                "sl": float(sl),
                "tp": float(tp),
            }
            continue

        m = re_saida.search(line)
        if m:
            ts, ticket, lucro, preco_saida, hora = m.groups()
            saidas[ticket] = {
                "ts_log": ts,
                "lucro": float(lucro),
                "preco_saida": float(preco_saida),
                "hora_saida": hora,
            }

    for ticket, ab in aberturas.items():
        pos = posicoes.get(ticket, {})
        sai = saidas.get(ticket, {})
        trades.append({
            "ticket": ticket,
            "tipo": pos.get("tipo", ab.get("tipo")),
            "abertura_log": ab.get("ts"),
            "abertura_pos": pos.get("ts_posicao"),
            "entrada": pos.get("entrada"),
            "sl": pos.get("sl"),
            "tp": pos.get("tp"),
            "fechamento_log": sai.get("ts_log"),
            "hora_saida": sai.get("hora_saida"),
            "preco_saida": sai.get("preco_saida"),
            "lucro": sai.get("lucro"),
        })

    trades.sort(key=lambda x: x["abertura_log"] or "")
    return trades


def ler_csv_data(csv_path, dt_col=None, fmt="%Y.%m.%d %H:%M:%S"):
    """Lê CSV e retorna lista de dicionários. Se dt_col fornecido, parseia datetime."""
    dados = []
    if not os.path.exists(csv_path):
        return dados
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            row["_idx"] = i
            if dt_col and dt_col in row:
                try:
                    row["dt"] = datetime.strptime(row[dt_col], fmt)
                except Exception:
                    pass
            dados.append(row)
    return dados


def cruzar_contexto(trades, decisions, contexto, multitf, williams):
    resultado = []
    for t in trades:
        ts_abertura = t.get("abertura_log")
        if not ts_abertura:
            continue
        dt_abertura = datetime.strptime(ts_abertura, "%Y-%m-%d %H:%M:%S")

        def mais_proximo(dados, col_dt="dt"):
            if not dados:
                return None
            validos = [x for x in dados if col_dt in x]
            if not validos:
                return None
            return min(validos, key=lambda x: abs((x[col_dt] - dt_abertura).total_seconds()))

        dec = mais_proximo(decisions)
        # Para historico_contexto sem timestamp, aproxima pelo índice (mesma frequência ~1s)
        ctx = None
        if contexto and decisions:
            idx_dec = decisions.index(dec) if dec in decisions else int(len(contexto) * 0.5)
            idx_ctx = min(idx_dec, len(contexto) - 1)
            ctx = contexto[idx_ctx]
        mtf = mais_proximo(multitf)
        wr = mais_proximo(williams)

        resultado.append({
            "ticket": t["ticket"],
            "tipo": t["tipo"],
            "abertura": ts_abertura,
            "entrada": t["entrada"],
            "sl": t["sl"],
            "tp": t["tp"],
            "saida": t["hora_saida"],
            "preco_saida": t["preco_saida"],
            "lucro": t["lucro"],
            "decisao": dec.get("acao") if dec else None,
            "confianca": float(dec.get("confianca", 0)) if dec else None,
            "atr": float(dec.get("volatility", 0)) if dec else None,
            "rsi": float(dec.get("rsi_14", 0)) if dec else None,
            "entropia": float(dec.get("entropia_book", 0)) if dec else None,
            "bid_qty": float(ctx.get("bid_qty", 0)) if ctx else None,
            "ask_qty": float(ctx.get("ask_qty", 0)) if ctx else None,
            "action_ctx": ctx.get("action") if ctx else None,
            "reward_ctx": float(ctx.get("reward", 0)) if ctx else None,
            "m5_rsi": float(mtf.get("rsi_5", 0)) if mtf else None,
            "m15_rsi": float(mtf.get("rsi_15", 0)) if mtf else None,
            "m30_rsi": float(mtf.get("rsi_30", 0)) if mtf else None,
            "m5_wr": float(mtf.get("wr_5", 0)) if mtf else None,
            "m15_wr": float(mtf.get("wr_15", 0)) if mtf else None,
            "m30_wr": float(mtf.get("wr_30", 0)) if mtf else None,
            "wr_value": float(wr.get("wr", 0)) if wr else None,
            "wr_zone": wr.get("zona") if wr else None,
            "wr_divergencia": wr.get("divergencia") if wr else None,
        })
    return resultado


def calcular_metricas(trades):
    wins = [t["lucro"] for t in trades if t["lucro"] > 0]
    losses = [t["lucro"] for t in trades if t["lucro"] < 0]
    be = [t["lucro"] for t in trades if t["lucro"] == 0]
    saldo = sum(t["lucro"] for t in trades)
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_gain = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')
    payoff = avg_gain / abs(avg_loss) if avg_loss != 0 else 0
    return {
        "n": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "be": len(be),
        "win_rate": win_rate,
        "saldo": saldo,
        "avg_gain": avg_gain,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "payoff": payoff,
    }


def analisar_agente(lines):
    acoes = defaultdict(int)
    decisoes = []
    for line in lines:
        m = re.search(r"agente iniciado no modo:\s*(\w+)", line)
        if m:
            acoes[m.group(1)] += 1
            continue
        if "DECISAO:" in line or "DECISÃO:" in line:
            decisoes.append(line.strip())
        if "AJUSTE APLICADO" in line:
            decisoes.append(line.strip())
        if "ROLLBACK" in line:
            decisoes.append(line.strip())
    return dict(acoes), decisoes


def analisar_sniper(data=None):
    path = os.path.join(BASE, "sniper_supermo_historico.csv")
    if not os.path.exists(path):
        return None
    rows = ler_csv_data(path, dt_col="timestamp", fmt="%Y.%m.%d %H:%M:%S")
    data_uso = data or data_pregao()
    alvo = datetime.strptime(data_uso, "%Y-%m-%d").date()
    hoje = [r for r in rows if r.get("dt") and r["dt"].date() == alvo]
    return hoje


def analisar_experiencias():
    path = os.path.join(BASE, "experiencias_wdo.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def gerar_plano(metricas, trades):
    """Pilar 2 - gera plano do dia seguinte a partir das metricas/trades.
    SOMENTE LEITURA para humano: nenhuma acao automatica nesta fase."""
    plano = []
    plano.append("=" * 60)
    plano.append("PLANO DO DIA SEGUINTE - MONSTRO WDO v22")
    plano.append(f"Gerado em: {datetime.now():%d/%m/%Y %H:%M:%S}")
    plano.append("=" * 60)

    if metricas["saldo"] <= -100:
        plano.append("[PRIORIDADE 1] Saldo negativo acentuado.")
        plano.append("  -> Contramedida: manter SL=8pts, NAO relaxar filtros.")
        plano.append("  -> Reversivel: sim, ajustar sniper_ratio_min +0.1 na pausa 12:30 se amanha melhorar.")

    sells_loss = [t for t in trades if t.get("tipo") == "SELL" and (t.get("lucro") or 0) < 0]
    if len(sells_loss) >= 3:
        plano.append("[PRIORIDADE 2] Multiplos SELLs loss detectados.")
        plano.append("  -> Contramedida: na pausa 12:30, considerar aumentar dol_conf_min ou CONFIDENCE_GAP.")
        plano.append("  -> Reversivel: sim, voltar ao valor anterior no fecho.")

    if metricas["win_rate"] < 35:
        plano.append("[PRIORIDADE 3] Win rate abaixo de 35%.")
        plano.append("  -> Contramedida: NAO ajustar nada automaticamente; aguardar mais amostra.")
        plano.append("  -> Reversivel: nao se aplica.")

    if metricas["be"] > 5:
        plano.append("[PRIORIDADE 4] Breakevens frequentes.")
        plano.append("  -> Contramedida: trailing stop pode estar muito agressivo; verificar TRAILING_GATILHO.")
        plano.append("  -> Reversivel: sim, ajustar trailing_gatilho 5->7 pts.")

    plano.append("[PADRAO] Manter parametros atuais se nenhuma prioridade critica acionar.")
    return "\n".join(plano)


def run_autopsia(data=None):
    """Interface importavel para o agente (Pilar 2). Retorna (metricas, plano, trades)."""
    data_uso = data or data_pregao()
    lines = ler_log()
    trades = extrair_trades(lines)
    metricas = calcular_metricas(trades)
    plano = gerar_plano(metricas, trades)
    return metricas, plano, trades


def main():
    data_uso = data_pregao()
    fim = fim_manha(data_uso)
    print("=" * 80)
    print(f"AUTOPSIA PREGAO {data_uso} - MONSTRO WDO v22")
    print("=" * 80)

    lines = ler_log()
    trades = extrair_trades(lines)
    metricas = calcular_metricas(trades)
    acoes_agente, decisoes_agente = analisar_agente(lines)

    print("\n--- AGENTE AUTONOMO ---")
    print("Atuacoes do dia:", acoes_agente)
    print("\nDecisoes/registros da arvore:")
    for d in decisoes_agente:
        print(" ", d)

    print("\n--- TABELA DE TRADES ---")
    print(f"{'#':<3} {'Ticket':<12} {'Abertura':<20} {'Tipo':<5} {'Entrada':<9} {'SL':<9} {'TP':<6} {'Saida':<20} {'P&L(R$)':<10} {'Result':<7}")
    for i, t in enumerate(trades, 1):
        res = "GAIN" if t["lucro"] > 0 else ("LOSS" if t["lucro"] < 0 else "BE")
        print(f"{i:<3} {t['ticket']:<12} {str(t['abertura_log']):<20} {t['tipo']:<5} {t['entrada']:<9.1f} {t['sl']:<9.1f} {t['tp']:<6.1f} {str(t['hora_saida']):<20} {t['lucro']:<10.2f} {res:<7}")

    print("\n--- METRICAS FINANCEIRAS (dia completo) ---")
    print(f"Total trades: {metricas['n']}")
    print(f"Wins: {metricas['wins']} | Losses: {metricas['losses']} | BE: {metricas['be']}")
    print(f"Win Rate: {metricas['win_rate']:.1f}%")
    print(f"Saldo liquido: R$ {metricas['saldo']:.2f}")
    print(f"Media Gain: R$ {metricas['avg_gain']:.2f}")
    print(f"Media Loss: R$ {metricas['avg_loss']:.2f}")
    print(f"Profit Factor: {metricas['profit_factor']:.2f}")
    print(f"Payoff Medio: {metricas['payoff']:.2f}")

    # Periodo da manha (ate 12:30)
    trades_manha = [t for t in trades if t["abertura_log"] and t["abertura_log"] <= fim]
    met_manha = calcular_metricas(trades_manha)
    print("\n--- METRICAS FINANCEIRAS (ATE 12:30) ---")
    print(f"Total trades: {met_manha['n']}")
    print(f"Wins: {met_manha['wins']} | Losses: {met_manha['losses']} | BE: {met_manha['be']}")
    print(f"Win Rate: {met_manha['win_rate']:.1f}%")
    print(f"Saldo liquido: R$ {met_manha['saldo']:.2f}")

    # Carrega CSVs
    decisions = ler_csv_data(os.path.join(BASE, "decisions_wdo.csv"), "timestamp")
    contexto = ler_csv_data(os.path.join(BASE, "historico_contexto_wdo.csv"))
    multitf = ler_csv_data(os.path.join(BASE, "historico_multitf.csv"), "timestamp")
    williams = ler_csv_data(os.path.join(BASE, "williams_r_historico.csv"), "timestamp", fmt="%Y-%m-%d %H:%M:%S")

    print(f"\n--- VOLUMETRIA CSV ---")
    print(f"decisions_wdo.csv: {len(decisions)} registros")
    print(f"historico_contexto_wdo.csv: {len(contexto)} registros")
    print(f"historico_multitf.csv: {len(multitf)} registros")
    print(f"williams_r_historico.csv: {len(williams)} registros")

    cruzado = cruzar_contexto(trades, decisions, contexto, multitf, williams)

    print("\n--- CONTEXTO DOS TRADES (primeiros 10) ---")
    print(f"{'#':<3} {'Tipo':<5} {'IA':<6} {'Conf':<6} {'ATR':<6} {'RSI':<6} {'Entropia':<9} {'CtxAction':<10} {'M5/M15/M30 WR':<35} {'WR':<8} {'P&L':<8}")
    for i, c in enumerate(cruzado[:10], 1):
        mtf_wr = f"{c['m5_wr']:.0f}/{c['m15_wr']:.0f}/{c['m30_wr']:.0f}" if c['m5_wr'] is not None else "None"
        print(f"{i:<3} {c['tipo']:<5} {str(c['decisao']):<6} {c['confianca']:<6.3f} {c['atr']:<6.2f} {c['rsi']:<6.1f} {c['entropia']:<9.3f} {str(c['action_ctx']):<10} {mtf_wr:<35} {str(c['wr_value'])[:7]:<8} {c['lucro']:<8.2f}")

    # Sniper
    sniper_hoje = analisar_sniper(data_uso)
    print(f"\n--- SNIPER SUPERMO ---")
    print(f"Registros hoje: {len(sniper_hoje) if sniper_hoje else 0}")
    if sniper_hoje:
        ativos = [r for r in sniper_hoje if float(r.get("score", 0)) > 0]
        print(f"Ativacoes (score > 0): {len(ativos)}")
        for r in ativos[:5]:
            print(" ", r)

    # Experiencias
    exp = analisar_experiencias()
    print(f"\n--- EXPERIENCIAS WDO JSON ---")
    print(f"Total experiencias: {len(exp)}")
    if exp:
        positivas = [e for e in exp if e.get("lucro", 0) > 0]
        negativas = [e for e in exp if e.get("lucro", 0) < 0]
        print(f"Positivas: {len(positivas)} | Negativas: {len(negativas)} | Zero: {len(exp) - len(positivas) - len(negativas)}")

    # Salva JSON intermediário
    output = {
        "data": data_uso,
        "metricas": metricas,
        "metricas_manha": met_manha,
        "trades": trades,
        "agente": {"atuacoes": acoes_agente, "decisoes": decisoes_agente},
        "cruzamento": cruzado,
    }
    out_path = os.path.join(BASE, f"autopsia_{data_uso.replace('-', '')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[OK] Relatorio intermediario salvo em: {out_path}")


if __name__ == "__main__":
    main()
