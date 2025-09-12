#!/bin/bash

# Script de inicialização do container

echo "🚀 Iniciando Kommo Analytics..."

# Configurar cron jobs
echo "⏰ Configurando cron jobs..."
/app/AUTOMATION/setup_cron.sh

# Iniciar cron em background
echo "🔄 Iniciando cron daemon..."
sudo service cron start || cron

# Aguardar um pouco para garantir que o cron está rodando
sleep 2

# Verificar se o banco está acessível (modo opcional para produção)
echo "🔍 Verificando conexão com banco de dados..."
python3 -c "
import mysql.connector
import os
import time

max_retries = 5
retry_count = 0

while retry_count < max_retries:
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'kommo_analytics'),
            password=os.getenv('DB_PASSWORD', 'previdas_ltda_2025'),
            database=os.getenv('DB_NAME', 'kommo_analytics')
        )
        conn.close()
        print('✅ Conexão com banco estabelecida!')
        break
    except Exception as e:
        retry_count += 1
        print(f'⏳ Tentativa {retry_count}/{max_retries} - Aguardando banco...')
        time.sleep(2)

if retry_count >= max_retries:
    print('⚠️ Não foi possível conectar ao banco - continuando sem verificação')
    print('💡 Certifique-se de que o banco está acessível para funcionalidade completa')
"

# ETL inicial será executado pelo cron automaticamente
echo "📊 ETL será executado automaticamente pelo cron"

# Iniciar Streamlit
echo "🌐 Iniciando Streamlit..."
exec streamlit run DASHBOARD/main_app.py --server.port=8501 --server.address=0.0.0.0

