#!/bin/bash
# Script para monitorar e reiniciar o dashboard Streamlit automaticamente
# Verifica se o dashboard está rodando e reinicia se necessário

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
LOG_DIR="$PROJECT_DIR/LOGS"
VENV_PATH="$PROJECT_DIR/dashboard_env"
DASHBOARD_URL="http://localhost:8501"

# Função para log
monitor_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/dashboard_monitor.log"
}

# Função para verificar se o dashboard está rodando
check_dashboard() {
    if curl -s --max-time 10 "$DASHBOARD_URL" > /dev/null 2>&1; then
        return 0  # Dashboard está rodando
    else
        return 1  # Dashboard não está respondendo
    fi
}

# Função para iniciar o dashboard
start_dashboard() {
    monitor_log "🚀 Iniciando dashboard Streamlit..."
    
    cd "$PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Matar processos existentes do streamlit
    pkill -f "streamlit run" 2>/dev/null || true
    sleep 3
    
    # Iniciar novo processo em background
    nohup streamlit run DASHBOARD/main_app.py \
        --server.address=0.0.0.0 \
        --server.port=8501 \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        >> "$LOG_DIR/streamlit_output.log" 2>&1 &
    
    # Aguardar alguns segundos para o dashboard inicializar
    sleep 10
    
    if check_dashboard; then
        monitor_log "✅ Dashboard iniciado com sucesso"
        return 0
    else
        monitor_log "❌ Falha ao iniciar dashboard"
        return 1
    fi
}

# Verificação principal
monitor_log "🔍 Verificando status do dashboard..."

if check_dashboard; then
    monitor_log "✅ Dashboard está funcionando normalmente"
    exit 0
else
    monitor_log "⚠️ Dashboard não está respondendo - tentando reiniciar..."
    
    # Tentar reiniciar até 3 vezes
    for attempt in 1 2 3; do
        monitor_log "🔄 Tentativa $attempt de reinicialização..."
        
        if start_dashboard; then
            monitor_log "🎉 Dashboard reiniciado com sucesso na tentativa $attempt"
            exit 0
        else
            monitor_log "❌ Falha na tentativa $attempt"
            sleep 15
        fi
    done
    
    monitor_log "🚨 CRÍTICO: Não foi possível reiniciar o dashboard após 3 tentativas"
    exit 1
fi


