# Dashboard Streamlit - Kommo Analytics (6 MÓDULOS ETL)
import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime, timedelta, date
import json
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(page_title="Kommo Analytics", layout="wide")

# Funções para verificação de status e solicitação de ETL
def get_etl_status():
    """Lê status da última execução dos ETLs"""
    try:
        status_file = "/home/raquel-fonseca/Projects/KommoAnalytics/LOGS/last_execution_status.txt"
        
        if not os.path.exists(status_file):
            return "nunca_executado", None, None
        
        status_data = {}
        with open(status_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    status_data[key] = value
        
        timestamp = status_data.get('timestamp', 'Desconhecido')
        success_count = int(status_data.get('success_count', 0))
        total_etls = int(status_data.get('total_etls', 6))
        status = status_data.get('status', 'UNKNOWN')
        
        return status, timestamp, f"{success_count}/{total_etls}"
        
    except Exception as e:
        st.error(f"Erro ao ler status: {e}")
        return "erro", None, None

def request_kommo_etl():
    """Solicita execução do ETL Kommo"""
    try:
        with open('/tmp/kommo_etl_requested.flag', 'w') as f:
            f.write(f"{datetime.now().isoformat()}\nrequested_by_dashboard")
        return True
    except:
        return False

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
st.title("📊 Kommo Analytics Dashboard")

# Status do ETL
status, last_run, success_ratio = get_etl_status()

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    if status == "SUCCESS":
        st.success(f"✅ ETL Completo: {success_ratio}")
    elif status == "PARTIAL":
        st.warning(f"⚠️ ETL Parcial: {success_ratio}")
    else:
        st.error("❌ ETL com Problemas")

with col2:
    if last_run:
        st.info(f"🕐 Última execução: {last_run}")

with col3:
    if st.button("🔄 Solicitar ETL"):
        if request_kommo_etl():
            st.success("✅ ETL solicitado!")
            time.sleep(2)
            st.rerun()

# Sidebar
st.sidebar.title(" Filtros")
periodo = st.sidebar.selectbox("Período:", ["7 dias", "15 dias", "30 dias"], index=2)  # 30 dias por padrão
dias = int(periodo.split()[0])
data_inicio = datetime.now() - timedelta(days=dias)

# SEÇÃO 1: MÓDULO 1 - ENTRADA E ORIGEM DE LEADS
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
        # Top UTMs por medium
        utm_medium_df = utms_df.groupby('utm_medium')['total_leads'].sum().reset_index().sort_values('total_leads', ascending=False)
        fig_utm_medium = px.pie(
            utm_medium_df, 
            values='total_leads', 
            names='utm_medium',
            title="Leads por UTM Medium"
        )
        st.plotly_chart(fig_utm_medium, use_container_width=True)

    # Tabela de UTMs
    st.subheader("📋 Top 10 Combinações UTM")
    utms_display = utms_df.copy()
    utms_display = utms_display.rename(columns={
        'utm_source': 'UTM Source',
        'utm_medium': 'UTM Medium', 
        'utm_campaign': 'UTM Campaign',
        'total_leads': 'Total Leads'
    })
    st.dataframe(utms_display, use_container_width=True)
else:
    st.info("Nenhum dado de UTM encontrado para o período selecionado.")

# SEÇÃO 2: MÓDULO 2 - QUALIFICAÇÃO E AVANÇO NO FUNIL
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

# SEÇÃO 2.5: ANÁLISE DE VENDAS PERDIDAS
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

# SEÇÃO 2.6: MOTIVOS DE PERDA
st.header("🔍 Motivos de Perda")
st.markdown("**Análise detalhada dos motivos de perda no funil**")

# Buscar dados reais de motivos de perda
motivos_perda_query = f"""
SELECT 
    COALESCE(loss_reason_name, 'Não especificado') as motivo,
    COUNT(DISTINCT lead_id) as leads_perdidos,
    AVG(time_in_status_hours) as tempo_medio
FROM funnel_history 
WHERE entry_date >= '{data_inicio.date()}'
AND status_name = 'Venda perdida'
GROUP BY loss_reason_name
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

# SEÇÃO 3: MÓDULO 3 - ATIVIDADES COMERCIAIS  
st.header("📞 Módulo 3: Atividades Comerciais")
st.markdown("**Para entender o esforço do time e avaliar cadência de prospecção**")

# Buscar dados reais de atividades comerciais
atividades_query = f"""
SELECT 
    contact_type as activity_type,
    COUNT(*) as total_atividades,
    COUNT(DISTINCT user_id) as vendedores_unicos,
    COUNT(CASE WHEN is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) as concluidas,
    ROUND(COUNT(CASE WHEN is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao,
    COUNT(DISTINCT entity_id) as leads_contatatados
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY contact_type 
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
                {'Vendedor': nome_vendedor, 'Tipo': 'Ligações', 'Quantidade': vendedor['ligacoes']},
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

# Análise de Follow-ups
st.subheader("📊 Segmentação de Follow-ups")

followups_query = f"""
SELECT 
    contact_type,
    COUNT(*) as total_followups,
    COUNT(CASE WHEN is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) as concluidos,
    ROUND(COUNT(CASE WHEN is_successful = 1 OR completed_at IS NOT NULL THEN 1 END) / COUNT(*) * 100, 1) as taxa_conclusao,
    COUNT(DISTINCT user_id) as vendedores_unicos,
    COUNT(DISTINCT entity_id) as leads_unicos
FROM commercial_activities 
WHERE created_date >= '{data_inicio.date()}'
    AND contact_type LIKE '%follow%'
GROUP BY contact_type 
ORDER BY total_followups DESC
"""

followups_df = run_query(followups_query)

if not followups_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de follow-ups por tipo
        fig_followups = px.pie(
            followups_df, 
            values='total_followups', 
            names='contact_type',
            title="Distribuição de Follow-ups por Tipo"
        )
        st.plotly_chart(fig_followups, use_container_width=True)
    
    with col2:
        # Taxa de conclusão por tipo
        fig_conclusao_followups = px.bar(
            followups_df, 
            x='contact_type', 
            y='taxa_conclusao',
            title="Taxa de Conclusão por Tipo de Follow-up (%)",
            labels={'contact_type': 'Tipo de Follow-up', 'taxa_conclusao': 'Taxa (%)'}
        )
        fig_conclusao_followups.update_xaxes(tickangle=45)
        st.plotly_chart(fig_conclusao_followups, use_container_width=True)
    
    # Tabela detalhada de follow-ups
    st.subheader("📋 Detalhamento de Follow-ups")
    followups_display = followups_df.copy()
    followups_display = followups_display.rename(columns={
        'contact_type': 'Tipo de Follow-up',
        'total_followups': 'Total Follow-ups',
        'concluidos': 'Concluídos',
        'taxa_conclusao': 'Taxa Conclusão (%)',
        'vendedores_unicos': 'Vendedores Únicos',
        'leads_unicos': 'Leads Únicos'
    })
    st.dataframe(followups_display, use_container_width=True)
else:
    st.info("Nenhum follow-up encontrado no período selecionado.")


# SEÇÃO 4: MÓDULO 4 - CONVERSÃO E RECEITA
st.header("💰 Módulo 4: Conversão e Receita")
st.markdown("**Para medir resultados reais: vendas fechadas, receita, ticket médio e win rate**")

# Buscar dados reais de conversão e receita
vendas_query = f"""
SELECT 
    status_name,
    status_type,
    COUNT(*) as total_leads,
    SUM(lead_value) as receita_total,
    AVG(lead_value) as ticket_medio,
    AVG(sales_cycle_days) as ciclo_medio_dias
FROM sales_conversions 
WHERE created_date >= '{data_inicio.date()}'
GROUP BY status_name, status_type
ORDER BY total_leads DESC
"""

vendas_df = run_query(vendas_query)

# Métricas principais do Módulo 4
if not vendas_df.empty:
    vendas_ganhas = vendas_df[vendas_df['status_type'] == 'won']
    vendas_perdidas = vendas_df[vendas_df['status_type'] == 'lost']
    
    total_vendas_fechadas = vendas_ganhas['total_leads'].sum() if not vendas_ganhas.empty else 0
    total_vendas_perdidas = vendas_perdidas['total_leads'].sum() if not vendas_perdidas.empty else 0
    receita_total = vendas_ganhas['receita_total'].sum() if not vendas_ganhas.empty else 0
    ticket_medio = vendas_ganhas['ticket_medio'].mean() if not vendas_ganhas.empty else 0
    win_rate = (total_vendas_fechadas / (total_vendas_fechadas + total_vendas_perdidas) * 100) if (total_vendas_fechadas + total_vendas_perdidas) > 0 else 0
    ciclo_medio = vendas_ganhas['ciclo_medio_dias'].mean() if not vendas_ganhas.empty else 0
    
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
    vendedores_win_rate = vendedores_vendas_df[vendedores_vendas_df['win_rate'].notna()].head(8)
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
    vendedores_ciclo = vendedores_vendas_df[vendedores_vendas_df['ciclo_medio'].notna()].head(8)
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

# SEÇÃO 5: MÓDULO 5 - PERFORMANCE POR PESSOA E CANAL
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
col1, col2, col3 = st.columns(3)

if not performance_vendedores_df.empty and not performance_canais_df.empty:
    top_vendedor = performance_vendedores_df.iloc[0]
    top_canal = performance_canais_df.iloc[0]
    total_vendedores = performance_vendedores_df['user_name'].nunique()
    
    with col1:
        st.metric("👑 Top Vendedor", f"{top_vendedor['user_name'][:15]}", f"R$ {top_vendedor['receita_total']:,.0f}")
    
    with col2:
        st.metric("🏆 Top Canal", f"{top_canal['canal_origem'][:15]}", f"R$ {top_canal['receita_total']:,.0f}")
    
    with col3:
        st.metric("👥 Vendedores", f"{total_vendedores}")

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
                title="�� Win Rate vs Ticket Médio",
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

# SEÇÃO 6: MÓDULO 6 - PREVISÕES E FORECASTING
st.header("🔮 Módulo 6: Previsões e Forecasting")
st.markdown("**Análise preditiva e planejamento estratégico baseado em dados reais dos Módulos 1-5**")

# Buscar dados de forecast integrado
forecast_query = f"""
SELECT 
    mes_ano,
    meta_receita,
    previsao_receita,
    previsao_leads,
    previsao_win_rate,
    previsao_ticket_medio,
    created_date
FROM monthly_forecasts 
WHERE created_date >= '{data_inicio.date()}'
ORDER BY created_date DESC
LIMIT 1
"""

forecast_df = run_query(forecast_query)

# Buscar gaps e alertas
gaps_query = f"""
SELECT 
    mes_ano,
    gap_receita,
    gap_leads,
    risco_meta,
    receita_necessaria_diaria,
    leads_necessarios_diarios,
    win_rate_necessario,
    ticket_medio_necessario,
    alertas,
    acoes_recomendadas,
    created_date
FROM forecast_gaps 
WHERE created_date >= '{data_inicio.date()}'
ORDER BY created_date DESC
LIMIT 1
"""

gaps_df = run_query(gaps_query)



# Métricas principais do Módulo 6
col1, col2, col3, col4 = st.columns(4)

if not forecast_df.empty:
    # Extrair métricas do forecast integrado
    previsao_leads = forecast_df['previsao_leads'].iloc[0] if not forecast_df.empty else 0
    previsao_receita = forecast_df['previsao_receita'].iloc[0] if not forecast_df.empty else 0
    meta_receita = forecast_df['meta_receita'].iloc[0] if not forecast_df.empty else 0
    previsao_win_rate = forecast_df['previsao_win_rate'].iloc[0] if not forecast_df.empty else 0
    
    with col1:
        st.metric("📈 Previsão Leads", f"{int(previsao_leads):,}", "próximos 30 dias")
    
    with col2:
        st.metric("💰 Previsão Receita", f"R$ {previsao_receita:,.0f}", "próximos 30 dias")
    
    with col3:
        st.metric("🎯 Meta Receita", f"R$ {meta_receita:,.0f}", f"+{((meta_receita/previsao_receita-1)*100):.0f}%" if previsao_receita > 0 else "")
    
    with col4:
        st.metric("📊 Win Rate Previsto", f"{previsao_win_rate:.1f}%", "taxa de conversão")

# Métricas de Gaps e Alertas
if not gaps_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    gap_receita = gaps_df['gap_receita'].iloc[0] if not gaps_df.empty else 0
    gap_leads = gaps_df['gap_leads'].iloc[0] if not gaps_df.empty else 0
    risco_meta = gaps_df['risco_meta'].iloc[0] if not gaps_df.empty else 'N/A'
    receita_necessaria_diaria = gaps_df['receita_necessaria_diaria'].iloc[0] if not gaps_df.empty else 0
    
    with col1:
        st.metric("⚠️ Gap de Receita", f"R$ {gap_receita:,.0f}", "meta vs previsão")
    
    with col2:
        st.metric("📉 Gap de Leads", f"{int(gap_leads):,}", "meta vs previsão")
    
    with col3:
        st.metric("🚨 Risco da Meta", risco_meta, "nível de risco")
    
    with col4:
        st.metric("💡 Receita/Dia Necessária", f"R$ {receita_necessaria_diaria:,.0f}", "para atingir meta")

# Gráfico de Forecast: Previsto vs Realizado
st.subheader("📊 Forecast: Previsto vs Realizado")

if not forecast_df.empty and not gaps_df.empty:
    # Criar gráfico de comparação
    fig_forecast = go.Figure()
    
    # Dados para o gráfico
    categorias = ['Meta', 'Previsão', 'Gap']
    valores = [
        forecast_df['meta_receita'].iloc[0],
        forecast_df['previsao_receita'].iloc[0],
        gaps_df['gap_receita'].iloc[0]
    ]
    cores = ['#2E8B57', '#FF6B6B', '#FFA500']
    
    fig_forecast.add_trace(go.Bar(
        x=categorias,
        y=valores,
        marker_color=cores,
        text=[f'R$ {v:,.0f}' for v in valores],
        textposition='auto',
        name='Receita (R$)'
    ))
    
    fig_forecast.update_layout(
        title="💰 Meta vs Previsão vs Gap de Receita",
        xaxis_title="Categorias",
        yaxis_title="Valor (R$)",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    # Métricas de performance
    col1, col2, col3 = st.columns(3)
    
    with col1:
        percentual_atingimento = (forecast_df['previsao_receita'].iloc[0] / forecast_df['meta_receita'].iloc[0]) * 100
        st.metric(
            "📈 Percentual de Atingimento",
            f"{percentual_atingimento:.1f}%",
            f"Meta: R$ {forecast_df['meta_receita'].iloc[0]:,.0f}"
        )
    
    with col2:
        st.metric(
            "⚠️ Gap de Receita",
            f"R$ {gaps_df['gap_receita'].iloc[0]:,.0f}",
            "Valor necessário para atingir meta"
        )
    
    with col3:
        st.metric(
            "💡 Receita/Dia Necessária",
            f"R$ {gaps_df['receita_necessaria_diaria'].iloc[0]:,.0f}",
            "Para atingir a meta"
        )

# Análise de Previsão vs Meta
st.subheader("📊 Análise: Previsão vs Meta")

if not forecast_df.empty and not gaps_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        # Comparação de receita
        previsao_receita = forecast_df['previsao_receita'].iloc[0] if not forecast_df.empty else 0
        meta_receita = forecast_df['meta_receita'].iloc[0] if not forecast_df.empty else 0
        gap_receita = gaps_df['gap_receita'].iloc[0] if not gaps_df.empty else 0
        
        if previsao_receita > 0 and meta_receita > 0:
            percentual_atingimento = (previsao_receita / meta_receita) * 100
            st.metric(
                "💰 Receita: Previsão vs Meta",
                f"R$ {previsao_receita:,.0f}",
                f"{percentual_atingimento:.1f}% da meta"
            )
            
            if gap_receita > 0:
                st.warning(f"⚠️ Gap: R$ {gap_receita:,.0f} abaixo da meta")
            else:
                st.success("✅ Meta será superada!")
    
    with col2:
        # Comparação de leads
        previsao_leads = forecast_df['previsao_leads'].iloc[0] if not forecast_df.empty else 0
        gap_leads = gaps_df['gap_leads'].iloc[0] if not gaps_df.empty else 0
        
        if previsao_leads > 0:
            st.metric(
                "📈 Leads: Previsão",
                f"{int(previsao_leads):,}",
                "próximos 30 dias"
            )
            
            if gap_leads > 0:
                st.warning(f"⚠️ Gap: {int(gap_leads):,} leads abaixo da meta")
            else:
                st.success("✅ Meta de leads será atingida!")

# Resumo Executivo do Forecast
st.subheader("📋 Resumo Executivo")

if not forecast_df.empty and not gaps_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"**Mês:** {forecast_df['mes_ano'].iloc[0]}")
    
    with col2:
        st.info(f"**Win Rate Previsto:** {forecast_df['previsao_win_rate'].iloc[0]:.1f}%")
    
    with col3:
        st.info(f"**Ticket Médio Previsto:** R$ {forecast_df['previsao_ticket_medio'].iloc[0]:,.0f}")
    
    with col4:
        risco_meta = gaps_df['risco_meta'].iloc[0] if not gaps_df.empty else 'N/A'
        if risco_meta == 'ALTO':
            st.error(f"**Risco:** {risco_meta}")
        elif risco_meta == 'MÉDIO':
            st.warning(f"**Risco:** {risco_meta}")
        else:
            st.success(f"**Risco:** {risco_meta}")

# Resumo Executivo do Mês
st.subheader("📋 Resumo Executivo do Mês")

if not forecast_df.empty and not gaps_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
st.subheader("🚨 Alertas Automáticos")

if not gaps_df.empty:
    alertas = []
    acoes_recomendadas = []
    
