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
from dateutil.relativedelta import relativedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_forecast_mensal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class ForecastMensalETL:
    """ETL que calcula forecast mês a mês para o futuro"""
    
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
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro na API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar dados da API: {str(e)}")
            return None
    
    def get_leads_historical_data(self, months=12):
        """Busca dados históricos de leads dos últimos N meses"""
        logger.info(f"Buscando dados históricos dos últimos {months} meses...")
        
        # Calcular data de início
        data_inicio = datetime.now() - relativedelta(months=months)
        
        all_leads = []
        page = 1
        limit = 250
        
        while True:
            params = {
                'limit': limit,
                'page': page,
                'filter[created_at][from]': int(data_inicio.timestamp()),
                'filter[created_at][to]': int(datetime.now().timestamp())
            }
            
            data = self.get_kommo_data('leads', params)
            if not data or '_embedded' not in data:
                break
                
            leads = data['_embedded']['leads']
            if not leads:
                break
                
            all_leads.extend(leads)
            logger.info(f"Página {page}: {len(leads)} leads encontrados")
            
            page += 1
            time.sleep(0.1)  # Rate limiting
            
            if len(leads) < limit:
                break
        
        logger.info(f"Total de leads encontrados: {len(all_leads)}")
        return all_leads
    
    def calculate_monthly_metrics(self, leads_data):
        """Calcula métricas mensais dos dados históricos"""
        logger.info("Calculando métricas mensais...")
        
        df_data = []
        for lead in leads_data:
            created_at = datetime.fromtimestamp(lead['created_at'])
            price = lead.get('price', 0)
            
            df_data.append({
                'created_at': created_at,
                'price': price,
                'month': created_at.month,
                'year': created_at.year,
                'is_sale': 1 if price > 0 else 0
            })
        
        df = pd.DataFrame(df_data)
        
        # Calcular métricas por mês
        monthly_metrics = df.groupby(['year', 'month']).agg({
            'price': ['sum', 'count'],
            'is_sale': 'sum'
        }).round(2)
        
        monthly_metrics.columns = ['receita_total', 'total_leads', 'vendas_fechadas']
        monthly_metrics['conversion_rate'] = (monthly_metrics['vendas_fechadas'] / monthly_metrics['total_leads'] * 100).round(2)
        monthly_metrics['ticket_medio'] = (monthly_metrics['receita_total'] / monthly_metrics['vendas_fechadas']).round(2)
        
        return monthly_metrics
    
    def generate_future_forecast(self, monthly_metrics, months_ahead=6):
        """Gera forecast para os próximos N meses"""
        logger.info(f"Gerando forecast para os próximos {months_ahead} meses...")
        
        # Calcular médias dos últimos 6 meses
        recent_months = monthly_metrics.tail(6)
        
        avg_receita = recent_months['receita_total'].mean()
        avg_leads = recent_months['total_leads'].mean()
        avg_conversao = recent_months['conversion_rate'].mean()
        avg_ticket = recent_months['ticket_medio'].mean()
        
        # Calcular tendência (crescimento/declínio)
        if len(recent_months) >= 2:
            receita_trend = (recent_months['receita_total'].iloc[-1] - recent_months['receita_total'].iloc[0]) / len(recent_months)
            leads_trend = (recent_months['total_leads'].iloc[-1] - recent_months['total_leads'].iloc[0]) / len(recent_months)
        else:
            receita_trend = 0
            leads_trend = 0
        
        # Gerar forecast para cada mês futuro
        forecast_data = []
        current_date = datetime.now()
        
        for i in range(1, months_ahead + 1):
            forecast_date = current_date + relativedelta(months=i)
            
            # Aplicar tendência
            forecast_receita = avg_receita + (receita_trend * i)
            forecast_leads = avg_leads + (leads_trend * i)
            forecast_conversao = avg_conversao  # Manter conversão estável
            forecast_ticket = avg_ticket  # Manter ticket estável
            
            # Calcular vendas esperadas
            forecast_vendas = (forecast_leads * forecast_conversao / 100)
            
            forecast_data.append({
                'data_previsao': forecast_date.date(),
                'mes': forecast_date.month,
                'ano': forecast_date.year,
                'receita_prevista': max(0, forecast_receita),  # Não permitir valores negativos
                'leads_previstos': max(0, forecast_leads),
                'vendas_previstas': max(0, forecast_vendas),
                'conversao_prevista': forecast_conversao,
                'ticket_previsto': forecast_ticket,
                'tipo': 'monthly_forecast'
            })
        
        return forecast_data, {
            'avg_receita': avg_receita,
            'avg_leads': avg_leads,
            'avg_conversao': avg_conversao,
            'avg_ticket': avg_ticket,
            'receita_trend': receita_trend,
            'leads_trend': leads_trend
        }
    
    def load_forecast_to_database(self, forecast_data, summary_metrics):
        """Carrega dados de forecast no banco de dados"""
        logger.info("Carregando forecast no banco de dados...")
        
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor()
        
        hoje = datetime.now().date()
        agora = datetime.now()
        
        # Limpar dados antigos de forecast mensal
        cursor.execute("DELETE FROM revenue_forecast WHERE tipo = 'monthly_forecast'")
        
        # Inserir cada previsão mensal
        for forecast in forecast_data:
            cursor.execute("""
                INSERT INTO revenue_forecast 
                (data_previsao, receita_prevista, dia_semana, tipo, created_date, updated_at_etl)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                forecast['data_previsao'],
                float(forecast['receita_prevista']),
                forecast['mes'],  # Usar mês como dia_semana para identificação
                forecast['tipo'],
                hoje,
                agora
            ))
        
        # Inserir resumo das métricas
        cursor.execute("""
            INSERT INTO revenue_forecast 
            (data_previsao, receita_prevista, dia_semana, tipo, created_date, updated_at_etl)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            hoje,
            float(summary_metrics['avg_receita']),
            0,  # dia_semana = 0 para resumo
            'summary_metrics',
            hoje,
            agora
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info(f"Forecast carregado: {len(forecast_data)} meses previstos")
    
    def run_etl(self):
        """Executa o ETL completo"""
        logger.info("=== INICIANDO ETL FORECAST MENSAL ===")
        
        try:
            # 1. Extrair dados históricos
            leads_data = self.get_leads_historical_data(months=12)
            
            if not leads_data:
                logger.error("Nenhum dado encontrado na API")
                return False
            
            # 2. Calcular métricas mensais
            monthly_metrics = self.calculate_monthly_metrics(leads_data)
            
            # 3. Gerar forecast futuro
            forecast_data, summary_metrics = self.generate_future_forecast(monthly_metrics, months_ahead=6)
            
            # 4. Carregar no banco
            self.load_forecast_to_database(forecast_data, summary_metrics)
            
            logger.info("=== ETL FORECAST MENSAL CONCLUÍDO COM SUCESSO ===")
            return True
            
        except Exception as e:
            logger.error(f"Erro no ETL: {str(e)}")
            return False

if __name__ == "__main__":
    etl = ForecastMensalETL()
    success = etl.run_etl()
    
    if success:
        print("ETL Forecast Mensal executado com sucesso!")
    else:
        print("Erro na execução do ETL Forecast Mensal!")
