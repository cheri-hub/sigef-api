"""
Serviço de Autenticação.

Orquestra o fluxo de autenticação Gov.br e SIGEF,
gerenciando sessões e validações.
"""

from src.core.exceptions import SessionExpiredError
from src.core.logging import get_logger
from src.core.security import mask_cpf
from src.domain.entities import Session
from src.domain.interfaces import IGovBrAuthenticator, ISessionRepository, ISigefClient

logger = get_logger(__name__)


class AuthService:
    """
    Serviço de autenticação seguindo princípios SOLID.
    
    - Single Responsibility: Apenas orquestra autenticação
    - Open/Closed: Extensível via novas implementações das interfaces
    - Liskov Substitution: Usa abstrações, não implementações
    - Interface Segregation: Interfaces específicas por responsabilidade
    - Dependency Inversion: Depende de abstrações injetadas
    """
    
    def __init__(
        self,
        govbr_authenticator: IGovBrAuthenticator,
        sigef_client: ISigefClient,
        session_repository: ISessionRepository,
    ):
        """
        Inicializa serviço com dependências injetadas.
        
        Args:
            govbr_authenticator: Implementação de autenticação Gov.br
            sigef_client: Cliente SIGEF
            session_repository: Repositório de sessões
        """
        self.govbr = govbr_authenticator
        self.sigef = sigef_client
        self.sessions = session_repository
    
    async def get_or_create_session(self, force_new: bool = False) -> Session:
        """
        Obtém sessão existente válida ou cria nova.
        
        Args:
            force_new: Se True, sempre cria nova sessão.
        
        Returns:
            Sessão autenticada no Gov.br e SIGEF.
        """
        if not force_new:
            # Tenta carregar sessão existente
            session = await self.sessions.load_latest()
            
            if session and session.is_valid():
                logger.info(
                    "Usando sessão existente",
                    session_id=session.session_id,
                    cpf=session.cpf,
                )
                
                # Valida se ainda funciona
                if await self.govbr.validate_session(session):
                    session.touch()
                    await self.sessions.save(session)
                    return session
                
                logger.info("Sessão existente inválida, criando nova")
        
        # Cria nova sessão
        return await self.create_new_session()
    
    async def create_new_session(self) -> Session:
        """
        Cria nova sessão autenticada.
        
        Fluxo:
        1. Autentica no Gov.br (interativo com certificado)
        2. Usa sessão Gov.br para autenticar no SIGEF
        3. Persiste sessão combinada
        
        Returns:
            Sessão autenticada em ambas plataformas.
        """
        logger.info("Iniciando nova autenticação")
        
        # 1. Gov.br
        session = await self.govbr.authenticate(headless=False)
        logger.info("Gov.br autenticado", cpf_masked=mask_cpf(session.cpf))
        
        # 2. SIGEF
        session = await self.sigef.authenticate(session)
        logger.info("SIGEF autenticado")
        
        # 3. Persiste
        await self.sessions.save(session)
        logger.info("Sessão persistida", session_id=session.session_id)
        
        return session
    
    async def validate_current_session(self) -> tuple[bool, Session | None]:
        """
        Valida a sessão atual.
        
        Returns:
            Tupla (is_valid, session). Session é None se inválida.
        """
        session = await self.sessions.load_latest()
        
        if not session:
            return False, None
        
        if session.is_expired():
            logger.info("Sessão expirada", session_id=session.session_id)
            return False, None
        
        is_valid = await self.govbr.validate_session(session)
        
        if is_valid:
            session.touch()
            await self.sessions.save(session)
            return True, session
        
        return False, None
    
    async def logout(self, session_id: str | None = None) -> None:
        """
        Encerra uma sessão.
        
        Args:
            session_id: ID da sessão a encerrar.
                       Se None, encerra a mais recente.
        """
        if session_id:
            await self.sessions.delete(session_id)
        else:
            session = await self.sessions.load_latest()
            if session:
                await self.sessions.delete(session.session_id)
        
        logger.info("Sessão encerrada", session_id=session_id)
    
    async def create_session_from_browser_auth(
        self,
        session_id: str,
        govbr_cookies: list[dict],
        sigef_cookies: list[dict] | None = None,
        jwt_payload: dict | None = None,
    ):
        """
        Cria uma sessão a partir de dados retornados pela autenticação no browser.
        
        Usado quando o cliente faz login no navegador e retorna os cookies para a API.
        NÃO altera a autenticação Gov.br/SIGEF existente.
        
        Args:
            session_id: ID da sessão
            govbr_cookies: Cookies do Gov.br capturados no navegador
            sigef_cookies: Cookies do SIGEF (opcional)
            jwt_payload: Dados JWT do Gov.br (opcional)
        
        Returns:
            Session criada com os dados fornecidos
        """
        from src.domain.entities import Cookie, Session, JWTPayload
        
        logger.info(f"Criando sessão via browser auth: {session_id}")
        
        # Converte cookies dict para objetos Cookie
        govbr_cookie_objs = []
        for cookie_data in govbr_cookies:
            govbr_cookie_objs.append(
                Cookie(
                    name=cookie_data.get("name", ""),
                    value=cookie_data.get("value", ""),
                    domain=cookie_data.get("domain", ""),
                    path=cookie_data.get("path", "/"),
                    expires=cookie_data.get("expires"),
                    http_only=cookie_data.get("httpOnly", False),
                    secure=cookie_data.get("secure", False),
                    same_site=cookie_data.get("sameSite", "Lax"),
                )
            )
        
        sigef_cookie_objs = []
        if sigef_cookies:
            for cookie_data in sigef_cookies:
                sigef_cookie_objs.append(
                    Cookie(
                        name=cookie_data.get("name", ""),
                        value=cookie_data.get("value", ""),
                        domain=cookie_data.get("domain", ""),
                        path=cookie_data.get("path", "/"),
                        expires=cookie_data.get("expires"),
                        http_only=cookie_data.get("httpOnly", False),
                        secure=cookie_data.get("secure", False),
                        same_site=cookie_data.get("sameSite", "Lax"),
                    )
                )
        
        # Cria JWT payload se fornecido
        jwt_obj = None
        if jwt_payload:
            jwt_obj = JWTPayload(
                cpf=jwt_payload.get("cpf"),
                nome=jwt_payload.get("nome"),
                email=jwt_payload.get("email"),
                access_token=jwt_payload.get("access_token"),
                id_token=jwt_payload.get("id_token"),
                cnpjs=jwt_payload.get("cnpjs", []),
                nivel_acesso=jwt_payload.get("nivel_acesso", "bronze"),
                raw=jwt_payload.get("raw", {}),
            )
        
        # Cria session
        session = Session(
            session_id=session_id,
            cpf=jwt_payload.get("cpf") if jwt_payload else None,
            nome=jwt_payload.get("nome") if jwt_payload else None,
            jwt_payload=jwt_obj,
            govbr_cookies=govbr_cookie_objs,
            sigef_cookies=sigef_cookie_objs,
        )
        
        # Marca como autenticado
        session.is_govbr_authenticated = len(govbr_cookie_objs) > 0
        session.is_sigef_authenticated = len(sigef_cookie_objs) > 0
        
        # Persiste
        await self.sessions.save(session)
        
        logger.info(
            f"Sessão criada via browser auth",
            session_id=session_id,
            cpf_masked=mask_cpf(session.cpf) if session.cpf else "N/A",
        )
        
        return session
    
    async def get_session_info(self) -> dict | None:
        """
        Retorna informações da sessão atual.
        
        Returns:
            Dicionário com dados do usuário ou None.
        """
        session = await self.sessions.load_latest()
        
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "cpf": session.cpf,
            "nome": session.nome,
            "is_valid": session.is_valid(),
            "is_govbr_authenticated": session.is_govbr_authenticated,
            "is_sigef_authenticated": session.is_sigef_authenticated,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
        }
