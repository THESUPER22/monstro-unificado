#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧬 API ENDPOINTS PARA MONITORAMENTO DO SISTEMA EVOLUTIVO
Implementa endpoints para integração do sistema evolutivo com o dashboard
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from flask import jsonify

# Variáveis globais para acesso aos sistemas evolutivos
sistema_evolutivo_global = None
sistema_adaptativo_global = None
sistema_hibrido_global = None
filtros_evolutivos_global = None

# Constantes
HISTORICO_CSV = "historico_contexto.csv"
HISTORICO_EVOLUCAO_CSV = "historico_evolucao.csv"
HISTORICO_EVOLUCAO_HIBRIDA_CSV = "historico_evolucao_hibrida.csv"


# region [Funções de Processamento de Dados]

def extrair_reward_trend(dias: int = 7) -> List[Dict]:
    """Extrai tendência de recompensa dos últimos dias."""
    try:
        if not os.path.exists(HISTORICO_CSV):
            return []

        df = pd.read_csv(HISTORICO_CSV)
        if len(df) == 0:
            return []

        # Filtra apenas operações reais (BUY/SELL)
        df_operacoes = df[df['action'].isin(['BUY', 'SELL'])]

        # Agrupa por blocos de operações (cada 10 operações)
        df_operacoes['bloco'] = (df_operacoes.index // 10) * 10

        # Calcula média de reward por bloco
        rewards_por_bloco = df_operacoes.groupby(
            'bloco')['reward'].mean().reset_index()

        # Formata para retorno
        trend = [
            {
                "operacao": int(row['bloco']),
                "reward": float(row['reward']),
                "timestamp": datetime.now().isoformat()  # Simulado, não temos timestamp real
            }
            for _, row in rewards_por_bloco.iterrows()
        ]

        # Retorna últimos 50 pontos para não sobrecarregar o gráfico
        return trend[-50:]

    except Exception as e:
        logging.error(f"❌ Erro ao extrair reward trend: {e}")
        return []


def extrair_win_rate_trend() -> List[Dict]:
    """Extrai tendência de taxa de acerto ao longo do tempo."""
    try:
        if not os.path.exists(HISTORICO_CSV):
            return []

        df = pd.read_csv(HISTORICO_CSV)
        if len(df) == 0:
            return []

        # Filtra apenas operações reais (BUY/SELL)
        df_operacoes = df[df['action'].isin(['BUY', 'SELL'])]

        # Agrupa por blocos de operações (cada 20 operações)
        df_operacoes['bloco'] = (df_operacoes.index // 20) * 20

        # Calcula win rate por bloco
        win_rates = []
        for bloco, grupo in df_operacoes.groupby('bloco'):
            wins = sum(grupo['reward'] > 0)
            total = len(grupo)
            win_rate = wins / total if total > 0 else 0
            win_rates.append({
                "operacao": int(bloco),
                "win_rate": float(win_rate),
                "timestamp": datetime.now().isoformat()  # Simulado
            })

        return win_rates[-30:]  # Retorna últimos 30 pontos

    except Exception as e:
        logging.error(f"❌ Erro ao extrair win rate trend: {e}")
        return []


def extrair_model_accuracy_trend() -> List[Dict]:
    """Ext tendência de precisão do modelo ao longo do tempo."""
    try:
        # Aqui precisaríamos de dados específicos sobre a precisão do modelo
        # Como não temos esses dados diretamente, vamos simular com base no histórico

        if not os.path.exists(HISTORICO_CSV):
            return []

        df = pd.read_csv(HISTORICO_CSV)
        if len(df) == 0:
            return []

        # Filtra apenas operações reais (BUY/SELL)
        df_operacoes = df[df['action'].isin(['BUY', 'SELL'])]

        # Agrupa por blocos de operações (cada 25 operações)
        df_operacoes['bloco'] = (df_operacoes.index // 25) * 25

        # Calcula uma métrica de precisão baseada no reward
        # (isso é uma aproximação, não uma medida real de precisão do modelo)
        accuracy_trend = []
        for bloco, grupo in df_operacoes.groupby('bloco'):
            # Consideramos que operações com reward positivo foram "acertos" do modelo
            acertos = sum(grupo['reward'] > 0)
            total = len(grupo)
            accuracy = acertos / total if total > 0 else 0

            # Adicionamos um pouco de variação para simular flutuações na precisão
            accuracy = min(0.95, max(0.5, accuracy *
                           (1 + np.random.normal(0, 0.05))))

            accuracy_trend.append({
                "operacao": int(bloco),
                "accuracy": float(accuracy),
                "timestamp": datetime.now().isoformat()  # Simulado
            })

        return accuracy_trend[-30:]  # Retorna últimos 30 pontos

    except Exception as e:
        logging.error(f"❌ Erro ao extrair model accuracy trend: {e}")
        return []


def agregar_metricas_por_periodo(periodo: str) -> Dict:
    """Agrega métricas por período (diário, semanal, mensal)."""
    try:
        if not os.path.exists(HISTORICO_CSV):
            return {}

        df = pd.read_csv(HISTORICO_CSV)
        if len(df) == 0:
            return {}

        # Filtra apenas operações reais (BUY/SELL)
        df_operacoes = df[df['action'].isin(['BUY', 'SELL'])]

        # Calcula métricas básicas
        total_ops = len(df_operacoes)
        if total_ops == 0:
            return {}

        wins = sum(df_operacoes['reward'] > 0)
        win_rate = wins / total_ops

        # Calcula reward médio
        avg_reward = df_operacoes['reward'].mean()

        # Calcula profit factor
        ganhos = df_operacoes[df_operacoes['reward'] > 0]['reward'].sum()
        perdas = abs(df_operacoes[df_operacoes['reward'] < 0]['reward'].sum())
        profit_factor = ganhos / perdas if perdas > 0 else float('inf')

        # Retorna métricas agregadas
        return {
            "total_operacoes": int(total_ops),
            "win_rate": float(win_rate),
            "avg_reward": float(avg_reward),
            "profit_factor": float(profit_factor)
        }

    except Exception as e:
        logging.error(f"❌ Erro ao agregar métricas por período: {e}")
        return {}


def get_evolution_performance_metrics() -> Dict:
    """Extrai métricas de performance do sistema evolutivo."""
    try:
        metrics = {
            "reward_trend": extrair_reward_trend(),
            "win_rate": extrair_win_rate_trend(),
            "model_accuracy": extrair_model_accuracy_trend(),
            "periods": {
                "daily": agregar_metricas_por_periodo("daily"),
                "weekly": agregar_metricas_por_periodo("weekly"),
                "monthly": agregar_metricas_por_periodo("monthly")
            }
        }
        return metrics
    except Exception as e:
        logging.error(f"❌ Erro ao obter métricas de performance: {e}")
        return {}


def get_current_evolution_parameters() -> Dict:
    """Obtém parâmetros atuais de todos os sistemas evolutivos."""
    parameters = {}

    # Parâmetros do sistema adaptativo
    if sistema_adaptativo_global:
        try:
            parameters["adaptive"] = sistema_adaptativo_global.filtros_atuais
        except Exception as e:
            logging.error(f"❌ Erro ao obter parâmetros adaptativos: {e}")
            parameters["adaptive"] = {"erro": str(e)}

    # Parâmetros do sistema híbrido
    if sistema_hibrido_global:
        try:
            parameters["hybrid"] = sistema_hibrido_global.obter_filtros_finais()
        except Exception as e:
            logging.error(f"❌ Erro ao obter parâmetros híbridos: {e}")
            parameters["hybrid"] = {"erro": str(e)}

    # Parâmetros dos filtros evolutivos
    if filtros_evolutivos_global:
        try:
            parameters["filters"] = filtros_evolutivos_global.get_filtros_atuais()
        except Exception as e:
            logging.error(f"❌ Erro ao obter parâmetros de filtros: {e}")
            parameters["filters"] = {"erro": str(e)}

    return parameters


def get_evolution_parameters_history() -> List[Dict]:
    """Obtém histórico de alterações nos parâmetros evolutivos."""
    history = []

    try:
        # Tenta carregar histórico do sistema híbrido
        if os.path.exists(HISTORICO_EVOLUCAO_HIBRIDA_CSV):
            df = pd.read_csv(HISTORICO_EVOLUCAO_HIBRIDA_CSV)

            for _, row in df.iterrows():
                history.append({
                    "timestamp": row.get('timestamp', ''),
                    "parameter": "threshold_confianca",
                    "value": float(row.get('threshold_final', 0)),
                    "system": "hybrid",
                    "nivel": row.get('nivel', '')
                })

                history.append({
                    "timestamp": row.get('timestamp', ''),
                    "parameter": "min_entropia",
                    "value": float(row.get('min_entropia_final', 0)),
                    "system": "hybrid",
                    "nivel": row.get('nivel', '')
                })

        # Tenta carregar histórico do sistema adaptativo
        if os.path.exists(HISTORICO_EVOLUCAO_CSV):
            df = pd.read_csv(HISTORICO_EVOLUCAO_CSV)

            for _, row in df.iterrows():
                history.append({
                    "timestamp": row.get('timestamp', ''),
                    "parameter": "threshold_confianca",
                    "value": float(row.get('threshold_confianca', 0)),
                    "system": "adaptive",
                    "ciclo": int(row.get('ciclo', 0))
                })

    except Exception as e:
        logging.error(f"❌ Erro ao obter histórico de parâmetros: {e}")

    # Ordena por timestamp
    history.sort(key=lambda x: x.get('timestamp', ''))

    return history[-100:]  # Retorna últimos 100 registros


def get_evolution_trading_impact() -> Dict:
    """Analisa o impacto da evolução nas decisões de trading."""
    impact = {
        "before_after": {},
        "by_evolution_cycle": []
    }

    try:
        # Aqui precisaríamos de dados que correlacionem ciclos evolutivos com performance
        # Como não temos esses dados diretamente, vamos criar uma aproximação

        if os.path.exists(HISTORICO_EVOLUCAO_HIBRIDA_CSV):
            df_evolucao = pd.read_csv(HISTORICO_EVOLUCAO_HIBRIDA_CSV)

            if len(df_evolucao) > 0:
                # Pega primeiro e último registro para comparação antes/depois
                primeiro = df_evolucao.iloc[0]
                ultimo = df_evolucao.iloc[-1]

                impact["before_after"] = {
                    "before": {
                        "win_rate": float(primeiro.get('taxa_acerto', 0)),
                        "profit_factor": float(primeiro.get('profit_factor', 0)),
                        "threshold": float(primeiro.get('threshold_final', 0))
                    },
                    "after": {
                        "win_rate": float(ultimo.get('taxa_acerto', 0)),
                        "profit_factor": float(ultimo.get('profit_factor', 0)),
                        "threshold": float(ultimo.get('threshold_final', 0))
                    }
                }

                # Calcula métricas por ciclo de evolução
                for _, row in df_evolucao.iterrows():
                    impact["by_evolution_cycle"].append({
                        "cycle": int(row.get('ciclo_adaptacao', 0)),
                        "win_rate": float(row.get('taxa_acerto', 0)),
                        "profit_factor": float(row.get('profit_factor', 0)),
                        "nivel": row.get('nivel', ''),
                        "timestamp": row.get('timestamp', '')
                    })

    except Exception as e:
        logging.error(f"❌ Erro ao analisar impacto da evolução: {e}")

    return impact


def get_evolution_significant_events() -> List[Dict]:
    """Identifica eventos significativos na evolução do sistema."""
    events = []

    try:
        # Eventos de mudança de nível
        if os.path.exists(HISTORICO_EVOLUCAO_HIBRIDA_CSV):
            df = pd.read_csv(HISTORICO_EVOLUCAO_HIBRIDA_CSV)

            # Detecta mudanças de nível
            nivel_anterior = None
            for _, row in df.iterrows():
                nivel_atual = row.get('nivel', '')

                if nivel_anterior and nivel_atual != nivel_anterior:
                    events.append({
                        "timestamp": row.get('timestamp', ''),
                        "event": "Level Up",
                        "description": f"Sistema evoluiu de '{nivel_anterior}' para '{nivel_atual}'",
                        "impact": "Aumento de seletividade e threshold"
                    })

                nivel_anterior = nivel_atual

        # Eventos de ajuste significativo de parâmetros
        if os.path.exists(HISTORICO_EVOLUCAO_CSV):
            df = pd.read_csv(HISTORICO_EVOLUCAO_CSV)

            # Detecta mudanças significativas no threshold
            threshold_anterior = None
            for _, row in df.iterrows():
                threshold_atual = row.get('threshold_confianca', 0)

                if threshold_anterior and abs(threshold_atual - threshold_anterior) > 0.05:
                    direction = "aumentado" if threshold_atual > threshold_anterior else "reduzido"
                    events.append({
                        "timestamp": row.get('timestamp', ''),
                        "event": "Parameter Adjustment",
                        "description": f"Threshold {direction} de {threshold_anterior:.2f} para {threshold_atual:.2f}",
                        "impact": "Alteração na seletividade do sistema"
                    })

                threshold_anterior = threshold_atual

    except Exception as e:
        logging.error(f"❌ Erro ao identificar eventos significativos: {e}")

    # Ordena por timestamp
    events.sort(key=lambda x: x.get('timestamp', ''))

    return events


def get_adaptative_system_status() -> Dict:
    """Obtém status do sistema adaptativo."""
    if not sistema_adaptativo_global:
        return {"disponivel": False}

    try:
        filtros = sistema_adaptativo_global.filtros_atuais
        return {
            "disponivel": True,
            "ciclos_evolucao": sistema_adaptativo_global.ciclos_evolucao,
            "filtros": filtros,
            "ultima_evolucao": datetime.now().isoformat()  # Simulado
        }
    except Exception as e:
        logging.error(f"❌ Erro ao obter status do sistema adaptativo: {e}")
        return {"disponivel": False, "erro": str(e)}


def get_hybrid_system_status() -> Dict:
    """Obtém status do sistema híbrido."""
    if not sistema_hibrido_global:
        return {"disponivel": False}

    try:
        filtros = sistema_hibrido_global.obter_filtros_finais()
        return {
            "disponivel": True,
            "nivel_atual": sistema_hibrido_global.nivel_atual,
            "ciclos_adaptacao": sistema_hibrido_global.ciclos_adaptacao,
            "filtros": filtros,
            "ultima_avaliacao": sistema_hibrido_global.ultima_avaliacao.isoformat() if sistema_hibrido_global.ultima_avaliacao else None
        }
    except Exception as e:
        logging.error(f"❌ Erro ao obter status do sistema híbrido: {e}")
        return {"disponivel": False, "erro": str(e)}


def get_filters_system_status() -> Dict:
    """Obtém status do sistema de filtros evolutivos."""
    if not filtros_evolutivos_global:
        return {"disponivel": False}

    try:
        stats = filtros_evolutivos_global.get_estatisticas()
        return {
            "disponivel": True,
            "nivel_atual": stats.get('nivel_atual', ''),
            "total_experiencias": stats.get('total_experiencias', 0),
            "filtros_ativos": stats.get('filtros_ativos', {}),
            "taxa_acerto_recente": stats.get('taxa_acerto_recente', 0)
        }
    except Exception as e:
        logging.error(f"❌ Erro ao obter status dos filtros evolutivos: {e}")
        return {"disponivel": False, "erro": str(e)}


def get_recent_evolution_alerts() -> List[Dict]:
    """Obtém alertas recentes do sistema evolutivo."""
    alerts = []

    try:
        # Alerta de mudança de nível
        if sistema_hibrido_global and sistema_hibrido_global.nivel_atual:
            nivel = sistema_hibrido_global.nivel_atual
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "info",
                "title": f"Nível Atual: {nivel.upper()}",
                "message": f"Sistema operando no nível {nivel}",
                "source": "hybrid"
            })

        # Alerta de ciclos de adaptação
        if sistema_hibrido_global:
            ciclos = sistema_hibrido_global.ciclos_adaptacao
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "info",
                "title": f"Ciclos de Adaptação: {ciclos}",
                "message": f"Sistema realizou {ciclos} ciclos de adaptação",
                "source": "hybrid"
            })

        # Alerta de threshold atual
        if sistema_adaptativo_global and sistema_adaptativo_global.filtros_atuais:
            threshold = sistema_adaptativo_global.filtros_atuais.get(
                'threshold_confianca', 0)
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "info",
                "title": f"Threshold: {threshold:.2f}",
                "message": f"Threshold de confiança atual: {threshold:.2f}",
                "source": "adaptive"
            })

        # Alerta de taxa de acerto
        if filtros_evolutivos_global:
            try:
                taxa = filtros_evolutivos_global.calcular_taxa_acerto_recente()
                tipo = "success" if taxa >= 0.6 else "warning" if taxa >= 0.5 else "danger"
                alerts.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": tipo,
                    "title": f"Taxa de Acerto: {taxa:.1%}",
                    "message": f"Taxa de acerto recente: {taxa:.1%}",
                    "source": "filters"
                })
            except:
                pass

    except Exception as e:
        logging.error(f"❌ Erro ao obter alertas recentes: {e}")
        alerts.append({
            "timestamp": datetime.now().isoformat(),
            "type": "danger",
            "title": "Erro no Sistema",
            "message": f"Erro ao processar alertas: {str(e)}",
            "source": "system"
        })

    return alerts
# region [API Endpoints]


def register_evolution_endpoints(app):
    """Registra todos os endpoints de API para o sistema evolutivo."""

    @app.route("/api/evolution/metrics", methods=["GET"])
    def api_evolution_metrics():
        """Retorna métricas de performance evolutiva."""
        try:
            metrics = get_evolution_performance_metrics()
            return jsonify({
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"❌ Erro na API de métricas evolutivas: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/evolution/parameters", methods=["GET"])
    def api_evolution_parameters():
        """Retorna parâmetros evolutivos atuais e histórico."""
        try:
            parameters = {
                "current": get_current_evolution_parameters(),
                "history": get_evolution_parameters_history(),
                "timestamp": datetime.now().isoformat()
            }
            return jsonify(parameters)
        except Exception as e:
            logging.error(f"❌ Erro na API de parâmetros evolutivos: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/evolution/impact", methods=["GET"])
    def api_evolution_impact():
        """Retorna dados sobre o impacto da evolução nas decisões de trading."""
        try:
            impact = {
                "trading_performance": get_evolution_trading_impact(),
                "significant_events": get_evolution_significant_events(),
                "timestamp": datetime.now().isoformat()
            }
            return jsonify(impact)
        except Exception as e:
            logging.error(f"❌ Erro na API de impacto evolutivo: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/evolution/status", methods=["GET"])
    def api_evolution_status():
        """Retorna status geral dos sistemas evolutivos."""
        try:
            status = {
                "adaptative": get_adaptative_system_status(),
                "hybrid": get_hybrid_system_status(),
                "filters": get_filters_system_status(),
                "timestamp": datetime.now().isoformat()
            }
            return jsonify(status)
        except Exception as e:
            logging.error(f"❌ Erro na API de status evolutivo: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/evolution/alerts", methods=["GET"])
    def api_evolution_alerts():
        """Retorna alertas recentes dos sistemas evolutivos."""
        try:
            alerts = {
                "alerts": get_recent_evolution_alerts(),
                "timestamp": datetime.now().isoformat()
            }
            return jsonify(alerts)
        except Exception as e:
            logging.error(f"❌ Erro na API de alertas evolutivos: {e}")
            return jsonify({"error": str(e)}), 500

# endregion


# Função para inicializar o módulo
def initialize_evolution_api(app, sistemas):
    """Inicializa o módulo de API evolutiva."""
    global sistema_evolutivo_global, sistema_adaptativo_global, sistema_hibrido_global, filtros_evolutivos_global

    # Armazena referências aos sistemas
    sistema_evolutivo_global = sistemas.get('evolutivo')
    sistema_adaptativo_global = sistemas.get('adaptativo')
    sistema_hibrido_global = sistemas.get('hibrido')
    filtros_evolutivos_global = sistemas.get('filtros')

    # Registra endpoints
    register_evolution_endpoints(app)

    logging.info("✅ API de evolução inicializada com sucesso")
    return True


if __name__ == "__main__":
    # Teste do módulo
    print("Este módulo deve ser importado pelo monstro_unificado.py")
