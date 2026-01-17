# Gov-Auth - Proposta Comercial

## Descrição

Sistema completo de autenticação integrada com **Gov.br** e **SIGEF (INCRA)** com consulta de imóveis rurais via WFS (Web Feature Service) e extraction de dados georreferenciados.

**Stack:** Python 3.11 + FastAPI + React 18 + TypeScript + Docker + PostgreSQL

**Principais funcionalidades:**
- Autenticação via Govbr com certificado digital (A1)
- Integração com SIGEF para acesso a dados de parcelas certificadas
- Consulta automática em **7 camadas WFS** (SIGEF Particular/Público, SNCI Privado/Público, Assentamentos, Quilombolas, Pendentes de Titulação)
- Modal interativo com **5 seções de dados** extraídos via HTML parsing
- Suporte a downloads CSV de parcelas (vértices, limites, polígonos)
- Dashboard com consulta geográfica por bounding box
- Sistema completo de gerenciamento de sessões com persistência
- Deployment containerizado (Docker + Docker Compose)
- API REST documentada com 15+ endpoints

---

## Investimento

**Valor:** R$ 7.722,00
**Horas:** 66 horas de desenvolvimento

## Entregáveis

- Backend completo em Python/FastAPI
- Frontend em React 18/TypeScript
- Serviço de autenticação Gov.br
- Clientes WFS (INCRA e GeoOne)
- Cliente HTTP para SIGEF
- Sistema de gerenciamento de sessões GOV
- Dockerfile
- docker-compose.yml para desenvolvimento e produção
- Health checks e logging estruturado
- README completo com instruções
- DOCKER_DEPLOY
- Documentação técnica da API
- Guias de configuração ambiente
- Scripts de setup automático
- Testes unitários (pytest)
- Configuração de variáveis de ambiente

---

## Características Técnicas

### Backend
- **Framework:** FastAPI 0.104+
- **ORM:** SQLAlchemy
- **Autenticação:** Gov.br SSO + JWT
- **Browser:** Playwright para automação
- **HTTP:** httpx com async/await
- **Parsing:** BeautifulSoup4 para HTML
- **Logging:** structlog com JSON estruturado

### Frontend
- **Framework:** React 18
- **Linguagem:** TypeScript
- **Styling:** Tailwind CSS
- **Icons:** Lucide React
- **HTTP:** axios com interceptors
- **Build:** Vite

### Dados
- **WFS:** INCRA (HTTPS) + GeoOne
- **APIs:** IBGE para dados municipais
- **Scraping:** SIGEF com sessões autenticadas
- **Geocoding:** Conversão de códigos IBGE

---

## Suporte

**6 MESES DE SUPORTE INCLUSO**

Cobertura:
- Correção de bugs
- Dúvidas de uso e configuração

---

**Desenvolvedor:** Luis Montagner  
**Projeto:** SICAR API v1.1.0  
**Data:** 13-17 Dezembro 2025