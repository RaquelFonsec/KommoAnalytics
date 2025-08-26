#!/bin/bash
# Script de início rápido para configurar automação completa
# Executa todos os passos necessários para automação

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"

echo "🚀 ======== KOMMO ANALYTICS - CONFIGURAÇÃO DE AUTOMAÇÃO ========"
echo "📍 Projeto: $PROJECT_DIR"
echo "⏰ Data: $(date '+%d/%m/%Y às %H:%M:%S')"
echo ""

# Tornar todos os scripts executáveis
echo "🔧 Tornando scripts executáveis..."
chmod +x "$PROJECT_DIR/AUTOMATION"/*.sh

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p "$PROJECT_DIR/LOGS"
# mkdir -p "$PROJECT_DIR/REPORTS"  # Removido - não mais necessário

# Verificar saúde do sistema
echo "🔍 Verificando saúde do sistema..."
if "$PROJECT_DIR/AUTOMATION/health_check.sh"; then
    echo "✅ Sistema saudável!"
else
    echo "⚠️ Problemas detectados - verificar logs"
fi

echo ""
echo "📋 ======== CONFIGURANDO AUTOMAÇÃO ========"

# Configurar cron
"$PROJECT_DIR/AUTOMATION/setup_cron.sh"

echo ""
echo "🧪 ======== TESTE INICIAL ========"
echo "Executando um ciclo completo de ETL para teste..."

# Executar ETLs uma vez para testar
if "$PROJECT_DIR/AUTOMATION/run_all_etls.sh"; then
    echo "✅ Teste de ETL concluído com sucesso!"
else
    echo "⚠️ Problemas no teste de ETL - verificar logs"
fi

echo ""
echo "📊 ======== CONFIGURAÇÃO CONCLUÍDA ========"
echo ""
echo "✅ AUTOMAÇÃO CONFIGURADA COM SUCESSO!"
echo ""
echo "📋 CRONOGRAMA ATIVO:"
echo "   🕕 ETLs: A cada 6 horas (00:00, 06:00, 12:00, 18:00)"
echo "   🌅 Relatórios: Diariamente às 06:00"
echo "   🔍 Health Check: Disponível sob demanda"
echo ""
echo "📁 ARQUIVOS IMPORTANTES:"
echo "   📊 Dashboard: http://localhost:8501"
echo "   📋 Logs: $PROJECT_DIR/LOGS/"
echo "   📈 Relatórios: Removido (não mais necessário)"
echo ""
echo "🛠️ COMANDOS ÚTEIS:"
echo "   📋 Ver cron: crontab -l"
echo "   🧪 Testar ETL: $PROJECT_DIR/AUTOMATION/run_all_etls.sh"
echo "   🔍 Health Check: $PROJECT_DIR/AUTOMATION/health_check.sh"
echo "   📊 Relatório: $PROJECT_DIR/AUTOMATION/daily_report.sh"
echo ""
echo "🎉 O sistema está agora totalmente automatizado!"
echo "Os dados do dashboard serão atualizados automaticamente a cada 6 horas."
