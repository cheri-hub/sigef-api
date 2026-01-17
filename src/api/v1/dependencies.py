"""
Injeção de Dependências.

Configura e fornece instâncias dos serviços
usando o sistema de dependency injection do FastAPI.
"""

import secrets
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import Settings, get_settings
from src.core.logging import get_logger
from src.domain.interfaces import IGovBrAuthenticator, ISessionRepository, ISigefClient
from src.infrastructure.govbr import PlaywrightGovBrAuthenticator
from src.infrastructure.persistence import FileSessionRepository
from src.infrastructure.sigef import HttpSigefClient
from src.services.auth_service import AuthService
from src.services.sigef_service import SigefService

logger = get_logger(__name__)


# ============== Segurança ==============

# Esquemas de autenticação
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
) -> str:
    """
    Valida API Key via header X-API-Key ou Authorization: Bearer.
    
    Aceita dois formatos:
    - Header: X-API-Key: sua-api-key
    - Header: Authorization: Bearer sua-api-key
    
    Raises:
        HTTPException: Se API Key inválida ou ausente
    
    Returns:
        API Key validada
    """
    settings = get_settings()
    
    # Em desenvolvimento, permite sem API Key
    if settings.is_development:
        return "dev-mode"
    
    # Extrai API Key do header apropriado
    provided_key = None
    
    if api_key:
        provided_key = api_key
    elif bearer and bearer.credentials:
        provided_key = bearer.credentials
    
    if not provided_key:
        logger.warning("Requisição sem API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key não fornecida. Use header 'X-API-Key' ou 'Authorization: Bearer <key>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Valida API Key (constant-time comparison previne timing attacks)
    if not secrets.compare_digest(provided_key, settings.api_key):
        logger.warning("API Key inválida fornecida")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida",
        )
    
    return provided_key


# Type alias para uso nos endpoints
RequireAPIKey = Annotated[str, Depends(verify_api_key)]


# ============== Infraestrutura ==============

@lru_cache
def get_session_repository() -> ISessionRepository:
    """Retorna repositório de sessões (singleton)."""
    return FileSessionRepository()


@lru_cache
def get_govbr_authenticator() -> IGovBrAuthenticator:
    """Retorna autenticador Gov.br (singleton)."""
    return PlaywrightGovBrAuthenticator()


@lru_cache
def get_sigef_client() -> ISigefClient:
    """Retorna cliente SIGEF (singleton)."""
    return HttpSigefClient()


# ============== Serviços ==============

@lru_cache
def get_auth_service() -> AuthService:
    """Retorna serviço de autenticação (singleton)."""
    return AuthService(
        govbr_authenticator=get_govbr_authenticator(),
        sigef_client=get_sigef_client(),
        session_repository=get_session_repository(),
    )


@lru_cache
def get_sigef_service() -> SigefService:
    """Retorna serviço SIGEF (singleton)."""
    return SigefService(
        sigef_client=get_sigef_client(),
        session_repository=get_session_repository(),
        auth_service=get_auth_service(),
    )


# ============== Reset (para testes) ==============

def reset_dependencies() -> None:
    """Limpa cache de dependências (útil para testes)."""
    get_session_repository.cache_clear()
    get_govbr_authenticator.cache_clear()
    get_sigef_client.cache_clear()
    get_auth_service.cache_clear()
    get_sigef_service.cache_clear()
