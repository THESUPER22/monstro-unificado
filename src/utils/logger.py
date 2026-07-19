import logging
from config.settings import LOG_FILE

def setup_logger():
    """Configura o sistema de logging."""
    # Configuração básica
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Formatador para console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Adiciona handler ao logger root
    logging.getLogger('').addHandler(console_handler)
    
    # Log inicial
    logging.info("🚀 Sistema de logging inicializado")
    
class CustomLogger:
    """Classe para logging customizado com emojis e formatação especial."""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def debug(self, message):
        self.logger.debug(f"🔍 {message}")
    
    def info(self, message):
        self.logger.info(f"ℹ️ {message}")
    
    def warning(self, message):
        self.logger.warning(f"⚠️ {message}")
    
    def error(self, message):
        self.logger.error(f"❌ {message}")
    
    def critical(self, message):
        self.logger.critical(f"🔥 {message}")
    
    def success(self, message):
        self.logger.info(f"✅ {message}")
    
    def trade(self, message):
        self.logger.info(f"💰 {message}")
    
    def market(self, message):
        self.logger.info(f"📊 {message}")
    
    def ai(self, message):
        self.logger.info(f"🧠 {message}")
    
    def system(self, message):
        self.logger.info(f"🔧 {message}")
        
def get_logger(name):
    """Retorna uma instância do logger customizado."""
    return CustomLogger(name) 