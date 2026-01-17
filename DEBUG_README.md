# Scripts de Debug da API

Ferramentas para testar e debugar a API Gov.br Auth.

## 📁 Arquivos

### `debug_api.py` - Debug Interativo

Interface interativa completa para testar todos os endpoints da API.

**Características:**
- Menu interativo com Rich UI
- Formatação colorida de respostas JSON
- Suporte a todos os endpoints (Auth, SIGEF, Downloads)
- Gerenciamento de sessão
- Salvamento automático de arquivos baixados

**Uso:**
```bash
python debug_api.py
```

**Menu:**
```
HEALTH & AUTH
1  - Health Check
2  - Auth Status
3  - Login (Gov.br)
4  - Logout
5  - Ver Sessão Atual

SIGEF
6  - Buscar Parcela
7  - Download CSV (Individual)
8  - Download All CSVs
9  - Download Memorial (PDF)
10 - Download File (Direto)
11 - Batch Download

0  - Sair
```

---

### `test_api_quick.py` - Testes Rápidos

Script simples para testes automatizados sem interação.

**Características:**
- Testa todos os endpoints principais
- Útil para CI/CD
- Saída formatada e clara
- Exit codes apropriados

**Uso:**

```bash
# Executar todos os testes
python test_api_quick.py

# Executar teste específico
python test_api_quick.py health
python test_api_quick.py auth
python test_api_quick.py parcela
python test_api_quick.py csv
python test_api_quick.py memorial
python test_api_quick.py all
```

**Saída:**
```
🧪 Testes Rápidos - Gov.br Auth API
Base URL: http://localhost:8000

🏥 Health Check
   ✓ Status: healthy
   ✓ Version: 1.1.0

🔐 Auth Status
   ✓ Autenticado: Sim
   ✓ CPF: ***.***.**-**
   ✓ Nome: João Silva
   ✓ Gov.br: ✓
   ✓ SIGEF: ✓

📍 Parcela Info (999a354b...)
   ✓ Código: 999a354b-0c33-46a2-bfb3-28213892d541
   ✓ Denominação: FAZENDA EXEMPLO
   ✓ Área: 1234.56 ha
   ✓ Município: Brasília/DF
   ✓ Situação: Certificada

✓ Todos os testes passaram (4/4)
```

---

## 🚀 Setup

### Instalar Dependências

```bash
pip install rich
```

Ou se ainda não instalou o projeto completo:

```bash
pip install -r requirements.txt
```

### Iniciar API

Antes de executar os scripts, certifique-se de que a API está rodando:

```bash
# Terminal 1 - Backend
python -m src.main

# Terminal 2 - Debug
python debug_api.py
```

---

## 📋 Pré-requisitos

### Para Testes Básicos
- ✅ API rodando em `http://localhost:8000`
- ✅ Python 3.11+
- ✅ Dependência `rich` instalada

### Para Testes de Download
- ✅ Sessão autenticada (use opção 3 no menu)
- ✅ Certificado digital A1 instalado
- ✅ Chrome instalado

---

## 🎯 Casos de Uso

### 1. Verificar se API está funcionando

```bash
python test_api_quick.py health
```

### 2. Testar autenticação completa

```bash
python debug_api.py
# Escolha opção 3 (Login)
# Escolha opção 2 (Auth Status) para verificar
```

### 3. Baixar dados de uma parcela

```bash
python debug_api.py
# Opção 6 - Buscar Parcela
# Opção 9 - Download Memorial
# Opção 8 - Download All CSVs
```

### 4. Teste rápido de todos os endpoints

```bash
python test_api_quick.py
```

### 5. Debug de erro específico

```bash
python debug_api.py
# Execute a operação que está falhando
# Veja JSON da resposta detalhado
# Headers e status code completos
```

---

## 🔧 Configuração

Ambos os scripts usam as seguintes configurações padrão:

```python
API_BASE_URL = "http://localhost:8000"
API_V1_URL = "http://localhost:8000/api/v1"
```

Para mudar a URL da API, edite a variável `API_BASE_URL` no início de cada arquivo.

**Exemplo para produção:**
```python
API_BASE_URL = "https://api.example.com"
```

---

## 📊 Exemplos de Saída

### Health Check
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "environment": "development",
  "timestamp": "2024-12-28T10:30:00"
}
```

### Auth Status (Autenticado)
```json
{
  "authenticated": true,
  "session": {
    "session_id": "abc123...",
    "cpf": "***.***.**-**",
    "nome": "João Silva",
    "is_valid": true,
    "is_govbr_authenticated": true,
    "is_sigef_authenticated": true,
    "created_at": "2024-12-28T10:00:00",
    "expires_at": "2024-12-28T22:00:00"
  },
  "message": "Sessão ativa e válida"
}
```

### Download CSV (Sucesso)
```json
{
  "success": true,
  "message": "CSV de parcela baixado com sucesso",
  "arquivo": "/downloads/999a354b_parcela.csv",
  "tamanho_bytes": 12345
}
```

### Download Memorial (Sucesso)
```
Content-Type: application/pdf
Content-Length: 245678

[Binary PDF Data]
```

---

## ⚠️ Troubleshooting

### Erro: Connection refused
```
✗ Erro: [Errno 111] Connection refused
```

**Solução:** Certifique-se de que a API está rodando:
```bash
python -m src.main
```

### Erro: 401 Unauthorized
```
⚠ Não autenticado - faça login primeiro
```

**Solução:** Execute o login:
```bash
python debug_api.py
# Opção 3 - Login
```

### Erro: 404 Not Found (Parcela)
```
✗ Parcela não encontrada
```

**Solução:** Verifique o código da parcela. Use um código válido do SIGEF.

### Erro: 502 Bad Gateway (SIGEF)
```
✗ Erro ao baixar CSV: HTTP 502
```

**Solução:** 
1. Verifique conexão com SIGEF
2. Tente novamente (pode ser instabilidade temporária)
3. Re-autentique se necessário

---

## 🧪 Testes Automatizados (CI/CD)

Para usar em pipelines de CI/CD:

```yaml
# .github/workflows/api-tests.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Start API
        run: |
          python -m src.main &
          sleep 5
      
      - name: Run tests
        run: python test_api_quick.py
```

---

## 📝 Notas

- Os scripts NÃO fazem login automaticamente (requer certificado)
- Memorial e CSVs são salvos no diretório atual
- Timeout padrão: 60s para downloads, 30s para consultas
- Rich é usado apenas para UI, não afeta funcionalidade

---

## 🔗 Referências

- [API Documentation](../README.md)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Rich Documentation](https://rich.readthedocs.io)

---

*Scripts de debug v1.0 - Dezembro 2024*
