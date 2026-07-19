"""
Módulo de diagnóstico para o Monstro das Negociações
Verifica a integridade dos arquivos essenciais e configurações
"""

import os
import logging
from typing import List, Tuple

def checar_arquivos_essenciais() -> Tuple[bool, List[str]]:
    """
    Verifica se todos os arquivos essenciais existem.
    
    Returns:
        Tuple[bool, List[str]]: (sucesso, lista_de_erros)
    """
    arquivos_essenciais = [
        "monstro_unificado.py",
        "config.json",
    ]
    
    arquivos_opcionais = [
        "modelo_monstro.h5",
        "memoria.pkl", 
        "historico_evolucao.csv",
        "historico_contexto.csv",
        "decisions.csv",
        "experiencias.json"
    ]
    
    erros = []
    
    # Verifica arquivos essenciais
    for arquivo in arquivos_essenciais:
        if not os.path.exists(arquivo):
            erro = f"❌ Arquivo essencial não encontrado: {arquivo}"
            erros.append(erro)
            logging.error(erro)
    
    # Verifica arquivos opcionais (apenas avisa)
    for arquivo in arquivos_opcionais:
        if not os.path.exists(arquivo):
            aviso = f"⚠️ Arquivo opcional não encontrado: {arquivo} (será criado automaticamente)"
            logging.warning(aviso)
    
    # Verifica permissões de escrita
    try:
        with open("teste_escrita.tmp", "w") as f:
            f.write("teste")
        os.remove("teste_escrita.tmp")
    except Exception as e:
        erro = f"❌ Erro de permissão de escrita: {e}"
        erros.append(erro)
        logging.error(erro)
    
    sucesso = len(erros) == 0
    
    if sucesso:
        logging.info("✅ Diagnóstico de arquivos: OK")
    else:
        logging.error(f"❌ Diagnóstico falhou com {len(erros)} erros")
    
    return sucesso, erros

def verificar_configuracoes() -> Tuple[bool, List[str]]:
    """
    Verifica se as configurações estão corretas.
    
    Returns:
        Tuple[bool, List[str]]: (sucesso, lista_de_avisos)
    """
    avisos = []
    
    # Verifica se o MetaTrader está instalado
    mt5_paths = [
        r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5 Terminal\terminal64.exe"
    ]
    
    mt5_encontrado = any(os.path.exists(path) for path in mt5_paths)
    if not mt5_encontrado:
        avisos.append("⚠️ MetaTrader 5 não encontrado nos caminhos padrão")
    
    # Verifica espaço em disco (mínimo 1GB)
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (1024**3)
        if free_gb < 1:
            avisos.append(f"⚠️ Pouco espaço em disco: {free_gb}GB livre")
    except:
        avisos.append("⚠️ Não foi possível verificar espaço em disco")
    
    return len(avisos) == 0, avisos

def diagnostico_completo() -> bool:
    """
    Executa diagnóstico completo do sistema.
    
    Returns:
        bool: True se tudo estiver OK
    """
    logging.info("🔍 Iniciando diagnóstico completo do Monstro...")
    
    # Verifica arquivos
    arquivos_ok, erros_arquivos = checar_arquivos_essenciais()
    
    # Verifica configurações
    config_ok, avisos_config = verificar_configuracoes()
    
    # Log dos resultados
    if arquivos_ok and config_ok:
        logging.info("✅ Diagnóstico completo: Sistema OK")
        return True
    else:
        logging.warning("⚠️ Diagnóstico completo: Problemas encontrados")
        for erro in erros_arquivos:
            logging.error(erro)
        for aviso in avisos_config:
            logging.warning(aviso)
        return len(erros_arquivos) == 0  # OK se apenas avisos

if __name__ == "__main__":
    # Configura logging básico para teste
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Executa diagnóstico
    resultado = diagnostico_completo()
    print(f"Resultado do diagnóstico: {'✅ OK' if resultado else '❌ FALHOU'}") 