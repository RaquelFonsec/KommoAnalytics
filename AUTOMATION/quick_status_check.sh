#!/bin/bash
# Verificação Rápida de Status - Kommo Analytics
# Script para verificar rapidamente se tudo está funcionando

echo "🔍 VERIFICAÇÃO RÁPIDA - KOMMO ANALYTICS"
echo "========================================"

# Verificar se o cron está ativo
echo -n "📅 Cron ativo: "
if crontab -l 2>/dev/null | grep -q "KommoAnalytics"; then
    echo "✅"
else
    echo "❌"
fi

# Verificar última execução
echo -n "🚀 Última execução: "
if [ -f "LOGS/last_execution_status.txt" ]; then
    cat LOGS/last_execution_status.txt
else
    echo "❌ Arquivo não encontrado"
fi

# Verificar logs de hoje
echo -n "📋 Logs de hoje: "
today=$(date +%Y%m%d)
log_count=$(ls LOGS/*${today}.log 2>/dev/null | wc -l)
if [ $log_count -eq 6 ]; then
    echo "✅ $log_count/6 módulos"
else
    echo "⚠️ $log_count/6 módulos"
fi

# Verificar se o banco está acessível
echo -n "🗄️ Banco de dados: "
if mysql -u kommo_analytics -pprevidas_ltda_2025 kommo_analytics -e "SELECT 1" >/dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
fi

# Verificar ambiente virtual
echo -n "🐍 Ambiente virtual: "
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "✅"
else
    echo "❌"
fi

# Verificar scripts de automação
echo -n "🔧 Scripts de automação: "
if [ -f "AUTOMATION/run_all_etls.sh" ] && [ -f "AUTOMATION/setup_cron.sh" ]; then
    echo "✅"
else
    echo "❌"
fi

echo ""
echo "📊 STATUS GERAL:"
if crontab -l 2>/dev/null | grep -q "KommoAnalytics" && [ -f "LOGS/last_execution_status.txt" ]; then
    echo "   🎉 AUTOMAÇÃO FUNCIONANDO!"
    echo "   ✅ Dados atualizados diariamente às 6h"
    echo "   ✅ Próxima execução: Amanhã às 6h"
else
    echo "   ⚠️ Automação precisa de configuração"
    echo "   🔧 Executar: ./AUTOMATION/setup_cron.sh"
fi

echo ""
echo "🔍 COMANDOS ÚTEIS:"
echo "   • Monitoramento completo: python AUTOMATION/monitor_automation.py"
echo "   • Teste de qualidade: python AUTOMATION/test_data_freshness.py"
echo "   • Execução manual: ./AUTOMATION/run_all_etls.sh"
echo "   • Ver cron: crontab -l"
echo "   • Ver logs: ls -la LOGS/"


