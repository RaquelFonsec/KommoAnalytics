#!/bin/bash
# Script de backup automático do banco de dados Kommo Analytics
# Executa backup diário às 2h da manhã

PROJECT_DIR="/app"
BACKUP_DIR="$PROJECT_DIR/BACKUP"
LOG_DIR="$PROJECT_DIR/LOGS"

# Criar diretórios se não existirem
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Função para log com timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/backup.log"
}

# Nome do arquivo de backup
BACKUP_FILE="kommo_analytics_$(date +%Y%m%d_%H%M%S).sql"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

log_with_timestamp "🚀 === INICIANDO BACKUP DO BANCO DE DADOS ==="

# Executar backup
log_with_timestamp "📊 Criando backup: $BACKUP_FILE"

if mysqldump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    "$DB_NAME" > "$BACKUP_PATH" 2>> "$LOG_DIR/backup_error.log"; then
    
    # Verificar tamanho do backup
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    log_with_timestamp "✅ Backup criado com sucesso: $BACKUP_SIZE"
    
    # Comprimir backup
    log_with_timestamp "🗜️ Comprimindo backup..."
    gzip "$BACKUP_PATH"
    COMPRESSED_SIZE=$(du -h "$BACKUP_PATH.gz" | cut -f1)
    log_with_timestamp "✅ Backup comprimido: $COMPRESSED_SIZE"
    
    # Limpar backups antigos (manter apenas últimos 7 dias)
    log_with_timestamp "🧹 Limpando backups antigos..."
    find "$BACKUP_DIR" -name "kommo_analytics_*.sql.gz" -mtime +7 -delete
    log_with_timestamp "✅ Limpeza concluída"
    
    # Verificar espaço em disco
    DISK_USAGE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $5}')
    log_with_timestamp "💾 Uso do disco: $DISK_USAGE"
    
    log_with_timestamp "🎉 === BACKUP CONCLUÍDO COM SUCESSO ==="
    echo "SUCCESS: $BACKUP_FILE.gz ($COMPRESSED_SIZE)" > "$LOG_DIR/last_backup_status.txt"
    
else
    log_with_timestamp "❌ Erro ao criar backup"
    log_with_timestamp "📋 Verificar logs em: $LOG_DIR/backup_error.log"
    echo "ERROR: Backup failed" > "$LOG_DIR/last_backup_status.txt"
    exit 1
fi
