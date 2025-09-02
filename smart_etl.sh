#!/bin/bash
# Script Smart ETL - Verifica se há solicitação e executa ETLs automaticamente
# Autor: Sistema de Automação Kommo Analytics
# Data: $(date)

# Configurações
PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
FLAG_FILE="/tmp/kommo_etl_requested.flag"
LOG_DIR="$PROJECT_DIR/LOGS"
VENV_PATH="$PROJECT_DIR/dashboard_env"

# Criar diretório de logs se não existir
mkdir -p "$LOG_DIR"

# Função para log com timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/smart_etl.log"
}

# Verificar se há solicitação de ETL
check_etl_request() {
    if [ -f "$FLAG_FILE" ]; then
        log_with_timestamp "🚨 Solicitação de ETL detectada!"
        return 0
    else
        log_with_timestamp "✅ Nenhuma solicitação de ETL pendente"
        return 1
    fi
}

# Executar ETLs
run_etls() {
    log_with_timestamp "🔄 Iniciando execução dos ETLs..."
    
    # Executar script de ETLs
    cd "$PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    
    if bash AUTOMATION/run_all_etls.sh; then
        log_with_timestamp "✅ ETLs executados com sucesso"
        return 0
    else
        log_with_timestamp "❌ Erro na execução dos ETLs"
        return 1
    fi
}

# Limpar flag após execução
cleanup_flag() {
    if [ -f "$FLAG_FILE" ]; then
        rm "$FLAG_FILE"
        log_with_timestamp "🧹 Flag de solicitação removida"
    fi
}

# Função principal
main() {
    log_with_timestamp "🔍 Verificando solicitações de ETL..."
    
    if check_etl_request; then
        log_with_timestamp "🚀 Executando ETLs solicitados..."
        
        if run_etls; then
            log_with_timestamp "🎉 ETLs concluídos com sucesso!"
            cleanup_flag
            exit 0
        else
            log_with_timestamp "⚠️ ETLs falharam - flag mantida para retry"
            exit 1
        fi
    else
        log_with_timestamp "💤 Nenhuma ação necessária"
        exit 0
    fi
}

# Executar função principal
main
