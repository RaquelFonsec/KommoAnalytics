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
        logging.FileHandler('etl_forecast_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class ForecastETLAPI:
    """ETL que busca dados diretamente da API do Kommo para Forecast"""
    
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
    
    def get_leads_historical_data(self, days=90):
        """Busca dados históricos de leads para análise de tendências"""
        logger.info(f"🔍 Buscando dados históricos de leads dos últimos {days} dias...")
        
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
        
        logger.info(f" Encontrados {len(all_leads)} leads históricos")
        return all_leads
    
    def calculate_forecast_metrics(self, leads_data):
        """Calcula métricas de forecast baseadas nos dados históricos"""
        logger.info(" Calculando métricas de forecast...")
        
        # Converter para DataFrame para análise
        df_data = []
        for lead in leads_data:
            created_at = datetime.fromtimestamp(lead.get('created_at', 0))
            price = lead.get('price', 0)
            status_id = lead.get('status_id')
            
            df_data.append({
                'date': created_at.date(),
                'price': price,
                'status_id': status_id,
                'is_sale': 1 if price > 0 else 0,
                'month': created_at.strftime('%Y-%m'),
                'week': created_at.isocalendar()[1],
                'day_of_week': created_at.weekday()
            })
        
        df = pd.DataFrame(df_data)
        
        # Calcular métricas por mês
        monthly_metrics = df.groupby('month').agg({
            'price': ['sum', 'count', 'mean'],
            'is_sale': 'sum'
        }).round(2)
        
        monthly_metrics.columns = ['receita_total', 'total_leads', 'ticket_medio', 'vendas_fechadas']
        monthly_metrics['conversion_rate'] = (monthly_metrics['vendas_fechadas'] / monthly_metrics['total_leads'] * 100).round(2)
        
        # Calcular tendências
        recent_months = monthly_metrics.tail(3)
        if len(recent_months) >= 2:
            # Tendência de receita
            receita_trend = recent_months['receita_total'].pct_change().mean() * 100
            # Tendência de conversão
            conversao_trend = recent_months['conversion_rate'].pct_change().mean() * 100
            # Tendência de volume
            volume_trend = recent_months['total_leads'].pct_change().mean() * 100
        else:
            receita_trend = conversao_trend = volume_trend = 0
        
        # Calcular forecast para próximo mês
        current_month = datetime.now().strftime('%Y-%m')
        if current_month in monthly_metrics.index:
            current_receita = monthly_metrics.loc[current_month, 'receita_total']
            current_conversao = monthly_metrics.loc[current_month, 'conversion_rate']
            current_volume = monthly_metrics.loc[current_month, 'total_leads']
        else:
            # Usar média dos últimos 3 meses
            current_receita = recent_months['receita_total'].mean()
            current_conversao = recent_months['conversion_rate'].mean()
            current_volume = recent_months['total_leads'].mean()
        
        # Forecast conservador (baseado na tendência)
        forecast_receita = current_receita * (1 + receita_trend/100)
        forecast_conversao = current_conversao * (1 + conversao_trend/100)
        forecast_volume = current_volume * (1 + volume_trend/100)
        
        # Calcular probabilidade de atingir meta (assumindo meta de R$ 100.000)
        meta_receita = 100000
        probabilidade_meta = min(100, (forecast_receita / meta_receita) * 100)
        
        return {
            'current_month': current_month,
            'current_receita': current_receita,
            'current_conversao': current_conversao,
            'current_volume': current_volume,
            'forecast_receita': forecast_receita,
            'forecast_conversao': forecast_conversao,
            'forecast_volume': forecast_volume,
            'receita_trend': receita_trend,
            'conversao_trend': conversao_trend,
            'volume_trend': volume_trend,
            'meta_receita': meta_receita,
            'probabilidade_meta': probabilidade_meta,
            'monthly_metrics': monthly_metrics.to_dict('index')
        }
    
    def calculate_weekly_forecast(self, leads_data):
        """Calcula forecast semanal"""
        logger.info(" Calculando forecast semanal...")
        
        # Converter para DataFrame
        df_data = []
        for lead in leads_data:
            created_at = datetime.fromtimestamp(lead.get('created_at', 0))
            price = lead.get('price', 0)
            
            df_data.append({
                'date': created_at.date(),
                'price': price,
                'is_sale': 1 if price > 0 else 0,
                'week': created_at.isocalendar()[1],
                'year': created_at.year
            })
        
        df = pd.DataFrame(df_data)
        
        # Calcular métricas por semana
        weekly_metrics = df.groupby(['year', 'week']).agg({
            'price': ['sum', 'count'],
            'is_sale': 'sum'
        }).round(2)
        
        weekly_metrics.columns = ['receita_total', 'total_leads', 'vendas_fechadas']
        weekly_metrics['conversion_rate'] = (weekly_metrics['vendas_fechadas'] / weekly_metrics['total_leads'] * 100).round(2)
        
        # Calcular média das últimas 4 semanas
        recent_weeks = weekly_metrics.tail(4)
        avg_weekly_receita = recent_weeks['receita_total'].mean()
        avg_weekly_conversao = recent_weeks['conversion_rate'].mean()
        avg_weekly_volume = recent_weeks['total_leads'].mean()
        
        # Forecast para próximas 4 semanas
        forecast_4_weeks_receita = avg_weekly_receita * 4
        forecast_4_weeks_conversao = avg_weekly_conversao
        forecast_4_weeks_volume = avg_weekly_volume * 4
        
        return {
            'avg_weekly_receita': avg_weekly_receita,
            'avg_weekly_conversao': avg_weekly_conversao,
            'avg_weekly_volume': avg_weekly_volume,
            'forecast_4_weeks_receita': forecast_4_weeks_receita,
            'forecast_4_weeks_conversao': forecast_4_weeks_conversao,
            'forecast_4_weeks_volume': forecast_4_weeks_volume,
            'weekly_metrics': weekly_metrics.to_dict('index')
        }
    
    def extract_forecast_data(self, days=90):
        """Extrai dados de forecast da API do Kommo"""
        logger.info(" Extraindo dados de forecast da API do Kommo...")
        
        # Buscar dados históricos
        leads_data = self.get_leads_historical_data(days)
        
        # Calcular métricas de forecast
        monthly_forecast = self.calculate_forecast_metrics(leads_data)
        weekly_forecast = self.calculate_weekly_forecast(leads_data)
        
        return {
            'monthly_forecast': monthly_forecast,
            'weekly_forecast': weekly_forecast,
            'total_leads_analyzed': len(leads_data)
        }
    
    def load_to_database(self, dados):
        """Carrega dados de forecast no banco de dados"""
        logger.info(" Carregando dados de forecast no banco...")
        
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor()
        
        hoje = datetime.now().date()
        agora = datetime.now()
        
        # Limpar dados antigos
        cursor.execute("DELETE FROM revenue_forecast WHERE created_date = %s", (hoje,))
        
        # Inserir forecast mensal
        monthly = dados['monthly_forecast']
        cursor.execute("""
            INSERT INTO revenue_forecast 
            (data_previsao, receita_prevista, dia_semana, tipo, created_date, updated_at_etl)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            datetime.now().date(),  # data_previsao
            float(monthly['forecast_receita']),  # receita_prevista
            1,  # dia_semana (1 = segunda)
            'monthly_forecast',  # tipo
            hoje,
            agora
        ))
        
        # Inserir forecast semanal
        weekly = dados['weekly_forecast']
        cursor.execute("""
            INSERT INTO revenue_forecast 
            (data_previsao, receita_prevista, dia_semana, tipo, created_date, updated_at_etl)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            datetime.now().date() + timedelta(days=1),  # data_previsao (dia seguinte)
            float(weekly['forecast_4_weeks_receita']),  # receita_prevista
            2,  # dia_semana (2 = terça)
            'weekly_forecast',  # tipo
            hoje,
            agora
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(" Dados de forecast inseridos no banco")
        return True

def main():
    """Execução principal"""
    try:
        logger.info(" === INICIANDO ETL MÓDULO 6 - FORECAST (API KOMMO) ===")
        
        etl = ForecastETLAPI()
        
        # Extrair dados de forecast
        dados = etl.extract_forecast_data(days=90)
        
        # Carregar no banco
        etl.load_to_database(dados)
        
        # Estatísticas finais
        monthly = dados['monthly_forecast']
        weekly = dados['weekly_forecast']
        
        logger.info(" === ETL MÓDULO 6 CONCLUÍDO COM SUCESSO (API KOMMO) ===")
        logger.info(f" FORECAST MENSAL:")
        logger.info(f"   Receita Atual: R$ {monthly['current_receita']:,.2f}")
        logger.info(f"   Receita Prevista: R$ {monthly['forecast_receita']:,.2f}")
        logger.info(f"   Tendência: {monthly['receita_trend']:+.1f}%")
        logger.info(f"   Probabilidade Meta: {monthly['probabilidade_meta']:.1f}%")
        
        logger.info(f" FORECAST SEMANAL:")
        logger.info(f"   Receita Semanal Média: R$ {weekly['avg_weekly_receita']:,.2f}")
        logger.info(f"   Receita 4 Semanas: R$ {weekly['forecast_4_weeks_receita']:,.2f}")
        logger.info(f"   Conversão Média: {weekly['avg_weekly_conversao']:.1f}%")
        
        logger.info(f" DADOS ANALISADOS:")
        logger.info(f"   Total Leads: {dados['total_leads_analyzed']}")
        
    except Exception as e:
        logger.error(f" Erro durante execução do ETL: {e}")
        raise

if __name__ == "__main__":
    main()
