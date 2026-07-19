from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do MetaTrader
MT5_PATH = os.getenv('MT5_PATH', r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe")
SYMBOL = os.getenv('SYMBOL', "WDOM25")
TIMEFRAME = os.getenv('TIMEFRAME', "M1")
MAGIC_NUMBER = int(os.getenv('MAGIC_NUMBER', "123456"))

# Configurações de Arquivos
HISTORICO_CSV = os.getenv('HISTORICO_CSV', "historico_contexto.csv")
MODELO_PATH = os.getenv('MODELO_PATH', "modelo.h5")
LOG_FILE = os.getenv('LOG_FILE', "monstro.log")

# Configurações de Trading
VOLUME_MINIMO = float(os.getenv('VOLUME_MINIMO', "20.0"))
TRAILING_ATIVO = bool(os.getenv('TRAILING_ATIVO', "True"))
TRAILING_INTERVALO = int(os.getenv('TRAILING_INTERVALO', "5"))
TRAILING_GATILHO = int(os.getenv('TRAILING_GATILHO', "5000"))
TRAILING_DISTANCIA = int(os.getenv('TRAILING_DISTANCIA', "5000"))

# Configurações da API Web
FLASK_PORT = int(os.getenv('FLASK_PORT', "5001"))
FLASK_DEBUG = bool(os.getenv('FLASK_DEBUG', "False"))

# Configurações da IA
N_FEATURES = int(os.getenv('N_FEATURES', "11"))
LEARNING_RATE = float(os.getenv('LEARNING_RATE', "0.001")) 