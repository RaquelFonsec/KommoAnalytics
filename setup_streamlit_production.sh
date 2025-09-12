#!/bin/bash

# Script para configurar Streamlit para produção
# Kommo Analytics

echo "Configurando Streamlit para producao..."

# Criar diretório .streamlit se não existir
mkdir -p DASHBOARD/.streamlit

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "Erro: Arquivo .env nao encontrado"
    echo "Configure o arquivo .env antes de executar este script"
    exit 1
fi

# Carregar variáveis do .env
source .env

# Criar secrets.toml para produção
cat > DASHBOARD/.streamlit/secrets.toml << EOF
# Configurações de produção - Kommo Analytics
# Gerado automaticamente pelo setup_streamlit_production.sh

# Banco de Dados
DB_HOST = "${DB_HOST:-localhost}"
DB_PORT = ${DB_PORT:-3306}
DB_USER = "${DB_USER:-kommo_analytics}"
DB_PASSWORD = "${DB_PASSWORD:-previdas_ltda_2025}"
DB_NAME = "${DB_NAME:-kommo_analytics}"

# Kommo API
KOMMO_ACCESS_TOKEN = "${KOMMO_ACCESS_TOKEN}"
KOMMO_ACCOUNT_ID = ${KOMMO_ACCOUNT_ID}

# Configurações adicionais
STREAMLIT_SERVER_PORT = ${STREAMLIT_SERVER_PORT:-8501}
STREAMLIT_SERVER_ADDRESS = "${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"
EOF

echo "✅ secrets.toml configurado para produção"
echo "✅ Configurações do Streamlit prontas"
echo ""
echo "📋 Próximos passos:"
echo "1. Execute: ./deploy_digital_ocean.sh"
echo "2. Acesse: http://seu-ip:8501"
