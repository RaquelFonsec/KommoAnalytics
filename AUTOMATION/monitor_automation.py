#!/usr/bin/env python3
"""
Monitor de Automação - Kommo Analytics
Verifica se os ETLs estão sendo executados automaticamente e gera relatórios
"""

import os
import sys
import sqlite3
import mysql.connector
from datetime import datetime, timedelta
import json
import subprocess
from pathlib import Path

# Configurações
PROJECT_DIR = "/home/raquel-fonseca/KommoAnalytics"
LOG_DIR = f"{PROJECT_DIR}/LOGS"
DB_CONFIG = {
    'host': 'localhost',
    'user': 'kommo_analytics',
    'password': 'previdas_ltda_2025',
    'database': 'kommo_analytics'
}

def check_cron_status():
    """Verifica se o cron está configurado corretamente"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            cron_content = result.stdout
            if 'KommoAnalytics' in cron_content and 'run_all_etls.sh' in cron_content:
                return True, " Cron configurado corretamente"
            else:
                return False, "Cron não encontrado para KommoAnalytics"
        else:
            return False, " Erro ao verificar cron"
    except Exception as e:
        return False, f" Erro ao verificar cron: {e}"

def check_last_execution():
    """Verifica a última execução dos ETLs"""
    status_file = f"{LOG_DIR}/last_execution_status.txt"
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            content = f.read().strip()
            if 'SUCCESS: 6/6' in content:
                return True, " Última execução: Todos os ETLs bem-sucedidos"
            elif 'PARTIAL:' in content:
                return False, " Última execução: Alguns ETLs falharam"
            else:
                return False, " Status da última execução desconhecido"
    else:
        return False, " Arquivo de status não encontrado"

def check_log_files():
    """Verifica se os logs estão sendo gerados"""
    today = datetime.now().strftime('%Y%m%d')
    log_files = []
    
    for i in range(1, 7):
        if i == 1:
            name = "módulo 1 - leads"
        elif i == 2:
            name = "módulo 2 - funil"
        elif i == 3:
            name = "módulo 3 - atividades"
        elif i == 4:
            name = "módulo 4 - conversão"
        elif i == 5:
            name = "módulo 5 - performance"
        else:
            name = "módulo 6 - forecast"
        
        log_file = f"{LOG_DIR}/{name}_{today}.log"
        if os.path.exists(log_file):
            log_files.append(f" {name}")
        else:
            log_files.append(f" {name}")
    
    return log_files

def check_database_freshness():
    """Verifica se os dados do banco estão atualizados"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar última atualização de cada módulo
        checks = []
        
        # Módulo 1 - Leads
        cursor.execute("SELECT MAX(created_date) FROM leads_metrics")
        result = cursor.fetchone()
        if result and result[0]:
            last_lead_date = result[0]
            days_old = (datetime.now().date() - last_lead_date).days
            if days_old <= 1:
                checks.append(f" Leads: Atualizados há {days_old} dia(s)")
            else:
                checks.append(f" Leads: Atualizados há {days_old} dias")
        
        # Módulo 3 - Atividades
        cursor.execute("SELECT MAX(created_date) FROM commercial_activities")
        result = cursor.fetchone()
        if result and result[0]:
            last_activity_date = result[0]
            days_old = (datetime.now().date() - last_activity_date).days
            if days_old <= 1:
                checks.append(f" Atividades: Atualizadas há {days_old} dia(s)")
            else:
                checks.append(f" Atividades: Atualizadas há {days_old} dias")
        
        # Módulo 4 - Vendas
        cursor.execute("SELECT MAX(created_date) FROM sales_metrics")
        result = cursor.fetchone()
        if result and result[0]:
            last_sale_date = result[0]
            days_old = (datetime.now().date() - last_sale_date).days
            if days_old <= 1:
                checks.append(f" Vendas: Atualizadas há {days_old} dia(s)")
            else:
                checks.append(f" Vendas: Atualizadas há {days_old} dias")
        
        cursor.close()
        conn.close()
        return checks
        
    except Exception as e:
        return [f" Erro ao verificar banco: {e}"]

def generate_report():
    """Gera relatório completo de monitoramento"""
    print("🔍 MONITORAMENTO DE AUTOMAÇÃO - KOMMO ANALYTICS")
    print("=" * 60)
    
    # Verificar cron
    cron_ok, cron_msg = check_cron_status()
    print(f"\n📅 STATUS DO CRON:")
    print(f"   {cron_msg}")
    
    # Verificar última execução
    exec_ok, exec_msg = check_last_execution()
    print(f"\n ÚLTIMA EXECUÇÃO:")
    print(f"   {exec_msg}")
    
    # Verificar logs
    print(f"\n LOGS DE HOJE ({datetime.now().strftime('%d/%m/%Y')}):")
    log_files = check_log_files()
    for log in log_files:
        print(f"   {log}")
    
    # Verificar banco de dados
    print(f"\n🗄️ FRESCURA DOS DADOS:")
    db_checks = check_database_freshness()
    for check in db_checks:
        print(f"   {check}")
    
    # Resumo
    print(f"\n📊 RESUMO:")
    if cron_ok and exec_ok:
        print("   🎉 AUTOMAÇÃO FUNCIONANDO PERFEITAMENTE!")
        print("   ✅ Dados atualizados diariamente às 6h")
        print("   ✅ Próxima execução: Amanhã às 6h")
    elif cron_ok:
        print("   ⚠️ Cron configurado, mas última execução falhou")
        print("   🔧 Verificar logs para identificar problemas")
    else:
        print("   ❌ Automação não configurada corretamente")
        print("   🔧 Executar: ./AUTOMATION/setup_cron.sh")
    
    print(f"\n📁 Logs em: {LOG_DIR}")
    print(f"🔧 Script de configuração: ./AUTOMATION/setup_cron.sh")
    print(f"🧪 Teste manual: ./AUTOMATION/run_all_etls.sh")

if __name__ == "__main__":
    generate_report()
