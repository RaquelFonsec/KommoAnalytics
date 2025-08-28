FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório de logs
RUN mkdir -p LOGS

# Expor porta
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando para iniciar a aplicação
ENTRYPOINT ["streamlit", "run", "DASHBOARD/main_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
