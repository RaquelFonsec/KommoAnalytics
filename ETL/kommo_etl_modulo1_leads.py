# ETL COMPLETO para Entrada e Origem de Leads - Kommo CRM
import os
import requests
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class KommoLeadsETL:
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

        # Mapeamento dos campos customizados específicos do  Kommo
        self.source_field_mapping = {
            'utm_source': 47286,     # Campo utm_source
            'utm_medium': 47282,     # Campo utm_medium  
            'utm_campaign': 47284,   # Campo utm_campaign
            'utm_content': 47280,    # Campo utm_content
            'utm_term': 47288,       # Campo utm_term
            'utm_referrer': 47290,   # Campo utm_referrer
            'referrer': 47292,       # Campo referrer
            'lead_source': 1100138,  # Campo "Origem Lead"
            'gclientid': 47294,      # Google Client ID
            'gclid': 47296,          # Google Click ID
            'fbclid': 47298,         # Facebook Click ID
        }

    def standardize_source_name(self, source_name: str) -> str:
        """
        NOVO: Padronizar nomes das fontes para evitar duplicatas
        """
        if not source_name:
            return "Não Classificado"
        
        # Converter para lowercase para comparação
        source_lower = source_name.lower().strip()
        
        # Dicionário de padronização
        standardization_map = {
            # Instagram variants
            'instagram': 'Instagram',
            'insta': 'Instagram', 
            'instagran': 'Instagram',
            'instragam': 'Instagram',
            
            # Mídia Paga variants
            'midia paga': 'Mídia Paga',
            'midias pagas': 'Mídia Paga',
            'campanha paga': 'Mídia Paga',
            
            # Anúncio variants
            'anuncio': 'Anúncio',
            'anúncio': 'Anúncio',
            
            # Website variants
            'site': 'Website Direto',
            'website': 'Website Direto',
            
            # Landing Page variants
            'lp': 'Landing Page',
            'landing page': 'Landing Page',
            'lp dra. alice': 'Landing Page',
            
            # Bot variants
            'bot': 'Bot/Chatbot',
            'sem bot': 'Sem Bot',
            'chatbot': 'Bot/Chatbot',
            
            # Formulário variants
            'formulario adv': 'Formulário Advogado',
            'formulario advogado': 'Formulário Advogado',
            
            # Números e símbolos problemáticos
            '2': 'Origem Não Especificada',
            '3': 'Origem Não Especificada', 
            '4': 'Origem Não Especificada',
            '5': 'Origem Não Especificada',
            '.': 'Origem Não Especificada',
            
            # Indicação variants
            'indicacao': 'Indicação',
            'indicação': 'Indicação',
            'recomendação': 'Indicação',
            
            # TikTok
            'tik tok': 'TikTok',
            'tiktok': 'TikTok',
            
            # Meta/Facebook
            'meta ads': 'Meta Ads',
            'facebook ads': 'Meta Ads',
            'facebook': 'Meta Ads',
            'fb': 'Meta Ads',
            
            # Google
            'google ads': 'Google Ads',
            'google': 'Google Ads',
            'adwords': 'Google Ads',
            
            # Suporte/Interno
            'suporte': 'Suporte Interno',
            'paciente': 'Cliente Existente',
            'prospectei': 'Outbound',
            'webconnect': 'Ferramenta Externa',
            
            # Período/Teste
            'uso período gratuíto': 'Período Gratuito',
            'utilizava o basico': 'Upgrade Cliente',
            'já conhecia desde 2023': 'Cliente Antigo',
            'não sei': 'Origem Desconhecida'
        }
        
        # Verificar mapeamento direto
        if source_lower in standardization_map:
            return standardization_map[source_lower]
        
        # Se não encontrou mapeamento, retorna capitalizado
        return source_name.title()

    def get_custom_fields_mapping(self):
        """
        DESCOBRIR: Buscar mapeamento de campos customizados do Kommo
        Execute uma vez para descobrir os IDs dos campos
        """
        try:
            url = f"{self.kommo_config['base_url']}/api/v4/leads/custom_fields"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                fields = response.json().get('_embedded', {}).get('custom_fields', [])
                
                print("=== CAMPOS CUSTOMIZADOS DISPONÍVEIS ===")
                for field in fields:
                    field_id = field.get('id')
                    field_name = field.get('name', '').lower()
                    field_code = field.get('code', '')
                    
                    print(f"ID: {field_id} | Nome: {field.get('name')} | Code: {field_code}")
                    
                    # Detectar campos relacionados a origem
                    if any(keyword in field_name for keyword in [
                        'utm', 'source', 'origem', 'fonte', 'canal', 'referrer', 
                        'campanha', 'campaign', 'medio', 'medium'
                    ]):
                        print(f"  ⭐ CAMPO DE ORIGEM DETECTADO!")
                
                return fields
            else:
                logger.error(f"Erro ao buscar campos customizados: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar campos customizados: {e}")
            return []

    def extract_leads(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        EXTRACT - Extrair leads do Kommo API com paginação
        """
        try:
            # Converter datas para timestamp Unix
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            logger.info(f"Extraindo leads de {start_date} até {end_date}")
            
            # Inicializar estruturas de dados
            all_contacts = []
            all_leads = []
            all_events = []
            
            # 1. Buscar contatos (leads) com paginação
            try:
                page = 1
                while True:
                    contacts_url = f"{self.kommo_config['base_url']}/api/v4/contacts"
                    contacts_params = {
                        'filter[created_at][from]': start_timestamp,
                        'filter[created_at][to]': end_timestamp,
                        'limit': 250,
                        'page': page,
                        'with': 'leads,custom_fields'
                    }
                    
                    contacts_response = requests.get(
                        contacts_url, 
                        headers=self.headers, 
                        params=contacts_params
                    )
                    
                    if contacts_response.status_code == 200:
                        page_data = contacts_response.json()
                        page_contacts = page_data.get('_embedded', {}).get('contacts', [])
                        
                        if not page_contacts:
                            break
                            
                        all_contacts.extend(page_contacts)
                        logger.info(f" Contatos - Página {page}: {len(page_contacts)} contatos")
                        page += 1
                        
                        if len(page_contacts) < 250:
                            break
                            
                        time.sleep(0.5)  # Rate limiting
                    else:
                        logger.warning(f"⚠️ Erro na página {page} de contatos: {contacts_response.status_code}")
                        break
                
                logger.info(f" Total de contatos extraídos: {len(all_contacts)}")
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair contatos: {e}")
            
            # 2. Buscar leads/negócios com paginação
            try:
                page = 1
                while True:
                    leads_url = f"{self.kommo_config['base_url']}/api/v4/leads"
                    leads_params = {
                        'filter[created_at][from]': start_timestamp,
                        'filter[created_at][to]': end_timestamp,
                        'limit': 250,
                        'page': page,
                        'with': 'contacts,custom_fields'
                    }
                    
                    leads_response = requests.get(
                        leads_url, 
                        headers=self.headers, 
                        params=leads_params
                    )
                    
                    if leads_response.status_code == 200:
                        page_data = leads_response.json()
                        page_leads = page_data.get('_embedded', {}).get('leads', [])
                        
                        if not page_leads:
                            break
                            
                        all_leads.extend(page_leads)
                        logger.info(f" Leads - Página {page}: {len(page_leads)} leads")
                        page += 1
                        
                        if len(page_leads) < 250:
                            break
                            
                        time.sleep(0.5)  # Rate limiting
                    else:
                        logger.warning(f"⚠️ Erro na página {page} de leads: {leads_response.status_code}")
                        break
                
                logger.info(f" Total de leads extraídos: {len(all_leads)}")
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair leads: {e}")
            
            # 3. Buscar eventos para tempo de resposta
            try:
                events_url = f"{self.kommo_config['base_url']}/api/v4/events"
                events_params = {
                    'filter[created_at][from]': start_timestamp,
                    'filter[created_at][to]': end_timestamp,
                    'limit': 250
                }
                
                events_response = requests.get(
                    events_url, 
                    headers=self.headers, 
                    params=events_params
                )
                
                if events_response.status_code == 200:
                    events_data = events_response.json()
                    all_events = events_data.get('_embedded', {}).get('events', [])
                    logger.info(f"✅ Eventos extraídos: {len(all_events)}")
                else:
                    logger.warning(f"⚠️ Erro ao extrair eventos: {events_response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair eventos: {e}")
            
            return {
                'contacts': all_contacts,
                'leads': all_leads,
                'events': all_events
            }
            
        except Exception as e:
            logger.error(f"Erro inesperado na extração: {e}")
            raise

    def classify_lead_source_improved(self, lead: Dict) -> Dict:
        """
        MELHORADO: Classificação detalhada da origem do lead
        """
        try:
            custom_fields = lead.get('custom_fields_values', [])
            
            # Estrutura de retorno expandida
            source_info = {
                'primary_source': 'Não Classificado',
                'utm_source': None,
                'utm_medium': None, 
                'utm_campaign': None,
                'utm_content': None,
                'utm_term': None,
                'utm_referrer': None,
                'referrer': None,
                'lead_source_field': None,  # Campo "Origem Lead" específico
                'gclid': None,
                'fbclid': None,
                'gclientid': None,
                'detailed_source': 'Não Classificado'
            }
            
            if not custom_fields:
                # Fallback para pipeline se não houver campos customizados
                pipeline_id = lead.get('pipeline_id')
                source_info['primary_source'] = self.get_source_from_pipeline(pipeline_id)
                return source_info
            
            # Processar cada campo customizado
            for field in custom_fields:
                field_id = field.get('field_id')
                
                # Pegar valor do campo
                values = field.get('values', [])
                if not values:
                    continue
                    
                field_value = str(values[0].get('value', '')).strip()
                
                if not field_value or field_value.lower() in ['null', 'none', '']:
                    continue
                
                # Mapear campos por ID 
                if field_id == 47286:  # utm_source
                    source_info['utm_source'] = field_value
                elif field_id == 47282:  # utm_medium
                    source_info['utm_medium'] = field_value
                elif field_id == 47284:  # utm_campaign
                    source_info['utm_campaign'] = field_value
                elif field_id == 47280:  # utm_content
                    source_info['utm_content'] = field_value
                elif field_id == 47288:  # utm_term
                    source_info['utm_term'] = field_value
                elif field_id == 47290:  # utm_referrer
                    source_info['utm_referrer'] = field_value
                elif field_id == 47292:  # referrer
                    source_info['referrer'] = field_value
                elif field_id == 1100138:  # "Origem Lead"
                    source_info['lead_source_field'] = field_value
                elif field_id == 47296:  # gclid
                    source_info['gclid'] = field_value
                elif field_id == 47298:  # fbclid
                    source_info['fbclid'] = field_value
                elif field_id == 47294:  # gclientid
                    source_info['gclientid'] = field_value
            
            # Determinar fonte primária baseada nos dados coletados
            source_info['primary_source'] = self.determine_primary_source(source_info)
            source_info['detailed_source'] = self.get_detailed_source(source_info)
            
            return source_info
            
        except Exception as e:
            logger.warning(f"Erro ao classificar origem do lead {lead.get('id')}: {e}")
            return {
                'primary_source': 'Erro',
                'utm_source': None,
                'utm_medium': None,
                'utm_campaign': None,
                'utm_content': None,
                'utm_term': None,
                'utm_referrer': None,
                'referrer': None,
                'lead_source_field': None,
                'gclid': None,
                'fbclid': None,
                'gclientid': None,
                'detailed_source': 'Erro'
            }

    # CORREÇÃO URGENTE - Adicione estes métodos ao seu ETL

    def determine_primary_source(self, source_info: Dict) -> str:
        """
        CORRIGIDO: Método original que estava funcionando + melhorias
        """
        # Prioridade: Click IDs > Campo "Origem Lead" > UTM Source > UTM Medium > Referrer
        
        lead_source_field = source_info.get('lead_source_field', '').lower() if source_info.get('lead_source_field') else ''
        utm_source = source_info.get('utm_source', '').lower() if source_info.get('utm_source') else ''
        utm_medium = source_info.get('utm_medium', '').lower() if source_info.get('utm_medium') else ''
        referrer = source_info.get('referrer', '').lower() if source_info.get('referrer') else ''
        gclid = source_info.get('gclid')
        fbclid = source_info.get('fbclid')
        
        # 1. PRIORIDADE MÁXIMA: Click IDs (mais confiáveis)
        if gclid:
            return 'Google Ads'
        if fbclid:
            return 'Meta Ads'
        
        # 2. Campo "Origem Lead" padronizado
        if lead_source_field:
            standardized = self.standardize_source_name(lead_source_field)
            if standardized != 'Não Classificado':
                return standardized
        
        # 3. UTM Source (segunda prioridade)
        if utm_source:
            if 'google' in utm_source:
                if utm_medium and ('cpc' in utm_medium or 'paid' in utm_medium or 'ads' in utm_medium):
                    return 'Google Ads'
                else:
                    return 'Google Orgânico'
            elif any(platform in utm_source for platform in ['facebook', 'fb', 'meta']):
                return 'Meta Ads'
            elif 'instagram' in utm_source:
                return 'Instagram'
            elif 'site' in utm_source or 'website' in utm_source:
                return 'Website Direto'
            elif any(term in utm_source for term in ['lp', 'landing']):
                return 'Landing Page'
            else:
                return self.standardize_source_name(utm_source)
        
        # 4. UTM Medium
        elif utm_medium:
            if any(term in utm_medium for term in ['cpc', 'paid', 'ppc']):
                return 'Mídia Paga'
            elif any(term in utm_medium for term in ['organic', 'orgânico']):
                return 'Orgânico'
            elif 'social' in utm_medium:
                return 'Redes Sociais'
            elif any(term in utm_medium for term in ['email', 'newsletter']):
                return 'Email Marketing'
            elif 'referral' in utm_medium:
                return 'Indicação'
            else:
                return self.standardize_source_name(utm_medium)
        
        # 5. Referrer
        elif referrer:
            return self.standardize_source_name(referrer)
        
        return 'Não Classificado'

    def determine_primary_source_improved(self, source_info: Dict) -> str:
        """
        Versão melhorada da determinação de fonte primária
        """
        return self.determine_primary_source(source_info)

    def standardize_source_name(self, source_name: str) -> str:
        """
        Padronizar nomes das fontes para evitar duplicatas
        """
        if not source_name:
            return "Não Classificado"
        
        # Converter para lowercase para comparação
        source_lower = source_name.lower().strip()
        
        # Dicionário de padronização
        standardization_map = {
            # Instagram variants
            'instagram': 'Instagram',
            'insta': 'Instagram', 
            'instagran': 'Instagram',
            'instragam': 'Instagram',
            
            # Mídia Paga variants
            'midia paga': 'Mídia Paga',
            'midias pagas': 'Mídia Paga',
            'campanha paga': 'Mídia Paga',
            
            # Anúncio variants
            'anuncio': 'Anúncio',
            'anúncio': 'Anúncio',
            
            # Website variants
            'site': 'Website Direto',
            'website': 'Website Direto',
            
            # Landing Page variants
            'lp': 'Landing Page',
            'landing page': 'Landing Page',
            'lp dra. alice': 'Landing Page',
            
            # Bot variants
            'bot': 'Bot/Chatbot',
            'sem bot': 'Sem Bot',
            'chatbot': 'Bot/Chatbot',
            
            # Formulário variants
            'formulario adv': 'Formulário Advogado',
            'formulario advogado': 'Formulário Advogado',
            
            # Números e símbolos problemáticos
            '2': 'Origem Não Especificada',
            '3': 'Origem Não Especificada', 
            '4': 'Origem Não Especificada',
            '5': 'Origem Não Especificada',
            '.': 'Origem Não Especificada',
            
            # Indicação variants
            'indicacao': 'Indicação',
            'indicação': 'Indicação',
            'recomendação': 'Indicação',
            
            # TikTok
            'tik tok': 'TikTok',
            'tiktok': 'TikTok',
            
            # Meta/Facebook
            'meta ads': 'Meta Ads',
            'facebook ads': 'Meta Ads',
            'facebook': 'Meta Ads',
            'fb': 'Meta Ads',
            
            # Google
            'google ads': 'Google Ads',
            'google': 'Google Ads',
            'adwords': 'Google Ads',
            
            # Suporte/Interno
            'suporte': 'Suporte Interno',
            'paciente': 'Cliente Existente',
            'prospectei': 'Outbound',
            'webconnect': 'Ferramenta Externa',
            
            # Período/Teste
            'uso período gratuíto': 'Período Gratuito',
            'utilizava o basico': 'Upgrade Cliente',
            'já conhecia desde 2023': 'Cliente Antigo',
            'não sei': 'Origem Desconhecida'
        }
        
        # Verificar mapeamento direto
        if source_lower in standardization_map:
            return standardization_map[source_lower]
        
        # Se não encontrou mapeamento, retorna capitalizado
        return source_name.title()

    def add_data_quality_alerts(self, df: pd.DataFrame):
        """
        Adicionar alertas de qualidade dos dados
        """
        try:
            total_leads = len(df)
            
            # Calcular métricas de qualidade
            sem_utm_source = df['utm_source'].isna().sum()
            sem_origem_lead = df['lead_source_field'].isna().sum()
            nao_classificados = (df['primary_source'] == 'Não Classificado').sum()
            tempo_resposta_alto = (df['response_time_hours'] > 24).sum()
            
            # Percentuais
            pct_sem_utm = (sem_utm_source / total_leads * 100) if total_leads > 0 else 0
            pct_nao_class = (nao_classificados / total_leads * 100) if total_leads > 0 else 0
            pct_resposta_lenta = (tempo_resposta_alto / total_leads * 100) if total_leads > 0 else 0
            
            logger.warning("⚠️  ALERTAS DE QUALIDADE DOS DADOS:")
            
            if pct_sem_utm > 90:
                logger.warning(f"🚨 CRÍTICO: {pct_sem_utm:.1f}% dos leads sem UTM Source!")
                logger.warning("   → Implementar UTMs em TODAS as campanhas URGENTE")
            
            if pct_nao_class > 50:
                logger.warning(f"🚨 CRÍTICO: {pct_nao_class:.1f}% dos leads não classificados!")
                logger.warning("   → Revisar processo de classificação")
            
            if pct_resposta_lenta > 30:
                logger.warning(f"🚨 CRÍTICO: {pct_resposta_lenta:.1f}% com resposta >24h!")
                logger.warning("   → Implementar alertas automáticos")
            
            # Score geral
            score_utm = max(0, 100 - pct_sem_utm)
            score_classificacao = max(0, 100 - pct_nao_class)
            score_resposta = max(0, 100 - pct_resposta_lenta)
            score_geral = (score_utm + score_classificacao + score_resposta) / 3
            
            if score_geral < 40:
                logger.warning(f"📊 SCORE GERAL: {score_geral:.1f}% - AÇÃO URGENTE NECESSÁRIA!")
            elif score_geral < 70:
                logger.warning(f"📊 SCORE GERAL: {score_geral:.1f}% - Melhorias necessárias")
            else:
                logger.info(f"📊 SCORE GERAL: {score_geral:.1f}% - Qualidade boa")
                
        except Exception as e:
            logger.error(f"Erro nos alertas de qualidade: {e}")

    def generate_improvement_suggestions(self):
        """
        CORRIGIDO: Gerar sugestões específicas de melhoria
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            print("\n🎯 SUGESTÕES DE MELHORIA BASEADAS NOS DADOS")
            print("=" * 60)
            
            # 1. Fontes com pior tempo de resposta
            cursor.execute("""
                SELECT primary_source, AVG(response_time_hours) as avg_response, COUNT(*) as leads
                FROM leads_metrics 
                WHERE response_time_hours IS NOT NULL AND response_time_hours > 0
                GROUP BY primary_source
                HAVING COUNT(*) >= 5
                ORDER BY avg_response DESC
                LIMIT 5
            """)
            
            print("🚨 FONTES COM TEMPO DE RESPOSTA CRÍTICO:")
            print("-" * 50)
            critical_sources = cursor.fetchall()
            if critical_sources:
                for row in critical_sources:
                    fonte, tempo, leads = row
                    if tempo is not None and fonte is not None:
                        print(f"   {fonte:<20} | {tempo:6.1f}h | {leads} leads")
                        
                        if tempo > 100:
                            print(f"      → URGENTE: Implementar alertas automáticos")
                        elif tempo > 24:
                            print(f"      → Melhorar processo de atendimento")
            else:
                print("   Dados insuficientes para análise de tempo de resposta")
            
            # 2. Oportunidades de UTM (CORRIGIDO)
            cursor.execute("""
                SELECT primary_source, COUNT(*) as total,
                       SUM(CASE WHEN utm_source IS NULL OR utm_source = '' THEN 1 ELSE 0 END) as sem_utm
                FROM leads_metrics
                WHERE primary_source IS NOT NULL
                GROUP BY primary_source
                HAVING COUNT(*) >= 10 AND 
                       SUM(CASE WHEN utm_source IS NULL OR utm_source = '' THEN 1 ELSE 0 END) > COUNT(*) * 0.8
                ORDER BY total DESC
            """)
            
            print(f"\n💰 OPORTUNIDADES DE IMPLEMENTAR UTM:")
            print("-" * 50)
            utm_opportunities = cursor.fetchall()
            if utm_opportunities:
                for row in utm_opportunities:
                    fonte, total, sem_utm = row
                    if fonte is not None and total is not None and sem_utm is not None:
                        pct = (sem_utm/total*100) if total > 0 else 0
                        print(f"   {fonte:<20} | {total:3} leads | {pct:5.1f}% sem UTM")
                        fonte_clean = fonte.lower().replace(' ', '_').replace('ã', 'a').replace('ç', 'c')
                        print(f"      → Implementar: utm_source={fonte_clean}")
            else:
                print("   Nenhuma oportunidade específica identificada")
            
            # 3. Fontes com melhor performance (para replicar)
            cursor.execute("""
                SELECT primary_source, AVG(response_time_hours) as avg_response, 
                       AVG(lead_cost) as avg_cost, COUNT(*) as leads
                FROM leads_metrics 
                WHERE response_time_hours IS NOT NULL AND response_time_hours > 0
                  AND primary_source IS NOT NULL
                GROUP BY primary_source
                HAVING COUNT(*) >= 5
                ORDER BY avg_response ASC
                LIMIT 3
            """)
            
            print(f"\n✅ FONTES BENCHMARK (para replicar):")
            print("-" * 50)
            benchmark_sources = cursor.fetchall()
            if benchmark_sources:
                for row in benchmark_sources:
                    fonte, tempo, custo, leads = row
                    if fonte is not None and tempo is not None:
                        custo_str = f"R$ {custo:.2f}" if custo is not None else "N/A"
                        print(f"   {fonte:<20} | {tempo:5.1f}h | {custo_str:>8} | {leads} leads")
                        print(f"      → Replicar processo para outras fontes")
            else:
                print("   Dados insuficientes para identificar benchmarks")
            
            print(f"\n🎯 PLANO DE AÇÃO RECOMENDADO:")
            print("-" * 50)
            print("   1. URGENTE: Corrigir classificação de leads (100% não classificados)")
            print("   2. Implementar alertas automáticos para leads >2h")
            print("   3. Padronizar UTMs em todas campanhas ativas") 
            print("   4. Tornar campo 'Origem Lead' obrigatório no Kommo")
            print("   5. Treinar equipe sobre preenchimento correto")
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # USAR O MÉTODO TRANSFORM ORIGINAL (que funcionava)
    def transform_leads_data(self, raw_data: Dict) -> pd.DataFrame:
        """
        VOLTA AO MÉTODO ORIGINAL que funcionava + alertas
        """
        try:
            leads = raw_data['leads']
            events = raw_data['events']
            
            processed_leads = []
            
            logger.info(f"Transformando {len(leads)} leads...")
            
            for i, lead in enumerate(leads):
                try:
                    if i % 100 == 0:
                        logger.info(f"Processando lead {i+1}/{len(leads)}")
                    
                    # Obter informações da origem (método que funcionava)
                    source_info = self.classify_lead_source_improved(lead)
                    
                    lead_data = {
                        'lead_id': lead.get('id'),
                        'created_date': datetime.fromtimestamp(lead.get('created_at', 0)).date(),
                        'created_datetime': datetime.fromtimestamp(lead.get('created_at', 0)),
                        
                        # Dados de origem
                        'primary_source': source_info['primary_source'],
                        'utm_source': source_info['utm_source'],
                        'utm_medium': source_info['utm_medium'],
                        'utm_campaign': source_info['utm_campaign'],
                        'utm_content': source_info['utm_content'],
                        'utm_term': source_info['utm_term'],
                        'utm_referrer': source_info['utm_referrer'],
                        'referrer': source_info['referrer'],
                        'lead_source_field': source_info['lead_source_field'],
                        'gclid': source_info['gclid'],
                        'fbclid': source_info['fbclid'],
                        'gclientid': source_info['gclientid'],
                        'detailed_source': source_info['detailed_source'],
                        
                        # Dados existentes
                        'lead_value': float(lead.get('price', 0)),
                        'lead_cost': self.extract_lead_cost(lead),
                        'response_time_hours': self.calculate_response_time(lead, events),
                        'pipeline_id': lead.get('pipeline_id'),
                        'status_id': lead.get('status_id'),
                        'responsible_user_id': lead.get('responsible_user_id'),
                        'contact_count': len(lead.get('_embedded', {}).get('contacts', [])),
                        'updated_at': datetime.now()
                    }
                    
                    processed_leads.append(lead_data)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar lead {lead.get('id')}: {e}")
                    continue
            
            df = pd.DataFrame(processed_leads)
            logger.info(f"Transformados {len(df)} leads com padronização")
            
            # Adicionar alertas de qualidade
            self.add_data_quality_alerts(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na transformação: {e}")
            raise
    # (Métodos add_data_quality_alerts e generate_improvement_suggestions removidos - duplicados)

    def get_detailed_source(self, source_info: Dict) -> str:
        """
        Criar string detalhada da origem para análise granular
        """
        parts = []
        
        # Adicionar informações na ordem de prioridade
        if source_info.get('lead_source_field'):
            parts.append(f"Origem: {source_info['lead_source_field']}")
            
        if source_info.get('utm_source'):
            parts.append(f"Source: {source_info['utm_source']}")
        if source_info.get('utm_medium'):
            parts.append(f"Medium: {source_info['utm_medium']}")
        if source_info.get('utm_campaign'):
            parts.append(f"Campaign: {source_info['utm_campaign']}")
        if source_info.get('utm_content'):
            parts.append(f"Content: {source_info['utm_content']}")
        if source_info.get('utm_term'):
            parts.append(f"Term: {source_info['utm_term']}")
            
        if source_info.get('referrer'):
            parts.append(f"Referrer: {source_info['referrer']}")
            
        # Adicionar IDs de clique se existirem
        if source_info.get('gclid'):
            parts.append(f"GCLID: {source_info['gclid']}")
        if source_info.get('fbclid'):
            parts.append(f"FBCLID: {source_info['fbclid']}")
        
        return " | ".join(parts) if parts else source_info.get('primary_source', 'Não Classificado')

    def get_source_from_pipeline(self, pipeline_id: int) -> str:
        """
        Mapear pipeline para fonte (baseado nas suas imagens do dashboard)
        """
        # Ajuste estes IDs conforme seus pipelines no Kommo
        pipeline_mapping = {
            1: 'Website',
            2: 'Redes Sociais',
            3: 'Google Ads', 
            4: 'Meta Ads',
            5: 'Indicação',
            6: 'Outbound',
            7: 'Email Marketing',
            8: 'Eventos'
        }
        
        return pipeline_mapping.get(pipeline_id, 'Não Classificado')

    def calculate_response_time(self, lead: Dict, events: List[Dict]) -> Optional[float]:
        """
        Calcular tempo de resposta em horas
        """
        try:
            lead_id = lead.get('id')
            lead_created = datetime.fromtimestamp(lead.get('created_at', 0))
            
            # Buscar primeiro evento/nota relacionado ao lead
            lead_events = [
                event for event in events 
                if event.get('entity_id') == lead_id and event.get('entity_type') == 'lead'
            ]
            
            if lead_events:
                # Ordenar por data de criação
                lead_events.sort(key=lambda x: x.get('created_at', 0))
                first_response = datetime.fromtimestamp(lead_events[0].get('created_at', 0))
                
                # Calcular diferença em horas
                time_diff = (first_response - lead_created).total_seconds() / 3600
                return round(time_diff, 2)
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao calcular tempo de resposta para lead {lead.get('id')}: {e}")
            return None

    def extract_lead_cost(self, lead: Dict) -> Optional[float]:
        """
        Extrair custo do lead se disponível
        """
        try:
            custom_fields = lead.get('custom_fields_values', [])
            
            if not custom_fields:
                return None
            
            for field in custom_fields:
                field_name = field.get('field_name', '').lower()
                field_value = field.get('values', [{}])[0].get('value')
                
                # Buscar por diferentes tipos de campos de custo
                if any(keyword in field_name for keyword in [
                    'custo', 'cost', 'cac', 'custo aquisição', 'custo por lead',
                    'investimento', 'gasto', 'despesa', 'valor pago', 'custo marketing'
                ]):
                    if field_value:
                        # Limpar e converter o valor
                        value_str = str(field_value).strip()
                        # Remover símbolos de moeda e espaços
                        value_str = value_str.replace('R$', '').replace('$', '').replace(' ', '')
                        # Substituir vírgula por ponto para decimais
                        value_str = value_str.replace(',', '.')
                        # Remover caracteres não numéricos exceto ponto
                        value_str = ''.join(c for c in value_str if c.isdigit() or c == '.')
                        
                        if value_str:
                            try:
                                return float(value_str)
                            except ValueError:
                                logger.warning(f"Valor de custo inválido: {field_value}")
                                continue
            
            # Se não encontrou custo específico, tentar estimar baseado na origem
            lead_source = self.classify_lead_source_improved(lead)['primary_source']
            estimated_costs_by_source = {
                'Google Ads': 50.0,
                'Meta Ads': 35.0,
                'Instagram': 40.0,
                'LinkedIn': 80.0,
                'Email Marketing': 15.0,
                'Website': 0.0,  # Orgânico
                'Google Orgânico': 0.0,
                'Indicação': 0.0,
                'Outbound': 25.0,
                'YouTube': 30.0,
                'WhatsApp': 10.0
            }
            
            return estimated_costs_by_source.get(lead_source, 0.0)
            
        except Exception as e:
            logger.warning(f"Erro ao extrair custo do lead {lead.get('id')}: {e}")
            return None

    def transform_leads_data_v2(self, raw_data: Dict) -> pd.DataFrame:
        """
        VERSÃO MELHORADA do transform com padronização
        """
        try:
            leads = raw_data['leads']
            events = raw_data['events']
            
            processed_leads = []
            
            logger.info(f"Transformando {len(leads)} leads com melhorias...")
            
            for i, lead in enumerate(leads):
                try:
                    if i % 100 == 0:
                        logger.info(f"Processando lead {i+1}/{len(leads)}")
                    
                    # Obter informações da origem
                    source_info = self.classify_lead_source_improved(lead)
                    
                    # APLICAR PADRONIZAÇÃO
                    primary_source = self.determine_primary_source_improved(source_info)
                    
                    lead_data = {
                        'lead_id': lead.get('id'),
                        'created_date': datetime.fromtimestamp(lead.get('created_at', 0)).date(),
                        'created_datetime': datetime.fromtimestamp(lead.get('created_at', 0)),
                        
                        # Dados de origem PADRONIZADOS
                        'primary_source': primary_source,
                        'utm_source': source_info['utm_source'],
                        'utm_medium': source_info['utm_medium'],
                        'utm_campaign': source_info['utm_campaign'],
                        'utm_content': source_info['utm_content'],
                        'utm_term': source_info['utm_term'],
                        'utm_referrer': source_info['utm_referrer'],
                        'referrer': source_info['referrer'],
                        'lead_source_field': source_info['lead_source_field'],
                        'gclid': source_info['gclid'],
                        'fbclid': source_info['fbclid'],
                        'gclientid': source_info['gclientid'],
                        'detailed_source': source_info['detailed_source'],
                        
                        # Dados existentes
                        'lead_value': float(lead.get('price', 0)),
                        'lead_cost': self.extract_lead_cost(lead),
                        'response_time_hours': self.calculate_response_time(lead, events),
                        'pipeline_id': lead.get('pipeline_id'),
                        'status_id': lead.get('status_id'),
                        'responsible_user_id': lead.get('responsible_user_id'),
                        'contact_count': len(lead.get('_embedded', {}).get('contacts', [])),
                        'updated_at': datetime.now()
                    }
                    
                    processed_leads.append(lead_data)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar lead {lead.get('id')}: {e}")
                    continue
            
            df = pd.DataFrame(processed_leads)
            logger.info(f"✅ Transformados {len(df)} leads com padronização")
            
            # ADICIONAR ALERTAS DE QUALIDADE
            self.add_data_quality_alerts(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na transformação: {e}")
            raise

    def load_to_database(self, df: pd.DataFrame):
        """
        LOAD - Carregar dados para o banco MySQL
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Tabela melhorada com campos de origem detalhados
            create_table_query = """
            CREATE TABLE IF NOT EXISTS leads_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id BIGINT UNIQUE,
                created_date DATE,
                created_datetime DATETIME,
                
                -- Campos de origem detalhados
                primary_source VARCHAR(100),
                utm_source VARCHAR(255),
                utm_medium VARCHAR(255),
                utm_campaign VARCHAR(255),
                utm_content VARCHAR(255),
                utm_term VARCHAR(255),
                utm_referrer VARCHAR(255),
                referrer VARCHAR(255),
                lead_source_field VARCHAR(255),
                gclid VARCHAR(255),
                fbclid VARCHAR(255),
                gclientid VARCHAR(255),
                detailed_source TEXT,
                
                -- Campos existentes
                lead_value DECIMAL(10,2),
                lead_cost DECIMAL(10,2),
                response_time_hours DECIMAL(8,2),
                pipeline_id BIGINT,
                status_id BIGINT,
                responsible_user_id BIGINT,
                contact_count INT,
                updated_at DATETIME,
                
                -- Índices para performance
                INDEX idx_created_date (created_date),
                INDEX idx_primary_source (primary_source),
                INDEX idx_utm_source (utm_source),
                INDEX idx_utm_medium (utm_medium),
                INDEX idx_pipeline_id (pipeline_id)
            )
            """
            cursor.execute(create_table_query)
            
            # Insert melhorado
            insert_query = """
            INSERT INTO leads_metrics (
                lead_id, created_date, created_datetime, primary_source, utm_source,
                utm_medium, utm_campaign, utm_content, utm_term, utm_referrer,
                referrer, lead_source_field, gclid, fbclid, gclientid, detailed_source,
                lead_value, lead_cost, response_time_hours, pipeline_id, status_id,
                responsible_user_id, contact_count, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                primary_source = VALUES(primary_source),
                utm_source = VALUES(utm_source),
                utm_medium = VALUES(utm_medium),
                utm_campaign = VALUES(utm_campaign),
                utm_content = VALUES(utm_content),
                utm_term = VALUES(utm_term),
                utm_referrer = VALUES(utm_referrer),
                referrer = VALUES(referrer),
                lead_source_field = VALUES(lead_source_field),
                gclid = VALUES(gclid),
                fbclid = VALUES(fbclid),
                gclientid = VALUES(gclientid),
                detailed_source = VALUES(detailed_source),
                lead_value = VALUES(lead_value),
                lead_cost = VALUES(lead_cost),
                response_time_hours = VALUES(response_time_hours),
                updated_at = VALUES(updated_at)
            """
            
            # Converter DataFrame para lista de tuplas
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    int(row['lead_id']),
                    row['created_date'],
                    row['created_datetime'],
                    row['primary_source'],
                    row['utm_source'],
                    row['utm_medium'], 
                    row['utm_campaign'],
                    row['utm_content'],
                    row['utm_term'],
                    row['utm_referrer'],
                    row['referrer'],
                    row['lead_source_field'],
                    row['gclid'],
                    row['fbclid'],
                    row['gclientid'],
                    row['detailed_source'],
                    float(row['lead_value']) if pd.notna(row['lead_value']) else 0,
                    float(row['lead_cost']) if pd.notna(row['lead_cost']) else None,
                    float(row['response_time_hours']) if pd.notna(row['response_time_hours']) else None,
                    int(row['pipeline_id']) if pd.notna(row['pipeline_id']) else None,
                    int(row['status_id']) if pd.notna(row['status_id']) else None,
                    int(row['responsible_user_id']) if pd.notna(row['responsible_user_id']) else None,
                    int(row['contact_count']) if pd.notna(row['contact_count']) else 0,
                    row['updated_at']
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            connection.commit()
            
            logger.info(f" Carregados {len(data_to_insert)} registros com origem detalhada")
            
        except mysql.connector.Error as e:
            logger.error(f"Erro no banco de dados: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_daily_metrics(self, date: datetime):
        """
        Gerar métricas diárias consolidadas
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Criar tabela de métricas diárias se não existir
            create_metrics_table = """
            CREATE TABLE IF NOT EXISTS daily_leads_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_date DATE UNIQUE,
                total_leads INT,
                leads_by_source JSON,
                avg_response_time_hours DECIMAL(8,2),
                total_lead_value DECIMAL(12,2),
                total_lead_cost DECIMAL(12,2),
                cost_per_lead DECIMAL(10,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_metric_date (metric_date)
            )
            """
            cursor.execute(create_metrics_table)
            
            # Calcular métricas do dia
            date_str = date.strftime('%Y-%m-%d')
            
            # Total de leads
            cursor.execute("""
                SELECT COUNT(*) FROM leads_metrics 
                WHERE created_date = %s
            """, (date_str,))
            total_leads = cursor.fetchone()[0]
            
            # Leads por fonte
            cursor.execute("""
                SELECT primary_source, COUNT(*) 
                FROM leads_metrics 
                WHERE created_date = %s 
                GROUP BY primary_source
            """, (date_str,))
            leads_by_source = dict(cursor.fetchall())
            
            # Tempo médio de resposta
            cursor.execute("""
                SELECT AVG(response_time_hours) 
                FROM leads_metrics 
                WHERE created_date = %s AND response_time_hours IS NOT NULL
            """, (date_str,))
            avg_response_time = cursor.fetchone()[0] or 0
            
            # Valor total dos leads
            cursor.execute("""
                SELECT SUM(lead_value) 
                FROM leads_metrics 
                WHERE created_date = %s
            """, (date_str,))
            total_lead_value = cursor.fetchone()[0] or 0
            
            # Custo total dos leads
            cursor.execute("""
                SELECT SUM(lead_cost) 
                FROM leads_metrics 
                WHERE created_date = %s AND lead_cost IS NOT NULL
            """, (date_str,))
            total_lead_cost = cursor.fetchone()[0] or 0
            
            # Custo por lead
            cost_per_lead = (total_lead_cost / total_leads) if total_leads > 0 else 0
            
            # Inserir métricas consolidadas
            insert_metrics_query = """
            INSERT INTO daily_leads_metrics (
                metric_date, total_leads, leads_by_source, avg_response_time_hours,
                total_lead_value, total_lead_cost, cost_per_lead
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_leads = VALUES(total_leads),
                leads_by_source = VALUES(leads_by_source),
                avg_response_time_hours = VALUES(avg_response_time_hours),
                total_lead_value = VALUES(total_lead_value),
                total_lead_cost = VALUES(total_lead_cost),
                cost_per_lead = VALUES(cost_per_lead)
            """
            
            import json
            cursor.execute(insert_metrics_query, (
                date_str,
                total_leads,
                json.dumps(leads_by_source),
                float(avg_response_time),
                float(total_lead_value),
                float(total_lead_cost),
                float(cost_per_lead)
            ))
            
            connection.commit()
            
            logger.info(f"Métricas diárias geradas para {date_str}")
            logger.info(f"   - Total leads: {total_leads}")
            logger.info(f"   - Leads por fonte: {leads_by_source}")
            logger.info(f"   - Tempo médio resposta: {avg_response_time:.2f}h")
            logger.info(f"   - Custo por lead: R$ {cost_per_lead:.2f}")
            
        except Exception as e:
            logger.error(f"Erro ao gerar métricas diárias: {e}")
            raise
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def verify_data_quality(self):
        """
        CORRIGIDO: Verificar qualidade dos dados após ETL
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            print("\n🔍 VERIFICAÇÃO DE QUALIDADE DOS DADOS")
            print("=" * 60)
            
            # 1. Estatísticas gerais
            cursor.execute("SELECT COUNT(*) FROM leads_metrics")
            total_leads = cursor.fetchone()[0]
            
            print(f"\n📊 ESTATÍSTICAS GERAIS:")
            print(f"   Total de leads: {total_leads:,}")
            
            # 2. Análise de campos vazios
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN utm_source IS NULL OR utm_source = '' THEN 1 ELSE 0 END) as sem_utm_source,
                    SUM(CASE WHEN utm_medium IS NULL OR utm_medium = '' THEN 1 ELSE 0 END) as sem_utm_medium,
                    SUM(CASE WHEN utm_campaign IS NULL OR utm_campaign = '' THEN 1 ELSE 0 END) as sem_utm_campaign,
                    SUM(CASE WHEN lead_source_field IS NULL OR lead_source_field = '' THEN 1 ELSE 0 END) as sem_origem_lead,
                    SUM(CASE WHEN primary_source = 'Não Classificado' THEN 1 ELSE 0 END) as nao_classificados
                FROM leads_metrics
            """)
            
            sem_utm_source, sem_utm_medium, sem_utm_campaign, sem_origem_lead, nao_classificados = cursor.fetchone()
            
            print(f"\n❌ LEADS SEM DADOS:")
            print(f"   Sem UTM Source:      {sem_utm_source:,} ({sem_utm_source/total_leads*100:5.1f}%)")
            print(f"   Sem UTM Medium:      {sem_utm_medium:,} ({sem_utm_medium/total_leads*100:5.1f}%)")
            print(f"   Sem UTM Campaign:    {sem_utm_campaign:,} ({sem_utm_campaign/total_leads*100:5.1f}%)")
            print(f"   Sem Origem Lead:     {sem_origem_lead:,} ({sem_origem_lead/total_leads*100:5.1f}%)")
            print(f"   'Não Classificados': {nao_classificados:,} ({nao_classificados/total_leads*100:5.1f}%)")
            
            # 3. Análise por fonte primária (CORRIGIDO)
            cursor.execute("""
                SELECT 
                    primary_source,
                    COUNT(*) as total,
                    SUM(CASE WHEN utm_source IS NULL OR utm_source = '' THEN 1 ELSE 0 END) as sem_utm_source,
                    SUM(CASE WHEN utm_medium IS NULL OR utm_medium = '' THEN 1 ELSE 0 END) as sem_utm_medium
                FROM leads_metrics
                GROUP BY primary_source
                ORDER BY total DESC
                LIMIT 10
            """)
            
            print(f"\n🎯 ANÁLISE POR FONTE PRIMÁRIA (Top 10):")
            print("-" * 70)
            print(f"{'Fonte':<20} {'Total':>6} {'Sem UTM Source':>14} {'Sem UTM Medium':>15}")
            print("-" * 70)
            
            for row in cursor.fetchall():
                fonte, total, sem_utm_s, sem_utm_m = row
                # CORREÇÃO: Verificar se os valores não são None
                fonte_str = fonte[:18] if fonte else "N/A"
                total_val = total if total is not None else 0
                sem_utm_s_val = sem_utm_s if sem_utm_s is not None else 0
                sem_utm_m_val = sem_utm_m if sem_utm_m is not None else 0
                
                print(f"{fonte_str:<20} {total_val:>6} {sem_utm_s_val:>14} {sem_utm_m_val:>15}")
            
            # 4. Qualidade por período
            cursor.execute("""
                SELECT 
                    DATE(created_date) as data,
                    COUNT(*) as total_leads,
                    SUM(CASE WHEN utm_source IS NOT NULL AND utm_source != '' THEN 1 ELSE 0 END) as com_utm,
                    SUM(CASE WHEN primary_source != 'Não Classificado' THEN 1 ELSE 0 END) as classificados
                FROM leads_metrics
                WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(created_date)
                ORDER BY data DESC
            """)
            
            print(f"\n QUALIDADE DOS ÚLTIMOS 7 DIAS:")
            print("-" * 60)
            print(f"{'Data':<12} {'Total':>6} {'Com UTM':>8} {'Classificados':>13}")
            print("-" * 60)
            
            recent_results = cursor.fetchall()
            if recent_results:
                for row in recent_results:
                    data, total, com_utm, classificados = row
                    # CORREÇÃO: Verificar valores None
                    data_str = str(data) if data else "N/A"
                    total_val = total if total is not None else 0
                    com_utm_val = com_utm if com_utm is not None else 0
                    class_val = classificados if classificados is not None else 0
                    
                    print(f"{data_str:<12} {total_val:>6} {com_utm_val:>8} {class_val:>13}")
            else:
                print("   Nenhum dado encontrado para os últimos 7 dias")
            
            # 5. Score de qualidade
            score_utm = ((total_leads - sem_utm_source) / total_leads * 100) if total_leads > 0 else 0
            score_classificacao = ((total_leads - nao_classificados) / total_leads * 100) if total_leads > 0 else 0
            score_geral = (score_utm + score_classificacao) / 2
            
            print(f"\n SCORE DE QUALIDADE DOS DADOS:")
            print(f"   UTM Tracking:     {score_utm:5.1f}%")
            print(f"   Classificação:    {score_classificacao:5.1f}%")
            print(f"   Score Geral:      {score_geral:5.1f}%")
            
            # 6. Recomendações baseadas no score
            print(f"\n💡 RECOMENDAÇÕES:")
            print("-" * 40)
            
            if score_geral < 30:
                print("    CRÍTICO - Implementação urgente de rastreamento")
                print("      → UTMs obrigatórios em todas campanhas")
                print("      → Campo 'Origem Lead' obrigatório")
                print("      → Treinamento da equipe ASAP")
            elif score_geral < 60:
                print("   ⚠️  BAIXO - Melhorias necessárias")
                print("      → Padronizar UTMs")
                print("      → Melhorar processo de classificação")
            elif score_geral < 80:
                print("    BOM - Ajustes pontuais")
                print("      → Otimizar campanhas sem UTM")
                print("      → Revisar leads não classificados")
            else:
                print("    EXCELENTE - Manter qualidade")
                print("      → Monitoramento contínuo")
            
            # 7. Leads recentes com problemas (para investigação)
            cursor.execute("""
                SELECT lead_id, created_date, primary_source, pipeline_id
                FROM leads_metrics
                WHERE primary_source = 'Não Classificado'
                AND (utm_source IS NULL OR utm_source = '')
                AND (lead_source_field IS NULL OR lead_source_field = '')
                ORDER BY created_date DESC
                LIMIT 5
            """)
            
            print(f"\n EXEMPLOS DE LEADS PROBLEMÁTICOS:")
            print("-" * 50)
            problematic = cursor.fetchall()
            if problematic:
                for row in problematic:
                    lead_id, data, fonte, pipeline = row
                    data_str = str(data) if data else "N/A"
                    fonte_str = fonte if fonte else "N/A"
                    pipeline_val = pipeline if pipeline is not None else "N/A"
                    print(f"   Lead {lead_id} | {data_str} | {fonte_str} | Pipeline: {pipeline_val}")
            else:
                print("   Nenhum lead problemático encontrado")
            
            print(f"\n Verificação de qualidade concluída!")
            
        except Exception as e:
            logger.error(f"Erro ao verificar qualidade dos dados: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def generate_source_analysis_report(self, start_date: datetime, end_date: datetime):
        """
        NOVO: Gerar relatório completo de análise de origens
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            date_filter = "WHERE created_date BETWEEN %s AND %s"
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            print(f"\n" + "="*80)
            print(f" RELATÓRIO DE ENTRADA E ORIGEM DE LEADS ({start_str} a {end_str})")
            print("="*80)
            
            # 1. RESUMO GERAL
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_leads,
                    SUM(lead_value) as total_value,
                    AVG(lead_cost) as avg_cost,
                    AVG(response_time_hours) as avg_response_time,
                    COUNT(DISTINCT primary_source) as unique_sources
                FROM leads_metrics {date_filter}
            """, (start_str, end_str))
            
            summary = cursor.fetchone()
            total_leads, total_value, avg_cost, avg_response, unique_sources = summary
            
            print(f"\n RESUMO GERAL:")
            print(f"   • Total de Leads: {total_leads:,}")
            print(f"   • Valor Total: R$ {total_value:,.2f}")
            print(f"   • Custo Médio por Lead: R$ {avg_cost:.2f}" if avg_cost else "   • Custo Médio por Lead: N/A")
            print(f"   • Tempo Médio de Resposta: {avg_response:.1f}h" if avg_response else "   • Tempo Médio de Resposta: N/A")
            print(f"   • Fontes Únicas: {unique_sources}")
            
            # 2. LEADS POR FONTE PRIMÁRIA
            cursor.execute(f"""
                SELECT 
                    primary_source, 
                    COUNT(*) as total_leads, 
                    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads_metrics {date_filter})), 1) as percentage,
                    SUM(lead_value) as total_value,
                    AVG(lead_cost) as avg_cost,
                    AVG(response_time_hours) as avg_response_time
                FROM leads_metrics {date_filter}
                GROUP BY primary_source 
                ORDER BY total_leads DESC
            """, (start_str, end_str, start_str, end_str))
            
            print(f"\n LEADS POR FONTE PRIMÁRIA:")
            print("-" * 80)
            for row in cursor.fetchall():
                source, leads, percentage, value, cost, response = row
                cost_str = f"R$ {cost:.2f}" if cost else "N/A"
                response_str = f"{response:.1f}h" if response else "N/A"
                print(f"   {source:<20} | {leads:>4} leads ({percentage:>5.1f}%) | Valor: R$ {value:>8,.2f} | Custo: {cost_str:>8} | Resposta: {response_str:>6}")
            
            # 3. ANÁLISE UTM DETALHADA
            cursor.execute(f"""
                SELECT utm_source, utm_medium, COUNT(*) as leads
                FROM leads_metrics 
                {date_filter} AND utm_source IS NOT NULL
                GROUP BY utm_source, utm_medium 
                ORDER BY leads DESC
                LIMIT 10
            """, (start_str, end_str))
            
            print(f"\n TOP 10 COMBINAÇÕES UTM:")
            print("-" * 50)
            utm_results = cursor.fetchall()
            if utm_results:
                for row in utm_results:
                    source, medium, leads = row
                    medium_str = medium if medium else "N/A"
                    print(f"   {source:<15} / {medium_str:<15} | {leads:>3} leads")
            else:
                print("    Nenhum dado UTM encontrado")
            
            # 4. CAMPANHAS MAIS EFETIVAS
            cursor.execute(f"""
                SELECT utm_campaign, COUNT(*) as leads, SUM(lead_value) as value
                FROM leads_metrics 
                {date_filter} AND utm_campaign IS NOT NULL
                GROUP BY utm_campaign 
                ORDER BY leads DESC
                LIMIT 10
            """, (start_str, end_str))
            
            print(f"\n TOP 10 CAMPANHAS:")
            print("-" * 60)
            campaign_results = cursor.fetchall()
            if campaign_results:
                for row in campaign_results:
                    campaign, leads, value = row
                    print(f"   {campaign:<35} | {leads:>3} leads | R$ {value:>8,.2f}")
            else:
                print("    Nenhuma campanha UTM encontrada")
            
            # 5. ANÁLISE DO CAMPO "ORIGEM LEAD"
            cursor.execute(f"""
                SELECT lead_source_field, COUNT(*) as leads
                FROM leads_metrics 
                {date_filter} AND lead_source_field IS NOT NULL
                GROUP BY lead_source_field 
                ORDER BY leads DESC
                LIMIT 10
            """, (start_str, end_str))
            
            print(f"\n CAMPO 'ORIGEM LEAD' (Top 10):")
            print("-" * 50)
            origem_results = cursor.fetchall()
            if origem_results:
                for row in origem_results:
                    origem, leads = row
                    print(f"   {origem:<30} | {leads:>3} leads")
            else:
                print("    Nenhum dado no campo 'Origem Lead'")
            
            # 6. TRÁFEGO PAGO (CLIDs)
            cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN gclid IS NOT NULL THEN 'Google Ads (GCLID)'
                        WHEN fbclid IS NOT NULL THEN 'Meta Ads (FBCLID)'
                        ELSE 'Orgânico/Outros'
                    END as traffic_type,
                    COUNT(*) as leads,
                    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads_metrics {date_filter})), 1) as percentage
                FROM leads_metrics {date_filter}
                GROUP BY traffic_type
                ORDER BY leads DESC
            """, (start_str, end_str, start_str, end_str))
            
            print(f"\n ANÁLISE TRÁFEGO PAGO vs ORGÂNICO:")
            print("-" * 50)
            for row in cursor.fetchall():
                traffic_type, leads, percentage = row
                print(f"   {traffic_type:<25} | {leads:>4} leads ({percentage:>5.1f}%)")
            
            # 7. TEMPO DE RESPOSTA POR FONTE
            cursor.execute(f"""
                SELECT 
                    primary_source,
                    AVG(response_time_hours) as avg_response,
                    COUNT(*) as leads_with_response
                FROM leads_metrics 
                {date_filter} AND response_time_hours IS NOT NULL
                GROUP BY primary_source
                HAVING COUNT(*) >= 5
                ORDER BY avg_response ASC
            """, (start_str, end_str))
            
            print(f"\n TEMPO DE RESPOSTA POR FONTE (mín. 5 leads):")
            print("-" * 50)
            response_results = cursor.fetchall()
            if response_results:
                for row in response_results:
                    source, avg_response, count = row
                    print(f"   {source:<20} | {avg_response:>6.1f}h (de {count} leads)")
            else:
                print("    Dados insuficientes de tempo de resposta")
            
            # 8. CUSTO POR LEAD POR FONTE
            cursor.execute(f"""
                SELECT 
                    primary_source,
                    AVG(lead_cost) as avg_cost,
                    COUNT(*) as leads_with_cost
                FROM leads_metrics 
                {date_filter} AND lead_cost IS NOT NULL AND lead_cost > 0
                GROUP BY primary_source
                HAVING COUNT(*) >= 3
                ORDER BY avg_cost DESC
            """, (start_str, end_str))
            
            print(f"\n CUSTO POR LEAD POR FONTE (mín. 3 leads):")
            print("-" * 50)
            cost_results = cursor.fetchall()
            if cost_results:
                for row in cost_results:
                    source, avg_cost, count = row
                    print(f"   {source:<20} | R$ {avg_cost:>7.2f} (de {count} leads)")
            else:
                print("    Dados insuficientes de custo")
            
            # 9. PERFORMANCE SEMANAL
            cursor.execute(f"""
                SELECT 
                    WEEK(created_date) as week_num,
                    COUNT(*) as leads,
                    AVG(response_time_hours) as avg_response
                FROM leads_metrics 
                {date_filter}
                GROUP BY WEEK(created_date)
                ORDER BY week_num
            """, (start_str, end_str))
            
            print(f"\n PERFORMANCE SEMANAL:")
            print("-" * 40)
            week_results = cursor.fetchall()
            if week_results:
                for row in week_results:
                    week, leads, avg_response = row
                    response_str = f"{avg_response:.1f}h" if avg_response else "N/A"
                    print(f"   Semana {week:<2} | {leads:>3} leads | Resposta: {response_str}")
            else:
                print("    Dados insuficientes para análise semanal")
            
            print("\n" + "="*80)
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def run_etl(self, start_date: datetime = None, end_date: datetime = None):
        """
        Executar o ETL completo para Entrada e Origem de Leads
        """
        try:
            # Definir período padrão (últimos 30 dias)
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if not end_date:
                end_date = datetime.now().replace(hour=23, minute=59, second=59)
            
            logger.info("="*60)
            logger.info(" INICIANDO ETL KOMMO - ENTRADA E ORIGEM DE LEADS")
            logger.info("="*60)
            
            # EXTRACT
            logger.info("1️  EXTRACT - Extraindo dados do Kommo...")
            raw_data = self.extract_leads(start_date, end_date)
            
            # TRANSFORM
            logger.info("2️  TRANSFORM - Transformando e classificando dados...")
            df_leads = self.transform_leads_data(raw_data)
            
            if df_leads.empty:
                logger.warning("⚠️  Nenhum lead encontrado para o período")
                return
            
            # LOAD
            logger.info("3️  LOAD - Carregando no banco de dados...")
            self.load_to_database(df_leads)
            
            # GENERATE METRICS
            logger.info("4️  METRICS - Gerando métricas diárias...")
            # Gerar métricas para cada dia no período
            current_date = start_date
            while current_date <= end_date:
                self.generate_daily_metrics(current_date)
                current_date += timedelta(days=1)
            
            # GENERATE REPORT
            logger.info("5️  REPORT - Gerando relatório de análise...")
            self.generate_source_analysis_report(start_date, end_date)
            
            # GENERATE SUGGESTIONS
            logger.info("6️  SUGGESTIONS - Gerando sugestões de melhoria...")
            self.generate_improvement_suggestions()
            
            # CHECK DATA QUALITY
            logger.info("7️  QUALITY - Verificando qualidade dos dados...")
            self.verify_data_quality()
            
            logger.info("="*60)
            logger.info(" ETL CONCLUÍDO COM SUCESSO!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f" Erro no ETL: {e}")
            raise


# Script principal
if __name__ == "__main__":
    etl = KommoLeadsETL()
    
    # Opção 1: Descobrir campos customizados (execute primeiro)
    print(" Descobrindo campos customizados...")
    # etl.get_custom_fields_mapping()
    
    # Opção 2: Executar ETL para período específico
    # start = datetime(2025, 1, 1)
    # end = datetime(2025, 1, 31)
    # etl.run_etl(start, end)
    
    # Opção 3: Executar ETL para últimos 30 dias (padrão)
    etl.run_etl()
    
    # Opção 4: Gerar apenas relatório para período específico
    # start = datetime(2025, 1, 1)
    # end = datetime(2025, 1, 31)
    # etl.generate_source_analysis_report(start, end)