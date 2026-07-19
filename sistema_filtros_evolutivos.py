#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 SISTEMA DE FILTROS EVOLUTIVOS PARA O MONSTRO
Aumenta seletividade conforme experiência cresce, melhorando assertividade
"""

import json
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


class FiltrosEvolutivos:
    """Sistema de filtros que evolui com a experiência do Monstro."""

    def __init__(self):
        self.config_file = "filtros_evolutivos.json"
        self.load_config()

    def load_config(self):
        """Carrega configuração dos filtros evolutivos."""
        default_config = {
            "niveis_experiencia": {
                "iniciante": {"min_exp": 0, "max_exp": 1000},
                "intermediario": {"min_exp": 1001, "max_exp": 5000},
                "avancado": {"min_exp": 5001, "max_exp": 15000},
                "expert": {"min_exp": 15001, "max_exp": 50000},
                "mestre": {"min_exp": 50001, "max_exp": 999999}
            },
            "filtros_por_nivel": {
                "iniciante": {
                    "threshold_confianca": 0.6,
                    "min_entropia": 0.3,
                    "max_spread": 2.0,
                    "min_volume_book": 200,
                    "filtro_rsi": {"min": 25, "max": 75},
                    "filtro_volatilidade": {"min": 0.5, "max": 10.0},
                    "cooldown_operacoes": 30  # segundos
                },
                "intermediario": {
                    "threshold_confianca": 0.65,
                    "min_entropia": 0.4,
                    "max_spread": 1.5,
                    "min_volume_book": 300,
                    "filtro_rsi": {"min": 30, "max": 70},
                    "filtro_volatilidade": {"min": 0.8, "max": 8.0},
                    "cooldown_operacoes": 45
                },
                "avancado": {
                    "threshold_confianca": 0.7,
                    "min_entropia": 0.5,
                    "max_spread": 1.0,
                    "min_volume_book": 400,
                    "filtro_rsi": {"min": 35, "max": 65},
                    "filtro_volatilidade": {"min": 1.0, "max": 6.0},
                    "cooldown_operacoes": 60
                },
                "expert": {
                    "threshold_confianca": 0.75,
                    "min_entropia": 0.6,
                    "max_spread": 0.8,
                    "min_volume_book": 500,
                    "filtro_rsi": {"min": 40, "max": 60},
                    "filtro_volatilidade": {"min": 1.2, "max": 5.0},
                    "cooldown_operacoes": 90
                },
                "mestre": {
                    "threshold_confianca": 0.8,
                    "min_entropia": 0.7,
                    "max_spread": 0.5,
                    "min_volume_book": 600,
                    "filtro_rsi": {"min": 45, "max": 55},
                    "filtro_volatilidade": {"min": 1.5, "max": 4.0},
                    "cooldown_operacoes": 120
                }
            },
            "metricas_performance": {
                "taxa_acerto_minima": 0.6,
                "lucro_medio_minimo": 10.0,
                "max_drawdown_permitido": -200.0
            }
        }

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()

    def save_config(self):
        """Salva configuração dos filtros."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_nivel_experiencia(self):
        """Determina nível de experiência baseado no histórico."""
        try:
            if os.path.exists('historico_contexto.csv'):
                df = pd.read_csv('historico_contexto.csv')
                total_experiencias = len(df)
            else:
                total_experiencias = 0

            # Determina nível baseado na quantidade de experiências
            for nivel, config in self.config["niveis_experiencia"].items():
                if config["min_exp"] <= total_experiencias <= config["max_exp"]:
                    return nivel, total_experiencias

            return "mestre", total_experiencias

        except Exception as e:
            print(f"Erro ao determinar nível: {e}")
            return "iniciante", 0

    def get_filtros_atuais(self):
        """Retorna filtros para o nível atual de experiência."""
        nivel, experiencias = self.get_nivel_experiencia()
        filtros = self.config["filtros_por_nivel"][nivel].copy()

        # Adiciona informações do nível
        filtros["nivel_atual"] = nivel
        filtros["total_experiencias"] = experiencias

        return filtros

    def calcular_taxa_acerto_recente(self, janela_dias=7):
        """Calcula taxa de acerto dos últimos dias."""
        try:
            if not os.path.exists('historico_contexto.csv'):
                return 0.0

            df = pd.read_csv('historico_contexto.csv')

            # Filtra operações reais (não NAO_AGIU)
            operacoes = df[df['action'].isin(['BUY', 'SELL'])]

            if len(operacoes) == 0:
                return 0.0

            # Pega últimas operações (baseado em quantidade, não data)
            ultimas_operacoes = operacoes.tail(100)  # Últimas 100 operações

            # Calcula taxa de acerto
            acertos = len(ultimas_operacoes[ultimas_operacoes['reward'] > 0])
            taxa_acerto = acertos / len(ultimas_operacoes)

            return taxa_acerto

        except Exception as e:
            print(f"Erro ao calcular taxa de acerto: {e}")
            return 0.0

    def deve_operar(self, contexto_decisao):
        """
        Decide se deve operar baseado nos filtros evolutivos.

        Args:
            contexto_decisao: Dict com dados da decisão
                - confianca: float (0-1)
                - entropia_book: float
                - spread: float
                - volume_book: int
                - rsi_14: float
                - volatility: float
                - ultima_operacao_tempo: datetime

        Returns:
            tuple: (deve_operar: bool, motivo: str, filtros_aplicados: dict)
        """
        filtros = self.get_filtros_atuais()
        motivos_bloqueio = []

        # Filtro 1: Confiança mínima
        if contexto_decisao.get('confianca', 0) < filtros['threshold_confianca']:
            motivos_bloqueio.append(
                f"Confiança baixa ({contexto_decisao.get('confianca', 0):.3f} < {filtros['threshold_confianca']})")

        # Filtro 2: Entropia mínima
        if contexto_decisao.get('entropia_book', 0) < filtros['min_entropia']:
            motivos_bloqueio.append(
                f"Entropia baixa ({contexto_decisao.get('entropia_book', 0):.3f} < {filtros['min_entropia']})")

        # Filtro 3: Spread máximo
        if contexto_decisao.get('spread', 999) > filtros['max_spread']:
            motivos_bloqueio.append(
                f"Spread alto ({contexto_decisao.get('spread', 999)} > {filtros['max_spread']})")

        # Filtro 4: Volume mínimo do book
        volume_total = contexto_decisao.get(
            'bid_qty', 0) + contexto_decisao.get('ask_qty', 0)
        if volume_total < filtros['min_volume_book']:
            motivos_bloqueio.append(
                f"Volume baixo ({volume_total} < {filtros['min_volume_book']})")

        # Filtro 5: RSI em zona neutra (mais restritivo conforme evolui)
        rsi = contexto_decisao.get('rsi_14', 50)
        if not (filtros['filtro_rsi']['min'] <= rsi <= filtros['filtro_rsi']['max']):
            motivos_bloqueio.append(
                f"RSI fora da zona ({rsi} não está entre {filtros['filtro_rsi']['min']}-{filtros['filtro_rsi']['max']})")

        # Filtro 6: Volatilidade adequada
        volatilidade = contexto_decisao.get('volatility', 0)
        if not (filtros['filtro_volatilidade']['min'] <= volatilidade <= filtros['filtro_volatilidade']['max']):
            motivos_bloqueio.append(
                f"Volatilidade inadequada ({volatilidade:.2f} não está entre {filtros['filtro_volatilidade']['min']}-{filtros['filtro_volatilidade']['max']})")

        # Filtro 7: Cooldown entre operações
        if 'ultima_operacao_tempo' in contexto_decisao:
            tempo_desde_ultima = (
                datetime.now() - contexto_decisao['ultima_operacao_tempo']).total_seconds()
            if tempo_desde_ultima < filtros['cooldown_operacoes']:
                motivos_bloqueio.append(
                    f"Cooldown ativo ({tempo_desde_ultima:.0f}s < {filtros['cooldown_operacoes']}s)")

        # Filtro 8: Performance recente (só para níveis avançados)
        if filtros['nivel_atual'] in ['avancado', 'expert', 'mestre']:
            taxa_acerto = self.calcular_taxa_acerto_recente()
            if taxa_acerto < self.config['metricas_performance']['taxa_acerto_minima']:
                motivos_bloqueio.append(
                    f"Performance baixa (taxa: {taxa_acerto:.1%} < {self.config['metricas_performance']['taxa_acerto_minima']:.1%})")

        # Decisão final
        deve_operar = len(motivos_bloqueio) == 0
        motivo = "Todos os filtros aprovados" if deve_operar else "; ".join(
            motivos_bloqueio)

        return deve_operar, motivo, filtros

    def log_decisao_filtro(self, contexto, decisao, motivo, filtros):
        """Registra decisão do filtro para análise."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "nivel": filtros['nivel_atual'],
            "experiencias": filtros['total_experiencias'],
            "decisao": decisao,
            "motivo": motivo,
            "contexto": {
                "confianca": contexto.get('confianca', 0),
                "entropia": contexto.get('entropia_book', 0),
                "spread": contexto.get('spread', 0),
                "rsi": contexto.get('rsi_14', 50),
                "volatilidade": contexto.get('volatility', 0)
            }
        }

        # Salva em arquivo de log
        log_file = "filtros_evolutivos.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_estatisticas(self):
        """Retorna estatísticas dos filtros evolutivos."""
        nivel, experiencias = self.get_nivel_experiencia()
        filtros = self.get_filtros_atuais()
        taxa_acerto = self.calcular_taxa_acerto_recente()

        return {
            "nivel_atual": nivel,
            "total_experiencias": experiencias,
            "taxa_acerto_recente": taxa_acerto,
            "filtros_ativos": filtros,
            "proximos_niveis": self._get_proximos_niveis(experiencias)
        }

    def _get_proximos_niveis(self, experiencias_atuais):
        """Calcula progresso para próximos níveis."""
        niveis = list(self.config["niveis_experiencia"].keys())
        nivel_atual_idx = 0

        for i, nivel in enumerate(niveis):
            config = self.config["niveis_experiencia"][nivel]
            if config["min_exp"] <= experiencias_atuais <= config["max_exp"]:
                nivel_atual_idx = i
                break

        progresso = {}
        if nivel_atual_idx < len(niveis) - 1:
            proximo_nivel = niveis[nivel_atual_idx + 1]
            min_exp_proximo = self.config["niveis_experiencia"][proximo_nivel]["min_exp"]
            faltam = min_exp_proximo - experiencias_atuais
            progresso["proximo_nivel"] = proximo_nivel
            progresso["experiencias_necessarias"] = faltam
            progresso["progresso_pct"] = min(
                100, (experiencias_atuais / min_exp_proximo) * 100)

        return progresso


def integrar_filtros_no_monstro():
    """Função para integrar os filtros evolutivos no monstro_unificado.py"""

    codigo_integracao = '''
# ===== INTEGRAÇÃO DOS FILTROS EVOLUTIVOS =====
from sistema_filtros_evolutivos import FiltrosEvolutivos

# Inicializar sistema de filtros (adicionar no início do main)
filtros_evolutivos = FiltrosEvolutivos()

# Modificar função prever_acao para incluir filtros
def prever_acao_com_filtros(modelo, contexto_completo):
    """Versão melhorada da previsão com filtros evolutivos."""

    # Primeira etapa: Previsão da IA
    probabilidade = modelo.predict(contexto_completo, verbose=0)[0][0]

    # Segunda etapa: Aplicar filtros evolutivos
    contexto_decisao = {
        'confianca': probabilidade,
        'entropia_book': contexto_completo.get('entropia_book', 0),
        'spread': contexto_completo.get('spread', 0),
        'bid_qty': contexto_completo.get('bid_qty', 0),
        'ask_qty': contexto_completo.get('ask_qty', 0),
        'rsi_14': contexto_completo.get('rsi_14', 50),
        'volatility': contexto_completo.get('volatility', 0),
        'ultima_operacao_tempo': globals().get('ultima_operacao_tempo', datetime.now() - timedelta(hours=1))
    }

    deve_operar, motivo, filtros = filtros_evolutivos.deve_operar(contexto_decisao)

    if not deve_operar:
        logging.info(f"🚫 Operação bloqueada pelos filtros evolutivos: {motivo}")
        filtros_evolutivos.log_decisao_filtro(contexto_decisao, False, motivo, filtros)
        return "NADA", 0.0

    # Se passou nos filtros, decide direção
    if probabilidade > 0.5:
        acao = "BUY"
    else:
        acao = "SELL"

    logging.info(f"✅ Operação aprovada pelos filtros (Nível: {filtros['nivel_atual']}, Confiança: {probabilidade:.3f})")
    filtros_evolutivos.log_decisao_filtro(contexto_decisao, True, f"Aprovado para {acao}", filtros)

    # Atualiza timestamp da última operação
    globals()['ultima_operacao_tempo'] = datetime.now()

    return acao, probabilidade

# Adicionar endpoint no dashboard para monitorar filtros
@app.route("/api/filtros_evolutivos")
def api_filtros_evolutivos():
    """API para monitorar status dos filtros evolutivos."""
    try:
        stats = filtros_evolutivos.get_estatisticas()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)})
'''

    print("🔧 CÓDIGO DE INTEGRAÇÃO GERADO!")
    print("📝 Para integrar no monstro_unificado.py:")
    print("1. Adicione a importação no início")
    print("2. Substitua chamadas de prever_acao por prever_acao_com_filtros")
    print("3. Adicione o endpoint da API no dashboard")

    return codigo_integracao


if __name__ == "__main__":
    # Teste do sistema
    filtros = FiltrosEvolutivos()

    print("🎯 SISTEMA DE FILTROS EVOLUTIVOS INICIALIZADO")
    print("="*50)

    stats = filtros.get_estatisticas()
    print(f"📊 Nível atual: {stats['nivel_atual']}")
    print(f"🧠 Experiências: {stats['total_experiencias']}")
    print(f"🎯 Taxa de acerto: {stats['taxa_acerto_recente']:.1%}")

    if 'proximo_nivel' in stats['proximos_niveis']:
        print(
            f"⬆️  Próximo nível: {stats['proximos_niveis']['proximo_nivel']}")
        print(f"📈 Progresso: {stats['proximos_niveis']['progresso_pct']:.1f}%")

    # Teste de decisão
    contexto_teste = {
        'confianca': 0.75,
        'entropia_book': 0.6,
        'spread': 0.5,
        'bid_qty': 300,
        'ask_qty': 250,
        'rsi_14': 45,
        'volatility': 2.0
    }

    deve_operar, motivo, filtros_aplicados = filtros.deve_operar(
        contexto_teste)
    print(f"\n🧪 TESTE DE DECISÃO:")
    print(f"Resultado: {'✅ OPERAR' if deve_operar else '❌ NÃO OPERAR'}")
    print(f"Motivo: {motivo}")
