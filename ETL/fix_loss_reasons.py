# Script para corrigir nomes dos motivos de perda
import os
import requests
import mysql.connector
import pandas as pd
from datetime import datetime
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class LossReasonsFixer:
    def __init__(self):
        self.kommo_config = {
            'base_url': 'https://previdas.kommo.com',
            'access_token': os.getenv('KOMMO_ACCESS_TOKEN'),
            'account_id': os.getenv('KOMMO_ACCOUNT_ID')
        }
        
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME')
        }
        
        self.headers = {
            'Authorization': f'Bearer {self.kommo_config["access_token"]}',
            'Content-Type': 'application/json'
        }

    def get_loss_reasons_from_api(self):
        """
        Buscar todos os motivos de perda disponíveis na API do Kommo
        """
        try:
            logger.info("Buscando motivos de perda na API do Kommo...")
            
            # Buscar motivos de perda
            url = f"{self.kommo_config['base_url']}/api/v4/leads/loss_reasons"
            params = {'limit': 250}
            
            loss_reasons = {}
            page = 1
            
            while True:
                params['page'] = page
                try:
                    response = requests.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    reasons = data.get('_embedded', {}).get('loss_reasons', [])
                    
                    if not reasons:
                        break
                    
                    for reason in reasons:
                        reason_id = reason.get('id')
                        reason_name = reason.get('name')
                        
                        if reason_id and reason_name:
                            loss_reasons[reason_id] = reason_name
                    
                    logger.info(f"Página {page}: {len(reasons)} motivos de perda encontrados")
                    
                    if len(reasons) < 250:
                        break
                        
                    page += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao buscar motivos de perda na página {page}: {e}")
                    break
            
            logger.info(f"Total de motivos de perda encontrados: {len(loss_reasons)}")
            
            # Log de amostra
            sample_reasons = list(loss_reasons.items())[:10]
            logger.info("Amostra de motivos de perda:")
            for reason_id, reason_name in sample_reasons:
                logger.info(f"  ID {reason_id}: {reason_name}")
            
            return loss_reasons
            
        except Exception as e:
            logger.error(f"Erro ao buscar motivos de perda: {e}")
            return {}

    def update_database_loss_reasons(self, loss_reasons_mapping):
        """
        Atualizar os nomes dos motivos de perda no banco de dados
        """
        try:
            logger.info("Atualizando motivos de perda no banco de dados...")
            
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Buscar registros que precisam ser atualizados
            cursor.execute("""
                SELECT DISTINCT loss_reason_id, loss_reason_name 
                FROM funnel_history 
                WHERE loss_reason_id IS NOT NULL 
                AND loss_reason_name LIKE 'Motivo ID %'
            """)
            
            records_to_update = cursor.fetchall()
            logger.info(f"Encontrados {len(records_to_update)} registros para atualizar")
            
            updated_count = 0
            
            for reason_id, current_name in records_to_update:
                if reason_id in loss_reasons_mapping:
                    new_name = loss_reasons_mapping[reason_id]
                    
                    # Atualizar o registro
                    cursor.execute("""
                        UPDATE funnel_history 
                        SET loss_reason_name = %s 
                        WHERE loss_reason_id = %s
                    """, (new_name, reason_id))
                    
                    updated_count += 1
                    logger.info(f"Atualizado: ID {reason_id} -> '{new_name}'")
            
            connection.commit()
            logger.info(f"Total de registros atualizados: {updated_count}")
            
            cursor.close()
            connection.close()
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Erro ao atualizar banco de dados: {e}")
            return 0

    def run_fix(self):
        """
        Executar a correção completa dos motivos de perda
        """
        try:
            logger.info("="*60)
            logger.info("INICIANDO CORREÇÃO DOS MOTIVOS DE PERDA")
            logger.info("="*60)
            
            # 1. Buscar motivos de perda da API
            loss_reasons = self.get_loss_reasons_from_api()
            
            if not loss_reasons:
                logger.error("Nenhum motivo de perda encontrado na API")
                return
            
            # 2. Atualizar banco de dados
            updated_count = self.update_database_loss_reasons(loss_reasons)
            
            logger.info("="*60)
            logger.info("CORREÇÃO CONCLUÍDA!")
            logger.info(f"Registros atualizados: {updated_count}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Erro na correção: {e}")

if __name__ == "__main__":
    fixer = LossReasonsFixer()
    fixer.run_fix()

