#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relatorio_metricas.py - P1 17/11 #1

Le os deals do MT5, agrupa por position_id e imprime/salva o relatorio de
metricas com intervalo de confianca (bruto, liquido e gate). Somente leitura:
nao toca no robo, nao envia ordem, nao altera config.

Uso:
    python relatorio_metricas.py                # 15 dias, magic do robo
    python relatorio_metricas.py --dias 30
    python relatorio_metricas.py --magics 123456,7008
    python relatorio_metricas.py --magics todos
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from escrita_atomica import salvar_texto_atomico  # noqa: E402
from metricas import (formatar_relatorio, por_dia,  # noqa: E402
                      resultado_por_posicao, resumo)


def _config():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def _magics_de(texto, cfg):
    """None = todos; '123456,7008' = lista; vazio = magic do robo."""
    if texto is None or texto == "":
        return [int(cfg.get("geral", {}).get("magic_number", 123456))]
    if texto.strip().lower() in ("todos", "all", "*"):
        return None
    return [int(p) for p in texto.replace(";", ",").split(",") if p.strip()]


def _json_seguro(obj):
    if isinstance(obj, dict):
        return {k: _json_seguro(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_seguro(v) for v in obj]
    if isinstance(obj, float) and (obj != obj or obj in (float("inf"), float("-inf"))):
        return None
    return obj


def main(argv=None):
    ap = argparse.ArgumentParser(description="Relatorio de metricas com IC (WDO)")
    ap.add_argument("--dias", type=int, default=15,
                    help="janela em dias corridos (default 15 ~ 10 sessoes)")
    ap.add_argument("--magics", default=None,
                    help="ex.: 123456,7008 | 'todos' | vazio = magic do robo")
    ap.add_argument("--saida", default=None,
                    help="arquivo .txt (default relatorio_metricas_<data>.txt)")
    ap.add_argument("--json", action="store_true", help="tambem imprime JSON")
    args = ap.parse_args(argv)

    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        print(f"MT5 indisponivel: {e}")
        return 2

    cfg = _config()
    magics = _magics_de(args.magics, cfg)

    if not mt5.initialize():
        print(f"MT5 nao inicializou: {mt5.last_error()}")
        return 1
    try:
        agora = datetime.now()
        ini = agora - timedelta(days=max(1, args.dias))
        deals = mt5.history_deals_get(ini, agora + timedelta(days=1))
        if deals is None:
            print(f"history_deals_get retornou None (terminal sincronizando?): {mt5.last_error()}")
            return 1
        posicoes = resultado_por_posicao(deals, magics)
    finally:
        mt5.shutdown()

    res = resumo(posicoes)
    dias = por_dia(posicoes)
    periodo = f"{ini:%Y-%m-%d} -> {agora:%Y-%m-%d} ({args.dias} dias)"
    texto = formatar_relatorio(res, dias, periodo, magics)

    print(texto)
    if res["n"] == 0:
        print(f"AVISO: nenhuma posicao fechada para magics {magics} na janela.")

    saida = args.saida or os.path.join(
        BASE, f"relatorio_metricas_{agora:%Y-%m-%d}.txt")
    caminho = salvar_texto_atomico(saida, texto)
    print(f"[relatorio] salvo em {caminho}")

    if args.json:
        print(json.dumps(_json_seguro({"resumo": res, "por_dia": dias}),
                         indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
