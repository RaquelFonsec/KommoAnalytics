import os
import mysql.connector
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from decimal import Decimal
import json
import requests
import time
import pandas as pd
import numpy as np

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_conversao_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class ConversaoETLAPI:
    """ETL que busca dados diretamente da API do Kommo para Conversão e Receita"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', '172.17.0.1'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'kommo_analytics'),
            'password': os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            'database': os.getenv('DB_NAME', 'kommo_analytics')
        }
        
        # Configurações da API Kommo
        self.kommo_api_url = "https://previdas.kommo.com/api/v4"
        self.kommo_token = os.getenv('KOMMO_ACCESS_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.kommo_token}',
            'Content-Type': 'application/json'
        }
    
    def get_kommo_data(self, endpoint, params=None):
        """Busca dados da API do Kommo"""
        try:
            url = f"{self.kommo_api_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 401:
                logger.error("Erro 401: Token de acesso inválido ou expirado")
                return None
            elif response.status_code == 404:
                logger.warning(f"Endpoint {endpoint} não encontrado (404)")
                return None
            elif response.status_code == 403:
                logger.error("Erro 403: Acesso negado - verificar permissões do token")
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com a API: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar dados da API: {e}")
            return None
    
    def get_users_from_api(self):
        """Busca usuários da API do Kommo"""
        logger.info("🔍 Buscando usuários da API do Kommo...")
        
        users_data = self.get_kommo_data('users')
        if not users_data:
            logger.warning("⚠️ Não foi possível buscar usuários da API")
            return {}
        
        users_mapping = {}
        for user in users_data.get('_embedded', {}).get('users', []):
            user_id = user.get('id')
            name = user.get('name', f'User_{user_id}')
            role = user.get('role', 'Vendedor')
            
            users_mapping[user_id] = {
                'name': name,
                'role': role
            }
        
        logger.info(f"✅ Encontrados {len(users_mapping)} usuários na API")
        return users_mapping
    
    def get_leads_from_api(self, days=90):
        """Busca leads da API do Kommo"""
        logger.info(f"🔍 Buscando leads dos últimos {days} dias da API do Kommo...")
        
        # Calcular data de início
        data_inicio = datetime.now() - timedelta(days=days)
        timestamp_inicio = int(data_inicio.timestamp())
        
        params = {
            'filter[created_at][from]': timestamp_inicio,
            'limit': 250
        }
        
        all_leads = []
        page = 1
        
        while True:
            params['page'] = page
            leads_data = self.get_kommo_data('leads', params)
            
            if not leads_data or not leads_data.get('_embedded', {}).get('leads'):
                break
            
            leads = leads_data['_embedded']['leads']
            all_leads.extend(leads)
            
            if len(leads) < 250:
                break
            
            page += 1
            time.sleep(0.5)
        
        logger.info(f"✅ Encontrados {len(all_leads)} leads na API")
        return all_leads
    
    def extract_conversion_data(self, days=90):
        """Extrai dados de conversão da API do Kommo"""
        logger.info("📊 Extraindo dados de conversão da API do Kommo...")
        
        # Buscar dados da API
        users_mapping = self.get_users_from_api()
        leads = self.get_leads_from_api(days)
        
        # Processar dados de conversão
        conversion_data = []
        
        for lead in leads:
            lead_id = lead.get('id')
            responsible_user_id = lead.get('responsible_user_id')
            pipeline_id = lead.get('pipeline_id')
            status_id = lead.get('status_id')
            price = lead.get('price', 0)
            created_at = lead.get('created_at')
            updated_at = lead.get('updated_at')
            
            # Mapear usuário
            user_info = users_mapping.get(responsible_user_id, {'name': f'User_{responsible_user_id}', 'role': 'Vendedor'})
            user_name = user_info['name']
            user_role = user_info['role']
            
            # Determinar status
            status_name = 'Em andamento'
            status_type = 'open'
            
            if price > 0:
                status_name = 'Venda ganha'
                status_type = 'won'
            elif status_id and price == 0:
                # Verificar se é status de perda
                status_name = 'Venda perdida'
                status_type = 'lost'
            
            # Calcular ciclo de vendas
            created_date = datetime.fromtimestamp(created_at)
            updated_date = datetime.fromtimestamp(updated_at)
            sales_cycle_days = (updated_date - created_date).days
            
            conversion_data.append({
                'lead_id': lead_id,
                'responsible_user_id': responsible_user_id,
                'responsible_user_name': user_name,
                'responsible_user_role': user_role,
                'pipeline_id': pipeline_id,
                'status_id': status_id,
                'status_name': status_name,
                'status_type': status_type,
                'sale_price': price,
                'created_date': created_date.date(),
                'updated_date': updated_date.date(),
                'sales_cycle_days': sales_cycle_days
            })
        
        logger.info(f"✅ Processados {len(conversion_data)} registros de conversão")
        return conversion_data
    
    def load_to_database(self, data):
        """Carrega dados de conversão no banco de dados"""
        logger.info("💾 Carregando dados de conversão no banco...")
        
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor()
        
        # Limpar dados antigos
        cursor.execute("DELETE FROM sales_metrics WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)")
        
        # Inserir novos dados
        insert_query = """
        INSERT INTO sales_metrics 
        (lead_id, responsible_user_name, responsible_user_role, 
         pipeline_id, status_name, status_type, sale_price, 
         created_date, closed_at, sales_cycle_days)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for record in data:
            cursor.execute(insert_query, (
                record['lead_id'],
                record['responsible_user_name'],
                record['responsible_user_role'],
                record['pipeline_id'],
                record['status_name'],
                record['status_type'],
                record['sale_price'],
                record['created_date'],
                record['updated_date'],
                record['sales_cycle_days']
            ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"✅ Inseridos {len(data)} registros de conversão no banco")
        return True

def main():
    """Execução principal"""
    try:
        logger.info("🚀 === INICIANDO ETL MÓDULO 4 - CONVERSÃO E RECEITA (API KOMMO) ===")
        
        etl = ConversaoETLAPI()
        
        # Extrair dados de conversão
        dados = etl.extract_conversion_data(days=90)
        
        # Carregar no banco
        etl.load_to_database(dados)
        
        # Estatísticas finais
        vendas_ganhas = [d for d in dados if d['status_name'] == 'Venda ganha']
        vendas_perdidas = [d for d in dados if d['status_name'] == 'Venda perdida']
        receita_total = sum(d['sale_price'] for d in vendas_ganhas)
        ticket_medio = receita_total / len(vendas_ganhas) if vendas_ganhas else 0
        win_rate = len(vendas_ganhas) / (len(vendas_ganhas) + len(vendas_perdidas)) * 100 if (vendas_ganhas or vendas_perdidas) else 0
        
        logger.info("🎉 === ETL MÓDULO 4 CONCLUÍDO COM SUCESSO (API KOMMO) ===")
        logger.info(f"📊 CONVERSÃO E RECEITA:")
        logger.info(f"  ✅ Vendas Fechadas: {len(vendas_ganhas)}")
        logger.info(f"  ❌ Vendas Perdidas: {len(vendas_perdidas)}")
        logger.info(f"  💰 Receita Total: R$ {receita_total:,.2f}")
        logger.info(f"  💵 Ticket Médio: R$ {ticket_medio:,.2f}")
        logger.info(f"  📈 Win Rate: {win_rate:.1f}%")
        logger.info(f"  📊 Total Leads: {len(dados)}")
        
    except Exception as e:
        logger.error(f"❌ Erro durante execução do ETL: {e}")
        raise

if __name__ == "__main__":
    main()
