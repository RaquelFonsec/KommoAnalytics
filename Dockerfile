FROM python:3.12-slim

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    cron \
    procps \
    sudo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    echo "appuser ALL=(ALL) NOPASSWD: /usr/sbin/service" >> /etc/sudoers

# Copiar requirements primeiro (para cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p /app/LOGS /app/BACKUP && \
    chown -R appuser:appuser /app

# Configurar permissões
RUN chmod +x /app/AUTOMATION/*.sh && \
    chmod +x /app/docker-entrypoint.sh

# Mudar para usuário não-root
USER appuser

# Expor porta
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando para executar
CMD ["/app/docker-entrypoint.sh"]