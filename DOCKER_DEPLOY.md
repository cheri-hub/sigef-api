# 🐳 Deploy com Docker

Guia para rodar o projeto Gov-Auth em container Docker.

## 📋 Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Git

## 🚀 Quick Start

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/gov-auth.git
cd gov-auth
```

### 2. Configure variáveis de ambiente

```bash
cp .env.example .env
```

**IMPORTANTE**: Edite `.env` e altere as chaves de segurança:

```bash
# Gere chaves seguras
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 32)
```

### 3. Build e Start

```bash
# Build das imagens
docker-compose build

# Inicia os containers
docker-compose up -d

# Verifica logs
docker-compose logs -f
```

### 4. Acesse a aplicação

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Documentação API**: http://localhost:8000/docs

## 📦 Comandos Úteis

### Gerenciamento de Containers

```bash
# Ver status
docker-compose ps

# Parar containers
docker-compose stop

# Parar e remover
docker-compose down

# Rebuild completo
docker-compose build --no-cache
docker-compose up -d

# Ver logs específicos
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Manutenção

```bash
# Limpar dados (sessions, downloads)
rm -rf data/*
rm -rf logs/*

# Entrar no container
docker-compose exec backend bash

# Executar comando no container
docker-compose exec backend python -c "print('Hello')"
```

## 🔧 Configuração Avançada

### Volumes Persistentes

Por padrão, dados são salvos em:
- `./data` - Sessões e downloads
- `./logs` - Logs da aplicação

Para alterar, edite `docker-compose.yml`:

```yaml
volumes:
  - /seu/caminho/data:/app/data
  - /seu/caminho/logs:/app/logs
```

### Portas Customizadas

Edite `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"  # Backend na porta 8080
  - "3001:80"    # Frontend na porta 3001
```

### Modo Desenvolvimento

Para desenvolvimento com hot-reload:

```yaml
# docker-compose.dev.yml
services:
  backend:
    volumes:
      - .:/app
    environment:
      - DEBUG=true
      - BROWSER_HEADLESS=false
    command: uvicorn src.main:app --reload --host 0.0.0.0
```

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 🌐 Deploy em Servidor

### 1. Servidor VPS/Cloud

```bash
# No servidor
git clone https://github.com/seu-usuario/gov-auth.git
cd gov-auth

# Configure .env
nano .env

# Inicie
docker-compose up -d

# Configure nginx reverso (opcional)
# Para expor na porta 80/443
```

### 2. Nginx Reverse Proxy

Crie `/etc/nginx/sites-available/gov-auth`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. SSL com Let's Encrypt

```bash
# Instale certbot
apt install certbot python3-certbot-nginx

# Obtenha certificado
certbot --nginx -d seu-dominio.com
```

## 🐛 Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
docker-compose logs backend

# Verificar portas em uso
netstat -tulpn | grep -E ':(3000|8000)'

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Erro de permissão

```bash
# Ajustar permissões
chmod -R 755 data/ logs/
chown -R 1000:1000 data/ logs/
```

### Playwright não funciona

O Dockerfile já instala o Chromium. Se tiver problemas:

```bash
# Entre no container
docker-compose exec backend bash

# Reinstale navegadores
playwright install chromium
```

### Memória insuficiente

Edite `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

## 📊 Monitoramento

### Healthchecks

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000/health
```

### Logs estruturados

Em produção, configure `LOG_FORMAT=json` para integrar com ferramentas como:
- ELK Stack
- Grafana Loki
- Datadog

## 🔐 Segurança

### Checklist de Produção

- [ ] Alterar `SECRET_KEY` e `API_KEY`
- [ ] Configurar `ENVIRONMENT=production`
- [ ] Desabilitar `DEBUG=false`
- [ ] Usar `BROWSER_HEADLESS=true`
- [ ] Configurar SSL/HTTPS
- [ ] Configurar firewall (apenas portas 80/443)
- [ ] Backup regular de `data/` e `logs/`
- [ ] Atualizar imagens regularmente

```bash
# Atualizar
git pull
docker-compose build
docker-compose up -d
```

## 📚 Recursos Adicionais

- [Documentação Docker](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Nginx](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)

---

**Desenvolvido com 🐍 Python + FastAPI + 🐳 Docker**
