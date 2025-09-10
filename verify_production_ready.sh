#!/bin/bash

# Script de Verificação - Kommo Analytics Production Ready
# Verifica se todos os arquivos essenciais estão presentes e funcionais

echo "🔍 VERIFICAÇÃO DE PRODUÇÃO - Kommo Analytics"
echo "=============================================="

# Contador de verificações
total_checks=0
passed_checks=0

# Função para verificar arquivo
check_file() {
    local file="$1"
    local description="$2"
    ((total_checks++))
    
    if [ -f "$file" ]; then
        echo "✅ $description: $file"
        ((passed_checks++))
    else
        echo "❌ $description: $file - FALTANDO!"
    fi
}

# Função para verificar diretório
check_dir() {
    local dir="$1"
    local description="$2"
    ((total_checks++))
    
    if [ -d "$dir" ]; then
        echo "✅ $description: $dir"
        ((passed_checks++))
    else
        echo "❌ $description: $dir - FALTANDO!"
    fi
}

echo ""
echo "📁 VERIFICANDO ESTRUTURA DE ARQUIVOS:"
echo "------------------------------------"

# Arquivos essenciais do Docker
check_file "Dockerfile" "Dockerfile"
check_file "docker-compose.prod.yml" "Docker Compose Produção"
check_file "docker-entrypoint.sh" "Script de Inicialização"
check_file "requirements.txt" "Dependências Python"
check_file "nginx.conf" "Configuração Nginx"

# Arquivos de configuração
check_file "env.prod.example" "Exemplo de Configuração"
check_file "deploy_digital_ocean.sh" "Script de Deploy"

# Aplicação principal
check_file "DASHBOARD/main_app.py" "Aplicação Principal Streamlit"

# Scripts de automação essenciais
check_file "AUTOMATION/run_all_etls.sh" "Script Principal ETL"
check_file "AUTOMATION/backup_database.sh" "Script de Backup"
check_file "AUTOMATION/setup_cron.sh" "Configuração Cron"
check_file "AUTOMATION/health_check.sh" "Health Check"
check_file "AUTOMATION/guarantee_daily_updates.py" "Monitor Diário"

# ETLs
check_file "ETL/kommo_etl_modulo1_leads.py" "ETL Módulo 1 - Leads"
check_file "ETL/kommo_etl_modulo2_funil.py" "ETL Módulo 2 - Funil"
check_file "ETL/kommo_etl_modulo3_atividades.py" "ETL Módulo 3 - Atividades"
check_file "ETL/kommo_etl_modulo4_conversao.py" "ETL Módulo 4 - Conversão"
check_file "ETL/kommo_etl_modulo5_performance.py" "ETL Módulo 5 - Performance"
check_file "ETL/kommo_etl_modulo6_forecast_integrado.py" "ETL Módulo 6 - Forecast"

# Diretórios essenciais
check_dir "LOGS" "Diretório de Logs"
check_dir "BACKUP" "Diretório de Backups"
check_dir "ETL" "Diretório ETL"
check_dir "AUTOMATION" "Diretório Automação"
check_dir "DASHBOARD" "Diretório Dashboard"

echo ""
echo "🔧 VERIFICANDO CONFIGURAÇÕES:"
echo "-----------------------------"

# Verificar se os scripts têm permissão de execução
((total_checks++))
if [ -x "deploy_digital_ocean.sh" ]; then
    echo "✅ Script de deploy executável"
    ((passed_checks++))
else
    echo "❌ Script de deploy não executável"
fi

((total_checks++))
if [ -x "AUTOMATION/run_all_etls.sh" ]; then
    echo "✅ Script ETL executável"
    ((passed_checks++))
else
    echo "❌ Script ETL não executável"
fi

# Verificar se o Dockerfile tem as configurações corretas
((total_checks++))
if grep -q "FROM python:3.12-slim" Dockerfile; then
    echo "✅ Dockerfile usa Python 3.12"
    ((passed_checks++))
else
    echo "❌ Dockerfile não usa Python 3.12"
fi

((total_checks++))
if grep -q "EXPOSE 8501" Dockerfile; then
    echo "✅ Dockerfile expõe porta 8501"
    ((passed_checks++))
else
    echo "❌ Dockerfile não expõe porta 8501"
fi

echo ""
echo "📊 RESULTADO DA VERIFICAÇÃO:"
echo "============================"
echo "Verificações passaram: $passed_checks/$total_checks"

if [ $passed_checks -eq $total_checks ]; then
    echo "🎉 SUCESSO! Projeto está pronto para produção!"
    echo ""
    echo "📋 PRÓXIMOS PASSOS:"
    echo "1. Configure o arquivo .env com suas credenciais"
    echo "2. Execute: ./deploy_digital_ocean.sh"
    echo "3. Acesse: http://seu-ip:8501"
    exit 0
else
    echo "⚠️ ATENÇÃO! Alguns arquivos estão faltando ou com problemas."
    echo "Corrija os problemas antes de fazer o deploy."
    exit 1
fi
