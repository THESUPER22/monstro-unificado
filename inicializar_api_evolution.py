# Função para inicializar a API de evolução no monstro_unificado_v2.py

def inicializar_api_evolution(app, sistema_evolutivo=None, sistema_adaptativo=None, sistema_hibrido=None, filtros_evolutivos=None):
    """Inicializa a API de evolução para o dashboard."""
    try:
        from api_evolution_endpoints import initialize_evolution_api

        # Cria dicionário com referências aos sistemas
        sistemas = {
            'evolutivo': sistema_evolutivo,
            'adaptativo': sistema_adaptativo,
            'hibrido': sistema_hibrido,
            'filtros': filtros_evolutivos
        }

        # Inicializa API de evolução
        initialize_evolution_api(app, sistemas)
        logging.info("✅ API de evolução integrada ao Monstro")
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao inicializar API de evolução: {e}")
        return False
