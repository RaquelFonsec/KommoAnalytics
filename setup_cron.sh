#!/bin/bash
# Script para configurar cron jobs do Kommo Analytics
# Autor: Sistema de Automação Kommo Analytics

PROJECT_DIR="/home/raquel-fonseca/Projects/KommoAnalytics"
SMART_ETL_SCRIPT="$PROJECT_DIR/smart_etl.sh"

echo "🔧 Configurando Cron Jobs para Kommo Analytics..."

# Verificar se o script existe
if [ ! -f "$SMART_ETL_SCRIPT" ]; then
    echo "❌ Script smart_etl.sh não encontrado em $SMART_ETL_SCRIPT"
    exit 1
fi

# Tornar script executável
chmod +x "$SMART_ETL_SCRIPT"

# Criar arquivo temporário com os cron jobs
cat > /tmp/kommo_cron << EOF
# Kommo Analytics - Cron Jobs
# Verificar a cada 30 minutos se precisa executar ETL
*/30 * * * * $SMART_ETL_SCRIPT

# Executar forçadamente a cada 6 horas (backup)
0 */6 * * * touch /tmp/kommo_etl_requested.flag

# Backup diário do banco de dados
0 2 * * * $PROJECT_DIR/AUTOMATION/backup_database.sh

# Limpeza automática semanal (domingo às 3h)
0 3 * * 0 $PROJECT_DIR/cleanup.sh

# Limpeza de logs antigos (semanal)
0 3 * * 0 find $PROJECT_DIR/LOGS -name "*.log" -type f -mtime +7 -delete
EOF

# Instalar cron jobs
crontab /tmp/kommo_cron

# Verificar se foi instalado
if crontab -l | grep -q "Kommo Analytics"; then
    echo "✅ Cron jobs instalados com sucesso!"
    echo ""
    echo "📋 Cron jobs configurados:"
    crontab -l | grep -v "^#"
    echo ""
    echo "📁 Logs disponíveis em: $PROJECT_DIR/LOGS/"
    echo "🚀 Script smart ETL: $SMART_ETL_SCRIPT"
else
    echo "❌ Erro ao instalar cron jobs"
    exit 1
fi

# Limpar arquivo temporário
rm /tmp/kommo_cron

echo ""
echo "🎉 Configuração concluída!"
echo "💡 O sistema agora verifica automaticamente a cada 30 minutos se há solicitações de ETL"
echo "🔄 E executa forçadamente a cada 6 horas como backup"
