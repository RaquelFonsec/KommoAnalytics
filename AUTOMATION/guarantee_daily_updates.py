#!/usr/bin/env python3
"""
Sistema de Garantia de Atualização Diária - Kommo Analytics
Garante que o dashboard seja sempre atualizado e não desatualize após commits
"""

import os
import sys
import subprocess
import mysql.connector
from datetime import datetime, timedelta, date
import logging
import json

# Configurações
PROJECT_DIR = "/home/raquel-fonseca/Projects/KommoAnalytics"
LOG_DIR = f"{PROJECT_DIR}/LOGS"
DB_CONFIG = {
    'host': 'os.getenv('DB_HOST', 'localhost')',
    'port': 3306,
    'user': 'kommo_analytics',
    'password': 'previdas_ltda_2025',
    'database': 'kommo_analytics'
}

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/update_guarantee.log'),
        logging.StreamHandler()
    ]
)

class UpdateGuarantee:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.last_update_file = f"{LOG_DIR}/last_update.json"
        
    def check_database_freshness(self):
        """Verifica se os dados do banco estão atualizados"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Verificar última atualização de cada tabela
            tables = [
                'leads_metrics',
                'sales_metrics', 
                'commercial_activities',
                'performance_vendedores',
                'performance_canais',
                'monthly_forecasts'
            ]
            
            freshness_status = {}
            
            for table in tables:
                cursor.execute(f"""
                    SELECT MAX(created_date) as last_update 
                    FROM {table}
                """)
                result = cursor.fetchone()
                
                if result and result[0]:
                    last_update = result[0]
                    # Converter para datetime se for date
                    if isinstance(last_update, date):
                        last_update = datetime.combine(last_update, datetime.min.time())
                    hours_ago = (datetime.now() - last_update).total_seconds() / 3600
                    freshness_status[table] = {
                        'last_update': last_update.isoformat(),
                        'hours_ago': hours_ago,
                        'is_fresh': hours_ago < 24  # Considera atualizado se < 24h
                    }
                else:
                    freshness_status[table] = {
                        'last_update': None,
                        'hours_ago': None,
                        'is_fresh': False
                    }
            
            cursor.close()
            conn.close()
            
            return freshness_status
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar frescor dos dados: {e}")
            return None
    
    def force_update_if_needed(self):
        """Força atualização se os dados estiverem desatualizados"""
        freshness = self.check_database_freshness()
        
        if not freshness:
            self.logger.error("Não foi possível verificar frescor dos dados")
            return False
        
        needs_update = False
        stale_tables = []
        
        for table, status in freshness.items():
            if not status['is_fresh']:
                needs_update = True
                stale_tables.append(table)
                self.logger.warning(f"Tabela {table} desatualizada: {status['hours_ago']:.1f}h atrás")
        
        if needs_update:
            self.logger.info(f"Forçando atualização de {len(stale_tables)} tabelas desatualizadas")
            return self.run_etls()
        
        self.logger.info("Todos os dados estão atualizados")
        return True
    
    def run_etls(self):
        """Executa todos os ETLs"""
        try:
            etl_script = f"{PROJECT_DIR}/AUTOMATION/run_all_etls.sh"
            
            # Tornar executável se necessário
            os.chmod(etl_script, 0o755)
            
            # Executar script de ETLs
            result = subprocess.run(
                [etl_script],
                capture_output=True,
                text=True,
                cwd=PROJECT_DIR
            )
            
            if result.returncode == 0:
                self.logger.info("ETLs executados com sucesso")
                self.save_update_timestamp()
                return True
            else:
                self.logger.error(f"Erro na execução dos ETLs: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao executar ETLs: {e}")
            return False
    
    def save_update_timestamp(self):
        """Salva timestamp da última atualização"""
        update_info = {
            'timestamp': datetime.now().isoformat(),
            'type': 'forced_update',
            'status': 'success'
        }
        
        with open(self.last_update_file, 'w') as f:
            json.dump(update_info, f, indent=2)
    
    def check_cron_status(self):
        """Verifica se o cron está funcionando"""
        try:
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True
            )
            
            if 'KommoAnalytics' in result.stdout:
                self.logger.info("Cron jobs configurados corretamente")
                return True
            else:
                self.logger.warning("Cron jobs não encontrados")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar cron: {e}")
            return False
    
    def create_backup_before_update(self):
        """Cria backup antes da atualização"""
        try:
            backup_script = f"{PROJECT_DIR}/AUTOMATION/backup_database.sh"
            os.chmod(backup_script, 0o755)
            
            result = subprocess.run(
                [backup_script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("Backup criado com sucesso")
                return True
            else:
                self.logger.error(f"Erro no backup: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return False
    
    def verify_dashboard_integrity(self):
        """Verifica integridade do dashboard"""
        try:
            # Verificar se o arquivo principal existe
            main_app = f"{PROJECT_DIR}/DASHBOARD/main_app.py"
            if not os.path.exists(main_app):
                self.logger.error("Arquivo main_app.py não encontrado")
                return False
            
            # Verificar se as tabelas necessárias existem
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            required_tables = [
                'leads_metrics',
                'sales_metrics',
                'commercial_activities',
                'performance_vendedores',
                'performance_canais',
                'monthly_forecasts'
            ]
            
            for table in required_tables:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                if not cursor.fetchone():
                    self.logger.error(f"Tabela {table} não encontrada")
                    cursor.close()
                    conn.close()
                    return False
            
            cursor.close()
            conn.close()
            
            self.logger.info("Integridade do dashboard verificada")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na verificação de integridade: {e}")
            return False
    
    def run_full_guarantee(self):
        """Executa garantia completa de atualização"""
        self.logger.info("🛡️ Iniciando garantia de atualização...")
        
        # 1. Verificar integridade
        if not self.verify_dashboard_integrity():
            self.logger.error("❌ Falha na verificação de integridade")
            return False
        
        # 2. Verificar cron
        if not self.check_cron_status():
            self.logger.warning("⚠️ Cron não configurado - configurando...")
            self.setup_cron()
        
        # 3. Criar backup
        self.create_backup_before_update()
        
        # 4. Forçar atualização se necessário
        if not self.force_update_if_needed():
            self.logger.error("❌ Falha na atualização")
            return False
        
        # 5. Verificar resultado final
        final_freshness = self.check_database_freshness()
        if final_freshness:
            all_fresh = all(status['is_fresh'] for status in final_freshness.values())
            if all_fresh:
                self.logger.info("✅ Garantia de atualização concluída com sucesso")
                return True
            else:
                self.logger.error("❌ Dados ainda desatualizados após atualização")
                return False
        
        return False
    
    def setup_cron(self):
        """Configura cron jobs se necessário"""
        try:
            setup_script = f"{PROJECT_DIR}/AUTOMATION/setup_cron.sh"
            os.chmod(setup_script, 0o755)
            
            result = subprocess.run(
                [setup_script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("Cron configurado com sucesso")
                return True
            else:
                self.logger.error(f"Erro na configuração do cron: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao configurar cron: {e}")
            return False

def main():
    """Função principal"""
    guarantee = UpdateGuarantee()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        # Modo forçado - sempre executa ETLs
        guarantee.logger.info("🔄 Modo forçado - executando ETLs...")
        success = guarantee.run_etls()
    else:
        # Modo normal - verifica e atualiza se necessário
        success = guarantee.run_full_guarantee()
    
    if success:
        print("✅ Garantia de atualização concluída com sucesso")
        sys.exit(0)
    else:
        print("❌ Falha na garantia de atualização")
        sys.exit(1)

if __name__ == "__main__":
    main()
