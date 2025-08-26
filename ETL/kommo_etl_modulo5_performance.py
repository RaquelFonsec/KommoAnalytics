#!/usr/bin/env python3
"""
ETL para Performance por Pessoa e Canal - Kommo CRM
Módulo 5: Rankings de vendedores por receita e conversão, conversão por canal
"""

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

# ETL Módulo 5 - Performance por Pessoa e Canal - Kommo CRM
import os
import requests
import mysql.connector
from datetime import datetime, timedelta
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KommoPerformanceETL:
    def __init__(self):
        self.kommo_config = {
            'base_url': os.getenv('KOMMO_API_URL', 'https://previdas.kommo.com'),
            'access_token': os.getenv('KOMMO_ACCESS_TOKEN'),
        }
        
        self.db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'kommo_analytics',
            'password': 'previdas_ltda_2025',
            'database': 'kommo_analytics'
        }
        
        self.headers = {
            'Authorization': f'Bearer {self.kommo_config["access_token"]}',
            'Content-Type': 'application/json'
        }

    def extract_from_existing_tables(self, days=30):
        """Extrair dados das tabelas já existentes para análise de performance"""
        try:
            logger.info("📊 Extraindo dados das tabelas existentes para análise de performance...")
            
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            # 1. Dados de leads por vendedor e canal
            leads_query = """
            SELECT 
                lm.lead_id,
                lm.primary_source as canal_origem,
                lm.utm_source,
                lm.utm_medium,
                lm.utm_campaign,
                lm.created_date,
                lm.response_time_hours,
                lm.lead_cost,
                
                sm.responsible_user_name,
                sm.responsible_user_role,
                sm.status_name,
                sm.status_type,
                sm.sale_price,
                sm.sales_cycle_days,
                sm.closed_at,
                CASE WHEN sm.status_name = 'Venda ganha' THEN 1 ELSE 0 END as is_won,
                CASE WHEN sm.status_name = 'Venda perdida' THEN 1 ELSE 0 END as is_lost
                
            FROM leads_metrics lm
            LEFT JOIN sales_metrics sm ON lm.lead_id = sm.lead_id
            WHERE lm.created_date >= %s
            """
            
            cursor.execute(leads_query, (start_date,))
            leads_data = cursor.fetchall()
            
            # 2. Dados de atividades por vendedor
            atividades_query = """
            SELECT 
                user_id,
                user_name,
                user_role,
                activity_type,
                COUNT(*) as total_atividades,
                COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) as atividades_concluidas,
                COUNT(DISTINCT entity_id) as leads_contactados,
                created_date
            FROM commercial_activities
            WHERE created_date >= %s
            GROUP BY user_id, user_name, user_role, activity_type, created_date
            """
            
            cursor.execute(atividades_query, (start_date,))
            atividades_data = cursor.fetchall()
            
            # 3. Dados do funil por canal
            funil_query = """
            SELECT 
                fh.lead_id,
                fh.status_name,
                fh.entry_date,
                fh.time_in_status_hours,
                fh.loss_reason_name,
                
                lm.primary_source as canal_origem,
                lm.utm_source,
                lm.utm_medium
                
            FROM funnel_history fh
            LEFT JOIN leads_metrics lm ON fh.lead_id = lm.lead_id
            WHERE fh.entry_date >= %s
            AND fh.pipeline_id = 11146887
            """
            
            cursor.execute(funil_query, (start_date,))
            funil_data = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            logger.info(f"✅ Extraídos: {len(leads_data)} leads, {len(atividades_data)} atividades, {len(funil_data)} movimentações de funil")
            
            return {
                'leads': leads_data,
                'atividades': atividades_data,
                'funil': funil_data
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na extração de dados: {e}")
            return {'leads': [], 'atividades': [], 'funil': []}

    def transform_performance_data(self, raw_data):
        """Transformar dados para análise de performance"""
        try:
            logger.info("🔄 Transformando dados de performance...")
            
            leads_data = raw_data['leads']
            atividades_data = raw_data['atividades']
            funil_data = raw_data['funil']
            
            # 1. PERFORMANCE POR VENDEDOR
            vendedores_performance = {}
            
            for lead in leads_data:
                user_name = lead.get('responsible_user_name', 'Usuário Desconhecido')
                user_role = lead.get('responsible_user_role', 'Unknown')
                
                if user_name not in vendedores_performance:
                    vendedores_performance[user_name] = {
                        'user_id': hash(user_name) % 1000000,  # Gerar ID baseado no nome
                        'user_name': user_name,
                        'user_role': user_role,
                        'total_leads': 0,
                        'vendas_fechadas': 0,
                        'vendas_perdidas': 0,
                        'receita_total': 0.0,
                        'tempo_resposta_medio': 0.0,
                        'ciclo_vendas_medio': 0.0,
                        'leads_com_resposta': 0,
                        'leads_com_ciclo': 0,
                        'total_atividades': 0,
                        'atividades_concluidas': 0,
                        'leads_contactados': 0
                    }
                
                perf = vendedores_performance[user_name]
                perf['total_leads'] += 1
                
                if lead.get('status_name') == 'Venda ganha':
                    perf['vendas_fechadas'] += 1
                    sale_price = lead.get('sale_price', 0)
                    perf['receita_total'] += float(sale_price) if sale_price else 0.0
                    if lead.get('sales_cycle_days'):
                        cycle_days = lead.get('sales_cycle_days', 0)
                        perf['ciclo_vendas_medio'] += float(cycle_days) if cycle_days else 0.0
                        perf['leads_com_ciclo'] += 1
                
                if lead.get('status_name') == 'Venda perdida':
                    perf['vendas_perdidas'] += 1
                
                if lead.get('response_time_hours'):
                    response_time = lead.get('response_time_hours', 0)
                    perf['tempo_resposta_medio'] += float(response_time) if response_time else 0.0
                    perf['leads_com_resposta'] += 1
            
            # Calcular médias
            for user_name, perf in vendedores_performance.items():
                if perf['leads_com_resposta'] > 0:
                    perf['tempo_resposta_medio'] = perf['tempo_resposta_medio'] / perf['leads_com_resposta']
                if perf['leads_com_ciclo'] > 0:
                    perf['ciclo_vendas_medio'] = perf['ciclo_vendas_medio'] / perf['leads_com_ciclo']
                
                # Calcular métricas derivadas
                total_vendas = perf['vendas_fechadas'] + perf['vendas_perdidas']
                perf['win_rate'] = (perf['vendas_fechadas'] / total_vendas * 100) if total_vendas > 0 else 0
                perf['ticket_medio'] = (perf['receita_total'] / perf['vendas_fechadas']) if perf['vendas_fechadas'] > 0 else 0
                perf['conversion_rate'] = (perf['vendas_fechadas'] / perf['total_leads'] * 100) if perf['total_leads'] > 0 else 0
            
            # Adicionar dados de atividades
            for atividade in atividades_data:
                user_name = atividade.get('user_name', 'Usuário Desconhecido')
                if user_name in vendedores_performance:
                    perf = vendedores_performance[user_name]
                    perf['total_atividades'] += atividade.get('total_atividades', 0)
                    perf['atividades_concluidas'] += atividade.get('atividades_concluidas', 0)
                    perf['leads_contactados'] += atividade.get('leads_contactados', 0)
            
            # 2. PERFORMANCE POR CANAL
            canais_performance = {}
            
            for lead in leads_data:
                canal = lead.get('canal_origem', 'Não Classificado')
                utm_source = lead.get('utm_source', '')
                utm_medium = lead.get('utm_medium', '')
                
                # Criar chave única para canal
                canal_key = f"{canal}|{utm_source}|{utm_medium}"
                
                if canal_key not in canais_performance:
                    canais_performance[canal_key] = {
                        'canal_origem': canal,
                        'utm_source': utm_source,
                        'utm_medium': utm_medium,
                        'total_leads': 0,
                        'vendas_fechadas': 0,
                        'vendas_perdidas': 0,
                        'receita_total': 0.0,
                        'custo_total': 0.0,
                        'tempo_resposta_medio': 0.0,
                        'leads_com_resposta': 0,
                        'ciclo_vendas_medio': 0.0,
                        'leads_com_ciclo': 0
                    }
                
                perf = canais_performance[canal_key]
                perf['total_leads'] += 1
                lead_cost = lead.get('lead_cost', 0)
                perf['custo_total'] += float(lead_cost) if lead_cost else 0.0
                
                if lead.get('status_name') == 'Venda ganha':
                    perf['vendas_fechadas'] += 1
                    sale_price = lead.get('sale_price', 0)
                    perf['receita_total'] += float(sale_price) if sale_price else 0.0
                    if lead.get('sales_cycle_days'):
                        cycle_days = lead.get('sales_cycle_days', 0)
                        perf['ciclo_vendas_medio'] += float(cycle_days) if cycle_days else 0.0
                        perf['leads_com_ciclo'] += 1
                
                if lead.get('status_name') == 'Venda perdida':
                    perf['vendas_perdidas'] += 1
                
                if lead.get('response_time_hours'):
                    response_time = lead.get('response_time_hours', 0)
                    perf['tempo_resposta_medio'] += float(response_time) if response_time else 0.0
                    perf['leads_com_resposta'] += 1
            
            # Calcular métricas derivadas para canais
            for canal_key, perf in canais_performance.items():
                if perf['leads_com_resposta'] > 0:
                    perf['tempo_resposta_medio'] = perf['tempo_resposta_medio'] / perf['leads_com_resposta']
                if perf['leads_com_ciclo'] > 0:
                    perf['ciclo_vendas_medio'] = perf['ciclo_vendas_medio'] / perf['leads_com_ciclo']
                
                total_vendas = perf['vendas_fechadas'] + perf['vendas_perdidas']
                perf['win_rate'] = (perf['vendas_fechadas'] / total_vendas * 100) if total_vendas > 0 else 0
                perf['conversion_rate'] = (perf['vendas_fechadas'] / perf['total_leads'] * 100) if perf['total_leads'] > 0 else 0
                perf['custo_por_lead'] = (perf['custo_total'] / perf['total_leads']) if perf['total_leads'] > 0 else 0
                perf['roi'] = ((perf['receita_total'] - perf['custo_total']) / perf['custo_total'] * 100) if perf['custo_total'] > 0 else 0
                perf['ticket_medio'] = (perf['receita_total'] / perf['vendas_fechadas']) if perf['vendas_fechadas'] > 0 else 0
            
            logger.info(f"📊 Transformados: {len(vendedores_performance)} vendedores, {len(canais_performance)} canais")
            
            return {
                'vendedores': list(vendedores_performance.values()),
                'canais': list(canais_performance.values())
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na transformação: {e}")
            return {'vendedores': [], 'canais': []}

    def create_performance_tables(self):
        """Criar tabelas para análise de performance"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Tabela de performance por vendedor
            create_vendedores_table = """
            CREATE TABLE IF NOT EXISTS performance_vendedores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                user_name VARCHAR(255),
                user_role VARCHAR(100),
                total_leads INT DEFAULT 0,
                vendas_fechadas INT DEFAULT 0,
                vendas_perdidas INT DEFAULT 0,
                receita_total DECIMAL(15,2) DEFAULT 0.00,
                win_rate DECIMAL(5,2) DEFAULT 0.00,
                conversion_rate DECIMAL(5,2) DEFAULT 0.00,
                ticket_medio DECIMAL(15,2) DEFAULT 0.00,
                tempo_resposta_medio DECIMAL(8,2) DEFAULT 0.00,
                ciclo_vendas_medio DECIMAL(8,2) DEFAULT 0.00,
                total_atividades INT DEFAULT 0,
                atividades_concluidas INT DEFAULT 0,
                leads_contactados INT DEFAULT 0,
                taxa_conclusao_atividades DECIMAL(5,2) DEFAULT 0.00,
                created_date DATE NOT NULL,
                updated_at_etl DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_created_date (created_date),
                INDEX idx_receita (receita_total),
                INDEX idx_win_rate (win_rate),
                UNIQUE KEY unique_user_date (user_id, created_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            # Tabela de performance por canal
            create_canais_table = """
            CREATE TABLE IF NOT EXISTS performance_canais (
                id INT AUTO_INCREMENT PRIMARY KEY,
                canal_origem VARCHAR(255),
                utm_source VARCHAR(255),
                utm_medium VARCHAR(255),
                total_leads INT DEFAULT 0,
                vendas_fechadas INT DEFAULT 0,
                vendas_perdidas INT DEFAULT 0,
                receita_total DECIMAL(15,2) DEFAULT 0.00,
                custo_total DECIMAL(15,2) DEFAULT 0.00,
                win_rate DECIMAL(5,2) DEFAULT 0.00,
                conversion_rate DECIMAL(5,2) DEFAULT 0.00,
                ticket_medio DECIMAL(15,2) DEFAULT 0.00,
                custo_por_lead DECIMAL(15,2) DEFAULT 0.00,
                roi DECIMAL(8,2) DEFAULT 0.00,
                tempo_resposta_medio DECIMAL(8,2) DEFAULT 0.00,
                ciclo_vendas_medio DECIMAL(8,2) DEFAULT 0.00,
                created_date DATE NOT NULL,
                updated_at_etl DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_canal (canal_origem),
                INDEX idx_created_date (created_date),
                INDEX idx_receita (receita_total),
                INDEX idx_conversion_rate (conversion_rate),
                INDEX idx_roi (roi),
                UNIQUE KEY unique_canal_date (canal_origem, utm_source, utm_medium, created_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_vendedores_table)
            cursor.execute(create_canais_table)
            connection.commit()
            
            logger.info("✅ Tabelas de performance criadas/atualizadas")
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")

    def load_performance_data(self, performance_data):
        """Carregar dados de performance no banco"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            created_date = datetime.now().date()
            
            # Limpar dados existentes do período
            cursor.execute("DELETE FROM performance_vendedores WHERE created_date = %s", (created_date,))
            cursor.execute("DELETE FROM performance_canais WHERE created_date = %s", (created_date,))
            
            # Inserir dados de vendedores
            vendedores_insert = """
            INSERT INTO performance_vendedores 
            (user_id, user_name, user_role, total_leads, vendas_fechadas, vendas_perdidas,
             receita_total, win_rate, conversion_rate, ticket_medio, tempo_resposta_medio,
             ciclo_vendas_medio, total_atividades, atividades_concluidas, leads_contactados,
             taxa_conclusao_atividades, created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            vendedores_inserted = 0
            for vendedor in performance_data['vendedores']:
                try:
                    taxa_conclusao = (vendedor['atividades_concluidas'] / vendedor['total_atividades'] * 100) if vendedor['total_atividades'] > 0 else 0
                    
                    cursor.execute(vendedores_insert, (
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
                        vendedor['tempo_resposta_medio'],
                        vendedor['ciclo_vendas_medio'],
                        vendedor['total_atividades'],
                        vendedor['atividades_concluidas'],
                        vendedor['leads_contactados'],
                        taxa_conclusao,
                        created_date
                    ))
                    vendedores_inserted += 1
                except Exception as e:
                    logger.warning(f"Erro ao inserir vendedor {vendedor.get('user_name', 'unknown')}: {e}")
                    continue
            
            # Inserir dados de canais
            canais_insert = """
            INSERT INTO performance_canais 
            (canal_origem, utm_source, utm_medium, total_leads, vendas_fechadas, vendas_perdidas,
             receita_total, custo_total, win_rate, conversion_rate, ticket_medio, custo_por_lead,
             roi, tempo_resposta_medio, ciclo_vendas_medio, created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            canais_inserted = 0
            for canal in performance_data['canais']:
                try:
                    cursor.execute(canais_insert, (
                        canal['canal_origem'],
                        canal['utm_source'] or '',
                        canal['utm_medium'] or '',
                        canal['total_leads'],
                        canal['vendas_fechadas'],
                        canal['vendas_perdidas'],
                        canal['receita_total'],
                        canal['custo_total'],
                        canal['win_rate'],
                        canal['conversion_rate'],
                        canal['ticket_medio'],
                        canal['custo_por_lead'],
                        canal['roi'],
                        canal['tempo_resposta_medio'],
                        canal['ciclo_vendas_medio'],
                        created_date
                    ))
                    canais_inserted += 1
                except Exception as e:
                    logger.warning(f"Erro ao inserir canal {canal.get('canal_origem', 'unknown')}: {e}")
                    continue
            
            connection.commit()
            logger.info(f"✅ Carregados {vendedores_inserted} vendedores e {canais_inserted} canais no banco")
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")

    def run_etl(self):
        """Executar ETL completo do Módulo 5"""
        try:
            logger.info("🚀 === INICIANDO ETL MÓDULO 5 - PERFORMANCE POR PESSOA E CANAL ===")
            
            # 1. Criar tabelas
            self.create_performance_tables()
            
            # 2. Extrair dados das tabelas existentes
            raw_data = self.extract_from_existing_tables(days=30)
            
            if not raw_data['leads']:
                logger.warning("⚠️ Nenhum dado de lead encontrado")
                return
            
            # 3. Transformar dados
            performance_data = self.transform_performance_data(raw_data)
            
            if not performance_data['vendedores'] and not performance_data['canais']:
                logger.warning("⚠️ Nenhum dado de performance transformado")
                return
            
            # 4. Carregar dados
            self.load_performance_data(performance_data)
            
            logger.info("🎉 === ETL MÓDULO 5 CONCLUÍDO COM SUCESSO ===")
            
            # Resumo dos insights
            vendedores = performance_data['vendedores']
            canais = performance_data['canais']
            
            if vendedores:
                top_vendedor_receita = max(vendedores, key=lambda x: x['receita_total'])
                top_vendedor_conversao = max(vendedores, key=lambda x: x['win_rate'])
                
                logger.info("👥 PERFORMANCE DE VENDEDORES:")
                logger.info(f"  🥇 Top Receita: {top_vendedor_receita['user_name']} - R$ {top_vendedor_receita['receita_total']:,.2f}")
                logger.info(f"  🎯 Top Conversão: {top_vendedor_conversao['user_name']} - {top_vendedor_conversao['win_rate']:.1f}%")
                logger.info(f"  📊 Total Vendedores Analisados: {len(vendedores)}")
            
            if canais:
                top_canal_receita = max(canais, key=lambda x: x['receita_total'])
                top_canal_conversao = max(canais, key=lambda x: x['win_rate'])
                
                logger.info("📈 PERFORMANCE DE CANAIS:")
                logger.info(f"  🥇 Top Receita: {top_canal_receita['canal_origem']} - R$ {top_canal_receita['receita_total']:,.2f}")
                logger.info(f"  🎯 Top Conversão: {top_canal_conversao['canal_origem']} - {top_canal_conversao['win_rate']:.1f}%")
                logger.info(f"  📊 Total Canais Analisados: {len(canais)}")
            
        except Exception as e:
            logger.error(f"❌ Erro no ETL: {e}")

if __name__ == "__main__":
    etl = KommoPerformanceETL()
    etl.run_etl()
