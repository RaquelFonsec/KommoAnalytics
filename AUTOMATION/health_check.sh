#!/bin/bash
# Script de Health Check para Kommo Analytics
# Verifica saúde completa do sistema

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
LOG_DIR="$PROJECT_DIR/LOGS"
VENV_PATH="$PROJECT_DIR/dashboard_env"

# Função para log com timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/health_check.log"
}

# Função para verificar se processo está rodando
check_process() {
    local process_name="$1"
    local pattern="$2"
    
    if pgrep -f "$pattern" > /dev/null; then
        echo "✅ $process_name está rodando"
        return 0
    else
        echo "❌ $process_name não está rodando"
        return 1
    fi
}

# Função para verificar espaço em disco
check_disk_space() {
    local usage=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$usage" -lt 80 ]; then
        echo "✅ Espaço em disco: ${usage}% (OK)"
        return 0
    else
        echo "⚠️ Espaço em disco: ${usage}% (CRÍTICO)"
        return 1
    fi
}

# Função para verificar memória
check_memory() {
    local usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$usage" -lt 85 ]; then
        echo "✅ Uso de memória: ${usage}% (OK)"
        return 0
    else
        echo "⚠️ Uso de memória: ${usage}% (ALTO)"
        return 1
    fi
}

# Função para verificar conectividade com banco
check_database() {
    cd "$PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    
    if python3 -c "
import mysql.connector
from dotenv import load_dotenv
import os
load_dotenv('env_template.txt')
try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    conn.close()
    print('✅ Conexão com banco OK')
    exit(0)
except Exception as e:
    print(f'❌ Erro na conexão: {e}')
    exit(1)
" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Função para verificar logs de erro
check_error_logs() {
    local error_count=0
    
    # Verificar logs dos últimos 24h
    if [ -f "$LOG_DIR/etl_automation.log" ]; then
        local etl_errors=$(grep -c "ERROR\|❌" "$LOG_DIR/etl_automation.log" 2>/dev/null || echo "0")
        if [ "$etl_errors" -gt 0 ]; then
            echo "⚠️ $etl_errors erros nos logs ETL"
            ((error_count++))
        fi
    fi
    
    if [ -f "$LOG_DIR/backup.log" ]; then
        local backup_errors=$(grep -c "ERROR\|❌" "$LOG_DIR/backup.log" 2>/dev/null || echo "0")
        if [ "$backup_errors" -gt 0 ]; then
            echo "⚠️ $backup_errors erros nos logs de backup"
            ((error_count++))
        fi
    fi
    
    if [ $error_count -eq 0 ]; then
        echo "✅ Logs sem erros críticos"
        return 0
    else
        return 1
    fi
}

# Função para verificar cron jobs
check_cron_jobs() {
    if crontab -l 2>/dev/null | grep -q "KommoAnalytics"; then
        echo "✅ Cron jobs configurados"
        return 0
    else
        echo "❌ Cron jobs não configurados"
        return 1
    fi
}

# Função para verificar última execução dos ETLs
check_last_etl_execution() {
    local last_execution=$(find "$LOG_DIR" -name "etl_automation.log" -exec tail -1 {} \; 2>/dev/null | grep -o "2025-[0-9][0-9]-[0-9][0-9]" | tail -1)
    
    if [ -n "$last_execution" ]; then
        local today=$(date +%Y-%m-%d)
        if [ "$last_execution" = "$today" ]; then
            echo "✅ ETLs executados hoje"
            return 0
        else
            echo "⚠️ Última execução ETL: $last_execution"
            return 1
        fi
    else
        echo "❌ Nenhuma execução ETL encontrada"
        return 1
    fi
}

# Função principal
main() {
    log_with_timestamp "🔍 === INICIANDO HEALTH CHECK COMPLETO ==="
    
    local total_checks=0
    local passed_checks=0
    
    echo ""
    echo "📊 VERIFICAÇÕES DE SAÚDE:"
    echo "=========================="
    
    # Verificar processos
    echo ""
    echo "🖥️ PROCESSOS:"
    check_process "Streamlit Dashboard" "streamlit.*main_app.py" && ((passed_checks++)) || true
    ((total_checks++))
    
    # Verificar recursos do sistema
    echo ""
    echo "💾 RECURSOS:"
    check_disk_space && ((passed_checks++)) || true
    ((total_checks++))
    check_memory && ((passed_checks++)) || true
    ((total_checks++))
    
    # Verificar conectividade
    echo ""
    echo "🌐 CONECTIVIDADE:"
    check_database && ((passed_checks++)) || true
    ((total_checks++))
    
    # Verificar configuração
    echo ""
    echo "⚙️ CONFIGURAÇÃO:"
    check_cron_jobs && ((passed_checks++)) || true
    ((total_checks++))
    check_last_etl_execution && ((passed_checks++)) || true
    ((total_checks++))
    
    # Verificar logs
    echo ""
    echo "📋 LOGS:"
    check_error_logs && ((passed_checks++)) || true
    ((total_checks++))
    
    # Resumo
    echo ""
    echo "📊 RESUMO:"
    echo "=========="
    echo "✅ Checks aprovados: $passed_checks/$total_checks"
    
    if [ $passed_checks -eq $total_checks ]; then
        echo "🎉 SISTEMA TOTALMENTE SAUDÁVEL!"
        log_with_timestamp "✅ Health check: SISTEMA SAUDÁVEL ($passed_checks/$total_checks)"
        echo "HEALTHY: $passed_checks/$total_checks" > "$LOG_DIR/health_status.txt"
        exit 0
    else
        echo "⚠️ ALGUNS PROBLEMAS IDENTIFICADOS"
        log_with_timestamp "⚠️ Health check: PROBLEMAS DETECTADOS ($passed_checks/$total_checks)"
        echo "ISSUES: $passed_checks/$total_checks" > "$LOG_DIR/health_status.txt"
        exit 1
    fi
}

# Executar health check
main


