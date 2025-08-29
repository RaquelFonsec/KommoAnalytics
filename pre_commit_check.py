#!/usr/bin/env python3
"""
Verificação Pré-Commit - Dashboard Kommo Analytics
Script simples para garantir que o dashboard não desatualize
"""

import mysql.connector
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('env_template.txt')

def quick_check():
    """Verificação rápida antes do commit"""
    print("🛡️ VERIFICAÇÃO PRÉ-COMMIT - DASHBOARD")
    print("=" * 50)
    
    # 1. Verificar se o dashboard está rodando
    print("1️⃣ Verificando dashboard...")
    try:
        result = subprocess.run(['pgrep', '-f', 'streamlit'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Dashboard rodando")
            dashboard_ok = True
        else:
            print("   ❌ Dashboard não está rodando")
            dashboard_ok = False
    except:
        print("   ❌ Erro ao verificar dashboard")
        dashboard_ok = False
    
    # 2. Verificar conexão com banco
    print("2️⃣ Verificando banco de dados...")
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        print("   ✅ Conexão com banco OK")
        connection.close()
        db_ok = True
    except Exception as e:
        print(f"   ❌ Erro no banco: {e}")
        db_ok = False
    
    # 3. Verificar se há dados recentes
    print("3️⃣ Verificando dados recentes...")
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = connection.cursor(dictionary=True)
        
        # Verificar leads recentes
        cursor.execute("SELECT COUNT(*) as total FROM leads_metrics WHERE created_date >= CURDATE() - INTERVAL 7 DAY")
        result = cursor.fetchone()
        leads_recentes = result['total']
        
        # Verificar deals recentes
        cursor.execute("SELECT COUNT(*) as total FROM funnel_history WHERE created_at >= CURDATE() - INTERVAL 7 DAY")
        result = cursor.fetchone()
        deals_recentes = result['total']
        
        print(f"   📊 Leads últimos 7 dias: {leads_recentes}")
        print(f"   📊 Deals últimos 7 dias: {deals_recentes}")
        
        if leads_recentes > 0 and deals_recentes > 0:
            print("   ✅ Dados recentes encontrados")
            dados_ok = True
        else:
            print("   ⚠️ Poucos dados recentes")
            dados_ok = False
        
        connection.close()
    except Exception as e:
        print(f"   ❌ Erro ao verificar dados: {e}")
        dados_ok = False
    
    # 4. Verificar scripts ETL principais
    print("4️⃣ Verificando scripts ETL...")
    etl_scripts = [
        'ETL/kommo_etl_modulo1_leads.py',
        'ETL/kommo_etl_modulo2_funil.py',
        'ETL/kommo_etl_modulo3_atividades.py',
        'ETL/kommo_etl_modulo5_performance.py',
        'ETL/kommo_etl_modulo6_forecast_integrado.py'
    ]
    
    scripts_ok = True
    for script in etl_scripts:
        if os.path.exists(script):
            print(f"   ✅ {script}")
        else:
            print(f"   ❌ {script} - FALTANDO")
            scripts_ok = False
    
    # Resultado final
    print("\n" + "=" * 50)
    print("📋 RESULTADO DA VERIFICAÇÃO")
    print("=" * 50)
    
    all_ok = dashboard_ok and db_ok and dados_ok and scripts_ok
    
    if all_ok:
        print("🎉 VERIFICAÇÃO PASSOU!")
        print("✅ PODE FAZER COMMIT COM SEGURANÇA")
        
        # Criar backup automático
        print("\n💾 Criando backup automático...")
        try:
            backup_file = f"backup_pre_commit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            backup_cmd = f"mysqldump -h {os.getenv('DB_HOST')} -u {os.getenv('DB_USER')} -p{os.getenv('DB_PASSWORD')} {os.getenv('DB_NAME')} > {backup_file}"
            subprocess.run(backup_cmd, shell=True, capture_output=True)
            print(f"   ✅ Backup criado: {backup_file}")
        except:
            print("   ⚠️ Erro ao criar backup")
        
        print("\n💡 APÓS O COMMIT:")
        print("   1. Monitore o dashboard por 24h")
        print("   2. Execute: python AUTOMATION/quality_assurance.py")
        print("   3. Verifique se os dados continuam atualizando")
        
        return True
        
    else:
        print("❌ VERIFICAÇÃO FALHOU!")
        print("⚠️ NÃO FAÇA COMMIT ATÉ CORRIGIR:")
        
        if not dashboard_ok:
            print("   - Inicie o dashboard: streamlit run DASHBOARD/main_app.py")
        if not db_ok:
            print("   - Verifique credenciais do banco")
        if not dados_ok:
            print("   - Execute ETLs: python ETL/kommo_etl_modulo*.py")
        if not scripts_ok:
            print("   - Verifique se todos os scripts ETL existem")
        
        return False

if __name__ == "__main__":
    success = quick_check()
    exit(0 if success else 1)
