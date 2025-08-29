#!/usr/bin/env python3
"""
Sistema de Garantia de Estabilidade do Dashboard
Verifica e protege contra desatualizações após commits
"""

import mysql.connector
import os
import subprocess
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('env_template.txt')

def get_db_connection():
    """Conecta ao banco de dados MySQL"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def check_data_freshness():
    """Verifica se os dados estão atualizados"""
    print("🔍 VERIFICANDO FRESCURA DOS DADOS...")
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar última atualização de cada módulo
        modules = [
            ('leads_metrics', 'Módulo 1 - Leads'),
            ('funnel_history', 'Módulo 2 - Funil'),
            ('commercial_activities', 'Módulo 3 - Atividades'),
            ('sales_metrics', 'Módulo 4 - Vendas'),
            ('performance_vendedores', 'Módulo 5 - Performance'),
            ('monthly_forecasts', 'Módulo 6 - Previsões')
        ]
        
        all_fresh = True
        
        for table, module_name in modules:
            try:
                # Verificar última atualização
                if table == 'leads_metrics':
                    cursor.execute(f"SELECT MAX(created_date) as last_update FROM {table}")
                elif table == 'funnel_history':
                    cursor.execute(f"SELECT MAX(created_at) as last_update FROM {table}")
                elif table == 'monthly_forecasts':
                    cursor.execute(f"SELECT MAX(created_date) as last_update FROM {table}")
                else:
                    cursor.execute(f"SELECT MAX(created_date) as last_update FROM {table}")
                
                result = cursor.fetchone()
                last_update = result['last_update']
                
                if last_update:
                    # Converter para datetime se necessário
                    if isinstance(last_update, str):
                        last_update = datetime.strptime(last_update, '%Y-%m-%d')
                    elif isinstance(last_update, datetime):
                        last_update = last_update.date()
                    
                    days_old = (datetime.now().date() - last_update).days
                    status = "✅" if days_old <= 3 else "❌"
                    print(f"  {status} {module_name}: {days_old} dias atrás")
                    
                    if days_old > 3:
                        all_fresh = False
                else:
                    print(f"  ⚠️ {module_name}: Sem dados")
                    all_fresh = False
                    
            except Exception as e:
                print(f"  ❌ {module_name}: Erro - {e}")
                all_fresh = False
        
        return all_fresh
        
    except Exception as e:
        print(f"Erro na verificação: {e}")
        return False
    finally:
        connection.close()

def check_etl_processes():
    """Verifica se os processos ETL estão funcionando"""
    print("\n⚙️ VERIFICANDO PROCESSOS ETL...")
    
    # Verificar se os scripts ETL existem e são executáveis
    etl_scripts = [
        'ETL/kommo_etl_modulo1_leads.py',
        'ETL/kommo_etl_modulo2_funil.py',
        'ETL/kommo_etl_modulo3_atividades.py',
        'ETL/kommo_etl_modulo4_conversao.py',
        'ETL/kommo_etl_modulo5_performance.py',
        'ETL/kommo_etl_modulo6_forecast_integrado.py'
    ]
    
    all_scripts_ok = True
    
    for script in etl_scripts:
        if os.path.exists(script):
            print(f"  ✅ {script}")
        else:
            print(f"  ❌ {script} - NÃO ENCONTRADO")
            all_scripts_ok = False
    
    return all_scripts_ok

def check_cron_jobs():
    """Verifica se os cron jobs estão configurados"""
    print("\n⏰ VERIFICANDO CRON JOBS...")
    
    try:
        # Verificar cron jobs ativos
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        
        if result.returncode == 0:
            cron_content = result.stdout
            print("  ✅ Cron jobs configurados:")
            
            # Verificar jobs importantes
            important_jobs = [
                'kommo_etl_modulo1_leads.py',
                'kommo_etl_modulo2_funil.py',
                'kommo_etl_modulo3_atividades.py',
                'kommo_etl_modulo4_vendas.py',
                'kommo_etl_modulo5_performance.py',
                'kommo_etl_modulo6_forecast_integrado.py'
            ]
            
            for job in important_jobs:
                if job in cron_content:
                    print(f"    ✅ {job}")
                else:
                    print(f"    ❌ {job} - NÃO CONFIGURADO")
            
            return True
        else:
            print("  ❌ Nenhum cron job configurado")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro ao verificar cron: {e}")
        return False

def check_dashboard_status():
    """Verifica se o dashboard está rodando"""
    print("\n🌐 VERIFICANDO STATUS DO DASHBOARD...")
    
    try:
        # Verificar se o processo Streamlit está rodando
        result = subprocess.run(['pgrep', '-f', 'streamlit'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ Dashboard Streamlit está rodando")
            return True
        else:
            print("  ❌ Dashboard Streamlit NÃO está rodando")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro ao verificar dashboard: {e}")
        return False

def check_database_connectivity():
    """Verifica conectividade com o banco"""
    print("\n🗄️ VERIFICANDO CONECTIVIDADE COM BANCO...")
    
    connection = get_db_connection()
    if connection:
        print("  ✅ Conexão com banco OK")
        connection.close()
        return True
    else:
        print("  ❌ Falha na conexão com banco")
        return False

def create_backup():
    """Cria backup antes de qualquer operação crítica"""
    print("\n💾 CRIANDO BACKUP DE SEGURANÇA...")
    
    try:
        backup_file = f"backup_pre_commit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        backup_command = f"mysqldump -h {os.getenv('DB_HOST')} -u {os.getenv('DB_USER')} -p{os.getenv('DB_PASSWORD')} {os.getenv('DB_NAME')} > {backup_file}"
        
        result = subprocess.run(backup_command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ Backup criado: {backup_file}")
            return True
        else:
            print(f"  ❌ Erro no backup: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro ao criar backup: {e}")
        return False

def run_safety_checks():
    """Executa todas as verificações de segurança"""
    print("=" * 80)
    print("🛡️ VERIFICAÇÕES DE SEGURANÇA - DASHBOARD")
    print("=" * 80)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 80)
    
    checks = {
        "Dados Atualizados": check_data_freshness(),
        "Scripts ETL": check_etl_processes(),
        "Cron Jobs": check_cron_jobs(),
        "Dashboard Rodando": check_dashboard_status(),
        "Conexão Banco": check_database_connectivity()
    }
    
    print("\n" + "=" * 80)
    print("📋 RESUMO DAS VERIFICAÇÕES")
    print("=" * 80)
    
    all_ok = True
    for check_name, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check_name}: {'OK' if status else 'FALHA'}")
        if not status:
            all_ok = False
    
    print("\n" + "=" * 80)
    
    if all_ok:
        print("🎉 TODAS AS VERIFICAÇÕES PASSARAM!")
        print("✅ O dashboard está seguro para commit")
        
        # Criar backup de segurança
        create_backup()
        
        print("\n💡 RECOMENDAÇÕES:")
        print("  1. Faça commit normalmente")
        print("  2. Após o commit, execute: python AUTOMATION/quality_assurance.py")
        print("  3. Monitore o dashboard por 24h")
        
    else:
        print("⚠️ VERIFICAÇÕES FALHARAM!")
        print("❌ NÃO FAÇA COMMIT ATÉ CORRIGIR OS PROBLEMAS")
        
        print("\n🔧 AÇÕES NECESSÁRIAS:")
        if not checks["Dados Atualizados"]:
            print("  1. Execute os ETLs: python ETL/kommo_etl_modulo*.py")
        if not checks["Scripts ETL"]:
            print("  2. Verifique se todos os scripts ETL existem")
        if not checks["Cron Jobs"]:
            print("  3. Configure cron jobs: bash AUTOMATION/setup_cron.sh")
        if not checks["Dashboard Rodando"]:
            print("  4. Inicie o dashboard: streamlit run DASHBOARD/main_app.py")
        if not checks["Conexão Banco"]:
            print("  5. Verifique credenciais do banco")
    
    print("=" * 80)
    return all_ok

def create_protection_script():
    """Cria script de proteção para Git hooks"""
    print("\n🔒 CRIANDO SCRIPT DE PROTEÇÃO...")
    
    protection_script = """#!/bin/bash
# Git Hook: pre-commit
# Proteção contra desatualização do dashboard

echo "🛡️ Verificando segurança do dashboard..."

# Executar verificações
python3 guarantee_dashboard_stability.py

if [ $? -eq 0 ]; then
    echo "✅ Commit permitido"
    exit 0
else
    echo "❌ Commit bloqueado - Corrija os problemas primeiro"
    exit 1
fi
"""
    
    with open('.git/hooks/pre-commit', 'w') as f:
        f.write(protection_script)
    
    # Tornar executável
    os.chmod('.git/hooks/pre-commit', 0o755)
    
    print("  ✅ Script de proteção criado: .git/hooks/pre-commit")
    print("  📝 Agora todos os commits serão verificados automaticamente")

def main():
    """Função principal"""
    print("🛡️ SISTEMA DE GARANTIA DE ESTABILIDADE DO DASHBOARD")
    print("=" * 60)
    
    # Executar verificações
    is_safe = run_safety_checks()
    
    if is_safe:
        # Perguntar se quer criar proteção automática
        response = input("\n🔒 Deseja criar proteção automática para commits? (s/n): ")
        if response.lower() == 's':
            create_protection_script()
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Execute este script antes de cada commit")
    print("2. Ou configure a proteção automática")
    print("3. Monitore o dashboard após commits")
    print("4. Use: python AUTOMATION/quality_assurance.py para verificações completas")

if __name__ == "__main__":
    main()
