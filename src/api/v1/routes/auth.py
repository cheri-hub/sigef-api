"""
Rotas de Autenticação.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.v1.dependencies import get_auth_service, RequireAPIKey
from src.api.v1.schemas import (
    AuthStatusResponse,
    BrowserCallbackRequest,
    BrowserLoginResponse,
    LoginResponse,
    SessionInfoResponse,
)
from src.core.exceptions import GovBrError, SessionExpiredError
from src.core.logging import get_logger
from src.infrastructure.browser_auth import BrowserAuthSession
from src.services.auth_service import AuthService

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Verifica status de autenticação",
    description="Retorna se existe uma sessão válida e seus detalhes.",
)
async def get_auth_status(
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    """Verifica status de autenticação."""
    is_valid, session = await auth_service.validate_current_session()
    
    if is_valid and session:
        return AuthStatusResponse(
            authenticated=True,
            session=SessionInfoResponse(
                session_id=session.session_id,
                cpf=session.cpf,
                nome=session.nome,
                is_valid=session.is_valid(),
                is_govbr_authenticated=session.is_govbr_authenticated,
                is_sigef_authenticated=session.is_sigef_authenticated,
                created_at=session.created_at,
                expires_at=session.expires_at,
                last_used_at=session.last_used_at,
            ),
            message="Sessão válida",
        )
    
    return AuthStatusResponse(
        authenticated=False,
        session=None,
        message="Nenhuma sessão válida encontrada",
    )


@router.post(
    "/browser-login",
    response_model=BrowserLoginResponse,
    summary="Inicia autenticação Gov.br no navegador do cliente",
    description="""
    Retorna URL de autenticação para o cliente abrir no seu navegador.
    
    **Fluxo:**
    1. Cliente chama este endpoint
    2. Recebe uma URL com auth_token
    3. Cliente abre a URL no navegador (em sua máquina)
    4. Usuário faz login no Gov.br
    5. Página retorna os cookies para a API
    6. Sessão fica pronta para uso
    
    Funciona com Docker e servidores sem acesso a display!
    """,
)
async def browser_login(request: Request) -> BrowserLoginResponse:
    """
    Inicia fluxo de autenticação no navegador do cliente.
    
    NÃO abre navegador no servidor, apenas retorna a URL.
    """
    browser_auth = BrowserAuthSession()
    session_data = browser_auth.create_browser_session()
    
    # Constrói URL de autenticação
    # O cliente usará esta URL para fazer login no Gov.br
    base_url = str(request.base_url).rstrip("/")
    login_url = f"{base_url}/auth-browser?token={session_data['auth_token']}"
    
    logger.info(
        f"Sessão de browser-login criada: {session_data['session_id']}"
    )
    
    return BrowserLoginResponse(
        auth_token=session_data["auth_token"],
        session_id=session_data["session_id"],
        login_url=login_url,
    )


@router.post(
    "/browser-callback",
    summary="Callback de autenticação do navegador",
    description="""
    Recebe os cookies e dados de autenticação retornados pelo navegador do cliente.
    
    Uso interno: chamado automaticamente pela página de autenticação após o login.
    """,
)
async def browser_callback(
    callback_data: BrowserCallbackRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """
    Processa callback da autenticação do navegador.
    
    Este endpoint:
    1. Recebe os cookies capturados no navegador do cliente
    2. Cria uma sessão válida com esses cookies
    3. Persiste a sessão
    """
    browser_auth = BrowserAuthSession()
    
    # Valida o token
    session_data = browser_auth.get_browser_session(callback_data.auth_token)
    if not session_data:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido ou expirado"
        )
    
    # Salva os cookies
    cookies_info = {
        "govbr_cookies": callback_data.govbr_cookies,
        "sigef_cookies": callback_data.sigef_cookies,
        "jwt_payload": callback_data.jwt_payload,
    }
    
    success = browser_auth.save_browser_cookies(
        callback_data.auth_token,
        cookies_info
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Erro ao salvar cookies de autenticação"
        )
    
    # Cria sessão no repositório com os cookies retornados
    try:
        session = await auth_service.create_session_from_browser_auth(
            session_data["session_id"],
            callback_data.govbr_cookies,
            callback_data.sigef_cookies,
            callback_data.jwt_payload,
        )
        
        logger.info(
            f"Sessão criada via browser-callback: {session.session_id}"
        )
        
        return {
            "success": True,
            "message": "Autenticação completa",
            "session_id": session.session_id,
        }
    
    except Exception as e:
        logger.error(f"Erro ao criar sessão via browser: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar sessão: {str(e)}"
        )


@router.get(
    "/login",
    response_model=BrowserLoginResponse,
    summary="Inicia autenticação Gov.br",
    description="Retorna URL de autenticação para o cliente.",
)
async def get_login_url(request: Request) -> BrowserLoginResponse:
    """Alias para /browser-login (GET)."""
    browser_auth = BrowserAuthSession()
    session_data = browser_auth.create_browser_session()
    
    base_url = str(request.base_url).rstrip("/")
    login_url = f"{base_url}/auth-browser?token={session_data['auth_token']}"
    
    return BrowserLoginResponse(
        auth_token=session_data["auth_token"],
        session_id=session_data["session_id"],
        login_url=login_url,
    )


@router.post(
    "/logout",
    summary="Encerra sessão",
    description="Remove a sessão atual.",
)
async def logout(
    _api_key: RequireAPIKey,
    session_id: str | None = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """
    Encerra sessão.
    
    Args:
        session_id: ID da sessão a encerrar. Se não informado, encerra a atual.
    """
    await auth_service.logout(session_id)
    return {"message": "Logout realizado com sucesso"}


@router.get(
    "/session",
    response_model=SessionInfoResponse | None,
    summary="Obtém informações da sessão",
    description="Retorna detalhes da sessão atual.",
)
async def get_session_info(
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionInfoResponse | None:
    """Retorna informações da sessão atual."""
    info = await auth_service.get_session_info()
    
    if not info:
        return None
    
    return SessionInfoResponse(**info)
