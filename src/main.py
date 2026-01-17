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
from fastapi.openapi.utils import get_openapi

from src.api.v1 import router as v1_router
from src.api.middleware.auth import APIKeyMiddleware
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
        API para autenticação no Gov.br via certificado digital A1
        e integração com SIGEF INCRA para download de dados de parcelas.
        
        ## Funcionalidades
        
        - **Autenticação Gov.br**: Login via certificado digital
        - **Integração SIGEF**: Download de dados de parcelas
        - **Download CSV**: Exportação de Parcela, Vértice e Limites
        - **Batch Processing**: Download em lote de múltiplas parcelas
        
        ## Autenticação
        
        As rotas `/v1/sigef/*` e `/v1/auth/login` requerem autenticação via API Key.
        Use o botão **Authorize** acima e insira: `Bearer <sua-api-key>`
        
        Rotas públicas (sem autenticação):
        - `/v1/consultar/*` - Consultas WFS
        - `/v1/auth/status` - Status da sessão
        
        ## Uso
        
        1. Faça login via `/v1/auth/login`
        2. Verifique status via `/v1/auth/status`
        3. Baixe dados via `/v1/sigef/download`
        """,
        version="1.0.0",
        root_path="/api" if settings.is_production else "",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Custom OpenAPI schema with security
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key",
                "description": "Insira sua API Key"
            }
        }
        # Apply security to all routes except public ones
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                # Skip public routes
                if "/consultar" in path or "/auth/status" in path or path in ["/health", "/"]:
                    continue
                if method != "parameters":
                    openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API Key Authentication (apenas em produção)
    if settings.is_production:
        app.add_middleware(APIKeyMiddleware)
    
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
    
    # Rotas
    app.include_router(v1_router)
    
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
