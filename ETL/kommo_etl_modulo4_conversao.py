
import os
import requests
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import logging
import json
from dotenv import load_dotenv
from collections import defaultdict
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class KommoConversionETL:
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
        
        # Cache para pipelines, status e usuários
        self.pipelines_cache = {}
        self.status_cache = {}
        self.users_cache = {}

    def extract_pipelines_and_statuses(self) -> Dict:
        """
        Extrair estrutura de pipelines e identificar status de fechamento
        """
        try:
            logger.info("Extraindo pipelines e status...")
            
            pipelines_url = f"{self.kommo_config['base_url']}/api/v4/leads/pipelines"
            pipelines_response = requests.get(pipelines_url, headers=self.headers)
            pipelines_response.raise_for_status()
            pipelines_data = pipelines_response.json()
            
            won_statuses = []
            proposal_statuses = []
            
            pipelines = pipelines_data.get('_embedded', {}).get('pipelines', [])
            logger.info(f"Encontrados {len(pipelines)} pipelines")
            
            for pipeline in pipelines:
                pipeline_id = pipeline.get('id')
                self.pipelines_cache[int(pipeline_id)] = {
                    'name': pipeline.get('name'),
                    'is_main': pipeline.get('is_main', False),
                    'sort': pipeline.get('sort', 0)
                }
                
                # Os status estão em _embedded.statuses, não em statuses diretamente
                statuses = pipeline.get('_embedded', {}).get('statuses', [])
                logger.info(f"Pipeline '{pipeline.get('name')}' tem {len(statuses)} status")
                
                for status in statuses:
                    status_id = status.get('id')
                    status_name = status.get('name', '').lower()
                    
                    self.status_cache[int(status_id)] = {
                        'name': status.get('name'),
                        'pipeline_id': int(pipeline_id),
                        'sort': status.get('sort', 0),
                        'is_editable': status.get('is_editable', True),
                        'color': status.get('color'),
                        'type': self.classify_status_for_conversion(status_name)
                    }
                    
                    # Identificar status de vitória e proposta usando a função corrigida
                    status_type = self.classify_status_for_conversion(status_name)
                    if status_type == 'won':
                        won_statuses.append(int(status_id))
                    elif status_type == 'proposal':
                        proposal_statuses.append(int(status_id))
            
            logger.info(f"Identificados {len(won_statuses)} status de vitória e {len(proposal_statuses)} de proposta")
            
            return {
                'pipelines': self.pipelines_cache,
                'statuses': self.status_cache,
                'won_statuses': won_statuses,
                'proposal_statuses': proposal_statuses
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair pipelines: {e}")
            raise

    def classify_status_for_conversion(self, status_name: str) -> str:
        """
        Classificar status para análise de conversão
        """
        status_lower = status_name.lower()
        
        if any(word in status_lower for word in ['ganho', 'fechado', 'won', 'vendido', 'sucesso', 'venda ganha']):
            return 'won'
        elif any(word in status_lower for word in ['perdido', 'lost', 'cancelado', 'rejeitado', 'venda perdida']):
            return 'lost'
        elif any(word in status_lower for word in ['proposta', 'proposal', 'orçamento', 'cotação', 'oferta feita']):
            return 'proposal'
        elif any(word in status_lower for word in ['negociação', 'negotiation', 'negociação']):
            return 'negotiation'
        elif any(word in status_lower for word in ['reunião', 'meeting', 'apresentação']):
            return 'meeting'
        elif any(word in status_lower for word in ['qualificado', 'qualified', 'interesse']):
            return 'qualified'
        elif any(word in status_lower for word in ['novo', 'lead', 'contato', 'leads de entrada']):
            return 'lead'
        else:
            return 'other'

    def extract_users(self) -> Dict:
        """
        Extrair dados dos usuários/vendedores
        """
        try:
            users_url = f"{self.kommo_config['base_url']}/api/v4/users"
            users_response = requests.get(users_url, headers=self.headers)
            users_response.raise_for_status()
            users_data = users_response.json()
            
            users = users_data.get('_embedded', {}).get('users', [])
            
            for user in users:
                user_id = user.get('id')
                self.users_cache[user_id] = {
                    'name': user.get('name'),
                    'email': user.get('email'),
                    'role': user.get('role', {}).get('name', 'Unknown'),
                    'is_active': user.get('is_active', True)
                }
            
            return self.users_cache
            
        except Exception as e:
            logger.error(f"Erro ao extrair usuários: {e}")
            raise

    def extract_closed_deals(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        EXTRACT - Extrair negócios fechados (ganhos e perdidos)
        """
        try:
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            logger.info(f"Extraindo negócios fechados de {start_date} até {end_date}")
            
            # Extrair leads fechados (ganhos e perdidos)
            leads_url = f"{self.kommo_config['base_url']}/api/v4/leads"
            
            # Buscar leads atualizados no período (para capturar fechamentos)
            leads_params = {
                'filter[updated_at][from]': start_timestamp,
                'filter[updated_at][to]': end_timestamp,
                'limit': 250,
                'with': 'contacts,custom_fields,loss_reason'
            }
            
            all_leads = []
            page = 1
            
            while True:
                leads_params['page'] = page
                leads_response = requests.get(leads_url, headers=self.headers, params=leads_params)
                leads_response.raise_for_status()
                leads_data = leads_response.json()
                
                leads = leads_data.get('_embedded', {}).get('leads', [])
                if not leads:
                    break
                
                all_leads.extend(leads)
                
                if len(leads) < 250:
                    break
                
                page += 1
                time.sleep(0.1)
            
            # Extrair histórico de mudanças de status para calcular ciclo de vendas
            events_url = f"{self.kommo_config['base_url']}/api/v4/events"
            events_params = {
                'filter[created_at][from]': start_timestamp - (30 * 24 * 3600),  # 30 dias antes para capturar ciclo completo
                'filter[created_at][to]': end_timestamp,
                'filter[type]': 'lead_status_changed',
                'limit': 250
            }
            
            all_status_changes = []
            page = 1
            
            while True:
                events_params['page'] = page
                events_response = requests.get(events_url, headers=self.headers, params=events_params)
                events_response.raise_for_status()
                events_data = events_response.json()
                
                events = events_data.get('_embedded', {}).get('events', [])
                if not events:
                    break
                
                all_status_changes.extend(events)
                
                if len(events) < 250:
                    break
                
                page += 1
                time.sleep(0.1)
            
            logger.info(f"Extraídos {len(all_leads)} leads e {len(all_status_changes)} mudanças de status")
            
            return {
                'leads': all_leads,
                'status_changes': all_status_changes
            }
            
        except Exception as e:
            logger.error(f"Erro na extração de conversões: {e}")
            raise

    def calculate_sales_cycle(self, lead: Dict, status_changes: List[Dict]) -> Optional[int]:
        """
        Calcular ciclo de vendas em dias (do primeiro contato ao fechamento)
        """
        try:
            lead_id = lead.get('id')
            current_status = lead.get('status_id')
            
            # Verificar se o lead está em status de fechamento (ganho ou perdido)
            if self.status_cache.get(current_status, {}).get('type') not in ['won', 'lost']:
                return None
            
            # Buscar mudanças relacionadas a este lead
            lead_changes = [
                change for change in status_changes
                if change.get('entity_id') == lead_id and change.get('entity_type') == 'lead'
            ]
            
            if not lead_changes:
                # Se não há histórico, usar data de criação até data de atualização
                created_date = datetime.fromtimestamp(lead.get('created_at', 0))
                updated_date = datetime.fromtimestamp(lead.get('updated_at', 0))
                cycle_days = (updated_date - created_date).days
                return max(cycle_days, 0)
            
            # Ordenar mudanças por data
            lead_changes.sort(key=lambda x: x.get('created_at', 0))
            
            # Data do primeiro contato (criação do lead ou primeira mudança)
            first_contact = datetime.fromtimestamp(lead.get('created_at', 0))
            
            # Data do fechamento (última mudança para status final)
            closing_date = None
            
            for change in reversed(lead_changes):
                # Verificar se value_after é uma lista ou dicionário
                value_after = change.get('value_after', {})
                
                # Se é lista, pegar o primeiro item
                if isinstance(value_after, list) and value_after:
                    value_after = value_after[0]
                
                # Se é dicionário, usar diretamente
                if isinstance(value_after, dict):
                    lead_status = value_after.get('lead_status', {})
                    if isinstance(lead_status, dict):
                        new_status_id = lead_status.get('id')
                        if self.status_cache.get(new_status_id, {}).get('type') in ['won', 'lost']:
                            closing_date = datetime.fromtimestamp(change.get('created_at', 0))
                            break
            
            if not closing_date:
                closing_date = datetime.fromtimestamp(lead.get('updated_at', 0))
            
            cycle_days = (closing_date - first_contact).days
            return max(cycle_days, 0)
            
        except Exception as e:
            logger.warning(f"Erro ao calcular ciclo de vendas para lead {lead.get('id')}: {e}")
            return None

    def identify_proposal_stage(self, lead: Dict, status_changes: List[Dict]) -> Optional[datetime]:
        """
        Identificar quando o lead chegou ao estágio de proposta
        """
        try:
            lead_id = lead.get('id')
            
            # Buscar mudanças para status de proposta
            lead_changes = [
                change for change in status_changes
                if change.get('entity_id') == lead_id
            ]
            
            lead_changes.sort(key=lambda x: x.get('created_at', 0))
            
            for change in lead_changes:
                # Verificar se value_after é uma lista ou dicionário
                value_after = change.get('value_after', {})
                
                # Se é lista, pegar o primeiro item
                if isinstance(value_after, list) and value_after:
                    value_after = value_after[0]
                
                # Se é dicionário, usar diretamente
                if isinstance(value_after, dict):
                    lead_status = value_after.get('lead_status', {})
                    if isinstance(lead_status, dict):
                        new_status_id = lead_status.get('id')
                        if self.status_cache.get(new_status_id, {}).get('type') == 'proposal':
                            return datetime.fromtimestamp(change.get('created_at', 0))
            
            # Se status atual é proposta, mas não encontrou histórico
            current_status = lead.get('status_id')
            if self.status_cache.get(current_status, {}).get('type') == 'proposal':
                return datetime.fromtimestamp(lead.get('created_at', 0))
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao identificar estágio de proposta: {e}")
            return None

    def extract_loss_reason(self, lead: Dict) -> str:
        """
        Extrair motivo de perda do lead
        """
        try:
            # Verificar se há loss_reason no lead
            loss_reason = lead.get('loss_reason')
            if loss_reason:
                return loss_reason.get('name', 'Não especificado')
            
            # Verificar em campos customizados
            custom_fields = lead.get('custom_fields_values', [])
            if custom_fields is None:
                custom_fields = []
            for field in custom_fields:
                field_name = field.get('field_name', '').lower()
                if 'motivo' in field_name or 'reason' in field_name or 'perda' in field_name:
                    values = field.get('values', [])
                    if values and len(values) > 0:
                        value = values[0].get('value')
                        if value:
                            return str(value)
            
            return 'Não especificado'
            
        except Exception as e:
            logger.warning(f"Erro ao extrair motivo de perda: {e}")
            return 'Erro'

    def transform_conversion_data(self, raw_data: Dict, pipeline_data: Dict) -> pd.DataFrame:
        """
        TRANSFORM - Processar dados de conversão e receita
        """
        try:
            leads = raw_data['leads']
            status_changes = raw_data['status_changes']
            won_statuses = pipeline_data['won_statuses']
            proposal_statuses = pipeline_data['proposal_statuses']
            
            conversion_records = []
            
            for lead in leads:
                try:
                    lead_id = lead.get('id')
                    current_status = lead.get('status_id')
                    status_type = self.status_cache.get(current_status, {}).get('type', 'other')
                    
                    # Dados básicos do lead
                    lead_value = float(lead.get('price', 0))
                    responsible_user = lead.get('responsible_user_id')
                    created_date = datetime.fromtimestamp(lead.get('created_at', 0))
                    updated_date = datetime.fromtimestamp(lead.get('updated_at', 0))
                    
                    # Calcular ciclo de vendas
                    sales_cycle_days = self.calculate_sales_cycle(lead, status_changes)
                    
                    # Identificar se passou por proposta
                    proposal_date = self.identify_proposal_stage(lead, status_changes)
                    
                    # Determinar se é uma conversão válida para análise
                    is_won = status_type == 'won'
                    is_lost = status_type == 'lost'
                    is_proposal = status_type == 'proposal' or proposal_date is not None
                    
                    # Extrair motivo de perda se aplicável
                    loss_reason = self.extract_loss_reason(lead) if is_lost else None
                    
                    # Calcular métricas de conversão
                    conversion_record = {
                        'lead_id': lead_id,
                        'pipeline_id': lead.get('pipeline_id'),
                        'status_id': current_status,
                        'status_name': self.status_cache.get(current_status, {}).get('name', 'Unknown'),
                        'status_type': status_type,
                        'responsible_user_id': responsible_user,
                        'responsible_user_name': self.users_cache.get(responsible_user, {}).get('name', 'Unknown'),
                        
                        # Datas importantes
                        'created_date': created_date.date(),
                        'created_datetime': created_date,
                        'updated_date': updated_date.date(),
                        'updated_datetime': updated_date,
                        'proposal_date': proposal_date.date() if proposal_date else None,
                        'proposal_datetime': proposal_date,
                        
                        # Métricas financeiras
                        'lead_value': lead_value,
                        'revenue_generated': lead_value if is_won else 0,
                        
                        # Métricas de conversão
                        'is_won': is_won,
                        'is_lost': is_lost,
                        'is_proposal': is_proposal,
                        'sales_cycle_days': sales_cycle_days,
                        'loss_reason': loss_reason,
                        
                        # Classificações para Win Rate
                        'had_proposal': is_proposal,
                        'won_from_proposal': is_won and is_proposal,
                        
                        # Metadados
                        'contact_count': len(lead.get('_embedded', {}).get('contacts', [])),
                        'updated_at': datetime.now()
                    }
                    
                    conversion_records.append(conversion_record)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar lead {lead.get('id')}: {e}")
                    continue
            
            df = pd.DataFrame(conversion_records)
            logger.info(f"Processados {len(df)} registros de conversão")
            
            # Log estatísticas básicas
            if not df.empty:
                total_won = df['is_won'].sum()
                total_lost = df['is_lost'].sum()
                
                
                total_proposals = df['is_proposal'].sum()
                total_revenue = df['revenue_generated'].sum()
                
                logger.info(f"Resumo: {total_won} ganhos, {total_lost} perdidos, {total_proposals} propostas")
                logger.info(f"Receita total: R$ {total_revenue:,.2f}")
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na transformação: {e}")
            raise

    def load_conversion_data(self, df: pd.DataFrame):
        """
        LOAD - Carregar dados de conversão no banco
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de conversões
            create_table_query = """
            CREATE TABLE IF NOT EXISTS sales_conversions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id BIGINT UNIQUE,
                pipeline_id BIGINT,
                status_id BIGINT,
                status_name VARCHAR(255),
                status_type VARCHAR(50),
                responsible_user_id BIGINT,
                responsible_user_name VARCHAR(255),
                
                created_date DATE,
                created_datetime DATETIME,
                updated_date DATE,
                updated_datetime DATETIME,
                proposal_date DATE,
                proposal_datetime DATETIME,
                
                lead_value DECIMAL(12,2),
                revenue_generated DECIMAL(12,2),
                
                is_won BOOLEAN,
                is_lost BOOLEAN,
                is_proposal BOOLEAN,
                sales_cycle_days INT,
                loss_reason VARCHAR(500),
                
                had_proposal BOOLEAN,
                won_from_proposal BOOLEAN,
                
                contact_count INT,
                updated_at DATETIME,
                
                INDEX idx_lead_id (lead_id),
                INDEX idx_responsible_user (responsible_user_id),
                INDEX idx_created_date (created_date),
                INDEX idx_updated_date (updated_date),
                INDEX idx_status_type (status_type),
                INDEX idx_is_won (is_won),
                INDEX idx_pipeline_id (pipeline_id)
            )
            """
            cursor.execute(create_table_query)
            
            # Inserir dados
            insert_query = """
            INSERT INTO sales_conversions (
                lead_id, pipeline_id, status_id, status_name, status_type,
                responsible_user_id, responsible_user_name, created_date, created_datetime,
                updated_date, updated_datetime, proposal_date, proposal_datetime,
                lead_value, revenue_generated, is_won, is_lost, is_proposal,
                sales_cycle_days, loss_reason, had_proposal, won_from_proposal,
                contact_count, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status_id = VALUES(status_id),
                status_name = VALUES(status_name),
                status_type = VALUES(status_type),
                updated_date = VALUES(updated_date),
                updated_datetime = VALUES(updated_datetime),
                lead_value = VALUES(lead_value),
                revenue_generated = VALUES(revenue_generated),
                is_won = VALUES(is_won),
                is_lost = VALUES(is_lost),
                sales_cycle_days = VALUES(sales_cycle_days),
                loss_reason = VALUES(loss_reason),
                updated_at = VALUES(updated_at)
            """
            
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    int(row['lead_id']),
                    int(row['pipeline_id']) if pd.notna(row['pipeline_id']) else None,
                    int(row['status_id']) if pd.notna(row['status_id']) else None,
                    row['status_name'],
                    row['status_type'],
                    int(row['responsible_user_id']) if pd.notna(row['responsible_user_id']) else None,
                    row['responsible_user_name'],
                    row['created_date'],
                    row['created_datetime'],
                    row['updated_date'],
                    row['updated_datetime'],
                    row['proposal_date'] if pd.notna(row['proposal_date']) else None,
                    row['proposal_datetime'] if pd.notna(row['proposal_datetime']) else None,
                    float(row['lead_value']) if pd.notna(row['lead_value']) else 0,
                    float(row['revenue_generated']) if pd.notna(row['revenue_generated']) else 0,
                    bool(row['is_won']),
                    bool(row['is_lost']),
                    bool(row['is_proposal']),
                    int(row['sales_cycle_days']) if pd.notna(row['sales_cycle_days']) else None,
                    row['loss_reason'] if pd.notna(row['loss_reason']) else None,
                    bool(row['had_proposal']),
                    bool(row['won_from_proposal']),
                    int(row['contact_count']) if pd.notna(row['contact_count']) else 0,
                    row['updated_at']
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            connection.commit()
            
            logger.info(f"Carregados {len(data_to_insert)} registros de conversão")
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados de conversão: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_conversion_metrics(self, date: datetime):
        """
        Gerar métricas consolidadas de conversão e receita
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de métricas de conversão
            create_metrics_table = """
            CREATE TABLE IF NOT EXISTS conversion_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE,
                responsible_user_id BIGINT,
                responsible_user_name VARCHAR(255),
                pipeline_id BIGINT,
                
                total_deals INT,
                deals_won INT,
                deals_lost INT,
                proposals_sent INT,
                
                revenue_generated DECIMAL(15,2),
                avg_deal_value DECIMAL(12,2),
                avg_won_deal_value DECIMAL(12,2),
                
                win_rate DECIMAL(5,2),
                proposal_win_rate DECIMAL(5,2),
                avg_sales_cycle_days DECIMAL(8,2),
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY unique_date_user_pipeline (metric_date, responsible_user_id, pipeline_id),
                INDEX idx_metric_date (metric_date),
                INDEX idx_user_id (responsible_user_id),
                INDEX idx_pipeline_id (pipeline_id)
            )
            """
            cursor.execute(create_metrics_table)
            
            date_str = date.strftime('%Y-%m-%d')
            
            # Calcular métricas por usuário e pipeline
            cursor.execute("""
                SELECT 
                    responsible_user_id,
                    responsible_user_name,
                    pipeline_id,
                    COUNT(*) as total_deals,
                    SUM(CASE WHEN is_won = 1 THEN 1 ELSE 0 END) as deals_won,
                    SUM(CASE WHEN is_lost = 1 THEN 1 ELSE 0 END) as deals_lost,
                    SUM(CASE WHEN had_proposal = 1 THEN 1 ELSE 0 END) as proposals_sent,
                    SUM(revenue_generated) as revenue_generated,
                    AVG(lead_value) as avg_deal_value,
                    AVG(CASE WHEN is_won = 1 THEN lead_value ELSE NULL END) as avg_won_deal_value,
                    AVG(CASE WHEN sales_cycle_days IS NOT NULL THEN sales_cycle_days ELSE NULL END) as avg_cycle,
                    SUM(CASE WHEN won_from_proposal = 1 THEN 1 ELSE 0 END) as won_from_proposals
                FROM sales_conversions 
                WHERE updated_date = %s
                AND responsible_user_id IS NOT NULL
                GROUP BY responsible_user_id, responsible_user_name, pipeline_id
            """, (date_str,))
            
            results = cursor.fetchall()
            
            # Inserir métricas
            insert_metrics_query = """
            INSERT INTO conversion_metrics (
                metric_date, responsible_user_id, responsible_user_name, pipeline_id,
                total_deals, deals_won, deals_lost, proposals_sent, revenue_generated,
                avg_deal_value, avg_won_deal_value, win_rate, proposal_win_rate,
                avg_sales_cycle_days
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_deals = VALUES(total_deals),
                deals_won = VALUES(deals_won),
                deals_lost = VALUES(deals_lost),
                proposals_sent = VALUES(proposals_sent),
                revenue_generated = VALUES(revenue_generated),
                avg_deal_value = VALUES(avg_deal_value),
                avg_won_deal_value = VALUES(avg_won_deal_value),
                win_rate = VALUES(win_rate),
                proposal_win_rate = VALUES(proposal_win_rate),
                avg_sales_cycle_days = VALUES(avg_sales_cycle_days)
            """
            
            for result in results:
                (user_id, user_name, pipeline_id, total_deals, deals_won, deals_lost, 
                 proposals_sent, revenue, avg_deal_value, avg_won_value, avg_cycle, won_from_proposals) = result
                
                # Calcular taxas
                win_rate = (deals_won / total_deals * 100) if total_deals > 0 else 0
                proposal_win_rate = (won_from_proposals / proposals_sent * 100) if proposals_sent > 0 else 0
                
                cursor.execute(insert_metrics_query, (
                    date_str,
                    user_id,
                    user_name,
                    pipeline_id,
                    total_deals,
                    deals_won,
                    deals_lost,
                    proposals_sent,
                    round(revenue or 0, 2),
                    round(avg_deal_value or 0, 2),
                    round(avg_won_value or 0, 2),
                    round(win_rate, 2),
                    round(proposal_win_rate, 2),
                    round(avg_cycle or 0, 2)
                ))
            
            connection.commit()
            
            logger.info(f"Métricas de conversão geradas para {date_str}")
            
            # Gerar também métricas consolidadas do time
            self.generate_team_conversion_summary(date_str, cursor, connection)
            
        except Exception as e:
            logger.error(f"Erro ao gerar métricas de conversão: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_team_conversion_summary(self, date_str: str, cursor, connection):
        """
        Gerar resumo consolidado de conversão do time
        """
        try:
            # Criar tabela de resumo do time
            create_team_table = """
            CREATE TABLE IF NOT EXISTS team_conversion_summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE UNIQUE,
                total_deals INT,
                total_won INT,
                total_lost INT,
                total_proposals INT,
                total_revenue DECIMAL(15,2),
                avg_deal_value DECIMAL(12,2),
                team_win_rate DECIMAL(5,2),
                team_proposal_win_rate DECIMAL(5,2),
                avg_sales_cycle DECIMAL(8,2),
                top_performer_user_id BIGINT,
                top_performer_revenue DECIMAL(15,2),
                active_closers_count INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_metric_date (metric_date)
            )
            """
            cursor.execute(create_team_table)
            
            # Calcular métricas consolidadas do time
            cursor.execute("""
                SELECT 
                    SUM(total_deals) as team_deals,
                    SUM(deals_won) as team_won,
                    SUM(deals_lost) as team_lost,
                    SUM(proposals_sent) as team_proposals,
                    SUM(revenue_generated) as team_revenue,
                    AVG(avg_deal_value) as team_avg_deal,
                    AVG(avg_sales_cycle_days) as team_avg_cycle,
                    COUNT(*) as active_closers
                FROM conversion_metrics 
                WHERE metric_date = %s
            """, (date_str,))
            
            team_result = cursor.fetchone()
            
            if team_result and team_result[0]:
                (team_deals, team_won, team_lost, team_proposals, team_revenue, 
                 team_avg_deal, team_avg_cycle, active_closers) = team_result
                
                # Calcular taxas do time
                team_win_rate = (team_won / team_deals * 100) if team_deals > 0 else 0
                team_proposal_win_rate = (team_won / team_proposals * 100) if team_proposals > 0 else 0
                
                # Encontrar top performer por receita
                cursor.execute("""
                    SELECT responsible_user_id, SUM(revenue_generated) as total_revenue
                    FROM conversion_metrics 
                    WHERE metric_date = %s 
                    GROUP BY responsible_user_id
                    ORDER BY total_revenue DESC 
                    LIMIT 1
                """, (date_str,))
                
                top_performer = cursor.fetchone()
                top_performer_id = top_performer[0] if top_performer else None
                top_performer_revenue = top_performer[1] if top_performer else 0
                
                # Inserir resumo do time
                insert_team_query = """
                INSERT INTO team_conversion_summary (
                    metric_date, total_deals, total_won, total_lost, total_proposals,
                    total_revenue, avg_deal_value, team_win_rate, team_proposal_win_rate,
                    avg_sales_cycle, top_performer_user_id, top_performer_revenue, active_closers_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_deals = VALUES(total_deals),
                    total_won = VALUES(total_won),
                    total_lost = VALUES(total_lost),
                    total_proposals = VALUES(total_proposals),
                    total_revenue = VALUES(total_revenue),
                    avg_deal_value = VALUES(avg_deal_value),
                    team_win_rate = VALUES(team_win_rate),
                    team_proposal_win_rate = VALUES(team_proposal_win_rate),
                    avg_sales_cycle = VALUES(avg_sales_cycle),
                    top_performer_user_id = VALUES(top_performer_user_id),
                    top_performer_revenue = VALUES(top_performer_revenue),
                    active_closers_count = VALUES(active_closers_count)
                """
                
                cursor.execute(insert_team_query, (
                    date_str,
                    int(team_deals or 0),
                    int(team_won or 0),
                    int(team_lost or 0),
                    int(team_proposals or 0),
                    round(team_revenue or 0, 2),
                    round(team_avg_deal or 0, 2),
                    round(team_win_rate, 2),
                    round(team_proposal_win_rate, 2),
                    round(team_avg_cycle or 0, 2),
                    top_performer_id,
                    round(top_performer_revenue or 0, 2),
                    int(active_closers or 0)
                ))
                
                connection.commit()
                
                logger.info("=== RESUMO CONVERSÃO DO TIME ===")
                logger.info(f"Negócios: {team_deals} total, {team_won} ganhos ({team_win_rate:.1f}%)")
                logger.info(f"Receita: R$ {team_revenue:,.2f}")
                logger.info(f"Ticket médio: R$ {team_avg_deal:,.2f}")
                logger.info(f"Ciclo médio: {team_avg_cycle:.1f} dias")
                
        except Exception as e:
            logger.error(f"Erro ao gerar resumo do time: {e}")

    def generate_loss_analysis(self, date: datetime):
        """
        Gerar análise detalhada de perdas
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de análise de perdas
            create_loss_table = """
            CREATE TABLE IF NOT EXISTS loss_analysis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE,
                loss_reason VARCHAR(500),
                count_losses INT,
                total_value_lost DECIMAL(15,2),
                avg_cycle_to_loss DECIMAL(8,2),
                most_common_stage VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_date_reason (metric_date, loss_reason),
                INDEX idx_metric_date (metric_date)
            )
            """
            cursor.execute(create_loss_table)
            
            date_str = date.strftime('%Y-%m-%d')
            
            # Analisar perdas por motivo
            cursor.execute("""
                SELECT 
                    COALESCE(loss_reason, 'Não especificado') as reason,
                    COUNT(*) as count_losses,
                    SUM(lead_value) as total_value_lost,
                    AVG(sales_cycle_days) as avg_cycle,
                    status_name as common_stage
                FROM sales_conversions 
                WHERE updated_date = %s AND is_lost = 1
                GROUP BY loss_reason, status_name
                ORDER BY count_losses DESC
            """, (date_str,))
            
            loss_results = cursor.fetchall()
            
            # Inserir análise de perdas
            insert_loss_query = """
            INSERT INTO loss_analysis (
                metric_date, loss_reason, count_losses, total_value_lost,
                avg_cycle_to_loss, most_common_stage
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                count_losses = VALUES(count_losses),
                total_value_lost = VALUES(total_value_lost),
                avg_cycle_to_loss = VALUES(avg_cycle_to_loss),
                most_common_stage = VALUES(most_common_stage)
            """
            
            for reason, count_losses, value_lost, avg_cycle, common_stage in loss_results:
                cursor.execute(insert_loss_query, (
                    date_str,
                    reason,
                    count_losses,
                    round(value_lost or 0, 2),
                    round(avg_cycle or 0, 2),
                    common_stage
                ))
            
            connection.commit()
            
            if loss_results:
                logger.info("=== ANÁLISE DE PERDAS ===")
                for reason, count_losses, value_lost, avg_cycle, stage in loss_results[:5]:
                    logger.info(f"{reason}: {count_losses} perdas, R$ {value_lost:,.2f}, {avg_cycle:.1f} dias")
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise de perdas: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def run_etl(self, start_date: datetime = None, end_date: datetime = None):
        """
        Executar ETL completo de conversão e receita
        """
        try:
            # Definir período padrão (últimos 30 dias para capturar ciclos completos)
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if not end_date:
                end_date = datetime.now().replace(hour=23, minute=59, second=59)
            
            logger.info("=== INICIANDO ETL CONVERSÃO KOMMO ===")
            
            # 1. Extrair estrutura de pipelines
            logger.info("1. Extraindo pipelines e status...")
            pipeline_data = self.extract_pipelines_and_statuses()
            
            # 2. Extrair usuários
            logger.info("2. Extraindo usuários...")
            self.extract_users()
            
            # 3. Extrair negócios fechados
            logger.info("3. Extraindo negócios fechados...")
            raw_data = self.extract_closed_deals(start_date, end_date)
            
            if not raw_data['leads']:
                logger.info("Nenhum negócio encontrado para o período")
                return
            
            # 4. Transformar dados
            logger.info("4. Transformando dados de conversão...")
            df_conversions = self.transform_conversion_data(raw_data, pipeline_data)
            
            if df_conversions.empty:
                logger.info("Nenhum dado de conversão para processar")
                return
            
            # 5. Carregar dados
            logger.info("5. Carregando dados de conversão...")
            self.load_conversion_data(df_conversions)
            
            # 6. Gerar métricas para cada dia do período
            logger.info("6. Gerando métricas de conversão...")
            current_date = start_date
            while current_date <= end_date:
                self.generate_conversion_metrics(current_date)
                current_date += timedelta(days=1)
            
            # 7. Gerar análise de perdas
            logger.info("7. Gerando análise de perdas...")
            self.generate_loss_analysis(end_date)
            
            logger.info("=== ETL CONVERSÃO CONCLUÍDO ===")
            
        except Exception as e:
            logger.error(f"Erro no ETL de conversão: {e}")
            raise


# Script principal
if __name__ == "__main__":
    etl = KommoConversionETL()
    
    # Executar para últimos 30 dias
    etl.run_etl()
    
    # Ou para período específico
    # start = datetime(2025, 1, 1)
    # end = datetime(2025, 1, 31)
    # etl.run_etl(start, end)