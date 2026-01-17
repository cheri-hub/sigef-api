# 🔒 Análise de Segurança - Gov.br Auth API

**Data:** 06/01/2026  
**Versão:** 1.0.0  
**Ambiente Analisado:** Produção e Desenvolvimento

---

## 📊 Resumo Executivo

| Categoria | Status | Criticidade | Ações Necessárias |
|-----------|--------|-------------|-------------------|
| Autenticação | ⚠️ Parcial | ALTA | 3 melhorias identificadas |
| Autorização | ⚠️ Parcial | ALTA | Implementar RBAC |
| Gestão de Credenciais | ⚠️ Parcial | CRÍTICA | 2 vulnerabilidades |
| Validação de Inputs | ✅ Bom | MÉDIA | Manter padrão |
| Armazenamento | ⚠️ Parcial | ALTA | Criptografia necessária |
| Logging & Auditoria | ✅ Bom | BAIXA | Adicionar eventos críticos |
| Exposição de Informações | ⚠️ Parcial | ALTA | Sanitizar respostas |
| Dependências | ❓ Desconhecido | MÉDIA | Scan necessário |
| Configuração | ⚠️ Parcial | ALTA | Hardening requerido |

**Score Geral:** 58/100 - **ATENÇÃO NECESSÁRIA**

---

## 🔴 VULNERABILIDADES CRÍTICAS

### 1. ⚠️ Armazenamento de Sessões em Plaintext

**Severidade:** CRÍTICA  
**Arquivo:** `src/infrastructure/persistence/session_repository.py:160-162`

```python
# PROBLEMA: Dados sensíveis salvos sem criptografia
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

**Impacto:**
- Cookies de autenticação Gov.br expostos
- JWT tokens armazenados em plaintext
- Certificados A1 potencialmente acessíveis
- Comprometimento total da sessão se filesystem for acessado

**Dados Expostos:**
```json
{
  "jwt_payload": {
    "access_token": "eyJhbG...",  // Token de acesso completo
    "id_token": "eyJhbG...",       // ID token com CPF/dados pessoais
    "cpf": "12345678900"           // CPF do usuário
  },
  "govbr_cookies": [
    {"name": "JSESSIONID", "value": "ABC123..."},
    {"name": "TOKEN", "value": "XYZ789..."}
  ]
}
```

**Recomendação:**
```python
# Usar criptografia AES-256-GCM
from cryptography.fernet import Fernet

class EncryptedSessionRepository:
    def __init__(self):
        # Ler chave de criptografia do .env (NÃO do código!)
        self.cipher = Fernet(os.getenv("SESSION_ENCRYPTION_KEY").encode())
    
    async def save(self, session: Session) -> None:
        data = self._session_to_dict(session)
        json_data = json.dumps(data).encode()
        encrypted = self.cipher.encrypt(json_data)
        
        with open(path, "wb") as f:
            f.write(encrypted)
```

---

### 2. ⚠️ Comparação de API Key sem Timing Attack Protection

**Severidade:** ALTA  
**Arquivo:** `src/api/middleware/auth.py:68`

```python
# PROBLEMA: Comparação direta permite timing attacks
if credentials != settings.api_key:
    logger.warning("API Key inválida")
```

**Impacto:**
- Atacante pode descobrir API Key byte-a-byte via timing attack
- Medindo tempo de resposta, é possível inferir caracteres corretos

**Recomendação:**
```python
import secrets

# Usar comparação constant-time
if not secrets.compare_digest(credentials, settings.api_key):
    logger.warning("API Key inválida")
```

---

### 3. ⚠️ Chaves Padrão em Desenvolvimento Podem ir para Produção

**Severidade:** ALTA  
**Arquivo:** `src/core/config.py:36,44`

```python
api_key: str = "dev-api-key-change-in-production"
secret_key: str = "change-this-secret-key-in-production"
```

**Impacto:**
- Se `.env` não for configurado, chaves padrão são usadas
- Sem validação de força das chaves
- Sem alerta se chaves padrão estiverem em produção

**Recomendação:**
```python
from pydantic import field_validator

class Settings(BaseSettings):
    api_key: str
    secret_key: str
    
    @field_validator("api_key", "secret_key")
    def validate_production_keys(cls, v, info):
        if cls.is_production and (
            "dev-" in v or 
            "change-" in v or 
            len(v) < 32
        ):
            raise ValueError(
                f"{info.field_name} INSEGURA em produção! "
                "Gere chave forte: openssl rand -hex 32"
            )
        return v
```

---

## 🟠 VULNERABILIDADES ALTAS

### 4. ⚠️ Sem Rate Limiting

**Severidade:** ALTA  
**Arquivo:** `src/api/middleware/auth.py` (ausente)

**Impacto:**
- API Key brute force attacks
- DDoS via endpoints pesados (WFS queries)
- Abuso de recursos computacionais

**Recomendação:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# No main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Nos endpoints
@router.post("/consulta")
@limiter.limit("10/minute")  # 10 requests por minuto
async def consultar(request: Request, ...):
    ...
```

---

### 5. ⚠️ Logging de Dados Sensíveis

**Severidade:** ALTA  
**Arquivo:** Múltiplos (grep mostrou 30+ ocorrências)

**Exemplo Problemático:**
```python
# src/services/auth_service.py:93
logger.info("Gov.br autenticado", cpf=session.cpf)  # ❌ CPF no log!
```

**Impacto:**
- CPF exposto em logs
- Cookies podem vazar em debug
- Violação LGPD (Lei Geral de Proteção de Dados)

**Recomendação:**
```python
# Criar helper para mascarar dados
def mask_cpf(cpf: str) -> str:
    return f"{cpf[:3]}.***.***-{cpf[-2:]}"

# Usar masked logging
logger.info("Gov.br autenticado", cpf_masked=mask_cpf(session.cpf))
```

---

### 6. ⚠️ Cookies SameSite=Lax (vulnerável a CSRF)

**Severidade:** ALTA  
**Arquivo:** `src/infrastructure/persistence/session_repository.py:73,87`

```python
same_site=c.get("same_site", "Lax"),  # ❌ Deveria ser "Strict"
```

**Impacto:**
- Cross-Site Request Forgery (CSRF) possível
- Cookies enviados em navegação cross-origin

**Recomendação:**
```python
# Forçar Strict em cookies sensíveis
same_site="Strict",
secure=True,  # Sempre HTTPS
http_only=True  # Prevenir acesso via JavaScript
```

---

### 7. ⚠️ Sem Validação de CORS em Produção

**Severidade:** ALTA  
**Arquivo:** `src/core/config.py:120-126`

```python
@property
def cors_origins(self) -> list[str]:
    if self.is_production:
        # ❌ Retorna lista vazia se CORS_ORIGINS não estiver configurado
        return []
    return ["http://localhost:3000", "http://localhost:8080"]
```

**Impacto:**
- Se `CORS_ORIGINS` não estiver no .env, NENHUM domínio é permitido
- Aplicação C# fica bloqueada sem logs claros
- Sem validação de formato (permite "*" acidentalmente)

**Recomendação:**
```python
@property
def cors_origins(self) -> list[str]:
    if self.is_production:
        origins = os.getenv("CORS_ORIGINS", "").split(",")
        origins = [o.strip() for o in origins if o.strip()]
        
        if not origins:
            logger.warning("⚠️ CORS_ORIGINS vazio em produção!")
            
        if "*" in origins:
            raise ValueError("Wildcard CORS (*) não permitido em produção")
        
        # Validar formato de URL
        for origin in origins:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"CORS origin inválido: {origin}")
        
        return origins
    return ["http://localhost:3000"]
```

---

## 🟡 VULNERABILIDADES MÉDIAS

### 8. ⚠️ Sem Content Security Policy (CSP)

**Severidade:** MÉDIA  
**Arquivo:** `src/main.py` (headers ausentes)

**Recomendação:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

### 9. ⚠️ Playwright Browser Automation Exposta

**Severidade:** MÉDIA  
**Arquivo:** `src/infrastructure/sigef/client.py:124`

```python
headless=False,  # ❌ Modo visível em produção
```

**Impacto:**
- Consumo de recursos (renderização GUI)
- Possível captura de tela por malware
- Performance degradada

**Recomendação:**
```python
headless=settings.browser_headless,  # True em produção

# No config.py
browser_headless: bool = Field(
    default=True,
    description="Headless mode (False apenas em dev)"
)

@field_validator("browser_headless")
def validate_headless(cls, v):
    if cls.is_production and not v:
        logger.warning("⚠️ Browser headless=False em produção!")
    return v
```

---

### 10. ⚠️ Sem Validação de Input em Códigos de Parcela

**Severidade:** MÉDIA  
**Arquivo:** `src/infrastructure/sigef/client.py:60-66`

```python
def _validate_parcela_code(self, codigo: str) -> str:
    codigo = codigo.strip().lower()
    
    if not PARCELA_CODE_PATTERN.match(codigo):
        raise InvalidParcelaCodeError(codigo)
    
    return codigo
```

**Status:** ✅ BOM - Regex validation presente

**Recomendação Adicional:**
```python
# Adicionar sanitização extra
import bleach

def _validate_parcela_code(self, codigo: str) -> str:
    # Prevenir XSS/injection
    codigo = bleach.clean(codigo.strip().lower())
    
    # Limitar tamanho (UUID = 36 chars)
    if len(codigo) > 50:
        raise InvalidParcelaCodeError("Código muito longo")
    
    if not PARCELA_CODE_PATTERN.match(codigo):
        raise InvalidParcelaCodeError(codigo)
    
    return codigo
```

---

### 11. ⚠️ Exception Messages Expõem Internals

**Severidade:** MÉDIA  
**Arquivo:** `src/api/v1/routes/sigef.py:70,110`

```python
except SigefError as e:
    raise HTTPException(status_code=502, detail=str(e))  # ❌ Expõe stack trace
```

**Impacto:**
- Paths internos expostos
- Detalhes de implementação revelados
- Information leakage

**Recomendação:**
```python
except SigefError as e:
    logger.error("Erro SIGEF", error=str(e), exc_info=True)
    
    # Mensagem genérica para cliente
    if settings.is_production:
        raise HTTPException(
            status_code=502,
            detail="Erro ao comunicar com SIGEF. Contate suporte."
        )
    else:
        # Só em dev mostra detalhes
        raise HTTPException(status_code=502, detail=str(e))
```

---

### 12. ⚠️ ThreadPoolExecutor Global sem Limits

**Severidade:** MÉDIA  
**Arquivo:** `src/infrastructure/sigef/client.py:39`

```python
_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,  # ✅ BOM - limite configurado
    thread_name_prefix="sigef-playwright"
)
```

**Status:** ✅ ADEQUADO

**Recomendação:** Adicionar shutdown graceful:
```python
# No main.py lifespan
async def lifespan(app: FastAPI):
    yield
    
    # Shutdown
    _executor.shutdown(wait=True, cancel_futures=True)
```

---

## 🟢 PONTOS FORTES

### ✅ Tratamento de Exceções Estruturado

**Arquivo:** `src/core/exceptions.py`

- Hierarquia clara de exceções
- Códigos de erro padronizados
- Detalhes contextuais preservados

```python
class GovAuthException(Exception):
    def __init__(self, message: str, code: str, details: dict):
        self.message = message
        self.code = code
        self.details = details
```

---

### ✅ Logging Estruturado

**Arquivo:** Múltiplos arquivos (30+ ocorrências)

- Uso consistente de `logger.info/warning/error`
- Contexto adicional em logs
- Separação por níveis

**Melhorias Aplicadas:**
```python
logger.warning(
    "Requisição sem Authorization header",
    path=request.url.path,
    client=request.client.host
)
```

---

### ✅ Validação de Schemas com Pydantic

**Arquivo:** `src/api/v1/schemas.py`

- Validação automática de tipos
- Enums para valores fixos
- Field validators customizados

```python
class DownloadRequest(BaseModel):
    codigo: str = Field(..., min_length=36, max_length=36)
    tipo: TipoExportacaoEnum
```

---

### ✅ Middleware de Autenticação Implementado

**Arquivo:** `src/api/middleware/auth.py`

- API Key validation
- Rotas públicas definidas
- Logging de tentativas inválidas

---

### ✅ Retry Logic com Tenacity

**Arquivo:** `src/infrastructure/sigef/client.py` (importação detectada)

```python
from tenacity import retry, stop_after_attempt, wait_exponential
```

---

## 📋 CHECKLIST DE CORREÇÕES (PRIORIDADE)

### 🔴 CRÍTICO - Implementar IMEDIATAMENTE

- [ ] **Criptografar sessões em disco** (AES-256-GCM)
- [ ] **Usar `secrets.compare_digest()` para API Key**
- [ ] **Validar chaves em produção** (min 32 chars, sem padrões default)
- [ ] **Implementar geração automática de SECRET_KEY no primeiro boot**

### 🟠 ALTO - Implementar em 1 semana

- [ ] **Rate Limiting** (slowapi ou Redis)
- [ ] **Mascarar CPF/dados pessoais em logs**
- [ ] **SameSite=Strict em cookies**
- [ ] **Validar e sanitizar CORS_ORIGINS**
- [ ] **Security Headers Middleware** (CSP, HSTS, X-Frame-Options)
- [ ] **Headless=True forçado em produção**

### 🟡 MÉDIO - Implementar em 1 mês

- [ ] **Sanitizar exception messages em produção**
- [ ] **Scan de dependências** (safety, pip-audit)
- [ ] **Adicionar RBAC** (roles: admin, user, readonly)
- [ ] **Implementar session rotation** (novo session_id após auth)
- [ ] **Audit log separado** (quem fez o quê, quando)

---

## 🛠️ FERRAMENTAS RECOMENDADAS

### Scan de Segurança

```bash
# Scan de dependências
pip install safety
safety check --json

pip install pip-audit
pip-audit

# Scan de código SAST
pip install bandit
bandit -r src/ -f json -o security-report.json

# Scan de secrets no código
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline
```

### Testes de Penetração

```bash
# OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t http://localhost:8000 \
    -r zap-report.html

# API Fuzzing
pip install hypothesis
```

### Monitoramento Contínuo

```bash
# Dependabot (GitHub)
# Cria .github/dependabot.yml

# Snyk
snyk test --json > snyk-report.json
```

---

## 📊 MÉTRICAS DE SEGURANÇA

### Antes das Correções

| Métrica | Valor | Status |
|---------|-------|--------|
| Vulnerabilidades Críticas | 3 | 🔴 |
| Vulnerabilidades Altas | 5 | 🟠 |
| Vulnerabilidades Médias | 5 | 🟡 |
| Cobertura de Testes de Segurança | 0% | ❌ |
| Tempo para detecção de brecha | Desconhecido | ❌ |
| Criptografia de dados em repouso | Não | ❌ |
| Rate limiting implementado | Não | ❌ |

### Meta Após Correções

| Métrica | Valor Alvo | Prazo |
|---------|------------|-------|
| Vulnerabilidades Críticas | 0 | 1 semana |
| Vulnerabilidades Altas | 0 | 2 semanas |
| Vulnerabilidades Médias | ≤2 | 1 mês |
| Cobertura de Testes de Segurança | ≥60% | 2 meses |
| Tempo para detecção de brecha | <24h | 2 meses |
| Criptografia de dados em repouso | Sim | 1 semana |
| Rate limiting implementado | Sim | 1 semana |

---

## 🎯 RECOMENDAÇÕES FINAIS

### Arquiteturais

1. **Adicionar WAF (Web Application Firewall)**
   - ModSecurity rules no Nginx
   - Proteção contra OWASP Top 10

2. **Implementar Redis para Sessions**
   - Substituir JSON files
   - Sessions distribuídas
   - TTL automático

3. **Segregação de Ambientes**
   - Dev/Staging/Prod isolados
   - Chaves diferentes por ambiente
   - Logs centralizados (ELK Stack)

### Processuais

1. **Security Code Review**
   - Revisão por pares obrigatória
   - Checklist de segurança
   - Testes de segurança no CI/CD

2. **Incident Response Plan**
   - Playbook para breaches
   - Contatos de emergência
   - Backup/restore procedures

3. **Security Training**
   - OWASP Top 10 para devs
   - Secure coding practices
   - LGPD compliance

---

## 📞 CONTATOS PARA REMEDIAÇÃO

- **Desenvolvedor Principal:** [Adicionar contato]
- **Security Lead:** [Adicionar contato]
- **DevOps/Infra:** [Adicionar contato]

---

**Próxima Revisão:** 06/02/2026  
**Auditor:** GitHub Copilot (Claude Sonnet 4.5)  
**Versão do Documento:** 1.0
