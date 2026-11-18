# -*- coding: utf-8 -*-
"""Avaliador PRE-REGISTRADO do shadow de SL/TP (P1 #2, ROADMAP 23.54.3).

Este script e congelado ANTES da coleta: o SHA-256 do arquivo fica registrado
no ROADMAP e um teste (`tests/test_avaliar_shadow.py`) falha se o hash mudar.
Alterar o avaliador depois de ver resultado invalida a coleta.

Entrada: JSONL (ou lista JSON) com um sinal por linha:

    {"ts": "2026-11-18T10:00:00", "dia": "2026-11-18",
     "sinal": "BUY", "operado": true,
     "sl_pts": 8.0, "tp_pts": 8.0, "atr": 12.3,
     "path": [[t, bid, ask], ...]}          # 1 s, 30 min pos-sinal

Regras de fill (iguais para todas as variantes, ROADMAP 23.54.3):
  - entrada 0,5 pt contra o sinal (BUY paga ask+0,5; SELL recebe bid-0,5);
  - TP so conta se o preco ULTRAPASSAR 1 tick (0,5 pt) do nivel; fill no nivel;
  - SL com 1 tick de slippage e respeitando gap: `min(preco, nivel) - 1 tick`
    no BUY e `max(preco, nivel) + 1 tick` no SELL;
  - saida pelo lado certo do book (BUY no bid, SELL no ask);
  - fecho forcado as 17:35 BRT = **20:35 UTC** (Brasil sem horario de verao);
  - custo R$ 1,20/contrato = 0,12 pt (1 pt = R$ 10,00).

Tempo: TODO timestamp e normalizado para UTC. Epoch numerico e lido como
`datetime.fromtimestamp(ts, tz=UTC)` (relogio do servidor); string sem fuso e
tratada como UTC. O JSONL do executor grava UTC.

Calibracao: a A0 simulada e comparada com o resultado REAL dos sinais operados
(`pnl_real_pts` no JSONL ou arquivo `--reais {ticket: pts}`). Se
`|media(sim - real)| > 0,5 pt` o simulador e declarado INVALIDO e nada e
promovido; sem dados reais tambem nao promove.

Decisao: diferenca PAREADA de expectativa liquida contra A0, apenas nos sinais
`operado=true`; >= 200 sinais e >= 15 pregoes; IC 95% por bootstrap de dias
(blocos = dia, seed fixa); limite inferior > 0, media >= +0,5 pt, >= 60% dos
dias positivos e Holm para as 3 comparacoes (B, C, D contra A0). Alem disso,
cada variante precisa passar no criterio ABSOLUTO: liquido > 0 com limite
inferior do IC95 > 0 (a 0,5 pt/lado).

Parada: se em 40 pregoes nao houver 200 sinais pareados, encerra como
"inconclusivo" (nao promove, nao estende).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, time, timezone
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TICK = 0.5
CUSTO_PTS = 1.20 / 10.0          # R$ 1,20 por contrato / R$ 10,00 por ponto
HORARIO_FECHO_UTC = time(20, 35)  # 17:35 BRT (UTC-3, sem DST)

LIMIAR_SINAIS = 200
LIMIAR_PREGOES = 15
LIMIAR_PREGOES_MAX = 40
GANHO_MIN_PTS = 0.5
FRACAO_DIAS_POSITIVOS = 0.60
ALFA = 0.05
N_BOOTSTRAP = 2000
SEED_BOOTSTRAP = 20261117
TOLERANCIA_CALIBRACAO_PTS = 0.5

VARIANTES = ("A0", "B", "C", "D")


# ------------------------------------------------------------------ dados ---
def _quando(valor) -> datetime:
    """Normaliza para UTC: epoch = relogio do servidor; string sem fuso = UTC."""
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(float(valor), tz=timezone.utc)
    dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def carregar(caminho: str) -> List[dict]:
    """Le JSONL (um objeto por linha) ou um array JSON."""
    with open(caminho, encoding="utf-8") as f:
        texto = f.read().strip()
    if not texto:
        return []
    if texto.startswith("["):
        dados = json.loads(texto)
    else:
        dados = [json.loads(linha) for linha in texto.splitlines() if linha.strip()]
    if not isinstance(dados, list):
        raise ValueError("entrada deve ser uma lista de sinais")
    return dados


# -------------------------------------------------------------- variantes ---
def sl_tp(variante: str, sinal: dict) -> Tuple[float, float]:
    """(SL, TP) em pontos para a variante, so com o que foi pre-registrado."""
    if variante == "A0":
        return float(sinal["sl_pts"]), float(sinal["tp_pts"])
    if variante == "B":
        atr = float(sinal["atr"])
        return max(3.0, 1.5 * atr), 3.0 * atr
    if variante == "C":
        return 8.0, 8.0
    if variante == "D":
        return 8.0, 12.0
    raise ValueError(f"variante desconhecida: {variante!r}")


# --------------------------------------------------------------- simulacao -
def simular(sinal: dict, variante: str) -> dict:
    """Simula UM sinal na variante e devolve o resultado bruto (pontos)."""
    lado = 1 if str(sinal["sinal"]).upper() == "BUY" else -1
    path = sinal.get("path") or []
    if not path:
        raise ValueError("sinal sem path")

    sl_pts, tp_pts = sl_tp(variante, sinal)
    _, bid0, ask0 = path[0]
    entrada = (ask0 + 0.5) if lado == 1 else (bid0 - 0.5)
    sl_nivel = entrada - lado * sl_pts
    tp_nivel = entrada + lado * tp_pts

    def saida_do_lado(bid, ask):
        return bid if lado == 1 else ask

    motivo = "fim_dados"
    saida = saida_do_lado(path[-1][1], path[-1][2])
    for ponto in path[1:]:
        quando = _quando(ponto[0])
        bid, ask = ponto[1], ponto[2]
        preco = saida_do_lado(bid, ask)
        if quando.time() >= HORARIO_FECHO_UTC:
            saida, motivo = preco, "fechamento"
            break
        if lado == 1:
            if preco <= sl_nivel:
                # gap: se abriu abaixo do nivel, piora a partir do preco
                saida, motivo = min(preco, sl_nivel) - TICK, "sl"
                break
            if tp_pts > 0 and preco >= tp_nivel + TICK:
                saida, motivo = tp_nivel, "tp"
                break
        else:
            if preco >= sl_nivel:
                saida, motivo = max(preco, sl_nivel) + TICK, "sl"
                break
            if tp_pts > 0 and preco <= tp_nivel - TICK:
                saida, motivo = tp_nivel, "tp"
                break

    bruto = lado * (saida - entrada)
    return {"bruto_pts": bruto, "motivo": motivo, "sl_pts": sl_pts,
            "tp_pts": tp_pts, "entrada": entrada, "saida": saida}


def liquido_pts(bruto: float, slippage_lado: float = 0.5) -> float:
    """Bruto menos slippage adicional por lado e custo de R$ 1,20."""
    return bruto - 2.0 * slippage_lado - CUSTO_PTS


# -------------------------------------------------------------- estatistica -
def bootstrap_por_dia(diffs_por_dia: Dict[str, List[float]],
                      n: int = N_BOOTSTRAP,
                      seed: int = SEED_BOOTSTRAP) -> dict:
    """IC 95% da media, reamostrando DIAS inteiros (blocos)."""
    dias = sorted(diffs_por_dia)
    if not dias:
        return {"media": 0.0, "li": 0.0, "ls": 0.0, "n_dias": 0}
    todas = [x for d in dias for x in diffs_por_dia[d]]
    rng = random.Random(seed)
    medias = []
    for _ in range(n):
        amostra = []
        for _ in dias:
            amostra.extend(diffs_por_dia[rng.choice(dias)])
        medias.append(mean(amostra))
    medias.sort()
    return {
        "media": mean(todas),
        "li": medias[int(0.025 * n)],
        "ls": medias[min(n - 1, int(0.975 * n))],
        "n_dias": len(dias),
        "n": len(todas),
    }


def p_unilateral(diffs_por_dia: Dict[str, List[float]],
                 n: int = N_BOOTSTRAP,
                 seed: int = SEED_BOOTSTRAP) -> float:
    """p bootstrap unilateral de H0: media <= 0."""
    dias = sorted(diffs_por_dia)
    if not dias:
        return 1.0
    rng = random.Random(seed)
    menores = 0
    for _ in range(n):
        amostra = []
        for _ in dias:
            amostra.extend(diffs_por_dia[rng.choice(dias)])
        if mean(amostra) <= 0:
            menores += 1
    return (menores + 1) / (n + 1)


def holm(pvals: Dict[str, float]) -> Dict[str, float]:
    """Ajuste de Holm para as 3 comparacoes pre-registradas."""
    itens = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(itens)
    ajustado = {}
    acumulado = 0.0
    for i, (chave, p) in enumerate(itens):
        valor = min(1.0, (m - i) * p)
        acumulado = max(acumulado, valor)
        ajustado[chave] = acumulado
    return ajustado


def status_coleta(n_sinais: int, n_pregoes: int) -> str:
    """Regra de parada congelada."""
    if n_sinais >= LIMIAR_SINAIS and n_pregoes >= LIMIAR_PREGOES:
        return "decidir"
    if n_pregoes >= LIMIAR_PREGOES_MAX:
        return "inconclusivo"
    return "coletando"


# ------------------------------------------------------------------ avaliar -
def calibrar(sinais: Sequence[dict], pareado_a0: Sequence[dict],
             reais: Optional[Dict[str, float]] = None) -> dict:
    """A0 simulada vs resultado REAL dos sinais operados.

    ``reais`` mapeia ``str(ticket) -> pnl em pontos``; se ausente, usa
    ``pnl_real_pts`` do proprio sinal. Tolerancia: ``|media(sim - real)|``
    <= 0,5 pt. Sem dados reais o simulador NAO e validado.
    """
    reais = reais or {}
    difs: List[float] = []
    for sinal, sim in zip([s for s in sinais if s.get("operado")], pareado_a0):
        real = reais.get(str(sinal.get("ticket")))
        if real is None:
            real = sinal.get("pnl_real_pts")
        if real is None:
            continue
        difs.append(float(sim["liquido_pts"]) - float(real))
    if not difs:
        return {"n": 0, "media": None, "ok": False,
                "motivo": "sem dados reais (pnl_real_pts/ticket ausente)"}
    media = mean(difs)
    ok = abs(media) <= TOLERANCIA_CALIBRACAO_PTS
    return {"n": len(difs), "media": media, "ok": ok,
            "motivo": "" if ok else "simulador invalido (|media| > 0,5 pt)"}


def avaliar(sinais: Sequence[dict], slippage_lado: float = 0.5,
            reais: Optional[Dict[str, float]] = None) -> dict:
    """Roda as 4 variantes e devolve resultados por variante e decisao."""
    por_variante: Dict[str, List[dict]] = {v: [] for v in VARIANTES}
    for sinal in sinais:
        dia = sinal.get("dia") or _quando(sinal["ts"]).date().isoformat()
        for v in VARIANTES:
            r = simular(sinal, v)
            r.update({"dia": str(dia)[:10],
                      "operado": bool(sinal.get("operado", False))})
            r["liquido_pts"] = liquido_pts(r["bruto_pts"], slippage_lado)
            por_variante[v].append(r)

    # pareado: so sinais que o robo realmente operou, na mesma ordem
    pareado = {v: [] for v in VARIANTES}
    for i, sinal in enumerate(sinais):
        if not bool(sinal.get("operado", False)):
            continue
        for v in VARIANTES:
            pareado[v].append(por_variante[v][i])

    diffs: Dict[str, Dict[str, List[float]]] = {}
    resumo: Dict[str, dict] = {}
    for v in VARIANTES:
        por_dia: Dict[str, List[float]] = {}
        for r in pareado[v]:
            por_dia.setdefault(r["dia"], []).append(r["liquido_pts"])
        resumo[v] = {"n": len(pareado[v]), "liquido_pts": mean(
            [r["liquido_pts"] for r in pareado[v]]) if pareado[v] else 0.0}
        resumo[v]["absoluto"] = bootstrap_por_dia(por_dia)
        if v != "A0":
            d: Dict[str, List[float]] = {}
            for a, b in zip(pareado["A0"], pareado[v]):
                d.setdefault(b["dia"], []).append(b["liquido_pts"] - a["liquido_pts"])
            diffs[v] = d
            resumo[v]["diff_vs_A0"] = bootstrap_por_dia(d)
            resumo[v]["p"] = p_unilateral(d)

    pvals = {v: resumo[v]["p"] for v in diffs}
    ajustados = holm(pvals) if pvals else {}
    for v, p in ajustados.items():
        resumo[v]["p_holm"] = p

    n_pareados = len(pareado["A0"])
    n_pregoes = len({r["dia"] for r in pareado["A0"]})
    status = status_coleta(n_pareados, n_pregoes)
    calibracao = calibrar(sinais, pareado["A0"], reais)

    promovidas = []
    for v in diffs:
        r = resumo[v]
        dias = diffs[v]
        frac_pos = (sum(1 for d in dias if mean(dias[d]) > 0) / len(dias)
                    if dias else 0.0)
        r["frac_dias_positivos"] = frac_pos
        ok = (status == "decidir"
              and calibracao["ok"]
              and r["absoluto"]["li"] > 0
              and r["diff_vs_A0"]["li"] > 0
              and r["diff_vs_A0"]["media"] >= GANHO_MIN_PTS
              and frac_pos >= FRACAO_DIAS_POSITIVOS
              and r.get("p_holm", 1.0) < ALFA)
        r["promover"] = bool(ok)
        if ok:
            promovidas.append(v)

    return {"status_coleta": status, "n_pareados": n_pareados,
            "n_pregoes": n_pregoes, "slippage_lado": slippage_lado,
            "calibracao": calibracao, "resumo": resumo,
            "promovidas": promovidas, "diffs_por_dia": diffs}


# --------------------------------------------------------------------- CLI --
def _imprimir(resultado: dict) -> None:
    print(f"coleta: {resultado['status_coleta']} "
          f"({resultado['n_pareados']} sinais pareados, "
          f"{resultado['n_pregoes']} pregoes)")
    print(f"slippage adicional: {resultado['slippage_lado']:g} pt/lado | "
          f"custo {CUSTO_PTS:g} pt/trade")
    cal = resultado["calibracao"]
    media = "n/d" if cal["media"] is None else f"{cal['media']:+.2f}"
    print(f"calibracao A0: n={cal['n']} media={media} "
          f"{'OK' if cal['ok'] else 'INVALIDO'}"
          + (f" ({cal['motivo']})" if cal["motivo"] else ""))
    print(f"{'var':>4} {'n':>5} {'liquido':>9} {'abs IC95':>18} "
          f"{'dif vs A0':>11} {'IC95':>18} {'%dias+':>7} {'p_Holm':>7} "
          f"{'promover':>8}")
    for v, r in resultado["resumo"].items():
        d = r.get("diff_vs_A0", {})
        a = r.get("absoluto", {})
        ic = f"[{d.get('li', 0):+.2f}, {d.get('ls', 0):+.2f}]" if d else "-"
        ic_abs = f"[{a.get('li', 0):+.2f}, {a.get('ls', 0):+.2f}]" if a else "-"
        print(f"{v:>4} {r['n']:>5} {r['liquido_pts']:>+9.2f} "
              f"{ic_abs:>18} "
              f"{d.get('media', 0):>+11.2f} {ic:>18} "
              f"{r.get('frac_dias_positivos', 0):>6.0%} "
              f"{r.get('p_holm', float('nan')):>7.3f} "
              f"{'SIM' if r.get('promover') else 'nao':>8}")
    print(f"promovidas: {resultado['promovidas'] or 'nenhuma'}")


def _carregar_reais(caminho: str) -> Dict[str, float]:
    """Le {ticket: pnl_pts} de JSON (objeto) ou JSONL ({ticket, pnl_pts})."""
    with open(caminho, encoding="utf-8") as f:
        texto = f.read().strip()
    if not texto:
        return {}
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        dados = [json.loads(l) for l in texto.splitlines() if l.strip()]
    if isinstance(dados, dict):
        if "ticket" in dados:
            dados = [dados]
        else:
            return {str(k): float(v) for k, v in dados.items()}
    return {str(item["ticket"]): float(item["pnl_pts"]) for item in dados}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--entrada", required=True, help="JSONL/JSON dos sinais")
    p.add_argument("--saida", help="grava o resultado completo em JSON")
    p.add_argument("--reais", help="JSONL/JSON {ticket: pnl_pts} p/ calibracao")
    p.add_argument("--slippage-lado", type=float, default=0.5,
                   choices=(0.0, 0.5, 1.0))
    args = p.parse_args(argv)

    reais = _carregar_reais(args.reais) if args.reais else None
    resultado = avaliar(carregar(args.entrada), args.slippage_lado, reais)
    _imprimir(resultado)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
