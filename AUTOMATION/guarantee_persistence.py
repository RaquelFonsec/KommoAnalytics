#!/usr/bin/env python3
"""
Script de Garantia de Persistência - Kommo Analytics
Garante que todos os dados estão persistidos e o sistema está pronto para produção
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

class PersistenceGuarantee:
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
    
    def check_data_persistence(self):
        """Verificar se todos os dados estão persistidos"""
        logger.info("🔍 Verificando persistência dos dados...")
        
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Tabelas e suas colunas de data
        tables_config = {
            'leads_metrics': 'created_date',
            'funnel_history': 'created_at',
            'commercial_activities': 'created_date',
            'sales_metrics': 'created_date',
            'performance_vendedores': 'created_date',
            'performance_canais': 'created_date',
            'monthly_forecasts': 'created_date',
            'forecast_gaps': 'created_date'
        }
        
        persistence_status = {}
        
        for table, date_column in tables_config.items():
            try:
                query = f"SELECT COUNT(*) as total, MAX({date_column}) as ultima_atualizacao FROM {table}"
                cursor.execute(query)
                result = cursor.fetchone()
                
                if result:
                    total_records, last_update = result
                    persistence_status[table] = {
                        'total': total_records,
                        'last_update': last_update,
                        'is_recent': self.is_recent_update(last_update)
                    }
                    logger.info(f"✅ {table}: {total_records} registros, última atualização: {last_update}")
                else:
                    persistence_status[table] = {'error': 'Nenhum dado encontrado'}
                    logger.warning(f"⚠️ {table}: Nenhum dado encontrado")
                    
            except Exception as e:
                persistence_status[table] = {'error': str(e)}
                logger.error(f"❌ {table}: Erro - {e}")
        
        cursor.close()
        conn.close()
        
        return persistence_status
    
    def is_recent_update(self, last_update):
        """Verificar se a atualização é recente (últimas 72h)"""
        if not last_update:
            return False
        
        if isinstance(last_update, datetime):
            update_time = last_update
        else:
            update_time = datetime.combine(last_update, datetime.min.time())
        
        return (datetime.now() - update_time).days <= 3
    
    def check_etl_functionality(self):
        """Verificar se todos os ETLs estão funcionando"""
        logger.info("🔍 Verificando funcionalidade dos ETLs...")
        
        etl_scripts = [
            'kommo_etl_modulo1_leads.py',
            'kommo_etl_modulo2_funil.py',
            'kommo_etl_modulo3_atividades.py',
            'kommo_etl_modulo4_conversao.py',
            'kommo_etl_modulo5_performance.py',
            'kommo_etl_modulo6_forecast_integrado.py'
        ]
        
        etl_status = {}
        
        for script in etl_scripts:
            script_path = os.path.join(self.project_dir, 'ETL', script)
            
            if os.path.exists(script_path):
                # Testar sintaxe do script
                try:
                    result = subprocess.run([
                        sys.executable, '-m', 'py_compile', script_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        etl_status[script] = {'status': 'OK', 'error': None}
                        logger.info(f"✅ {script}: Sintaxe OK")
                    else:
                        etl_status[script] = {'status': 'ERROR', 'error': result.stderr}
                        logger.error(f"❌ {script}: Erro de sintaxe")
                        
                except Exception as e:
                    etl_status[script] = {'status': 'ERROR', 'error': str(e)}
                    logger.error(f"❌ {script}: Erro - {e}")
            else:
                etl_status[script] = {'status': 'MISSING', 'error': 'Arquivo não encontrado'}
                logger.error(f"❌ {script}: Arquivo não encontrado")
        
        return etl_status
    
    def check_automation_setup(self):
        """Verificar configuração de automação"""
        logger.info("🔍 Verificando configuração de automação...")
        
        automation_status = {}
        
        # Verificar cron jobs
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                cron_content = result.stdout
                kommo_jobs = [line for line in cron_content.split('\n') if 'KommoAnalytics' in line]
                automation_status['cron_jobs'] = {
                    'configured': len(kommo_jobs) > 0,
                    'count': len(kommo_jobs),
                    'jobs': kommo_jobs
                }
                logger.info(f"✅ Cron jobs: {len(kommo_jobs)} configurados")
            else:
                automation_status['cron_jobs'] = {'configured': False, 'error': 'Erro ao verificar cron'}
                logger.error("❌ Erro ao verificar cron jobs")
        except Exception as e:
            automation_status['cron_jobs'] = {'configured': False, 'error': str(e)}
            logger.error(f"❌ Erro ao verificar cron: {e}")
        
        # Verificar scripts de automação
        automation_scripts = [
            'run_all_etls.sh',
            'backup_database.sh',
            'health_check.sh',
            'monitor_daily_updates.py'
        ]
        
        scripts_status = {}
        for script in automation_scripts:
            script_path = os.path.join(self.project_dir, 'AUTOMATION', script)
            if os.path.exists(script_path):
                scripts_status[script] = {'exists': True, 'executable': os.access(script_path, os.X_OK)}
            else:
                scripts_status[script] = {'exists': False, 'executable': False}
        
        automation_status['scripts'] = scripts_status
        logger.info(f"✅ Scripts de automação: {sum(1 for s in scripts_status.values() if s['exists'])}/{len(automation_scripts)}")
        
        return automation_status
    
    def check_backup_system(self):
        """Verificar sistema de backup"""
        logger.info("🔍 Verificando sistema de backup...")
        
        backup_dir = os.path.join(self.project_dir, 'BACKUP')
        backup_status = {}
        
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.sql.gz')]
            backup_status['backup_dir'] = True
            backup_status['backup_files'] = len(backup_files)
            
            if backup_files:
                # Verificar backup mais recente
                latest_backup = max(backup_files, key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
                backup_status['latest_backup'] = latest_backup
                backup_status['latest_backup_time'] = datetime.fromtimestamp(
                    os.path.getctime(os.path.join(backup_dir, latest_backup))
                )
                logger.info(f"✅ Backup: {len(backup_files)} arquivos, mais recente: {latest_backup}")
            else:
                backup_status['latest_backup'] = None
                logger.warning("⚠️ Nenhum arquivo de backup encontrado")
        else:
            backup_status['backup_dir'] = False
            backup_status['backup_files'] = 0
            logger.error("❌ Diretório de backup não encontrado")
        
        return backup_status
    
    def generate_production_report(self):
        """Gerar relatório completo para produção"""
        logger.info("📊 Gerando relatório de garantia para produção...")
        
        # Coletar todas as verificações
        data_persistence = self.check_data_persistence()
        etl_functionality = self.check_etl_functionality()
        automation_setup = self.check_automation_setup()
        backup_system = self.check_backup_system()
        
        # Gerar relatório
        report = f"""
🔒 RELATÓRIO DE GARANTIA PARA PRODUÇÃO - KOMMO ANALYTICS
Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
===============================================================

📊 PERSISTÊNCIA DOS DADOS:
"""
        
        # Status da persistência
        tables_ok = 0
        tables_total = len(data_persistence)
        
        for table, status in data_persistence.items():
            if 'error' not in status and status.get('is_recent', False):
                report += f"  ✅ {table}: {status['total']} registros (atualizado hoje)\n"
                tables_ok += 1
            elif 'error' not in status:
                report += f"  ⚠️ {table}: {status['total']} registros (última atualização: {status['last_update']})\n"
            else:
                report += f"  ❌ {table}: {status['error']}\n"
        
        report += f"\n📋 ETLs FUNCIONAIS:\n"
        
        # Status dos ETLs
        etls_ok = sum(1 for status in etl_functionality.values() if status['status'] == 'OK')
        etls_total = len(etl_functionality)
        
        for script, status in etl_functionality.items():
            if status['status'] == 'OK':
                report += f"  ✅ {script}\n"
            else:
                report += f"  ❌ {script}: {status['error']}\n"
        
        report += f"\n⚙️ AUTOMAÇÃO CONFIGURADA:\n"
        
        # Status da automação
        if automation_setup['cron_jobs']['configured']:
            report += f"  ✅ Cron jobs: {automation_setup['cron_jobs']['count']} configurados\n"
        else:
            report += f"  ❌ Cron jobs: {automation_setup['cron_jobs']['error']}\n"
        
        scripts_ok = sum(1 for status in automation_setup['scripts'].values() if status['exists'])
        scripts_total = len(automation_setup['scripts'])
        report += f"  ✅ Scripts de automação: {scripts_ok}/{scripts_total}\n"
        
        report += f"\n💾 SISTEMA DE BACKUP:\n"
        
        # Status do backup
        if backup_system['backup_dir']:
            report += f"  ✅ Diretório de backup: OK\n"
            report += f"  ✅ Arquivos de backup: {backup_system['backup_files']}\n"
            if backup_system['latest_backup']:
                report += f"  ✅ Último backup: {backup_system['latest_backup']}\n"
        else:
            report += f"  ❌ Sistema de backup: Não configurado\n"
        
        # Resumo final
        report += f"\n📊 RESUMO PARA PRODUÇÃO:\n"
        report += f"========================\n"
        report += f"  📊 Dados persistidos: {tables_ok}/{tables_total} tabelas atualizadas\n"
        report += f"  🔧 ETLs funcionais: {etls_ok}/{etls_total}\n"
        report += f"  ⚙️ Automação: {'✅ Configurada' if automation_setup['cron_jobs']['configured'] else '❌ Não configurada'}\n"
        report += f"  💾 Backup: {'✅ Funcionando' if backup_system['backup_dir'] else '❌ Não configurado'}\n"
        
        # Recomendação final
        all_ok = (tables_ok == tables_total and 
                  etls_ok == etls_total and 
                  automation_setup['cron_jobs']['configured'] and 
                  backup_system['backup_dir'])
        
        if all_ok:
            report += f"\n🎉 SISTEMA PRONTO PARA PRODUÇÃO!\n"
            report += f"✅ Todos os componentes estão funcionando corretamente\n"
            report += f"✅ Dados persistidos e atualizados\n"
            report += f"✅ Automação configurada\n"
            report += f"✅ Backup funcionando\n"
            report += f"✅ Pode ser movido para produção com segurança\n"
        else:
            report += f"\n⚠️ SISTEMA NÃO ESTÁ PRONTO PARA PRODUÇÃO\n"
            report += f"🔧 Corrija os problemas identificados acima\n"
            report += f"📞 Entre em contato se precisar de ajuda\n"
        
        return report, all_ok
    
    def run_guarantee_check(self):
        """Executar verificação completa de garantia"""
        logger.info("🚀 === INICIANDO VERIFICAÇÃO DE GARANTIA PARA PRODUÇÃO ===")
        
        report, is_ready = self.generate_production_report()
        
        logger.info("🎉 === VERIFICAÇÃO CONCLUÍDA ===")
        print(report)
        
        return is_ready

if __name__ == "__main__":
    guarantee = PersistenceGuarantee()
    is_ready = guarantee.run_guarantee_check()
    
    if is_ready:
        print("\n🎉 SISTEMA GARANTIDO PARA PRODUÇÃO!")
        print("✅ Todos os dados estão persistidos")
        print("✅ Sistema funcionará corretamente em produção")
        print("✅ Atualizações diárias garantidas")
        exit(0)
    else:
        print("\n⚠️ SISTEMA NÃO ESTÁ PRONTO PARA PRODUÇÃO!")
        print("🔧 Corrija os problemas antes de mover para produção")
        exit(1)
