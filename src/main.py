"""
Gov.br Auth API - Aplicação Principal.

API para autenticação Gov.br via certificado digital
e integração com SIGEF INCRA.
"""

import sys
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.v1 import router as v1_router
from src.api.middleware.ratelimit import get_limiter
from src.api.middleware.security import SecurityHeadersMiddleware
from src.core.config import get_settings
from src.core.exceptions import GovAuthException
from src.core.logging import get_logger, setup_logging

# Fix para Windows: Playwright precisa de ProactorEventLoop para criar subprocessos
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia ciclo de vida da aplicação.
    
    Startup:
    - Configura logging
    - Inicializa recursos
    
    Shutdown:
    - Libera recursos
    """
    # Startup
    setup_logging()
    settings = get_settings()
    
    logger.info(
        "Iniciando Gov.br Auth API",
        environment=settings.environment,
        debug=settings.debug,
    )
    
    # Garante que diretórios existam
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.downloads_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Encerrando Gov.br Auth API")


def create_app() -> FastAPI:
    """
    Factory function para criar aplicação FastAPI.
    
    Permite configuração diferente para testes.
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Gov.br Auth API",
        description="""
# API para Autenticação Gov.br e Integração SIGEF

API para autenticação no Gov.br via certificado digital A1/A3
e integração com SIGEF INCRA para download de dados de parcelas.

## 🔐 Autenticação

A API utiliza autenticação via Bearer Token (API Key):

```
Authorization: Bearer sua-api-key-aqui
```

## 📋 Funcionalidades

### Autenticação
- **Login Gov.br**: Autenticação via certificado digital (browser remoto)
- **Status**: Verificação de sessão ativa
- **Logout**: Encerramento de sessão

### Integração SIGEF
- **Consulta**: Busca de parcelas por código
- **Detalhes**: Informações completas da parcela
- **Download**: CSV de parcela, vértices e limites

### Download Direto (para C#/.NET)
Os endpoints `/sigef/arquivo/*` retornam arquivos diretamente como bytes,
facilitando integração com aplicações externas.

## 🚀 Início Rápido

### 1. Autenticar
```bash
curl -X POST http://localhost:8000/api/v1/auth/browser-login
# Retorna URL para login no navegador
```

### 2. Download de CSV
```bash
curl -o parcela.csv http://localhost:8000/api/v1/sigef/arquivo/csv/{codigo}/parcela
```

### 3. Download Completo (ZIP)
```bash
curl -o completo.zip http://localhost:8000/api/v1/sigef/arquivo/todos/{codigo}
```

## 📦 Integração C#

```csharp
var client = new HttpClient();
client.DefaultRequestHeaders.Authorization = 
    new AuthenticationHeaderValue("Bearer", "sua-api-key");

// Download CSV
var response = await client.GetAsync(
    "http://localhost:8000/api/v1/sigef/arquivo/csv/{codigo}/parcela"
);
var bytes = await response.Content.ReadAsByteArrayAsync();
File.WriteAllBytes("parcela.csv", bytes);
```

## 📚 Documentação Completa

- [Integração C#](https://github.com/seu-repo/gov-auth/blob/main/INTEGRACAO_CSHARP.md)
- [Docker Deploy](https://github.com/seu-repo/gov-auth/blob/main/DOCKER_DEPLOY.md)
        """,
        version="1.0.0",
        docs_url=None,  # Configuraremos manualmente
        redoc_url=None,  # Configuraremos manualmente
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        swagger_ui_parameters={
            "syntaxHighlight.theme": "monokai",
            "tryItOutEnabled": True,
            "displayRequestDuration": True,
        },
        openapi_tags=[
            {
                "name": "Autenticação",
                "description": "Endpoints para login/logout Gov.br e gerenciamento de sessão",
            },
            {
                "name": "SIGEF",
                "description": "Consulta e download de dados de parcelas do SIGEF INCRA",
            },
            {
                "name": "Download Direto",
                "description": "Endpoints para download direto de arquivos (ideal para C#/.NET)",
            },
            {
                "name": "Consulta WFS",
                "description": "Consulta geoespacial de imóveis rurais via WFS",
            },
            {
                "name": "Health",
                "description": "Verificação de saúde da aplicação",
            },
        ],
    )
    
    # Security Headers (sempre ativo)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API Key é validada via dependência explícita nos endpoints (RequireAPIKey)
    # Não usamos mais middleware global
    
    # Exception handlers
    @app.exception_handler(GovAuthException)
    async def govauth_exception_handler(request: Request, exc: GovAuthException):
        """Handler para exceções do domínio."""
        return JSONResponse(
            status_code=exc.status_code if hasattr(exc, "status_code") else 500,
            content={
                "error": exc.__class__.__name__,
                "detail": str(exc),
            },
        )
    
    # Rotas - sem prefix pois Nginx já encaminha /api/v1/... como /api/v1/...
    # O root_path="/api" cuida da documentação Swagger
    app.include_router(v1_router)
    
    # Middleware para CSS dark mode no Swagger UI
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    
    class SwaggerContrastMiddleware(BaseHTTPMiddleware):
            """Injeta CSS dark mode no Swagger UI."""
            
            CUSTOM_CSS = """
<style>
/* ========== MINIMAL DARK MODE ========== */

/* Cores base - paleta simples */
:root {
    --bg-primary: #121212;
    --bg-secondary: #1e1e1e;
    --bg-tertiary: #2a2a2a;
    --text-primary: #ffffff;
    --text-secondary: #d0d0d0;
    --text-heading: #ffffff;
    --border: #333;
    --accent: #6c9eff;
}

/* Reset de fundo - TUDO escuro */
html, body {
    background: var(--bg-primary) !important;
}
.swagger-ui,
.swagger-ui .wrapper,
.swagger-ui .scheme-container,
.swagger-ui .opblock-body,
.swagger-ui .opblock-section-header,
.swagger-ui .responses-wrapper,
.swagger-ui .response,
.swagger-ui .model-container,
.swagger-ui .loading-container,
.swagger-ui .dialog-ux .modal-ux,
.swagger-ui .dialog-ux .modal-ux-content,
.swagger-ui section.models,
.swagger-ui section.models .model-box,
.swagger-ui .model-box-control,
.swagger-ui .models-control,
.swagger-ui .opblock-description-wrapper {
    background: var(--bg-primary) !important;
}

/* Topbar escondida ou escura */
.swagger-ui .topbar {
    background: var(--bg-secondary) !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 8px 0 !important;
}

/* Títulos e headers - brancos */
.swagger-ui .info .title,
.swagger-ui .markdown h1,
.swagger-ui .markdown h2,
.swagger-ui .markdown h3,
.swagger-ui .markdown h4,
.swagger-ui .opblock-tag,
.swagger-ui .opblock-section-header h4,
.swagger-ui .responses-inner h4,
.swagger-ui .responses-inner h5,
.swagger-ui .dialog-ux .modal-ux-header h3,
.swagger-ui section.models h4 {
    color: var(--text-heading) !important;
}

/* Textos normais */
.swagger-ui,
.swagger-ui .info .description,
.swagger-ui .info .description p,
.swagger-ui .info li,
.swagger-ui .info a,
.swagger-ui .markdown p,
.swagger-ui .markdown li,
.swagger-ui .renderedMarkdown p,
.swagger-ui .opblock-summary-path,
.swagger-ui .opblock-summary-path span,
.swagger-ui .opblock-summary-description,
.swagger-ui .response-col_status,
.swagger-ui .response-col_description,
.swagger-ui .parameter__name,
.swagger-ui .parameter__type,
.swagger-ui .parameter__in,
.swagger-ui .model,
.swagger-ui .model-title,
.swagger-ui .prop-type,
.swagger-ui .prop-format,
.swagger-ui .servers > label,
.swagger-ui label,
.swagger-ui .dialog-ux .modal-ux-header h3,
.swagger-ui .dialog-ux .modal-ux-content p,
.swagger-ui table thead tr th,
.swagger-ui table tbody tr td,
.swagger-ui .col_header {
    color: var(--text-primary) !important;
}

/* Textos secundários */
.swagger-ui .opblock-tag small,
.swagger-ui .opblock-summary-description,
.swagger-ui .response-col_description,
.swagger-ui .parameter__in,
.swagger-ui .prop-format {
    color: var(--text-secondary) !important;
}

/* Links */
.swagger-ui a {
    color: var(--accent) !important;
}

/* Código inline */
.swagger-ui code,
.swagger-ui .markdown code {
    background: var(--bg-tertiary) !important;
    color: #f8f8f2 !important;
    padding: 2px 6px !important;
    border-radius: 3px !important;
    border: none !important;
}

/* Blocos de código */
.swagger-ui pre,
.swagger-ui .markdown pre,
.swagger-ui pre.microlight,
.swagger-ui .highlight-code pre {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 12px !important;
}
.swagger-ui pre code,
.swagger-ui .markdown pre code {
    background: transparent !important;
    color: var(--text-primary) !important;
    padding: 0 !important;
}

/* Tabelas simples */
.swagger-ui table,
.swagger-ui .markdown table {
    border-collapse: collapse !important;
}
.swagger-ui table th,
.swagger-ui .markdown table th {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    padding: 10px !important;
    border: 1px solid var(--border) !important;
    font-weight: 600 !important;
}
.swagger-ui table td,
.swagger-ui .markdown table td {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    padding: 8px !important;
    border: 1px solid var(--border) !important;
}

/* Seções/Tags */
.swagger-ui .opblock-tag-section {
    border: none !important;
}
.swagger-ui .opblock-tag {
    border-bottom: 1px solid var(--border) !important;
}
.swagger-ui .opblock-tag:hover {
    background: var(--bg-secondary) !important;
}
.swagger-ui .expand-operation svg,
.swagger-ui .expand-methods svg {
    fill: var(--text-secondary) !important;
}

/* Operações - mesmo estilo, só badge colorido */
.swagger-ui .opblock {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    margin-bottom: 8px !important;
}
.swagger-ui .opblock .opblock-summary {
    border: none !important;
}
.swagger-ui .opblock-summary-method {
    font-weight: 700 !important;
    border-radius: 3px !important;
    min-width: 70px !important;
}
/* GET - verde discreto */
.swagger-ui .opblock.opblock-get .opblock-summary-method {
    background: #2e7d32 !important;
    color: #fff !important;
}
/* POST - azul discreto */
.swagger-ui .opblock.opblock-post .opblock-summary-method {
    background: #1976d2 !important;
    color: #fff !important;
}
/* DELETE - vermelho discreto */
.swagger-ui .opblock.opblock-delete .opblock-summary-method {
    background: #c62828 !important;
    color: #fff !important;
}
/* PUT - laranja discreto */
.swagger-ui .opblock.opblock-put .opblock-summary-method {
    background: #ef6c00 !important;
    color: #fff !important;
}

/* Seção expandida */
.swagger-ui .opblock-body {
    border-top: 1px solid var(--border) !important;
}
.swagger-ui .opblock-section-header {
    border-bottom: 1px solid var(--border) !important;
    padding: 8px 12px !important;
}

/* Inputs */
.swagger-ui input[type="text"],
.swagger-ui input[type="password"],
.swagger-ui input[type="email"],
.swagger-ui textarea,
.swagger-ui select {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 8px !important;
}
.swagger-ui input:focus,
.swagger-ui textarea:focus,
.swagger-ui select:focus {
    border-color: var(--accent) !important;
    outline: none !important;
}

/* Botões - minimalistas */
.swagger-ui .btn {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    font-weight: 500 !important;
}
.swagger-ui .btn:hover {
    background: #383838 !important;
}
.swagger-ui .btn.execute {
    background: #1976d2 !important;
    border-color: #1976d2 !important;
    color: #fff !important;
}
.swagger-ui .btn.execute:hover {
    background: #1565c0 !important;
}
.swagger-ui .btn.cancel {
    background: var(--bg-tertiary) !important;
}
.swagger-ui .try-out__btn {
    background: transparent !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent) !important;
}

/* Parameters table */
.swagger-ui table.parameters {
    border: none !important;
}
.swagger-ui table.parameters > tbody > tr > td {
    border-bottom: 1px solid var(--border) !important;
    padding: 10px 0 !important;
}

/* Responses */
.swagger-ui table.responses-table > tbody > tr > td {
    border-bottom: 1px solid var(--border) !important;
    padding: 10px !important;
}
.swagger-ui .response-col_links {
    color: var(--text-secondary) !important;
}

/* Models section */
.swagger-ui section.models {
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}
.swagger-ui section.models h4 {
    color: var(--text-primary) !important;
}
.swagger-ui .model-box {
    background: var(--bg-secondary) !important;
}

/* Botões Expand/Collapse e badges brancos */
.swagger-ui .model-box-control,
.swagger-ui .models-control,
.swagger-ui .model-toggle,
.swagger-ui .model-toggle::after,
.swagger-ui span.model-toggle,
.swagger-ui .json-schema-2020-12-expand-collapse,
.swagger-ui button.model-box-control,
.swagger-ui .model-container > .model-box {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}

/* Badges Any of, Collapse all, Expand all */
.swagger-ui .json-schema-2020-12-keyword,
.swagger-ui .json-schema-2020-12-keyword__name,
.swagger-ui .json-schema-2020-12-keyword__value,
.swagger-ui .json-schema-2020-12-summary,
.swagger-ui .model-title__text,
.swagger-ui .json-schema-2020-12-anyof,
.swagger-ui .json-schema-2020-12-oneof,
.swagger-ui .json-schema-2020-12-allof,
.swagger-ui button,
.swagger-ui [class*="json-schema"] {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}

/* Schema tabs e toggles */
.swagger-ui .tab,
.swagger-ui .tab li,
.swagger-ui .tab li button,
.swagger-ui .opblock-description-wrapper,
.swagger-ui .opblock-external-docs-wrapper,
.swagger-ui .opblock-title_normal {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* Botões de modelos */
.swagger-ui .model-toggle,
.swagger-ui .model-jump-to-path,
.swagger-ui .inner-object,
.swagger-ui .renderedMarkdown,
.swagger-ui .property-row {
    background: transparent !important;
}

/* Spans e elementos inline com fundo branco */
.swagger-ui span,
.swagger-ui .brace-open,
.swagger-ui .brace-close,
.swagger-ui .inner-object {
    background: transparent !important;
}

/* Reset específico para elementos de schema */
.swagger-ui .json-schema-2020-12-accordion,
.swagger-ui .json-schema-2020-12-body,
.swagger-ui .json-schema-form-item,
.swagger-ui .json-schema-form-item-add,
.swagger-ui .json-schema-form-item-remove {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}

/* Model wrapper */
.swagger-ui .model-wrapper,
.swagger-ui .model,
.swagger-ui .model-example,
.swagger-ui .example {
    background: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
}

/* Authorization icons */
.swagger-ui .authorization__btn svg {
    fill: var(--text-secondary) !important;
}
.swagger-ui .authorization__btn.locked svg {
    fill: #4caf50 !important;
}
.swagger-ui .authorization__btn.unlocked svg {
    fill: #f44336 !important;
}

/* Modal */
.swagger-ui .dialog-ux .backdrop-ux {
    background: rgba(0,0,0,0.7) !important;
}
.swagger-ui .dialog-ux .modal-ux {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}
.swagger-ui .dialog-ux .modal-ux-header {
    border-bottom: 1px solid var(--border) !important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: var(--bg-primary);
}
::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #555;
}

/* Filter input */
.swagger-ui .filter-container {
    background: var(--bg-primary) !important;
}
.swagger-ui .filter-container .filter {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border) !important;
}

/* Info icons */
.swagger-ui .info__extlink svg {
    fill: var(--text-secondary) !important;
}

/* Remove box shadows */
.swagger-ui .opblock,
.swagger-ui .model-container,
.swagger-ui .scheme-container {
    box-shadow: none !important;
}
</style>
"""
            
            async def dispatch(self, request, call_next):
                response = await call_next(request)
                
                # Injeta CSS apenas na página /docs
                if request.url.path == "/docs" and response.status_code == 200:
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    # Injeta CSS antes do </head>
                    body_str = body.decode()
                    body_str = body_str.replace(
                        "</head>",
                        f"{self.CUSTOM_CSS}</head>"
                    )
                    
                    # Remove Content-Length dos headers originais (será recalculado)
                    new_headers = {
                        k: v for k, v in response.headers.items()
                        if k.lower() != "content-length"
                    }
                    
                    return Response(
                        content=body_str,
                        status_code=response.status_code,
                        headers=new_headers,
                        media_type="text/html",
                    )
                
                return response
    
    app.add_middleware(SwaggerContrastMiddleware)
    
    # Rota de página HTML de autenticação
    from src.api.v1.static.auth_page import HTML_AUTH_PAGE
    from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
    
    @app.get("/docs", include_in_schema=False)
    async def swagger_ui():
        """Swagger UI."""
        return get_swagger_ui_html(
            openapi_url="/api/openapi.json",
            title="Gov.br Auth API - Docs",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc():
        """ReDoc."""
        return get_redoc_html(
            openapi_url="/api/openapi.json",
            title="Gov.br Auth API - ReDoc",
        )
    
    @app.get("/auth-browser", tags=["Autenticação"])
    async def auth_browser_page():
        """Página HTML de autenticação do navegador do cliente."""
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=HTML_AUTH_PAGE)
    
    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Verifica saúde da aplicação."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.environment,
            "timestamp": datetime.now().isoformat(),
        }
    
    @app.get("/", tags=["Info"])
    async def root():
        """Informações da API."""
        return {
            "name": "Gov.br Auth API",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else "Disabled in production",
            "health": "/health",
            "api": "/api/v1",
        }
    
    return app


# Instância da aplicação
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
