import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

def get_db_connection():
    """Conecta ao banco de dados"""
    try:
        # Tentar usar secrets do Streamlit primeiro
        connection = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            autocommit=True,
            charset='utf8mb4'
        )
    except:
        # Fallback para variáveis de ambiente
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', '172.17.0.1'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'kommo_analytics'),
            password=os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            database=os.getenv('DB_NAME', 'kommo_analytics'),
            autocommit=True,
            charset='utf8mb4'
        )
    
    return connection

def render_modulo6_forecast_mensal():
    """Renderiza o Módulo 6 - Forecast Mensal"""
    
    st.markdown("## 6. Previsibilidade (Forecast)")
    st.markdown("**Para saber se a meta será batida:** Forecast de receita (previsto vs. realizado)")
    st.markdown("**💡 Importância:** antecipa gargalos antes de fechar o mês.")
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Buscar dados de forecast mensal
    forecast_query = """
    SELECT 
        data_previsao,
        receita_prevista,
        dia_semana,
        tipo,
        created_date
    FROM revenue_forecast 
    WHERE tipo = 'monthly_forecast'
    AND created_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    ORDER BY data_previsao ASC
    """
    
    cursor.execute(forecast_query)
    forecast_data = cursor.fetchall()
    
    if not forecast_data:
        st.warning("⚠️ Nenhum dado de forecast encontrado. Execute o ETL do Módulo 6 para gerar os dados.")
        cursor.close()
        connection.close()
        return
    
    # Converter para DataFrame
    df_forecast = pd.DataFrame(forecast_data, columns=[
        'data_previsao', 'receita_prevista', 'dia_semana', 'tipo', 'created_date'
    ])
    
    # Buscar dados reais dos últimos 6 meses para comparação
    real_data_query = """
    SELECT 
        DATE_FORMAT(created_date, '%Y-%m-01') as mes,
        SUM(CASE WHEN status_name = 'Venda ganha' THEN sale_price ELSE 0 END) as receita_real,
        COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) as vendas_fechadas,
        COUNT(*) as total_leads
    FROM sales_metrics 
    WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
    GROUP BY DATE_FORMAT(created_date, '%Y-%m-01')
    ORDER BY mes ASC
    """
    
    cursor.execute(real_data_query)
    real_data = cursor.fetchall()
    
    df_real = pd.DataFrame(real_data, columns=['mes', 'receita_real', 'vendas_fechadas', 'total_leads'])
    df_real['mes'] = pd.to_datetime(df_real['mes'])
    
    # Calcular métricas principais
    receita_prevista_total = df_forecast['receita_prevista'].sum()
    receita_real_ultimos_3_meses = df_real['receita_real'].tail(3).sum()
    
    # Calcular gap CORRETO: comparar mês atual (Setembro) com previsão do mês atual
    # Buscar receita real de Setembro (mês atual)
    hoje = datetime.now()
    mes_atual = hoje.strftime('%Y-%m')
    
    # Buscar receita prevista para o mês atual (Setembro)
    # Primeiro tentar buscar do tipo 'summary_metrics' (dados do mês atual)
    cursor.execute('''
        SELECT receita_prevista 
        FROM revenue_forecast 
        WHERE tipo = 'summary_metrics' 
        AND DATE_FORMAT(data_previsao, '%Y-%m') = %s
    ''', (mes_atual,))
    resultado_summary = cursor.fetchone()
    
    if resultado_summary:
        receita_prevista_setembro = resultado_summary[0]
    else:
        # Se não encontrar, usar o primeiro mês do forecast mensal
        df_forecast['data_previsao'] = pd.to_datetime(df_forecast['data_previsao'])
        receita_prevista_setembro = df_forecast['receita_prevista'].iloc[0] if not df_forecast.empty else 0
    
    # Buscar receita real de Setembro
    receita_real_setembro = df_real[df_real['mes'].dt.strftime('%Y-%m') == mes_atual]['receita_real'].sum()
    
    # Calcular gap do mês atual
    gap_receita = receita_real_setembro - receita_prevista_setembro
    
    # Calcular win rate
    total_vendas = df_real['vendas_fechadas'].tail(3).sum()
    total_leads = df_real['total_leads'].tail(3).sum()
    win_rate = (total_vendas / total_leads * 100) if total_leads > 0 else 0
    
    # Exibir métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Receita Prevista (Setembro)",
            value=f"R$ {receita_prevista_setembro:,.2f}",
            delta=f"R$ {gap_receita:,.2f}" if gap_receita != 0 else None
        )
    
    with col2:
        st.metric(
            label="📊 Receita Realizada (Setembro)",
            value=f"R$ {receita_real_setembro:,.2f}",
            delta=f"R$ {gap_receita:,.2f}" if gap_receita != 0 else None
        )
    
    with col3:
        st.metric(
            label="🎯 Vendas Fechadas",
            value=f"{total_vendas:,}",
            delta=f"{total_leads:,} leads"
        )
    
    with col4:
        st.metric(
            label="📈 Win Rate",
            value=f"{win_rate:.1f}%",
            delta="Taxa de conversão"
        )
    
    # Gráfico de Forecast vs Realizado
    st.markdown("### 📊 Previsto vs Realizado")
    
    # Preparar dados para o gráfico
    df_forecast['data_previsao'] = pd.to_datetime(df_forecast['data_previsao'])
    df_forecast['tipo_grafico'] = 'Previsto'
    
    df_real['tipo_grafico'] = 'Realizado'
    df_real_plot = df_real.rename(columns={'mes': 'data_previsao', 'receita_real': 'receita_prevista'})
    
    # Combinar dados
    df_combined = pd.concat([
        df_forecast[['data_previsao', 'receita_prevista', 'tipo_grafico']],
        df_real_plot[['data_previsao', 'receita_prevista', 'tipo_grafico']]
    ])
    
    # Criar gráfico
    fig = px.bar(
        df_combined, 
        x='data_previsao', 
        y='receita_prevista',
        color='tipo_grafico',
        title="Receita: Previsto vs Realizado",
        labels={'receita_prevista': 'Receita (R$)', 'data_previsao': 'Mês'},
        color_discrete_map={'Previsto': '#1f77b4', 'Realizado': '#ff7f0e'}
    )
    
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Receita (R$)",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Análise de Gaps
    st.markdown("### ⚠️ Análise de Gaps")
    
    if gap_receita > 0:
        st.success(f"✅ **Superando Meta**: R$ {gap_receita:,.2f} acima do previsto para Setembro")
    elif gap_receita < 0:
        st.error(f"🚨 **Gap de Receita**: R$ {abs(gap_receita):,.2f} abaixo do previsto para Setembro")
    else:
        st.info("📊 **No Target**: Receita alinhada com previsão para Setembro")
    
    # Informações adicionais
    st.markdown(f"**📅 Período**: Setembro 2025 (17 dias de {hoje.day} dias)")
    st.markdown(f"**📊 Progresso do Mês**: {(hoje.day/30)*100:.1f}% do mês concluído")
    
    # Calcular projeção para o mês completo
    if hoje.day > 0:
        receita_projetada_mes = (receita_real_setembro / hoje.day) * 30
        st.markdown(f"**🎯 Projeção para o Mês**: R$ {receita_projetada_mes:,.2f}")
        
        gap_projetado = receita_projetada_mes - receita_prevista_setembro
        if gap_projetado > 0:
            st.success(f"**📈 Projeção Positiva**: R$ {gap_projetado:,.2f} acima da meta se mantiver o ritmo")
        else:
            st.warning(f"**⚠️ Projeção Negativa**: R$ {abs(gap_projetado):,.2f} abaixo da meta se mantiver o ritmo")
    
    # Tabela detalhada de forecast
    st.markdown("### 📋 Forecast Detalhado por Mês")
    
    df_forecast_display = df_forecast.copy()
    df_forecast_display['mes_ano'] = df_forecast_display['data_previsao'].dt.strftime('%B %Y')
    df_forecast_display['receita_formatada'] = df_forecast_display['receita_prevista'].apply(lambda x: f"R$ {x:,.2f}")
    
    st.dataframe(
        df_forecast_display[['mes_ano', 'receita_formatada']].rename(columns={
            'mes_ano': 'Mês/Ano',
            'receita_formatada': 'Receita Prevista'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    
    cursor.close()
    connection.close()
