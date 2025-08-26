# ETL para Atividade Comercial - Kommo CRM
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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class KommoActivityETL:
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
        
        # Cache para usuários
        self.users_cache = {}

    def extract_users(self) -> Dict:
        """
        Extrair informações dos usuários/vendedores
        """
        try:
            logger.info("Extraindo usuários...")
            
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
                    'is_active': user.get('is_active', True),
                    'is_free': user.get('is_free', False)
                }
            
            logger.info(f"Carregados {len(self.users_cache)} usuários")
            return self.users_cache
            
        except Exception as e:
            logger.error(f"Erro ao extrair usuários: {e}")
            raise

    def extract_activities(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        EXTRACT - Extrair TODAS as atividades comerciais da API do Kommo
        """
        try:
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            logger.info(f"🔍 Extraindo TODAS as atividades comerciais de {start_date} até {end_date}")
            
            activities_data = {
                'calls': [],
                'tasks': [],
                'notes': [],
                'events': [],
                'meetings': [],
                'emails': [],
                'whatsapp': []
            }
            
            # 1. Extrair TODAS as tarefas (incluindo ligações)
            logger.info("📋 Extraindo tarefas e ligações...")
            tasks = self.extract_all_tasks(start_timestamp, end_timestamp)
            activities_data['tasks'] = tasks
            
            # 2. Extrair eventos de interação
            logger.info("📞 Extraindo eventos de comunicação...")
            events = self.extract_communication_events(start_timestamp, end_timestamp)
            activities_data['events'] = events
            
            # 3. Extrair notas e comentários
            logger.info("📝 Extraindo notas e comentários...")
            notes = self.extract_all_notes(start_timestamp, end_timestamp)
            activities_data['notes'] = notes
            
            # 4. Extrair reuniões agendadas
            logger.info("📅 Extraindo reuniões agendadas...")
            meetings = self.extract_meetings(start_timestamp, end_timestamp)
            activities_data['meetings'] = meetings
            
            # 3. Extrair notas/comentários - Tentar endpoint alternativo
            logger.info("Extraindo notas...")
            notes = self.extract_notes_alternative(start_timestamp, end_timestamp)
            activities_data['notes'] = notes
            
            # 4. Extrair eventos de atividade - Tentar endpoint alternativo
            logger.info("Extraindo eventos...")
            events = self.extract_events_alternative(start_timestamp, end_timestamp)
            activities_data['events'] = events
            
            return activities_data
            
        except Exception as e:
            logger.error(f"Erro na extração de atividades: {e}")
            raise

    def extract_calls(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair dados de ligações
        """
        try:
            # Tentar endpoint alternativo para ligações
            calls_url = f"{self.kommo_config['base_url']}/api/v4/events"
            calls_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'filter[type]': 'outgoing_call,incoming_call',
                'limit': 250
            }
            
            all_calls = []
            page = 1
            
            while True:
                calls_params['page'] = page
                calls_response = requests.get(calls_url, headers=self.headers, params=calls_params)
                
                # Verificar se a resposta é válida
                if calls_response.status_code != 200:
                    logger.warning(f"Status code {calls_response.status_code} para ligações")
                    break
                
                # Verificar se a resposta tem conteúdo
                if not calls_response.text.strip():
                    logger.warning("Resposta vazia para ligações")
                    break
                
                try:
                    calls_data = calls_response.json()
                except json.JSONDecodeError as e:
                    logger.warning(f"Erro ao decodificar JSON de ligações: {e}")
                    logger.warning(f"Resposta: {calls_response.text[:200]}...")
                    break
                
                calls = calls_data.get('_embedded', {}).get('events', [])
                if not calls:
                    break
                    
                all_calls.extend(calls)
                
                if len(calls) < 250:
                    break
                    
                page += 1
                time.sleep(0.1)
            
            logger.info(f"Extraídas {len(all_calls)} ligações")
            return all_calls
            
        except Exception as e:
            logger.warning(f"Erro ao extrair ligações: {e}")
            return []

    def extract_all_tasks(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair TODAS as tarefas incluindo ligações, follow-ups, reuniões
        """
        try:
            logger.info("📋 Buscando todas as tarefas comerciais...")
            
            tasks_url = f"{self.kommo_config['base_url']}/api/v4/tasks"
            tasks_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'limit': 250
            }
            
            all_tasks = []
            page = 1
            
            while True:
                tasks_params['page'] = page
                tasks_response = requests.get(tasks_url, headers=self.headers, params=tasks_params)
                
                if tasks_response.status_code != 200:
                    logger.warning(f"Erro na página {page}: {tasks_response.status_code}")
                    break
                
                try:
                    tasks_data = tasks_response.json()
                except json.JSONDecodeError:
                    logger.warning(f"Erro ao decodificar JSON na página {page}")
                    break
                
                tasks = tasks_data.get('_embedded', {}).get('tasks', [])
                if not tasks:
                    break
                
                logger.info(f"Página {page}: {len(tasks)} tarefas encontradas")
                
                # Processar e categorizar cada tarefa
                for task in tasks:
                    task_type = task.get('task_type')
                    text = task.get('text', '').lower()
                    
                    # Categorizar tipo de atividade
                    activity_type = self.categorize_task_activity(task_type, text)
                    
                    enhanced_task = {
                        'id': task.get('id'),
                        'entity_id': task.get('entity_id'),
                        'entity_type': task.get('entity_type'),
                        'responsible_user_id': task.get('responsible_user_id'),
                        'created_at': task.get('created_at'),
                        'updated_at': task.get('updated_at'),
                        'complete_till': task.get('complete_till'),
                        'text': task.get('text', ''),
                        'task_type_id': task_type,
                        'activity_type': activity_type,
                        'is_completed': task.get('is_completed', False),
                        'result': task.get('result', {}),
                        'account_id': task.get('account_id')
                    }
                    all_tasks.append(enhanced_task)
                
                if len(tasks) < 250:
                    break
                    
                page += 1
                time.sleep(0.1)
            
            logger.info(f"✅ Extraídas {len(all_tasks)} tarefas comerciais")
            return all_tasks
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair tarefas: {e}")
            return []
    
    def categorize_task_activity(self, task_type: int, text: str) -> str:
        """
        Categorizar tipo de atividade baseado no tipo e texto
        """
        text_lower = text.lower()
        
        # Mapeamento de tipos conhecidos do Kommo
        type_mapping = {
            1: 'contact',
            2: 'call',
            3: 'meeting',
            4: 'email',
            5: 'follow_up'
        }
        
        # Verificar por tipo primeiro
        if task_type in type_mapping:
            base_type = type_mapping[task_type]
        else:
            base_type = 'other'
        
        # Refinar baseado no texto
        if any(word in text_lower for word in ['ligar', 'call', 'telefone', 'contato telefônico']):
            return 'call'
        elif any(word in text_lower for word in ['reunião', 'meeting', 'apresentação', 'demo']):
            return 'meeting'
        elif any(word in text_lower for word in ['email', 'e-mail', 'enviar']):
            return 'email'
        elif any(word in text_lower for word in ['whatsapp', 'wpp', 'zap', 'mensagem']):
            return 'whatsapp'
        elif any(word in text_lower for word in ['follow', 'retorno', 'acompanhar']):
            return 'follow_up'
        elif any(word in text_lower for word in ['proposta', 'orçamento', 'contrato']):
            return 'proposal'
        else:
            return base_type

    def extract_communication_events(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair eventos de comunicação (ligações realizadas, emails enviados, etc.)
        """
        try:
            logger.info("📞 Buscando eventos de comunicação...")
            
            events_url = f"{self.kommo_config['base_url']}/api/v4/events"
            
            communication_events = []
            
            # Tipos de eventos de comunicação
            event_types = [
                'lead_status_changed',
                'task_completed',
                'note_added',
                'call_incoming',
                'call_outgoing'
            ]
            
            for event_type in event_types:
                logger.info(f"  Buscando eventos: {event_type}")
                
                events_params = {
                    'filter[created_at][from]': start_timestamp,
                    'filter[created_at][to]': end_timestamp,
                    'filter[type]': event_type,
                    'limit': 250
                }
                
                page = 1
                while True:
                    events_params['page'] = page
                    
                    try:
                        events_response = requests.get(events_url, headers=self.headers, params=events_params)
                        
                        if events_response.status_code != 200:
                            break
                        
                        events_data = events_response.json()
                        events = events_data.get('_embedded', {}).get('events', [])
                        
                        if not events:
                            break
                        
                        communication_events.extend(events)
                        logger.info(f"    Página {page}: {len(events)} eventos {event_type}")
                        
                        if len(events) < 250:
                            break
                            
                        page += 1
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"Erro ao buscar eventos {event_type} página {page}: {e}")
                        break
            
            logger.info(f"✅ Extraídos {len(communication_events)} eventos de comunicação")
            return communication_events
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair eventos de comunicação: {e}")
            return []

    def extract_all_notes(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair todas as notas e comentários
        """
        try:
            logger.info("📝 Buscando notas e comentários...")
            
            # Método 1: Buscar via eventos
            notes_url = f"{self.kommo_config['base_url']}/api/v4/events"
            notes_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'filter[type]': 'note_added',
                'limit': 250
            }
            
            all_notes = []
            page = 1
            
            while True:
                notes_params['page'] = page
                
                try:
                    notes_response = requests.get(notes_url, headers=self.headers, params=notes_params)
                    
                    if notes_response.status_code != 200:
                        break
                    
                    notes_data = notes_response.json()
                    notes = notes_data.get('_embedded', {}).get('events', [])
                    
                    if not notes:
                        break
                    
                    all_notes.extend(notes)
                    logger.info(f"Página {page}: {len(notes)} notas encontradas")
                    
                    if len(notes) < 250:
                        break
                        
                    page += 1
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Erro ao buscar notas página {page}: {e}")
                    break
            
            logger.info(f"✅ Extraídas {len(all_notes)} notas")
            return all_notes
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair notas: {e}")
            return []

    def extract_meetings(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair reuniões agendadas
        """
        try:
            logger.info("📅 Buscando reuniões agendadas...")
            
            # Buscar tarefas que são reuniões
            tasks_url = f"{self.kommo_config['base_url']}/api/v4/tasks"
            meeting_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'filter[task_type]': 3,  # Tipo 3 = reunião
                'limit': 250
            }
            
            all_meetings = []
            page = 1
            
            while True:
                meeting_params['page'] = page
                
                try:
                    meeting_response = requests.get(tasks_url, headers=self.headers, params=meeting_params)
                    
                    if meeting_response.status_code != 200:
                        break
                    
                    meeting_data = meeting_response.json()
                    meetings = meeting_data.get('_embedded', {}).get('tasks', [])
                    
                    if not meetings:
                        break
                    
                    all_meetings.extend(meetings)
                    logger.info(f"Página {page}: {len(meetings)} reuniões encontradas")
                    
                    if len(meetings) < 250:
                        break
                        
                    page += 1
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Erro ao buscar reuniões página {page}: {e}")
                    break
            
            logger.info(f"✅ Extraídas {len(all_meetings)} reuniões")
            return all_meetings
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair reuniões: {e}")
            return []

    def extract_tasks(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair tarefas/follow-ups
        """
        try:
            tasks_url = f"{self.kommo_config['base_url']}/api/v4/tasks"
            tasks_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'limit': 250
            }
            
            all_tasks = []
            page = 1
            
            while True:
                tasks_params['page'] = page
                tasks_response = requests.get(tasks_url, headers=self.headers, params=tasks_params)
                tasks_response.raise_for_status()
                tasks_data = tasks_response.json()
                
                tasks = tasks_data.get('_embedded', {}).get('tasks', [])
                if not tasks:
                    break
                    
                all_tasks.extend(tasks)
                
                if len(tasks) < 250:
                    break
                    
                page += 1
                time.sleep(0.1)
            
            logger.info(f"Extraídas {len(all_tasks)} tarefas")
            return all_tasks
            
        except Exception as e:
            logger.warning(f"Erro ao extrair tarefas: {e}")
            return []

    def extract_notes(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair notas/comentários
        """
        try:
            # Tentar endpoint alternativo para notas
            notes_url = f"{self.kommo_config['base_url']}/api/v4/events"
            notes_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'filter[type]': 'note_added',
                'limit': 250
            }
            
            all_notes = []
            page = 1
            
            while True:
                notes_params['page'] = page
                notes_response = requests.get(notes_url, headers=self.headers, params=notes_params)
                
                # Verificar se a resposta é válida
                if notes_response.status_code != 200:
                    logger.warning(f"Status code {notes_response.status_code} para notas")
                    break
                
                # Verificar se a resposta tem conteúdo
                if not notes_response.text.strip():
                    logger.warning("Resposta vazia para notas")
                    break
                
                try:
                    notes_data = notes_response.json()
                except json.JSONDecodeError as e:
                    logger.warning(f"Erro ao decodificar JSON de notas: {e}")
                    logger.warning(f"Resposta: {notes_response.text[:200]}...")
                    break
                
                notes = notes_data.get('_embedded', {}).get('events', [])
                if not notes:
                    break
                    
                all_notes.extend(notes)
                
                if len(notes) < 250:
                    break
                    
                page += 1
                time.sleep(0.1)
            
            logger.info(f"Extraídas {len(all_notes)} notas")
            return all_notes
            
        except Exception as e:
            logger.warning(f"Erro ao extrair notas: {e}")
            return []

    def extract_notes_alternative(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Tentar extrair notas usando diferentes abordagens
        """
        try:
            # Tentativa 1: Buscar nas tarefas que têm texto (notas)
            logger.info("Tentando extrair notas das tarefas...")
            
            tasks_url = f"{self.kommo_config['base_url']}/api/v4/tasks"
            tasks_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'limit': 250
            }
            
            all_notes = []
            page = 1
            
            while True:
                tasks_params['page'] = page
                tasks_response = requests.get(tasks_url, headers=self.headers, params=tasks_params)
                
                if tasks_response.status_code != 200:
                    break
                
                try:
                    tasks_data = tasks_response.json()
                except json.JSONDecodeError:
                    break
                
                tasks = tasks_data.get('_embedded', {}).get('tasks', [])
                if not tasks:
                    break
                    
                # Converter tarefas com texto para formato de notas
                for task in tasks:
                    if task.get('text') and len(task.get('text', '')) > 10:  # Nota com conteúdo
                        note_data = {
                            'id': f"note_task_{task.get('id')}",
                            'entity_id': task.get('entity_id'),
                            'entity_type': task.get('entity_type'),
                            'responsible_user_id': task.get('responsible_user_id'),
                            'created_at': task.get('created_at'),
                            'note_type': 'task_note',
                            'text': task.get('text', ''),
                            'params': {}
                        }
                        all_notes.append(note_data)
                
                if len(tasks) < 250:
                    break
                    
                page += 1
                time.sleep(0.1)
            
            logger.info(f"Extraídas {len(all_notes)} notas das tarefas")
            return all_notes
            
        except Exception as e:
            logger.warning(f"Erro ao extrair notas alternativo: {e}")
            return []

    def extract_activity_events(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Extrair eventos de atividade (e-mails, mensagens)
        """
        try:
            events_url = f"{self.kommo_config['base_url']}/api/v4/events"
            
            # Tipos de eventos relacionados a atividades
            activity_event_types = [
                'outgoing_call',
                'incoming_call', 
                'outgoing_sms',
                'incoming_sms',
                'task_completed',
                'note_added',
                'email_sent',
                'email_received',
                'meeting_scheduled',
                'meeting_completed'
            ]
            
            all_events = []
            
            for event_type in activity_event_types:
                events_params = {
                    'filter[created_at][from]': start_timestamp,
                    'filter[created_at][to]': end_timestamp,
                    'filter[type]': event_type,
                    'limit': 250
                }
                
                page = 1
                while True:
                    events_params['page'] = page
                    events_response = requests.get(events_url, headers=self.headers, params=events_params)
                    
                    # Verificar se a resposta é válida
                    if events_response.status_code != 200:
                        logger.warning(f"Status code {events_response.status_code} para eventos tipo {event_type}")
                        break
                    
                    # Verificar se a resposta tem conteúdo
                    if not events_response.text.strip():
                        logger.warning(f"Resposta vazia para eventos tipo {event_type}")
                        break
                    
                    try:
                        events_data = events_response.json()
                    except json.JSONDecodeError as e:
                        logger.warning(f"Erro ao decodificar JSON de eventos tipo {event_type}: {e}")
                        logger.warning(f"Resposta: {events_response.text[:200]}...")
                        break
                    
                    events = events_data.get('_embedded', {}).get('events', [])
                    if not events:
                        break
                        
                    all_events.extend(events)
                    
                    if len(events) < 250:
                        break
                        
                    page += 1
                    time.sleep(0.1)
                
                time.sleep(0.2)  # Delay entre tipos de evento
            
            logger.info(f"Extraídos {len(all_events)} eventos de atividade")
            return all_events
            
        except Exception as e:
            logger.warning(f"Erro ao extrair eventos: {e}")
            return []

    def extract_events_alternative(self, start_timestamp: int, end_timestamp: int) -> List[Dict]:
        """
        Tentar extrair eventos usando diferentes abordagens
        """
        try:
            # Tentativa 1: Buscar nas tarefas completadas como eventos
            logger.info("Tentando extrair eventos das tarefas...")
            
            tasks_url = f"{self.kommo_config['base_url']}/api/v4/tasks"
            tasks_params = {
                'filter[created_at][from]': start_timestamp,
                'filter[created_at][to]': end_timestamp,
                'filter[is_completed]': 1,  # Apenas tarefas completadas
                'limit': 250
            }
            
            all_events = []
            page = 1
            
            while True:
                tasks_params['page'] = page
                tasks_response = requests.get(tasks_url, headers=self.headers, params=tasks_params)
                
                if tasks_response.status_code != 200:
                    break
                
                try:
                    tasks_data = tasks_response.json()
                except json.JSONDecodeError:
                    break
                
                tasks = tasks_data.get('_embedded', {}).get('tasks', [])
                if not tasks:
                    break
                    
                # Converter tarefas completadas para formato de eventos
                for task in tasks:
                    if task.get('is_completed'):
                        event_data = {
                            'id': f"event_task_{task.get('id')}",
                            'entity_id': task.get('entity_id'),
                            'entity_type': task.get('entity_type'),
                            'responsible_user_id': task.get('responsible_user_id'),
                            'created_at': task.get('completed_at') or task.get('created_at'),
                            'type': 'task_completed',
                            'params': {
                                'task_type': task.get('task_type'),
                                'text': task.get('text', '')
                            }
                        }
                        all_events.append(event_data)
                
                if len(tasks) < 250:
                    break
                    
                page += 1
                time.sleep(0.1)
            
            logger.info(f"Extraídos {len(all_events)} eventos das tarefas")
            return all_events
            
        except Exception as e:
            logger.warning(f"Erro ao extrair eventos alternativo: {e}")
            return []

    def classify_contact_type(self, activity_data: Dict, activity_type: str) -> str:
        """
        Classificar tipo de contato baseado na atividade
        """
        try:
            if activity_type == 'call':
                call_status = activity_data.get('call_status')
                if call_status == 'outgoing':
                    return 'ligacao_feita'
                elif call_status == 'incoming':
                    return 'ligacao_recebida'
                else:
                    return 'ligacao'
                    
            elif activity_type == 'note':
                note_type = activity_data.get('note_type')
                params = activity_data.get('params', {})
                
                # Detectar tipo baseado no conteúdo ou parâmetros
                if 'email' in str(params).lower() or note_type == 'email_out':
                    return 'email'
                elif 'whatsapp' in str(params).lower() or 'whats' in str(params).lower():
                    return 'whatsapp'
                elif 'sms' in str(params).lower():
                    return 'sms'
                else:
                    return 'nota'
                    
            elif activity_type == 'task':
                task_type = activity_data.get('task_type')
                text = activity_data.get('text', '').lower()
                
                # Classificar baseado no tipo de tarefa (task_type)
                if task_type == 1:  # Reunião
                    return 'reuniao_agendada'
                elif task_type == 2:  # Ligação
                    return 'ligacao_agendada'
                elif task_type == 3:  # E-mail
                    return 'email'
                elif task_type == 4:  # Tarefa
                    return 'tarefa'
                elif task_type == 5:  # Follow-up
                    return 'followup'
                # Se não tem task_type, tentar classificar pelo texto
                elif 'reunião' in text or 'meeting' in text:
                    return 'reuniao_agendada'
                elif 'ligar' in text or 'call' in text:
                    return 'ligacao_agendada'
                elif 'email' in text or 'e-mail' in text:
                    return 'email'
                elif 'follow' in text or 'acompanhar' in text:
                    return 'followup'
                else:
                    return 'tarefa'
                    
            elif activity_type == 'event':
                event_type = activity_data.get('type')
                if 'call' in event_type:
                    return 'ligacao'
                elif 'sms' in event_type:
                    return 'sms'
                elif 'note' in event_type:
                    return 'nota'
                else:
                    return 'evento'
            
            return 'outro'
            
        except Exception as e:
            logger.warning(f"Erro ao classificar tipo de contato: {e}")
            return 'erro'

    def calculate_response_metrics(self, activities: List[Dict], notes: List[Dict]) -> Dict:
        """
        Calcular métricas de resposta dos leads
        """
        try:
            response_metrics = defaultdict(lambda: {
                'contacts_sent': 0,
                'responses_received': 0,
                'response_rate': 0,
                'avg_response_time_hours': 0
            })
            
            # Agrupar atividades por lead
            activities_by_lead = defaultdict(list)
            
            for activity in activities:
                entity_id = activity.get('entity_id')
                entity_type = activity.get('entity_type')
                
                if entity_type in ['leads', 'lead']:
                    activities_by_lead[entity_id].append(activity)
            
            # Calcular métricas para cada lead
            for lead_id, lead_activities in activities_by_lead.items():
                # Ordenar por data
                lead_activities.sort(key=lambda x: x.get('created_at', 0))
                
                contacts_sent = 0
                responses_received = 0
                response_times = []
                
                for i, activity in enumerate(lead_activities):
                    activity_type = self.classify_contact_type(activity, 'event')
                    
                    # Contar contatos enviados
                    if activity_type in ['ligacao_feita', 'email', 'whatsapp', 'sms']:
                        contacts_sent += 1
                        
                        # Verificar se houve resposta nas próximas 24h
                        activity_time = datetime.fromtimestamp(activity.get('created_at', 0))
                        
                        for j in range(i + 1, len(lead_activities)):
                            next_activity = lead_activities[j]
                            next_time = datetime.fromtimestamp(next_activity.get('created_at', 0))
                            
                            # Se passou de 24h, parar de procurar
                            if (next_time - activity_time).total_seconds() > 86400:
                                break
                            
                            # Se foi uma resposta do lead (nota recebida, ligação recebida)
                            next_type = self.classify_contact_type(next_activity, 'event')
                            if next_type in ['ligacao_recebida', 'nota'] and next_activity.get('created_by') != activity.get('created_by'):
                                responses_received += 1
                                response_time = (next_time - activity_time).total_seconds() / 3600
                                response_times.append(response_time)
                                break
                
                response_rate = (responses_received / contacts_sent * 100) if contacts_sent > 0 else 0
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                response_metrics[lead_id] = {
                    'contacts_sent': contacts_sent,
                    'responses_received': responses_received,
                    'response_rate': round(response_rate, 2),
                    'avg_response_time_hours': round(avg_response_time, 2)
                }
            
            return response_metrics
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas de resposta: {e}")
            return {}

    def transform_activity_data(self, raw_data: Dict) -> pd.DataFrame:
        """
        TRANSFORM - Processar dados de atividades
        """
        try:
            calls = raw_data['calls']
            tasks = raw_data['tasks']
            notes = raw_data['notes']
            events = raw_data['events']
            
            # Calcular métricas de resposta
            response_metrics = self.calculate_response_metrics(events, notes)
            
            activity_records = []
            
            # Processar ligações
            for call in calls:
                try:
                    activity_records.append({
                        'activity_id': f"call_{call.get('id')}",
                        'activity_type': 'call',
                        'contact_type': self.classify_contact_type(call, 'call'),
                        'user_id': call.get('responsible_user_id'),
                        'user_name': self.users_cache.get(call.get('responsible_user_id'), {}).get('name', 'Unknown'),
                        'entity_id': call.get('entity_id'),
                        'entity_type': call.get('entity_type'),
                        'created_date': datetime.fromtimestamp(call.get('created_at', 0)).date(),
                        'created_datetime': datetime.fromtimestamp(call.get('created_at', 0)),
                        'duration_seconds': call.get('duration', 0),
                        'is_successful': call.get('call_status') == 'answered',
                        'note_text': call.get('note', {}).get('text', ''),
                        'source': 'calls_api',
                        'updated_at': datetime.now()
                    })
                except Exception as e:
                    logger.warning(f"Erro ao processar call {call.get('id')}: {e}")
                    continue
            
            # Processar tarefas
            task_types_count = {}
            for task in tasks:
                try:
                    # Só processar tarefas que têm responsible_user_id válido
                    if not task.get('responsible_user_id'):
                        continue
                        
                    # Verificar se foi completada no prazo
                    complete_till = task.get('complete_till')
                    completed_at = task.get('completed_at')
                    is_completed_on_time = False
                    
                    if complete_till and completed_at:
                        deadline = datetime.fromtimestamp(complete_till)
                        completion = datetime.fromtimestamp(completed_at)
                        is_completed_on_time = completion <= deadline
                    
                    # Classificar tipo de contato
                    contact_type = self.classify_contact_type(task, 'task')
                    task_types_count[contact_type] = task_types_count.get(contact_type, 0) + 1
                    
                    activity_records.append({
                        'activity_id': f"task_{task.get('id')}",
                        'activity_type': 'task',
                        'contact_type': self.classify_contact_type(task, 'task'),
                        'user_id': task.get('responsible_user_id'),
                        'user_name': self.users_cache.get(task.get('responsible_user_id'), {}).get('name', 'Unknown'),
                        'entity_id': task.get('entity_id'),
                        'entity_type': task.get('entity_type'),
                        'created_date': datetime.fromtimestamp(task.get('created_at', 0)).date(),
                        'created_datetime': datetime.fromtimestamp(task.get('created_at', 0)),
                        'duration_seconds': None,
                        'is_successful': bool(task.get('is_completed')),
                        'is_completed_on_time': is_completed_on_time,
                        'note_text': task.get('text', ''),
                        'complete_till': datetime.fromtimestamp(complete_till) if complete_till else None,
                        'completed_at': datetime.fromtimestamp(completed_at) if completed_at else None,
                        'source': 'tasks_api',
                        'updated_at': datetime.now()
                    })
                except Exception as e:
                    logger.warning(f"Erro ao processar task {task.get('id')}: {e}")
                    continue
            
            # Processar notas
            for note in notes:
                try:
                    # Só processar notas que têm responsible_user_id válido
                    if not note.get('responsible_user_id'):
                        continue
                        
                    activity_records.append({
                        'activity_id': f"note_{note.get('id')}",
                        'activity_type': 'note',
                        'contact_type': self.classify_contact_type(note, 'note'),
                        'user_id': note.get('responsible_user_id'),
                        'user_name': self.users_cache.get(note.get('responsible_user_id'), {}).get('name', 'Unknown'),
                        'entity_id': note.get('entity_id'),
                        'entity_type': note.get('entity_type'),
                        'created_date': datetime.fromtimestamp(note.get('created_at', 0)).date(),
                        'created_datetime': datetime.fromtimestamp(note.get('created_at', 0)),
                        'duration_seconds': None,
                        'is_successful': True,
                        'note_text': note.get('params', {}).get('text', ''),
                        'source': 'notes_api',
                        'updated_at': datetime.now()
                    })
                except Exception as e:
                    logger.warning(f"Erro ao processar note {note.get('id')}: {e}")
                    continue
            
            # Processar eventos
            for event in events:
                try:
                    # Só processar eventos que têm created_by válido
                    if not event.get('created_by'):
                        continue
                        
                    activity_records.append({
                        'activity_id': f"event_{event.get('id')}",
                        'activity_type': 'event',
                        'contact_type': self.classify_contact_type(event, 'event'),
                        'user_id': event.get('created_by'),
                        'user_name': self.users_cache.get(event.get('created_by'), {}).get('name', 'Unknown'),
                        'entity_id': event.get('entity_id'),
                        'entity_type': event.get('entity_type'),
                        'created_date': datetime.fromtimestamp(event.get('created_at', 0)).date(),
                        'created_datetime': datetime.fromtimestamp(event.get('created_at', 0)),
                        'duration_seconds': None,
                        'is_successful': True,
                        'note_text': str(event.get('value_after', '')),
                        'source': 'events_api',
                        'updated_at': datetime.now()
                    })
                except Exception as e:
                    logger.warning(f"Erro ao processar event {event.get('id')}: {e}")
                    continue
            
            # Adicionar métricas de resposta apenas se houver dados válidos
            for entity_id, metrics in response_metrics.items():
                if metrics['contacts_sent'] > 0:  # Só adicionar se houver contatos enviados
                    activity_records.append({
                        'activity_id': f"response_{entity_id}",
                        'activity_type': 'response_metrics',
                        'contact_type': 'response_rate',
                        'user_id': None,
                        'user_name': 'System',
                        'entity_id': entity_id,
                        'entity_type': 'lead',
                        'created_date': datetime.now().date(),
                        'created_datetime': datetime.now(),
                        'duration_seconds': None,
                        'is_successful': metrics['response_rate'] > 0,
                        'contacts_sent': metrics['contacts_sent'],
                        'responses_received': metrics['responses_received'],
                        'response_rate': metrics['response_rate'],
                        'avg_response_time_hours': metrics['avg_response_time_hours'],
                        'source': 'calculated',
                        'updated_at': datetime.now()
                    })
            
            df = pd.DataFrame(activity_records)
            logger.info(f"Processadas {len(df)} atividades")
            
            # Log da classificação das tarefas
            if task_types_count:
                logger.info("📊 Classificação das tarefas:")
                for task_type, count in task_types_count.items():
                    logger.info(f"  {task_type}: {count} tarefas")
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na transformação: {e}")
            raise

    def load_activity_data(self, df: pd.DataFrame):
        """
        LOAD - Carregar dados de atividades no banco
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de atividades
            create_table_query = """
            CREATE TABLE IF NOT EXISTS commercial_activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                activity_id VARCHAR(100) UNIQUE,
                activity_type ENUM('call', 'email', 'whatsapp', 'meeting', 'task', 'note', 'follow_up', 'proposal', 'contact', 'other') NOT NULL,
                contact_type VARCHAR(100),
                user_id BIGINT NOT NULL,
                user_name VARCHAR(255),
                user_role VARCHAR(100),
                entity_id BIGINT DEFAULT 0,
                entity_type VARCHAR(50) DEFAULT 'lead',
                created_date DATE NOT NULL,
                created_datetime DATETIME NOT NULL,
                updated_datetime DATETIME NULL,
                complete_till DATETIME NULL,
                completed_at DATETIME NULL,
                duration_seconds INT DEFAULT 0,
                is_successful BOOLEAN DEFAULT FALSE,
                is_completed BOOLEAN DEFAULT FALSE,
                is_completed_on_time BOOLEAN DEFAULT FALSE,
                note_text TEXT,
                task_result TEXT,
                contacts_sent INT DEFAULT 0,
                responses_received INT DEFAULT 0,
                response_rate DECIMAL(5,2) DEFAULT 0.00,
                avg_response_time_hours DECIMAL(8,2) DEFAULT 0.00,
                lead_responded BOOLEAN DEFAULT FALSE,
                is_follow_up BOOLEAN DEFAULT FALSE,
                task_type_id INT NULL,
                event_type VARCHAR(50) NULL,
                source VARCHAR(50) DEFAULT 'kommo_api',
                week_number INT DEFAULT 0,
                month_year VARCHAR(7) DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_created_date (created_date),
                INDEX idx_activity_type (activity_type),
                INDEX idx_contact_type (contact_type),
                INDEX idx_entity_id (entity_id),
                INDEX idx_week (week_number),
                INDEX idx_month (month_year),
                INDEX idx_status (is_completed)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_query)
            
            # Limpar dados existentes para o período
            start_date = df['created_date'].min()
            end_date = df['created_date'].max()
            
            if start_date and end_date:
                delete_query = """
                DELETE FROM commercial_activities 
                WHERE created_date BETWEEN %s AND %s
                """
                cursor.execute(delete_query, (start_date, end_date))
                logger.info(f"Limpos dados existentes de {start_date} até {end_date}")
            
            # Inserir dados
            insert_query = """
            INSERT INTO commercial_activities (
                activity_id, activity_type, contact_type, user_id, user_name,
                entity_id, entity_type, created_date, created_datetime,
                duration_seconds, is_successful, is_completed_on_time,
                note_text, complete_till, completed_at, contacts_sent,
                responses_received, response_rate, avg_response_time_hours,
                source, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                is_successful = VALUES(is_successful),
                is_completed_on_time = VALUES(is_completed_on_time),
                completed_at = VALUES(completed_at),
                response_rate = VALUES(response_rate),
                updated_at = VALUES(updated_at)
            """
            
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    row['activity_id'],
                    row['activity_type'],
                    row['contact_type'],
                    int(row['user_id']) if pd.notna(row['user_id']) else None,
                    row.get('user_name', ''),
                    int(row['entity_id']) if pd.notna(row['entity_id']) else None,
                    row.get('entity_type', ''),
                    row['created_date'],
                    row['created_datetime'],
                    int(row['duration_seconds']) if pd.notna(row['duration_seconds']) else None,
                    bool(row.get('is_successful', False)),
                    bool(row.get('is_completed_on_time', False)),
                    str(row.get('note_text', ''))[:1000] if pd.notna(row.get('note_text')) else '',  # Limitar tamanho do texto
                    row.get('complete_till') if pd.notna(row.get('complete_till')) else None,
                    row.get('completed_at') if pd.notna(row.get('completed_at')) else None,
                    int(row['contacts_sent']) if pd.notna(row.get('contacts_sent')) else None,
                    int(row['responses_received']) if pd.notna(row.get('responses_received')) else None,
                    float(row['response_rate']) if pd.notna(row.get('response_rate')) else None,
                    float(row['avg_response_time_hours']) if pd.notna(row.get('avg_response_time_hours')) else None,
                    row.get('source', ''),
                    row['updated_at']
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            connection.commit()
            
            logger.info(f"Carregadas {len(data_to_insert)} atividades")
            
        except Exception as e:
            logger.error(f"Erro ao carregar atividades: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_activity_metrics(self, date: datetime):
        """
        Gerar métricas consolidadas de atividades
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de métricas de atividades
            create_metrics_table = """
            CREATE TABLE IF NOT EXISTS activity_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE,
                user_id BIGINT,
                user_name VARCHAR(255),
                total_contacts INT,
                calls_made INT,
                emails_sent INT,
                whatsapp_sent INT,
                meetings_scheduled INT,
                followups_completed INT,
                followups_on_time INT,
                followup_compliance_rate DECIMAL(5,2),
                avg_response_rate DECIMAL(5,2),
                total_contact_time_minutes INT,
                activities_per_lead DECIMAL(5,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_date_user (metric_date, user_id),
                INDEX idx_metric_date (metric_date),
                INDEX idx_user_id (user_id)
            )
            """
            cursor.execute(create_metrics_table)
            
            date_str = date.strftime('%Y-%m-%d')
            
            # Limpar métricas existentes para a data
            delete_metrics_query = """
            DELETE FROM activity_metrics 
            WHERE metric_date = %s
            """
            cursor.execute(delete_metrics_query, (date_str,))
            logger.info(f"Limpas métricas existentes para {date_str}")
            
            # Calcular métricas por usuário
            cursor.execute("""
                SELECT 
                    user_id,
                    user_name,
                    COUNT(*) as total_activities,
                    SUM(CASE WHEN contact_type IN ('ligacao_feita', 'ligacao_agendada') THEN 1 ELSE 0 END) as calls_made,
                    SUM(CASE WHEN contact_type = 'email' THEN 1 ELSE 0 END) as emails_sent,
                    SUM(CASE WHEN contact_type = 'whatsapp' THEN 1 ELSE 0 END) as whatsapp_sent,
                    SUM(CASE WHEN contact_type = 'reuniao_agendada' THEN 1 ELSE 0 END) as meetings_scheduled,
                    SUM(CASE WHEN contact_type = 'followup' AND is_successful = 1 THEN 1 ELSE 0 END) as followups_completed,
                    SUM(CASE WHEN contact_type = 'followup' AND is_completed_on_time = 1 THEN 1 ELSE 0 END) as followups_on_time,
                    SUM(CASE WHEN contact_type = 'followup' THEN 1 ELSE 0 END) as total_followups,
                    AVG(CASE WHEN response_rate IS NOT NULL THEN response_rate ELSE NULL END) as avg_response_rate,
                    SUM(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds ELSE 0 END) / 60 as total_time_minutes,
                    COUNT(DISTINCT entity_id) as unique_leads
                FROM commercial_activities 
                WHERE created_date = %s AND user_id IS NOT NULL
                GROUP BY user_id, user_name
            """, (date_str,))
            
            results = cursor.fetchall()
            
            # Inserir métricas
            insert_metrics_query = """
            INSERT INTO activity_metrics (
                metric_date, user_id, user_name, total_contacts, calls_made,
                emails_sent, whatsapp_sent, meetings_scheduled, followups_completed,
                followups_on_time, followup_compliance_rate, avg_response_rate,
                total_contact_time_minutes, activities_per_lead
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_contacts = VALUES(total_contacts),
                calls_made = VALUES(calls_made),
                emails_sent = VALUES(emails_sent),
                whatsapp_sent = VALUES(whatsapp_sent),
                meetings_scheduled = VALUES(meetings_scheduled),
                followups_completed = VALUES(followups_completed),
                followups_on_time = VALUES(followups_on_time),
                followup_compliance_rate = VALUES(followup_compliance_rate),
                avg_response_rate = VALUES(avg_response_rate),
                total_contact_time_minutes = VALUES(total_contact_time_minutes),
                activities_per_lead = VALUES(activities_per_lead)
            """
            
            for result in results:
                (user_id, user_name, total_activities, calls_made, emails_sent, 
                 whatsapp_sent, meetings_scheduled, followups_completed, followups_on_time,
                 total_followups, avg_response_rate, total_time_minutes, unique_leads) = result
                
                # Calcular métricas derivadas
                total_contacts = calls_made + emails_sent + whatsapp_sent + meetings_scheduled
                followup_compliance_rate = (followups_on_time / total_followups * 100) if total_followups > 0 else 0
                activities_per_lead = (total_activities / unique_leads) if unique_leads > 0 else 0
                
                cursor.execute(insert_metrics_query, (
                    date_str,
                    user_id,
                    user_name,
                    total_contacts,
                    calls_made,
                    emails_sent,
                    whatsapp_sent,
                    meetings_scheduled,
                    followups_completed,
                    followups_on_time,
                    round(followup_compliance_rate, 2),
                    round(avg_response_rate or 0, 2),
                    round(total_time_minutes, 0),
                    round(activities_per_lead, 2)
                ))
            
            connection.commit()
            
            logger.info(f"Métricas de atividade geradas para {date_str}")
            
            # Log resumo das métricas
            cursor.execute("""
                SELECT 
                    user_name,
                    total_contacts,
                    calls_made,
                    meetings_scheduled,
                    followup_compliance_rate,
                    avg_response_rate
                FROM activity_metrics 
                WHERE metric_date = %s
                ORDER BY total_contacts DESC
            """, (date_str,))
            
            summary = cursor.fetchall()
            logger.info("=== RESUMO ATIVIDADES POR VENDEDOR ===")
            for user_name, contacts, calls, meetings, compliance, response_rate in summary:
                logger.info(f"{user_name}: {contacts} contatos, {calls} ligações, {meetings} reuniões, {compliance}% compliance, {response_rate}% resposta")
            
            # Gerar também métricas consolidadas do time
            self.generate_team_activity_summary(date_str, cursor, connection)
            
        except Exception as e:
            logger.error(f"Erro ao gerar métricas de atividade: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_team_activity_summary(self, date_str: str, cursor, connection):
        """
        Gerar resumo consolidado da atividade do time
        """
        try:
            # Criar tabela de resumo do time
            create_team_table = """
            CREATE TABLE IF NOT EXISTS team_activity_summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE UNIQUE,
                total_team_contacts INT,
                total_calls_made INT,
                total_emails_sent INT,
                total_whatsapp_sent INT,
                total_meetings_scheduled INT,
                avg_team_response_rate DECIMAL(5,2),
                avg_followup_compliance DECIMAL(5,2),
                active_users_count INT,
                contacts_per_user DECIMAL(5,2),
                top_performer_user_id BIGINT,
                top_performer_contacts INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_metric_date (metric_date)
            )
            """
            cursor.execute(create_team_table)
            
            # Calcular métricas do time
            cursor.execute("""
                SELECT 
                    SUM(total_contacts) as team_contacts,
                    SUM(calls_made) as team_calls,
                    SUM(emails_sent) as team_emails,
                    SUM(whatsapp_sent) as team_whatsapp,
                    SUM(meetings_scheduled) as team_meetings,
                    AVG(avg_response_rate) as team_response_rate,
                    AVG(followup_compliance_rate) as team_compliance,
                    COUNT(*) as active_users
                FROM activity_metrics 
                WHERE metric_date = %s
            """, (date_str,))
            
            team_result = cursor.fetchone()
            
            if team_result and team_result[0]:  # Se há dados
                (team_contacts, team_calls, team_emails, team_whatsapp, 
                 team_meetings, team_response_rate, team_compliance, active_users) = team_result
                
                # Encontrar top performer
                cursor.execute("""
                    SELECT user_id, total_contacts 
                    FROM activity_metrics 
                    WHERE metric_date = %s 
                    ORDER BY total_contacts DESC 
                    LIMIT 1
                """, (date_str,))
                
                top_performer = cursor.fetchone()
                top_performer_id = top_performer[0] if top_performer else None
                top_performer_contacts = top_performer[1] if top_performer else 0
                
                contacts_per_user = (team_contacts / active_users) if active_users > 0 else 0
                
                # Inserir resumo do time
                insert_team_query = """
                INSERT INTO team_activity_summary (
                    metric_date, total_team_contacts, total_calls_made, total_emails_sent,
                    total_whatsapp_sent, total_meetings_scheduled, avg_team_response_rate,
                    avg_followup_compliance, active_users_count, contacts_per_user,
                    top_performer_user_id, top_performer_contacts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_team_contacts = VALUES(total_team_contacts),
                    total_calls_made = VALUES(total_calls_made),
                    total_emails_sent = VALUES(total_emails_sent),
                    total_whatsapp_sent = VALUES(total_whatsapp_sent),
                    total_meetings_scheduled = VALUES(total_meetings_scheduled),
                    avg_team_response_rate = VALUES(avg_team_response_rate),
                    avg_followup_compliance = VALUES(avg_followup_compliance),
                    active_users_count = VALUES(active_users_count),
                    contacts_per_user = VALUES(contacts_per_user),
                    top_performer_user_id = VALUES(top_performer_user_id),
                    top_performer_contacts = VALUES(top_performer_contacts)
                """
                
                cursor.execute(insert_team_query, (
                    date_str,
                    int(team_contacts or 0),
                    int(team_calls or 0),
                    int(team_emails or 0),
                    int(team_whatsapp or 0),
                    int(team_meetings or 0),
                    round(team_response_rate or 0, 2),
                    round(team_compliance or 0, 2),
                    int(active_users or 0),
                    round(contacts_per_user, 2),
                    top_performer_id,
                    int(top_performer_contacts or 0)
                ))
                
                connection.commit()
                
                logger.info("=== RESUMO DO TIME ===")
                logger.info(f"Total contatos: {team_contacts}")
                logger.info(f"Usuários ativos: {active_users}")
                logger.info(f"Contatos por usuário: {contacts_per_user:.1f}")
                logger.info(f"Taxa resposta média: {team_response_rate:.1f}%")
                
        except Exception as e:
            logger.error(f"Erro ao gerar resumo do time: {e}")

    def generate_activity_reports(self, start_date: datetime, end_date: datetime):
        """
        Gerar relatórios de atividade para análise
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            logger.info("=== RELATÓRIOS DE ATIVIDADE ===")
            
            # 1. Ranking de vendedores por atividade
            cursor.execute("""
                SELECT 
                    user_name,
                    SUM(total_contacts) as total_contacts,
                    SUM(calls_made) as calls,
                    SUM(meetings_scheduled) as meetings,
                    AVG(avg_response_rate) as avg_response_rate,
                    AVG(followup_compliance_rate) as compliance
                FROM activity_metrics 
                WHERE metric_date BETWEEN %s AND %s
                GROUP BY user_id, user_name
                ORDER BY total_contacts DESC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            ranking = cursor.fetchall()
            
            logger.info("\n📊 RANKING POR ATIVIDADE:")
            for i, (name, contacts, calls, meetings, response, compliance) in enumerate(ranking[:5], 1):
                logger.info(f"{i}º {name}: {contacts} contatos, {calls} ligações, {meetings} reuniões")
                logger.info(f"   📈 {response:.1f}% resposta, {compliance:.1f}% compliance follow-ups")
            
            # 2. Análise de tipos de contato
            cursor.execute("""
                SELECT 
                    contact_type,
                    COUNT(*) as quantity,
                    AVG(CASE WHEN is_successful = 1 THEN 100 ELSE 0 END) as success_rate
                FROM commercial_activities 
                WHERE created_date BETWEEN %s AND %s 
                AND contact_type IN ('ligacao_feita', 'email', 'whatsapp', 'reuniao_agendada')
                GROUP BY contact_type
                ORDER BY quantity DESC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            contact_types = cursor.fetchall()
            
            logger.info("\n📞 ANÁLISE POR TIPO DE CONTATO:")
            for contact_type, quantity, success_rate in contact_types:
                logger.info(f"{contact_type}: {quantity} atividades, {success_rate:.1f}% sucesso")
            
            # 3. Análise temporal (por dia da semana)
            cursor.execute("""
                SELECT 
                    DAYNAME(created_date) as day_name,
                    COUNT(*) as activities,
                    COUNT(DISTINCT user_id) as active_users
                FROM commercial_activities 
                WHERE created_date BETWEEN %s AND %s
                GROUP BY DAYOFWEEK(created_date), DAYNAME(created_date)
                ORDER BY DAYOFWEEK(created_date)
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            daily_activity = cursor.fetchall()
            
            logger.info("\n📅 ATIVIDADE POR DIA DA SEMANA:")
            for day, activities, users in daily_activity:
                logger.info(f"{day}: {activities} atividades, {users} usuários ativos")
            
            # 4. Follow-ups compliance
            cursor.execute("""
                SELECT 
                    user_name,
                    COUNT(*) as total_followups,
                    SUM(CASE WHEN is_completed_on_time = 1 THEN 1 ELSE 0 END) as on_time,
                    ROUND(SUM(CASE WHEN is_completed_on_time = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as compliance_rate
                FROM commercial_activities 
                WHERE created_date BETWEEN %s AND %s 
                AND contact_type = 'followup'
                AND activity_type = 'task'
                GROUP BY user_id, user_name
                HAVING total_followups >= 5
                ORDER BY compliance_rate DESC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            followup_compliance = cursor.fetchall()
            
            logger.info("\n⏰ COMPLIANCE DE FOLLOW-UPS:")
            for name, total, on_time, rate in followup_compliance:
                logger.info(f"{name}: {on_time}/{total} no prazo ({rate}%)")
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatórios: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_activity_metrics_period(self, start_date: datetime, end_date: datetime):
        """
        Gerar métricas consolidadas de atividades para um período
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de métricas de atividades
            create_metrics_table = """
            CREATE TABLE IF NOT EXISTS activity_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE,
                user_id BIGINT,
                user_name VARCHAR(255),
                total_contacts INT,
                calls_made INT,
                emails_sent INT,
                whatsapp_sent INT,
                meetings_scheduled INT,
                followups_completed INT,
                followups_on_time INT,
                followup_compliance_rate DECIMAL(5,2),
                avg_response_rate DECIMAL(5,2),
                total_contact_time_minutes INT,
                activities_per_lead DECIMAL(5,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_date_user (metric_date, user_id),
                INDEX idx_metric_date (metric_date),
                INDEX idx_user_id (user_id)
            )
            """
            cursor.execute(create_metrics_table)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Limpar métricas existentes para o período
            delete_metrics_query = """
            DELETE FROM activity_metrics 
            WHERE metric_date BETWEEN %s AND %s
            """
            cursor.execute(delete_metrics_query, (start_str, end_str))
            logger.info(f"Limpas métricas existentes de {start_str} até {end_str}")
            
            # Calcular métricas por usuário para todo o período
            cursor.execute("""
                SELECT 
                    user_id,
                    user_name,
                    COUNT(*) as total_activities,
                    SUM(CASE WHEN contact_type IN ('ligacao_feita', 'ligacao_agendada') THEN 1 ELSE 0 END) as calls_made,
                    SUM(CASE WHEN contact_type = 'email' THEN 1 ELSE 0 END) as emails_sent,
                    SUM(CASE WHEN contact_type = 'whatsapp' THEN 1 ELSE 0 END) as whatsapp_sent,
                    SUM(CASE WHEN contact_type = 'reuniao_agendada' THEN 1 ELSE 0 END) as meetings_scheduled,
                    SUM(CASE WHEN contact_type = 'followup' AND is_successful = 1 THEN 1 ELSE 0 END) as followups_completed,
                    SUM(CASE WHEN contact_type = 'followup' AND is_completed_on_time = 1 THEN 1 ELSE 0 END) as followups_on_time,
                    SUM(CASE WHEN contact_type = 'followup' THEN 1 ELSE 0 END) as total_followups,
                    AVG(CASE WHEN response_rate IS NOT NULL THEN response_rate ELSE NULL END) as avg_response_rate,
                    SUM(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds ELSE 0 END) / 60 as total_time_minutes,
                    COUNT(DISTINCT entity_id) as unique_leads
                FROM commercial_activities 
                WHERE created_date BETWEEN %s AND %s AND user_id IS NOT NULL
                GROUP BY user_id, user_name
            """, (start_str, end_str))
            
            results = cursor.fetchall()
            
            # Inserir métricas
            insert_metrics_query = """
            INSERT INTO activity_metrics (
                metric_date, user_id, user_name, total_contacts, calls_made,
                emails_sent, whatsapp_sent, meetings_scheduled, followups_completed,
                followups_on_time, followup_compliance_rate, avg_response_rate,
                total_contact_time_minutes, activities_per_lead
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_contacts = VALUES(total_contacts),
                calls_made = VALUES(calls_made),
                emails_sent = VALUES(emails_sent),
                whatsapp_sent = VALUES(whatsapp_sent),
                meetings_scheduled = VALUES(meetings_scheduled),
                followups_completed = VALUES(followups_completed),
                followups_on_time = VALUES(followups_on_time),
                followup_compliance_rate = VALUES(followup_compliance_rate),
                avg_response_rate = VALUES(avg_response_rate),
                total_contact_time_minutes = VALUES(total_contact_time_minutes),
                activities_per_lead = VALUES(activities_per_lead)
            """
            
            for result in results:
                (user_id, user_name, total_activities, calls_made, emails_sent, 
                 whatsapp_sent, meetings_scheduled, followups_completed, followups_on_time,
                 total_followups, avg_response_rate, total_time_minutes, unique_leads) = result
                
                # Calcular métricas derivadas
                total_contacts = calls_made + emails_sent + whatsapp_sent + meetings_scheduled
                followup_compliance_rate = (followups_on_time / total_followups * 100) if total_followups > 0 else 0
                activities_per_lead = (total_activities / unique_leads) if unique_leads > 0 else 0
                
                cursor.execute(insert_metrics_query, (
                    start_str,  # Usar data de início como referência
                    user_id,
                    user_name,
                    total_contacts,
                    calls_made,
                    emails_sent,
                    whatsapp_sent,
                    meetings_scheduled,
                    followups_completed,
                    followups_on_time,
                    followup_compliance_rate,
                    avg_response_rate or 0,
                    total_time_minutes or 0,
                    activities_per_lead
                ))
            
            connection.commit()
            
            logger.info(f"Métricas de atividade geradas para período {start_str} até {end_str}")
            
            # Log resumo das métricas
            cursor.execute("""
                SELECT 
                    user_name,
                    total_contacts,
                    calls_made,
                    meetings_scheduled,
                    followup_compliance_rate,
                    avg_response_rate
                FROM activity_metrics 
                WHERE metric_date = %s
                ORDER BY total_contacts DESC
            """, (start_str,))
            
            summary = cursor.fetchall()
            logger.info("=== RESUMO ATIVIDADES POR VENDEDOR ===")
            for user_name, contacts, calls, meetings, compliance, response_rate in summary:
                logger.info(f"{user_name}: {contacts} contatos, {calls} ligações, {meetings} reuniões, {compliance}% compliance, {response_rate}% resposta")
            
        except Exception as e:
            logger.error(f"Erro ao gerar métricas de atividade: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def run_etl(self, start_date: datetime = None, end_date: datetime = None):
        """
        Executar ETL completo de atividades
        """
        try:
            # Definir período padrão (últimos 60 dias para capturar mais dados)
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if not end_date:
                end_date = datetime.now()
                end_date = end_date.replace(hour=23, minute=59, second=59)
            
            logger.info("=== INICIANDO ETL ATIVIDADES KOMMO ===")
            
            # 1. Extrair usuários
            logger.info("1. Extraindo usuários...")
            self.extract_users()
            
            # 2. Extrair atividades
            logger.info("2. Extraindo atividades...")
            raw_data = self.extract_activities(start_date, end_date)
            
            total_activities = (len(raw_data['calls']) + len(raw_data['tasks']) + 
                              len(raw_data['notes']) + len(raw_data['events']))
            
            if total_activities == 0:
                logger.info("Nenhuma atividade encontrada para o período")
                return
            
            # 3. Transformar dados
            logger.info("3. Transformando dados de atividades...")
            df_activities = self.transform_activity_data(raw_data)
            
            if df_activities.empty:
                logger.info("Nenhum dado de atividade para processar")
                return
            
            # 4. Carregar dados
            logger.info("4. Carregando dados de atividades...")
            self.load_activity_data(df_activities)
            
            # 5. Gerar métricas
            logger.info("5. Gerando métricas de atividade...")
            self.generate_activity_metrics_period(start_date, end_date)
            
            # 6. Gerar relatórios (opcional, para período maior)
            if (end_date - start_date).days >= 7:
                logger.info("6. Gerando relatórios de análise...")
                self.generate_activity_reports(start_date, end_date)
            
            logger.info("=== ETL ATIVIDADES CONCLUÍDO ===")
            
        except Exception as e:
            logger.error(f"Erro no ETL de atividades: {e}")
            raise


# Script principal
if __name__ == "__main__":
    etl = KommoActivityETL()
    
    # Executar para ontem
    etl.run_etl()
    
    # Ou para um período específico (com relatórios)
    # start = datetime(2025, 1, 15)
    # end = datetime(2025, 1, 22)
    # etl.run_etl(start, end)