# -*- coding: utf-8 -*-
"""Filtro PRE-REGISTRADO da coleta shadow de SL/TP (P1 18/11).

Regra unica e congelada (SHA-256 no teste e no ROADMAP):

    mantem o sinal se ``completo is True`` E ``max_gap_s <= 10.0``

O ``max_gap_s`` gravado pelo coletor e conferido contra o ``path``: vale o
MAIOR dos dois (fail-closed), para que um campo desatualizado nunca esconda um
buraco real. Linhas sem o campo sao recalculadas do ``path`` com a MESMA
definicao de ``shadow_sltp.max_gap_s`` (primeira amostra, buracos entre
amostras e cauda ate ``inicio + duracao``). Linha ilegivel, sem ``path`` ou com
gap ilegivel e DESCARTADA: nunca "passa por zero".

Nao altera o avaliador congelado (``avaliar_shadow_sltp.py``). Le JSONL (um
objeto por linha) ou um array JSON e sempre escreve JSONL.

Uso:
    python filtrar_completos.py --entrada <coleta.jsonl> --saida <filtrado.jsonl>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional

GAP_MAX_S = 10.0
DURACAO_PADRAO_S = 1800.0


def _epoch(valor) -> Optional[float]:
    """Normaliza epoch/ISO para segundos. Sem fuso = UTC (igual ao avaliador)."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:  # noqa: BLE001
        return None


def _gap_do_path(sinal: dict) -> Optional[float]:
    """Recalcula o gap do ``path`` (mesma definicao do coletor)."""
    path = sinal.get("path")
    if not isinstance(path, list) or not path:
        return None
    try:
        tempos = [float(p[0]) for p in path]
        inicio = _epoch(sinal.get("ts"))
        if inicio is None:
            inicio = tempos[0]
        duracao = sinal.get("duracao_s")
        if not isinstance(duracao, (int, float)) or isinstance(duracao, bool):
            duracao = DURACAO_PADRAO_S
        buracos = [max(0.0, tempos[0] - inicio)]
        buracos += [max(0.0, b - a) for a, b in zip(tempos, tempos[1:])]
        buracos.append(max(0.0, inicio + float(duracao) - tempos[-1]))
        return round(max(buracos), 3)
    except Exception:  # noqa: BLE001
        return None


def max_gap_s(sinal: dict) -> Optional[float]:
    """Maior buraco (s) na linha do tempo; ``None`` se ilegivel.

    Fail-closed: usa o MAIOR entre o campo gravado e o recalculado do ``path``.
    Um campo desatualizado nunca esconde um buraco real.
    """
    campo = sinal.get("max_gap_s")
    if isinstance(campo, bool) or not isinstance(campo, (int, float)):
        campo = None
    else:
        campo = float(campo)
    calc = _gap_do_path(sinal)
    if campo is None:
        return calc
    if calc is None:
        return campo
    return max(campo, calc)


def decidir(sinal) -> tuple:
    """(manter, motivo). Motivos: ok | incompleto | gap | invalido."""
    if not isinstance(sinal, dict):
        return False, "invalido"
    path = sinal.get("path")
    if not isinstance(path, list) or not path:
        return False, "invalido"
    if sinal.get("completo") is not True:
        return False, "incompleto"
    gap = max_gap_s(sinal)
    if gap is None:
        return False, "invalido"
    if gap > GAP_MAX_S:
        return False, "gap"
    return True, "ok"


def carregar_texto(texto: str) -> list:
    """[(objeto, texto_original)] preservando a linha crua do JSONL."""
    limpo = texto.strip()
    if not limpo:
        return []
    if limpo.startswith("["):
        dados = json.loads(limpo)
        if not isinstance(dados, list):
            raise ValueError("entrada deve ser um array JSON")
        return [(d, None) for d in dados]
    saida = []
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        try:
            obj = json.loads(linha)
        except Exception:  # noqa: BLE001 - linha ruim e descartada depois
            obj = None
        saida.append((obj, linha))
    return saida


def filtrar(texto: str) -> tuple:
    """(linhas_mantidas, estatisticas). Nao reescreve o que foi mantido."""
    itens = carregar_texto(texto)
    mantidos = []
    estat = {"total": len(itens), "mantidos": 0, "incompleto": 0,
             "gap": 0, "invalido": 0}
    for obj, original in itens:
        ok, motivo = decidir(obj)
        if not ok:
            estat[motivo] += 1
            continue
        estat["mantidos"] += 1
        if original is not None:
            mantidos.append(original.rstrip("\r\n"))
        else:
            mantidos.append(json.dumps(obj, ensure_ascii=False,
                                       separators=(",", ":")))
    return mantidos, estat


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Filtro congelado do shadow SL/TP")
    p.add_argument("--entrada", required=True)
    p.add_argument("--saida", help="arquivo de saida (padrao: stdout)")
    args = p.parse_args(argv)

    with open(args.entrada, encoding="utf-8") as f:
        texto = f.read()
    mantidos, estat = filtrar(texto)
    corpo = "".join(linha + "\n" for linha in mantidos)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8", newline="\n") as f:
            f.write(corpo)
    else:
        sys.stdout.write(corpo)
    print("filtro: " + " ".join(f"{k}={v}" for k, v in estat.items()),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
