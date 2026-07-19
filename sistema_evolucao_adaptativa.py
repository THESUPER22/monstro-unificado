#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧬 SISTEMA DE EVOLUÇÃO ADAPTATIVA DO MONSTRO
Implementa ciclo contínuo: Operação → Experiência → Aprendizado → Adaptação → Operação Melhorada
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


class SistemaEvolucaoAdaptativa:
    """Sistema que evolui os filtros automaticamente baseado na performance."""

    def __init__(self):
        self.config_file = "config_evolutivo.json"
        self.historico_evolucao = "historico_evolucao_filtros.csv"
        self.metricas_performance = {}
        self.ciclos_evolucao = 0
        self.filtros_atuais = self.carregar_filtros_iniciais()
        self.historico_filtros = []

        # Parâmetros de evolução
        self.MIN_OPERACOES_CICLO = 50  # Mínimo de operações para avaliar
        self.TARGET_TAXA_ACERTO = 0.75  # Meta: 75% de acerto
        self.TARGET_PROFIT_FACTOR = 2.0  # Meta: Profit Factor 2.0
        self.MAX_DRAWDOWN_PERMITIDO = 0.05  # Máximo 5% de drawdown

        logging.info("🧬 Sistema de Evolução Adaptativa inicializado")

    def carregar_filtros_iniciais(self) -> Dict:
        """Carrega filtros iniciais ou cria configuração padrão."""
        filtros_default = {
            # Filtros de Entrada
            "min_entropia_book": 0.3,
            "max_entropia_book": 0.8,
            "min_volume_book": 200,
            "max_spread": 5,
            "min_atr": 10,
            "max_atr": 100,
            "rsi_sobrecompra": 70,
            "rsi_sobrevenda": 30,

            # Filtros de Confiança
            "threshold_confianca": 0.6,
            "min_score_distancia": 0.4,

            # Filtros de Tempo
            "min_tempo_entre_trades": 30,  # segundos
            "max_trades_por_hora": 20,

            # Filtros de Volatilidade
            "volatilidade_min": 0.5,
            "volatilidade_max": 5.0,

            # Meta de Performance
            "taxa_acerto_alvo": 0.65,
            "profit_factor_alvo": 1.8,
            "max_drawdown_alvo": 0.03
        }

        try:
            with open(self.config_file, 'r') as f:
                filtros = json.load(f)
                logging.info("✅ Filtros carregados do arquivo")
                return filtros
        except FileNotFoundError:
            logging.info("📝 Criando filtros iniciais padrão")
            self.salvar_filtros(filtros_default)
            return filtros_default

    def salvar_filtros(self, filtros: Dict):
        """Salva filtros atuais no arquivo."""
        with open(self.config_file, 'w') as f:
            json.dump(filtros, f, indent=2)
        logging.info("💾 Filtros salvos")

    def analisar_performance_recente(self) -> Dict:
        """Analisa performance das últimas operações."""
        try:
            # Carrega histórico de contexto
            df = pd.read_csv("historico_contexto.csv")

            # Pega últimas N operações
            ultimas_ops = df.tail(self.MIN_OPERACOES_CICLO)

            if len(ultimas_ops) < self.MIN_OPERACOES_CICLO:
                logging.warning(
                    f"⚠️ Poucas operações para análise: {len(ultimas_ops)}")
                return {}

            # Calcula métricas
            operacoes_reais = ultimas_ops[ultimas_ops['action'].isin([
                                                                     'BUY', 'SELL'])]

            if len(operacoes_reais) == 0:
                return {}

            rewards = operacoes_reais['reward'].values
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
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = (cumulative_pnl - running_max) / running_max
            max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0

            metricas = {
                'total_operacoes': len(rewards),
                'trades_positivos': trades_positivos,
                'trades_negativos': trades_negativos,
                'taxa_acerto': taxa_acerto,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'lucro_medio': rewards.mean(),
                'timestamp': datetime.now().isoformat()
            }

            logging.info(
                f"📊 Performance analisada: Taxa={taxa_acerto:.2%}, PF={profit_factor:.2f}")
            return metricas

        except Exception as e:
            logging.error(f"❌ Erro ao analisar performance: {e}")
            return {}

    def calcular_ajustes_filtros(self, metricas: Dict) -> Dict:
        """Calcula ajustes necessários nos filtros baseado na performance."""
        if not metricas:
            return {}

        ajustes = {}
        taxa_acerto = metricas.get('taxa_acerto', 0)
        profit_factor = metricas.get('profit_factor', 0)
        max_drawdown = metricas.get('max_drawdown', 0)

        # LÓGICA DE EVOLUÇÃO ADAPTATIVA

        # Se taxa de acerto está baixa, aumenta seletividade
        if taxa_acerto < self.TARGET_TAXA_ACERTO:
            logging.info("🔍 Taxa de acerto baixa - Aumentando seletividade")

            # Aumenta threshold de confiança
            ajustes['threshold_confianca'] = min(
                0.9, self.filtros_atuais['threshold_confianca'] + 0.05)

            # Reduz número máximo de trades por hora
            ajustes['max_trades_por_hora'] = max(
                5, self.filtros_atuais['max_trades_por_hora'] - 2)

            # Aumenta tempo mínimo entre trades
            ajustes['min_tempo_entre_trades'] = min(
                300, self.filtros_atuais['min_tempo_entre_trades'] + 15)

            # Torna filtros de entrada mais restritivos
            ajustes['min_entropia_book'] = min(
                0.6, self.filtros_atuais['min_entropia_book'] + 0.05)
            ajustes['max_spread'] = max(
                2, self.filtros_atuais['max_spread'] - 0.5)
            ajustes['min_volume_book'] = min(
                500, self.filtros_atuais['min_volume_book'] + 50)

        # Se taxa de acerto está boa mas profit factor baixo
        elif taxa_acerto >= self.TARGET_TAXA_ACERTO and profit_factor < self.TARGET_PROFIT_FACTOR:
            logging.info(
                "💰 Profit factor baixo - Otimizando qualidade dos trades")

            # Aumenta score mínimo de distância
            ajustes['min_score_distancia'] = min(
                0.7, self.filtros_atuais['min_score_distancia'] + 0.1)

            # Ajusta filtros de volatilidade para pegar movimentos maiores
            ajustes['min_atr'] = min(30, self.filtros_atuais['min_atr'] + 5)

        # Se drawdown está alto, aumenta proteção
        if max_drawdown > self.MAX_DRAWDOWN_PERMITIDO:
            logging.info("🛡️ Drawdown alto - Aumentando proteção")

            # Reduz drasticamente número de trades
            ajustes['max_trades_por_hora'] = max(
                3, self.filtros_atuais['max_trades_por_hora'] - 5)

            # Aumenta muito o threshold de confiança
            ajustes['threshold_confianca'] = min(
                0.95, self.filtros_atuais['threshold_confianca'] + 0.1)

            # Reduz spread máximo
            ajustes['max_spread'] = max(
                1, self.filtros_atuais['max_spread'] - 1)

        # Se performance está excelente, pode relaxar um pouco para mais volume
        elif (taxa_acerto > self.TARGET_TAXA_ACERTO + 0.05 and
              profit_factor > self.TARGET_PROFIT_FACTOR + 0.2 and
              max_drawdown < self.MAX_DRAWDOWN_PERMITIDO / 2):

            logging.info(
                "🚀 Performance excelente - Aumentando volume com cuidado")

            # Relaxa ligeiramente os filtros
            ajustes['threshold_confianca'] = max(
                0.5, self.filtros_atuais['threshold_confianca'] - 0.02)
            ajustes['max_trades_por_hora'] = min(
                30, self.filtros_atuais['max_trades_por_hora'] + 1)
            ajustes['min_tempo_entre_trades'] = max(
                15, self.filtros_atuais['min_tempo_entre_trades'] - 5)

        return ajustes

    def aplicar_ajustes(self, ajustes: Dict):
        """Aplica ajustes calculados aos filtros atuais."""
        if not ajustes:
            logging.info(
                "📊 Nenhum ajuste necessário - Performance dentro do esperado")
            return

        # Salva estado anterior
        filtros_anteriores = self.filtros_atuais.copy()

        # Aplica ajustes
        for chave, valor in ajustes.items():
            if chave in self.filtros_atuais:
                valor_anterior = self.filtros_atuais[chave]
                self.filtros_atuais[chave] = valor
                logging.info(f"🔧 {chave}: {valor_anterior} → {valor}")

        # Salva histórico da evolução
        self.historico_filtros.append({
            'timestamp': datetime.now().isoformat(),
            'ciclo': self.ciclos_evolucao,
            'filtros_anteriores': filtros_anteriores,
            'filtros_novos': self.filtros_atuais.copy(),
            'ajustes_aplicados': ajustes
        })

        # Salva filtros atualizados
        self.salvar_filtros(self.filtros_atuais)

        logging.info(f"✅ Ciclo de evolução {self.ciclos_evolucao} concluído")

    def salvar_historico_evolucao(self, metricas: Dict):
        """Salva histórico da evolução para análise."""
        try:
            dados = {
                'timestamp': datetime.now().isoformat(),
                'ciclo': self.ciclos_evolucao,
                'taxa_acerto': metricas.get('taxa_acerto', 0),
                'profit_factor': metricas.get('profit_factor', 0),
                'max_drawdown': metricas.get('max_drawdown', 0),
                'total_operacoes': metricas.get('total_operacoes', 0),
                'threshold_confianca': self.filtros_atuais['threshold_confianca'],
                'max_trades_por_hora': self.filtros_atuais['max_trades_por_hora'],
                'min_entropia_book': self.filtros_atuais['min_entropia_book']
            }

            # Cria DataFrame
            df_novo = pd.DataFrame([dados])

            # Adiciona ao histórico existente
            if pd.io.common.file_exists(self.historico_evolucao):
                df_existente = pd.read_csv(self.historico_evolucao)
                df_final = pd.concat(
                    [df_existente, df_novo], ignore_index=True)
            else:
                df_final = df_novo

            # Salva
            df_final.to_csv(self.historico_evolucao, index=False)
            logging.info("📈 Histórico de evolução salvo")

        except Exception as e:
            logging.error(f"❌ Erro ao salvar histórico: {e}")

    def executar_ciclo_evolucao(self) -> bool:
        """Executa um ciclo completo de evolução."""
        logging.info(
            f"🧬 Iniciando ciclo de evolução #{self.ciclos_evolucao + 1}")

        # 1. Analisa performance recente
        metricas = self.analisar_performance_recente()

        if not metricas:
            logging.warning("⚠️ Não há dados suficientes para evolução")
            return False

        # 2. Calcula ajustes necessários
        ajustes = self.calcular_ajustes_filtros(metricas)

        # 3. Aplica ajustes
        self.aplicar_ajustes(ajustes)

        # 4. Salva histórico
        self.salvar_historico_evolucao(metricas)

        # 5. Incrementa contador
        self.ciclos_evolucao += 1

        logging.info("🎯 Ciclo de evolução concluído com sucesso")
        return True

    def obter_filtros_atuais(self) -> Dict:
        """Retorna filtros atuais para uso no sistema de trading."""
        return self.filtros_atuais.copy()

    def deve_executar_trade(self, contexto: Dict) -> Tuple[bool, str]:
        """Verifica se deve executar trade baseado nos filtros evolutivos."""
        filtros = self.filtros_atuais

        # Verifica cada filtro
        if contexto.get('entropia_book', 0) < filtros['min_entropia_book']:
            return False, "Entropia muito baixa"

        if contexto.get('entropia_book', 0) > filtros['max_entropia_book']:
            return False, "Entropia muito alta"

        if contexto.get('spread', 999) > filtros['max_spread']:
            return False, "Spread muito alto"

        if contexto.get('volume_book', 0) < filtros['min_volume_book']:
            return False, "Volume insuficiente"

        if contexto.get('confianca', 0) < filtros['threshold_confianca']:
            return False, "Confiança insuficiente"

        if contexto.get('volatility', 0) < filtros['volatilidade_min']:
            return False, "Volatilidade muito baixa"

        if contexto.get('volatility', 999) > filtros['volatilidade_max']:
            return False, "Volatilidade muito alta"

        # Se passou em todos os filtros
        return True, "Aprovado pelos filtros evolutivos"

    def gerar_relatorio_evolucao(self) -> str:
        """Gera relatório da evolução do sistema."""
        relatorio = f"""
🧬 RELATÓRIO DE EVOLUÇÃO ADAPTATIVA
{'='*50}

📊 Status Atual:
   Ciclos de evolução: {self.ciclos_evolucao}
   Threshold confiança: {self.filtros_atuais['threshold_confianca']:.2f}
   Max trades/hora: {self.filtros_atuais['max_trades_por_hora']}
   Min entropia: {self.filtros_atuais['min_entropia_book']:.2f}
   Max spread: {self.filtros_atuais['max_spread']}

🎯 Metas de Performance:
   Taxa de acerto alvo: {self.TARGET_TAXA_ACERTO:.1%}
   Profit factor alvo: {self.TARGET_PROFIT_FACTOR:.1f}
   Max drawdown permitido: {self.MAX_DRAWDOWN_PERMITIDO:.1%}

📈 Evolução:
   Total de ajustes: {len(self.historico_filtros)}
   Última evolução: {self.historico_filtros[-1]['timestamp'] if self.historico_filtros else 'Nunca'}
"""
        return relatorio

# Função para integração com o sistema principal


def integrar_sistema_evolutivo():
    """Integra o sistema evolutivo com o Monstro principal."""
    sistema = SistemaEvolucaoAdaptativa()

    # Executa ciclo de evolução se necessário
    sistema.executar_ciclo_evolucao()

    return sistema


if __name__ == "__main__":
    # Teste do sistema
    sistema = SistemaEvolucaoAdaptativa()
    print(sistema.gerar_relatorio_evolucao())

    # Executa ciclo de evolução
    sucesso = sistema.executar_ciclo_evolucao()
    print(f"Evolução executada: {sucesso}")
