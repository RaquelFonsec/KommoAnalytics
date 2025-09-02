# Dashboard Streamlit - Kommo Analytics (6 MÓDULOS ETL)
import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(page_title="Kommo Analytics", layout="wide")

# Configuração do banco
def init_connection():
    try:
        connection = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            port=int(st.secrets["DB_PORT"]),
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            autocommit=True,
            charset='utf8mb4'
        )
        return connection
    except Exception as e:
        st.error(f"Erro na conexão com banco: {e}")
        return None

def run_query(query, params=None):
    try:
        conn = init_connection()
        if conn is None:
            return pd.DataFrame()
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return pd.DataFrame()

# Header
st.title(" Kommo Analytics Dashboard -")

# Sidebar
st.sidebar.title(" Filtros")
periodo = st.sidebar.selectbox("Período:", ["7 dias", "15 dias", "30 dias"], index=2)  # 30 dias por padrão
dias = int(periodo.split()[0])
data_inicio = datetime.now() - timedelta(days=dias)

# Data para queries
selected_date = datetime.now().strftime('%Y-%m-%d')

# SEÇÃO 1: RESUMO EXECUTIVO
st.header(" Resumo Executivo")

col1, col2, col3, col4 = st.columns(4)

# KPIs principais
kpis_query = f"""
SELECT 
    COUNT(DISTINCT l.lead_id) as total_leads,
    COUNT(DISTINCT CASE WHEN fh.status_name = 'Venda ganha' THEN fh.lead_id END) as vendas,
    COUNT(DISTINCT CASE WHEN fh.status_name = 'Venda perdida' THEN fh.lead_id END) as vendas_perdidas,
    COALESCE(AVG(l.response_time_hours), 0) as tempo_resposta_medio,
    COALESCE(SUM(l.lead_cost), 0) as custo_total
FROM leads_metrics l
LEFT JOIN funnel_history fh ON l.lead_id = fh.lead_id AND fh.pipeline_id = 11146887
WHERE l.created_date >= '{data_inicio.date()}'
"""

kpis_df = run_query(kpis_query)

if not kpis_df.empty:
    kpi = kpis_df.iloc[0]
    
    with col1:
        st.metric("📈 Total Leads", f"{kpi['total_leads']:,}")
    with col2:
        win_rate = (kpi['vendas'] / kpi['total_leads'] * 100) if kpi['total_leads'] > 0 else 0
        st.metric("🎯 Vendas Ganhas", f"{kpi['vendas']:,}", f"{win_rate:.1f}% win rate")
    with col3:
        loss_rate = (kpi['vendas_perdidas'] / kpi['total_leads'] * 100) if kpi['total_leads'] > 0 else 0
        st.metric(" Vendas Perdidas", f"{kpi['vendas_perdidas']:,}", f"{loss_rate:.1f}% loss rate")
    with col4:
        st.metric("💰 Custo Total", f"R$ {kpi['custo_total']:,.0f}")

# SEÇÃO 2: MÓDULO 1 - ENTRADA E ORIGEM DE LEADS
st.header("🎯 Módulo 1: Entrada e Origem de Leads")
st.markdown("**Para saber de onde vêm os resultados e priorizar canais que convertem mais**")

# Leads por canal - Query primeiro
leads_canal_query = f"""
SELECT 
    COALESCE(primary_source, 'Não Classificado') as canal,
    COUNT(*) as total_leads,
    AVG(response_time_hours) as tempo_resposta_medio,
    SUM(lead_cost) as custo_total,
    AVG(lead_cost) as custo_medio
FROM leads_metrics 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY primary_source
ORDER BY total_leads DESC
"""

leads_canal_df = run_query(leads_canal_query)
    
# Métricas principais do Módulo 1
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_leads_modulo1 = leads_canal_df['total_leads'].sum() if not leads_canal_df.empty else 0
    st.metric("📊 Total Leads Recebidos", f"{total_leads_modulo1:,}")

with col2:
    tempo_medio_resposta = leads_canal_df['tempo_resposta_medio'].mean() if not leads_canal_df.empty else 0
    st.metric("⏱️ Tempo Médio Resposta", f"{tempo_medio_resposta:.1f}h")

with col3:
    custo_total_modulo1 = leads_canal_df['custo_total'].sum() if not leads_canal_df.empty else 0
    st.metric("💰 Custo Total", f"R$ {custo_total_modulo1:,.0f}")

with col4:
    custo_por_lead = custo_total_modulo1 / total_leads_modulo1 if total_leads_modulo1 > 0 else 0
    st.metric("🎯 Custo por Lead", f"R$ {custo_por_lead:.2f}")

col1, col2 = st.columns(2)

with col1:
    if not leads_canal_df.empty:
        fig_leads = px.pie(leads_canal_df, values='total_leads', names='canal', title="Leads por Canal")
        st.plotly_chart(fig_leads, use_container_width=True)

with col2:
    # Custo por canal
    if not leads_canal_df.empty:
        # Filtrar apenas canais com custo
        canais_com_custo = leads_canal_df[leads_canal_df['custo_total'] > 0]
        if not canais_com_custo.empty:
            fig_custo = px.bar(canais_com_custo, x='canal', y='custo_medio', title="Custo Médio por Lead por Canal")
            fig_custo.update_xaxes(tickangle=45)
            st.plotly_chart(fig_custo, use_container_width=True)
        else:
            st.info("Nenhum canal com custo registrado")

# Análise detalhada por canal
st.subheader("📊 Análise Detalhada por Canal")

col1, col2 = st.columns(2)

with col1:
    # Tempo de resposta por canal
    if not leads_canal_df.empty:
        # Filtrar apenas canais com tempo de resposta
        canais_com_tempo = leads_canal_df[leads_canal_df['tempo_resposta_medio'].notna()]
        if not canais_com_tempo.empty:
            fig_tempo = px.bar(canais_com_tempo, x='canal', y='tempo_resposta_medio', title="Tempo de Resposta por Canal")
            fig_tempo.update_xaxes(tickangle=45)
            st.plotly_chart(fig_tempo, use_container_width=True)
        else:
            st.info("Nenhum canal com tempo de resposta registrado")

with col2:
    # Eficiência de custo (leads por real investido)
    if not leads_canal_df.empty:
        canais_com_custo = leads_canal_df[leads_canal_df['custo_total'] > 0].copy()
        if not canais_com_custo.empty:
            canais_com_custo['eficiencia'] = canais_com_custo['total_leads'] / canais_com_custo['custo_total']
            fig_eficiencia = px.bar(canais_com_custo, x='canal', y='eficiencia', title="Eficiência: Leads por R$ Investido")
            fig_eficiencia.update_xaxes(tickangle=45)
            st.plotly_chart(fig_eficiencia, use_container_width=True)
        else:
            st.info("Nenhum canal com custo para análise de eficiência")

# Tabela detalhada de canais
st.subheader("📋 Detalhamento por Canal")

if not leads_canal_df.empty:
    # Formatar dados para exibição
    canais_display = leads_canal_df.copy()
    canais_display['tempo_resposta_medio'] = canais_display['tempo_resposta_medio'].round(1)
    canais_display['custo_medio'] = canais_display['custo_medio'].round(2)
    canais_display['pct_total'] = (canais_display['total_leads'] / canais_display['total_leads'].sum() * 100).round(1)
    
    # Renomear colunas
    canais_display = canais_display.rename(columns={
        'canal': 'Canal',
        'total_leads': 'Total Leads',
        'tempo_resposta_medio': 'Tempo Resposta (h)',
        'custo_total': 'Custo Total (R$)',
        'custo_medio': 'Custo Médio (R$)',
        'pct_total': '% do Total'
    })
    
    st.dataframe(canais_display, use_container_width=True)
else:
    st.info("Nenhum dado de canal encontrado.")

# Análise de performance
st.subheader("🎯 Análise de Performance dos Canais")

# Buscar dados reais de performance
performance_query = f"""
SELECT 
    primary_source as canal,
    COUNT(*) as total_leads,
    AVG(response_time_hours) as tempo_medio,
    SUM(lead_cost) as custo_total,
    AVG(lead_cost) as custo_medio
FROM leads_metrics 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY primary_source
ORDER BY total_leads DESC
"""

performance_df = run_query(performance_query)

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Maior volume
    if not performance_df.empty:
        maior_volume = performance_df.iloc[0]
        st.metric("📈 Maior Volume", f"{maior_volume['canal'][:15]}", f"{maior_volume['total_leads']:,} leads")
    else:
        st.metric("📈 Maior Volume", "N/A")

with col2:
    # Melhor tempo de resposta
    if not performance_df.empty:
        canais_com_tempo = performance_df[performance_df['tempo_medio'].notna()]
        if not canais_com_tempo.empty:
            melhor_tempo = canais_com_tempo.loc[canais_com_tempo['tempo_medio'].idxmin()]
            st.metric("⚡ Melhor Tempo", f"{melhor_tempo['canal'][:15]}", f"{melhor_tempo['tempo_medio']:.1f}h")
        else:
            st.metric("⚡ Melhor Tempo", "N/A")
    else:
        st.metric("⚡ Melhor Tempo", "N/A")

with col3:
    # Melhor custo
    if not performance_df.empty:
        canais_com_custo = performance_df[performance_df['custo_total'] > 0]
        if not canais_com_custo.empty:
            melhor_custo = canais_com_custo.loc[canais_com_custo['custo_medio'].idxmin()]
            st.metric("💰 Melhor Custo", f"{melhor_custo['canal'][:15]}", f"R$ {melhor_custo['custo_medio']:.2f}")
        else:
            st.metric("💰 Melhor Custo", "N/A")
    else:
        st.metric("💰 Melhor Custo", "N/A")

with col4:
    # Total de canais únicos
    total_canais = len(performance_df) if not performance_df.empty else 0
    st.metric("🎯 Canais Únicos", f"{total_canais}")

# Adicionar análise de vendas por canal
st.subheader("📊 Vendas por Canal")

vendas_canal_query = f"""
SELECT 
    lm.primary_source as canal,
    COUNT(DISTINCT fh.lead_id) as vendas_ganhas,
    COUNT(DISTINCT CASE WHEN fh.status_name = 'Venda perdida' THEN fh.lead_id END) as vendas_perdidas
FROM funnel_history fh
JOIN leads_metrics lm ON fh.lead_id = lm.lead_id
WHERE fh.entry_date >= '{data_inicio.date()}'
AND fh.status_name IN ('Venda ganha', 'Venda perdida')
GROUP BY lm.primary_source
ORDER BY vendas_ganhas DESC
"""

vendas_canal_df = run_query(vendas_canal_query)

if not vendas_canal_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de vendas ganhas por canal
        fig_vendas = px.bar(
            vendas_canal_df, 
            x='canal', 
            y='vendas_ganhas',
            title="Vendas Ganhas por Canal"
        )
        fig_vendas.update_xaxes(tickangle=45)
        st.plotly_chart(fig_vendas, use_container_width=True)
    
    with col2:
        # Taxa de conversão por canal
        vendas_canal_df['taxa_conversao'] = (
            vendas_canal_df['vendas_ganhas'] / 
            (vendas_canal_df['vendas_ganhas'] + vendas_canal_df['vendas_perdidas']) * 100
        )
        
        fig_taxa = px.bar(
            vendas_canal_df, 
            x='canal', 
            y='taxa_conversao',
            title="Taxa de Conversão por Canal (%)"
        )
        fig_taxa.update_xaxes(tickangle=45)
        st.plotly_chart(fig_taxa, use_container_width=True)

# Adicionar análise de UTMs
st.subheader("🔗 Análise de UTMs")

utms_query = f"""
SELECT 
    utm_source,
    utm_medium,
    utm_campaign,
    COUNT(*) as total_leads
FROM leads_metrics 
WHERE created_date >= '{data_inicio.date()}'
AND utm_source IS NOT NULL
GROUP BY utm_source, utm_medium, utm_campaign
ORDER BY total_leads DESC
LIMIT 10
"""

utms_df = run_query(utms_query)

if not utms_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Top UTMs por source
        utm_source_df = utms_df.groupby('utm_source')['total_leads'].sum().reset_index().sort_values('total_leads', ascending=False)
        fig_utm_source = px.pie(
            utm_source_df, 
            values='total_leads', 
            names='utm_source',
            title="Leads por UTM Source"
        )
        st.plotly_chart(fig_utm_source, use_container_width=True)
    
    with col2:
        # Top campanhas
        utm_campaign_df = utms_df.groupby('utm_campaign')['total_leads'].sum().reset_index().sort_values('total_leads', ascending=False).head(5)
        fig_utm_campaign = px.bar(
            utm_campaign_df, 
            x='utm_campaign', 
            y='total_leads',
            title="Top 5 Campanhas"
        )
        fig_utm_campaign.update_xaxes(tickangle=45)
        st.plotly_chart(fig_utm_campaign, use_container_width=True)
    
    # Tabela detalhada de UTMs
    st.subheader("📋 Detalhamento de UTMs")
    utms_display = utms_df.copy()
    utms_display['pct_total'] = (utms_display['total_leads'] / utms_display['total_leads'].sum() * 100).round(1)
    utms_display = utms_display.rename(columns={
        'utm_source': 'UTM Source',
        'utm_medium': 'UTM Medium', 
        'utm_campaign': 'UTM Campaign',
        'total_leads': 'Total Leads',
        'pct_total': '% do Total'
    })
    st.dataframe(utms_display, use_container_width=True)
else:
    st.info("Nenhum dado de UTM encontrado.")

# SEÇÃO 3: MÓDULO 2 - QUALIFICAÇÃO E AVANÇO NO FUNIL
st.header("🔄 Módulo 2: Qualificação e Avanço no Funil")
st.markdown("**Para medir se o funil está saudável**")

col1, col2 = st.columns(2)

with col1:
    # Funil de conversão
    funil_query = f"""
    SELECT 
        COALESCE(fh.status_name, 'Desconhecido') as etapa,
        COUNT(DISTINCT fh.lead_id) as leads,
        AVG(fh.time_in_status_hours) as tempo_medio
    FROM funnel_history fh
    WHERE fh.entry_date >= '{data_inicio.date()}'
    AND fh.pipeline_id = 11146887
    GROUP BY fh.status_name, fh.status_sort
    ORDER BY fh.status_sort
    """
    
    funil_df = run_query(funil_query)
    
    if not funil_df.empty:
        fig_funil = go.Figure(go.Funnel(
            y=funil_df['etapa'],
            x=funil_df['leads'],
            textinfo="value+percent initial"
        ))
        fig_funil.update_layout(title="Funil de Conversão")
        st.plotly_chart(fig_funil, use_container_width=True)

with col2:
    # Taxa de conversão por etapa
    if not funil_df.empty:
        total_leads_funil = funil_df['leads'].sum()
        funil_df['taxa_conversao'] = (funil_df['leads'] / total_leads_funil * 100)
        
        fig_conversao = px.bar(funil_df, x='etapa', y='taxa_conversao', title="Taxa de Conversão por Etapa")
        fig_conversao.update_xaxes(tickangle=45)
        st.plotly_chart(fig_conversao, use_container_width=True)

# Métricas do Módulo 2
col1, col2, col3, col4 = st.columns(4)

with col1:
    etapas_ativas = len(funil_df) if not funil_df.empty else 0
    st.metric("🔄 Etapas Ativas", f"{etapas_ativas}")

with col2:
    tempo_medio_etapa = funil_df['tempo_medio'].mean() if not funil_df.empty else 0
    st.metric("⏱️ Tempo Médio por Etapa", f"{tempo_medio_etapa:.1f}h")

with col3:
    taxa_avanco = (funil_df['leads'].min() / funil_df['leads'].max() * 100) if not funil_df.empty and len(funil_df) > 1 else 0
    st.metric("📈 Taxa de Avanço", f"{taxa_avanco:.1f}%")

with col4:
    perdas = funil_df['leads'].max() - funil_df['leads'].min() if not funil_df.empty and len(funil_df) > 1 else 0
    st.metric("📉 Perdas no Funil", f"{perdas:,}")

# SEÇÃO 2.5: FUNIL PRINCIPAL - DETALHADO
st.header("🎯 Funil Principal - Detalhado")
st.markdown("**Análise específica do Funil de Vendas Principal (ID: 11146887)**")

col1, col2 = st.columns(2)

with col1:
    # Status do funil principal
    status_principal_query = f"""
SELECT 
        status_name,
        COUNT(DISTINCT lead_id) as leads_unicos,
        AVG(time_in_status_hours) as tempo_medio_horas,
        COUNT(*) as total_movimentacoes
    FROM funnel_history 
    WHERE pipeline_id = 11146887
    AND entry_date >= '{data_inicio.date()}'
    GROUP BY status_name, status_sort
    ORDER BY status_sort
    """
    
    status_principal_df = run_query(status_principal_query)
    
    if not status_principal_df.empty:
        fig_status = px.bar(
            status_principal_df, 
            x='status_name', 
            y='leads_unicos',
            title="Leads por Status - Funil Principal"
        )
        fig_status.update_xaxes(tickangle=45)
        st.plotly_chart(fig_status, use_container_width=True)

with col2:
    # Taxa de conversão por status
    if not status_principal_df.empty:
        total_leads_principal = status_principal_df['leads_unicos'].sum()
        status_principal_df['taxa_conversao'] = (status_principal_df['leads_unicos'] / total_leads_principal * 100)
        
        fig_taxa = px.bar(
            status_principal_df, 
            x='status_name', 
            y='taxa_conversao',
            title="Taxa de Conversão por Status (%)"
        )
        fig_taxa.update_xaxes(tickangle=45)
        st.plotly_chart(fig_taxa, use_container_width=True)

# Métricas do Funil Principal
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_leads_principal = status_principal_df['leads_unicos'].sum() if not status_principal_df.empty else 0
    st.metric("📊 Total Leads Principal", f"{total_leads_principal:,}")

with col2:
    vendas_principal = status_principal_df[status_principal_df['status_name'] == 'Venda ganha']['leads_unicos'].iloc[0] if not status_principal_df.empty and 'Venda ganha' in status_principal_df['status_name'].values else 0
    st.metric("✅ Vendas Ganhas", f"{vendas_principal:,}")

with col3:
    tempo_medio_etapa = status_principal_df['tempo_medio_horas'].mean() if not status_principal_df.empty else 0
    st.metric("⏱️ Tempo Médio Etapa", f"{tempo_medio_etapa:.1f}h")

with col4:
    vendas_perdidas_principal = status_principal_df[status_principal_df['status_name'] == 'Venda perdida']['leads_unicos'].iloc[0] if not status_principal_df.empty and 'Venda perdida' in status_principal_df['status_name'].values else 0
    st.metric("❌ Vendas Perdidas", f"{vendas_perdidas_principal:,}")

# SEÇÃO 3.5: ANÁLISE DE VENDAS PERDIDAS
st.header("❌ Análise de Vendas Perdidas")
st.markdown("**Detalhamento das vendas perdidas no funil principal**")

col1, col2 = st.columns(2)

with col1:
    # Vendas perdidas por tempo no funil
    perdas_tempo_query = f"""
    SELECT 
        CASE 
            WHEN time_in_status_hours <= 24 THEN '0-24h'
            WHEN time_in_status_hours <= 72 THEN '1-3 dias'
            WHEN time_in_status_hours <= 168 THEN '3-7 dias'
            WHEN time_in_status_hours <= 720 THEN '1-4 semanas'
            ELSE 'Mais de 4 semanas'
        END as tempo_categoria,
        COUNT(DISTINCT lead_id) as leads_perdidos,
        AVG(time_in_status_hours) as tempo_medio
    FROM funnel_history 
    WHERE pipeline_id = 11146887
    AND status_name = 'Venda perdida'
    AND entry_date >= '{data_inicio.date()}'
    GROUP BY tempo_categoria
    ORDER BY tempo_medio
    """
    
    perdas_tempo_df = run_query(perdas_tempo_query)
    
    if not perdas_tempo_df.empty:
        fig_perdas_tempo = px.bar(
            perdas_tempo_df, 
            x='tempo_categoria', 
            y='leads_perdidos',
            title="Vendas Perdidas por Tempo no Funil"
        )
        st.plotly_chart(fig_perdas_tempo, use_container_width=True)

with col2:
    # Comparação ganhas vs perdidas
    comparacao_query = f"""
    SELECT 
        status_name,
        COUNT(DISTINCT lead_id) as leads,
        AVG(time_in_status_hours) as tempo_medio
    FROM funnel_history 
    WHERE pipeline_id = 11146887
    AND status_name IN ('Venda ganha', 'Venda perdida')
    AND entry_date >= '{data_inicio.date()}'
    GROUP BY status_name
    """
    
    comparacao_df = run_query(comparacao_query)
    
    if not comparacao_df.empty:
        fig_comparacao = px.pie(
            comparacao_df, 
            values='leads', 
            names='status_name',
            title="Ganhas vs Perdidas"
        )
        st.plotly_chart(fig_comparacao, use_container_width=True)

# Métricas de vendas perdidas
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_perdidas = comparacao_df[comparacao_df['status_name'] == 'Venda perdida']['leads'].iloc[0] if not comparacao_df.empty and 'Venda perdida' in comparacao_df['status_name'].values else 0
    st.metric("❌ Total Perdidas", f"{total_perdidas:,}")

with col2:
    total_ganhas = comparacao_df[comparacao_df['status_name'] == 'Venda ganha']['leads'].iloc[0] if not comparacao_df.empty and 'Venda ganha' in comparacao_df['status_name'].values else 0
    st.metric("✅ Total Ganhas", f"{total_ganhas:,}")

with col3:
    taxa_perda = (total_perdidas / (total_perdidas + total_ganhas) * 100) if (total_perdidas + total_ganhas) > 0 else 0
    st.metric("📉 Taxa de Perda", f"{taxa_perda:.1f}%")

with col4:
    tempo_medio_perdidas = comparacao_df[comparacao_df['status_name'] == 'Venda perdida']['tempo_medio'].iloc[0] if not comparacao_df.empty and 'Venda perdida' in comparacao_df['status_name'].values else 0
    st.metric("⏱️ Tempo até Perda", f"{tempo_medio_perdidas:.1f}h")

# SEÇÃO 3.6: MOTIVOS DE PERDA
st.header("🔍 Motivos de Perda")
st.markdown("**Análise detalhada dos motivos de perda no funil**")

# Buscar dados reais de motivos de perda
motivos_perda_query = f"""
SELECT 
    COALESCE(loss_reason, 'Não especificado') as motivo,
    COUNT(DISTINCT lead_id) as leads_perdidos,
    AVG(sales_cycle_days) as tempo_medio
FROM sales_metrics 
WHERE created_date >= '{data_inicio.date()}'
AND status_name = 'Venda perdida'
GROUP BY loss_reason
ORDER BY leads_perdidos DESC
"""

motivos_perda_df = run_query(motivos_perda_query)

# Calcular métricas de motivos de perda
total_perdidas_motivos = motivos_perda_df['leads_perdidos'].sum() if not motivos_perda_df.empty else 0
com_motivo = motivos_perda_df[motivos_perda_df['motivo'] != 'Não especificado']['leads_perdidos'].sum() if not motivos_perda_df.empty else 0
sem_motivo = motivos_perda_df[motivos_perda_df['motivo'] == 'Não especificado']['leads_perdidos'].iloc[0] if not motivos_perda_df.empty and 'Não especificado' in motivos_perda_df['motivo'].values else 0
pct_com_motivo = (com_motivo / total_perdidas_motivos * 100) if total_perdidas_motivos > 0 else 0
motivo_principal = motivos_perda_df['motivo'].iloc[0] if not motivos_perda_df.empty else "N/A"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📝 Com Motivo", f"{com_motivo:,}")

with col2:
    st.metric("❓ Sem Motivo", f"{sem_motivo:,}")

with col3:
    st.metric("📊 % Com Motivo", f"{pct_com_motivo:.1f}%")

with col4:
    st.metric("🎯 Motivo Principal", motivo_principal[:20])

col1, col2 = st.columns(2)

with col1:
    # Gráfico de motivos de perda
    if not motivos_perda_df.empty:
        fig_motivos = px.bar(
            motivos_perda_df, 
            x='motivo', 
            y='leads_perdidos',
            title="Vendas Perdidas por Motivo"
        )
        fig_motivos.update_xaxes(tickangle=45)
        st.plotly_chart(fig_motivos, use_container_width=True)

with col2:
    # Distribuição com/sem motivo
    distribuicao_data = {
        'categoria': ['Com Motivo', 'Sem Motivo'],
        'leads_perdidos': [com_motivo, sem_motivo]
    }
    distribuicao_df = pd.DataFrame(distribuicao_data)
    
    if not distribuicao_df.empty and distribuicao_df['leads_perdidos'].sum() > 0:
        fig_distribuicao = px.pie(
            distribuicao_df, 
            values='leads_perdidos', 
            names='categoria',
            title="Distribuição: Com vs Sem Motivo"
        )
        st.plotly_chart(fig_distribuicao, use_container_width=True)

# Tabela detalhada de motivos
st.subheader("📋 Detalhamento dos Motivos de Perda")

if not motivos_perda_df.empty:
    # Formatar dados para exibição
    motivos_display = motivos_perda_df.copy()
    motivos_display['tempo_medio'] = motivos_display['tempo_medio'].round(1)
    motivos_display['pct_total'] = (motivos_display['leads_perdidos'] / motivos_display['leads_perdidos'].sum() * 100).round(1)
    
    # Renomear colunas
    motivos_display = motivos_display.rename(columns={
        'motivo': 'Motivo',
        'leads_perdidos': 'Leads Perdidos',
        'tempo_medio': 'Tempo Médio (h)',
        'pct_total': '% do Total'
    })
    
    st.dataframe(motivos_display, use_container_width=True)
else:
    st.info("Nenhum motivo de perda encontrado nos dados.")

# Adicionar alerta sobre qualidade dos dados
if pct_com_motivo < 10:
    st.warning("🚨 **ALERTA CRÍTICO**: Apenas {:.1f}% das vendas perdidas têm motivo registrado. Implemente obrigatoriedade de motivo de perda no CRM!".format(pct_com_motivo))
elif pct_com_motivo < 50:
    st.warning("⚠️ **ATENÇÃO**: Apenas {:.1f}% das vendas perdidas têm motivo registrado. Treine a equipe para sempre registrar motivos.".format(pct_com_motivo))
else:
    st.success("✅ **BOM CONTROLE**: {:.1f}% das vendas perdidas têm motivo registrado.".format(pct_com_motivo))

# SEÇÃO 4: MÓDULO 3 - ATIVIDADES COMERCIAIS  
st.header("📞 Módulo 3: Atividades Comerciais")
st.markdown("**Para entender o esforço do time e avaliar cadência de prospecção**")

# Buscar dados reais de atividades comerciais
atividades_query = f"""
SELECT 
    activity_type,
    COUNT(*) as total_atividades,
    COUNT(DISTINCT user_id) as vendedores_unicos,
    COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) as concluidas,
    ROUND(COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao,
    COUNT(DISTINCT entity_id) as leads_contatatados
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY activity_type 
ORDER BY total_atividades DESC
"""

atividades_df = run_query(atividades_query)

# Métricas principais do Módulo 3
col1, col2, col3, col4 = st.columns(4)

if not atividades_df.empty:
    total_atividades = atividades_df['total_atividades'].sum()
    total_vendedores = atividades_df['vendedores_unicos'].max()  # Usar max para evitar soma duplicada
    taxa_conclusao_media = (atividades_df['concluidas'].sum() / atividades_df['total_atividades'].sum() * 100) if total_atividades > 0 else 0
    leads_contactados = atividades_df['leads_contatatados'].sum()
    
    with col1:
        st.metric("📊 Total Atividades", f"{total_atividades:,}")
    
    with col2:
        st.metric("👥 Vendedores Ativos", f"{total_vendedores}")
    
    with col3:
        st.metric("✅ Taxa Conclusão", f"{taxa_conclusao_media:.1f}%")
    
    with col4:
        st.metric("🎯 Leads Contactados", f"{leads_contactados:,}")

col1, col2 = st.columns(2)

with col1:
    # Gráfico de atividades por tipo
    if not atividades_df.empty:
        fig_atividades = px.bar(
            atividades_df, 
            x='activity_type', 
            y='total_atividades',
            title="Atividades por Tipo",
            labels={'activity_type': 'Tipo de Atividade', 'total_atividades': 'Total'}
        )
        fig_atividades.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_atividades, use_container_width=True)

with col2:
    # Taxa de conclusão por tipo
    if not atividades_df.empty:
        fig_conclusao = px.bar(
            atividades_df, 
            x='activity_type', 
            y='taxa_conclusao',
            title="Taxa de Conclusão por Tipo (%)",
            labels={'activity_type': 'Tipo de Atividade', 'taxa_conclusao': 'Taxa (%)'}
        )
        fig_conclusao.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_conclusao, use_container_width=True)

# Análise por vendedor
st.subheader("👥 Performance por Vendedor")

vendedores_query = f"""
SELECT 
    user_name,
    user_role,
    COUNT(*) as total_atividades,
    COUNT(CASE WHEN is_follow_up = 1 THEN 1 END) as followups,
    COUNT(CASE WHEN note_text LIKE '%ligar%' OR note_text LIKE '%contato%' OR note_text LIKE '%telefone%' OR note_text LIKE '%whatsapp%' THEN 1 END) as contatos,
    COUNT(CASE WHEN note_text LIKE '%reuniao%' OR note_text LIKE '%meeting%' OR note_text LIKE '%apresentacao%' OR note_text LIKE '%agendamento%' THEN 1 END) as reunioes,
    COUNT(CASE WHEN note_text LIKE '%email%' OR note_text LIKE '%e-mail%' OR note_text LIKE '%correio%' THEN 1 END) as emails,
    COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) as concluidas,
    ROUND(COUNT(CASE WHEN is_completed = 1 OR is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao,
    COUNT(DISTINCT entity_id) as leads_diferentes
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY user_name, user_role 
ORDER BY total_atividades DESC
LIMIT 10
"""

vendedores_df = run_query(vendedores_query)

# Buscar dados de segmentação dos follow-ups para integrar na tabela principal
followup_segmentation_query = f"""
SELECT 
    user_name,
    COUNT(*) as total_followups,
    COUNT(CASE WHEN follow_up_category = 'alta_prioridade' THEN 1 END) as alta_prioridade,
    COUNT(CASE WHEN follow_up_category = 'media_prioridade' THEN 1 END) as media_prioridade,
    COUNT(CASE WHEN follow_up_category = 'baixa_prioridade' THEN 1 END) as baixa_prioridade,
    AVG(urgency_score) as score_medio_urgencia
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}' AND is_follow_up = 1
GROUP BY user_name
"""

followup_segmentation_df = run_query(followup_segmentation_query)

# Buscar dados de taxa de resposta e follow-ups no prazo
response_metrics_query = f"""
SELECT 
    user_name,
    COUNT(CASE WHEN activity_type = 'note' AND note_text LIKE '%resposta%' OR note_text LIKE '%retorno%' THEN 1 END) as respostas_recebidas,
    COUNT(CASE WHEN activity_type = 'task' AND is_follow_up = 1 AND complete_till IS NOT NULL AND complete_till >= created_date THEN 1 END) as followups_no_prazo,
    COUNT(CASE WHEN activity_type = 'task' AND is_follow_up = 1 AND complete_till IS NOT NULL AND complete_till < created_date THEN 1 END) as followups_atrasados
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY user_name
"""

response_metrics_df = run_query(response_metrics_query)

if not vendedores_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Top vendedores por atividades
        fig_vendedores = px.bar(
            vendedores_df.head(8), 
            x='user_name', 
            y='total_atividades',
            title="Top Vendedores por Atividades",
            labels={'user_name': 'Vendedor', 'total_atividades': 'Total Atividades'}
        )
        fig_vendedores.update_xaxes(tickangle=45)
        st.plotly_chart(fig_vendedores, use_container_width=True)
    
    with col2:
        # Tipos de contato por vendedor (top 5)
        top_vendedores = vendedores_df.head(5)
        tipos_contato = []
        
        for _, vendedor in top_vendedores.iterrows():
            nome_vendedor = vendedor['user_name'][:15] + "..." if len(vendedor['user_name']) > 15 else vendedor['user_name']
            tipos_contato.extend([
                {'Vendedor': nome_vendedor, 'Tipo': 'Contatos', 'Quantidade': vendedor['contatos']},
                {'Vendedor': nome_vendedor, 'Tipo': 'Follow-ups', 'Quantidade': vendedor['followups']},
                {'Vendedor': nome_vendedor, 'Tipo': 'E-mails', 'Quantidade': vendedor['emails']},
                {'Vendedor': nome_vendedor, 'Tipo': 'Reuniões', 'Quantidade': vendedor['reunioes']}
            ])
        
        tipos_df = pd.DataFrame(tipos_contato)
        
        if not tipos_df.empty:
            fig_tipos = px.bar(
                tipos_df, 
                x='Vendedor', 
                y='Quantidade',
                color='Tipo',
                title="Tipos de Contato por Vendedor (Top 5)"
            )
            fig_tipos.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig_tipos, use_container_width=True)

# Tabela detalhada de vendedores
st.subheader("📋 Detalhamento por Vendedor")

if not vendedores_df.empty:
    # Criar DataFrame final com todas as métricas
    vendedores_final = []
    for _, row in vendedores_df.iterrows():
        vendedor = row['user_name']
        
        # Buscar dados de segmentação de follow-ups
        followup_data = followup_segmentation_df[followup_segmentation_df['user_name'] == vendedor]
        alta_prioridade = followup_data.iloc[0]['alta_prioridade'] if not followup_data.empty else 0
        media_prioridade = followup_data.iloc[0]['media_prioridade'] if not followup_data.empty else 0
        baixa_prioridade = followup_data.iloc[0]['baixa_prioridade'] if not followup_data.empty else 0
        score_urgencia = followup_data.iloc[0]['score_medio_urgencia'] if not followup_data.empty else 0
        
        # Buscar dados de resposta e prazo
        response_data = response_metrics_df[response_metrics_df['user_name'] == vendedor]
        respostas_recebidas = response_data.iloc[0]['respostas_recebidas'] if not response_data.empty else 0
        followups_no_prazo = response_data.iloc[0]['followups_no_prazo'] if not response_data.empty else 0
        followups_atrasados = response_data.iloc[0]['followups_atrasados'] if not response_data.empty else 0
        
        # Calcular taxa de resposta
        total_contatos = row['contatos'] + row['emails']
        taxa_resposta = (respostas_recebidas / total_contatos * 100) if total_contatos > 0 else 0
        
        # Calcular taxa de follow-ups no prazo
        total_followups = row['followups']
        taxa_followups_prazo = (followups_no_prazo / total_followups * 100) if total_followups > 0 else 0
        
        vendedores_final.append({
            'Vendedor': vendedor,
            'Cargo': row.get('user_role', 'N/A'),
            'Total Atividades': row['total_atividades'],
            'Follow-ups': row['followups'],
            'Contatos': row['contatos'],
            'Reuniões': row['reunioes'],
            'E-mails': row['emails'],
            'Concluídas': row['concluidas'],
            'Taxa Conclusão (%)': row['taxa_conclusao'],
            'Leads Únicos': row['leads_diferentes'],
            'Alta Prioridade': alta_prioridade,
            'Média Prioridade': media_prioridade,
            'Baixa Prioridade': baixa_prioridade,
            'Score Urgência': f"{score_urgencia:.1f}" if score_urgencia > 0 else "0.0",
            'Taxa Resposta (%)': f"{taxa_resposta:.1f}",
            'Follow-ups no Prazo (%)': f"{taxa_followups_prazo:.1f}"
        })
    
    vendedores_final_df = pd.DataFrame(vendedores_final)
    
    # Exibir tabela com todas as métricas
    st.dataframe(vendedores_final_df, use_container_width=True)
    
    # Resumo das métricas de follow-up
    st.subheader("🎯 Resumo de Follow-ups e Engajamento")

    # Explicação das métricas
    st.info("""
**📊 NOVAS MÉTRICAS INTEGRADAS:**

**🎯 SEGMENTAÇÃO DE FOLLOW-UPS:**
- **Alta Prioridade**: Ações imediatas necessárias (score 8-10)
- **Média Prioridade**: Acompanhamento regular (score 5-7)  
- **Baixa Prioridade**: Manutenção de relacionamento (score 1-4)
- **Score Urgência**: Média ponderada de 1-10 baseada na API do Kommo

**📈 MÉTRICAS DE ENGAJAMENTO:**
- **Taxa Resposta (%)**: % de contatos que geraram resposta do lead
- **Follow-ups no Prazo (%)**: % de follow-ups realizados dentro do prazo definido

**💡 IMPORTÂNCIA**: Avalia a cadência de prospecção, qualidade do engajamento e eficiência na gestão de follow-ups.
""")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Score médio de urgência por vendedor
        if not followup_segmentation_df.empty:
            urgency_summary = followup_segmentation_df.sort_values('score_medio_urgencia', ascending=False).head(8)
            fig_urgency = px.bar(
                urgency_summary, 
                x='user_name', 
                y='score_medio_urgencia',
                title="Score Médio de Urgência por Vendedor",
                labels={'user_name': 'Vendedor', 'score_medio_urgencia': 'Score Urgência (1-10)'}
            )
            fig_urgency.update_xaxes(tickangle=45)
            st.plotly_chart(fig_urgency, use_container_width=True)
    
    with col2:
        # Distribuição por categoria de prioridade
        if not followup_segmentation_df.empty:
            priority_dist = followup_segmentation_df[['alta_prioridade', 'media_prioridade', 'baixa_prioridade']].sum()
            priority_df = pd.DataFrame({
                'Categoria': ['Alta Prioridade', 'Média Prioridade', 'Baixa Prioridade'],
                'Quantidade': [priority_dist['alta_prioridade'], priority_dist['media_prioridade'], priority_dist['baixa_prioridade']]
            })
            
            fig_priority = px.pie(
                priority_df, 
                values='Quantidade', 
                names='Categoria',
                title="Distribuição por Categoria de Prioridade"
            )
            st.plotly_chart(fig_priority, use_container_width=True)

# Análise temporal
st.subheader("📈 Atividades ao Longo do Tempo")

temporal_query = f"""
SELECT 
    DATE(created_datetime) as data,
    activity_type,
    COUNT(*) as atividades
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY DATE(created_datetime), activity_type
ORDER BY data DESC
LIMIT 50
"""

temporal_df = run_query(temporal_query)

if not temporal_df.empty:
    # Gráfico de linha temporal
    fig_temporal = px.line(
        temporal_df, 
        x='data', 
        y='atividades',
        color='activity_type',
        title="Atividades por Dia e Tipo"
    )
    st.plotly_chart(fig_temporal, use_container_width=True)

# SEÇÃO 5: MÓDULO 4 - CONVERSÃO E RECEITA
st.header("💰 Módulo 4: Conversão e Receita")
st.markdown("**Para medir resultados reais: vendas fechadas, receita, ticket médio e win rate**")

# Buscar dados reais de conversão e receita
vendas_query = f"""
SELECT 
    status_name,
    status_type,
    COUNT(*) as total_leads,
    SUM(sale_price) as receita_total,
    AVG(sale_price) as ticket_medio,
    AVG(sales_cycle_days) as ciclo_medio_dias
FROM sales_metrics 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY status_name, status_type
ORDER BY total_leads DESC
"""

vendas_df = run_query(vendas_query)

# Métricas principais do Módulo 4
if not vendas_df.empty:
    vendas_ganhas = vendas_df[vendas_df['status_name'] == 'Venda ganha']
    vendas_perdidas = vendas_df[vendas_df['status_name'] == 'Venda perdida']
    
    total_vendas_fechadas = vendas_ganhas['total_leads'].iloc[0] if not vendas_ganhas.empty else 0
    total_vendas_perdidas = vendas_perdidas['total_leads'].iloc[0] if not vendas_perdidas.empty else 0
    receita_total = vendas_ganhas['receita_total'].iloc[0] if not vendas_ganhas.empty else 0
    ticket_medio = vendas_ganhas['ticket_medio'].iloc[0] if not vendas_ganhas.empty else 0
    win_rate = (total_vendas_fechadas / (total_vendas_fechadas + total_vendas_perdidas) * 100) if (total_vendas_fechadas + total_vendas_perdidas) > 0 else 0
    ciclo_medio = vendas_ganhas['ciclo_medio_dias'].iloc[0] if not vendas_ganhas.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("✅ Vendas Fechadas", f"{total_vendas_fechadas:,}")
    
    with col2:
        st.metric("💰 Receita Total", f"R$ {receita_total:,.2f}")
    
    with col3:
        st.metric("🎫 Ticket Médio", f"R$ {ticket_medio:,.2f}")
    
    with col4:
        st.metric("📈 Win Rate", f"{win_rate:.1f}%")

# Performance por vendedor
st.subheader("👥 Performance de Vendas por Vendedor")

vendedores_vendas_query = f"""
SELECT 
    responsible_user_name as vendedor,
    responsible_user_role as cargo,
    COUNT(*) as total_leads,
    COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) as vendas_fechadas,
    COUNT(CASE WHEN status_name = 'Venda perdida' THEN 1 END) as vendas_perdidas,
    SUM(CASE WHEN status_name = 'Venda ganha' THEN sale_price ELSE 0 END) as receita_total,
    ROUND(AVG(CASE WHEN status_name = 'Venda ganha' THEN sale_price END), 2) as ticket_medio,
    ROUND(COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) / 
          NULLIF(COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) + 
                 COUNT(CASE WHEN status_name = 'Venda perdida' THEN 1 END), 0) * 100, 1) as win_rate,
    ROUND(AVG(CASE WHEN status_name = 'Venda ganha' THEN sales_cycle_days END), 1) as ciclo_medio
FROM sales_metrics 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY responsible_user_name, responsible_user_role
ORDER BY vendas_fechadas DESC
LIMIT 10
"""

vendedores_vendas_df = run_query(vendedores_vendas_query)

if not vendedores_vendas_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Top vendedores por vendas fechadas
        fig_vendedores_vendas = px.bar(
            vendedores_vendas_df.head(8), 
            x='vendedor', 
            y='vendas_fechadas',
            title="Top Vendedores por Vendas Fechadas",
            labels={'vendedor': 'Vendedor', 'vendas_fechadas': 'Vendas Fechadas'}
        )
        fig_vendedores_vendas.update_xaxes(tickangle=45)
        st.plotly_chart(fig_vendedores_vendas, use_container_width=True)
    
    with col2:
        # Receita por vendedor
        vendedores_com_receita = vendedores_vendas_df[vendedores_vendas_df['receita_total'] > 0].head(8)
        if not vendedores_com_receita.empty:
            fig_receita = px.bar(
                vendedores_com_receita, 
                x='vendedor', 
                y='receita_total',
                title="Receita por Vendedor",
                labels={'vendedor': 'Vendedor', 'receita_total': 'Receita (R$)'}
            )
            fig_receita.update_xaxes(tickangle=45)
            st.plotly_chart(fig_receita, use_container_width=True)

# Win Rate por vendedor
col1, col2 = st.columns(2)

with col1:
    # Win Rate por vendedor
    if not vendedores_vendas_df.empty and 'win_rate' in vendedores_vendas_df.columns:
        vendedores_win_rate = vendedores_vendas_df[vendedores_vendas_df['win_rate'].notna()].head(8)
    else:
        vendedores_win_rate = pd.DataFrame()
    if not vendedores_win_rate.empty:
        fig_win_rate = px.bar(
            vendedores_win_rate, 
            x='vendedor', 
            y='win_rate',
            title="Win Rate por Vendedor (%)",
            labels={'vendedor': 'Vendedor', 'win_rate': 'Win Rate (%)'}
        )
        fig_win_rate.update_xaxes(tickangle=45)
        st.plotly_chart(fig_win_rate, use_container_width=True)

with col2:
    # Ciclo de vendas por vendedor
    if not vendedores_vendas_df.empty and 'ciclo_medio' in vendedores_vendas_df.columns:
        vendedores_ciclo = vendedores_vendas_df[vendedores_vendas_df['ciclo_medio'].notna()].head(8)
    else:
        vendedores_ciclo = pd.DataFrame()
    if not vendedores_ciclo.empty:
        fig_ciclo = px.bar(
            vendedores_ciclo, 
            x='vendedor', 
            y='ciclo_medio',
            title="Ciclo Médio de Vendas (dias)",
            labels={'vendedor': 'Vendedor', 'ciclo_medio': 'Ciclo (dias)'}
        )
        fig_ciclo.update_xaxes(tickangle=45)
        st.plotly_chart(fig_ciclo, use_container_width=True)

# Tabela detalhada de performance de vendas
st.subheader("📋 Ranking Detalhado de Vendedores")

if not vendedores_vendas_df.empty:
    # Renomear colunas para exibição
    vendedores_vendas_display = vendedores_vendas_df.copy()
    vendedores_vendas_display = vendedores_vendas_display.rename(columns={
        'vendedor': 'Vendedor',
        'cargo': 'Cargo',
        'total_leads': 'Total Leads',
        'vendas_fechadas': 'Vendas Fechadas',
        'vendas_perdidas': 'Vendas Perdidas',
        'receita_total': 'Receita Total (R$)',
        'ticket_medio': 'Ticket Médio (R$)',
        'win_rate': 'Win Rate (%)',
        'ciclo_medio': 'Ciclo Médio (dias)'
    })
    
    st.dataframe(vendedores_vendas_display, use_container_width=True)

# Análise temporal de conversões
st.subheader("📈 Conversões ao Longo do Tempo")

conversoes_temporais_query = f"""
SELECT 
    DATE(closed_at) as data_fechamento,
    COUNT(CASE WHEN status_name = 'Venda ganha' THEN 1 END) as vendas_fechadas,
    COUNT(CASE WHEN status_name = 'Venda perdida' THEN 1 END) as vendas_perdidas,
    SUM(CASE WHEN status_name = 'Venda ganha' THEN sale_price ELSE 0 END) as receita_diaria
FROM sales_metrics 
WHERE closed_at IS NOT NULL 
AND created_date >= '{data_inicio.date()}'
GROUP BY DATE(closed_at)
ORDER BY data_fechamento DESC
LIMIT 30
"""

conversoes_temporais_df = run_query(conversoes_temporais_query)

if not conversoes_temporais_df.empty:
    fig_temporal = go.Figure()
    
    fig_temporal.add_trace(go.Scatter(
        x=conversoes_temporais_df['data_fechamento'],
        y=conversoes_temporais_df['vendas_fechadas'],
        mode='lines+markers',
        name='Vendas Fechadas',
        line=dict(color='green')
    ))
    
    fig_temporal.add_trace(go.Scatter(
        x=conversoes_temporais_df['data_fechamento'],
        y=conversoes_temporais_df['vendas_perdidas'],
        mode='lines+markers',
        name='Vendas Perdidas',
        line=dict(color='red')
    ))
    
    fig_temporal.update_layout(
        title="Conversões Diárias",
        xaxis_title="Data",
        yaxis_title="Quantidade",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_temporal, use_container_width=True)

# Insights e alertas de conversão
st.subheader("💡 Insights de Conversão")

if not vendas_df.empty:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if win_rate < 10:
            st.error(f"🚨 **CRÍTICO**: Win Rate de apenas {win_rate:.1f}%. Meta: >20%")
        elif win_rate < 20:
            st.warning(f"⚠️ **BAIXO**: Win Rate de {win_rate:.1f}%. Melhorar qualificação!")
        else:
            st.success(f"✅ **BOM**: Win Rate de {win_rate:.1f}%")
    
    with col2:
        if ticket_medio < 1000:
            st.warning(f"⚠️ **BAIXO**: Ticket médio R$ {ticket_medio:.0f}. Focar em up-sell!")
        else:
            st.success(f"✅ **BOM**: Ticket médio R$ {ticket_medio:.0f}")
    
    with col3:
        if ciclo_medio > 30:
            st.warning(f"⚠️ **LONGO**: Ciclo de {ciclo_medio:.0f} dias. Acelerar processo!")
        else:
            st.success(f"✅ **BOM**: Ciclo de {ciclo_medio:.0f} dias")

# SEÇÃO 6: MÓDULO 5 - PERFORMANCE POR PESSOA E CANAL
st.header("🏆 Módulo 5: Performance por Pessoa e Canal")
st.markdown("**Para gestão e tomada de decisão: rankings de vendedores e análise de canais mais qualificados**")

# Buscar dados de performance de vendedores
performance_vendedores_query = f"""
SELECT 
    user_name,
    user_role,
    SUM(total_leads) as total_leads,
    SUM(vendas_fechadas) as vendas_fechadas,
    SUM(vendas_perdidas) as vendas_perdidas,
    SUM(receita_total) as receita_total,
    AVG(win_rate) as win_rate,
    AVG(conversion_rate) as conversion_rate,
    AVG(ticket_medio) as ticket_medio,
    AVG(tempo_resposta_medio) as tempo_resposta_medio,
    AVG(ciclo_vendas_medio) as ciclo_vendas_medio,
    SUM(total_atividades) as total_atividades,
    SUM(atividades_concluidas) as atividades_concluidas,
    SUM(leads_contactados) as leads_contactados,
    AVG(taxa_conclusao_atividades) as taxa_conclusao_atividades
FROM performance_vendedores 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY user_name, user_role
ORDER BY receita_total DESC
"""

performance_vendedores_df = run_query(performance_vendedores_query)

# Buscar dados de performance de canais
performance_canais_query = f"""
SELECT 
    canal_origem,
    utm_source,
    utm_medium,
    SUM(total_leads) as total_leads,
    SUM(vendas_fechadas) as vendas_fechadas,
    SUM(vendas_perdidas) as vendas_perdidas,
    SUM(receita_total) as receita_total,
    SUM(custo_total) as custo_total,
    AVG(win_rate) as win_rate,
    AVG(conversion_rate) as conversion_rate,
    AVG(ticket_medio) as ticket_medio,
    AVG(custo_por_lead) as custo_por_lead,
    AVG(roi) as roi,
    AVG(tempo_resposta_medio) as tempo_resposta_medio,
    AVG(ciclo_vendas_medio) as ciclo_vendas_medio
FROM performance_canais 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY canal_origem, utm_source, utm_medium
ORDER BY receita_total DESC
"""

performance_canais_df = run_query(performance_canais_query)

# Métricas principais do Módulo 5
col1, col2, col3, col4 = st.columns(4)

if not performance_vendedores_df.empty and not performance_canais_df.empty:
    top_vendedor = performance_vendedores_df.iloc[0]
    top_canal = performance_canais_df.iloc[0]
    total_vendedores = performance_vendedores_df['user_name'].nunique()
    total_canais = performance_canais_df['canal_origem'].nunique()
    
    with col1:
        st.metric("👑 Top Vendedor", f"{top_vendedor['user_name'][:15]}", f"R$ {top_vendedor['receita_total']:,.0f}")
    
    with col2:
        st.metric("🏆 Top Canal", f"{top_canal['canal_origem'][:15]}", f"R$ {top_canal['receita_total']:,.0f}")
    
    with col3:
        st.metric("👥 Vendedores", f"{total_vendedores}")
    
    with col4:
        st.metric("📈 Canais", f"{total_canais}")

# Performance de Vendedores
st.subheader("👥 Ranking de Vendedores")

if not performance_vendedores_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Ranking por receita
        fig_vendedores_receita = px.bar(
            performance_vendedores_df.head(8), 
            x='user_name', 
            y='receita_total',
            title="🥇 Ranking por Receita",
            labels={'user_name': 'Vendedor', 'receita_total': 'Receita (R$)'},
            color='receita_total',
            color_continuous_scale='Viridis'
        )
        fig_vendedores_receita.update_xaxes(tickangle=45)
        st.plotly_chart(fig_vendedores_receita, use_container_width=True)
    
    with col2:
        # Ranking por taxa de conversão
        vendedores_conversao = performance_vendedores_df[performance_vendedores_df['win_rate'] > 0].head(8)
        if not vendedores_conversao.empty:
            fig_vendedores_conversao = px.bar(
                vendedores_conversao, 
                x='user_name', 
                y='win_rate',
                title="🎯 Ranking por Taxa de Conversão",
                labels={'user_name': 'Vendedor', 'win_rate': 'Win Rate (%)'},
                color='win_rate',
                color_continuous_scale='RdYlGn'
            )
            fig_vendedores_conversao.update_xaxes(tickangle=45)
            st.plotly_chart(fig_vendedores_conversao, use_container_width=True)
        else:
            # Mostrar todos os vendedores se não houver filtro
            fig_vendedores_conversao = px.bar(
                performance_vendedores_df.head(8), 
                x='user_name', 
                y='win_rate',
                title="🎯 Ranking por Taxa de Conversão",
                labels={'user_name': 'Vendedor', 'win_rate': 'Win Rate (%)'},
                color='win_rate',
                color_continuous_scale='RdYlGn'
            )
            fig_vendedores_conversao.update_xaxes(tickangle=45)
            st.plotly_chart(fig_vendedores_conversao, use_container_width=True)

    # Análise avançada de vendedores
    col1, col2 = st.columns(2)
    
    with col1:
        # Eficiência (receita por atividade)
        vendedores_eficiencia = performance_vendedores_df[
            (performance_vendedores_df['total_atividades'] > 0) & 
            (performance_vendedores_df['receita_total'] > 0)
        ].copy()
        
        if not vendedores_eficiencia.empty:
            vendedores_eficiencia['eficiencia'] = vendedores_eficiencia['receita_total'] / vendedores_eficiencia['total_atividades']
            vendedores_eficiencia = vendedores_eficiencia.nlargest(8, 'eficiencia')
            
            fig_eficiencia = px.bar(
                vendedores_eficiencia,
                x='user_name',
                y='eficiencia',
                title="💡 Eficiência (R$ por Atividade)",
                labels={'user_name': 'Vendedor', 'eficiencia': 'R$ / Atividade'},
                color='eficiencia',
                color_continuous_scale='Plasma'
            )
            fig_eficiencia.update_xaxes(tickangle=45)
            st.plotly_chart(fig_eficiencia, use_container_width=True)
    
    with col2:
        # Scatter plot: Win Rate vs Ticket Médio
        vendedores_scatter = performance_vendedores_df[
            (performance_vendedores_df['win_rate'] > 0) & 
            (performance_vendedores_df['ticket_medio'] > 0)
        ]
        
        if not vendedores_scatter.empty:
            fig_scatter = px.scatter(
                vendedores_scatter,
                x='win_rate',
                y='ticket_medio',
                size='receita_total',
                hover_name='user_name',
                title="🎯 Win Rate vs Ticket Médio",
                labels={'win_rate': 'Win Rate (%)', 'ticket_medio': 'Ticket Médio (R$)'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# Performance de Canais
st.subheader("📈 Análise de Canais")

if not performance_canais_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Conversão por canal de origem
        canais_conversao = performance_canais_df[performance_canais_df['conversion_rate'] > 0].head(10)
        if not canais_conversao.empty:
            fig_canais_conversao = px.bar(
                canais_conversao,
                x='canal_origem',
                y='conversion_rate',
                title="🎯 Conversão por Canal de Origem",
                labels={'canal_origem': 'Canal', 'conversion_rate': 'Taxa Conversão (%)'},
                color='conversion_rate',
                color_continuous_scale='RdYlGn'
            )
            fig_canais_conversao.update_xaxes(tickangle=45)
            st.plotly_chart(fig_canais_conversao, use_container_width=True)
    
    with col2:
        # ROI por canal
        canais_roi = performance_canais_df[performance_canais_df['roi'] != 0].head(10)
        if not canais_roi.empty:
            fig_canais_roi = px.bar(
                canais_roi,
                x='canal_origem',
                y='roi',
                title="💰 ROI por Canal (%)",
                labels={'canal_origem': 'Canal', 'roi': 'ROI (%)'},
                color='roi',
                color_continuous_scale='RdYlBu'
            )
            fig_canais_roi.update_xaxes(tickangle=45)
            st.plotly_chart(fig_canais_roi, use_container_width=True)

    # Análise de qualidade dos canais
    col1, col2 = st.columns(2)
    
    with col1:
        # Volume vs Qualidade (Scatter)
        canais_scatter = performance_canais_df[performance_canais_df['total_leads'] > 0]
        if not canais_scatter.empty:
            fig_canais_scatter = px.scatter(
                canais_scatter,
                x='total_leads',
                y='conversion_rate',
                size='receita_total',
                hover_name='canal_origem',
                title="📊 Volume vs Qualidade dos Canais",
                labels={'total_leads': 'Total Leads', 'conversion_rate': 'Taxa Conversão (%)'}
            )
            st.plotly_chart(fig_canais_scatter, use_container_width=True)
    
    with col2:
        # Eficiência de custo
        canais_custo = performance_canais_df[performance_canais_df['custo_por_lead'] > 0].head(8)
        if not canais_custo.empty:
            fig_custo_lead = px.bar(
                canais_custo,
                x='canal_origem',
                y='custo_por_lead',
                title="💸 Custo por Lead por Canal",
                labels={'canal_origem': 'Canal', 'custo_por_lead': 'Custo por Lead (R$)'},
                color='custo_por_lead',
                color_continuous_scale='Reds_r'
            )
            fig_custo_lead.update_xaxes(tickangle=45)
            st.plotly_chart(fig_custo_lead, use_container_width=True)

# Tabelas detalhadas
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Top 10 Vendedores")
    if not performance_vendedores_df.empty:
        top_vendedores = performance_vendedores_df.head(10).copy()
        top_vendedores_display = top_vendedores[['user_name', 'vendas_fechadas', 'receita_total', 'win_rate', 'ticket_medio']].rename(columns={
            'user_name': 'Vendedor',
            'vendas_fechadas': 'Vendas',
            'receita_total': 'Receita (R$)',
            'win_rate': 'Win Rate (%)',
            'ticket_medio': 'Ticket Médio (R$)'
        })
        st.dataframe(top_vendedores_display, use_container_width=True)

with col2:
    st.subheader("📈 Top 10 Canais")
    if not performance_canais_df.empty:
        top_canais = performance_canais_df.head(10).copy()
        top_canais_display = top_canais[['canal_origem', 'vendas_fechadas', 'receita_total', 'conversion_rate', 'roi']].rename(columns={
            'canal_origem': 'Canal',
            'vendas_fechadas': 'Vendas',
            'receita_total': 'Receita (R$)',
            'conversion_rate': 'Conv Rate (%)',
            'roi': 'ROI (%)'
        })
        st.dataframe(top_canais_display, use_container_width=True)

# SEÇÃO 7: MÓDULO 6 - PREVISIBILIDADE (FORECAST)
st.header("🔮 Módulo 6: Previsibilidade (Forecast)")
st.markdown("**Forecast de receita (previsto vs. realizado) para antecipar gargalos antes de fechar o mês**")

# Buscar forecast baseado nos dados dos Módulos 1 a 5
forecast_query = f"""
SELECT 
    mes_ano,
    data_previsao,
    meta_receita,
    previsao_receita,
    previsao_leads,
    previsao_win_rate,
    previsao_ticket_medio
FROM monthly_forecasts 
WHERE mes_ano = DATE_FORMAT('{selected_date}', '%Y-%m')
ORDER BY data_previsao DESC
LIMIT 1
"""

forecast_df = run_query(forecast_query)

# Buscar resultados reais baseados nos dados dos Módulos 1 a 5
results_query = f"""
SELECT 
    DATE_FORMAT('{selected_date}', '%Y-%m') as mes_ano,
    NOW() as data_atualizacao,
    SUM(CASE WHEN sm.status_name = 'Venda ganha' THEN sm.sale_price ELSE 0 END) as receita_realizada,
    COUNT(DISTINCT l.lead_id) as leads_realizados,
    COUNT(DISTINCT CASE WHEN sm.status_name = 'Venda ganha' THEN sm.lead_id END) as vendas_fechadas,
    COUNT(DISTINCT CASE WHEN sm.status_name = 'Venda perdida' THEN sm.lead_id END) as vendas_perdidas,
    ROUND(COUNT(DISTINCT CASE WHEN sm.status_name = 'Venda ganha' THEN sm.lead_id END) / 
          NULLIF(COUNT(DISTINCT CASE WHEN sm.status_name IN ('Venda ganha', 'Venda perdida') THEN sm.lead_id END), 0) * 100, 1) as win_rate_real,
    AVG(CASE WHEN sm.status_name = 'Venda ganha' THEN sm.sale_price END) as ticket_medio_real,
    DATEDIFF('{selected_date}', DATE_FORMAT('{selected_date}', '%Y-%m-01')) + 1 as dias_passados,
    DATEDIFF(LAST_DAY('{selected_date}'), '{selected_date}') as dias_restantes
FROM leads_metrics l
LEFT JOIN sales_metrics sm ON l.lead_id = sm.lead_id
WHERE l.created_date >= DATE_FORMAT('{selected_date}', '%Y-%m-01')
AND l.created_date <= LAST_DAY('{selected_date}')
"""

results_df = run_query(results_query)

# Buscar gaps e gargalos baseados nos dados dos Módulos 1 a 5
gaps_query = f"""
SELECT 
    mes_ano,
    data_analise,
    gap_receita,
    gap_leads,
    gap_win_rate,
    gap_ticket_medio,
    receita_necessaria_diaria,
    leads_necessarios_diarios,
    win_rate_necessario,
    ticket_medio_necessario,
    risco_meta,
    alertas,
    acoes_recomendadas
FROM forecast_gaps 
WHERE mes_ano = DATE_FORMAT('{selected_date}', '%Y-%m')
ORDER BY data_analise DESC
LIMIT 1
"""

gaps_df = run_query(gaps_query)

# Métricas principais do Módulo 6 - Forecast vs Realizado
col1, col2, col3, col4 = st.columns(4)

if not forecast_df.empty and not results_df.empty:
    forecast = forecast_df.iloc[0]
    results = results_df.iloc[0]
    
    # Verificar se os valores não são None e definir valores padrão
    meta_receita = forecast.get('meta_receita', 0) or 0
    receita_realizada = results.get('receita_realizada', 0) or 0
    win_rate_real = results.get('win_rate_real', 0) or 0
    previsao_win_rate = forecast.get('previsao_win_rate', 0) or 0
    dias_restantes = results.get('dias_restantes', 0) or 0
    dias_passados = results.get('dias_passados', 0) or 0
    
    with col1:
        st.metric(
            "🎯 Meta Receita", 
            f"R$ {meta_receita:,.0f}", 
            f"vs R$ {receita_realizada:,.0f} realizado"
        )
    
    with col2:
        gap_receita = meta_receita - receita_realizada
        gap_percentual = (gap_receita/meta_receita)*100 if meta_receita > 0 else 0
        st.metric(
            "📊 Gap Receita", 
            f"R$ {gap_receita:,.0f}", 
            f"{gap_percentual:.1f}% da meta"
        )
    
    with col3:
        st.metric(
            "📈 Win Rate", 
            f"{win_rate_real:.1f}%", 
            f"vs {previsao_win_rate:.1f}% previsto"
        )
    
    with col4:
        st.metric(
            "⏰ Dias Restantes", 
            f"{dias_restantes}", 
            f"de {dias_passados} passados"
        )
else:
    # Mostrar mensagem quando não há dados
    with col1:
        st.metric("🎯 Meta Receita", "R$ 0", "Sem dados")
    with col2:
        st.metric("📊 Gap Receita", "R$ 0", "Sem dados")
    with col3:
        st.metric("📈 Win Rate", "0.0%", "Sem dados")
    with col4:
        st.metric("⏰ Dias Restantes", "0", "Sem dados")

# Análise de Gaps e Gargalos
st.subheader("⚠️ Análise de Gaps para Fechamento do Mês")

if not gaps_df.empty:
    gaps = gaps_df.iloc[0]
    
    # Verificar se os valores não são None e definir valores padrão
    risco_meta = gaps.get('risco_meta', 'baixo') or 'baixo'
    alertas = gaps.get('alertas', 'Sem dados') or 'Sem dados'
    acoes_recomendadas = gaps.get('acoes_recomendadas', 'Sem dados') or 'Sem dados'
    receita_necessaria_diaria = gaps.get('receita_necessaria_diaria', 0) or 0
    leads_necessarios_diarios = gaps.get('leads_necessarios_diarios', 0) or 0
    win_rate_necessario = gaps.get('win_rate_necessario', 0) or 0
    ticket_medio_necessario = gaps.get('ticket_medio_necessario', 0) or 0
    
    # Alertas de risco
    risco_color = {
        'baixo': 'green',
        'medio': 'orange', 
        'alto': 'red',
        'critico': 'darkred'
    }
    
    st.markdown(f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: {risco_color.get(risco_meta, 'gray')}; color: white;">
        <h4>🚨 Risco da Meta: {risco_meta.upper()}</h4>
        <p><strong>Alertas:</strong> {alertas}</p>
        <p><strong>Ações Recomendadas:</strong> {acoes_recomendadas}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas de gap
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Receita Necessária/Dia",
            f"R$ {receita_necessaria_diaria:,.0f}",
            f"para atingir meta"
        )
    
    with col2:
        st.metric(
            "📊 Leads Necessários/Dia",
            f"{leads_necessarios_diarios:.0f}",
            f"para atingir meta"
        )
    
    with col3:
        st.metric(
            "🎯 Win Rate Necessário",
            f"{win_rate_necessario:.1f}%",
            f"para atingir meta"
        )
    
    with col4:
        st.metric(
            "💎 Ticket Médio Necessário",
            f"R$ {ticket_medio_necessario:,.0f}",
            f"para atingir meta"
        )
else:
    st.warning("⚠️ Não há dados de gaps disponíveis para o período selecionado.")

# Comparação Previsto vs Realizado
st.subheader("📊 Comparação Previsto vs Realizado")

col1, col2 = st.columns(2)

with col1:
    if not forecast_df.empty and not results_df.empty:
        forecast = forecast_df.iloc[0]
        results = results_df.iloc[0]
        
        # Verificar se os valores não são None e definir valores padrão
        meta_receita = forecast.get('meta_receita', 0) or 0
        previsao_receita = forecast.get('previsao_receita', 0) or 0
        receita_realizada = results.get('receita_realizada', 0) or 0
        
        # Gráfico de barras comparativo
        fig_comparativo = go.Figure()
        
        # Receita
        fig_comparativo.add_trace(go.Bar(
            name='Meta',
            x=['Receita'],
            y=[meta_receita],
            marker_color='red'
        ))
        
        fig_comparativo.add_trace(go.Bar(
            name='Previsto',
            x=['Receita'],
            y=[previsao_receita],
            marker_color='orange'
        ))
        
        fig_comparativo.add_trace(go.Bar(
            name='Realizado',
            x=['Receita'],
            y=[receita_realizada],
            marker_color='green'
        ))
        
        fig_comparativo.update_layout(
            title="💰 Receita: Meta vs Previsto vs Realizado",
            yaxis_title="Valor (R$)",
            barmode='group'
        )
        
        st.plotly_chart(fig_comparativo, use_container_width=True)
    else:
        st.warning("⚠️ Não há dados suficientes para gerar o gráfico de comparação.")
    
    with col2:
        if not forecast_df.empty and not results_df.empty:
            forecast = forecast_df.iloc[0]
            results = results_df.iloc[0]
            
            # Verificar se os valores não são None e definir valores padrão
            previsao_win_rate = forecast.get('previsao_win_rate', 0) or 0
            win_rate_real = results.get('win_rate_real', 0) or 0
            previsao_ticket_medio = forecast.get('previsao_ticket_medio', 0) or 0
            ticket_medio_real = results.get('ticket_medio_real', 0) or 0
            
            # Gráfico de Win Rate e Ticket Médio
            fig_metrics = go.Figure()
            
            # Win Rate
            fig_metrics.add_trace(go.Bar(
                name='Win Rate Previsto',
                x=['Win Rate'],
                y=[previsao_win_rate],
                marker_color='lightblue'
            ))
            
            fig_metrics.add_trace(go.Bar(
                name='Win Rate Real',
                x=['Win Rate'],
                y=[win_rate_real],
                marker_color='blue'
            ))
            
            # Ticket Médio
            fig_metrics.add_trace(go.Bar(
                name='Ticket Previsto',
                x=['Ticket Médio'],
                y=[previsao_ticket_medio],
                marker_color='lightgreen'
            ))
            
            fig_metrics.add_trace(go.Bar(
                name='Ticket Real',
                x=['Ticket Médio'],
                y=[ticket_medio_real],
                marker_color='green'
            ))
            
            fig_metrics.update_layout(
                title="📊 Win Rate e Ticket Médio: Previsto vs Realizado",
                yaxis_title="Valor (%) / (R$)",
                barmode='group'
            )
            
            st.plotly_chart(fig_metrics, use_container_width=True)

# Resumo Executivo do Forecast
st.subheader("📋 Resumo Executivo do Forecast")

if not forecast_df.empty and not results_df.empty and not gaps_df.empty:
    forecast = forecast_df.iloc[0]
    results = results_df.iloc[0]
    gaps = gaps_df.iloc[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎯 METAS E PREVISÕES:**")
        st.markdown(f"- **Meta de Receita:** R$ {forecast.get('meta_receita', 0) or 0:,.2f}")
        st.markdown(f"- **Previsão de Receita:** R$ {forecast.get('previsao_receita', 0) or 0:,.2f}")
        st.markdown(f"- **Previsão de Leads:** {forecast.get('previsao_leads', 0) or 0:,}")
        st.markdown(f"- **Win Rate Esperado:** {forecast.get('previsao_win_rate', 0) or 0:.1f}%")
        st.markdown(f"- **Ticket Médio Esperado:** R$ {forecast.get('previsao_ticket_medio', 0) or 0:,.2f}")
    
    with col2:
        st.markdown("**📊 RESULTADOS ATUAIS:**")
        st.markdown(f"- **Receita Realizada:** R$ {results.get('receita_realizada', 0) or 0:,.2f}")
        st.markdown(f"- **Leads Realizados:** {results.get('leads_realizados', 0) or 0:,}")
        st.markdown(f"- **Vendas Fechadas:** {results.get('vendas_fechadas', 0) or 0}")
        st.markdown(f"- **Win Rate Real:** {results.get('win_rate_real', 0) or 0:.1f}%")
        st.markdown(f"- **Ticket Médio Real:** R$ {results.get('ticket_medio_real', 0) or 0:,.2f}")
        st.markdown(f"- **Dias Restantes:** {results.get('dias_restantes', 0) or 0}")

# Análise de Performance
st.subheader("📈 Análise de Performance")

if not gaps_df.empty:
    gaps = gaps_df.iloc[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 GAPS IDENTIFICADOS:**")
        st.markdown(f"- **Gap de Receita:** R$ {gaps.get('gap_receita', 0) or 0:,.2f}")
        st.markdown(f"- **Gap de Leads:** {gaps.get('gap_leads', 0) or 0}")
        st.markdown(f"- **Gap de Win Rate:** {gaps.get('gap_win_rate', 0) or 0:.1f}%")
        st.markdown(f"- **Gap de Ticket Médio:** R$ {gaps.get('gap_ticket_medio', 0) or 0:,.2f}")
    
    with col2:
        st.markdown("**🎯 NECESSIDADES PARA ATINGIR META:**")
        st.markdown(f"- **Receita/Dia:** R$ {gaps.get('receita_necessaria_diaria', 0) or 0:,.0f}")
        st.markdown(f"- **Leads/Dia:** {gaps.get('leads_necessarios_diarios', 0) or 0:.0f}")
        st.markdown(f"- **Win Rate:** {gaps.get('win_rate_necessario', 0) or 0:.1f}%")
        st.markdown(f"- **Ticket Médio:** R$ {gaps.get('ticket_medio_necessario', 0) or 0:,.0f}")

# Alertas Automáticos
st.subheader("🚨 Alertas Automáticos")

if not gaps_df.empty:
    gaps = gaps_df.iloc[0]
    
    if gaps.get('risco_meta') == 'critico':
        st.error("🚨 **ALERTA CRÍTICO**: Risco alto de não atingir a meta! Ações imediatas necessárias.")
    elif gaps.get('risco_meta') == 'alto':
        st.warning("⚠️ **ALERTA ALTO**: Risco moderado de não atingir a meta. Acompanhamento intensivo necessário.")
    elif gaps.get('risco_meta') == 'medio':
        st.info("ℹ️ **ALERTA MÉDIO**: Risco baixo, mas atenção aos gaps identificados.")
    else:
        st.success("✅ **STATUS OK**: Meta em dia, mantendo performance atual.")

# Buscar dados de segmentação dos follow-ups para integrar na tabela principal
followup_segmentation_query = f"""
SELECT 
    user_name,
    COUNT(*) as total_followups,
    COUNT(CASE WHEN follow_up_category = 'alta_prioridade' THEN 1 END) as alta_prioridade,
    COUNT(CASE WHEN follow_up_category = 'media_prioridade' THEN 1 END) as media_prioridade,
    COUNT(CASE WHEN follow_up_category = 'baixa_prioridade' THEN 1 END) as baixa_prioridade,
    AVG(urgency_score) as score_medio_urgencia
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}' AND is_follow_up = 1
GROUP BY user_name
"""

followup_segmentation_df = run_query(followup_segmentation_query)

# Buscar dados de taxa de resposta e follow-ups no prazo
response_metrics_query = f"""
SELECT 
    user_name,
    COUNT(CASE WHEN activity_type = 'note' AND note_text LIKE '%resposta%' OR note_text LIKE '%retorno%' THEN 1 END) as respostas_recebidas,
    COUNT(CASE WHEN activity_type = 'task' AND is_follow_up = 1 AND complete_till IS NOT NULL AND complete_till >= created_date THEN 1 END) as followups_no_prazo,
    COUNT(CASE WHEN activity_type = 'task' AND is_follow_up = 1 AND complete_till IS NOT NULL AND complete_till < created_date THEN 1 END) as followups_atrasados
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY user_name
"""

response_metrics_df = run_query(response_metrics_query)


