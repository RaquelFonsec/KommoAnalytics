#!/bin/bash
# Script de limpeza do projeto Kommo Analytics
# Remove arquivos desnecessários, duplicados e temporários

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
LOG_FILE="$PROJECT_DIR/LOGS/cleanup_$(date +%Y%m%d_%H%M%S).log"

# Função para log
cleanup_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Função para remover arquivo com confirmação
safe_remove() {
    local file="$1"
    local reason="$2"
    
    if [ -f "$file" ]; then
        cleanup_log "🗑️ Removendo: $file ($reason)"
        rm -f "$file"
        return 0
    else
        cleanup_log "❓ Arquivo não encontrado: $file"
        return 1
    fi
}

# Função para remover diretório com confirmação
safe_remove_dir() {
    local dir="$1"
    local reason="$2"
    
    if [ -d "$dir" ]; then
        cleanup_log "🗑️ Removendo diretório: $dir ($reason)"
        rm -rf "$dir"
        return 0
    else
        cleanup_log "❓ Diretório não encontrado: $dir"
        return 1
    fi
}

cleanup_log "🧹 ======== INICIANDO LIMPEZA DO PROJETO ========"
cleanup_log "📍 Projeto: $PROJECT_DIR"

# Contador de arquivos removidos
removed_count=0

# 1. REMOVER ETLs DUPLICADOS/OBSOLETOS
cleanup_log "📂 === LIMPANDO ETLs DUPLICADOS ==="

# Módulo 3 - manter apenas o principal
safe_remove "$PROJECT_DIR/ETL/kommo_etl_modulo3_fixed.py" "versão obsoleta" && ((removed_count++))
safe_remove "$PROJECT_DIR/ETL/kommo_etl_modulo3_simple.py" "versão de teste" && ((removed_count++))

# Módulo 4 - manter apenas o principal
safe_remove "$PROJECT_DIR/ETL/kommo_etl_modulo4_conversao_receita.py" "versão duplicada" && ((removed_count++))

# Módulo 6 - manter apenas o forecasting (que cria tabelas)
safe_remove "$PROJECT_DIR/ETL/kommo_etl_modulo6_forecast.py" "versão alternativa" && ((removed_count++))

# 2. REMOVER SCRIPTS TEMPORÁRIOS
cleanup_log "📂 === REMOVENDO SCRIPTS TEMPORÁRIOS ==="

safe_remove "$PROJECT_DIR/extract_loss_reasons.py" "script temporário" && ((removed_count++))
safe_remove "$PROJECT_DIR/fix_loss_reasons.py" "script temporário" && ((removed_count++))
safe_remove "$PROJECT_DIR/fix_loss_reasons_v2.py" "script temporário" && ((removed_count++))
safe_remove "$PROJECT_DIR/get_token.py" "script temporário" && ((removed_count++))
safe_remove "$PROJECT_DIR/quick_auth.py" "script temporário" && ((removed_count++))

# 3. REMOVER ARQUIVOS DE CONFIGURAÇÃO DUPLICADOS
cleanup_log "📂 === REMOVENDO CONFIGURAÇÕES DUPLICADAS ==="

safe_remove "$PROJECT_DIR/setup_database.py" "duplicado em DATABASE/" && ((removed_count++))
safe_remove "$PROJECT_DIR/SETUP/requirements.txt" "duplicado na raiz" && ((removed_count++))

# 4. REMOVER ARQUIVOS SQL SOLTOS
cleanup_log "📂 === REMOVENDO ARQUIVOS SQL TEMPORÁRIOS ==="

safe_remove "$PROJECT_DIR/clean_leads_data.sql" "script temporário" && ((removed_count++))
safe_remove "$PROJECT_DIR/create_performance_tables.sql" "já incorporado nos ETLs" && ((removed_count++))

# 5. REMOVER AMBIENTE VIRTUAL ANTIGO
cleanup_log "📂 === REMOVENDO AMBIENTE VIRTUAL OBSOLETO ==="

if [ -d "$PROJECT_DIR/venv" ]; then
    cleanup_log "🗑️ Removendo ambiente virtual antigo: venv/ (substituído por dashboard_env/)"
    rm -rf "$PROJECT_DIR/venv"
    ((removed_count++))
fi

# 6. LIMPAR CACHE PYTHON
cleanup_log "📂 === LIMPANDO CACHE PYTHON ==="

find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null && cleanup_log "🗑️ Removidos diretórios __pycache__"
find "$PROJECT_DIR" -name "*.pyc" -type f -delete 2>/dev/null && cleanup_log "🗑️ Removidos arquivos .pyc"
find "$PROJECT_DIR" -name "*.pyo" -type f -delete 2>/dev/null && cleanup_log "🗑️ Removidos arquivos .pyo"

# 7. LIMPAR LOGS ANTIGOS (MAIS DE 30 DIAS)
cleanup_log "📂 === LIMPANDO LOGS ANTIGOS ==="

old_logs=$(find "$PROJECT_DIR/LOGS" -name "*.log" -type f -mtime +30 2>/dev/null | wc -l)
if [ "$old_logs" -gt 0 ]; then
    find "$PROJECT_DIR/LOGS" -name "*.log" -type f -mtime +30 -delete 2>/dev/null
    cleanup_log "🗑️ Removidos $old_logs logs antigos (>30 dias)"
fi

# 8. LIMPAR EXPORTS ANTIGOS
cleanup_log "📂 === LIMPANDO EXPORTS ANTIGOS ==="

old_exports=$(find "$PROJECT_DIR" -path "*/exports/*" -name "*.json" -type f -mtime +7 2>/dev/null | wc -l)
if [ "$old_exports" -gt 0 ]; then
    find "$PROJECT_DIR" -path "*/exports/*" -name "*.json" -type f -mtime +7 -delete 2>/dev/null
    cleanup_log "🗑️ Removidos $old_exports exports antigos (>7 dias)"
fi

# 9. REMOVER DIRETÓRIO SETUP VAZIO
if [ -d "$PROJECT_DIR/SETUP" ] && [ -z "$(ls -A "$PROJECT_DIR/SETUP")" ]; then
    safe_remove_dir "$PROJECT_DIR/SETUP" "diretório vazio" && ((removed_count++))
fi

# 10. REORGANIZAR ESTRUTURA - MOVER start_pipeline.sh PARA AUTOMATION
if [ -f "$PROJECT_DIR/start_pipeline.sh" ]; then
    cleanup_log "📦 Movendo start_pipeline.sh para AUTOMATION/"
    mv "$PROJECT_DIR/start_pipeline.sh" "$PROJECT_DIR/AUTOMATION/"
    chmod +x "$PROJECT_DIR/AUTOMATION/start_pipeline.sh"
fi

# 11. LIMPAR ARQUIVOS TEMPORÁRIOS DO SISTEMA
cleanup_log "📂 === LIMPANDO ARQUIVOS TEMPORÁRIOS ==="

# Remover arquivos de backup do vim/nano
find "$PROJECT_DIR" -name "*~" -type f -delete 2>/dev/null
find "$PROJECT_DIR" -name "*.swp" -type f -delete 2>/dev/null
find "$PROJECT_DIR" -name "*.swo" -type f -delete 2>/dev/null

# Remover arquivos .DS_Store (macOS)
find "$PROJECT_DIR" -name ".DS_Store" -type f -delete 2>/dev/null

# 12. VERIFICAR TAMANHO APÓS LIMPEZA
cleanup_log "📊 === CALCULANDO ESPAÇO LIBERADO ==="

project_size=$(du -sh "$PROJECT_DIR" 2>/dev/null | cut -f1)
cleanup_log "📏 Tamanho atual do projeto: $project_size"

# 13. GERAR ESTRUTURA FINAL LIMPA
cleanup_log "📋 === ESTRUTURA FINAL DO PROJETO ==="

cat > "$PROJECT_DIR/STRUCTURE.md" << 'EOF'
# KOMMO ANALYTICS - ESTRUTURA DO PROJETO

## 📁 Diretórios Principais

```
KommoAnalytics/
├── 🤖 AUTOMATION/          # Scripts de automação
│   ├── run_all_etls.sh     # Execução automática dos ETLs
│   ├── setup_cron.sh       # Configuração do cron
│   ├── daily_report.sh     # Relatório diário
│   ├── health_check.sh     # Verificação de saúde
│   ├── dashboard_monitor.sh # Monitor do dashboard
│   └── cleanup_project.sh  # Limpeza do projeto
│
├── 📊 DASHBOARD/           # Interface web Streamlit
│   └── main_app.py         # Aplicação principal
│
├── 🔄 ETL/                # Scripts de extração e transformação
│   ├── kommo_etl_modulo1_leads.py      # Módulo 1: Leads
│   ├── kommo_etl_modulo2_funil.py      # Módulo 2: Funil
│   ├── kommo_etl_modulo3_atividades.py # Módulo 3: Atividades
│   ├── kommo_etl_modulo4_conversao.py  # Módulo 4: Conversão
│   ├── kommo_etl_modulo5_performance.py # Módulo 5: Performance
│   ├── kommo_etl_modulo6_forecasting.py # Módulo 6: Forecast
│   ├── oauth_setup.py      # Configuração OAuth
│   └── exchange_auth_code.py # Troca de códigos
│
├── 🗄️ DATABASE/           # Scripts de banco de dados
│   └── setup_database.py  # Configuração inicial
│
├── 📁 DATA/               # Dados e exports
│   └── exports/           # Arquivos exportados
│
├── 📋 LOGS/               # Logs do sistema
├── 📈 REPORTS/            # Relatórios (removido)
├── 🐍 dashboard_env/      # Ambiente virtual Python
│
├── 📄 requirements.txt    # Dependências Python
├── 📄 README.md          # Documentação principal
└── 📄 .env               # Variáveis de ambiente
```

## 🎯 ETLs Ativos

1. **Módulo 1**: Entrada e Origem de Leads
2. **Módulo 2**: Funil de Vendas
3. **Módulo 3**: Atividades Comerciais
4. **Módulo 4**: Conversão e Receita
5. **Módulo 5**: Performance por Pessoa e Canal
6. **Módulo 6**: Previsibilidade (Forecast)

## ⚙️ Automação Configurada

- **ETLs**: A cada 6 horas
- **Dashboard**: Monitoramento a cada 15 minutos
- **Relatórios**: Diariamente às 06:00
- **Limpeza**: Automática (logs >7 dias, exports >7 dias)

## 🚀 Acesso

- **Dashboard**: http://localhost:8501
- **Logs**: ./LOGS/
- **Relatórios**: ./REPORTS/ (removido)
EOF

cleanup_log "📋 Estrutura documentada em: STRUCTURE.md"

# RESUMO FINAL
cleanup_log "🧹 ======== LIMPEZA CONCLUÍDA ========"
cleanup_log "🗑️ Arquivos removidos: $removed_count"
cleanup_log "📏 Tamanho atual: $project_size"
cleanup_log "📄 Log completo: $LOG_FILE"
cleanup_log "✅ Projeto organizado e otimizado!"

echo ""
echo "🎉 LIMPEZA CONCLUÍDA COM SUCESSO!"
echo "📊 $removed_count arquivos removidos"
echo "📏 Tamanho do projeto: $project_size"
echo "📋 Estrutura documentada em: STRUCTURE.md"
echo "📄 Log detalhado: $LOG_FILE"
