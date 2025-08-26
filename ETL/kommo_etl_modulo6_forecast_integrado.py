# ETL Módulo 6 - Previsibilidade (Forecast) Integrado
# Baseado nos dados reais dos Módulos 1 a 5 do mês atual
import os
import mysql.connector
from datetime import datetime, timedelta, date
import logging
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class KommoForecastIntegradoETL:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'kommo_analytics'),
            'password': os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            'database': os.getenv('DB_NAME', 'kommo_analytics')
        }

    def extract_modulos_data(self, mes_ano):
        """Extrair dados consolidados dos Módulos 1 a 5 do mês"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # MÓDULO 1: Entrada e Origem de Leads
            modulo1_query = """
            SELECT 
                COUNT(DISTINCT lead_id) as total_leads,
                COUNT(DISTINCT CASE WHEN primary_source IS NOT NULL THEN lead_id END) as leads_classificados,
                COALESCE(AVG(response_time_hours), 0) as tempo_resposta_medio,
                COALESCE(SUM(lead_cost), 0) as custo_total_leads
            FROM leads_metrics 
            WHERE DATE_FORMAT(created_date, '%Y-%m') = %s
            """
            
            # MÓDULO 2: Funil de Conversão
            modulo2_query = """
            SELECT 
                COUNT(DISTINCT lead_id) as leads_no_funil,
                COUNT(DISTINCT CASE WHEN status_name = 'Venda ganha' THEN lead_id END) as vendas_ganhas,
                COUNT(DISTINCT CASE WHEN status_name = 'Venda perdida' THEN lead_id END) as vendas_perdidas,
                AVG(time_in_status_hours) as tempo_medio_status
            FROM funnel_history 
            WHERE DATE_FORMAT(created_at, '%Y-%m') = %s
            """
            
            # MÓDULO 3: Atividades Comerciais
            modulo3_query = """
            SELECT 
                COUNT(DISTINCT entity_id) as leads_contatados,
                COUNT(DISTINCT user_id) as vendedores_ativos,
                COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) as atividades_concluidas,
                COUNT(*) as total_atividades,
                ROUND(COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao
            FROM commercial_activities 
            WHERE DATE_FORMAT(created_date, '%Y-%m') = %s
            """
            
            # MÓDULO 4: Conversão e Receita
            modulo4_query = """
            SELECT 
                COUNT(DISTINCT lead_id) as total_negociacoes,
                COUNT(DISTINCT CASE WHEN status_name = 'Venda ganha' THEN lead_id END) as vendas_fechadas,
                COUNT(DISTINCT CASE WHEN status_name = 'Venda perdida' THEN lead_id END) as vendas_perdidas,
                COALESCE(SUM(CASE WHEN status_name = 'Venda ganha' THEN sale_price ELSE 0 END), 0) as receita_total,
                COALESCE(AVG(CASE WHEN status_name = 'Venda ganha' THEN sale_price END), 0) as ticket_medio,
                ROUND(COUNT(DISTINCT CASE WHEN status_name = 'Venda ganha' THEN lead_id END) / 
                      NULLIF(COUNT(DISTINCT CASE WHEN status_name IN ('Venda ganha', 'Venda perdida') THEN lead_id END), 0) * 100, 1) as win_rate
            FROM sales_metrics 
            WHERE DATE_FORMAT(created_date, '%Y-%m') = %s
            """
            
            # MÓDULO 5: Performance por Pessoa e Canal
            modulo5_query = """
            SELECT 
                COUNT(DISTINCT user_id) as vendedores_unicos,
                COUNT(DISTINCT entity_id) as leads_contactados,
                COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) as atividades_concluidas,
                ROUND(COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao_geral
            FROM commercial_activities 
            WHERE DATE_FORMAT(created_date, '%Y-%m') = %s AND user_id IS NOT NULL
            """
            
            # Executar queries
            cursor.execute(modulo1_query, (mes_ano,))
            modulo1 = cursor.fetchone()
            
            cursor.execute(modulo2_query, (mes_ano,))
            modulo2 = cursor.fetchone()
            
            cursor.execute(modulo3_query, (mes_ano,))
            modulo3 = cursor.fetchone()
            
            cursor.execute(modulo4_query, (mes_ano,))
            modulo4 = cursor.fetchone()
            
            cursor.execute(modulo5_query, (mes_ano,))
            modulo5 = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return {
                'modulo1': {
                    'total_leads': modulo1[0] or 0,
                    'leads_classificados': modulo1[1] or 0,
                    'tempo_resposta_medio': modulo1[2] or 0,
                    'custo_total_leads': modulo1[3] or 0
                },
                'modulo2': {
                    'leads_no_funil': modulo2[0] or 0,
                    'vendas_ganhas': modulo2[1] or 0,
                    'vendas_perdidas': modulo2[2] or 0,
                    'tempo_medio_status': modulo2[3] or 0
                },
                'modulo3': {
                    'leads_contatados': modulo3[0] or 0,
                    'vendedores_ativos': modulo3[1] or 0,
                    'atividades_concluidas': modulo3[2] or 0,
                    'total_atividades': modulo3[3] or 0,
                    'taxa_conclusao': modulo3[4] or 0
                },
                'modulo4': {
                    'total_negociacoes': modulo4[0] or 0,
                    'vendas_fechadas': modulo4[1] or 0,
                    'vendas_perdidas': modulo4[2] or 0,
                    'receita_total': modulo4[3] or 0,
                    'ticket_medio': modulo4[4] or 0,
                    'win_rate': modulo4[5] or 0
                },
                'modulo5': {
                    'vendedores_unicos': modulo5[0] or 0,
                    'leads_contactados': modulo5[1] or 0,
                    'atividades_concluidas': modulo5[2] or 0,
                    'taxa_conclusao_geral': modulo5[3] or 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair dados dos módulos: {e}")
            return None

    def calculate_forecast_based_on_modules(self, mes_ano, dados_modulos):
        """Calcular forecast baseado nos dados dos Módulos 1 a 5"""
        try:
            if not dados_modulos:
                return None
            
            # Dados reais dos módulos
            m1 = dados_modulos['modulo1']
            m2 = dados_modulos['modulo2']
            m3 = dados_modulos['modulo3']
            m4 = dados_modulos['modulo4']
            m5 = dados_modulos['modulo5']
            
            # Calcular dias do mês
            data_inicio = datetime.strptime(f"{mes_ano}-01", "%Y-%m-%d")
            data_fim = (data_inicio.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            dias_no_mes = data_fim.day
            dias_passados = min((datetime.now() - data_inicio).days + 1, dias_no_mes)
            dias_restantes = max(dias_no_mes - dias_passados, 0)
            
            # MÉTRICAS REAIS (baseadas nos módulos)
            leads_reais = float(m1['total_leads'])
            vendas_fechadas_reais = float(m4['vendas_fechadas'])
            vendas_perdidas_reais = float(m4['vendas_perdidas'])
            receita_real = float(m4['receita_total'])
            win_rate_real = float(m4['win_rate'])
            ticket_medio_real = float(m4['ticket_medio'])
            atividades_concluidas = float(m3['atividades_concluidas'])
            vendedores_ativos = float(m3['vendedores_ativos'])
            
            # CALCULAR PREVISÕES BASEADAS NOS DADOS REAIS
            
            # 1. Previsão de Leads (baseada no Módulo 1)
            leads_por_dia = leads_reais / dias_passados if dias_passados > 0 else 0
            previsao_leads_mes = leads_por_dia * dias_no_mes
            
            # 2. Previsão de Receita (baseada no Módulo 4)
            receita_por_dia = receita_real / dias_passados if dias_passados > 0 else 0
            previsao_receita_mes = receita_por_dia * dias_no_mes
            
            # 3. Meta de Receita (baseada na performance atual + 15% de crescimento)
            meta_receita = previsao_receita_mes * 1.15
            
            # 4. Previsão de Win Rate (baseada no Módulo 4)
            previsao_win_rate = win_rate_real  # Manter o win rate atual
            
            # 5. Previsão de Ticket Médio (baseada no Módulo 4)
            previsao_ticket_medio = ticket_medio_real  # Manter o ticket médio atual
            
            # 6. Previsão de Vendas (baseada no win rate e leads)
            previsao_vendas = (previsao_leads_mes * previsao_win_rate) / 100
            
            return {
                'mes_ano': mes_ano,
                'data_previsao': datetime.now().date(),
                'meta_receita': meta_receita,
                'previsao_receita': previsao_receita_mes,
                'previsao_leads': int(previsao_leads_mes),
                'previsao_vendas': int(previsao_vendas),
                'previsao_win_rate': previsao_win_rate,
                'previsao_ticket_medio': previsao_ticket_medio,
                'dias_passados': dias_passados,
                'dias_restantes': dias_restantes,
                'dias_no_mes': dias_no_mes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular forecast: {e}")
            return None

    def calculate_gaps_and_alerts(self, mes_ano, forecast, dados_modulos):
        """Calcular gaps e alertas baseados nos dados dos módulos"""
        try:
            if not forecast or not dados_modulos:
                return None
            
            m4 = dados_modulos['modulo4']  # Dados de vendas
            
            # Dados reais
            receita_real = float(m4['receita_total'])
            leads_reais = float(dados_modulos['modulo1']['total_leads'])
            vendas_fechadas = float(m4['vendas_fechadas'])
            win_rate_real = float(m4['win_rate'])
            ticket_medio_real = float(m4['ticket_medio'])
            
            # Gaps
            gap_receita = forecast['meta_receita'] - receita_real
            gap_leads = forecast['previsao_leads'] - leads_reais
            gap_win_rate = forecast['previsao_win_rate'] - win_rate_real
            gap_ticket_medio = forecast['previsao_ticket_medio'] - ticket_medio_real
            
            # Necessidades diárias
            receita_necessaria_diaria = gap_receita / forecast['dias_restantes'] if forecast['dias_restantes'] > 0 else 0
            leads_necessarios_diarios = gap_leads / forecast['dias_restantes'] if forecast['dias_restantes'] > 0 else 0
            
            # Win rate necessário para atingir meta
            leads_necessarios_total = leads_necessarios_diarios * forecast['dias_restantes']
            vendas_necessarias = gap_receita / forecast['previsao_ticket_medio'] if forecast['previsao_ticket_medio'] > 0 else 0
            win_rate_necessario = (vendas_necessarias / leads_necessarios_total) * 100 if leads_necessarios_total > 0 else 0
            
            # Ticket médio necessário
            ticket_medio_necessario = gap_receita / vendas_necessarias if vendas_necessarias > 0 else 0
            
            # Determinar risco baseado no gap de receita
            risco = 'baixo'
            if gap_receita > forecast['meta_receita'] * 0.3:
                risco = 'critico'
            elif gap_receita > forecast['meta_receita'] * 0.2:
                risco = 'alto'
            elif gap_receita > forecast['meta_receita'] * 0.1:
                risco = 'medio'
            
            # Alertas baseados nos módulos
            alertas = []
            if gap_receita > 0:
                alertas.append(f"Gap de receita: R$ {gap_receita:,.2f}")
            if gap_leads > 0:
                alertas.append(f"Gap de leads: {gap_leads:.0f} leads")
            if win_rate_real < forecast['previsao_win_rate']:
                alertas.append(f"Win rate abaixo do esperado: {win_rate_real:.1f}% vs {forecast['previsao_win_rate']:.1f}%")
            
            # Ações recomendadas baseadas nos módulos
            acoes = []
            if receita_necessaria_diaria > 0:
                acoes.append(f"Aumentar receita diária para R$ {receita_necessaria_diaria:,.2f}")
            if leads_necessarios_diarios > 0:
                acoes.append(f"Capturar {leads_necessarios_diarios:.0f} leads adicionais por dia")
            if win_rate_necessario > win_rate_real:
                acoes.append(f"Melhorar win rate para {win_rate_necessario:.1f}%")
            
            return {
                'mes_ano': mes_ano,
                'data_analise': datetime.now().date(),
                'gap_receita': gap_receita,
                'gap_leads': gap_leads,
                'gap_win_rate': gap_win_rate,
                'gap_ticket_medio': gap_ticket_medio,
                'receita_necessaria_diaria': receita_necessaria_diaria,
                'leads_necessarios_diarios': leads_necessarios_diarios,
                'win_rate_necessario': win_rate_necessario,
                'ticket_medio_necessario': ticket_medio_necessario,
                'risco_meta': risco,
                'alertas': '; '.join(alertas),
                'acoes_recomendadas': '; '.join(acoes)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular gaps: {e}")
            return None

    def load_forecast_data(self, mes_ano, forecast, gaps):
        """Carregar dados de forecast no banco"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # 1. Atualizar previsão mensal
            forecast_update = """
            INSERT INTO monthly_forecasts 
            (mes_ano, data_previsao, meta_receita, previsao_receita, previsao_leads, previsao_win_rate, previsao_ticket_medio)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            meta_receita = VALUES(meta_receita),
            previsao_receita = VALUES(previsao_receita),
            previsao_leads = VALUES(previsao_leads),
            previsao_win_rate = VALUES(previsao_win_rate),
            previsao_ticket_medio = VALUES(previsao_ticket_medio)
            """
            
            cursor.execute(forecast_update, (
                forecast['mes_ano'],
                forecast['data_previsao'],
                forecast['meta_receita'],
                forecast['previsao_receita'],
                forecast['previsao_leads'],
                forecast['previsao_win_rate'],
                forecast['previsao_ticket_medio']
            ))
            
            # 2. Atualizar análise de gaps
            if gaps:
                gaps_update = """
                INSERT INTO forecast_gaps 
                (mes_ano, data_analise, gap_receita, gap_leads, gap_win_rate, gap_ticket_medio,
                 receita_necessaria_diaria, leads_necessarios_diarios, win_rate_necessario, ticket_medio_necessario,
                 risco_meta, alertas, acoes_recomendadas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                gap_receita = VALUES(gap_receita),
                gap_leads = VALUES(gap_leads),
                gap_win_rate = VALUES(gap_win_rate),
                gap_ticket_medio = VALUES(gap_ticket_medio),
                receita_necessaria_diaria = VALUES(receita_necessaria_diaria),
                leads_necessarios_diarios = VALUES(leads_necessarios_diarios),
                win_rate_necessario = VALUES(win_rate_necessario),
                ticket_medio_necessario = VALUES(ticket_medio_necessario),
                risco_meta = VALUES(risco_meta),
                alertas = VALUES(alertas),
                acoes_recomendadas = VALUES(acoes_recomendadas)
                """
                
                cursor.execute(gaps_update, (
                    gaps['mes_ano'],
                    gaps['data_analise'],
                    gaps['gap_receita'],
                    gaps['gap_leads'],
                    gaps['gap_win_rate'],
                    gaps['gap_ticket_medio'],
                    gaps['receita_necessaria_diaria'],
                    gaps['leads_necessarios_diarios'],
                    gaps['win_rate_necessario'],
                    gaps['ticket_medio_necessario'],
                    gaps['risco_meta'],
                    gaps['alertas'],
                    gaps['acoes_recomendadas']
                ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            logger.info("✅ Dados de forecast integrado carregados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")

    def run_etl(self):
        """Executar ETL completo do Módulo 6 - Forecast Integrado"""
        try:
            logger.info("🚀 === INICIANDO ETL MÓDULO 6 - FORECAST INTEGRADO ===")
            logger.info("🎯 Baseado nos dados reais dos Módulos 1 a 5 do mês atual")
            
            # Mês atual
            mes_ano = datetime.now().strftime('%Y-%m')
            
            # 1. Extrair dados dos Módulos 1 a 5
            logger.info("📊 Extraindo dados dos Módulos 1 a 5...")
            dados_modulos = self.extract_modulos_data(mes_ano)
            if not dados_modulos:
                logger.error("❌ Erro ao extrair dados dos módulos")
                return
            
            # 2. Calcular forecast baseado nos módulos
            logger.info("🧮 Calculando forecast baseado nos módulos...")
            forecast = self.calculate_forecast_based_on_modules(mes_ano, dados_modulos)
            if not forecast:
                logger.error("❌ Erro ao calcular forecast")
                return
            
            # 3. Calcular gaps e alertas
            logger.info("⚠️ Calculando gaps e alertas...")
            gaps = self.calculate_gaps_and_alerts(mes_ano, forecast, dados_modulos)
            
            # 4. Carregar dados
            logger.info("💾 Carregando dados...")
            self.load_forecast_data(mes_ano, forecast, gaps)
            
            logger.info("🎉 === ETL MÓDULO 6 INTEGRADO CONCLUÍDO ===")
            
            # Resumo executivo
            logger.info("📊 RESUMO EXECUTIVO BASEADO NOS MÓDULOS:")
            logger.info(f"  📅 Mês: {forecast['mes_ano']}")
            logger.info(f"  📈 Módulo 1 - Leads: {dados_modulos['modulo1']['total_leads']:,}")
            logger.info(f"  🎯 Módulo 2 - Funil: {dados_modulos['modulo2']['vendas_ganhas']} vendas ganhas")
            logger.info(f"  📞 Módulo 3 - Atividades: {dados_modulos['modulo3']['atividades_concluidas']:,} concluídas")
            logger.info(f"  💰 Módulo 4 - Receita: R$ {dados_modulos['modulo4']['receita_total']:,.2f}")
            logger.info(f"  👥 Módulo 5 - Vendedores: {dados_modulos['modulo5']['vendedores_unicos']} ativos")
            logger.info(f"  🎯 Meta de Receita: R$ {forecast['meta_receita']:,.2f}")
            logger.info(f"  📈 Previsão de Receita: R$ {forecast['previsao_receita']:,.2f}")
            logger.info(f"  📊 Previsão de Leads: {forecast['previsao_leads']:,}")
            logger.info(f"  🎯 Win Rate: {forecast['previsao_win_rate']:.1f}%")
            logger.info(f"  💰 Ticket Médio: R$ {forecast['previsao_ticket_medio']:,.2f}")
            
            if gaps:
                logger.info("⚠️ ANÁLISE DE GAPS:")
                logger.info(f"  Gap de Receita: R$ {gaps['gap_receita']:,.2f}")
                logger.info(f"  Gap de Leads: {gaps['gap_leads']:.0f}")
                logger.info(f"  Risco da Meta: {gaps['risco_meta'].upper()}")
                logger.info(f"  Receita Necessária/Dia: R$ {gaps['receita_necessaria_diaria']:,.2f}")
                logger.info(f"  Leads Necessários/Dia: {gaps['leads_necessarios_diarios']:.0f}")
            
        except Exception as e:
            logger.error(f"❌ Erro no ETL: {e}")

if __name__ == "__main__":
    etl = KommoForecastIntegradoETL()
    etl.run_etl()
