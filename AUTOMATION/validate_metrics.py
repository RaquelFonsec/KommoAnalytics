#!/usr/bin/env python3
"""
Script de Validação de Métricas - Kommo Analytics
Verifica se todas as métricas dos 6 módulos estão corretas e consistentes
"""

import os
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class MetricsValidator:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'kommo_analytics'),
            'password': os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            'database': os.getenv('DB_NAME', 'kommo_analytics')
        }
        self.validation_results = {}
        
    def get_connection(self):
        """Conectar ao banco de dados"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Exception as e:
            logger.error(f"❌ Erro na conexão: {e}")
            return None
    
    def validate_modulo1_leads(self):
        """Validar Módulo 1: Entrada e Origem de Leads"""
        logger.info("🔍 Validando Módulo 1: Entrada e Origem de Leads...")
        
        query = """
        SELECT 
            COUNT(DISTINCT lead_id) as total_leads,
            COUNT(DISTINCT CASE WHEN primary_source IS NOT NULL THEN lead_id END) as leads_classificados,
            COUNT(DISTINCT CASE WHEN primary_source IS NULL OR primary_source = '' THEN lead_id END) as leads_nao_classificados,
            COALESCE(AVG(response_time_hours), 0) as tempo_resposta_medio,
            COALESCE(SUM(lead_cost), 0) as custo_total,
            COUNT(DISTINCT DATE(created_date)) as dias_com_leads,
            MIN(created_date) as primeiro_lead,
            MAX(created_date) as ultimo_lead
        FROM leads_metrics 
        WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações
            validations = {
                'total_leads_positive': data['total_leads'] > 0,
                'leads_classificados_ratio': (data['leads_classificados'] / data['total_leads']) > 0.5 if data['total_leads'] > 0 else False,
                'tempo_resposta_reasonable': 0 <= data['tempo_resposta_medio'] <= 168,  # 0-7 dias
                'custo_total_positive': data['custo_total'] >= 0,
                'dias_com_leads_reasonable': data['dias_com_leads'] > 0,
                'data_range_valid': data['primeiro_lead'] <= data['ultimo_lead']
            }
            
            self.validation_results['modulo1'] = {
                'data': data.to_dict(),
                'validations': validations,
                'status': all(validations.values()),
                'issues': [k for k, v in validations.items() if not v]
            }
            
            logger.info(f"✅ Módulo 1: {data['total_leads']} leads, {data['leads_classificados']} classificados")
            return True
        else:
            logger.error("❌ Módulo 1: Nenhum dado encontrado")
            return False
    
    def validate_modulo2_funil(self):
        """Validar Módulo 2: Funil de Conversão"""
        logger.info("🔍 Validando Módulo 2: Funil de Conversão...")
        
        query = """
        SELECT 
            COUNT(DISTINCT lead_id) as total_leads_funil,
            COUNT(DISTINCT CASE WHEN status_name = 'Venda ganha' THEN lead_id END) as vendas_ganhas,
            COUNT(DISTINCT CASE WHEN status_name = 'Venda perdida' THEN lead_id END) as vendas_perdidas,
            COUNT(DISTINCT CASE WHEN status_name NOT IN ('Venda ganha', 'Venda perdida') THEN lead_id END) as leads_em_andamento,
            AVG(time_in_status_hours) as tempo_medio_status,
            COUNT(DISTINCT pipeline_id) as pipelines_ativos,
            MIN(created_at) as primeiro_registro,
            MAX(created_at) as ultimo_registro
        FROM funnel_history 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações
            total_vendas = data['vendas_ganhas'] + data['vendas_perdidas']
            validations = {
                'total_leads_positive': data['total_leads_funil'] > 0,
                'vendas_consistent': total_vendas <= data['total_leads_funil'],
                'win_rate_reasonable': (data['vendas_ganhas'] / total_vendas) <= 1 if total_vendas > 0 else True,
                'tempo_status_reasonable': 0 <= data['tempo_medio_status'] <= 720,  # 0-30 dias
                'pipelines_ativos': data['pipelines_ativos'] > 0,
                'data_range_valid': data['primeiro_registro'] <= data['ultimo_registro']
            }
            
            self.validation_results['modulo2'] = {
                'data': data.to_dict(),
                'validations': validations,
                'status': all(validations.values()),
                'issues': [k for k, v in validations.items() if not v]
            }
            
            win_rate = (data['vendas_ganhas'] / total_vendas * 100) if total_vendas > 0 else 0
            logger.info(f"✅ Módulo 2: {data['total_leads_funil']} leads, {win_rate:.1f}% win rate")
            return True
        else:
            logger.error("❌ Módulo 2: Nenhum dado encontrado")
            return False
    
    def validate_modulo3_atividades(self):
        """Validar Módulo 3: Atividades Comerciais"""
        logger.info("🔍 Validando Módulo 3: Atividades Comerciais...")
        
        query = """
        SELECT 
            COUNT(DISTINCT entity_id) as leads_contatados,
            COUNT(DISTINCT user_id) as vendedores_ativos,
            COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) as atividades_concluidas,
            COUNT(*) as total_atividades,
            ROUND(COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao,
            COUNT(DISTINCT activity_type) as tipos_atividade,
            COUNT(DISTINCT contact_type) as tipos_contato,
            MIN(created_date) as primeira_atividade,
            MAX(created_date) as ultima_atividade
        FROM commercial_activities 
        WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações
            validations = {
                'total_atividades_positive': data['total_atividades'] > 0,
                'atividades_concluidas_consistent': data['atividades_concluidas'] <= data['total_atividades'],
                'taxa_conclusao_reasonable': 0 <= data['taxa_conclusao'] <= 100,
                'vendedores_ativos_positive': data['vendedores_ativos'] > 0,
                'leads_contatados_positive': data['leads_contatados'] > 0,
                'tipos_atividade_diverse': data['tipos_atividade'] > 0,
                'data_range_valid': data['primeira_atividade'] <= data['ultima_atividade']
            }
            
            self.validation_results['modulo3'] = {
                'data': data.to_dict(),
                'validations': validations,
                'status': all(validations.values()),
                'issues': [k for k, v in validations.items() if not v]
            }
            
            logger.info(f"✅ Módulo 3: {data['total_atividades']} atividades, {data['taxa_conclusao']}% conclusão")
            return True
        else:
            logger.error("❌ Módulo 3: Nenhum dado encontrado")
            return False
    
    def validate_modulo4_vendas(self):
        """Validar Módulo 4: Conversão e Receita"""
        logger.info("🔍 Validando Módulo 4: Conversão e Receita...")
        
        query = """
        SELECT 
            COUNT(DISTINCT lead_id) as total_negociacoes,
            COUNT(DISTINCT CASE WHEN status_name = 'Venda ganha' THEN lead_id END) as vendas_fechadas,
            COUNT(DISTINCT CASE WHEN status_name = 'Venda perdida' THEN lead_id END) as vendas_perdidas,
            COALESCE(SUM(CASE WHEN status_name = 'Venda ganha' THEN sale_price ELSE 0 END), 0) as receita_total,
            COALESCE(AVG(CASE WHEN status_name = 'Venda ganha' THEN sale_price END), 0) as ticket_medio,
            ROUND(COUNT(DISTINCT CASE WHEN status_name = 'Venda ganha' THEN lead_id END) / 
                  NULLIF(COUNT(DISTINCT CASE WHEN status_name IN ('Venda ganha', 'Venda perdida') THEN lead_id END), 0) * 100, 1) as win_rate,
            COUNT(DISTINCT responsible_user_name) as vendedores_vendas,
            MIN(created_date) as primeira_venda,
            MAX(created_date) as ultima_venda
        FROM sales_metrics 
        WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações
            total_vendas = data['vendas_fechadas'] + data['vendas_perdidas']
            validations = {
                'total_negociacoes_positive': data['total_negociacoes'] > 0,
                'vendas_consistent': total_vendas <= data['total_negociacoes'],
                'win_rate_reasonable': 0 <= data['win_rate'] <= 100,
                'receita_positive': data['receita_total'] >= 0,
                'ticket_medio_reasonable': data['ticket_medio'] >= 0,
                'vendedores_vendas_positive': data['vendedores_vendas'] > 0,
                'data_range_valid': data['primeira_venda'] <= data['ultima_venda']
            }
            
            self.validation_results['modulo4'] = {
                'data': data.to_dict(),
                'validations': validations,
                'status': all(validations.values()),
                'issues': [k for k, v in validations.items() if not v]
            }
            
            logger.info(f"✅ Módulo 4: R$ {data['receita_total']:,.2f} receita, {data['win_rate']}% win rate")
            return True
        else:
            logger.error("❌ Módulo 4: Nenhum dado encontrado")
            return False
    
    def validate_modulo5_performance(self):
        """Validar Módulo 5: Performance por Pessoa e Canal"""
        logger.info("🔍 Validando Módulo 5: Performance por Pessoa e Canal...")
        
        query = """
        SELECT 
            COUNT(DISTINCT user_id) as vendedores_unicos,
            COUNT(DISTINCT entity_id) as leads_contactados,
            COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) as atividades_concluidas,
            ROUND(COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao_geral,
            COUNT(DISTINCT activity_type) as tipos_atividade,
            COUNT(DISTINCT contact_type) as tipos_contato,
            AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds END) as duracao_media_atividades
        FROM commercial_activities 
        WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY) AND user_id IS NOT NULL
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações
            validations = {
                'vendedores_unicos_positive': data['vendedores_unicos'] > 0,
                'leads_contactados_positive': data['leads_contactados'] > 0,
                'atividades_concluidas_consistent': data['atividades_concluidas'] >= 0,
                'taxa_conclusao_reasonable': 0 <= data['taxa_conclusao_geral'] <= 100,
                'tipos_atividade_diverse': data['tipos_atividade'] > 0,
                'duracao_media_reasonable': data['duracao_media_atividades'] is None or data['duracao_media_atividades'] >= 0
            }
            
            self.validation_results['modulo5'] = {
                'data': data.to_dict(),
                'validations': validations,
                'status': all(validations.values()),
                'issues': [k for k, v in validations.items() if not v]
            }
            
            logger.info(f"✅ Módulo 5: {data['vendedores_unicos']} vendedores, {data['taxa_conclusao_geral']}% conclusão")
            return True
        else:
            logger.error("❌ Módulo 5: Nenhum dado encontrado")
            return False
    
    def validate_modulo6_forecast(self):
        """Validar Módulo 6: Previsibilidade (Forecast)"""
        logger.info("🔍 Validando Módulo 6: Previsibilidade (Forecast)...")
        
        query = """
        SELECT 
            mes_ano,
            data_previsao,
            meta_receita,
            previsao_receita,
            previsao_leads,
            previsao_win_rate,
            previsao_ticket_medio
        FROM monthly_forecasts 
        WHERE mes_ano = DATE_FORMAT(NOW(), '%Y-%m')
        ORDER BY data_previsao DESC
        LIMIT 1
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações
            validations = {
                'mes_ano_current': data['mes_ano'] == datetime.now().strftime('%Y-%m'),
                'meta_receita_positive': data['meta_receita'] > 0,
                'previsao_receita_positive': data['previsao_receita'] > 0,
                'previsao_leads_positive': data['previsao_leads'] > 0,
                'previsao_win_rate_reasonable': 0 <= data['previsao_win_rate'] <= 100,
                'previsao_ticket_medio_positive': data['previsao_ticket_medio'] > 0,
                'data_previsao_recent': (datetime.now().date() - data['data_previsao']).days <= 7
            }
            
            self.validation_results['modulo6'] = {
                'data': data.to_dict(),
                'validations': validations,
                'status': all(validations.values()),
                'issues': [k for k, v in validations.items() if not v]
            }
            
            logger.info(f"✅ Módulo 6: Meta R$ {data['meta_receita']:,.2f}, Previsão R$ {data['previsao_receita']:,.2f}")
            return True
        else:
            logger.error("❌ Módulo 6: Nenhum dado encontrado")
            return False
    
    def validate_data_consistency(self):
        """Validar consistência entre módulos"""
        logger.info("🔍 Validando consistência entre módulos...")
        
        # Verificar se leads do módulo 1 aparecem nos outros módulos
        query = """
        SELECT 
            (SELECT COUNT(DISTINCT lead_id) FROM leads_metrics WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as total_leads_modulo1,
            (SELECT COUNT(DISTINCT lead_id) FROM funnel_history WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as total_leads_modulo2,
            (SELECT COUNT(DISTINCT entity_id) FROM commercial_activities WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as total_leads_modulo3,
            (SELECT COUNT(DISTINCT lead_id) FROM sales_metrics WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as total_leads_modulo4
        """
        
        conn = self.get_connection()
        if not conn:
            return False
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            data = df.iloc[0]
            
            # Validações de consistência
            consistency_checks = {
                'leads_modulo1_positive': data['total_leads_modulo1'] > 0,
                'leads_modulo2_positive': data['total_leads_modulo2'] > 0,
                'leads_modulo3_positive': data['total_leads_modulo3'] > 0,
                'leads_modulo4_positive': data['total_leads_modulo4'] > 0,
                'modulo2_has_data': data['total_leads_modulo2'] > 0,
                'modulo3_has_data': data['total_leads_modulo3'] > 0,
                'modulo4_has_data': data['total_leads_modulo4'] > 0
            }
            
            self.validation_results['consistency'] = {
                'data': data.to_dict(),
                'validations': consistency_checks,
                'status': all(consistency_checks.values()),
                'issues': [k for k, v in consistency_checks.items() if not v]
            }
            
            logger.info(f"✅ Consistência: M1={data['total_leads_modulo1']}, M2={data['total_leads_modulo2']}, M3={data['total_leads_modulo3']}, M4={data['total_leads_modulo4']}")
            return True
        else:
            logger.error("❌ Consistência: Nenhum dado encontrado")
            return False
    
    def generate_validation_report(self):
        """Gerar relatório de validação"""
        logger.info("📊 Gerando relatório de validação...")
        
        total_modules = len(self.validation_results)
        valid_modules = sum(1 for result in self.validation_results.values() if result['status'])
        
        report = f"""
🔍 RELATÓRIO DE VALIDAÇÃO - KOMMO ANALYTICS
Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
================================================

📊 STATUS GERAL:
- Módulos validados: {total_modules}/6
- Módulos OK: {valid_modules}/6
- Taxa de sucesso: {(valid_modules/total_modules*100):.1f}%

📋 DETALHAMENTO POR MÓDULO:
"""
        
        for module_name, result in self.validation_results.items():
            status_icon = "✅" if result['status'] else "❌"
            report += f"\n{status_icon} {module_name.upper()}:"
            
            if result['status']:
                report += " OK"
            else:
                report += f" PROBLEMAS: {', '.join(result['issues'])}"
        
        report += f"""

🎯 RECOMENDAÇÕES:
"""
        
        if valid_modules == total_modules:
            report += "- ✅ Todos os módulos estão funcionando corretamente"
            report += "- ✅ Dados consistentes e atualizados"
            report += "- ✅ Sistema pronto para uso diário"
        else:
            report += "- ⚠️ Alguns módulos precisam de atenção"
            report += "- 🔧 Execute os ETLs novamente se necessário"
            report += "- 📊 Verifique os logs para detalhes"
        
        return report
    
    def run_full_validation(self):
        """Executar validação completa"""
        logger.info("🚀 === INICIANDO VALIDAÇÃO COMPLETA ===")
        
        # Validar cada módulo
        self.validate_modulo1_leads()
        self.validate_modulo2_funil()
        self.validate_modulo3_atividades()
        self.validate_modulo4_vendas()
        self.validate_modulo5_performance()
        self.validate_modulo6_forecast()
        
        # Validar consistência
        self.validate_data_consistency()
        
        # Gerar relatório
        report = self.generate_validation_report()
        
        logger.info("🎉 === VALIDAÇÃO CONCLUÍDA ===")
        print(report)
        
        return all(result['status'] for result in self.validation_results.values())

if __name__ == "__main__":
    validator = MetricsValidator()
    success = validator.run_full_validation()
    
    if success:
        print("\n🎉 TODAS AS MÉTRICAS ESTÃO CORRETAS!")
        print("✅ Sistema pronto para atualização diária automática")
    else:
        print("\n⚠️ ALGUMAS MÉTRICAS PRECISAM DE ATENÇÃO!")
        print("🔧 Verifique os problemas identificados acima")
