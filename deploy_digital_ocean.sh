#!/bin/bash

# Script de Deploy para Digital Ocean
# Kommo Analytics

echo "🚀 Deploy para Digital Ocean - Kommo Analytics"

# Verificar se estamos no diretório correto
if [ ! -f "Dockerfile" ]; then
    echo "❌ Erro: Execute este script no diretório raiz do projeto"
    exit 1
fi

# Verificar se o .env existe
if [ ! -f ".env" ]; then
    echo "❌ Erro: Arquivo .env não encontrado"
    echo "📋 Configure as variáveis de ambiente:"
    echo "   - DB_HOST: Host do banco na Digital Ocean"
    echo "   - DB_PASSWORD: Senha do banco"
    echo "   - KOMMO_ACCESS_TOKEN: Token da API Kommo"
    echo "   - KOMMO_ACCOUNT_ID: ID da conta Kommo"
    echo ""
    echo "💡 Exemplo: cp env.prod.example .env"
    exit 1
fi

# Verificar se as variáveis essenciais estão configuradas
if ! grep -q "KOMMO_ACCESS_TOKEN=" .env || grep -q "KOMMO_ACCESS_TOKEN=seu_token_aqui" .env; then
    echo "Erro: KOMMO_ACCESS_TOKEN não configurado no .env"
    exit 1
fi

if ! grep -q "KOMMO_ACCOUNT_ID=" .env || grep -q "KOMMO_ACCOUNT_ID=seu_account_id_aqui" .env; then
    echo " Erro: KOMMO_ACCOUNT_ID não configurado no .env"
    exit 1
fi

# Configurar Streamlit para produção
echo " Configurando Streamlit para produção..."
./setup_streamlit_production.sh

# Parar containers existentes
echo " Parando containers existentes..."
docker-compose -f docker-compose.prod.yml down

# Remover imagens antigas
echo " Limpando imagens antigas..."
docker system prune -f

# Construir nova imagem
echo " Construindo nova imagem..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Iniciar containers
echo " Iniciando containers..."
docker-compose -f docker-compose.prod.yml up -d

# Aguardar inicialização
echo " Aguardando inicialização..."
sleep 30

# Verificar status
echo "🔍 Verificando status dos containers..."
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
echo "📋 Últimas linhas dos logs:"
docker-compose -f docker-compose.prod.yml logs --tail=20

echo "✅ Deploy concluído!"
echo "🌐 Aplicação disponível em: http://seu-ip:8501"
echo "📊 Para ver logs em tempo real: docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🔧 Comandos úteis:"
echo "   - Ver logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   - Parar: docker-compose -f docker-compose.prod.yml down"
echo "   - Reiniciar: docker-compose -f docker-compose.prod.yml restart"
