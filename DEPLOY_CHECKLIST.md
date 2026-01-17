# Gov.br Auth API - Checklist de Deploy

## 📋 Checklist Pré-Deploy

### Segurança
- [ ] **API_KEY gerada** - Mínimo 32 caracteres aleatórios
- [ ] **SECRET_KEY gerada** - Mínimo 32 caracteres aleatórios  
- [ ] **CORS configurado** - Domínios específicos da aplicação C#
- [ ] **ENVIRONMENT=production** - Ativa middleware de autenticação
- [ ] **DEBUG=false** - Desabilita Swagger/ReDoc em produção
- [ ] **Certificados A1** - Armazenados com permissões restritas

### Docker
- [ ] **Build testado** - `docker-compose build` sem erros
- [ ] **Containers rodando** - `docker-compose up -d` funcional
- [ ] **Health check** - `curl http://localhost:8000/health` retorna 200
- [ ] **Volumes configurados** - Persistência de sessions/downloads/logs
- [ ] **Logs funcionando** - `docker-compose logs -f api` exibe JSON

### Infraestrutura
- [ ] **Reverse proxy** - Nginx configurado com SSL/TLS
- [ ] **Certificado SSL** - Let's Encrypt ou certificado válido
- [ ] **Firewall** - Apenas portas 80/443 expostas
- [ ] **Backup** - Volumes Docker com backup automático
- [ ] **Monitoramento** - Healthcheck + alertas configurados

### Integração C#
- [ ] **Cliente HTTP criado** - Com Bearer token authentication
- [ ] **Timeouts configurados** - Mínimo 60s para operações longas
- [ ] **Retry logic** - Exponential backoff implementado
- [ ] **Tratamento de erros** - HTTP status codes mapeados
- [ ] **Testes de integração** - Endpoints validados

---

## 🚀 Deploy em VPS/Cloud

### 1. Preparar Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
```

### 2. Clonar Repositório

```bash
cd /opt
sudo git clone https://github.com/seu-usuario/gov-auth.git
cd gov-auth
```

### 3. Configurar Ambiente

```bash
# Criar arquivo .env
sudo nano .env
```

**Conteúdo do .env:**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
HOST=0.0.0.0
PORT=8000

# CORS - Domínios da aplicação C#
CORS_ORIGINS=https://app.exemplo.com.br,https://admin.exemplo.com.br

# Segurança - GERAR CHAVES FORTES!
API_KEY=<gerar-chave-32-chars>
SECRET_KEY=<gerar-chave-32-chars>
```

**Gerar chaves seguras:**
```bash
# Gerar API_KEY
openssl rand -hex 32

# Gerar SECRET_KEY
openssl rand -hex 32
```

### 4. Build e Deploy

```bash
# Build das imagens
sudo docker-compose build

# Subir serviços
sudo docker-compose up -d

# Verificar logs
sudo docker-compose logs -f api

# Verificar status
sudo docker-compose ps
```

### 5. Configurar Nginx (Reverse Proxy)

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/gov-auth-api
```

**Configuração Nginx:**
```nginx
server {
    listen 80;
    server_name api.exemplo.com.br;

    # Redirecionar para HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.exemplo.com.br;

    # Certificados SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.exemplo.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.exemplo.com.br/privkey.pem;

    # Configurações SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Headers de segurança
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy para API
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts para operações longas
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

**Ativar configuração:**
```bash
sudo ln -s /etc/nginx/sites-available/gov-auth-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Configurar SSL (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado
sudo certbot --nginx -d api.exemplo.com.br

# Renovação automática (já configurado)
sudo certbot renew --dry-run
```

---

## 🔒 Validação de Segurança

### Teste 1: API Key Required

```bash
# Deve retornar 401 Unauthorized
curl https://api.exemplo.com.br/api/v1/auth/status/test

# Com API Key - deve funcionar
curl -H "Authorization: Bearer SUA_API_KEY" \
     https://api.exemplo.com.br/health
```

### Teste 2: CORS Headers

```bash
curl -H "Origin: https://app-nao-permitida.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://api.exemplo.com.br/api/v1/consulta

# Deve retornar CORS error ou sem headers CORS
```

### Teste 3: SSL/TLS

```bash
# Verificar certificado
openssl s_client -connect api.exemplo.com.br:443 -showcerts

# Testar grade SSL
curl https://www.ssllabs.com/ssltest/analyze.html?d=api.exemplo.com.br
```

---

## 📊 Monitoramento

### Health Check Automático

```bash
# Cron job para monitorar (executar a cada 5 minutos)
*/5 * * * * curl -f http://localhost:8000/health || echo "API DOWN" | mail -s "Gov Auth API Alert" admin@exemplo.com
```

### Logs Estruturados

```bash
# Ver logs em tempo real
sudo docker-compose logs -f api

# Filtrar erros
sudo docker-compose logs api | grep ERROR

# Exportar logs para análise
sudo docker-compose logs api > /var/log/gov-auth-$(date +%Y%m%d).log
```

### Métricas Docker

```bash
# Uso de recursos
docker stats gov-auth-api

# Disco utilizado
du -sh /opt/gov-auth/data/*
```

---

## 🧪 Teste de Integração C#

### Cliente de Teste

```bash
# No servidor C#
dotnet add package System.Net.Http.Json

# Testar conexão
curl -X POST https://api.exemplo.com.br/api/v1/consulta \
     -H "Authorization: Bearer SUA_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "min_x": -50.0,
       "min_y": -25.0,
       "max_x": -49.0,
       "max_y": -24.0
     }'
```

---

## 🆘 Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
sudo docker-compose logs api

# Verificar permissões
sudo chown -R 1000:1000 /opt/gov-auth/data

# Rebuild forçado
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

### API Key não funciona

```bash
# Verificar variável de ambiente
docker exec gov-auth-api env | grep API_KEY

# Verificar se middleware está ativo
docker exec gov-auth-api cat /etc/hosts
```

### CORS Bloqueando

```bash
# Verificar headers na resposta
curl -v -H "Origin: https://app.exemplo.com.br" \
     https://api.exemplo.com.br/health

# Deve conter:
# access-control-allow-origin: https://app.exemplo.com.br
```

---

## 📝 Notas Finais

1. **Backup Regular:** Volumes Docker em /opt/gov-auth/data
2. **Logs Rotativos:** Configurar logrotate para /var/log/gov-auth
3. **Updates:** `docker-compose pull && docker-compose up -d`
4. **Rollback:** `git checkout <commit-anterior> && docker-compose up -d --build`

---

**Status:** ✅ Pronto para deploy em produção  
**Última atualização:** Janeiro 2026
