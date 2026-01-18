# Gov.br Auth API - Docker
# Build para deploy on-premise

FROM python:3.11-slim

# Metadados
LABEL maintainer="dev@example.com"
LABEL description="Gov.br Auth API com integração SIGEF"
LABEL version="1.0.0"

# Variáveis de build
ARG ENVIRONMENT=production
ARG PORT=8000

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=${ENVIRONMENT} \
    PORT=${PORT}

# Diretório de trabalho
WORKDIR /app

# Instala dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Para Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # Utilitários
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements primeiro (para cache de camadas)
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia código fonte
COPY src/ ./src/
COPY pyproject.toml .

# Cria diretórios de dados
RUN mkdir -p /app/data/sessions /app/data/downloads /app/data/logs

# Usuário não-root
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Instala browsers do Playwright como appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
RUN playwright install chromium

# Porta
EXPOSE ${PORT}

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando de produção
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
