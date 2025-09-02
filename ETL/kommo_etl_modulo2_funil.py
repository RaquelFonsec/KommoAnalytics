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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class KommoFunnelETL:
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
        
        # ID do pipeline principal identificado
        self.main_pipeline_id = 11146887
        
        # Cache para pipelines e status
        self.pipelines_cache = {}
        self.status_cache = {}

    def extract_pipelines_and_statuses(self) -> Dict:
        """
        Extrair estrutura de pipelines e status do Kommo - foco no pipeline principal
        """
        try:
            logger.info("Extraindo estrutura do pipeline principal...")
            
            # Buscar pipeline principal específico
            pipeline_url = f"{self.kommo_config['base_url']}/api/v4/leads/pipelines/{self.main_pipeline_id}"
            pipeline_response = requests.get(pipeline_url, headers=self.headers)
            pipeline_response.raise_for_status()
            pipeline_data = pipeline_response.json()
            
            # Processar pipeline principal
            self.pipelines_cache[self.main_pipeline_id] = {
                'name': pipeline_data.get('name', 'Funil de vendas'),
                'is_main': pipeline_data.get('is_main', True),
                'sort': pipeline_data.get('sort', 1)
            }
            
            # Buscar status do pipeline principal
            statuses_url = f"{self.kommo_config['base_url']}/api/v4/leads/pipelines/{self.main_pipeline_id}/statuses"
            statuses_response = requests.get(statuses_url, headers=self.headers)
            statuses_response.raise_for_status()
            statuses_data = statuses_response.json()
            
            statuses = statuses_data.get('_embedded', {}).get('statuses', [])
            
            for status in statuses:
                status_id = status.get('id')
                status_name = status.get('name')
                
                self.status_cache[int(status_id)] = {
                    'name': status_name,
                    'pipeline_id': self.main_pipeline_id,
                    'pipeline_name': 'Funil de vendas',
                    'sort': status.get('sort', 0),
                    'is_editable': status.get('is_editable', True),
                    'color': status.get('color'),
                    'type': self.classify_status_type(status_name)
                }
            
            logger.info(f"Pipeline principal carregado com {len(statuses)} status")
            
            # Log dos status encontrados para verificação
            logger.info("Status do pipeline principal:")
            for status_id, status_info in sorted(self.status_cache.items(), key=lambda x: x[1]['sort']):
                logger.info(f"  {status_id}: {status_info['name']} -> {status_info['type']}")
            
            return {'pipelines': self.pipelines_cache, 'statuses': self.status_cache}
            
        except Exception as e:
            logger.error(f"Erro ao extrair pipeline principal: {e}")
            raise

    def classify_status_type(self, status_name: str) -> str:
        """
        Classificar tipo do status baseado nos status reais do pipeline principal
        """
        if not status_name:
            return 'other'
        
        # Mapeamento baseado nos status reais encontrados na exploração
        status_mapping = {
            'Incoming leads': 'lead',
            'Interessados': 'qualified', 
            'Abordados': 'qualified',
            'Qualificação': 'qualified',
            'Qualificado para reunião': 'qualified',
            'Apresentação': 'meeting',
            'No Show': 'meeting_failed',
            'FUP': 'proposal',
            'Negociação': 'negotiation',
            'Venda ganha': 'won',
            'Venda perdida': 'lost'
        }
        
        # Verificar mapeamento direto primeiro
        if status_name in status_mapping:
            return status_mapping[status_name]
        
        # Fallback para classificação por palavras-chave
        status_lower = status_name.lower()
        
        if any(word in status_lower for word in ['incoming', 'novo', 'lead', 'entrada']):
            return 'lead'
        elif any(word in status_lower for word in ['interessado', 'abordo', 'qualific']):
            return 'qualified'
        elif any(word in status_lower for word in ['apresenta', 'reunião', 'meeting', 'show']):
            return 'meeting'
        elif any(word in status_lower for word in ['fup', 'follow', 'proposta']):
            return 'proposal'
        elif any(word in status_lower for word in ['negoci']):
            return 'negotiation'
        elif any(word in status_lower for word in ['ganho', 'ganha', 'won', 'fechado']):
            return 'won'
        elif any(word in status_lower for word in ['perdido', 'perdida', 'lost']):
            return 'lost'
        
            return 'other'

    def extract_leads_history(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        EXTRACT - Extrair histórico de leads do pipeline principal
        """
        try:
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            logger.info(f"Extraindo histórico do pipeline principal ({self.main_pipeline_id})")
            logger.info(f"Período: {start_date.strftime('%Y-%m-%d')} até {end_date.strftime('%Y-%m-%d')}")
            
            # 1. Buscar leads do pipeline principal
            leads_url = f"{self.kommo_config['base_url']}/api/v4/leads"
            leads_params = {
                'filter[pipeline_id]': self.main_pipeline_id,
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'limit': 250,
                'with': 'contacts,custom_fields'
            }
            
            all_leads = []
            page = 1
            
            while True:
                leads_params['page'] = page
                leads_response = requests.get(leads_url, headers=self.headers, params=leads_params)
                
                if leads_response.status_code == 200:
                    leads_data = leads_response.json()
                    leads = leads_data.get('_embedded', {}).get('leads', [])
                    
                    if not leads:
                        break
                        
                    all_leads.extend(leads)
                    logger.info(f"Página {page}: {len(leads)} leads do pipeline principal")
                    
                    if len(leads) < 250:
                        break
                        
                    page += 1
                    time.sleep(0.5)
                else:
                    logger.warning(f"Erro na página {page} de leads: {leads_response.status_code}")
                    break
            
            # 2. Buscar também leads atualizados no período (mesmo que criados antes)
            logger.info("Buscando leads atualizados no período...")
            
            updated_leads_params = {
                'filter[pipeline_id]': self.main_pipeline_id,
                'filter[updated_at][from]': start_timestamp,
                'filter[updated_at][to]': end_timestamp,
                'limit': 250,
                'with': 'contacts,custom_fields'
            }
            
            page = 1
            while True:
                updated_leads_params['page'] = page
                updated_response = requests.get(leads_url, headers=self.headers, params=updated_leads_params)
                
                if updated_response.status_code == 200:
                    updated_data = updated_response.json()
                    updated_leads = updated_data.get('_embedded', {}).get('leads', [])
                    
                    if not updated_leads:
                        break
                    
                    # Evitar duplicatas
                    existing_ids = {lead['id'] for lead in all_leads}
                    new_leads = [lead for lead in updated_leads if lead['id'] not in existing_ids]
                    all_leads.extend(new_leads)
                    
                    logger.info(f"Página {page} (atualizados): {len(new_leads)} novos leads")
                    
                    if len(updated_leads) < 250:
                        break
                        
                    page += 1
                    time.sleep(0.5)
                else:
                    break
            
            # 3. Buscar eventos de mudança de status para estes leads (OTIMIZADO)
            logger.info("Buscando eventos de mudança de status...")
            
            lead_ids = [lead['id'] for lead in all_leads]
            all_events = []
            
            # Buscar eventos de forma mais eficiente
            events_url = f"{self.kommo_config['base_url']}/api/v4/events"
            events_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'filter[type]': 'lead_status_changed',
                'limit': 250
            }
            
            page = 1
            total_events = 0
            
            while True:
                events_params['page'] = page
                events_response = requests.get(events_url, headers=self.headers, params=events_params)
                
                if events_response.status_code == 200:
                    events_data = events_response.json()
                    events = events_data.get('_embedded', {}).get('events', [])
                    
                    if not events:
                        break
                        
                    # Filtrar eventos apenas dos leads do pipeline principal
                    pipeline_events = [
                        event for event in events 
                        if event.get('entity_id') in lead_ids
                    ]
                    
                    all_events.extend(pipeline_events)
                    total_events += len(pipeline_events)
                    
                    logger.info(f"Página {page} de eventos: {len(pipeline_events)} eventos do pipeline principal")
                    
                    if len(events) < 250:
                        break
                        
                    page += 1
                    time.sleep(0.2)  # Reduzido delay
                else:
                    logger.warning(f"Erro na página {page} de eventos: {events_response.status_code}")
                    break
            
            # 4. Buscar motivos de perda
            logger.info("Extraindo motivos de perda...")
            lost_reasons = self.extract_loss_reasons(start_date, end_date, lead_ids)
            
            logger.info(f"Extraídos: {len(all_leads)} leads, {len(all_events)} eventos, {len(lost_reasons)} motivos de perda")
            
            return {
                'leads': all_leads,
                'status_changes': all_events,
                'loss_reasons': lost_reasons
            }
            
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            raise

    def get_loss_reasons_mapping(self):
        """
        Buscar mapeamento de IDs para nomes dos motivos de perda
        """
        try:
            logger.info("Buscando mapeamento de motivos de perda...")
            
            url = f"{self.kommo_config['base_url']}/api/v4/leads/loss_reasons"
            params = {'limit': 250}
            
            loss_reasons_mapping = {}
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
                            loss_reasons_mapping[reason_id] = reason_name
                    
                    if len(reasons) < 250:
                        break
                        
                    page += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao buscar motivos de perda na página {page}: {e}")
                    break
            
            logger.info(f"Mapeamento de motivos de perda carregado: {len(loss_reasons_mapping)} motivos")
            return loss_reasons_mapping
            
        except Exception as e:
            logger.error(f"Erro ao buscar mapeamento de motivos de perda: {e}")
            return {}

    def extract_loss_reasons(self, start_date: datetime, end_date: datetime, lead_ids: List[int]) -> Dict:
        """
        Extrair motivos de perda dos leads do pipeline principal
        """
        try:
            logger.info("Buscando motivos de perda na API do Kommo...")
            
            # Buscar mapeamento de motivos de perda
            loss_reasons_mapping = self.get_loss_reasons_mapping()
            
            # Identificar status de "perdido" do pipeline principal
            lost_status_ids = [
                status_id for status_id, status in self.status_cache.items()
                if status['type'] == 'lost' and status['pipeline_id'] == self.main_pipeline_id
            ]
            
            logger.info(f"Status de perda identificados: {lost_status_ids}")
            
            loss_reasons = {}
            
            if lost_status_ids and lead_ids:
                # Buscar todos os leads perdidos de uma vez
                leads_url = f"{self.kommo_config['base_url']}/api/v4/leads"
                params = {
                    'filter[pipeline_id]': self.main_pipeline_id,
                    'filter[statuses]': lost_status_ids,  # Todos os status de perda
                    'limit': 250,
                    'with': 'loss_reason'  # Incluir motivos de perda
                }
                
                page = 1
                total_lost_leads = 0
                
                while True:
                    params['page'] = page
                    try:
                        response = requests.get(leads_url, headers=self.headers, params=params)
                        response.raise_for_status()
                        
                        data = response.json()
                        leads = data.get('_embedded', {}).get('leads', [])
                        
                        if not leads:
                            break
                        
                        for lead in leads:
                            if lead['id'] in lead_ids:  # Apenas leads que estamos processando
                                lead_id = lead.get('id')
                                loss_reason_id = lead.get('loss_reason_id')
                                loss_reason_name = lead.get('loss_reason_name')
                                
                                # Usar mapeamento para obter nome real do motivo
                                if loss_reason_id and loss_reason_id in loss_reasons_mapping:
                                    loss_reason_name = loss_reasons_mapping[loss_reason_id]
                                elif not loss_reason_name or loss_reason_name.strip() == '':
                                    if loss_reason_id:
                                        loss_reason_name = f"Motivo ID {loss_reason_id}"
                                    else:
                                        loss_reason_name = None  # Deixar NULL no banco
                                
                                loss_reasons[lead_id] = {
                                    'reason_id': loss_reason_id,
                                    'reason_name': loss_reason_name,
                                    'status_id': lead.get('status_id')
                                }
                                total_lost_leads += 1
                        
                        logger.info(f"Página {page}: {len(leads)} leads perdidos processados")
                        
                        if len(leads) < 250:
                            break
                            
                        page += 1
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.warning(f"Erro ao buscar leads perdidos na página {page}: {e}")
                        break
                
                logger.info(f"Total de leads perdidos com motivos: {total_lost_leads}")
                
                # Log de amostra dos motivos encontrados
                if loss_reasons:
                    sample_reasons = list(loss_reasons.values())[:5]
                    logger.info("Amostra de motivos de perda encontrados:")
                    for reason in sample_reasons:
                        logger.info(f"  Lead: reason_id={reason['reason_id']}, reason_name='{reason['reason_name']}'")
            
            return loss_reasons
            
        except Exception as e:
            logger.error(f"Erro ao extrair motivos de perda: {e}")
            return {}

    def transform_funnel_data(self, raw_data: Dict) -> pd.DataFrame:
        """
        TRANSFORM - Processar dados do funil do pipeline principal
        """
        try:
            leads = raw_data['leads']
            status_changes = raw_data['status_changes']
            loss_reasons = raw_data['loss_reasons']
            
            logger.info(f"Transformando {len(leads)} leads do pipeline principal...")
            
            # Criar mapeamento de mudanças por lead
            status_changes_by_lead = {}
            for event in status_changes:
                lead_id = event.get('entity_id')
                if lead_id not in status_changes_by_lead:
                    status_changes_by_lead[lead_id] = []
                status_changes_by_lead[lead_id].append(event)
            
            # Processar cada lead
            funnel_records = []
            
            for i, lead in enumerate(leads):
                try:
                    if i % 50 == 0:
                        logger.info(f"Processando lead {i+1}/{len(leads)}")
                    
                    lead_id = lead.get('id')
                    lead_changes = status_changes_by_lead.get(lead_id, [])
                    lead_loss_reason = loss_reasons.get(lead_id, {})
                    
                    # Ordenar mudanças por data
                    lead_changes.sort(key=lambda x: x.get('created_at', 0))
                    
                    # Calcular métricas do funil para este lead
                    funnel_data = self.calculate_lead_funnel_metrics(lead, lead_changes, lead_loss_reason)
                    funnel_records.extend(funnel_data)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar lead {lead.get('id')}: {e}")
                    continue
            
            df = pd.DataFrame(funnel_records)
            logger.info(f"Processados {len(df)} registros de funil do pipeline principal")
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na transformação: {e}")
            raise

    def calculate_lead_funnel_metrics(self, lead: Dict, status_changes: List[Dict], loss_reason: Dict) -> List[Dict]:
        """
        Calcular métricas de funil para um lead específico do pipeline principal
        """
        records = []
        
        try:
            lead_id = lead.get('id')
            current_status_id = lead.get('status_id')
            pipeline_id = lead.get('pipeline_id')
            lead_created = datetime.fromtimestamp(lead.get('created_at', 0))
            
            # Verificar se é do pipeline principal
            if pipeline_id != self.main_pipeline_id:
                return []
            
            # Se não há mudanças de status, criar registro para status atual
            if not status_changes:
                status_info = self.status_cache.get(current_status_id, {})
                
                return [{
                    'lead_id': lead_id,
                    'pipeline_id': self.main_pipeline_id,
                    'pipeline_name': 'Funil de vendas',
                    'status_id': current_status_id,
                    'status_name': status_info.get('name', 'Unknown'),
                    'status_type': status_info.get('type', 'other'),
                    'status_sort': status_info.get('sort', 0),
                    'entry_date': lead_created,
                    'exit_date': None,
                    'time_in_status_hours': self.calculate_hours_since(lead_created),
                    'is_current_status': True,
                    'conversion_type': None,
                    'next_status_type': None,
                    'lead_value': float(lead.get('price', 0)),
                    'responsible_user_id': lead.get('responsible_user_id'),
                    'loss_reason_id': loss_reason.get('reason_id'),
                    'loss_reason_name': loss_reason.get('reason_name'),
                    'created_at': datetime.now()
                }]
            
            # Processar histórico de mudanças
            for i, change in enumerate(status_changes):
                try:
                    change_date = datetime.fromtimestamp(change.get('created_at', 0))
                    
                    # Extrair status da mudança
                    value_after = change.get('value_after', {})
                    
                    if isinstance(value_after, list) and value_after:
                        value_after = value_after[0]
                    
                    new_status_id = None
                    if isinstance(value_after, dict):
                        new_status_id = value_after.get('lead_status', {}).get('id')
                    
                    # Processar status se válido e do pipeline principal
                    if new_status_id and new_status_id in self.status_cache:
                        status_info = self.status_cache[new_status_id]
                        
                        # Verificar se é do pipeline principal
                        if status_info.get('pipeline_id') != self.main_pipeline_id:
                            continue
                        
                        next_status_info = None
                        
                        # Determinar próximo status (se houver)
                        if i < len(status_changes) - 1:
                            next_change = status_changes[i + 1]
                            next_value_after = next_change.get('value_after', {})
                            if isinstance(next_value_after, list) and next_value_after:
                                next_value_after = next_value_after[0]
                            if isinstance(next_value_after, dict):
                                next_status_id = next_value_after.get('lead_status', {}).get('id')
                                if next_status_id in self.status_cache:
                                    next_status_info = self.status_cache[next_status_id]
                        
                        # Calcular tempo no status
                        if i < len(status_changes) - 1:
                            next_change_date = datetime.fromtimestamp(status_changes[i + 1].get('created_at', 0))
                            time_in_status = (next_change_date - change_date).total_seconds() / 3600
                            exit_date = next_change_date
                            is_current = False
                        else:
                            # Último status - calcular tempo até agora
                            time_in_status = self.calculate_hours_since(change_date)
                            exit_date = None
                            is_current = True
                        
                        # Determinar tipo de conversão
                        conversion_type = None
                        next_status_type = None
                        
                        if next_status_info:
                            next_status_type = next_status_info.get('type')
                            conversion_type = self.determine_conversion_type(
                                status_info.get('type'),
                                next_status_type
                            )
                        elif status_info.get('type') == 'lost':
                            conversion_type = 'lost'
                        elif status_info.get('type') == 'won':
                            conversion_type = 'won'
                        
                        records.append({
                            'lead_id': lead_id,
                            'pipeline_id': self.main_pipeline_id,
                            'pipeline_name': 'Funil de vendas',
                            'status_id': new_status_id,
                            'status_name': status_info.get('name', 'Unknown'),
                            'status_type': status_info.get('type', 'other'),
                            'status_sort': status_info.get('sort', 0),
                            'entry_date': change_date,
                            'exit_date': exit_date,
                            'time_in_status_hours': round(time_in_status, 2),
                            'is_current_status': is_current,
                            'conversion_type': conversion_type,
                            'next_status_type': next_status_type,
                            'lead_value': float(lead.get('price', 0)),
                            'responsible_user_id': lead.get('responsible_user_id'),
                            'loss_reason_id': loss_reason.get('reason_id') if status_info.get('type') == 'lost' else None,
                            'loss_reason_name': loss_reason.get('reason_name') if status_info.get('type') == 'lost' else None,
                            'created_at': datetime.now()
                        })
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar mudança de status: {e}")
                    continue
            
            return records
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas do lead {lead.get('id')}: {e}")
            return []

    def calculate_hours_since(self, date: datetime) -> float:
        """
        Calcular horas desde uma data até agora
        """
        now = datetime.now()
        diff = (now - date).total_seconds() / 3600
        return round(diff, 2)

    def determine_conversion_type(self, from_type: str, to_type: str) -> str:
        """
        Determinar tipo de conversão entre status do pipeline principal
        """
        if not from_type or not to_type:
            return 'unknown'
            
        if to_type == 'won':
            return 'won'
        elif to_type == 'lost':
            return 'lost'
        elif from_type == to_type:
            return 'same_stage'
        else:
            # Definir ordem dos stages do pipeline principal
            stage_order = ['lead', 'qualified', 'meeting', 'proposal', 'negotiation', 'won', 'lost']
            
            from_index = stage_order.index(from_type) if from_type in stage_order else -1
            to_index = stage_order.index(to_type) if to_type in stage_order else -1
            
            if from_index != -1 and to_index != -1:
                if to_index > from_index:
                    return 'advance'
                elif to_index < from_index:
                    return 'regression'
            
            return 'lateral'

    def load_funnel_data(self, df: pd.DataFrame):
        """
        LOAD - Carregar dados do funil do pipeline principal no banco
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de histórico do funil
            create_table_query = """
            CREATE TABLE IF NOT EXISTS funnel_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id BIGINT,
                pipeline_id BIGINT,
                pipeline_name VARCHAR(255),
                status_id BIGINT,
                status_name VARCHAR(255),
                status_type VARCHAR(50),
                status_sort INT,
                entry_date DATETIME,
                exit_date DATETIME NULL,
                time_in_status_hours DECIMAL(10,2),
                is_current_status BOOLEAN,
                conversion_type VARCHAR(50),
                next_status_type VARCHAR(50),
                lead_value DECIMAL(12,2),
                responsible_user_id BIGINT,
                loss_reason_id BIGINT NULL,
                loss_reason_name VARCHAR(255) NULL,
                created_at DATETIME,
                UNIQUE KEY unique_lead_status_entry (lead_id, status_id, entry_date),
                INDEX idx_lead_id (lead_id),
                INDEX idx_pipeline_id (pipeline_id),
                INDEX idx_status_type (status_type),
                INDEX idx_entry_date (entry_date),
                INDEX idx_conversion_type (conversion_type),
                INDEX idx_status_sort (status_sort),
                INDEX idx_is_current (is_current_status)
            )
            """
            cursor.execute(create_table_query)
            
            # Limpar dados existentes do pipeline principal para o período
            if not df.empty:
                start_date = df['entry_date'].min().date()
                end_date = df['entry_date'].max().date()
                
                delete_query = """
                DELETE FROM funnel_history 
                WHERE pipeline_id = %s 
                AND DATE(entry_date) BETWEEN %s AND %s
                """
                cursor.execute(delete_query, (self.main_pipeline_id, start_date, end_date))
                logger.info(f"Limpos dados existentes do pipeline principal de {start_date} até {end_date}")
            
            # Inserir dados
            insert_query = """
            INSERT INTO funnel_history (
                lead_id, pipeline_id, pipeline_name, status_id, status_name, status_type, status_sort,
                entry_date, exit_date, time_in_status_hours, is_current_status,
                conversion_type, next_status_type, lead_value, responsible_user_id,
                loss_reason_id, loss_reason_name, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                exit_date = VALUES(exit_date),
                time_in_status_hours = VALUES(time_in_status_hours),
                is_current_status = VALUES(is_current_status),
                conversion_type = VALUES(conversion_type),
                next_status_type = VALUES(next_status_type),
                loss_reason_id = VALUES(loss_reason_id),
                loss_reason_name = VALUES(loss_reason_name),
                created_at = VALUES(created_at)
            """
            
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    int(row['lead_id']),
                    int(row['pipeline_id']),
                    row['pipeline_name'],
                    int(row['status_id']) if pd.notna(row['status_id']) else None,
                    row['status_name'],
                    row['status_type'],
                    int(row['status_sort']) if pd.notna(row['status_sort']) else 0,
                    row['entry_date'],
                    row['exit_date'] if pd.notna(row['exit_date']) else None,
                    float(row['time_in_status_hours']) if pd.notna(row['time_in_status_hours']) else None,
                    bool(row['is_current_status']),
                    row['conversion_type'],
                    row['next_status_type'],
                    float(row['lead_value']) if pd.notna(row['lead_value']) else 0,
                    int(row['responsible_user_id']) if pd.notna(row['responsible_user_id']) else None,
                    int(row['loss_reason_id']) if pd.notna(row['loss_reason_id']) else None,
                    row['loss_reason_name'],
                    row['created_at']
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            connection.commit()
            
            logger.info(f"Carregados {len(data_to_insert)} registros do funil principal")
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados do funil: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_main_funnel_metrics(self, date: datetime):
        """
        Gerar métricas específicas do funil principal
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de métricas do funil principal
            create_metrics_table = """
            CREATE TABLE IF NOT EXISTS main_funnel_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE,
                
                -- Contadores por status
                incoming_leads INT DEFAULT 0,
                interessados INT DEFAULT 0, 
                abordados INT DEFAULT 0,
                qualificacao INT DEFAULT 0,
                qualificado_reuniao INT DEFAULT 0,
                apresentacao INT DEFAULT 0,
                no_show INT DEFAULT 0,
                fup INT DEFAULT 0,
                negociacao INT DEFAULT 0,
                venda_ganha INT DEFAULT 0,
                venda_perdida INT DEFAULT 0,
                
                -- Métricas de conversão
                taxa_qualificacao DECIMAL(5,2) DEFAULT 0,
                taxa_reuniao DECIMAL(5,2) DEFAULT 0, 
                taxa_proposta DECIMAL(5,2) DEFAULT 0,
                taxa_fechamento DECIMAL(5,2) DEFAULT 0,
                
                -- Tempos médios por etapa
                tempo_medio_por_etapa DECIMAL(8,2) DEFAULT 0,
                tempo_lead_qualificacao_horas DECIMAL(8,2) DEFAULT 0,
                tempo_qualificacao_reuniao_horas DECIMAL(8,2) DEFAULT 0,
                tempo_reuniao_proposta_horas DECIMAL(8,2) DEFAULT 0,
                tempo_proposta_fechamento_horas DECIMAL(8,2) DEFAULT 0,
                
                -- Valor total
                valor_pipeline DECIMAL(12,2) DEFAULT 0,
                ticket_medio DECIMAL(10,2) DEFAULT 0,
                
                -- Métricas adicionais
                total_leads_ativos INT DEFAULT 0,
                leads_novos_dia INT DEFAULT 0,
                leads_convertidos_dia INT DEFAULT 0,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                UNIQUE KEY unique_date (metric_date),
                INDEX idx_metric_date (metric_date)
            )
            """
            
            cursor.execute(create_metrics_table)
            
            # Calcular métricas para a data específica
            metrics_query = """
            SELECT 
                DATE(entry_date) as metric_date,
                COUNT(CASE WHEN status_name = 'Incoming leads' THEN 1 END) as incoming_leads,
                COUNT(CASE WHEN status_name = 'Interessados' THEN 1 END) as interessados,
                COUNT(CASE WHEN status_name = 'Abordados' THEN 1 END) as abordados,
                COUNT(CASE WHEN status_name = 'Qualificação' THEN 1 END) as qualificacao,
                COUNT(CASE WHEN status_name = 'Qualificado para reunião' THEN 1 END) as qualificado_reuniao,
                COUNT(CASE WHEN status_name = 'Apresentação' THEN 1 END) as apresentacao,
                COUNT(CASE WHEN status_name = 'No Show' THEN 1 END) as no_show,
                COUNT(CASE WHEN status_name = 'FUP' THEN 1 END) as fup,
                COUNT(CASE WHEN status_name = 'Negociação' THEN 1 END) as negociacao,
                COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) as venda_ganha,
                COUNT(CASE WHEN status_name = 'Venda perdida' THEN 1 END) as venda_perdida,
                AVG(time_in_status_hours) as tempo_medio_por_etapa,
                SUM(lead_value) as valor_pipeline
            FROM funnel_history 
            WHERE pipeline_id = %s AND DATE(entry_date) = %s
            GROUP BY DATE(entry_date)
            """
            
            cursor.execute(metrics_query, (self.main_pipeline_id, date.date()))
            result = cursor.fetchone()
            
            if result:
                # Calcular taxas de conversão
                total_leads = result[1] + result[2] + result[3] + result[4] + result[5] + result[6] + result[7] + result[8] + result[9] + result[10] + result[11]
                
                taxa_qualificacao = (result[2] + result[3] + result[4] + result[5]) / total_leads * 100 if total_leads > 0 else 0
                taxa_reuniao = (result[6] + result[7]) / total_leads * 100 if total_leads > 0 else 0
                taxa_proposta = (result[8] + result[9]) / total_leads * 100 if total_leads > 0 else 0
                taxa_fechamento = result[10] / total_leads * 100 if total_leads > 0 else 0
                
                # Inserir métricas
                insert_metrics = """
                INSERT INTO main_funnel_metrics (
                    metric_date, incoming_leads, interessados, abordados, qualificacao,
                    qualificado_reuniao, apresentacao, no_show, fup, negociacao,
                    venda_ganha, venda_perdida, tempo_medio_por_etapa, valor_pipeline,
                    taxa_qualificacao, taxa_reuniao, taxa_proposta, taxa_fechamento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    incoming_leads = VALUES(incoming_leads),
                    interessados = VALUES(interessados),
                    abordados = VALUES(abordados),
                    qualificacao = VALUES(qualificacao),
                    qualificado_reuniao = VALUES(qualificado_reuniao),
                    apresentacao = VALUES(apresentacao),
                    no_show = VALUES(no_show),
                    fup = VALUES(fup),
                    negociacao = VALUES(negociacao),
                    venda_ganha = VALUES(venda_ganha),
                    venda_perdida = VALUES(venda_perdida),
                    tempo_medio_por_etapa = VALUES(tempo_medio_por_etapa),
                    valor_pipeline = VALUES(valor_pipeline),
                    taxa_qualificacao = VALUES(taxa_qualificacao),
                    taxa_reuniao = VALUES(taxa_reuniao),
                    taxa_proposta = VALUES(taxa_proposta),
                    taxa_fechamento = VALUES(taxa_fechamento)
                """
                
                cursor.execute(insert_metrics, (
                    date.date(), result[1], result[2], result[3], result[4], result[5], 
                    result[6], result[7], result[8], result[9], result[10], result[11], 
                    result[12], result[13], taxa_qualificacao, taxa_reuniao, taxa_proposta, taxa_fechamento
                ))
                connection.commit()
                logger.info(f"Métricas do funil principal calculadas para {date.date()}")
            
        except Exception as e:
            logger.error(f"Erro ao gerar métricas do funil principal: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def run_etl(self, start_date: datetime = None, end_date: datetime = None):
        """
        Executar ETL completo do funil principal
        """
        try:
            logger.info("="*60)
            logger.info("INICIANDO ETL FUNIL PRINCIPAL KOMMO")
            logger.info("="*60)
            
            # Definir período padrão (últimos 30 dias)
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            logger.info(f"Período: {start_date.date()} até {end_date.date()}")
            
            # 1. Extrair dados
            logger.info("1️ PIPELINES - Extraindo estrutura...")
            self.extract_pipelines_and_statuses()
            
            logger.info("2️ LEADS - Extraindo leads do funil principal...")
            raw_data = self.extract_leads_history(start_date, end_date)
            
            # 2. Transformar dados
            logger.info("3️ TRANSFORM - Processando dados do funil...")
            df_funnel = self.transform_funnel_data(raw_data)
            
            # 3. Carregar dados
            logger.info("4️ LOAD - Carregando dados do funil...")
            self.load_funnel_data(df_funnel)
            
            # 4. Gerar métricas
            logger.info("5️ METRICS - Gerando métricas do funil principal...")
            self.generate_main_funnel_metrics(end_date)
            
            logger.info("="*60)
            logger.info(" ETL FUNIL PRINCIPAL CONCLUÍDO COM SUCESSO!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f" Erro no ETL do funil principal: {e}")
            raise

if __name__ == "__main__":
    etl = KommoFunnelETL()
    etl.run_etl()