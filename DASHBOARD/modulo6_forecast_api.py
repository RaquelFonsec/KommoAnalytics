import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Criar conexão com banco de dados"""
    try:
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', '172.17.0.1'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'kommo_analytics'),
            password=os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            database=os.getenv('DB_NAME', 'kommo_analytics')
        )
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None

def run_query(query):
    """Executar query no banco de dados"""
    try:
        conn = get_db_connection()
        if conn:
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return pd.DataFrame()

def render_modulo6_forecast(selected_date):
    """Renderizar Módulo 6 - Forecast com dados da API"""
    
    st.header("🔮 Módulo 6: Previsibilidade (Forecast)")
    st.markdown("**Forecast de receita (previsto vs. realizado) para antecipar gargalos antes de fechar o mês**")
    
    # Informar sobre os dados disponíveis
    st.info("ℹ️ **Nota:** Os dados de forecast são gerados em tempo real pela API do Kommo com base em 90 dias de dados históricos.")
    
    # Buscar dados de forecast da API
    forecast_df = pd.DataFrame()
    try:
        forecast_query = """
        SELECT 
            tipo,
            data_previsao,
            receita_prevista,
            dia_semana,
            created_date
        FROM revenue_forecast 
        WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ORDER BY created_date DESC, tipo
        """
        forecast_df = run_query(forecast_query)
        
        if forecast_df.empty:
            st.warning("⚠️ Nenhum dado de forecast encontrado para hoje. Execute o ETL do Módulo 6 para gerar os dados.")
            
    except Exception as e:
        st.error(f"❌ Erro ao buscar dados de forecast: {e}")
        forecast_df = pd.DataFrame()
    
    # Buscar resultados reais dos últimos 3 meses (para comparação realista)
    results_df = pd.DataFrame()
    try:
        results_query = f"""
        SELECT 
            'Últimos 3 meses' as mes_ano,
            NOW() as data_atualizacao,
            COALESCE(SUM(CASE WHEN sm.status_name = 'Venda ganha' THEN sm.sale_price ELSE 0 END), 0) as receita_realizada,
            COUNT(DISTINCT l.lead_id) as leads_realizados,
            COUNT(DISTINCT CASE WHEN sm.status_name = 'Venda ganha' THEN sm.lead_id END) as vendas_fechadas,
            COUNT(DISTINCT CASE WHEN sm.status_name = 'Venda perdida' THEN sm.lead_id END) as vendas_perdidas,
            COALESCE(ROUND(COUNT(DISTINCT CASE WHEN sm.status_name = 'Venda ganha' THEN sm.lead_id END) / 
                  NULLIF(COUNT(DISTINCT CASE WHEN sm.status_name IN ('Venda ganha', 'Venda perdida') THEN sm.lead_id END), 0) * 100, 1), 0) as win_rate_real,
            COALESCE(AVG(CASE WHEN sm.status_name = 'Venda ganha' AND sm.sale_price > 0 THEN sm.sale_price END), 0) as ticket_medio_real,
            90 as dias_passados,
            0 as dias_restantes
        FROM leads_metrics l
        LEFT JOIN sales_metrics sm ON l.lead_id = sm.lead_id
        WHERE l.created_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
        """
        results_df = run_query(results_query)
    except Exception as e:
        st.error(f"❌ Erro ao buscar resultados: {e}")
        results_df = pd.DataFrame()
    
    # Métricas principais do Forecast - PREVISTO vs REALIZADO
    if not forecast_df.empty and not results_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        # Extrair dados de forecast
        monthly_forecast = forecast_df[forecast_df['tipo'] == 'monthly_forecast']
        weekly_forecast = forecast_df[forecast_df['tipo'] == 'weekly_forecast']
        
        # Dados reais
        receita_real = results_df.iloc[0]['receita_realizada'] if not results_df.empty else 0
        leads_real = results_df.iloc[0]['leads_realizados'] if not results_df.empty else 0
        vendas_real = results_df.iloc[0]['vendas_fechadas'] if not results_df.empty else 0
        win_rate_real = results_df.iloc[0]['win_rate_real'] if not results_df.empty else 0
        dias_passados = results_df.iloc[0]['dias_passados'] if not results_df.empty else 0
        dias_restantes = results_df.iloc[0]['dias_restantes'] if not results_df.empty else 0
        
        # Dados previstos
        receita_prevista_mensal = monthly_forecast.iloc[0]['receita_prevista'] if not monthly_forecast.empty else 0
        receita_prevista_semanal = weekly_forecast.iloc[0]['receita_prevista'] if not weekly_forecast.empty else 0
        
        # Calcular meta (assumindo meta de R$ 100.000)
        meta_receita = 100000
        
        with col1:
            st.metric(
                label="💰 Receita Realizada",
                value=f"R$ {receita_real:,.2f}",
                delta=f"vs. R$ {receita_prevista_mensal:,.2f} previsto"
            )
        
        with col2:
            # Calcular gap
            gap_receita = receita_prevista_mensal - receita_real
            gap_percentual = (gap_receita / receita_prevista_mensal * 100) if receita_prevista_mensal > 0 else 0
            
            st.metric(
                label="📊 Gap Receita",
                value=f"R$ {gap_receita:,.2f}",
                delta=f"{gap_percentual:+.1f}% vs previsto"
            )
        
        with col3:
            st.metric(
                label="🎯 Vendas Fechadas",
                value=f"{vendas_real:,}",
                delta=f"Win Rate: {win_rate_real:.1f}%"
            )
        
        with col4:
            # Calcular probabilidade de atingir meta
            probabilidade_meta = min(100, (receita_prevista_mensal / meta_receita) * 100)
            
            st.metric(
                label="🔮 Probabilidade Meta",
                value=f"{probabilidade_meta:.1f}%",
                delta=f"Meta: R$ {meta_receita:,.0f}"
            )
    
    # Gráfico de Forecast vs Realizado
    if not forecast_df.empty and not results_df.empty:
        st.subheader("📈 Forecast vs Realizado")
        
        # Preparar dados para o gráfico
        chart_data = []
        
        # Adicionar dados mensais
        if not monthly_forecast.empty:
            chart_data.append({
                'Período': 'Mensal',
                'Tipo': 'Previsto',
                'Receita': monthly_forecast.iloc[0]['receita_prevista'],
                'Data': monthly_forecast.iloc[0]['data_previsao']
            })
        
        # Adicionar dados semanais
        if not weekly_forecast.empty:
            chart_data.append({
                'Período': '4 Semanas',
                'Tipo': 'Previsto',
                'Receita': weekly_forecast.iloc[0]['receita_prevista'],
                'Data': weekly_forecast.iloc[0]['data_previsao']
            })
        
        # Adicionar dados reais
        if not results_df.empty:
            chart_data.append({
                'Período': 'Realizado',
                'Tipo': 'Realizado',
                'Receita': receita_real,
                'Data': selected_date
            })
        
        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            
            fig = px.bar(
                df_chart, 
                x='Período', 
                y='Receita',
                color='Tipo',
                title="Forecast vs Realizado",
                color_discrete_map={'Previsto': '#FFA500', 'Realizado': '#00FF00'},
                text='Receita'
            )
            
            # Formatar valores no gráfico
            fig.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
            
            fig.update_layout(
                yaxis_title="Receita (R$)",
                xaxis_title="Período",
                showlegend=True,
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Análise de Gaps
    if not forecast_df.empty and not results_df.empty:
        st.subheader("🎯 Análise de Gaps")
        
        # Calcular gaps
        gap_receita = receita_real - receita_prevista_mensal
        gap_percentual = (gap_receita / receita_prevista_mensal * 100) if receita_prevista_mensal > 0 else 0
        
        st.markdown("**📊 Status Atual:**")
        if gap_receita > 0:
            st.success(f"✅ **Superando Meta:** R$ {gap_receita:,.2f} ({gap_percentual:.1f}%)")
            st.success("🎉 **Status:** Meta será atingida")
        else:
            st.error(f"❌ **Gap de Receita:** R$ {gap_receita:,.2f} ({gap_percentual:.1f}%)")
            st.warning("⚠️ **Risco:** Meta pode não ser atingida")
    
    # Botão de atualização removido - ETL será executado via cron jobs
    
    return True