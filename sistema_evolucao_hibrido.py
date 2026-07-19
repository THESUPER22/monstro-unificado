#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧬🎯 SISTEMA DE EVOLUÇÃO HÍBRIDO DO MONSTRO
Combina evolução por níveis + evolução adaptativa por performance
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


class SistemaEvolucaoHibrido:
    """Sistema híbrido que combina evolução por níveis e por performance."""

    def __init__(self):
        self.config_file = "config_evolucao_hibrida.json"
        self.historico_evolucao = "historico_evolucao_hibrida.csv"

        # Carrega configurações
        self.config = self.carregar_configuracao()
        self.nivel_atual = self.determinar_nivel_atual()
        self.filtros_base = self.obter_filtros_nivel(self.nivel_atual)
        self.ajustes_adaptativos = {}

        # Métricas de controle
        self.ultima_avaliacao = None
        self.ciclos_adaptacao = 0

        logging.info(
            f"🧬 Sistema Híbrido inicializado - Nível: {self.nivel_atual}")

    def carregar_configuracao(self) -> Dict:
        """Carrega configuração híbrida."""
        config_default = {
            "niveis_experiencia": {
                "iniciante": {
                    "min_exp": 0,
                    "max_exp": 500,
                    "descricao": "Aprendendo padrões básicos"
                },
                "intermediario": {
                    "min_exp": 501,
                    "max_exp": 2000,
                    "descricao": "Desenvolvendo seletividade"
                },
                "avancado": {
                    "min_exp": 2001,
                    "max_exp": 5000,
                    "descricao": "Refinando estratégias"
                },
                "expert": {
                    "min_exp": 5001,
                    "max_exp": 15000,
                    "descricao": "Otimizando performance"
                },
                "mestre": {
                    "min_exp": 15001,
                    "max_exp": 999999,
                    "descricao": "Máxima seletividade"
                }
            },
            "filtros_base_por_nivel": {
                "iniciante": {
                    "threshold_confianca": 0.55,
                    "min_entropia": 0.2,
                    "max_spread": 3.0,
                    "min_volume_book": 150,
                    "max_trades_hora": 30,
                    "cooldown_segundos": 15
                },
                "intermediario": {
                    "threshold_confianca": 0.60,
                    "min_entropia": 0.3,
                    "max_spread": 2.5,
                    "min_volume_book": 200,
                    "max_trades_hora": 25,
                    "cooldown_segundos": 30
                },
                "avancado": {
                    "threshold_confianca": 0.65,
                    "min_entropia": 0.4,
                    "max_spread": 2.0,
                    "min_volume_book": 250,
                    "max_trades_hora": 20,
                    "cooldown_segundos": 45
                },
                "expert": {
                    "threshold_confianca": 0.70,
                    "min_entropia": 0.5,
                    "max_spread": 1.5,
                    "min_volume_book": 300,
                    "max_trades_hora": 15,
                    "cooldown_segundos": 60
                },
                "mestre": {
                    "threshold_confianca": 0.75,
                    "min_entropia": 0.6,
                    "max_spread": 1.0,
                    "min_volume_book": 400,
                    "max_trades_hora": 10,
                    "cooldown_segundos": 90
                }
            },
            "parametros_adaptacao": {
                "min_operacoes_avaliacao": 30,
                "taxa_acerto_alvo": 0.70,
                "profit_factor_alvo": 2.0,
                "max_drawdown_permitido": 0.05,
                "intervalo_avaliacao_horas": 4
            }
        }

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            with open(self.config_file, 'w') as f:
                json.dump(config_default, f, indent=2)
            return config_default

    def determinar_nivel_atual(self) -> str:
        """Determina nível atual baseado no número de experiências."""
        try:
            if os.path.exists("historico_contexto.csv"):
                df = pd.read_csv("historico_contexto.csv")
                num_experiencias = len(df)
            else:
                num_experiencias = 0

            for nivel, config in self.config["niveis_experiencia"].items():
                if config["min_exp"] <= num_experiencias <= config["max_exp"]:
                    logging.info(
                        f"📊 Nível determinado: {nivel} ({num_experiencias} experiências)")
                    return nivel

            return "mestre"  # Fallback

        except Exception as e:
            logging.error(f"❌ Erro ao determinar nível: {e}")
            return "iniciante"

    def obter_filtros_nivel(self, nivel: str) -> Dict:
        """Obtém filtros base para o nível atual."""
        return self.config["filtros_base_por_nivel"].get(nivel,
                                                         self.config["filtros_base_por_nivel"]["iniciante"])

    def analisar_performance_recente(self) -> Dict:
        """Analisa performance para adaptação dinâmica."""
        try:
            df = pd.read_csv("historico_contexto.csv")

            # Pega operações das últimas 4 horas
            agora = datetime.now()
            limite_tempo = agora - timedelta(hours=4)

            # Como não temos timestamp no CSV, pega as últimas N operações
            min_ops = self.config["parametros_adaptacao"]["min_operacoes_avaliacao"]
            ultimas_ops = df.tail(min_ops)

            if len(ultimas_ops) < min_ops:
                return {}

            # Filtra apenas operações reais
            ops_reais = ultimas_ops[ultimas_ops['action'].isin(
                ['BUY', 'SELL'])]

            if len(ops_reais) == 0:
                return {}

            rewards = ops_reais['reward'].values
            trades_positivos = len(rewards[rewards > 0])
            trades_negativos = len(rewards[rewards < 0])

            taxa_acerto = trades_positivos / \
                len(rewards) if len(rewards) > 0 else 0

            lucro_total = rewards[rewards > 0].sum(
            ) if trades_positivos > 0 else 0
            perda_total = abs(rewards[rewards < 0].sum()
                              ) if trades_negativos > 0 else 1
            profit_factor = lucro_total / perda_total if perda_total > 0 else 0

            # Calcula drawdown
            cumulative_pnl = np.cumsum(rewards)
            if len(cumulative_pnl) > 0:
                running_max = np.maximum.accumulate(cumulative_pnl)
                drawdown = (cumulative_pnl - running_max) / \
                    np.maximum(running_max, 1)
                max_drawdown = abs(drawdown.min())
            else:
                max_drawdown = 0

            return {
                'total_operacoes': len(rewards),
                'taxa_acerto': taxa_acerto,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'lucro_medio': rewards.mean(),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logging.error(f"❌ Erro ao analisar performance: {e}")
            return {}

    def calcular_ajustes_adaptativos(self, metricas: Dict) -> Dict:
        """Calcula ajustes adaptativos baseados na performance."""
        if not metricas:
            return {}

        ajustes = {}
        params = self.config["parametros_adaptacao"]

        taxa_acerto = metricas.get('taxa_acerto', 0)
        profit_factor = metricas.get('profit_factor', 0)
        max_drawdown = metricas.get('max_drawdown', 0)

        # LÓGICA DE ADAPTAÇÃO INTELIGENTE

        # Performance abaixo do esperado - AUMENTA SELETIVIDADE
        if taxa_acerto < params["taxa_acerto_alvo"]:
            intensidade = (params["taxa_acerto_alvo"] - taxa_acerto) * 2

            ajustes['threshold_confianca'] = min(0.05, intensidade * 0.1)
            ajustes['min_entropia'] = min(0.1, intensidade * 0.05)
            ajustes['max_spread'] = -min(0.5, intensidade * 0.3)
            ajustes['max_trades_hora'] = -max(1, int(intensidade * 5))
            ajustes['cooldown_segundos'] = min(30, int(intensidade * 20))

            logging.info(
                f"📉 Taxa de acerto baixa ({taxa_acerto:.1%}) - Aumentando seletividade")

        # Profit factor baixo - OTIMIZA QUALIDADE
        elif profit_factor < params["profit_factor_alvo"]:
            intensidade = (params["profit_factor_alvo"] - profit_factor) / 2

            ajustes['threshold_confianca'] = min(0.03, intensidade * 0.05)
            ajustes['min_entropia'] = min(0.05, intensidade * 0.03)
            ajustes['cooldown_segundos'] = min(15, int(intensidade * 10))

            logging.info(
                f"💰 Profit factor baixo ({profit_factor:.2f}) - Otimizando qualidade")

        # Drawdown alto - PROTEÇÃO MÁXIMA
        if max_drawdown > params["max_drawdown_permitido"]:
            intensidade = max_drawdown / params["max_drawdown_permitido"]

            ajustes['threshold_confianca'] = min(0.1, intensidade * 0.05)
            ajustes['max_trades_hora'] = -max(2, int(intensidade * 3))
            ajustes['max_spread'] = -min(0.3, intensidade * 0.2)
            ajustes['cooldown_segundos'] = min(60, int(intensidade * 30))

            logging.warning(
                f"🚨 Drawdown alto ({max_drawdown:.1%}) - Ativando proteção máxima")

        # Performance excelente - RELAXA LIGEIRAMENTE
        elif (taxa_acerto > params["taxa_acerto_alvo"] + 0.05 and
              profit_factor > params["profit_factor_alvo"] + 0.3):

            ajustes['threshold_confianca'] = -0.01
            ajustes['max_trades_hora'] = 1
            ajustes['cooldown_segundos'] = -5

            logging.info(
                "🚀 Performance excelente - Relaxando filtros ligeiramente")

        return ajustes

    def aplicar_ajustes(self, ajustes: Dict):
        """Aplica ajustes adaptativos aos filtros base."""
        if not ajustes:
            self.ajustes_adaptativos = {}
            return

        # Aplica ajustes aos filtros base
        for chave, ajuste in ajustes.items():
            if chave in self.filtros_base:
                self.ajustes_adaptativos[chave] = ajuste
                logging.info(f"🔧 Ajuste adaptativo {chave}: {ajuste:+.3f}")

        self.ciclos_adaptacao += 1

    def obter_filtros_finais(self) -> Dict:
        """Retorna filtros finais (base + ajustes adaptativos)."""
        filtros_finais = self.filtros_base.copy()

        # Aplica ajustes adaptativos
        for chave, ajuste in self.ajustes_adaptativos.items():
            if chave in filtros_finais:
                valor_original = filtros_finais[chave]

                if chave in ['threshold_confianca', 'min_entropia']:
                    # Soma para thresholds
                    filtros_finais[chave] = max(
                        0, min(1, valor_original + ajuste))
                elif chave in ['max_spread']:
                    # Soma para spreads (pode ser negativo)
                    filtros_finais[chave] = max(0.5, valor_original + ajuste)
                elif chave in ['max_trades_hora']:
                    # Soma para trades por hora
                    filtros_finais[chave] = max(
                        1, int(valor_original + ajuste))
                elif chave in ['cooldown_segundos']:
                    # Soma para cooldown
                    filtros_finais[chave] = max(
                        5, int(valor_original + ajuste))
                else:
                    filtros_finais[chave] = max(0, valor_original + ajuste)

        return filtros_finais

    def deve_executar_trade(self, contexto: Dict) -> Tuple[bool, str]:
        """Verifica se deve executar trade com filtros híbridos."""
        filtros = self.obter_filtros_finais()

        # Aplica todos os filtros
        if contexto.get('confianca', 0) < filtros['threshold_confianca']:
            return False, f"Confiança insuficiente ({contexto.get('confianca', 0):.2f} < {filtros['threshold_confianca']:.2f})"

        if contexto.get('entropia_book', 0) < filtros['min_entropia']:
            return False, f"Entropia baixa ({contexto.get('entropia_book', 0):.2f})"

        if contexto.get('spread', 999) > filtros['max_spread']:
            return False, f"Spread alto ({contexto.get('spread', 999):.1f})"

        if contexto.get('volume_book', 0) < filtros['min_volume_book']:
            return False, f"Volume insuficiente ({contexto.get('volume_book', 0)})"

        return True, "Aprovado pelos filtros híbridos"

    def executar_ciclo_evolucao(self) -> bool:
        """Executa ciclo completo de evolução híbrida."""
        logging.info("🧬 Iniciando ciclo de evolução híbrida")

        # 1. Verifica se mudou de nível
        nivel_anterior = self.nivel_atual
        self.nivel_atual = self.determinar_nivel_atual()

        if nivel_anterior != self.nivel_atual:
            logging.info(
                f"🎉 EVOLUÇÃO DE NÍVEL: {nivel_anterior} → {self.nivel_atual}")
            self.filtros_base = self.obter_filtros_nivel(self.nivel_atual)
            self.ajustes_adaptativos = {}  # Reset ajustes adaptativos

        # 2. Analisa performance para adaptação
        metricas = self.analisar_performance_recente()

        if metricas:
            # 3. Calcula e aplica ajustes adaptativos
            ajustes = self.calcular_ajustes_adaptativos(metricas)
            self.aplicar_ajustes(ajustes)

            # 4. Salva histórico
            self.salvar_historico_evolucao(metricas)

        self.ultima_avaliacao = datetime.now()
        logging.info("✅ Ciclo de evolução híbrida concluído")
        return True

    def salvar_historico_evolucao(self, metricas: Dict):
        """Salva histórico da evolução híbrida."""
        try:
            filtros_finais = self.obter_filtros_finais()

            dados = {
                'timestamp': datetime.now().isoformat(),
                'nivel': self.nivel_atual,
                'ciclo_adaptacao': self.ciclos_adaptacao,
                'taxa_acerto': metricas.get('taxa_acerto', 0),
                'profit_factor': metricas.get('profit_factor', 0),
                'max_drawdown': metricas.get('max_drawdown', 0),
                'threshold_final': filtros_finais['threshold_confianca'],
                'max_trades_hora_final': filtros_finais['max_trades_hora'],
                'min_entropia_final': filtros_finais['min_entropia']
            }

            df_novo = pd.DataFrame([dados])

            if os.path.exists(self.historico_evolucao):
                df_existente = pd.read_csv(self.historico_evolucao)
                df_final = pd.concat(
                    [df_existente, df_novo], ignore_index=True)
            else:
                df_final = df_novo

            df_final.to_csv(self.historico_evolucao, index=False)
            logging.info("📊 Histórico de evolução híbrida salvo")

        except Exception as e:
            logging.error(f"❌ Erro ao salvar histórico: {e}")

    def gerar_relatorio_status(self) -> str:
        """Gera relatório do status atual do sistema híbrido."""
        filtros_finais = self.obter_filtros_finais()

        relatorio = f"""
🧬🎯 SISTEMA DE EVOLUÇÃO HÍBRIDO - STATUS
{'='*50}

📊 Nível Atual: {self.nivel_atual.upper()}
   Descrição: {self.config['niveis_experiencia'][self.nivel_atual]['descricao']}
   Ciclos de adaptação: {self.ciclos_adaptacao}

🎯 Filtros Ativos:
   Threshold confiança: {filtros_finais['threshold_confianca']:.3f}
   Min entropia: {filtros_finais['min_entropia']:.2f}
   Max spread: {filtros_finais['max_spread']:.1f}
   Max trades/hora: {filtros_finais['max_trades_hora']}
   Cooldown: {filtros_finais['cooldown_segundos']}s

🔧 Ajustes Adaptativos Ativos:
"""

        if self.ajustes_adaptativos:
            for chave, ajuste in self.ajustes_adaptativos.items():
                relatorio += f"   {chave}: {ajuste:+.3f}\n"
        else:
            relatorio += "   Nenhum ajuste ativo\n"

        relatorio += f"""
📈 Última Avaliação: {self.ultima_avaliacao.strftime('%d/%m/%Y %H:%M') if self.ultima_avaliacao else 'Nunca'}
"""

        return relatorio

# Função para integração com o Monstro principal


def obter_sistema_evolucao_hibrido():
    """Retorna instância do sistema híbrido para uso no Monstro."""
    return SistemaEvolucaoHibrido()


if __name__ == "__main__":
    # Teste do sistema híbrido
    sistema = SistemaEvolucaoHibrido()
    print(sistema.gerar_relatorio_status())

    # Executa ciclo de evolução
    sistema.executar_ciclo_evolucao()
    print("\n" + sistema.gerar_relatorio_status())
    print("\n" + sistema.gerar_relatorio_status())
