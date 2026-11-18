# -*- coding: utf-8 -*-
"""Metricas de resultado por operacao, com intervalo de confianca (P1 17/11 #1).

Por que existe: o numero que decide nao e a media, e a incerteza. Em 17/11 o
historico LIVE tinha 69 trades, +1,29 pt/trade bruto e erro padrao ~1 pt - ou
seja, indistinguivel de zero. Qualquer relatorio que mostre so a media esconde
exatamente o que importa.

Fonte: deals do MT5 agrupados por ``position_id`` (um resultado por operacao,
somando ``profit + commission + swap + fee``). Nunca o parse do log nem o
``historico_lucro`` em memoria.

Tres visoes, com o custo canonico do projeto:
  - bruto:   como veio do extrato;
  - liquido: menos R$ 1,20 por contrato (0,60 entrada + 0,60 saida);
  - gate:    liquido menos slippage de 1,0 pt por lado (2,0 pt/trade).

1 ponto de WDO = R$ 10,00 por contrato.

Modulo puro (sem MT5/TensorFlow), testavel em ``tests/test_metricas.py``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence

VALOR_PONTO_RS = 10.0          # 1 ponto de WDO por contrato
CUSTO_RS_POR_CONTRATO = 1.20   # 0,60 entrada + 0,60 saida
SLIPPAGE_PT_POR_LADO = 1.0     # gate canonico

# t de Student bicaudal 95%. Tabela + interpolacao linear: nao vale arrastar
# scipy para dentro do relatorio por causa de 20 numeros.
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    40: 2.021, 50: 2.009, 60: 2.000, 80: 1.990, 100: 1.984,
    120: 1.980, 200: 1.972, 500: 1.965,
}
_T95_INF = 1.960


def _r(x, casas: int = 4):
    if x is None or (isinstance(x, float) and math.isinf(x)):
        return x
    return round(float(x), casas)


def t_critico95(graus_liberdade: int) -> float:
    """t bicaudal 95% para ``gl`` graus de liberdade (interpolado)."""
    gl = int(graus_liberdade)
    if gl < 1:
        raise ValueError(f"graus de liberdade deve ser >= 1 (recebido {graus_liberdade!r})")
    if gl in _T95:
        return _T95[gl]
    chaves = sorted(_T95)
    if gl > chaves[-1]:
        # 200 < gl < infinito: desce suavemente de 1,972 para 1,960
        return _r(_T95_INF + (_T95[chaves[-1]] - _T95_INF) * (200.0 / gl), 3)
    anterior = max(k for k in chaves if k < gl)
    seguinte = min(k for k in chaves if k > gl)
    fracao = (gl - anterior) / float(seguinte - anterior)
    return _r(_T95[anterior] + fracao * (_T95[seguinte] - _T95[anterior]), 3)


def _campo(deal, nome: str, padrao=None):
    valor = deal.get(nome, padrao) if isinstance(deal, dict) else getattr(deal, nome, padrao)
    return padrao if valor is None else valor


@dataclass(frozen=True)
class Posicao:
    """Resultado fechado de uma posicao (todos os deals do position_id)."""

    position_id: int
    symbol: str
    magic: int
    volume: float
    resultado_rs: float
    entrada_ts: int
    saida_ts: int
    n_deals: int

    @property
    def resultado_pt(self) -> float:
        """Resultado em pontos POR CONTRATO (normaliza volume)."""
        if self.volume <= 0:
            return 0.0
        return self.resultado_rs / (VALOR_PONTO_RS * self.volume)

    @property
    def dia(self) -> str:
        """Dia do SERVIDOR (mesma convencao do MT5, ver pnl_dia.py)."""
        return datetime.fromtimestamp(self.saida_ts, timezone.utc).date().isoformat()


def resultado_por_posicao(deals: Iterable, magics: Optional[Iterable[int]] = None) -> List[Posicao]:
    """Agrupa deals por ``position_id`` e soma o resultado de cada posicao.

    Deals com ``position_id`` 0 (deposito, ajuste, balanco) ficam de fora: nao
    sao operacao. Retorna a lista ordenada por horario de saida.
    """
    alvo = set(int(m) for m in magics) if magics is not None else None
    acumulado: Dict[int, dict] = {}

    for deal in deals or ():
        pid = _campo(deal, "position_id", 0)
        if not pid:
            continue
        magic = int(_campo(deal, "magic", -1))
        if alvo is not None and magic not in alvo:
            continue

        item = acumulado.setdefault(int(pid), {
            "symbol": _campo(deal, "symbol", ""),
            "magic": magic,
            "resultado": 0.0,
            "volume_entrada": 0.0,
            "volume_max": 0.0,
            "entrada": None,
            "saida": 0,
            "n": 0,
        })
        item["resultado"] += (float(_campo(deal, "profit", 0.0))
                              + float(_campo(deal, "commission", 0.0))
                              + float(_campo(deal, "swap", 0.0))
                              + float(_campo(deal, "fee", 0.0)))
        volume = float(_campo(deal, "volume", 0.0))
        item["volume_max"] = max(item["volume_max"], volume)
        if int(_campo(deal, "entry", 0)) == 0:      # DEAL_ENTRY_IN
            item["volume_entrada"] += volume
        ts = int(_campo(deal, "time", 0))
        item["entrada"] = ts if item["entrada"] is None else min(item["entrada"], ts)
        item["saida"] = max(item["saida"], ts)
        item["n"] += 1

    posicoes = []
    for pid, item in acumulado.items():
        volume = item["volume_entrada"] or item["volume_max"] or 1.0
        posicoes.append(Posicao(
            position_id=pid,
            symbol=item["symbol"],
            magic=item["magic"],
            volume=volume,
            resultado_rs=_r(item["resultado"], 2),
            entrada_ts=item["entrada"] or 0,
            saida_ts=item["saida"],
            n_deals=item["n"],
        ))
    posicoes.sort(key=lambda p: (p.saida_ts, p.position_id))
    return posicoes


def estatisticas(valores: Sequence[float]) -> dict:
    """Estatisticas de uma serie (em pontos): media, EP, IC95, PF, DD, sequencia."""
    vals = [float(v) for v in valores]
    n = len(vals)
    if n == 0:
        return {"n": 0, "media": None, "desvio": None, "erro_padrao": None,
                "ic95": (None, None), "total": 0.0, "minimo": None,
                "maximo": None, "vitorias": 0, "empates": 0, "derrotas": 0,
                "taxa_acerto": None, "fator_lucro": None, "drawdown": 0.0,
                "seq_perdas": 0}

    media = sum(vals) / n
    desvio = (math.sqrt(sum((v - media) ** 2 for v in vals) / (n - 1))
              if n > 1 else 0.0)
    ep = desvio / math.sqrt(n) if n > 1 else None
    if ep is None:
        ic = (None, None)
    else:
        t = t_critico95(n - 1)
        ic = (media - t * ep, media + t * ep)

    ganhos = sum(v for v in vals if v > 0)
    perdas = -sum(v for v in vals if v < 0)
    if perdas > 0:
        pf = ganhos / perdas
    else:
        pf = math.inf if ganhos > 0 else 0.0

    pico = 0.0
    acumulado = 0.0
    drawdown = 0.0
    for v in vals:
        acumulado += v
        pico = max(pico, acumulado)
        drawdown = max(drawdown, pico - acumulado)

    seq = atual = 0
    for v in vals:
        if v < 0:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 0

    return {
        "n": n,
        "media": _r(media),
        "desvio": _r(desvio),
        "erro_padrao": _r(ep),
        "ic95": (_r(ic[0]), _r(ic[1])),
        "total": _r(sum(vals)),
        "minimo": _r(min(vals)),
        "maximo": _r(max(vals)),
        "vitorias": sum(1 for v in vals if v > 0),
        "empates": sum(1 for v in vals if v == 0),
        "derrotas": sum(1 for v in vals if v < 0),
        "taxa_acerto": _r(sum(1 for v in vals if v > 0) / n),
        "fator_lucro": _r(pf),
        "drawdown": _r(drawdown),
        "seq_perdas": seq,
    }


def resumo(posicoes: Sequence[Posicao],
           custo_rs_por_contrato: float = CUSTO_RS_POR_CONTRATO,
           slippage_pt_por_lado: float = SLIPPAGE_PT_POR_LADO,
           valor_ponto_rs: float = VALOR_PONTO_RS) -> dict:
    """Tres visoes (bruto/liquido/gate) em pontos por contrato + totais em R$."""
    custo_pt = custo_rs_por_contrato / valor_ponto_rs
    gate_pt = 2.0 * slippage_pt_por_lado + custo_pt

    bruto = [p.resultado_pt for p in posicoes]
    liquido = [v - custo_pt for v in bruto]
    gate = [v - gate_pt for v in bruto]

    total_bruto = sum(p.resultado_rs for p in posicoes)
    total_liquido = sum(p.resultado_rs - custo_rs_por_contrato * p.volume
                        for p in posicoes)
    total_gate = sum(p.resultado_rs
                     - (custo_rs_por_contrato
                        + 2.0 * slippage_pt_por_lado * valor_ponto_rs) * p.volume
                     for p in posicoes)

    return {
        "n": len(posicoes),
        "bruto": estatisticas(bruto),
        "liquido": estatisticas(liquido),
        "gate": estatisticas(gate),
        "total_bruto_rs": _r(total_bruto, 2),
        "total_liquido_rs": _r(total_liquido, 2),
        "total_gate_rs": _r(total_gate, 2),
        "custo_pt": _r(custo_pt),
        "gate_pt": _r(gate_pt),
        "valor_ponto_rs": valor_ponto_rs,
    }


def por_dia(posicoes: Sequence[Posicao],
            custo_rs_por_contrato: float = CUSTO_RS_POR_CONTRATO,
            slippage_pt_por_lado: float = SLIPPAGE_PT_POR_LADO,
            valor_ponto_rs: float = VALOR_PONTO_RS) -> List[dict]:
    """Agrega por dia do servidor, em ordem cronologica."""
    dias: Dict[str, dict] = {}
    for p in posicoes:
        d = dias.setdefault(p.dia, {"dia": p.dia, "n": 0, "bruto_rs": 0.0, "gate_rs": 0.0})
        d["n"] += 1
        d["bruto_rs"] += p.resultado_rs
        d["gate_rs"] += (p.resultado_rs
                         - (custo_rs_por_contrato
                            + 2.0 * slippage_pt_por_lado * valor_ponto_rs) * p.volume)
    saida = []
    for dia in sorted(dias):
        d = dias[dia]
        d["bruto_rs"] = _r(d["bruto_rs"], 2)
        d["gate_rs"] = _r(d["gate_rs"], 2)
        saida.append(d)
    return saida


def veredito(est_gate: dict) -> str:
    """Le o IC95 do gate: e o unico criterio honesto de 'tem edge?'."""
    if est_gate.get("n", 0) < 2:
        return "amostra insuficiente (n < 2)"
    lo, hi = est_gate["ic95"]
    if lo > 0:
        return "LUCRATIVO com 95% de confianca (IC inteiro acima de zero)"
    if hi < 0:
        return "PERDEDOR com 95% de confianca (IC inteiro abaixo de zero)"
    return "INDISTINGUIVEL de zero (IC contem zero)"


def _fmt(x, casas: int = 2, sinal: bool = False) -> str:
    if x is None:
        return "-"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    if sinal:
        return f"{x:+.{casas}f}"
    return f"{x:.{casas}f}"


def _br(x, casas: int = 2) -> str:
    """Numero com virgula decimal (texto em portugues)."""
    return f"{x:.{casas}f}".replace(".", ",")


def formatar_relatorio(res: dict,
                       dias: Sequence[dict],
                       periodo: str,
                       magics: Optional[Iterable[int]] = None,
                       gerado_em: Optional[str] = None) -> str:
    """Texto ASCII do relatorio (mesmo estilo do ROADMAP)."""
    gerado_em = gerado_em or datetime.now().strftime("%Y-%m-%d %H:%M")
    magics_txt = "todos" if magics is None else str(sorted(int(m) for m in magics))
    linhas = [
        "RELATORIO DE METRICAS - MONSTRO WDO",
        f"gerado em {gerado_em} | periodo {periodo} | magics {magics_txt}",
        "",
        "POR DIA (dia do servidor MT5)",
        "dia         n   bruto R$    gate R$",
    ]
    for d in dias:
        linhas.append(f"{d['dia']}  {d['n']:2d}  {_fmt(d['bruto_rs'], 2, True):>10}"
                      f"  {_fmt(d['gate_rs'], 2, True):>9}")

    linhas += [
        "",
        f"VISOES (n={res['n']}; custo {_br(res['custo_pt'])} pt/trade; "
        f"gate {_br(res['gate_pt'])} pt/trade)",
        "visao     n   media pt    IC95 (pt)          total R$     PF   acerto  seq  DD pt",
    ]
    for nome, chave, total in (
            ("bruto", "bruto", "total_bruto_rs"),
            ("liquido", "liquido", "total_liquido_rs"),
            ("gate", "gate", "total_gate_rs")):
        e = res[chave]
        ic = e["ic95"]
        ic_txt = f"[{_fmt(ic[0], 2, True)}, {_fmt(ic[1], 2, True)}]"
        taxa = "-" if e["taxa_acerto"] is None else f"{e['taxa_acerto'] * 100:.1f}%"
        linhas.append(
            f"{nome:<8} {e['n']:3d}  {_fmt(e['media'], 2, True):>8}  {ic_txt:<19}"
            f" {_fmt(res[total], 2, True):>10}  {_fmt(e['fator_lucro'], 2):>4}"
            f"  {taxa:>6}  {e['seq_perdas']:3d}  {_fmt(e['drawdown'], 2):>6}")

    linhas += [
        "",
        "LEITURA",
        "- IC95 = media +- t(gl=n-1) * erro padrao. n pequeno => IC largo, de proposito.",
        f"- O gate cobra {_br(res['gate_pt'])} pt/trade (2,0 de slippage + "
        f"{_br(res['custo_pt'])} de custo). A media bruta precisa superar isso.",
        "- p-valor binomial contra 50% nao e reportado: em chop o break-even real",
        "  fica em 50-54%, entao ele parece melhor do que e.",
        f"- Veredito (gate): {veredito(res['gate'])}.",
        "",
    ]
    return "\n".join(linhas)
