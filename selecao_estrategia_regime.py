#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selecao_estrategia_regime.py  (Sessao 19 - DESIGN / ESBOCO)

Selecao de estrategia por regime de mercado (regime detection + meta-labeling).

PRINCIPIO DE ARQUITETURA:
  Python (regras) decide ONDE e SE. Keras decide COM QUE FORCA.
  Este modulo e o "controlador de trafego": mapeia o modo operacional ja
  detectado (ModoOperacional/DetectorModoMercado do v22) para um PERFIL de
  estrategias ativas, pesos de filtro e parametros de risco.

NAO esta plugado no monstro_unificado_v22.py ainda (mercado em operacao).
Plano de integracao: ver ROADMAP_WDO.md -> Sessao 19.

Tabelas de config = unica fonte de verdade. Nenhuma logica de mercado aqui,
apenas o mapeamento regime -> perfil + rastreador de performance por regime.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Estrategias conhecidas do v22 (nome canonico -> componente real no codigo)
# ---------------------------------------------------------------------------
ESTRATEGIAS_CONHECIDAS = {
    "williams_r":        "MonitorWilliamsR (Larry Williams %R + divergencias)",
    "rsi_mean_reversion": "RSI extremo + retorno a media (filtro mean reversion)",
    "sniper_supermo":     "SniperSupermo (momentum de big players)",
    "dol_veto":           "Referencia institucional DOL (veto/confirma)",
    "filtro_tendencia":   "Filtro de tendencia SMA-20 vs preco",
    "filtro_entropia":    "Filtro de entropia (escala real 2.6x-2.9x)",
}

# Modos operacionais do v22 (ModoOperacional + DetectorModoMercado)
MODOS_VALIDOS = ["NORMAL", "LATERAL", "EXPLOSAO", "CONSERVADOR", "DEFESA", "AGUARDANDO"]


def _perfil(
    estrategias: List[str],
    volume_mult: float = 1.0,
    sl_mult: float = 1.0,
    tp_mult: float = 1.0,
    peso_keras: float = 1.0,
    score_minimo: float = 0.0,
    filtros: Optional[Dict[str, float]] = None,
    descricao: str = "",
) -> dict:
    """Monta um perfil de regime de forma tipada (evita typos na tabela)."""
    for e in estrategias:
        if e not in ESTRATEGIAS_CONHECIDAS:
            raise ValueError(f"Estrategia desconhecida no perfil: {e}")
    return {
        "estrategias_ativas": list(estrategias),
        "volume_mult": volume_mult,
        "sl_mult": sl_mult,
        "tp_mult": tp_mult,
        "peso_keras": peso_keras,
        "score_minimo": score_minimo,
        "filtros": filtros or {},
        "descricao": descricao,
    }


# ---------------------------------------------------------------------------
# TABELA DE CONFIG: regime -> perfil. UNICA FONTE DE VERDADE para calibracao.
# Calibracao futura = ajustar esta tabela com base nas estatisticas do
# RastreadorPerformanceRegime (nao mecher na logica do robô).
# ---------------------------------------------------------------------------
PERFIL_POR_REGIME: Dict[str, dict] = {
    "NORMAL": _perfil(
        estrategias=["williams_r", "rsi_mean_reversion", "sniper_supermo",
                     "dol_veto", "filtro_tendencia", "filtro_entropia"],
        descricao="Mercado equilibrado: todas as estrategias ativas com pesos padrao",
    ),
    "LATERAL": _perfil(
        estrategias=["williams_r", "rsi_mean_reversion", "dol_veto", "filtro_entropia"],
        volume_mult=0.5,
        sl_mult=0.7,
        tp_mult=0.7,
        peso_keras=1.2,
        score_minimo=3.0,
        filtros={"filtro_tendencia": 0.0},
        descricao="Baixa volatilidade/entropia: foco em mean reversion, alvos curtos. "
                  "Tendencia desligada (nao existe), Sniper desligado (sem explosao)",
    ),
    "EXPLOSAO": _perfil(
        estrategias=["sniper_supermo", "filtro_tendencia", "filtro_entropia", "dol_veto"],
        volume_mult=1.5,
        sl_mult=1.2,
        tp_mult=1.5,
        peso_keras=0.8,
        score_minimo=4.0,
        filtros={"williams_r": 0.0, "rsi_mean_reversion": 0.0},
        descricao="Alta entropia + volume crescendo (>=1000cc): segue o rompimento. "
                  "Mean reversion desligado (luta contra momentum), Williams %R desligado",
    ),
    "CONSERVADOR": _perfil(
        estrategias=["williams_r", "rsi_mean_reversion", "sniper_supermo", "dol_veto"],
        volume_mult=0.5,
        sl_mult=0.7,
        tp_mult=0.8,
        peso_keras=1.5,
        score_minimo=5.0,
        descricao="ATR baixo + entropia baixa: so operacoes de altissima conviccao",
    ),
    "DEFESA": _perfil(
        estrategias=[],
        volume_mult=0.0,
        descricao="N losses seguidos: NAO OPERA (so observacao)",
    ),
    "AGUARDANDO": _perfil(
        estrategias=[],
        volume_mult=0.0,
        descricao="Book desequilibrado (bid/ask): NAO OPERA",
    ),
}


@dataclass
class RegistoTrade:
    """Um trade registrado por regime para medicao de performance."""
    modo: str
    estrategia: str
    lucro: float
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class SelecionadorRegime:
    """Mapeia o modo operacional do v22 para um perfil de estrategias + risco."""

    def __init__(self, config: Optional[Dict[str, dict]] = None):
        self.config = config or PERFIL_POR_REGIME
        validar_config(self.config)

    def selecionar_perfil(self, modo: str) -> dict:
        """Retorna o perfil completo para o modo. Modo desconhecido -> NORMAL."""
        modo = modo.upper()
        return self.config.get(modo, self.config["NORMAL"])

    def estrategias_ativas(self, modo: str) -> List[str]:
        """Lista de estrategias liberadas no regime (ordem = prioridade)."""
        return list(self.selecionar_perfil(modo)["estrategias_ativas"])

    def estrategia_liberada(self, estrategia: str, modo: str) -> bool:
        """Uma estrategia especifica esta ativa neste regime?"""
        return estrategia in self.estrategias_ativas(modo)

    def permitido_operar(self, modo: str) -> bool:
        """Regimes de bloqueio total (DEFESA/AGUARDANDO) -> False."""
        perfil = self.selecionar_perfil(modo)
        return perfil["volume_mult"] > 0 and bool(perfil["estrategias_ativas"])

    def parametros(self, modo: str, volume_base: float, sl_base: float,
                   tp_base: float) -> Dict[str, float]:
        """Aplica os multiplicadores do regime sobre os parametros base."""
        p = self.selecionar_perfil(modo)
        return {
            "volume": volume_base * p["volume_mult"],
            "sl": sl_base * p["sl_mult"],
            "tp": tp_base * p["tp_mult"],
            "peso_keras": p["peso_keras"],
            "score_minimo": p["score_minimo"],
        }

    def filtro_bloqueia(self, estrategia: str, modo: str, valor: float,
                        limiar_padrao: float) -> bool:
        """
        Decide se um filtro/estrategia BLOQUEIA a operacao neste regime.
        Retorna True = bloqueia, False = passa.
        peso 0.0 = filtro desligado no regime (nunca bloqueia -> False).
        peso 1.0 = usa o limiar padrao do v22.
        peso >1  = torna o filtro mais exigente (bloqueia mais facil).
        """
        peso = self.selecionar_perfil(modo)["filtros"].get(estrategia, 1.0)
        if peso <= 0.0:
            return False  # estrategia desligada no regime -> nao bloqueia
        return valor >= (limiar_padrao * peso)


class RastreadorPerformanceRegime:
    """Mede lucro/assertividade POR REGIME e POR ESTRATEGIA.
    E o loop de calibracao: depois de N dias, leia .relatorio() e ajuste
    PERFIL_POR_REGIME de acordo (e o 'balanceamento perfeito' de forma medida).
    """

    def __init__(self, caminho_json: Optional[str] = None):
        self.trades: List[RegistoTrade] = []
        self.caminho_json = caminho_json
        if caminho_json and Path(caminho_json).exists():
            self._carregar()

    def registrar_trade(self, modo: str, estrategia: str, lucro: float) -> None:
        self.trades.append(RegistoTrade(modo=modo.upper(), estrategia=estrategia, lucro=float(lucro)))
        if self.caminho_json:
            self._salvar()

    def _agregar(self, chave, filtro=None):
        linhas = self.trades if filtro is None else [t for t in self.trades if filtro(t)]
        grupos: Dict[str, List[float]] = {}
        for t in linhas:
            k = getattr(t, chave)
            grupos.setdefault(k, []).append(t.lucro)
        out = {}
        for k, lucros in grupos.items():
            n = len(lucros)
            wins = [x for x in lucros if x > 0]
            out[k] = {
                "n": n,
                "wins": len(wins),
                "win_rate": round(len(wins) / n, 4) if n else 0.0,
                "avg_profit": round(sum(lucros) / n, 2) if n else 0.0,
                "total": round(sum(lucros), 2),
            }
        return out

    def estatisticas_por_modo(self) -> Dict[str, dict]:
        return self._agregar("modo")

    def estatisticas_por_estrategia(self) -> Dict[str, dict]:
        return self._agregar("estrategia")

    def melhor_estrategia_por_regime(self) -> Dict[str, str]:
        """Para cada regime, a estrategia com maior total de lucro."""
        resultado: Dict[str, str] = {}
        por_modo_estrategia: Dict[str, Dict[str, list]] = {}
        for t in self.trades:
            por_modo_estrategia.setdefault(t.modo, {}).setdefault(t.estrategia, []).append(t.lucro)
        for modo, estr in por_modo_estrategia.items():
            melhor = max(estr.items(), key=lambda kv: sum(kv[1]))
            resultado[modo] = melhor[0]
        return resultado

    def relatorio(self) -> str:
        linhas = [
            "=== RELATORIO DE PERFORMANCE POR REGIME (calibracao) ===",
            f"Trades totais: {len(self.trades)}",
            "",
            "POR MODO:",
        ]
        for modo, s in sorted(self.estatisticas_por_modo().items()):
            linhas.append(
                f"  {modo:<12} n={s['n']:<4} win_rate={s['win_rate']:.0%} "
                f"avg={s['avg_profit']:>8.2f} total={s['total']:>10.2f}"
            )
        linhas.append("")
        linhas.append("POR ESTRATEGIA:")
        for est, s in sorted(self.estatisticas_por_estrategia().items()):
            linhas.append(
                f"  {est:<18} n={s['n']:<4} win_rate={s['win_rate']:.0%} "
                f"avg={s['avg_profit']:>8.2f} total={s['total']:>10.2f}"
            )
        return "\n".join(linhas)

    def _salvar(self) -> None:
        dados = [asdict(t) for t in self.trades]
        Path(self.caminho_json).write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    def _carregar(self) -> None:
        caminho = Path(self.caminho_json)
        if not caminho.exists() or caminho.stat().st_size == 0:
            return
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        for d in dados:
            self.trades.append(RegistoTrade(**d))


def validar_config(config: Dict[str, dict]) -> None:
    """Garante que a tabela de config nao tem typos nem modos sem perfil."""
    for modo in MODOS_VALIDOS:
        if modo not in config:
            raise ValueError(f"Modo sem perfil na config: {modo}")
    for modo, perfil in config.items():
        if modo not in MODOS_VALIDOS:
            raise ValueError(f"Modo desconhecido na config: {modo}")
        for f in perfil["filtros"]:
            if f not in ESTRATEGIAS_CONHECIDAS:
                raise ValueError(f"Estrategia desconhecida nos filtros de {modo}: {f}")
        if perfil["volume_mult"] < 0 or perfil["sl_mult"] <= 0 or perfil["tp_mult"] <= 0:
            raise ValueError(f"Multiplicadores invalidos no modo {modo}")


if __name__ == "__main__":
    sel = SelecionadorRegime()
    print("Estrategias por regime:")
    for m in MODOS_VALIDOS:
        ativas = sel.estrategias_ativas(m)
        print(f"  {m:<12} opera={str(sel.permitido_operar(m)):<5} -> {ativas}")

    rast = RastreadorPerformanceRegime()
    rast.registrar_trade("LATERAL", "rsi_mean_reversion", 12.0)
    rast.registrar_trade("LATERAL", "rsi_mean_reversion", -8.0)
    rast.registrar_trade("EXPLOSAO", "sniper_supermo", 25.0)
    rast.registrar_trade("NORMAL", "williams_r", 4.0)
    print()
    print(rast.relatorio())
    print(f"\nMelhor estrategia por regime: {rast.melhor_estrategia_por_regime()}")
