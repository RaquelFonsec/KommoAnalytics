#!/usr/bin/env python3
"""
Verificação de Execução dos ETLs - Kommo Analytics
Garante que os dados estão sendo atualizados corretamente
"""

import mysql.connector
import os
import subprocess
import sys
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
    print("🔍 VERIFICANDO FRESCURA DOS DADOS")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar dados mais recentes
        cursor.execute("""
            SELECT 
                MAX(created_at) as ultima_atualizacao,
                COUNT(*) as total_registros
            FROM funnel_history 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        funnel_data = cursor.fetchone()
        
        cursor.execute("""
            SELECT 
                MAX(created_at) as ultima_atualizacao,
                COUNT(*) as total_registros
            FROM activity_metrics 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        activity_data = cursor.fetchone()
        
        print(f"📊 Dados do Funil (últimas 24h):")
        print(f"  📅 Última atualização: {funnel_data['ultima_atualizacao']}")
        print(f"  📊 Total de registros: {funnel_data['total_registros']:,}")
        
        print(f"\n📊 Dados de Atividades (últimas 24h):")
        print(f"  📅 Última atualização: {activity_data['ultima_atualizacao']}")
        print(f"  📊 Total de registros: {activity_data['total_registros']:,}")
        
        # Verificar se há dados recentes
        is_fresh = (funnel_data['total_registros'] > 0 and activity_data['total_registros'] > 0)
        
        if is_fresh:
            print("\n✅ DADOS ATUALIZADOS!")
            return True
        else:
            print("\n❌ DADOS DESATUALIZADOS!")
            return False
            
    except Exception as e:
        print(f"Erro ao verificar dados: {e}")
        return False
    finally:
        connection.close()

def check_loss_reasons():
    """Verifica se os motivos de perda estão corretos"""
    print("\n🎯 VERIFICANDO MOTIVOS DE PERDA")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar se há motivos com ID
        cursor.execute("""
            SELECT COUNT(*) as total_ids
            FROM funnel_history 
            WHERE loss_reason_name LIKE 'Motivo ID%'
        """)
        ids_count = cursor.fetchone()
        
        if ids_count['total_ids'] > 0:
            print(f"❌ PROBLEMA: {ids_count['total_ids']} motivos ainda com ID")
            return False
        else:
            print("✅ MOTIVOS DE PERDA CORRETOS!")
            return True
            
    except Exception as e:
        print(f"Erro ao verificar motivos de perda: {e}")
        return False
    finally:
        connection.close()

def check_followups():
    """Verifica se os follow-ups estão corretos"""
    print("\n📞 VERIFICANDO FOLLOW-UPS")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar follow-ups dos últimos 7 dias
        cursor.execute("""
            SELECT 
                SUM(followups_completed) as total_followups,
                COUNT(*) as total_records
            FROM activity_metrics 
            WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        """)
        followup_data = cursor.fetchone()
        
        print(f"📊 Follow-ups dos últimos 7 dias:")
        
        if followup_data['total_followups'] is not None:
            print(f"  🔄 Total de follow-ups: {followup_data['total_followups']:,}")
        else:
            print(f"  🔄 Total de follow-ups: 0")
            
        if followup_data['total_records'] is not None:
            print(f"  📊 Total de registros: {followup_data['total_records']:,}")
        else:
            print(f"  📊 Total de registros: 0")
        
        if followup_data['total_followups'] and followup_data['total_followups'] > 0:
            print("✅ FOLLOW-UPS CORRETOS!")
            return True
        else:
            print("❌ PROBLEMA: Follow-ups zerados")
            return False
            
    except Exception as e:
        print(f"Erro ao verificar follow-ups: {e}")
        return False
    finally:
        connection.close()

def run_etl_manually():
    """Executa os ETLs manualmente se necessário"""
    print("\n🔧 EXECUTANDO ETLs MANUALMENTE")
    print("=" * 50)
    
    try:
        # Executar ETL do módulo 2
        print("🚀 Executando ETL do módulo 2 (Funil)...")
        result = subprocess.run([
            'python3', 'ETL/kommo_etl_modulo2_funil.py'
        ], capture_output=True, text=True, cwd='/home/raquel-fonseca/Projects/KommoAnalytics')
        
        if result.returncode == 0:
            print("✅ ETL do módulo 2 executado com sucesso")
        else:
            print(f"❌ Erro no ETL do módulo 2: {result.stderr}")
            return False
        
        # Aguardar 30 segundos
        import time
        time.sleep(30)
        
        # Executar ETL do módulo 3
        print("🚀 Executando ETL do módulo 3 (Atividades)...")
        result = subprocess.run([
            'python3', 'ETL/kommo_etl_modulo3_atividades.py'
        ], capture_output=True, text=True, cwd='/home/raquel-fonseca/Projects/KommoAnalytics')
        
        if result.returncode == 0:
            print("✅ ETL do módulo 3 executado com sucesso")
        else:
            print(f"❌ Erro no ETL do módulo 3: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Erro ao executar ETLs: {e}")
        return False

def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO DE EXECUÇÃO DOS ETLs")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)
    
    # Verificar dados
    data_fresh = check_data_freshness()
    loss_reasons_ok = check_loss_reasons()
    followups_ok = check_followups()
    
    # Resumo
    print("\n📊 RESUMO DA VERIFICAÇÃO:")
    print("=" * 50)
    print(f"  📊 Dados atualizados: {'✅' if data_fresh else '❌'}")
    print(f"  🎯 Motivos de perda: {'✅' if loss_reasons_ok else '❌'}")
    print(f"  📞 Follow-ups: {'✅' if followups_ok else '❌'}")
    
    # Se há problemas, executar ETLs manualmente
    if not (data_fresh and loss_reasons_ok and followups_ok):
        print("\n⚠️ PROBLEMAS IDENTIFICADOS!")
        print("🔧 Executando ETLs para corrigir...")
        
        if run_etl_manually():
            print("\n✅ ETLs executados com sucesso!")
            print("🔄 Verificando novamente...")
            
            # Verificar novamente
            data_fresh = check_data_freshness()
            loss_reasons_ok = check_loss_reasons()
            followups_ok = check_followups()
            
            if data_fresh and loss_reasons_ok and followups_ok:
                print("\n🎉 TODOS OS PROBLEMAS CORRIGIDOS!")
            else:
                print("\n❌ Ainda há problemas - verificar manualmente")
        else:
            print("\n❌ Falha ao executar ETLs")
    else:
        print("\n🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

