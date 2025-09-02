#!/bin/bash
# Script para configurar automação via cron
# Executa ETLs a cada 4 horas automaticamente

PROJECT_DIR="/home/raquel-fonseca/KommoAnalytics"
ETL_SCRIPT="$PROJECT_DIR/AUTOMATION/run_all_etls.sh"
MONITOR_SCRIPT="$PROJECT_DIR/AUTOMATION/monitor_daily_updates.py"
BACKUP_SCRIPT="$PROJECT_DIR/AUTOMATION/backup_database.sh"
HEALTH_SCRIPT="$PROJECT_DIR/AUTOMATION/health_check.sh"

echo " Configurando automação do Kommo Analytics..."

# Tornar scripts executáveis
chmod +x "$ETL_SCRIPT"
chmod +x "$MONITOR_SCRIPT"
chmod +x "$BACKUP_SCRIPT"
chmod +x "$HEALTH_SCRIPT"

# Backup do crontab atual
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "# Novo crontab" > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt

# Verificar se já existe entrada para o projeto
if crontab -l 2>/dev/null | grep -q "KommoAnalytics"; then
    echo " Automação já configurada. Removendo entrada antiga..."
    crontab -l 2>/dev/null | grep -v "KommoAnalytics" | crontab -
fi

# Adicionar novas entradas do cron
(crontab -l 2>/dev/null; echo "# KommoAnalytics - ETL automático a cada 4h") | crontab -
(crontab -l 2>/dev/null; echo "0 */4 * * * $ETL_SCRIPT >> $PROJECT_DIR/LOGS/cron_etl.log 2>&1") | crontab -

# Adicionar backup diário às 2h
(crontab -l 2>/dev/null; echo "# KommoAnalytics - Backup diário às 2h") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT >> $PROJECT_DIR/LOGS/cron_backup.log 2>&1") | crontab -

# Adicionar monitoramento diário às 8h
(crontab -l 2>/dev/null; echo "# KommoAnalytics - Monitoramento diário às 8h") | crontab -
(crontab -l 2>/dev/null; echo "0 8 * * * cd $PROJECT_DIR && source dashboard_env/bin/activate && python $MONITOR_SCRIPT >> $PROJECT_DIR/LOGS/monitor_daily.log 2>&1") | crontab -

# Adicionar health check diário às 10h
(crontab -l 2>/dev/null; echo "# KommoAnalytics - Health check diário às 10h") | crontab -
(crontab -l 2>/dev/null; echo "0 10 * * * $HEALTH_SCRIPT >> $PROJECT_DIR/LOGS/cron_health.log 2>&1") | crontab -

echo " Automação configurada com sucesso!"
echo ""

echo "📋 CRONOGRAMA CONFIGURADO:"
echo "   🔄 A cada 4h: Execução completa de todos ETLs"
echo "   💾 Diariamente às 2h: Backup automático do banco"
echo "   📊 Diariamente às 8h: Monitoramento e health check"
echo "   🔍 Diariamente às 10h: Health check completo do sistema"
echo ""
echo "📊 PRÓXIMAS EXECUÇÕES:"
echo "   ETL: $(date -d '+4 hours' '+%H:00 - %d/%m/%Y')"
echo "   Backup: $(date -d 'tomorrow 2:00' '+%H:00 - %d/%m/%Y')"
echo "   Monitor: $(date -d 'tomorrow 8:00' '+%H:%M - %d/%m/%Y')"
echo "   Health: $(date -d 'tomorrow 10:00' '+%H:%M - %d/%m/%Y')"
echo ""
echo "📁 LOGS EM: $PROJECT_DIR/LOGS/"
echo "💾 BACKUPS EM: $PROJECT_DIR/BACKUP/"
echo "🔧 CONFIGURAÇÃO: crontab -l"
echo ""
echo " Para testar agora: $ETL_SCRIPT"
