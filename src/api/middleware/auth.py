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
    """
    
    PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/"}
    PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi")
    
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
        
        # Valida API Key no header Authorization
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            logger.warning(
                "Requisição sem Authorization header",
                path=request.url.path,
                client=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Formato esperado: "Bearer <api_key>"
        try:
            scheme, credentials = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Valida API Key
        if credentials != settings.api_key:
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
