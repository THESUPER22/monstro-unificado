#!/usr/bin/env python3
"""
🛡️ PROTEÇÃO DEFINITIVA DO MODELO MONSTRO
Este script mantém uma cópia de segurança do modelo em local separado
e verifica periodicamente sua integridade.
"""

import glob
import logging
import os
import shutil
import time
from datetime import datetime

# Configurações de proteção
MODELO_PRINCIPAL = "modelo_monstro.h5"
PASTA_PROTECAO = "modelo_protegido"
INTERVALO_VERIFICACAO = 3600  # 1 hora em segundos

def configurar_logging():
    """Configura logging para o sistema de proteção."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - PROTEÇÃO - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('protecao_modelo.log'),
            logging.StreamHandler()
        ]
    )

def criar_pasta_protecao():
    """Cria pasta de proteção se não existir."""
    if not os.path.exists(PASTA_PROTECAO):
        os.makedirs(PASTA_PROTECAO)
        logging.info(f"📁 Pasta de proteção criada: {PASTA_PROTECAO}")

def proteger_modelo():
    """Cria backup de proteção do modelo."""
    try:
        if not os.path.exists(MODELO_PRINCIPAL):
            logging.warning(f"⚠️ Modelo principal não encontrado: {MODELO_PRINCIPAL}")
            return False

        criar_pasta_protecao()

        # Nome do backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_nome = f"modelo_monstro_protegido_{timestamp}.h5"
        backup_path = os.path.join(PASTA_PROTECAO, backup_nome)

        # Cria backup
        shutil.copy2(MODELO_PRINCIPAL, backup_path)
        logging.info(f"🔒 Backup de proteção criado: {backup_path}")

        # Mantém cópia mais recente como "modelo_monstro_seguro.h5"
        copia_segura = os.path.join(PASTA_PROTECAO, "modelo_monstro_seguro.h5")
        shutil.copy2(MODELO_PRINCIPAL, copia_segura)
        logging.info(f"💾 Cópia segura atualizada: {copia_segura}")

        # Limpa backups antigos (mantém últimos 5)
        backups = sorted(glob.glob(os.path.join(PASTA_PROTECAO, "modelo_monstro_protegido_*.h5")))
        while len(backups) > 5:
            backup_antigo = backups.pop(0)
            os.remove(backup_antigo)
            logging.info(f"🧹 Backup antigo removido: {backup_antigo}")

        return True

    except Exception as e:
        logging.error(f"❌ Erro ao proteger modelo: {e}")
        return False

def verificar_integridade():
    """Verifica se o modelo principal ainda existe e está íntegro."""
    try:
        if not os.path.exists(MODELO_PRINCIPAL):
            logging.error(f"💀 MODELO PRINCIPAL PERDIDO: {MODELO_PRINCIPAL}")
            return restaurar_modelo()

        # Verifica tamanho do arquivo (modelo válido deve ter mais que 50KB)
        tamanho = os.path.getsize(MODELO_PRINCIPAL) / 1024  # KB
        if tamanho < 50:
            logging.error(f"💀 MODELO CORROMPIDO (muito pequeno): {tamanho:.1f}KB")
            return restaurar_modelo()

        logging.info(f"✅ Modelo principal íntegro: {tamanho:.1f}KB")
        return True

    except Exception as e:
        logging.error(f"❌ Erro na verificação: {e}")
        return False

def restaurar_modelo():
    """Restaura modelo da cópia de proteção."""
    try:
        copia_segura = os.path.join(PASTA_PROTECAO, "modelo_monstro_seguro.h5")

        if os.path.exists(copia_segura):
            shutil.copy2(copia_segura, MODELO_PRINCIPAL)
            logging.info(f"🚑 MODELO RESTAURADO de: {copia_segura}")
            return True
        else:
            # Tenta backup mais recente
            backups = sorted(glob.glob(os.path.join(PASTA_PROTECAO, "modelo_monstro_protegido_*.h5")), reverse=True)
            if backups:
                backup_recente = backups[0]
                shutil.copy2(backup_recente, MODELO_PRINCIPAL)
                logging.info(f"🚑 MODELO RESTAURADO de backup: {backup_recente}")
                return True
            else:
                logging.error("💀 NENHUMA CÓPIA DE PROTEÇÃO ENCONTRADA!")
                return False

    except Exception as e:
        logging.error(f"❌ Erro na restauração: {e}")
        return False

def protecao_continua():
    """Loop principal de proteção contínua."""
    logging.info("🛡️ SISTEMA DE PROTEÇÃO INICIADO")
    logging.info(f"🔄 Verificação a cada {INTERVALO_VERIFICACAO/60:.0f} minutos")

    while True:
        try:
            # Verifica integridade
            if verificar_integridade():
                # Se modelo está OK, cria backup de proteção
                proteger_modelo()

            # Aguarda próxima verificação
            logging.info(f"😴 Aguardando {INTERVALO_VERIFICACAO/60:.0f} minutos...")
            time.sleep(INTERVALO_VERIFICACAO)

        except KeyboardInterrupt:
            logging.info("🛑 Sistema de proteção interrompido pelo usuário")
            break
        except Exception as e:
            logging.error(f"❌ Erro no loop de proteção: {e}")
            time.sleep(60)  # Aguarda 1 minuto em caso de erro

if __name__ == "__main__":
    configurar_logging()

    # Proteção inicial
    logging.info("🚀 Iniciando proteção inicial...")
    proteger_modelo()

    # Inicia proteção contínua
    protecao_continua()
