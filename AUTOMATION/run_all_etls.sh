#!/bin/bash
# Script para executar todos os ETLs automaticamente
# Autor: Sistema de Automação Kommo Analytics
# Data: 2025-09-12

# Configurações
PROJECT_DIR="/app"
LOG_DIR="$PROJECT_DIR/LOGS"
ETL_DIR="$PROJECT_DIR/ETL"

# Criar diretório de logs se não existir
mkdir -p "$LOG_DIR"

# Função para log com timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/etl_automation.log"
}

# Função para executar ETL com tratamento de erro
run_etl() {
    local etl_name="$1"
    local etl_file="$2"
    
    log_with_timestamp " Iniciando $etl_name..."
    
    cd "$ETL_DIR"
    
    if python3 "$etl_file" >> "$LOG_DIR/${etl_name,,}_$(date +%Y%m%d).log" 2>&1; then
        log_with_timestamp " $etl_name concluído com sucesso"
        return 0
    else
        log_with_timestamp " Erro no $etl_name - verificar logs"
        return 1
    fi
}

# Início da execução
log_with_timestamp "🔄 ======== INICIANDO AUTOMAÇÃO DE ETLs ========"
log_with_timestamp "📊 Projeto: Kommo Analytics"
log_with_timestamp "📍 Diretório: $PROJECT_DIR"

# Contador de sucessos
success_count=0
total_etls=6

# Módulo 1: Entrada e Origem de Leads
if run_etl "Módulo 1 - Leads" "kommo_etl_modulo1_leads.py"; then
    ((success_count++))
fi

# Aguardar 30 segundos entre ETLs para não sobrecarregar
sleep 30

# Módulo 2: Funil de Vendas
if run_etl "Módulo 2 - Funil" "kommo_etl_modulo2_funil.py"; then
    ((success_count++))
fi

sleep 30

# Módulo 3: Atividades Comerciais
if run_etl "Módulo 3 - Atividades" "kommo_etl_modulo3_atividades.py"; then
    ((success_count++))
fi

sleep 30

# Módulo 4: Conversão e Receita
if run_etl "Módulo 4 - Conversão" "kommo_etl_modulo4_conversao.py"; then
    ((success_count++))
fi

sleep 30

# Módulo 5: Performance por Pessoa e Canal
if run_etl "Módulo 5 - Performance" "kommo_etl_modulo5_performance.py"; then
    ((success_count++))
fi

sleep 30

# Módulo 6: Previsibilidade (Forecast)
if run_etl "Módulo 6 - Forecast" "kommo_etl_modulo6_forecast_integrado.py"; then
    ((success_count++))
fi

# Resumo da execução
log_with_timestamp "📊 ======== RESUMO DA EXECUÇÃO ========"
log_with_timestamp "✅ ETLs bem-sucedidos: $success_count/$total_etls"
log_with_timestamp "⏰ Próxima execução em 6 horas"

if [ $success_count -eq $total_etls ]; then
    log_with_timestamp "🎉 Todos os ETLs executados com sucesso!"
    echo "SUCCESS: $success_count/$total_etls" > "$LOG_DIR/last_execution_status.txt"
else
    log_with_timestamp "⚠️ Alguns ETLs falharam - verificar logs individuais"
    echo "PARTIAL: $success_count/$total_etls" > "$LOG_DIR/last_execution_status.txt"
fi

log_with_timestamp "🔄 ======== AUTOMAÇÃO CONCLUÍDA ========"

# Limpar logs antigos (manter apenas últimos 7 dias)
find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete

# Enviar notificação (opcional)
# curl -X POST "https://seu-webhook.com/notificacao" -d "ETLs executados: $success_count/$total_etls"

