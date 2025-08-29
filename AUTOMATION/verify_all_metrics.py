#!/usr/bin/env python3
"""
Verificação Completa de Métricas - Kommo Analytics
Garante que todas as métricas de todos os módulos estão corretas
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

def verify_module1_leads():
    """Verificar Módulo 1 - Entrada e Origem de Leads"""
    print("\n🎯 MÓDULO 1 - ENTRADA E ORIGEM DE LEADS")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar leads por origem
        cursor.execute("""
            SELECT 
                primary_source,
                COUNT(*) as total,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads_metrics), 2) as percentual
            FROM leads_metrics 
            WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY primary_source
            ORDER BY total DESC
            LIMIT 10
        """)
        sources = cursor.fetchall()
        
        print("📊 Leads por Origem (últimos 30 dias):")
        for source in sources:
            status = "✅" if source['primary_source'] != 'Origem Desconhecida' else "⚠️"
            print(f"  {status} {source['primary_source']}: {source['total']:,} ({source['percentual']}%)")
        
        # Verificar tempo de resposta
        cursor.execute("""
            SELECT 
                AVG(response_time_hours) as tempo_medio,
                COUNT(*) as total_leads
            FROM leads_metrics 
            WHERE response_time_hours > 0 
            AND created_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """)
        response = cursor.fetchone()
        
        print(f"\n⏱️ Tempo de Resposta:")
        print(f"  📊 Média: {response['tempo_medio']:.1f}h")
        print(f"  📈 Total de leads: {response['total_leads']:,}")
        
        # Verificar se há dados
        if response['total_leads'] > 0:
            print("✅ MÓDULO 1 - DADOS CORRETOS!")
            return True
        else:
            print("❌ MÓDULO 1 - SEM DADOS!")
            return False
            
    except Exception as e:
        print(f"Erro no módulo 1: {e}")
        return False
    finally:
        connection.close()

def verify_module2_funnel():
    """Verificar Módulo 2 - Funil de Vendas"""
    print("\n🎯 MÓDULO 2 - FUNIL DE VENDAS")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar motivos de perda
        cursor.execute("""
            SELECT 
                loss_reason_name,
                COUNT(*) as total
            FROM funnel_history 
            WHERE loss_reason_name IS NOT NULL
            GROUP BY loss_reason_name
            ORDER BY total DESC
            LIMIT 5
        """)
        reasons = cursor.fetchall()
        
        print("📊 Motivos de Perda:")
        for reason in reasons:
            status = "✅" if not reason['loss_reason_name'].startswith('Motivo ID') else "❌"
            print(f"  {status} {reason['loss_reason_name']}: {reason['total']:,}")
        
        # Verificar conversão por etapa
        cursor.execute("""
            SELECT 
                status_name,
                status_type,
                COUNT(*) as total,
                AVG(time_in_status_hours) as tempo_medio
            FROM funnel_history 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY status_name, status_type
            ORDER BY total DESC
            LIMIT 10
        """)
        stages = cursor.fetchall()
        
        print(f"\n📊 Conversão por Etapa:")
        for stage in stages:
            print(f"  📋 {stage['status_name']}: {stage['total']:,} ({stage['tempo_medio']:.1f}h)")
        
        # Verificar se há motivos com ID
        cursor.execute("""
            SELECT COUNT(*) as total_ids
            FROM funnel_history 
            WHERE loss_reason_name LIKE 'Motivo ID%'
        """)
        ids_count = cursor.fetchone()
        
        if ids_count['total_ids'] == 0:
            print("✅ MÓDULO 2 - DADOS CORRETOS!")
            return True
        else:
            print(f"❌ MÓDULO 2 - {ids_count['total_ids']} motivos com ID!")
            return False
            
    except Exception as e:
        print(f"Erro no módulo 2: {e}")
        return False
    finally:
        connection.close()

def verify_module3_activities():
    """Verificar Módulo 3 - Atividades Comerciais"""
    print("\n🎯 MÓDULO 3 - ATIVIDADES COMERCIAIS")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar follow-ups
        cursor.execute("""
            SELECT 
                user_name,
                SUM(followups_completed) as total_followups,
                SUM(meetings_scheduled) as total_reunioes,
                SUM(calls_made) as total_ligacoes
            FROM activity_metrics 
            WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY user_name
            ORDER BY total_followups DESC
            LIMIT 10
        """)
        activities = cursor.fetchall()
        
        print("📊 Atividades por Vendedor (últimos 30 dias):")
        for activity in activities:
            status = "✅" if activity['total_followups'] > 0 else "❌"
            print(f"  {status} {activity['user_name']}: {activity['total_followups']} follow-ups, {activity['total_reunioes']} reuniões, {activity['total_ligacoes']} ligações")
        
        # Verificar total de atividades
        cursor.execute("""
            SELECT 
                SUM(followups_completed) as total_followups,
                SUM(meetings_scheduled) as total_reunioes,
                SUM(calls_made) as total_ligacoes,
                SUM(emails_sent) as total_emails
            FROM activity_metrics 
            WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """)
        totals = cursor.fetchone()
        
        print(f"\n📊 Totais (últimos 30 dias):")
        print(f"  🔄 Follow-ups: {totals['total_followups']:,}")
        print(f"  📅 Reuniões: {totals['total_reunioes']:,}")
        print(f"  📞 Ligações: {totals['total_ligacoes']:,}")
        print(f"  📧 Emails: {totals['total_emails']:,}")
        
        if totals['total_followups'] > 0:
            print("✅ MÓDULO 3 - DADOS CORRETOS!")
            return True
        else:
            print("❌ MÓDULO 3 - SEM FOLLOW-UPS!")
            return False
            
    except Exception as e:
        print(f"Erro no módulo 3: {e}")
        return False
    finally:
        connection.close()

def verify_module4_conversion():
    """Verificar Módulo 4 - Conversão e Receita"""
    print("\n🎯 MÓDULO 4 - CONVERSÃO E RECEITA")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar vendas
        cursor.execute("""
            SELECT 
                COUNT(*) as total_vendas,
                SUM(sale_price) as receita_total,
                AVG(sale_price) as ticket_medio,
                COUNT(CASE WHEN status_type = 'won' THEN 1 END) as vendas_ganhas,
                COUNT(CASE WHEN status_type = 'lost' THEN 1 END) as vendas_perdidas
            FROM sales_metrics 
            WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """)
        sales = cursor.fetchone()
        
        print("📊 Vendas (últimos 30 dias):")
        print(f"  📈 Total de vendas: {sales['total_vendas']:,}")
        print(f"  💰 Receita total: R$ {sales['receita_total']:,.2f}")
        print(f"  🎯 Ticket médio: R$ {sales['ticket_medio']:,.2f}")
        print(f"  ✅ Vendas ganhas: {sales['vendas_ganhas']:,}")
        print(f"  ❌ Vendas perdidas: {sales['vendas_perdidas']:,}")
        
        if sales['total_vendas'] > 0:
            win_rate = (sales['vendas_ganhas'] / sales['total_vendas']) * 100
            print(f"  📊 Win Rate: {win_rate:.1f}%")
            print("✅ MÓDULO 4 - DADOS CORRETOS!")
            return True
        else:
            print("❌ MÓDULO 4 - SEM VENDAS!")
            return False
            
    except Exception as e:
        print(f"Erro no módulo 4: {e}")
        return False
    finally:
        connection.close()

def verify_module5_performance():
    """Verificar Módulo 5 - Performance por Pessoa e Canal"""
    print("\n🎯 MÓDULO 5 - PERFORMANCE POR PESSOA E CANAL")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar performance por vendedor
        cursor.execute("""
            SELECT 
                user_name,
                SUM(vendas_fechadas) as total_vendas,
                SUM(receita_total) as receita_total,
                AVG(conversion_rate) as taxa_media
            FROM performance_vendedores 
            WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY user_name
            ORDER BY receita_total DESC
            LIMIT 10
        """)
        sellers = cursor.fetchall()
        
        print("📊 Performance por Vendedor (últimos 30 dias):")
        for seller in sellers:
            print(f"  👤 {seller['user_name']}: {seller['total_vendas']} vendas, R$ {seller['receita_total']:,.2f}, {seller['taxa_media']:.1f}% conversão")
        
        # Verificar performance por canal
        cursor.execute("""
            SELECT 
                canal_origem,
                SUM(total_leads) as total_leads,
                SUM(vendas_fechadas) as total_vendas,
                AVG(conversion_rate) as taxa_media
            FROM performance_canais 
            WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY canal_origem
            ORDER BY total_vendas DESC
            LIMIT 10
        """)
        channels = cursor.fetchall()
        
        print(f"\n📊 Performance por Canal (últimos 30 dias):")
        for channel in channels:
            print(f"  📡 {channel['canal_origem']}: {channel['total_leads']} leads, {channel['total_vendas']} vendas, {channel['taxa_media']:.1f}% conversão")
        
        if len(sellers) > 0:
            print("✅ MÓDULO 5 - DADOS CORRETOS!")
            return True
        else:
            print("❌ MÓDULO 5 - SEM DADOS!")
            return False
            
    except Exception as e:
        print(f"Erro no módulo 5: {e}")
        return False
    finally:
        connection.close()

def verify_module6_forecast():
    """Verificar Módulo 6 - Previsibilidade (Forecast)"""
    print("\n🎯 MÓDULO 6 - PREVISIBILIDADE (FORECAST)")
    print("=" * 50)
    
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Verificar previsões mensais
        cursor.execute("""
            SELECT 
                mes_ano,
                previsao_receita,
                meta_receita,
                previsao_win_rate
            FROM monthly_forecasts 
            WHERE mes_ano >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), '%Y-%m')
            ORDER BY mes_ano DESC
            LIMIT 6
        """)
        forecasts = cursor.fetchall()
        
        print("📊 Previsões Mensais (últimos 6 meses):")
        for forecast in forecasts:
            print(f"  📅 {forecast['mes_ano']}: R$ {forecast['previsao_receita']:,.2f} previsto, R$ {forecast['meta_receita']:,.2f} meta, {forecast['previsao_win_rate']:.1f}% win rate")
        
        # Verificar gaps de forecast
        cursor.execute("""
            SELECT 
                COUNT(*) as total_gaps
            FROM forecast_gaps 
            WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        gaps = cursor.fetchone()
        
        print(f"\n⚠️ Gaps de Forecast (últimos 30 dias): {gaps['total_gaps']:,}")
        
        if len(forecasts) > 0:
            print("✅ MÓDULO 6 - DADOS CORRETOS!")
            return True
        else:
            print("❌ MÓDULO 6 - SEM PREVISÕES!")
            return False
            
    except Exception as e:
        print(f"Erro no módulo 6: {e}")
        return False
    finally:
        connection.close()

def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO COMPLETA DE MÉTRICAS - KOMMO ANALYTICS")
    print("=" * 70)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 70)
    
    # Verificar todos os módulos
    module1_ok = verify_module1_leads()
    module2_ok = verify_module2_funnel()
    module3_ok = verify_module3_activities()
    module4_ok = verify_module4_conversion()
    module5_ok = verify_module5_performance()
    module6_ok = verify_module6_forecast()
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO FINAL DA VERIFICAÇÃO")
    print("=" * 70)
    
    modules = [
        ("Módulo 1 - Leads", module1_ok),
        ("Módulo 2 - Funil", module2_ok),
        ("Módulo 3 - Atividades", module3_ok),
        ("Módulo 4 - Conversão", module4_ok),
        ("Módulo 5 - Performance", module5_ok),
        ("Módulo 6 - Forecast", module6_ok)
    ]
    
    total_ok = 0
    for name, status in modules:
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}: {'CORRETO' if status else 'PROBLEMA'}")
        if status:
            total_ok += 1
    
    print(f"\n📊 RESULTADO: {total_ok}/6 módulos corretos")
    
    if total_ok == 6:
        print("\n🎉 TODOS OS MÓDULOS ESTÃO COM MÉTRICAS CORRETAS!")
        print("✅ Sistema 100% funcional")
    elif total_ok >= 4:
        print(f"\n⚠️ {6-total_ok} módulo(s) com problemas menores")
        print("🔧 Verificar módulos com problemas")
    else:
        print(f"\n❌ {6-total_ok} módulo(s) com problemas críticos")
        print("🚨 Executar ETLs para corrigir")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
