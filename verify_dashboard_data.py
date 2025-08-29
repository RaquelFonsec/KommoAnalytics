#!/usr/bin/env python3
"""
Script para verificar se os dados do ETL estão sendo exibidos corretamente no dashboard
Foca nos problemas específicos mencionados pelo usuário
"""

import mysql.connector
import os
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

def check_module1_leads():
    """Verifica dados do Módulo 1 - Leads e Origem"""
    print("\n=== MÓDULO 1 - LEADS E ORIGEM ===")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar total de leads
        cursor.execute("SELECT COUNT(*) as total FROM leads_metrics")
        result = cursor.fetchone()
        print(f"Total de leads: {result['total']}")
        
        # Verificar origem dos leads
        cursor.execute("""
            SELECT primary_source, COUNT(*) as count 
            FROM leads_metrics 
            GROUP BY primary_source 
            ORDER BY count DESC
        """)
        sources = cursor.fetchall()
        print("\nOrigem dos leads:")
        for source in sources:
            print(f"  {source['primary_source']}: {source['count']}")
        
        # Verificar tempo de resposta
        cursor.execute("""
            SELECT AVG(response_time_hours) as avg_response 
            FROM leads_metrics 
            WHERE response_time_hours IS NOT NULL
        """)
        result = cursor.fetchone()
        print(f"\nTempo médio de resposta: {result['avg_response']:.2f} horas")
        
        # Verificar leads com origem desconhecida
        cursor.execute("""
            SELECT COUNT(*) as unknown_count 
            FROM leads_metrics 
            WHERE primary_source = 'Origem Desconhecida'
        """)
        result = cursor.fetchone()
        print(f"Leads com origem desconhecida: {result['unknown_count']}")
        
    except Exception as e:
        print(f"Erro ao verificar Módulo 1: {e}")
    finally:
        connection.close()

def check_module2_funnel():
    """Verifica dados do Módulo 2 - Funil de Conversão"""
    print("\n=== MÓDULO 2 - FUNIL DE CONVERSÃO ===")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar motivos de perda
        cursor.execute("""
            SELECT loss_reason_name, COUNT(*) as count 
            FROM funnel_history 
            WHERE loss_reason_name IS NOT NULL 
            GROUP BY loss_reason_name 
            ORDER BY count DESC
            LIMIT 10
        """)
        reasons = cursor.fetchall()
        print("\nMotivos de perda (top 10):")
        for reason in reasons:
            print(f"  {reason['loss_reason_name']}: {reason['count']}")
        
        # Verificar se há IDs em vez de nomes
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM funnel_history 
            WHERE loss_reason_name LIKE '%ID%' OR loss_reason_name LIKE '%id%'
        """)
        result = cursor.fetchone()
        print(f"\nMotivos com ID: {result['count']}")
        
    except Exception as e:
        print(f"Erro ao verificar Módulo 2: {e}")
    finally:
        connection.close()

def check_module3_activities():
    """Verifica dados do Módulo 3 - Atividades Comerciais"""
    print("\n=== MÓDULO 3 - ATIVIDADES COMERCIAIS ===")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar follow-ups por vendedor
        cursor.execute("""
            SELECT 
                user_name,
                COUNT(CASE WHEN contact_type = 'followup' THEN 1 END) as followups,
                COUNT(CASE WHEN contact_type = 'meeting' THEN 1 END) as meetings,
                COUNT(CASE WHEN contact_type = 'call' THEN 1 END) as calls,
                COUNT(*) as total_activities
            FROM commercial_activities 
            GROUP BY user_name 
            ORDER BY followups DESC
        """)
        activities = cursor.fetchall()
        print("\nAtividades por vendedor:")
        for activity in activities:
            print(f"  {activity['user_name']}: {activity['followups']} follow-ups, {activity['meetings']} reuniões, {activity['calls']} ligações (total: {activity['total_activities']})")
        
        # Verificar tipos de contato
        cursor.execute("""
            SELECT contact_type, COUNT(*) as count 
            FROM commercial_activities 
            GROUP BY contact_type 
            ORDER BY count DESC
        """)
        types = cursor.fetchall()
        print("\nTipos de contato:")
        for type_ in types:
            print(f"  {type_['contact_type']}: {type_['count']}")
        
    except Exception as e:
        print(f"Erro ao verificar Módulo 3: {e}")
    finally:
        connection.close()

def check_module4_conversion():
    """Verifica dados do Módulo 4 - Conversão e Receita"""
    print("\n=== MÓDULO 4 - CONVERSÃO E RECEITA ===")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar vendas
        cursor.execute("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) as won_deals,
                COUNT(CASE WHEN status_name = 'Venda perdida' THEN 1 END) as lost_deals,
                SUM(CASE WHEN status_name = 'Venda ganha' THEN sale_price ELSE 0 END) as total_revenue
            FROM sales_metrics
        """)
        result = cursor.fetchone()
        print(f"Total de deals: {result['total_deals']}")
        print(f"Deals ganhos: {result['won_deals']}")
        print(f"Deals perdidos: {result['lost_deals']}")
        print(f"Receita total: R$ {result['total_revenue']:,.2f}")
        
        if result['total_deals'] > 0:
            win_rate = (result['won_deals'] / result['total_deals']) * 100
            print(f"Win Rate: {win_rate:.1f}%")
        
    except Exception as e:
        print(f"Erro ao verificar Módulo 4: {e}")
    finally:
        connection.close()

def check_module5_performance():
    """Verifica dados do Módulo 5 - Performance por Pessoa e Canal"""
    print("\n=== MÓDULO 5 - PERFORMANCE POR PESSOA E CANAL ===")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar performance por vendedor
        cursor.execute("""
            SELECT 
                user_name,
                leads_contactados,
                vendas_fechadas,
                receita_total,
                conversion_rate
            FROM performance_vendedores 
            ORDER BY receita_total DESC
        """)
        sellers = cursor.fetchall()
        print("\nPerformance por vendedor:")
        for seller in sellers:
            print(f"  {seller['user_name']}: {seller['leads_contactados']} leads, {seller['vendas_fechadas']} vendas, R$ {seller['receita_total']:,.2f}, {seller['conversion_rate']:.1f}%")
        
        # Verificar performance por canal
        cursor.execute("""
            SELECT 
                canal_origem,
                total_leads,
                conversion_rate,
                ticket_medio
            FROM performance_canais 
            ORDER BY conversion_rate DESC
        """)
        channels = cursor.fetchall()
        print("\nPerformance por canal:")
        for channel in channels:
            print(f"  {channel['canal_origem']}: {channel['total_leads']} leads, {channel['conversion_rate']:.1f}%, R$ {channel['ticket_medio']:,.2f}")
        
    except Exception as e:
        print(f"Erro ao verificar Módulo 5: {e}")
    finally:
        connection.close()

def check_module6_forecast():
    """Verifica dados do Módulo 6 - Previsibilidade"""
    print("\n=== MÓDULO 6 - PREVISIBILIDADE ===")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar previsões mensais
        cursor.execute("""
            SELECT 
                mes_ano,
                meta_receita,
                previsao_receita,
                previsao_leads,
                previsao_win_rate
            FROM monthly_forecasts 
            ORDER BY mes_ano DESC
            LIMIT 3
        """)
        forecasts = cursor.fetchall()
        print("\nPrevisões mensais (últimos 3 meses):")
        for forecast in forecasts:
            print(f"  {forecast['mes_ano']}: Meta R$ {forecast['meta_receita']:,.2f}, Previsto R$ {forecast['previsao_receita']:,.2f}, Leads {forecast['previsao_leads']}, Win Rate {forecast['previsao_win_rate']:.1f}%")
        
        # Verificar gaps de previsão
        cursor.execute("""
            SELECT 
                gap_receita,
                gap_leads,
                risco_meta
            FROM forecast_gaps 
            ORDER BY gap_receita DESC
        """)
        gaps = cursor.fetchall()
        print("\nGaps de previsão:")
        for gap in gaps:
            print(f"  Gap Receita: R$ {gap['gap_receita']:,.2f}, Gap Leads: {gap['gap_leads']}, Risco: {gap['risco_meta']}")
        
    except Exception as e:
        print(f"Erro ao verificar Módulo 6: {e}")
    finally:
        connection.close()

def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO DOS DADOS DO DASHBOARD")
    print("=" * 50)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Verificar cada módulo
    check_module1_leads()
    check_module2_funnel()
    check_module3_activities()
    check_module4_conversion()
    check_module5_performance()
    check_module6_forecast()
    
    print("\n" + "=" * 50)
    print("✅ Verificação concluída!")

if __name__ == "__main__":
    main()
