# CÓDIGO DE INTEGRAÇÃO PARA MONSTRO_UNIFICADO.PY
# Adicione este código ao arquivo monstro_unificado.py para integrar os endpoints de evolução

# 1. Adicione a importação no início do arquivo, após as outras importações
from api_evolution_endpoints import initialize_evolution_api


# 2. Adicione este código na função de inicialização do sistema (após a inicialização do Flask)
def inicializar_api_evolution():
    """Inicializa a API de evolução."""
    global app, sistema_evolutivo_global, sistema_adaptativo_global, sistema_hibrido_global, filtros_evolutivos_global

    # Cria dicionário com referências aos sistemas
    sistemas = {
        'evolutivo': sistema_evolutivo_global,
        'adaptativo': sistema_adaptativo_global,
        'hibrido': sistema_hibrido_global,
        'filtros': filtros_evolutivos_global
    }

    # Inicializa API de evolução
    initialize_evolution_api(app, sistemas)
    logging.info("✅ API de evolução integrada ao Monstro")


# 3. Chame a função inicializar_api_evolution() após inicializar o Flask e os sistemas evolutivos
# Exemplo:
"""
# Inicializa Flask
app = Flask(__name__)

# Inicializa sistemas evolutivos
inicializar_sistema_evolutivo()

# Inicializa API de evolução
inicializar_api_evolution()
"""

# 4. Adicione este código ao final do arquivo para testar a integração
"""
# Teste da API de evolução
@app.route("/teste_evolution_api")
def teste_evolution_api():
    return jsonify({
        "status": "API de evolução integrada com sucesso",
        "endpoints": [
            "/api/evolution/metrics",
            "/api/evolution/parameters",
            "/api/evolution/impact",
            "/api/evolution/status",
            "/api/evolution/alerts"
        ]
    })
""""""
