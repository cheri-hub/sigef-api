# SIGEF API - Minimal Edition

API mínima para autenticação Gov.br e download de arquivos SIGEF.

**Branch:** `datageoplan-python-api-min`

## 🎯 Funcionalidades

Esta versão contém apenas os endpoints necessários para o cliente C#:

- **Autenticação Gov.br**: Via certificado digital no navegador do cliente
- **Download de CSVs**: Parcela, Vértice e Limite
- **Download Completo**: ZIP com todos os arquivos

## 📡 Endpoints Disponíveis

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/v1/auth/status` | Verifica status de autenticação |
| `POST` | `/v1/auth/browser-login` | Inicia fluxo de autenticação |
| `POST` | `/v1/auth/browser-callback` | Recebe dados de autenticação |
| `POST` | `/v1/auth/logout` | Encerra sessão |

### SIGEF

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/v1/sigef/arquivo/csv/{codigo}/{tipo}` | Download CSV (parcela/vertice/limite) |
| `GET` | `/v1/sigef/arquivo/todos/{codigo}` | Download ZIP com todos os arquivos |

## 📁 Estrutura do Projeto

```
sigef-api/
├── src/
│   ├── api/
│   │   ├── middleware/          # Auth, Rate Limit, Security
│   │   └── v1/
│   │       ├── routes/
│   │       │   ├── auth.py      # Endpoints de autenticação
│   │       │   └── sigef.py     # Endpoints SIGEF
│   │       ├── static/          # Página de auth browser
│   │       ├── schemas.py       # DTOs Pydantic
│   │       └── dependencies.py  # Injeção de dependências
│   ├── core/                    # Config, Logging, Exceptions
│   ├── domain/                  # Entidades (Session, Parcela)
│   ├── infrastructure/
│   │   ├── browser_auth/        # Sessões de browser-login
│   │   ├── govbr/               # Autenticador Gov.br
│   │   ├── persistence/         # Repositório de sessões
│   │   └── sigef/               # Cliente SIGEF
│   ├── services/                # Auth e SIGEF services
│   └── main.py                  # FastAPI app
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

## 🚀 Quick Start

### Requisitos

- Python 3.11+
- Google Chrome instalado

### Instalação

```bash
# Clone o repositório
git clone https://github.com/cheri-hub/sigef-api.git
cd sigef-api
git checkout datageoplan-python-api-min

# Crie ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Instale browsers do Playwright
playwright install chromium
```

### Configuração

Copie o arquivo de exemplo e configure:

```bash
cp .env.example .env
```

Edite `.env`:

```env
# Chave de API (gere uma segura)
API_KEY=sua-chave-segura-aqui

# Ambiente
ENVIRONMENT=development
DEBUG=true

# Diretórios
DATA_DIR=./data
LOGS_DIR=./logs
```

### Executar

```bash
# Desenvolvimento
python -m uvicorn src.main:app --reload --port 8000

# Produção
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build
docker build -t sigef-api .

# Run
docker run -p 8000:8000 -e API_KEY=sua-chave sigef-api
```

## 🔐 Autenticação

Todas as requisições (exceto `/v1/auth/status` e `/v1/auth/browser-login`) requerem:

```
Authorization: Bearer sua-api-key
```

## 📋 Fluxo de Autenticação

1. Cliente chama `POST /v1/auth/browser-login`
2. API retorna `auth_token` e `login_url`
3. Cliente abre `login_url` no navegador
4. Usuário faz login com certificado digital
5. Página captura cookies e envia para `POST /v1/auth/browser-callback`
6. Sessão criada, cliente pode usar endpoints SIGEF

## 📦 Cliente C#

O cliente C# está disponível em: https://github.com/cheri-hub/sigef-client

## 📄 Licença

MIT
