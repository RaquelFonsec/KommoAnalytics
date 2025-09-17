#!/bin/bash

# Script completo de setup do servidor para Digital Ocean
# Kommo Analytics

echo "🚀 Setup completo do servidor - Kommo Analytics"
echo "================================================"

# Verificar se é root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Execute como root: sudo ./setup_server_complete.sh"
    exit 1
fi

# 1. Instalar Docker
echo "📦 Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker instalado"
else
    echo "✅ Docker já está instalado"
fi

# 2. Instalar Docker Compose
echo "📦 Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose instalado"
else
    echo "✅ Docker Compose já está instalado"
fi

# 3. Instalar Git
echo "📦 Instalando Git..."
if ! command -v git &> /dev/null; then
    apt-get update
    apt-get install -y git
    echo "✅ Git instalado"
else
    echo "✅ Git já está instalado"
fi

# 4. Clonar repositório
echo "📁 Clonando repositório..."
if [ ! -d "KommoAnalytics" ]; then
    git clone https://github.com/RaquelFonsec/KommoAnalytics.git
    echo "✅ Repositório clonado"
else
    echo "✅ Repositório já existe"
fi

cd KommoAnalytics

# 5. Fazer checkout da branch de produção
echo "🔄 Configurando branch de produção..."
git checkout production-docker-deploy
echo "✅ Branch de produção configurada"

# 6. Configurar .env
echo "⚙️ Configurando variáveis de ambiente..."
if [ ! -f ".env" ]; then
    cp env.prod.example .env
    echo "✅ Arquivo .env criado"
    echo ""
    echo "⚠️ IMPORTANTE: Configure o arquivo .env com suas credenciais:"
    echo "   nano .env"
    echo ""
    echo "📋 Variáveis necessárias:"
    echo "   - DB_HOST: Host do banco na Digital Ocean"
    echo "   - DB_PASSWORD: Senha do banco"
    echo "   - KOMMO_ACCESS_TOKEN: Token da API Kommo"
    echo "   - KOMMO_ACCOUNT_ID: ID da conta Kommo"
    echo ""
    read -p "Pressione Enter após configurar o .env..."
else
    echo "✅ Arquivo .env já existe"
fi

# 7. Tornar scripts executáveis
echo "🔧 Configurando permissões..."
chmod +x deploy_digital_ocean.sh
chmod +x setup_streamlit_production.sh
chmod +x verify_production_ready.sh
echo "✅ Permissões configuradas"

# 8. Verificar configuração
echo "🔍 Verificando configuração..."
./verify_production_ready.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completo! Servidor pronto para deploy."
    echo ""
    echo "📋 Próximos passos:"
    echo "1. Configure o arquivo .env com suas credenciais"
    echo "2. Execute: ./deploy_digital_ocean.sh"
    echo "3. Acesse: http://seu-ip:8501"
else
    echo "❌ Erro na verificação. Corrija os problemas antes de continuar."
    exit 1
fi
