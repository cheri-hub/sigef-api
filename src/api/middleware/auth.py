"""
Middleware de autenticação API Key.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Valida API Key em todas as requisições exceto rotas públicas.
    
    Rotas públicas (não requerem autenticação):
    - /health
    - /docs
    - /redoc
    - /openapi.json
    - /api/v1/consultar (WFS queries)
    - /api/v1/auth/status
    """
    
    PUBLIC_PATHS = {
        "/health", "/docs", "/redoc", "/openapi.json", "/",
    }
    PUBLIC_PREFIXES = (
        "/docs", "/redoc", "/openapi",
        "/v1/consultar", "/v1/auth/status",
    )
    
    async def dispatch(self, request: Request, call_next):
        """Processa requisição e valida API Key."""
        settings = get_settings()
        path = request.url.path
        
        # Permite rotas públicas (match exato)
        if path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Permite rotas públicas (match por prefixo)
        if path.startswith(self.PUBLIC_PREFIXES):
            return await call_next(request)
        
        # Em desenvolvimento, permite sem API Key
        if settings.is_development:
            return await call_next(request)
        
        # Valida API Key no header X-API-Key
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(
                "Requisição sem X-API-Key header",
                path=request.url.path,
                client=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-API-Key header missing",
            )
        
        # Valida API Key
        if api_key != settings.api_key:
            logger.warning(
                "API Key inválida",
                path=request.url.path,
                client=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API Key",
            )
        
        logger.debug(
            "Requisição autenticada",
            path=request.url.path,
            method=request.method
        )
        
        return await call_next(request)
