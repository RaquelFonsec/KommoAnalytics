#!/bin/bash
# Script para configurar automação via cron
# Executa ETLs a cada 6 horas automaticamente

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
ETL_SCRIPT="$PROJECT_DIR/AUTOMATION/run_all_etls.sh"

echo "🔧 Configurando automação do Kommo Analytics..."

# Tornar script executável
chmod +x "$ETL_SCRIPT"

# Backup do crontab atual
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "# Novo crontab" > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt

# Verificar se já existe entrada para o projeto
if crontab -l 2>/dev/null | grep -q "KommoAnalytics"; then
    echo "⚠️ Automação já configurada. Removendo entrada antiga..."
    crontab -l 2>/dev/null | grep -v "KommoAnalytics" | crontab -
fi

# Adicionar nova entrada do cron
(crontab -l 2>/dev/null; echo "# KommoAnalytics - ETL automático diário às 6h") | crontab -
(crontab -l 2>/dev/null; echo "0 6 * * * $ETL_SCRIPT >> $PROJECT_DIR/LOGS/cron_etl.log 2>&1") | crontab -

echo "✅ Automação configurada com sucesso!"
echo ""
echo "📋 CRONOGRAMA CONFIGURADO:"
echo "   🌅 Diariamente às 6h: Execução completa de todos ETLs"
echo ""
echo "📊 PRÓXIMAS EXECUÇÕES:"
echo "   $(date -d 'tomorrow 6:00' '+%H:00 - %d/%m/%Y')"
echo "   $(date -d '+2 days 6:00' '+%H:00 - %d/%m/%Y')"
echo "   $(date -d '+3 days 6:00' '+%H:00 - %d/%m/%Y')"
echo ""
echo "📁 LOGS EM: $PROJECT_DIR/LOGS/"
echo "🔧 CONFIGURAÇÃO: crontab -l"
echo ""
echo "🚀 Para testar agora: $ETL_SCRIPT"
