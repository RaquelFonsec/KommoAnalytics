#!/bin/bash
# Script de monitoramento de saúde do sistema
# Verifica se todos os componentes estão funcionando

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
LOG_DIR="$PROJECT_DIR/LOGS"

# Função para log
health_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/health_check.log"
}

# Função para verificar status
check_status() {
    local component="$1"
    local check_command="$2"
    
    if eval "$check_command" >/dev/null 2>&1; then
        health_log "✅ $component: OK"
        return 0
    else
        health_log "❌ $component: FALHA"
        return 1
    fi
}

health_log "🔍 ======== VERIFICAÇÃO DE SAÚDE DO SISTEMA ========"

# Verificar conexão com banco
check_status "Conexão MySQL" "mysql -u kommo_analytics -pprevidas_ltda_2025 -e 'SELECT 1;'"

# Verificar se as tabelas principais existem
tables=("leads_metrics" "sales_metrics" "performance_vendedores" "performance_canais")
for table in "${tables[@]}"; do
    check_status "Tabela $table" "mysql -u kommo_analytics -pprevidas_ltda_2025 kommo_analytics -e 'SELECT COUNT(*) FROM $table LIMIT 1;'"
done

# Verificar se o ambiente virtual existe
check_status "Ambiente Virtual" "test -d $PROJECT_DIR/dashboard_env"

# Verificar se o Streamlit está rodando
check_status "Streamlit Dashboard" "curl -s http://localhost:8501 > /dev/null"

# Verificar se os scripts ETL existem
etl_scripts=("kommo_etl_modulo1_leads.py" "kommo_etl_modulo2_funil.py" "kommo_etl_modulo3_atividades.py" "kommo_etl_modulo4_conversao.py" "kommo_etl_modulo5_performance.py" "kommo_etl_modulo6_forecasting.py")
for script in "${etl_scripts[@]}"; do
    check_status "Script $script" "test -f $PROJECT_DIR/ETL/$script"
done

# Verificar espaço em disco
disk_usage=$(df "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    health_log "✅ Espaço em disco: ${disk_usage}% usado"
else
    health_log "⚠️ Espaço em disco: ${disk_usage}% usado (ATENÇÃO!)"
fi

# Verificar arquivo .env
check_status "Arquivo .env" "test -f $PROJECT_DIR/.env && grep -q 'KOMMO_ACCESS_TOKEN' $PROJECT_DIR/.env"

# Verificar última execução dos ETLs
if [ -f "$LOG_DIR/last_execution_status.txt" ]; then
    last_status=$(cat "$LOG_DIR/last_execution_status.txt")
    if [[ "$last_status" == "SUCCESS"* ]]; then
        health_log "✅ Última execução ETL: $last_status"
    else
        health_log "⚠️ Última execução ETL: $last_status"
    fi
else
    health_log "⚠️ Nenhuma execução ETL registrada"
fi

# Verificar logs de erro recentes
error_count=$(find "$LOG_DIR" -name "*.log" -type f -mtime -1 -exec grep -l "ERROR\|ERRO\|❌" {} \; | wc -l)
if [ "$error_count" -eq 0 ]; then
    health_log "✅ Sem erros nas últimas 24h"
else
    health_log "⚠️ $error_count arquivos com erros nas últimas 24h"
fi

health_log "🔍 ======== VERIFICAÇÃO CONCLUÍDA ========"

# Retornar código de saída baseado na saúde geral
if [ "$error_count" -gt 0 ] || [ "$disk_usage" -gt 90 ]; then
    exit 1
else
    exit 0
fi


