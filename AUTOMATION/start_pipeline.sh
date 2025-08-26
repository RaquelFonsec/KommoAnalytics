#!/bin/bash

echo "🚀 Iniciando Pipeline Automatizado Kommo Analytics"
echo "=================================================="

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Erro: Arquivo .env não encontrado!"
    echo "Crie o arquivo .env com suas credenciais do Kommo"
    exit 1
fi

# Criar diretórios necessários
mkdir -p DATA/logs
mkdir -p DATA/exports

echo "✅ Diretórios criados"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Erro: Python3 não encontrado!"
    exit 1
fi

echo "✅ Python3 encontrado"

# Instalar dependências se necessário
echo "📦 Verificando dependências..."
pip install -q schedule streamlit plotly pandas requests python-dotenv

echo "✅ Dependências verificadas"

# Parar processos existentes
echo "🛑 Parando processos existentes..."
pkill -f streamlit 2>/dev/null || true
pkill -f pipeline_automated.py 2>/dev/null || true

sleep 2

# Iniciar pipeline automatizado
echo "🚀 Iniciando pipeline automatizado..."
echo "📊 Dashboard será iniciado automaticamente"
echo "🔄 ETL será executado a cada 6 horas"
echo "⏰ Logs em: DATA/logs/pipeline.log"
echo ""
echo "Para parar: Ctrl+C"
echo "Para ver logs: tail -f DATA/logs/pipeline.log"
echo ""

# Executar pipeline
python3 pipeline_automated.py


