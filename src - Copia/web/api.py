from flask import Flask, jsonify, request
from config.settings import FLASK_PORT, FLASK_DEBUG
from src.utils.logger import get_logger

logger = get_logger('web_api')
app = Flask(__name__)

# Variáveis globais para estado
historico_lucro = []
score = 0
ultima_decisao = None
posicao_aberta = False

@app.route("/status")
def status():
    """Retorna o status atual do sistema."""
    return jsonify({
        "score": score,
        "ultima_decisao": ultima_decisao,
        "posicao_atual": "Aberta" if posicao_aberta else "Nenhuma",
        "total_operacoes": len(historico_lucro),
        "lucro_total": sum(historico_lucro)
    })

@app.route("/lucro")
def lucro():
    """Retorna o histórico de lucros."""
    return jsonify({
        "lucros": historico_lucro,
        "total": sum(historico_lucro),
        "media": sum(historico_lucro) / len(historico_lucro) if historico_lucro else 0,
        "operacoes": len(historico_lucro)
    })

@app.route("/pausar", methods=["POST"])
def pausar():
    """Pausa o sistema de trading."""
    global thread_ativo
    thread_ativo = False
    logger.system("Sistema pausado via API")
    return jsonify({"status": "pausado"})

@app.route("/retomar", methods=["POST"])
def retomar():
    """Retoma o sistema de trading."""
    global thread_ativo
    thread_ativo = True
    logger.system("Sistema retomado via API")
    return jsonify({"status": "ativo"})

@app.route("/resetar_score", methods=["POST"])
def resetar_score():
    """Reseta o score do sistema."""
    global score
    score_antigo = score
    score = 0
    logger.system(f"Score resetado de {score_antigo} para 0")
    return jsonify({"status": "score resetado", "score_anterior": score_antigo})

@app.route("/fechar_posicao", methods=["POST"])
def fechar_posicao():
    """Fecha todas as posições abertas."""
    from src.trading.order_manager import OrderManager
    order_manager = OrderManager()
    
    if order_manager.fechar_todas_posicoes():
        logger.success("Todas as posições fechadas via API")
        return jsonify({"status": "posições fechadas"})
    else:
        logger.error("Erro ao fechar posições via API")
        return jsonify({"status": "erro ao fechar posições"}), 500

@app.route("/estatisticas")
def estatisticas():
    """Retorna estatísticas detalhadas do sistema."""
    if not historico_lucro:
        return jsonify({
            "mensagem": "Nenhuma operação realizada ainda"
        })
        
    lucro_total = sum(historico_lucro)
    media_lucro = lucro_total / len(historico_lucro)
    operacoes_positivas = len([x for x in historico_lucro if x > 0])
    operacoes_negativas = len([x for x in historico_lucro if x < 0])
    
    return jsonify({
        "lucro_total": lucro_total,
        "media_por_operacao": media_lucro,
        "total_operacoes": len(historico_lucro),
        "operacoes_positivas": operacoes_positivas,
        "operacoes_negativas": operacoes_negativas,
        "taxa_acerto": operacoes_positivas / len(historico_lucro) if historico_lucro else 0,
        "maior_lucro": max(historico_lucro) if historico_lucro else 0,
        "maior_prejuizo": min(historico_lucro) if historico_lucro else 0
    })

def iniciar_api():
    """Inicia o servidor Flask."""
    logger.system(f"Iniciando API na porta {FLASK_PORT}")
    app.run(port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False) 