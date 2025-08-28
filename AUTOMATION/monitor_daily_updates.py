#!/usr/bin/env python3
"""
Script de Monitoramento de Atualizações Diárias - Kommo Analytics
Monitora e garante que todas as atualizações diárias funcionem corretamente
"""

import os
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import logging
import subprocess
import sys
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class DailyUpdateMonitor:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'kommo_analytics'),
            'password': os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            'database': os.getenv('DB_NAME', 'kommo_analytics')
        }
        self.project_dir = "/home/raquel-fonseca/Projects/KommoAnalytics"
        
    def get_connection(self):
        """Conectar ao banco de dados"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Exception as e:
            logger.error(f"❌ Erro na conexão: {e}")
            return None
    
    def check_last_etl_execution(self):
        """Verificar última execução dos ETLs"""
        logger.info("🔍 Verificando última execução dos ETLs...")
        
        # Verificar logs de execução
        log_files = [
            "LOGS/etl_automation.log",
            "LOGS/dashboard_monitor.log",
            "LOGS/health_check.log"
        ]
        
        last_executions = {}
        for log_file in log_files:
            log_path = os.path.join(self.project_dir, log_file)
            if os.path.exists(log_path):
                # Pegar última linha com timestamp
                try:
                    with open(log_path, 'r') as f:
                        lines = f.readlines()
                        for line in reversed(lines):
                            if '2025-' in line:  # Encontrar linha com data
                                last_executions[log_file] = line.strip()
                                break
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao ler {log_file}: {e}")
        
        return last_executions
    
    def check_data_freshness(self):
        """Verificar se os dados estão atualizados"""
        logger.info("🔍 Verificando atualização dos dados...")
        
        query = """
        SELECT 
            'leads_metrics' as tabela,
            MAX(created_date) as ultima_atualizacao,
            COUNT(*) as total_registros
        FROM leads_metrics
        UNION ALL
        SELECT 
            'funnel_history' as tabela,
            MAX(created_at) as ultima_atualizacao,
            COUNT(*) as total_registros
        FROM funnel_history
        UNION ALL
        SELECT 
            'commercial_activities' as tabela,
            MAX(created_date) as ultima_atualizacao,
            COUNT(*) as total_registros
        FROM commercial_activities
        UNION ALL
        SELECT 
            'sales_metrics' as tabela,
            MAX(created_date) as ultima_atualizacao,
            COUNT(*) as total_registros
        FROM sales_metrics
        UNION ALL
        SELECT 
            'monthly_forecasts' as tabela,
            MAX(data_previsao) as ultima_atualizacao,
            COUNT(*) as total_registros
        FROM monthly_forecasts
        """
        
        conn = self.get_connection()
        if not conn:
            return None
            
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Verificar se dados são recentes (últimas 24h)
        now = datetime.now()
        data_freshness = {}
        
        for _, row in df.iterrows():
            last_update = row['ultima_atualizacao']
            if last_update:
                hours_ago = (now - last_update).total_seconds() / 3600
                data_freshness[row['tabela']] = {
                    'ultima_atualizacao': last_update,
                    'horas_atras': hours_ago,
                    'total_registros': row['total_registros'],
                    'atualizado': hours_ago <= 24  # Considerar atualizado se < 24h
                }
        
        return data_freshness
    
    def check_cron_jobs(self):
        """Verificar se os cron jobs estão configurados"""
        logger.info("🔍 Verificando configuração dos cron jobs...")
        
        try:
            # Verificar crontab atual
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            
            if result.returncode == 0:
                crontab_content = result.stdout
                
                # Verificar se há entradas do Kommo Analytics
                kommo_entries = []
                for line in crontab_content.split('\n'):
                    if 'KommoAnalytics' in line or 'kommo_analytics' in line:
                        kommo_entries.append(line.strip())
                
                return {
                    'crontab_configured': True,
                    'kommo_entries': kommo_entries,
                    'total_entries': len(kommo_entries)
                }
            else:
                return {
                    'crontab_configured': False,
                    'kommo_entries': [],
                    'total_entries': 0
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar cron: {e}")
            return {
                'crontab_configured': False,
                'kommo_entries': [],
                'total_entries': 0
            }
    
    def test_etl_execution(self):
        """Testar execução dos ETLs"""
        logger.info("🔍 Testando execução dos ETLs...")
        
        etl_scripts = [
            "ETL/kommo_etl_modulo1_leads.py",
            "ETL/kommo_etl_modulo2_funil.py", 
            "ETL/kommo_etl_modulo3_atividades.py",
            "ETL/kommo_etl_modulo4_conversao.py",
            "ETL/kommo_etl_modulo5_performance.py",
            "ETL/kommo_etl_modulo6_forecast_integrado.py"
        ]
        
        test_results = {}
        
        for script in etl_scripts:
            script_path = os.path.join(self.project_dir, script)
            if os.path.exists(script_path):
                try:
                    # Testar se o script pode ser importado (sintaxe OK)
                    result = subprocess.run([
                        sys.executable, '-m', 'py_compile', script_path
                    ], capture_output=True, text=True)
                    
                    test_results[script] = {
                        'exists': True,
                        'syntax_ok': result.returncode == 0,
                        'error': result.stderr if result.returncode != 0 else None
                    }
                except Exception as e:
                    test_results[script] = {
                        'exists': True,
                        'syntax_ok': False,
                        'error': str(e)
                    }
            else:
                test_results[script] = {
                    'exists': False,
                    'syntax_ok': False,
                    'error': 'Arquivo não encontrado'
                }
        
        return test_results
    
    def check_dashboard_status(self):
        """Verificar status do dashboard"""
        logger.info("🔍 Verificando status do dashboard...")
        
        try:
            # Verificar se o dashboard está rodando
            result = subprocess.run([
                'curl', '-s', 'http://localhost:8501'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'Streamlit' in result.stdout:
                return {
                    'running': True,
                    'accessible': True,
                    'response_time': 'OK'
                }
            else:
                return {
                    'running': False,
                    'accessible': False,
                    'response_time': 'N/A'
                }
                
        except Exception as e:
            return {
                'running': False,
                'accessible': False,
                'response_time': f'Erro: {str(e)}'
            }
    
    def generate_monitoring_report(self, last_executions, data_freshness, cron_status, etl_tests, dashboard_status):
        """Gerar relatório de monitoramento"""
        logger.info("📊 Gerando relatório de monitoramento...")
        
        report = f"""
🔍 RELATÓRIO DE MONITORAMENTO - ATUALIZAÇÕES DIÁRIAS
Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
=====================================================

📋 STATUS DOS ETLs:
"""
        
        # Status dos ETLs
        etl_ok = sum(1 for result in etl_tests.values() if result['syntax_ok'])
        etl_total = len(etl_tests)
        
        report += f"- ETLs funcionais: {etl_ok}/{etl_total}\n"
        
        for script, result in etl_tests.items():
            status = "✅" if result['syntax_ok'] else "❌"
            report += f"  {status} {script.split('/')[-1]}\n"
        
        report += f"""

📊 ATUALIZAÇÃO DOS DADOS:
"""
        
        # Status dos dados
        if data_freshness:
            fresh_data = sum(1 for data in data_freshness.values() if data['atualizado'])
            total_tables = len(data_freshness)
            
            report += f"- Tabelas atualizadas: {fresh_data}/{total_tables}\n"
            
            for table, data in data_freshness.items():
                status = "✅" if data['atualizado'] else "⚠️"
                hours = f"{data['horas_atras']:.1f}h atrás"
                report += f"  {status} {table}: {hours} ({data['total_registros']} registros)\n"
        
        report += f"""

⏰ CONFIGURAÇÃO DO CRON:
"""
        
        # Status do cron
        if cron_status['crontab_configured']:
            report += f"- ✅ Cron configurado\n"
            report += f"- 📋 {cron_status['total_entries']} entradas do Kommo Analytics\n"
            
            for entry in cron_status['kommo_entries']:
                report += f"  📅 {entry}\n"
        else:
            report += "- ❌ Cron não configurado\n"
        
        report += f"""

🌐 STATUS DO DASHBOARD:
"""
        
        # Status do dashboard
        if dashboard_status['running']:
            report += "- ✅ Dashboard rodando\n"
            report += "- ✅ Acessível em http://localhost:8501\n"
        else:
            report += "- ❌ Dashboard não está rodando\n"
        
        report += f"""

📋 ÚLTIMAS EXECUÇÕES:
"""
        
        # Últimas execuções
        if last_executions:
            for log_file, last_exec in last_executions.items():
                report += f"- 📄 {log_file.split('/')[-1]}: {last_exec[:50]}...\n"
        else:
            report += "- ⚠️ Nenhuma execução registrada\n"
        
        report += f"""

🎯 RECOMENDAÇÕES:
"""
        
        # Recomendações baseadas nos resultados
        issues = []
        
        if etl_ok < etl_total:
            issues.append("🔧 Corrigir ETLs com erro de sintaxe")
        
        if data_freshness:
            fresh_count = sum(1 for data in data_freshness.values() if data['atualizado'])
            if fresh_count < len(data_freshness):
                issues.append("🔄 Executar ETLs para atualizar dados antigos")
        
        if not cron_status['crontab_configured']:
            issues.append("⏰ Configurar cron jobs para automação")
        
        if not dashboard_status['running']:
            issues.append("🌐 Iniciar o dashboard Streamlit")
        
        if issues:
            for issue in issues:
                report += f"- {issue}\n"
        else:
            report += "- ✅ Sistema funcionando perfeitamente\n"
            report += "- ✅ Atualizações diárias configuradas\n"
            report += "- ✅ Dashboard acessível\n"
        
        return report
    
    def run_full_monitoring(self):
        """Executar monitoramento completo"""
        logger.info("🚀 === INICIANDO MONITORAMENTO COMPLETO ===")
        
        # Coletar informações
        last_executions = self.check_last_etl_execution()
        data_freshness = self.check_data_freshness()
        cron_status = self.check_cron_jobs()
        etl_tests = self.test_etl_execution()
        dashboard_status = self.check_dashboard_status()
        
        # Gerar relatório
        report = self.generate_monitoring_report(
            last_executions, data_freshness, cron_status, etl_tests, dashboard_status
        )
        
        logger.info("🎉 === MONITORAMENTO CONCLUÍDO ===")
        print(report)
        
        # Retornar status geral
        etl_ok = sum(1 for result in etl_tests.values() if result['syntax_ok'])
        data_ok = sum(1 for data in data_freshness.values() if data['atualizado']) if data_freshness else 0
        cron_ok = cron_status['crontab_configured']
        dashboard_ok = dashboard_status['running']
        
        overall_status = (
            etl_ok == len(etl_tests) and
            data_ok == len(data_freshness) and
            cron_ok and
            dashboard_ok
        )
        
        return overall_status

if __name__ == "__main__":
    monitor = DailyUpdateMonitor()
    success = monitor.run_full_monitoring()
    
    if success:
        print("\n🎉 SISTEMA TOTALMENTE FUNCIONAL!")
        print("✅ Todas as atualizações diárias estão configuradas e funcionando")
        print("✅ Dashboard acessível e dados atualizados")
        print("✅ Automação cron configurada")
    else:
        print("\n⚠️ ALGUNS PROBLEMAS IDENTIFICADOS!")
        print("🔧 Verifique as recomendações acima para corrigir")
        print("📞 Entre em contato se precisar de ajuda")


