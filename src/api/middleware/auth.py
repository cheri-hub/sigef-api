"""
Middleware de autenticação API Key.
"""

import secrets

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
    """
    
    PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/"}
    
    async def dispatch(self, request: Request, call_next):
        """Processa requisição e valida API Key."""
        settings = get_settings()
        
        # Permite rotas públicas
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Em desenvolvimento, permite sem API Key
        if settings.is_development:
            return await call_next(request)
        
        # Valida API Key - aceita X-API-Key ou Authorization: Bearer
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization")
        
        provided_key = None
        
        if api_key:
            provided_key = api_key
        elif auth_header:
            # Formato esperado: "Bearer <api_key>"
            try:
                scheme, credentials = auth_header.split()
                if scheme.lower() == "bearer":
                    provided_key = credentials
            except ValueError:
                pass
        
        if not provided_key:
            logger.warning(
                "Requisição sem API Key",
                path=request.url.path,
                client=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key não fornecida. Use header 'X-API-Key' ou 'Authorization: Bearer <key>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Valida API Key (constant-time comparison previne timing attacks)
        if not secrets.compare_digest(provided_key, settings.api_key):
            logger.warning(
                "API Key inválida",
                path=request.url.path,
                client=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key inválida",
            )
        
        logger.debug(
            "Requisição autenticada",
            path=request.url.path,
            method=request.method
        )
        
        return await call_next(request)
