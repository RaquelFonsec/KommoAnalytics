#!/bin/bash
# Script de Limpeza Automática - Kommo Analytics
# Autor: Sistema de Automação Kommo Analytics
# Data: $(date)

echo "🧹 Iniciando limpeza do projeto Kommo Analytics..."

# Configurações
PROJECT_DIR="$(pwd)"
LOG_DIR="$PROJECT_DIR/LOGS"
BACKUP_DIR="$PROJECT_DIR/BACKUP"

# Função para log com timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/cleanup.log"
}

# 1. Remover arquivos Python compilados
log_with_timestamp "🗑️ Removendo arquivos Python compilados..."
find . -name "*.pyc" -delete 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 2. Remover arquivos temporários
log_with_timestamp "🗑️ Removendo arquivos temporários..."
find . -name "*.tmp" -o -name "*.temp" -o -name "*~" -o -name ".#*" -o -name ".DS_Store" -o -name "Thumbs.db" -o -name "*.bak" -o -name "*.old" -delete 2>/dev/null

# 3. Limpar logs antigos (manter apenas últimos 7 dias)
log_with_timestamp "🗑️ Limpando logs antigos..."
find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete 2>/dev/null

# 4. Limpar backups antigos (manter apenas últimos 3 dias)
log_with_timestamp "🗑️ Limpando backups antigos..."
find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +3 -delete 2>/dev/null

# 5. Remover diretórios vazios
log_with_timestamp "🗑️ Removendo diretórios vazios..."
find . -type d -empty -delete 2>/dev/null

# 6. Verificar tamanho após limpeza
log_with_timestamp "📊 Verificando tamanho do projeto..."
TOTAL_SIZE=$(du -sh . | cut -f1)
log_with_timestamp "✅ Limpeza concluída! Tamanho total: $TOTAL_SIZE"

# 7. Mostrar estatísticas
echo ""
echo "📈 ESTATÍSTICAS DA LIMPEZA:"
echo "=========================="
echo "📁 Tamanho total do projeto: $TOTAL_SIZE"
echo "📊 Logs mantidos: $(find $LOG_DIR -name "*.log" | wc -l) arquivos"
echo "💾 Backups mantidos: $(find $BACKUP_DIR -name "*.sql.gz" | wc -l) arquivos"
echo "🗂️ Diretórios principais:"
du -sh */ 2>/dev/null | sort -hr | head -10

echo ""
echo "✅ Limpeza automática concluída com sucesso!"
echo "🔄 Execute este script periodicamente para manter o projeto organizado."
