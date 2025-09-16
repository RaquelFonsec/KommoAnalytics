import os
import mysql.connector
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from decimal import Decimal
import json
import requests
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_performance_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class PerformanceETLAPI:
    """ETL que busca dados diretamente da API do Kommo"""
    
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
            return {}
        
        users_mapping = {}
        for user in users_data.get('_embedded', {}).get('users', []):
            user_id = user.get('id')
            user_name = user.get('name', 'Usuário Não Identificado')
            user_role = user.get('role', 'Vendedor')
            
            users_mapping[user_id] = {
                'name': user_name,
                'role': user_role
            }
        
        logger.info(f"✅ Encontrados {len(users_mapping)} usuários na API")
        return users_mapping
    
    def get_sources_from_api(self):
        """Busca fontes/origens da API do Kommo"""
        logger.info("🔍 Buscando fontes da API do Kommo...")
        
        # Tentar diferentes endpoints para fontes
        endpoints = ['leads/pipelines']
        sources_mapping = {}
        
        for endpoint in endpoints:
            try:
                sources_data = self.get_kommo_data(endpoint)
                if sources_data and sources_data.get('_embedded'):
                    # Tentar diferentes estruturas de resposta
                    sources = sources_data.get('_embedded', {}).get('pipelines', [])
                    
                    for source in sources:
                        source_id = source.get('id')
                        source_name = source.get('name', f'Canal {source_id}')
                        sources_mapping[source_id] = source_name
                    
                    if sources_mapping:
                        break
            except Exception as e:
                logger.warning(f"Endpoint {endpoint} não disponível: {e}")
                continue
        
        if not sources_mapping:
            # Mapeamento padrão se não conseguir buscar da API
            sources_mapping = {
                1: 'Website',
                2: 'Facebook',
                3: 'Instagram',
                4: 'Google Ads',
                5: 'Indicação',
                6: 'WhatsApp',
                7: 'Telefone',
                8: 'Email',
                9: 'LinkedIn',
                10: 'YouTube'
            }
            logger.info("Usando mapeamento padrão de fontes")
        
        logger.info(f"✅ Encontradas {len(sources_mapping)} fontes na API")
        return sources_mapping
    
    def get_leads_from_api(self, days=30):
        """Busca leads da API do Kommo do mês atual (Setembro)"""
        logger.info(f"🔍 Buscando leads do mês atual (Setembro) da API do Kommo...")
        
        # Calcular data de início (mês atual - Setembro)
        hoje = datetime.now()
        
        # Primeiro dia do mês atual
        data_inicio = datetime(hoje.year, hoje.month, 1)
        # Data atual (hoje)
        data_fim = hoje
        
        timestamp_inicio = int(data_inicio.timestamp())
        timestamp_fim = int(data_fim.timestamp())
        
        logger.info(f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')} ({hoje.day} dias)")
        
        params = {
            'filter[created_at][from]': timestamp_inicio,
            'filter[created_at][to]': timestamp_fim,
            'limit': 250  # Máximo por página
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
            
            # Verificar se há mais páginas
            if len(leads) < 250:
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        logger.info(f"✅ Encontrados {len(all_leads)} leads na API")
        return all_leads
    
    def get_deals_from_api(self, days=30):
        """Busca deals da API do Kommo dos últimos N dias"""
        logger.info(f"🔍 Buscando deals dos últimos {days} dias da API do Kommo...")
        
        # Calcular data de início
        data_inicio = datetime.now() - timedelta(days=days)
        timestamp_inicio = int(data_inicio.timestamp())
        
        params = {
            'filter[created_at][from]': timestamp_inicio,
            'limit': 250
        }
        
        all_deals = []
        page = 1
        
        while True:
            params['page'] = page
            deals_data = self.get_kommo_data('leads', params)  # Deals são leads com status específico
            
            if not deals_data or not deals_data.get('_embedded', {}).get('leads'):
                break
            
            deals = deals_data['_embedded']['leads']
            all_deals.extend(deals)
            
            if len(deals) < 250:
                break
            
            page += 1
            time.sleep(0.5)
        
        logger.info(f"✅ Encontrados {len(all_deals)} deals na API")
        return all_deals
    
    def extract_performance_data(self, days=30):
        """Extrai dados de performance da API do Kommo"""
        logger.info("📊 Extraindo dados de performance da API do Kommo...")
        
        # Buscar dados da API
        users_mapping = self.get_users_from_api()
        sources_mapping = self.get_sources_from_api()
        leads = self.get_leads_from_api(days)
        # Não precisamos buscar deals separadamente - os leads já contêm as informações de status
        
        # Processar dados de vendedores
        vendedores_performance = {}
        canais_performance = {}
        
        # Processar leads
        for lead in leads:
            responsible_user_id = lead.get('responsible_user_id')
            pipeline_id = lead.get('pipeline_id')
            status_id = lead.get('status_id')
            price = lead.get('price', 0)
            created_at = lead.get('created_at')
            
            # Mapear usuário
            user_info = users_mapping.get(responsible_user_id, {'name': f'User_{responsible_user_id}', 'role': 'Vendedor'})
            user_name = user_info['name']
            user_role = user_info['role']
            
            # Inicializar vendedor se não existir
            if user_name not in vendedores_performance:
                vendedores_performance[user_name] = {
                    'user_id': responsible_user_id,
                    'user_name': user_name,
                    'user_role': user_role,
                    'total_leads': 0,
                    'vendas_fechadas': 0,
                    'vendas_perdidas': 0,
                    'receita_total': 0,
                    'leads': []
                }
            
            vendedores_performance[user_name]['total_leads'] += 1
            vendedores_performance[user_name]['leads'].append(lead)
            
            # Verificar se é venda fechada ou perdida
            if price > 0:  # Se tem preço, é venda fechada
                vendedores_performance[user_name]['vendas_fechadas'] += 1
                vendedores_performance[user_name]['receita_total'] += price
            elif status_id and price == 0:  # Se tem status mas sem preço, pode ser venda perdida
                vendedores_performance[user_name]['vendas_perdidas'] += 1
            
            # Processar canais
            # Buscar informações de origem do lead
            canal_origem = 'Origem Não Identificada'
            
            # Tentar extrair de campos customizados do lead primeiro
            if lead.get('custom_fields_values'):
                for field in lead.get('custom_fields_values', []):
                    field_code = field.get('field_code') or ''
                    if isinstance(field_code, str):
                        field_code = field_code.lower()
                        if any(keyword in field_code for keyword in ['utm_source', 'source', 'origem', 'canal', 'utm', 'fonte']):
                            values = field.get('values', [])
                            if values and values[0].get('value'):
                                canal_origem = values[0].get('value', 'Origem Não Identificada')
                                break
            
            # Tentar extrair de contatos se não encontrou no lead
            if canal_origem == 'Origem Não Identificada' and lead.get('_embedded', {}).get('contacts'):
                contacts = lead.get('_embedded', {}).get('contacts', [])
                if contacts:
                    contact = contacts[0]
                    # Verificar campos customizados do contato
                    if contact.get('custom_fields_values'):
                        for field in contact.get('custom_fields_values', []):
                            field_code = field.get('field_code') or ''
                            if isinstance(field_code, str):
                                field_code = field_code.lower()
                                if any(keyword in field_code for keyword in ['utm_source', 'source', 'origem', 'canal', 'utm', 'fonte']):
                                    values = field.get('values', [])
                                    if values and values[0].get('value'):
                                        canal_origem = values[0].get('value', 'Origem Não Identificada')
                                        break
            
            # Tentar usar pipeline_id como canal se ainda não identificou
            if canal_origem == 'Origem Não Identificada' and lead.get('pipeline_id'):
                pipeline_id = lead.get('pipeline_id')
                canal_origem = sources_mapping.get(pipeline_id, f'Pipeline {pipeline_id}')
            
            # Tentar usar source_id como último recurso
            if canal_origem == 'Origem Não Identificada' and lead.get('source_id'):
                source_id = lead.get('source_id')
                canal_origem = sources_mapping.get(source_id, f'Canal {source_id}')
            
            if canal_origem not in canais_performance:
                canais_performance[canal_origem] = {
                    'canal_origem': canal_origem,
                    'total_leads': 0,
                    'vendas_fechadas': 0,
                    'vendas_perdidas': 0,
                    'receita_total': 0,
                    'custo_total': 0
                }
            
            canais_performance[canal_origem]['total_leads'] += 1
        
        # Processar canais também para vendas
        for lead in leads:
            responsible_user_id = lead.get('responsible_user_id')
            price = lead.get('price', 0)
            
            # Processar canais para vendas também
            canal_origem = 'Origem Não Identificada'
            
            # Tentar extrair de campos customizados do lead primeiro
            if lead.get('custom_fields_values'):
                for field in lead.get('custom_fields_values', []):
                    field_code = field.get('field_code') or ''
                    if isinstance(field_code, str):
                        field_code = field_code.lower()
                        if any(keyword in field_code for keyword in ['utm_source', 'source', 'origem', 'canal', 'utm', 'fonte']):
                            values = field.get('values', [])
                            if values and values[0].get('value'):
                                canal_origem = values[0].get('value', 'Origem Não Identificada')
                                break
            
            # Tentar extrair de contatos se não encontrou no lead
            if canal_origem == 'Origem Não Identificada' and lead.get('_embedded', {}).get('contacts'):
                contacts = lead.get('_embedded', {}).get('contacts', [])
                if contacts:
                    contact = contacts[0]
                    # Verificar campos customizados do contato
                    if contact.get('custom_fields_values'):
                        for field in contact.get('custom_fields_values', []):
                            field_code = field.get('field_code') or ''
                            if isinstance(field_code, str):
                                field_code = field_code.lower()
                                if any(keyword in field_code for keyword in ['utm_source', 'source', 'origem', 'canal', 'utm', 'fonte']):
                                    values = field.get('values', [])
                                    if values and values[0].get('value'):
                                        canal_origem = values[0].get('value', 'Origem Não Identificada')
                                        break
            
            # Tentar usar pipeline_id como canal se ainda não identificou
            if canal_origem == 'Origem Não Identificada' and lead.get('pipeline_id'):
                pipeline_id = lead.get('pipeline_id')
                canal_origem = sources_mapping.get(pipeline_id, f'Pipeline {pipeline_id}')
            
            # Tentar usar source_id como último recurso
            if canal_origem == 'Origem Não Identificada' and lead.get('source_id'):
                source_id = lead.get('source_id')
                canal_origem = sources_mapping.get(source_id, f'Canal {source_id}')
            
            # Atualizar canais com vendas
            if canal_origem in canais_performance:
                if price > 0:  # Venda fechada
                    canais_performance[canal_origem]['vendas_fechadas'] += 1
                    canais_performance[canal_origem]['receita_total'] += price
                elif lead.get('status_id') and price == 0:  # Venda perdida
                    canais_performance[canal_origem]['vendas_perdidas'] += 1
        
        # Calcular métricas finais
        vendedores_final = []
        for vendedor in vendedores_performance.values():
            total_leads = vendedor['total_leads']
            vendas_fechadas = vendedor['vendas_fechadas']
            vendas_perdidas = vendedor['vendas_perdidas']
            receita_total = vendedor['receita_total']
            
            win_rate = (vendas_fechadas / (vendas_fechadas + vendas_perdidas) * 100) if (vendas_fechadas + vendas_perdidas) > 0 else 0
            conversion_rate = (vendas_fechadas / total_leads * 100) if total_leads > 0 else 0
            ticket_medio = (receita_total / vendas_fechadas) if vendas_fechadas > 0 else 0
            
            vendedores_final.append({
                'user_id': vendedor['user_id'],
                'user_name': vendedor['user_name'],
                'user_role': vendedor['user_role'],
                'total_leads': total_leads,
                'vendas_fechadas': vendas_fechadas,
                'vendas_perdidas': vendas_perdidas,
                'receita_total': receita_total,
                'win_rate': win_rate,
                'conversion_rate': conversion_rate,
                'ticket_medio': ticket_medio
            })
        
        canais_final = []
        for canal in canais_performance.values():
            total_leads = canal['total_leads']
            vendas_fechadas = canal['vendas_fechadas']
            vendas_perdidas = canal['vendas_perdidas']
            receita_total = canal['receita_total']
            
            win_rate = (vendas_fechadas / (vendas_fechadas + vendas_perdidas) * 100) if (vendas_fechadas + vendas_perdidas) > 0 else 0
            conversion_rate = (vendas_fechadas / total_leads * 100) if total_leads > 0 else 0
            ticket_medio = (receita_total / vendas_fechadas) if vendas_fechadas > 0 else 0
            
            canais_final.append({
                'canal_origem': canal['canal_origem'],
                'total_leads': total_leads,
                'vendas_fechadas': vendas_fechadas,
                'vendas_perdidas': vendas_perdidas,
                'receita_total': receita_total,
                'win_rate': win_rate,
                'conversion_rate': conversion_rate,
                'ticket_medio': ticket_medio
            })
        
        return {'vendedores': vendedores_final, 'canais': canais_final}
    
    def load_to_database(self, dados):
        """Carrega dados no banco de dados"""
        logger.info("💾 Carregando dados no banco...")
        
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor()
        
        # Usar data do mês atual (Setembro)
        hoje = datetime.now()
        data_setembro = datetime(hoje.year, hoje.month, 1).date()
        agora = datetime.now()
        
        # Limpar dados antigos
        cursor.execute("DELETE FROM performance_vendedores WHERE created_date = %s", (data_setembro,))
        cursor.execute("DELETE FROM performance_canais WHERE created_date = %s", (data_setembro,))
        
        # Inserir vendedores
        vendedores_inseridos = 0
        for vendedor in dados['vendedores']:
            cursor.execute("""
                INSERT INTO performance_vendedores 
                (user_id, user_name, user_role, total_leads, vendas_fechadas, vendas_perdidas,
                 receita_total, win_rate, conversion_rate, ticket_medio, tempo_resposta_medio,
                 ciclo_vendas_medio, total_atividades, atividades_concluidas, leads_contactados,
                 taxa_conclusao_atividades, created_date, updated_at_etl)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                vendedor['user_id'],
                vendedor['user_name'],
                vendedor['user_role'],
                vendedor['total_leads'],
                vendedor['vendas_fechadas'],
                vendedor['vendas_perdidas'],
                vendedor['receita_total'],
                vendedor['win_rate'],
                vendedor['conversion_rate'],
                vendedor['ticket_medio'],
                0,  # tempo_resposta_medio
                0,  # ciclo_vendas_medio
                0,  # total_atividades
                0,  # atividades_concluidas
                vendedor['total_leads'],  # leads_contactados
                0,  # taxa_conclusao_atividades
                data_setembro,
                agora
            ))
            vendedores_inseridos += 1
        
        # Inserir canais
        canais_inseridos = 0
        for canal in dados['canais']:
            cursor.execute("""
                INSERT INTO performance_canais 
                (canal_origem, utm_source, utm_medium, total_leads, vendas_fechadas, vendas_perdidas,
                 receita_total, custo_total, win_rate, conversion_rate, ticket_medio, custo_por_lead,
                 roi, tempo_resposta_medio, ciclo_vendas_medio, created_date, updated_at_etl)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                canal['canal_origem'],
                '',  # utm_source
                '',  # utm_medium
                canal['total_leads'],
                canal['vendas_fechadas'],
                canal['vendas_perdidas'],
                canal['receita_total'],
                0,  # custo_total
                canal['win_rate'],
                canal['conversion_rate'],
                canal['ticket_medio'],
                0,  # custo_por_lead
                0,  # roi
                0,  # tempo_resposta_medio
                0,  # ciclo_vendas_medio
                data_setembro,
                agora
            ))
            canais_inseridos += 1
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"✅ Inseridos {vendedores_inseridos} vendedores e {canais_inseridos} canais")
        return vendedores_inseridos, canais_inseridos

def main():
    """Execução principal"""
    try:
        logger.info("🚀 === INICIANDO ETL MÓDULO 5 - PERFORMANCE POR PESSOA E CANAL (API KOMMO) ===")
        
        etl = PerformanceETLAPI()
        
        # Extrair dados da API (mês atual - Setembro)
        dados = etl.extract_performance_data(days=30)  # Busca dados do mês atual
        
        # Carregar no banco
        etl.load_to_database(dados)
        
        # Estatísticas finais
        vendedores = dados['vendedores']
        canais = dados['canais']
        
        if vendedores:
            top_vendedor = max(vendedores, key=lambda x: x['receita_total'])
            top_conversao = max(vendedores, key=lambda x: x['conversion_rate'])
            
            logger.info(" === ETL MÓDULO 5 CONCLUÍDO COM SUCESSO (API KOMMO) ===")
            logger.info(f" PERFORMANCE DE VENDEDORES:")
            logger.info(f"   Top Receita: {top_vendedor['user_name']} - R$ {top_vendedor['receita_total']:,.2f}")
            logger.info(f"   Top Conversão: {top_conversao['user_name']} - {top_conversao['conversion_rate']:.1f}%")
            logger.info(f"   Total Vendedores Analisados: {len(vendedores)}")
        
        if canais:
            top_canal = max(canais, key=lambda x: x['receita_total'])
            top_canal_conversao = max(canais, key=lambda x: x['conversion_rate'])
            
            logger.info(f" PERFORMANCE DE CANAIS:")
            logger.info(f"   Top Receita: {top_canal['canal_origem']} - R$ {top_canal['receita_total']:,.2f}")
            logger.info(f"   Top Conversão: {top_canal_conversao['canal_origem']} - {top_canal_conversao['conversion_rate']:.1f}%")
            logger.info(f"   Total Canais Analisados: {len(canais)}")
            
    except Exception as e:
        logger.error(f" Erro durante execução do ETL: {e}")
        raise

if __name__ == "__main__":
    main()
